"""
cckp_client.py — World Bank CCKP 0.25° 기후 데이터 클라이언트 (독립 모듈)

데이터 출처: AWS S3 공개 버킷 s3://wbg-cckp (무인증)
해상도: 0.25° × 0.25° 전구 격자 (CMIP6 앙상블 평균)
시나리오: SSP1-2.6 / SSP2-4.5 / SSP3-7.0 / SSP5-8.5

제공 변수 (기존 49개에 없는 신규 5개):
  cckp_hi35   — 열지수 초과일 (Heat Index >35°C, 습도 보정 체감온도)
  cckp_hd40   — 극한고온일 (Tmax >40°C)
  cckp_tr26   — 열대야 한국기준 (Tmin >26°C)
  cckp_cdd18  — 냉방도일 (Cooling Degree Days, base 18°C)
  cckp_hdd18  — 난방도일 (Heating Degree Days, base 18°C)

독립 사용:
    import asyncio
    from cckp_client import query_cckp
    result = asyncio.run(query_cckp(36.0, 129.3))
    # → {"cckp_hi35": {"ssp245": {"baseline": 12.3, "near": 18.5, ...}, ...}, ...}

tier_resolver 통합:
    cckp_data = await query_cckp(lat, lon)
    for var, ssp_dict in cckp_data.items():
        for ssp in SSP_KEYS:
            for period in PERIOD_KEYS:
                drivers[ssp][period][var] = {"value": ssp_dict[ssp][period], "source": "CCKP_0.25deg"}
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)

# ── 캐시 디렉토리 ──────────────────────────────────────────────────────────────
# Render: /tmp/cckp_cache (ephemeral, 세션 내 유지)
# 로컬: ~/.climada/cckp_cache
_DEFAULT_CACHE = Path(os.environ.get(
    "CCKP_CACHE_DIR",
    os.path.join(tempfile.gettempdir(), "cckp_cache")
))

# ── S3 공개 버킷 ───────────────────────────────────────────────────────────────
_S3_BASE = "https://wbg-cckp.s3.us-west-2.amazonaws.com"
_COLLECTION = "cmip6-x0.25"
_MODEL = "ensemble-all"

# ── 변수 메타데이터 ─────────────────────────────────────────────────────────────
# CCKP 내부 변수명 → 우리 시스템 변수명 매핑
CCKP_VARS: dict[str, dict] = {
    "cckp_hi35": {
        "cckp_name": "hi35",
        "label":     "열지수 초과일 (HI>35°C)",
        "unit":      "days/yr",
        "desc":      "열지수(체감온도) >35°C 일수 — 기온+습도 복합 열스트레스",
        "reference": "World Bank CCKP CMIP6 0.25°",
    },
    "cckp_hd40": {
        "cckp_name": "hd40",
        "label":     "극한고온일 (Tmax>40°C)",
        "unit":      "days/yr",
        "desc":      "최고기온 >40°C 일수 — 장비·인프라 한계온도 기준",
        "reference": "World Bank CCKP CMIP6 0.25°",
    },
    "cckp_tr26": {
        "cckp_name": "tr26",
        "label":     "열대야 한국기준 (Tmin>26°C)",
        "unit":      "days/yr",
        "desc":      "최저기온 >26°C 일수 — 기상청 폭염특보 기준 (etccdi_tr의 >20°C보다 엄격)",
        "reference": "World Bank CCKP CMIP6 0.25° / KMA",
    },
    "cckp_cdd18": {
        "cckp_name": "cdd18",
        "label":     "냉방도일 (CDD, base 18°C)",
        "unit":      "°C·day/yr",
        "desc":      "냉방에너지 수요 지표 — Σmax(Tavg-18°C, 0)",
        "reference": "World Bank CCKP CMIP6 0.25°",
    },
    "cckp_hdd18": {
        "cckp_name": "hdd18",
        "label":     "난방도일 (HDD, base 18°C)",
        "unit":      "°C·day/yr",
        "desc":      "난방에너지 수요 지표 — Σmax(18°C-Tavg, 0)",
        "reference": "World Bank CCKP CMIP6 0.25°",
    },
}

# ── 기간 매핑: 우리 period_key → CCKP 기간 레이블 ──────────────────────────────
# CCKP는 20년 단위 climatology 제공 (1995-2014, 2020-2039, 2040-2059, 2060-2079, 2080-2099)
_PERIOD_MAP = {
    "baseline": "1995-2014",
    "near":     "2020-2039",
    "mid":      "2040-2059",
    "far":      "2060-2079",
    "end":      "2080-2099",
}
# baseline은 historical 시나리오에서만 사용
_BASELINE_SSP = "historical"

_SSP_KEYS = ["ssp126", "ssp245", "ssp370", "ssp585"]

# ── 메모리 캐시 (프로세스 재시작 전까지 유지) ────────────────────────────────────
_POINT_CACHE: dict[str, Optional[float]] = {}


# ─────────────────────────────────────────────────────────────────────────────
# S3 URL 빌더 — 두 가지 파일명 패턴을 모두 시도
# ─────────────────────────────────────────────────────────────────────────────

def _build_urls(cckp_var: str, ssp: str, period: str) -> list[str]:
    """
    CCKP S3 파일 URL 후보 목록 반환 (파일명 패턴 불확실성 대비 다중 시도).
    참조: worldbank.github.io/climateknowledgeportal/README.html
    """
    scenario = _BASELINE_SSP if period == "baseline" else ssp
    cckp_period = _PERIOD_MAP[period]
    folder = f"{_MODEL}-{scenario}"
    base_path = f"{_S3_BASE}/{_COLLECTION}/{cckp_var}/{folder}"

    candidates = [
        # 패턴 1: climatology-{var}-annual-mean_...
        f"{base_path}/climatology-{cckp_var}-annual-mean_{_COLLECTION}_{_MODEL}-{scenario}_climatology_mean_{cckp_period}.nc",
        # 패턴 2: {var}-climatology-annual-mean_...
        f"{base_path}/{cckp_var}-climatology-annual-mean_{_COLLECTION}_{_MODEL}-{scenario}_{cckp_period}.nc",
        # 패턴 3: mean 없이
        f"{base_path}/climatology-{cckp_var}-annual_{_COLLECTION}_{_MODEL}-{scenario}_climatology_{cckp_period}.nc",
    ]
    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# NC 파일 다운로드 및 포인트 추출
# ─────────────────────────────────────────────────────────────────────────────

def _cache_path(cckp_var: str, ssp: str, period: str, cache_dir: Path) -> Path:
    tag = f"{cckp_var}_{ssp}_{period}"
    return cache_dir / f"{tag}.nc"


async def _download_nc(url: str, dest: Path, timeout: int = 60) -> bool:
    """httpx 스트리밍으로 NC 파일 다운로드. 성공 시 True."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            async with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    return False
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".tmp")
                with open(tmp, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                shutil.move(str(tmp), str(dest))
                return True
    except Exception as exc:
        logger.debug("CCKP download failed %s: %s", url, exc)
        return False


async def _ensure_nc(cckp_var: str, ssp: str, period: str, cache_dir: Path) -> Optional[Path]:
    """
    로컬 캐시에 NC 파일이 없으면 S3에서 다운로드.
    여러 URL 패턴을 순차적으로 시도.
    """
    dest = _cache_path(cckp_var, ssp, period, cache_dir)
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    for url in _build_urls(cckp_var, ssp, period):
        logger.info("CCKP downloading: %s", url)
        ok = await _download_nc(url, dest)
        if ok:
            logger.info("CCKP cached: %s", dest.name)
            return dest

    logger.warning("CCKP: no file found for %s / %s / %s", cckp_var, ssp, period)
    return None


def _extract_point(nc_path: Path, cckp_var: str, lat: float, lon: float) -> Optional[float]:
    """netCDF4로 NC 파일에서 (lat, lon) 포인트 추출."""
    try:
        import netCDF4 as nc  # noqa: PLC0415
        with nc.Dataset(nc_path) as ds:
            # 위도/경도 차원명 탐색
            lat_name = next((k for k in ds.variables if k.lower() in ("lat", "latitude")), None)
            lon_name = next((k for k in ds.variables if k.lower() in ("lon", "longitude")), None)
            if not lat_name or not lon_name:
                return None

            lats = ds.variables[lat_name][:]
            lons = ds.variables[lon_name][:]

            # 0~360 경도 정규화
            if lons.max() > 180:
                lon_q = lon % 360
            else:
                lon_q = lon

            lat_idx = int(np.argmin(np.abs(lats - lat)))
            lon_idx = int(np.argmin(np.abs(lons - lon_q)))

            # 변수명 탐색 (정확 매칭 → 부분 매칭)
            var_key = cckp_var if cckp_var in ds.variables else next(
                (k for k in ds.variables if cckp_var.lower() in k.lower()), None
            )
            if not var_key:
                return None

            data = ds.variables[var_key]
            # 차원: (time?, lat, lon) 또는 (lat, lon)
            if data.ndim == 3:
                val = float(data[0, lat_idx, lon_idx])
            elif data.ndim == 2:
                val = float(data[lat_idx, lon_idx])
            else:
                return None

            # fill_value 처리
            fill = getattr(data, "_FillValue", None) or getattr(data, "missing_value", None)
            if fill is not None and abs(val - float(fill)) < 1e-3:
                return None

            return round(val, 3)

    except Exception as exc:
        logger.warning("CCKP extract failed %s: %s", nc_path.name, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────────────────────

async def query_cckp(
    lat: float,
    lon: float,
    variables: Optional[list[str]] = None,
    ssps: Optional[list[str]] = None,
    cache_dir: Optional[Path] = None,
) -> dict[str, dict]:
    """
    임의 위도/경도 → CCKP 기후 변수값 반환 (비동기).

    Args:
        lat:       위도 (-90 ~ 90)
        lon:       경도 (-180 ~ 180)
        variables: 조회할 변수 키 목록 (None → 전체 5개)
                   예: ["cckp_hi35", "cckp_hd40"]
        ssps:      SSP 목록 (None → 4개 전체)
        cache_dir: NC 파일 캐시 경로 (None → 기본값 사용)

    Returns:
        {
          "cckp_hi35": {
            "ssp126": {"baseline": 5.2, "near": 8.1, "mid": 14.3, "far": 21.0, "end": 28.5},
            "ssp245": {...},
            ...
          },
          "cckp_hd40": {...},
          ...
        }
        값이 없는 경우 None으로 채워짐.
    """
    variables = variables or list(CCKP_VARS.keys())
    ssps      = ssps      or _SSP_KEYS
    cache_dir = cache_dir or _DEFAULT_CACHE
    periods   = list(_PERIOD_MAP.keys())

    result: dict[str, dict] = {v: {ssp: {p: None for p in periods} for ssp in ssps} for v in variables}

    # 모든 (var, ssp, period) 조합 비동기 처리
    tasks = []
    for var_key in variables:
        meta = CCKP_VARS.get(var_key)
        if not meta:
            continue
        cckp_name = meta["cckp_name"]

        for ssp in ssps:
            for period in periods:
                cache_key = f"{cckp_name}_{ssp}_{period}_{lat:.3f}_{lon:.3f}"
                tasks.append((var_key, cckp_name, ssp, period, cache_key))

    # 파일 다운로드를 병렬화 (같은 파일이면 중복 방지)
    download_tasks: dict[str, asyncio.Task] = {}
    for var_key, cckp_name, ssp, period, cache_key in tasks:
        file_key = f"{cckp_name}_{ssp}_{period}"
        if file_key not in download_tasks:
            download_tasks[file_key] = asyncio.create_task(
                _ensure_nc(cckp_name, ssp, period, cache_dir)
            )

    await asyncio.gather(*download_tasks.values(), return_exceptions=True)

    # 포인트 추출 (동기, 빠름)
    for var_key, cckp_name, ssp, period, cache_key in tasks:
        if cache_key in _POINT_CACHE:
            result[var_key][ssp][period] = _POINT_CACHE[cache_key]
            continue

        file_key = f"{cckp_name}_{ssp}_{period}"
        nc_path = download_tasks[file_key].result() if not download_tasks[file_key].exception() else None

        if nc_path:
            val = _extract_point(nc_path, cckp_name, lat, lon)
            _POINT_CACHE[cache_key] = val
            result[var_key][ssp][period] = val

    return result


def query_cckp_sync(
    lat: float,
    lon: float,
    variables: Optional[list[str]] = None,
    ssps: Optional[list[str]] = None,
) -> dict[str, dict]:
    """
    동기 래퍼 — 비-async 환경에서 직접 호출 가능.

    사용:
        from cckp_client import query_cckp_sync
        data = query_cckp_sync(36.0, 129.3)
    """
    return asyncio.run(query_cckp(lat, lon, variables=variables, ssps=ssps))


def list_cckp_vars() -> dict[str, dict]:
    """사용 가능한 CCKP 변수 목록과 메타데이터 반환."""
    return {k: {f: v[f] for f in ("label", "unit", "desc", "reference")} for k, v in CCKP_VARS.items()}


async def verify_cckp_access(var_key: str = "cckp_hi35", ssp: str = "ssp245", period: str = "mid") -> dict:
    """
    S3 접근 가능 여부 확인 — 헬스체크용.
    파일 헤더(1KB)만 요청해서 존재 확인.
    """
    meta = CCKP_VARS.get(var_key)
    if not meta:
        return {"ok": False, "error": f"Unknown variable: {var_key}"}

    urls = _build_urls(meta["cckp_name"], ssp, period)
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in urls:
            try:
                resp = await client.head(url)
                if resp.status_code == 200:
                    size_mb = int(resp.headers.get("content-length", 0)) / 1e6
                    return {"ok": True, "url": url, "size_mb": round(size_mb, 1)}
            except Exception:
                continue
    return {"ok": False, "tried_urls": urls}


# ─────────────────────────────────────────────────────────────────────────────
# CLI / 단독 실행
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 36.0
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else 129.3

    print(f"CCKP query: lat={lat}, lon={lon}")
    data = query_cckp_sync(lat, lon)
    print(json.dumps(data, indent=2, ensure_ascii=False))

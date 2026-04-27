"""
cckp_client.py — World Bank CCKP 0.25° 기후 데이터 클라이언트 (독립 모듈)

데이터 출처: AWS S3 공개 버킷 s3://wbg-cckp/data/cmip6-x0.25/ (무인증)
해상도: 0.25° × 0.25° 전구 격자, 앙상블 중앙값(median)

파일 구조 (실측):
  baseline: data/cmip6-x0.25/{var}/ensemble-all-historical/
              climatology-{var}-annual-mean_..._median_1995-2014.nc
  미래 SSP:  data/cmip6-x0.25/{var}/ensemble-all-{ssp}/
              anomaly-{var}-annual-mean_..._median_{period}.nc
  ※ 미래값 = baseline + anomaly

제공 변수 (기존 54-5개에 없는 신규 5개):
  cckp_hi35   — 열지수 초과일 (Heat Index >35°C)
  cckp_hd40   — 극한고온일 (Tmax >40°C)
  cckp_tr26   — 열대야 한국기준 (Tmin >26°C)
  cckp_cdd65  — 냉방도일 (CDD base 65°F ≈ 18.3°C)
  cckp_hdd65  — 난방도일 (HDD base 65°F ≈ 18.3°C)

독립 사용:
    python cckp_client.py 36.0095 129.3435
    from cckp_client import query_cckp_sync
    data = query_cckp_sync(36.0095, 129.3435)
"""
from __future__ import annotations

import asyncio
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
_DEFAULT_CACHE = Path(os.environ.get(
    "CCKP_CACHE_DIR",
    os.path.join(tempfile.gettempdir(), "cckp_cache"),
))

# ── S3 경로 (실측 확인) ────────────────────────────────────────────────────────
_S3_BASE  = "https://wbg-cckp.s3.us-west-2.amazonaws.com"
_S3_ROOT  = "data/cmip6-x0.25"
_MODEL    = "ensemble-all"
_STAT     = "median"  # p10 / median / p90

# ── 변수 정의 (CCKP 실제 변수명 기반) ─────────────────────────────────────────
CCKP_VARS: dict[str, dict] = {
    "cckp_hi35": {
        "cckp_name": "hi35",
        "label":     "열지수 초과일 (HI>35°C)",
        "unit":      "days/yr",
        "desc":      "체감온도(Heat Index) >35°C 일수 — 기온+습도 복합 열스트레스",
    },
    "cckp_hd40": {
        "cckp_name": "hd40",
        "label":     "극한고온일 (Tmax>40°C)",
        "unit":      "days/yr",
        "desc":      "최고기온 >40°C 일수 — 설비·소재 한계온도 기준",
    },
    "cckp_tr26": {
        "cckp_name": "tr26",
        "label":     "열대야 한국기준 (Tmin>26°C)",
        "unit":      "days/yr",
        "desc":      "최저기온 >26°C 열대야 — KMA 폭염특보 기준",
    },
    "cckp_cdd65": {
        "cckp_name": "cdd65",
        "label":     "냉방도일 (CDD base 65°F)",
        "unit":      "°F·day/yr",
        "desc":      "냉방에너지 수요 지표 — Σmax(T-65°F, 0), ASHRAE 기준",
    },
    "cckp_hdd65": {
        "cckp_name": "hdd65",
        "label":     "난방도일 (HDD base 65°F)",
        "unit":      "°F·day/yr",
        "desc":      "난방에너지 수요 지표 — Σmax(65°F-T, 0), ASHRAE 기준",
    },
    # ── ETCCDI 교차검증 변수 (온도 계열, CCKP CMIP6 0.25°) ─────────────────────
    "cckp_csdi": {
        "cckp_name": "csdi",
        "label":     "한파 지속기간 (CSDI)",
        "unit":      "days/yr",
        "min_val":   0,
        "desc":      "Cold Spell Duration Index — 연속 6일 이상 Tmin<p10 기간 합계",
    },
    "cckp_wsdi": {
        "cckp_name": "wsdi",
        "label":     "온난 지속기간 (WSDI-CP)",
        "unit":      "days/yr",
        "min_val":   0,
        "desc":      "Warm Spell Duration Index (CCKP) — 연속 6일 이상 Tmax>p90 기간",
    },
    "cckp_cdd_consec": {
        "cckp_name": "cdd",
        "label":     "연속건조일수 (CDD-CP)",
        "unit":      "days",
        "min_val":   0,
        "desc":      "Consecutive Dry Days (CCKP) — 최장 연속 강수<1mm 기간 (연간 최대)",
    },
    # ── 신규 확장 변수 (CCKP CMIP6 0.25°) ────────────────────────────────────
    "cckp_spei12": {
        "cckp_name": "spei12",
        "label":     "가뭄지수 (SPEI-12)",
        "unit":      "index",
        "desc":      "12개월 표준화강수증발산지수 — 음수일수록 가뭄, <-1.5 = 심각한 가뭄",
    },
    "cckp_gsl": {
        "cckp_name": "gsl",
        "label":     "생장기간 (GSL)",
        "unit":      "days/yr",
        "min_val":   0,
        "desc":      "Growing Season Length — 작물 재배 가능 기간, 기온 상승으로 증가",
    },
    "cckp_hurs": {
        "cckp_name": "hurs",
        "label":     "상대습도 (HURS)",
        "unit":      "%",
        "desc":      "Near-surface relative humidity — 열스트레스·부식·곰팡이 리스크 지표",
    },
    "cckp_id": {
        "cckp_name": "id",
        "label":     "결빙일 (ID, Tmax<0°C)",
        "unit":      "days/yr",
        "min_val":   0,
        "desc":      "Ice Days — 최고기온이 0°C 미만인 날, 동파·한랭 설비 손상 위험",
    },
    "cckp_rxmonth": {
        "cckp_name": "rxmonth",
        "label":     "월최대강수 (Rx-month)",
        "unit":      "mm/month",
        "min_val":   0,
        "desc":      "Monthly Maximum Precipitation — 연중 가장 강수가 많은 달의 총량",
    },
}

# ── 기간 매핑: 우리 period_key → CCKP 20년 기간 ────────────────────────────────
_PERIOD_MAP = {
    "baseline": "1995-2014",   # historical climatology
    "near":     "2020-2039",
    "mid":      "2040-2059",
    "far":      "2060-2079",
    "end":      "2080-2099",
}
_SSP_KEYS = ["ssp126", "ssp245", "ssp370", "ssp585"]

# ── 메모리 캐시 ────────────────────────────────────────────────────────────────
_POINT_CACHE: dict[str, Optional[float]] = {}


# ─────────────────────────────────────────────────────────────────────────────
# URL 빌더
# ─────────────────────────────────────────────────────────────────────────────

def _url_baseline(cckp_var: str) -> str:
    folder = f"{_MODEL}-historical"
    fname  = f"climatology-{cckp_var}-annual-mean_cmip6-x0.25_{_MODEL}-historical_climatology_{_STAT}_1995-2014.nc"
    return f"{_S3_BASE}/{_S3_ROOT}/{cckp_var}/{folder}/{fname}"


def _url_anomaly(cckp_var: str, ssp: str, period: str) -> str:
    cckp_period = _PERIOD_MAP[period]
    folder = f"{_MODEL}-{ssp}"
    fname  = f"anomaly-{cckp_var}-annual-mean_cmip6-x0.25_{_MODEL}-{ssp}_climatology_{_STAT}_{cckp_period}.nc"
    return f"{_S3_BASE}/{_S3_ROOT}/{cckp_var}/{folder}/{fname}"


# ─────────────────────────────────────────────────────────────────────────────
# 다운로드 & 포인트 추출
# ─────────────────────────────────────────────────────────────────────────────

async def _download(url: str, dest: Path, timeout: int = 15) -> bool:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            async with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    return False
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".tmp")
                with open(tmp, "wb") as f:
                    async for chunk in resp.aiter_bytes(65536):
                        f.write(chunk)
                shutil.move(str(tmp), str(dest))
                return True
    except Exception as exc:
        logger.debug("CCKP download failed %s: %s", url, exc)
        return False


def _cache_path(tag: str, cache_dir: Path) -> Path:
    return cache_dir / f"{tag}.nc"


def _extract_point(nc_path: Path, cckp_var: str, lat: float, lon: float) -> Optional[float]:
    try:
        import netCDF4 as nc  # noqa: PLC0415
        with nc.Dataset(nc_path) as ds:
            lat_k = next((k for k in ds.variables if k.lower() in ("lat", "latitude")), None)
            lon_k = next((k for k in ds.variables if k.lower() in ("lon", "longitude")), None)
            if not lat_k or not lon_k:
                return None

            lats = np.array(ds.variables[lat_k][:])
            lons = np.array(ds.variables[lon_k][:])
            lon_q = lon % 360 if lons.max() > 180 else lon

            li = int(np.argmin(np.abs(lats - lat)))
            loi = int(np.argmin(np.abs(lons - lon_q)))

            var_k = cckp_var if cckp_var in ds.variables else next(
                (k for k in ds.variables if cckp_var.lower() in k.lower()), None
            )
            if not var_k:
                return None

            d = ds.variables[var_k]
            val = float(d[0, li, loi] if d.ndim == 3 else d[li, loi])

            fill = getattr(d, "_FillValue", None) or getattr(d, "missing_value", None)
            if fill is not None and abs(val - float(fill)) < 1e3:
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

    미래값 = baseline + anomaly (CCKP 구조 반영).

    Returns:
        {
          "cckp_hi35": {
            "ssp245": {"baseline": 5.2, "near": 8.1, "mid": 14.3, ...},
            ...
          },
          ...
        }
    """
    variables = variables or list(CCKP_VARS.keys())
    ssps      = ssps      or _SSP_KEYS
    cache_dir = cache_dir or _DEFAULT_CACHE
    periods   = list(_PERIOD_MAP.keys())

    result: dict = {v: {ssp: {p: None for p in periods} for ssp in ssps} for v in variables}

    for var_key in variables:
        meta = CCKP_VARS.get(var_key)
        if not meta:
            continue
        cname = meta["cckp_name"]

        # 1) baseline NC 확보
        base_tag  = f"{cname}_historical_baseline"
        base_path = _cache_path(base_tag, cache_dir)
        if not (base_path.exists() and base_path.stat().st_size > 0):
            ok = await _download(_url_baseline(cname), base_path)
            if not ok:
                logger.warning("CCKP: baseline download failed for %s", cname)
                continue

        base_val = _extract_point(base_path, cname, lat, lon)
        if base_val is None:
            logger.warning("CCKP: baseline extract returned None for %s at (%.3f, %.3f)", cname, lat, lon)
            continue

        # 모든 SSP의 anomaly NC 병렬 다운로드
        anomaly_tasks: dict[str, asyncio.Task] = {}
        for ssp in ssps:
            for period in periods:
                if period == "baseline":
                    continue
                tag = f"{cname}_{ssp}_{period}"
                if tag not in anomaly_tasks:
                    path = _cache_path(tag, cache_dir)
                    if path.exists() and path.stat().st_size > 0:
                        anomaly_tasks[tag] = asyncio.create_task(asyncio.sleep(0))
                    else:
                        anomaly_tasks[tag] = asyncio.create_task(
                            _download(_url_anomaly(cname, ssp, period), path)
                        )

        await asyncio.gather(*anomaly_tasks.values(), return_exceptions=True)

        # 2) 포인트 추출 + baseline + anomaly = 절댓값
        for ssp in ssps:
            # baseline은 SSP 무관
            for p_key in periods:
                result[var_key][ssp][p_key] = base_val  # 초기값

            for period in periods:
                if period == "baseline":
                    result[var_key][ssp]["baseline"] = base_val
                    continue

                tag   = f"{cname}_{ssp}_{period}"
                path  = _cache_path(tag, cache_dir)
                pt_key = f"{tag}_{lat:.3f}_{lon:.3f}"

                if pt_key in _POINT_CACHE:
                    anomaly = _POINT_CACHE[pt_key]
                else:
                    anomaly = _extract_point(path, cname, lat, lon) if path.exists() else None
                    _POINT_CACHE[pt_key] = anomaly

                if anomaly is not None:
                    raw = base_val + anomaly
                    # 일수 계열 변수는 음수 불가 (온난화로 csdi 등이 0에 수렴)
                    min_val = meta.get("min_val", None)
                    if min_val is not None:
                        raw = max(min_val, raw)
                    result[var_key][ssp][period] = round(raw, 3)
                else:
                    result[var_key][ssp][period] = base_val

    return result


def query_cckp_sync(
    lat: float,
    lon: float,
    variables: Optional[list[str]] = None,
    ssps: Optional[list[str]] = None,
) -> dict[str, dict]:
    """동기 래퍼 — 스크립트/REPL에서 직접 사용 가능."""
    return asyncio.run(query_cckp(lat, lon, variables=variables, ssps=ssps))


def list_cckp_vars() -> dict[str, dict]:
    return {k: {f: v[f] for f in ("label", "unit", "desc")} for k, v in CCKP_VARS.items()}


async def verify_cckp_access(var_key: str = "cckp_hi35") -> dict:
    meta = CCKP_VARS.get(var_key)
    if not meta:
        return {"ok": False, "error": f"Unknown variable: {var_key}"}
    url = _url_baseline(meta["cckp_name"])
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.head(url)
            if resp.status_code == 200:
                size_mb = int(resp.headers.get("content-length", 0)) / 1e6
                return {"ok": True, "url": url, "size_mb": round(size_mb, 1)}
        except Exception as e:
            return {"ok": False, "error": str(e), "url": url}
    return {"ok": False, "url": url}


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, sys, logging as _log
    _log.basicConfig(level=_log.INFO, format="%(levelname)s %(message)s")

    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 36.0095
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else 129.3435
    ssps = sys.argv[3].split(",") if len(sys.argv) > 3 else ["ssp245", "ssp585"]

    print(f"\n=== CCKP Pilot - OCI Pohang ({lat}N, {lon}E) ===\n")
    data = query_cckp_sync(lat, lon, ssps=ssps)

    for var_key, ssp_dict in data.items():
        meta = CCKP_VARS[var_key]
        print(f"[{meta['label']}] ({meta['unit']})")
        for ssp in ssps:
            vals = ssp_dict[ssp]
            row = "  {:<8}".format(ssp)
            for p in ["baseline","near","mid","far","end"]:
                v = vals.get(p)
                row += f"  {v:>8.1f}" if v is not None else "       N/A"
            print(row)
        print()

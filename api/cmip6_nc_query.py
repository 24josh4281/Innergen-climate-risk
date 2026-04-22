"""
cmip6_nc_query.py — NC 파일 직접 읽기로 모델별 T2/T3 기간 평균 조회

구조: {CMIP6_ROOT}/{region}/{ssp}/{model}/{var}_{model}_{ssp}_{region}_2015_2100.nc

지원 지역 (11개):
  africa, central_asia, east_asia, europe, middle_east,
  north_america, oceania, russia_siberia, se_asia, south_america, south_asia

사용법:
  result = query_model_nc(lat, lon, model="miroc6", ssps=["ssp585"])
  # → {ssp: {period: {var: value}}}
"""
from __future__ import annotations

import math
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import xarray as xr

warnings.filterwarnings("ignore")

CMIP6_ROOT = Path("c:/Users/24jos/climada/data/scenarios/cmip6_v2")

PERIODS = {
    "baseline": (2015, 2024),
    "near":     (2025, 2034),
    "mid":      (2045, 2054),
    "far":      (2075, 2084),
    "end":      (2090, 2099),
}

SSP_KEYS = ["ssp126", "ssp245", "ssp370", "ssp585"]
SSP_DIR  = {"ssp126": "ssp1_2_6", "ssp245": "ssp2_4_5",
            "ssp370": "ssp3_7_0", "ssp585": "ssp5_8_5"}

def _k2c(v):
    """Kelvin → Celsius (numpy 배열 호환)."""
    import numpy as np
    arr = np.asarray(v, dtype=float)
    return np.where(arr > 100, arr - 273.15, arr)

UNIT_CONV = {
    "tasmax":  _k2c,
    "tasmin":  _k2c,
    "tas":     _k2c,
    "pr":      lambda v: v * 86400,      # kg/m²/s → mm/day
    "sfcWind": lambda v: v,
    "evspsbl": lambda v: v * 86400,
    "prsn":    lambda v: v * 86400,
}

# 모든 변수: .mean() 집계 (월평균 → 기간평균)
# tasmax도 연간 평균으로 집계해야 ETCCDI 추정기(SU/WSDI)와 일치
AGG_MAX_VARS: set[str] = set()

# ── 지역 매핑 (lat/lon 박스 기반) ──────────────────────────────────────────────

# (region, lat_min, lat_max, lon_min, lon_max, lon_360)
# lon_360=True: 해당 NC 파일이 0-360 경도 사용
_REGION_BOXES = [
    ("east_asia",      25.0, 45.0,  100.0,  145.0, False),
    ("se_asia",        10.0, 22.0,  117.0,  127.0, False),
    ("south_asia",      5.0, 35.0,   60.0,   99.0, False),
    ("central_asia",   35.0, 55.0,   47.0,   88.0, False),
    ("russia_siberia", 50.0, 82.0,   30.0,  180.0, False),
    ("middle_east",    15.0, 45.0,   25.0,   65.0, False),
    ("africa",        -35.0, 37.0,  -18.0,   52.0, False),
    ("europe",         30.0, 72.0,  -15.0,   45.0, False),
    ("north_america",  15.0, 75.0, -136.0,  -54.0, True),   # 0-360: 225-305
    ("south_america", -56.0, 15.0,  -83.0,  -34.0, True),   # 0-360: 278-325
    ("oceania",       -47.0,  0.0,  111.0,  180.0, False),
]


def find_regions(lat: float, lon: float) -> list[str]:
    """
    좌표에 해당하는 CMIP6 지역 목록 반환 (복수 가능, 세밀한 지역 우선).
    """
    matches = []
    for region, lat_min, lat_max, lon_min, lon_max, lon_360 in _REGION_BOXES:
        check_lon = lon % 360 if lon_360 else lon
        lon_min_c = lon_min % 360 if lon_360 else lon_min
        lon_max_c = lon_max % 360 if lon_360 else lon_max
        if lat_min <= lat <= lat_max and lon_min_c <= check_lon <= lon_max_c:
            matches.append(region)
    # 면적이 작은 지역(세밀) 우선 정렬 (se_asia, south_asia 등)
    area = {r: (b[2] - b[1]) * (b[4] - b[3]) for r, *b in _REGION_BOXES}
    matches.sort(key=lambda r: area.get(r, 1e9))
    return matches


def _find_nc_file(region: str, ssp: str, model: str, var: str) -> Optional[Path]:
    """NC 파일 경로 탐색 (서브디렉토리 우선, 없으면 평탄 경로)."""
    ssp_dir = SSP_DIR.get(ssp, ssp)
    base = CMIP6_ROOT / region / ssp_dir

    # 서브디렉토리 형식: {base}/{model}/{var}_{model}_{ssp_dir}_{region}_2015_2100.nc
    subdir = base / model / f"{var}_{model}_{ssp_dir}_{region}_2015_2100.nc"
    if subdir.exists():
        return subdir

    # 평탄 형식: {base}/{var}_{model}_{ssp_dir}_{region}_2015_2100.nc
    flat = base / f"{var}_{model}_{ssp_dir}_{region}_2015_2100.nc"
    if flat.exists():
        return flat

    return None


def _extract_period_means(
    nc_path: Path,
    var: str,
    lat: float,
    lon: float,
    lon_360: bool = False,
) -> dict[str, Optional[float]]:
    """
    NC 파일에서 (lat, lon) 좌표 추출 → 기간별 평균 반환.
    Returns {period_key: value | None}
    """
    ds = xr.open_dataset(nc_path)
    try:
        data_var = var if var in ds else next(
            (v for v in ds.data_vars if var.lower() in v.lower()), None
        )
        if data_var is None:
            return {p: None for p in PERIODS}

        da = ds[data_var]
        lat_name = next((c for c in da.dims if "lat" in c.lower()), None)
        lon_name = next((c for c in da.dims if "lon" in c.lower()), None)
        if not lat_name or not lon_name:
            return {p: None for p in PERIODS}

        nc_lons = da.coords[lon_name].values
        sel_lon = lon % 360 if (nc_lons.max() > 180 or lon_360) else lon

        site_da = da.sel({lat_name: lat, lon_name: sel_lon}, method="nearest")

        time_dim = next((d for d in site_da.dims if "time" in d.lower()), None)
        if not time_dim:
            return {p: None for p in PERIODS}

        # 연간 집계
        if var in AGG_MAX_VARS:
            annual = site_da.groupby(f"{time_dim}.year").max()
        else:
            annual = site_da.groupby(f"{time_dim}.year").mean()

        conv = UNIT_CONV.get(var, lambda v: v)
        years = annual.coords["year"].values.astype(int)
        vals  = conv(annual.values)

        result: dict[str, Optional[float]] = {}
        for period_key, (sy, ey) in PERIODS.items():
            mask = (years >= sy) & (years <= ey)
            if mask.sum() == 0:
                result[period_key] = None
            else:
                result[period_key] = round(float(np.nanmean(vals[mask])), 4)

        return result
    finally:
        ds.close()


def query_model_nc(
    lat: float,
    lon: float,
    model: str,
    ssps: Optional[list[str]] = None,
    variables: Optional[list[str]] = None,
) -> dict:
    """
    임의 좌표 × 특정 모델의 CMIP6 기간별 값 조회 (NC 파일 직접 읽기).

    Args:
        lat:       위도
        lon:       경도
        model:     모델 ID (예: "miroc6", "mpi_esm1_2_lr")
        ssps:      조회할 SSP 목록 (None → 전체 4개)
        variables: 조회할 변수 목록 (None → tasmax/tasmin/tas/pr)

    Returns:
        {
          "region": str,              # 매칭된 CMIP6 지역
          "ssp126": {                 # SSP별
            "baseline": {             # 기간별
              "tasmax": value,        # 변수별 값 (°C, mm/day)
              ...
            }
          },
          ...
        }
        None if no coverage.
    """
    ssps      = ssps or SSP_KEYS
    variables = variables or ["tasmax", "tasmin", "tas", "pr"]

    regions = find_regions(lat, lon)
    if not regions:
        return {}

    # 가장 세밀한 지역 우선, 데이터 없으면 다음 지역 시도
    chosen_region: Optional[str] = None
    for region in regions:
        # 하나라도 파일 있으면 선택
        test_ssp = ssps[0] if ssps else "ssp585"
        test_var = variables[0] if variables else "tas"
        if _find_nc_file(region, test_ssp, model, test_var) is not None:
            chosen_region = region
            break

    if chosen_region is None:
        return {}

    lon_360 = next(
        (b[5] for b in _REGION_BOXES if b[0] == chosen_region), False
    )

    result: dict = {"region": chosen_region}

    for ssp in ssps:
        result[ssp] = {p: {} for p in PERIODS}
        for var in variables:
            nc_path = _find_nc_file(chosen_region, ssp, model, var)
            if nc_path is None:
                for p in PERIODS:
                    result[ssp][p][var] = None
                continue
            try:
                period_vals = _extract_period_means(nc_path, var, lat, lon, lon_360)
                for p, v in period_vals.items():
                    result[ssp][p][var] = v
            except Exception:
                for p in PERIODS:
                    result[ssp][p][var] = None

    return result


def list_models_for_coord(lat: float, lon: float, ssp: str = "ssp585") -> list[str]:
    """특정 좌표에서 조회 가능한 모델 목록."""
    regions = find_regions(lat, lon)
    available = []
    for region in regions:
        ssp_dir_path = CMIP6_ROOT / region / SSP_DIR.get(ssp, ssp)
        if not ssp_dir_path.exists():
            continue
        for entry in sorted(ssp_dir_path.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                model = entry.name
                if model not in available:
                    available.append(model)
        # 평탄 파일에서도 추출
        for f in ssp_dir_path.glob("tas_*.nc"):
            parts = f.stem.split("_")
            try:
                si = next(i for i, p in enumerate(parts) if p == "ssp")
                model = "_".join(parts[1:si])
                if model and model not in available:
                    available.append(model)
            except StopIteration:
                pass
    return sorted(set(available))

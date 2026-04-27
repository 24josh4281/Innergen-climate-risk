"""
kma_client.py — 기상청 1km 기후변화 시나리오 클라이언트 (167개 행정구역)

데이터: 농촌진흥청 weather.rda.go.kr → ENS 앙상블 → 20년 평균 CSV
커버리지: 한반도 (33°~39.5°N, 124°~132.5°E)

변수 (CMIP6 표준명):
    tasmax  — 최고기온 (°C)
    tasmin  — 최저기온 (°C)
    pr      — 강수량 (mm/day)
    sfcWind — 풍속 (m/s)
    hurs    — 상대습도 (%)
    rsds    — 일사량 (W/m² or MJ/m²/day)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_KMA_DATA_PATH = Path(os.environ.get(
    "KMA_DATA_DIR",
    "B:/climada/data/kma/processed",
)) / "kma_periods.csv"

KOR_LAT_RANGE = (33.0, 39.5)
KOR_LON_RANGE = (124.0, 132.5)

KMA_VARS = {
    "tasmax":  {"label": "최고기온",   "unit": "°C"},
    "tasmin":  {"label": "최저기온",   "unit": "°C"},
    "pr":      {"label": "강수량",     "unit": "mm/day"},
    "sfcWind": {"label": "풍속",       "unit": "m/s"},
    "hurs":    {"label": "상대습도",   "unit": "%"},
    "rsds":    {"label": "일사량",     "unit": "MJ/m²/day"},
}

KMA_PERIODS  = ["baseline", "near", "mid", "far", "end"]
KMA_SSP_KEYS = ["ssp126", "ssp245", "ssp370", "ssp585"]

_DF_CACHE = None


def is_korean_coord(lat: float, lon: float) -> bool:
    return (KOR_LAT_RANGE[0] <= lat <= KOR_LAT_RANGE[1] and
            KOR_LON_RANGE[0] <= lon <= KOR_LON_RANGE[1])


def is_available() -> bool:
    return _KMA_DATA_PATH.exists()


def _load_df():
    global _DF_CACHE
    if _DF_CACHE is None:
        if not _KMA_DATA_PATH.exists():
            return None
        try:
            import pandas as pd
            _DF_CACHE = pd.read_csv(_KMA_DATA_PATH, encoding="utf-8-sig")
        except Exception as e:
            logger.warning("KMA CSV 로드 실패: %s", e)
            return None
    return _DF_CACHE


def _nearest_region(lat: float, lon: float, df) -> tuple[int, str, float]:
    """DataFrame에서 가장 가까운 행정구역 반환 (region_id, name, dist_km)."""
    unique_regions = df[['region_id', 'region_name', 'lat', 'lon']].drop_duplicates('region_id')
    dists = np.sqrt((unique_regions['lat'].values - lat)**2 +
                    (unique_regions['lon'].values - lon)**2) * 111.0
    idx = int(np.argmin(dists))
    row = unique_regions.iloc[idx]
    return int(row['region_id']), str(row['region_name']), round(float(dists[idx]), 1)


def query_kma(lat: float, lon: float) -> dict[str, dict]:
    """
    KMA 행정구역 데이터에서 좌표 기준 가장 가까운 지역 값 반환.

    Returns:
        {
          "kma_tasmax": {"ssp126": {"baseline": 17.3, "near": 18.1, ...}, ...},
          "kma_pr":     {...},
          ...
        }
        데이터 없으면 빈 dict.
    """
    if not is_available() or not is_korean_coord(lat, lon):
        return {}

    df = _load_df()
    if df is None:
        return {}

    region_id, region_name, dist_km = _nearest_region(lat, lon, df)

    if dist_km > 50:
        logger.warning("KMA: 가장 가까운 행정구역이 %.1fkm 이상 — %s", dist_km, region_name)

    logger.debug("KMA: (%.3f,%.3f) → %s (ID %d, %.1fkm)", lat, lon, region_name, region_id, dist_km)

    sub = df[df['region_id'] == region_id]
    if sub.empty:
        return {}

    result: dict = {}

    for var in KMA_VARS:
        out_key = f"kma_{var}"
        result[out_key] = {ssp: {p: None for p in KMA_PERIODS} for ssp in KMA_SSP_KEYS}

        var_sub = sub[sub['var'] == var]
        for _, row in var_sub.iterrows():
            ssp    = str(row['ssp'])
            period = str(row['period'])
            val    = float(row['value'])

            if ssp == 'baseline' and period == 'baseline':
                # baseline은 SSP 무관 — 모든 SSP에 동일 적용
                for s in KMA_SSP_KEYS:
                    result[out_key][s]['baseline'] = val
            elif ssp in KMA_SSP_KEYS and period in KMA_PERIODS:
                result[out_key][ssp][period] = val

    # 값이 하나도 없는 변수 제거
    result = {k: v for k, v in result.items()
              if any(pv is not None
                     for sv in v.values()
                     for pv in sv.values())}

    if result:
        result['_kma_meta'] = {
            'region_id':   region_id,
            'region_name': region_name,
            'dist_km':     dist_km,
        }

    return result


def get_kma_coverage() -> dict:
    if not is_available():
        return {"available": False, "message": "데이터 없음 — download_kma_scenario.py 실행 필요"}
    df = _load_df()
    if df is None:
        return {"available": False, "message": "CSV 로드 실패"}
    return {
        "available":  True,
        "ssps":       sorted(df['ssp'].unique().tolist()),
        "vars":       sorted(df['var'].unique().tolist()),
        "periods":    sorted(df['period'].unique().tolist()),
        "n_regions":  int(df['region_id'].nunique()),
        "resolution": "행정구역별 (167개 시/군/구)",
        "coverage":   f"{KOR_LAT_RANGE[0]}°~{KOR_LAT_RANGE[1]}°N, {KOR_LON_RANGE[0]}°~{KOR_LON_RANGE[1]}°E",
        "source":     "농촌진흥청 ENS 앙상블",
    }


if __name__ == "__main__":
    import sys
    import logging as _log
    _log.basicConfig(level=_log.INFO, format="%(levelname)s %(message)s")

    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 36.0095
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else 129.3435

    cov = get_kma_coverage()
    if not cov["available"]:
        print(f"데이터 없음: {cov['message']}")
        sys.exit(0)

    data = query_kma(lat, lon)
    meta = data.pop('_kma_meta', {})
    print(f"\n=== KMA ({lat}°N, {lon}°E) → {meta.get('region_name')} (거리 {meta.get('dist_km')}km) ===\n")

    for var_key in sorted(data):
        label = KMA_VARS.get(var_key.replace("kma_", ""), {}).get("label", var_key)
        unit  = KMA_VARS.get(var_key.replace("kma_", ""), {}).get("unit", "")
        print(f"[{label}] ({unit})")
        for ssp in ["ssp126", "ssp585"]:
            vals = data[var_key].get(ssp, {})
            row = f"  {ssp:<8}"
            for p in KMA_PERIODS:
                v = vals.get(p)
                row += f"  {v:>7.2f}" if v is not None else "      N/A"
            print(row)
        print()

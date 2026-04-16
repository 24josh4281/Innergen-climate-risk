"""
cmip6_grid.py — CMIP6 그리드 데이터 조회 모듈

api/data/cmip6_grid_east_asia.json 및 cmip6_grid_global.json을
메모리에 로드하고, 주어진 위도/경도에 가장 가까운 그리드 포인트 값을 반환.
"""

import json
import math
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

# 그리드 커버리지 정의 (east_asia: 동아시아+동남아)
EA_LAT_MIN, EA_LAT_MAX = 5.0, 55.0
EA_LON_MIN, EA_LON_MAX = 95.0, 150.0

# Period key 매핑 (plan 기준)
PERIOD_KEYS = ["baseline", "near", "mid", "far", "end"]
PERIOD_LABELS = {
    "baseline": "2015-2024",
    "near":     "2025-2034",
    "mid":      "2045-2054",
    "far":      "2075-2084",
    "end":      "2090-2099",
}

SSP_KEYS = ["ssp126", "ssp245", "ssp370", "ssp585"]

# CMIP6 변수 단위 변환
def convert_value(var: str, raw: float) -> Optional[float]:
    if raw is None or math.isnan(raw):
        return None
    if var in ("tasmax", "tasmin", "tas"):
        return round(raw - 273.15 if raw > 200 else raw, 2)
    elif var in ("pr", "prsn", "evspsbl"):
        return round(raw * 86400, 3)
    return round(raw, 4)


class Cmip6Grid:
    """CMIP6 그리드 메모리 캐시 및 조회 클래스."""

    def __init__(self):
        self._east_asia: dict = {}
        self._global: dict = {}
        self._loaded = False

    def load(self):
        """JSON 파일 로드 (앱 시작시 1회)."""
        ea_path = DATA_DIR / "cmip6_grid_east_asia.json"
        gl_path = DATA_DIR / "cmip6_grid_global.json"

        if ea_path.exists():
            logger.info(f"Loading east_asia grid ({ea_path.stat().st_size // 1024} KB)...")
            with open(ea_path, encoding="utf-8") as f:
                self._east_asia = json.load(f)
            logger.info("East Asia grid loaded.")
        else:
            logger.warning(f"East Asia grid not found: {ea_path}")

        if gl_path.exists():
            logger.info(f"Loading global grid ({gl_path.stat().st_size // 1024} KB)...")
            with open(gl_path, encoding="utf-8") as f:
                self._global = json.load(f)
            logger.info("Global grid loaded.")
        else:
            logger.warning(f"Global grid not found: {gl_path}")

        self._loaded = True

    def _find_nearest(self, grid_pts: list, lat: float, lon: float) -> Optional[float]:
        """그리드 포인트 리스트에서 최근접 값 반환. [[lat, lon, val], ...]"""
        if not grid_pts:
            return None
        best_val = None
        best_dist = float("inf")
        for pt in grid_pts:
            dlat = pt[0] - lat
            dlon = pt[1] - lon
            dist = dlat * dlat + dlon * dlon
            if dist < best_dist:
                best_dist = dist
                best_val = pt[2]
        return best_val

    def _is_east_asia(self, lat: float, lon: float) -> bool:
        return (EA_LAT_MIN <= lat <= EA_LAT_MAX) and (EA_LON_MIN <= lon <= EA_LON_MAX)

    def query(self, lat: float, lon: float) -> dict:
        """
        주어진 위도/경도의 CMIP6 기후값 반환.

        Returns:
            {
              "ssp126": {
                "baseline": {"tasmax": 32.1, "pr": 4.2, ...},
                "near": {...},
                ...
              },
              ...
            }
        """
        use_ea = self._is_east_asia(lat, lon)
        source_grid = self._east_asia if use_ea and self._east_asia else self._global

        if not source_grid:
            return {}

        result = {}
        for ssp in SSP_KEYS:
            if ssp not in source_grid:
                continue
            result[ssp] = {}
            for period in PERIOD_KEYS:
                result[ssp][period] = {}
                for var, var_data in source_grid[ssp].items():
                    if period not in var_data:
                        continue
                    raw = self._find_nearest(var_data[period], lat, lon)
                    result[ssp][period][var] = convert_value(var, raw)

        return result

    def is_covered(self, lat: float, lon: float) -> bool:
        """좌표가 east_asia 그리드 커버리지 내인지 확인."""
        return self._is_east_asia(lat, lon)

    @property
    def loaded(self):
        return self._loaded


# 싱글턴
cmip6_grid = Cmip6Grid()

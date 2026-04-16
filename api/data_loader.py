"""
data_loader.py — 14개 OCI 사업장 사전계산 데이터 로더 (메모리 캐시)
"""

import logging
import math
from pathlib import Path
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

SSP_NORM = {
    "ssp1_2_6": "ssp126", "ssp2_4_5": "ssp245",
    "ssp3_7_0": "ssp370", "ssp5_8_5": "ssp585",
    "ssp126": "ssp126",   "ssp245": "ssp245",
    "ssp370": "ssp370",   "ssp585": "ssp585",
}
PERIOD_NORM = {
    "baseline_2015_2024": "baseline",
    "near_2025_2034": "near",
    "mid_2045_2054": "mid",
    "far_2075_2084": "far",
    "end_2090_2099": "end",
    "baseline": "baseline", "near": "near",
    "mid": "mid", "far": "far", "end": "end",
}


class SiteDataLoader:
    """14개 OCI 사업장 사전계산 CSV를 메모리에 캐시."""

    def __init__(self):
        self._cmip6: Optional[pd.DataFrame] = None
        self._physrisk: Optional[pd.DataFrame] = None
        self._loaded = False

    def load(self):
        cmip6_path = DATA_DIR / "cmip6_sites.csv"
        physrisk_path = DATA_DIR / "physrisk_sites.csv"

        if cmip6_path.exists():
            df = pd.read_csv(cmip6_path)
            # 정규화
            if "ssp" in df.columns:
                df["ssp"] = df["ssp"].map(SSP_NORM).fillna(df["ssp"])
            if "period" in df.columns:
                df["period"] = df["period"].map(PERIOD_NORM).fillna(df["period"])
            self._cmip6 = df
            logger.info(f"cmip6_sites.csv loaded: {len(df)} rows")
        else:
            logger.warning(f"cmip6_sites.csv not found at {cmip6_path}")

        if physrisk_path.exists():
            self._physrisk = pd.read_csv(physrisk_path)
            logger.info(f"physrisk_sites.csv loaded: {len(self._physrisk)} rows")
        else:
            logger.warning(f"physrisk_sites.csv not found at {physrisk_path}")

        self._loaded = True

    def get_site_cmip6(self, site_name: str) -> dict:
        """사이트 이름으로 CMIP6 데이터 조회."""
        if self._cmip6 is None:
            return {}
        df = self._cmip6[self._cmip6["site"] == site_name]
        if df.empty:
            return {}

        result = {}
        for _, row in df.iterrows():
            ssp = row.get("ssp", "")
            period = row.get("period", "")
            var = row.get("variable", "")
            val = row.get("ens_mean", None)
            if ssp and period and var:
                if ssp not in result:
                    result[ssp] = {}
                if period not in result[ssp]:
                    result[ssp][period] = {}
                result[ssp][period][var] = float(val) if val is not None and not math.isnan(float(val)) else None

        return result

    # physrisk hazard 이름 → 웹 driver 키 매핑
    HAZARD_MAP = {
        "ChronicHeat":       "heat_stress",
        "Drought":           "drought_risk",
        "WaterRisk":         "water_stress",
        "RiverineInundation":"river_flood",
        "CoastalInundation": "coastal_flood",
        "Wind":              "cyclone_risk",
        "Fire":              "wildfire_risk",
        "Precipitation":     "pluvial_flood",
    }

    # year → period 매핑 (physrisk CSV는 연도 기준)
    YEAR_TO_PERIOD = {
        2030: "near",
        2050: "mid",
        2080: "far",
        2090: "end",
    }

    def get_site_physrisk(self, site_name: str) -> dict:
        """사이트 이름으로 physrisk 데이터 조회 (flat hazard dict 반환)."""
        if self._physrisk is None:
            return {}

        df = self._physrisk[self._physrisk["site"] == site_name]
        if df.empty:
            return {}

        # 각 hazard의 대표값 (ssp585, year=2050 기준)
        result = {}
        for _, row in df.iterrows():
            hazard_raw = str(row.get("hazard", ""))
            driver_key = self.HAZARD_MAP.get(hazard_raw)
            if not driver_key:
                continue
            scenario = str(row.get("scenario", "ssp585"))
            year = int(row.get("year", 2050))
            val = row.get("value")

            # ssp585, year=2050 우선
            if scenario == "ssp585" and year == 2050:
                if val is not None and not math.isnan(float(val)):
                    # 0-100 정규화 (physrisk 값은 일수, 월 등 다양 → 비율로 변환)
                    raw = float(val)
                    # 대부분 0~365 범위 → 100점 기준으로 정규화
                    normalized = min(100.0, round(raw / 3.65, 1))
                    result[driver_key] = normalized

        return result

    @property
    def loaded(self):
        return self._loaded


site_data = SiteDataLoader()

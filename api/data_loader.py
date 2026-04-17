"""
data_loader.py — 사업장 사전계산 데이터 로더 (메모리 캐시)

PhyRisk 반환 구조: {driver_key: {ssp: {period: score}}}
  - 위험유형별 primary indicator 선택
  - 위험유형별 정규화 함수 적용
  - SSP3-7.0: SSP2-4.5 + SSP5-8.5 평균으로 보간
  - 연도→기간 매핑: 2030→baseline·near, 2050→mid, 2090→far·end
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

# physrisk 연도 → CMIP6 기간 매핑 (physrisk: 2030/2050/2090만 있음)
YEAR_TO_PERIODS = {
    2030: ["baseline", "near"],   # 2030 → 현재·근미래 프록시
    2050: ["mid"],
    2090: ["far", "end"],          # 2090 → 장기·말기 프록시
}


class SiteDataLoader:
    """사업장 사전계산 CSV를 메모리에 캐시."""

    def __init__(self):
        self._cmip6: Optional[pd.DataFrame] = None
        self._physrisk: Optional[pd.DataFrame] = None
        self._loaded = False

    def load(self):
        cmip6_path = DATA_DIR / "cmip6_sites.csv"
        physrisk_path = DATA_DIR / "physrisk_sites.csv"

        if cmip6_path.exists():
            df = pd.read_csv(cmip6_path)
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

    # ── CMIP6 데이터 조회 ──────────────────────────────────────────────────

    def get_site_cmip6(self, site_name: str) -> dict:
        """Returns {ssp: {period: {var: value}}}"""
        if self._cmip6 is None:
            return {}
        df = self._cmip6[self._cmip6["site"] == site_name]
        if df.empty:
            return {}

        result = {}
        for _, row in df.iterrows():
            ssp    = row.get("ssp", "")
            period = row.get("period", "")
            var    = row.get("variable", "")
            val    = row.get("ens_mean", None)
            if ssp and period and var:
                result.setdefault(ssp, {}).setdefault(period, {})
                try:
                    result[ssp][period][var] = float(val) if val is not None and not math.isnan(float(val)) else None
                except (TypeError, ValueError):
                    result[ssp][period][var] = None
        return result

    # ── PhyRisk 위험유형 → driver 키 매핑 ────────────────────────────────

    HAZARD_MAP = {
        "ChronicHeat":        "heat_stress",
        "Drought":            "drought_risk",
        "WaterRisk":          "water_stress",
        "RiverineInundation": "river_flood",
        "CoastalInundation":  "coastal_flood",
        "Wind":               "cyclone_risk",
        "Fire":               "wildfire_risk",
        "Precipitation":      "pluvial_flood",
    }

    # 위험유형별 사용할 primary indicator (physrisk_sites.csv의 indicator 컬럼)
    INDICATOR_MAP = {
        "ChronicHeat":        "days_wbgt_above",                # WBGT 초과일수 (일/년)
        "Drought":            "months/spei12m/below/threshold", # 12개월 SPI 가뭄월수 (월/년)
        "WaterRisk":          "water_stress",                   # 수자원 스트레스 지수 (0~1)
        "RiverineInundation": "flood_depth",                    # 홍수 침수깊이 (m)
        "CoastalInundation":  "flood_depth",                    # 해안 침수깊이 (m)
        "Wind":               "max_speed",                      # 최대 풍속 (m/s)
        "Fire":               "fire_probability",               # 화재 발생확률 (0~1)
        "Precipitation":      "max/daily/water_equivalent",     # 일최대강수량 Rx1day (mm)
    }

    @staticmethod
    def _normalize(hazard: str, raw: float) -> float:
        """
        원시 physrisk 값 → 0~100 위험도 점수 변환.
        각 위험유형의 물리적 단위에 맞게 개별 정규화.
        """
        if raw is None or math.isnan(raw):
            return None
        fns = {
            "ChronicHeat":        lambda v: v / 3.65,    # 일/년 ÷ 3.65  (365일=100점)
            "Drought":            lambda v: v / 0.12,    # 월/년 ÷ 0.12  (12개월=100점)
            "WaterRisk":          lambda v: v * 100,     # 0~1 비율 → 0~100점
            "RiverineInundation": lambda v: v * 20,      # m × 20        (5m=100점)
            "CoastalInundation":  lambda v: v * 20,      # m × 20
            "Wind":               lambda v: v / 0.7,     # m/s ÷ 0.7    (70m/s=100점)
            "Fire":               lambda v: v * 100,     # 0~1 확률 → 0~100점
            "Precipitation":      lambda v: v / 5.0,     # mm ÷ 5        (500mm=100점)
        }
        fn = fns.get(hazard, lambda v: v / 3.65)
        return min(100.0, max(0.0, round(fn(raw), 1)))

    def get_site_physrisk(self, site_name: str) -> dict:
        """
        사이트 physrisk 데이터 조회.

        Returns:
            {driver_key: {ssp: {period: score}}}
            - ssp: ssp126 / ssp245 / ssp370(보간) / ssp585
            - period: baseline / near / mid / far / end
            - score: 0~100 정규화 위험도 점수
        """
        if self._physrisk is None:
            return {}

        df = self._physrisk[self._physrisk["site"] == site_name]
        if df.empty:
            return {}

        result = {}

        for hazard_raw, driver_key in self.HAZARD_MAP.items():
            indicator = self.INDICATOR_MAP.get(hazard_raw)

            # 해당 위험유형 + primary indicator 필터
            hdf = df[df["hazard"] == hazard_raw]
            if indicator:
                ind_df = hdf[hdf["indicator"] == indicator]
                if ind_df.empty:
                    ind_df = hdf  # fallback: indicator 없으면 전체 사용
                hdf = ind_df

            if hdf.empty:
                continue

            hazard_ssp = {}

            # SSP126 / SSP245 / SSP585 각각 추출
            for ssp_raw in ["ssp126", "ssp245", "ssp585"]:
                sdf = hdf[hdf["scenario"] == ssp_raw]
                periods = {}
                for _, row in sdf.iterrows():
                    try:
                        year = int(row["year"])
                        raw  = float(row["value"])
                    except (TypeError, ValueError):
                        continue
                    score = self._normalize(hazard_raw, raw)
                    if score is None:
                        continue
                    # 연도 → 기간 매핑 (복수 기간 프록시)
                    for period in YEAR_TO_PERIODS.get(year, []):
                        periods[period] = score
                hazard_ssp[ssp_raw] = periods

            # SSP370: SSP245 + SSP585 평균 보간
            p245 = hazard_ssp.get("ssp245", {})
            p585 = hazard_ssp.get("ssp585", {})
            all_periods = set(p245) | set(p585)
            hazard_ssp["ssp370"] = {}
            for p in all_periods:
                v245 = p245.get(p)
                v585 = p585.get(p)
                if v245 is not None and v585 is not None:
                    hazard_ssp["ssp370"][p] = round((v245 + v585) / 2, 1)
                else:
                    hazard_ssp["ssp370"][p] = v585 if v585 is not None else v245

            result[driver_key] = hazard_ssp

        return result

    @property
    def loaded(self):
        return self._loaded


site_data = SiteDataLoader()

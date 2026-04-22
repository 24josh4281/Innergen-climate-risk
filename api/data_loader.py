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


ENSEMBLE_RAW_DIR = Path("c:/Users/24jos/climada/data/ensemble")

class SiteDataLoader:
    """사업장 사전계산 CSV를 메모리에 캐시."""

    def __init__(self):
        self._cmip6: Optional[pd.DataFrame] = None
        self._cmip6_ens: Optional[pd.DataFrame] = None   # 앙상블 전체 통계 (std/n_models 포함)
        self._physrisk: Optional[pd.DataFrame] = None
        self._etccdi: Optional[pd.DataFrame] = None
        self._static: Optional[pd.DataFrame] = None
        self._cmip6_model: Optional[pd.DataFrame] = None  # 모델별 기간 요약
        self._loaded = False

    def load(self):
        cmip6_path    = DATA_DIR / "cmip6_sites.csv"
        physrisk_path = DATA_DIR / "physrisk_sites.csv"
        etccdi_path   = DATA_DIR / "etccdi_sites.csv"

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

        # 앙상블 전체 통계 (cmip6_ensemble_periods.csv — std/n_models/best_model 포함)
        ens_periods_path = ENSEMBLE_RAW_DIR / "cmip6_ensemble_periods.csv"
        if ens_periods_path.exists():
            ep = pd.read_csv(ens_periods_path)
            if "ssp" in ep.columns:
                ep["ssp"] = ep["ssp"].map(SSP_NORM).fillna(ep["ssp"])
            if "period" in ep.columns:
                ep["period"] = ep["period"].map(PERIOD_NORM).fillna(ep["period"])
            self._cmip6_ens = ep
            logger.info(f"cmip6_ensemble_periods.csv loaded: {len(ep)} rows")
        else:
            logger.warning(f"cmip6_ensemble_periods.csv not found at {ens_periods_path}")

        # 모델별 기간 요약 (cmip6_model_periods.csv)
        model_periods_path = ENSEMBLE_RAW_DIR / "cmip6_model_periods.csv"
        if model_periods_path.exists():
            mp = pd.read_csv(model_periods_path)
            if "ssp" in mp.columns:
                mp["ssp"] = mp["ssp"].map(SSP_NORM).fillna(mp["ssp"])
            if "period" in mp.columns:
                mp["period"] = mp["period"].map(PERIOD_NORM).fillna(mp["period"])
            self._cmip6_model = mp
            logger.info(f"cmip6_model_periods.csv loaded: {len(mp)} rows")
        else:
            logger.warning(f"cmip6_model_periods.csv not found at {model_periods_path}")

        if physrisk_path.exists():
            self._physrisk = pd.read_csv(physrisk_path)
            logger.info(f"physrisk_sites.csv loaded: {len(self._physrisk)} rows")
        else:
            logger.warning(f"physrisk_sites.csv not found at {physrisk_path}")

        if etccdi_path.exists():
            self._etccdi = pd.read_csv(etccdi_path)
            logger.info(f"etccdi_sites.csv loaded: {len(self._etccdi)} rows")
        else:
            logger.warning(f"etccdi_sites.csv not found at {etccdi_path}")

        static_path = DATA_DIR / "static_sites.csv"
        if static_path.exists():
            self._static = pd.read_csv(static_path)
            logger.info(f"static_sites.csv loaded: {len(self._static)} rows")
        else:
            logger.warning(f"static_sites.csv not found at {static_path}")

        self._loaded = True

    # ── CMIP6 데이터 조회 ──────────────────────────────────────────────────

    # build_ensemble.py used .sum() for pr/prsn/evspsbl instead of .mean()
    # → values stored as ~12× the true mm/day rate; correct by dividing by 12
    _PR_DIV12 = {"pr", "prsn", "evspsbl"}

    def get_site_cmip6(self, site_name: str) -> dict:
        """
        Returns {ssp: {period: {var: value}}}
        value는 ens_mean. 앙상블 통계가 필요하면 get_site_cmip6_full() 사용.
        """
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
                    fval = float(val) if val is not None and not math.isnan(float(val)) else None
                    if fval is not None and var in self._PR_DIV12:
                        fval = round(fval / 12.0, 4)
                    result[ssp][period][var] = fval
                except (TypeError, ValueError):
                    result[ssp][period][var] = None
        return result

    def get_site_cmip6_full(self, site_name: str) -> dict:
        """
        앙상블 통계 포함 전체 조회 (cmip6_ensemble_periods.csv 기반).
        Returns {ssp: {period: {var: {mean, median, p10, p90, std, n_models, best_model}}}}
        """
        src = self._cmip6_ens if self._cmip6_ens is not None else self._cmip6
        if src is None:
            return {}
        df = src[src["site"] == site_name]
        if df.empty:
            return {}

        stat_cols = ["ens_mean", "ens_median", "ens_p10", "ens_p90", "ens_std",
                     "n_models", "best_model"]

        def _safe(val):
            try:
                return float(val) if val is not None and not math.isnan(float(val)) else None
            except (TypeError, ValueError):
                return None

        result = {}
        for _, row in df.iterrows():
            ssp    = row.get("ssp", "")
            period = row.get("period", "")
            var    = row.get("variable", "")
            if not (ssp and period and var):
                continue
            result.setdefault(ssp, {}).setdefault(period, {})
            stats = {}
            for col in stat_cols:
                raw_val = row.get(col)
                if col in ("n_models", "best_model"):
                    stats[col] = raw_val
                else:
                    fval = _safe(raw_val)
                    if fval is not None and var in self._PR_DIV12:
                        fval = round(fval / 12.0, 4)
                    stats[col] = fval
            result[ssp][period][var] = stats
        return result

    def get_site_cmip6_by_model(self, site_name: str, model: str) -> dict:
        """
        특정 모델의 기간별 값 조회.
        Returns {ssp: {period: {var: value}}}
        """
        if self._cmip6_model is None:
            return {}
        df = self._cmip6_model[
            (self._cmip6_model["site"] == site_name) &
            (self._cmip6_model["model"] == model)
        ]
        if df.empty:
            return {}

        result = {}
        for _, row in df.iterrows():
            ssp    = row.get("ssp", "")
            period = row.get("period", "")
            var    = row.get("variable", "")
            val    = row.get("value", None)
            if ssp and period and var:
                result.setdefault(ssp, {}).setdefault(period, {})
                try:
                    fval = float(val) if val is not None and not math.isnan(float(val)) else None
                    if fval is not None and var in self._PR_DIV12:
                        fval = round(fval / 12.0, 4)
                    result[ssp][period][var] = fval
                except (TypeError, ValueError):
                    result[ssp][period][var] = None
        return result

    def list_models(self, site_name: Optional[str] = None) -> list[str]:
        """사용 가능한 CMIP6 모델 목록."""
        if self._cmip6_model is None:
            return []
        df = self._cmip6_model
        if site_name:
            df = df[df["site"] == site_name]
        return sorted(df["model"].unique().tolist())

    # ── ETCCDI 데이터 조회 ─────────────────────────────────────────────────────

    def get_site_etccdi(self, site_name: str) -> dict:
        """ETCCDI 기후 극값 지수 조회. Returns {ssp: {period: {var: value}}}"""
        if self._etccdi is None:
            return {}
        df = self._etccdi[self._etccdi["site"] == site_name]
        if df.empty:
            return {}

        result = {}
        for _, row in df.iterrows():
            ssp    = str(row.get("ssp", ""))
            period = str(row.get("period", ""))
            var    = str(row.get("variable", ""))
            val    = row.get("ens_mean", None)
            if ssp and period and var:
                result.setdefault(ssp, {}).setdefault(period, {})
                try:
                    result[ssp][period][var] = float(val) if val is not None and not math.isnan(float(val)) else None
                except (TypeError, ValueError):
                    result[ssp][period][var] = None
        return result

    # ── PhyRisk 위험유형 → driver 키 매핑 (hazard_raw, driver_key, indicator) ───
    # 한 위험유형에서 복수 driver 추출 가능

    HAZARD_DRIVERS: list[tuple[str, str, str]] = [
        # ChronicHeat — 5개 driver
        ("ChronicHeat", "heat_stress",      "days_wbgt_above"),                # WBGT 초과일수 (일/yr)
        ("ChronicHeat", "extreme_heat_35c", "days_tas/above/35c"),             # 35°C 초과일수 (일/yr)
        ("ChronicHeat", "work_loss_high",   "mean_work_loss/high"),            # 고강도 노동손실 (0~1)
        ("ChronicHeat", "work_loss_medium", "mean_work_loss/medium"),          # 중강도 노동손실 (0~1)
        ("ChronicHeat", "heat_degree_days", "mean_degree_days/above/32c"),     # 냉방 도일 CDD
        # Drought
        ("Drought",            "drought_risk",    "months/spei12m/below/threshold"),
        # WaterRisk — 2개 driver
        ("WaterRisk",          "water_stress",    "water_stress"),
        ("WaterRisk",          "water_depletion", "water_depletion"),           # 물 고갈 지수 (0~1)
        # 기타
        ("RiverineInundation", "river_flood",     "flood_depth"),
        ("CoastalInundation",  "coastal_flood",   "flood_depth"),
        ("Wind",               "cyclone_risk",    "max_speed"),
        ("Fire",               "wildfire_risk",   "fire_probability"),
        ("Precipitation",      "pluvial_flood",   "max/daily/water_equivalent"),
    ]

    @staticmethod
    def _normalize(driver_key: str, raw: float) -> float:
        """
        원시 physrisk 값 → 0~100 위험도 점수 변환 (driver_key 기반).
        """
        if raw is None or math.isnan(raw):
            return None
        fns = {
            # ChronicHeat group
            "heat_stress":      lambda v: v / 3.65,   # WBGT days ÷ 3.65  (365일=100점)
            "extreme_heat_35c": lambda v: v * 10.0,   # days × 10          (10일=100점)
            "work_loss_high":   lambda v: v * 100,    # 0~1 비율 → 0~100점
            "work_loss_medium": lambda v: v * 100,    # 0~1 비율 → 0~100점
            "heat_degree_days": lambda v: v / 6.0,    # CDD ÷ 6            (600CDD=100점)
            # Drought / Water
            "drought_risk":     lambda v: v / 0.12,   # 월/년 ÷ 0.12       (12개월=100점)
            "water_stress":     lambda v: v * 100,    # 0~1 → 100점
            "water_depletion":  lambda v: v * 100,    # 0~1 → 100점
            # Flood / Wind / Fire
            "river_flood":      lambda v: v * 20,     # m × 20             (5m=100점)
            "coastal_flood":    lambda v: v * 20,
            "cyclone_risk":     lambda v: v / 0.7,    # m/s ÷ 0.7          (70m/s=100점)
            "wildfire_risk":    lambda v: v * 100,    # 0~1 확률 → 100점
            "pluvial_flood":    lambda v: v / 5.0,    # mm ÷ 5             (500mm=100점)
        }
        fn = fns.get(driver_key, lambda v: v / 3.65)
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

        for hazard_raw, driver_key, indicator in self.HAZARD_DRIVERS:
            hdf = df[df["hazard"] == hazard_raw]
            ind_df = hdf[hdf["indicator"] == indicator]
            if ind_df.empty:
                ind_df = hdf  # fallback: indicator 없으면 해당 hazard 전체
            if ind_df.empty:
                continue

            hazard_ssp = {}

            for ssp_raw in ["ssp126", "ssp245", "ssp585"]:
                sdf = ind_df[ind_df["scenario"] == ssp_raw]
                periods = {}
                for _, row in sdf.iterrows():
                    try:
                        year = int(row["year"])
                        raw  = float(row["value"])
                    except (TypeError, ValueError):
                        continue
                    score = self._normalize(driver_key, raw)
                    if score is None:
                        continue
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

    # ── Static / Historical 데이터 조회 ───────────────────────────────────────

    def get_site_static(self, site_name: str) -> dict:
        """
        Aqueduct / IBTrACS / PSHA 정적 데이터 조회.

        Returns:
            {variable: value}  — SSP·시점 구분 없는 단일 값
        """
        if self._static is None:
            return {}
        df = self._static[self._static["site"] == site_name]
        if df.empty:
            return {}
        result = {}
        for _, row in df.iterrows():
            var = row.get("variable", "")
            val = row.get("value", None)
            if var:
                try:
                    result[var] = float(val) if val is not None and not math.isnan(float(val)) else None
                except (TypeError, ValueError):
                    result[var] = None
        return result

    @property
    def loaded(self):
        return self._loaded


site_data = SiteDataLoader()

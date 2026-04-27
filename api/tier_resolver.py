"""
tier_resolver.py — Tier 판별 + 데이터 조합 오케스트레이터

T1 (기존 14사이트 5km 이내): 사전계산 CSV 즉시 반환
T2 (east_asia/se_asia CMIP6 커버리지): CMIP6 1° 그리드 + 근사 physrisk
T3 (전구 임의 좌표): CMIP6 2° 전구 그리드 + 근사 physrisk
"""
from __future__ import annotations

import math
import asyncio
import logging
from typing import Optional

from site_constants import OCI_SITES, DRIVER_META, convert_cmip6_value
from data_loader import site_data
from cmip6_grid import cmip6_grid
from physrisk_client import fetch_physrisk
from psha_client import fetch_earthquake_risk
from etccdi_estimator import estimate_etccdi, ETCCDI_CONFIDENCE
from cmip6_nc_query import query_model_nc, list_models_for_coord
from climada_global import query_climada
from static_estimator import query_static
from physrisk_client import estimate_physrisk_cmip6
from psha_client import pga_to_risk_score
from interpret_engine import interpret as _interpret_drivers

logger = logging.getLogger(__name__)

try:
    from cckp_client import query_cckp as _query_cckp
    _CCKP_AVAILABLE = True
except ImportError:
    _CCKP_AVAILABLE = False
    logger.warning("cckp_client 로드 실패 — CCKP 변수 비활성화")

try:
    from kma_client import query_kma as _query_kma, is_available as _kma_available
    _KMA_AVAILABLE = True
except ImportError:
    _KMA_AVAILABLE = False
    _query_kma = None
    _kma_available = lambda: False

try:
    from kma_cordex_client import (
        query_cordex as _query_cordex,
        is_available as _cordex_available,
        is_cordex_coord as _is_cordex_coord,
    )
    _CORDEX_AVAILABLE = True
except ImportError:
    _CORDEX_AVAILABLE = False
    _query_cordex = None
    _cordex_available = lambda: False
    _is_cordex_coord = lambda lat, lon: False

# T1 판별 거리 임계값 (km)
T1_RADIUS_KM = -1.0

SSP_KEYS = ["ssp126", "ssp245", "ssp370", "ssp585"]
SSP_LABELS = {
    "ssp126": "SSP1-2.6 (강한 감축)",
    "ssp245": "SSP2-4.5 (중간 경로)",
    "ssp370": "SSP3-7.0 (고배출)",
    "ssp585": "SSP5-8.5 (화석연료 집약)",
}
PERIOD_KEYS = ["baseline", "near", "mid", "far", "end"]
PERIOD_LABELS = {
    "baseline": "현재 (2015-2024)",
    "near":     "단기 (2025-2034)",
    "mid":      "중기 (2045-2054)",
    "far":      "장기 (2075-2084)",
    "end":      "장기+ (2090-2099)",
}

CMIP6_VARS = ["tasmax", "tasmin", "tas", "pr", "prsn", "sfcWind", "evspsbl"]

ETCCDI_VARS = [
    "etccdi_txx", "etccdi_tnn", "etccdi_su",   "etccdi_tr",   "etccdi_fd",
    "etccdi_wsdi","etccdi_wbgt","etccdi_cdd",   "etccdi_cwd",
    "etccdi_rx1day","etccdi_rx5day","etccdi_r95p","etccdi_sdii",
]

ALL_CLIMATE_VARS = CMIP6_VARS + ETCCDI_VARS


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 Haversine 거리 (km)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_t1(lat: float, lon: float) -> tuple[Optional[str], float]:
    """가장 가까운 T1 사이트와 거리 반환."""
    best_site = None
    best_dist = float("inf")
    for site_name, meta in OCI_SITES.items():
        dist = haversine_km(lat, lon, meta["lat"], meta["lon"])
        if dist < best_dist:
            best_dist = dist
            best_site = site_name
    return best_site, round(best_dist, 2)


def determine_tier(lat: float, lon: float) -> tuple[str, Optional[str], float]:
    """
    Tier 결정.

    Returns:
        (tier, matched_t1_site, distance_km)
    """
    nearest_site, dist_km = find_nearest_t1(lat, lon)

    if dist_km <= T1_RADIUS_KM:
        return "T1", nearest_site, dist_km

    # T2: east_asia CMIP6 커버리지 내
    if cmip6_grid.is_covered(lat, lon):
        return "T2", nearest_site, dist_km

    # T3: 전구
    return "T3", nearest_site, dist_km


def _infer_country(lat: float, lon: float) -> str:
    """위도/경도 기반 국가 코드 근사 추론."""
    # 간단한 박스 매핑
    COUNTRY_BOXES = [
        (34, 39, 124, 132, "KOR"),
        (20, 54, 73, 135, "CHN"),
        (30, 46, 129, 146, "JPN"),
        (4, 22, 116, 128, "PHL"),
        (24, 50, -125, -66, "USA"),
        (36, 72, -10, 40, "EUR"),
        (-35, 37, -18, 52, "AFR"),
        (18, 35, 35, 73, "MID"),
        (5, 35, 60, 98, "SAS"),
    ]
    for lat_min, lat_max, lon_min, lon_max, code in COUNTRY_BOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return code
    return "GLB"


def _expand_flat_physrisk(flat: dict) -> dict:
    """
    T2/T3 physrisk 근사값(flat dict) → nested 구조 변환.
    {driver_key: score} → {driver_key: {ssp: {period: score}}}
    (시나리오 구분 없는 단일 근사값을 모든 SSP·시점에 복사)
    """
    result = {}
    for driver_key, score in flat.items():
        result[driver_key] = {
            ssp: {period: score for period in PERIOD_KEYS}
            for ssp in SSP_KEYS
        }
    return result


def _build_drivers_from_cmip6(
    cmip6_data: dict,
    physrisk_data: dict,
    source_label: str,
    static_data: Optional[dict] = None,
    lat: Optional[float] = None,
) -> dict:
    """
    CMIP6 + physrisk + static 데이터를 합쳐 drivers 딕셔너리 생성.

    Args:
        cmip6_data:    {ssp: {period: {var: value}}}
        physrisk_data: {driver_key: {ssp: {period: score}}}
        source_label:  CMIP6 데이터 출처 레이블
        static_data:   {variable: value}  — Aqueduct/IBTrACS/PSHA 정적 값
        lat:           위도 (ETCCDI 회귀 추정용, T2/T3에서만 사용)

    Returns:
        {ssp: {period: {var: {value, source}}}}
    """
    static_data = static_data or {}
    result = {}
    for ssp in SSP_KEYS:
        result[ssp] = {}
        for period in PERIOD_KEYS:
            result[ssp][period] = {}

            # ── CMIP6 + ETCCDI 변수 ────────────────────────────────────────
            cmip6_period = (cmip6_data.get(ssp) or {}).get(period) or {}

            # T2/T3: ETCCDI 없으면 CMIP6 예측변수로 회귀 추정
            etccdi_estimated: dict = {}
            if lat is not None:
                missing_etccdi = any(
                    cmip6_period.get(v) is None for v in ETCCDI_VARS
                )
                if missing_etccdi:
                    tm = cmip6_period.get("tasmax")
                    tn = cmip6_period.get("tasmin")
                    ta = cmip6_period.get("tas")
                    pr = cmip6_period.get("pr")
                    etccdi_estimated = estimate_etccdi(tm, tn, ta, pr, lat)

            for var in ALL_CLIMATE_VARS:
                val = cmip6_period.get(var)
                if var.startswith("etccdi_"):
                    if val is None and var in etccdi_estimated:
                        val = etccdi_estimated[var]
                        src = "ETCCDI_est"
                    else:
                        src = "ETCCDI"
                else:
                    src = "CMIP6"
                entry: dict = {"value": val, "source": src}
                # 추정값은 신뢰도 등급 첨부 (사용자 불확실성 인지용)
                if src == "ETCCDI_est" and var in ETCCDI_CONFIDENCE:
                    entry["confidence"] = ETCCDI_CONFIDENCE[var]
                result[ssp][period][var] = entry

            # ── PhyRisk 변수 (SSP·시점별 개별 값) ──────────────────────────
            # CMIP6 기반 추정값 (null 보완용) — 해당 SSP/period 값 사용
            _est_fallback: Optional[dict] = None

            for hazard, meta in DRIVER_META.items():
                if meta.get("source_type") in ("physrisk", "psha"):
                    nested = physrisk_data.get(hazard)
                    if isinstance(nested, dict):
                        val = nested.get(ssp, {}).get(period)
                    else:
                        val = None

                    # null이면 CMIP6 기반 추정으로 보완
                    src = "PhyRisk"
                    if val is None and lat is not None:
                        if _est_fallback is None:
                            _est_fallback = estimate_physrisk_cmip6(
                                lat, 0.0,  # lon은 이미 CMIP6 pr에 반영
                                tasmax=cmip6_period.get("tasmax"),
                                tasmin=cmip6_period.get("tasmin"),
                                tas=cmip6_period.get("tas"),
                                pr=cmip6_period.get("pr"),
                            )
                        val = _est_fallback.get(hazard)
                        if val is not None:
                            src = "PhyRisk_est"

                    # earthquake_risk: static psha_pga_475 기반 변환
                    if hazard == "earthquake_risk" and val is None:
                        pga = static_data.get("psha_pga_475")
                        if pga is not None:
                            val = pga_to_risk_score(pga)
                            src = "PSHA_derived"

                    result[ssp][period][hazard] = {
                        "value": val,
                        "source": src,
                    }

            # ── 정적 변수 (Aqueduct / IBTrACS / PSHA) ─────────────────────
            for var, val in static_data.items():
                src_map = {
                    "aq_": "Aqueduct4",
                    "tc_": "IBTrACS",
                    "psha_": "PSHA",
                }
                source = next((s for pfx, s in src_map.items() if var.startswith(pfx)), "static")
                result[ssp][period][var] = {
                    "value": val,
                    "source": source,
                }

    return result


def _inject_climada(drivers: dict, lat: float, lon: float) -> None:
    """
    CLIMADA HDF5에서 TC/홍수/산불/지진 EAL 조회 후 drivers에 삽입.
    지원 국가 외는 None 유지.
    """
    try:
        climada = query_climada(lat, lon)
    except Exception as e:
        logger.warning(f"CLIMADA query failed ({lat},{lon}): {e}")
        climada = {}

    for ssp in SSP_KEYS:
        for period in PERIOD_KEYS:
            for var, key in [("TC_EAL", "TC_EAL"), ("Flood_EAL", "Flood_EAL"),
                              ("Wildfire_EAL", "Wildfire_EAL"), ("EQ_EAL", "EQ_EAL")]:
                existing = drivers[ssp][period].get(var)
                if existing is None or (isinstance(existing, dict) and existing.get("value") is None):
                    drivers[ssp][period][var] = {
                        "value": climada.get(key),
                        "source": "CLIMADA_HDF5" if climada.get(key) is not None else "no_coverage",
                    }


async def _inject_kma(drivers: dict, lat: float, lon: float) -> None:
    """
    KMA 1km 기후변화 시나리오 값을 drivers에 병합 (한반도 좌표 전용).
    데이터 미준비 시 조용히 스킵.
    """
    if not _KMA_AVAILABLE or not _kma_available():
        return
    try:
        kma = _query_kma(lat, lon)
    except Exception as e:
        logger.warning("KMA query failed (%s,%s): %s", lat, lon, e)
        return

    for var_key, ssp_dict in kma.items():
        if var_key == '_kma_meta':  # 메타 키 스킵
            continue
        for ssp in SSP_KEYS:
            for period in PERIOD_KEYS:
                val = (ssp_dict.get(ssp) or {}).get(period)
                # KMA 값이 있으면 기존 CMIP6 값을 덮어씀 (더 높은 해상도)
                if val is not None:
                    drivers[ssp][period][var_key] = {
                        "value":  val,
                        "source": "KMA_RDA",   # 농촌진흥청 ENS 앙상블
                    }


async def _inject_cordex(drivers: dict, lat: float, lon: float) -> None:
    """
    기상청 CORDEX 1km 시나리오 값을 drivers에 병합 (한반도 좌표 전용).
    KMA_RDA보다 나중에 주입되므로 같은 변수가 있으면 덮어씀 (더 권위 있는 소스).
    데이터 미준비 시 조용히 스킵.
    """
    if not _CORDEX_AVAILABLE or not _cordex_available():
        return
    try:
        cordex = _query_cordex(lat, lon)
    except Exception as e:
        logger.warning("KMA CORDEX query failed (%s,%s): %s", lat, lon, e)
        return

    for var_key, ssp_dict in cordex.items():
        if var_key.startswith('_'):
            continue
        for ssp in SSP_KEYS:
            for period in PERIOD_KEYS:
                val = (ssp_dict.get(ssp) or {}).get(period)
                if val is not None:
                    drivers[ssp][period][var_key] = {
                        "value":  val,
                        "source": "KMA_CORDEX",  # 기상청 동역학 상세화
                    }


async def _inject_cckp(drivers: dict, lat: float, lon: float) -> None:
    """
    CCKP 0.25° 신규 변수 5개를 drivers에 병합.
    netCDF4 미설치 또는 S3 접근 실패 시 조용히 스킵.
    """
    if not _CCKP_AVAILABLE:
        return
    try:
        cckp = await _query_cckp(lat, lon)
    except Exception as e:
        logger.warning("CCKP query failed (%s,%s): %s", lat, lon, e)
        return

    for var_key, ssp_dict in cckp.items():
        for ssp in SSP_KEYS:
            for period in PERIOD_KEYS:
                val = (ssp_dict.get(ssp) or {}).get(period)
                drivers[ssp][period][var_key] = {
                    "value":  val,
                    "source": "CCKP_0.25deg" if val is not None else "no_data",
                }


_RES_MAP = {"T1": "precomputed", "T2": "1deg",  "T3": "2deg"}
_SRC_MAP = {"T1": "ensemble_17models", "T2": "cmip6_1deg_grid", "T3": "cmip6_2deg_grid"}


def _build_meta(lat: float, lon: float, country: str, tier: str) -> dict:
    meta = {
        "lat": lat,
        "lon": lon,
        "country": country,
        "resolution": _RES_MAP[tier],
        "data_source": _SRC_MAP[tier],
    }
    # KMA_RDA: 한반도 167개 행정구역
    from kma_client import is_korean_coord
    if is_korean_coord(lat, lon) and _KMA_AVAILABLE and _kma_available():
        meta["kma_rda"] = True
    # CORDEX: 전역 CSV 있으면 전 세계, 없으면 EAS-22만
    if _is_cordex_coord(lat, lon) and _CORDEX_AVAILABLE and _cordex_available():
        meta["kma_cordex"] = True
    return meta


async def resolve(lat: float, lon: float) -> dict:
    """임의 좌표 → 기후 리스크 데이터 반환."""
    tier, matched_site, dist_km = determine_tier(lat, lon)
    country = _infer_country(lat, lon)
    meta = _build_meta(lat, lon, country, tier)

    # ── T1: 사전계산 데이터 직접 반환 ───────────────────────────────────────
    if tier == "T1":
        cmip6_data      = site_data.get_site_cmip6(matched_site)
        etccdi_data     = site_data.get_site_etccdi(matched_site)
        physrisk_nested = site_data.get_site_physrisk(matched_site)
        static_data     = site_data.get_site_static(matched_site)

        # ETCCDI 데이터를 cmip6_data에 병합 (같은 {ssp: {period: {var: val}}} 구조)
        for ssp, periods in etccdi_data.items():
            cmip6_data.setdefault(ssp, {})
            for period, vars_dict in periods.items():
                cmip6_data[ssp].setdefault(period, {}).update(vars_dict)

        drivers = _build_drivers_from_cmip6(cmip6_data, physrisk_nested, "CMIP6_T1", static_data, lat=lat)
        _inject_climada(drivers, lat, lon)
        try:
            await asyncio.wait_for(_inject_cckp(drivers, lat, lon), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("CCKP injection timed out — skipping for (%s,%s)", lat, lon)
        await _inject_kma(drivers, lat, lon)
        await _inject_cordex(drivers, lat, lon)
        result = {"meta": meta, "drivers": drivers}
        result["interpretation"] = _interpret_drivers(drivers)
        return result

    # ── T2/T3: CMIP6 그리드 + 비동기 physrisk/PSHA ──────────────────────────
    cmip6_data = cmip6_grid.query(lat, lon)

    # ssp245/mid 기준 CMIP6 값으로 PhyRisk 품질 향상 (중간 경로 기준)
    _ref = (cmip6_data.get("ssp245") or {}).get("mid") or {}
    physrisk_task = asyncio.create_task(fetch_physrisk(
        lat, lon,
        tasmax=_ref.get("tasmax"), tasmin=_ref.get("tasmin"),
        tas=_ref.get("tas"), pr=_ref.get("pr"),
    ))
    psha_task = asyncio.create_task(fetch_earthquake_risk(lat, lon))

    physrisk_result, psha_result = await asyncio.gather(physrisk_task, psha_task, return_exceptions=True)

    if isinstance(physrisk_result, Exception):
        logger.warning(f"PhyRisk failed: {physrisk_result}")
        physrisk_result = {}
    if isinstance(psha_result, Exception):
        logger.warning(f"PSHA failed: {psha_result}")
        psha_result = {}

    # T2/T3 physrisk는 flat dict → nested 변환 (시나리오 구분 없는 근사값)
    combined_flat = {**physrisk_result, **psha_result}
    combined_physrisk = _expand_flat_physrisk(combined_flat)

    # T2/T3: 전구 정적 추정값 (IBTrACS 격자 + Aqueduct 보간 + PSHA 지진위험대)
    static_data = query_static(lat, lon)

    drivers = _build_drivers_from_cmip6(cmip6_data, combined_physrisk, "CMIP6", static_data, lat=lat)
    _inject_climada(drivers, lat, lon)
    try:
        await asyncio.wait_for(_inject_cckp(drivers, lat, lon), timeout=10.0)
    except asyncio.TimeoutError:
        logger.warning("CCKP injection timed out — skipping for (%s,%s)", lat, lon)
    await _inject_kma(drivers, lat, lon)
    await _inject_cordex(drivers, lat, lon)

    result = {"meta": meta, "drivers": drivers}
    result["interpretation"] = _interpret_drivers(drivers)
    return result


def build_summary(meta: dict, drivers: dict) -> dict:
    """
    drivers 전체 구조 → 사용자 친화적 요약 응답 변환.

    baseline은 SSP 독립 (역사적 관측 기반).
    hazards는 SSP126·SSP245·SSP585 × mid(2050)·end(2090) 6개 조합으로 반환.

    Returns:
        {location, climate, hazards}
    """
    def _v(ssp, period, var):
        return (drivers.get(ssp, {}).get(period, {}).get(var, {}) or {}).get("value")

    # baseline은 SSP 무관 — ssp245 baseline과 동일
    def _base(var):
        for ssp in ("ssp245", "ssp126", "ssp585"):
            v = _v(ssp, "baseline", var)
            if v is not None:
                return v
        return None

    base_t = _base("tas")

    def _proj(ssp, period):
        t = _v(ssp, period, "tas")
        return {
            "temp_mean":     t,
            "temp_change":   round(t - base_t, 2) if (t is not None and base_t is not None) else None,
            "temp_max":      _v(ssp, period, "tasmax"),
            "summer_days":   _v(ssp, period, "etccdi_su"),
            "rx1day_mm":     _v(ssp, period, "etccdi_rx1day"),
            "precip_mm_day": _v(ssp, period, "pr"),
        }

    def _hazards(ssp, period):
        return {
            "heat_stress":   _v(ssp, period, "heat_stress"),
            "flood":         _v(ssp, period, "flood_risk"),
            "drought":       _v(ssp, period, "drought_risk"),
            "wildfire":      _v(ssp, period, "wildfire_risk"),
            "cyclone":       _v(ssp, period, "cyclone_risk"),
            "water_stress":  _v(ssp, period, "water_stress"),
            "sea_level_rise":_v(ssp, period, "sea_level_rise"),
            "earthquake":    _v(ssp, period, "earthquake_risk"),
        }

    return {
        "location": meta,
        "climate": {
            "baseline": {
                "temp_mean":     base_t,
                "temp_max":      _base("tasmax"),
                "precip_mm_day": _base("pr"),
                "summer_days":   _base("etccdi_su"),
                "frost_days":    _base("etccdi_fd"),
                "rx1day_mm":     _base("etccdi_rx1day"),
                "wbgt_mean":     _base("etccdi_wbgt"),
            },
            "ssp126_2050": _proj("ssp126", "mid"),
            "ssp126_2090": _proj("ssp126", "end"),
            "ssp245_2050": _proj("ssp245", "mid"),
            "ssp245_2090": _proj("ssp245", "end"),
            "ssp585_2050": _proj("ssp585", "mid"),
            "ssp585_2090": _proj("ssp585", "end"),
        },
        "hazards": {
            "ssp126": {
                "2050": _hazards("ssp126", "mid"),
                "2090": _hazards("ssp126", "end"),
            },
            "ssp245": {
                "2050": _hazards("ssp245", "mid"),
                "2090": _hazards("ssp245", "end"),
            },
            "ssp585": {
                "2050": _hazards("ssp585", "mid"),
                "2090": _hazards("ssp585", "end"),
            },
        },
    }


async def resolve_with_ensemble(lat: float, lon: float) -> dict:
    """
    resolve() + 앙상블 통계 (p10/p90/std/n_models/best_model) 반환.
    precomputed 좌표: 통계 포함 / 그 외: ensemble_stats=null.
    """
    base = await resolve(lat, lon)
    if base["meta"]["resolution"] != "precomputed":
        base["ensemble_stats"] = None
        return base

    tier, matched_site, _ = determine_tier(lat, lon)
    full = site_data.get_site_cmip6_full(matched_site)
    base["ensemble_stats"] = full
    return base


async def resolve_model(lat: float, lon: float, model: str) -> dict:
    """
    특정 CMIP6 모델의 단일 값 조회 (T1/T2/T3 전체 지원).

    T1: 사전계산 CSV (빠름, ~즉시)
    T2/T3: NC 파일 직접 읽기 (느림, ~3-10초, 좌표 필수)

    Args:
        lat, lon: 좌표 (T2/T3에서 NC 파일 조회 기준점)
        model:    모델 ID (예: "miroc6", "mpi_esm1_2_lr")

    Returns:
        {meta, model, region, drivers, available_models}
    """
    tier, matched_site, dist_km = determine_tier(lat, lon)
    country = _infer_country(lat, lon)
    meta = _build_meta(lat, lon, country, tier)

    # ── precomputed: 사전계산 CSV 조회 (빠름) ────────────────────────────────
    if tier == "T1":
        available = site_data.list_models(matched_site)
        model_cmip6 = site_data.get_site_cmip6_by_model(matched_site, model)
        if not model_cmip6:
            return {
                "meta": meta, "model": model, "region": "T1_precomputed",
                "drivers": None, "available_models": available,
                "error": f"모델 '{model}' 데이터 없음. available_models 확인.",
            }
        etccdi_data     = site_data.get_site_etccdi(matched_site)
        physrisk_nested = site_data.get_site_physrisk(matched_site)
        static_data     = site_data.get_site_static(matched_site)
        for ssp, periods in etccdi_data.items():
            model_cmip6.setdefault(ssp, {})
            for period, vd in periods.items():
                model_cmip6[ssp].setdefault(period, {}).update(vd)
        drivers = _build_drivers_from_cmip6(
            model_cmip6, physrisk_nested, f"CMIP6_model:{model}", static_data, lat=lat,
        )
        _inject_climada(drivers, lat, lon)
        return {
            "meta": meta, "model": model, "region": "T1_precomputed",
            "drivers": drivers, "available_models": available,
        }

    # ── T2/T3: NC 파일 직접 읽기 (좌표 기반) ────────────────────────────────
    available = list_models_for_coord(lat, lon)

    nc_result = query_model_nc(lat, lon, model=model)
    if not nc_result:
        return {
            "meta": meta, "model": model, "region": None,
            "drivers": None, "available_models": available,
            "error": f"좌표 ({lat}, {lon})에 해당하는 NC 커버리지 없음 또는 모델 '{model}' 미지원.",
        }

    region = nc_result.pop("region", "unknown")

    # NC 결과 → cmip6_data 형식 변환 ({ssp: {period: {var: val}}})
    cmip6_from_nc: dict = {}
    for ssp in SSP_KEYS:
        if ssp not in nc_result:
            continue
        cmip6_from_nc[ssp] = {}
        for period in PERIOD_KEYS:
            cmip6_from_nc[ssp][period] = nc_result[ssp].get(period, {})

    # PhyRisk/Static은 물리 추정값 사용 (T2/T3 동일)
    _ref = (cmip6_from_nc.get("ssp245") or {}).get("mid") or {}
    physrisk_flat = await asyncio.gather(
        fetch_physrisk(lat, lon, tasmax=_ref.get("tasmax"),
                       tasmin=_ref.get("tasmin"), tas=_ref.get("tas"), pr=_ref.get("pr")),
        return_exceptions=True,
    )
    phys = physrisk_flat[0] if not isinstance(physrisk_flat[0], Exception) else {}
    combined_physrisk = _expand_flat_physrisk(phys)
    static_data = query_static(lat, lon)

    source_label = f"CMIP6_model:{model}_T2" if tier == "T2" else f"CMIP6_model:{model}_T3"
    drivers = _build_drivers_from_cmip6(cmip6_from_nc, combined_physrisk, source_label, static_data, lat=lat)
    _inject_climada(drivers, lat, lon)

    return {
        "meta": meta, "model": model, "region": region,
        "drivers": drivers, "available_models": available,
    }


def list_available_models() -> list[str]:
    """전체 사용 가능한 CMIP6 모델 목록."""
    return site_data.list_models()

"""
tier_resolver.py — Tier 판별 + 데이터 조합 오케스트레이터

T1 (기존 14사이트 5km 이내): 사전계산 CSV 즉시 반환
T2 (east_asia/se_asia CMIP6 커버리지): CMIP6 1° 그리드 + 근사 physrisk
T3 (전구 임의 좌표): CMIP6 2° 전구 그리드 + 근사 physrisk
"""

import math
import asyncio
import logging
from typing import Optional

from site_constants import OCI_SITES, DRIVER_META, convert_cmip6_value
from data_loader import site_data
from cmip6_grid import cmip6_grid
from physrisk_client import fetch_physrisk
from psha_client import fetch_earthquake_risk

logger = logging.getLogger(__name__)

# T1 판별 거리 임계값 (km)
T1_RADIUS_KM = 5.0

SSP_KEYS = ["ssp126", "ssp245", "ssp370", "ssp585"]
SSP_LABELS = {
    "ssp126": "SSP1-2.6 (저탄소)",
    "ssp245": "SSP2-4.5 (중간)",
    "ssp370": "SSP3-7.0 (고탄소)",
    "ssp585": "SSP5-8.5 (극단)",
}
PERIOD_KEYS = ["baseline", "near", "mid", "far", "end"]
PERIOD_LABELS = {
    "baseline": "현재 (2015-2024)",
    "near":     "근미래 (2025-2034)",
    "mid":      "중기 (2045-2054)",
    "far":      "장기 (2075-2084)",
    "end":      "말기 (2090-2099)",
}

CMIP6_VARS = ["tasmax", "tasmin", "tas", "pr", "prsn", "sfcWind", "evspsbl"]


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


def _build_drivers_from_cmip6(cmip6_data: dict, physrisk_data: dict, source_label: str) -> dict:
    """
    CMIP6 + physrisk 데이터를 합쳐 drivers 딕셔너리 생성.

    Returns:
        {ssp: {period: {var: {value, source}}}}
    """
    result = {}
    for ssp in SSP_KEYS:
        result[ssp] = {}
        for period in PERIOD_KEYS:
            result[ssp][period] = {}

            # CMIP6 변수
            cmip6_period = (cmip6_data.get(ssp) or {}).get(period) or {}
            for var in CMIP6_VARS:
                val = cmip6_period.get(var)
                result[ssp][period][var] = {
                    "value": val,
                    "source": source_label,
                }

            # PhyRisk (ssp/period 무관하게 현재 단일 값으로 처리)
            for hazard, meta in DRIVER_META.items():
                if meta.get("source_type") in ("physrisk", "psha"):
                    val = physrisk_data.get(hazard)
                    result[ssp][period][hazard] = {
                        "value": val,
                        "source": "physrisk_estimate",
                    }

    return result


async def resolve(lat: float, lon: float) -> dict:
    """
    핵심 함수: Tier 결정 → 데이터 조합 → 결과 반환.

    Returns:
        {meta, data, drivers}
    """
    tier, matched_site, dist_km = determine_tier(lat, lon)
    country = _infer_country(lat, lon)

    meta = {
        "lat": lat,
        "lon": lon,
        "country": country,
        "tier": tier,
        "tier_label": _tier_label(tier, matched_site, dist_km),
        "matched_t1_site": matched_site,
        "distance_to_nearest_t1_km": dist_km,
    }

    # ── T1: 사전계산 데이터 직접 반환 ───────────────────────────────────────
    if tier == "T1":
        cmip6_data = site_data.get_site_cmip6(matched_site)
        # get_site_physrisk now returns flat {driver_key: val}
        physrisk_flat = site_data.get_site_physrisk(matched_site)

        drivers = _build_drivers_from_cmip6(cmip6_data, physrisk_flat, "precomputed_t1")
        return {"meta": meta, "drivers": drivers}

    # ── T2/T3: CMIP6 그리드 + 비동기 physrisk/PSHA ──────────────────────────
    cmip6_data = cmip6_grid.query(lat, lon)

    # 비동기 병렬 호출
    physrisk_task = asyncio.create_task(fetch_physrisk(lat, lon))
    psha_task = asyncio.create_task(fetch_earthquake_risk(lat, lon))

    physrisk_result, psha_result = await asyncio.gather(physrisk_task, psha_task, return_exceptions=True)

    if isinstance(physrisk_result, Exception):
        logger.warning(f"PhyRisk failed: {physrisk_result}")
        physrisk_result = {}
    if isinstance(psha_result, Exception):
        logger.warning(f"PSHA failed: {psha_result}")
        psha_result = {}

    # PSHA 결과 병합
    combined_physrisk = {**physrisk_result, **psha_result}

    source_label = "cmip6_grid_1deg" if tier == "T2" else "cmip6_grid_2deg"
    drivers = _build_drivers_from_cmip6(cmip6_data, combined_physrisk, source_label)

    # CLIMADA HDF5 조회 불가 명시
    for ssp in SSP_KEYS:
        for period in PERIOD_KEYS:
            for climada_var in ["TC_EAL", "Flood_EAL", "EQ_EAL", "Wildfire_EAL"]:
                drivers[ssp][period][climada_var] = {
                    "value": None,
                    "source": "nearest_t1_estimate",
                    "note": "CLIMADA HDF5 직접조회 불가 (서버 제약)",
                }

    return {"meta": meta, "drivers": drivers}


def _tier_label(tier: str, matched_site: Optional[str], dist_km: float) -> str:
    if tier == "T1":
        site_display = OCI_SITES.get(matched_site, {}).get("display", matched_site)
        return f"정밀 ({site_display}, {dist_km:.1f}km)"
    elif tier == "T2":
        return f"지역 (동아시아 CMIP6 1° 그리드 + 근사 API, {dist_km:.0f}km from nearest site)"
    else:
        return f"글로벌 (CMIP6 2° 전구 그리드 + 근사 API, {dist_km:.0f}km from nearest site)"

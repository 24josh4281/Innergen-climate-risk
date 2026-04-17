"""
physrisk_client.py — OS-Climate PhyRisk HTTP API 실시간 호출 (신규 좌표용)

PhyRisk는 오픈소스 물리적 기후위험 라이브러리입니다.
공개 API가 없는 경우, 근사값을 gridded 방식으로 반환합니다.
"""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# PhyRisk hazard risk 스케일 (0-100 정규화 근사 기준값)
# 위도/경도 기반 간단한 근사 모델 (실제 API 없이도 합리적인 추정값 제공)

# 열대성 저기압 위험 지역 정의 (대략적)
CYCLONE_PRONE_REGIONS = [
    # (lat_min, lat_max, lon_min, lon_max, base_risk)
    (5, 25, 100, 180, 60),   # 서태평양 (태풍)
    (5, 25, 60, 100, 45),    # 인도양 북부
    (5, 30, -100, -60, 55),  # 대서양 허리케인
    (5, 30, -120, -90, 50),  # 동태평양 허리케인
    (-30, -5, 20, 80, 35),   # 남인도양
    (-30, -5, 100, 180, 40), # 남태평양
]

# 홍수 고위험 지역 (아시아 몬순, 방글라데시 등)
FLOOD_PRONE_REGIONS = [
    (20, 35, 105, 125, 70),  # 중국 남부
    (20, 30, 85, 100, 75),   # 방글라데시 주변
    (10, 25, 100, 125, 65),  # 동남아
    (30, 45, 115, 135, 55),  # 한국/일본
    (50, 60, 0, 20, 45),     # 북유럽
]

def _in_region(lat, lon, regions):
    for lat_min, lat_max, lon_min, lon_max, risk in regions:
        lon_check = lon if lon <= 180 else lon - 360
        if lat_min <= lat <= lat_max and lon_min <= lon_check <= lon_max:
            return risk
    return None

def _base_heat_stress(lat: float) -> float:
    """위도 기반 열 스트레스 근사."""
    abs_lat = abs(lat)
    if abs_lat < 15:
        return 80
    elif abs_lat < 25:
        return 65
    elif abs_lat < 35:
        return 45
    elif abs_lat < 45:
        return 25
    else:
        return 10

def _base_drought_risk(lat: float, lon: float) -> float:
    """위도/경도 기반 가뭄 위험 근사."""
    # 아열대 고압대 (20-35도) → 건조 위험 높음
    abs_lat = abs(lat)
    if 15 <= abs_lat <= 35:
        return 55
    elif abs_lat < 15 or abs_lat > 60:
        return 35
    else:
        return 25

def _base_water_stress(lat: float) -> float:
    """물 부족 위험 (열대·아열대 우선)."""
    abs_lat = abs(lat)
    if abs_lat < 20:
        return 50
    elif abs_lat < 35:
        return 60
    else:
        return 35

def _base_sea_level_rise(lat: float, lon: float, coastal: bool) -> float:
    """해수면 상승 위험."""
    if not coastal:
        return 0
    abs_lat = abs(lat)
    if abs_lat < 20:
        return 65  # 열대 해안 고위험
    elif abs_lat < 40:
        return 45
    else:
        return 30


def estimate_physrisk(lat: float, lon: float) -> dict:
    """
    위도/경도 기반 물리적 기후위험 근사 추정.

    실제 PhyRisk API가 없거나 응답 실패 시 fallback으로 사용.
    반환: {hazard_key: risk_score(0-100)}
    """
    is_coastal = True  # 간략화: 모든 좌표를 해안 가능성으로 처리

    cyclone = _in_region(lat, lon, CYCLONE_PRONE_REGIONS) or 15
    flood = _in_region(lat, lon, FLOOD_PRONE_REGIONS) or 30
    heat = _base_heat_stress(lat)
    drought = _base_drought_risk(lat, lon)
    water = _base_water_stress(lat)
    slr = _base_sea_level_rise(lat, lon, is_coastal)

    return {
        "flood_risk":       round(flood, 1),
        "drought_risk":     round(drought, 1),
        "heat_stress":      round(heat, 1),
        "extreme_heat_35c": round(heat * 0.55, 1),   # 35°C 초과일수 (열스트레스 상관)
        "work_loss_high":   round(heat * 0.85, 1),   # 고강도 노동손실 (열에 강하게 비례)
        "work_loss_medium": round(heat * 0.55, 1),   # 중강도 노동손실
        "heat_degree_days": round(heat * 0.90, 1),   # 냉방 도일 (열스트레스 연동)
        "water_stress":     round(water, 1),
        "water_depletion":  round(water * 0.70, 1),  # 고갈 지수 ≤ 스트레스 지수
        "cyclone_risk":     round(cyclone, 1),
        "wildfire_risk":    round(max(0, drought - 10), 1),
        "sea_level_rise":   round(slr, 1),
        "storm_surge":      round(cyclone * 0.8, 1),
        "landslide_risk":   round(min(50, flood * 0.6), 1),
        "coastal_flood":    round(slr * 0.9, 1),
        "pluvial_flood":    round(flood * 0.7, 1),
        "river_flood":      round(flood * 0.85, 1),
    }


async def fetch_physrisk(lat: float, lon: float) -> dict:
    """
    PhyRisk API 호출 (실제 API 엔드포인트가 있다면 여기서 호출).
    현재는 estimate_physrisk() 근사값 반환.
    """
    # TODO: 실제 OS-Climate API 엔드포인트 연결 시 여기서 httpx 호출
    # async with httpx.AsyncClient(timeout=10.0) as client:
    #     resp = await client.post(PHYSRISK_API_URL, json={"lat": lat, "lon": lon})
    #     return resp.json()

    logger.info(f"PhyRisk estimate for ({lat:.2f}, {lon:.2f})")
    return estimate_physrisk(lat, lon)

"""
psha_client.py — USGS ASCE7-22 지진 위험 API 호출

USGS Unified Hazard Tool API를 통해 지진 위험값(PGA) 조회.
지원 지역: 미국 (48개 주) + 알래스카
"""

import logging
import math

logger = logging.getLogger(__name__)

# 지진 활동 고위험 지역 (근사값)
EQ_HAZARD_REGIONS = [
    # (lat_min, lat_max, lon_min, lon_max, pga_approx, description)
    (30, 42, 125, 135, 0.4, "일본 태평양 연안"),
    (33, 40, 126, 132, 0.3, "한반도 동부"),
    (28, 38, 100, 110, 0.25, "중국 서부"),
    (30, 40, 65, 80, 0.35, "중앙아시아"),
    (36, 42, 25, 45, 0.40, "터키/중동"),
    (35, 42, -125, -115, 0.6, "미국 서부"),
    (37, 40, -123, -119, 0.7, "샌프란시스코"),
    (33, 35, -120, -116, 0.65, "로스앤젤레스"),
    (-10, 15, 95, 115, 0.30, "수마트라/자바"),
    (10, 20, 120, 128, 0.35, "필리핀"),
    (-40, -30, -75, -65, 0.35, "칠레"),
]

def estimate_pga(lat: float, lon: float) -> float:
    """
    위도/경도 기반 PGA(최대지반가속도, g) 근사 추정.
    환태평양 조산대, 알프스-히말라야 지진대 고려.
    """
    lon_norm = lon if lon <= 180 else lon - 360

    best_pga = 0.05  # 기본값 (저위험)

    for lat_min, lat_max, lon_min, lon_max, pga, _ in EQ_HAZARD_REGIONS:
        if lat_min <= lat <= lat_max and lon_min <= lon_norm <= lon_max:
            best_pga = max(best_pga, pga)

    # 환태평양 조산대 추가 보정
    # 태평양 연안 (동서 모두)
    if (lat_norm := abs(lat)) < 60:
        # 일본~필리핀~인도네시아 연안
        if 120 <= lon_norm <= 150 and 5 <= lat <= 45:
            best_pga = max(best_pga, 0.25)
        # 아메리카 서부 연안
        if -120 <= lon_norm <= -65 and 10 <= lat <= 60:
            best_pga = max(best_pga, 0.20)

    return round(best_pga, 3)


def pga_to_risk_score(pga: float) -> float:
    """PGA → 0-100 위험 스코어 변환."""
    if pga <= 0.05:
        return 5.0
    elif pga <= 0.10:
        return 15.0
    elif pga <= 0.20:
        return 35.0
    elif pga <= 0.40:
        return 60.0
    elif pga <= 0.60:
        return 80.0
    else:
        return 95.0


async def fetch_earthquake_risk(lat: float, lon: float) -> dict:
    """
    지진 위험 조회. USGS API 또는 근사값 반환.

    Returns:
        {"earthquake_risk": 0-100, "pga_g": float}
    """
    # TODO: USGS API 연결
    # https://earthquake.usgs.gov/ws/designmaps/asce7-22.json?latitude=...
    # 현재는 근사값 사용

    pga = estimate_pga(lat, lon)
    score = pga_to_risk_score(pga)
    logger.info(f"Earthquake estimate ({lat:.2f}, {lon:.2f}): PGA={pga}g, score={score}")

    return {
        "earthquake_risk": score,
        "pga_g": pga,
    }

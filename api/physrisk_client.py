"""
physrisk_client.py — OS-Climate PhyRisk 근사 추정 (전구 커버리지)

실제 OS-Climate API 접근 불가 → CMIP6 그리드 기반 물리 모델 근사값 사용.
CMIP6 값 있으면 기상 연동 추정, 없으면 위도/경도 지역 통계 폴백.
"""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# 열대성 저기압 위험 지역
CYCLONE_PRONE_REGIONS = [
    (5,  25,  100, 180, 70),   # 서태평양 태풍
    (5,  25,   60, 100, 50),   # 인도양 북부
    (5,  30, -100, -60, 60),   # 대서양 허리케인
    (5,  30, -120, -90, 55),   # 동태평양 허리케인
    (-30, -5,  20,  80, 40),   # 남인도양
    (-30, -5, 100, 180, 45),   # 남태평양
]

# 산사태 고위험 지형대 (급경사 + 강수 지역)
LANDSLIDE_PRONE_REGIONS = [
    (25, 40, 100, 125, 60),   # 동아시아 산악
    (10, 30,  70, 100, 55),   # 히말라야 전방
    (5,  25, 100, 125, 50),   # 동남아 산악
    (-5, 15, -80, -65, 45),   # 안데스 북부
]


def _in_region(lat: float, lon: float, regions: list) -> Optional[float]:
    for lat_min, lat_max, lon_min, lon_max, risk in regions:
        lon_check = lon if lon <= 180 else lon - 360
        if lat_min <= lat <= lat_max and lon_min <= lon_check <= lon_max:
            return float(risk)
    return None


# ── CMIP6 기반 물리 추정 ─────────────────────────────────────────────────────

def _heat_stress_from_cmip6(tasmax: float, tas: float, lat: float) -> float:
    """
    열 스트레스 점수 (0-100).
    tasmax 35°C 이상부터 급격히 증가, 위도 보정 적용.
    """
    # 기준: tasmax 20°C=0, 35°C=50, 42°C=85, 48°C=100
    if tasmax <= 20:
        score = max(0, (tasmax - 10) * 1.5)
    elif tasmax <= 35:
        score = (tasmax - 20) / 15 * 50
    elif tasmax <= 42:
        score = 50 + (tasmax - 35) / 7 * 35
    else:
        score = min(100, 85 + (tasmax - 42) / 6 * 15)
    # 습도 대리: 저위도는 동일 온도에서 체감 더 높음
    humid_boost = max(0, (20 - abs(lat)) / 20 * 10)
    return round(min(100, score + humid_boost), 1)


def _drought_risk_from_cmip6(pr: float, tasmax: float, lat: float) -> float:
    """
    가뭄 위험 점수 (0-100).
    강수량이 적고 기온이 높을수록 위험 증가.
    """
    # pr(mm/day): 0=극심, 2=건조, 5=적정, 10=습윤
    if pr <= 0.3:
        pr_score = 90
    elif pr <= 2:
        pr_score = 70 - (pr - 0.3) / 1.7 * 15
    elif pr <= 5:
        pr_score = 55 - (pr - 2) / 3 * 30
    elif pr <= 10:
        pr_score = 25 - (pr - 5) / 5 * 15
    else:
        pr_score = max(0, 10 - (pr - 10) / 10 * 10)
    # 고온 가중치
    temp_boost = max(0, (tasmax - 30) / 10 * 15)
    return round(min(100, pr_score + temp_boost), 1)


def _flood_risk_from_cmip6(pr: float, lat: float, lon: float) -> float:
    """
    홍수 위험 점수 (0-100).
    강수량이 많을수록 위험 증가, 지역 특성 반영.
    """
    # pr(mm/day): 0=무위험, 5=낮음, 10=중간, 20=높음
    if pr <= 1:
        pr_score = 10
    elif pr <= 5:
        pr_score = 10 + (pr - 1) / 4 * 20
    elif pr <= 10:
        pr_score = 30 + (pr - 5) / 5 * 25
    elif pr <= 20:
        pr_score = 55 + (pr - 10) / 10 * 25
    else:
        pr_score = min(100, 80 + (pr - 20) / 20 * 20)
    # 아시아 몬순 가중
    lon_check = lon if lon <= 180 else lon - 360
    if 5 <= lat <= 40 and 60 <= lon_check <= 150:
        pr_score = min(100, pr_score * 1.15)
    return round(pr_score, 1)


def _wildfire_risk_from_cmip6(tasmax: float, pr: float, lat: float) -> float:
    """
    산불 위험 점수 (0-100).
    건조+고온 조합이 핵심.
    """
    drought = _drought_risk_from_cmip6(pr, tasmax, lat)
    heat_factor = max(0, (tasmax - 25) / 15)  # 25°C=0, 40°C=1
    score = drought * 0.6 + heat_factor * 40
    return round(min(100, score), 1)


def _water_stress_from_cmip6(pr: float, tasmax: float, lat: float) -> float:
    """수자원 스트레스 (증발 수요 vs 공급)."""
    # 잠재 증발산 proxy: 고온 지역에서 수요 증가
    pet_proxy = max(0, (tasmax - 15) / 25 * 5)   # mm/day 단위 근사
    supply_demand_ratio = max(0.01, pr / max(0.1, pet_proxy))
    if supply_demand_ratio >= 3:
        score = 10
    elif supply_demand_ratio >= 1.5:
        score = 10 + (3 - supply_demand_ratio) / 1.5 * 25
    elif supply_demand_ratio >= 0.5:
        score = 35 + (1.5 - supply_demand_ratio) / 1.0 * 35
    else:
        score = 70 + (0.5 - supply_demand_ratio) / 0.5 * 30
    return round(min(100, score), 1)


def estimate_physrisk_cmip6(
    lat: float, lon: float,
    tasmax: Optional[float] = None,
    tasmin: Optional[float] = None,
    tas: Optional[float] = None,
    pr: Optional[float] = None,
) -> dict:
    """
    CMIP6 기상 변수 + 위치 정보 기반 물리적 위험 추정.
    CMIP6 값이 없으면 위도/경도 기반 통계 폴백.
    """
    has_cmip6 = all(v is not None for v in [tasmax, tasmin, tas, pr])

    # ── 위치 기반 고정 지수 ────────────────────────────────────────────────
    cyclone = _in_region(lat, lon, CYCLONE_PRONE_REGIONS) or 10
    is_coastal = True  # 보수적 처리
    abs_lat = abs(lat)

    if has_cmip6:
        heat    = _heat_stress_from_cmip6(tasmax, tas, lat)
        drought = _drought_risk_from_cmip6(pr, tasmax, lat)
        flood   = _flood_risk_from_cmip6(pr, lat, lon)
        wildfire= _wildfire_risk_from_cmip6(tasmax, pr, lat)
        water   = _water_stress_from_cmip6(pr, tasmax, lat)
    else:
        # 위도 통계 폴백
        heat    = max(10, 80 - abs_lat * 1.6)
        drought = 55 if 15 <= abs_lat <= 35 else 30
        flood   = _in_region(lat, lon, [
            (20, 35, 105, 125, 65), (20, 30, 85, 100, 70),
            (10, 25, 100, 125, 60), (30, 45, 115, 135, 50)]) or 30
        wildfire= max(0, drought - 10)
        water   = 60 if 15 <= abs_lat <= 35 else 40

    # 해수면 상승: 위도 기반 (CMIP6 변수 없음)
    if abs_lat < 20:
        slr = 65
    elif abs_lat < 40:
        slr = 45
    else:
        slr = 25

    landslide = _in_region(lat, lon, LANDSLIDE_PRONE_REGIONS) or max(0, flood * 0.5)

    return {
        "flood_risk":       round(flood, 1),
        "drought_risk":     round(drought, 1),
        "heat_stress":      round(heat, 1),
        "extreme_heat_35c": round(heat * 0.55, 1),
        "work_loss_high":   round(heat * 0.85, 1),
        "work_loss_medium": round(heat * 0.55, 1),
        "heat_degree_days": round(heat * 0.90, 1),
        "water_stress":     round(water, 1),
        "water_depletion":  round(water * 0.70, 1),
        "cyclone_risk":     round(cyclone, 1),
        "wildfire_risk":    round(wildfire, 1),
        "sea_level_rise":   round(slr, 1),
        "storm_surge":      round(cyclone * 0.8, 1),
        "landslide_risk":   round(min(80, landslide), 1),
        "coastal_flood":    round(slr * 0.9, 1),
        "pluvial_flood":    round(flood * 0.7, 1),
        "river_flood":      round(flood * 0.85, 1),
    }


# 하위 호환 alias
def estimate_physrisk(lat: float, lon: float) -> dict:
    return estimate_physrisk_cmip6(lat, lon)


async def fetch_physrisk(
    lat: float, lon: float,
    tasmax: Optional[float] = None,
    tasmin: Optional[float] = None,
    tas: Optional[float] = None,
    pr: Optional[float] = None,
) -> dict:
    """PhyRisk 근사 추정 (비동기 래퍼)."""
    logger.info(f"PhyRisk estimate for ({lat:.2f}, {lon:.2f}), cmip6={'yes' if tasmax else 'no'}")
    return estimate_physrisk_cmip6(lat, lon, tasmax, tasmin, tas, pr)

"""
psha_client.py — 전구 지진위험 추정

static_estimator의 GEM 29개 지진위험대 룩업테이블을 사용하여
earthquake_risk (0-100 점수) 반환.
"""

import logging
from static_estimator import _psha_at

logger = logging.getLogger(__name__)


def pga_to_risk_score(pga: float) -> float:
    """PGA (g) → 0-100 위험 점수."""
    if pga <= 0.05:   return 5.0
    elif pga <= 0.10: return 15.0
    elif pga <= 0.20: return 35.0
    elif pga <= 0.30: return 50.0
    elif pga <= 0.40: return 65.0
    elif pga <= 0.60: return 80.0
    else:             return 95.0


async def fetch_earthquake_risk(lat: float, lon: float) -> dict:
    """
    GEM 지진위험대 기반 지진 위험 추정.

    Returns:
        {"earthquake_risk": 0-100, "pga_g": float}
    """
    psha = _psha_at(lat, lon)
    pga = psha.get("psha_pga_475", 0.04)
    score = pga_to_risk_score(pga)
    logger.debug(f"EQ ({lat:.2f},{lon:.2f}): PGA={pga}g -> score={score}")
    return {"earthquake_risk": score, "pga_g": pga}

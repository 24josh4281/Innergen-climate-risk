"""
site_constants.py — 14개 OCI 사업장 좌표 및 메타데이터
"""

OCI_SITES = {
    "OCI_HQ_Seoul":     {"lat": 37.5649, "lon": 126.9793, "country": "KOR", "display": "OCI 본사 (서울)"},
    "OCI_Dream_Seoul":  {"lat": 37.5172, "lon": 126.9000, "country": "KOR", "display": "OCI드림 (서울)"},
    "OCI_RnD_Seongnam": {"lat": 37.3219, "lon": 127.1190, "country": "KOR", "display": "OCI R&D (성남)"},
    "Pohang_Plant":     {"lat": 36.0095, "lon": 129.3435, "country": "KOR", "display": "포항 공장"},
    "Gwangyang_Plant":  {"lat": 34.9393, "lon": 127.6961, "country": "KOR", "display": "광양 공장"},
    "Gunsan_Plant":     {"lat": 35.9700, "lon": 126.7114, "country": "KOR", "display": "군산 공장"},
    "Iksan_Plant":      {"lat": 35.9333, "lon": 127.0167, "country": "KOR", "display": "익산 공장"},
    "Saehan_Recycle":   {"lat": 35.9333, "lon": 127.0167, "country": "KOR", "display": "새한 리사이클"},
    "OCI_Shanghai":     {"lat": 31.2304, "lon": 121.4737, "country": "CHN", "display": "OCI 상해"},
    "MaSteel_OCI":      {"lat": 31.6839, "lon": 118.5127, "country": "CHN", "display": "마강 OCI"},
    "Shandong_OCI":     {"lat": 34.7979, "lon": 117.2571, "country": "CHN", "display": "산동 OCI"},
    "Jianyang_Carbon":  {"lat": 26.7587, "lon": 104.4734, "country": "CHN", "display": "건양 카본"},
    "OCI_Japan_Tokyo":  {"lat": 35.6762, "lon": 139.6503, "country": "JPN", "display": "OCI 도쿄"},
    "Philko_Makati":    {"lat": 14.5995, "lon": 120.9842, "country": "PHL", "display": "Philko 마카티"},
}

# 38개 기후 동인 메타데이터
DRIVER_META = {
    # CMIP6 기온/강수 계열 (7)
    "tasmax":   {"label": "최고기온",    "unit": "°C",     "source_type": "cmip6", "rag_thresholds": {"red": 38, "amber": 33}},
    "tasmin":   {"label": "최저기온",    "unit": "°C",     "source_type": "cmip6", "rag_thresholds": {"red": -15, "amber": -5, "inverse": True}},
    "tas":      {"label": "평균기온",    "unit": "°C",     "source_type": "cmip6", "rag_thresholds": {"red": 30, "amber": 25}},
    "pr":       {"label": "강수량",     "unit": "mm/day", "source_type": "cmip6", "rag_thresholds": {"red": 10, "amber": 6}},
    "prsn":     {"label": "강설량",     "unit": "mm/day", "source_type": "cmip6", "rag_thresholds": {"red": 5, "amber": 2}},
    "sfcWind":  {"label": "지표풍속",   "unit": "m/s",    "source_type": "cmip6", "rag_thresholds": {"red": 10, "amber": 7}},
    "evspsbl":  {"label": "증발산",     "unit": "mm/day", "source_type": "cmip6", "rag_thresholds": {"red": 5, "amber": 3}},
    # PhyRisk 동인들 (물리적 위험)
    "flood_risk":      {"label": "홍수 위험",        "unit": "score", "source_type": "physrisk"},
    "drought_risk":    {"label": "가뭄 위험",        "unit": "score", "source_type": "physrisk"},
    "heat_stress":     {"label": "열 스트레스",      "unit": "score", "source_type": "physrisk"},
    "extreme_heat_35c":{"label": "35°C 초과일수",    "unit": "score", "source_type": "physrisk"},
    "work_loss_high":  {"label": "고강도 노동손실",  "unit": "score", "source_type": "physrisk"},
    "work_loss_medium":{"label": "중강도 노동손실",  "unit": "score", "source_type": "physrisk"},
    "heat_degree_days":{"label": "열 도일 (CDD)",    "unit": "score", "source_type": "physrisk"},
    "water_stress":    {"label": "수자원 스트레스",  "unit": "score", "source_type": "physrisk"},
    "water_depletion": {"label": "물 고갈 지수",     "unit": "score", "source_type": "physrisk"},
    "cyclone_risk":    {"label": "사이클론 위험",    "unit": "score", "source_type": "physrisk"},
    "wildfire_risk":   {"label": "산불 위험",        "unit": "score", "source_type": "physrisk"},
    "sea_level_rise":  {"label": "해수면 상승",      "unit": "m",     "source_type": "physrisk"},
    "storm_surge":     {"label": "폭풍 해일",        "unit": "score", "source_type": "physrisk"},
    "earthquake_risk": {"label": "지진 위험",        "unit": "score", "source_type": "psha"},
    "landslide_risk":  {"label": "산사태 위험",      "unit": "score", "source_type": "physrisk"},
    "coastal_flood":   {"label": "해안 침수",        "unit": "score", "source_type": "physrisk"},
    "pluvial_flood":   {"label": "도시 홍수",        "unit": "score", "source_type": "physrisk"},
    "river_flood":     {"label": "하천 홍수",        "unit": "score", "source_type": "physrisk"},
}

# CMIP6 변수 단위 변환 (K → °C, kg/m²/s → mm/day)
def convert_cmip6_value(var: str, raw_val: float) -> float:
    if raw_val is None:
        return None
    if var in ("tasmax", "tasmin", "tas"):
        # K to °C
        if raw_val > 200:
            return round(raw_val - 273.15, 2)
        return round(raw_val, 2)
    elif var in ("pr", "prsn", "evspsbl"):
        # kg/m²/s → mm/day
        return round(raw_val * 86400, 3)
    return round(raw_val, 4)

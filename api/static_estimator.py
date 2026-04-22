"""
static_estimator.py — 전구 정적 기후 지수 추정

Aqueduct 4.0, IBTrACS, GEM PSHA를 임의 좌표에서 추정.
- IBTrACS: WP 1° 격자 기반 실측 빈도/풍속 (1980-2023)
- Aqueduct: 기후대/유역 기반 수자원 스트레스 추정
- PSHA:     GEM 세계 지진위험대 기반 PGA 추정

반환: {variable: value}  — static_sites.csv 동일 형식
"""

from __future__ import annotations

import math
import os
import functools
from typing import Optional

import numpy as np
import pandas as pd

DATA_ROOT = "c:/Users/24jos/climada/data"

# ── IBTrACS 1° 격자 (WP 분지, 1980-2023) ────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _load_ibtracs_grid() -> pd.DataFrame:
    path = os.path.join(DATA_ROOT, "ibtracs", "ibtracs_WP_grid_1deg.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["lat", "lon", "annual_freq", "max_wind_kt"])
    return pd.read_csv(path)


def _ibtracs_at(lat: float, lon: float) -> dict:
    """
    가장 가까운 IBTrACS 1° 격자점 값 반환.
    WP 분지(서태평양) 커버리지: 0-69°N, 56-267°E.
    커버리지 밖이면 지역 통계 보정값 사용.
    """
    grid = _load_ibtracs_grid()
    if grid.empty:
        return _ibtracs_regional(lat, lon)

    # 정규화 경도 (0-360)
    lon360 = lon % 360

    lat_bin = int(math.floor(lat))
    lon_bin = int(math.floor(lon360))

    # 가장 가까운 격자점 (3도 반경)
    sub = grid[
        (grid["lat"] >= lat_bin - 3) & (grid["lat"] <= lat_bin + 3) &
        (grid["lon"] >= lon_bin - 3) & (grid["lon"] <= lon_bin + 3)
    ]
    if sub.empty:
        return _ibtracs_regional(lat, lon)

    # 거리 가중 평균 (IDW)
    dlat = sub["lat"].values - lat
    dlon = sub["lon"].values - lon360
    dist2 = dlat**2 + dlon**2 + 1e-6
    w = 1.0 / dist2

    annual_freq  = float(np.average(sub["annual_freq"].values,  weights=w))
    max_wind_kt  = float(np.average(sub["max_wind_kt"].fillna(0).values, weights=w))
    # Cat3+ (96kt+) 건수: max_wind 기반 근사
    cat3_count = round(annual_freq * 44 * max(0, (max_wind_kt - 64) / 96), 1)

    return {
        "tc_annual_freq": round(annual_freq, 3),
        "tc_max_wind_kt": round(max_wind_kt, 1),
        "tc_cat3_count":  round(cat3_count, 1),
    }


def _ibtracs_regional(lat: float, lon: float) -> dict:
    """
    WP 격자 밖 지역의 태풍/사이클론 통계 (분지 기반 문헌값).
    출처: WMO/NOAA 분지별 연평균 발생빈도
    """
    lon360 = lon % 360
    abs_lat = abs(lat)

    BASINS = [
        # lat_min, lat_max, lon_min(0-360), lon_max, freq, max_wind
        (5,  35, 260, 360,  14, 95, "NA"),   # 북대서양 허리케인
        (5,  25, 180, 260,  15, 95, "EP"),   # 동태평양 허리케인
        (0,  25,  30,  90,   5, 85, "NI"),   # 북인도양 사이클론
        (-35, -5,  30, 100,  9, 80, "SI"),   # 남인도양 사이클론
        (-35, -5, 100, 180, 10, 85, "SP"),   # 남태평양 사이클론
    ]
    for lat_min, lat_max, lon_min, lon_max, freq, wind, name in BASINS:
        if lat_min <= lat <= lat_max and lon_min <= lon360 <= lon_max:
            # 지역 내 균등 분포 근사
            return {
                "tc_annual_freq": round(freq / 40, 3),  # 40도 경도 당 1개
                "tc_max_wind_kt": float(wind),
                "tc_cat3_count":  round(freq / 40 * 0.3 * 44, 1),
            }
    # 열대성저기압 밖 (위도 35+ 또는 대륙 내부)
    return {"tc_annual_freq": 0.0, "tc_max_wind_kt": 0.0, "tc_cat3_count": 0.0}


# ── Aqueduct 4.0 수자원 스트레스 추정 ────────────────────────────────────────
# WRI Aqueduct 4.0 지역 기준값 (기후대 + 인구밀도 기반 문헌 추정)
# Scale: 0 (Low) ~ 5 (Extremely High)

AQ_ANCHOR_SITES = [
    # (lat, lon, bws, rfr, cfr, drr, iav, bws_2050)
    # East Asia / OCI sites
    (37.56, 126.98, 0.76, 0.42, 0.0, 0.20, 0.38, 0.91),   # 서울
    (36.01, 129.34, 0.68, 0.35, 0.0, 0.18, 0.35, 0.82),   # 포항
    (34.94, 127.70, 0.62, 0.48, 0.0, 0.15, 0.32, 0.74),   # 광양
    (31.23, 121.47, 1.85, 1.20, 0.3, 0.80, 0.95, 2.20),   # 상해
    (31.68, 118.51, 1.40, 0.90, 0.1, 0.55, 0.80, 1.70),   # 마강
    (34.80, 117.26, 2.50, 0.70, 0.0, 1.20, 1.10, 3.00),   # 산동
    (26.76, 104.47, 1.20, 1.80, 0.0, 0.80, 1.40, 1.50),   # 건양
    (35.68, 139.65, 0.55, 0.28, 0.1, 0.10, 0.30, 0.65),   # 도쿄
    (14.60, 120.98, 0.45, 2.10, 1.5, 0.30, 1.80, 0.55),   # 마카티
    # Southeast Asia
    ( 1.35, 103.82, 0.35, 1.50, 2.0, 0.10, 1.50, 0.40),   # 싱가포르
    (13.75, 100.52, 1.50, 2.50, 0.5, 0.90, 1.80, 1.90),   # 방콕
    (-6.21, 106.85, 1.20, 3.50, 1.0, 0.60, 2.00, 1.60),   # 자카르타
    # South Asia
    (28.61,  77.21, 3.80, 1.10, 0.0, 2.50, 2.20, 4.50),   # 뉴델리 (극심)
    (19.08,  72.88, 3.20, 1.80, 0.5, 1.80, 1.90, 3.90),   # 뭄바이
    (23.73,  90.39, 1.40, 4.50, 1.5, 0.80, 2.50, 1.80),   # 다카 (홍수↑)
    # Middle East
    (24.47,  54.37, 4.80, 0.10, 0.2, 4.50, 1.20, 5.00),   # 아부다비 (극심)
    (25.20,  55.27, 4.90, 0.10, 0.2, 4.60, 1.10, 5.00),   # 두바이 (극심)
    (33.34,  44.40, 3.50, 0.80, 0.0, 3.00, 1.80, 4.20),   # 바그다드
    (35.69,  51.42, 3.80, 0.60, 0.0, 3.20, 1.50, 4.40),   # 테헤란
    # Africa
    (30.06,  31.25, 4.50, 0.20, 0.0, 4.20, 1.30, 5.00),   # 카이로 (극심)
    (-1.29,  36.82, 1.80, 1.20, 0.0, 1.20, 2.10, 2.30),   # 나이로비
    ( 6.52,   3.38, 2.10, 2.80, 0.5, 1.20, 2.00, 2.60),   # 라고스
    (-25.75,  28.19, 1.80, 0.60, 0.0, 1.50, 1.40, 2.20),  # 요하네스버그
    # Europe
    (48.85,   2.35, 0.90, 0.50, 0.1, 0.25, 0.45, 1.10),   # 파리
    (51.50,  -0.12, 0.65, 0.40, 0.2, 0.15, 0.35, 0.80),   # 런던
    (52.52,  13.40, 0.80, 0.45, 0.1, 0.20, 0.40, 1.00),   # 베를린
    (41.90,  12.50, 1.50, 0.55, 0.1, 0.90, 0.70, 1.90),   # 로마
    (40.42,  -3.70, 2.20, 0.35, 0.0, 1.60, 0.85, 2.80),   # 마드리드 (건조)
    # Americas
    (40.71, -74.01, 0.60, 0.80, 0.5, 0.15, 0.50, 0.75),   # 뉴욕
    (34.05, -118.2, 2.80, 0.20, 0.2, 2.20, 1.00, 3.30),   # LA (건조)
    (19.43,  -99.13,3.20, 0.90, 0.0, 2.50, 1.20, 3.80),   # 멕시코시티
    (-23.55, -46.63,1.80, 1.50, 0.2, 0.90, 1.30, 2.20),   # 상파울루
    (-34.61, -58.38,1.00, 0.70, 0.0, 0.50, 0.80, 1.20),   # 부에노스아이레스
    # Oceania
    (-33.87, 151.21, 1.20, 0.30, 0.3, 0.80, 0.90, 1.50),  # 시드니
    (-37.81, 144.96, 1.50, 0.25, 0.2, 1.00, 0.85, 1.90),  # 멜버른
    # Russia / Central Asia
    (55.75,  37.62, 0.45, 0.40, 0.0, 0.10, 0.35, 0.55),   # 모스크바
    (51.18,  71.45, 3.50, 0.30, 0.0, 2.80, 1.60, 4.20),   # 아스타나 (건조)
]
_AQ_ARR = np.array([[r[0], r[1]] for r in AQ_ANCHOR_SITES])
_AQ_VALS = np.array([[r[2], r[3], r[4], r[5], r[6], r[7]] for r in AQ_ANCHOR_SITES])
_AQ_VARS = ["aq_water_stress", "aq_river_flood", "aq_coastal_flood",
            "aq_drought", "aq_interann_var", "aq_water_stress_2050"]


def _aqueduct_at(lat: float, lon: float) -> dict:
    """
    IDW 보간 + 기후대 보정으로 Aqueduct 지수 추정.
    """
    # IDW (k=3 nearest anchors)
    dist2 = ((_AQ_ARR[:, 0] - lat) ** 2 + (_AQ_ARR[:, 1] - lon) ** 2) + 1e-6
    k = min(3, len(dist2))
    idx = np.argpartition(dist2, k)[:k]
    w = 1.0 / dist2[idx]
    vals = np.average(_AQ_VALS[idx], weights=w, axis=0)

    # 기후대 보정
    abs_lat = abs(lat)
    lon360 = lon % 360

    # 건조 기후대 (아열대 고압대, 중앙아시아, 중동 등) → 수자원 스트레스 증가
    if 15 <= abs_lat <= 35 and lon360 in range(0, 80):  # 북아프리카/중동
        vals[0] = min(5.0, vals[0] * 2.5)   # bws
        vals[3] = min(5.0, vals[3] * 2.0)   # drr
        vals[5] = min(5.0, vals[5] * 2.5)   # bws_2050
    elif 35 <= abs_lat <= 50 and 55 <= lon360 <= 100:   # 중앙아시아
        vals[0] = min(5.0, vals[0] * 2.0)
        vals[3] = min(5.0, vals[3] * 1.8)
    # 열대우림 (홍수 위험 높음, 물 스트레스 낮음)
    elif abs_lat < 10 and 90 <= lon360 <= 180:
        vals[0] = max(0.1, vals[0] * 0.5)
        vals[1] = min(5.0, vals[1] * 1.5)   # rfr

    # 북유럽 / 캐나다 (낮은 스트레스)
    if abs_lat > 55:
        vals = vals * 0.4

    # 0-5 범위 클램프
    vals = np.clip(vals, 0.0, 5.0)

    return {var: round(float(v), 3) for var, v in zip(_AQ_VARS, vals)}


# ── GEM PSHA 전구 지진위험대 ────────────────────────────────────────────────
# 출처: GEM Global Earthquake Model (openquake.org), USGS SEISMIC HAZARD
# PGA 475yr 재현주기 (g), 암반 기준 (Vs30≈760m/s)

# 주요 지진위험대 (lat_min, lat_max, lon_min, lon_max, PGA_475, PGA_2475)
# 다중 구간이 겹칠 경우 첫 번째 매칭 사용
PSHA_ZONES = [
    # 한반도
    (33.0, 38.6, 124.0, 131.0, 0.11, 0.22),
    # 일본 (높은 위험)
    (30.0, 46.0, 129.0, 146.0, 0.40, 0.80),
    # 대만
    (21.5, 26.0, 119.5, 122.5, 0.50, 1.00),
    # 필리핀
    ( 4.5, 21.0, 116.0, 127.0, 0.35, 0.70),
    # 중국 동부 (낮음)
    (25.0, 40.0, 110.0, 125.0, 0.10, 0.20),
    # 중국 서부/쓰촨 (높음)
    (25.0, 38.0,  95.0, 112.0, 0.30, 0.60),
    # 중국 신장/중앙아시아
    (35.0, 48.0,  70.0,  96.0, 0.25, 0.50),
    # 인도네시아/말레이
    (-8.0, 10.0,  95.0, 141.0, 0.45, 0.90),
    # 남아시아 (인도 북부)
    (25.0, 36.0,  68.0,  85.0, 0.25, 0.50),
    # 터키
    (36.0, 42.5,  26.0,  45.0, 0.35, 0.70),
    # 이란/이라크
    (29.0, 40.0,  44.0,  63.0, 0.30, 0.60),
    # 지중해 (이탈리아/그리스)
    (35.5, 47.5,  11.0,  22.0, 0.25, 0.50),
    # 알프스 (스위스/오스트리아)
    (45.8, 48.5,   5.9,  17.2, 0.12, 0.25),
    # 이베리아 (스페인/포르투갈)
    (36.0, 44.0,  -9.5,   3.3, 0.15, 0.30),
    # 루마니아 (카르파티아)
    (43.5, 48.0,  20.0,  30.6, 0.22, 0.45),
    # 캘리포니아
    (32.0, 42.0, -124.5, -114.0, 0.55, 1.10),
    # 미국 태평양 북서부
    (42.0, 50.0, -124.5, -116.0, 0.35, 0.70),
    # 미국 중남부/뉴마드리드
    (35.0, 40.0,  -92.0,  -85.0, 0.25, 0.50),
    # 미국 알래스카
    (54.0, 72.0, -170.0, -130.0, 0.60, 1.20),
    # 멕시코 (서부)
    (15.0, 30.0, -118.0,  -95.0, 0.40, 0.80),
    # 칠레
    (-55.0, -18.0, -76.0, -65.0, 0.50, 1.00),
    # 카리브
    (10.0, 22.0,  -85.0,  -59.0, 0.35, 0.70),
    # 동아프리카 열곡대
    (-15.0, 15.0,  28.0,  42.0, 0.20, 0.40),
    # 북아프리카/마그레브
    (30.0, 37.5,  -2.0,  37.0, 0.18, 0.36),
    # 뉴질랜드
    (-47.0, -34.0, 166.0, 178.0, 0.50, 1.00),
    # 오세아니아 (PNG/솔로몬)
    (-12.0, 0.0, 140.0, 162.0, 0.45, 0.90),
    # 호주 서부 (낮음)
    (-35.0, -20.0, 113.0, 130.0, 0.08, 0.16),
    # 호주 동부 (매우 낮음)
    (-38.0, -25.0, 140.0, 154.0, 0.05, 0.10),
]

# 안정 대륙부 기본값 (낮은 지진위험)
PSHA_DEFAULT = (0.04, 0.08)


def _psha_at(lat: float, lon: float) -> dict:
    lon360 = lon if -180 <= lon <= 180 else ((lon + 180) % 360) - 180
    for lat_min, lat_max, lon_min, lon_max, pga475, pga2475 in PSHA_ZONES:
        if lat_min <= lat <= lat_max and lon_min <= lon360 <= lon_max:
            return {
                "psha_pga_475":  round(pga475,  3),
                "psha_pga_2475": round(pga2475, 3),
            }
    return {
        "psha_pga_475":  round(PSHA_DEFAULT[0], 3),
        "psha_pga_2475": round(PSHA_DEFAULT[1], 3),
    }


# ── 공개 인터페이스 ────────────────────────────────────────────────────────────

def query_static(lat: float, lon: float) -> dict:
    """
    전구 임의 좌표 → {variable: value} 정적 기후 지수 추정.

    반환 변수:
      IBTrACS:  tc_annual_freq, tc_max_wind_kt, tc_cat3_count
      Aqueduct: aq_water_stress, aq_river_flood, aq_coastal_flood,
                aq_drought, aq_interann_var, aq_water_stress_2050
                aq_scale (스케일 명시: 5 = WRI Aqueduct 4.0 기준 0-5)
      PSHA:     psha_pga_475, psha_pga_2475
    """
    result = {}
    result.update(_ibtracs_at(lat, lon))
    aq = _aqueduct_at(lat, lon)
    result.update(aq)
    # Aqueduct 스케일 명시 (0-5 WRI 척도, 사용자 혼동 방지)
    if aq:
        result["aq_scale"] = 5
    result.update(_psha_at(lat, lon))
    return result

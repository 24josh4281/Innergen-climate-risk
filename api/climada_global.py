"""
climada_global.py — CLIMADA HDF5 직접 조회 (전구 커버리지)

h5py 기반으로 TC/홍수/산불/지진 HDF5 파일에서 가장 가까운 격자점 EAL 추출.
지진: ISO 3166-1 숫자 코드 기반 40개국 커버리지

반환값: {TC_EAL, Flood_EAL, Wildfire_EAL, EQ_EAL}  (normalized 0-100 score)
"""

from __future__ import annotations

import math
import os
import glob
import logging
from typing import Optional

import numpy as np
import scipy.sparse as sp
import h5py

logger = logging.getLogger(__name__)

HAZARD_ROOT = "c:/Users/24jos/climada/data/hazard"

# ── 국가 경계 박스 (lat_min, lat_max, lon_min, lon_max, iso3) ────────────────
COUNTRY_BOXES = [
    (33.0, 38.6,  124.6, 130.9, "KOR"),
    (18.0, 54.0,   73.0, 135.0, "CHN"),
    (30.0, 46.0,  129.0, 146.0, "JPN"),
    ( 4.5, 21.0,  116.0, 127.0, "PHL"),
    (21.5, 26.0,  119.5, 122.5, "TWN"),
    (15.0, 33.0,  -118.0, -86.0, "MEX"),
    (24.0, 50.0,  -125.0,  -66.0, "USA"),
    (10.0, 44.0,   -8.0,   3.3,  "ESP"),
    (41.0, 51.5,   -5.5,   9.7,  "FRA"),
    (35.5, 47.5,    6.0,  15.6,  "ITA"),
    (47.5, 55.5,    5.9,  15.0,  "DEU"),
    (49.5, 61.0,   -8.2,   2.0,  "GBR"),
    (46.4, 49.0,   16.8,  22.9,  "HUN"),
    (46.4, 49.0,    9.5,  17.1,  "AUT"),
    (49.5, 51.5,    2.5,   6.4,  "BEL"),
    (48.6, 51.1,   12.1,  18.8,  "CZE"),
    (-44.0, -10.0, 112.0, 154.0, "AUS"),
    (45.0, 60.0,  -141.0, -52.0, "CAN"),
    (36.0, 42.5,   26.0,  45.0,  "TUR"),
    (41.0, 44.2,   22.4,  28.6,  "BGR"),
    (34.8, 41.7,   19.7,  28.2,  "GRC"),
    (42.0, 46.6,   13.4,  19.7,  "HRV"),
    (32.7, 42.1,  -31.3,  -6.3,  "PRT"),
    (43.5, 48.2,   20.0,  29.7,  "ROU"),
    (42.2, 46.2,   18.9,  23.0,  "SRB"),
    (45.8, 47.9,    5.9,  10.5,  "CHE"),
    (49.0, 54.8,   14.2,  24.1,  "POL"),
    (49.5, 51.5,    3.3,   7.2,  "BEL"),
    (54.6, 57.7,    8.1,  15.1,  "DNK"),
    (55.4, 69.0,   11.1,  24.1,  "SWE"),
    (59.8, 70.0,   20.7,  31.5,  "FIN"),
    (39.7, 42.6,   19.3,  21.0,  "ALB"),
    (42.5, 46.5,   13.5,  19.4,  "BIH"),
    (42.6, 45.2,   15.7,  19.6,  "HRV"),  # overlap HRV
    (41.9, 43.5,   18.5,  20.3,  "MNE"),
    (40.9, 42.3,   20.5,  23.0,  "MKD"),
    (47.8, 49.6,   16.9,  22.5,  "SVK"),
    (45.5, 46.8,   13.4,  16.5,  "SVN"),
    (18.0, 20.1,  -72.0, -65.0,  "HTI"),  # Haiti + Dominican Rep
    (-54.4, 80.7,  -9.1,  33.6,  "NOR"),  # Norway inc. overseas
]

# ISO-3 → ISO numeric (지진 파일 ID)
ISO3_TO_NUM = {
    "KOR": 410, "CHN": 156, "JPN": 392, "PHL": 608, "TWN": 158,
    "MEX": 484, "USA": 840, "GBR": 826, "FRA": 250, "DEU": 276,
    "ITA": 380, "ESP": 724, "PRT": 620, "GRC": 300, "TUR": 792,
    "ROU": 642, "SRB": 688, "HRV": 191, "BGR": 100, "HUN": 348,
    "AUT": 40,  "CHE": 756, "CZE": 203, "POL": 616, "BEL": 56,
    "DNK": 208, "SWE": 752, "FIN": 246, "NOR": 578, "ALB": 8,
    "BIH": 70,  "MNE": 499, "MKD": 807, "SVK": 703, "SVN": 705,
    "HTI": 332,
}


def _iso3_from_latlon(lat: float, lon: float) -> Optional[str]:
    """위도/경도 → ISO-3 국가 코드 근사."""
    for lat_min, lat_max, lon_min, lon_max, iso in COUNTRY_BOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return iso
    return None


def _find_hdf5(subdir_pattern: str) -> Optional[str]:
    """hazard 루트에서 glob 패턴으로 첫 번째 HDF5 파일 경로 반환."""
    matches = glob.glob(os.path.join(HAZARD_ROOT, subdir_pattern, "**", "*.hdf5"),
                        recursive=True)
    if matches:
        return sorted(matches)[0]
    return None


def _nearest_centroid_idx(lats: np.ndarray, lons: np.ndarray,
                           lat: float, lon: float) -> int:
    """Haversine 거리 최소 centroid 인덱스."""
    dlat = np.radians(lats - lat)
    dlon = np.radians(lons - lon)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(math.radians(lat)) * np.cos(np.radians(lats)) * np.sin(dlon / 2) ** 2)
    return int(np.argmin(a))


def _eal_at(hdf5_path: str, lat: float, lon: float,
             max_dist_deg: float = 5.0) -> Optional[float]:
    """HDF5에서 가장 가까운 centroid의 EAL 반환. 오류 또는 거리 초과 시 None."""
    try:
        with h5py.File(hdf5_path, "r") as f:
            lats = f["centroids"]["lat"][:]
            lons = f["centroids"]["lon"][:]
            freq = f["frequency"][:]
            data    = f["intensity"]["data"][:]
            indices = f["intensity"]["indices"][:]
            indptr  = f["intensity"]["indptr"][:]
        n_events = len(freq)
        n_cen    = len(lats)
        mat = sp.csr_matrix((data, indices, indptr), shape=(n_events, n_cen))
        eal_vec = np.array(mat.T.dot(freq))
        idx = _nearest_centroid_idx(lats, lons, lat, lon)
        dist_deg = math.sqrt((lats[idx] - lat) ** 2 + (lons[idx] - lon) ** 2)
        if dist_deg > max_dist_deg:
            return None
        return float(eal_vec[idx])
    except Exception as e:
        logger.debug(f"HDF5 read error {hdf5_path}: {e}")
        return None


# ── EAL 정규화 기준값 ────────────────────────────────────────────────────────
# TC: m/s, Flood: m, Wildfire: K, EQ: MMI

TC_NORM = {
    "KOR": 30, "CHN": 35, "JPN": 35, "PHL": 50, "TWN": 45,
    "MEX": 40, "USA": 40, "default": 40,
}
FLOOD_NORM = {
    "KOR": 0.5, "CHN": 0.8, "JPN": 0.6, "PHL": 1.0, "TWN": 0.8,
    "default": 0.6,
}
WILDFIRE_NORM = {
    "KOR": 300, "CHN": 400, "JPN": 250, "PHL": 200,
    "AUS": 800, "USA": 600, "default": 350,
}
# EQ MMI EAL: JPN이 가장 높음 (~30). 전 세계 기준 30을 상한으로 사용
EQ_MMI_MAX = 30.0


def _normalize(eal: Optional[float], norm_map: dict, iso: str) -> Optional[float]:
    if eal is None:
        return None
    ref = norm_map.get(iso) or norm_map.get("default") or 1.0
    return round(min(100.0, eal / ref * 100), 2)


# ── 공개 인터페이스 ───────────────────────────────────────────────────────────

def query_climada(lat: float, lon: float) -> dict:
    """
    위도/경도 → CLIMADA HDF5 EAL 조회 (TC/홍수/산불/지진).

    Returns:
        {
          "TC_EAL":       float|None,   # 0-100 score
          "Flood_EAL":    float|None,
          "Wildfire_EAL": float|None,
          "EQ_EAL":       float|None,
          "iso3":         str|None,
          "source":       "CLIMADA_HDF5"
        }
    """
    iso = _iso3_from_latlon(lat, lon)
    result = {
        "TC_EAL": None, "Flood_EAL": None,
        "Wildfire_EAL": None, "EQ_EAL": None,
        "iso3": iso, "source": "CLIMADA_HDF5",
    }

    if iso is None:
        return result

    # ── TC ────────────────────────────────────────────────────────────────────
    tc_path = _find_hdf5(
        f"tropical_cyclone/tropical_cyclone_0synth_tracks_150arcsec_historical_{iso}_*")
    if tc_path:
        result["TC_EAL"] = _normalize(_eal_at(tc_path, lat, lon), TC_NORM, iso)

    # ── River Flood ───────────────────────────────────────────────────────────
    flood_path = _find_hdf5(f"river_flood/river_flood_150arcsec_hist_{iso}_*")
    if flood_path:
        result["Flood_EAL"] = _normalize(_eal_at(flood_path, lat, lon), FLOOD_NORM, iso)

    # ── Wildfire ──────────────────────────────────────────────────────────────
    wf_path = _find_hdf5(f"wildfire/wildfire_{iso}_*")
    if wf_path:
        result["Wildfire_EAL"] = _normalize(_eal_at(wf_path, lat, lon), WILDFIRE_NORM, iso)

    # ── Earthquake (ISO numeric ID) ───────────────────────────────────────────
    num_id = ISO3_TO_NUM.get(iso)
    if num_id is not None:
        eq_path = _find_hdf5(f"earthquake/earthquake_hist_above4_{num_id}")
        if eq_path:
            raw = _eal_at(eq_path, lat, lon, max_dist_deg=3.0)
            if raw is not None:
                result["EQ_EAL"] = round(min(100.0, raw / EQ_MMI_MAX * 100), 2)

    return result

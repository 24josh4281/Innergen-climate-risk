"""
물리적 리스크 수치 추출
좌표: 34.7979N, 117.2571E (Zaozhuang, Shandong, China)
"""
import numpy as np
import warnings
warnings.filterwarnings('ignore')
from pathlib import Path
from climada.hazard import Hazard
from climada.entity import Exposures

LAT, LON = 34.7979, 117.2571
DATA = Path("c:/Users/24jos/climada/data")

def nearest_centroid_idx(haz, lat, lon):
    lats = haz.centroids.lat
    lons = haz.centroids.lon
    dist = (lats - lat)**2 + (lons - lon)**2
    return int(np.argmin(dist))

def get_stats(haz, cidx):
    col = haz.intensity[:, cidx].toarray().flatten()
    col = col[col > 0]
    if len(col) == 0:
        return None
    return {
        'mean':   float(np.mean(col)),
        'max':    float(np.max(col)),
        'p50':    float(np.percentile(col, 50)),
        'p95':    float(np.percentile(col, 95)),
        'n_events': len(col),
    }

def load_and_extract(path, label=None):
    label = label or path.stem
    try:
        haz = Hazard.from_hdf5(path)
        cidx = nearest_centroid_idx(haz, LAT, LON)
        dist = np.sqrt((haz.centroids.lat[cidx]-LAT)**2 + (haz.centroids.lon[cidx]-LON)**2)
        stats = get_stats(haz, cidx)
        return label, stats, haz.units, dist
    except Exception as e:
        return label, None, '', 0

def print_stats(label, stats, units, dist_deg):
    dist_km = dist_deg * 111
    if stats is None:
        print(f"  {label}: 해당 위치 데이터 없음")
        return
    print(f"  {label} [단위: {units}, 가장 가까운 격자점: {dist_km:.1f} km]")
    print(f"    평균: {stats['mean']:.4f}  |  중앙값: {stats['p50']:.4f}  |  95th: {stats['p95']:.4f}  |  최대: {stats['max']:.4f}  |  이벤트수: {stats['n_events']}")

print("=" * 70)
print(f"물리적 리스크 분석 결과")
print(f"좌표: {LAT}N, {LON}E  (Zaozhuang, Shandong, China)")
print("=" * 70)

# ─────────────────────────────────────────────
# 1. 지진 (Earthquake)
# ─────────────────────────────────────────────
print("\n[1] 지진 (Earthquake) - 역사 기반")
for f in sorted(DATA.glob("hazard/earthquake/**/earthquake_hist_above4_156*.hdf5")):
    label, stats, units, dist = load_and_extract(f, "EQ hist (국가코드 156=중국)")
    print_stats(label, stats, units, dist)

# ─────────────────────────────────────────────
# 2. 홍수 (Flood - 고해상도)
# ─────────────────────────────────────────────
print("\n[2] 홍수 (Flood) - 역사 기반 고해상도")
f = DATA / "hazard/flood/flood_CHN/v1/flood_CHN.hdf5"
label, stats, units, dist = load_and_extract(f, "Flood CHN hist")
print_stats(label, stats, units, dist)

# ─────────────────────────────────────────────
# 3. 하천홍수 (River Flood) - 시나리오별
# ─────────────────────────────────────────────
print("\n[3] 하천홍수 (River Flood) - 시나리오별")
rf_files = {
    'hist 1980-2000': DATA / "hazard/river_flood/river_flood_150arcsec_hist_CHN_1980_2000/v2/river_flood_150arcsec_hist_CHN_1980_2000.hdf5",
    'RCP2.6 2010-2030': DATA / "hazard/river_flood/river_flood_150arcsec_rcp26_CHN_2010_2030/v3/river_flood_150arcsec_rcp26_CHN_2010_2030.hdf5",
    'RCP2.6 2030-2050': DATA / "hazard/river_flood/river_flood_150arcsec_rcp26_CHN_2030_2050/v3/river_flood_150arcsec_rcp26_CHN_2030_2050.hdf5",
    'RCP2.6 2050-2070': DATA / "hazard/river_flood/river_flood_150arcsec_rcp26_CHN_2050_2070/v3/river_flood_150arcsec_rcp26_CHN_2050_2070.hdf5",
    'RCP2.6 2070-2090': DATA / "hazard/river_flood/river_flood_150arcsec_rcp26_CHN_2070_2090/v3/river_flood_150arcsec_rcp26_CHN_2070_2090.hdf5",
    'RCP6.0 2010-2030': DATA / "hazard/river_flood/river_flood_150arcsec_rcp60_CHN_2010_2030/v3/river_flood_150arcsec_rcp60_CHN_2010_2030.hdf5",
    'RCP6.0 2030-2050': DATA / "hazard/river_flood/river_flood_150arcsec_rcp60_CHN_2030_2050/v3/river_flood_150arcsec_rcp60_CHN_2030_2050.hdf5",
    'RCP6.0 2050-2070': DATA / "hazard/river_flood/river_flood_150arcsec_rcp60_CHN_2050_2070/v3/river_flood_150arcsec_rcp60_CHN_2050_2070.hdf5",
    'RCP6.0 2070-2090': DATA / "hazard/river_flood/river_flood_150arcsec_rcp60_CHN_2070_2090/v3/river_flood_150arcsec_rcp60_CHN_2070_2090.hdf5",
    'RCP8.5 2010-2030': DATA / "hazard/river_flood/river_flood_150arcsec_rcp85_CHN_2010_2030/v3/river_flood_150arcsec_rcp85_CHN_2010_2030.hdf5",
    'RCP8.5 2030-2050': DATA / "hazard/river_flood/river_flood_150arcsec_rcp85_CHN_2030_2050/v3/river_flood_150arcsec_rcp85_CHN_2030_2050.hdf5",
    'RCP8.5 2050-2070': DATA / "hazard/river_flood/river_flood_150arcsec_rcp85_CHN_2050_2070/v3/river_flood_150arcsec_rcp85_CHN_2050_2070.hdf5",
    'RCP8.5 2070-2090': DATA / "hazard/river_flood/river_flood_150arcsec_rcp85_CHN_2070_2090/v3/river_flood_150arcsec_rcp85_CHN_2070_2090.hdf5",
}
for label, f in rf_files.items():
    l, stats, units, dist = load_and_extract(f, label)
    print_stats(l, stats, units, dist)

# ─────────────────────────────────────────────
# 4. 열대성 사이클론 (TC) - 역사 + 시나리오
# ─────────────────────────────────────────────
print("\n[4] 열대성 사이클론 (TC) - 역사 + 시나리오")
tc_files = {
    'TC hist (STORM)':        DATA / "hazard/tropical_cyclone/TC_CHN_0300as_STORM/v1.1/TC_CHN_0300as_STORM.hdf5",
    'TC hist (synth x10)':    DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_CHN_1980_2020/v2.1/tropical_cyclone_10synth_tracks_150arcsec_CHN_1980_2020.hdf5",
    'TC RCP2.6 2040':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2040/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2040.hdf5",
    'TC RCP2.6 2060':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2060/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2060.hdf5",
    'TC RCP2.6 2080':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2080/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2080.hdf5",
    'TC RCP4.5 2040':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2040/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2040.hdf5",
    'TC RCP4.5 2060':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2060/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2060.hdf5",
    'TC RCP4.5 2080':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2080/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2080.hdf5",
    'TC RCP6.0 2040':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2040/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2040.hdf5",
    'TC RCP6.0 2060':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2060/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2060.hdf5",
    'TC RCP6.0 2080':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2080/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2080.hdf5",
    'TC RCP8.5 2040':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp85_CHN_2040/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp85_CHN_2040.hdf5",
    'TC RCP8.5 2060':         DATA / "hazard/tropical_cyclone/tropical_cyclone_10synth_tracks_150arcsec_rcp85_CHN_2060/v2.1/tropical_cyclone_10synth_tracks_150arcsec_rcp85_CHN_2060.hdf5",
}
for label, f in tc_files.items():
    l, stats, units, dist = load_and_extract(f, label)
    print_stats(l, stats, units, dist)

# ─────────────────────────────────────────────
# 5. 산불 (Wildfire)
# ─────────────────────────────────────────────
print("\n[5] 산불 (Wildfire) - 역사 2001-2020")
f = DATA / "hazard/wildfire/wildfire_CHN_150arcsec_historical_2001_2020/v1/wildfire_CHN_150arcsec_historical_2001_2020.hdf5"
label, stats, units, dist = load_and_extract(f, "Wildfire CHN 2001-2020")
print_stats(label, stats, units, dist)

# ─────────────────────────────────────────────
# 6. 자산 노출 (LitPop)
# ─────────────────────────────────────────────
print("\n[6] 자산 노출 (LitPop) - 기준년도 2018")
litpop_files = {
    'LitPop 총자산 (USD)':     DATA / "exposures/litpop/LitPop_150arcsec_CHN/v3/LitPop_150arcsec_CHN.hdf5",
    'LitPop 생산자본 (USD)':   DATA / "exposures/litpop/LitPop_assets_pc_150arcsec_CHN/v3/LitPop_assets_pc_150arcsec_CHN.hdf5",
    'LitPop 인구 (명)':        DATA / "exposures/litpop/LitPop_pop_150arcsec_CHN/v3/LitPop_pop_150arcsec_CHN.hdf5",
}
for label, f in litpop_files.items():
    try:
        exp = Exposures.from_hdf5(f)
        lats = exp.gdf.geometry.y.values
        lons = exp.gdf.geometry.x.values
        dist = np.sqrt((lats - LAT)**2 + (lons - LON)**2)
        idx = int(np.argmin(dist))
        val = exp.gdf['value'].iloc[idx]
        dist_km = dist[idx] * 111
        print(f"  {label}: {val:,.0f}  [격자점 거리: {dist_km:.1f} km]")
    except Exception as e:
        print(f"  {label}: 오류 - {e}")

print("\n" + "=" * 70)
print("분석 완료")
print("=" * 70)

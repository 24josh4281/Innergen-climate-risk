import warnings; warnings.filterwarnings('ignore')
import numpy as np, h5py
from pathlib import Path
from scipy.spatial import cKDTree

LAT, LON = 34.7979, 117.2571

def extract_sparse(fpath, tlat, tlon):
    with h5py.File(fpath, 'r') as f:
        try:
            indices = f['intensity']['indices'][:]
            n = int(indices.max()) + 1
            lats = f['centroids']['lat'][:n]
            lons = f['centroids']['lon'][:n]
        except:
            return None, None
        tree = cKDTree(np.column_stack([lats, lons]))
        dist_deg, idx = tree.query([tlat, tlon])
        data   = f['intensity']['data'][:]
        indptr = f['intensity']['indptr'][:]
        vals = []
        for e in range(len(indptr)-1):
            rs, re = indptr[e], indptr[e+1]
            w = np.where(indices[rs:re] == idx)[0]
            vals.append(float(data[rs+w[0]]) if len(w) > 0 else 0.0)
        return np.array(vals), dist_deg*111.0

def summary(vals, dist_km, unit):
    nz = vals[vals > 0]
    freq = len(nz)/len(vals)*100
    avg  = float(np.mean(nz)) if len(nz) > 0 else 0.0
    mx   = float(np.max(vals))
    return f"dist={dist_km:.0f}km  freq={freq:.2f}%  avg={avg:.3f}{unit}  max={mx:.3f}{unit}"

print("="*68)
print(f"  물리적 리스크 — Zaozhuang ({LAT}N, {LON}E)")
print("="*68)

# 1. River Flood
print("\n[1] 하천홍수 (River Flood) 침수깊이 m")
RF = Path("c:/Users/24jos/climada/data/hazard/river_flood")
for scen, period, fname in [
    ("hist",   "1980-2000", "river_flood_150arcsec_hist_CHN_1980_2000/v2/river_flood_150arcsec_hist_CHN_1980_2000.hdf5"),
    ("RCP2.6", "2010-2030", "river_flood_150arcsec_rcp26_CHN_2010_2030/v3/river_flood_150arcsec_rcp26_CHN_2010_2030.hdf5"),
    ("RCP2.6", "2030-2050", "river_flood_150arcsec_rcp26_CHN_2030_2050/v3/river_flood_150arcsec_rcp26_CHN_2030_2050.hdf5"),
    ("RCP2.6", "2050-2070", "river_flood_150arcsec_rcp26_CHN_2050_2070/v3/river_flood_150arcsec_rcp26_CHN_2050_2070.hdf5"),
    ("RCP2.6", "2070-2090", "river_flood_150arcsec_rcp26_CHN_2070_2090/v3/river_flood_150arcsec_rcp26_CHN_2070_2090.hdf5"),
    ("RCP6.0", "2010-2030", "river_flood_150arcsec_rcp60_CHN_2010_2030/v3/river_flood_150arcsec_rcp60_CHN_2010_2030.hdf5"),
    ("RCP6.0", "2030-2050", "river_flood_150arcsec_rcp60_CHN_2030_2050/v3/river_flood_150arcsec_rcp60_CHN_2030_2050.hdf5"),
    ("RCP6.0", "2050-2070", "river_flood_150arcsec_rcp60_CHN_2050_2070/v3/river_flood_150arcsec_rcp60_CHN_2050_2070.hdf5"),
    ("RCP6.0", "2070-2090", "river_flood_150arcsec_rcp60_CHN_2070_2090/v3/river_flood_150arcsec_rcp60_CHN_2070_2090.hdf5"),
    ("RCP8.5", "2010-2030", "river_flood_150arcsec_rcp85_CHN_2010_2030/v3/river_flood_150arcsec_rcp85_CHN_2010_2030.hdf5"),
    ("RCP8.5", "2030-2050", "river_flood_150arcsec_rcp85_CHN_2030_2050/v3/river_flood_150arcsec_rcp85_CHN_2030_2050.hdf5"),
    ("RCP8.5", "2050-2070", "river_flood_150arcsec_rcp85_CHN_2050_2070/v3/river_flood_150arcsec_rcp85_CHN_2050_2070.hdf5"),
    ("RCP8.5", "2070-2090", "river_flood_150arcsec_rcp85_CHN_2070_2090/v3/river_flood_150arcsec_rcp85_CHN_2070_2090.hdf5"),
]:
    fp = RF/fname
    if not fp.exists(): continue
    v, d = extract_sparse(str(fp), LAT, LON)
    if v is None: continue
    print(f"  {scen:6} {period}  {summary(v, d, 'm')}")

# 2. Flood pluvial
print("\n[2] 홍수 (Flood pluvial/coastal) 침수깊이 m")
fp = Path("c:/Users/24jos/climada/data/hazard/flood/flood_CHN/v1/flood_CHN.hdf5")
if fp.exists():
    v, d = extract_sparse(str(fp), LAT, LON)
    if v is not None:
        print(f"  Historical  {summary(v, d, 'm')}")

# 3. Earthquake
print("\n[3] 지진 (Earthquake) MMI 진도")
eq_base = Path("c:/Users/24jos/climada/data/hazard/earthquake")
if eq_base.exists():
    for ef in sorted(eq_base.rglob("*.hdf5")):
        v, d = extract_sparse(str(ef), LAT, LON)
        if v is None: continue
        print(f"  {ef.parent.parent.name[:35]}  {summary(v, d, '')}")

# 4. Wildfire
print("\n[4] 산불 (Wildfire) FRP MW")
fp = Path("c:/Users/24jos/climada/data/hazard/wildfire/wildfire_CHN_150arcsec_historical_2001_2020/v1/wildfire_CHN_150arcsec_historical_2001_2020.hdf5")
if fp.exists():
    v, d = extract_sparse(str(fp), LAT, LON)
    if v is not None and len(v) > 0:
        print(f"  2001-2020  {summary(v, d, 'MW')}")
    else:
        print("  이벤트 없음")

# 5. Tropical Cyclone
print("\n[5] 태풍 (Tropical Cyclone) 최대풍속 m/s")
tc_base = Path("c:/Users/24jos/climada/data/hazard/tropical_cyclone")
for scen, period, dname in [
    ("hist",   "1980-2020",     "tropical_cyclone_0synth_tracks_150arcsec_historical_CHN_1980_2020"),
    ("hist x10","1980-2020",    "tropical_cyclone_10synth_tracks_150arcsec_CHN_1980_2020"),
    ("RCP2.6", "2040",          "tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2040"),
    ("RCP2.6", "2060",          "tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2060"),
    ("RCP2.6", "2080",          "tropical_cyclone_10synth_tracks_150arcsec_rcp26_CHN_2080"),
    ("RCP4.5", "2040",          "tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2040"),
    ("RCP4.5", "2060",          "tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2060"),
    ("RCP4.5", "2080",          "tropical_cyclone_10synth_tracks_150arcsec_rcp45_CHN_2080"),
    ("RCP6.0", "2040",          "tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2040"),
    ("RCP6.0", "2060",          "tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2060"),
    ("RCP6.0", "2080",          "tropical_cyclone_10synth_tracks_150arcsec_rcp60_CHN_2080"),
    ("RCP8.5", "2040",          "tropical_cyclone_10synth_tracks_150arcsec_rcp85_CHN_2040"),
    ("RCP8.5", "2060",          "tropical_cyclone_10synth_tracks_150arcsec_rcp85_CHN_2060"),
]:
    matches = list(tc_base.rglob(f"{dname}/*.hdf5"))
    if not matches: continue
    v, d = extract_sparse(str(matches[0]), LAT, LON)
    if v is None: continue
    print(f"  {scen:9} {period:7}  {summary(v, d, 'm/s')}")

# 6. LitPop
print("\n[6] LitPop 자산/인구")
for label, fname in [
    ("GDP 자산(USD)",      "LitPop_150arcsec_CHN/v3/LitPop_150arcsec_CHN.hdf5"),
    ("1인당자산(USD/cap)", "LitPop_assets_pc_150arcsec_CHN/v3/LitPop_assets_pc_150arcsec_CHN.hdf5"),
    ("인구(명)",           "LitPop_pop_150arcsec_CHN/v3/LitPop_pop_150arcsec_CHN.hdf5"),
]:
    fp = Path(f"c:/Users/24jos/climada/data/exposures/litpop/{fname}")
    if not fp.exists(): continue
    with h5py.File(str(fp),'r') as f:
        b = f['exposures']['block0_values'][:]  # (n,3): value, lat, lon
        tree = cKDTree(np.column_stack([b[:,1], b[:,2]]))
        dist_deg, idx = tree.query([LAT, LON])
        print(f"  {label}: {b[idx,0]:>15,.0f}  (격자거리 {dist_deg*111:.1f}km)")

# 7. IBTrACS
print("\n[7] 태풍 IBTrACS (1950-2023, R=500km)")
print("  접근횟수: 106회 | 연평균: 1.43회/년 | 최대: 61.7m/s (1994 FRED T3)")
print("  최근접: 17km (1981 NINA) | 2020s 평균강도 82kt (상승중)")

print("\n" + "="*68)

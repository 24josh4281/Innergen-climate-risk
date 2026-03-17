import warnings
warnings.filterwarnings('ignore')
import numpy as np
import h5py
from pathlib import Path
from scipy.spatial import cKDTree

LAT, LON = 34.7979, 117.2571

def extract_intensity_sparse(fpath, target_lat, target_lon):
    with h5py.File(fpath, 'r') as f:
        lats = lons = None
        for path in [('centroids','latitude'), ('centroids','lat')]:
            try:
                obj = f
                for p in path: obj = obj[p]
                lats = obj[:]
                break
            except: pass
        for path in [('centroids','longitude'), ('centroids','lon')]:
            try:
                obj = f
                for p in path: obj = obj[p]
                lons = obj[:]
                break
            except: pass
        if lats is None or lons is None:
            return None, None
        coords = np.column_stack([lats, lons])
        tree = cKDTree(coords)
        dist_deg, idx = tree.query([target_lat, target_lon], k=1)
        dist_km = dist_deg * 111.0

        intensity_vals = []
        try:
            data    = f['intensity']['data'][:]
            indices = f['intensity']['indices'][:]
            indptr  = f['intensity']['indptr'][:]
            n_events = len(indptr) - 1
            for e in range(n_events):
                rs, re = indptr[e], indptr[e+1]
                row_cols = indices[rs:re]
                row_data = data[rs:re]
                where = np.where(row_cols == idx)[0]
                intensity_vals.append(float(row_data[where[0]]) if len(where) > 0 else 0.0)
        except Exception as ex:
            return None, dist_km
        return np.array(intensity_vals), dist_km

print("=" * 65)
print(f"Zaozhuang, Shandong  ({LAT}N, {LON}E)")
print("=" * 65)

# ── River Flood ──────────────────────────────────────────────────
print("\n[하천 홍수 River Flood]")
rf_base = Path("c:/Users/24jos/climada/data/hazard/river_flood")
rf_files = [
    ("hist",   "1980-2000", rf_base/"river_flood_150arcsec_hist_CHN_1980_2000/v2/river_flood_150arcsec_hist_CHN_1980_2000.hdf5"),
    ("RCP2.6", "2010-2030", rf_base/"river_flood_150arcsec_rcp26_CHN_2010_2030/v3/river_flood_150arcsec_rcp26_CHN_2010_2030.hdf5"),
    ("RCP2.6", "2030-2050", rf_base/"river_flood_150arcsec_rcp26_CHN_2030_2050/v3/river_flood_150arcsec_rcp26_CHN_2030_2050.hdf5"),
    ("RCP2.6", "2050-2070", rf_base/"river_flood_150arcsec_rcp26_CHN_2050_2070/v3/river_flood_150arcsec_rcp26_CHN_2050_2070.hdf5"),
    ("RCP2.6", "2070-2090", rf_base/"river_flood_150arcsec_rcp26_CHN_2070_2090/v3/river_flood_150arcsec_rcp26_CHN_2070_2090.hdf5"),
    ("RCP6.0", "2010-2030", rf_base/"river_flood_150arcsec_rcp60_CHN_2010_2030/v3/river_flood_150arcsec_rcp60_CHN_2010_2030.hdf5"),
    ("RCP6.0", "2030-2050", rf_base/"river_flood_150arcsec_rcp60_CHN_2030_2050/v3/river_flood_150arcsec_rcp60_CHN_2030_2050.hdf5"),
    ("RCP6.0", "2050-2070", rf_base/"river_flood_150arcsec_rcp60_CHN_2050_2070/v3/river_flood_150arcsec_rcp60_CHN_2050_2070.hdf5"),
    ("RCP6.0", "2070-2090", rf_base/"river_flood_150arcsec_rcp60_CHN_2070_2090/v3/river_flood_150arcsec_rcp60_CHN_2070_2090.hdf5"),
    ("RCP8.5", "2010-2030", rf_base/"river_flood_150arcsec_rcp85_CHN_2010_2030/v3/river_flood_150arcsec_rcp85_CHN_2010_2030.hdf5"),
    ("RCP8.5", "2030-2050", rf_base/"river_flood_150arcsec_rcp85_CHN_2030_2050/v3/river_flood_150arcsec_rcp85_CHN_2030_2050.hdf5"),
    ("RCP8.5", "2050-2070", rf_base/"river_flood_150arcsec_rcp85_CHN_2050_2070/v3/river_flood_150arcsec_rcp85_CHN_2050_2070.hdf5"),
    ("RCP8.5", "2070-2090", rf_base/"river_flood_150arcsec_rcp85_CHN_2070_2090/v3/river_flood_150arcsec_rcp85_CHN_2070_2090.hdf5"),
]
for scen, period, fpath in rf_files:
    if not fpath.exists(): continue
    vals, dist_km = extract_intensity_sparse(str(fpath), LAT, LON)
    if vals is None: continue
    nz = vals[vals > 0]
    freq = len(nz)/len(vals)*100 if len(vals) > 0 else 0
    mean_d = float(np.mean(nz)) if len(nz) > 0 else 0
    max_d  = float(np.max(vals)) if len(vals) > 0 else 0
    print(f"  {scen:6s} {period}  dist={dist_km:.0f}km  freq={freq:.1f}%  avg={mean_d:.3f}m  max={max_d:.3f}m")

# ── Wildfire ─────────────────────────────────────────────────────
print("\n[산불 Wildfire]")
wf_path = Path("c:/Users/24jos/climada/data/hazard/wildfire/wildfire_CHN_150arcsec_historical_2001_2020/v1/wildfire_CHN_150arcsec_historical_2001_2020.hdf5")
if wf_path.exists():
    vals, dist_km = extract_intensity_sparse(str(wf_path), LAT, LON)
    if vals is not None and len(vals) > 0:
        nz = vals[vals > 0]
        print(f"  2001-2020  dist={dist_km:.0f}km  freq={len(nz)/len(vals)*100:.2f}%  max={float(np.max(vals)):.2f}")
    else:
        print("  해당 좌표 산불 이벤트 없음")

# ── Earthquake ───────────────────────────────────────────────────
print("\n[지진 Earthquake]")
eq_base = Path("c:/Users/24jos/climada/data/hazard/earthquake")
if eq_base.exists():
    eq_files = list(eq_base.rglob("*.hdf5"))
    for ef in eq_files:
        vals, dist_km = extract_intensity_sparse(str(ef), LAT, LON)
        if vals is None: continue
        nz = vals[vals > 0]
        print(f"  {ef.parent.parent.name}  dist={dist_km:.0f}km  events={len(vals)}  freq={len(nz)/len(vals)*100:.2f}%  max_MMI={float(np.max(vals)):.2f}")

# ── LitPop ───────────────────────────────────────────────────────
print("\n[LitPop 자산/인구 노출값]")
lp_files = {
    "GDP 자산 (USD)": Path("c:/Users/24jos/climada/data/exposures/litpop/LitPop_150arcsec_CHN/v3/LitPop_150arcsec_CHN.hdf5"),
    "1인당 자산 (USD/cap)": Path("c:/Users/24jos/climada/data/exposures/litpop/LitPop_assets_pc_150arcsec_CHN/v3/LitPop_assets_pc_150arcsec_CHN.hdf5"),
    "인구 (명)": Path("c:/Users/24jos/climada/data/exposures/litpop/LitPop_pop_150arcsec_CHN/v3/LitPop_pop_150arcsec_CHN.hdf5"),
}
for label, fpath in lp_files.items():
    if not fpath.exists(): continue
    try:
        with h5py.File(str(fpath), 'r') as f:
            lats = f['latitude'][:]
            lons = f['longitude'][:]
            vals = f['value'][:]
            tree = cKDTree(np.column_stack([lats, lons]))
            _, idx = tree.query([LAT, LON])
            print(f"  {label}: {vals[idx]:,.0f}")
    except Exception as e:
        print(f"  {label}: 오류 ({e})")

# ── Flood (coast) ─────────────────────────────────────────────────
print("\n[홍수 Flood (coastal/pluvial)]")
fl_path = Path("c:/Users/24jos/climada/data/hazard/flood/flood_CHN/v1/flood_CHN.hdf5")
if fl_path.exists():
    vals, dist_km = extract_intensity_sparse(str(fl_path), LAT, LON)
    if vals is not None and len(vals) > 0:
        nz = vals[vals > 0]
        print(f"  flood_CHN  dist={dist_km:.0f}km  freq={len(nz)/len(vals)*100:.1f}%  avg={float(np.mean(nz)) if len(nz)>0 else 0:.3f}m  max={float(np.max(vals)):.3f}m")
    else:
        print("  해당 좌표 침수 이벤트 없음")

# ── Tropical Cyclone summary ──────────────────────────────────────
print("\n[태풍 Tropical Cyclone - IBTrACS 1950-2023, R=500km]")
print("  접근 횟수: 106회 | 연평균: 1.43회/년")
print("  최대풍속: 61.7 m/s (1994 FRED, T3급)")
print("  최근접:   17.0 km (1981 NINA)")
print("  2020s 평균풍속: 82 kt (상승 추세)")

print("\n" + "=" * 65)
print("분석 완료")

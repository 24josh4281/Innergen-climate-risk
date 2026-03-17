import warnings
warnings.filterwarnings('ignore')
import numpy as np
import netCDF4 as nc

LAT, LON = 34.7979, 117.2571
RADIUS_KM = 500

f = nc.Dataset('c:/Users/24jos/climada/data/ibtracs/IBTrACS.WP.v04r01.nc')
lats  = f.variables['lat'][:]       # (4225, 360)
lons  = f.variables['lon'][:]
winds = f.variables['wmo_wind'][:]   # kt
years = f.variables['season'][:]     # (4225,)
names = nc.chartostring(f.variables['name'][:])

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1))*np.cos(np.radians(lat2))*np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

hits = []
n_storms = lats.shape[0]
for i in range(n_storms):
    yr = int(years[i])
    if yr < 1950 or yr > 2023:
        continue
    valid = ~np.ma.getmaskarray(lats[i]) & ~np.ma.getmaskarray(lons[i])
    if not valid.any():
        continue
    lat_v = np.array(lats[i][valid], dtype=float)
    lon_v = np.array(lons[i][valid], dtype=float)
    wind_v = np.array(winds[i][valid], dtype=float) if not np.all(np.ma.getmaskarray(winds[i][valid])) else np.zeros(valid.sum())

    dists = haversine(LAT, LON, lat_v, lon_v)
    min_idx = np.argmin(dists)
    min_dist = dists[min_idx]
    if min_dist <= RADIUS_KM:
        max_wind = float(np.nanmax(wind_v)) if wind_v.size > 0 else 0
        hits.append({'year': yr, 'name': str(names[i]).strip(), 'dist_km': float(min_dist), 'max_wind_kt': max_wind})

f.close()
hits.sort(key=lambda x: x['dist_km'])

print(f"=== IBTrACS 태풍 분석: 반경 {RADIUS_KM}km (1950-2023) ===")
print(f"총 영향 태풍: {len(hits)}개\n")

if hits:
    winds_hit = [h['max_wind_kt'] for h in hits]
    print(f"연평균 접근 빈도: {len(hits)/74:.2f}회/년")
    print(f"최대 풍속 평균: {np.mean(winds_hit):.1f} kt ({np.mean(winds_hit)*0.5144:.1f} m/s)")
    print(f"최대 풍속 최대: {np.max(winds_hit):.1f} kt ({np.max(winds_hit)*0.5144:.1f} m/s)")

    print(f"\n--- 최근접 상위 10개 ---")
    for h in hits[:10]:
        cat = 'TS' if h['max_wind_kt']<64 else ('T1' if h['max_wind_kt']<83 else ('T2' if h['max_wind_kt']<96 else ('T3' if h['max_wind_kt']<113 else ('T4' if h['max_wind_kt']<137 else 'T5'))))
        print(f"  {h['year']} {h['name']:15s} | {h['dist_km']:6.1f}km | {h['max_wind_kt']:.0f}kt ({h['max_wind_kt']*0.5144:.1f}m/s) [{cat}]")

    print(f"\n--- 10년 단위 접근 빈도 ---")
    for decade in range(1950, 2030, 10):
        cnt = sum(1 for h in hits if decade <= h['year'] < decade+10)
        avg_w = np.mean([h['max_wind_kt'] for h in hits if decade <= h['year'] < decade+10]) if cnt > 0 else 0
        print(f"  {decade}s: {cnt}회 (평균 풍속 {avg_w:.0f}kt)")

# -*- coding: utf-8 -*-
"""
STEP 1: Heat Index, SPEI, Warming Rate calculation
Based on existing monthly CMIP6 data
"""
import warnings; warnings.filterwarnings('ignore')
import zipfile, io, numpy as np, pandas as pd, xarray as xr
from pathlib import Path

BASE = Path("c:/Users/24jos/climada/data/scenarios_v2")
OUT  = Path("c:/Users/24jos/climada/data/scenarios_v2/output")
OUT.mkdir(exist_ok=True)

SITES = {
    'HQ Seoul':             ('Korea',       37.5649, 126.9793, 'korea_china'),
    'R&D Seongnam':         ('Korea',       37.4018, 127.1615, 'korea_china'),
    'Pohang Plant':         ('Korea',       35.9953, 129.3744, 'korea_china'),
    'Gunsan Plant':         ('Korea',       35.9676, 126.7127, 'korea_china'),
    'Iksan Plant':          ('Korea',       35.9490, 126.9657, 'korea_china'),
    'Gwangyang Plant':      ('Korea',       34.9155, 127.6936, 'korea_china'),
    'Saehan Jeongeup':      ('Korea',       35.6183, 126.8638, 'korea_china'),
    'OCI Shanghai':         ('China',       31.2305, 121.4495, 'korea_china'),
    'Shandong OCI (ZZ)':    ('China',       34.7979, 117.2571, 'korea_china'),
    'MaSteel OCI (MAS)':    ('China',       31.7097, 118.5023, 'korea_china'),
    'Jianyang Carbon (ZZ)': ('China',       34.8604, 117.3123, 'korea_china'),
    'OCI Japan Tokyo':      ('Japan',       35.6458, 139.7386, 'japan'),
    'Philko Makati':        ('Philippines', 14.5547, 121.0244, 'philippines'),
}

REGION_DIRS = {
    'korea_china': BASE,
    'japan':       BASE / 'japan',
    'philippines': BASE / 'philippines',
}

SCENARIOS = ['ssp2_4_5', 'ssp5_8_5']
SCEN_LABELS = {'ssp2_4_5': 'SSP2-4.5', 'ssp5_8_5': 'SSP5-8.5'}

def load_var(region, ssp, short, lat, lon):
    ssp_dir = REGION_DIRS[region] / ssp
    candidates = list(ssp_dir.glob(f"{short}_*.zip"))
    if not candidates:
        return None
    try:
        zf = zipfile.ZipFile(candidates[0])
        nc_files = [n for n in zf.namelist() if n.endswith('.nc')]
        if not nc_files:
            return None
        with zf.open(nc_files[0]) as f:
            ds = xr.open_dataset(io.BytesIO(f.read()), use_cftime=True)
        lat_d = [d for d in ds.dims if 'lat' in d.lower()][0]
        lon_d = [d for d in ds.dims if 'lon' in d.lower()][0]
        dv = [v for v in ds.data_vars if short.lower() in v.lower()][0]
        ds_pt = ds.sel({lat_d: lat, lon_d: lon}, method='nearest')
        ts = ds_pt[dv].to_series()
        ts.index = pd.to_datetime([f"{t.year:04d}-{t.month:02d}-01" for t in ts.index])
        zf.close()
        return ts
    except Exception:
        return None

def heat_index_C(T_C, RH):
    """Rothfusz 1990 (NOAA), T: degC, RH: %, returns HI in degC"""
    T = T_C * 9/5 + 32
    HI = (-42.379 + 2.04901523*T + 10.14333127*RH
          - 0.22475541*T*RH - 0.00683783*T**2
          - 0.05481717*RH**2 + 0.00122874*T**2*RH
          + 0.00085282*T*RH**2 - 0.00000199*T**2*RH**2)
    return (HI - 32) * 5/9

def huss_to_rh(huss_gkg, T_C, P_hPa=1013.25):
    q = huss_gkg / 1000
    es = 6.112 * np.exp(17.67 * T_C / (T_C + 243.5))
    e = q * P_hPa / (0.622 + q)
    return np.clip(e / es * 100, 0, 100)

def spei_approx(pr_mm_day, evap_mm_day):
    pet = pr_mm_day - evap_mm_day
    mu, std = pet.mean(), pet.std()
    return (pet - mu) / std if std > 0 else pet * 0

def warming_rate(ts):
    ts = ts.dropna()
    if len(ts) < 12:
        return np.nan
    x = np.arange(len(ts))
    slope = np.polyfit(x, ts.values, 1)[0]
    return slope * 12 * 10

def hi_level(hi):
    if hi is None or (isinstance(hi, float) and np.isnan(hi)):
        return 'N/A'
    if hi >= 54: return 'Extreme Danger'
    if hi >= 40: return 'Danger'
    if hi >= 32: return 'Extreme Caution'
    if hi >= 27: return 'Caution'
    return 'Safe'

PERIODS = {
    '2020s':(2020,2029),'2030s':(2030,2039),'2040s':(2040,2049),
    '2050s':(2050,2059),'2060s':(2060,2069),'2070s':(2070,2079),
    '2080s':(2080,2089),'2090s':(2090,2099)
}

def period_mean(ts, y1, y2):
    sub = ts[(ts.index.year >= y1) & (ts.index.year <= y2)]
    return float(sub.mean()) if len(sub) > 0 else np.nan

print("=" * 65)
print("STEP 1: Climate Risk Indices")
print("  Heat Index | SPEI Approx | Warming Rate")
print("=" * 65)

rows_hi, rows_spei, rows_warm = [], [], []

for site, (country, lat, lon, region) in SITES.items():
    print(f"\n[{site}]")
    for ssp in SCENARIOS:
        lbl = SCEN_LABELS[ssp]
        tas  = load_var(region, ssp, 'tas',      lat, lon)
        huss = load_var(region, ssp, 'huss',     lat, lon)
        pr   = load_var(region, ssp, 'pr',       lat, lon)
        evap = load_var(region, ssp, 'evspsbl',  lat, lon)

        # Heat Index
        if tas is not None and huss is not None:
            T_C  = tas - 273.15 if tas.mean() > 100 else tas.copy()
            H_gkg = huss * 1000 if huss.mean() < 1 else huss.copy()
            RH   = huss_to_rh(H_gkg, T_C)
            HI   = T_C.copy()
            mask = T_C >= 27
            if mask.any():
                HI[mask] = heat_index_C(T_C[mask], RH[mask])
            row = {'Country': country, 'Site': site, 'Scenario': lbl}
            for pd_lbl, (y1, y2) in PERIODS.items():
                val = period_mean(HI, y1, y2)
                row[f'HI_{pd_lbl}_degC'] = round(val, 2) if not np.isnan(val) else None
            row['NOAA_Risk_2090s'] = hi_level(row.get('HI_2090s_degC'))
            rows_hi.append(row)

        # SPEI
        if pr is not None and evap is not None:
            pr_mm  = pr * 86400  if pr.mean()   < 1 else pr.copy()
            ev_mm  = evap * 86400 if evap.mean() < 1 else evap.copy()
            spei   = spei_approx(pr_mm, ev_mm)
            row2 = {'Country': country, 'Site': site, 'Scenario': lbl}
            for pd_lbl, (y1, y2) in PERIODS.items():
                val = period_mean(spei, y1, y2)
                row2[f'SPEI_{pd_lbl}'] = round(val, 3) if not np.isnan(val) else None
            rows_spei.append(row2)

        # Warming rate
        if tas is not None:
            T_C = tas - 273.15 if tas.mean() > 100 else tas.copy()
            near = T_C[(T_C.index.year >= 2020) & (T_C.index.year <= 2050)]
            far  = T_C[(T_C.index.year >= 2050) & (T_C.index.year <= 2100)]
            rows_warm.append({
                'Country': country, 'Site': site, 'Scenario': lbl,
                'Rate_2020_2050_degC_per_decade': round(warming_rate(near), 3),
                'Rate_2050_2100_degC_per_decade': round(warming_rate(far),  3),
                'dT_total_degC': round(
                    period_mean(T_C, 2090, 2099) - period_mean(T_C, 2020, 2029), 2),
            })
        print(f"  {lbl}: OK")

df_hi   = pd.DataFrame(rows_hi)
df_spei = pd.DataFrame(rows_spei)
df_warm = pd.DataFrame(rows_warm)

df_hi.to_csv(str(OUT / 'index_heat_index.csv'),    index=False, encoding='utf-8-sig')
df_spei.to_csv(str(OUT / 'index_spei.csv'),         index=False, encoding='utf-8-sig')
df_warm.to_csv(str(OUT / 'index_warming_rate.csv'), index=False, encoding='utf-8-sig')

print("\n\n" + "=" * 65)
print("HEAT INDEX  (SSP5-8.5, degC)  |  NOAA Risk Level")
print("=" * 65)
sub = df_hi[df_hi['Scenario'] == 'SSP5-8.5'][[
    'Country','Site','HI_2020s_degC','HI_2050s_degC','HI_2090s_degC','NOAA_Risk_2090s']]
print(sub.to_string(index=False))

print("\n\n" + "=" * 65)
print("WARMING RATE  (SSP5-8.5, degC/decade)")
print("=" * 65)
sub2 = df_warm[df_warm['Scenario'] == 'SSP5-8.5'][[
    'Country','Site','Rate_2020_2050_degC_per_decade','Rate_2050_2100_degC_per_decade','dT_total_degC']]
print(sub2.to_string(index=False))

print("\n\n" + "=" * 65)
print("SPEI APPROX  (SSP5-8.5)  <-1: drought risk")
print("=" * 65)
sub3 = df_spei[df_spei['Scenario'] == 'SSP5-8.5'][[
    'Country','Site','SPEI_2020s','SPEI_2050s','SPEI_2090s']]
print(sub3.to_string(index=False))

print(f"\nSaved to: {OUT}")

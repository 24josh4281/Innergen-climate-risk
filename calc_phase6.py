# -*- coding: utf-8 -*-
"""
Phase 6: Seasonal Climate Analysis (Monthly Data)
  A. JJA (Jun-Jul-Aug) — Summer heat / precipitation
  B. DJF (Dec-Jan-Feb) — Winter cold / snowfall
  C. MAM / SON       — Spring/Autumn transition
  D. Seasonal extremes shift across 4 SSPs × 8 decades

Outputs:
  ph6_seasonal_temp.csv   — Seasonal Tmean/Tmax/Tmin per site × SSP × period
  ph6_seasonal_precip.csv — Seasonal precipitation + snowfall
  ph6_seasonal_wind.csv   — Seasonal wind speed
  ph6_heat_stress.csv     — JJA WBGT + Humidex seasonal mean
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
    'Shandong OCI (ZZ)':   ('China',       34.7979, 117.2571, 'korea_china'),
    'MaSteel OCI (MAS)':   ('China',       31.7097, 118.5023, 'korea_china'),
    'Jianyang Carbon (ZZ)':('China',       34.8604, 117.3123, 'korea_china'),
    'OCI Japan Tokyo':      ('Japan',       35.6458, 139.7386, 'japan'),
    'Philko Makati':        ('Philippines', 14.5547, 121.0244, 'philippines'),
}
REGION_DIRS = {
    'korea_china': BASE,
    'japan':       BASE / 'japan',
    'philippines': BASE / 'philippines',
}
SCENARIOS = ['ssp1_2_6', 'ssp2_4_5', 'ssp3_7_0', 'ssp5_8_5']
SCEN_LABELS = {
    'ssp1_2_6': 'SSP1-2.6', 'ssp2_4_5': 'SSP2-4.5',
    'ssp3_7_0': 'SSP3-7.0', 'ssp5_8_5': 'SSP5-8.5'
}
PERIODS = {
    '2020s':(2020,2029),'2030s':(2030,2039),'2040s':(2040,2049),
    '2050s':(2050,2059),'2060s':(2060,2069),'2070s':(2070,2079),
    '2080s':(2080,2089),'2090s':(2090,2099)
}
SEASONS = {
    'JJA': [6,7,8],   # Summer
    'DJF': [12,1,2],  # Winter
    'MAM': [3,4,5],   # Spring
    'SON': [9,10,11], # Autumn
}

def load_var(region, ssp, short, lat, lon, conv=lambda x: x):
    ssp_dir = REGION_DIRS[region] / ssp
    cands = list(ssp_dir.glob(f"{short}_*.zip"))
    if not cands:
        return None
    try:
        zf = zipfile.ZipFile(cands[0])
        nc_files = [n for n in zf.namelist() if n.endswith('.nc')]
        series = []
        for nc in nc_files[:7]:
            try:
                ds = xr.open_dataset(io.BytesIO(zf.open(nc).read()), use_cftime=True)
                lat_d = [d for d in ds.dims if 'lat' in d.lower()][0]
                lon_d = [d for d in ds.dims if 'lon' in d.lower()][0]
                dv = [v for v in ds.data_vars if short.lower() in v.lower()][0]
                ds_pt = ds.sel({lat_d: lat, lon_d: lon}, method='nearest')
                ts = ds_pt[dv].to_series()
                ts.index = pd.to_datetime([f"{t.year:04d}-{t.month:02d}-01" for t in ts.index])
                series.append(ts)
            except:
                continue
        zf.close()
        if not series:
            return None
        ts = pd.concat(series, axis=1).mean(axis=1)
        return conv(ts)
    except:
        return None

def seasonal_period_mean(ts, months, y1, y2):
    """Mean of seasonal months within a decade."""
    if ts is None:
        return np.nan
    sub = ts[(ts.index.year >= y1) & (ts.index.year <= y2) & ts.index.month.isin(months)]
    return float(sub.mean()) if len(sub) > 0 else np.nan

def seasonal_period_sum(ts, months, y1, y2):
    """Annual sum of seasonal months (mean over years)."""
    if ts is None:
        return np.nan
    sub = ts[(ts.index.year >= y1) & (ts.index.year <= y2) & ts.index.month.isin(months)]
    if len(sub) == 0:
        return np.nan
    # Sum per year then average
    annual = sub.groupby(sub.index.year).sum()
    return float(annual.mean())

# ── A. Seasonal Temperature ──────────────────────────────────────────────────
print("Phase 6A: Seasonal Temperature...")
rows_temp = []
for site, (country, lat, lon, region) in SITES.items():
    print(f"  {site}")
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        tas    = load_var(region, ssp, 'tas',    lat, lon, conv=lambda x: x - 273.15)
        tasmax = load_var(region, ssp, 'tasmax', lat, lon, conv=lambda x: x - 273.15)
        tasmin = load_var(region, ssp, 'tasmin', lat, lon, conv=lambda x: x - 273.15)
        row = {'Country': country, 'Site': site, 'Scenario': scen}
        for period, (y1, y2) in PERIODS.items():
            for season, months in SEASONS.items():
                row[f'Tmean_{season}_{period}']  = seasonal_period_mean(tas,    months, y1, y2)
                row[f'Tmax_{season}_{period}']   = seasonal_period_mean(tasmax, months, y1, y2)
                row[f'Tmin_{season}_{period}']   = seasonal_period_mean(tasmin, months, y1, y2)
        rows_temp.append(row)

df_temp = pd.DataFrame(rows_temp)
df_temp.to_csv(OUT / 'ph6_seasonal_temp.csv', index=False, encoding='utf-8-sig')
print(f"  OK: ph6_seasonal_temp.csv {df_temp.shape}")

# ── B. Seasonal Precipitation + Snowfall ─────────────────────────────────────
print("Phase 6B: Seasonal Precipitation...")
rows_pr = []
for site, (country, lat, lon, region) in SITES.items():
    print(f"  {site}")
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        pr   = load_var(region, ssp, 'pr',   lat, lon, conv=lambda x: x * 86400 * 30)  # kg/m2/s -> mm/month
        prsn = load_var(region, ssp, 'prsn', lat, lon, conv=lambda x: x * 86400 * 30)  # snowfall mm/month
        row  = {'Country': country, 'Site': site, 'Scenario': scen}
        for period, (y1, y2) in PERIODS.items():
            for season, months in SEASONS.items():
                row[f'Pr_{season}_{period}_mm']   = seasonal_period_sum(pr,   months, y1, y2)
                row[f'Snow_{season}_{period}_mm'] = seasonal_period_sum(prsn, months, y1, y2)
        rows_pr.append(row)

df_pr = pd.DataFrame(rows_pr)
df_pr.to_csv(OUT / 'ph6_seasonal_precip.csv', index=False, encoding='utf-8-sig')
print(f"  OK: ph6_seasonal_precip.csv {df_pr.shape}")

# ── C. Seasonal Wind Speed ───────────────────────────────────────────────────
print("Phase 6C: Seasonal Wind Speed...")
rows_wind = []
for site, (country, lat, lon, region) in SITES.items():
    print(f"  {site}")
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        wind = load_var(region, ssp, 'sfcWind', lat, lon)
        row  = {'Country': country, 'Site': site, 'Scenario': scen}
        for period, (y1, y2) in PERIODS.items():
            for season, months in SEASONS.items():
                row[f'Wind_{season}_{period}_ms'] = seasonal_period_mean(wind, months, y1, y2)
        rows_wind.append(row)

df_wind = pd.DataFrame(rows_wind)
df_wind.to_csv(OUT / 'ph6_seasonal_wind.csv', index=False, encoding='utf-8-sig')
print(f"  OK: ph6_seasonal_wind.csv {df_wind.shape}")

# ── D. JJA Heat Stress: WBGT + Humidex (monthly proxy) ──────────────────────
print("Phase 6D: JJA Heat Stress indices...")

def huss_to_dewpoint(T_K, huss, P=101325):
    """Specific humidity -> dewpoint (deg C)"""
    Rd, Rv = 287.058, 461.5
    e = huss * P / (huss + Rd / Rv)
    e = np.maximum(e, 1.0)
    Td = 243.04 * np.log(e / 611.2) / (17.368 - np.log(e / 611.2))
    return Td

def wbgt_monthly(T_C, Td_C):
    """Simple WBGT approximation from Tair and Td (Willett & Sherwood 2012)."""
    return 0.567 * T_C + 0.393 * (6.105 * np.exp(17.27 * Td_C / (237.7 + Td_C))) + 3.94

def humidex_monthly(T_C, Td_C):
    e = 6.112 * np.exp(17.67 * Td_C / (Td_C + 243.5))
    return T_C + 0.5555 * (e - 10.0)

JJA = [6, 7, 8]
rows_heat = []
for site, (country, lat, lon, region) in SITES.items():
    print(f"  {site}")
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        tas  = load_var(region, ssp, 'tas',    lat, lon, conv=lambda x: x - 273.15)
        huss = load_var(region, ssp, 'huss',   lat, lon)
        row  = {'Country': country, 'Site': site, 'Scenario': scen}
        for period, (y1, y2) in PERIODS.items():
            if tas is None or huss is None:
                row[f'WBGT_JJA_{period}']    = np.nan
                row[f'Humidex_JJA_{period}'] = np.nan
                row[f'DI_JJA_{period}']      = np.nan  # Discomfort Index
                continue
            mask = (tas.index.year >= y1) & (tas.index.year <= y2) & tas.index.month.isin(JJA)
            T  = tas[mask]
            H  = huss[mask]
            if len(T) == 0:
                row[f'WBGT_JJA_{period}']    = np.nan
                row[f'Humidex_JJA_{period}'] = np.nan
                row[f'DI_JJA_{period}']      = np.nan
                continue
            # Align index
            common_idx = T.index.intersection(H.index)
            T_a = T[common_idx].values
            H_a = H[common_idx].values
            # Use mean pressure 101325 Pa
            Td = huss_to_dewpoint(T_a + 273.15, H_a)
            wbgt_vals = wbgt_monthly(T_a, Td)
            humidex_vals = humidex_monthly(T_a, Td)
            # Discomfort Index (Thom 1959): DI = T - 0.55*(1-0.01*RH)*(T-14.5)
            # Approximate RH from Td: RH = 100 * exp(17.625*Td/(243.04+Td)) / exp(17.625*T/(243.04+T))
            RH = 100 * np.exp(17.625 * Td / (243.04 + Td)) / np.exp(17.625 * T_a / (243.04 + T_a))
            DI = T_a - 0.55 * (1 - 0.01 * RH) * (T_a - 14.5)
            row[f'WBGT_JJA_{period}']    = float(np.nanmean(wbgt_vals))
            row[f'Humidex_JJA_{period}'] = float(np.nanmean(humidex_vals))
            row[f'DI_JJA_{period}']      = float(np.nanmean(DI))
        rows_heat.append(row)

df_heat = pd.DataFrame(rows_heat)
df_heat.to_csv(OUT / 'ph6_heat_stress.csv', index=False, encoding='utf-8-sig')
print(f"  OK: ph6_heat_stress.csv {df_heat.shape}")

print("\n" + "="*60)
print("Phase 6 complete. Files:")
print(f"  ph6_seasonal_temp.csv   {df_temp.shape}")
print(f"  ph6_seasonal_precip.csv {df_pr.shape}")
print(f"  ph6_seasonal_wind.csv   {df_wind.shape}")
print(f"  ph6_heat_stress.csv     {df_heat.shape}")

# Quick summary: JJA WBGT SSP5-8.5 2090s
print("\n=== JJA WBGT (SSP5-8.5, 2090s) ===")
s = df_heat[df_heat['Scenario']=='SSP5-8.5'][['Country','Site','WBGT_JJA_2090s','Humidex_JJA_2090s','DI_JJA_2090s']]
print(s.sort_values('WBGT_JJA_2090s', ascending=False).to_string(index=False))

print("\n=== DJF Tmin (SSP5-8.5, 2090s) ===")
t = df_temp[df_temp['Scenario']=='SSP5-8.5'][['Country','Site','Tmin_DJF_2090s','Tmin_DJF_2020s']]
t['DeltaTmin_DJF'] = t['Tmin_DJF_2090s'] - t['Tmin_DJF_2020s']
print(t.sort_values('Tmin_DJF_2090s').to_string(index=False))

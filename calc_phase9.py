# -*- coding: utf-8 -*-
"""
Phase 9: Additional Physical Risk Variables
  A. mrro  (Surface Runoff) — flood/waterlogging proxy [kg/m2/s -> mm/month]
  B. mrsos (Top-layer Soil Moisture) — drought/agriculture stress [kg/m2]
  C. rsds  (Surface Downwelling Solar Radiation) — heat island + solar energy [W/m2]

Derived indices:
  - Runoff: annual total + wet-season (JJA/SON) surge risk
  - Soil Moisture: summer minimum (drought stress), winter maximum
  - rsds: JJA mean (heat load), annual total (solar potential)
  - Soil Moisture Stress Index (SMSI): normalized deficit from historical mean

Outputs:
  ph9_runoff.csv         (13 sites x 4 SSP x 8 periods)
  ph9_soilmoisture.csv
  ph9_solar.csv
  ph9_water_stress.csv   (combined runoff+soilmoisture stress indicator)
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
JJA = [6,7,8]; SON = [9,10,11]; DJF = [12,1,2]; MAM = [3,4,5]

def load_monthly(region, ssp, short, lat, lon, conv=lambda x: x):
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

def pmean(ts, y1, y2, months=None):
    if ts is None: return np.nan
    m = (ts.index.year >= y1) & (ts.index.year <= y2)
    if months: m &= ts.index.month.isin(months)
    s = ts[m]
    return float(s.mean()) if len(s) > 0 else np.nan

def pannsum(ts, y1, y2, months=None):
    """Annual sum averaged over years in period."""
    if ts is None: return np.nan
    m = (ts.index.year >= y1) & (ts.index.year <= y2)
    if months: m &= ts.index.month.isin(months)
    s = ts[m]
    if len(s) == 0: return np.nan
    return float(s.groupby(s.index.year).sum().mean())

# ── A. Runoff ──────────────────────────────────────────────────────────────
print("Phase 9A: Surface Runoff (mrro)...")
rows_ro = []
for site, (country, lat, lon, region) in SITES.items():
    print(f"  {site}")
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        # mrro: kg/m2/s -> mm/month (x86400x30)
        mrro = load_monthly(region, ssp, 'mrro', lat, lon, conv=lambda x: x * 86400 * 30)
        row = {'Country': country, 'Site': site, 'Scenario': scen}
        for period, (y1, y2) in PERIODS.items():
            row[f'Runoff_annual_{period}_mm']  = pannsum(mrro, y1, y2)
            row[f'Runoff_JJA_{period}_mm']     = pannsum(mrro, y1, y2, JJA)
            row[f'Runoff_SON_{period}_mm']     = pannsum(mrro, y1, y2, SON)
            row[f'Runoff_max_month_{period}']  = pmean(mrro, y1, y2)   # monthly mean
        rows_ro.append(row)

df_ro = pd.DataFrame(rows_ro)
df_ro.to_csv(OUT / 'ph9_runoff.csv', index=False, encoding='utf-8-sig')
print(f"  ph9_runoff.csv {df_ro.shape}")

# ── B. Soil Moisture ──────────────────────────────────────────────────────
print("Phase 9B: Soil Moisture (mrsos)...")
rows_sm = []
for site, (country, lat, lon, region) in SITES.items():
    print(f"  {site}")
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        mrsos = load_monthly(region, ssp, 'mrsos', lat, lon)  # kg/m2
        row = {'Country': country, 'Site': site, 'Scenario': scen}
        for period, (y1, y2) in PERIODS.items():
            row[f'SM_annual_{period}_kgm2']  = pmean(mrsos, y1, y2)
            row[f'SM_JJA_{period}_kgm2']     = pmean(mrsos, y1, y2, JJA)
            row[f'SM_DJF_{period}_kgm2']     = pmean(mrsos, y1, y2, DJF)
            # Summer deficit vs winter (stress index proxy)
            jja_v = pmean(mrsos, y1, y2, JJA)
            djf_v = pmean(mrsos, y1, y2, DJF)
            if not np.isnan(jja_v) and not np.isnan(djf_v) and djf_v > 0:
                row[f'SM_deficit_{period}'] = round((djf_v - jja_v) / djf_v * 100, 1)
            else:
                row[f'SM_deficit_{period}'] = np.nan
        rows_sm.append(row)

df_sm = pd.DataFrame(rows_sm)
df_sm.to_csv(OUT / 'ph9_soilmoisture.csv', index=False, encoding='utf-8-sig')
print(f"  ph9_soilmoisture.csv {df_sm.shape}")

# ── C. Solar Radiation ────────────────────────────────────────────────────
print("Phase 9C: Solar Radiation (rsds)...")
rows_sol = []
for site, (country, lat, lon, region) in SITES.items():
    print(f"  {site}")
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        rsds = load_monthly(region, ssp, 'rsds', lat, lon)  # W/m2
        row = {'Country': country, 'Site': site, 'Scenario': scen}
        for period, (y1, y2) in PERIODS.items():
            row[f'Solar_annual_{period}_Wm2']  = pmean(rsds, y1, y2)
            row[f'Solar_JJA_{period}_Wm2']     = pmean(rsds, y1, y2, JJA)
            row[f'Solar_DJF_{period}_Wm2']     = pmean(rsds, y1, y2, DJF)
            # kWh/m2/day (W/m2 * 24/1000)
            ann = pmean(rsds, y1, y2)
            row[f'Solar_annual_{period}_kWhm2d'] = round(ann * 24 / 1000, 2) if not np.isnan(ann) else np.nan
        rows_sol.append(row)

df_sol = pd.DataFrame(rows_sol)
df_sol.to_csv(OUT / 'ph9_solar.csv', index=False, encoding='utf-8-sig')
print(f"  ph9_solar.csv {df_sol.shape}")

# ── D. Water Stress Composite ──────────────────────────────────────────────
print("Phase 9D: Water Stress composite...")
rows_ws = []
# Load SPI3 and PE for reference
ph1_spi = pd.read_csv(OUT / 'ph1_spi3.csv')
ph1_pe  = pd.read_csv(OUT / 'ph1_pe_balance.csv')

for site, (country, lat, lon, region) in SITES.items():
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        ro_row = df_ro[(df_ro['Site']==site) & (df_ro['Scenario']==scen)]
        sm_row = df_sm[(df_sm['Site']==site) & (df_sm['Scenario']==scen)]
        spi_row = ph1_spi[(ph1_spi['Site']==site) & (ph1_spi['Scenario']==scen)] \
                  if ssp in ['ssp2_4_5','ssp5_8_5'] else pd.DataFrame()
        pe_row  = ph1_pe[(ph1_pe['Site']==site) & (ph1_pe['Scenario']==scen)] \
                  if ssp in ['ssp2_4_5','ssp5_8_5'] else pd.DataFrame()

        row = {'Country': country, 'Site': site, 'Scenario': scen}
        for period, (y1, y2) in PERIODS.items():
            ro_ann  = float(ro_row[f'Runoff_annual_{period}_mm'].values[0]) if len(ro_row) > 0 else np.nan
            sm_def  = float(sm_row[f'SM_deficit_{period}'].values[0]) if len(sm_row) > 0 else np.nan
            spi_v   = float(spi_row[f'SPI3_{period}'].values[0]) if len(spi_row) > 0 and f'SPI3_{period}' in spi_row.columns else np.nan
            pe_v    = float(pe_row[f'PE_{period}'].values[0]) if len(pe_row) > 0 and f'PE_{period}' in pe_row.columns else np.nan

            # Flood risk proxy: high runoff = higher flood risk (normalized later)
            row[f'FloodRisk_proxy_{period}']   = ro_ann
            # Drought risk proxy: low SPI + high SM deficit = drought stress
            drought_components = []
            if not np.isnan(sm_def):   drought_components.append(min(sm_def / 50.0, 1.0))   # 0-1
            if not np.isnan(spi_v):    drought_components.append(max(-spi_v / 2.0, 0.0))    # 0-1 (negative SPI = drought)
            if not np.isnan(pe_v):     drought_components.append(max(-pe_v / 200.0, 0.0))   # 0-1
            row[f'DroughtStress_{period}'] = round(float(np.mean(drought_components)) * 100, 1) if drought_components else np.nan
        rows_ws.append(row)

df_ws = pd.DataFrame(rows_ws)
df_ws.to_csv(OUT / 'ph9_water_stress.csv', index=False, encoding='utf-8-sig')
print(f"  ph9_water_stress.csv {df_ws.shape}")

# ── Summary ───────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("Phase 9 complete.")
for fn, df in [('ph9_runoff.csv',df_ro),('ph9_soilmoisture.csv',df_sm),
               ('ph9_solar.csv',df_sol),('ph9_water_stress.csv',df_ws)]:
    print(f"  {fn}: {df.shape}")

print("\n=== Annual Runoff SSP5-8.5 2090s (mm/yr) ===")
sub = df_ro[(df_ro['Scenario']=='SSP5-8.5')][['Country','Site','Runoff_annual_2090s_mm','Runoff_annual_2020s_mm']].copy()
sub['Delta_mm'] = sub['Runoff_annual_2090s_mm'] - sub['Runoff_annual_2020s_mm']
print(sub.sort_values('Runoff_annual_2090s_mm', ascending=False).to_string(index=False))

print("\n=== Soil Moisture Summer Deficit SSP5-8.5 2090s (%) ===")
sm_sub = df_sm[(df_sm['Scenario']=='SSP5-8.5')][['Country','Site','SM_deficit_2090s','SM_deficit_2020s']]
print(sm_sub.sort_values('SM_deficit_2090s', ascending=False).to_string(index=False))

print("\n=== Solar Radiation JJA SSP5-8.5 2090s (W/m2) ===")
sol_sub = df_sol[(df_sol['Scenario']=='SSP5-8.5')][['Country','Site','Solar_JJA_2090s_Wm2','Solar_annual_2090s_kWhm2d']]
print(sol_sub.sort_values('Solar_JJA_2090s_Wm2', ascending=False).to_string(index=False))

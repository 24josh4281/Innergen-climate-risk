# -*- coding: utf-8 -*-
"""
Phase 15: OCI_MASTER_ALL_v2
  - Merge Phase 11~14 outputs into OCI_MASTER_ALL
  - Fill SSP1/3 compound events gap using daily data
  - Final master: 13 sites x 4 SSP x 8 periods x ~80 columns

Also fixes SSP1-2.6 / SSP3-7.0 gaps:
  - SPI3: recalculate for all 4 SSP using monthly pr data
  - Compound hot+dry: recalculate for SSP1/3 using daily data
"""
import warnings; warnings.filterwarnings('ignore')
import zipfile, io, numpy as np, pandas as pd, xarray as xr
from pathlib import Path
from scipy.stats import norm as sp_norm

BASE  = Path("c:/Users/24jos/climada/data/scenarios_v2")
DAILY = BASE / "daily"
OUT   = BASE / "output"

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
REGION_DIRS_M = {'korea_china': BASE, 'japan': BASE/'japan', 'philippines': BASE/'philippines'}
REGION_DIRS_D = {'korea_china': DAILY, 'japan': DAILY/'japan', 'philippines': DAILY/'philippines'}
SCENARIOS = ['ssp1_2_6','ssp2_4_5','ssp3_7_0','ssp5_8_5']
SCEN_LABELS = {'ssp1_2_6':'SSP1-2.6','ssp2_4_5':'SSP2-4.5','ssp3_7_0':'SSP3-7.0','ssp5_8_5':'SSP5-8.5'}
PERIODS = {'2020s':(2020,2029),'2030s':(2030,2039),'2040s':(2040,2049),'2050s':(2050,2059),
           '2060s':(2060,2069),'2070s':(2070,2079),'2080s':(2080,2089),'2090s':(2090,2099)}

# ── Helper loaders ────────────────────────────────────────────────────
def load_monthly(region, ssp, short, lat, lon, conv=lambda x: x):
    ssp_dir = REGION_DIRS_M[region] / ssp
    cands = list(ssp_dir.glob(f"{short}_*.zip"))
    if not cands: return None
    try:
        zf = zipfile.ZipFile(cands[0])
        series = []
        for nc in [n for n in zf.namelist() if n.endswith('.nc')][:7]:
            try:
                ds = xr.open_dataset(io.BytesIO(zf.open(nc).read()), use_cftime=True)
                lat_d = [d for d in ds.dims if 'lat' in d.lower()][0]
                lon_d = [d for d in ds.dims if 'lon' in d.lower()][0]
                dv = [v for v in ds.data_vars if short.lower() in v.lower()][0]
                ts = ds.sel({lat_d:lat, lon_d:lon}, method='nearest')[dv].to_series()
                ts.index = pd.to_datetime([f"{t.year:04d}-{t.month:02d}-01" for t in ts.index])
                series.append(ts)
            except: continue
        zf.close()
        if not series: return None
        return conv(pd.concat(series,axis=1).mean(axis=1))
    except: return None

def load_daily(region, ssp, varname, lat, lon):
    ssp_dir = REGION_DIRS_D[region] / ssp
    cands = list(ssp_dir.glob(f"{varname}_daily_{ssp}_*.zip"))
    if not cands: return None
    try:
        zf = zipfile.ZipFile(cands[0])
        series = []
        for nc in [n for n in zf.namelist() if n.endswith('.nc')][:3]:
            try:
                ds = xr.open_dataset(io.BytesIO(zf.open(nc).read()), use_cftime=True)
                lat_d = [d for d in ds.dims if 'lat' in d.lower()][0]
                lon_d = [d for d in ds.dims if 'lon' in d.lower()][0]
                dv = [v for v in ds.data_vars if varname.lower() in v.lower()][0]
                ts = ds.sel({lat_d:lat, lon_d:lon}, method='nearest')[dv].to_series()
                ts.index = pd.to_datetime([f"{t.year:04d}-{t.month:02d}-{t.day:02d}" for t in ts.index])
                series.append(ts)
            except: continue
        zf.close()
        if not series: return None
        return pd.concat(series,axis=1).mean(axis=1)
    except: return None

# ── A. SPI-3 for all 4 SSPs ──────────────────────────────────────────
print("Phase 15A: SPI-3 for SSP1/3 gap-fill...")
rows_spi = []
for site, (country, lat, lon, region) in SITES.items():
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        pr_m = load_monthly(region, ssp, 'pr', lat, lon, conv=lambda x: x*86400*30)
        row = {'Country':country,'Site':site,'Scenario':scen}
        for period, (y1,y2) in PERIODS.items():
            if pr_m is None:
                row[f'SPI3_{period}'] = np.nan; continue
            # 3-month rolling sum
            pr3 = pr_m.rolling(3, min_periods=2).sum()
            base = pr3[(pr3.index.year>=2020)&(pr3.index.year<=2039)].dropna()
            if len(base) < 10:
                row[f'SPI3_{period}'] = np.nan; continue
            mu, sigma = base.mean(), base.std()
            if sigma < 1e-6:
                row[f'SPI3_{period}'] = 0.0; continue
            sub = pr3[(pr3.index.year>=y1)&(pr3.index.year<=y2)].dropna()
            spi_val = float(sp_norm.ppf(sub.rank(pct=True).clip(0.001,0.999)).mean()) if len(sub)>0 else np.nan
            row[f'SPI3_{period}'] = round(spi_val, 3)
        rows_spi.append(row)

df_spi4 = pd.DataFrame(rows_spi)
df_spi4.to_csv(OUT/'ph15_spi3_4ssp.csv', index=False, encoding='utf-8-sig')
print(f"  ph15_spi3_4ssp.csv {df_spi4.shape}")

# ── B. Compound Hot+Dry for SSP1/3 using daily data ──────────────────
print("Phase 15B: Compound events for SSP1/3...")
rows_ce = []
for site, (country, lat, lon, region) in SITES.items():
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        tmax_d = load_daily(region, ssp, 'tasmax', lat, lon)
        pr_d   = load_daily(region, ssp, 'pr', lat, lon)
        if tmax_d is not None: tmax_d = tmax_d - 273.15
        if pr_d is not None:   pr_d   = pr_d * 86400
        row = {'Country':country,'Site':site,'Scenario':scen}
        # 90th pct threshold (base 2020-2039)
        tx90 = np.nan
        if tmax_d is not None:
            base = tmax_d[(tmax_d.index.year>=2020)&(tmax_d.index.year<=2039)].dropna()
            if len(base)>0: tx90 = float(np.percentile(base,90))
        for epoch, (y1,y2) in [('near',(2020,2059)),('far',(2060,2099))]:
            if tmax_d is None or pr_d is None or np.isnan(tx90):
                row[f'CompoundDays_pct_{epoch}'] = np.nan; continue
            common = tmax_d.index.intersection(pr_d.index)
            tx_sub = tmax_d[common]
            pr_sub = pr_d[common]
            mask = (tx_sub.index.year>=y1)&(tx_sub.index.year<=y2)
            hot  = tx_sub[mask] > tx90
            dry  = pr_sub[mask] < 1.0
            compound = (hot & dry).sum()
            total    = mask.sum()
            row[f'CompoundDays_pct_{epoch}'] = round(float(compound/total*100),2) if total>0 else np.nan
        rows_ce.append(row)

df_ce4 = pd.DataFrame(rows_ce)
df_ce4.to_csv(OUT/'ph15_compound_4ssp.csv', index=False, encoding='utf-8-sig')
print(f"  ph15_compound_4ssp.csv {df_ce4.shape}")

# ── C. Build OCI_MASTER_ALL_v2 ────────────────────────────────────────
print("Phase 15C: Building OCI_MASTER_ALL_v2...")
master_v1 = pd.read_csv(OUT/'OCI_MASTER_ALL.csv')
ph11h = pd.read_csv(OUT/'ph11_daily_heat.csv')
ph11c = pd.read_csv(OUT/'ph11_daily_cold.csv')
ph11p = pd.read_csv(OUT/'ph11_daily_precip.csv')
ph12e = pd.read_csv(OUT/'ph12_eal.csv')
ph12d = pd.read_csv(OUT/'ph12_disruption.csv')
ph13u = pd.read_csv(OUT/'ph13_urgency.csv')

rows_v2 = []
for _, base_row in master_v1.iterrows():
    site = base_row['Site']; ssp = base_row['Scenario']; period = base_row['Period']
    row = base_row.to_dict()

    def gv(df, col, s=site, sc=ssp, p=None):
        r = df[(df['Site']==s)&(df['Scenario']==sc)] if 'Scenario' in df.columns else df[df['Site']==s]
        if p and 'Period' in r.columns: r = r[r['Period']==p]
        if len(r)==0 or col not in r.columns: return np.nan
        try: return float(r[col].values[0])
        except: return np.nan

    # Ph11 daily heat
    row['TX90p_days']   = gv(ph11h, f'TX90p_{period}')
    row['HWD_days']     = gv(ph11h, f'HWD_{period}')
    row['TX35_days']    = gv(ph11h, f'TX35_{period}')
    row['TX37_days']    = gv(ph11h, f'TX37_{period}')
    row['TX40_days']    = gv(ph11h, f'TX40_{period}')
    # Ph11 daily cold
    row['FD_daily']     = gv(ph11c, f'FD_{period}')
    row['TR20_days']    = gv(ph11c, f'TR20_{period}')
    row['TR25_days']    = gv(ph11c, f'TR25_{period}')
    # Ph11 daily precip
    row['CDD_daily']    = gv(ph11p, f'CDD_{period}')
    row['CWD_daily']    = gv(ph11p, f'CWD_{period}')
    row['R10mm_days']   = gv(ph11p, f'R10mm_{period}')
    row['R20mm_days']   = gv(ph11p, f'R20mm_{period}')
    row['R30mm_days']   = gv(ph11p, f'R30mm_{period}')
    row['Rx1day_daily'] = gv(ph11p, f'Rx1day_{period}')
    # Ph12 financial
    row['EAL_USDM_yr']  = gv(ph12e, 'EAL_USDM_yr', p=period)
    row['EAL_cum10yr']  = gv(ph12e, 'EAL_cumulative_10yr_USDM', p=period)
    row['BID_days_yr']  = gv(ph12d, 'BID_days_yr', p=period)
    row['BID_rev_pct']  = gv(ph12d, 'BID_loss_pct_revenue', p=period)
    # Ph13 urgency (period-independent — use 2090s)
    row['Urgency_Score']= gv(ph13u, 'Urgency_Score', p=None)
    row['Cross_50_yr']  = gv(ph13u, 'Cross_50_yr', p=None)
    # Updated SPI3 (4 SSP)
    spi_row = df_spi4[(df_spi4['Site']==site)&(df_spi4['Scenario']==ssp)]
    if len(spi_row)>0 and f'SPI3_{period}' in spi_row.columns:
        row['SPI3'] = float(spi_row[f'SPI3_{period}'].values[0])
    # Updated compound events (4 SSP)
    ce_row = df_ce4[(df_ce4['Site']==site)&(df_ce4['Scenario']==ssp)]
    epoch = 'near' if int(period[:4]) < 2060 else 'far'
    if len(ce_row)>0 and f'CompoundDays_pct_{epoch}' in ce_row.columns:
        row['CompoundDays_pct'] = float(ce_row[f'CompoundDays_pct_{epoch}'].values[0])

    rows_v2.append(row)

df_v2 = pd.DataFrame(rows_v2)
df_v2.to_csv(OUT/'OCI_MASTER_ALL_v2.csv', index=False, encoding='utf-8-sig')
print(f"OCI_MASTER_ALL_v2.csv: {df_v2.shape}")
print(f"  Added {df_v2.shape[1] - master_v1.shape[1]} new columns")

# Summary
print("\n=== SPI3 4-SSP (2090s, select sites) ===")
spi_show = df_spi4[['Site','Scenario']+[f'SPI3_{p}' for p in ['2020s','2050s','2090s']]]
spi_show = spi_show[spi_show['Site'].isin(['HQ Seoul','Shandong OCI (ZZ)','Philko Makati'])]
print(spi_show.to_string(index=False, float_format='%.2f'))

print("\n=== Compound Hot+Dry 4-SSP ===")
ce_show = df_ce4[['Site','Scenario','CompoundDays_pct_near','CompoundDays_pct_far']]
ce_show = ce_show[ce_show['Site'].isin(['HQ Seoul','Shandong OCI (ZZ)','Philko Makati'])]
print(ce_show.to_string(index=False, float_format='%.2f'))

print("\nPhase 15 complete.")

# -*- coding: utf-8 -*-
"""
Phase 4: Statistical Extreme Analysis
  A. Return Period Analysis  — GEV fitting on Rx1day (10/50/100-yr flood)
  B. Compound Extreme Events — joint heat+drought probability
"""
import warnings; warnings.filterwarnings('ignore')
import zipfile, io, numpy as np, pandas as pd, xarray as xr
from pathlib import Path
from scipy.stats import genextreme, pearsonr

BASE  = Path("c:/Users/24jos/climada/data/scenarios_v2")
DBASE = BASE / "daily"
OUT   = Path("c:/Users/24jos/climada/data/scenarios_v2/output")

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
DAILY_REGION_DIRS = {
    'korea_china': DBASE,
    'japan':       DBASE / 'japan',
    'philippines': DBASE / 'philippines',
}
SCENARIOS = ['ssp2_4_5', 'ssp5_8_5']
SCEN_LABELS = {'ssp2_4_5': 'SSP2-4.5', 'ssp5_8_5': 'SSP5-8.5'}

EPOCH = {
    'near': (2020, 2059),
    'far':  (2060, 2099),
}

# ── Helper: load daily time series from zip ─────────────────────────────────
def load_daily(zip_path, var_short, lat, lon, conv=lambda x: x):
    try:
        zf = zipfile.ZipFile(zip_path)
    except:
        return None
    nc_files = [n for n in zf.namelist() if n.endswith('.nc')]
    series_list = []
    for nc in nc_files[:3]:
        try:
            ds = xr.open_dataset(io.BytesIO(zf.open(nc).read()), use_cftime=True)
            lat_d = [d for d in ds.dims if 'lat' in d.lower()][0]
            lon_d = [d for d in ds.dims if 'lon' in d.lower()][0]
            dv = [v for v in ds.data_vars if var_short.lower() in v.lower()][0]
            ds_pt = ds.sel({lat_d: lat, lon_d: lon}, method='nearest')
            ts = ds_pt[dv].to_series()
            ts.index = pd.to_datetime(
                [f'{t.year:04d}-{t.month:02d}-{t.day:02d}' for t in ts.index])
            series_list.append(conv(ts))
        except:
            continue
    zf.close()
    if not series_list:
        return None
    return pd.concat(series_list, axis=1).mean(axis=1)

# ── A. GEV Return Period ─────────────────────────────────────────────────────
def gev_return_levels(annual_maxima, return_periods=(10, 50, 100)):
    """Fit GEV to annual maxima → return level for each return period"""
    data = annual_maxima.dropna().values
    if len(data) < 10:
        return {rp: np.nan for rp in return_periods}
    try:
        shape, loc, scale = genextreme.fit(data)
        results = {}
        for rp in return_periods:
            p = 1 - 1/rp
            rl = genextreme.ppf(p, shape, loc=loc, scale=scale)
            results[rp] = round(float(rl), 1)
        return results
    except:
        return {rp: np.nan for rp in return_periods}

# ── B. Compound Events ───────────────────────────────────────────────────────
def compound_prob(tasmax_daily, pr_daily, heat_thresh_pct=90, dry_thresh_mm=1.0):
    """
    P(hot AND dry): fraction of days where
      Tmax > 90th percentile AND pr < 1mm
    Returns annual fraction (0-1)
    """
    t_thresh = np.nanpercentile(tasmax_daily.dropna().values, heat_thresh_pct)
    hot  = tasmax_daily > t_thresh
    dry  = pr_daily < dry_thresh_mm
    both = hot & dry
    # annual compound day fraction
    ann = both.resample('YE').sum() / both.resample('YE').count()
    return ann, t_thresh

# ── Main Loop ────────────────────────────────────────────────────────────────
print("=" * 65)
print("Phase 4: Statistical Extreme Analysis")
print("  A. Return Period (GEV)   B. Compound Events")
print("=" * 65)

rows_rp, rows_ce = [], []

for site, (country, lat, lon, region) in SITES.items():
    print(f"\n[{site}]")
    ddir = DAILY_REGION_DIRS[region]

    for ssp in SCENARIOS:
        lbl = SCEN_LABELS[ssp]
        ssp_ddir = ddir / ssp

        # Load daily pr and tasmax
        pr_cands  = list(ssp_ddir.glob('pr_daily_*.zip'))
        tx_cands  = list(ssp_ddir.glob('tasmax_daily_*.zip'))

        pr_daily  = load_daily(pr_cands[0],  'pr',     lat, lon,
                               conv=lambda x: x * 86400) if pr_cands  else None
        tx_daily  = load_daily(tx_cands[0],  'tasmax', lat, lon,
                               conv=lambda x: x - 273.15) if tx_cands else None

        # ── A. Return Period ──────────────────────────────────────────────
        if pr_daily is not None:
            row_rp = {'Country': country, 'Site': site, 'Scenario': lbl}
            for epoch_lbl, (y1, y2) in EPOCH.items():
                sub = pr_daily[(pr_daily.index.year >= y1) &
                               (pr_daily.index.year <= y2)]
                ann_max = sub.resample('YE').max()
                rls = gev_return_levels(ann_max)
                row_rp[f'RL10yr_{epoch_lbl}_mm']  = rls.get(10)
                row_rp[f'RL50yr_{epoch_lbl}_mm']  = rls.get(50)
                row_rp[f'RL100yr_{epoch_lbl}_mm'] = rls.get(100)
                row_rp[f'Rx1day_mean_{epoch_lbl}_mm'] = round(
                    float(ann_max.mean()), 1)
            rows_rp.append(row_rp)

        # ── B. Compound Events ────────────────────────────────────────────
        if tx_daily is not None and pr_daily is not None:
            row_ce = {'Country': country, 'Site': site, 'Scenario': lbl}
            # align index
            tx_a, pr_a = tx_daily.align(pr_daily, join='inner')
            for epoch_lbl, (y1, y2) in EPOCH.items():
                tx_sub = tx_a[(tx_a.index.year >= y1) & (tx_a.index.year <= y2)]
                pr_sub = pr_a[(pr_a.index.year >= y1) & (pr_a.index.year <= y2)]
                ann_frac, thresh = compound_prob(tx_sub, pr_sub)
                row_ce[f'CompoundDays_pct_{epoch_lbl}'] = round(
                    float(ann_frac.mean() * 100), 2)
                row_ce[f'HeatThresh_{epoch_lbl}_C'] = round(float(thresh), 1)
            rows_ce.append(row_ce)

        print(f"  {lbl}: OK")

df_rp = pd.DataFrame(rows_rp)
df_ce = pd.DataFrame(rows_ce)
df_rp.to_csv(str(OUT / 'ph4_return_period.csv'), index=False, encoding='utf-8-sig')
df_ce.to_csv(str(OUT / 'ph4_compound_events.csv'), index=False, encoding='utf-8-sig')

print("\n\n" + "=" * 65)
print("Phase 4 complete.")
print(f"  ph4_return_period.csv   {df_rp.shape}")
print(f"  ph4_compound_events.csv {df_ce.shape}")

print("\n=== RETURN PERIOD (GEV) — SSP5-8.5 ===")
print("  Near-future (2020-2059) vs Far-future (2060-2099)")
sub = df_rp[df_rp['Scenario']=='SSP5-8.5'][[
    'Country','Site',
    'RL10yr_near_mm','RL50yr_near_mm','RL100yr_near_mm',
    'RL10yr_far_mm', 'RL50yr_far_mm', 'RL100yr_far_mm']]
pd.set_option('display.float_format', '{:.1f}'.format)
print(sub.to_string(index=False))

print("\n=== COMPOUND HOT+DRY DAYS (% of year) — SSP5-8.5 ===")
sub2 = df_ce[df_ce['Scenario']=='SSP5-8.5'][[
    'Country','Site',
    'CompoundDays_pct_near','HeatThresh_near_C',
    'CompoundDays_pct_far', 'HeatThresh_far_C']]
print(sub2.to_string(index=False))

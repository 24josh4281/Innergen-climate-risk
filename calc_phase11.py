# -*- coding: utf-8 -*-
"""
Phase 11: Daily-Data Precise ETCCDI
  A. TX90p  — Days above 90th pct of Tmax (base: 2020-2039)
  B. HWD    — Heatwave Duration (max spell of >=3 consecutive TX90p days per year)
  C. TXdays — Days with Tmax > 35 / 37 / 40 C
  D. TNdays — Days with Tmin < 0 C (frost), > 20 C (tropical nights precise)
  E. CDD    — Consecutive Dry Days (pr < 1 mm/day)
  F. CWD    — Consecutive Wet Days (pr >= 1 mm/day)
  G. Rxmm   — Days with pr > 10 / 20 / 30 mm (R10mm, R20mm, R30mm)
  H. Pmax99 — 99th percentile daily precipitation

All per decade (2020s~2090s) × 4 SSP × 13 sites
Outputs:
  ph11_daily_heat.csv    — TX90p, HWD, TXdays
  ph11_daily_cold.csv    — frost days, precise TR
  ph11_daily_precip.csv  — CDD, CWD, R10/20/30mm, Pmax99
  ph11_daily_summary.csv — all combined (13 sites x 4 SSP x 8 periods)
"""
import warnings; warnings.filterwarnings('ignore')
import zipfile, io, numpy as np, pandas as pd, xarray as xr
from pathlib import Path
from scipy.ndimage import label as ndlabel

BASE  = Path("c:/Users/24jos/climada/data/scenarios_v2")
DAILY = BASE / "daily"
OUT   = BASE / "output"
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
    'korea_china': DAILY,
    'japan':       DAILY / 'japan',
    'philippines': DAILY / 'philippines',
}
SCENARIOS = ['ssp1_2_6', 'ssp2_4_5', 'ssp3_7_0', 'ssp5_8_5']
SCEN_LABELS = {
    'ssp1_2_6':'SSP1-2.6','ssp2_4_5':'SSP2-4.5',
    'ssp3_7_0':'SSP3-7.0','ssp5_8_5':'SSP5-8.5'
}
PERIODS = {
    '2020s':(2020,2029),'2030s':(2030,2039),'2040s':(2040,2049),
    '2050s':(2050,2059),'2060s':(2060,2069),'2070s':(2070,2079),
    '2080s':(2080,2089),'2090s':(2090,2099)
}

def load_daily_ts(region, ssp, varname, lat, lon):
    """Load daily time series for one site. Returns pd.Series(date index, values)."""
    ssp_dir = REGION_DIRS[region] / ssp
    pattern = f"{varname}_daily_{ssp}_*.zip"
    cands = list(ssp_dir.glob(pattern))
    if not cands:
        return None
    try:
        zf = zipfile.ZipFile(cands[0])
        nc_files = [n for n in zf.namelist() if n.endswith('.nc')]
        series = []
        for nc in nc_files[:3]:   # up to 3 models
            try:
                ds = xr.open_dataset(io.BytesIO(zf.open(nc).read()), use_cftime=True)
                lat_d = [d for d in ds.dims if 'lat' in d.lower()][0]
                lon_d = [d for d in ds.dims if 'lon' in d.lower()][0]
                dv = [v for v in ds.data_vars if varname.lower() in v.lower()][0]
                ds_pt = ds.sel({lat_d: lat, lon_d: lon}, method='nearest')
                ts = ds_pt[dv].to_series()
                ts.index = pd.to_datetime([f"{t.year:04d}-{t.month:02d}-{t.day:02d}" for t in ts.index])
                series.append(ts)
            except Exception:
                continue
        zf.close()
        if not series:
            return None
        return pd.concat(series, axis=1).mean(axis=1)
    except Exception:
        return None

def max_spell(arr):
    """Max consecutive True run length in boolean array."""
    if not any(arr):
        return 0
    labeled, n = ndlabel(arr)
    if n == 0:
        return 0
    return max((arr[labeled==i]).sum() for i in range(1, n+1))

def decade_stats(ts_daily, y1, y2, func):
    """Apply func to daily series sliced to decade."""
    if ts_daily is None:
        return np.nan
    sub = ts_daily[(ts_daily.index.year >= y1) & (ts_daily.index.year <= y2)]
    if len(sub) == 0:
        return np.nan
    return func(sub)

def ann_mean(ts, y1, y2, func):
    """Annual values then mean over decade."""
    if ts is None:
        return np.nan
    sub = ts[(ts.index.year >= y1) & (ts.index.year <= y2)]
    if len(sub) == 0:
        return np.nan
    ann = sub.groupby(sub.index.year).apply(func)
    return float(ann.mean())

# ── Main computation ─────────────────────────────────────────────────────
rows_heat  = []
rows_cold  = []
rows_precip= []

total = len(SITES) * len(SCENARIOS)
done  = 0

for site, (country, lat, lon, region) in SITES.items():
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        done += 1
        print(f"  [{done}/{total}] {site} | {scen}")

        tmax = load_daily_ts(region, ssp, 'tasmax', lat, lon)
        tmin = load_daily_ts(region, ssp, 'tasmin', lat, lon)
        pr   = load_daily_ts(region, ssp, 'pr',     lat, lon)

        # Convert units
        if tmax is not None: tmax = tmax - 273.15     # K -> C
        if tmin is not None: tmin = tmin - 273.15
        if pr   is not None: pr   = pr   * 86400      # kg/m2/s -> mm/day

        # Base period threshold: 90th pct of Tmax in 2020-2039
        tx90 = np.nan
        if tmax is not None:
            base = tmax[(tmax.index.year >= 2020) & (tmax.index.year <= 2039)]
            if len(base) > 0:
                tx90 = float(np.percentile(base.dropna(), 90))

        # Pr 99th pct base
        pr99 = np.nan
        if pr is not None:
            base_pr = pr[(pr.index.year >= 2020) & (pr.index.year <= 2039) & (pr > 1)]
            if len(base_pr) > 0:
                pr99 = float(np.percentile(base_pr.dropna(), 99))

        row_h = {'Country':country,'Site':site,'Scenario':scen,'TX90_base_C':round(tx90,2) if not np.isnan(tx90) else np.nan}
        row_c = {'Country':country,'Site':site,'Scenario':scen}
        row_p = {'Country':country,'Site':site,'Scenario':scen,'Pr99_base_mm':round(pr99,2) if not np.isnan(pr99) else np.nan}

        for period, (y1, y2) in PERIODS.items():
            # ── Heat indices ──
            # TX90p: days/yr above 90th pct threshold
            if tmax is not None and not np.isnan(tx90):
                row_h[f'TX90p_{period}'] = ann_mean(tmax, y1, y2, lambda s: (s > tx90).sum())
            else:
                row_h[f'TX90p_{period}'] = np.nan

            # HWD: max consecutive heatwave days per year (>= 3 consecutive TX>TX90)
            if tmax is not None and not np.isnan(tx90):
                sub = tmax[(tmax.index.year >= y1) & (tmax.index.year <= y2)]
                hot = (sub > tx90).values
                hwd_ann = []
                for yr in range(y1, y2+1):
                    yr_mask = sub.index.year == yr
                    if yr_mask.sum() == 0: continue
                    yr_hot = hot[yr_mask.values] if hasattr(yr_mask,'values') else hot[sub.index.year==yr]
                    hwd_ann.append(max_spell(yr_hot))
                row_h[f'HWD_{period}'] = float(np.mean(hwd_ann)) if hwd_ann else np.nan
            else:
                row_h[f'HWD_{period}'] = np.nan

            # Days > 35 / 37 / 40 C
            for thresh in [35, 37, 40]:
                if tmax is not None:
                    row_h[f'TX{thresh}_{period}'] = ann_mean(tmax, y1, y2, lambda s, t=thresh: (s > t).sum())
                else:
                    row_h[f'TX{thresh}_{period}'] = np.nan

            # ── Cold indices ──
            # FD: frost days (Tmin < 0)
            if tmin is not None:
                row_c[f'FD_{period}'] = ann_mean(tmin, y1, y2, lambda s: (s < 0).sum())
            else:
                row_c[f'FD_{period}'] = np.nan

            # TR20: tropical nights (Tmin > 20)
            if tmin is not None:
                row_c[f'TR20_{period}'] = ann_mean(tmin, y1, y2, lambda s: (s > 20).sum())
            else:
                row_c[f'TR20_{period}'] = np.nan

            # TR25: very warm nights (Tmin > 25) — extreme heat stress
            if tmin is not None:
                row_c[f'TR25_{period}'] = ann_mean(tmin, y1, y2, lambda s: (s > 25).sum())
            else:
                row_c[f'TR25_{period}'] = np.nan

            # ── Precip indices ──
            # CDD: max consecutive dry days (pr < 1mm) per year
            if pr is not None:
                sub = pr[(pr.index.year >= y1) & (pr.index.year <= y2)]
                dry = (sub < 1.0).values
                cdd_ann = []
                for yr in range(y1, y2+1):
                    yr_dry = dry[sub.index.year == yr]
                    cdd_ann.append(max_spell(yr_dry))
                row_p[f'CDD_{period}'] = float(np.mean(cdd_ann)) if cdd_ann else np.nan
            else:
                row_p[f'CDD_{period}'] = np.nan

            # CWD: max consecutive wet days (pr >= 1mm)
            if pr is not None:
                sub = pr[(pr.index.year >= y1) & (pr.index.year <= y2)]
                wet = (sub >= 1.0).values
                cwd_ann = []
                for yr in range(y1, y2+1):
                    yr_wet = wet[sub.index.year == yr]
                    cwd_ann.append(max_spell(yr_wet))
                row_p[f'CWD_{period}'] = float(np.mean(cwd_ann)) if cwd_ann else np.nan
            else:
                row_p[f'CWD_{period}'] = np.nan

            # R10/R20/R30mm days per year
            for thresh in [10, 20, 30]:
                if pr is not None:
                    row_p[f'R{thresh}mm_{period}'] = ann_mean(pr, y1, y2, lambda s, t=thresh: (s >= t).sum())
                else:
                    row_p[f'R{thresh}mm_{period}'] = np.nan

            # Rx1day: annual max daily precipitation
            if pr is not None:
                row_p[f'Rx1day_{period}'] = ann_mean(pr, y1, y2, lambda s: s.max())
            else:
                row_p[f'Rx1day_{period}'] = np.nan

            # Pr99 exceedance days
            if pr is not None and not np.isnan(pr99):
                row_p[f'Pr99exc_{period}'] = ann_mean(pr, y1, y2, lambda s, t=pr99: (s > t).sum())
            else:
                row_p[f'Pr99exc_{period}'] = np.nan

        rows_heat.append(row_h)
        rows_cold.append(row_c)
        rows_precip.append(row_p)

df_heat   = pd.DataFrame(rows_heat)
df_cold   = pd.DataFrame(rows_cold)
df_precip = pd.DataFrame(rows_precip)

df_heat.to_csv(OUT / 'ph11_daily_heat.csv',   index=False, encoding='utf-8-sig')
df_cold.to_csv(OUT / 'ph11_daily_cold.csv',   index=False, encoding='utf-8-sig')
df_precip.to_csv(OUT / 'ph11_daily_precip.csv', index=False, encoding='utf-8-sig')

# Combined summary
df_all = df_heat.merge(df_cold.drop(columns=['Country']), on=['Site','Scenario']) \
                .merge(df_precip.drop(columns=['Country']), on=['Site','Scenario'])
df_all.to_csv(OUT / 'ph11_daily_summary.csv', index=False, encoding='utf-8-sig')

print("\n" + "="*60)
print("Phase 11 complete.")
for fn, df in [('ph11_daily_heat.csv',df_heat),('ph11_daily_cold.csv',df_cold),
               ('ph11_daily_precip.csv',df_precip),('ph11_daily_summary.csv',df_all)]:
    print(f"  {fn}: {df.shape}")

print("\n=== TX90p Days/yr (SSP5-8.5) ===")
cols = ['Site','TX90_base_C'] + [f'TX90p_{p}' for p in ['2020s','2050s','2090s']]
print(df_heat[df_heat['Scenario']=='SSP5-8.5'][cols].to_string(index=False, float_format='%.1f'))

print("\n=== Heatwave Duration HWD (SSP5-8.5) ===")
cols2 = ['Site'] + [f'HWD_{p}' for p in ['2020s','2050s','2090s']]
print(df_heat[df_heat['Scenario']=='SSP5-8.5'][cols2].to_string(index=False, float_format='%.1f'))

print("\n=== CDD Consecutive Dry Days (SSP5-8.5) ===")
cols3 = ['Site'] + [f'CDD_{p}' for p in ['2020s','2050s','2090s']]
print(df_precip[df_precip['Scenario']=='SSP5-8.5'][cols3].to_string(index=False, float_format='%.1f'))

print("\n=== R30mm Heavy Rain Days (SSP5-8.5) ===")
cols4 = ['Site'] + [f'R30mm_{p}' for p in ['2020s','2050s','2090s']]
print(df_precip[df_precip['Scenario']=='SSP5-8.5'][cols4].to_string(index=False, float_format='%.1f'))

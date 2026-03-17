# -*- coding: utf-8 -*-
"""
Phase 3: ETCCDI Indices — Full 4-SSP Set
Scenarios: SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5
Sites: 13 OCI facilities (Korea 7, China 4, Japan 1, Philippines 1)
"""
import warnings; warnings.filterwarnings('ignore')
import zipfile, io, numpy as np, pandas as pd, xarray as xr
from pathlib import Path

DAILY_BASE   = Path("c:/Users/24jos/climada/data/scenarios_v2/daily")
MONTHLY_BASE = Path("c:/Users/24jos/climada/data/scenarios_v2")
OUT = Path("c:/Users/24jos/climada/data/scenarios_v2/output")
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
    'korea_china': DAILY_BASE,
    'japan':       DAILY_BASE / 'japan',
    'philippines': DAILY_BASE / 'philippines',
}
MONTHLY_REGION_DIRS = {
    'korea_china': MONTHLY_BASE,
    'japan':       MONTHLY_BASE / 'japan',
    'philippines': MONTHLY_BASE / 'philippines',
}

SCENARIOS = ['ssp1_2_6', 'ssp2_4_5', 'ssp3_7_0', 'ssp5_8_5']
SCEN_LABELS = {
    'ssp1_2_6': 'SSP1-2.6',
    'ssp2_4_5': 'SSP2-4.5',
    'ssp3_7_0': 'SSP3-7.0',
    'ssp5_8_5': 'SSP5-8.5',
}

PERIODS = {
    '2020s': (2020, 2029),
    '2030s': (2030, 2039),
    '2040s': (2040, 2049),
    '2050s': (2050, 2059),
    '2060s': (2060, 2069),
    '2070s': (2070, 2079),
    '2080s': (2080, 2089),
    '2090s': (2090, 2099),
}

# ── Data loaders ─────────────────────────────────────────────────────────────

def load_daily(region, ssp, short, lat, lon):
    ssp_dir = REGION_DIRS[region] / ssp
    candidates = list(ssp_dir.glob(f"{short}_daily_{ssp}_*.zip"))
    if not candidates:
        return None
    try:
        zf = zipfile.ZipFile(candidates[0])
        nc_files = [n for n in zf.namelist() if n.endswith('.nc')]
        if not nc_files:
            return None
        series_list = []
        for nc in nc_files[:3]:
            try:
                with zf.open(nc) as f:
                    ds = xr.open_dataset(io.BytesIO(f.read()), use_cftime=True)
                lat_d = [d for d in ds.dims if 'lat' in d.lower()][0]
                lon_d = [d for d in ds.dims if 'lon' in d.lower()][0]
                dv = [v for v in ds.data_vars
                      if short.lower() in v.lower() or v.lower() == short.lower()][0]
                ds_pt = ds.sel({lat_d: lat, lon_d: lon}, method='nearest')
                ts = ds_pt[dv].to_series()
                try:
                    ts.index = pd.to_datetime(
                        [f"{t.year:04d}-{t.month:02d}-{t.day:02d}" for t in ts.index])
                except Exception:
                    ts.index = pd.to_datetime([str(t)[:10] for t in ts.index])
                if ts.mean() > 100:
                    ts = ts - 273.15
                elif ts.mean() < 0.01 and ts.mean() >= 0:
                    ts = ts * 86400
                series_list.append(ts)
            except Exception:
                continue
        zf.close()
        if not series_list:
            return None
        return pd.concat(series_list, axis=1).mean(axis=1)
    except Exception as e:
        print(f"    load_daily error ({short}): {e}")
        return None

def load_monthly_huss(region, ssp, lat, lon):
    ssp_dir = MONTHLY_REGION_DIRS[region] / ssp
    candidates = list(ssp_dir.glob("huss_*.zip"))
    if not candidates:
        return None
    try:
        zf = zipfile.ZipFile(candidates[0])
        nc_files = [n for n in zf.namelist() if n.endswith('.nc')]
        with zf.open(nc_files[0]) as f:
            ds = xr.open_dataset(io.BytesIO(f.read()), use_cftime=True)
        lat_d = [d for d in ds.dims if 'lat' in d.lower()][0]
        lon_d = [d for d in ds.dims if 'lon' in d.lower()][0]
        dv = [v for v in ds.data_vars if 'huss' in v.lower()][0]
        ds_pt = ds.sel({lat_d: lat, lon_d: lon}, method='nearest')
        ts = ds_pt[dv].to_series()
        try:
            ts.index = pd.to_datetime(
                [f"{t.year:04d}-{t.month:02d}-01" for t in ts.index])
        except Exception:
            ts.index = pd.to_datetime([str(t)[:7] + "-01" for t in ts.index])
        if ts.mean() < 1:
            ts = ts * 1000
        zf.close()
        return ts
    except Exception:
        return None

# ── ETCCDI index functions ────────────────────────────────────────────────────

def calc_TXx(tmax_daily):
    return tmax_daily.resample('ME').max()

def calc_TNn(tmin_daily):
    return tmin_daily.resample('ME').min()

def calc_SU(tmax_daily):
    return (tmax_daily > 25).resample('YE').sum()

def calc_TR(tmin_daily):
    return (tmin_daily > 20).resample('YE').sum()

def calc_FD(tmin_daily):
    return (tmin_daily < 0).resample('YE').sum()

def calc_WSDI(tmax_daily):
    base = tmax_daily[(tmax_daily.index.year >= 2015) & (tmax_daily.index.year <= 2044)]
    p90 = base.quantile(0.90)
    above = (tmax_daily > p90).astype(int)
    runs = above.rolling(6).sum()
    in_wsdi = (runs >= 6).astype(int)
    return in_wsdi.resample('YE').sum()

def calc_Rx1day(pr_daily):
    return pr_daily.resample('ME').max()

def calc_Rx5day(pr_daily):
    return pr_daily.rolling(5).sum().resample('ME').max()

def calc_SDII(pr_daily):
    wet = pr_daily[pr_daily >= 1.0]
    wet_sum = wet.resample('YE').sum()
    wet_cnt = (pr_daily >= 1.0).resample('YE').sum()
    return wet_sum / wet_cnt.replace(0, np.nan)

def calc_R95p(pr_daily):
    base = pr_daily[(pr_daily.index.year >= 2015) & (pr_daily.index.year <= 2044)]
    p95 = base[base >= 1.0].quantile(0.95)
    return pr_daily[pr_daily > p95].resample('YE').sum()

def calc_CDD(pr_daily):
    dry = (pr_daily < 1.0).astype(int)
    def max_run(s):
        max_c, cur = 0, 0
        for v in s:
            cur = cur + 1 if v else 0
            max_c = max(max_c, cur)
        return max_c
    return dry.resample('YE').apply(max_run)

def calc_CWD(pr_daily):
    wet = (pr_daily >= 1.0).astype(int)
    def max_run(s):
        max_c, cur = 0, 0
        for v in s:
            cur = cur + 1 if v else 0
            max_c = max(max_c, cur)
        return max_c
    return wet.resample('YE').apply(max_run)

def calc_WBGT(tmax_daily, huss_monthly_gkg):
    T = tmax_daily.resample('ME').mean()
    T.index = T.index.to_period('M').to_timestamp()
    huss_monthly_gkg.index = huss_monthly_gkg.index.to_period('M').to_timestamp()
    common = T.index.intersection(huss_monthly_gkg.index)
    T = T[common]
    q = huss_monthly_gkg[common]
    P = 1013.25
    e = q / 1000 * P / (0.622 + q / 1000)
    es = 6.112 * np.exp(17.67 * T / (T + 243.5))
    RH = np.clip(e / es * 100, 5, 100)
    Tw = T * np.arctan(0.151977 * (RH + 8.313659)**0.5) \
       + np.arctan(T + RH) \
       - np.arctan(RH - 1.676331) \
       + 0.00391838 * RH**1.5 * np.arctan(0.023101 * RH) \
       - 4.686035
    Tg = T + 2
    return 0.7 * Tw + 0.2 * Tg + 0.1 * T

def period_mean(ts, y1, y2):
    sub = ts[(ts.index.year >= y1) & (ts.index.year <= y2)]
    return float(sub.mean()) if len(sub) > 0 else np.nan

# ── Risk thresholds ───────────────────────────────────────────────────────────

THRESHOLDS = {
    'TXx (degC)':       {'low': 30, 'med': 35, 'high': 40},
    'SU (days/yr)':     {'low': 30, 'med': 60, 'high': 120},
    'TR (days/yr)':     {'low': 10, 'med': 30, 'high': 60},
    'FD (days/yr)':     {'low': 60, 'med': 30, 'high': 10},
    'WSDI (days/yr)':   {'low': 10, 'med': 20, 'high': 30},
    'Rx1day (mm)':      {'low': 30, 'med': 50, 'high': 80},
    'Rx5day (mm)':      {'low': 50, 'med': 100,'high': 150},
    'SDII (mm/wetday)': {'low': 10, 'med': 15, 'high': 20},
    'R95p (mm/yr)':     {'low': 200,'med': 400,'high': 600},
    'CDD (days)':       {'low': 20, 'med': 40, 'high': 60},
    'CWD (days)':       {'low': 10, 'med': 15, 'high': 20},
    'WBGT (degC)':      {'low': 25, 'med': 28, 'high': 32},
}

def risk_level(index_name, value):
    if value is None or np.isnan(value):
        return 'N/A'
    t = THRESHOLDS.get(index_name)
    if not t:
        return '-'
    if index_name == 'FD (days/yr)':
        if value <= t['high']: return 'High'
        if value <= t['med']:  return 'Med'
        return 'Low'
    if value >= t['high']: return 'High'
    if value >= t['med']:  return 'Med'
    if value >= t['low']:  return 'Low'
    return 'Safe'

# ── Main ─────────────────────────────────────────────────────────────────────

print("=" * 70)
print("Phase 3: ETCCDI Indices - 4-SSP Complete Set")
print("=" * 70)

all_rows = []

for site, (country, lat, lon, region) in SITES.items():
    print(f"\n[{site}]", flush=True)
    for ssp in SCENARIOS:
        lbl = SCEN_LABELS[ssp]
        tmax = load_daily(region, ssp, 'tasmax', lat, lon)
        tmin = load_daily(region, ssp, 'tasmin', lat, lon)
        pr   = load_daily(region, ssp, 'pr',     lat, lon)
        huss = load_monthly_huss(region, ssp, lat, lon)

        if tmax is None and tmin is None and pr is None:
            print(f"  {lbl}: no daily data, skip")
            continue

        row = {'Country': country, 'Site': site, 'Scenario': lbl}
        idx_series = {}

        if tmax is not None:
            idx_series['TXx (degC)']     = calc_TXx(tmax)
            idx_series['SU (days/yr)']   = calc_SU(tmax)
            idx_series['WSDI (days/yr)'] = calc_WSDI(tmax)
            if huss is not None:
                idx_series['WBGT (degC)'] = calc_WBGT(tmax, huss)
        if tmin is not None:
            idx_series['TNn (degC)']   = calc_TNn(tmin)
            idx_series['TR (days/yr)'] = calc_TR(tmin)
            idx_series['FD (days/yr)'] = calc_FD(tmin)
        if pr is not None:
            idx_series['Rx1day (mm)']      = calc_Rx1day(pr)
            idx_series['Rx5day (mm)']      = calc_Rx5day(pr)
            idx_series['SDII (mm/wetday)'] = calc_SDII(pr)
            idx_series['R95p (mm/yr)']     = calc_R95p(pr)
            idx_series['CDD (days)']       = calc_CDD(pr)
            idx_series['CWD (days)']       = calc_CWD(pr)

        for pd_lbl, (y1, y2) in PERIODS.items():
            for idx_name, ts in idx_series.items():
                val = period_mean(ts, y1, y2)
                row[f'{idx_name}|{pd_lbl}'] = round(val, 2) if not np.isnan(val) else None

        all_rows.append(row)
        print(f"  {lbl}: {len(idx_series)} indices computed", flush=True)

# Pivot to tidy format
df_raw = pd.DataFrame(all_rows)
tidy_rows = []
for _, r in df_raw.iterrows():
    for col in df_raw.columns:
        if '|' in col:
            idx_name, period = col.split('|', 1)
            tidy_rows.append({
                'Country':  r['Country'],
                'Site':     r['Site'],
                'Scenario': r['Scenario'],
                'Index':    idx_name,
                'Period':   period,
                'Value':    r[col],
                'Risk':     risk_level(idx_name, r[col]) if period == '2090s' else '-',
            })

df_tidy = pd.DataFrame(tidy_rows)
df_tidy.to_csv(str(OUT / 'ph3_etccdi_4ssp.csv'), index=False, encoding='utf-8-sig')

print("\n\n" + "=" * 70)
print("Phase 3 complete. Saved: ph3_etccdi_4ssp.csv")
print(f"Shape: {df_tidy.shape}")

# Quick summary: SSP5-8.5, 2090s
print("\n=== ETCCDI SSP5-8.5  2090s ===")
sub = df_tidy[(df_tidy['Scenario'] == 'SSP5-8.5') & (df_tidy['Period'] == '2090s')]
pivot = sub.pivot_table(index=['Country', 'Site'], columns='Index', values='Value', aggfunc='first')
pd.set_option('display.float_format', '{:.1f}'.format)
pd.set_option('display.max_columns', 20)
print(pivot.to_string())

# SSP spread comparison: TXx 2090s across all SSPs
print("\n=== TXx (degC) 2090s — SSP Spread ===")
txx = df_tidy[(df_tidy['Index'] == 'TXx (degC)') & (df_tidy['Period'] == '2090s')]
pivot2 = txx.pivot_table(index=['Country', 'Site'], columns='Scenario', values='Value', aggfunc='first')
print(pivot2.to_string())

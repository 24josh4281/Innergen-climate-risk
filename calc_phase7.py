# -*- coding: utf-8 -*-
"""
Phase 7: Threshold Exceedance Years
  A. Temperature threshold crossing: when does annual mean first exceed baseline+1.5/2/3/4 C?
  B. TXx (monthly Tmax proxy) threshold: first decade mean > 35 / 37 / 40 C
  C. Tropical Night threshold: monthly Tmin > 20C fraction approaching 100%
  D. Frost Day disappearance: last decade with FD > 10 days/yr
  E. Extreme precip threshold: Rx1day proxy > 80mm / 100mm
  F. CDD threshold: first decade CDD > 2000 / 3000 days

Outputs:
  ph7_exceedance_years.csv  — 13 sites x 4 SSP x N thresholds
  ph7_warming_timeline.csv  — Year when +1.5/2/3/4C first exceeded (rolling 10yr)
"""
import warnings; warnings.filterwarnings('ignore')
import zipfile, io, numpy as np, pandas as pd, xarray as xr
from pathlib import Path
from scipy import stats

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

def load_annual(region, ssp, short, lat, lon, conv=lambda x: x, agg='mean'):
    """Load monthly data and aggregate to annual."""
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
        ts_monthly = pd.concat(series, axis=1).mean(axis=1)
        ts_monthly = conv(ts_monthly)
        if agg == 'mean':
            return ts_monthly.groupby(ts_monthly.index.year).mean()
        elif agg == 'max':
            return ts_monthly.groupby(ts_monthly.index.year).max()
        elif agg == 'min':
            return ts_monthly.groupby(ts_monthly.index.year).min()
        elif agg == 'sum':
            return ts_monthly.groupby(ts_monthly.index.year).sum()
    except:
        return None

def first_exceed_year(ts_annual, threshold, window=10, must_sustain=True):
    """
    Year when rolling 10-yr mean first permanently exceeds threshold.
    If must_sustain=False, return first year the rolling mean exceeds.
    Returns None if never exceeded.
    """
    if ts_annual is None or len(ts_annual) == 0:
        return None
    roll = ts_annual.rolling(window, min_periods=5).mean()
    exceed = roll[roll > threshold]
    if len(exceed) == 0:
        return None
    return int(exceed.index[0])

def last_below_year(ts_annual, threshold, window=10):
    """Last decade where rolling mean is still below threshold (e.g. FD disappearance)."""
    if ts_annual is None or len(ts_annual) == 0:
        return None
    roll = ts_annual.rolling(window, min_periods=5).mean()
    below = roll[roll > threshold]
    if len(below) == 0:
        return None
    return int(below.index[-1])

print("Phase 7: Threshold Exceedance Years")
print("="*60)

rows_exc = []
rows_warm = []

for site, (country, lat, lon, region) in SITES.items():
    print(f"  Processing: {site}")
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]

        # Load annual time series
        tas_a    = load_annual(region, ssp, 'tas',    lat, lon, conv=lambda x: x - 273.15, agg='mean')
        tasmax_a = load_annual(region, ssp, 'tasmax', lat, lon, conv=lambda x: x - 273.15, agg='max')
        tasmin_a = load_annual(region, ssp, 'tasmin', lat, lon, conv=lambda x: x - 273.15, agg='min')
        pr_a     = load_annual(region, ssp, 'pr',     lat, lon, conv=lambda x: x * 86400,  agg='max')  # daily max proxy
        prsn_a   = load_annual(region, ssp, 'prsn',   lat, lon, conv=lambda x: x * 86400 * 30, agg='sum')  # annual snowfall

        # Baseline: 2020-2029 mean
        def baseline(ts):
            if ts is None: return np.nan
            return float(ts[(ts.index >= 2020) & (ts.index <= 2029)].mean())

        tas_base = baseline(tas_a)

        row_exc = {'Country': country, 'Site': site, 'Scenario': scen}
        row_exc['Tmean_baseline_2020s'] = round(tas_base, 2) if not np.isnan(tas_base) else np.nan

        # A. Warming thresholds above 2020s baseline
        for dT in [1.5, 2.0, 3.0, 4.0]:
            if not np.isnan(tas_base):
                thresh = tas_base + dT
                yr = first_exceed_year(tas_a, thresh, window=10)
            else:
                yr = None
            row_exc[f'Warm+{dT}C_year'] = yr if yr else 'Never'

        # B. Absolute Tmax thresholds (annual max of monthly Tmax)
        for thresh in [35.0, 37.0, 40.0]:
            yr = first_exceed_year(tasmax_a, thresh, window=5)
            row_exc[f'TXx>{thresh}C_year'] = yr if yr else 'Never'

        # C. Tmin threshold (tropical nights proxy from monthly min)
        for thresh in [20.0, 22.0, 25.0]:
            yr = first_exceed_year(tasmin_a, thresh, window=10)
            row_exc[f'TNn_ann>{thresh}C_year'] = yr if yr else 'Never'

        # D. Frost disappearance: last year with annual min Tmin < 0°C
        if tasmin_a is not None:
            frost_yrs = tasmin_a[tasmin_a < 0.0]
            row_exc['LastFrost_year'] = int(frost_yrs.index[-1]) if len(frost_yrs) > 0 else 'None'
        else:
            row_exc['LastFrost_year'] = 'None'

        # E. Extreme precip proxy (monthly max daily rate mm/day)
        for thresh in [60.0, 80.0, 100.0]:
            yr = first_exceed_year(pr_a, thresh, window=5)
            row_exc[f'Prmax>{thresh}mm_year'] = yr if yr else 'Never'

        # F. Snowfall disappearance: last decade with annual snowfall > 10 mm
        if prsn_a is not None:
            snow_yrs = prsn_a[prsn_a > 10.0]
            row_exc['LastSnow>10mm_year'] = int(snow_yrs.index[-1]) if len(snow_yrs) > 0 else 'None'
        else:
            row_exc['LastSnow>10mm_year'] = 'None'

        rows_exc.append(row_exc)

        # Warming timeline: year-by-year rolling mean warming
        if tas_a is not None and not np.isnan(tas_base):
            roll_warm = tas_a.rolling(10, min_periods=5).mean() - tas_base
            for yr in range(2025, 2100, 5):
                if yr in roll_warm.index:
                    rows_warm.append({
                        'Country': country, 'Site': site, 'Scenario': scen,
                        'Year': yr, 'WarmingC': round(float(roll_warm.loc[yr]), 2)
                    })

df_exc = pd.DataFrame(rows_exc)
df_warm = pd.DataFrame(rows_warm)

df_exc.to_csv(OUT / 'ph7_exceedance_years.csv', index=False, encoding='utf-8-sig')
df_warm.to_csv(OUT / 'ph7_warming_timeline.csv', index=False, encoding='utf-8-sig')
print(f"\nph7_exceedance_years.csv  {df_exc.shape}")
print(f"ph7_warming_timeline.csv  {df_warm.shape}")

# Summary printout
print("\n=== WARMING THRESHOLD CROSSING (10yr rolling mean) ===")
cols_show = ['Country','Site','Scenario','Warm+1.5C_year','Warm+2.0C_year','Warm+3.0C_year','Warm+4.0C_year']
print(df_exc[cols_show].to_string(index=False))

print("\n=== TXx THRESHOLD CROSSING ===")
cols_txx = ['Country','Site','Scenario','TXx>35.0C_year','TXx>37.0C_year','TXx>40.0C_year']
print(df_exc[cols_txx].to_string(index=False))

print("\n=== LAST FROST YEAR ===")
cols_frost = ['Country','Site','Scenario','LastFrost_year','LastSnow>10mm_year']
ssp5 = df_exc[df_exc['Scenario']=='SSP5-8.5'][cols_frost]
print(ssp5.to_string(index=False))

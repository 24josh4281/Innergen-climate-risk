# -*- coding: utf-8 -*-
"""
Phase 1: Additional Climate Risk Indices (Monthly Data)
  A. CDD / HDD  (Cooling/Heating Degree Days)
  B. Humidex + Apparent Temperature
  C. SPI-3      (Standardized Precipitation Index, 3-month)
  D. FWI proxy  (Fire Weather Index approximation)
  E. P-E Balance (Precipitation - Evapotranspiration)
"""
import warnings; warnings.filterwarnings('ignore')
import zipfile, io, numpy as np, pandas as pd, xarray as xr
from pathlib import Path
from scipy.stats import norm

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
SCENARIOS = ['ssp2_4_5', 'ssp5_8_5']
SCEN_LABELS = {'ssp2_4_5': 'SSP2-4.5', 'ssp5_8_5': 'SSP5-8.5'}
PERIODS = {
    '2020s':(2020,2029),'2030s':(2030,2039),'2040s':(2040,2049),
    '2050s':(2050,2059),'2060s':(2060,2069),'2070s':(2070,2079),
    '2080s':(2080,2089),'2090s':(2090,2099)
}

# ── Helper: load monthly time series ────────────────────────────────────────
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

def period_mean(ts, y1, y2):
    if ts is None: return np.nan
    sub = ts[(ts.index.year >= y1) & (ts.index.year <= y2)]
    return float(sub.mean()) if len(sub) > 0 else np.nan

def period_sum(ts, y1, y2):
    if ts is None: return np.nan
    ann = ts.resample('YE').sum()
    sub = ann[(ann.index.year >= y1) & (ann.index.year <= y2)]
    return float(sub.mean()) if len(sub) > 0 else np.nan

DAYS_IN_MONTH = [31,28.25,31,30,31,30,31,31,30,31,30,31]

# ── A. CDD / HDD ─────────────────────────────────────────────────────────────
def calc_cdd_hdd(tas_monthly, base=18.0):
    """Monthly Tmean → annual CDD and HDD (degree-days, base 18°C)"""
    cdd_ann, hdd_ann = [], []
    for year, grp in tas_monthly.groupby(tas_monthly.index.year):
        if len(grp) < 12: continue
        grp = grp.sort_index()
        days = DAYS_IN_MONTH
        cdd = sum(max(0, t - base) * d for t, d in zip(grp.values, days))
        hdd = sum(max(0, base - t) * d for t, d in zip(grp.values, days))
        cdd_ann.append((year, cdd))
        hdd_ann.append((year, hdd))
    cdd_s = pd.Series({y: v for y, v in cdd_ann})
    hdd_s = pd.Series({y: v for y, v in hdd_ann})
    return cdd_s, hdd_s

# ── B. Humidex ───────────────────────────────────────────────────────────────
def huss_to_dewpoint(huss_gkg, T_C, P_hPa=1013.25):
    """Specific humidity (g/kg) → dew point (°C)"""
    q = huss_gkg / 1000
    e = q * P_hPa / (0.622 + q)  # actual vapor pressure (hPa)
    Td = (243.5 * np.log(e / 6.112)) / (17.67 - np.log(e / 6.112))
    return Td

def calc_humidex(T_C, Td_C):
    """Humidex (Environment Canada)"""
    e = 6.112 * np.exp(17.67 * Td_C / (Td_C + 243.5))
    return T_C + 0.5555 * (e - 10.0)

def humidex_risk(h):
    if h is None or np.isnan(h): return 'N/A'
    if h >= 54: return 'Extreme'
    if h >= 45: return 'Dangerous'
    if h >= 40: return 'Great Discomfort'
    if h >= 30: return 'Some Discomfort'
    return 'Comfortable'

def calc_apparent_temp(T_C, wind_ms, RH_pct):
    """Apparent Temperature — Australian Bureau of Meteorology"""
    e = RH_pct / 100 * 6.105 * np.exp(25.16 * (T_C - 273.15) / (T_C - 29.86)
                                       if T_C > 100 else
                                       25.16 * T_C / (T_C + 214.14))
    return T_C + 0.33 * e - 0.70 * wind_ms - 4.0

# ── C. SPI-3 ─────────────────────────────────────────────────────────────────
def calc_spi3(pr_monthly):
    """3-month Standardized Precipitation Index"""
    pr3 = pr_monthly.rolling(3).sum().dropna()
    # fit gamma (approximate via log-normal)
    log_p = np.log(pr3 + 0.001)
    mu, std = log_p.mean(), log_p.std()
    z = (log_p - mu) / std if std > 0 else pr3 * 0
    return z  # ~SPI (log-normal approximation)

# ── D. FWI Proxy ─────────────────────────────────────────────────────────────
def calc_fwi_proxy(T_C, RH_pct, wind_ms, pr_mmday):
    """
    Simplified monthly FWI proxy (0-100 scale).
    Based on: high temp, low RH, high wind, low precip → high fire risk.
    Not the full Canadian FWI (which needs daily data), but a standardized proxy.
    """
    # Normalise each factor [0-1], combine
    t_factor   = np.clip((T_C - 0)  / 40.0, 0, 1)    # 0°C→0, 40°C→1
    rh_factor  = np.clip((100 - RH_pct) / 100.0, 0, 1) # low RH = high risk
    wind_factor= np.clip(wind_ms / 15.0, 0, 1)         # 15 m/s → max
    pr_factor  = np.clip(1 - pr_mmday / 10.0, 0, 1)    # 0 rain = max
    fwi = 25 * t_factor + 30 * rh_factor + 20 * wind_factor + 25 * pr_factor
    return fwi  # 0-100

# ── Main Loop ────────────────────────────────────────────────────────────────
print("=" * 65)
print("Phase 1: Additional Climate Risk Indices")
print("  A.CDD/HDD  B.Humidex  C.SPI-3  D.FWI  E.P-E Balance")
print("=" * 65)

rows_cdd, rows_humidex, rows_spi, rows_fwi, rows_pe = [], [], [], [], []

for site, (country, lat, lon, region) in SITES.items():
    print(f"\n[{site}]")
    for ssp in SCENARIOS:
        lbl = SCEN_LABELS[ssp]
        tas    = load_var(region, ssp, 'tas',     lat, lon, lambda x: x - 273.15)
        huss   = load_var(region, ssp, 'huss',    lat, lon, lambda x: x * 1000)
        wind   = load_var(region, ssp, 'sfcWind', lat, lon)
        pr     = load_var(region, ssp, 'pr',      lat, lon, lambda x: x * 86400)
        evap   = load_var(region, ssp, 'evspsbl', lat, lon, lambda x: x * 86400)

        # A. CDD / HDD
        if tas is not None:
            cdd_s, hdd_s = calc_cdd_hdd(tas)
            row = {'Country': country, 'Site': site, 'Scenario': lbl}
            for pd_lbl, (y1, y2) in PERIODS.items():
                sub_cdd = cdd_s[(cdd_s.index >= y1) & (cdd_s.index <= y2)]
                sub_hdd = hdd_s[(hdd_s.index >= y1) & (hdd_s.index <= y2)]
                row[f'CDD_{pd_lbl}'] = round(float(sub_cdd.mean()), 1) if len(sub_cdd) > 0 else None
                row[f'HDD_{pd_lbl}'] = round(float(sub_hdd.mean()), 1) if len(sub_hdd) > 0 else None
            rows_cdd.append(row)

        # B. Humidex
        if tas is not None and huss is not None:
            Td = huss_to_dewpoint(huss, tas)
            HX = calc_humidex(tas, Td)
            row2 = {'Country': country, 'Site': site, 'Scenario': lbl}
            for pd_lbl, (y1, y2) in PERIODS.items():
                sub = HX[(HX.index.year >= y1) & (HX.index.year <= y2)]
                val = float(sub.mean()) if len(sub) > 0 else np.nan
                row2[f'Humidex_{pd_lbl}'] = round(val, 2)
            row2['Humidex_Risk_2090s'] = humidex_risk(row2.get('Humidex_2090s'))
            # Apparent Temperature (summer months June-Aug)
            if wind is not None:
                ts_align = pd.concat([tas, huss, wind], axis=1).dropna()
                ts_align.columns = ['T','H','W']
                RH_ts = np.clip(
                    (ts_align['H']/1000 * 1013.25 / (0.622 + ts_align['H']/1000))
                    / (6.112 * np.exp(17.67 * ts_align['T'] / (ts_align['T'] + 243.5))) * 100,
                    0, 100)
                AT = ts_align['T'] + 0.33 * (RH_ts / 100 * 6.105 *
                     np.exp(17.27 * ts_align['T'] / (ts_align['T'] + 237.7))) \
                     - 0.70 * ts_align['W'] - 4.0
                for pd_lbl, (y1, y2) in PERIODS.items():
                    sub = AT[(AT.index.year >= y1) & (AT.index.year <= y2)]
                    val = float(sub.mean()) if len(sub) > 0 else np.nan
                    row2[f'AT_{pd_lbl}'] = round(val, 2)
            rows_humidex.append(row2)

        # C. SPI-3
        if pr is not None:
            spi = calc_spi3(pr)
            row3 = {'Country': country, 'Site': site, 'Scenario': lbl}
            for pd_lbl, (y1, y2) in PERIODS.items():
                sub = spi[(spi.index.year >= y1) & (spi.index.year <= y2)]
                val = float(sub.mean()) if len(sub) > 0 else np.nan
                row3[f'SPI3_{pd_lbl}'] = round(val, 3)
            rows_spi.append(row3)

        # D. FWI proxy
        if tas is not None and huss is not None and wind is not None and pr is not None:
            ts4 = pd.concat([tas, huss, wind, pr], axis=1).dropna()
            ts4.columns = ['T','H','W','P']
            RH = np.clip(
                (ts4['H']/1000 * 1013.25 / (0.622 + ts4['H']/1000))
                / (6.112 * np.exp(17.67 * ts4['T'] / (ts4['T'] + 243.5))) * 100,
                0, 100)
            fwi = calc_fwi_proxy(ts4['T'], RH, ts4['W'], ts4['P'])
            row4 = {'Country': country, 'Site': site, 'Scenario': lbl}
            for pd_lbl, (y1, y2) in PERIODS.items():
                sub = fwi[(fwi.index.year >= y1) & (fwi.index.year <= y2)]
                val = float(sub.mean()) if len(sub) > 0 else np.nan
                row4[f'FWI_{pd_lbl}'] = round(val, 2)
            # Peak summer FWI (JJA mean)
            fwi_jja = fwi[fwi.index.month.isin([6,7,8])]
            for pd_lbl, (y1, y2) in PERIODS.items():
                sub = fwi_jja[(fwi_jja.index.year >= y1) & (fwi_jja.index.year <= y2)]
                val = float(sub.mean()) if len(sub) > 0 else np.nan
                row4[f'FWI_JJA_{pd_lbl}'] = round(val, 2)
            rows_fwi.append(row4)

        # E. P-E Balance
        if pr is not None and evap is not None:
            pe = pr - evap.reindex(pr.index).ffill()
            row5 = {'Country': country, 'Site': site, 'Scenario': lbl}
            for pd_lbl, (y1, y2) in PERIODS.items():
                sub = pe[(pe.index.year >= y1) & (pe.index.year <= y2)]
                val = float(sub.mean()) if len(sub) > 0 else np.nan
                row5[f'PE_{pd_lbl}'] = round(val, 3)
            rows_pe.append(row5)

        print(f"  {lbl}: OK")

# ── Save ─────────────────────────────────────────────────────────────────────
df_cdd  = pd.DataFrame(rows_cdd)
df_hx   = pd.DataFrame(rows_humidex)
df_spi  = pd.DataFrame(rows_spi)
df_fwi  = pd.DataFrame(rows_fwi)
df_pe   = pd.DataFrame(rows_pe)

df_cdd.to_csv( str(OUT / 'ph1_cdd_hdd.csv'),    index=False, encoding='utf-8-sig')
df_hx.to_csv(  str(OUT / 'ph1_humidex.csv'),     index=False, encoding='utf-8-sig')
df_spi.to_csv( str(OUT / 'ph1_spi3.csv'),        index=False, encoding='utf-8-sig')
df_fwi.to_csv( str(OUT / 'ph1_fwi.csv'),         index=False, encoding='utf-8-sig')
df_pe.to_csv(  str(OUT / 'ph1_pe_balance.csv'),  index=False, encoding='utf-8-sig')

print("\n\n" + "=" * 65)
print("Phase 1 complete. Files saved:")
print(f"  ph1_cdd_hdd.csv    {df_cdd.shape}")
print(f"  ph1_humidex.csv    {df_hx.shape}")
print(f"  ph1_spi3.csv       {df_spi.shape}")
print(f"  ph1_fwi.csv        {df_fwi.shape}")
print(f"  ph1_pe_balance.csv {df_pe.shape}")

# ── Quick summary print ───────────────────────────────────────────────────────
print("\n\n=== CDD/HDD SSP5-8.5 2090s ===")
sub = df_cdd[df_cdd['Scenario']=='SSP5-8.5'][['Country','Site','CDD_2090s','HDD_2090s']]
print(sub.to_string(index=False))

print("\n=== Humidex SSP5-8.5 2090s + Risk ===")
sub2 = df_hx[df_hx['Scenario']=='SSP5-8.5'][['Country','Site','Humidex_2020s','Humidex_2050s','Humidex_2090s','Humidex_Risk_2090s']]
print(sub2.to_string(index=False))

print("\n=== FWI Proxy SSP5-8.5 (Annual) 2090s ===")
sub3 = df_fwi[df_fwi['Scenario']=='SSP5-8.5'][['Country','Site','FWI_2020s','FWI_2050s','FWI_2090s','FWI_JJA_2090s']]
print(sub3.to_string(index=False))

print("\n=== P-E Balance SSP5-8.5 2090s (mm/day, +surplus/-deficit) ===")
sub4 = df_pe[df_pe['Scenario']=='SSP5-8.5'][['Country','Site','PE_2020s','PE_2050s','PE_2090s']]
print(sub4.to_string(index=False))

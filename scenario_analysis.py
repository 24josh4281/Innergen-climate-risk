# -*- coding: utf-8 -*-
"""
Climate Scenario Risk Analysis - scenarios_v2 edition
Supports multiple sites; default: Zaozhuang Chemical Complex
Usage:
  python scenario_analysis.py
  python scenario_analysis.py --lat 37.5 --lon 127.0 --name seoul_site
"""
import warnings; warnings.filterwarnings('ignore')
import argparse, zipfile, io, numpy as np, pandas as pd, xarray as xr
import matplotlib.pyplot as plt
from pathlib import Path

# ── 좌표 및 경로 설정 ─────────────────────────────────────────────────────
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--lat',    type=float, default=34.7979)
parser.add_argument('--lon',    type=float, default=117.2571)
parser.add_argument('--name',   type=str,   default='zaozhuang')
parser.add_argument('--region', type=str,   default='korea_china',
                    help='korea_china | japan | philippines')
args, _ = parser.parse_known_args()

LAT    = args.lat
LON    = args.lon
SITE   = args.name
REGION = args.region

# region별 데이터 경로 매핑
_REGION_DIRS = {
    'korea_china': Path("c:/Users/24jos/climada/data/scenarios_v2"),
    'japan':       Path("c:/Users/24jos/climada/data/scenarios_v2/japan"),
    'philippines': Path("c:/Users/24jos/climada/data/scenarios_v2/philippines"),
}
BASE = _REGION_DIRS.get(REGION, _REGION_DIRS['korea_china'])
OUT  = Path("c:/Users/24jos/climada/data/scenarios_v2/output")
OUT.mkdir(parents=True, exist_ok=True)

# ── 변수 정의: (단변수명, CDS 변수명, 단위변환 함수) ────────────────────────
CMIP6_VARS = {
    'tasmax':  ('daily_maximum_near_surface_air_temperature',          lambda x: x - 273.15),  # K -> C
    'tasmin':  ('daily_minimum_near_surface_air_temperature',          lambda x: x - 273.15),
    'tas':     ('near_surface_air_temperature',                        lambda x: x - 273.15),
    'pr':      ('precipitation',                                       lambda x: x * 86400),   # kg/m2/s -> mm/day
    'evspsbl': ('evaporation_including_sublimation_and_transpiration', lambda x: x * 86400),
    'prsn':    ('snowfall_flux',                                       lambda x: x * 86400),
    'sfcWind': ('near_surface_wind_speed',                             lambda x: x),            # m/s
    'zos':     ('sea_surface_height_above_geoid',                      lambda x: x * 100),      # m -> cm
    'mrro':    ('total_runoff',                                        lambda x: x * 86400),   # kg/m2/s -> mm/day
    'mrsos':   ('moisture_in_upper_portion_of_soil_column',            lambda x: x),            # kg/m2
    'huss':    ('near_surface_specific_humidity',                      lambda x: x * 1000),    # kg/kg -> g/kg
    'rsds':    ('surface_downwelling_shortwave_radiation',             lambda x: x),            # W/m2
}

SCENARIOS = ['ssp1_2_6', 'ssp2_4_5', 'ssp3_7_0', 'ssp5_8_5']
SCEN_LABELS = {
    'ssp1_2_6': 'SSP1-2.6',
    'ssp2_4_5': 'SSP2-4.5',
    'ssp3_7_0': 'SSP3-7.0',
    'ssp5_8_5': 'SSP5-8.5',
}
SCEN_COLORS = {
    'ssp1_2_6': '#4CAF50',
    'ssp2_4_5': '#2196F3',
    'ssp3_7_0': '#FF9800',
    'ssp5_8_5': '#F44336',
}

# ── 헬퍼: zip에서 해당 좌표 시계열 추출 ────────────────────────────────────
def extract_timeseries(zip_path, var_short):
    """zip 안의 모든 모델 nc를 읽어 LAT/LON 최근접 격자 월별 시계열 반환"""
    results = {}
    try:
        zf = zipfile.ZipFile(zip_path)
    except Exception as e:
        print(f"  zip open error: {e}")
        return None

    nc_files = [n for n in zf.namelist() if n.endswith('.nc')]
    for nc in nc_files:
        parts = nc.split('_')
        model = parts[2] if len(parts) > 2 else nc
        try:
            with zf.open(nc) as f:
                raw = io.BytesIO(f.read())
            try:
                ds = xr.open_dataset(raw, use_cftime=True)
            except Exception:
                raw.seek(0)
                ds = xr.open_dataset(raw, decode_times=False)

            lat_dims = [d for d in ds.dims if 'lat' in d.lower()]
            lon_dims = [d for d in ds.dims if 'lon' in d.lower()]

            if lat_dims and lon_dims:
                lat_d, lon_d = lat_dims[0], lon_dims[0]
                dvars = [v for v in ds.data_vars
                         if var_short.lower() in v.lower() or v.lower() == var_short.lower()]
                if not dvars:
                    continue
                dv = dvars[0]
                # 먼저 최근접 격자 시도
                ds_pt = ds.sel({lat_d: LAT, lon_d: LON}, method='nearest')
                ts = ds_pt[dv].to_series()
                # NaN만 있으면 (육지 변수의 해안 격자 문제) → 최근접 육지 격자 탐색
                if ts.isna().all():
                    da2d = ds[dv].isel(time=0).values
                    lats_arr = ds[lat_d].values
                    lons_arr = ds[lon_d].values
                    la, lo = np.meshgrid(lats_arr, lons_arr, indexing='ij')
                    dist = (la - LAT)**2 + (lo - LON)**2
                    dist_masked = np.where(np.isnan(da2d), np.inf, dist)
                    if dist_masked.min() < np.inf:
                        idx = np.unravel_index(dist_masked.argmin(), dist.shape)
                        ts = ds[dv].isel({lat_d: idx[0], lon_d: idx[1]}).to_series()
                        model_note = f"(land proxy {lats_arr[idx[0]]:.2f}N,{lons_arr[idx[1]]:.2f}E)"
                    else:
                        continue
            elif 'latitude' in ds.coords and 'longitude' in ds.coords:
                dvars = [v for v in ds.data_vars if var_short.lower() in v.lower()]
                if not dvars:
                    continue
                dist = (ds.latitude - LAT)**2 + (ds.longitude - LON)**2
                idx  = np.unravel_index(int(dist.values.argmin()), dist.shape)
                dims = list(ds[dvars[0]].dims)
                ts = ds[dvars[0]].isel({dims[1]: idx[0], dims[2]: idx[1]}).to_series()
            else:
                continue

            # cftime -> datetime 변환
            try:
                ts.index = pd.to_datetime(
                    [f"{t.year:04d}-{t.month:02d}-01" for t in ts.index]
                )
            except Exception:
                try:
                    ts.index = pd.to_datetime([str(t)[:10] for t in ts.index])
                except Exception:
                    # decode_times=False: 숫자 인덱스 처리
                    n = len(ts)
                    try:
                        start_year = int(nc.split('_')[-2][:4])
                    except Exception:
                        start_year = 2015
                    ts.index = pd.date_range(start=f'{start_year}-01', periods=n, freq='MS')

            results[model] = ts

        except Exception as e:
            print(f"    skip {model}: {e}")

    zf.close()
    if not results:
        return None

    series_list = []
    for model, ts in results.items():
        ts.name = model
        ts.index = pd.to_datetime(ts.index)
        series_list.append(ts)
    return pd.concat(series_list, axis=1)


def period_mean(df, y1, y2):
    if df is None: return np.nan
    df.index = pd.to_datetime(df.index)
    subset = df[(df.index.year >= y1) & (df.index.year <= y2)]
    return float(subset.values.mean()) if len(subset) > 0 else np.nan


# ── 데이터 로드 ────────────────────────────────────────────────────────────
print("=" * 65)
print(f"Climate Risk Analysis (scenarios_v2)")
print(f"Site: {SITE}  |  {LAT}N, {LON}E")
print("=" * 65)

data = {}  # data[ssp][short] = DataFrame(월별, columns=models)

for ssp in SCENARIOS:
    ssp_dir = BASE / ssp
    data[ssp] = {}
    label = SCEN_LABELS[ssp]

    for short in CMIP6_VARS:
        candidates = list(ssp_dir.glob(f"{short}_*.zip"))
        if not candidates:
            continue
        zip_path = candidates[0]
        print(f"  Loading [{label}] {short} ...", end=' ', flush=True)
        df = extract_timeseries(zip_path, short)
        if df is not None:
            _, conv = CMIP6_VARS[short]
            df = df.apply(conv)
            data[ssp][short] = df
            print(f"{len(df.columns)} models, {len(df)} months")
        else:
            print("no data")

# ── 10년 앙상블 평균 테이블 ────────────────────────────────────────────────
print("\n" + "=" * 65)
print("10-YEAR ENSEMBLE MEAN  (SSP2-4.5 | SSP5-8.5)")
print("=" * 65)

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

HAZARD_VARS = [
    ('Heat Wave (Tmax C)',       'tasmax'),
    ('Cold Wave (Tmin C)',       'tasmin'),
    ('Mean Temp (Tas C)',        'tas'),
    ('Heavy Rain (Pr mm/day)',   'pr'),
    ('Drought (Evap mm/day)',    'evspsbl'),
    ('Snowfall (Prsn mm/day)',   'prsn'),
    ('Wind Speed (m/s)',         'sfcWind'),
    ('Sea Level (cm)',           'zos'),
    ('Runoff (mrro mm/day)',     'mrro'),
    ('Soil Moisture (kg/m2)',    'mrsos'),
    ('Spec Humidity (g/kg)',     'huss'),
    ('Solar Rad (rsds W/m2)',    'rsds'),
]

all_rows = []
for hazard_label, short in HAZARD_VARS:
    print(f"\n[{hazard_label}]")
    header = f"{'Period':8s}" + "".join(f"{SCEN_LABELS[s]:>14s}" for s in SCENARIOS)
    print(header)
    print("-" * len(header))
    rows = {'hazard': hazard_label}
    for period_label, (y1, y2) in PERIODS.items():
        line = f"{period_label:8s}"
        for ssp in SCENARIOS:
            lbl = SCEN_LABELS[ssp]
            if short in data.get(ssp, {}):
                val = period_mean(data[ssp][short], y1, y2)
                line += f"{val:>14.3f}"
                rows[f"{lbl}_{period_label}"] = val
            else:
                line += f"{'N/A':>14s}"
        print(line)
    all_rows.append(rows)

# ── CSV 저장 ───────────────────────────────────────────────────────────────
df_out = pd.DataFrame(all_rows).set_index('hazard')
csv_path = OUT / f"scenario_risk_{SITE}.csv"
df_out.to_csv(str(csv_path))
print(f"\nCSV saved: {csv_path}")

# ── 시각화 ────────────────────────────────────────────────────────────────
print("\nGenerating plots...")

PLOT_ITEMS = [
    ('Mean Temperature (C)',    ['tas']),
    ('Max Temperature (C)',     ['tasmax']),
    ('Min Temperature (C)',     ['tasmin']),
    ('Precipitation (mm/day)',  ['pr']),
    ('Wind Speed (m/s)',        ['sfcWind']),
    ('Snowfall (mm/day)',       ['prsn']),
    ('Sea Level (cm)',          ['zos']),
    ('Runoff (mm/day)',         ['mrro']),
    ('Soil Moisture (kg/m2)',   ['mrsos']),
    ('Spec Humidity (g/kg)',    ['huss']),
    ('Evapotranspiration (mm/day)', ['evspsbl']),
    ('Solar Radiation (W/m2)',  ['rsds']),
]

fig, axes = plt.subplots(4, 3, figsize=(20, 18))
axes = axes.flatten()
fig.suptitle(
    f"Climate Risk Scenarios — {SITE.replace('_',' ').title()}\n"
    f"({LAT}N, {LON}E)  |  SSP2-4.5 / SSP5-8.5 (CMIP6, 7 models)",
    fontsize=13, fontweight='bold'
)

for ax, (title, shorts) in zip(axes, PLOT_ITEMS):
    plotted = False
    for short in shorts:
        for ssp in SCENARIOS:
            if short not in data.get(ssp, {}):
                continue
            df = data[ssp][short].copy()
            df.index = pd.to_datetime(df.index)
            annual = df.resample('YE').mean().mean(axis=1)
            smooth = annual.rolling(10, center=True).mean()
            ax.plot(annual.index.year, annual.values,
                    alpha=0.15, color=SCEN_COLORS[ssp], linewidth=0.8)
            ax.plot(smooth.index.year, smooth.values,
                    label=SCEN_LABELS[ssp], color=SCEN_COLORS[ssp], linewidth=2)
            plotted = True
    ax.set_title(title, fontsize=10)
    ax.set_xlabel('Year', fontsize=8)
    if plotted:
        ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.axvline(2050, color='gray', linestyle='--', alpha=0.4, linewidth=0.8)

plt.tight_layout()
plot_path = OUT / f"scenario_risk_{SITE}.png"
plt.savefig(str(plot_path), dpi=150, bbox_inches='tight')
plt.close()
print(f"Plot saved: {plot_path}")

print("\n" + "=" * 65)
print("Analysis complete.")
print(f"Output: {OUT}")
print("=" * 65)

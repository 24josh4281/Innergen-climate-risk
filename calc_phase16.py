# -*- coding: utf-8 -*-
"""
Phase 16: Scenario Divergence + Wind/Snow Risk

A. Scenario Divergence Analysis
   - Year when |SSP5 - SSP1| first exceeds 5/10/15 risk points
   - "Window of opportunity": decades where mitigation still makes >10pt difference
   - Compound effect: how much does SSP3-7.0 vs SSP2-4.5 differ?

B. Wind Risk (sfcWind monthly)
   - Annual max wind speed, 90th/95th pct
   - JJA wind speed (typhoon season proxy)
   - Gale days proxy: months with sfcWind > 8/10/12 m/s

C. Snow/Freeze Risk (prsn monthly)
   - Annual snowfall trend (decline -> reduced water storage risk)
   - DJF snowfall: last decade with meaningful snow (>50mm/yr)
   - Combined freeze-thaw risk for infrastructure

Outputs:
  ph16_divergence.csv       — SSP divergence crossing years
  ph16_wind_risk.csv        — Wind speed indices
  ph16_snow_risk.csv        — Snowfall/freeze indices
  ph16_divergence_plot.png
  ph16_wind_snow_plot.png
"""
import warnings; warnings.filterwarnings('ignore')
import zipfile, io, numpy as np, pandas as pd, xarray as xr
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path("c:/Users/24jos/climada/data/scenarios_v2")
OUT  = BASE / "output"

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
REGION_DIRS = {'korea_china': BASE, 'japan': BASE/'japan', 'philippines': BASE/'philippines'}
SCENARIOS = ['ssp1_2_6','ssp2_4_5','ssp3_7_0','ssp5_8_5']
SCEN_LABELS = {'ssp1_2_6':'SSP1-2.6','ssp2_4_5':'SSP2-4.5','ssp3_7_0':'SSP3-7.0','ssp5_8_5':'SSP5-8.5'}
PERIODS = {'2020s':(2020,2029),'2030s':(2030,2039),'2040s':(2040,2049),'2050s':(2050,2059),
           '2060s':(2060,2069),'2070s':(2070,2079),'2080s':(2080,2089),'2090s':(2090,2099)}
PERIOD_MID = {'2020s':2025,'2030s':2035,'2040s':2045,'2050s':2055,
              '2060s':2065,'2070s':2075,'2080s':2085,'2090s':2095}
SSP_COLORS = {'SSP1-2.6':'#2196F3','SSP2-4.5':'#4CAF50','SSP3-7.0':'#FF9800','SSP5-8.5':'#F44336'}
SITES_ORDER = list(SITES.keys())

def load_monthly(region, ssp, short, lat, lon, conv=lambda x: x):
    ssp_dir = REGION_DIRS[region] / ssp
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

# ── A. Scenario Divergence ────────────────────────────────────────────
print("Phase 16A: Scenario Divergence...")
ph8 = pd.read_csv(OUT/'ph8_risk_score.csv')

rows_div = []
for site in SITES_ORDER:
    country = ph8[ph8['Site']==site]['Country'].iloc[0]
    # Get risk scores per SSP × period
    scores = {}
    for ssp in ['SSP1-2.6','SSP2-4.5','SSP3-7.0','SSP5-8.5']:
        for period in PERIODS:
            r = ph8[(ph8['Site']==site)&(ph8['Scenario']==ssp)&(ph8['Period']==period)]
            scores[(ssp,period)] = float(r['RiskScore'].values[0]) if len(r)>0 else np.nan

    row = {'Country':country, 'Site':site}
    # SSP5 - SSP1 divergence crossing years
    for thresh in [5, 10, 15]:
        cross_yr = 2100
        for period in PERIODS:
            s5 = scores.get(('SSP5-8.5',period), np.nan)
            s1 = scores.get(('SSP1-2.6',period), np.nan)
            if not np.isnan(s5) and not np.isnan(s1) and (s5-s1) >= thresh:
                cross_yr = PERIOD_MID[period]
                break
        row[f'Div_SSP5_SSP1_{thresh}pt_yr'] = cross_yr

    # SSP3 - SSP2 gap at each period
    for period in PERIODS:
        s3 = scores.get(('SSP3-7.0',period), np.nan)
        s2 = scores.get(('SSP2-4.5',period), np.nan)
        row[f'Gap_SSP3_SSP2_{period}'] = round(s3-s2, 1) if not np.isnan(s3) and not np.isnan(s2) else np.nan

    # Risk at each SSP × 2090s
    for ssp_key, ssp_label in SCEN_LABELS.items():
        row[f'Risk2090_{ssp_label.replace("-","").replace(".","")}']=scores.get((ssp_label,'2090s'),np.nan)

    # Max divergence decade
    divs = []
    for period in PERIODS:
        s5 = scores.get(('SSP5-8.5',period), np.nan)
        s1 = scores.get(('SSP1-2.6',period), np.nan)
        divs.append((s5-s1) if not np.isnan(s5) and not np.isnan(s1) else np.nan)
    row['MaxDiv_SSP5_SSP1'] = round(max([d for d in divs if not np.isnan(d)], default=np.nan), 1)

    rows_div.append(row)

df_div = pd.DataFrame(rows_div)
df_div.to_csv(OUT/'ph16_divergence.csv', index=False, encoding='utf-8-sig')
print(f"  ph16_divergence.csv {df_div.shape}")

# ── B. Wind Risk ──────────────────────────────────────────────────────
print("Phase 16B: Wind Risk (sfcWind)...")
rows_wind = []
for site, (country, lat, lon, region) in SITES.items():
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        wind = load_monthly(region, ssp, 'sfcWind', lat, lon)
        row  = {'Country':country,'Site':site,'Scenario':scen}
        if wind is not None:
            # Base period stats
            base = wind[(wind.index.year>=2020)&(wind.index.year<=2039)]
            row['Wind_base_mean_ms']  = round(float(base.mean()),2)
            row['Wind_base_p90_ms']   = round(float(np.percentile(base.dropna(),90)),2)
            row['Wind_base_p95_ms']   = round(float(np.percentile(base.dropna(),95)),2)
        else:
            row['Wind_base_mean_ms'] = row['Wind_base_p90_ms'] = row['Wind_base_p95_ms'] = np.nan

        for period, (y1,y2) in PERIODS.items():
            sub = wind[(wind.index.year>=y1)&(wind.index.year<=y2)] if wind is not None else None
            if sub is not None and len(sub)>0:
                row[f'Wind_mean_{period}']  = round(float(sub.mean()),2)
                row[f'Wind_max_{period}']   = round(float(sub.max()),2)
                # JJA wind (typhoon/storm season)
                jja = sub[sub.index.month.isin([6,7,8])]
                row[f'Wind_JJA_{period}']   = round(float(jja.mean()),2) if len(jja)>0 else np.nan
                # Gale proxy: months > 8 m/s
                row[f'Gale8_months_{period}'] = int((sub>8).sum())
            else:
                row[f'Wind_mean_{period}'] = row[f'Wind_max_{period}'] = np.nan
                row[f'Wind_JJA_{period}']  = row[f'Gale8_months_{period}'] = np.nan
        rows_wind.append(row)

df_wind = pd.DataFrame(rows_wind)
df_wind.to_csv(OUT/'ph16_wind_risk.csv', index=False, encoding='utf-8-sig')
print(f"  ph16_wind_risk.csv {df_wind.shape}")

# ── C. Snow/Freeze Risk ───────────────────────────────────────────────
print("Phase 16C: Snow/Freeze Risk (prsn)...")
rows_snow = []
for site, (country, lat, lon, region) in SITES.items():
    for ssp in SCENARIOS:
        scen = SCEN_LABELS[ssp]
        prsn = load_monthly(region, ssp, 'prsn', lat, lon, conv=lambda x: x*86400*30)
        tas  = load_monthly(region, ssp, 'tas',  lat, lon, conv=lambda x: x-273.15)
        row  = {'Country':country,'Site':site,'Scenario':scen}
        for period, (y1,y2) in PERIODS.items():
            # Annual snowfall
            if prsn is not None:
                ann = prsn[(prsn.index.year>=y1)&(prsn.index.year<=y2)].groupby(prsn.index.year[prsn.index.year.isin(range(y1,y2+1))]).sum()
                row[f'Snow_annual_{period}_mm'] = round(float(ann.mean()),1) if len(ann)>0 else np.nan
                # DJF snowfall
                djf = prsn[(prsn.index.year>=y1)&(prsn.index.year<=y2)&prsn.index.month.isin([12,1,2])]
                djf_ann = djf.groupby(djf.index.year).sum() if len(djf)>0 else pd.Series(dtype=float)
                row[f'Snow_DJF_{period}_mm'] = round(float(djf_ann.mean()),1) if len(djf_ann)>0 else np.nan
            else:
                row[f'Snow_annual_{period}_mm'] = row[f'Snow_DJF_{period}_mm'] = np.nan
            # Freeze-thaw risk: months crossing 0 C (Tmin<0 but Tmax>0 proxy)
            if tas is not None:
                sub_t = tas[(tas.index.year>=y1)&(tas.index.year<=y2)]
                freeze_months = int((sub_t<0).sum())
                row[f'FreezeMonths_{period}'] = freeze_months
            else:
                row[f'FreezeMonths_{period}'] = np.nan
        rows_snow.append(row)

df_snow = pd.DataFrame(rows_snow)
df_snow.to_csv(OUT/'ph16_snow_risk.csv', index=False, encoding='utf-8-sig')
print(f"  ph16_snow_risk.csv {df_snow.shape}")

# ── Visualization 1: Divergence Plot ─────────────────────────────────
print("Generating divergence plots...")
fig, axes = plt.subplots(3, 5, figsize=(20, 12))
axes = axes.flatten()
for idx, site in enumerate(SITES_ORDER):
    if idx >= len(axes): break
    ax = axes[idx]
    for ssp_label, color in SSP_COLORS.items():
        xs, ys = [], []
        for period in PERIODS:
            r = ph8[(ph8['Site']==site)&(ph8['Scenario']==ssp_label)&(ph8['Period']==period)]
            if len(r)>0:
                xs.append(PERIOD_MID[period])
                ys.append(float(r['RiskScore'].values[0]))
        if xs: ax.plot(xs, ys, color=color, linewidth=2, marker='o', markersize=3, label=ssp_label)
    ax.fill_between(
        [PERIOD_MID[p] for p in PERIODS if len(ph8[(ph8['Site']==site)&(ph8['Scenario']=='SSP1-2.6')&(ph8['Period']==p)])>0],
        [float(ph8[(ph8['Site']==site)&(ph8['Scenario']=='SSP1-2.6')&(ph8['Period']==p)]['RiskScore'].values[0])
         for p in PERIODS if len(ph8[(ph8['Site']==site)&(ph8['Scenario']=='SSP1-2.6')&(ph8['Period']==p)])>0],
        [float(ph8[(ph8['Site']==site)&(ph8['Scenario']=='SSP5-8.5')&(ph8['Period']==p)]['RiskScore'].values[0])
         for p in PERIODS if len(ph8[(ph8['Site']==site)&(ph8['Scenario']=='SSP5-8.5')&(ph8['Period']==p)])>0],
        alpha=0.1, color='grey', label='SSP1-5 gap'
    )
    ax.axhline(50, color='orange', linestyle=':', linewidth=0.8, alpha=0.6)
    ax.set_title(site.replace(' Plant','').replace(' OCI',''), fontsize=8, fontweight='bold')
    ax.set_ylim(20, 80); ax.set_xlim(2020, 2100)
    ax.set_xticks([2030,2060,2090]); ax.set_xticklabels(['30','60','90'],fontsize=7)
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=6, loc='upper left')
for idx in range(len(SITES_ORDER), len(axes)): axes[idx].set_visible(False)
plt.suptitle('OCI Climate Risk Scenario Divergence (SSP1 vs SSP5 gap = mitigation benefit)',
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT/'ph16_divergence_plot.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph16_divergence_plot.png saved")

# ── Visualization 2: Wind + Snow ──────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(16, 10))

# Top-left: Wind mean SSP5-8.5 trend
ax = axes[0,0]
site_colors = plt.cm.tab20(np.linspace(0,1,13))
for si, site in enumerate(SITES_ORDER):
    sub = df_wind[(df_wind['Site']==site)&(df_wind['Scenario']=='SSP5-8.5')]
    if len(sub)==0: continue
    xs = [PERIOD_MID[p] for p in PERIODS]; ys = [float(sub[f'Wind_mean_{p}'].values[0]) for p in PERIODS]
    ax.plot(xs, ys, color=site_colors[si], linewidth=1.5, label=site.replace(' Plant','').replace(' OCI',''))
ax.set_title('Mean Wind Speed Trend (SSP5-8.5)', fontsize=9, fontweight='bold')
ax.set_ylabel('m/s'); ax.legend(fontsize=5, ncol=2); ax.grid(alpha=0.3)

# Top-right: Wind 2090s comparison 4 SSPs (select sites)
ax2 = axes[0,1]
key_sites = ['HQ Seoul','Pohang Plant','OCI Shanghai','Philko Makati','OCI Japan Tokyo']
x = np.arange(len(key_sites)); w = 0.18
for i, ssp in enumerate(SCEN_LABELS.keys()):
    scen = SCEN_LABELS[ssp]
    vals = [float(df_wind[(df_wind['Site']==s)&(df_wind['Scenario']==scen)]['Wind_max_2090s'].values[0])
            if len(df_wind[(df_wind['Site']==s)&(df_wind['Scenario']==scen)])>0 else 0 for s in key_sites]
    ax2.bar(x+i*w, vals, width=w, label=scen, color=list(SSP_COLORS.values())[i], alpha=0.8)
ax2.set_xticks(x+1.5*w); ax2.set_xticklabels([s.replace(' Plant','').replace(' OCI','') for s in key_sites], rotation=20, ha='right', fontsize=8)
ax2.set_ylabel('Monthly Max Wind (m/s)'); ax2.set_title('Peak Wind Speed 2090s (4 SSP)', fontsize=9, fontweight='bold')
ax2.legend(fontsize=7); ax2.grid(axis='y', alpha=0.3)

# Bottom-left: Annual snowfall trend SSP5-8.5
ax3 = axes[1,0]
snow_sites = ['HQ Seoul','Pohang Plant','Shandong OCI (ZZ)','OCI Japan Tokyo']
for si, site in enumerate(snow_sites):
    sub = df_snow[(df_snow['Site']==site)&(df_snow['Scenario']=='SSP5-8.5')]
    if len(sub)==0: continue
    xs = [PERIOD_MID[p] for p in PERIODS]
    ys = [float(sub[f'Snow_annual_{p}_mm'].values[0]) if f'Snow_annual_{p}_mm' in sub.columns else np.nan for p in PERIODS]
    ax3.plot(xs, ys, marker='o', markersize=4, linewidth=2, label=site.replace(' Plant',''), color=site_colors[si*3])
ax3.set_title('Annual Snowfall Trend (SSP5-8.5)', fontsize=9, fontweight='bold')
ax3.set_ylabel('Snowfall (mm/yr)'); ax3.legend(fontsize=8); ax3.grid(alpha=0.3)
ax3.set_xlabel('Year')

# Bottom-right: Freeze months decline
ax4 = axes[1,1]
for si, site in enumerate(snow_sites):
    sub = df_snow[(df_snow['Site']==site)&(df_snow['Scenario']=='SSP5-8.5')]
    if len(sub)==0: continue
    xs = [PERIOD_MID[p] for p in PERIODS]
    ys = [float(sub[f'FreezeMonths_{p}'].values[0]) if f'FreezeMonths_{p}' in sub.columns else np.nan for p in PERIODS]
    ax4.plot(xs, ys, marker='s', markersize=4, linewidth=2, label=site.replace(' Plant',''), color=site_colors[si*3])
ax4.set_title('Freeze Months Decline (SSP5-8.5)', fontsize=9, fontweight='bold')
ax4.set_ylabel('Months/decade with T<0'); ax4.legend(fontsize=8); ax4.grid(alpha=0.3)
ax4.set_xlabel('Year')

plt.suptitle('OCI Wind Risk & Snow/Freeze Risk Analysis', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT/'ph16_wind_snow_plot.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph16_wind_snow_plot.png saved")

print("\n=== SCENARIO DIVERGENCE (SSP5-SSP1 gap crossing years) ===")
print(df_div[['Country','Site','Div_SSP5_SSP1_5pt_yr','Div_SSP5_SSP1_10pt_yr','MaxDiv_SSP5_SSP1']].to_string(index=False))

print("\n=== WIND RISK SSP5-8.5 2090s (top 5 sites) ===")
w_sub = df_wind[(df_wind['Scenario']=='SSP5-8.5')][['Country','Site','Wind_mean_2090s','Wind_max_2090s','Wind_JJA_2090s']].sort_values('Wind_max_2090s', ascending=False).head(8)
print(w_sub.to_string(index=False, float_format='%.2f'))

print("\nPhase 16 complete.")

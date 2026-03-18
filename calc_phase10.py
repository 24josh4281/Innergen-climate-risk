# -*- coding: utf-8 -*-
"""
Phase 10: Master Consolidation + Final Visualizations
  - Merges all Phase 1-9 outputs into OCI_MASTER_ALL.csv
  - Generates executive summary visualizations
  - Produces CHANGELOG entry
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap

OUT = Path("c:/Users/24jos/climada/data/scenarios_v2/output")

SITES_ORDER = [
    'HQ Seoul','R&D Seongnam','Pohang Plant','Gunsan Plant','Iksan Plant',
    'Gwangyang Plant','Saehan Jeongeup',
    'OCI Shanghai','Shandong OCI (ZZ)','MaSteel OCI (MAS)','Jianyang Carbon (ZZ)',
    'OCI Japan Tokyo','Philko Makati'
]
SCENARIOS = ['SSP1-2.6','SSP2-4.5','SSP3-7.0','SSP5-8.5']
PERIODS   = ['2020s','2030s','2040s','2050s','2060s','2070s','2080s','2090s']

# ── Load all phase outputs ────────────────────────────────────────────────
print("Loading phase outputs...")
ph1_cdd  = pd.read_csv(OUT / 'ph1_cdd_hdd.csv')
ph1_hum  = pd.read_csv(OUT / 'ph1_humidex.csv')
ph1_spi  = pd.read_csv(OUT / 'ph1_spi3.csv')
ph1_fwi  = pd.read_csv(OUT / 'ph1_fwi.csv')
ph1_pe   = pd.read_csv(OUT / 'ph1_pe_balance.csv')
ph3      = pd.read_csv(OUT / 'ph3_etccdi_4ssp.csv')
ph4_rp   = pd.read_csv(OUT / 'ph4_return_period.csv')
ph4_ce   = pd.read_csv(OUT / 'ph4_compound_events.csv')
ph6_temp = pd.read_csv(OUT / 'ph6_seasonal_temp.csv')
ph6_prec = pd.read_csv(OUT / 'ph6_seasonal_precip.csv')
ph6_heat = pd.read_csv(OUT / 'ph6_heat_stress.csv')
ph7_exc  = pd.read_csv(OUT / 'ph7_exceedance_years.csv')
ph7_warm = pd.read_csv(OUT / 'ph7_warming_timeline.csv')
ph8_risk = pd.read_csv(OUT / 'ph8_risk_score.csv')
ph9_ro   = pd.read_csv(OUT / 'ph9_runoff.csv')
ph9_sm   = pd.read_csv(OUT / 'ph9_soilmoisture.csv')
ph9_sol  = pd.read_csv(OUT / 'ph9_solar.csv')
ph9_ws   = pd.read_csv(OUT / 'ph9_water_stress.csv')
print("  All files loaded.")

# ── Build one master row per (Site, Scenario, Period) ─────────────────────
print("Building master table...")
rows = []
for ssp in SCENARIOS:
    ssp_key = ssp.lower().replace('-','_').replace('.','_')  # e.g. ssp1_2_6

    for period in PERIODS:
        for site in SITES_ORDER:
            def fv(df, col, site_col='Site', scen_col='Scenario'):
                r = df[(df[site_col]==site) & (df[scen_col]==ssp)]
                if len(r) == 0: return np.nan
                if col not in r.columns: return np.nan
                v = r[col].values[0]
                try: return float(v)
                except: return np.nan  # 'Never', 'None' etc.

            def fv_period(df, col_template, site_col='Site', scen_col='Scenario'):
                col = col_template.format(period=period)
                r = df[(df[site_col]==site) & (df[scen_col]==ssp)]
                if len(r) == 0: return np.nan
                return float(r[col].values[0]) if col in r.columns else np.nan

            def etccdi_val(index_name):
                r = ph3[(ph3['Site']==site) & (ph3['Scenario']==ssp) & (ph3['Period']==period) & (ph3['Index']==index_name)]
                return float(r['Value'].values[0]) if len(r) > 0 else np.nan

            country = ph3[ph3['Site']==site]['Country'].iloc[0] if len(ph3[ph3['Site']==site])>0 else ''

            row = {
                # Identity
                'Country': country, 'Site': site, 'Scenario': ssp, 'Period': period,
                # ── ETCCDI (Ph3) ──
                'TXx_degC':        etccdi_val('TXx (degC)'),
                'TNn_degC':        etccdi_val('TNn (degC)'),
                'SU_days':         etccdi_val('SU (days/yr)'),
                'TR_days':         etccdi_val('TR (days/yr)'),
                'FD_days':         etccdi_val('FD (days/yr)'),
                'WSDI_days':       etccdi_val('WSDI (days/yr)'),
                'Rx1day_mm':       etccdi_val('Rx1day (mm)'),
                'Rx5day_mm':       etccdi_val('Rx5day (mm)'),
                'SDII_mmday':      etccdi_val('SDII (mm/day)'),
                'R95p_mmyr':       etccdi_val('R95p (mm/yr)'),
                'CDD_etccdi_days': etccdi_val('CDD (days)'),
                'CWD_days':        etccdi_val('CWD (days)'),
                'WBGT_degC':       etccdi_val('WBGT (degC)'),
                # ── Phase 1 ──
                'CDD_heat_degdays': fv_period(ph1_cdd, 'CDD_{period}'),
                'HDD_heat_degdays': fv_period(ph1_cdd, 'HDD_{period}'),
                'Humidex_degC':    fv_period(ph1_hum, 'Humidex_{period}'),
                'AppTemp_degC':    fv_period(ph1_hum, 'AppTemp_{period}'),
                'SPI3':            fv_period(ph1_spi, 'SPI3_{period}') if ssp in ['SSP2-4.5','SSP5-8.5'] else np.nan,
                'FWI_annual':      fv_period(ph1_fwi, 'FWI_{period}'),
                'FWI_JJA':         fv_period(ph1_fwi, 'FWI_JJA_{period}'),
                'PE_balance_mm':   fv_period(ph1_pe, 'PE_{period}') if ssp in ['SSP2-4.5','SSP5-8.5'] else np.nan,
                # ── Phase 4 ──
                'RL10yr_near_mm':  fv(ph4_rp, 'RL10yr_near_mm') if period in ['2020s','2030s','2040s','2050s'] else np.nan,
                'RL50yr_near_mm':  fv(ph4_rp, 'RL50yr_near_mm') if period in ['2020s','2030s','2040s','2050s'] else np.nan,
                'RL100yr_near_mm': fv(ph4_rp, 'RL100yr_near_mm') if period in ['2020s','2030s','2040s','2050s'] else np.nan,
                'RL10yr_far_mm':   fv(ph4_rp, 'RL10yr_far_mm') if period in ['2060s','2070s','2080s','2090s'] else np.nan,
                'RL100yr_far_mm':  fv(ph4_rp, 'RL100yr_far_mm') if period in ['2060s','2070s','2080s','2090s'] else np.nan,
                'CompoundDays_pct': fv(ph4_ce, 'CompoundDays_pct_near') if period in ['2020s','2030s','2040s','2050s']
                                    else fv(ph4_ce, 'CompoundDays_pct_far') if ssp in ['SSP2-4.5','SSP5-8.5'] else np.nan,
                # ── Phase 6 (Seasonal) ──
                'Tmax_JJA_degC':   fv_period(ph6_temp, 'Tmax_JJA_{period}'),
                'Tmin_DJF_degC':   fv_period(ph6_temp, 'Tmin_DJF_{period}'),
                'Tmean_JJA_degC':  fv_period(ph6_temp, 'Tmean_JJA_{period}'),
                'Pr_JJA_mm':       fv_period(ph6_prec, 'Pr_JJA_{period}_mm'),
                'Pr_DJF_mm':       fv_period(ph6_prec, 'Pr_DJF_{period}_mm'),
                'Snow_DJF_mm':     fv_period(ph6_prec, 'Snow_DJF_{period}_mm'),
                'WBGT_JJA_degC':   fv_period(ph6_heat, 'WBGT_JJA_{period}'),
                'Humidex_JJA_degC':fv_period(ph6_heat, 'Humidex_JJA_{period}'),
                'DI_JJA':          fv_period(ph6_heat, 'DI_JJA_{period}'),
                # ── Phase 7 ──
                'Warm_plus15C_yr': fv(ph7_exc, 'Warm+1.5C_year'),
                'Warm_plus20C_yr': fv(ph7_exc, 'Warm+2.0C_year'),
                'Warm_plus30C_yr': fv(ph7_exc, 'Warm+3.0C_year'),
                'Warm_plus40C_yr': fv(ph7_exc, 'Warm+4.0C_year'),
                'TXx_35C_yr':      fv(ph7_exc, 'TXx>35.0C_year'),
                'TXx_40C_yr':      fv(ph7_exc, 'TXx>40.0C_year'),
                # ── Phase 8 ──
                'D1_Heat':         fv_period(ph8_risk.rename(columns={'Period':'_period_'}), 'D1_Heat') if False else
                                   float(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)]['D1_Heat'].values[0])
                                   if len(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)])>0 else np.nan,
                'D2_Precip':       float(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)]['D2_Precip'].values[0])
                                   if len(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)])>0 else np.nan,
                'D3_Cold':         float(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)]['D3_Cold'].values[0])
                                   if len(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)])>0 else np.nan,
                'D4_Drought':      float(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)]['D4_Drought'].values[0])
                                   if len(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)])>0 else np.nan,
                'RiskScore_0_100': float(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)]['RiskScore'].values[0])
                                   if len(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)])>0 else np.nan,
                'RiskTier':        ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)]['RiskTier'].values[0]
                                   if len(ph8_risk[(ph8_risk['Site']==site)&(ph8_risk['Scenario']==ssp)&(ph8_risk['Period']==period)])>0 else '',
                # ── Phase 9 ──
                'Runoff_annual_mm':fv_period(ph9_ro, 'Runoff_annual_{period}_mm'),
                'Runoff_JJA_mm':   fv_period(ph9_ro, 'Runoff_JJA_{period}_mm'),
                'SoilMoist_JJA':   fv_period(ph9_sm, 'SM_JJA_{period}_kgm2'),
                'SM_deficit_pct':  fv_period(ph9_sm, 'SM_deficit_{period}'),
                'Solar_annual_kWhm2d': fv_period(ph9_sol, 'Solar_annual_{period}_kWhm2d'),
                'Solar_JJA_Wm2':   fv_period(ph9_sol, 'Solar_JJA_{period}_Wm2'),
                'DroughtStress':   fv_period(ph9_ws, 'DroughtStress_{period}'),
            }
            rows.append(row)

df_master = pd.DataFrame(rows)
df_master.to_csv(OUT / 'OCI_MASTER_ALL.csv', index=False, encoding='utf-8-sig')
print(f"OCI_MASTER_ALL.csv: {df_master.shape}")
print(f"  {df_master.shape[1]} variables x {df_master.shape[0]} rows")
print(f"  (13 sites x 4 SSP x 8 periods = {13*4*8} rows)")

# ── Visualization 1: 4SSP Risk Score bar chart (2090s) ───────────────────
print("\nGenerating 4SSP Risk Bar Chart...")
SSP_COLORS = {'SSP1-2.6':'#2196F3','SSP2-4.5':'#4CAF50','SSP3-7.0':'#FF9800','SSP5-8.5':'#F44336'}
sub = df_master[df_master['Period']=='2090s'][['Site','Scenario','RiskScore_0_100']].copy()
pivot = sub.pivot(index='Site', columns='Scenario', values='RiskScore_0_100').reindex(SITES_ORDER)

fig, ax = plt.subplots(figsize=(14, 6))
x = np.arange(len(SITES_ORDER))
w = 0.2
for i, ssp in enumerate(SCENARIOS):
    bars = ax.bar(x + i*w, pivot[ssp], width=w, label=ssp,
                  color=SSP_COLORS[ssp], edgecolor='white', linewidth=0.5)
    for bar in bars:
        h = bar.get_height()
        if not np.isnan(h):
            ax.text(bar.get_x()+bar.get_width()/2, h+0.5, f'{h:.0f}',
                    ha='center', va='bottom', fontsize=5.5, rotation=90)

ax.axhline(65, color='red', linestyle='--', linewidth=1, alpha=0.7, label='High Risk threshold (65)')
ax.axhline(50, color='orange', linestyle=':', linewidth=1, alpha=0.6, label='Medium threshold (50)')
ax.set_xticks(x + 1.5*w)
ax.set_xticklabels([s.replace(' Plant','').replace(' OCI','') for s in SITES_ORDER],
                    rotation=35, ha='right', fontsize=8)
ax.set_ylabel('Climate Risk Score (0-100)', fontsize=10)
ax.set_ylim(0, 105)
ax.legend(fontsize=8, loc='upper left')
ax.set_title('OCI Climate Risk Score by Site & Scenario — 2090s Projection\n(Weighted composite: Heat 25%, Precip 18%, Drought 14%, Compound 14%, ...)',
             fontsize=10, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / 'ph10_risk_bar_2090s.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph10_risk_bar_2090s.png")

# ── Visualization 2: Key metrics trend 2020s→2090s (SSP5-8.5) ────────────
print("Generating trend summary chart...")
metrics = {
    'TXx (degC)':       ('TXx_degC',       'Peak Temp TXx (°C)'),
    'Tropical Nights':  ('TR_days',         'Tropical Nights (days/yr)'),
    'Heavy Precip R95p':('R95p_mmyr',       'R95p Heavy Precip (mm/yr)'),
    'JJA WBGT':         ('WBGT_JJA_degC',   'JJA WBGT (°C)'),
    'Annual Runoff':    ('Runoff_annual_mm', 'Annual Runoff (mm/yr)'),
    'Risk Score':       ('RiskScore_0_100',  'Climate Risk Score'),
}
period_yrs = {'2020s':2025,'2030s':2035,'2040s':2045,'2050s':2055,
              '2060s':2065,'2070s':2075,'2080s':2085,'2090s':2095}
ssp585 = df_master[df_master['Scenario']=='SSP5-8.5']
site_colors = plt.cm.tab20(np.linspace(0, 1, 13))

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()

for ax_i, (label, (col, ylabel)) in enumerate(metrics.items()):
    ax = axes[ax_i]
    for s_i, site in enumerate(SITES_ORDER):
        sd = ssp585[ssp585['Site']==site].sort_values('Period')
        xs = [period_yrs[p] for p in sd['Period'] if p in period_yrs]
        ys = [float(sd[sd['Period']==p][col].values[0]) if col in sd.columns and len(sd[sd['Period']==p])>0 else np.nan
              for p in sd['Period'] if p in period_yrs]
        ys = [y for y in ys if not np.isnan(y)]
        if len(xs) != len(ys):
            xs = xs[:len(ys)]
        ax.plot(xs, ys, color=site_colors[s_i], linewidth=1.5, alpha=0.8,
                label=site.replace(' Plant','').replace(' OCI','') if ax_i==0 else '')
    ax.set_title(label, fontsize=9, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_xlim(2020, 2100)
    ax.set_xticks([2030, 2060, 2090])
    ax.grid(alpha=0.3)

axes[0].legend(fontsize=6, loc='upper left', ncol=2)
plt.suptitle('OCI Climate Risk Key Metrics — SSP5-8.5 Trajectory (2020-2100)', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'ph10_trend_summary.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph10_trend_summary.png")

# ── Visualization 3: Exceedance Year summary heatmap ─────────────────────
print("Generating exceedance year heatmap...")
exc_cols = {
    '+1.5C': 'Warm_plus15C_yr', '+2.0C': 'Warm_plus20C_yr',
    '+3.0C': 'Warm_plus30C_yr', '+4.0C': 'Warm_plus40C_yr',
    'TXx>35': 'TXx_35C_yr', 'TXx>40': 'TXx_40C_yr',
}
master_exc = df_master[df_master['Period']=='2090s'][['Site','Scenario']+list(exc_cols.values())].drop_duplicates()

fig, axes = plt.subplots(1, 4, figsize=(20, 6), sharey=True)
cmap_exc = LinearSegmentedColormap.from_list('exc', ['#1a9641','#fdae61','#d7191c'])

for ax, ssp in zip(axes, SCENARIOS):
    sub = master_exc[master_exc['Scenario']==ssp].set_index('Site').reindex(SITES_ORDER)
    mat = np.zeros((len(SITES_ORDER), len(exc_cols)))
    for j, col in enumerate(exc_cols.values()):
        for i, site in enumerate(SITES_ORDER):
            val = sub.loc[site, col] if site in sub.index else np.nan
            try:
                mat[i, j] = float(val)
            except:
                mat[i, j] = 2100  # "Never"

    im = ax.imshow(mat, cmap=cmap_exc, vmin=2025, vmax=2100, aspect='auto')
    ax.set_xticks(range(len(exc_cols)))
    ax.set_xticklabels(list(exc_cols.keys()), rotation=45, ha='right', fontsize=8)
    ax.set_title(ssp, fontsize=10, fontweight='bold')
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            raw = mat[i,j]
            if np.isnan(raw): label, color = 'N/A', 'grey'
            else:
                v = int(raw)
                label = 'Never' if v >= 2099 else str(v)
                color = 'white' if v > 2080 else 'black'
            ax.text(j, i, label, ha='center', va='center', fontsize=6.5, color=color)
    if ax == axes[0]:
        ax.set_yticks(range(len(SITES_ORDER)))
        ax.set_yticklabels(SITES_ORDER, fontsize=8)

plt.colorbar(im, ax=axes[-1], label='Year of threshold exceedance', shrink=0.8)
plt.suptitle('OCI Climate Threshold Crossing Years — 4 SSP Scenarios\n(earlier = more urgent risk)',
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'ph10_exceedance_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph10_exceedance_heatmap.png")

# ── Final summary printout ────────────────────────────────────────────────
print("\n" + "="*70)
print("PHASE 10 COMPLETE — OCI Climate Risk Analysis Master Dataset")
print("="*70)
print(f"\nOCI_MASTER_ALL.csv: {df_master.shape[0]} rows x {df_master.shape[1]} columns")
print(f"Coverage: 13 sites x 4 SSPs x 8 decades = {13*4*8} observations")
print(f"Variables: {df_master.shape[1]-4} climate indicators per observation")

print("\n--- TOP RISK SITES (SSP5-8.5, 2090s) ---")
top = df_master[(df_master['Scenario']=='SSP5-8.5')&(df_master['Period']=='2090s')]\
      [['Country','Site','RiskScore_0_100','RiskTier','TXx_degC','WBGT_JJA_degC',
        'TR_days','R95p_mmyr','Runoff_annual_mm']].sort_values('RiskScore_0_100',ascending=False)
print(top.to_string(index=False, float_format='%.1f'))

print("\n--- SCENARIO SPREAD (2090s mean across all sites) ---")
spread = df_master[df_master['Period']=='2090s'].groupby('Scenario')['RiskScore_0_100'].agg(['mean','min','max'])
print(spread.round(1).to_string())

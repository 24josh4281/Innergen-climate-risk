# -*- coding: utf-8 -*-
"""
Phase 14: Executive Summary
  - Per-site one-pager: Top 5 risks, key numbers, action year
  - Portfolio-level risk dashboard PNG
  - Final master executive CSV

Outputs:
  ph14_executive_summary.csv   -- one row per site, all key KPIs
  ph14_executive_dashboard.png -- 2x2 dashboard: risk ranking, EAL, urgency, mitigation
  ph14_site_onepagers.png      -- 13-panel per-site summary cards
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch

OUT = Path("c:/Users/24jos/climada/data/scenarios_v2/output")

SITES_ORDER = [
    'HQ Seoul','R&D Seongnam','Pohang Plant','Gunsan Plant','Iksan Plant',
    'Gwangyang Plant','Saehan Jeongeup',
    'OCI Shanghai','Shandong OCI (ZZ)','MaSteel OCI (MAS)','Jianyang Carbon (ZZ)',
    'OCI Japan Tokyo','Philko Makati'
]
ASSET_VALUES = {
    'HQ Seoul':1500,'R&D Seongnam':500,'Pohang Plant':2000,'Gunsan Plant':1200,
    'Iksan Plant':800,'Gwangyang Plant':1800,'Saehan Jeongeup':600,
    'OCI Shanghai':800,'Shandong OCI (ZZ)':500,'MaSteel OCI (MAS)':400,
    'Jianyang Carbon (ZZ)':350,'OCI Japan Tokyo':200,'Philko Makati':100,
}
SSP_COLORS = {'SSP1-2.6':'#2196F3','SSP2-4.5':'#4CAF50','SSP3-7.0':'#FF9800','SSP5-8.5':'#F44336'}

# Load all relevant files
ph8  = pd.read_csv(OUT / 'ph8_risk_score.csv')
ph11h= pd.read_csv(OUT / 'ph11_daily_heat.csv')
ph11p= pd.read_csv(OUT / 'ph11_daily_precip.csv')
ph12 = pd.read_csv(OUT / 'ph12_eal.csv')
ph12f= pd.read_csv(OUT / 'ph12_disruption.csv')
ph13 = pd.read_csv(OUT / 'ph13_urgency.csv')
ph13m= pd.read_csv(OUT / 'ph13_mitigation_benefit.csv')
ph7  = pd.read_csv(OUT / 'ph7_exceedance_years.csv')
ph6h = pd.read_csv(OUT / 'ph6_heat_stress.csv')
ph9r = pd.read_csv(OUT / 'ph9_runoff.csv')

def g(df, site, ssp, col, period=None):
    r = df[df['Site']==site] if 'Scenario' not in df.columns else df[(df['Site']==site)&(df['Scenario']==ssp)]
    if period and 'Period' in r.columns: r = r[r['Period']==period]
    if len(r)==0 or col not in r.columns: return np.nan
    v = r[col].values[0]
    try: return float(v)
    except: return str(v)

# ── Build executive summary (one row per site, SSP5-8.5 focus) ──────────
print("Building executive summary...")
rows = []
for site in SITES_ORDER:
    ssp = 'SSP5-8.5'
    country = ph8[ph8['Site']==site]['Country'].iloc[0]
    asset = ASSET_VALUES[site]

    # Risk scores
    r20 = g(ph8, site, ssp, 'RiskScore', '2020s')
    r50 = g(ph8, site, ssp, 'RiskScore', '2050s')
    r90 = g(ph8, site, ssp, 'RiskScore', '2090s')
    tier = g(ph8, site, ssp, 'RiskTier', '2090s')

    # Threshold years
    warm15 = g(ph7, site, ssp, 'Warm+1.5C_year')
    warm20 = g(ph7, site, ssp, 'Warm+2.0C_year')
    txx35  = g(ph7, site, ssp, 'TXx>35.0C_year')

    # Heat stress
    wbgt90 = g(ph6h, site, ssp, 'WBGT_JJA_2090s')
    tx90p_90 = g(ph11h, site, ssp, 'TX90p_2090s')
    hwd90   = g(ph11h, site, ssp, 'HWD_2090s')
    tx35_90 = g(ph11h, site, ssp, 'TX35_2090s')

    # Precip/flood
    cdd90   = g(ph11p, site, ssp, 'CDD_2090s')
    r30_90  = g(ph11p, site, ssp, 'R30mm_2090s')
    rx1_90  = g(ph11p, site, ssp, 'Rx1day_2090s')
    runoff90= g(ph9r, site, ssp, 'Runoff_annual_2090s_mm')

    # Financial
    eal90   = g(ph12, site, ssp, 'EAL_USDM_yr', '2090s')
    eal_cum = g(ph12, site, ssp, 'EAL_cumulative_10yr_USDM', '2090s')
    bid90   = g(ph12f, site, ssp, 'BID_days_yr', '2090s')
    bid_pct = g(ph12f, site, ssp, 'BID_loss_pct_revenue', '2090s')

    # Urgency & mitigation
    urg = g(ph13, site, ssp, 'Urgency_Score')
    cross50 = g(ph13, site, ssp, 'Cross_50_yr')
    mit_eal = g(ph13m, site, 'SSP5-8.5', 'EAL_Saved_USDM_yr', '2090s') if 'Scenario' not in ph13m.columns else \
              ph13m[(ph13m['Site']==site)&(ph13m['Period']=='2090s')]['EAL_Saved_USDM_yr'].values[0] \
              if len(ph13m[(ph13m['Site']==site)&(ph13m['Period']=='2090s')])>0 else np.nan

    # Top 5 risks (narrative)
    risks = []
    if not np.isnan(wbgt90) and wbgt90 > 33: risks.append(f'Extreme heat (WBGT {wbgt90:.1f}C JJA)')
    if not np.isnan(tx35_90) and tx35_90 > 20: risks.append(f'Heat days >35C: {tx35_90:.0f} days/yr')
    if not np.isnan(hwd90) and hwd90 > 10: risks.append(f'Heatwave duration: {hwd90:.0f} days max')
    if not np.isnan(rx1_90) and rx1_90 > 150: risks.append(f'Extreme rain Rx1day: {rx1_90:.0f} mm')
    if not np.isnan(r30_90) and r30_90 > 15: risks.append(f'Heavy rain R30mm: {r30_90:.0f} days/yr')
    if not np.isnan(cdd90) and cdd90 > 35: risks.append(f'Consecutive dry: {cdd90:.0f} days max')
    if not np.isnan(runoff90) and runoff90 > 800: risks.append(f'Flood runoff: {runoff90:.0f} mm/yr')
    if not np.isnan(bid90) and bid90 > 40: risks.append(f'Disruption: {bid90:.0f} days/yr')
    risks = risks[:5]
    while len(risks) < 5: risks.append('N/A')

    rows.append({
        'Country': country, 'Site': site, 'Asset_USDM': asset,
        # Risk trajectory
        'RiskScore_2020s': round(r20,1) if not np.isnan(r20) else np.nan,
        'RiskScore_2050s': round(r50,1) if not np.isnan(r50) else np.nan,
        'RiskScore_2090s': round(r90,1) if not np.isnan(r90) else np.nan,
        'RiskTier_2090s': tier,
        # Key physical metrics (SSP5-8.5, 2090s)
        'WBGT_JJA_2090s': round(wbgt90,1) if not np.isnan(wbgt90) else np.nan,
        'TX90p_days_2090s': round(tx90p_90,0) if not np.isnan(tx90p_90) else np.nan,
        'HWD_days_2090s': round(hwd90,0) if not np.isnan(hwd90) else np.nan,
        'TX35_days_2090s': round(tx35_90,0) if not np.isnan(tx35_90) else np.nan,
        'Rx1day_mm_2090s': round(rx1_90,0) if not np.isnan(rx1_90) else np.nan,
        'R30mm_days_2090s': round(r30_90,0) if not np.isnan(r30_90) else np.nan,
        'CDD_days_2090s': round(cdd90,0) if not np.isnan(cdd90) else np.nan,
        'Runoff_mm_2090s': round(runoff90,0) if not np.isnan(runoff90) else np.nan,
        # Threshold years
        'Warm_1p5C_year': warm15, 'Warm_2p0C_year': warm20, 'TXx35_year': txx35,
        # Financial
        'EAL_USDM_yr_2090s': round(eal90,3) if not np.isnan(eal90) else np.nan,
        'EAL_cum10yr_USDM': round(eal_cum,1) if not np.isnan(eal_cum) else np.nan,
        'BID_days_yr_2090s': round(bid90,1) if not np.isnan(bid90) else np.nan,
        'BID_revenue_loss_pct': round(bid_pct,1) if not np.isnan(bid_pct) else np.nan,
        # Urgency
        'Urgency_Score': round(urg,1) if not np.isnan(urg) else np.nan,
        'Cross_Risk50_year': int(cross50) if not np.isnan(cross50) else np.nan,
        'EAL_Saved_Mitigation_USDM_yr': round(float(mit_eal),3) if not np.isnan(float(mit_eal)) else np.nan,
        # Top risks
        'Top1_Risk': risks[0], 'Top2_Risk': risks[1], 'Top3_Risk': risks[2],
        'Top4_Risk': risks[3], 'Top5_Risk': risks[4],
    })

df_exec = pd.DataFrame(rows)
df_exec.to_csv(OUT / 'ph14_executive_summary.csv', index=False, encoding='utf-8-sig')
print(f"ph14_executive_summary.csv: {df_exec.shape}")
print()
print(df_exec[['Country','Site','RiskScore_2020s','RiskScore_2090s','RiskTier_2090s',
               'EAL_USDM_yr_2090s','BID_days_yr_2090s','Urgency_Score','Top1_Risk']].to_string(index=False))

# ── Dashboard PNG ─────────────────────────────────────────────────────
print("\nGenerating executive dashboard...")
fig = plt.figure(figsize=(20, 14))
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

PERIODS = ['2020s','2030s','2040s','2050s','2060s','2070s','2080s','2090s']
PERIOD_MID = {'2020s':2025,'2030s':2035,'2040s':2045,'2050s':2055,
              '2060s':2065,'2070s':2075,'2080s':2085,'2090s':2095}

# Panel 1: Risk Score Ranking (SSP5-8.5 2090s)
ax1 = fig.add_subplot(gs[0, 0])
df_sort = df_exec.sort_values('RiskScore_2090s', ascending=True)
colors_bar = ['#F44336' if t=='High' else '#FF9800' if t=='Medium-High'
              else '#FFC107' if t=='Medium' else '#8BC34A' for t in df_sort['RiskTier_2090s']]
bars = ax1.barh(df_sort['Site'].str.replace(' Plant','').str.replace(' OCI',''),
                df_sort['RiskScore_2090s'], color=colors_bar, edgecolor='white')
for bar, val in zip(bars, df_sort['RiskScore_2090s']):
    ax1.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
             f'{val:.0f}', va='center', fontsize=8)
ax1.axvline(65, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax1.axvline(50, color='orange', linestyle='--', alpha=0.5, linewidth=1)
ax1.set_xlabel('Risk Score (0-100)', fontsize=9)
ax1.set_title('Climate Risk Ranking (SSP5-8.5, 2090s)', fontsize=10, fontweight='bold')
ax1.set_xlim(0, 90)

# Panel 2: EAL comparison (SSP2 vs SSP5, 2090s)
ax2 = fig.add_subplot(gs[0, 1])
sites_short = [s.replace(' Plant','').replace(' OCI','') for s in SITES_ORDER]
x = np.arange(len(SITES_ORDER))
w = 0.35
for i, ssp in enumerate(['SSP2-4.5','SSP5-8.5']):
    vals = [float(ph12[(ph12['Site']==s)&(ph12['Scenario']==ssp)&(ph12['Period']=='2090s')]['EAL_USDM_yr'].values[0])
            if len(ph12[(ph12['Site']==s)&(ph12['Scenario']==ssp)&(ph12['Period']=='2090s')])>0 else 0
            for s in SITES_ORDER]
    ax2.bar(x+i*w, vals, width=w, label=ssp, color=SSP_COLORS[ssp], alpha=0.85)
ax2.set_xticks(x+w/2)
ax2.set_xticklabels(sites_short, rotation=40, ha='right', fontsize=7)
ax2.set_ylabel('EAL (USD M/yr)', fontsize=9)
ax2.set_title('Expected Annual Loss by Site (2090s)', fontsize=10, fontweight='bold')
ax2.legend(fontsize=8)
ax2.grid(axis='y', alpha=0.3)

# Panel 3: Business Interruption Days (SSP5-8.5 trajectory)
ax3 = fig.add_subplot(gs[1, 0])
site_colors = plt.cm.tab20(np.linspace(0, 1, 13))
for si, site in enumerate(SITES_ORDER):
    xs, ys = [], []
    for period in PERIODS:
        r = ph12f[(ph12f['Site']==site)&(ph12f['Scenario']=='SSP5-8.5')&(ph12f['Period']==period)]
        if len(r)>0:
            xs.append(PERIOD_MID[period])
            ys.append(float(r['BID_days_yr'].values[0]))
    ax3.plot(xs, ys, color=site_colors[si], linewidth=1.5,
             label=site.replace(' Plant','').replace(' OCI',''))
ax3.axhline(30, color='orange', linestyle='--', alpha=0.5, linewidth=1)
ax3.axhline(50, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax3.set_xlabel('Year', fontsize=9)
ax3.set_ylabel('Business Interruption Days/yr', fontsize=9)
ax3.set_title('Climate Disruption Days Trajectory (SSP5-8.5)', fontsize=10, fontweight='bold')
ax3.legend(fontsize=5, ncol=2, loc='upper left')
ax3.grid(alpha=0.3)
ax3.set_xlim(2020, 2100)

# Panel 4: Mitigation benefit (savings from SSP5->SSP1)
ax4 = fig.add_subplot(gs[1, 1])
mit_sub = ph13m[ph13m['Period']=='2090s'][['Site','EAL_Saved_10yr_USDM']].sort_values('EAL_Saved_10yr_USDM', ascending=True)
colors_mit = ['#E91E63' if v > 20 else '#FF9800' if v > 10 else '#8BC34A'
              for v in mit_sub['EAL_Saved_10yr_USDM']]
ax4.barh(mit_sub['Site'].str.replace(' Plant','').str.replace(' OCI',''),
         mit_sub['EAL_Saved_10yr_USDM'], color=colors_mit, edgecolor='white')
ax4.set_xlabel('EAL Saved over 10 yrs (USD M) — SSP5 vs SSP1', fontsize=9)
ax4.set_title('Mitigation Benefit by Site (2090s decade)', fontsize=10, fontweight='bold')
ax4.grid(axis='x', alpha=0.3)

total_saved = mit_sub['EAL_Saved_10yr_USDM'].sum()
ax4.set_title(f'Mitigation Benefit (SSP5->SSP1, 2090s)\nPortfolio total: USD {total_saved:.0f}M over 10 yrs',
              fontsize=9, fontweight='bold')

plt.suptitle('OCI CLIMATE PHYSICAL RISK — EXECUTIVE DASHBOARD (SSP5-8.5 Baseline)\nAll projections: CMIP6 7-model ensemble, 2020-2100',
             fontsize=13, fontweight='bold', y=1.01)
plt.savefig(OUT / 'ph14_executive_dashboard.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph14_executive_dashboard.png saved")

print("\nPhase 14 complete.")
print(f"  ph14_executive_summary.csv: {df_exec.shape}")
print(f"  ph14_executive_dashboard.png")

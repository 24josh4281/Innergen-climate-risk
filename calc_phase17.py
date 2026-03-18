# -*- coding: utf-8 -*-
"""
Phase 17: Country Aggregation + Site Summary Cards

A. Country-level aggregate risk
   - Korea (7 sites), China (4), Japan (1), Philippines (1)
   - Asset-weighted average risk score
   - Total EAL per country
   - Country risk comparison bar + radar

B. Per-site comprehensive summary cards (13 panels)
   - Key metrics: Risk score, Top3 physical hazards, EAL, BID, action year
   - Color-coded by risk tier
   - All 13 sites on one page

Outputs:
  ph17_country_aggregate.csv
  ph17_country_comparison.png
  ph17_site_cards.png
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
COUNTRIES = {'Korea':['HQ Seoul','R&D Seongnam','Pohang Plant','Gunsan Plant','Iksan Plant','Gwangyang Plant','Saehan Jeongeup'],
             'China':['OCI Shanghai','Shandong OCI (ZZ)','MaSteel OCI (MAS)','Jianyang Carbon (ZZ)'],
             'Japan':['OCI Japan Tokyo'],'Philippines':['Philko Makati']}
SCENARIOS = ['SSP1-2.6','SSP2-4.5','SSP3-7.0','SSP5-8.5']
PERIODS   = ['2020s','2030s','2040s','2050s','2060s','2070s','2080s','2090s']
PERIOD_MID= {'2020s':2025,'2030s':2035,'2040s':2045,'2050s':2055,
             '2060s':2065,'2070s':2075,'2080s':2085,'2090s':2095}
SSP_COLORS = {'SSP1-2.6':'#2196F3','SSP2-4.5':'#4CAF50','SSP3-7.0':'#FF9800','SSP5-8.5':'#F44336'}
TIER_COLORS = {'Low':'#1a9641','Medium-Low':'#a6d96a','Medium':'#ffffbf',
               'Medium-High':'#fdae61','High':'#d7191c','Extreme':'#7b0000'}

ph8  = pd.read_csv(OUT/'ph8_risk_score.csv')
ph12e= pd.read_csv(OUT/'ph12_eal.csv')
ph12d= pd.read_csv(OUT/'ph12_disruption.csv')
ph14 = pd.read_csv(OUT/'ph14_executive_summary.csv')
ph13 = pd.read_csv(OUT/'ph13_urgency.csv')

# ── A. Country Aggregate ─────────────────────────────────────────────
print("Phase 17A: Country aggregate risk...")
rows_country = []
for country, sites in COUNTRIES.items():
    total_asset = sum(ASSET_VALUES[s] for s in sites)
    for ssp in SCENARIOS:
        for period in PERIODS:
            # Asset-weighted risk score
            weighted_risk, total_w = 0.0, 0.0
            for site in sites:
                r = ph8[(ph8['Site']==site)&(ph8['Scenario']==ssp)&(ph8['Period']==period)]
                if len(r)>0:
                    w = ASSET_VALUES[site]
                    weighted_risk += float(r['RiskScore'].values[0]) * w
                    total_w += w
            avg_risk = weighted_risk/total_w if total_w>0 else np.nan

            # Total EAL
            total_eal = 0.0
            for site in sites:
                r = ph12e[(ph12e['Site']==site)&(ph12e['Scenario']==ssp)&(ph12e['Period']==period)]
                if len(r)>0: total_eal += float(r['EAL_USDM_yr'].values[0])

            # Avg BID
            bids = []
            for site in sites:
                r = ph12d[(ph12d['Site']==site)&(ph12d['Scenario']==ssp)&(ph12d['Period']==period)]
                if len(r)>0: bids.append(float(r['BID_days_yr'].values[0]))
            avg_bid = float(np.mean(bids)) if bids else np.nan

            rows_country.append({
                'Country':country, 'Scenario':ssp, 'Period':period,
                'TotalAsset_USDM':total_asset, 'NumSites':len(sites),
                'WeightedRiskScore':round(avg_risk,1) if not np.isnan(avg_risk) else np.nan,
                'TotalEAL_USDM_yr':round(total_eal,3),
                'AvgBID_days_yr':round(avg_bid,1) if not np.isnan(avg_bid) else np.nan,
                'EAL_pct_assets':round(total_eal/total_asset*100,4),
            })

df_country = pd.DataFrame(rows_country)
df_country.to_csv(OUT/'ph17_country_aggregate.csv', index=False, encoding='utf-8-sig')
print(f"  ph17_country_aggregate.csv {df_country.shape}")

print("\n=== COUNTRY RISK (SSP5-8.5, 2090s) ===")
c_show = df_country[(df_country['Scenario']=='SSP5-8.5')&(df_country['Period']=='2090s')]\
         [['Country','TotalAsset_USDM','WeightedRiskScore','TotalEAL_USDM_yr','AvgBID_days_yr']]
print(c_show.to_string(index=False, float_format='%.2f'))

# ── B. Country Comparison Plot ───────────────────────────────────────
print("\nPhase 17B: Country comparison plot...")
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Panel 1: Country risk score trajectory
ax1 = axes[0,0]
c_colors = {'Korea':'#2196F3','China':'#F44336','Japan':'#4CAF50','Philippines':'#FF9800'}
for country, color in c_colors.items():
    for ssp, ls in [('SSP1-2.6','--'),('SSP5-8.5','-')]:
        sub = df_country[(df_country['Country']==country)&(df_country['Scenario']==ssp)].sort_values('Period')
        xs = [PERIOD_MID[p] for p in sub['Period']]
        ys = sub['WeightedRiskScore'].values
        lw = 2.5 if ssp=='SSP5-8.5' else 1.2
        label = f'{country} ({ssp})' if ssp=='SSP5-8.5' else None
        ax1.plot(xs, ys, color=color, linestyle=ls, linewidth=lw, label=label, alpha=0.9)
ax1.set_title('Country Risk Score Trajectory\n(solid=SSP5-8.5, dashed=SSP1-2.6)', fontsize=9, fontweight='bold')
ax1.set_ylabel('Asset-weighted Risk Score')
ax1.legend(fontsize=8); ax1.grid(alpha=0.3); ax1.set_xlim(2020,2100)

# Panel 2: Total EAL by country (stacked bar, SSP5-8.5, 2090s)
ax2 = axes[0,1]
x = np.arange(4); w = 0.35
countries = list(COUNTRIES.keys())
for i, ssp in enumerate(['SSP2-4.5','SSP5-8.5']):
    vals = [float(df_country[(df_country['Country']==c)&(df_country['Scenario']==ssp)&(df_country['Period']=='2090s')]['TotalEAL_USDM_yr'].values[0])
            for c in countries]
    ax2.bar(x+i*w, vals, width=w, label=ssp, color=SSP_COLORS[ssp], alpha=0.85)
    for xi, v in zip(x+i*w, vals):
        ax2.text(xi, v+0.02, f'{v:.2f}', ha='center', va='bottom', fontsize=8)
ax2.set_xticks(x+w/2); ax2.set_xticklabels(countries, fontsize=9)
ax2.set_ylabel('Total EAL (USD M/yr)')
ax2.set_title('Country Total EAL — 2090s', fontsize=9, fontweight='bold')
ax2.legend(fontsize=8); ax2.grid(axis='y', alpha=0.3)

# Panel 3: Country radar
ax3 = fig.add_subplot(2, 2, 3, polar=True)  # replace with polar
ax3.remove()
ax3 = fig.add_subplot(2, 2, 3, polar=True)
dim_labels = ['Heat','Precip','Cold','Drought','Compound','Energy','Fire','Flood']
dim_cols   = ['D1_Heat','D2_Precip','D3_Cold','D4_Drought','D5_Compound','D6_Energy','D7_Fire','D8_Flood']
N = len(dim_labels)
angles = np.linspace(0,2*np.pi,N,endpoint=False).tolist() + [0]
for country, color in c_colors.items():
    sites = COUNTRIES[country]
    vals = []
    for col in dim_cols:
        site_vals = []
        for s in sites:
            r = ph8[(ph8['Site']==s)&(ph8['Scenario']=='SSP5-8.5')&(ph8['Period']=='2090s')]
            if len(r)>0: site_vals.append(float(r[col].values[0]))
        vals.append(float(np.mean(site_vals)) if site_vals else 0)
    vals += [vals[0]]
    ax3.plot(angles, vals, color=color, linewidth=2, label=country)
    ax3.fill(angles, vals, color=color, alpha=0.1)
ax3.set_xticks(angles[:-1]); ax3.set_xticklabels(dim_labels, size=8)
ax3.set_ylim(0,100); ax3.set_title('Country Risk Profile (SSP5-8.5 2090s)', fontsize=9, fontweight='bold', pad=15)
ax3.legend(fontsize=7, loc='upper right', bbox_to_anchor=(1.3,1.1))

# Panel 4: BID comparison
ax4 = axes[1,1]
for country, color in c_colors.items():
    sub = df_country[(df_country['Country']==country)&(df_country['Scenario']=='SSP5-8.5')].sort_values('Period')
    xs = [PERIOD_MID[p] for p in sub['Period']]
    ys = sub['AvgBID_days_yr'].values
    ax4.plot(xs, ys, color=color, linewidth=2.5, marker='o', markersize=5, label=country)
ax4.axhline(30, color='orange', linestyle='--', alpha=0.5, linewidth=1)
ax4.set_title('Avg Business Interruption Days (SSP5-8.5)', fontsize=9, fontweight='bold')
ax4.set_ylabel('BID days/yr'); ax4.legend(fontsize=8); ax4.grid(alpha=0.3); ax4.set_xlim(2020,2100)

plt.suptitle('OCI Climate Risk — Country-Level Aggregation\nAsset-weighted analysis (SSP5-8.5 baseline)',
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT/'ph17_country_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph17_country_comparison.png saved")

# ── C. Site Summary Cards ─────────────────────────────────────────────
print("Phase 17C: Site summary cards...")
fig = plt.figure(figsize=(26, 20))
gs  = gridspec.GridSpec(3, 5, figure=fig, hspace=0.55, wspace=0.35)

for idx, site in enumerate(SITES_ORDER):
    row_i, col_i = idx // 5, idx % 5
    ax = fig.add_subplot(gs[row_i, col_i])
    ax.set_xlim(0,10); ax.set_ylim(0,10); ax.axis('off')

    # Background color by tier
    r14 = ph14[ph14['Site']==site]
    tier = r14['RiskTier_2090s'].values[0] if len(r14)>0 else 'Medium'
    tc   = TIER_COLORS.get(tier, '#ffffbf')
    ax.add_patch(FancyBboxPatch((0.1,0.1), 9.8, 9.8, boxstyle='round,pad=0.2',
                                facecolor=tc, edgecolor='grey', alpha=0.35, linewidth=1))

    # Site name
    country = ph8[ph8['Site']==site]['Country'].iloc[0]
    asset   = ASSET_VALUES[site]
    ax.text(5, 9.4, site, ha='center', va='center', fontsize=8.5, fontweight='bold')
    ax.text(5, 8.7, f'{country} | USD {asset}M assets', ha='center', va='center', fontsize=7, color='#333')

    # Risk score bar
    risk_now = float(r14['RiskScore_2020s'].values[0]) if len(r14)>0 else 0
    risk_fut = float(r14['RiskScore_2090s'].values[0]) if len(r14)>0 else 0
    for xi, (rs, label, color) in enumerate([(risk_now,'Now','steelblue'),(risk_fut,'2090s','crimson')]):
        bw = rs/100*4
        ax.add_patch(plt.Rectangle((1+xi*4.5, 7.8), bw, 0.5, color=color, alpha=0.8))
        ax.text(1+xi*4.5+bw+0.1, 8.05, f'{rs:.0f}', fontsize=7, va='center', color=color, fontweight='bold')
        ax.text(1+xi*4.5, 8.45, label, fontsize=6.5, color='grey')

    # Key metrics
    metrics = []
    if len(r14)>0:
        metrics = [
            ('WBGT JJA 90s', f"{r14['WBGT_JJA_2090s'].values[0]:.1f} C"),
            ('TX90p days',   f"{r14['TX90p_days_2090s'].values[0]:.0f} /yr"),
            ('Rx1day',       f"{r14['Rx1day_mm_2090s'].values[0]:.0f} mm"),
            ('EAL',          f"USD {r14['EAL_USDM_yr_2090s'].values[0]:.2f}M/yr"),
            ('BID',          f"{r14['BID_days_yr_2090s'].values[0]:.0f} days/yr"),
        ]
    for mi, (k, v) in enumerate(metrics):
        y_pos = 7.0 - mi*1.15
        ax.text(1.0, y_pos, k+':', fontsize=7, color='#555', va='center')
        ax.text(5.5, y_pos, v,    fontsize=7.5, color='#111', va='center', fontweight='bold')

    # Action urgency
    urg = r14['Urgency_Score'].values[0] if len(r14)>0 else 0
    cross = int(r14['Cross_Risk50_year'].values[0]) if len(r14)>0 and not np.isnan(r14['Cross_Risk50_year'].values[0]) else 9999
    urg_label = 'IMMEDIATE' if urg>50 else 'HIGH' if urg>20 else 'MODERATE' if urg>5 else 'LOW'
    urg_color = '#c62828' if urg>50 else '#e65100' if urg>20 else '#f57f17' if urg>5 else '#2e7d32'
    ax.text(5, 0.9, f'Urgency: {urg_label}  |  Risk>50: {cross if cross<9999 else "Never"}',
            ha='center', va='center', fontsize=7, color=urg_color, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=urg_color, alpha=0.8))

# Hide empty subplot
fig.add_subplot(gs[2,3]).axis('off')
fig.add_subplot(gs[2,4]).axis('off')

plt.suptitle('OCI Climate Risk — Site Summary Cards (SSP5-8.5, 2090s)\nBackground color = Risk Tier | Now vs 2090s risk score bars',
             fontsize=13, fontweight='bold', y=1.01)
plt.savefig(OUT/'ph17_site_cards.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph17_site_cards.png saved")
print("\nPhase 17 complete.")
print(f"  ph17_country_aggregate.csv {df_country.shape}")

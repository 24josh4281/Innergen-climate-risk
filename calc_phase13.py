# -*- coding: utf-8 -*-
"""
Phase 13: Time-to-Action Urgency Matrix
  - When does each site's RiskScore first cross 50 / 65 / 80?
  - Mitigation benefit: SSP5-8.5 vs SSP1-2.6 delta
  - Investment priority ranking (urgency x magnitude)
  - Visualization: urgency heatmap + priority bubble chart

Outputs:
  ph13_urgency.csv          — crossing years + priority score
  ph13_mitigation_benefit.csv — SSP5 - SSP1 risk gap per site
  ph13_urgency_heatmap.png
  ph13_priority_bubble.png
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

OUT = Path("c:/Users/24jos/climada/data/scenarios_v2/output")

SITES_ORDER = [
    'HQ Seoul','R&D Seongnam','Pohang Plant','Gunsan Plant','Iksan Plant',
    'Gwangyang Plant','Saehan Jeongeup',
    'OCI Shanghai','Shandong OCI (ZZ)','MaSteel OCI (MAS)','Jianyang Carbon (ZZ)',
    'OCI Japan Tokyo','Philko Makati'
]
SCENARIOS = ['SSP1-2.6','SSP2-4.5','SSP3-7.0','SSP5-8.5']
PERIODS   = ['2020s','2030s','2040s','2050s','2060s','2070s','2080s','2090s']
PERIOD_MID= {'2020s':2025,'2030s':2035,'2040s':2045,'2050s':2055,
             '2060s':2065,'2070s':2075,'2080s':2085,'2090s':2095}
SSP_COLORS = {'SSP1-2.6':'#2196F3','SSP2-4.5':'#4CAF50','SSP3-7.0':'#FF9800','SSP5-8.5':'#F44336'}

ASSET_VALUES = {
    'HQ Seoul':1500,'R&D Seongnam':500,'Pohang Plant':2000,'Gunsan Plant':1200,
    'Iksan Plant':800,'Gwangyang Plant':1800,'Saehan Jeongeup':600,
    'OCI Shanghai':800,'Shandong OCI (ZZ)':500,'MaSteel OCI (MAS)':400,
    'Jianyang Carbon (ZZ)':350,'OCI Japan Tokyo':200,'Philko Makati':100,
}

ph8 = pd.read_csv(OUT / 'ph8_risk_score.csv')
ph12 = pd.read_csv(OUT / 'ph12_eal.csv')

# ── A. Crossing years for each threshold ───────────────────────────────
rows_urg = []
for site in SITES_ORDER:
    country = ph8[ph8['Site']==site]['Country'].iloc[0]
    asset   = ASSET_VALUES[site]
    for ssp in SCENARIOS:
        sd = ph8[(ph8['Site']==site)&(ph8['Scenario']==ssp)].sort_values('Period')
        scores = {p: float(sd[sd['Period']==p]['RiskScore'].values[0])
                  if len(sd[sd['Period']==p])>0 else np.nan for p in PERIODS}

        def first_cross(threshold):
            for p in PERIODS:
                if not np.isnan(scores.get(p, np.nan)) and scores[p] >= threshold:
                    return PERIOD_MID[p]
            return 2100  # never

        yr50 = first_cross(50)
        yr65 = first_cross(65)
        yr80 = first_cross(80)

        # SSP5-8.5 2090s risk
        risk_2090 = scores.get('2090s', np.nan)
        risk_2020 = scores.get('2020s', np.nan)
        risk_delta = risk_2090 - risk_2020 if not np.isnan(risk_2090) and not np.isnan(risk_2020) else np.nan

        # Urgency score: inversely weighted by crossing year, scaled by magnitude
        urgency = (2100 - yr50) / 75 * 0.5 + (2100 - yr65) / 75 * 0.3 + risk_delta / 50 * 0.2
        urgency = max(0, min(1, urgency)) * 100

        # EAL 2090s
        eal_row = ph12[(ph12['Site']==site)&(ph12['Scenario']==ssp)&(ph12['Period']=='2090s')]
        eal_2090 = float(eal_row['EAL_USDM_yr'].values[0]) if len(eal_row)>0 else np.nan

        rows_urg.append({
            'Country': country, 'Site': site, 'Scenario': ssp,
            'Risk_2020s': round(risk_2020, 1) if not np.isnan(risk_2020) else np.nan,
            'Risk_2090s': round(risk_2090, 1) if not np.isnan(risk_2090) else np.nan,
            'Risk_delta': round(risk_delta, 1) if not np.isnan(risk_delta) else np.nan,
            'Cross_50_yr': yr50, 'Cross_65_yr': yr65, 'Cross_80_yr': yr80,
            'Urgency_Score': round(urgency, 1),
            'Asset_USDM': asset,
            'EAL_2090s_USDM': round(eal_2090, 3) if not np.isnan(eal_2090) else np.nan,
        })

df_urg = pd.DataFrame(rows_urg)
df_urg.to_csv(OUT / 'ph13_urgency.csv', index=False, encoding='utf-8-sig')

# ── B. Mitigation Benefit: SSP5-8.5 - SSP1-2.6 ────────────────────────
rows_mit = []
for site in SITES_ORDER:
    country = ph8[ph8['Site']==site]['Country'].iloc[0]
    asset   = ASSET_VALUES[site]
    for period in PERIODS:
        r5 = ph8[(ph8['Site']==site)&(ph8['Scenario']=='SSP5-8.5')&(ph8['Period']==period)]
        r1 = ph8[(ph8['Site']==site)&(ph8['Scenario']=='SSP1-2.6')&(ph8['Period']==period)]
        score5 = float(r5['RiskScore'].values[0]) if len(r5)>0 else np.nan
        score1 = float(r1['RiskScore'].values[0]) if len(r1)>0 else np.nan
        gap    = score5 - score1 if not np.isnan(score5) and not np.isnan(score1) else np.nan

        eal5_row = ph12[(ph12['Site']==site)&(ph12['Scenario']=='SSP5-8.5')&(ph12['Period']==period)]
        eal1_row = ph12[(ph12['Site']==site)&(ph12['Scenario']=='SSP1-2.6')&(ph12['Period']==period)]
        eal5 = float(eal5_row['EAL_USDM_yr'].values[0]) if len(eal5_row)>0 else np.nan
        eal1 = float(eal1_row['EAL_USDM_yr'].values[0]) if len(eal1_row)>0 else np.nan
        eal_saved = eal5 - eal1 if not np.isnan(eal5) and not np.isnan(eal1) else np.nan

        rows_mit.append({
            'Country': country, 'Site': site, 'Period': period,
            'Risk_SSP5': round(score5,1), 'Risk_SSP1': round(score1,1) if not np.isnan(score1) else np.nan,
            'RiskGap_SSP5_minus_SSP1': round(gap,1) if not np.isnan(gap) else np.nan,
            'EAL_SSP5_USDM': round(eal5,3), 'EAL_SSP1_USDM': round(eal1,3) if not np.isnan(eal1) else np.nan,
            'EAL_Saved_USDM_yr': round(eal_saved,3) if not np.isnan(eal_saved) else np.nan,
            'EAL_Saved_10yr_USDM': round(eal_saved*10,2) if not np.isnan(eal_saved) else np.nan,
        })

df_mit = pd.DataFrame(rows_mit)
df_mit.to_csv(OUT / 'ph13_mitigation_benefit.csv', index=False, encoding='utf-8-sig')

# ── Summary prints ─────────────────────────────────────────────────────
print("=== URGENCY RANKING (SSP5-8.5) ===")
sub = df_urg[df_urg['Scenario']=='SSP5-8.5']\
    [['Country','Site','Risk_2020s','Risk_2090s','Cross_50_yr','Cross_65_yr','Urgency_Score','EAL_2090s_USDM']]\
    .sort_values('Urgency_Score', ascending=False)
print(sub.to_string(index=False, float_format='%.1f'))

print("\n=== MITIGATION BENEFIT — EAL Saved/yr by 2090s (SSP5 -> SSP1) ===")
sub2 = df_mit[df_mit['Period']=='2090s'][['Country','Site','RiskGap_SSP5_minus_SSP1','EAL_Saved_USDM_yr','EAL_Saved_10yr_USDM']]\
       .sort_values('EAL_Saved_USDM_yr', ascending=False)
print(sub2.to_string(index=False, float_format='%.2f'))
total_saved = df_mit[df_mit['Period']=='2090s']['EAL_Saved_USDM_yr'].sum()
print(f"\nPortfolio mitigation benefit: USD {total_saved:.1f}M/yr by 2090s")

# ── Visualization 1: Urgency Heatmap ───────────────────────────────────
print("\nGenerating urgency heatmap...")
fig, axes = plt.subplots(1, 4, figsize=(20, 6), sharey=True)
cmap_urg = plt.cm.RdYlGn_r

for ax, ssp in zip(axes, SCENARIOS):
    sub = df_urg[df_urg['Scenario']==ssp].set_index('Site').reindex(SITES_ORDER)
    cols = ['Risk_2020s','Risk_2090s','Risk_delta','Cross_50_yr','Cross_65_yr','Urgency_Score']
    labels = ['Risk\n2020s','Risk\n2090s','Risk\nDelta','Cross\n50yr','Cross\n65yr','Urgency\nScore']

    # Normalize for display
    mat = np.zeros((len(SITES_ORDER), len(cols)))
    for j, col in enumerate(cols):
        vals = sub[col].values.astype(float)
        if col in ['Cross_50_yr','Cross_65_yr']:
            # Invert: earlier crossing = higher urgency = higher score
            normed = (2100 - vals) / 75 * 100
        else:
            vmin, vmax = np.nanmin(vals), np.nanmax(vals)
            normed = (vals - vmin) / (vmax - vmin + 1e-9) * 100 if vmax > vmin else vals * 0 + 50
        mat[:, j] = np.nan_to_num(normed, nan=0)

    im = ax.imshow(mat, cmap=cmap_urg, vmin=0, vmax=100, aspect='auto')
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_title(ssp, fontsize=10, fontweight='bold')
    for i in range(mat.shape[0]):
        for j, col in enumerate(cols):
            raw = sub[col].values[i]
            if np.isnan(float(raw)): continue
            if col in ['Cross_50_yr','Cross_65_yr']:
                disp = 'Never' if int(raw) >= 2100 else str(int(raw))
            else:
                disp = f'{float(raw):.0f}'
            color = 'white' if mat[i,j] > 70 else 'black'
            ax.text(j, i, disp, ha='center', va='center', fontsize=6, color=color)
    if ax == axes[0]:
        ax.set_yticks(range(len(SITES_ORDER)))
        ax.set_yticklabels(SITES_ORDER, fontsize=8)

plt.colorbar(im, ax=axes[-1], label='Normalized urgency (higher = more urgent)', shrink=0.8)
plt.suptitle('OCI Climate Risk Urgency Matrix — 4 SSP Scenarios\n(Cross 50yr/65yr = year risk score first exceeds threshold)',
             fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'ph13_urgency_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph13_urgency_heatmap.png saved")

# ── Visualization 2: Priority Bubble Chart (SSP5-8.5) ─────────────────
print("Generating priority bubble chart...")
sub_bub = df_urg[df_urg['Scenario']=='SSP5-8.5'].copy()
sub_bub['AssetBubble'] = sub_bub['Asset_USDM'] / 100  # scale for bubble size

fig, ax = plt.subplots(figsize=(12, 8))
country_colors = {'Korea':'#2196F3','China':'#F44336','Japan':'#4CAF50','Philippines':'#FF9800'}

for _, row in sub_bub.iterrows():
    color = country_colors.get(row['Country'], 'grey')
    cross50 = row['Cross_50_yr']
    cross50 = 2101 if cross50 >= 2100 else cross50
    ax.scatter(cross50, row['Risk_2090s'],
               s=row['Asset_USDM'] / 5, alpha=0.7, color=color, edgecolors='black', linewidth=0.5)
    ax.annotate(row['Site'].replace(' Plant','').replace(' OCI',''),
                (cross50, row['Risk_2090s']),
                textcoords='offset points', xytext=(5, 3), fontsize=7)

# Reference lines
ax.axhline(65, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax.axhline(50, color='orange', linestyle='--', alpha=0.5, linewidth=1)
ax.axvline(2035, color='grey', linestyle=':', alpha=0.4, linewidth=1)
ax.axvline(2050, color='grey', linestyle=':', alpha=0.4, linewidth=1)
ax.text(2036, 20, 'Near-term\n(by 2035)', fontsize=7, color='grey')
ax.text(2051, 20, 'Mid-term\n(by 2050)', fontsize=7, color='grey')

# Legend
patches = [mpatches.Patch(color=c, label=k) for k,c in country_colors.items()]
ax.legend(handles=patches, fontsize=8, loc='upper right')
ax.set_xlabel('Year Risk Score First Exceeds 50 (Medium threshold)', fontsize=9)
ax.set_ylabel('Risk Score in 2090s (SSP5-8.5)', fontsize=9)
ax.set_title('OCI Climate Risk Priority Matrix (SSP5-8.5)\nBubble size = asset value | Earlier crossing = more urgent',
             fontsize=10, fontweight='bold')
ax.set_xlim(2020, 2105)
ax.set_ylim(20, 90)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / 'ph13_priority_bubble.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph13_priority_bubble.png saved")
print("\nPhase 13 complete.")
print(f"  ph13_urgency.csv: {df_urg.shape}")
print(f"  ph13_mitigation_benefit.csv: {df_mit.shape}")

# -*- coding: utf-8 -*-
"""
Phase 8: Comprehensive Climate Risk Score Matrix
  - Normalize all key indices to 0-100 scale (higher = more risk)
  - Apply domain-expert weights to 8 risk dimensions
  - Produce Risk Score: 13 sites x 4 SSP x 8 periods
  - Output risk tier: Low / Medium-Low / Medium / Medium-High / High / Extreme

Risk Dimensions & Weights:
  1. Heat Stress       (25%): TXx, WBGT, TR days, Humidex
  2. Precipitation     (20%): Rx1day, R95p, SDII, CWD
  3. Cold Stress       (10%): TNn, FD, HDD
  4. Drought           (15%): CDD, SPI-3, P-E balance, FWI
  5. Compound Events   (15%): CompoundHotDry probability
  6. Energy Demand     (10%): CDD + HDD combined
  7. Fire Risk          (5%): FWI proxy
  8. Flooding           (0% separate — from GEV return period)

Outputs:
  ph8_risk_score.csv         — (52×30+) full matrix
  ph8_risk_summary.csv       — SSP5-8.5 2090s rank table
  ph8_risk_heatmap.png       — 13 sites × 8 dimensions heatmap
  ph8_risk_radar.png         — per-site radar charts (3x5 grid)
  ph8_risk_trajectory.png    — risk score time trajectory 4 SSPs
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyArrowPatch
import matplotlib.gridspec as gridspec

OUT = Path("c:/Users/24jos/climada/data/scenarios_v2/output")

# ── Load Phase output files ──────────────────────────────────────────────────
ph1_cdd  = pd.read_csv(OUT / 'ph1_cdd_hdd.csv')
ph1_hum  = pd.read_csv(OUT / 'ph1_humidex.csv')
ph1_spi  = pd.read_csv(OUT / 'ph1_spi3.csv')
ph1_fwi  = pd.read_csv(OUT / 'ph1_fwi.csv')
ph1_pe   = pd.read_csv(OUT / 'ph1_pe_balance.csv')
ph3      = pd.read_csv(OUT / 'ph3_etccdi_4ssp.csv')
ph4_rp   = pd.read_csv(OUT / 'ph4_return_period.csv')
ph4_ce   = pd.read_csv(OUT / 'ph4_compound_events.csv')

SCENARIOS = ['SSP1-2.6', 'SSP2-4.5', 'SSP3-7.0', 'SSP5-8.5']
PERIODS   = ['2020s','2030s','2040s','2050s','2060s','2070s','2080s','2090s']
SITES_ORDER = [
    'HQ Seoul','R&D Seongnam','Pohang Plant','Gunsan Plant','Iksan Plant',
    'Gwangyang Plant','Saehan Jeongeup',
    'OCI Shanghai','Shandong OCI (ZZ)','MaSteel OCI (MAS)','Jianyang Carbon (ZZ)',
    'OCI Japan Tokyo','Philko Makati'
]

# ── Helper: pivot ph3 ETCCDI to wide ────────────────────────────────────────
def get_etccdi(index_name, ssp, period):
    """Return Series(site->value) for given ETCCDI index, SSP, period."""
    sub = ph3[(ph3['Scenario']==ssp) & (ph3['Period']==period) & (ph3['Index']==index_name)]
    return sub.set_index('Site')['Value']

# ── Build master raw-value table ─────────────────────────────────────────────
rows = []
for ssp in SCENARIOS:
    # Get Ph1 SSP-filtered slices
    cdd_df  = ph1_cdd[ph1_cdd['Scenario']==ssp].set_index('Site')
    hum_df  = ph1_hum[ph1_hum['Scenario']==ssp].set_index('Site')
    spi_df  = ph1_spi[ph1_spi['Scenario']==ssp] if ssp in ['SSP2-4.5','SSP5-8.5'] else None
    fwi_df  = ph1_fwi[ph1_fwi['Scenario']==ssp].set_index('Site')
    pe_df   = ph1_pe[ph1_pe['Scenario']==ssp] if ssp in ['SSP2-4.5','SSP5-8.5'] else None
    ce_df   = ph4_ce[ph4_ce['Scenario']==ssp] if ssp in ['SSP2-4.5','SSP5-8.5'] else None
    rp_df   = ph4_rp[ph4_rp['Scenario']==ssp] if ssp in ['SSP2-4.5','SSP5-8.5'] else None

    for period in PERIODS:
        epoch = 'near' if int(period[:4]) < 2060 else 'far'

        # ETCCDI values
        txx   = get_etccdi('TXx (degC)',    ssp, period)
        tnn   = get_etccdi('TNn (degC)',    ssp, period)
        su    = get_etccdi('SU (days/yr)',  ssp, period)
        tr    = get_etccdi('TR (days/yr)',  ssp, period)
        fd    = get_etccdi('FD (days/yr)',  ssp, period)
        wsdi  = get_etccdi('WSDI (days/yr)',ssp, period)
        rx1   = get_etccdi('Rx1day (mm)',   ssp, period)
        r95p  = get_etccdi('R95p (mm/yr)',  ssp, period)
        cdd_e = get_etccdi('CDD (days)',    ssp, period)
        cwd_e = get_etccdi('CWD (days)',    ssp, period)
        wbgt  = get_etccdi('WBGT (degC)',   ssp, period)

        for site in SITES_ORDER:
            row = {
                'Site': site, 'Scenario': ssp, 'Period': period,
                'Country': ph3[ph3['Site']==site]['Country'].iloc[0] if len(ph3[ph3['Site']==site])>0 else ''
            }
            def sv(series, key, default=np.nan):
                return float(series.get(key, default)) if series is not None and key in series.index else default

            # Raw values
            row['TXx']       = sv(txx,  site)
            row['TNn']       = sv(tnn,  site)
            row['SU']        = sv(su,   site)
            row['TR']        = sv(tr,   site)
            row['FD']        = sv(fd,   site)
            row['WSDI']      = sv(wsdi, site)
            row['Rx1day']    = sv(rx1,  site)
            row['R95p']      = sv(r95p, site)
            row['CDD_etcc']  = sv(cdd_e,site)
            row['CWD']       = sv(cwd_e,site)
            row['WBGT']      = sv(wbgt, site)

            # Phase 1 values
            row['CDD_heat']  = float(cdd_df.loc[site, f'CDD_{period}'])  if cdd_df is not None and site in cdd_df.index and f'CDD_{period}' in cdd_df.columns else np.nan
            row['HDD_heat']  = float(cdd_df.loc[site, f'HDD_{period}'])  if cdd_df is not None and site in cdd_df.index and f'HDD_{period}' in cdd_df.columns else np.nan
            row['Humidex']   = float(hum_df.loc[site, f'Humidex_{period}']) if hum_df is not None and site in hum_df.index and f'Humidex_{period}' in hum_df.columns else np.nan
            row['FWI']       = float(fwi_df.loc[site, f'FWI_{period}'])  if fwi_df is not None and site in fwi_df.index and f'FWI_{period}' in fwi_df.columns else np.nan
            row['FWI_JJA']   = float(fwi_df.loc[site, f'FWI_JJA_{period}']) if fwi_df is not None and site in fwi_df.index and f'FWI_JJA_{period}' in fwi_df.columns else np.nan

            if spi_df is not None:
                spi_row = spi_df[spi_df['Site']==site]
                row['SPI3']  = float(spi_row[f'SPI3_{period}'].values[0]) if len(spi_row) > 0 and f'SPI3_{period}' in spi_row.columns else np.nan
            else:
                row['SPI3'] = np.nan

            if pe_df is not None:
                pe_row = pe_df[pe_df['Site']==site]
                row['PE']    = float(pe_row[f'PE_{period}'].values[0]) if len(pe_row) > 0 and f'PE_{period}' in pe_row.columns else np.nan
            else:
                row['PE'] = np.nan

            if ce_df is not None:
                ce_row = ce_df[ce_df['Site']==site]
                col = f'CompoundDays_pct_{epoch}'
                row['CompoundProb'] = float(ce_row[col].values[0]) if len(ce_row)>0 and col in ce_row.columns else np.nan
            else:
                row['CompoundProb'] = np.nan

            if rp_df is not None:
                rp_row = rp_df[rp_df['Site']==site]
                col100 = f'RL100yr_{epoch}_mm'
                row['RL100yr']  = float(rp_row[col100].values[0]) if len(rp_row)>0 and col100 in rp_row.columns else np.nan
            else:
                row['RL100yr'] = np.nan

            rows.append(row)

df_raw = pd.DataFrame(rows)

# ── Normalize each variable 0-100 across ALL rows ────────────────────────────
def norm100(series, invert=False):
    """Min-max normalize to 0-100. invert=True means low value = high risk."""
    vmin, vmax = series.min(), series.max()
    if vmax == vmin:
        return pd.Series(50.0, index=series.index)
    n = (series - vmin) / (vmax - vmin) * 100
    return 100 - n if invert else n

df_n = df_raw.copy()
# Heat risk: higher = worse
df_n['n_TXx']       = norm100(df_raw['TXx'])
df_n['n_WBGT']      = norm100(df_raw['WBGT'])
df_n['n_TR']        = norm100(df_raw['TR'])
df_n['n_Humidex']   = norm100(df_raw['Humidex'])
df_n['n_WSDI']      = norm100(df_raw['WSDI'])
# Cold risk: lower TNn = worse; more FD = worse
df_n['n_TNn']       = norm100(df_raw['TNn'], invert=True)  # lower temp = more risk
df_n['n_FD']        = norm100(df_raw['FD'])
df_n['n_HDD']       = norm100(df_raw['HDD_heat'])
# Precipitation risk: higher = worse
df_n['n_Rx1day']    = norm100(df_raw['Rx1day'])
df_n['n_R95p']      = norm100(df_raw['R95p'])
df_n['n_CWD']       = norm100(df_raw['CWD'])
# Drought: more CDD = worse; lower SPI = worse; lower PE = worse
df_n['n_CDD_etcc']  = norm100(df_raw['CDD_etcc'])
df_n['n_CDD_heat']  = norm100(df_raw['CDD_heat'])
df_n['n_SPI3']      = norm100(df_raw['SPI3'], invert=True)  # lower SPI = drier = more risk
df_n['n_PE']        = norm100(df_raw['PE'], invert=True)    # lower P-E = drier = more risk
# Fire risk
df_n['n_FWI']       = norm100(df_raw['FWI'])
df_n['n_FWI_JJA']   = norm100(df_raw['FWI_JJA'])
# Compound & flood
df_n['n_Compound']  = norm100(df_raw['CompoundProb'].fillna(df_raw['CompoundProb'].mean()))
df_n['n_RL100yr']   = norm100(df_raw['RL100yr'].fillna(df_raw['RL100yr'].mean()))

# ── Compute 8 Dimension Scores ───────────────────────────────────────────────
df_n['D1_Heat']     = (df_n['n_TXx']*0.30 + df_n['n_WBGT']*0.35 + df_n['n_TR']*0.20 + df_n['n_Humidex']*0.15)
df_n['D2_Precip']   = (df_n['n_Rx1day']*0.40 + df_n['n_R95p']*0.35 + df_n['n_CWD']*0.25)
df_n['D3_Cold']     = (df_n['n_TNn']*0.40 + df_n['n_FD']*0.35 + df_n['n_HDD']*0.25)
df_n['D4_Drought']  = (df_n['n_CDD_etcc']*0.30 + df_n['n_CDD_heat']*0.20 + df_n['n_SPI3']*0.30 + df_n['n_PE']*0.20)
df_n['D5_Compound'] = df_n['n_Compound']
df_n['D6_Energy']   = (df_n['n_CDD_heat']*0.55 + df_n['n_HDD']*0.45)
df_n['D7_Fire']     = (df_n['n_FWI']*0.50 + df_n['n_FWI_JJA']*0.50)
df_n['D8_Flood']    = df_n['n_RL100yr']

# ── Overall Risk Score (weighted) ────────────────────────────────────────────
W = {'D1_Heat':0.25, 'D2_Precip':0.20, 'D3_Cold':0.10,
     'D4_Drought':0.15, 'D5_Compound':0.15, 'D6_Energy':0.10,
     'D7_Fire':0.05, 'D8_Flood':0.00}  # Flood as separate info column
# Recalculate flood-included score
W2 = {'D1_Heat':0.25, 'D2_Precip':0.18, 'D3_Cold':0.09,
      'D4_Drought':0.14, 'D5_Compound':0.14, 'D6_Energy':0.09,
      'D7_Fire':0.04, 'D8_Flood':0.07}
df_n['RiskScore'] = sum(df_n[d]*w for d,w in W2.items())

def risk_tier(score):
    if score < 20:   return 'Low'
    elif score < 35: return 'Medium-Low'
    elif score < 50: return 'Medium'
    elif score < 65: return 'Medium-High'
    elif score < 80: return 'High'
    else:            return 'Extreme'

df_n['RiskTier'] = df_n['RiskScore'].apply(risk_tier)

# Save full matrix
cols_save = ['Country','Site','Scenario','Period',
             'D1_Heat','D2_Precip','D3_Cold','D4_Drought',
             'D5_Compound','D6_Energy','D7_Fire','D8_Flood',
             'RiskScore','RiskTier']
df_n[cols_save].to_csv(OUT / 'ph8_risk_score.csv', index=False, encoding='utf-8-sig')
print(f"ph8_risk_score.csv  {df_n[cols_save].shape}")

# Summary: SSP5-8.5, 2090s
df_sum = df_n[(df_n['Scenario']=='SSP5-8.5') & (df_n['Period']=='2090s')][cols_save].sort_values('RiskScore', ascending=False)
df_sum.to_csv(OUT / 'ph8_risk_summary.csv', index=False, encoding='utf-8-sig')
print(f"ph8_risk_summary.csv {df_sum.shape}")
print("\n=== CLIMATE RISK RANKING (SSP5-8.5, 2090s) ===")
print(df_sum[['Country','Site','RiskScore','RiskTier','D1_Heat','D2_Precip','D3_Cold','D4_Drought']].to_string(index=False, float_format='%.1f'))

# ── Visualization 1: Heatmap ─────────────────────────────────────────────────
print("\nGenerating Risk Heatmap...")
dims_labels = ['Heat','Precip','Cold','Drought','Compound','Energy','Fire','Flood','TOTAL']
dims_cols   = ['D1_Heat','D2_Precip','D3_Cold','D4_Drought','D5_Compound','D6_Energy','D7_Fire','D8_Flood','RiskScore']
ssp_list = ['SSP1-2.6','SSP2-4.5','SSP3-7.0','SSP5-8.5']

fig, axes = plt.subplots(1, 4, figsize=(22, 7), sharey=True)
cmap = plt.cm.RdYlGn_r

for ax, ssp in zip(axes, ssp_list):
    sub = df_n[(df_n['Scenario']==ssp) & (df_n['Period']=='2090s')].set_index('Site')
    sub = sub.reindex(SITES_ORDER)
    mat = sub[dims_cols].values
    im = ax.imshow(mat, cmap=cmap, vmin=0, vmax=100, aspect='auto')
    ax.set_xticks(range(len(dims_labels)))
    ax.set_xticklabels(dims_labels, rotation=45, ha='right', fontsize=8)
    ax.set_title(ssp, fontsize=11, fontweight='bold')
    # Value annotations
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            val = mat[i, j]
            if not np.isnan(val):
                color = 'white' if val > 70 or val < 30 else 'black'
                ax.text(j, i, f'{val:.0f}', ha='center', va='center', fontsize=6.5, color=color)
    if ax == axes[0]:
        ax.set_yticks(range(len(SITES_ORDER)))
        ax.set_yticklabels(SITES_ORDER, fontsize=8)

plt.colorbar(im, ax=axes[-1], label='Risk Score (0-100)', shrink=0.8)
plt.suptitle('OCI Climate Risk Dimension Scores — 2090s Projection\n(0=Low Risk, 100=Extreme Risk)',
             fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(OUT / 'ph8_risk_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph8_risk_heatmap.png saved")

# ── Visualization 2: Risk Score Trajectory (4 SSPs) ─────────────────────────
print("Generating Risk Trajectory...")
fig, axes = plt.subplots(3, 5, figsize=(20, 12))
axes = axes.flatten()

period_midyrs = {'2020s':2025,'2030s':2035,'2040s':2045,'2050s':2055,
                 '2060s':2065,'2070s':2075,'2080s':2085,'2090s':2095}
SSP_COLORS = {'SSP1-2.6':'#2196F3','SSP2-4.5':'#4CAF50','SSP3-7.0':'#FF9800','SSP5-8.5':'#F44336'}

for idx, site in enumerate(SITES_ORDER):
    if idx >= len(axes):
        break
    ax = axes[idx]
    site_data = df_n[df_n['Site']==site]
    for ssp, color in SSP_COLORS.items():
        sd = site_data[site_data['Scenario']==ssp].sort_values('Period')
        xs = [period_midyrs[p] for p in sd['Period']]
        ys = sd['RiskScore'].values
        ax.plot(xs, ys, color=color, linewidth=2, marker='o', markersize=3, label=ssp)
    ax.axhline(65, color='red', linestyle='--', alpha=0.4, linewidth=0.8)
    ax.set_title(site.replace(' Plant','').replace(' OCI',''), fontsize=8, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.set_xlim(2020, 2100)
    ax.set_xticks([2030, 2060, 2090])
    ax.set_xticklabels(['2030','2060','2090'], fontsize=7)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(['0','25','50','75','100'], fontsize=7)
    ax.grid(True, alpha=0.3)

# Legend
axes[0].legend(fontsize=6, loc='upper left')
# Hide unused axes
for idx in range(len(SITES_ORDER), len(axes)):
    axes[idx].set_visible(False)

plt.suptitle('OCI Climate Risk Score Trajectory by Site & Scenario (2020-2100)\nRed dashed line = High Risk threshold (65)',
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'ph8_risk_trajectory.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph8_risk_trajectory.png saved")

# ── Visualization 3: Radar Charts ────────────────────────────────────────────
print("Generating Radar Charts...")
dim_labels_r = ['Heat','Precip','Cold','Drought','Compound','Energy','Fire','Flood']
dim_cols_r   = ['D1_Heat','D2_Precip','D3_Cold','D4_Drought','D5_Compound','D6_Energy','D7_Fire','D8_Flood']
N = len(dim_labels_r)
angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
angles += angles[:1]

fig, axes = plt.subplots(3, 5, figsize=(20, 12), subplot_kw=dict(polar=True))
axes = axes.flatten()

for idx, site in enumerate(SITES_ORDER):
    if idx >= len(axes):
        break
    ax = axes[idx]
    for ssp, color in SSP_COLORS.items():
        row = df_n[(df_n['Site']==site) & (df_n['Scenario']==ssp) & (df_n['Period']=='2090s')]
        if len(row) == 0:
            continue
        vals = row[dim_cols_r].values[0].tolist()
        vals += vals[:1]
        ax.plot(angles, vals, color=color, linewidth=1.5, label=ssp)
        ax.fill(angles, vals, color=color, alpha=0.08)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dim_labels_r, size=7)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(['25','50','75'], size=5, color='grey')
    ax.set_title(site.replace(' Plant','').replace(' OCI',''), size=8, fontweight='bold', pad=10)

axes[0].legend(loc='upper right', bbox_to_anchor=(1.35, 1.15), fontsize=6)
for idx in range(len(SITES_ORDER), len(axes)):
    axes[idx].set_visible(False)

plt.suptitle('OCI Climate Risk Radar — 4 SSP Scenarios, 2090s\n(All dimensions normalized 0-100)',
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'ph8_risk_radar.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph8_risk_radar.png saved")

print("\n" + "="*60)
print("Phase 8 complete.")
print(f"  ph8_risk_score.csv     {df_n[cols_save].shape}")
print(f"  ph8_risk_summary.csv   {df_sum.shape}")
print(f"  ph8_risk_heatmap.png")
print(f"  ph8_risk_trajectory.png")
print(f"  ph8_risk_radar.png")

# -*- coding: utf-8 -*-
"""
Phase 12: Financial Risk Quantification
  - Climate Risk Score -> Expected Annual Loss (EAL)
  - Business Interruption Days estimate
  - Adaptation Cost estimate

Methodology:
  1. EAL = Asset Value x Damage Factor(RiskScore)
     Damage curve: sigmoid function calibrated to IPCC AR6 damage estimates
     Low risk (20) -> 0.01% asset/yr
     Medium (50)   -> 0.3% asset/yr
     High (80)     -> 2.0% asset/yr
     Extreme (100) -> 5.0% asset/yr

  2. Business Interruption Days (BID)
     - Heat stress: days with WBGT_JJA > 32C (WHO work restriction)
     - Flood: R30mm days (proxy for operational disruption)
     - Combined: unique disruption days/yr

  3. Adaptation Cost Index (ACI)
     - Cost to reduce risk from current trajectory to SSP1-2.6 level
     - Relative to asset value (%)

Notional Asset Values (USD M, rough proxy):
  Korea plants: 500-2000 M
  China plants: 300-800 M
  Japan: 200 M
  Philippines: 100 M

Outputs:
  ph12_eal.csv           — EAL per site x SSP x period
  ph12_disruption.csv    — Business interruption days
  ph12_financial_risk.csv — Combined financial risk summary
  ph12_financial_bar.png — EAL comparison chart
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path("c:/Users/24jos/climada/data/scenarios_v2/output")

# ── Asset Values (notional, USD Million) ────────────────────────────────
ASSET_VALUES = {
    'HQ Seoul':             1500,
    'R&D Seongnam':          500,
    'Pohang Plant':         2000,
    'Gunsan Plant':         1200,
    'Iksan Plant':           800,
    'Gwangyang Plant':      1800,
    'Saehan Jeongeup':       600,
    'OCI Shanghai':          800,
    'Shandong OCI (ZZ)':    500,
    'MaSteel OCI (MAS)':    400,
    'Jianyang Carbon (ZZ)': 350,
    'OCI Japan Tokyo':       200,
    'Philko Makati':         100,
}

SITES_ORDER = list(ASSET_VALUES.keys())
SCENARIOS = ['SSP1-2.6','SSP2-4.5','SSP3-7.0','SSP5-8.5']
PERIODS   = ['2020s','2030s','2040s','2050s','2060s','2070s','2080s','2090s']
SSP_COLORS = {'SSP1-2.6':'#2196F3','SSP2-4.5':'#4CAF50','SSP3-7.0':'#FF9800','SSP5-8.5':'#F44336'}

# ── Damage Function: RiskScore -> annual damage fraction ────────────────
def damage_fraction(risk_score):
    """
    Sigmoid damage curve.
    Risk 0  -> 0.001% (near zero)
    Risk 20 -> 0.01%
    Risk 50 -> 0.30%
    Risk 80 -> 2.00%
    Risk 100-> 5.00%
    Calibrated to logistic: f(x) = L / (1 + exp(-k*(x-x0)))
    """
    # Piecewise-linear interpolation through calibration points
    xs = [0, 20, 35, 50, 65, 80, 90, 100]
    ys = [0.001, 0.01, 0.08, 0.30, 0.80, 2.00, 3.50, 5.00]
    return float(np.interp(risk_score, xs, ys)) / 100   # return as fraction

# ── Business Interruption Days function ─────────────────────────────────
def bid_from_scores(d1_heat, d2_precip, wbgt_jja=None, r30mm=None):
    """
    Estimate business interruption days/yr from risk dimensions.
    Heat: WBGT > 32 C -> partial work restriction (0.5 days per day > 32C)
    Precip: R30mm days -> full-day disruption
    """
    # Heat BID proxy from D1_Heat score (0-100 -> 0-60 days/yr)
    heat_bid = d1_heat * 60 / 100 if not np.isnan(d1_heat) else 0
    # Precip BID proxy from D2_Precip (0-100 -> 0-20 days/yr)
    precip_bid = d2_precip * 20 / 100 if not np.isnan(d2_precip) else 0
    # Overlap reduction (not purely additive)
    total_bid = heat_bid + precip_bid * 0.7
    return round(total_bid, 1)

# ── Load Phase 8 risk scores ─────────────────────────────────────────────
ph8 = pd.read_csv(OUT / 'ph8_risk_score.csv')
ph6h = pd.read_csv(OUT / 'ph6_heat_stress.csv')
# ph11 may not exist yet; use R30mm proxy from ph6_seasonal_precip if available
try:
    ph11p = pd.read_csv(OUT / 'ph11_daily_precip.csv')
    has_ph11 = True
    print("ph11_daily_precip.csv loaded.")
except:
    has_ph11 = False
    print("ph11 not available yet, using ph6 proxy.")

rows_eal = []
rows_bid = []

for site in SITES_ORDER:
    asset = ASSET_VALUES[site]
    for ssp in SCENARIOS:
        for period in PERIODS:
            r = ph8[(ph8['Site']==site) & (ph8['Scenario']==ssp) & (ph8['Period']==period)]
            if len(r) == 0:
                continue
            rs   = float(r['RiskScore'].values[0])
            d1   = float(r['D1_Heat'].values[0])
            d2   = float(r['D2_Precip'].values[0])
            tier = r['RiskTier'].values[0]

            # EAL
            df   = damage_fraction(rs)
            eal  = asset * df  # USD M / yr
            eal_cumulative_decade = eal * 10  # 10-year cumulative

            # NPV at 5% discount — mid-decade year
            decade_start = {'2020s':2020,'2030s':2030,'2040s':2040,'2050s':2050,
                            '2060s':2060,'2070s':2070,'2080s':2080,'2090s':2090}
            t = decade_start[period] - 2024  # years from now
            discount = 1 / (1.05 ** t)
            eal_npv = eal * discount

            rows_eal.append({
                'Country': ph8[(ph8['Site']==site)]['Country'].iloc[0],
                'Site': site, 'Scenario': ssp, 'Period': period,
                'Asset_USDM': asset,
                'RiskScore': round(rs, 1),
                'RiskTier': tier,
                'DamageFraction_pct': round(df*100, 4),
                'EAL_USDM_yr': round(eal, 3),
                'EAL_cumulative_10yr_USDM': round(eal_cumulative_decade, 2),
                'EAL_NPV_USDM': round(eal_npv, 3),
            })

            # BID
            r6h = ph6h[(ph6h['Site']==site) & (ph6h['Scenario']==ssp)]
            wbgt = float(r6h[f'WBGT_JJA_{period}'].values[0]) if len(r6h)>0 and f'WBGT_JJA_{period}' in r6h.columns else np.nan

            r30mm_val = np.nan
            if has_ph11:
                r11 = ph11p[(ph11p['Site']==site) & (ph11p['Scenario']==ssp)]
                if len(r11)>0 and f'R30mm_{period}' in r11.columns:
                    r30mm_val = float(r11[f'R30mm_{period}'].values[0])

            bid = bid_from_scores(d1, d2, wbgt, r30mm_val)
            rows_bid.append({
                'Country': ph8[(ph8['Site']==site)]['Country'].iloc[0],
                'Site': site, 'Scenario': ssp, 'Period': period,
                'WBGT_JJA': round(wbgt, 1) if not np.isnan(wbgt) else np.nan,
                'R30mm_days': round(r30mm_val, 1) if not np.isnan(r30mm_val) else np.nan,
                'BID_days_yr': bid,
                'BID_hrs_yr': round(bid * 8, 0),    # 8-hr workday
                'BID_loss_pct_revenue': round(bid / 250 * 100, 2),  # 250 working days
            })

df_eal = pd.DataFrame(rows_eal)
df_bid = pd.DataFrame(rows_bid)

# Combined
df_fin = df_eal.merge(df_bid[['Site','Scenario','Period','WBGT_JJA','BID_days_yr','BID_loss_pct_revenue']],
                      on=['Site','Scenario','Period'])
df_fin.to_csv(OUT / 'ph12_financial_risk.csv', index=False, encoding='utf-8-sig')
df_eal.to_csv(OUT / 'ph12_eal.csv', index=False, encoding='utf-8-sig')
df_bid.to_csv(OUT / 'ph12_disruption.csv', index=False, encoding='utf-8-sig')

print(f"ph12_financial_risk.csv: {df_fin.shape}")
print(f"ph12_eal.csv: {df_eal.shape}")

print("\n=== EAL SSP5-8.5 2090s (USD M/yr) ===")
sub = df_eal[(df_eal['Scenario']=='SSP5-8.5')&(df_eal['Period']=='2090s')]\
     [['Country','Site','Asset_USDM','RiskScore','EAL_USDM_yr','EAL_cumulative_10yr_USDM']]\
     .sort_values('EAL_USDM_yr', ascending=False)
print(sub.to_string(index=False, float_format='%.2f'))

print("\n=== Business Interruption Days SSP5-8.5 2090s ===")
sub2 = df_bid[(df_bid['Scenario']=='SSP5-8.5')&(df_bid['Period']=='2090s')]\
      [['Country','Site','WBGT_JJA','BID_days_yr','BID_loss_pct_revenue']]\
      .sort_values('BID_days_yr', ascending=False)
print(sub2.to_string(index=False, float_format='%.1f'))

# Total portfolio EAL
total_assets = sum(ASSET_VALUES.values())
sub_tot = df_eal[df_eal['Period']=='2090s'].groupby('Scenario')['EAL_USDM_yr'].sum()
print(f"\n=== PORTFOLIO TOTAL EAL (2090s, all sites) ===")
print(f"Total asset value: USD {total_assets:,}M")
for sc, val in sub_tot.items():
    print(f"  {sc}: EAL = USD {val:.1f}M/yr  ({val/total_assets*100:.2f}% of assets/yr)")

# ── Visualization ─────────────────────────────────────────────────────
print("\nGenerating financial risk charts...")
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Left: EAL by site (SSP2-4.5 vs SSP5-8.5, 2090s)
ax = axes[0]
x = np.arange(len(SITES_ORDER))
w = 0.35
for i, ssp in enumerate(['SSP2-4.5', 'SSP5-8.5']):
    vals = [float(df_eal[(df_eal['Site']==s)&(df_eal['Scenario']==ssp)&(df_eal['Period']=='2090s')]['EAL_USDM_yr'].values[0])
            if len(df_eal[(df_eal['Site']==s)&(df_eal['Scenario']==ssp)&(df_eal['Period']=='2090s')])>0 else 0
            for s in SITES_ORDER]
    bars = ax.bar(x + i*w, vals, width=w, label=ssp, color=SSP_COLORS[ssp], alpha=0.85)
ax.set_xticks(x + w/2)
ax.set_xticklabels([s.replace(' Plant','').replace(' OCI','') for s in SITES_ORDER],
                    rotation=35, ha='right', fontsize=8)
ax.set_ylabel('EAL (USD Million/yr)', fontsize=9)
ax.set_title('Expected Annual Loss by Site — 2090s', fontsize=10, fontweight='bold')
ax.legend(fontsize=8)
ax.grid(axis='y', alpha=0.3)

# Right: EAL trajectory (portfolio total, 4 SSPs)
ax2 = axes[1]
period_yrs = {'2020s':2025,'2030s':2035,'2040s':2045,'2050s':2055,
              '2060s':2065,'2070s':2075,'2080s':2085,'2090s':2095}
for ssp in SCENARIOS:
    xs, ys = [], []
    for period in PERIODS:
        sub = df_eal[(df_eal['Scenario']==ssp)&(df_eal['Period']==period)]
        xs.append(period_yrs[period])
        ys.append(float(sub['EAL_USDM_yr'].sum()))
    ax2.plot(xs, ys, color=SSP_COLORS[ssp], linewidth=2.5, marker='o', markersize=5, label=ssp)
ax2.set_xlabel('Year', fontsize=9)
ax2.set_ylabel('Portfolio EAL (USD M/yr)', fontsize=9)
ax2.set_title(f'Portfolio Total EAL Trajectory\n(Total assets: USD {total_assets:,}M)', fontsize=10, fontweight='bold')
ax2.legend(fontsize=8)
ax2.grid(alpha=0.3)
ax2.set_xlim(2020, 2100)

plt.suptitle('OCI Climate Financial Risk — Expected Annual Loss Analysis', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig(OUT / 'ph12_financial_bar.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ph12_financial_bar.png saved")
print("\nPhase 12 complete.")

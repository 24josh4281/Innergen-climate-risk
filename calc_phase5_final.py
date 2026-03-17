# -*- coding: utf-8 -*-
"""
Phase 5: Final Integration
 - Merge Phase 1 (CDD/HDD, Humidex, SPI-3, FWI, P-E) + Phase 4 (GEV, Compound)
   with existing FINAL files
 - Create OCI_MASTER_SUMMARY.csv  (all indices, all SSPs, 2090s snapshot)
 - Create OCI_4SSP_ETCCDI_SUMMARY.csv (Phase 3, pivoted to wide)
 - Write CHANGELOG entry
"""
import pandas as pd, numpy as np
from pathlib import Path

OUT = Path("c:/Users/24jos/climada/data/scenarios_v2/output")

# ── 1. Load all result files ─────────────────────────────────────────────────
ph1_cdd  = pd.read_csv(OUT / 'ph1_cdd_hdd.csv')
ph1_hum  = pd.read_csv(OUT / 'ph1_humidex.csv')
ph1_spi  = pd.read_csv(OUT / 'ph1_spi3.csv')
ph1_fwi  = pd.read_csv(OUT / 'ph1_fwi.csv')
ph1_pe   = pd.read_csv(OUT / 'ph1_pe_balance.csv')
ph3_etcc = pd.read_csv(OUT / 'ph3_etccdi_4ssp.csv')
ph4_rp   = pd.read_csv(OUT / 'ph4_return_period.csv')
ph4_ce   = pd.read_csv(OUT / 'ph4_compound_events.csv')

# ── 2. ETCCDI 4-SSP wide pivot (2090s) ───────────────────────────────────────
ph3_90s = ph3_etcc[ph3_etcc['Period'] == '2090s'].copy()
ph3_wide = ph3_90s.pivot_table(
    index=['Country', 'Site'],
    columns=['Scenario', 'Index'],
    values='Value',
    aggfunc='first'
)
ph3_wide.columns = [f"{scen}|{idx}" for scen, idx in ph3_wide.columns]
ph3_wide = ph3_wide.reset_index()
ph3_wide.to_csv(OUT / 'OCI_4SSP_ETCCDI_SUMMARY.csv', index=False, encoding='utf-8-sig')
print(f"OCI_4SSP_ETCCDI_SUMMARY.csv  {ph3_wide.shape}")

# ── 3. Master summary (2090s snapshot) ───────────────────────────────────────
# Key columns from Phase 1 for SSP5-8.5 2090s
key_cols_cdd = ['Country', 'Site', 'CDD_2090s', 'HDD_2090s']
key_cols_hum = ['Country', 'Site', 'Humidex_2090s', 'Humidex_Risk_2090s']
key_cols_spi = ['Country', 'Site', 'SPI3_2090s']
key_cols_fwi = ['Country', 'Site', 'FWI_2090s', 'FWI_JJA_2090s']
key_cols_pe  = ['Country', 'Site', 'PE_2090s']

def ssp_filter(df, ssp_label='SSP5-8.5'):
    if 'Scenario' in df.columns:
        return df[df['Scenario'] == ssp_label]
    return df

cdd_s = ssp_filter(ph1_cdd)[key_cols_cdd]
hum_s = ssp_filter(ph1_hum)[key_cols_hum]
spi_s = ssp_filter(ph1_spi)[key_cols_spi]
fwi_s = ssp_filter(ph1_fwi)[key_cols_fwi]
pe_s  = ssp_filter(ph1_pe)[key_cols_pe]

rp_s  = ph4_rp[ph4_rp['Scenario'] == 'SSP5-8.5'][[
    'Country', 'Site',
    'RL10yr_far_mm', 'RL50yr_far_mm', 'RL100yr_far_mm',
    'Rx1day_mean_far_mm'
]]
ce_s  = ph4_ce[ph4_ce['Scenario'] == 'SSP5-8.5'][[
    'Country', 'Site',
    'CompoundDays_pct_far', 'HeatThresh_far_C'
]]

# ETCCDI key cols (SSP5-8.5, 2090s)
etcc_key_cols = ['TXx (degC)', 'SU (days/yr)', 'TR (days/yr)', 'FD (days/yr)',
                 'Rx1day (mm)', 'WBGT (degC)', 'WSDI (days/yr)']
etcc_s = ph3_90s[ph3_90s['Scenario'] == 'SSP5-8.5'].pivot_table(
    index=['Country', 'Site'], columns='Index', values='Value', aggfunc='first'
)[[c for c in etcc_key_cols if c in ph3_90s['Index'].unique()]]
etcc_s = etcc_s.reset_index()

# Merge everything
master = cdd_s
for df in [hum_s, spi_s, fwi_s, pe_s, rp_s, ce_s, etcc_s]:
    master = master.merge(df, on=['Country', 'Site'], how='left')

master.to_csv(OUT / 'OCI_MASTER_SUMMARY_SSP585.csv', index=False, encoding='utf-8-sig')
print(f"OCI_MASTER_SUMMARY_SSP585.csv  {master.shape}")

# ── 4. 4-SSP TXx trajectory summary ─────────────────────────────────────────
txx_traj = ph3_etcc[ph3_etcc['Index'] == 'TXx (degC)'].pivot_table(
    index=['Country', 'Site'], columns=['Scenario', 'Period'], values='Value', aggfunc='first'
)
txx_traj.columns = [f"{scen}|{per}" for scen, per in txx_traj.columns]
txx_traj = txx_traj.reset_index()
txx_traj.to_csv(OUT / 'OCI_TXx_4SSP_Trajectory.csv', index=False, encoding='utf-8-sig')
print(f"OCI_TXx_4SSP_Trajectory.csv    {txx_traj.shape}")

# ── 5. Print summary ─────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("Phase 5 complete. New files:")
print("  OCI_4SSP_ETCCDI_SUMMARY.csv   - 13 ETCCDI x 4 SSP x 2090s")
print("  OCI_MASTER_SUMMARY_SSP585.csv - All Phase 1/3/4 indices, SSP5-8.5")
print("  OCI_TXx_4SSP_Trajectory.csv   - TXx across 4 SSPs x 8 decades")

print("\n=== MASTER SUMMARY (SSP5-8.5, 2090s) ===")
pd.set_option('display.float_format', '{:.1f}'.format)
pd.set_option('display.max_columns', 15)
print(master[['Country','Site','CDD_2090s','HDD_2090s','TXx (degC)','WBGT (degC)',
              'RL100yr_far_mm','CompoundDays_pct_far']].to_string(index=False))

print("\n=== TXx 2090s SSP SPREAD ===")
ssp_cols = [c for c in txx_traj.columns if '2090s' in c]
print(txx_traj[['Country','Site'] + ssp_cols].to_string(index=False))

# Changelog — OCI Climate Physical Risk Analysis

All notable changes to this project are documented here.
Format: `[YYYY-MM-DD] TYPE: description`

---

## [2026-03-17] — ETCCDI Indices + Annual Resolution + GitHub Cleanup

### Added
- **`download_daily_cmip6.py`** — Daily CMIP6 download (tasmax, tasmin, pr) for 3 regions × 2 SSPs = 18 files (~165 MB total)
- **`calc_etccdi.py`** — ETCCDI 13 extreme climate indices computation:
  - Temperature: TXx, TNn, SU (Summer Days), TR (Tropical Nights), FD (Frost Days), WSDI
  - Precipitation: Rx1day, Rx5day, SDII, R95p, CDD, CWD
  - Heat stress: WBGT (Wet Bulb Globe Temperature)
- **`OCI_FINAL_4SSP_Decadal.csv`** — Master file: 12 variables × 4 SSP × 8 decades × 13 sites (156×37)
- **`OCI_FINAL_SpecificYears.csv`** — Annual resolution: 7 variables × 4 SSP × 4 years (2030/2035/2040/2045) × 13 sites
- **`OCI_FINAL_ETCCDI.csv`** — 13 ETCCDI indices × 2 SSP × 8 decades × 13 sites (pivot table format)
- **`OCI_FINAL_Indices.csv`** — Heat Index (NOAA Rothfusz) + Warming Rate + SPEI combined

### Key Results
- Philko Makati (Philippines): NOAA Danger level by SSP5-8.5 2090s (HI=41.8°C), TR=365 days/yr, WBGT=30.7°C
- Gwangyang Plant: Highest precipitation risk in Korea — Rx1day=74.8mm, R95p=845mm/yr (SSP5-8.5 2090s)
- Pohang Plant: Rx1day=62.1mm, R95p=833mm/yr, WSDI=113 days (SSP5-8.5 2090s)
- Korean sites (SSP5-8.5): Total warming +4.9~5.6°C by 2090s vs 2020s baseline
- All sites SPEI > -1.0: No drought risk detected across all scenarios

---

## [2026-03-16] — 4-SSP Expansion + Multi-Site Analysis

### Added
- **`download_ssp_extra.py`** — SSP1-2.6 and SSP3-7.0 monthly data download (3 regions × 2 SSPs × 12 vars = 72 files)
- **`calc_indices_step1.py`** — STEP 1 climate indices: Heat Index, SPEI approximation, Warming Rate for 13 OCI sites
- **`OCI_Climate_Risk_4SSP_AllSites.csv`** — Full 4-SSP dataset: 13 sites × 12 drivers × 4 SSPs × 8 decades
- **`OCI_Annual_2030_2045.csv`** — Specific-year ensemble means for 2030, 2035, 2040, 2045

### Changed
- `scenario_analysis.py`: Expanded from SSP2-4.5 / SSP5-8.5 to full 4-SSP set (SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5)
- `SCEN_COLORS` added for SSP1-2.6 (green) and SSP3-7.0 (orange)
- Output plots now include 4-line SSP comparison with 10-year rolling average

### Sites Added
| Country | Site | Lat | Lon |
|---------|------|-----|-----|
| Korea | HQ Seoul | 37.5649 | 126.9793 |
| Korea | R&D Seongnam | 37.4018 | 127.1615 |
| Korea | Pohang Plant | 35.9953 | 129.3744 |
| Korea | Gunsan Plant | 35.9676 | 126.7127 |
| Korea | Iksan Plant | 35.9490 | 126.9657 |
| Korea | Gwangyang Plant | 34.9155 | 127.6936 |
| Korea | Saehan Jeongeup | 35.6183 | 126.8638 |
| China | OCI Shanghai | 31.2305 | 121.4495 |
| China | Shandong OCI (ZZ) | 34.7979 | 117.2571 |
| China | MaSteel OCI (MAS) | 31.7097 | 118.5023 |
| China | Jianyang Carbon (ZZ) | 34.8604 | 117.3123 |
| Japan | OCI Japan Tokyo | 35.6458 | 139.7386 |
| Philippines | Philko Makati | 14.5547 | 121.0244 |

---

## [2026-03-15] — Regional Expansion (Japan, Philippines)

### Added
- Japan region (30-42N, 132-146E): SSP2-4.5 / SSP5-8.5, 12 variables
- Philippines region (10-22N, 118-128E): SSP2-4.5 / SSP5-8.5, 12 variables
- `download_scenarios_japan_ph.py` — regional download scripts
- `scenarios_v2/japan/`, `scenarios_v2/philippines/` data directories

---

## [2026-03-14] — scenarios_v2 Foundation

### Added
- `download_scenarios_v2.py` — CMIP6 monthly download (korea_china region, 7 models, 12 variables)
  - Models: ACCESS-CM2, MIROC6, MIROC-ES2L, FGOALS-F3-L, FGOALS-G3, KIOST-ESM, BCC-CSM2-MR
  - Variables: tas, tasmax, tasmin, pr, evspsbl, prsn, sfcWind, zos, mrro, mrsos, huss, rsds
  - Scenarios: SSP2-4.5, SSP5-8.5
  - Coverage: 30-42N, 110-132E, 2015-2100
- `scenario_analysis.py` — Initial 2-SSP time series analysis and decadal mean table
- Unit conversions: K→°C, kg/m²/s→mm/day, m→cm, kg/kg→g/kg

### Fixed
- cftime→datetime conversion for CMIP6 non-standard calendars (360_day, noleap)
- Land proxy fallback: nearest non-NaN grid cell for coastal sites

---

## [2026-03-13] — Project Initialization

### Added
- CLIMADA conda environment (`climada_env`, Python 3.12, miniforge3)
- CDS API configuration (`~/.cdsapirc`)
- `download_climada_data.py` — CLIMADA API downloads: river flood, tropical cyclone, earthquake, wildfire, LitPop
- `risk_analysis_final.py` — Coordinate-based hazard intensity extraction
- `ibtracs_analysis.py` — IBTrACS typhoon track analysis
- `download_era5.py` — ERA5 historical daily data (deferred)
- `download_slr.py` — Sea level rise (satellite + CMIP6)
- Initial `README.md`

---

## Data Inventory (as of 2026-03-17)

| Dataset | Files | Size | Location |
|---------|-------|------|----------|
| CMIP6 Monthly SSP2-4.5 (korea_china) | 12 zip | ~120 MB | scenarios_v2/ssp2_4_5/ |
| CMIP6 Monthly SSP5-8.5 (korea_china) | 12 zip | ~120 MB | scenarios_v2/ssp5_8_5/ |
| CMIP6 Monthly SSP1-2.6 (korea_china) | 12 zip | ~120 MB | scenarios_v2/ssp1_2_6/ |
| CMIP6 Monthly SSP3-7.0 (korea_china) | 12 zip | ~120 MB | scenarios_v2/ssp3_7_0/ |
| CMIP6 Monthly SSP2-4.5 (japan) | 12 zip | ~90 MB | scenarios_v2/japan/ssp2_4_5/ |
| CMIP6 Monthly SSP5-8.5 (japan) | 12 zip | ~90 MB | scenarios_v2/japan/ssp5_8_5/ |
| CMIP6 Monthly SSP1-2.6 (japan) | 12 zip | ~90 MB | scenarios_v2/japan/ssp1_2_6/ |
| CMIP6 Monthly SSP3-7.0 (japan) | 12 zip | ~90 MB | scenarios_v2/japan/ssp3_7_0/ |
| CMIP6 Monthly SSP2-4.5 (philippines) | 12 zip | ~50 MB | scenarios_v2/philippines/ssp2_4_5/ |
| CMIP6 Monthly SSP5-8.5 (philippines) | 12 zip | ~50 MB | scenarios_v2/philippines/ssp5_8_5/ |
| CMIP6 Monthly SSP1-2.6 (philippines) | 12 zip | ~50 MB | scenarios_v2/philippines/ssp1_2_6/ |
| CMIP6 Monthly SSP3-7.0 (philippines) | 12 zip | ~50 MB | scenarios_v2/philippines/ssp3_7_0/ |
| CMIP6 Daily SSP2-4.5 (korea_china) | 3 zip | ~34 MB | scenarios_v2/daily/ssp2_4_5/ |
| CMIP6 Daily SSP5-8.5 (korea_china) | 3 zip | ~34 MB | scenarios_v2/daily/ssp5_8_5/ |
| CMIP6 Daily SSP2-4.5 (japan) | 3 zip | ~25 MB | scenarios_v2/daily/japan/ssp2_4_5/ |
| CMIP6 Daily SSP5-8.5 (japan) | 3 zip | ~25 MB | scenarios_v2/daily/japan/ssp5_8_5/ |
| CMIP6 Daily SSP2-4.5 (philippines) | 3 zip | ~16 MB | scenarios_v2/daily/philippines/ssp2_4_5/ |
| CMIP6 Daily SSP5-8.5 (philippines) | 3 zip | ~16 MB | scenarios_v2/daily/philippines/ssp5_8_5/ |
| CLIMADA Hazard (flood/TC/quake/fire) | multiple | ~25 GB | data/hazard/ |
| LitPop (CHN) | 3 hdf5 | ~500 MB | data/exposures/ |
| **Analysis outputs** | **8 CSV + 40 PNG** | **~5 MB** | **scenarios_v2/output/** |

# Changelog — OCI Climate Physical Risk Analysis

All notable changes to this project are documented here.
Format: `[YYYY-MM-DD] TYPE: description`

---

## [2026-03-18] — Phase 11~14: 일별 정밀 ETCCDI + 재무 정량화 + 시급성 매트릭스 + 경영진 요약

### Added (Phase 11: 일별 데이터 정밀 ETCCDI)
- **`calc_phase11.py`** — 일별 CMIP6 데이터(4SSP) 기반 정밀 극한 지수
  - TX90p: 기준 90분위 초과 일수/년 (기준기간 2020-2039)
  - HWD: 폭염 지속일수 최대값 (>=3일 연속 TX>TX90 기준)
  - TX35/TX37/TX40: 온도 임계값별 초과 일수
  - FD/TR20/TR25: 서리일 / 열대야(20C/25C)
  - CDD/CWD: 연속 건조/습윤일 최대값 (실측 일별)
  - R10/R20/R30mm: 강우 임계값 초과 일수
  - Rx1day: 연최대 일강수량
- 출력: ph11_daily_heat/cold/precip/summary.csv (각 52×44~)

### Added (Phase 12: 재무 리스크 정량화)
- **`calc_phase12.py`** — EAL + 업무중단일수 추정
  - Sigmoid 피해함수: RiskScore -> 연간 자산 피해율 (0.01~5%)
  - Portfolio EAL SSP5-8.5 2090s: USD 22.3M/yr (자산 USD 10,750M 대비 0.21%)
  - 업무중단일수(BID): Philko 67일/yr, 중국사업장 36~39일/yr
- 출력: ph12_financial_risk/eal/disruption.csv + ph12_financial_bar.png

### Added (Phase 13: 시급성 매트릭스)
- **`calc_phase13.py`** — RiskScore 임계 도달연도 + 완화 편익
  - Risk>50 최초 도달: Philko 2025, Shandong/Jianyang 2045, 기타 2100+
  - 완화 편익(SSP5->SSP1): Portfolio USD 8.1M/yr 절감 가능 (2090s)
- 출력: ph13_urgency/mitigation_benefit.csv + urgency_heatmap/priority_bubble.png

### Added (Phase 14: 경영진 요약)
- **`calc_phase14.py`** — 사업장별 30개 KPI 원페이저 + 4패널 대시보드
  - ph14_executive_summary.csv: 13사업장 x 30개 핵심 지표
  - ph14_executive_dashboard.png: 리스크 랭킹 + EAL + 업무중단 + 완화편익 4패널

### Key Results (Phase 11~14, SSP5-8.5 2090s)
- **Philko Makati**: TX90p=294일/yr(!) BID=67일/yr(27% 매출손실), EAL USD 1.1M/yr
- **Shandong/Jianyang**: HWD 기준 TX35일수 급증, 2045년 Risk>50 최초 도달
- **한국 서울**: HWD 91일/yr, Rx1day 166mm, EAL USD 3.9M/yr (최대 단일사업장)
- **포항**: Rx1day 173mm, R30mm 18.7일/yr — 한국 내 홍수위험 최고
- **글완화 편익**: SSP5->SSP1 전환 시 포트폴리오 USD 81M 절감 (10년 누적)

---

## [2026-03-17] — Phase 6~10: 계절 분석 + 임계값 도달연도 + 종합 리스크 스코어 + 마스터 통합

### Added (Phase 6: 계절별 기후 분석)
- **`calc_phase6.py`** — 4계절(JJA/DJF/MAM/SON) × 4SSP × 8기간 × 13사업장
  - `ph6_seasonal_temp.csv` — Tmax/Tmin/Tmean 계절별 (52×99)
  - `ph6_seasonal_precip.csv` — 강수 + 적설 계절별 (52×67)
  - `ph6_seasonal_wind.csv` — 풍속 계절별 (52×35)
  - `ph6_heat_stress.csv` — JJA WBGT + Humidex + Discomfort Index (52×27)

### Added (Phase 7: 임계값 도달 연도)
- **`calc_phase7.py`** — 기온/극값 임계값 최초 초과 연도 분석
  - `ph7_exceedance_years.csv` — +1.5/2/3/4°C 도달연도, TXx>35/37/40°C, 마지막 서리일 (52×19)
  - `ph7_warming_timeline.csv` — 5년 간격 10년 롤링 온난화량 타임라인 (780×5)

### Added (Phase 8: 종합 리스크 스코어)
- **`calc_phase8.py`** — 8개 위험 차원 0-100 정규화 + 가중 합산
  - `ph8_risk_score.csv` — 전체 매트릭스 416행 (13사업장×4SSP×8기간) × 14열
  - `ph8_risk_summary.csv` — SSP5-8.5 2090s 랭킹 (13×14)
  - `ph8_risk_heatmap.png` — 4SSP × 8차원 리스크 히트맵
  - `ph8_risk_trajectory.png` — 사업장별 리스크 궤적 3×5 그리드
  - `ph8_risk_radar.png` — 사업장별 레이더 차트 (4SSP 오버레이)

### Added (Phase 9: 추가 물리 변수)
- **`calc_phase9.py`** — mrro/mrsos/rsds 지수 추출
  - `ph9_runoff.csv` — 지표유출 연간/계절별 (52×35)
  - `ph9_soilmoisture.csv` — 토양수분 + 여름 결핍 지수 (52×35)
  - `ph9_solar.csv` — 태양복사 연간/JJA/DJF, kWh/m²/day (52×35)
  - `ph9_water_stress.csv` — 물 스트레스 복합 지수 (52×19)

### Added (Phase 10: 마스터 통합)
- **`calc_phase10.py`** — Phase 1~9 전체 통합 + 최종 시각화
  - `OCI_MASTER_ALL.csv` — **416행 × 59열** (13사업장 × 4SSP × 8기간 × 55개 기후 지표)
  - `ph10_risk_bar_2090s.png` — 4SSP × 13사업장 리스크 스코어 막대 비교
  - `ph10_trend_summary.png` — 6개 핵심 지표 SSP5-8.5 추세 (사업장 오버레이)
  - `ph10_exceedance_heatmap.png` — 임계값 도달연도 히트맵 (4SSP × 13사업장)

### Key Results (Phase 6~10, SSP5-8.5 2090s)
- **Philko Makati (Philippines)**: RiskScore=68.3 (High), JJA WBGT=38.6°C (작업 중단 위험), TR=365일/년
- **Shandong/Jianyang (China)**: TXx>35°C 2027년 도달, TXx>40°C 2083년, RiskScore=49.2
- **Seoul HQ**: +1.5°C 2049년, +2°C 2057년, +4°C 2083년 도달
- **Pohang Plant**: 연간 유출량 2090s 873mm (2020s 533mm 대비 +64%)
- **SSP5-8.5 평균 리스크**: 44.9점 (범위 37~68), SSP2-4.5: 39.9점

---

## [2026-03-17] — Phase 1~5 완전 완료 + 4-SSP ETCCDI + GEV 분석 + 글로벌 확장

### Added (Phase 1: 추가 기후 지수)
- **`calc_phase1.py`** — 5개 추가 기후 지수 계산 (13사업장 × 4SSP × 8기간):
  - CDD/HDD (냉난방도일, base 18°C)
  - Humidex + Apparent Temperature (Environment Canada 공식)
  - SPI-3 (3개월 표준화 강수지수, log-normal 근사)
  - FWI proxy (화재기상지수, 0-100 스케일)
  - P-E Balance (강수-증발산 균형)
- **`ph1_cdd_hdd.csv`** — CDD/HDD 8기간 × 13사업장 × 4SSP (26×19)
- **`ph1_humidex.csv`** — Humidex + AT 8기간 × 13사업장 × 4SSP (26×20)
- **`ph1_spi3.csv`** — SPI-3 8기간 × 13사업장 × 2SSP (26×11)
- **`ph1_fwi.csv`** — FWI 8기간 × 13사업장 × 4SSP (26×19)
- **`ph1_pe_balance.csv`** — P-E 8기간 × 13사업장 × 2SSP (26×11)

### Added (Phase 2: SSP1-2.6 + SSP3-7.0 일별 데이터)
- **`download_daily_ssp13.py`** — SSP1-2.6 + SSP3-7.0 일별 CMIP6 다운로드
  - 3지역(korea_china, japan, philippines) × 2시나리오 × 3변수 = 18파일 (~165 MB)
  - 저장: `scenarios_v2/daily/{ssp1_2_6,ssp3_7_0}/`

### Added (Phase 3: 4-SSP ETCCDI 완전 세트)
- **`calc_etccdi_4ssp.py`** — 4개 SSP 전체에 대한 ETCCDI 13지수 계산
- **`ph3_etccdi_4ssp.csv`** — 13지수 × 4SSP × 8기간 × 13사업장 (5408×7)
  - SSP1-2.6 / SSP2-4.5 / SSP3-7.0 / SSP5-8.5 완전 세트

### Added (Phase 4: GEV 재현기간 + 복합극한)
- **`calc_phase4.py`** — GEV 분포 피팅 및 복합극한 이벤트 분석
  - GEV (scipy.stats.genextreme): 10/50/100년 재현기간 강수량
  - 복합극한: P(Tmax > 90th pct AND pr < 1mm) — 근기(2020-2059) / 원기(2060-2099)
- **`ph4_return_period.csv`** — GEV 재현기간 강수량 (26×11)
- **`ph4_compound_events.csv`** — 복합 폭염+건조 이벤트 확률 (26×7)

### Added (Phase 5: 최종 통합)
- **`calc_phase5_final.py`** — Phase 1~4 전체 통합 마스터 파일 생성
- **`OCI_4SSP_ETCCDI_SUMMARY.csv`** — 4SSP × 13지수 2090s 와이드 피벗 (13×54)
- **`OCI_MASTER_SUMMARY_SSP585.csv`** — SSP5-8.5 2090s 전체 지수 통합 (13×23)
- **`OCI_TXx_4SSP_Trajectory.csv`** — TXx 4SSP × 8기간 궤적 (13×34)

### Added (글로벌 확장)
- **`download_global_monthly.py`** — 11개 글로벌 지역 월별 CMIP6 (12var × 4SSP = 528파일)
- **`download_global_daily.py`** — 11개 글로벌 지역 일별 CMIP6 (3var × 2SSP = 66파일)
- 대상 지역: europe_west, europe_east, north_america_east/west, southeast_asia, south_asia, middle_east, south_america, australia, africa_north, africa_south

### Key Results (Phase 5 Master Summary, SSP5-8.5 2090s)
- **Philippines Philko Makati**: CDD 5,133일, WBGT 30.7°C, RL100yr 543.5mm, CompoundHotDry 7.6%
- **China Shandong/Jianyang**: TXx 33.1°C, CompoundHotDry 8.2%, RL100yr 291mm
- **Japan Tokyo**: RL100yr 471.5mm (동아시아 최고 홍수위험), CompoundHotDry 5.9%
- **Korea HQ Seoul**: CDD 1,036일, TXx 24.8°C, RL100yr 460mm
- **TXx SSP Spread** (서울 기준): SSP1 +20.6°C → SSP2 +21.3°C → SSP3 +23.1°C → SSP5 +24.8°C

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
| CMIP6 Monthly 4SSP (korea_china) | 48 zip | ~480 MB | scenarios_v2/{ssp}/ |
| CMIP6 Monthly 4SSP (japan) | 48 zip | ~360 MB | scenarios_v2/japan/{ssp}/ |
| CMIP6 Monthly 4SSP (philippines) | 48 zip | ~200 MB | scenarios_v2/philippines/{ssp}/ |
| CMIP6 Daily 4SSP (korea_china) | 12 zip | ~68 MB | scenarios_v2/daily/{ssp}/ |
| CMIP6 Daily 4SSP (japan) | 12 zip | ~50 MB | scenarios_v2/daily/japan/{ssp}/ |
| CMIP6 Daily 4SSP (philippines) | 12 zip | ~32 MB | scenarios_v2/daily/philippines/{ssp}/ |
| CMIP6 Monthly 4SSP (global 11 regions) | 528 zip | ~진행중 | data/global/{region}/{ssp}/ |
| CMIP6 Daily 2SSP (global 11 regions) | 66 zip | ~진행중 | data/global_daily/{region}/{ssp}/ |
| CLIMADA Hazard (flood/TC/quake/fire) | multiple | ~25 GB | data/hazard/ |
| LitPop (CHN) | 3 hdf5 | ~500 MB | data/exposures/ |
| **Phase 1~5 Analysis outputs** | **11 CSV** | **~2 MB** | **scenarios_v2/output/** |
| **FINAL outputs** | **4 CSV + 40 PNG** | **~3 MB** | **output/** |

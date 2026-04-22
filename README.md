# OCI Climate Physical Risk Analysis System

**위도·경도 입력 → 기후 물리적 리스크 정량 결과 자동 출력**
- 대상: 14개 사업장 (KOR 8, CHN 4, JPN 1, PHL 1)
- 소스: **8개 데이터 소스 × 38개 동인** (CMIP6 + PhyRisk + CLIMADA + SLR AR6 + Aqueduct + PSHA + ISIMIP3b + NEX-GDDP)
- 출력: 4-Output 표준 결과물 (원시데이터 / 위험도 히트맵 / 우선순위 / 재무추정)

---

## 빠른 시작 — 위도경도 → 결과 (★ 주력 파이프라인)

```bash
# 1. sites_config.py 에 사업장 추가
#    "사업장명": (위도, 경도, "국가코드", "한글명", 자산USD_M, 매출USD_M)

# 2. 38개 동인 전체 분석 실행 (약 3~5분)
C:/Users/24jos/miniforge3/envs/climada_env/python.exe calc_full_climate_risk.py

# 3. site_output/ 폴더에서 4개 결과물 확인
#    OUTPUT1_기후동인_원시데이터.xlsx  — CMIP6+NEX-GDDP 원시값, 9시점×4SSP, RAG색상
#    OUTPUT2_동인별_위험도.xlsx        — 38개 동인 × 14사업장 위험도 히트맵
#    OUTPUT3_우선순위_리스크.xlsx      — 단기·중기·장기 Top5 우선순위
#    OUTPUT4_재무적_위험추정.xlsx      — BID/에너지/홍수/SLR/TC 재무추정
```

**레거시 멀티소스 분석** (구버전 호환):
```bash
C:/Users/24jos/miniforge3/envs/climada_env/python.exe calc_multisource_risks.py
# 출력: OCI_MultiSource_Risks.xlsx, OCI_CMIP6_Only.xlsx 등 5종
```

---

## 데이터 소스 체계 (8종 × 38개 동인)

| # | 데이터 소스 | 동인 수 | 내용 | 경로 |
|---|-------------|---------|------|------|
| 1 | **CMIP6 17-모델 앙상블** | 7 | tasmax/tasmin/tas/pr/sfcWind/prsn/evspsbl | `data/scenarios/cmip6_v2/` |
| 2 | **OS-Climate PhyRisk** | 15 | 열스트레스/가뭄/수자원/홍수/바람/산불/강수 | `data/physrisk/physrisk_long.csv` |
| 3 | **CLIMADA Hazard HDF5** | 4 | TC EAL / 홍수 AAL / 지진빈도 / 산불빈도 | `data/hazard/` |
| 4 | **IPCC AR6 SLR** | 1 | 해수면 상승 중간값 (해안 6개 사업장) | `data/slr/slr_ar6_coastal_sites.csv` |
| 5 | **WRI Aqueduct 4.0** | 5 | 수자원스트레스/하천홍수/연안홍수/가뭄/변동성 | `data/aqueduct/aqueduct4_sites_literature.csv` |
| 6 | **지진 PSHA** | 2 | PGA 재현주기 475년/2475년 | `data/seismic/psha_literature_sites.csv` |
| 7 | **ISIMIP3b** | 1 | 홍수일수 변화 (delta days/yr vs 기준기후) | `data/isimip3b/isimip3b_flood_delta.csv` |
| 8 | **NASA NEX-GDDP** | 3 | tasmax/tasmin/pr (독립 검증 소스) | `data/nexgddp/nexgddp_sites_long.csv` |

---

## 데이터 소스 상세

### 1. CLIMADA Hazard (h5py 직접 접근)
- **형식**: HDF5 — `centroids/{lat, lon}` + `intensity{data, indices, indptr}` (CSR sparse) + `frequency`
- **읽기**: h5py + scipy.sparse.csr_matrix (CLIMADA Python 패키지 불필요)
- **스크립트**: `make_excel_climada_physrisk.py`의 `find_nearest_centroid()`
  - 30M 이하 centroid: 전체 로드 후 argmin
  - 30M 초과 (글로벌 TC 61개 파일): 규칙 그리드 구조로 메모리 없이 처리

| 위험 | 폴더 | 국가 | 지표 |
|------|------|------|------|
| Flood | `flood/flood_{KOR,CHN,JPN,PHL}` | KOR/CHN/JPN/PHL | RP10~250yr 수심(m) |
| River Flood | `river_flood/` | — | RP10~250yr 수심(m) |
| Tropical Cyclone | `tropical_cyclone/TC_{KOR,CHN,JPN,PHL}_0300as_STORM_*` | 61개 파일 | 풍속(m/s), 역사+RCP2.6/4.5/6.0/8.5 |
| Wildfire | `wildfire/wildfire_{KOR,CHN,JPN,PHL}_150arcsec_historical_*` | — | 복사열(kW/m²) |
| Earthquake | `earthquake/earthquake_hist_above4_{410,156,392,608}` | 국가코드 | PGA(g) |

---

### 2. OS-Climate PhyRisk
- **API**: physrisk-lib 1.7.1, AWS S3 공개 데이터
- **다운로드**: `download_physrisk.py`
- **파일**: `physrisk_long.csv` — 1,890행 (14사업장 × 11지표 × 3SSP × 3시점)
- **시나리오**: ssp126 / ssp245 / ssp585
- **시점**: 2030 / 2050 / 2090
- **주요 지표**: flood_depth, wind_speed, wildfire_risk, drought_index, heatwave_days, sea_level_rise 등

---

### 3. CMIP6 17-모델 앙상블 (Copernicus CDS)
- **다운로드**: `download_cmip6_v2.py` (cdsapi) → 478개 NC 파일
- **저장**: `c:/Users/24jos/climada/data/scenarios/cmip6_v2/{east_asia, se_asia}/`
- **모델 17개**:
  ```
  access_cm2, awi_cm_1_1_mr, bcc_csm2_mr, canesm5, cmcc_esm2,
  cnrm_cm6_1, fgoals_g3, gfdl_esm4, hadgem3_gc31_ll, inm_cm5_0,
  ipsl_cm6a_lr, miroc6, mpi_esm1_2_lr, mri_esm2_0, nesm3,
  noresm2_mm, ukesm1_0_ll
  ```
- **시나리오**: SSP1-2.6 / SSP2-4.5 / SSP3-7.0 / SSP5-8.5
- **변수 7개**: tasmax, tasmin, tas, pr, prsn, sfcWind, evspsbl
- **앙상블 구축**: `build_ensemble.py` → 통계(mean/median/p10/p90/std) + 지역별 최신뢰 모델

| 파일 (`data/ensemble/`) | 내용 | 크기 |
|-------------------------|------|------|
| `cmip6_ensemble_periods.csv` | 기간별 앙상블 통계 | 1,960행 |
| `cmip6_ensemble_annual.csv` | 연간 시계열 | 19,264행 |
| `cmip6_model_skill.csv` | 모델 신뢰도 평가 | 224행 |
| `cmip6_all_models_raw.csv` | 전체 모델 원시값 | 299,796행 |
| `best_model_by_region.csv` | 지역별 최신뢰 모델 | — |
| `site_tasmax_scenario_table.csv` | 사업장별 기온 시나리오 요약 | — |

---

### 4. IBTrACS 태풍 이력
- **다운로드**: `download_ibtracs.py`
- **파일**: `ibtracs_site_stats.csv` — 사업장별 태풍 빈도/강도 통계 (1980-2023)
- **범위**: WP(서태평양) 경보 구역, 14개 사업장 반경별 이벤트 집계

---

### 5. NASA NEX-GDDP-CMIP6
- **접근**: s3fs (anon=True) + xarray (engine="h5netcdf")
- **다운로드**: `download_nexgddp.py` (증분 저장, nexgddp_log.json으로 재시작 안전)
- **파일**: `nexgddp_sites_long.csv` — 1,247행 (89 유효 항목 × 14 사업장)
- **참고**: 576개 항목 중 487개 S3 미존재(no_data), 89개 유효 데이터

---

## 분석 파이프라인

```
[STEP 1: 데이터 다운로드]
  download_cmip6_v2.py         → cmip6_v2/ (478 NC 파일, east_asia/se_asia)
  download_cmip6_global.py     → cmip6_v2/{north_america,europe,...} (글로벌 11개 지역)
  download_physrisk.py         → physrisk_long.csv (1,890행)
  download_climada_hazards.py  → hazard/ (TC/홍수/지진/산불 HDF5)
  download_nexgddp.py          → nexgddp_sites_long.csv (NEX-GDDP)
  [수동 구축]                  → slr_ar6_coastal_sites.csv
                               → aqueduct4_sites_literature.csv
                               → psha_literature_sites.csv
                               → isimip3b_flood_delta.csv

[STEP 2: 앙상블 구축]
  build_ensemble.py            → cmip6_ensemble_periods.csv (east_asia/se_asia)
  build_ensemble_global.py     → cmip6_ensemble_all_regions.csv (전체 14사업장 × 9시점)

[STEP 3: ★ 표준 4-Output 파이프라인 (38개 동인)]
  calc_full_climate_risk.py    → OUTPUT1~4 Excel 4종
    OUTPUT1_기후동인_원시데이터.xlsx   (CMIP6 7변수 + NEX-GDDP 3변수, 9시점×4SSP)
    OUTPUT2_동인별_위험도.xlsx         (38개 동인 × 14사업장 히트맵 + 범례)
    OUTPUT3_우선순위_리스크.xlsx       (단·중·장기 Top5, SSP5-8.5 기준)
    OUTPUT4_재무적_위험추정.xlsx       (BID/에너지/홍수/SLR/TC 재무추정)

[STEP 4: 레거시 멀티소스 분석]
  calc_all_climate_risks.py    → OCI_AllRisks_SSP_2100_v2.xlsx
  calc_multisource_risks.py    → 소스별 단독 + 통합 + 가중복합 Excel 5종

[STEP 5: Phase 분석 1~20 (레거시)]
  calc_phase1~20.py            → OCI_MASTER_FINAL.csv (416행 × 123열)
  interpret_A~H.py             → 해석 프레임워크 7단계 Excel/PNG
```

---

## Excel 출력 파일

### ★ 표준 4-Output (38개 동인, 최신)

| 파일 | 크기 | 내용 |
|------|------|------|
| `OUTPUT1_기후동인_원시데이터.xlsx` | ~61KB | CMIP6(7)+NEX-GDDP(3) 원시값, P10~P90, 9시점×4SSP, RAG 색상 |
| `OUTPUT2_동인별_위험도.xlsx` | ~51KB | **38개 동인** × 14사업장 × 4시점 히트맵 (소스별 색상) + 범례·임계값 시트 |
| `OUTPUT3_우선순위_리스크.xlsx` | ~7KB | 단기·중기·장기 Top5 우선순위 리스크 (SSP5-8.5, 38동인 기준) |
| `OUTPUT4_재무적_위험추정.xlsx` | ~9KB | BID열스트레스/에너지/홍수/SLR/TC 항목별 재무추정 + 산정식 설명 시트 |

**재무 산정식**:
- BID열스트레스 = WBGT초과일/365 × 매출 × 손실률(KOR 5.8%, CHN 7.2%, JPN 4.5%, PHL 9.5%)
- 에너지비용 = CDD(>32°C) × 바닥면적(자산 1M$→200m²) × kWh계수 × 0.12$/kWh
- 홍수피해 = (Rx1day/300 + ISIMIP홍수일×0.02) × 자산 × 5%
- SLR대응 = SLR_median(m) × 2% × 자산 (해안 사업장)
- TC피해 = TC_EAL(m/s·yr) × 계수(KOR/JPN 3%, CHN 5%, PHL 8%) × 자산

### 레거시 멀티소스 분석

| 파일 | 크기 | 내용 |
|------|------|------|
| `OCI_AllRisks_SSP_2100_v2.xlsx` | ~123KB | 12개 동인 × 4SSP × 9연도 |
| `OCI_MultiSource_Risks.xlsx` | ~83KB | 통합 멀티소스 (16시트) |
| `OCI_CMIP6_Only.xlsx` | ~53KB | CMIP6 단독 |
| `OCI_CLIMADA_Only.xlsx` | ~20KB | CLIMADA 단독 |
| `OCI_PhyRisk_Only.xlsx` | ~87KB | PhyRisk 단독 (15지표 피벗) |
| `OCI_Weighted_Composite.xlsx` | ~33KB | 가중복합 (CMIP6 60%+PhyRisk 25%+CLIMADA 15%) |
| `OCI_CLIMADA_PhyRisk.xlsx` | ~125KB | CLIMADA + PhyRisk 원본 (9시트) |
| `OCI_CMIP6_Ensemble.xlsx` | ~322KB | CMIP6 17-모델 앙상블 기간별/연간 통계 |

---

## 주요 분석 결과 (SSP5-8.5, 2090s)

| 지표 | 값 |
|------|----|
| 포트폴리오 EAL | USD 22.3M/yr |
| 추가 에너지비용 | USD 198M/yr |
| 합계 기후비용 | ~USD 220M/yr (총자산 USD 10,750M의 2.0%) |
| 최고위험 사업장 | Philko Makati (RiskScore 74.8, BID 67일/yr, Tw>28°C 185.5일/yr) |
| 한국 EAL | USD 16.3M/yr |
| 중국 BID | 37.3일/yr (한국 대비 +50%) |
| 완화 편익 (SSP5→SSP1) | 10년 누적 USD 81M 절감 가능 |
| 최종 마스터 | OCI_MASTER_FINAL.csv — 416행 × 123열 |

---

## 14개 사업장 좌표

| 사업장 | 위도 | 경도 | 국가 | CMIP6 지역 |
|--------|------|------|------|-----------|
| OCI_HQ_Seoul | 37.5649 | 126.9793 | KOR | east_asia |
| OCI_Dream_Seoul | 37.5172 | 126.9000 | KOR | east_asia |
| OCI_RnD_Seongnam | 37.3219 | 127.1190 | KOR | east_asia |
| Pohang_Plant | 36.0095 | 129.3435 | KOR | east_asia |
| Gwangyang_Plant | 34.9393 | 127.6961 | KOR | east_asia |
| Gunsan_Plant | 35.9700 | 126.7114 | KOR | east_asia |
| Iksan_Plant | 35.9333 | 127.0167 | KOR | east_asia |
| Saehan_Recycle | 35.9333 | 127.0167 | KOR | east_asia |
| OCI_Shanghai | 31.2304 | 121.4737 | CHN | east_asia |
| MaSteel_OCI | 31.6839 | 118.5127 | CHN | east_asia |
| Shandong_OCI | 34.7979 | 117.2571 | CHN | east_asia |
| Jianyang_Carbon | 26.7587 | 104.4734 | CHN | east_asia |
| OCI_Japan_Tokyo | 35.6762 | 139.6503 | JPN | east_asia |
| Philko_Makati | 14.5995 | 120.9842 | PHL | se_asia |

---

## 환경 설정

```bash
# conda 환경 활성화
C:/Users/24jos/miniforge3/Scripts/activate climada_env
# Python 3.12, miniforge3

# CDS API 설정
# C:/Users/24jos/.cdsapirc 필요 (Copernicus CDS 계정)

# OS-Climate PhyRisk
# pip install physrisk-lib==1.7.1

# AWS S3 (NEX-GDDP) — 별도 계정 불필요 (anon=True)
# pip install s3fs h5netcdf
```

### 주요 패키지
```
xarray, pandas, numpy, matplotlib, scipy
cdsapi, h5py, s3fs, h5netcdf
physrisk-lib==1.7.1
```

---

## 스크립트 인덱스

### 핵심 분석 (위도경도 → 결과)

| 스크립트 | 역할 | 출력 |
|----------|------|------|
| `calc_multisource_risks.py` | ★ 멀티소스 통합 — 위도경도 입력 → 5종 Excel | OCI_*_Only.xlsx + OCI_Weighted_Composite.xlsx |
| `calc_all_climate_risks.py` | 12동인 × 4SSP × 9연도 전체 분석 | OCI_AllRisks_SSP_2100_v2.xlsx |

### 데이터 다운로드

| 스크립트 | 역할 |
|----------|------|
| `download_cmip6_v2.py` | CMIP6 17모델 × 4SSP × 7변수 (CDS API) |
| `download_physrisk.py` | OS-Climate PhyRisk (physrisk-lib) |
| `download_climada_hazards.py` | CLIMADA HDF5 위험 파일 |
| `download_ibtracs.py` | IBTrACS WP 태풍 이력 |
| `download_nexgddp.py` | NASA NEX-GDDP-CMIP6 (S3 anon, 증분) |
| `download_aqueduct.py` | WRI Aqueduct 수자원 위험 |
| `download_era5_baseline.py` | ERA5 현재기후 기준값 (2022-2024) |

### 앙상블 구축 & 통합

| 스크립트 | 역할 |
|----------|------|
| `build_ensemble.py` | 17-모델 앙상블 통계 + 지역별 최신뢰 모델 선정 |
| `build_ensemble_global.py` | 글로벌 확장 앙상블 |
| `integrate_all_data.py` | 전체 소스 통합 → master_risk_table (14×37) |

### Phase 분석 (1~20)

| 스크립트 | 역할 |
|----------|------|
| `calc_phase1~20.py` | Phase별 기후지수 + 리스크 분석 (전체 완료) |
| `calc_ssp_scenarios.py` | 4-SSP 시나리오 분기 분석 |

### 레거시 Excel & 비교

| 스크립트 | 역할 |
|----------|------|
| `make_excel_climada_physrisk.py` | CLIMADA Hazard + OS-Climate PhyRisk (9시트) |
| `make_excel_cmip6.py` | CMIP6 17-모델 앙상블 결과 |
| `compare_all_sites.py` | 전체 사업장 비교 분석 |
| `compare_korea_sites.py` | 한국 사업장 비교 |
| `analyze_site.py` | 단일 사업장 상세 분석 |

---

## 데이터 출처

| 소스 | 라이선스 | 설명 |
|------|---------|------|
| Copernicus CDS (CMIP6) | CC BY 4.0 | CMIP6 월별/일별 시나리오 |
| CLIMADA (ETH Zurich) | GPL 3.0 | 홍수/TC/산불/지진 HDF5 |
| OS-Climate PhyRisk | Apache 2.0 | 물리적 위험 지표 API |
| IBTrACS (NOAA) | Public Domain | 서태평양 태풍 이력 |
| NASA NEX-GDDP | Public Domain | 통계적 다운스케일 시나리오 |
| WRI Aqueduct | CC BY 4.0 | 수자원 위험 |

---

---

## 주요 계수 및 출처

| 동인 | 계수/방법 | 출처 |
|------|-----------|------|
| 폭염일 스케일 | 7.0일/°C (KOR), 8.0 (CHN/JPN/PHL) | Fischer & Schär (2010) Nat. Geosci. |
| 습구온도 | Tw = T × atan(0.151977×(RH+8.313659)^0.5) + ... | Stull (2011) J. Appl. Meteor. |
| 해수면상승 | IPCC AR6 Table 9.9 + CMIP6 zos | Fox-Kemper et al. (2021) |
| TC 빈도변화 | SSP5-8.5 2100년 −20% (강도는 +10%) | Emanuel (2020), Knutson et al. (2020) |
| 산불위험 FWI | CMIP6 sfcWind/pr/tas/prsn 복합 | Van Wagner (1987) |
| 아리디티 | AI = pr / evsp (0.01 임계, 5.0 상한) | UNEP (1992) |

---

*Last updated: 2026-04-06 (멀티소스 통합 + 위도경도 워크플로 완성 + 소스별 단독 출력 5종)*

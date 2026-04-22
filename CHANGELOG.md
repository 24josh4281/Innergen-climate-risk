# Changelog — OCI Climate Physical Risk Analysis

All notable changes to this project are documented here.
Format: `[YYYY-MM-DD] TYPE: description`

---

## [2026-04-10] — 전체 38개 기후 동인 통합 (8개 소스 완전 통합)

### 개요
기존 5개 CMIP6 변수에서 **8개 데이터 소스 × 38개 동인** 으로 전면 확장.
스크립트: `calc_full_climate_risk.py` (전면 재작성)

### 통합 동인 목록 (38개)

| 소스 | 동인 수 | 항목 |
|------|---------|------|
| CMIP6 17-모델 앙상블 | 7 | tasmax / tasmin / tas / pr / sfcWind / prsn / evspsbl |
| OS-Climate PhyRisk | 15 | DD32c / TX35 / TX40 / WorkLoss_H / WorkLoss_M / WBGT / SPI3 / SPI12 / WaterStress / WaterDepletion / FloodRiver / FloodCoastal / WindMax / FireProb / Rx1day |
| CLIMADA HDF5 | 4 | TC_EAL / Flood_AAL / EQ_freq / Wildfire_freq |
| IPCC AR6 SLR | 1 | SLR_median_m (해수면 상승, 해안 사업장 6개) |
| WRI Aqueduct 4.0 | 5 | AQ_WaterStress / AQ_RiverFlood / AQ_CoastalFlood / AQ_Drought / AQ_Variability |
| 지진 PSHA | 2 | PGA_475yr / PGA_2475yr (KBC/J-SHIS/PHIVOLCS) |
| ISIMIP3b | 1 | ISIMIP_FloodDays (홍수일수 변화 delta days/yr) |
| NASA NEX-GDDP | 3 | NEXGDDP_tasmax / NEXGDDP_tasmin / NEXGDDP_pr |

### RAG 임계값 체계
- 모든 38개 동인에 AMBER / RED 2단계 임계값 설정 (IPCC/ILO/ISO/WRI/USGS 기준)
- OUTPUT2에 소스별 색상 구분 및 범례·임계값 설명 시트 추가

### 출력 파일
- `OUTPUT1_기후동인_원시데이터.xlsx` — CMIP6(7) + NEX-GDDP(3) × 9시점 × 4SSP
- `OUTPUT2_동인별_위험도.xlsx` — 38개 동인 × 14사업장 × 4시점 히트맵 + 범례시트
- `OUTPUT3_우선순위_리스크.xlsx` — 단·중·장기 Top5 (38개 동인 기준 재산출)
- `OUTPUT4_재무적_위험추정.xlsx` — SLR AR6 + ISIMIP3b 실데이터 반영 재무추정

---

## [2026-04-10] — 좌표 입력 → 4-Output 기후 리스크 표준 결과물 체계 (구현 완료)

### 개요
좌표(위도/경도/자산/매출)를 입력하면 아래 4개 결과물을 자동 생성하는 표준 파이프라인.
스크립트: `calc_full_climate_risk.py`

### Output 1: 시나리오별 기후 동인 원시 데이터
- **범위**: SSP 4개 × 9개 시점(현재·2030·2040·2050·2060·2070·2080·2090·2100)
- **동인**: 기온(tasmax/tasmin/tas), 강수(pr), 바람(sfcWind), WBGT, CDD, 극한강수(Rx1day), SLR, FWI, TC빈도·강도 등 12개
- **통계**: 앙상블 평균 / P10 / P90 / 표준편차 / 지역 최적 모델값 / 모델수
- **파일**: `site_output/OUTPUT1_기후동인_원시데이터.xlsx`

### Output 2: 동인별 위험도 분류
- **기준**: IPCC AR6 / ILO / ISO 7933 / WMO 기반 GREEN-AMBER-RED 3단계
- **시점별 위험도 변화**: 현재 → 2030 → 2050 → 2100 추이
- **파일**: `site_output/OUTPUT2_동인별_위험도.xlsx`

### Output 3: 단기·중기·장기 우선순위 리스크 (1~5순위)
- **단기(~2030)**: 즉각 대응 필요 리스크
- **중기(2031~2050)**: CAPEX 계획 필요 리스크
- **장기(2051~2100)**: 전략적 전환 필요 리스크
- **파일**: `site_output/OUTPUT3_우선순위_리스크.xlsx`

### Output 4: 재무적 위험 추정
- **산정식 (사용자 제공 자산/매출 기반)**:
  - EAL(기대연간손실) = CLIMADA HDF5 피해함수 × 자산가치
  - 열스트레스 BID = WBGT초과일 × (매출/영업일수) × 생산성손실율(ILO)
  - 에너지비용 = CDD증가분 × 연면적 × 단위에너지비 × 전기요금(국가별)
  - 홍수피해 = Rx1day초과확률 × 자산 × 노출도 × 피해율
  - SLR 방호비 = 해수면상승(m) × 연안노출 × 단위방호비
  - 보험료증가 = 종합리스크점수 → 승수 → 추가보험료
- **파일**: `site_output/OUTPUT4_재무적_위험추정.xlsx`

### 기간 정의 (CMIP6 5년 윈도우)
| 시점명 | 데이터 기간 |
|--------|-----------|
| 현재   | 2020-2024 |
| 2030   | 2028-2032 |
| 2040   | 2038-2042 |
| 2050   | 2048-2052 |
| 2060   | 2058-2062 |
| 2070   | 2068-2072 |
| 2080   | 2078-2082 |
| 2090   | 2088-2092 |
| 2100   | 2096-2100 |

---

## [2026-04-10] — CMIP6 글로벌 다운로드 완료 + 지역별 모델 성능 분석

- 신규 지역 NC 파일 다운로드 완료: south_america / africa / oceania / central_asia / russia_siberia
- `build_model_ranking.py`: 지역×변수별 모델 스킬 점수, 지역 추천 모델 산출
- `calc_site_model_comparison.py`: 사업장별 앙상블 vs 지역 최적 모델 비교
- `site_output/모델별_지역_성능.xlsx`, `사업장별_앙상블_모델비교.xlsx` 생성
- OCI 14개 사업장 전체로 `sites_config.py` 업데이트

---

## [2026-04-08] — Phase H (계획): 10년 단위 SSP별 종합 보고서 (미구현)

### Planned (interpret_H_decadal_report.py)
**목적**: 4개 SSP 시나리오 × 10년 단위(2020s·2030·2040·2050) × 사업장별로
"무엇이 위험한가", "무엇이 필요한가"를 raw data → 해석 → 데이터 출처까지
단일 파일(Excel)에 일체 수록

**출력 파일**: `site_output/H_SSP별_10년_종합보고서.xlsx`

**시트 구성 (안)**

| 시트 | 내용 |
|------|------|
| `표지_요약` | 4SSP × 4시점 포트폴리오 위험 수준 요약 매트릭스 (RAG) |
| `SSP1_2020s` ~ `SSP5_2050` | 4×4 = 16개 시트 — 각 SSP × 시점별 상세 |
| `원본데이터_CMIP6` | CMIP6 앙상블 12개 동인 원시값 (사업장 × SSP × 연도) |
| `원본데이터_PhyRisk` | OS-Climate PhyRisk 원본 롱포맷 |
| `원본데이터_CLIMADA` | CLIMADA HDF5 추출값 (EAL, 풍속, 홍수깊이, 지진MMI) |
| `해석_방법론` | 동인별 RAG 임계값, 계수, 변환 공식, 불확실성 |
| `데이터출처` | 전체 소스 메타정보 (출처 기관, DOI, 라이선스, 접근일) |

**각 SSP × 시점 시트 구조**

```
[1] 시점 개요 — 전 사업장 복합점수 RAG 요약표
[2] 원시값 테이블 — 12개 동인 × 8사업장 실제 수치 (p10/mean/p90)
[3] 동인별 해석 — 각 동인이 왜 위험한지, 어떤 운영 임팩트인지
[4] 필요 대응조치 — 즉각/단기/중기 구분, 담당부서 및 비용 규모
[5] 데이터 출처 — 해당 시트 수치의 소스 기관, 버전, 불확실성 등급
```

**10년별 해석 프레임 (안)**

| 시점 | 해석 초점 | 대응 성격 |
|------|-----------|-----------|
| 2020s (현재기후 기준) | 기준값 대비 초과 여부 확인, 현재 노출 수준 | 즉각 대응, 현황 파악 |
| 2030년 | 단기 리스크 가시화, CAPEX 계획 창 | 투자계획 반영, 조기 경보 |
| 2040년 | 기후 신호 명확화, SSP 분기 시작 | 시나리오 분기 대응, 보험 재검토 |
| 2050년 | 중기 리스크 정점, SSP별 격차 최대 | 장기 전략 결정, 이전·폐기 vs 강화 |

**데이터 출처 통합 표 (데이터출처 시트)**

| 소스 | 기관 | 버전/접근일 | 공간해상도 | 라이선스 | 불확실성 |
|------|------|-------------|------------|----------|----------|
| CMIP6 앙상블 | WCRP / CDS | 2024-11 | 0.25° | CC BY 4.0 | 모델 간 ±15% |
| OS-Climate PhyRisk | OS-Climate | v1.7.1 | 사업장 포인트 | Apache 2.0 | ±25% |
| CLIMADA HDF5 | ETH Zürich | v3.3 | 150arcsec | GPL 3.0 | ±30% |
| IBTrACS | NOAA | v04r00 | 트랙 포인트 | Public Domain | - |
| ERA5 기준기후 | ECMWF CDS | 2022-2024 | 0.25° | CC BY 4.0 | <5% |
| IPCC AR6 SLR | IPCC | 2021 | 지역별 | CC BY 4.0 | SSP별 범위 제시 |

### Status
- 스크립트: **미구현** (다음 세션에서 `interpret_H_decadal_report.py` 작성 예정)
- 선행 의존: Phase A~G 결과 데이터 (`multisource_risks.csv`, `OCI_AllRisks_SSP_2100_v2.xlsx`)
- 예상 출력: Excel 1파일 × 20+ 시트, PNG 인포그래픽 1장

---

## [2026-04-08] — Phase A~G: 7단계 해석 프레임워크 실행 완료

### Added (interpret_A_consensus.py)
- **소스 합의도 검증**: CMIP6/PhyRisk/CLIMADA 3소스 간 CV(변동계수) 기반 HIGH/MED/LOW 등급
- **동인별 커버리지 매트릭스**: 12개 동인 × 4소스 ✓ 표시 + 합의도 등급
- **출력**: `A_합의도_검증.png`, `A_복합점수_추이.png`, `A_합의도_검증.xlsx`
- **주요 발견**: 아리디티·지진은 단일소스(LOW), TC빈도·하천홍수·산불은 3소스 일치(HIGH)

### Added (interpret_B_rag.py)
- **RAG 등급화**: 12개 동인 × ILO/ISO/IPCC 기준 임계값 → GREEN/AMBER/RED 자동 분류
- **SSP별 RED 개수 비교**: 2100년 기준 SSP1→SSP5 RED 동인 증가 수 (완화 편익 정량화)
- **출력**: `B_RAG_히트맵.png`, `B_RED개수_SSP비교.png`, `B_RAG_등급표.xlsx`
- **주요 발견**: SSP5-8.5 2100년 기준 전 사업장 종합 RED, 광양공장 RED 4개(최다)

### Added (interpret_C_profile.py)
- **레이더 차트**: 12개 동인 정규화(0-1) × 8사업장 × 2×4 배치
- **버블 차트**: composite_score vs eq_mmi, 버블크기=EAL, SSP1/SSP5 비교
- **k-means 클러스터링**: k=3, PCA 2D 시각화 + 클러스터별 특성 프로파일
- **출력**: `C_레이더차트.png`, `C_버블차트.png`, `C_클러스터.png`, `C_프로파일.xlsx`
- **주요 발견**: 클러스터1=열+폭염(산동OCI), 클러스터2=폭염+TC(KOR 6개), 클러스터3=하천홍수+습구온도(마스틸OCI)

### Added (interpret_D_threshold.py)
- **임계연도 타임라인**: 8개 동인 × 8사업장 × SSP5-8.5, AMBER/RED 도달연도 가로 막대
- **시나리오 팬차트**: SSP1~SSP5 복합점수 분기 시각화 (2×4 사업장별)
- **출력**: `D_임계연도_타임라인.png`, `D_시나리오팬차트.png`, `D_임계연도_테이블.xlsx`
- **주요 발견**: 중부공장 극한강수 2030년 즉각 RED, 산동/마스틸 폭염 2050년 단기 RED

### Added (interpret_E_compound.py)
- **복합리스크 4시나리오**: 열-건조, 태풍-홍수, 열-TC, 기온-SLR 복합 점수 계산
- **증폭지수**: 동시 고위험 발생시 ×1.2 증폭 반영, 포트폴리오 최대 132(마스틸OCI)
- **출력**: `E_복합리스크_매트릭스.png`, `E_증폭지수_SSP비교.png`, `E_복합리스크.xlsx`
- **주요 발견**: 마스틸OCI 열-TC 복합 63점, 기온-SLR 94점(전사업장 최고), 증폭 132

### Added (interpret_F_finance.py)
- **5개 재무 KPI**: EAL(CLIMADA직접값) + BID비용(WBGT×일매출×15%) + 에너지(CDD×kWh×전기료) + SLR인프라 + 보험프리미엄
- **완화편익**: SSP5-SSP1 연간 절감 가능액 시각화, 화살표 표시
- **출력**: `F_재무임팩트_스택바.png`, `F_완화편익.png`, `F_재무임팩트.xlsx`
- **주요 발견**: SSP5-8.5 2100년 포트폴리오 총 $168M/yr, SSP1 대비 $53M/yr 절감 가능

### Added (interpret_G_report.py)
- **경영진 인포그래픽**: 5개 패널 (KPI박스/순위막대/재무스택/시계열/행동권고)
- **사업장별 리스크 카드**: 8장 × 6개 동인 RAG + 재무비용 요약
- **TCFD 시나리오 분석**: 7개 위험범주 × SSP1/SSP5 × 2050/2100 비교표
- **CFO 재무 요약**: 우선순위 + 절감가능액 + 포트폴리오 합계
- **출력**: `G_경영진_인포그래픽.png`, `G_사업장_리스크카드.png`, `G_경영진_브리핑.xlsx`

### Key Results (Phase A-G, SSP5-8.5, 2100년)
- **포트폴리오 연간 기후비용**: $168M/yr (총자산 대비 ~3%)
- **완화 편익**: SSP5→SSP1 전환 시 $53M/yr 절감 가능
- **최고위험**: 마스틸OCI(중국) — 복합증폭 132, $134M/yr (자산의 24%)
- **즉각 대응 필요**: 중부공장(극한강수 2030 RED), 산동OCI(열 2050 RED)
- **소스 합의도**: 전 사업장 LOW (CMIP6 60%+PR 25%+CL 15% 가중 → MED 수준 신뢰도)

---

## [2026-04-06] — 멀티소스 통합 리스크 분석 + 소스별 단독 출력 + 위도경도 기반 워크플로 완성

### Added (calc_all_climate_risks.py)
- **12개 기후 리스크 동인 × 4SSP × 9목표연도** 통합 분석 스크립트
  - 동인: 폭염일(heat_days), 기온이상(delta_T), 습구온도(wbgt28), 극한강수(rx1day),
    가뭄(cdd), 산불(fwi), 해수면(slr_total), 아리디티(aridity), 태풍빈도(tc_freq),
    하천홍수(rf_depth), 연안홍수(coastal), 지진(eq_mmi)
  - 목표연도: 2025, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100
  - SMOOTH=5 (±5yr 이동평균) 노이즈 저감
  - 출력: `site_output/OCI_AllRisks_SSP_2100_v2.xlsx` — 12동인시트 + 데이터출처_계수 시트
- **CMIP6 앙상블 사이트명 매핑 수정**: SITE_ENS_MAP 도입
  - SD_OCI → Shandong_OCI, MS_OCI → MaSteel_OCI (앙상블 CSV 이름 불일치 해결)
- **Jungbu_Plant NC 직접추출**: 앙상블 CSV 미포함 사업장 → NC_VARS_FULL 8변수 직접 읽기
- **아리디티 계산 안정화**: evsp_m > 0.01 임계 + min(5.0, pr_m/evsp_m) 캡 (Pohang 503569 오류 수정)
- **데이터출처_계수 시트**: 모든 결과 파일에 계수 출처 추가
  - Fischer & Schär(2010), IPCC AR6 Table 9.9, Emanuel(2020), Knutson et al.(2020) 등

### Added (calc_multisource_risks.py) — 위도경도 기반 멀티소스 워크플로
- **5대 데이터 소스 → 15개 지표 통합** (8사업장 × 4SSP × 3시점 = 96행)
  - CMIP6 앙상블 CSV (Primary, 60%): heat_days/delta_T/wbgt28/rx1day/cdd/fwi/slr/aridity/tc_freq
  - CLIMADA HDF5 (Secondary B, 15%): 지진EAL/산불EAL/TC풍속/하천홍수깊이/연안홍수깊이
  - OS-Climate PhyRisk (Secondary A, 25%): 8위험 × 15지표 선형보간(2030/2050/2090)
  - IBTrACS: TC 이력 보조
- **CLIMADA 메모리 안전장치**: n_ev × n_cen > 1,000,000,000 → 자동 스킵 (flood_CHN 17.6GB 대응)
- **PhyRisk 연도 보간**: np.interp (2030/2050/2090), 2100 외삽 최대 1.5× 캡
- **SSP↔PhyRisk/RCP 매핑**: ssp1_2_6→ssp126/rcp26, ssp2_4_5→ssp245/rcp45, ssp5_8_5→ssp585/rcp85
- **소스 합의도 메트릭**: CV(변동계수) < 0.2 → HIGH, < 0.5 → MED, else → LOW
- **출력 파일 5종**:
  1. `OCI_MultiSource_Risks.xlsx` — 통합 (16시트)
  2. `OCI_CMIP6_Only.xlsx` — CMIP6 단독 (CMIP6종합 + 8사업장별 + 위험순위×3 + 출처)
  3. `OCI_CLIMADA_Only.xlsx` — CLIMADA 단독 (사업장별요약 + TC/하천홍수 시나리오비교 + 출처)
  4. `OCI_PhyRisk_Only.xlsx` — PhyRisk 단독 (원본 + 15지표 피벗 + SSP비교 + 출처)
  5. `OCI_Weighted_Composite.xlsx` — 가중복합 (전체 + 6개 순위시트 + 가중방법론)

### Fixed
- MergedCell write-only 오류: `write_title(nrow=1)` → row 3 머지 후 `write_hdr(row=3)` 충돌
  → `startrow=4` + `write_hdr(row=4)` 로 통일 (§8~§11 출처 시트 4곳)
- 최종 print 문 em-dash(`—`) cp949 인코딩 오류 → `-` 대체

### Workflow (위도경도 → 결과)
```
사업장 좌표 (lat, lon, country) 입력
  → CMIP6 NC nearest-neighbor 추출 (east_asia 0.25° 격자)
  → CLIMADA HDF5 nearest centroid (EAL, RP100yr)
  → PhyRisk CSV 보간 (연도별 선형)
  → 12개 동인 계산 (Fischer/Stull/IPCC 계수 적용)
  → 가중 복합점수 (C6×60% + PR×25% + CL×15%)
  → Excel 5종 자동 출력
```

---

## [2026-03-25] — 5대 데이터 소스 통합 Excel 출력 + 문서화 완료

### Added (데이터 소스 확장)
- **`download_cmip6_v2.py`** — 17-모델 × 4SSP × 7변수 CMIP6 앙상블 구축 (478 NC 파일)
  - 17 models: access_cm2, awi_cm_1_1_mr, bcc_csm2_mr, canesm5, cmcc_esm2, cnrm_cm6_1, fgoals_g3, gfdl_esm4, hadgem3_gc31_ll, inm_cm5_0, ipsl_cm6a_lr, miroc6, mpi_esm1_2_lr, mri_esm2_0, nesm3, noresm2_mm, ukesm1_0_ll
  - east_asia / se_asia 지역 분리 다운로드
- **`download_physrisk.py`** — OS-Climate PhyRisk API (physrisk-lib 1.7.1)
  - physrisk_long.csv: 14사업장 × 11지표 × 3SSP × 3시점 = 1,890행
- **`download_climada_hazards.py`** — CLIMADA HDF5 위험 파일 일괄 다운로드
  - flood/river_flood/tropical_cyclone(61파일)/wildfire/earthquake
- **`download_ibtracs.py`** + **`ibtracs_analysis.py`** — IBTrACS WP 태풍 이력
  - ibtracs_site_stats.csv: 14 사업장 반경별 태풍 빈도/강도 (1980-2023)
- **`download_nexgddp.py`** — NASA NEX-GDDP-CMIP6 (S3 anon, 증분 저장)
  - nexgddp_sites_long.csv: 1,247행 (89 유효 항목 × 14 사업장)
  - nexgddp_log.json으로 중단 재시작 안전

### Added (앙상블 + 통합)
- **`build_ensemble.py`** — 17-모델 앙상블 통계 + 지역별 최신뢰 모델
  - cmip6_ensemble_annual.csv (19,264행)
  - cmip6_ensemble_periods.csv (1,960행)
  - cmip6_model_skill.csv (224행)
  - cmip6_all_models_raw.csv (299,796행)
  - best_model_by_region.csv, site_tasmax_scenario_table.csv
- **`integrate_all_data.py`** — 5대 소스 통합
  - master_risk_table.csv: 14행 × 37컬럼 (NaN 없음)

### Added (Excel 출력)
- **`make_excel_climada_physrisk.py`** → `site_output/OCI_CLIMADA_PhyRisk.xlsx`
  - 9시트: 통합요약/PhyRisk_Long/PhyRisk_Pivot/CLIMADA_Flood/CLIMADA_RiverFlood/CLIMADA_TC/CLIMADA_Wildfire/CLIMADA_Earthquake/IBTrACS
  - CLIMADA HDF5 직접 접근 (h5py + scipy.sparse.csr_matrix, CLIMADA Python 불필요)
  - 대용량 TC HDF5(30M+ centroid) 처리: 규칙 그리드 구조 이용
- **`make_excel_cmip6.py`** → `site_output/OCI_CMIP6_Ensemble.xlsx`
  - CMIP6 17-모델 앙상블 기간별/연간/신뢰도/최적모델 시트

### Added (문서)
- **`README.md`** 전면 개편 — 5대 데이터 소스 체계, 파이프라인, 스크립트 인덱스 포함
- **`CHANGELOG.md`** 이 항목 추가 (Phase 데이터 통합 이력 완성)

### Technical Notes
- CLIMADA Python 패키지 불필요: h5py + scipy.sparse로 HDF5 직접 파싱
- HDF5 intensity 구조: `data/indices/indptr` → `csr_matrix((data, indices, indptr), shape=(n_events, n_cen))`
- HDF5 centroid 키: `'lat'`/`'lon'` (latitude/longitude 아님)
- Windows 백그라운드 실행: batch wrapper + `powercfg /change standby-timeout-ac 0` (절전 방지)
- NEX-GDDP 증분 저장: `mode="a"` CSV append + JSON 로그 → 세션 종료 후 재시작 안전

### 환경
- conda: climada_env (Python 3.12, miniforge3)
- 핵심 패키지: xarray, pandas, numpy, h5py, scipy, s3fs, h5netcdf, physrisk-lib==1.7.1, cdsapi

---

## [2026-03-18] — Phase 18~20: Risk Score v2 + 습구온도 + 에너지비용 + 최종통합

### Added (Phase 18: Risk Score v2 + Wet-bulb)
- **`calc_phase18.py`** — SSP1/3 복합극한 버그 수정 + 습구온도 분석
  - ph8_risk_score_v2.csv — 4-SSP compound events 정확히 반영한 리스크 스코어 (416×14)
  - ph12_eal_v2.csv — v2 리스크 기반 EAL 재계산
  - ph18_wetbulb.csv — 습구온도 Tw (Stull 2011) 분석 (52×43)
    - Tw_mean, Tw_JJA, Tw>26/28/32C 일수/yr × 8기간
  - ph18_risk_v2_wetbulb.png — 리스크 v2 + 습구온도 통합 시각화
  - 핵심: Philko Makati Tw>28C 185.5일/yr (SSP5-8.5 2090s), 작업안전 한계 초과

### Added (Phase 19: 에너지 비용 + 수자원 스트레스 + 포트폴리오 대시보드)
- **`calc_phase19.py`** — 에너지 수요 비용 모델 + 수자원 스트레스 + 복합 히트맵
  - ph19_energy_cost.csv — CDD/HDD 기반 에너지 비용 증가 추정 (416×10)
    - 냉방: 0.5kWh/m2/CDD, 난방: 0.3kWh/m2/HDD, 국가별 전기료 적용
    - SSP5-8.5 2090s 포트폴리오 추가 에너지비용: USD 198M/yr
  - ph19_water_stress.csv — SPI3+지표유출+토양수분 복합 수자원 스트레스 (52×35)
  - ph19_compound_heatmap.png — 13사업장 × 8위험차원 히트맵 (SSP2/5 비교)
  - ph19_portfolio_dashboard.png — EAL/에너지/수자원/습구온도 4종 통합 대시보드

### Added (Phase 20: 최종통합 + 경영진 인포그래픽)
- **`calc_phase20.py`** — 연도별 스냅샷 + 최종 마스터 CSV + 경영진 인포그래픽
  - ph20_decadal_snapshots.csv — 13사업장 × 4SSP × 8기간 핵심 KPI 스냅샷 (416×13)
  - **`OCI_MASTER_FINAL.csv`**: 416행 × 123열 (최종 완성 마스터)
    - v2 대비 44개 컬럼 추가 (습구온도, 에너지비용, 수자원스트레스, 리스크v2)
  - ph20_executive_infographic.png — 7패널 경영진 인포그래픽 (리스크랭킹/EAL팬/에너지비용/Tw28히트맵)
  - ph20_scenario_comparison.csv — 4-SSP 시나리오 비교표 (208×9)
  - ph20_scenario_table.png — 13사업장 × 4SSP 리스크/EAL/BID 비교 테이블

### Key Results (Phase 18~20)
- **포트폴리오 총 기후비용 (SSP5-8.5, 2090s)**:
  - EAL: USD 22.3M/yr
  - 추가 에너지비용: USD 198M/yr
  - **합계: USD ~220M/yr** (총자산 10,750M의 2.0%)
- **Philko Makati 최고위험**: RiskScore 74.8 (HIGH tier), BID 67일/yr, Tw>28C 185.5일/yr
- **한국 포트폴리오**: EAL USD 16.3M/yr, 광양공장 가장 높은 리스크 증가폭
- **최종 마스터**: OCI_MASTER_FINAL.csv — 416×123 (80+ 기후지표 완전통합)

---

## [2026-03-18] — Phase 15~17: 마스터 v2 + 시나리오 분기 + 풍속/적설 + 국가별 집계

### Added (Phase 15: OCI_MASTER_ALL_v2)
- **`calc_phase15.py`** — Ph11~14 통합 + SSP1/3 갭 채우기
  - SPI-3 4-SSP 전체 재계산 (ph15_spi3_4ssp.csv)
  - 복합극한 이벤트 4-SSP 재계산 (ph15_compound_4ssp.csv)
  - **`OCI_MASTER_ALL_v2.csv`**: 416행 × 79열 (v1 대비 20개 컬럼 추가)
  - 필리핀 복합극한(far): SSP1=11.6% → SSP5=31.7% (3배 차이)

### Added (Phase 16: 시나리오 분기 + 풍속/적설)
- **`calc_phase16.py`** — SSP 시나리오 분기점 + 풍속/적설 위험
  - ph16_divergence.csv — SSP5-SSP1 리스크 격차 분석
  - ph16_wind_risk.csv — 월별 최대풍속, JJA 풍속, 게일일수 (52×38)
  - ph16_snow_risk.csv — 연간 적설, DJF 적설, 동결월수 감소 추이 (52×27)
  - ph16_divergence_plot.png / ph16_wind_snow_plot.png
  - 핵심: 광양공장 최대풍속 9.3m/s (한국 최고)

### Added (Phase 17: 국가별 집계 + 사업장 카드)
- **`calc_phase17.py`** — 국가별 자산가중 리스크 + 사업장별 요약카드
  - ph17_country_aggregate.csv — 128행 (4국 × 4SSP × 8기간)
  - ph17_country_comparison.png — 국가별 리스크 궤적/EAL/레이더/BID 4패널
  - ph17_site_cards.png — 13사업장 티어별 색상 요약카드
  - SSP5 2090s: 필리핀 리스크 68.3/EAL 1.1M, 한국 EAL 총 16.3M/yr

### Key Results (Phase 15~17)
- **국가별 EAL (SSP5-8.5, 2090s)**: 한국 USD 16.3M/yr, 중국 USD 4.7M/yr, 필리핀 USD 1.1M/yr
- **중국 BID 37.3일/yr** — 한국(25.1) 대비 +50% 업무중단 위험 (열스트레스)
- **복합극한 필리핀**: SSP5 2060-2099 31.7% (연중 1/3이 폭염+건조 동시 발생)
- **마스터 데이터셋**: OCI_MASTER_ALL_v2.csv — 416×79 (55+ 기후지표 완전통합)

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

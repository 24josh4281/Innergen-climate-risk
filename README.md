# OCI Climate Physical Risk Analysis

CMIP6 기반 OCI 전 사업장(13개) 기후 물리적 리스크 정량 분석 시스템.
4개 SSP 시나리오(SSP1-2.6 / SSP2-4.5 / SSP3-7.0 / SSP5-8.5) × 2015~2100 앙상블 분석.

---

## 분석 대상 사업장 (13개)

| # | 국가 | 사업장 | 위도 | 경도 | 데이터 지역 |
|---|------|--------|------|------|------------|
| 1 | Korea | HQ Seoul | 37.5649 | 126.9793 | korea_china |
| 2 | Korea | R&D Seongnam | 37.4018 | 127.1615 | korea_china |
| 3 | Korea | Pohang Plant | 35.9953 | 129.3744 | korea_china |
| 4 | Korea | Gunsan Plant | 35.9676 | 126.7127 | korea_china |
| 5 | Korea | Iksan Plant | 35.9490 | 126.9657 | korea_china |
| 6 | Korea | Gwangyang Plant | 34.9155 | 127.6936 | korea_china |
| 7 | Korea | Saehan Jeongeup | 35.6183 | 126.8638 | korea_china |
| 8 | China | OCI Shanghai | 31.2305 | 121.4495 | korea_china |
| 9 | China | Shandong OCI (ZZ) | 34.7979 | 117.2571 | korea_china |
| 10 | China | MaSteel OCI (MAS) | 31.7097 | 118.5023 | korea_china |
| 11 | China | Jianyang Carbon (ZZ) | 34.8604 | 117.3123 | korea_china |
| 12 | Japan | OCI Japan Tokyo | 35.6458 | 139.7386 | japan |
| 13 | Philippines | Philko Makati | 14.5547 | 121.0244 | philippines |

---

## 시나리오 및 데이터 사양

| 항목 | 사양 |
|------|------|
| 시나리오 | SSP1-2.6 / SSP2-4.5 / SSP3-7.0 / SSP5-8.5 (CMIP6) |
| 기간 | 2015 ~ 2100 (월별), 2015 ~ 2100 (일별 일부) |
| 모델 | 7개 앙상블: ACCESS-CM2, MIROC6, MIROC-ES2L, FGOALS-F3-L, FGOALS-G3, KIOST-ESM, BCC-CSM2-MR |
| 월별 변수 | 12개 (tas, tasmax, tasmin, pr, evspsbl, prsn, sfcWind, zos, mrro, mrsos, huss, rsds) |
| 일별 변수 | 3개 (tasmax, tasmin, pr) — SSP2-4.5 / SSP5-8.5 전용 |
| 공간 영역 | 한국+중국(30-42N, 110-132E) / 일본(30-42N, 132-146E) / 필리핀(10-22N, 118-128E) |
| 데이터 소스 | Copernicus CDS (projections-cmip6) |

---

## 분석 산출물 (output/)

| 파일 | 내용 | 형태 |
|------|------|------|
| `OCI_FINAL_4SSP_Decadal.csv` | 12동인 × 4SSP × 8기간(2020s~2090s) × 13사업장 | 156행 × 37열 |
| `OCI_FINAL_SpecificYears.csv` | 7변수 × 4SSP × 4연도(2030/35/40/45) × 13사업장 | 364행 × 7열 |
| `OCI_FINAL_ETCCDI.csv` | ETCCDI 13지수 × 2SSP × 8기간 × 13사업장 | 208행 × 17열 |
| `OCI_FINAL_Indices.csv` | Heat Index + 온난화속도 + SPEI × 2SSP × 13사업장 | 26행 × 23열 |

### ETCCDI 지수 정의

| 지수 | 단위 | 정의 |
|------|------|------|
| TXx | °C | 일 최고기온의 연 최댓값 |
| TNn | °C | 일 최저기온의 연 최솟값 |
| SU | days/yr | 일 최고기온 > 25°C 일수 |
| TR | days/yr | 일 최저기온 > 20°C 일수 (열대야) |
| FD | days/yr | 일 최저기온 < 0°C 일수 (결빙일) |
| WSDI | days/yr | 최고기온 > 90th percentile 연속 6일+ |
| Rx1day | mm | 일 최대강수량 (연 최댓값) |
| Rx5day | mm | 연속 5일 최대강수량 |
| SDII | mm/wetday | 강수 강도 (강수일 평균) |
| R95p | mm/yr | 95th percentile 초과 강수 연합계 |
| CDD | days | 연속 건조일수 (일강수 < 1mm) |
| CWD | days | 연속 습윤일수 (일강수 ≥ 1mm) |
| WBGT | °C | 습구흑구온도 (열스트레스 지표) |

### 보조 지수 정의

| 지수 | 방법 | 기준 |
|------|------|------|
| Heat Index (HI) | NOAA Rothfusz 1990 | Caution≥27°C / Extreme Caution≥32°C / Danger≥40°C / Extreme Danger≥54°C |
| SPEI 근사 | P-ET 표준화 | < -1.0 = 가뭄 위험 |
| 온난화 속도 | 선형 회귀 | °C/decade (2020-2050 / 2050-2100 구간별) |

---

## 주요 결과 요약 (SSP5-8.5, 2090s)

| 위험 순위 | 사업장 | 핵심 지표 |
|-----------|--------|-----------|
| 🔴 최고 | Philko Makati | WBGT 30.7°C, TR 365일, HI 41.8°C (NOAA Danger), R95p 1,137mm |
| 🟠 높음 | Gwangyang Plant | Rx1day 74.8mm, R95p 845mm, WSDI 131일 |
| 🟠 높음 | Pohang Plant | Rx1day 62.1mm, R95p 833mm, WSDI 114일 |
| 🟡 중간 | OCI Shanghai | TXx 29.2°C, TR 176일, R95p 840mm |
| 🟡 중간 | Shandong/Jianyang | TXx 33.1°C, SU 191일, CDD 36일 |
| 🟡 중간 | OCI Japan Tokyo | Rx1day 56mm, R95p 817mm, TR 132일 |
| 🟢 낮음 | 한국 나머지 6개 | NOAA Safe, SPEI > -1.0, dT < +5.6°C |

### 온난화 폭 (2020→2090s 기온 상승, Tmean)

| 시나리오 | 한국 사업장 | 중국 사업장 | 일본 | 필리핀 |
|----------|------------|------------|------|--------|
| SSP1-2.6 | +1.4~1.7°C | +1.3~1.6°C | +0.8°C | +0.6°C |
| SSP2-4.5 | +2.2~2.7°C | +2.1~2.4°C | +1.3°C | +1.0°C |
| SSP3-7.0 | +3.2~3.8°C | +2.9~3.4°C | +2.5°C | +1.8°C |
| SSP5-8.5 | +4.9~5.6°C | +4.8~5.1°C | +5.2°C | +3.9°C |

---

## 디렉토리 구조

```
CLIMADA/  (코드, GitHub 관리)
├── README.md
├── CHANGELOG.md
├── CLAUDE.md                        # AI 세션 컨텍스트
├── .gitignore                       # *.nc, *.zip 제외
│
├── download_scenarios_v2.py         # STEP 0: 월별 CMIP6 다운로드 (12var × 4SSP × 3지역)
├── download_daily_cmip6.py          # STEP 0b: 일별 CMIP6 다운로드 (3var × 2SSP × 3지역)
├── calc_indices_step1.py            # STEP 1: Heat Index / SPEI / 온난화속도
├── calc_etccdi.py                   # STEP 2: ETCCDI 13지수 (일별 데이터 기반)
├── scenario_analysis.py             # STEP 3: 시계열 분석 + 시각화 (단일 사업장)
│
├── download_climada_data.py         # CLIMADA API 위험 데이터
├── download_era5.py                 # ERA5 과거 데이터 (보류)
├── download_slr.py                  # 해수면 상승
├── risk_analysis_final.py           # CLIMADA 위험 수치 추출
├── ibtracs_analysis.py              # IBTrACS 태풍 분석
└── extract_risk_values.py           # 좌표별 위험값 추출

c:/Users/24jos/climada/data/  (데이터, .gitignore 제외)
├── scenarios_v2/
│   ├── ssp1_2_6/                    # 월별 12var × 7models
│   ├── ssp2_4_5/
│   ├── ssp3_7_0/
│   ├── ssp5_8_5/
│   ├── japan/ssp{1,2,3,5}*/
│   ├── philippines/ssp{1,2,3,5}*/
│   ├── daily/ssp{2,5}_*/           # 일별 3var × 3models
│   └── output/                      # ← 최종 산출물 (GitHub 포함)
│       ├── OCI_FINAL_4SSP_Decadal.csv
│       ├── OCI_FINAL_SpecificYears.csv
│       ├── OCI_FINAL_ETCCDI.csv
│       ├── OCI_FINAL_Indices.csv
│       └── scenario_risk_*.png
├── hazard/                          # CLIMADA 위험 (~25 GB)
└── exposures/litpop/
```

---

## 실행 순서

### STEP 0: 데이터 다운로드 (최초 1회)
```bash
# 월별 CMIP6 (12변수 × 4SSP × 3지역 = 144파일)
python download_scenarios_v2.py

# 일별 CMIP6 (3변수 × 2SSP × 3지역 = 18파일)
python download_daily_cmip6.py
```

### STEP 1: 기후 지수 계산
```bash
# Heat Index / SPEI / 온난화속도
python calc_indices_step1.py

# ETCCDI 13개 극값 지수
python calc_etccdi.py
```

### STEP 2: 시나리오 분석 (단일 사업장)
```bash
# 기본 (Zaozhuang)
python scenario_analysis.py

# 사업장 지정
python scenario_analysis.py --lat 37.5649 --lon 126.9793 --name hq_seoul --region korea_china
```

### STEP 3: 결과 확인
```
output/OCI_FINAL_4SSP_Decadal.csv   — 10년 평균 주요 지표
output/OCI_FINAL_SpecificYears.csv  — 2030/2035/2040/2045 연도별
output/OCI_FINAL_ETCCDI.csv         — ETCCDI 극값 지수
output/OCI_FINAL_Indices.csv        — Heat Index + SPEI + 온난화속도
```

---

## 환경 설정

```bash
# conda 환경 활성화
conda activate climada_env  # Python 3.12, miniforge3

# 또는 직접 실행
C:/Users/24jos/miniforge3/envs/climada_env/python.exe script.py
```

### CDS API 설정
`C:/Users/24jos/.cdsapirc` 파일에 API 키 설정 필요.
최초 사용 전 아래 데이터셋 약관 동의 필수:
- CMIP6: https://cds.climate.copernicus.eu/datasets/projections-cmip6
- ERA5 Daily: https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics

### 주요 패키지
```
xarray, pandas, numpy, matplotlib
cdsapi, zipfile, scipy
```

---

## 데이터 출처

| 소스 | 용도 | URL |
|------|------|-----|
| Copernicus CDS | CMIP6 SSP 시나리오 | https://cds.climate.copernicus.eu |
| WCRP CMIP6 | 기후 모델 앙상블 | https://www.wcrp-climate.org/wgcm-cmip6 |
| CLIMADA (ETH Zurich) | 물리적 위험 데이터 | https://climada.ethz.ch |
| IBTrACS (NOAA) | 태풍 경로 | https://www.ncdc.noaa.gov/ibtracs |
| LitPop (ETH Zurich) | 자산·인구 노출 | https://climada-python.readthedocs.io |
| NOAA NWS | Heat Index 공식 | https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml |
| WMO/ETCCDI | 기후 극값 지수 | https://etccdi.pacificclimate.org |

---

## 개선 로드맵

| 우선순위 | 항목 | 상태 |
|----------|------|------|
| 높음 | ERA5 과거 데이터 완성 → baseline 설정 | 보류 |
| 높음 | 사업장별 PDF 리포트 자동화 | 미착수 |
| 중간 | SSP1-2.6 / SSP3-7.0 일별 CMIP6 추가 | 미착수 |
| 중간 | LitPop × 피해함수 → 예상손실(EAL) 산출 | 미착수 |
| 낮음 | ERA5 CAPE 기반 우박 프록시 | 미착수 |
| 낮음 | GRACE 지하수 → 지반침하 정밀화 | 미착수 |

---

*Last updated: 2026-03-17*

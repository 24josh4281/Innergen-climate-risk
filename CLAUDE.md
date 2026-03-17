# CLIMADA 프로젝트 컨텍스트

## 분석 대상
- **위치**: Zaozhuang, Shandong, China
- **좌표**: 34.7979°N, 117.2571°E
- **목적**: 8개 기후 위험 시나리오 물리적 리스크 분석

## 8개 시나리오 및 데이터 소스

| # | 위험 | 데이터 | 파일 |
|---|---|---|---|
| 1 | 폭염 | ERA5 Tmax | era5_tmax_zaozhuang_1950_2023.nc |
| 2 | 집중호우 | ERA5 Precip | era5_precip_zaozhuang_1950_2023.nc |
| 3 | 한파 | ERA5 Tmin | era5_tmin_zaozhuang_1950_2023.nc |
| 4 | 가뭄 | ERA5 PET (SPEI 계산용) | era5_pet_zaozhuang_1950_2023.nc |
| 5 | 폭설 | ERA5 Snowfall | era5_snowfall_zaozhuang_1950_2023.nc |
| 6 | 강풍 | ERA5 U10+V10 | era5_u10/v10_zaozhuang_1950_2023.nc |
| 7 | 평균온도 | ERA5 Tmean | era5_tmean_zaozhuang_1950_2023.nc |
| 8 | 해수면 상승 | Copernicus SSH + CMIP6 | download_slr.py |

## 환경
- conda env: `climada_env` (Python 3.12, miniforge3)
- activate: `C:/Users/24jos/miniforge3/Scripts/activate climada_env`
- CDS API: `C:/Users/24jos/.cdsapirc` 설정 완료

## 데이터 저장 경로
- ERA5: `c:/Users/24jos/climada/data/era5/`
  - 연도별 임시파일: `era5/tmp/<tag>/<tag>_YYYY.nc`
  - 병합 최종파일: `era5/<tag명>.nc`
- CLIMADA hazard/exposure: `c:/Users/24jos/climada/data/`
  - 하천홍수, 태풍, 산불, 지진, LitPop 다운로드 완료

## 주요 스크립트
- `download_era5.py` — ERA5 8개 변수 연도별 다운로드+병합
- `download_slr.py` — 해수면 상승 (위성+CMIP6)
- `download_climada_data.py` — CLIMADA API 데이터 다운로드
- `risk_analysis_final.py` — 좌표 기준 위험 강도 수치 추출

## 진행 상황 (2026-03-16 기준)
- [x] CLIMADA 환경 설치 완료
- [x] CLIMADA API 데이터 다운로드 완료 (하천홍수, 태풍, 산불, 지진, LitPop)
- [x] risk_analysis_final.py 작성 완료
- [x] **시나리오 데이터 다운로드 완료** (download_scenarios.py)
  - CMIP6 SSP2-4.5, SSP5-8.5: 8변수 × 2시나리오 = 16파일
  - CMIP5 RCP4.5, RCP8.5: 3변수 × 2시나리오 = 6파일
  - 저장: c:/Users/24jos/climada/data/scenarios/
- [x] **시나리오 분석 완료** (scenario_analysis.py)
  - 결과 CSV/PNG: c:/Users/24jos/climada/data/scenarios/output/
- [ ] ERA5 과거 데이터 미완 (보류 — 미래 시나리오 우선)
- [ ] 해수면 상승: 조장시 내륙 위치로 직접 영향 없음 (공급망 리스크로 대체 검토 필요)
- [ ] 다음: 위험별 임계값 기반 이벤트 빈도 분석 (폭염일수, 호우일수 등)

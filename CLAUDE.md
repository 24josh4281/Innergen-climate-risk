# CLIMADA 프로젝트 컨텍스트 (AI 세션용)

## 프로젝트 개요
- **목적**: 한국 기업 글로벌 사업장 기후 물리적 리스크 정량 분석 (임의 lat/lon 지원)
- **레퍼런스 사업장**: OCI 14개 (KOR 8개, CHN 4개, JPN 1개, PHL 1개)
- **신규 사업장 명명 규칙**: `회사명_지역` (예: `POSCO_포항`, `LOTTE_하노이`)
- **분석 완료**: Phase 1~20 + 7대 데이터 소스 통합 + Excel 출력

## 환경
- conda env: `climada_env` (Python 3.12, miniforge3)
- activate: `C:/Users/24jos/miniforge3/Scripts/activate climada_env`
- 직접 실행: `C:/Users/24jos/miniforge3/envs/climada_env/python.exe <script.py>`
- CDS API: `C:/Users/24jos/.cdsapirc` 설정 완료

## 7대 데이터 소스

| # | 소스 | 경로 | 커버리지 | 해상도 |
|---|------|------|----------|--------|
| 1 | CLIMADA Hazard HDF5 | `B:/climada/data/hazard/` | 전세계 | 격자 |
| 2 | OS-Climate PhyRisk | `B:/climada/data/physrisk/physrisk_long.csv` | 전세계 | 격자 |
| 3 | CMIP6 17모델 앙상블 | `B:/climada/data/scenarios/cmip6_v2/` | 전세계 | 1°~2° |
| 4 | IBTrACS 태풍 | `B:/climada/data/ibtracs/ibtracs_site_stats.csv` | 전세계 | 격자 |
| 5 | NASA NEX-GDDP | `B:/climada/data/nexgddp/nexgddp_sites_long.csv` | 전세계 | 0.25° |
| 6 | CORDEX 전역 RCM | `B:/climada/data/kma_cordex/processed/cordex_global.csv` | 6개 도메인 | 11~44km |
| 7 | KMA 기상청 시나리오 | `B:/climada/data/kma/processed/kma_periods.csv` | 한반도 | 행정구역(167개) |

## 데이터 레이어 구조 (tier_resolver.py 주입 순서)
```
① CMIP6 + PhyRisk + Static   → drivers 기반 생성 (_build_drivers_from_cmip6)
② CLIMADA HDF5               → TC/홍수/산불/지진 EAL 삽입 (_inject_climada)
③ CCKP                       → 추가 기후변수 보완 (_inject_cckp)
④ KMA_RDA   [한반도 전용]    → kma_* 키로 행정구역 고해상도 추가 (_inject_kma)
⑤ CORDEX    [전역]           → cordex_* 키로 RCM 격자값 추가 (_inject_cordex)
```

**레이어별 커버 변수**:
| 레이어 | 키 접두사 | 주요 변수 | 커버리지 |
|--------|-----------|-----------|----------|
| CMIP6 | (없음) | tasmax, tas, pr, etccdi_* | 전세계 1°~2° |
| PhyRisk | (없음) | heat_stress, flood_risk, drought_risk 등 | 전세계 |
| Static | aq_, tc_, psha_ | 수자원, 태풍통계, 지진위험 | 전세계 |
| CLIMADA | (없음) | TC_EAL, Flood_EAL, Wildfire_EAL, EQ_EAL | 전세계 |
| CCKP | (없음) | 추가 기후변수 | 전세계 0.25° |
| KMA_RDA | kma_ | kma_tasmax, kma_pr 등 6변수 | 한반도 167개 시군구 |
| CORDEX | cordex_ | cordex_tas, cordex_tasmax 등 7변수 | 전세계 6개 도메인 |

※ KMA/CORDEX는 기존 키를 덮어쓰지 않고 `kma_*` / `cordex_*` 별도 키로 추가됨

## 데이터 루트
- 코드: `c:/Users/24jos/OneDrive/문서/바탕 화면/VSCODE/CLIMADA/`
- 데이터: `B:/climada/data/`
- 출력: `site_output/` (코드 디렉토리 내)

## CLIMADA HDF5 읽기 (중요)
```python
import h5py, scipy.sparse as sp
with h5py.File(fpath, 'r') as f:
    lats = f['centroids']['lat'][:]   # 'lat' (latitude 아님)
    lons = f['centroids']['lon'][:]   # 'lon' (longitude 아님)
    data    = f['intensity']['data'][:]
    indices = f['intensity']['indices'][:]
    indptr  = f['intensity']['indptr'][:]
    freq    = f['frequency'][:]
    n_events, n_cen = len(freq), len(lats)
    mat = sp.csr_matrix((data, indices, indptr), shape=(n_events, n_cen))
```
- CLIMADA Python 패키지 없이 h5py 직접 사용
- 대용량 TC HDF5 (30M+ centroid): `make_excel_climada_physrisk.py`의 `find_nearest_centroid()` 참조

## CMIP6 앙상블 현황
- 17 models × 4 SSPs × 7 variables × east_asia+se_asia
- 앙상블 결과: `B:/climada/data/ensemble/`
  - `cmip6_ensemble_periods.csv` (1,960행) — 주 분석 데이터
  - `cmip6_ensemble_annual.csv` (19,264행)
  - `cmip6_model_skill.csv`, `best_model_by_region.csv`

## CORDEX 전역 RCM 현황
- 6개 도메인: EAS-22, SEA-22, NAM-22, EUR-11, SAM-44, AFR-44
- 7개 변수: tas, tasmax, tasmin, pr, sfcWind, hurs, rsds
- 4 SSPs × 5 기간 (baseline/near/mid/far/end)
- `cordex_global.csv` — 742MB, 1,630만 행, 약 50만 격자점
- API: `api/kma_cordex_client.py` — 임의 lat/lon nearest-point 쿼리

## Phase 분석 현황 (OCI 레퍼런스 사업장 기준, 모두 완료)
- Phase 1~5: 기본 기후지수, ETCCDI, GEV, 4-SSP
- Phase 6~10: 계절분석, 임계값도달연도, 리스크스코어, 마스터
- Phase 11~14: 일별정밀ETCCDI, 재무정량화, 시급성매트릭스, 경영진요약
- Phase 15~17: 마스터v2, 시나리오분기, 풍속/적설, 국가집계
- Phase 18~20: 리스크v2, 습구온도, 에너지비용, 최종통합
- 최종 마스터: `OCI_MASTER_FINAL.csv` — 416행 × 123열

## OCI 레퍼런스 사업장 좌표 (14개)
```python
SITES = {
    "OCI_HQ_Seoul":     (37.5649, 126.9793, "KOR"),
    "OCI_Dream_Seoul":  (37.5172, 126.9000, "KOR"),
    "OCI_RnD_Seongnam": (37.3219, 127.1190, "KOR"),
    "Pohang_Plant":     (36.0095, 129.3435, "KOR"),
    "Gwangyang_Plant":  (34.9393, 127.6961, "KOR"),
    "Gunsan_Plant":     (35.9700, 126.7114, "KOR"),
    "Iksan_Plant":      (35.9600, 126.9880, "KOR"),
    "Saehan_Recycle":   (35.6051, 126.8861, "KOR"),
    "OCI_Shanghai":     (31.2304, 121.4737, "CHN"),
    "MaSteel_OCI":      (31.6839, 118.5127, "CHN"),
    "Shandong_OCI":     (34.7979, 117.2571, "CHN"),
    "Jianyang_Carbon":  (26.7587, 104.4734, "CHN"),
    "OCI_Japan_Tokyo":  (35.6762, 139.6503, "JPN"),
    "Philko_Makati":    (14.5995, 120.9842, "PHL"),
}
```

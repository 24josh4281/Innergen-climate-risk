/**
 * constants.js — 공통 상수 (모든 커스텀 스크립트보다 먼저 로드)
 * heatmap.js / chart_render.js / excel_export.js 에서 재선언 금지
 */

// ── SSP ───────────────────────────────────────────────────────────────────────
const SSP_ORDER = ["ssp126", "ssp245", "ssp370", "ssp585"];

const SSP_LABELS = {
  ssp126: "SSP1-2.6",
  ssp245: "SSP2-4.5",
  ssp370: "SSP3-7.0",
  ssp585: "SSP5-8.5",
};

const SSP_COLORS = {
  ssp126: { border: "#00C896", bg: "rgba(0,200,150,0.12)" },
  ssp245: { border: "#00B4D8", bg: "rgba(0,180,216,0.12)" },
  ssp370: { border: "#F59E0B", bg: "rgba(245,158,11,0.12)" },
  ssp585: { border: "#FF4D6D", bg: "rgba(255,77,109,0.12)" },
};

// ── Period ────────────────────────────────────────────────────────────────────
const PERIOD_KEYS = ["baseline", "near", "mid", "far", "end"];

const PERIOD_LABELS = {
  baseline: "현재",
  near:     "2025-34",
  mid:      "2045-54",
  far:      "2075-84",
  end:      "2090-99",
};

/** 엑셀 출력용 (더 상세한 기간 표기) */
const PERIOD_LABEL_MAP = {
  baseline: "현재(2015-24)",
  near:     "단기(2025-34)",
  mid:      "중기(2045-54)",
  far:      "장기(2075-84)",
  end:      "장기+(2090-99)",
};

/** Chart.js X축 중간값 레이블 */
const PERIOD_MIDPOINTS = ["2020", "2030", "2050", "2080", "2095"];

// ── 변수 분류 ─────────────────────────────────────────────────────────────────
const CMIP6_KEYS = ["tasmax", "tasmin", "tas", "pr", "prsn", "sfcWind", "evspsbl"];

const PHYSRISK_KEYS = [
  // 열 위험 그룹
  "heat_stress", "extreme_heat_35c", "work_loss_high", "work_loss_medium", "heat_degree_days",
  // 수자원 그룹
  "water_stress", "water_depletion", "drought_risk",
  // 홍수/태풍 그룹
  "flood_risk", "river_flood", "coastal_flood", "pluvial_flood",
  "cyclone_risk", "storm_surge", "sea_level_rise",
  // 기타 물리 위험
  "wildfire_risk", "earthquake_risk", "landslide_risk",
];

const CLIMADA_KEYS = ["TC_EAL", "Flood_EAL", "EQ_EAL", "Wildfire_EAL"];

const ETCCDI_KEYS = [
  // 열 극값
  "etccdi_txx", "etccdi_tnn", "etccdi_su", "etccdi_tr", "etccdi_fd",
  "etccdi_wsdi", "etccdi_wbgt",
  // 강수 극값
  "etccdi_cdd", "etccdi_cwd", "etccdi_rx1day", "etccdi_rx5day",
  "etccdi_r95p", "etccdi_sdii",
];

const AQUEDUCT_KEYS = [
  "aq_water_stress", "aq_river_flood", "aq_coastal_flood",
  "aq_drought", "aq_interann_var", "aq_water_stress_2050",
];

const IBTRACS_KEYS = ["tc_annual_freq", "tc_max_wind_kt", "tc_cat3_count"];

const PSHA_KEYS = ["psha_pga_475", "psha_pga_2475"];

const CCKP_KEYS = ["cckp_hi35", "cckp_hd40", "cckp_tr26", "cckp_cdd65", "cckp_hdd65",
                   "cckp_csdi", "cckp_wsdi", "cckp_cdd_consec",
                   "cckp_spei12", "cckp_gsl", "cckp_hurs", "cckp_id", "cckp_rxmonth"];

// ── 동인 메타 (heatmap RAG 포함) ─────────────────────────────────────────────
const DRIVER_META = {
  // ── CMIP6 기온/강수 (7) ──────────────────────────────────────────────────
  tasmax:   { label: "최고기온",       unit: "°C",      rag: (v) => v > 38 ? "red" : v > 33 ? "amber" : "green" },
  tasmin:   { label: "최저기온",       unit: "°C",      rag: (v) => v < -15 ? "red" : v < -5 ? "amber" : "green" },
  tas:      { label: "평균기온",       unit: "°C",      rag: (v) => v > 30 ? "red" : v > 25 ? "amber" : "green" },
  pr:       { label: "강수량",         unit: "mm/day",  rag: (v) => v > 10 ? "red" : v > 6 ? "amber" : "green" },
  prsn:     { label: "강설량",         unit: "mm/day",  rag: (v) => v > 5 ? "red" : v > 2 ? "amber" : "green" },
  sfcWind:  { label: "지표풍속",       unit: "m/s",     rag: (v) => v > 10 ? "red" : v > 7 ? "amber" : "green" },
  evspsbl:  { label: "증발산",         unit: "mm/day",  rag: (v) => v > 5 ? "red" : v > 3 ? "amber" : "green" },
  // ── PhyRisk 열 위험 그룹 (5) ─────────────────────────────────────────────
  heat_stress:     { label: "열 스트레스",       unit: "score", rag: (v) => v > 65 ? "red" : v > 40 ? "amber" : "green" },
  extreme_heat_35c:{ label: "35°C 초과일수",     unit: "score", rag: (v) => v > 60 ? "red" : v > 30 ? "amber" : "green" },
  work_loss_high:  { label: "고강도 노동손실",   unit: "score", rag: (v) => v > 50 ? "red" : v > 25 ? "amber" : "green" },
  work_loss_medium:{ label: "중강도 노동손실",   unit: "score", rag: (v) => v > 40 ? "red" : v > 20 ? "amber" : "green" },
  heat_degree_days:{ label: "열 도일 (CDD)",     unit: "score", rag: (v) => v > 60 ? "red" : v > 30 ? "amber" : "green" },
  // ── PhyRisk 수자원 그룹 (3) ──────────────────────────────────────────────
  water_stress:    { label: "수자원 스트레스",   unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  water_depletion: { label: "물 고갈 지수",      unit: "score", rag: (v) => v > 40 ? "red" : v > 20 ? "amber" : "green" },
  drought_risk:    { label: "가뭄 위험",         unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  // ── PhyRisk 홍수/태풍 그룹 (6) ───────────────────────────────────────────
  flood_risk:      { label: "홍수 위험",         unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  river_flood:     { label: "하천 홍수",         unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  coastal_flood:   { label: "해안 침수",         unit: "score", rag: (v) => v > 50 ? "red" : v > 30 ? "amber" : "green" },
  pluvial_flood:   { label: "도시 홍수",         unit: "score", rag: (v) => v > 55 ? "red" : v > 30 ? "amber" : "green" },
  cyclone_risk:    { label: "사이클론 위험",     unit: "score", rag: (v) => v > 55 ? "red" : v > 30 ? "amber" : "green" },
  storm_surge:     { label: "폭풍 해일",         unit: "score", rag: (v) => v > 50 ? "red" : v > 30 ? "amber" : "green" },
  sea_level_rise:  { label: "해수면 상승",       unit: "score", rag: (v) => v > 55 ? "red" : v > 30 ? "amber" : "green" },
  // ── PhyRisk 기타 물리 위험 (3) ───────────────────────────────────────────
  wildfire_risk:   { label: "산불 위험",         unit: "score",      rag: (v) => v > 50 ? "red" : v > 30 ? "amber" : "green" },
  earthquake_risk: { label: "지진 위험",         unit: "score",      rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  landslide_risk:  { label: "산사태 위험",       unit: "score",      rag: (v) => v > 45 ? "red" : v > 25 ? "amber" : "green" },
  // ── ETCCDI 극값 지수 — 열 (7) ────────────────────────────────────────────
  etccdi_txx:    { label: "최고기온 극값(TXx)",  unit: "°C",        rag: (v) => v > 38 ? "red" : v > 33 ? "amber" : "green" },
  etccdi_tnn:    { label: "최저기온 극값(TNn)",   unit: "°C",        rag: (v) => v < -20 ? "red" : v < -10 ? "amber" : "green" },
  etccdi_su:     { label: "서머데이(SU>25°C)",    unit: "days/yr",   rag: (v) => v > 150 ? "red" : v > 80 ? "amber" : "green" },
  etccdi_tr:     { label: "열대야(TR>20°C)",      unit: "days/yr",   rag: (v) => v > 100 ? "red" : v > 50 ? "amber" : "green" },
  etccdi_fd:     { label: "서리일수(FD<0°C)",     unit: "days/yr",   rag: (v) => v > 100 ? "red" : v > 50 ? "amber" : "green" },
  etccdi_wsdi:   { label: "고온지속기간(WSDI)",   unit: "days/yr",   rag: (v) => v > 60 ? "red" : v > 20 ? "amber" : "green" },
  etccdi_wbgt:   { label: "습구흑구온도(WBGT)",   unit: "°C",        rag: (v) => v > 28 ? "red" : v > 23 ? "amber" : "green" },
  // ── ETCCDI 극값 지수 — 강수 (6) ──────────────────────────────────────────
  etccdi_cdd:    { label: "연속건조일수(CDD)",    unit: "days",      rag: (v) => v > 60 ? "red" : v > 30 ? "amber" : "green" },
  etccdi_cwd:    { label: "연속습윤일수(CWD)",    unit: "days",      rag: (v) => v > 20 ? "red" : v > 10 ? "amber" : "green" },
  etccdi_rx1day: { label: "1일최대강수(Rx1day)",  unit: "mm",        rag: (v) => v > 100 ? "red" : v > 50 ? "amber" : "green" },
  etccdi_rx5day: { label: "5일최대강수(Rx5day)",  unit: "mm",        rag: (v) => v > 200 ? "red" : v > 100 ? "amber" : "green" },
  etccdi_r95p:   { label: "극한강수(R95p)",       unit: "mm/yr",     rag: (v) => v > 500 ? "red" : v > 250 ? "amber" : "green" },
  etccdi_sdii:   { label: "강수강도(SDII)",       unit: "mm/wetday", rag: (v) => v > 20 ? "red" : v > 12 ? "amber" : "green" },
  // ── Aqueduct 4.0 수자원 위험 (6) — WRI 0~5 스케일 ──────────────────────────
  aq_water_stress:      { label: "수자원 스트레스(Aq)",      unit: "0-5", rag: (v) => v > 3.5 ? "red" : v > 2.0 ? "amber" : "green" },
  aq_river_flood:       { label: "하천홍수 위험(Aq)",        unit: "0-5", rag: (v) => v > 3.0 ? "red" : v > 1.5 ? "amber" : "green" },
  aq_coastal_flood:     { label: "해안침수 위험(Aq)",        unit: "0-5", rag: (v) => v > 2.0 ? "red" : v > 1.0 ? "amber" : "green" },
  aq_drought:           { label: "가뭄 위험(Aq)",            unit: "0-5", rag: (v) => v > 3.0 ? "red" : v > 1.5 ? "amber" : "green" },
  aq_interann_var:      { label: "연간변동성(Aq)",           unit: "0-5", rag: (v) => v > 3.0 ? "red" : v > 1.5 ? "amber" : "green" },
  aq_water_stress_2050: { label: "수자원 스트레스 2050(Aq)", unit: "0-5", rag: (v) => v > 3.5 ? "red" : v > 2.0 ? "amber" : "green" },
  // ── IBTrACS 태풍 통계 (3) — 역사적 1980-2023 ────────────────────────────────
  tc_annual_freq: { label: "태풍 연간빈도(IBT)",  unit: "회/yr", rag: (v) => v > 5 ? "red" : v > 2 ? "amber" : "green" },
  tc_max_wind_kt: { label: "최대풍속 극값(IBT)",  unit: "kt",    rag: (v) => v > 100 ? "red" : v > 64 ? "amber" : "green" },
  tc_cat3_count:  { label: "Cat3+ 태풍수(IBT)",   unit: "회",    rag: (v) => v > 5 ? "red" : v > 1 ? "amber" : "green" },
  // ── GEM PSHA 지진 (2) — 정적 문헌값 ────────────────────────────────────────
  psha_pga_475:   { label: "PGA 475년 빈도(PSHA)",  unit: "g", rag: (v) => v > 0.3 ? "red" : v > 0.15 ? "amber" : "green" },
  psha_pga_2475:  { label: "PGA 2475년 빈도(PSHA)", unit: "g", rag: (v) => v > 0.6 ? "red" : v > 0.3 ? "amber" : "green" },
  // ── World Bank CCKP 0.25° (5) — 신규 ────────────────────────────────────
  cckp_hi35:   { label: "열지수초과일(HI>35°C)",  unit: "days/yr",   rag: (v) => v > 60 ? "red" : v > 20 ? "amber" : "green" },
  cckp_hd40:   { label: "극한고온일(Tmax>40°C)",  unit: "days/yr",   rag: (v) => v > 30 ? "red" : v > 10 ? "amber" : "green" },
  cckp_tr26:   { label: "열대야한국기준(>26°C)",   unit: "days/yr",   rag: (v) => v > 30 ? "red" : v > 10 ? "amber" : "green" },
  cckp_cdd65:  { label: "냉방도일(CDD base 65°F)", unit: "°F·day/yr", rag: (v) => v > 2500 ? "red" : v > 1500 ? "amber" : "green" },
  cckp_hdd65:  { label: "난방도일(HDD base 65°F)", unit: "°F·day/yr", rag: (v) => v > 4000 ? "red" : v > 2000 ? "amber" : "green" },
  // ── CCKP ETCCDI 교차검증 (온도 계열) ────────────────────────────────────────
  cckp_csdi:        { label: "한파지속기간(CSDI)",    unit: "days/yr", rag: (v) => v > 10 ? "red" : v > 4 ? "amber" : "green" },
  cckp_wsdi:        { label: "온난지속기간(WSDI-CP)", unit: "days/yr", rag: (v) => v > 30 ? "red" : v > 10 ? "amber" : "green" },
  cckp_cdd_consec:  { label: "연속건조일수(CDD-CP)",  unit: "days",    rag: (v) => v > 60 ? "red" : v > 30 ? "amber" : "green" },
  // ── CCKP 신규 확장 변수 ─────────────────────────────────────────────────────
  cckp_spei12:  { label: "가뭄지수(SPEI-12)",       unit: "index",    rag: (v) => v < -1.5 ? "red" : v < -0.5 ? "amber" : "green" },
  cckp_gsl:     { label: "생장기간(GSL)",            unit: "days/yr",  rag: (v) => v > 350 ? "red" : v > 320 ? "amber" : "green" },
  cckp_hurs:    { label: "상대습도(HURS)",           unit: "%",        rag: (v) => v > 80 ? "red" : v > 72 ? "amber" : "green" },
  cckp_id:      { label: "결빙일(ID, Tmax<0°C)",    unit: "days/yr",  rag: (v) => v > 30 ? "red" : v > 10 ? "amber" : "green" },
  cckp_rxmonth: { label: "월최대강수(Rx-month)",     unit: "mm/month", rag: (v) => v > 400 ? "red" : v > 250 ? "amber" : "green" },
};

const DRIVER_KEYS = Object.keys(DRIVER_META);

// ── CMIP6 상세 메타 (Excel용) ─────────────────────────────────────────────────
const CMIP6_META_EX = {
  tasmax:  { label: "최고기온",  unit: "°C",     desc: "연평균 일최고기온 (Annual mean of daily Tmax)" },
  tasmin:  { label: "최저기온",  unit: "°C",     desc: "연평균 일최저기온 (Annual mean of daily Tmin)" },
  tas:     { label: "평균기온",  unit: "°C",     desc: "연평균 기온 (Annual mean temperature)" },
  pr:      { label: "강수량",    unit: "mm/day", desc: "연평균 일강수량 (Annual mean daily precip.)" },
  prsn:    { label: "강설량",    unit: "mm/day", desc: "연평균 일강설량 (Annual mean daily snowfall)" },
  sfcWind: { label: "지표풍속",  unit: "m/s",    desc: "연평균 지표 10m 풍속" },
  evspsbl: { label: "증발산",    unit: "mm/day", desc: "연평균 일증발산량" },
};

// ── ETCCDI 극값 지수 메타 ─────────────────────────────────────────────────────
const ETCCDI_META = {
  etccdi_txx:    { label: "최고기온 극값(TXx)",  unit: "°C",        desc: "연중 일최고기온의 최댓값" },
  etccdi_tnn:    { label: "최저기온 극값(TNn)",   unit: "°C",        desc: "연중 일최저기온의 최솟값" },
  etccdi_su:     { label: "서머데이(SU>25°C)",    unit: "days/yr",   desc: "일최고기온 25°C 초과 일수" },
  etccdi_tr:     { label: "열대야(TR>20°C)",      unit: "days/yr",   desc: "일최저기온 20°C 초과 일수" },
  etccdi_fd:     { label: "서리일수(FD<0°C)",     unit: "days/yr",   desc: "일최저기온 0°C 미만 일수" },
  etccdi_wsdi:   { label: "고온지속기간(WSDI)",   unit: "days/yr",   desc: "장기 고온 지속일수 (이상고온 스트레스)" },
  etccdi_wbgt:   { label: "습구흑구온도(WBGT)",   unit: "°C",        desc: "열·습도·복사 결합 노동안전 지수" },
  etccdi_cdd:    { label: "연속건조일수(CDD)",    unit: "days",      desc: "최장 연속 강수 1mm 미만 일수" },
  etccdi_cwd:    { label: "연속습윤일수(CWD)",    unit: "days",      desc: "최장 연속 강수 1mm 이상 일수" },
  etccdi_rx1day: { label: "1일최대강수(Rx1day)",  unit: "mm",        desc: "연중 1일 최대강수량" },
  etccdi_rx5day: { label: "5일최대강수(Rx5day)",  unit: "mm",        desc: "연중 5일 누적 최대강수량" },
  etccdi_r95p:   { label: "극한강수(R95p)",       unit: "mm/yr",     desc: "연 95th 백분위 초과 강수 총량" },
  etccdi_sdii:   { label: "강수강도(SDII)",       unit: "mm/wetday", desc: "강수일 평균 강수강도" },
};

// ── CLIMADA EAL 메타 (Excel용) ────────────────────────────────────────────────
const CLIMADA_META = {
  TC_EAL:       { label: "태풍 EAL",    unit: "USD/yr", desc: "CLIMADA LT HDF5 — 열대저기압 연간예상손실" },
  Flood_EAL:    { label: "홍수 EAL",    unit: "USD/yr", desc: "CLIMADA Flood HDF5 — 하천범람 연간예상손실" },
  EQ_EAL:       { label: "지진 EAL",    unit: "USD/yr", desc: "GEM PSHA — 지진 연간예상손실" },
  Wildfire_EAL: { label: "산불 EAL",    unit: "USD/yr", desc: "CLIMADA — 산불 연간예상손실" },
};

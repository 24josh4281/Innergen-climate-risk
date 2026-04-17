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
  near:     "근미래(2025-34)",
  mid:      "중기(2045-54)",
  far:      "장기(2075-84)",
  end:      "말기(2090-99)",
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
  wildfire_risk:   { label: "산불 위험",         unit: "score", rag: (v) => v > 50 ? "red" : v > 30 ? "amber" : "green" },
  earthquake_risk: { label: "지진 위험",         unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  landslide_risk:  { label: "산사태 위험",       unit: "score", rag: (v) => v > 45 ? "red" : v > 25 ? "amber" : "green" },
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

// ── CLIMADA EAL 메타 (Excel용) ────────────────────────────────────────────────
const CLIMADA_META = {
  TC_EAL:       { label: "태풍 EAL",    unit: "USD/yr", desc: "CLIMADA LT HDF5 — 열대저기압 연간예상손실" },
  Flood_EAL:    { label: "홍수 EAL",    unit: "USD/yr", desc: "CLIMADA Flood HDF5 — 하천범람 연간예상손실" },
  EQ_EAL:       { label: "지진 EAL",    unit: "USD/yr", desc: "GEM PSHA — 지진 연간예상손실" },
  Wildfire_EAL: { label: "산불 EAL",    unit: "USD/yr", desc: "CLIMADA — 산불 연간예상손실" },
};

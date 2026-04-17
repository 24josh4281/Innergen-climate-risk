/**
 * excel_export.js — SheetJS Excel 다운로드
 * 시트 구성: SSP별 4개 + CMIP6_기후변수 + PhyRisk_위험도 + CLIMADA_EAL + All_Data + 분석_정보
 */

const SSP_SHEET_NAMES = {
  ssp126: "SSP1-2.6",
  ssp245: "SSP2-4.5",
  ssp370: "SSP3-7.0",
  ssp585: "SSP5-8.5",
};

const PERIOD_LABEL_MAP = {
  baseline: "현재(2015-24)",
  near:     "근미래(2025-34)",
  mid:      "중기(2045-54)",
  far:      "장기(2075-84)",
  end:      "말기(2090-99)",
};

// 변수 분류
const CMIP6_DRIVER_KEYS  = ["tasmax", "tasmin", "tas", "pr", "prsn", "sfcWind", "evspsbl"];
const PHYSRISK_DRIVER_KEYS = [
  "heat_stress", "flood_risk", "river_flood", "coastal_flood", "pluvial_flood",
  "drought_risk", "water_stress", "cyclone_risk", "wildfire_risk",
  "sea_level_rise", "storm_surge", "earthquake_risk", "landslide_risk",
];
const CLIMADA_DRIVER_KEYS = ["TC_EAL", "Flood_EAL", "EQ_EAL", "Wildfire_EAL"];

const CLIMADA_META = {
  TC_EAL:       { label: "태풍 연간예상손실",   unit: "USD/yr",  desc: "CLIMADA LT HDF5 기반 열대저기압(TC) 피해" },
  Flood_EAL:    { label: "홍수 연간예상손실",   unit: "USD/yr",  desc: "CLIMADA Flood HDF5 기반 하천범람 피해" },
  EQ_EAL:       { label: "지진 연간예상손실",   unit: "USD/yr",  desc: "GEM PSHA 기반 지진 구조적 피해" },
  Wildfire_EAL: { label: "산불 연간예상손실",   unit: "USD/yr",  desc: "CLIMADA 기반 산불 피해" },
};

// ── 공통 헬퍼 ──────────────────────────────────────────────────────────────

function getVal(entry) {
  if (entry === null || entry === undefined) return null;
  const v = typeof entry === "object" ? entry.value : entry;
  if (v === null || v === undefined) return null;
  return typeof v === "number" ? Math.round(v * 100) / 100 : v;
}

function getSrc(entry) {
  return (entry && typeof entry === "object") ? (entry.source || "") : "";
}

function getNote(entry) {
  return (entry && typeof entry === "object") ? (entry.note || "") : "";
}

function fmt(v) {
  return v === null ? "N/A" : v;
}

// ── 1. SSP별 통합 히트맵 시트 (기존) ──────────────────────────────────────

function buildSspSheet(drivers, ssp) {
  const periods = Object.keys(PERIOD_LABEL_MAP);
  const sspData = drivers[ssp] || {};
  const allKeys = Object.keys(DRIVER_META);

  const header = ["기후 동인", "변수키", "단위", "데이터소스", ...periods.map(p => PERIOD_LABEL_MAP[p])];
  const rows = [header];

  for (const dk of allKeys) {
    const meta = DRIVER_META[dk];
    if (!meta) continue;
    const refEntry = (sspData["baseline"] || {})[dk];
    const src = getSrc(refEntry);
    const vals = periods.map(p => fmt(getVal((sspData[p] || {})[dk])));
    rows.push([meta.label, dk, meta.unit || "-", src, ...vals]);
  }
  return rows;
}

// ── 2. CMIP6 기후변수 시트 ────────────────────────────────────────────────

function buildCmip6Sheet(drivers) {
  const periods = Object.keys(PERIOD_LABEL_MAP);
  const rows = [];

  rows.push(["CMIP6 앙상블 기후변수"]);
  rows.push(["데이터소스: CMIP6 17모델 앙상블 — SSP 시나리오별 기간 평균값"]);
  rows.push(["변수: 최고기온(tasmax), 최저기온(tasmin), 평균기온(tas), 강수량(pr), 강설량(prsn), 풍속(sfcWind), 증발산(evspsbl)"]);
  rows.push([]);

  for (const [ssp, sspLabel] of Object.entries(SSP_SHEET_NAMES)) {
    const sspData = drivers[ssp] || {};
    rows.push([`[ ${sspLabel} ]`]);
    rows.push(["기후변수", "변수키", "단위", ...periods.map(p => PERIOD_LABEL_MAP[p])]);

    for (const dk of CMIP6_DRIVER_KEYS) {
      const meta = DRIVER_META[dk];
      if (!meta) continue;
      const vals = periods.map(p => fmt(getVal((sspData[p] || {})[dk])));
      rows.push([meta.label, dk, meta.unit || "-", ...vals]);
    }
    rows.push([]);
  }

  return rows;
}

// ── 3. PhyRisk 위험도 시트 ────────────────────────────────────────────────

function buildPhyriskSheet(drivers) {
  const rows = [];

  rows.push(["OS-Climate PhyRisk 위험도 점수"]);
  rows.push(["데이터소스: OS-Climate Physical Risk & Resilience API"]);
  rows.push(["단위: 0~100점 (원시값을 365일 기준으로 환산, 100점=최고위험)"]);
  rows.push(["기준: SSP5-8.5 / 2050년 (현재 API 단일 기준값 제공, 전 SSP·시점에 동일 적용)"]);
  rows.push([]);
  rows.push(["위험 유형", "변수키", "단위", "위험도 점수", "RAG 등급", "임계값(RED)", "임계값(AMBER)", "데이터소스"]);

  // SSP5-8.5, mid(2045-54) 기준
  const refData = (drivers["ssp585"] || {})["mid"] || {};

  for (const dk of PHYSRISK_DRIVER_KEYS) {
    const meta = DRIVER_META[dk];
    if (!meta) continue;
    const entry = refData[dk];
    const val = getVal(entry);
    const src = getSrc(entry) || "physrisk_estimate";

    let rag = "N/A";
    if (val !== null && meta.rag) {
      const r = meta.rag(val);
      rag = r === "red" ? "HIGH (고위험)" : r === "amber" ? "MEDIUM (중위험)" : "LOW (저위험)";
    }

    // RAG 임계값 텍스트 추출 (meta.rag 함수 소스에서 읽기 어려우므로 하드코딩 참조 제공)
    rows.push([meta.label, dk, meta.unit || "score", fmt(val), rag, "-", "-", src]);
  }

  return rows;
}

// ── 4. CLIMADA EAL 시트 ────────────────────────────────────────────────────

function buildClimadaSheet(drivers, meta) {
  const rows = [];

  rows.push(["CLIMADA 기반 연간예상손실(EAL)"]);
  rows.push(["데이터소스: CLIMADA HDF5 (TC, Flood), GEM PSHA (EQ), CLIMADA Wildfire"]);
  rows.push([]);

  const ssp585 = drivers["ssp585"] || {};
  const baseData = ssp585["baseline"] || {};

  // T2/T3: CLIMADA entries exist with null values
  const hasCLIMADA = CLIMADA_DRIVER_KEYS.some(k => baseData[k] !== undefined);

  if (hasCLIMADA) {
    rows.push(["CLIMADA 변수", "설명", "단위", "현재값", "데이터소스", "비고"]);
    for (const dk of CLIMADA_DRIVER_KEYS) {
      const info = CLIMADA_META[dk] || { label: dk, unit: "-", desc: "" };
      const entry = baseData[dk];
      const val = getVal(entry);
      const src = getSrc(entry);
      const note = getNote(entry);
      rows.push([info.label, info.desc, info.unit, fmt(val), src, note]);
    }
    rows.push([]);
    rows.push(["※ T2/T3 좌표는 CLIMADA HDF5를 서버에서 직접 조회하지 않습니다."]);
    rows.push(["  정밀 EAL 분석은 T1 정밀 사업장 지정 후 별도 오프라인 분석을 수행하십시오."]);
  } else {
    // T1: no CLIMADA entries in API response → reference to offline file
    const t1site = meta.matched_t1_site || "해당 사업장";
    rows.push([`T1 정밀 사업장 (${t1site}) — CLIMADA 사전계산 데이터`]);
    rows.push(["T1 사업장은 CLIMADA HDF5 기반 사전계산 EAL 데이터를 사용합니다."]);
    rows.push(["상세 EAL 분석 결과는 별도 오프라인 파일(OCI_CLIMADA_PhyRisk.xlsx)을 참조하십시오."]);
    rows.push([]);
    rows.push(["CLIMADA 분석 항목", "설명", "단위", "참조 파일"]);
    for (const dk of CLIMADA_DRIVER_KEYS) {
      const info = CLIMADA_META[dk] || { label: dk, unit: "-", desc: "" };
      rows.push([info.label, info.desc, info.unit, "OCI_CLIMADA_PhyRisk.xlsx"]);
    }
    rows.push([]);
    rows.push(["포트폴리오 EAL 요약 (SSP5-8.5, 2090s)", ""]);
    rows.push(["TC (태풍) EAL", "사전계산 완료 — OCI_CLIMADA_PhyRisk.xlsx 참조"]);
    rows.push(["Flood (홍수) EAL", "사전계산 완료 — OCI_CLIMADA_PhyRisk.xlsx 참조"]);
    rows.push(["EQ (지진) EAL", "GEM PSHA 기반 — OCI_CLIMADA_PhyRisk.xlsx 참조"]);
    rows.push(["Wildfire (산불) EAL", "사전계산 완료 — OCI_CLIMADA_PhyRisk.xlsx 참조"]);
  }

  return rows;
}

// ── 5. All_Data 시트 ──────────────────────────────────────────────────────

function buildAllDataRows(drivers) {
  const rows = [["SSP", "Period", "Driver_Key", "Label", "Unit", "Value", "Source", "Note"]];

  for (const [ssp, sspData] of Object.entries(drivers)) {
    for (const [period, periodData] of Object.entries(sspData)) {
      for (const [dk, entry] of Object.entries(periodData)) {
        const meta = DRIVER_META[dk] || CLIMADA_META[dk] || { label: dk, unit: "-" };
        const val = getVal(entry);
        const src = getSrc(entry);
        const note = getNote(entry);
        rows.push([
          ssp, period, dk,
          meta.label || dk,
          meta.unit || "-",
          fmt(val),
          src,
          note,
        ]);
      }
    }
  }
  return rows;
}

// ── 6. 분석 정보 시트 ────────────────────────────────────────────────────

function buildInfoRows(meta) {
  return [
    ["항목", "값"],
    ["분석 플랫폼", "Innergen Climate Scenario"],
    ["위도 (Lat)", meta.lat],
    ["경도 (Lon)", meta.lon],
    ["국가 코드", meta.country],
    ["데이터 Tier", meta.tier],
    ["Tier 설명", meta.tier_label],
    ["매칭 사업장", meta.matched_t1_site || "없음 (T2/T3)"],
    ["최근접 사업장까지 거리 (km)", meta.distance_to_nearest_t1_km],
    ["출력 일시", new Date().toLocaleString("ko-KR")],
    [],
    ["데이터 소스", "설명", "적용 변수"],
    ["CMIP6", "CMIP6 17모델 앙상블 — SSP 시나리오별 기후변수", "tasmax, tasmin, tas, pr, prsn, sfcWind, evspsbl"],
    ["PhyRisk", "OS-Climate Physical Risk & Resilience — 위험도 0-100 점수", "heat_stress, flood_risk, drought_risk 등 13개"],
    ["CLIMADA", "CLIMADA HDF5 사전계산 — 연간예상손실(EAL)", "TC_EAL, Flood_EAL, EQ_EAL, Wildfire_EAL"],
    [],
    ["시트 구성", "설명"],
    ["SSP1-2.6 ~ SSP5-8.5", "SSP별 전체 기후 동인 통합 히트맵"],
    ["CMIP6_기후변수", "CMIP6 7개 기후변수 × 4 SSP × 5 시점"],
    ["PhyRisk_위험도", "OS-Climate 13개 위험 유형별 점수 및 RAG 등급"],
    ["CLIMADA_EAL", "CLIMADA 기반 연간예상손실 (T1 사전계산 / T2-T3 근사)"],
    ["All_Data", "모든 변수 원시 데이터 (long 포맷)"],
    ["분석_정보", "본 시트 (메타데이터 및 출처)"],
  ];
}

// ── 메인 export 함수 ──────────────────────────────────────────────────────

/**
 * Excel 파일 생성 및 다운로드
 * @param {Object} apiResult - {meta, drivers}
 */
function exportExcel(apiResult) {
  const { meta, drivers } = apiResult;
  const wb = XLSX.utils.book_new();

  // 1. SSP별 통합 히트맵 시트 (4개)
  for (const [ssp, sheetName] of Object.entries(SSP_SHEET_NAMES)) {
    const rows = buildSspSheet(drivers, ssp);
    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws["!cols"] = [{ wch: 20 }, { wch: 16 }, { wch: 8 }, { wch: 22 }, ...Object.keys(PERIOD_LABEL_MAP).map(() => ({ wch: 15 }))];
    XLSX.utils.book_append_sheet(wb, ws, sheetName);
  }

  // 2. CMIP6 기후변수 시트
  const cmip6Rows = buildCmip6Sheet(drivers);
  const wsCmip6 = XLSX.utils.aoa_to_sheet(cmip6Rows);
  wsCmip6["!cols"] = [{ wch: 14 }, { wch: 12 }, { wch: 8 }, ...Object.keys(PERIOD_LABEL_MAP).map(() => ({ wch: 15 }))];
  XLSX.utils.book_append_sheet(wb, wsCmip6, "CMIP6_기후변수");

  // 3. PhyRisk 위험도 시트
  const physriskRows = buildPhyriskSheet(drivers);
  const wsPhysrisk = XLSX.utils.aoa_to_sheet(physriskRows);
  wsPhysrisk["!cols"] = [{ wch: 20 }, { wch: 18 }, { wch: 8 }, { wch: 14 }, { wch: 20 }, { wch: 14 }, { wch: 14 }, { wch: 22 }];
  XLSX.utils.book_append_sheet(wb, wsPhysrisk, "PhyRisk_위험도");

  // 4. CLIMADA EAL 시트
  const climadaRows = buildClimadaSheet(drivers, meta);
  const wsClimada = XLSX.utils.aoa_to_sheet(climadaRows);
  wsClimada["!cols"] = [{ wch: 22 }, { wch: 36 }, { wch: 10 }, { wch: 14 }, { wch: 24 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(wb, wsClimada, "CLIMADA_EAL");

  // 5. All_Data (raw long format)
  const allRows = buildAllDataRows(drivers);
  const wsAll = XLSX.utils.aoa_to_sheet(allRows);
  wsAll["!cols"] = [{ wch: 10 }, { wch: 12 }, { wch: 18 }, { wch: 20 }, { wch: 8 }, { wch: 12 }, { wch: 24 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(wb, wsAll, "All_Data");

  // 6. 분석 정보
  const infoRows = buildInfoRows(meta);
  const wsInfo = XLSX.utils.aoa_to_sheet(infoRows);
  wsInfo["!cols"] = [{ wch: 28 }, { wch: 50 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(wb, wsInfo, "분석_정보");

  // 파일명: InnergenCS_Tier_lat_lon_YYYYMMDD.xlsx
  const latStr = meta.lat.toFixed(2).replace(".", "p");
  const lonStr = meta.lon.toFixed(2).replace(".", "p");
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const filename = `InnergenCS_${meta.tier}_${latStr}_${lonStr}_${dateStr}.xlsx`;

  XLSX.writeFile(wb, filename);
}

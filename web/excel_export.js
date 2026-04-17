/**
 * excel_export.js — 데이터소스별 분리 Excel 다운로드
 *
 * 시트 구성 (10개):
 *   1. CMIP6_시나리오  — CMIP6 7개 기후변수 × 4SSP × 5시점 피벗
 *   2. ETCCDI_극값지수 — 13개 ETCCDI 극값 지수 × 4SSP × 5시점 피벗
 *   3. PhyRisk_위험도  — OS-Climate 18개 위험 유형 점수
 *   4. CLIMADA_EAL     — CLIMADA 연간예상손실 (사전계산 참조 또는 근사)
 *   5. SSP5-8.5        — 전체 동인 통합 (카테고리 구분)
 *   6. SSP3-7.0
 *   7. SSP2-4.5
 *   8. SSP1-2.6
 *   9. 전체_원시데이터 — long 포맷
 *  10. 분석_정보       — 메타데이터 + 출처
 */

// 상수: SSP_ORDER, SSP_LABELS, PERIOD_KEYS, PERIOD_LABEL_MAP, CMIP6_KEYS,
//       PHYSRISK_KEYS, CLIMADA_KEYS, CMIP6_META_EX, CLIMADA_META → constants.js

// PERIOD_KEYS는 PERIOD_KEYS와 동일 — constants.js의 PERIOD_KEYS 사용

// ── 헬퍼 ──────────────────────────────────────────────────────────────────────

function getVal(entry) {
  if (entry == null) return null;
  const v = typeof entry === "object" ? entry.value : entry;
  if (v == null) return null;
  return typeof v === "number" ? Math.round(v * 100) / 100 : v;
}

function getNote(entry) {
  return (entry && typeof entry === "object") ? (entry.note || "") : "";
}

function fmt(v) { return v === null ? "N/A" : v; }

/** 변수키 → 카테고리명 */
function category(dk) {
  if (CMIP6_KEYS.includes(dk))     return "CMIP6";
  if (ETCCDI_KEYS.includes(dk))    return "ETCCDI";
  if (PHYSRISK_KEYS.includes(dk))  return "PhyRisk";
  if (CLIMADA_KEYS.includes(dk))   return "CLIMADA";
  return "기타";
}

/** RAG 등급 텍스트 */
function ragLabel(dk, val) {
  const meta = (typeof DRIVER_META !== "undefined") ? DRIVER_META[dk] : null;
  if (!meta || val === null || !meta.rag) return "N/A";
  const r = meta.rag(val);
  return r === "red" ? "HIGH" : r === "amber" ? "MEDIUM" : "LOW";
}

// ── 시트 1: CMIP6_시나리오 ────────────────────────────────────────────────────
// 구조: 변수(행) × SSP·시점 조합(열) 피벗 테이블

function buildCmip6Sheet(drivers) {
  const rows = [];

  // 제목 블록
  rows.push(["CMIP6 기후 시나리오 데이터"]);
  rows.push(["출처: CMIP6 17개 모델 앙상블 평균 (CMIP6 Multi-Model Ensemble)"]);
  rows.push(["단위: 기온 °C / 강수·강설·증발산 mm/day / 풍속 m/s"]);
  rows.push([]);

  // 2-단 헤더
  // 행1: [변수, 단위, 설명, SSP1-2.6(×5 합치기), "", "", "", "", SSP2-4.5 ...]
  const ssp_span_row = ["변수", "단위", "설명"];
  for (const ssp of SSP_ORDER) {
    ssp_span_row.push(SSP_LABELS[ssp]);          // SSP 그룹 레이블
    for (let i = 1; i < PERIOD_KEYS.length; i++) ssp_span_row.push(""); // 병합용 빈셀
  }
  rows.push(ssp_span_row);

  // 행2: [변수, 단위, 설명, 현재, 근미래, 중기, 장기, 말기, 현재, ...]
  const period_row = ["", "", ""];
  for (const ssp of SSP_ORDER) {
    for (const p of PERIOD_KEYS) period_row.push(PERIOD_LABEL_MAP[p]);
  }
  rows.push(period_row);

  // 데이터 행
  for (const dk of CMIP6_KEYS) {
    const meta = CMIP6_META_EX[dk] || { label: dk, unit: "-", desc: "" };
    const row = [meta.label, meta.unit, meta.desc];
    for (const ssp of SSP_ORDER) {
      for (const p of PERIOD_KEYS) {
        row.push(fmt(getVal(((drivers[ssp] || {})[p] || {})[dk])));
      }
    }
    rows.push(row);
  }

  return rows;
}

// ── 시트 2: ETCCDI_극값지수 ──────────────────────────────────────────────────

function buildEtccdiSheet(drivers) {
  const rows = [];
  rows.push(["ETCCDI 기후 극값 지수 (Climate Extremes Indices)"]);
  rows.push(["출처: CMIP6 17개 모델 앙상블 일별 데이터 → ETCCDI 산출 (PhaseAnalysis)"]);
  rows.push(["단위: 기온 °C / 일수 days/yr / 강수 mm"]);
  rows.push([]);

  const ssp_span_row = ["지수", "단위", "설명"];
  for (const ssp of SSP_ORDER) {
    ssp_span_row.push(SSP_LABELS[ssp]);
    for (let i = 1; i < PERIOD_KEYS.length; i++) ssp_span_row.push("");
  }
  rows.push(ssp_span_row);

  const period_row = ["", "", ""];
  for (const ssp of SSP_ORDER) {
    for (const p of PERIOD_KEYS) period_row.push(PERIOD_LABEL_MAP[p]);
  }
  rows.push(period_row);

  for (const dk of ETCCDI_KEYS) {
    const meta = ETCCDI_META[dk] || { label: dk, unit: "-", desc: "" };
    const row = [meta.label, meta.unit, meta.desc];
    for (const ssp of SSP_ORDER) {
      for (const p of PERIOD_KEYS) {
        row.push(fmt(getVal(((drivers[ssp] || {})[p] || {})[dk])));
      }
    }
    rows.push(row);
  }
  return rows;
}

// ── 시트 3(구 2): PhyRisk_위험도 ─────────────────────────────────────────────
// ── 시트 2: PhyRisk_위험도 ───────────────────────────────────────────────────
// 구조: 위험유형(행) × SSP·시점(열) 피벗
// PhyRisk는 현재 단일 기준값(SSP5-8.5 / 2050)이지만 API가 전 SSP·시점에 동일값 채움

function buildPhyriskSheet(drivers) {
  const rows = [];

  rows.push(["OS-Climate PhyRisk 위험도 점수"]);
  rows.push(["출처: OS-Climate Physical Risk & Resilience (physrisk API)"]);
  rows.push(["스코어: 0~100점 — 원시값(일수 등)을 365일 기준 환산 (100점=최고위험)"]);
  rows.push(["※ 현재 API는 SSP5-8.5/2050년 단일 기준값을 전 시점에 동일 적용"]);
  rows.push([]);

  // 2-단 헤더 (CMIP6 시트와 동일 구조)
  const ssp_span_row = ["위험 유형", "단위", "RAG(SSP5-8.5 말기)"];
  for (const ssp of SSP_ORDER) {
    ssp_span_row.push(SSP_LABELS[ssp]);
    for (let i = 1; i < PERIOD_KEYS.length; i++) ssp_span_row.push("");
  }
  rows.push(ssp_span_row);

  const period_row = ["", "", ""];
  for (const ssp of SSP_ORDER) {
    for (const p of PERIOD_KEYS) period_row.push(PERIOD_LABEL_MAP[p]);
  }
  rows.push(period_row);

  // 데이터 행
  for (const dk of PHYSRISK_KEYS) {
    const meta = (typeof DRIVER_META !== "undefined") ? DRIVER_META[dk] : null;
    if (!meta) continue;

    // RAG는 SSP5-8.5 말기 기준
    const refVal = getVal(((drivers["ssp585"] || {})["end"] || {})[dk]);
    const rag = ragLabel(dk, refVal);

    const row = [meta.label, meta.unit || "score", rag];
    for (const ssp of SSP_ORDER) {
      for (const p of PERIOD_KEYS) {
        row.push(fmt(getVal(((drivers[ssp] || {})[p] || {})[dk])));
      }
    }
    rows.push(row);
  }

  return rows;
}

// ── 시트 3: CLIMADA_EAL ──────────────────────────────────────────────────────

function buildClimadaSheet(drivers, meta) {
  const rows = [];

  rows.push(["CLIMADA 기반 연간예상손실 (EAL)"]);
  rows.push(["출처: CLIMADA HDF5 (태풍·홍수·산불), GEM PSHA (지진)"]);
  rows.push([]);

  const base585 = (drivers["ssp585"] || {})["baseline"] || {};
  const hasCLIMADA = CLIMADA_KEYS.some(k => base585[k] !== undefined);

  if (hasCLIMADA) {
    // T2/T3: entries exist (값은 null, note 있음)
    rows.push(["CLIMADA 변수", "단위", "설명", "SSP1-2.6", "SSP2-4.5", "SSP3-7.0", "SSP5-8.5", "비고"]);
    rows.push(["", "", "", "(각 열: 현재~말기 평균 / 현재 단일값)", "", "", "", ""]);

    for (const dk of CLIMADA_KEYS) {
      const info = CLIMADA_META[dk] || { label: dk, unit: "-", desc: "" };
      const note = getNote(base585[dk]);
      // SSP별 현재 기준값 (T2/T3에선 모두 null)
      const vals = SSP_ORDER.map(ssp => fmt(getVal(((drivers[ssp] || {})["baseline"] || {})[dk])));
      rows.push([info.label, info.unit, info.desc, ...vals, note]);
    }

    rows.push([]);
    rows.push(["※ T2/T3 좌표는 CLIMADA HDF5를 서버에서 직접 조회하지 않습니다."]);
    rows.push(["  EAL 분석이 필요하면 T1 정밀 사업장으로 등록 후 별도 오프라인 분석을 수행하십시오."]);

  } else {
    // T1: 사전계산 완료 → 오프라인 파일 참조
    const t1 = meta.matched_t1_site || "해당 사업장";
    rows.push([`T1 정밀 사업장 (${t1}): CLIMADA HDF5 사전계산 데이터`]);
    rows.push(["EAL 상세 분석은 별도 오프라인 파일을 참조하십시오."]);
    rows.push([]);

    rows.push(["CLIMADA 항목", "단위", "설명", "사전계산 결과"]);
    for (const dk of CLIMADA_KEYS) {
      const info = CLIMADA_META[dk] || { label: dk, unit: "-", desc: "" };
      rows.push([info.label, info.unit, info.desc, "사전계산 완료 (오프라인 파일 참조)"]);
    }
    rows.push([]);
    rows.push(["항목", "포트폴리오 수준 요약 (참고)"]);
    rows.push(["태풍 (TC) EAL",    "SSP5-8.5 말기 포트폴리오 EAL 분석 완료"]);
    rows.push(["홍수 (Flood) EAL", "SSP5-8.5 말기 포트폴리오 EAL 분석 완료"]);
    rows.push(["지진 (EQ) EAL",    "GEM PSHA 기반 분석 완료"]);
    rows.push(["산불 (Wildfire) EAL", "SSP5-8.5 말기 분석 완료"]);
  }

  return rows;
}

// ── 시트 4~7: SSP별 통합 히트맵 ──────────────────────────────────────────────
// 카테고리(CMIP6/PhyRisk/CLIMADA) 열을 명시

function buildSspSheet(drivers, ssp) {
  const sspData = drivers[ssp] || {};
  const rows = [];

  // 제목
  rows.push([`${SSP_LABELS[ssp]} — 전체 기후 동인`]);
  rows.push([]);

  // 헤더
  rows.push([
    "카테고리", "기후 동인", "변수키", "단위",
    ...PERIOD_KEYS.map(p => PERIOD_LABEL_MAP[p]),
  ]);

  // CMIP6 그룹
  rows.push(["── CMIP6 기후변수 ──"]);
  for (const dk of CMIP6_KEYS) {
    const meta = CMIP6_META_EX[dk] || { label: dk, unit: "-" };
    const vals = PERIOD_KEYS.map(p => fmt(getVal((sspData[p] || {})[dk])));
    rows.push(["CMIP6", meta.label, dk, meta.unit, ...vals]);
  }

  rows.push([]);

  // ETCCDI 그룹
  rows.push(["── ETCCDI 극값 지수 ──"]);
  for (const dk of ETCCDI_KEYS) {
    const meta = ETCCDI_META[dk] || { label: dk, unit: "-" };
    const vals = PERIOD_KEYS.map(p => fmt(getVal((sspData[p] || {})[dk])));
    rows.push(["ETCCDI", meta.label, dk, meta.unit, ...vals]);
  }

  rows.push([]);

  // PhyRisk 그룹
  rows.push(["── PhyRisk 위험도 ──"]);
  for (const dk of PHYSRISK_KEYS) {
    const meta = (typeof DRIVER_META !== "undefined") ? DRIVER_META[dk] : { label: dk, unit: "score" };
    if (!meta) continue;
    const vals = PERIOD_KEYS.map(p => fmt(getVal((sspData[p] || {})[dk])));
    rows.push(["PhyRisk", meta.label, dk, meta.unit || "score", ...vals]);
  }

  rows.push([]);

  // CLIMADA 그룹 (T2/T3만 있음, T1은 생략 처리)
  const hasClimada = CLIMADA_KEYS.some(k => (sspData["baseline"] || {})[k] !== undefined);
  if (hasClimada) {
    rows.push(["── CLIMADA EAL ──"]);
    for (const dk of CLIMADA_KEYS) {
      const info = CLIMADA_META[dk] || { label: dk, unit: "USD/yr" };
      const vals = PERIOD_KEYS.map(p => fmt(getVal((sspData[p] || {})[dk])));
      rows.push(["CLIMADA", info.label, dk, info.unit, ...vals]);
    }
  }

  return rows;
}

// ── 시트 8: 전체_원시데이터 ──────────────────────────────────────────────────

function buildAllDataRows(drivers) {
  const rows = [["카테고리", "SSP", "시점", "변수키", "변수명", "단위", "값"]];

  const allMeta = dk => {
    if (CMIP6_META_EX[dk])  return CMIP6_META_EX[dk];
    if (ETCCDI_META[dk])    return ETCCDI_META[dk];
    if (CLIMADA_META[dk])   return CLIMADA_META[dk];
    return (typeof DRIVER_META !== "undefined" && DRIVER_META[dk]) ? DRIVER_META[dk] : { label: dk, unit: "-" };
  };

  for (const ssp of SSP_ORDER) {
    const sspData = drivers[ssp] || {};
    for (const p of PERIOD_KEYS) {
      const periodData = sspData[p] || {};
      // CMIP6 먼저
      for (const dk of CMIP6_KEYS) {
        const m = allMeta(dk);
        rows.push(["CMIP6", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "-", fmt(getVal(periodData[dk]))]);
      }
      // ETCCDI
      for (const dk of ETCCDI_KEYS) {
        const m = allMeta(dk);
        rows.push(["ETCCDI", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "-", fmt(getVal(periodData[dk]))]);
      }
      // PhyRisk
      for (const dk of PHYSRISK_KEYS) {
        const m = allMeta(dk);
        rows.push(["PhyRisk", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "score", fmt(getVal(periodData[dk]))]);
      }
      // CLIMADA
      for (const dk of CLIMADA_KEYS) {
        if (periodData[dk] === undefined) continue;
        const m = allMeta(dk);
        const note = getNote(periodData[dk]);
        rows.push(["CLIMADA", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "USD/yr",
          note || fmt(getVal(periodData[dk]))]);
      }
    }
  }

  return rows;
}

// ── 시트 9: 분석_정보 ────────────────────────────────────────────────────────

function buildInfoRows(meta) {
  return [
    ["항목", "값"],
    ["분석 플랫폼", "Innergen Climate Scenario"],
    ["분석 일시", new Date().toLocaleString("ko-KR")],
    ["위도 (Lat)", meta.lat],
    ["경도 (Lon)", meta.lon],
    ["국가 코드", meta.country],
    ["데이터 Tier", meta.tier],
    ["Tier 설명", meta.tier_label],
    ["매칭 사업장", meta.matched_t1_site || "없음 (T2/T3)"],
    ["최근접 사업장 거리 (km)", meta.distance_to_nearest_t1_km],
    [],
    ["카테고리", "출처", "변수", "설명"],
    [
      "CMIP6",
      "CMIP6 17개 모델 앙상블",
      "tasmax / tasmin / tas / pr / prsn / sfcWind / evspsbl",
      "SSP 시나리오별 기간 평균 기후변수 (기온·강수·바람·증발산)",
    ],
    [
      "PhyRisk",
      "OS-Climate Physical Risk & Resilience",
      "heat_stress / flood_risk / drought_risk 등 13개",
      "0~100점 위험도 점수 (원시값 365일 기준 환산)",
    ],
    [
      "CLIMADA",
      "CLIMADA HDF5 / GEM PSHA",
      "TC_EAL / Flood_EAL / EQ_EAL / Wildfire_EAL",
      "T1 사전계산 EAL / T2·T3 서버 제약으로 N/A",
    ],
    [],
    ["시트명", "내용"],
    ["CMIP6_시나리오",   "CMIP6 7개 변수 × 4SSP × 5시점 피벗 테이블"],
    ["PhyRisk_위험도",   "OS-Climate 13개 위험유형 × 4SSP × 5시점 피벗 테이블"],
    ["CLIMADA_EAL",      "연간예상손실 (T1 오프라인 참조 / T2-T3 N/A)"],
    ["SSP5-8.5 ~ SSP1-2.6", "SSP별 CMIP6·PhyRisk·CLIMADA 통합 (카테고리 구분)"],
    ["전체_원시데이터",  "카테고리·SSP·시점별 long 포맷 원시값"],
    ["분석_정보",        "본 시트 — 메타데이터 및 데이터소스 출처"],
  ];
}

// ── 메인 export ───────────────────────────────────────────────────────────────

function exportExcel(apiResult) {
  const { meta, drivers } = apiResult;
  const wb = XLSX.utils.book_new();

  const colW = (widths) => widths.map(w => ({ wch: w }));

  // ① CMIP6_시나리오 (피벗)
  const wsCmip6 = XLSX.utils.aoa_to_sheet(buildCmip6Sheet(drivers));
  wsCmip6["!cols"] = colW([14, 8, 36, ...SSP_ORDER.flatMap(() => PERIOD_KEYS.map(() => 14))]);
  XLSX.utils.book_append_sheet(wb, wsCmip6, "CMIP6_시나리오");

  // ② ETCCDI_극값지수 (피벗)
  const wsEtccdi = XLSX.utils.aoa_to_sheet(buildEtccdiSheet(drivers));
  wsEtccdi["!cols"] = colW([20, 10, 36, ...SSP_ORDER.flatMap(() => PERIOD_KEYS.map(() => 14))]);
  XLSX.utils.book_append_sheet(wb, wsEtccdi, "ETCCDI_극값지수");

  // ③ PhyRisk_위험도 (피벗)
  const wsPhysrisk = XLSX.utils.aoa_to_sheet(buildPhyriskSheet(drivers));
  wsPhysrisk["!cols"] = colW([20, 8, 14, ...SSP_ORDER.flatMap(() => PERIOD_KEYS.map(() => 14))]);
  XLSX.utils.book_append_sheet(wb, wsPhysrisk, "PhyRisk_위험도");

  // ④ CLIMADA_EAL
  const wsClimada = XLSX.utils.aoa_to_sheet(buildClimadaSheet(drivers, meta));
  wsClimada["!cols"] = colW([22, 10, 40, 16, 16, 16, 16, 40]);
  XLSX.utils.book_append_sheet(wb, wsClimada, "CLIMADA_EAL");

  // ④~⑦ SSP별 통합 (SSP5-8.5 → SSP1-2.6 순)
  for (const ssp of [...SSP_ORDER].reverse()) {
    const ws = XLSX.utils.aoa_to_sheet(buildSspSheet(drivers, ssp));
    ws["!cols"] = colW([10, 18, 16, 8, ...PERIOD_KEYS.map(() => 15)]);
    XLSX.utils.book_append_sheet(wb, ws, SSP_LABELS[ssp]);
  }

  // ⑧ 전체_원시데이터
  const wsAll = XLSX.utils.aoa_to_sheet(buildAllDataRows(drivers));
  wsAll["!cols"] = colW([10, 10, 16, 18, 18, 8, 14]);
  XLSX.utils.book_append_sheet(wb, wsAll, "전체_원시데이터");

  // ⑨ 분석_정보
  const wsInfo = XLSX.utils.aoa_to_sheet(buildInfoRows(meta));
  wsInfo["!cols"] = colW([20, 30, 45, 50]);
  XLSX.utils.book_append_sheet(wb, wsInfo, "분석_정보");

  // 파일명
  const latStr = meta.lat.toFixed(2).replace(".", "p");
  const lonStr = meta.lon.toFixed(2).replace(".", "p");
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  XLSX.writeFile(wb, `InnergenCS_${meta.tier}_${latStr}_${lonStr}_${dateStr}.xlsx`);
}

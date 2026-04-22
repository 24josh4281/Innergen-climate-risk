/**
 * excel_export.js — 데이터소스별 분리 Excel 다운로드
 *
 * 시트 구성 (13개):
 *   1. CMIP6_시나리오   — CMIP6 7개 기후변수 × 4SSP × 5시점 피벗
 *   2. ETCCDI_극값지수  — 13개 ETCCDI 극값 지수 × 4SSP × 5시점 피벗
 *   3. PhyRisk_위험도   — OS-Climate 18개 위험 유형 점수
 *   4. CLIMADA_EAL      — CLIMADA 연간예상손실
 *   5. Aqueduct_수자원  — WRI Aqueduct 4.0 수자원 위험 6종
 *   6. IBTrACS_태풍     — 역사적 태풍 통계 3종 (1980-2023)
 *   7. PSHA_지진        — GEM PSHA 지진위험 2종
 *   8. SSP5-8.5         — 전체 동인 통합 (카테고리 구분)
 *   9. SSP3-7.0
 *  10. SSP2-4.5
 *  11. SSP1-2.6
 *  12. 전체_원시데이터  — long 포맷
 *  13. 분석_정보        — 메타데이터 + 출처
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
  if (CMIP6_KEYS.includes(dk))      return "CMIP6";
  if (ETCCDI_KEYS.includes(dk))     return "ETCCDI";
  if (PHYSRISK_KEYS.includes(dk))   return "PhyRisk";
  if (CLIMADA_KEYS.includes(dk))    return "CLIMADA";
  if (AQUEDUCT_KEYS.includes(dk))   return "Aqueduct";
  if (IBTRACS_KEYS.includes(dk))    return "IBTrACS";
  if (PSHA_KEYS.includes(dk))       return "PSHA";
  if (CCKP_KEYS.includes(dk))       return "CCKP";
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

  // 행2: [변수, 단위, 설명, 현재, 단기, 중기, 장기, 장기+, 현재, ...]
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
  rows.push(["※ 현재 API는 SSP2-4.5/2050년 단일 기준값을 전 시점에 동일 적용"]);
  rows.push([]);

  // 2-단 헤더 (CMIP6 시트와 동일 구조)
  const ssp_span_row = ["위험 유형", "단위", "RAG(SSP2-4.5 중기)"];
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

    // RAG는 SSP2-4.5 중기 기준
    const refVal = getVal(((drivers["ssp245"] || {})["mid"] || {})[dk]);
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

  const base585 = (drivers["ssp245"] || {})["baseline"] || {};
  const hasCLIMADA = CLIMADA_KEYS.some(k => base585[k] !== undefined);

  if (hasCLIMADA) {
    // T2/T3: entries exist (값은 null, note 있음)
    rows.push(["CLIMADA 변수", "단위", "설명", "SSP1-2.6", "SSP2-4.5", "SSP3-7.0", "SSP5-8.5", "비고"]);
    rows.push(["", "", "", "(각 열: 현재~장기+ 평균 / 현재 단일값)", "", "", "", ""]);

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
    rows.push(["태풍 (TC) EAL",    "오프라인 포트폴리오 EAL 분석 완료 (별도 파일 참조)"]);
    rows.push(["홍수 (Flood) EAL", "오프라인 포트폴리오 EAL 분석 완료 (별도 파일 참조)"]);
    rows.push(["지진 (EQ) EAL",    "GEM PSHA 기반 분석 완료"]);
    rows.push(["산불 (Wildfire) EAL", "오프라인 EAL 분석 완료 (별도 파일 참조)"]);
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

  rows.push([]);

  // Aqueduct 그룹 (정적 — 모든 시점 동일)
  rows.push(["── Aqueduct 4.0 수자원 위험 ──"]);
  for (const dk of AQUEDUCT_KEYS) {
    const meta = DRIVER_META[dk] || { label: dk, unit: "0-5" };
    const val = fmt(getVal((sspData["baseline"] || {})[dk]));
    rows.push(["Aqueduct", meta.label, dk, meta.unit, val, val, val, val, val]);
  }

  rows.push([]);

  // IBTrACS 그룹 (역사적 — 모든 시점 동일)
  rows.push(["── IBTrACS 태풍 통계 (1980-2023) ──"]);
  for (const dk of IBTRACS_KEYS) {
    const meta = DRIVER_META[dk] || { label: dk, unit: "-" };
    const val = fmt(getVal((sspData["baseline"] || {})[dk]));
    rows.push(["IBTrACS", meta.label, dk, meta.unit, val, val, val, val, val]);
  }

  rows.push([]);

  // PSHA 그룹 (정적)
  rows.push(["── GEM PSHA 지진위험 ──"]);
  for (const dk of PSHA_KEYS) {
    const meta = DRIVER_META[dk] || { label: dk, unit: "g" };
    const val = fmt(getVal((sspData["baseline"] || {})[dk]));
    rows.push(["PSHA", meta.label, dk, meta.unit, val, val, val, val, val]);
  }

  rows.push([]);

  // CCKP 그룹 (SSP별 시계열)
  rows.push(["── World Bank CCKP 에너지·극한열 (0.25°) ──"]);
  for (const dk of CCKP_KEYS) {
    const meta = DRIVER_META[dk] || { label: dk, unit: "-" };
    const vals = PERIOD_KEYS.map(p => fmt(getVal((sspData[p] || {})[dk])));
    rows.push(["CCKP", meta.label, dk, meta.unit, ...vals]);
  }

  return rows;
}

// ── 시트 5: Aqueduct_수자원 ──────────────────────────────────────────────────

function buildAqueductSheet(drivers) {
  const rows = [];
  rows.push(["WRI Aqueduct 4.0 — 수자원 위험 지수 (0~5 스케일)"]);
  rows.push(["출처: World Resources Institute Aqueduct 4.0 (2023)"]);
  rows.push(["※ 기준: 0=Low, 1=Low-Med, 2=Med, 3=Med-High, 4=High, 5=Ext.High"]);
  rows.push([]);
  rows.push(["변수키", "변수명", "단위", "값 (정적)", "RAG", "설명"]);

  const base = (drivers["ssp245"] || {})["baseline"] || {};
  const AQ_DESC = {
    aq_water_stress:      "연평균 취수량 / 가용수량 비율 (0~5)",
    aq_river_flood:       "하천범람 노출 위험도 (0~5)",
    aq_coastal_flood:     "해안침수 노출 위험도 (0~5)",
    aq_drought:           "가뭄 노출 빈도 위험도 (0~5)",
    aq_interann_var:      "연간 강수 변동성 (0~5)",
    aq_water_stress_2050: "SSP3 2050년 미래 취수 스트레스 전망 (0~5)",
  };
  for (const dk of AQUEDUCT_KEYS) {
    const meta = DRIVER_META[dk] || { label: dk, unit: "0-5" };
    const val = getVal(base[dk]);
    rows.push([dk, meta.label, meta.unit, fmt(val), ragLabel(dk, val), AQ_DESC[dk] || ""]);
  }
  return rows;
}

// ── 시트 6: IBTrACS_태풍 ────────────────────────────────────────────────────

function buildIbtracSheet(drivers) {
  const rows = [];
  rows.push(["IBTrACS v04 — 역사적 태풍 통계 (1980-2023)"]);
  rows.push(["출처: NOAA International Best Track Archive for Climate Stewardship (IBTrACS)"]);
  rows.push(["※ 반경 300km 내 경로 통계 기준"]);
  rows.push([]);
  rows.push(["변수키", "변수명", "단위", "값 (역사적)", "RAG", "설명"]);

  const base = (drivers["ssp245"] || {})["baseline"] || {};
  const IB_DESC = {
    tc_annual_freq:  "연평균 태풍 통과 횟수 (반경 300km, 1980-2023)",
    tc_max_wind_kt:  "역사 최대풍속 극값 (kt, Tropical Storm 이상)",
    tc_cat3_count:   "Category 3 이상 태풍 총 통과 횟수",
  };
  for (const dk of IBTRACS_KEYS) {
    const meta = DRIVER_META[dk] || { label: dk, unit: "-" };
    const val = getVal(base[dk]);
    rows.push([dk, meta.label, meta.unit, fmt(val), ragLabel(dk, val), IB_DESC[dk] || ""]);
  }
  return rows;
}

// ── 시트 7: PSHA_지진 ────────────────────────────────────────────────────────

function buildPshaSheet(drivers) {
  const rows = [];
  rows.push(["GEM PSHA — 지진 위험도 (최대지반가속도, g 단위)"]);
  rows.push(["출처: GEM Global Seismic Hazard Assessment Programme / 각국 국가지진위험지도"]);
  rows.push([]);
  rows.push(["변수키", "변수명", "단위", "값 (정적)", "RAG", "설명"]);

  const base = (drivers["ssp245"] || {})["baseline"] || {};
  const PSHA_DESC = {
    psha_pga_475:   "재현주기 475년 (연초과확률 10%/50yr) PGA",
    psha_pga_2475:  "재현주기 2475년 (연초과확률 2%/50yr) PGA",
  };
  for (const dk of PSHA_KEYS) {
    const meta = DRIVER_META[dk] || { label: dk, unit: "g" };
    const val = getVal(base[dk]);
    rows.push([dk, meta.label, meta.unit, fmt(val), ragLabel(dk, val), PSHA_DESC[dk] || ""]);
  }
  return rows;
}

// ── 시트 12: 전체_원시데이터 ─────────────────────────────────────────────────

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
      for (const dk of CMIP6_KEYS) {
        const m = allMeta(dk);
        rows.push(["CMIP6", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "-", fmt(getVal(periodData[dk]))]);
      }
      for (const dk of ETCCDI_KEYS) {
        const m = allMeta(dk);
        rows.push(["ETCCDI", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "-", fmt(getVal(periodData[dk]))]);
      }
      for (const dk of PHYSRISK_KEYS) {
        const m = allMeta(dk);
        rows.push(["PhyRisk", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "score", fmt(getVal(periodData[dk]))]);
      }
      for (const dk of CCKP_KEYS) {
        const m = allMeta(dk);
        rows.push(["CCKP", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "-", fmt(getVal(periodData[dk]))]);
      }
      for (const dk of CLIMADA_KEYS) {
        if (periodData[dk] === undefined) continue;
        const m = allMeta(dk);
        const note = getNote(periodData[dk]);
        rows.push(["CLIMADA", SSP_LABELS[ssp], PERIOD_LABEL_MAP[p], dk, m.label, m.unit || "USD/yr",
          note || fmt(getVal(periodData[dk]))]);
      }
      // 정적 변수는 baseline만 기록 (중복 방지)
      if (p === "baseline") {
        for (const dk of AQUEDUCT_KEYS) {
          const m = allMeta(dk);
          rows.push(["Aqueduct", "공통", "정적", dk, m.label, m.unit || "0-5", fmt(getVal(periodData[dk]))]);
        }
        for (const dk of IBTRACS_KEYS) {
          const m = allMeta(dk);
          rows.push(["IBTrACS", "공통", "역사적", dk, m.label, m.unit || "-", fmt(getVal(periodData[dk]))]);
        }
        for (const dk of PSHA_KEYS) {
          const m = allMeta(dk);
          rows.push(["PSHA", "공통", "정적", dk, m.label, m.unit || "g", fmt(getVal(periodData[dk]))]);
        }
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
      "heat_stress / flood_risk / drought_risk 등 18개",
      "0~100점 위험도 점수 (원시값 물리 단위 → 정규화 환산)",
    ],
    [
      "CLIMADA",
      "CLIMADA HDF5 / GEM PSHA",
      "TC_EAL / Flood_EAL / EQ_EAL / Wildfire_EAL",
      "T1 사전계산 EAL / T2·T3 서버 제약으로 N/A",
    ],
    [
      "Aqueduct",
      "WRI Aqueduct 4.0 (2023)",
      "aq_water_stress / aq_river_flood / aq_coastal_flood 등 6개",
      "0~5 수자원 위험 지수 (baseline + SSP3 2050 전망)",
    ],
    [
      "IBTrACS",
      "NOAA IBTrACS v04r01",
      "tc_annual_freq / tc_max_wind_kt / tc_cat3_count",
      "역사적 태풍 통계 (1980-2023, 반경 300km)",
    ],
    [
      "PSHA",
      "GEM Global Seismic Hazard Assessment Programme",
      "psha_pga_475 / psha_pga_2475",
      "재현주기 475/2475년 최대지반가속도 (g)",
    ],
    [],
    ["시트명", "내용"],
    ["CMIP6_시나리오",    "CMIP6 7개 변수 × 4SSP × 5시점 피벗 테이블"],
    ["ETCCDI_극값지수",   "ETCCDI 13개 기후극값 × 4SSP × 5시점 피벗"],
    ["PhyRisk_위험도",    "OS-Climate 18개 위험유형 × 4SSP × 5시점 피벗"],
    ["CLIMADA_EAL",       "연간예상손실 (T1 오프라인 참조 / T2-T3 N/A)"],
    ["Aqueduct_수자원",   "WRI Aqueduct 4.0 수자원 위험 6종 (정적)"],
    ["IBTrACS_태풍",      "역사적 태풍 통계 3종 (1980-2023)"],
    ["PSHA_지진",         "GEM PSHA 지진위험 2종 (정적)"],
    ["SSP5-8.5 ~ SSP1-2.6", "SSP별 전체 동인 통합 (53개 변수 + 정적)"],
    ["전체_원시데이터",   "카테고리·SSP·시점별 long 포맷 원시값"],
    ["분석_정보",         "본 시트 — 메타데이터 및 데이터소스 출처"],
  ];
}

// ── 리스크 해석 시트 ─────────────────────────────────────────────────────────

function buildInterpretSheet(apiResult) {
  const interp = apiResult.interpretation || {};
  const mat    = interp.materiality || {};
  const tcfd   = interp.tcfd || {};
  const risks  = interp.top_risks || [];

  const ssp    = interp.evaluated_ssp    || "ssp245";
  const period = interp.evaluated_period || "mid";
  const sspLbl = (SSP_LABELS || {})[ssp]        || ssp;
  const perLbl = (PERIOD_LABEL_MAP || {})[period] || period;

  const rows = [];

  // ── 섹션 1: 물질성 평가 요약 ────────────────────────────────
  rows.push(["리스크 해석 — 국제기준 기반 (IPCC AR6 · WMO · TCFD · ISSB S2 · WRI Aqueduct)"]);
  rows.push([`평가 시나리오: ${sspLbl}  |  평가 시점: ${perLbl}`]);
  rows.push([]);
  rows.push(["[섹션 1] 물질성 평가 요약"]);
  rows.push(["항목", "내용"]);
  rows.push(["물질성 수준 (Materiality Level)", mat.level || "N/A"]);
  rows.push(["ISSB S2 (IFRS S2) 참조", mat.issb_s2_note || ""]);
  rows.push(["CDP 참조", mat.cdp_ref || ""]);
  rows.push(["급성 리스크 고위험 항목 수", mat.acute_red ?? "N/A"]);
  rows.push(["만성 리스크 고위험 항목 수", mat.chronic_red ?? "N/A"]);
  rows.push(["전체 고위험 항목 수 (HIGH 이상)", mat.total_red ?? "N/A"]);
  rows.push([]);

  // TCFD 분류
  rows.push(["TCFD 분류 — 급성 리스크 (Acute)", (tcfd.acute || []).join(", ")]);
  rows.push(["TCFD 분류 — 만성 리스크 (Chronic)", (tcfd.chronic || []).join(", ")]);
  rows.push([]);

  // ── 섹션 2: 핵심 리스크 항목 ────────────────────────────────
  rows.push(["[섹션 2] 핵심 고위험 항목 (HIGH 이상)"]);
  rows.push([
    "변수키", "변수명", "값", "단위", "등급", "TCFD 분류",
    "임계값(기준값)", "출처 기관", "출처 문서",
    "수치 맥락", "비즈니스 영향(1)", "비즈니스 영향(2)", "비즈니스 영향(3)",
  ]);

  const highRisks = risks.filter(r => ["HIGH", "VERY_HIGH"].includes(r.level));
  for (const r of highRisks) {
    const impacts = r.business_impacts || [];
    rows.push([
      r.var,
      r.label,
      r.value,
      r.unit,
      r.level,
      r.tcfd_type === "acute" ? "급성" : r.tcfd_type === "chronic" ? "만성" : "기타",
      r.threshold_min != null ? r.threshold_min : "",
      r.threshold_inst || "",
      r.threshold_source || "",
      r.context || "",
      impacts[0] || "",
      impacts[1] || "",
      impacts[2] || "",
    ]);
  }

  if (!highRisks.length) {
    rows.push(["(현 시나리오 기준 HIGH 이상 항목 없음)"]);
  }
  rows.push([]);

  // ── 섹션 3: AI 내러티브 ──────────────────────────────────────
  rows.push(["[섹션 3] 공시용 AI 내러티브 (ISSB S2 / CDP 초안)"]);
  rows.push(["모델: claude-haiku-4-5-20251001  |  생성 기준: TCFD 급성·만성 분류 포함"]);
  rows.push(["※ AI 생성 초안입니다. 실제 공시 전 ESG 전문가 검토가 필요합니다."]);
  rows.push(["내러티브 텍스트", "(웹 UI에서 먼저 조회 후 복사 — Excel 다운로드 시점에는 실시간 생성 미포함)"]);
  rows.push([]);
  rows.push(["참조 프레임워크", "IPCC AR6 (2021-2022), WMO Extreme Weather Guidelines (2020)"]);
  rows.push(["", "TCFD Recommendations (2017), ISSB S2 (IFRS S2, 2023)"]);
  rows.push(["", "WRI Aqueduct 4.0 (2023), ISO 7933 (열 스트레스), GEM PSHA (2018)"]);

  return rows;
}

// ── 메인 export ───────────────────────────────────────────────────────────────

function exportExcel(apiResult) {
  const { meta, drivers } = apiResult;
  const wb = XLSX.utils.book_new();

  const colW = (widths) => widths.map(w => ({ wch: w }));

  // ⓪ 리스크해석 (첫 번째 시트 — 공시 담당자가 바로 볼 수 있도록)
  const wsInterp = XLSX.utils.aoa_to_sheet(buildInterpretSheet(apiResult));
  wsInterp["!cols"] = colW([20, 60, 12, 10, 12, 8, 12, 20, 55, 40, 55, 55, 55]);
  XLSX.utils.book_append_sheet(wb, wsInterp, "리스크해석");

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

  // ⑤ Aqueduct_수자원
  const wsAq = XLSX.utils.aoa_to_sheet(buildAqueductSheet(drivers));
  wsAq["!cols"] = colW([24, 28, 6, 10, 8, 50]);
  XLSX.utils.book_append_sheet(wb, wsAq, "Aqueduct_수자원");

  // ⑥ IBTrACS_태풍
  const wsIbt = XLSX.utils.aoa_to_sheet(buildIbtracSheet(drivers));
  wsIbt["!cols"] = colW([18, 22, 8, 12, 8, 50]);
  XLSX.utils.book_append_sheet(wb, wsIbt, "IBTrACS_태풍");

  // ⑦ PSHA_지진
  const wsPsha = XLSX.utils.aoa_to_sheet(buildPshaSheet(drivers));
  wsPsha["!cols"] = colW([16, 26, 4, 10, 8, 50]);
  XLSX.utils.book_append_sheet(wb, wsPsha, "PSHA_지진");

  // ⑧~⑪ SSP별 통합 (SSP5-8.5 → SSP1-2.6 순)
  for (const ssp of [...SSP_ORDER].reverse()) {
    const ws = XLSX.utils.aoa_to_sheet(buildSspSheet(drivers, ssp));
    ws["!cols"] = colW([10, 28, 24, 8, ...PERIOD_KEYS.map(() => 15)]);
    XLSX.utils.book_append_sheet(wb, ws, SSP_LABELS[ssp]);
  }

  // ⑫ 전체_원시데이터
  const wsAll = XLSX.utils.aoa_to_sheet(buildAllDataRows(drivers));
  wsAll["!cols"] = colW([10, 10, 10, 24, 28, 8, 14]);
  XLSX.utils.book_append_sheet(wb, wsAll, "전체_원시데이터");

  // ⑬ 분석_정보
  const wsInfo = XLSX.utils.aoa_to_sheet(buildInfoRows(meta));
  wsInfo["!cols"] = colW([20, 30, 45, 55]);
  XLSX.utils.book_append_sheet(wb, wsInfo, "분석_정보");

  // 파일명
  const latStr = meta.lat.toFixed(2).replace(".", "p");
  const lonStr = meta.lon.toFixed(2).replace(".", "p");
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  XLSX.writeFile(wb, `InnergenCS_${meta.tier}_${latStr}_${lonStr}_${dateStr}.xlsx`);
}

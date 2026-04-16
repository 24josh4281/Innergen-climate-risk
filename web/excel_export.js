/**
 * excel_export.js — SheetJS Excel 다운로드
 * 4 SSP 시트 + All_Data + Tier_Info
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

function driverRows(drivers, ssp) {
  const sspData = drivers[ssp] || {};
  const periods = Object.keys(PERIOD_LABEL_MAP);
  const drivers_keys = Object.keys(DRIVER_META);

  // 헤더
  const header = ["기후 동인", "단위", ...periods.map(p => PERIOD_LABEL_MAP[p])];
  const rows = [header];

  for (const dk of drivers_keys) {
    const meta = DRIVER_META[dk];
    const vals = periods.map(p => {
      const entry = (sspData[p] || {})[dk];
      if (entry === null || entry === undefined) return "N/A";
      const v = typeof entry === "object" ? entry.value : entry;
      return v === null ? "N/A" : (typeof v === "number" ? Math.round(v * 100) / 100 : v);
    });
    rows.push([meta.label, meta.unit || "-", ...vals]);
  }

  return rows;
}

function allDataRows(drivers) {
  const rows = [["SSP", "Period", "Driver", "Value", "Source"]];
  for (const [ssp, sspData] of Object.entries(drivers)) {
    for (const [period, periodData] of Object.entries(sspData)) {
      for (const [dk, entry] of Object.entries(periodData)) {
        const val = typeof entry === "object" ? entry.value : entry;
        const src = typeof entry === "object" ? (entry.source || "") : "";
        rows.push([ssp, period, dk, val === null ? "N/A" : val, src]);
      }
    }
  }
  return rows;
}

/**
 * Excel 파일 생성 및 다운로드
 * @param {Object} apiResult - {meta, drivers}
 */
function exportExcel(apiResult) {
  const { meta, drivers } = apiResult;
  const wb = XLSX.utils.book_new();

  // 1. SSP별 시트
  for (const [ssp, sheetName] of Object.entries(SSP_SHEET_NAMES)) {
    const rows = driverRows(drivers, ssp);
    const ws = XLSX.utils.aoa_to_sheet(rows);
    // 헤더 스타일 (SheetJS Community에서 폰트 굵게는 제한적)
    ws["!cols"] = [{ wch: 22 }, { wch: 10 }, ...Object.keys(PERIOD_LABEL_MAP).map(() => ({ wch: 16 }))];
    XLSX.utils.book_append_sheet(wb, ws, sheetName);
  }

  // 2. All_Data 시트
  const allRows = allDataRows(drivers);
  const wsAll = XLSX.utils.aoa_to_sheet(allRows);
  wsAll["!cols"] = [{ wch: 12 }, { wch: 14 }, { wch: 22 }, { wch: 12 }, { wch: 20 }];
  XLSX.utils.book_append_sheet(wb, wsAll, "All_Data");

  // 3. Tier_Info 시트
  const tierRows = [
    ["항목", "값"],
    ["위도 (Lat)", meta.lat],
    ["경도 (Lon)", meta.lon],
    ["국가", meta.country],
    ["데이터 Tier", meta.tier],
    ["Tier 설명", meta.tier_label],
    ["매칭 T1 사이트", meta.matched_t1_site || "없음"],
    ["T1까지 거리 (km)", meta.distance_to_nearest_t1_km],
    ["출력 일시", new Date().toLocaleString("ko-KR")],
  ];
  const wsTier = XLSX.utils.aoa_to_sheet(tierRows);
  wsTier["!cols"] = [{ wch: 22 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(wb, wsTier, "Tier_Info");

  // 파일명
  const latStr = meta.lat.toFixed(2).replace(".", "p");
  const lonStr = meta.lon.toFixed(2).replace(".", "p");
  const filename = `ClimateRisk_${meta.tier}_${latStr}_${lonStr}.xlsx`;

  XLSX.writeFile(wb, filename);
}

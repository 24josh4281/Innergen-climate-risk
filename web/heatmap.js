/**
 * heatmap.js — RAG 히트맵 렌더링 (38동인 × 9시점)
 */

const PERIOD_LABELS = {
  baseline: "현재",
  near:     "2025-34",
  mid:      "2045-54",
  far:      "2075-84",
  end:      "2090-99",
};

const DRIVER_META = {
  // CMIP6 기온/강수
  tasmax:   { label: "최고기온",    unit: "°C",      rag: (v) => v > 38 ? "red" : v > 33 ? "amber" : "green" },
  tasmin:   { label: "최저기온",    unit: "°C",      rag: (v) => v < -15 ? "red" : v < -5 ? "amber" : "green" },
  tas:      { label: "평균기온",    unit: "°C",      rag: (v) => v > 30 ? "red" : v > 25 ? "amber" : "green" },
  pr:       { label: "강수량",      unit: "mm/day",  rag: (v) => v > 10 ? "red" : v > 6 ? "amber" : "green" },
  prsn:     { label: "강설량",      unit: "mm/day",  rag: (v) => v > 5 ? "red" : v > 2 ? "amber" : "green" },
  sfcWind:  { label: "지표풍속",    unit: "m/s",     rag: (v) => v > 10 ? "red" : v > 7 ? "amber" : "green" },
  evspsbl:  { label: "증발산",      unit: "mm/day",  rag: (v) => v > 5 ? "red" : v > 3 ? "amber" : "green" },
  // PhyRisk (0-100 스코어)
  flood_risk:     { label: "홍수 위험",       unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  drought_risk:   { label: "가뭄 위험",       unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  heat_stress:    { label: "열 스트레스",     unit: "score", rag: (v) => v > 65 ? "red" : v > 40 ? "amber" : "green" },
  water_stress:   { label: "수자원 스트레스", unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  cyclone_risk:   { label: "사이클론 위험",   unit: "score", rag: (v) => v > 55 ? "red" : v > 30 ? "amber" : "green" },
  wildfire_risk:  { label: "산불 위험",       unit: "score", rag: (v) => v > 50 ? "red" : v > 30 ? "amber" : "green" },
  sea_level_rise: { label: "해수면 상승",     unit: "score", rag: (v) => v > 55 ? "red" : v > 30 ? "amber" : "green" },
  storm_surge:    { label: "폭풍 해일",       unit: "score", rag: (v) => v > 50 ? "red" : v > 30 ? "amber" : "green" },
  earthquake_risk:{ label: "지진 위험",       unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
  landslide_risk: { label: "산사태 위험",     unit: "score", rag: (v) => v > 45 ? "red" : v > 25 ? "amber" : "green" },
  coastal_flood:  { label: "해안 침수",       unit: "score", rag: (v) => v > 50 ? "red" : v > 30 ? "amber" : "green" },
  pluvial_flood:  { label: "도시 홍수",       unit: "score", rag: (v) => v > 55 ? "red" : v > 30 ? "amber" : "green" },
  river_flood:    { label: "하천 홍수",       unit: "score", rag: (v) => v > 60 ? "red" : v > 35 ? "amber" : "green" },
};

const DRIVER_KEYS = Object.keys(DRIVER_META);
const PERIOD_KEYS = ["baseline", "near", "mid", "far", "end"];

/**
 * RAG 클래스 반환
 */
function ragClass(driverKey, value) {
  if (value === null || value === undefined) return "cell-na";
  const meta = DRIVER_META[driverKey];
  if (!meta) return "cell-na";
  const color = meta.rag(value);
  return `cell-${color}`;
}

/**
 * 값 포맷팅
 */
function formatVal(driverKey, value) {
  if (value === null || value === undefined) return "N/A";
  return typeof value === "number" ? value.toFixed(1) : value;
}

/**
 * 히트맵 렌더링
 * @param {Object} drivers - {ssp: {period: {driver: {value, source}}}}
 * @param {string} ssp - 현재 SSP 탭
 */
function renderHeatmap(drivers, ssp) {
  const head = document.getElementById("heatmap-head");
  const body = document.getElementById("heatmap-body");
  if (!head || !body) return;

  const sspData = drivers[ssp] || {};

  // 헤더
  head.innerHTML = `
    <tr>
      <th style="text-align:left; width:140px;">기후 동인</th>
      ${PERIOD_KEYS.map(p => `<th>${PERIOD_LABELS[p] || p}</th>`).join("")}
    </tr>
  `;

  // 바디
  let rows = "";
  for (const driverKey of DRIVER_KEYS) {
    const meta = DRIVER_META[driverKey];
    const cells = PERIOD_KEYS.map(period => {
      const periodData = sspData[period] || {};
      const entry = periodData[driverKey];
      const val = entry ? (typeof entry === "object" ? entry.value : entry) : null;
      const cls = ragClass(driverKey, val);
      return `<td class="${cls}">${formatVal(driverKey, val)}</td>`;
    }).join("");

    rows += `
      <tr>
        <td class="driver-label">${meta.label}</td>
        ${cells}
      </tr>
    `;
  }
  body.innerHTML = rows;
}

/**
 * SSP 탭 전환 이벤트 바인딩
 */
function bindHeatmapTabs(drivers) {
  document.querySelectorAll("#heatmap-ssp-tabs .ssp-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#heatmap-ssp-tabs .ssp-tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      renderHeatmap(drivers, btn.dataset.ssp);
    });
  });
}

/**
 * Top 5 고위험 항목 추출 (SSP5-8.5 말기 기준)
 */
function getTop5Risks(drivers) {
  const endData = (drivers["ssp585"] || {})["end"] || {};
  const items = [];

  for (const [key, meta] of Object.entries(DRIVER_META)) {
    const entry = endData[key];
    const val = entry ? (typeof entry === "object" ? entry.value : entry) : null;
    if (val === null || val === undefined) continue;
    const rag = meta.rag(val);
    if (rag === "red") {
      items.push({ key, label: meta.label, val, rag });
    }
  }

  // 값 내림차순 정렬
  items.sort((a, b) => b.val - a.val);
  return items.slice(0, 5);
}

/**
 * Top 5 카드 렌더링
 */
function renderTop5(drivers) {
  const list = document.getElementById("top5-list");
  if (!list) return;

  const items = getTop5Risks(drivers);

  if (items.length === 0) {
    list.innerHTML = `<p style="color: var(--text-dim); font-size:13px;">SSP5-8.5 말기 기준 고위험(RED) 항목이 없습니다.</p>`;
    return;
  }

  list.innerHTML = items.map((item, i) => `
    <div class="top5-item">
      <span class="top5-rank">#${i + 1}</span>
      <span class="top5-label">${item.label}</span>
      <span class="top5-val">${item.val.toFixed(1)}</span>
    </div>
  `).join("");
}

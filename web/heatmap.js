/**
 * heatmap.js — RAG 히트맵 렌더링 (49동인 × 9시점)
 * 상수: PERIOD_LABELS, PERIOD_KEYS, DRIVER_META, DRIVER_KEYS, SSP_* → constants.js
 */

// 카테고리별 드라이버 그룹 (히트맵 구분선용)
const DRIVER_GROUPS = [
  { label: "CMIP6 기후변수", keys: ["tasmax","tasmin","tas","pr","prsn","sfcWind","evspsbl"] },
  { label: "ETCCDI 극값 — 열", keys: ["etccdi_txx","etccdi_tnn","etccdi_su","etccdi_tr","etccdi_fd","etccdi_wsdi","etccdi_wbgt"] },
  { label: "ETCCDI 극값 — 강수", keys: ["etccdi_cdd","etccdi_cwd","etccdi_rx1day","etccdi_rx5day","etccdi_r95p","etccdi_sdii"] },
  { label: "PhyRisk — 열·노동", keys: ["heat_stress","extreme_heat_35c","work_loss_high","work_loss_medium","heat_degree_days"] },
  { label: "PhyRisk — 수자원·가뭄", keys: ["water_stress","water_depletion","drought_risk"] },
  { label: "PhyRisk — 홍수·태풍·기타", keys: ["flood_risk","river_flood","coastal_flood","pluvial_flood","cyclone_risk","storm_surge","sea_level_rise","wildfire_risk","earthquake_risk","landslide_risk"] },
  { label: "Aqueduct 수자원", keys: ["aq_water_stress","aq_river_flood","aq_coastal_flood","aq_drought","aq_interann_var","aq_water_stress_2050"] },
  { label: "IBTrACS 태풍", keys: ["tc_annual_freq","tc_max_wind_kt","tc_cat3_count"] },
  { label: "PSHA 지진재해", keys: ["psha_pga_475","psha_pga_2475"] },
  { label: "CCKP — 에너지·극한열 (World Bank 0.25°)", keys: ["cckp_hi35","cckp_hd40","cckp_tr26","cckp_cdd65","cckp_hdd65"] },
  { label: "CCKP — ETCCDI 교차검증 (온도 계열)", keys: ["cckp_csdi","cckp_wsdi","cckp_cdd_consec"] },
];

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

  // 바디 (카테고리 구분선 포함)
  const colCount = PERIOD_KEYS.length + 1;
  let rows = "";
  for (const group of DRIVER_GROUPS) {
    rows += `<tr class="heatmap-group-header"><td colspan="${colCount}">${group.label}</td></tr>`;
    for (const driverKey of group.keys) {
      const meta = DRIVER_META[driverKey];
      if (!meta) continue;
      const cells = PERIOD_KEYS.map(period => {
        const periodData = sspData[period] || {};
        const entry = periodData[driverKey];
        const val = entry ? (typeof entry === "object" ? entry.value : entry) : null;
        const cls = ragClass(driverKey, val);
        return `<td class="${cls}">${formatVal(driverKey, val)}</td>`;
      }).join("");

      rows += `
        <tr class="driver-row" data-driver-key="${driverKey}" role="button" tabindex="0" title="${meta.label} 시계열 보기">
          <td class="driver-label">${meta.label}</td>
          ${cells}
        </tr>
      `;
    }
  }
  body.innerHTML = rows;
}

/**
 * 히트맵 행 클릭 → 시계열 차트 연동
 */
function bindHeatmapRowClick(drivers) {
  const body = document.getElementById("heatmap-body");
  if (!body) return;

  body.addEventListener("click", (e) => {
    const row = e.target.closest(".driver-row");
    if (!row) return;
    const key = row.dataset.driverKey;
    if (!key) return;

    // 활성 행 강조
    body.querySelectorAll(".driver-row.active-row").forEach(r => r.classList.remove("active-row"));
    row.classList.add("active-row");

    // select 동기화
    const sel = document.getElementById("chart-var-select");
    if (sel) sel.value = key;

    // 차트 재렌더
    renderTimeseriesChart(drivers, key);

    // 차트 영역으로 스크롤
    const chartCard = document.querySelector(".card-title + div #timeseries-chart")?.closest(".card");
    const chartEl = document.getElementById("timeseries-chart");
    if (chartEl) {
      chartEl.closest(".card")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  });

  // 키보드 접근성
  body.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      e.target.closest(".driver-row")?.click();
    }
  });
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
 * Top 5 고위험 항목 추출 (SSP2-4.5 중기 기준)
 */
function getTop5Risks(drivers) {
  const endData = (drivers["ssp245"] || {})["mid"] || {};
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
    list.innerHTML = `<p style="color: var(--text-dim); font-size:13px;">SSP2-4.5 중기 기준 고위험(RED) 항목이 없습니다.</p>`;
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

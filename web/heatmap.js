/**
 * heatmap.js — RAG 히트맵 렌더링 (38동인 × 9시점)
 * 상수: PERIOD_LABELS, PERIOD_KEYS, DRIVER_META, DRIVER_KEYS, SSP_* → constants.js
 */

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

/**
 * chart_render.js — SSP 4선 시계열 차트 (Chart.js)
 */

let _chart = null;

const SSP_COLORS = {
  ssp126: { border: "#00C896", bg: "rgba(0,200,150,0.12)" },
  ssp245: { border: "#00B4D8", bg: "rgba(0,180,216,0.12)" },
  ssp370: { border: "#F59E0B", bg: "rgba(245,158,11,0.12)" },
  ssp585: { border: "#FF4D6D", bg: "rgba(255,77,109,0.12)" },
};

const SSP_LABELS = {
  ssp126: "SSP1-2.6",
  ssp245: "SSP2-4.5",
  ssp370: "SSP3-7.0",
  ssp585: "SSP5-8.5",
};

const PERIOD_MIDPOINTS = ["2020", "2030", "2050", "2080", "2095"];
// PERIOD_KEYS는 heatmap.js에서 전역 선언됨 — 여기서 재선언하지 않음

function extractSeriesValue(drivers, ssp, period, varKey) {
  const entry = ((drivers[ssp] || {})[period] || {})[varKey];
  if (entry === null || entry === undefined) return null;
  if (typeof entry === "object") return entry.value;
  return entry;
}

/**
 * 시계열 차트 렌더링
 * @param {Object} drivers - {ssp: {period: {driver: {value, source}}}}
 * @param {string} varKey - 표시할 변수 키
 */
function renderTimeseriesChart(drivers, varKey) {
  const ctx = document.getElementById("timeseries-chart");
  if (!ctx) return;

  // 기존 차트 파괴
  if (_chart) {
    _chart.destroy();
    _chart = null;
  }

  const datasets = Object.entries(SSP_COLORS).map(([ssp, colors]) => {
    const data = PERIOD_KEYS.map(period => extractSeriesValue(drivers, ssp, period, varKey));
    return {
      label: SSP_LABELS[ssp],
      data,
      borderColor: colors.border,
      backgroundColor: colors.bg,
      borderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      tension: 0.3,
      fill: false,
    };
  });

  _chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: PERIOD_MIDPOINTS,
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: {
            color: "#94a3b8",
            font: { size: 11 },
            boxWidth: 12,
          },
        },
        tooltip: {
          backgroundColor: "#112240",
          borderColor: "#1E3A5F",
          borderWidth: 1,
          titleColor: "#EEF2FF",
          bodyColor: "#8DAABF",
          callbacks: {
            label: (ctx) => {
              const val = ctx.raw;
              return val !== null ? `  ${ctx.dataset.label}: ${val?.toFixed ? val.toFixed(2) : val}` : `  ${ctx.dataset.label}: N/A`;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: "#64748b", font: { size: 11 } },
          grid: { color: "rgba(255,255,255,0.04)" },
        },
        y: {
          ticks: { color: "#64748b", font: { size: 11 } },
          grid: { color: "rgba(255,255,255,0.06)" },
        },
      },
    },
  });
}

/**
 * 차트 변수 선택 드롭다운 바인딩
 */
function bindChartVarSelect(drivers) {
  const sel = document.getElementById("chart-var-select");
  if (!sel) return;

  sel.addEventListener("change", () => {
    renderTimeseriesChart(drivers, sel.value);
  });
}

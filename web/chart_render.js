/**
 * chart_render.js — SSP 4선 시계열 차트 (Chart.js)
 * 상수: SSP_COLORS, SSP_LABELS, PERIOD_MIDPOINTS, PERIOD_KEYS → constants.js
 */

let _chart = null;

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

  if (_chart) {
    _chart.destroy();
    _chart = null;
  }

  const meta = DRIVER_META[varKey] || {};
  const unitLabel = meta.unit ? `${meta.label} (${meta.unit})` : (meta.label || varKey);
  const cardTitle = ctx.closest(".card")?.querySelector(".card-title");
  if (cardTitle) cardTitle.textContent = `SSP 시계열 추이 — ${meta.label || varKey}`;

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
          title: {
            display: !!meta.unit,
            text: unitLabel,
            color: "#4a6280",
            font: { size: 10 },
          },
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

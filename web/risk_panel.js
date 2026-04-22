/**
 * risk_panel.js — 국제기준 기반 리스크 해석 패널 렌더링
 *
 * 의존: constants.js (SSP_LABELS, PERIOD_LABELS)
 * 호출: renderInterpretationPanel(result) — app.js의 renderResults()에서 호출
 */

const LEVEL_KO   = { VERY_HIGH: "매우 높음", HIGH: "높음", MEDIUM: "중간", LOW: "낮음", UNKNOWN: "N/A" };
const LEVEL_CLASS = { VERY_HIGH: "level-very-high", HIGH: "level-high", MEDIUM: "level-medium", LOW: "level-low" };
const MAT_CLASS   = { HIGH: "mat-high", "MEDIUM-HIGH": "mat-medium-high", MEDIUM: "mat-medium", LOW: "mat-low" };

const TCFD_TYPE_KO = { acute: "급성 리스크", chronic: "만성 리스크", other: "기타" };

const PERIOD_LABEL_KO = {
  baseline: "현재(2015-24)", near: "단기(2025-34)",
  mid: "중기(2045-54)", far: "장기(2075-84)", end: "장기+(2090-99)",
};

/**
 * 메인 진입점 — renderResults()에서 호출
 * @param {Object} result  /api/query 응답 전체 ({meta, drivers, interpretation})
 */
function renderInterpretationPanel(result) {
  const interp = result && result.interpretation;
  const panel  = document.getElementById("risk-interpretation-panel");
  if (!panel) return;

  if (!interp || !interp.top_risks) {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";

  _renderHeader(interp);
  _renderTcfd(interp.tcfd);
  _renderRiskCards(interp.top_risks);
  _renderNarrativePlaceholder();
  _fetchNarrative(result.meta, interp);
}

// ── 헤더 (물질성 배지 + 시나리오) ────────────────────────────────────────────

function _renderHeader(interp) {
  const mat      = interp.materiality || {};
  const matLevel = mat.level || "N/A";
  const ssp      = interp.evaluated_ssp    || "ssp245";
  const period   = interp.evaluated_period || "mid";

  const badge = document.getElementById("interp-mat-badge");
  if (badge) {
    badge.textContent  = `물질성: ${matLevel}`;
    badge.className    = `interp-mat-badge ${MAT_CLASS[matLevel] || "mat-medium"}`;
  }

  const scenario = document.getElementById("interp-scenario");
  if (scenario) {
    scenario.textContent = `${(SSP_LABELS || {})[ssp] || ssp}  ·  ${PERIOD_LABEL_KO[period] || period}`;
  }

  const matNote = document.getElementById("interp-mat-note");
  if (matNote) {
    matNote.textContent = mat.issb_s2_note || "";
  }

  const cdpRef = document.getElementById("interp-cdp-ref");
  if (cdpRef) {
    cdpRef.textContent = mat.cdp_ref || "";
  }
}

// ── TCFD 분류 ────────────────────────────────────────────────────────────────

function _renderTcfd(tcfd) {
  const acute   = document.getElementById("interp-tcfd-acute");
  const chronic = document.getElementById("interp-tcfd-chronic");
  if (!tcfd) return;

  const toLabel = (vars) => vars.length
    ? vars.map(v => {
        const dm = (typeof DRIVER_META !== "undefined") ? DRIVER_META[v] : null;
        return dm ? dm.label : v;
      }).join(", ")
    : "해당 없음";

  if (acute)   acute.textContent   = toLabel(tcfd.acute   || []);
  if (chronic) chronic.textContent = toLabel(tcfd.chronic || []);
}

// ── 리스크 카드 목록 ─────────────────────────────────────────────────────────

function _renderRiskCards(topRisks) {
  const list = document.getElementById("interp-risks-list");
  if (!list) return;

  const highRisks = topRisks.filter(r => ["HIGH", "VERY_HIGH"].includes(r.level));
  if (!highRisks.length) {
    list.innerHTML = `<p class="interp-empty">현 시나리오 기준 고위험(HIGH 이상) 항목 없음</p>`;
    return;
  }

  list.innerHTML = highRisks.slice(0, 8).map(r => `
    <div class="risk-card ${LEVEL_CLASS[r.level] || ""}">
      <div class="risk-card-header">
        <span class="risk-name">${r.label}</span>
        <div class="risk-badges">
          <span class="risk-level-badge ${LEVEL_CLASS[r.level] || ""}">${LEVEL_KO[r.level] || r.level}</span>
          <span class="risk-tcfd-badge tcfd-${r.tcfd_type}">${TCFD_TYPE_KO[r.tcfd_type] || r.tcfd_type}</span>
        </div>
      </div>
      <div class="risk-value">${r.value} <span class="risk-unit">${r.unit}</span></div>
      <div class="risk-context">${r.context || ""}</div>
      ${r.business_impacts && r.business_impacts.length ? `
        <ul class="risk-impacts">
          ${r.business_impacts.slice(0, 3).map(i => `<li>${i}</li>`).join("")}
        </ul>
      ` : ""}
      ${r.threshold_inst ? `
        <div class="risk-source">
          출처:
          ${r.threshold_url
            ? `<a href="${r.threshold_url}" target="_blank" rel="noopener">${r.threshold_inst}</a>`
            : r.threshold_inst}
        </div>
      ` : ""}
    </div>
  `).join("");
}

// ── AI 내러티브 ───────────────────────────────────────────────────────────────

function _renderNarrativePlaceholder() {
  const el = document.getElementById("interp-narrative");
  if (el) {
    el.innerHTML = `<div class="narrative-loading">
      <span class="loading-spinner-sm"></span> 공시용 내러티브 생성 중 (Claude Haiku)...
    </div>`;
  }
}

async function _fetchNarrative(meta, interp) {
  const lat    = meta.lat;
  const lon    = meta.lon;
  const ssp    = interp.evaluated_ssp    || "ssp245";
  const period = interp.evaluated_period || "mid";

  const url = `/api/query/interpret/narrative?lat=${lat}&lon=${lon}&ssp=${ssp}&period=${period}&lang=ko`;
  const el  = document.getElementById("interp-narrative");
  if (!el) return;

  try {
    const resp = await fetch(url, { signal: AbortSignal.timeout(20_000) });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    el.innerHTML = `
      <blockquote class="narrative-text">${_escapeHtml(data.narrative)}</blockquote>
      <p class="narrative-meta">
        생성 모델: ${data.model || "claude-haiku"}
        ${data.cached ? " &nbsp;|&nbsp; <span class='cached-tag'>캐시</span>" : ""}
      </p>
      <p class="narrative-disclaimer">
        ※ AI 생성 초안입니다. 실제 공시 전 ESG 전문가 검토를 권장합니다.
      </p>
    `;
  } catch (e) {
    el.innerHTML = `
      <p class="narrative-error">내러티브 생성 실패 또는 시간 초과 — 위 규칙 기반 해석을 참조하세요.</p>
    `;
  }
}

// ── 유틸 ─────────────────────────────────────────────────────────────────────

function _escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

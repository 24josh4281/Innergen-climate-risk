/**
 * app.js — 메인 애플리케이션 오케스트레이터
 */

// 전역 상태
let _lastResult = null;
let _serverChecked = false;

// ── 초기화 ──────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  bindTabSwitcher();
  bindSearchButtons();
  bindExcelButton();
  bindExampleButton();
  await loadSiteChips();
  checkServerOnFirstUse();
});

// ── 탭 전환 ─────────────────────────────────────────────────────────────────

function bindTabSwitcher() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".search-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

// ── 저장된 사업장 칩 ─────────────────────────────────────────────────────────

async function loadSiteChips() {
  const sites = await fetchSites().catch(() => []);
  const container = document.getElementById("site-chips");
  if (!container) return;

  const fallback = [
    { id: "OCI_HQ_Seoul",     display: "서울 본사",  lat: 37.5649, lon: 126.9793 },
    { id: "Pohang_Plant",     display: "포항",       lat: 36.0095, lon: 129.3435 },
    { id: "OCI_Shanghai",     display: "상해",       lat: 31.2304, lon: 121.4737 },
    { id: "OCI_Japan_Tokyo",  display: "도쿄",       lat: 35.6762, lon: 139.6503 },
    { id: "Philko_Makati",    display: "마카티",     lat: 14.5995, lon: 120.9842 },
  ];

  const list = (sites.length > 0 ? sites : fallback).slice(0, 10);
  container.innerHTML = list.map(s => `
    <span class="site-chip"
      data-lat="${s.lat}" data-lon="${s.lon}" data-name="${s.display || s.id}">
      ${s.display || s.id}
    </span>
  `).join("");

  container.querySelectorAll(".site-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const lat = parseFloat(chip.dataset.lat);
      const lon = parseFloat(chip.dataset.lon);
      runQuery(lat, lon, chip.dataset.name);
    });
  });
}

// ── 검색 버튼 바인딩 ─────────────────────────────────────────────────────────

function bindSearchButtons() {
  // 주소 조회
  document.getElementById("btn-geocode").addEventListener("click", handleAddressSearch);
  document.getElementById("input-address").addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleAddressSearch();
  });

  // 위도경도 직접
  document.getElementById("btn-latlon").addEventListener("click", handleLatlonSearch);
  document.getElementById("input-lat").addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleLatlonSearch();
  });
  document.getElementById("input-lon").addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleLatlonSearch();
  });
}

async function handleAddressSearch() {
  const address = document.getElementById("input-address").value.trim();
  if (!address) return showStatus("⚠️ 주소를 입력해주세요.", false);

  showStatus("📍 주소 변환 중...", true);
  try {
    const { lat, lon, displayName } = await geocodeAddress(address);
    showStatus(`✅ ${displayName.slice(0, 60)}... → (${lat.toFixed(4)}, ${lon.toFixed(4)})`, false);
    await runQuery(lat, lon, address);
  } catch (e) {
    showStatus(`❌ 지오코딩 실패: ${e.message}`, false);
  }
}

function handleLatlonSearch() {
  const lat = parseFloat(document.getElementById("input-lat").value);
  const lon = parseFloat(document.getElementById("input-lon").value);
  if (isNaN(lat) || isNaN(lon)) return showStatus("⚠️ 위도/경도를 올바르게 입력해주세요.", false);
  runQuery(lat, lon, `${lat.toFixed(4)}, ${lon.toFixed(4)}`);
}

// ── 핵심 조회 플로우 ─────────────────────────────────────────────────────────

async function runQuery(lat, lon, label = "") {
  ensureServerReady(async () => {
    setLoading(true, `데이터 조회 중... (${label || `${lat.toFixed(3)}, ${lon.toFixed(3)}`})`);

    try {
      const result = await queryRisk(lat, lon);
      _lastResult = result;
      renderResults(result);
    } catch (e) {
      showStatus(`❌ 조회 실패: ${e.message}`, false);
      setLoading(false);
    }
  });
}

// ── 결과 렌더링 ──────────────────────────────────────────────────────────────

function renderResults(result, siteLabel) {
  const { meta, drivers } = result;

  // 결과 섹션 표시
  const section = document.getElementById("results");
  section.style.display = "block";
  section.scrollIntoView({ behavior: "smooth", block: "start" });

  // Tier 배너
  renderTierBanner(meta);

  // RAG 히트맵 (기본: SSP2-4.5)
  renderHeatmap(drivers, "ssp245");
  bindHeatmapTabs(drivers);
  bindHeatmapRowClick(drivers);

  // 시계열 차트
  renderTimeseriesChart(drivers, "tasmax");
  bindChartVarSelect(drivers);

  // 지도
  renderMap(meta.lat, meta.lon, meta);

  // Top 5
  renderTop5(drivers);

  // 리스크 해석 패널
  renderInterpretationPanel(result);

  setLoading(false);
  showStatus("", false);
}

// ── 예시 데모 버튼 ───────────────────────────────────────────────────────────

function bindExampleButton() {
  const btn = document.getElementById("btn-example-pohang");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "로딩 중...";
    try {
      const resp = await fetch("data/pohang_example.json");
      if (!resp.ok) throw new Error("예시 파일 로드 실패");
      const result = await resp.json();
      const site = result._site || {};
      // meta 보정 — 예시 표시용
      result.meta = {
        ...result.meta,
        lat:  site.lat  || 36.0095,
        lon:  site.lon  || 129.3435,
        tier: "EXAMPLE",
        resolution: "precomputed",
        data_source: "사전계산 (OCI 포항 사업장 예시)",
        kma_rda:    true,
        kma_cordex: true,
      };
      _lastResult = result;
      renderResults(result, site.display || "OCI 포항 사업장");
      showStatus(`✅ 예시 리포트: ${site.display || "OCI 포항 사업장"} (36.0095°N, 129.3435°E)`, false);
    } catch (e) {
      showStatus(`❌ 예시 로드 실패: ${e.message}`, false);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span class="example-flag">🇰🇷</span> OCI 포항 사업장 — 즉시 보기';
    }
  });
}

function renderTierBanner(meta) {
  const banner = document.getElementById("tier-banner");
  if (!banner) return;

  const isExample = meta.tier === "EXAMPLE";
  banner.className = `tier-banner ${isExample ? "T2" : meta.tier}`;
  if (isExample) {
    banner.innerHTML = `
      <span class="tier-badge" style="background:#7B1FA2;color:#fff;">예시</span>
      <div class="tier-info">
        <h3>OCI 포항 사업장 — 사전 계산된 예시 리포트</h3>
        <p>36.0095°N, 129.3435°E &nbsp;|&nbsp; KOR &nbsp;|&nbsp;
           <span style="color:var(--accent)">CMIP6 + PhyRisk + KMA_RDA + CORDEX + CLIMADA HDF5</span>
           &nbsp;|&nbsp; <span style="opacity:.6">실시간 API 없이 즉시 표시된 결과입니다</span>
        </p>
      </div>
    `;
    return;
  }
  banner.innerHTML = `
    <span class="tier-badge ${meta.tier}">${meta.tier}</span>
    <div class="tier-info">
      <h3>${meta.tier === "T1" ? "정밀 데이터 (기존 사업장)" : meta.tier === "T2" ? "지역 그리드 데이터" : "글로벌 그리드 데이터"}</h3>
      <p>${meta.tier_label}
        ${meta.tier !== "T1" ? ` &nbsp;|&nbsp; <span style="color:var(--rag-amber)">⚠️ CMIP6 그리드 근사값 (해상도 ${meta.tier === "T2" ? "1°" : "2°"})</span>` : ""}
      </p>
    </div>
  `;
}

// ── 서버 웜업 처리 ───────────────────────────────────────────────────────────

function checkServerOnFirstUse() {
  // 페이지 로드 시 바로 health check (백그라운드)
  fetch("/api/health", { signal: AbortSignal.timeout(3000) })
    .then(r => r.json())
    .then(d => { if (d.data_loaded) _serverChecked = true; })
    .catch(() => {});
}

function ensureServerReady(callback) {
  if (_serverChecked) {
    callback();
    return;
  }

  // 웜업 오버레이 표시
  const overlay = document.getElementById("warmup-overlay");
  overlay.style.display = "flex";

  waitForServer(
    () => {
      _serverChecked = true;
      overlay.style.display = "none";
      callback();
    },
    (msg) => {
      document.getElementById("warmup-msg").textContent = msg;
    }
  );
}

// ── UI 헬퍼 ─────────────────────────────────────────────────────────────────

function setLoading(loading, msg = "") {
  const btns = document.querySelectorAll(".btn-primary");
  btns.forEach(b => { b.disabled = loading; });
  if (msg) showStatus(msg, loading);
}

function showStatus(msg, spinning = false) {
  const bar = document.getElementById("status-bar");
  if (!bar) return;
  if (!msg) { bar.innerHTML = ""; return; }

  bar.innerHTML = `
    <div class="status-msg">
      ${spinning ? '<div class="spinner"></div>' : ""}
      <span>${msg}</span>
    </div>
  `;
}

// ── Excel 버튼 ───────────────────────────────────────────────────────────────

function bindExcelButton() {
  document.getElementById("btn-excel").addEventListener("click", () => {
    if (!_lastResult) return;
    try {
      exportExcel(_lastResult);
    } catch (e) {
      showStatus(`❌ Excel 생성 실패: ${e.message}`, false);
    }
  });
}

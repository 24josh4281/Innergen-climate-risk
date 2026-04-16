/**
 * api.js — Render.com FastAPI 호출 (Netlify 프록시 경유)
 */

const API_BASE = "/api";
let _serverReady = false;

/**
 * 서버 웜업 폴링 — 콜드스타트 감지
 * @param {Function} onReady - 준비 완료 콜백
 * @param {Function} onProgress - 진행 메시지 콜백 (msg) => void
 */
async function waitForServer(onReady, onProgress) {
  const MAX_WAIT_MS = 60000;
  const POLL_MS = 3000;
  const start = Date.now();

  while (Date.now() - start < MAX_WAIT_MS) {
    try {
      const resp = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
      if (resp.ok) {
        const data = await resp.json();
        if (data.data_loaded) {
          _serverReady = true;
          onReady();
          return;
        }
        onProgress(`데이터 로드 중... (${Math.round((Date.now() - start) / 1000)}초)`);
      }
    } catch (e) {
      onProgress(`서버 웜업 중... (${Math.round((Date.now() - start) / 1000)}초)`);
    }
    await new Promise(r => setTimeout(r, POLL_MS));
  }
  // 타임아웃 → 그냥 진행 (일부 기능 실패할 수 있음)
  _serverReady = true;
  onReady();
}

/**
 * 기후 리스크 데이터 조회
 * @param {number} lat
 * @param {number} lon
 * @returns {Promise<Object>} {meta, drivers}
 */
async function queryRisk(lat, lon) {
  const url = `${API_BASE}/query?lat=${lat}&lon=${lon}`;
  const resp = await fetch(url, { signal: AbortSignal.timeout(35000) });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `API 오류 (${resp.status})`);
  }
  return resp.json();
}

/**
 * 14개 OCI 사업장 목록 조회
 */
async function fetchSites() {
  try {
    const resp = await fetch(`${API_BASE}/sites`, { signal: AbortSignal.timeout(10000) });
    if (!resp.ok) return [];
    const data = await resp.json();
    return data.sites || [];
  } catch {
    return [];
  }
}

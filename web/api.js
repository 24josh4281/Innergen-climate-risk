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
 * 주소/지명 → 좌표 변환 (서버 Nominatim 프록시)
 * @param {string} query  — 예: "Tokyo", "서울 강남구"
 * @returns {Promise<{results: Array<{lat, lon, display_name, country_code}>}>}
 */
async function geocode(query) {
  const url = `${API_BASE}/geocode?q=${encodeURIComponent(query)}`;
  const resp = await fetch(url, { signal: AbortSignal.timeout(10000) });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Geocoding 오류 (${resp.status})`);
  }
  return resp.json();
}

/**
 * 기후 리스크 요약 조회 (경량 — 핵심 지표만)
 * @param {number} lat
 * @param {number} lon
 * @returns {Promise<{location, climate, hazards}>}
 */
async function querySummary(lat, lon) {
  const url = `${API_BASE}/query/summary?lat=${lat}&lon=${lon}`;
  const resp = await fetch(url, { signal: AbortSignal.timeout(35000) });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `API 오류 (${resp.status})`);
  }
  return resp.json();
}

/**
 * 기후 리스크 데이터 전체 조회
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
 * 앙상블 통계 포함 기후 리스크 조회 (T1: p10/p90/std/n_models 포함)
 * @param {number} lat
 * @param {number} lon
 * @returns {Promise<Object>} {meta, drivers, ensemble_stats}
 */
async function queryRiskEnsemble(lat, lon) {
  const url = `${API_BASE}/query/ensemble?lat=${lat}&lon=${lon}`;
  const resp = await fetch(url, { signal: AbortSignal.timeout(35000) });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `API 오류 (${resp.status})`);
  }
  return resp.json();
}

/**
 * 특정 CMIP6 모델 단일값 조회
 * @param {number} lat
 * @param {number} lon
 * @param {string} model  — 예: "miroc6", "mpi_esm1_2_lr"
 * @returns {Promise<Object>} {meta, model, region, drivers, available_models}
 */
async function queryRiskModel(lat, lon, model) {
  const url = `${API_BASE}/query/model?lat=${lat}&lon=${lon}&model=${encodeURIComponent(model)}`;
  const resp = await fetch(url, { signal: AbortSignal.timeout(60000) }); // NC 읽기 최대 60초
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `API 오류 (${resp.status})`);
  }
  return resp.json();
}

/**
 * 사용 가능한 CMIP6 모델 목록 조회
 * @param {number|null} lat  — null이면 전체 목록
 * @param {number|null} lon
 * @returns {Promise<{models: string[], count: number}>}
 */
async function fetchModels(lat = null, lon = null) {
  let url = `${API_BASE}/models`;
  if (lat !== null && lon !== null) url += `?lat=${lat}&lon=${lon}`;
  try {
    const resp = await fetch(url, { signal: AbortSignal.timeout(10000) });
    if (!resp.ok) return { models: [], count: 0 };
    return resp.json();
  } catch {
    return { models: [], count: 0 };
  }
}

/**
 * 저장된 사업장 목록 조회
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

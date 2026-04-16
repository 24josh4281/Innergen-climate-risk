/**
 * geocoding.js — Nominatim 지오코딩 (브라우저 측)
 */

const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";

/**
 * 주소 → {lat, lon, displayName} 변환
 * @param {string} address
 * @returns {Promise<{lat: number, lon: number, displayName: string}>}
 */
async function geocodeAddress(address) {
  const params = new URLSearchParams({
    q: address,
    format: "json",
    limit: "1",
    "accept-language": "ko,en",
    addressdetails: "1",
  });

  const url = `${NOMINATIM_URL}?${params}`;
  const resp = await fetch(url, {
    headers: { "User-Agent": "OCI-ClimateRisk/1.0 (contact@oci.com)" },
    signal: AbortSignal.timeout(8000),
  });

  if (!resp.ok) throw new Error(`Nominatim 오류 (${resp.status})`);

  const results = await resp.json();
  if (!results || results.length === 0) {
    throw new Error(`주소를 찾을 수 없습니다: "${address}"\n영어로 다시 시도해보세요.`);
  }

  const top = results[0];
  return {
    lat: parseFloat(top.lat),
    lon: parseFloat(top.lon),
    displayName: top.display_name,
  };
}

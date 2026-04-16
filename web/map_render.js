/**
 * map_render.js — Leaflet 위치 지도
 */

let _map = null;
let _markers = [];

/**
 * 지도 초기화 또는 업데이트
 * @param {number} lat - 조회 좌표
 * @param {number} lon
 * @param {Object} meta - API 응답의 meta 객체
 */
function renderMap(lat, lon, meta) {
  const container = document.getElementById("map");
  if (!container) return;

  // 기존 마커 제거
  _markers.forEach(m => m.remove());
  _markers = [];

  if (!_map) {
    _map = L.map("map", {
      zoomControl: true,
      attributionControl: true,
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(_map);
  }

  // 조회 좌표 마커 (파란색)
  const queryIcon = L.divIcon({
    className: "",
    html: `<div style="
      width: 14px; height: 14px;
      background: #3b82f6;
      border: 2px solid white;
      border-radius: 50%;
      box-shadow: 0 0 8px rgba(59,130,246,0.6);
    "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });

  const queryMarker = L.marker([lat, lon], { icon: queryIcon })
    .addTo(_map)
    .bindPopup(`<b>조회 위치</b><br>${lat.toFixed(4)}, ${lon.toFixed(4)}<br>${meta.tier_label || ""}`);
  _markers.push(queryMarker);

  // T1 매칭 사이트 마커 (초록색, T1일 때만)
  if (meta.matched_t1_site && meta.tier === "T1") {
    const t1Icon = L.divIcon({
      className: "",
      html: `<div style="
        width: 12px; height: 12px;
        background: #22c55e;
        border: 2px solid white;
        border-radius: 50%;
      "></div>`,
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });

    const t1Marker = L.marker([lat, lon], { icon: t1Icon })
      .addTo(_map)
      .bindPopup(`<b>${meta.matched_t1_site}</b><br>T1 정밀 사이트`);
    _markers.push(t1Marker);
  }

  _map.setView([lat, lon], meta.tier === "T1" ? 11 : 7);
  // Leaflet size 재계산 (hidden → visible 전환 시 필요)
  setTimeout(() => _map && _map.invalidateSize(), 100);
}

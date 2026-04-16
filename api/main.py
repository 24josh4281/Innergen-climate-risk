"""
main.py — FastAPI 기후 리스크 백엔드 (Render.com 배포용)

엔드포인트:
  GET /api/health   — 서버 준비 상태 확인
  GET /api/query    — 위도/경도 → 기후 리스크 데이터 반환
  GET /api/sites    — 기존 14개 OCI 사업장 목록
"""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from site_constants import OCI_SITES
from data_loader import site_data
from cmip6_grid import cmip6_grid
from tier_resolver import resolve

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_startup_time = None
_data_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _startup_time, _data_ready
    _startup_time = time.time()
    logger.info("Loading data...")

    # 데이터 로드 (순서 중요: site_data 먼저, 그 다음 CMIP6 그리드)
    site_data.load()
    cmip6_grid.load()

    _data_ready = True
    elapsed = round(time.time() - _startup_time, 1)
    logger.info(f"Data ready in {elapsed}s")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Climate Risk API",
    description="OCI 기후 물리적 리스크 조회 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (Netlify 프록시로 대부분 처리되지만 개발용으로도 열어둠)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """서버 준비 상태 확인 — Netlify 프론트에서 폴링."""
    global _data_ready, _startup_time
    elapsed = round(time.time() - (_startup_time or time.time()), 1)
    return {
        "status": "ready" if _data_ready else "loading",
        "data_loaded": _data_ready,
        "uptime_seconds": elapsed,
        "site_data_loaded": site_data.loaded,
        "cmip6_grid_loaded": cmip6_grid.loaded,
    }


@app.get("/api/sites")
async def list_sites():
    """기존 14개 OCI 사업장 목록."""
    return {
        "sites": [
            {
                "id": site_id,
                "display": meta["display"],
                "lat": meta["lat"],
                "lon": meta["lon"],
                "country": meta["country"],
            }
            for site_id, meta in OCI_SITES.items()
        ]
    }


@app.get("/api/query")
async def query_risk(
    lat: float = Query(..., ge=-90, le=90, description="위도"),
    lon: float = Query(..., ge=-180, le=360, description="경도"),
):
    """
    위도/경도 → 기후 물리적 리스크 데이터 반환.

    Tier 자동 결정:
    - T1: 기존 14사이트 5km 이내 (사전계산 정밀 데이터)
    - T2: 동아시아/동남아 CMIP6 1° 그리드
    - T3: 전구 CMIP6 2° 그리드
    """
    if not _data_ready:
        raise HTTPException(status_code=503, detail="데이터 로드 중입니다. 잠시 후 재시도해주세요.")

    # 경도 정규화 (0-360 → -180~180)
    if lon > 180:
        lon = lon - 360

    try:
        result = await resolve(lat, lon)
    except Exception as e:
        logger.error(f"resolve failed for ({lat}, {lon}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

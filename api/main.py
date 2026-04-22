"""
main.py — FastAPI 기후 리스크 백엔드

엔드포인트:
  GET /api/health          — 서버 상태 확인
  GET /api/geocode         — 주소 → 좌표 변환 (Nominatim 프록시)
  GET /api/query           — 위도/경도 → 전체 기후 리스크 데이터
  GET /api/query/summary   — 요약 응답 (위치·기후·위험도 핵심 지표만)
  GET /api/query/ensemble  — 앙상블 통계 포함 (p10/p90/std/n_models)
  GET /api/query/model     — 특정 CMIP6 모델 단일값 조회
  GET /api/models          — 사용 가능한 CMIP6 모델 목록
  GET /api/sites           — 사전계산 사업장 목록
"""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from site_constants import OCI_SITES
from data_loader import site_data
from cmip6_grid import cmip6_grid
import httpx
from tier_resolver import resolve, resolve_with_ensemble, resolve_model, list_available_models, build_summary
from interpret_engine import get_narrative

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


@app.get("/api/geocode")
async def geocode(
    q: str = Query(..., min_length=2, description="주소 또는 지명 (예: Tokyo, Seoul, Paris)"),
):
    """
    주소/지명 → 위도·경도 변환 (Nominatim/OpenStreetMap 프록시).

    브라우저 클라이언트뿐 아니라 순수 API 이용자도 주소로 조회 가능.
    """
    params = {"q": q, "format": "json", "limit": "5", "addressdetails": "1"}
    headers = {"User-Agent": "ClimateRiskAPI/2.0 (contact@inng.co.kr)"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params=params, headers=headers,
            )
            resp.raise_for_status()
            results = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding 서비스 오류: {e}")

    if not results:
        raise HTTPException(status_code=404, detail=f"주소를 찾을 수 없습니다: '{q}'")

    return {
        "query": q,
        "results": [
            {
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "display_name": r["display_name"],
                "country_code": (r.get("address") or {}).get("country_code", "").upper(),
            }
            for r in results
        ],
    }


@app.get("/api/query/summary")
async def query_summary(
    lat: float = Query(..., ge=-90, le=90, description="위도"),
    lon: float = Query(..., ge=-180, le=360, description="경도"),
):
    """
    기후 리스크 요약 — 핵심 지표만 반환 (경량 응답).

    반환:
      location  — 좌표·국가·해상도
      climate   — 현재 기후 + SSP2·SSP5 2050/2090 전망 (온도·강수·여름일수)
      hazards   — SSP5-8.5 말기 주요 위험도 점수 (0-100)
    """
    if not _data_ready:
        raise HTTPException(status_code=503, detail="데이터 로드 중입니다.")
    if lon > 180:
        lon = lon - 360
    try:
        result = await resolve(lat, lon)
        return build_summary(result["meta"], result["drivers"])
    except Exception as e:
        logger.error(f"query_summary failed ({lat},{lon}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/query/interpret/narrative")
async def interpret_narrative(
    lat: float = Query(..., ge=-90, le=90, description="위도"),
    lon: float = Query(..., ge=-180, le=360, description="경도"),
    ssp: str    = Query("ssp245", description="SSP 시나리오 (ssp126/ssp245/ssp370/ssp585)"),
    period: str = Query("mid",    description="시점 (baseline/near/mid/far/end)"),
    lang: str   = Query("ko",     description="언어 (ko/en)"),
):
    """
    Claude Haiku 기반 공시용 내러티브 생성 (lazy, 24h 캐시).

    /api/query 응답의 interpretation.narrative=null을 채우기 위한 엔드포인트.
    ANTHROPIC_API_KEY 미설정 시 규칙 기반 폴백 텍스트를 반환한다.
    """
    if not _data_ready:
        raise HTTPException(status_code=503, detail="데이터 로드 중입니다.")
    if lon > 180:
        lon = lon - 360
    if ssp not in ("ssp126", "ssp245", "ssp370", "ssp585"):
        raise HTTPException(status_code=422, detail=f"ssp 값 오류: {ssp}")
    if period not in ("baseline", "near", "mid", "far", "end"):
        raise HTTPException(status_code=422, detail=f"period 값 오류: {period}")

    try:
        result = await resolve(lat, lon)
        interp = result.get("interpretation", {})
        narrative, was_cached = await get_narrative(lat, lon, interp, ssp=ssp, period=period, lang=lang)
        return {
            "narrative": narrative,
            "model":     "claude-haiku-4-5-20251001",
            "cached":    was_cached,
            "language":  lang,
        }
    except Exception as e:
        logger.error(f"interpret_narrative failed ({lat},{lon}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/query/ensemble")
async def query_risk_ensemble(
    lat: float = Query(..., ge=-90, le=90, description="위도"),
    lon: float = Query(..., ge=-180, le=360, description="경도"),
):
    """
    앙상블 통계 포함 조회 (T1 전용).

    T1: p10/p90/std/median/n_models/best_model 포함.
    T2/T3: ensemble_stats=null (단일 그리드값만 반환).
    """
    if not _data_ready:
        raise HTTPException(status_code=503, detail="데이터 로드 중입니다. 잠시 후 재시도해주세요.")
    if lon > 180:
        lon = lon - 360
    try:
        result = await resolve_with_ensemble(lat, lon)
    except Exception as e:
        logger.error(f"resolve_with_ensemble failed for ({lat}, {lon}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")
    return result


@app.get("/api/query/model")
async def query_risk_model(
    lat: float = Query(..., ge=-90, le=90, description="위도"),
    lon: float = Query(..., ge=-180, le=360, description="경도"),
    model: str = Query(..., description="CMIP6 모델 ID (예: miroc6, mpi_esm1_2_lr)"),
):
    """
    특정 CMIP6 모델의 단일값 조회 (T1/T2/T3 전체 지원).

    T1: 사전계산 CSV 즉시 반환.
    T2/T3: NC 파일 직접 읽기 (~3-10초).
    """
    if not _data_ready:
        raise HTTPException(status_code=503, detail="데이터 로드 중입니다. 잠시 후 재시도해주세요.")
    if lon > 180:
        lon = lon - 360
    try:
        result = await resolve_model(lat, lon, model=model)
    except Exception as e:
        logger.error(f"resolve_model failed for ({lat}, {lon}, {model}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모델 조회 실패: {str(e)}")
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/models")
async def get_available_models(
    lat: float = Query(None, ge=-90, le=90, description="위도 (좌표 지정 시 해당 지역 모델만)"),
    lon: float = Query(None, ge=-180, le=360, description="경도"),
):
    """
    사용 가능한 CMIP6 모델 목록.

    lat/lon 지정 시: 해당 좌표에서 조회 가능한 모델만 반환.
    미지정 시: 전체 17개 모델 목록 반환.
    """
    if lon is not None and lon > 180:
        lon = lon - 360
    if lat is not None and lon is not None:
        from cmip6_nc_query import list_models_for_coord
        models = list_models_for_coord(lat, lon)
    else:
        models = list_available_models()
    return {"models": models, "count": len(models)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

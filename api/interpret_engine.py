"""
interpret_engine.py — 국제기준 기반 기후 리스크 해석 엔진

주요 함수:
  interpret(drivers, ssp, period) → interpretation dict (동기, <50ms)
  get_narrative(lat, lon, interpretation, ssp, period) → str (비동기, Claude API)

참조 프레임워크: IPCC AR6, WMO, TCFD, ISSB S2, WRI Aqueduct 4.0, GEM PSHA, ISO 7933
"""
from __future__ import annotations

import json
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── 임계값 DB 로드 (모듈 초기화 시 1회) ─────────────────────────────────────
_THRESH_PATH = Path(__file__).parent / "thresholds.json"
_THRESHOLDS: dict = json.loads(_THRESH_PATH.read_text(encoding="utf-8"))["thresholds"]

# ── TCFD 분류 집합 ────────────────────────────────────────────────────────────
_TCFD_ACUTE = {
    "etccdi_txx", "etccdi_wsdi", "etccdi_rx1day", "etccdi_rx5day",
    "etccdi_r95p", "etccdi_sdii", "flood_risk", "river_flood",
    "tc_annual_freq", "tc_max_wind_kt", "tc_cat3_count",
    "sfcWind", "psha_pga_475", "psha_pga_2475",
}
_TCFD_CHRONIC = {
    "tas", "tasmax", "tasmin", "etccdi_su", "etccdi_tr", "etccdi_wbgt",
    "etccdi_cdd", "etccdi_cwd", "aq_water_stress", "aq_drought",
    "aq_river_flood", "sea_level_rise", "wildfire_risk", "drought_risk",
    "water_stress", "heat_stress", "pr",
}

# ── 레벨 우선순위 ─────────────────────────────────────────────────────────────
_LEVEL_ORDER = {"VERY_HIGH": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}

# ── 24h 내러티브 캐시: {key: (text, timestamp)} ──────────────────────────────
_NARRATIVE_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 86_400  # 24시간


# ─────────────────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _extract_value(entry) -> Optional[float]:
    if entry is None:
        return None
    if isinstance(entry, dict):
        v = entry.get("value")
    else:
        v = entry
    return float(v) if v is not None else None


def _get_level(var: str, value: float) -> str:
    """변수값 → LOW / MEDIUM / HIGH / VERY_HIGH."""
    thresh = _THRESHOLDS.get(var)
    if not thresh:
        return "UNKNOWN"
    levels = thresh["levels"]
    inverse = thresh.get("inverse", False)

    order = ["VERY_HIGH", "HIGH", "MEDIUM", "LOW"] if not inverse else ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]

    for lvl_name in order:
        lv = levels.get(lvl_name, {})
        min_v = lv.get("min", 0)
        max_v = lv.get("max")
        if inverse:
            # 낮을수록 위험 (현재 사용 안함, 향후 대비)
            if max_v is None:
                return lvl_name
            if value <= max_v:
                return lvl_name
        else:
            if max_v is None:
                if value >= min_v:
                    return lvl_name
            else:
                if min_v <= value < max_v:
                    return lvl_name
    return "LOW"


def _classify_tcfd(var: str) -> str:
    if var in _TCFD_ACUTE:
        return "acute"
    if var in _TCFD_CHRONIC:
        return "chronic"
    return "other"


def _get_business_impacts(var: str, level: str) -> list[str]:
    thresh = _THRESHOLDS.get(var, {})
    impacts = thresh.get("business_impacts", {})
    return impacts.get(level) or impacts.get("HIGH") or []


def _get_context_text(var: str, value: float, level: str,
                      base_val: Optional[float]) -> str:
    """수치 맥락화 문장 생성."""
    thresh = _THRESHOLDS.get(var, {})
    unit = thresh.get("unit", "")
    levels = thresh.get("levels", {})
    lv_data = levels.get(level, {})
    source = thresh.get("reference", {}).get("institution", "국제기준")

    parts = []
    if base_val is not None and abs(value - base_val) > 0.05:
        delta = round(value - base_val, 2)
        sign = "+" if delta > 0 else ""
        parts.append(f"현재({base_val:.1f}{unit}) 대비 {sign}{delta:.1f}{unit}")

    if level in ("HIGH", "VERY_HIGH"):
        thresh_max = lv_data.get("min")  # HIGH의 min = 임계값 시작
        lv_label = lv_data.get("label", level)
        if thresh_max is not None:
            parts.append(f"{source} {lv_label} 임계값({thresh_max}{unit}) 초과")

    return ", ".join(parts) if parts else f"{value:.1f}{unit}"


# ─────────────────────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────────────────────

def interpret(drivers: dict, ssp: str = "ssp245", period: str = "mid") -> dict:
    """
    drivers 전체 → interpretation dict 반환 (규칙 기반, 동기 < 50ms).

    Args:
        drivers:  /api/query 반환값의 drivers 필드
        ssp:      평가 기준 SSP (기본 ssp245)
        period:   평가 기준 시점 (기본 mid = 2045-2054)
    Returns:
        {evaluated_ssp, evaluated_period, tcfd, top_risks, materiality, narrative}
    """
    period_data = (drivers.get(ssp) or {}).get(period) or {}
    base_data   = (drivers.get("ssp245") or {}).get("baseline") or {}

    top_risks = []
    tcfd_acute, tcfd_chronic = [], []

    for var, thresh in _THRESHOLDS.items():
        entry = period_data.get(var)
        value = _extract_value(entry)
        if value is None:
            continue

        level = _get_level(var, value)
        if level == "UNKNOWN":
            continue

        tcfd_type = _classify_tcfd(var)
        if level in ("HIGH", "VERY_HIGH"):
            if tcfd_type == "acute" and var not in tcfd_acute:
                tcfd_acute.append(var)
            elif tcfd_type == "chronic" and var not in tcfd_chronic:
                tcfd_chronic.append(var)

        base_val = _extract_value(base_data.get(var))
        ref = thresh.get("reference", {})

        top_risks.append({
            "var":              var,
            "label":            thresh.get("label", var),
            "value":            round(value, 2),
            "unit":             thresh.get("unit", ""),
            "level":            level,
            "tcfd_type":        tcfd_type,
            "threshold_min":    (thresh["levels"].get(level) or {}).get("min"),
            "threshold_source": ref.get("source", ""),
            "threshold_url":    ref.get("url", ""),
            "threshold_inst":   ref.get("institution", ""),
            "context":          _get_context_text(var, value, level, base_val),
            "business_impacts": _get_business_impacts(var, level),
        })

    # 위험도 내림차순 정렬
    top_risks.sort(key=lambda x: _LEVEL_ORDER.get(x["level"], 0), reverse=True)

    red_total   = sum(1 for r in top_risks if r["level"] in ("HIGH", "VERY_HIGH"))
    acute_red   = len(tcfd_acute)
    chronic_red = len(tcfd_chronic)

    if red_total >= 6:
        mat_level = "HIGH"
    elif red_total >= 4:
        mat_level = "MEDIUM-HIGH"
    elif red_total >= 2:
        mat_level = "MEDIUM"
    else:
        mat_level = "LOW"

    issb_note = (
        "IFRS S2 §10에 따른 물질적 기후 리스크 해당 가능성 있음 — 추가 평가 권장"
        if red_total >= 2 else
        "현 시나리오 기준 물질적 기후 리스크 낮음"
    )

    return {
        "evaluated_ssp":    ssp,
        "evaluated_period": period,
        "tcfd": {
            "acute":   tcfd_acute[:6],
            "chronic": tcfd_chronic[:6],
        },
        "top_risks": top_risks[:12],
        "materiality": {
            "acute_red":    acute_red,
            "chronic_red":  chronic_red,
            "total_red":    red_total,
            "level":        mat_level,
            "issb_s2_note": issb_note,
            "cdp_ref":      f"CDP C2.3 — 물리적 위험 영향 가능성: {mat_level}",
        },
        "narrative": None,
    }


async def get_narrative(lat: float, lon: float,
                        interpretation: dict,
                        ssp: str = "ssp245",
                        period: str = "mid",
                        lang: str = "ko") -> tuple[str, bool]:
    """
    Claude Haiku API → 공시용 내러티브 생성 (200-300자).
    실패 시 규칙 기반 폴백 텍스트를 반환하며 예외를 전파하지 않는다.
    Returns: (narrative_text, was_cached)
    """
    cache_key = hashlib.md5(
        f"{lat:.3f}_{lon:.3f}_{ssp}_{period}_{lang}".encode()
    ).hexdigest()

    # 캐시 히트
    cached = _NARRATIVE_CACHE.get(cache_key)
    if cached:
        text, ts = cached
        if time.time() - ts < _CACHE_TTL:
            return text, True

    top5  = (interpretation.get("top_risks") or [])[:5]
    mat   = interpretation.get("materiality", {})

    # try/except 양쪽에서 사용하므로 블록 밖에 정의
    ssp_label_map = {
        "ssp126": "SSP1-2.6 (강한 감축)", "ssp245": "SSP2-4.5 (중간 경로)",
        "ssp370": "SSP3-7.0 (고배출)",    "ssp585": "SSP5-8.5 (화석연료 집약)",
    }
    period_label_map = {
        "baseline": "현재(2015-24)", "near": "단기(2025-34)",
        "mid": "중기(2045-54)",      "far": "장기(2075-84)", "end": "장기+(2090-99)",
    }

    try:
        import anthropic  # noqa: PLC0415
        client = anthropic.Anthropic()

        risk_lines = "\n".join(
            f"- {r['label']}: {r['value']}{r['unit']} [{r['level']}] "
            f"(TCFD: {r['tcfd_type']}) — {r['context']}"
            for r in top5
        )

        system_text = (
            "당신은 ISSB S2 및 CDP 기후공시 전문 컨설턴트입니다. "
            "주어진 기후 물리적 리스크 데이터를 TCFD 프레임워크(급성/만성 리스크)에 따라 분류하고, "
            "투자자와 이해관계자가 이해할 수 있는 공시용 언어로 간결하고 정확한 리스크 요약을 작성합니다. "
            "항상 사용한 임계값의 기관 출처를 언급하고, "
            "마지막 문장에 반드시 '[AI 생성 초안 — 공시 전 전문가 검토 권장]'을 포함합니다."
        )

        user_text = (
            f"위치: 위도 {lat:.3f}, 경도 {lon:.3f}\n"
            f"평가 시나리오: {ssp_label_map.get(ssp, ssp)}\n"
            f"평가 시점: {period_label_map.get(period, period)}\n"
            f"물질성 수준: {mat.get('level', 'N/A')} "
            f"(급성 {mat.get('acute_red', 0)}건 / 만성 {mat.get('chronic_red', 0)}건 고위험)\n\n"
            f"주요 고위험 지표:\n{risk_lines}\n\n"
            f"위 데이터를 바탕으로 TCFD/ISSB S2 공시에 활용 가능한 "
            f"200~350자 한국어 리스크 요약 단락을 작성해주세요. "
            f"TCFD 급성·만성 분류를 반드시 명시하세요."
        )

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=[{
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_text}],
        )
        narrative = msg.content[0].text.strip()

    except Exception as exc:
        logger.warning("Claude API narrative 생성 실패 (%s) — 폴백 적용", exc)
        top = top5[0] if top5 else {}
        narrative = (
            f"이 위치는 {ssp_label_map.get(ssp, ssp)} 시나리오 기준 "  # type: ignore[name-defined]
            f"기후 물리적 리스크 수준이 {mat.get('level', 'N/A')}으로 평가됩니다. "
            f"가장 주목할 리스크는 {top.get('label', '해당 없음')} "
            f"({top.get('level', '')}, TCFD {top.get('tcfd_type', '')})이며, "
            f"IPCC AR6 등 국제기준 임계값을 초과합니다. "
            f"[AI 내러티브 생성 실패 — 규칙 기반 요약으로 대체. 공시 전 전문가 검토 필수]"
        )
        # 폴백도 캐시 (재시도 방지)

    _NARRATIVE_CACHE[cache_key] = (narrative, time.time())
    return narrative, False

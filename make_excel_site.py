"""
make_excel_site.py — 임의 위도/경도의 전체 기후 리스크 데이터를 Excel로 저장

사용법:
    python make_excel_site.py 36.0095 129.3435 "포항공장"
    python make_excel_site.py 37.5649 126.9793 "OCI_HQ"

출력: site_output/{이름}_{lat}_{lon}_climate_risk.xlsx
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
API_DIR  = BASE_DIR / "api"
OUT_DIR  = BASE_DIR / "site_output"
OUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(API_DIR))
os.chdir(API_DIR)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── 인자 파싱 ──────────────────────────────────────────────────────────────────
lat  = float(sys.argv[1]) if len(sys.argv) > 1 else 36.0095
lon  = float(sys.argv[2]) if len(sys.argv) > 2 else 129.3435
name = sys.argv[3]        if len(sys.argv) > 3 else f"{lat}_{lon}"

# ── 모듈 초기화 ────────────────────────────────────────────────────────────────
logger.info("데이터 초기화 중...")
from data_loader import site_data
from cmip6_grid import cmip6_grid
site_data.load()
cmip6_grid.load()

from tier_resolver import resolve, SSP_KEYS, PERIOD_KEYS, PERIOD_LABELS

# ── 데이터 조회 ────────────────────────────────────────────────────────────────
logger.info(f"좌표 조회: {lat}°N, {lon}°E")
result = asyncio.run(resolve(lat, lon))

drivers = result["drivers"]
meta    = result["meta"]

res = meta.get('resolution', '?')
tier_label = {"precomputed": "T1", "1deg": "T2", "2deg": "T3"}.get(res, res)
logger.info(f"Tier: {tier_label} | 해상도: {res}")

# ── openpyxl 임포트 ────────────────────────────────────────────────────────────
try:
    import openpyxl
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side, numbers
    )
    from openpyxl.utils import get_column_letter
except ImportError:
    logger.error("openpyxl 미설치. 설치: pip install openpyxl")
    sys.exit(1)

# ── 스타일 헬퍼 ────────────────────────────────────────────────────────────────
DARK_BG   = "0B1628"
CARD_BG   = "111B2E"
HEADER_BG = "1B2E4A"
ACCENT    = "4FC3F7"
RED_BG    = "C62828";  RED_FG    = "FFFFFF"
AMBER_BG  = "F57F17";  AMBER_FG  = "000000"
GREEN_BG  = "1B5E20";  GREEN_FG  = "FFFFFF"
TEXT_FG   = "E2EAF4"
DIM_FG    = "7B9CC4"
GROUP_BG  = "162236"

def hfont(bold=False, color=TEXT_FG, size=10):
    return Font(name="Consolas", bold=bold, color=color, size=size)

def hfill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def hborder():
    s = Side(style="thin", color="1E3250")
    return Border(left=s, right=s, top=s, bottom=s)

def cell_style(ws, row, col, value, bold=False, fg=TEXT_FG, bg=CARD_BG, align="left", num_fmt=None):
    c = ws.cell(row=row, column=col, value=value)
    c.font      = hfont(bold=bold, color=fg)
    c.fill      = hfill(bg)
    c.border    = hborder()
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=False)
    if num_fmt:
        c.number_format = num_fmt
    return c

def rag_style(ws, row, col, value, rag):
    if rag == "red":
        bg, fg = RED_BG, RED_FG
    elif rag == "amber":
        bg, fg = AMBER_BG, AMBER_FG
    else:
        bg, fg = GREEN_BG, GREEN_FG
    return cell_style(ws, row, col, value, fg=fg, bg=bg, align="center")

def header_row(ws, row, values, bg=HEADER_BG):
    for col, v in enumerate(values, 1):
        c = ws.cell(row=row, column=col, value=v)
        c.font      = hfont(bold=True, color=ACCENT)
        c.fill      = hfill(bg)
        c.border    = hborder()
        c.alignment = Alignment(horizontal="center", vertical="center")

def group_header(ws, row, label, ncols, bg=GROUP_BG):
    c = ws.cell(row=row, column=1, value=label)
    c.font      = hfont(bold=True, color=ACCENT, size=9)
    c.fill      = hfill(bg)
    c.border    = hborder()
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    ws.row_dimensions[row].height = 16

def freeze(ws, cell="B3"):
    ws.freeze_panes = cell

def autofit(ws, min_w=8, max_w=40):
    for col in ws.columns:
        maxlen = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                maxlen = max(maxlen, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max(maxlen + 2, min_w), max_w)

# ── 값 추출 헬퍼 ──────────────────────────────────────────────────────────────
def get_val(entry):
    if entry is None:
        return None
    if isinstance(entry, dict):
        v = entry.get("value")
    else:
        v = entry
    if v is None:
        return None
    return round(float(v), 3) if isinstance(v, (int, float)) else v

def fmt(v, decimals=1):
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return round(v, decimals)
    return v

# ── 드라이버 그룹 정의 ────────────────────────────────────────────────────────
GROUPS = [
    ("CMIP6 기후변수", [
        ("tasmax",  "최고기온",          "°C"),
        ("tasmin",  "최저기온",          "°C"),
        ("tas",     "평균기온",          "°C"),
        ("pr",      "강수량",            "mm/day"),
        ("prsn",    "적설량",            "mm/day"),
        ("sfcWind", "지표풍속",          "m/s"),
        ("evspsbl", "증발산량",          "mm/day"),
    ]),
    ("ETCCDI 극값 — 열", [
        ("etccdi_txx",  "월최고기온(TXx)",      "°C"),
        ("etccdi_tnn",  "월최저기온(TNn)",      "°C"),
        ("etccdi_su",   "여름일수(SU>25°C)",    "days/yr"),
        ("etccdi_tr",   "열대야(TR>20°C)",      "days/yr"),
        ("etccdi_fd",   "결빙일수(FD<0°C)",     "days/yr"),
        ("etccdi_wsdi", "온난기간(WSDI)",        "days/yr"),
        ("etccdi_wbgt", "습구흑구온도(WBGT)",    "°C"),
    ]),
    ("ETCCDI 극값 — 강수", [
        ("etccdi_cdd",    "연속건조일수(CDD)",   "days"),
        ("etccdi_cwd",    "연속습윤일수(CWD)",   "days"),
        ("etccdi_rx1day", "1일최대강수(Rx1day)", "mm"),
        ("etccdi_rx5day", "5일최대강수(Rx5day)", "mm"),
        ("etccdi_r95p",   "극한강수(R95p)",      "mm/yr"),
        ("etccdi_sdii",   "강수강도(SDII)",      "mm/wet-day"),
    ]),
    ("PhyRisk — 열·노동", [
        ("heat_stress",       "열 스트레스",       "score"),
        ("extreme_heat_35c",  "극한고온 35°C",     "score"),
        ("work_loss_high",    "노동손실(고강도)",  "score"),
        ("work_loss_medium",  "노동손실(중강도)",  "score"),
        ("heat_degree_days",  "냉방도일",          "score"),
    ]),
    ("PhyRisk — 수자원·가뭄", [
        ("water_stress",   "물 스트레스",    "score"),
        ("water_depletion","수자원 고갈",    "score"),
        ("drought_risk",   "가뭄 위험",      "score"),
    ]),
    ("PhyRisk — 홍수·태풍·기타", [
        ("flood_risk",     "홍수 위험",      "score"),
        ("river_flood",    "하천 홍수",      "score"),
        ("coastal_flood",  "해안 홍수",      "score"),
        ("pluvial_flood",  "도시 침수",      "score"),
        ("cyclone_risk",   "사이클론 위험",  "score"),
        ("storm_surge",    "폭풍 해일",      "score"),
        ("sea_level_rise", "해수면 상승",    "score"),
        ("wildfire_risk",  "산불 위험",      "score"),
        ("earthquake_risk","지진 위험",      "score"),
        ("landslide_risk", "산사태 위험",    "score"),
    ]),
    ("Aqueduct 수자원 (정적)", [
        ("aq_water_stress",      "수자원 스트레스",      "0-5"),
        ("aq_river_flood",       "하천홍수 위험",        "0-5"),
        ("aq_coastal_flood",     "해안홍수 위험",        "0-5"),
        ("aq_drought",           "가뭄 위험",            "0-5"),
        ("aq_interann_var",      "연간변동성",           "0-5"),
        ("aq_water_stress_2050", "수자원 스트레스 2050", "0-5"),
    ]),
    ("IBTrACS 태풍 (역사적)", [
        ("tc_annual_freq",  "태풍 연간 빈도",    "건/yr"),
        ("tc_max_wind_kt",  "최대 풍속",         "kt"),
        ("tc_cat3_count",   "카테고리3+ 태풍",   "건"),
    ]),
    ("PSHA 지진재해 (정적)", [
        ("psha_pga_475",  "PGA 475년 재현주기",  "g"),
        ("psha_pga_2475", "PGA 2475년 재현주기", "g"),
    ]),
    ("CCKP 에너지·극한열 — World Bank 0.25°", [
        ("cckp_hi35",  "열지수 초과일 (HI>35°C)",  "days/yr"),
        ("cckp_hd40",  "극한고온일 (Tmax>40°C)",   "days/yr"),
        ("cckp_tr26",  "열대야 한국기준 (>26°C)",  "days/yr"),
        ("cckp_cdd65", "냉방도일 (CDD base 65°F)", "°F·day/yr"),
        ("cckp_hdd65", "난방도일 (HDD base 65°F)", "°F·day/yr"),
    ]),
    ("CCKP ETCCDI 교차검증 — 온도 계열 (World Bank 0.25°)", [
        ("cckp_csdi",       "한파 지속기간 (CSDI)",    "days/yr"),
        ("cckp_wsdi",       "온난 지속기간 (WSDI-CP)", "days/yr"),
        ("cckp_cdd_consec", "연속건조일수 (CDD-CP)",   "days"),
    ]),
    ("CCKP 신규 확장 — 가뭄·습도·강수·한랭 (World Bank 0.25°)", [
        ("cckp_spei12",  "가뭄지수 (SPEI-12)",       "index"),
        ("cckp_gsl",     "생장기간 (GSL)",            "days/yr"),
        ("cckp_hurs",    "상대습도 (HURS)",           "%"),
        ("cckp_id",      "결빙일 (Tmax<0°C)",        "days/yr"),
        ("cckp_rxmonth", "월최대강수 (Rx-month)",     "mm/month"),
    ]),
]

SSP_LABELS = {
    "ssp126": "SSP1-2.6",
    "ssp245": "SSP2-4.5",
    "ssp370": "SSP3-7.0",
    "ssp585": "SSP5-8.5",
}
PERIOD_LABEL_SHORT = {
    "baseline": "현재",
    "near":     "단기(2030s)",
    "mid":      "중기(2050s)",
    "far":      "장기(2080s)",
    "end":      "말기(2090s)",
}
SSP_ORDER = ["ssp585", "ssp370", "ssp245", "ssp126"]

# ── RAG 임계값 (간단 버전) ────────────────────────────────────────────────────
RAG_RULES = {
    "tasmax":         lambda v: "red" if v > 38 else "amber" if v > 33 else "green",
    "tasmin":         lambda v: "amber" if v > 22 else "green",
    "tas":            lambda v: "red" if v > 30 else "amber" if v > 25 else "green",
    "pr":             lambda v: "amber" if v > 10 or v < 1 else "green",
    "prsn":           lambda v: "green",
    "sfcWind":        lambda v: "red" if v > 15 else "amber" if v > 10 else "green",
    "evspsbl":        lambda v: "amber" if v > 5 else "green",
    "etccdi_txx":     lambda v: "red" if v > 38 else "amber" if v > 33 else "green",
    "etccdi_tnn":     lambda v: "amber" if v < -10 else "green",
    "etccdi_su":      lambda v: "red" if v > 100 else "amber" if v > 60 else "green",
    "etccdi_tr":      lambda v: "red" if v > 30 else "amber" if v > 10 else "green",
    "etccdi_fd":      lambda v: "amber" if v > 60 else "green",
    "etccdi_wsdi":    lambda v: "red" if v > 30 else "amber" if v > 10 else "green",
    "etccdi_wbgt":    lambda v: "red" if v > 32 else "amber" if v > 28 else "green",
    "etccdi_cdd":     lambda v: "red" if v > 60 else "amber" if v > 30 else "green",
    "etccdi_cwd":     lambda v: "green",
    "etccdi_rx1day":  lambda v: "red" if v > 100 else "amber" if v > 50 else "green",
    "etccdi_rx5day":  lambda v: "red" if v > 200 else "amber" if v > 100 else "green",
    "etccdi_r95p":    lambda v: "red" if v > 500 else "amber" if v > 200 else "green",
    "etccdi_sdii":    lambda v: "amber" if v > 20 else "green",
    "cckp_hi35":      lambda v: "red" if v > 60 else "amber" if v > 20 else "green",
    "cckp_hd40":      lambda v: "red" if v > 30 else "amber" if v > 10 else "green",
    "cckp_tr26":      lambda v: "red" if v > 30 else "amber" if v > 10 else "green",
    "cckp_cdd65":     lambda v: "red" if v > 2500 else "amber" if v > 1500 else "green",
    "cckp_hdd65":     lambda v: "red" if v > 4000 else "amber" if v > 2000 else "green",
    "cckp_csdi":      lambda v: "red" if v > 10 else "amber" if v > 4 else "green",
    "cckp_wsdi":      lambda v: "red" if v > 30 else "amber" if v > 10 else "green",
    "cckp_cdd_consec":lambda v: "red" if v > 60 else "amber" if v > 30 else "green",
    "cckp_spei12":    lambda v: "red" if v < -1.5 else "amber" if v < -0.5 else "green",
    "cckp_gsl":       lambda v: "red" if v > 350 else "amber" if v > 320 else "green",
    "cckp_hurs":      lambda v: "red" if v > 80 else "amber" if v > 72 else "green",
    "cckp_id":        lambda v: "red" if v > 30 else "amber" if v > 10 else "green",
    "cckp_rxmonth":   lambda v: "red" if v > 400 else "amber" if v > 250 else "green",
}

def get_rag(dk, val):
    if val is None:
        return None
    fn = RAG_RULES.get(dk)
    if fn:
        return fn(val)
    # score 계열 (0~1)
    if isinstance(val, float) and 0 <= val <= 1:
        return "red" if val > 0.6 else "amber" if val > 0.3 else "green"
    # 0~5 계열
    if isinstance(val, (int, float)) and 0 <= val <= 5:
        return "red" if val >= 3 else "amber" if val >= 2 else "green"
    return "green"


# ══════════════════════════════════════════════════════════════════════════════
# Excel 생성
# ══════════════════════════════════════════════════════════════════════════════
wb = openpyxl.Workbook()
wb.remove(wb.active)  # 기본 시트 제거

PERIOD_COLS = list(PERIOD_KEYS)  # ["baseline","near","mid","far","end"]


# ── 시트 1~4: SSP별 통합 ───────────────────────────────────────────────────────
for ssp in SSP_ORDER:
    ssp_data  = drivers.get(ssp, {})
    ws = wb.create_sheet(SSP_LABELS[ssp])
    ws.sheet_view.showGridLines = False

    # 배경
    ws.sheet_properties.tabColor = "1B2E4A"

    # 제목행
    r = 1
    c = ws.cell(row=r, column=1,
                value=f"기후 물리적 리스크 — {name}  |  {lat}°N, {lon}°E  |  {SSP_LABELS[ssp]}")
    c.font      = hfont(bold=True, color=ACCENT, size=11)
    c.fill      = hfill(DARK_BG)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
    ws.row_dimensions[r].height = 22

    # 부제목 (메타)
    r = 2
    c = ws.cell(row=r, column=1,
                value=f"데이터 소스: CMIP6 17모델 앙상블 | PhyRisk | Aqueduct | IBTrACS | PSHA | CCKP    생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.font      = hfont(bold=False, color=DIM_FG, size=9)
    c.fill      = hfill(DARK_BG)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
    ws.row_dimensions[r].height = 14

    # 컬럼 헤더
    r = 3
    COL_HEADERS = ["카테고리", "변수명", "변수키", "단위"] + [PERIOD_LABEL_SHORT[p] for p in PERIOD_COLS]
    header_row(ws, r, COL_HEADERS)
    ws.row_dimensions[r].height = 18

    r = 4
    for grp_label, vars_list in GROUPS:
        group_header(ws, r, f"▶  {grp_label}", len(COL_HEADERS))
        r += 1
        for dk, var_label, unit in vars_list:
            vals = [get_val((ssp_data.get(p) or {}).get(dk)) for p in PERIOD_COLS]
            # 카테고리
            cell_style(ws, r, 1, grp_label.split(" ")[0], bg=CARD_BG, fg=DIM_FG)
            cell_style(ws, r, 2, var_label, bold=True, bg=CARD_BG)
            cell_style(ws, r, 3, dk, bg=CARD_BG, fg=DIM_FG)
            cell_style(ws, r, 4, unit, bg=CARD_BG, fg=DIM_FG, align="center")
            for ci, (p, v) in enumerate(zip(PERIOD_COLS, vals), 5):
                rag = get_rag(dk, v)
                if rag:
                    rag_style(ws, r, ci, fmt(v), rag)
                else:
                    cell_style(ws, r, ci, fmt(v), align="center")
            ws.row_dimensions[r].height = 15
            r += 1

    # 열 너비 고정
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 12
    for ci in range(5, 10):
        ws.column_dimensions[get_column_letter(ci)].width = 14

    freeze(ws, "B4")


# ── 시트 5: 원시데이터 (Long format) ─────────────────────────────────────────
ws = wb.create_sheet("전체_원시데이터")
ws.sheet_view.showGridLines = False
ws.row_dimensions[1].height = 18
header_row(ws, 1, ["카테고리", "SSP", "시점", "변수키", "변수명", "단위", "값", "RAG"])

r = 2
for ssp in SSP_ORDER:
    ssp_data = drivers.get(ssp, {})
    for p in PERIOD_COLS:
        period_data = ssp_data.get(p, {})
        for grp_label, vars_list in GROUPS:
            for dk, var_label, unit in vars_list:
                v = get_val(period_data.get(dk))
                rag = get_rag(dk, v)
                cat = grp_label.split(" ")[0]
                row_vals = [cat, SSP_LABELS[ssp], PERIOD_LABEL_SHORT[p], dk, var_label, unit, fmt(v), rag or "N/A"]
                for ci, rv in enumerate(row_vals, 1):
                    bg = CARD_BG if r % 2 == 0 else "0E1C30"
                    cell_style(ws, r, ci, rv, bg=bg, align="left" if ci < 7 else "center")
                r += 1

autofit(ws)
freeze(ws, "E2")


# ── 시트 6: 분석 정보 ─────────────────────────────────────────────────────────
ws = wb.create_sheet("분석_정보")
ws.sheet_view.showGridLines = False

info_rows = [
    ("항목", "값"),
    ("분석 플랫폼", "Innergen Climate Scenario"),
    ("생성 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ("위도 (Lat)", lat),
    ("경도 (Lon)", lon),
    ("사업장명", name),
    ("데이터 Tier", meta.get("resolution", "-")),
    ("", ""),
    ("데이터 소스", "설명"),
    ("CMIP6", "17개 모델 앙상블 — SSP126/245/370/585 × 5시점"),
    ("PhyRisk", "OS-Climate PhyRisk — 18개 위험 유형 (0~1 스케일)"),
    ("Aqueduct", "WRI Aqueduct 4.0 — 수자원 위험 6종 (0~5 스케일)"),
    ("IBTrACS", "NOAA IBTrACS v04 — 역사적 태풍 통계 (1980-2023)"),
    ("PSHA", "GEM Global Earthquake Model — PGA (475yr, 2475yr)"),
    ("CCKP", "World Bank CCKP CMIP6 0.25° — 에너지·극한열 5종 + ETCCDI 3종 + 신규확장 5종"),
    ("", ""),
    ("기준", "값"),
    ("시나리오", "SSP1-2.6 / SSP2-4.5 / SSP3-7.0 / SSP5-8.5"),
    ("시점 (현재)", "1995-2014 기준선"),
    ("시점 (단기)", "2020-2039"),
    ("시점 (중기)", "2040-2059"),
    ("시점 (장기)", "2060-2079"),
    ("시점 (말기)", "2080-2099"),
]

r = 1
for label, val in info_rows:
    cell_style(ws, r, 1, label, bold=(label in ("항목","데이터 소스","기준")), bg=HEADER_BG if label in ("항목","데이터 소스","기준") else CARD_BG)
    cell_style(ws, r, 2, val,   bg=HEADER_BG if label in ("항목","데이터 소스","기준") else CARD_BG)
    ws.row_dimensions[r].height = 16
    r += 1

ws.column_dimensions["A"].width = 22
ws.column_dimensions["B"].width = 55


# ── 저장 ──────────────────────────────────────────────────────────────────────
safe_name = name.replace(" ", "_").replace("/", "-")
out_path = OUT_DIR / f"{safe_name}_{lat}_{lon}_climate_risk.xlsx"
wb.save(str(out_path))
logger.info(f"\n✓ 저장 완료: {out_path}")
print(f"\n파일 경로: {out_path}")

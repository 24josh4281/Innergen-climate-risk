"""
build_web_data.py — CMIP6 Grid Pre-Extraction for Climate Risk Web Service

로컬에서 1회 실행 → api/data/ 에 JSON/CSV 저장 → repo에 커밋

출력:
  api/data/cmip6_grid_east_asia.json   동아시아+동남아 1° 그리드 (~15MB)
  api/data/cmip6_grid_global.json      전구 2° 그리드 (~30MB)
  api/data/cmip6_sites.csv             14개 사업장 사전계산 경량화
  api/data/physrisk_sites.csv          14개 사업장 physrisk 데이터

사용:
  python scripts/build_web_data.py
  python scripts/build_web_data.py --region east_asia  (테스트용 단일 지역)
"""

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Windows cp949 terminal fix
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ─── 경로 설정 ────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CMIP6_ROOT  = Path("c:/Users/24jos/climada/data/scenarios/cmip6_v2")
ENSEMBLE_DIR = Path("c:/Users/24jos/climada/data/ensemble")
PHYSRISK_PATH = Path("c:/Users/24jos/climada/data/physrisk/physrisk_long.csv")
OUT_DIR = PROJECT_DIR / "api" / "data"

# ─── 변수 목록 ────────────────────────────────────────────────────────────────
VARIABLES = ["tasmax", "tasmin", "tas", "pr", "prsn", "sfcWind", "evspsbl"]

SSP_DIRS = {
    "ssp126": "ssp1_2_6",
    "ssp245": "ssp2_4_5",
    "ssp370": "ssp3_7_0",
    "ssp585": "ssp5_8_5",
}

# 기간 정의 (연도 범위)
PERIODS = {
    "baseline": (2015, 2024),
    "near":     (2025, 2034),
    "mid":      (2045, 2054),
    "far":      (2075, 2084),
    "end":      (2090, 2099),
}

# ─── 지역별 그리드 해상도 ──────────────────────────────────────────────────────
# east_asia + se_asia: 1° 해상도 (더 정밀)
# 기타 지역: 2° 해상도 (글로벌 커버리지용)
REGION_CONFIGS = {
    "east_asia":     {"resolution": 1.0},
    "se_asia":       {"resolution": 1.0},
    "europe":        {"resolution": 2.0},
    "north_america": {"resolution": 2.0},
    "south_asia":    {"resolution": 2.0},
    "africa":        {"resolution": 2.0},
    "south_america": {"resolution": 2.0},
    "middle_east":   {"resolution": 2.0},
    "central_asia":  {"resolution": 2.0},
    "russia_siberia":{"resolution": 2.0},
    "oceania":       {"resolution": 2.0},
}

# 14개 OCI 사업장 좌표
OCI_SITES = {
    "OCI_HQ_Seoul":     (37.5649, 126.9793, "KOR"),
    "OCI_Dream_Seoul":  (37.5172, 126.9000, "KOR"),
    "OCI_RnD_Seongnam": (37.3219, 127.1190, "KOR"),
    "Pohang_Plant":     (36.0095, 129.3435, "KOR"),
    "Gwangyang_Plant":  (34.9393, 127.6961, "KOR"),
    "Gunsan_Plant":     (35.9700, 126.7114, "KOR"),
    "Iksan_Plant":      (35.9333, 127.0167, "KOR"),
    "Saehan_Recycle":   (35.9333, 127.0167, "KOR"),
    "OCI_Shanghai":     (31.2304, 121.4737, "CHN"),
    "MaSteel_OCI":      (31.6839, 118.5127, "CHN"),
    "Shandong_OCI":     (34.7979, 117.2571, "CHN"),
    "Jianyang_Carbon":  (26.7587, 104.4734, "CHN"),
    "OCI_Japan_Tokyo":  (35.6762, 139.6503, "JPN"),
    "Philko_Makati":    (14.5995, 120.9842, "PHL"),
}


def try_import_netcdf():
    try:
        import netCDF4 as nc
        return nc
    except ImportError:
        print("ERROR: netCDF4 not installed. Run: pip install netCDF4")
        sys.exit(1)


def get_period_time_indices(time_var, start_year, end_year):
    """NC time 변수에서 기간에 해당하는 인덱스 반환."""
    try:
        import netCDF4 as nc
        times = nc.num2date(time_var[:], time_var.units, calendar=getattr(time_var, 'calendar', 'standard'))
        indices = [i for i, t in enumerate(times) if start_year <= t.year <= end_year]
        return indices
    except Exception as e:
        # fallback: time 인덱스 직접 계산 (월별 데이터 가정)
        n_times = len(time_var)
        # 2015년 1월부터 시작 가정
        base_year = 2015
        indices = []
        for i in range(n_times):
            year = base_year + i // 12
            if start_year <= year <= end_year:
                indices.append(i)
        return indices


def regrid_to_resolution(lats, lons, data_2d, resolution):
    """데이터를 target 해상도 그리드로 리샘플링 (nearest-neighbor)."""
    lat_min, lat_max = float(lats.min()), float(lats.max())
    lon_min, lon_max = float(lons.min()), float(lons.max())

    # 0~360 → -180~180 변환
    if lon_max > 180:
        lons_conv = np.where(lons > 180, lons - 360, lons)
        lon_min = float(lons_conv.min())
        lon_max = float(lons_conv.max())
    else:
        lons_conv = lons

    # 타겟 그리드
    target_lats = np.arange(
        round(lat_min / resolution) * resolution,
        round(lat_max / resolution) * resolution + resolution * 0.5,
        resolution
    )
    target_lons = np.arange(
        round(lon_min / resolution) * resolution,
        round(lon_max / resolution) * resolution + resolution * 0.5,
        resolution
    )

    results = []
    for tlat in target_lats:
        for tlon in target_lons:
            # 최근접 그리드 포인트
            ilat = int(np.argmin(np.abs(lats - tlat)))
            ilon = int(np.argmin(np.abs(lons_conv - tlon)))
            val = float(data_2d[ilat, ilon])
            if not np.isnan(val) and not np.isinf(val):
                results.append((round(float(tlat), 2), round(float(tlon), 2), val))
    return results


def extract_region_cmip6(region, resolution, nc):
    """한 지역의 CMIP6 NC 파일에서 4SSP × 7변수 × 5기간 그리드 앙상블 추출."""
    region_dir = CMIP6_ROOT / region
    if not region_dir.exists():
        print(f"  [SKIP] {region}: directory not found")
        return {}

    print(f"\n[{region}] Extracting at {resolution}° resolution...")

    # 결과 저장: {ssp: {var: {period: {(lat,lon): [values]}}}}
    accumulator = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for ssp_key, ssp_dir in SSP_DIRS.items():
        ssp_path = region_dir / ssp_dir
        if not ssp_path.exists():
            continue

        models = sorted([m for m in os.listdir(ssp_path) if (ssp_path / m).is_dir()])
        print(f"  SSP {ssp_key}: {len(models)} models")

        for model in models:
            model_path = ssp_path / model
            for var in VARIABLES:
                # NC 파일 찾기
                nc_files = list(model_path.glob(f"{var}_*.nc"))
                if not nc_files:
                    continue
                nc_file = nc_files[0]

                try:
                    f = nc.Dataset(str(nc_file))
                    raw_lats = f.variables['lat'][:]
                    raw_lons = f.variables['lon'][:]
                    time_var = f.variables['time']
                    var_data = f.variables[var]

                    for period_key, (yr_start, yr_end) in PERIODS.items():
                        t_indices = get_period_time_indices(time_var, yr_start, yr_end)
                        if not t_indices:
                            continue

                        # 기간 평균 계산
                        chunk = var_data[t_indices, :, :]
                        if hasattr(chunk, 'data'):
                            chunk = chunk.filled(np.nan)
                        period_mean = np.nanmean(chunk, axis=0)

                        # 리그리딩
                        pts = regrid_to_resolution(raw_lats, raw_lons, period_mean, resolution)
                        for (tlat, tlon, val) in pts:
                            accumulator[ssp_key][var][period_key][(tlat, tlon)].append(val)

                    f.close()

                except Exception as e:
                    print(f"    [WARN] {model}/{var}: {e}")
                    continue

    # 앙상블 평균 계산
    result = {}
    for ssp_key in accumulator:
        result[ssp_key] = {}
        for var in accumulator[ssp_key]:
            result[ssp_key][var] = {}
            for period_key in accumulator[ssp_key][var]:
                pts_dict = accumulator[ssp_key][var][period_key]
                grid_vals = []
                for (tlat, tlon), vals in pts_dict.items():
                    if vals:
                        ens_mean = round(float(np.nanmean(vals)), 4)
                        grid_vals.append([tlat, tlon, ens_mean])
                result[ssp_key][var][period_key] = grid_vals

    return result


def merge_regions(region_data_list, resolution):
    """여러 지역 데이터를 하나의 그리드 딕셔너리로 병합."""
    merged = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    for region_data in region_data_list:
        for ssp_key, ssp_data in region_data.items():
            for var, var_data in ssp_data.items():
                for period_key, grid_vals in var_data.items():
                    for lat, lon, val in grid_vals:
                        key = f"{lat},{lon}"
                        if key not in merged[ssp_key][var][period_key]:
                            merged[ssp_key][var][period_key][key] = val

    # 직렬화 가능한 형식으로 변환
    result = {}
    for ssp_key in merged:
        result[ssp_key] = {}
        for var in merged[ssp_key]:
            result[ssp_key][var] = {}
            for period_key in merged[ssp_key][var]:
                # dict → list of [lat, lon, val]
                pts = []
                for latlon_key, val in merged[ssp_key][var][period_key].items():
                    lat_str, lon_str = latlon_key.split(",")
                    pts.append([float(lat_str), float(lon_str), val])
                result[ssp_key][var][period_key] = pts

    return result


def build_cmip6_sites_csv():
    """14개 OCI 사업장 CMIP6 앙상블 데이터를 경량 CSV로 저장."""
    src = ENSEMBLE_DIR / "cmip6_ensemble_periods.csv"
    if not src.exists():
        print(f"[WARN] {src} not found, skipping cmip6_sites.csv")
        return

    df = pd.read_csv(src)

    # 필요 컬럼만 선택
    keep_cols = ["site", "country", "ssp", "variable", "period", "ens_mean", "ens_median", "ens_p10", "ens_p90"]
    df_out = df[[c for c in keep_cols if c in df.columns]].copy()

    # SSP 키 표준화 (ssp1_2_6 → ssp126)
    df_out["ssp"] = df_out["ssp"].str.replace("_", "").str.replace("ssp", "ssp")
    df_out["ssp"] = df_out["ssp"].str.replace(r"ssp(\d)(\d)(\d)", r"ssp\1\2\3", regex=True)
    ssp_map = {"ssp126": "ssp126", "ssp245": "ssp245", "ssp370": "ssp370", "ssp585": "ssp585",
               "ssp1_2_6": "ssp126", "ssp2_4_5": "ssp245", "ssp3_7_0": "ssp370", "ssp5_8_5": "ssp585"}

    # period 키 표준화
    period_map = {
        "baseline_2015_2024": "baseline",
        "near_2025_2034": "near",
        "mid_2045_2054": "mid",
        "far_2075_2084": "far",
        "end_2090_2099": "end",
    }
    df_out["period"] = df_out["period"].map(period_map).fillna(df_out["period"])

    # 사이트 좌표 추가
    lat_map = {site: coords[0] for site, coords in OCI_SITES.items()}
    lon_map = {site: coords[1] for site, coords in OCI_SITES.items()}
    df_out["lat"] = df_out["site"].map(lat_map)
    df_out["lon"] = df_out["site"].map(lon_map)

    out_path = OUT_DIR / "cmip6_sites.csv"
    df_out.to_csv(out_path, index=False)
    size_kb = out_path.stat().st_size // 1024
    print(f"[OK] cmip6_sites.csv saved ({size_kb} KB, {len(df_out)} rows)")


def build_physrisk_sites_csv():
    """14개 OCI 사업장 physrisk 데이터를 경량 CSV로 저장."""
    if not PHYSRISK_PATH.exists():
        print(f"[WARN] {PHYSRISK_PATH} not found, skipping physrisk_sites.csv")
        return

    df = pd.read_csv(PHYSRISK_PATH)
    print(f"[INFO] physrisk_long.csv loaded: {df.shape}")
    print(f"       Columns: {list(df.columns)}")

    # 사이트 좌표 추가 (site 컬럼 기준 매핑)
    site_col = None
    for c in ["site", "Site", "SITE", "site_name"]:
        if c in df.columns:
            site_col = c
            break

    if site_col:
        lat_map = {site: coords[0] for site, coords in OCI_SITES.items()}
        lon_map = {site: coords[1] for site, coords in OCI_SITES.items()}
        df["lat"] = df[site_col].map(lat_map)
        df["lon"] = df[site_col].map(lon_map)

    out_path = OUT_DIR / "physrisk_sites.csv"
    df.to_csv(out_path, index=False)
    size_kb = out_path.stat().st_size // 1024
    print(f"[OK] physrisk_sites.csv saved ({size_kb} KB, {len(df)} rows)")


def validate_grid(grid_data, name):
    """그리드 데이터 기본 검증."""
    ssps = list(grid_data.keys())
    if not ssps:
        print(f"[WARN] {name}: empty grid data")
        return
    ssp = ssps[0]
    vars_ = list(grid_data[ssp].keys())
    if not vars_:
        print(f"[WARN] {name}: no variables in {ssp}")
        return
    var = vars_[0]
    periods = list(grid_data[ssp][var].keys())
    if not periods:
        print(f"[WARN] {name}: no periods in {ssp}/{var}")
        return
    period = periods[0]
    pts = grid_data[ssp][var][period]
    print(f"[VALIDATE] {name}: {len(ssps)} SSPs, {len(vars_)} vars, {len(periods)} periods")
    print(f"           Example {ssp}/{var}/{period}: {len(pts)} grid points")
    if pts:
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        print(f"           lat range: {min(lats):.1f}~{max(lats):.1f}, lon: {min(lons):.1f}~{max(lons):.1f}")


def main():
    parser = argparse.ArgumentParser(description="Build CMIP6 grid JSON for climate risk web service")
    parser.add_argument("--region", help="Process single region only (for testing)", default=None)
    parser.add_argument("--skip-global", action="store_true", help="Skip global grid (east_asia+se_asia only)")
    args = parser.parse_args()

    nc = try_import_netcdf()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Climate Risk Web — CMIP6 Grid Pre-Extraction")
    print("=" * 60)

    # ── 1. 동아시아+동남아 1° 그리드 ─────────────────────────────────────────
    if args.region:
        ea_regions = [args.region]
    else:
        ea_regions = ["east_asia", "se_asia"]

    print(f"\n[Phase 1] East Asia + SE Asia grid (1° resolution)")
    ea_data_list = []
    for region in ea_regions:
        if region in REGION_CONFIGS:
            res = REGION_CONFIGS[region]["resolution"]
            data = extract_region_cmip6(region, res, nc)
            if data:
                ea_data_list.append(data)

    if ea_data_list:
        ea_merged = merge_regions(ea_data_list, resolution=1.0)
        ea_out = OUT_DIR / "cmip6_grid_east_asia.json"
        with open(ea_out, "w", encoding="utf-8") as f:
            json.dump(ea_merged, f, separators=(",", ":"))
        size_mb = ea_out.stat().st_size / 1024 / 1024
        print(f"\n[OK] cmip6_grid_east_asia.json saved ({size_mb:.1f} MB)")
        validate_grid(ea_merged, "east_asia")

    # ── 2. 글로벌 2° 그리드 ────────────────────────────────────────────────────
    if not args.skip_global and not args.region:
        global_regions = [r for r in REGION_CONFIGS if r not in ["east_asia", "se_asia"]]
        print(f"\n[Phase 2] Global grid (2° resolution): {global_regions}")

        global_data_list = list(ea_data_list)  # east_asia도 글로벌에 포함
        for region in global_regions:
            res = REGION_CONFIGS[region]["resolution"]
            data = extract_region_cmip6(region, res, nc)
            if data:
                global_data_list.append(data)

        if global_data_list:
            global_merged = merge_regions(global_data_list, resolution=2.0)
            global_out = OUT_DIR / "cmip6_grid_global.json"
            with open(global_out, "w", encoding="utf-8") as f:
                json.dump(global_merged, f, separators=(",", ":"))
            size_mb = global_out.stat().st_size / 1024 / 1024
            print(f"\n[OK] cmip6_grid_global.json saved ({size_mb:.1f} MB)")
            validate_grid(global_merged, "global")

    # ── 3. 사이트 CSV 경량화 ──────────────────────────────────────────────────
    print(f"\n[Phase 3] Building site CSV files...")
    build_cmip6_sites_csv()
    build_physrisk_sites_csv()

    print("\n" + "=" * 60)
    print("Build complete. Files saved to api/data/")
    print("Commit these files to your repo before deploying to Render.")
    print("=" * 60)


if __name__ == "__main__":
    main()

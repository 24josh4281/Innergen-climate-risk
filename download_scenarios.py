# -*- coding: utf-8 -*-
"""
미래 기후 시나리오 다운로드
- CMIP6 SSP2-4.5 / SSP5-8.5  (2015-2100, monthly)
- CMIP5 RCP4.5  / RCP8.5     (2006-2100, monthly)

8개 위험:
  폭염        -> daily_maximum_near_surface_air_temperature
  한파        -> daily_minimum_near_surface_air_temperature
  평균온도    -> near_surface_air_temperature
  집중호우    -> precipitation
  가뭄        -> precipitation + evaporation (SPEI)
  폭설        -> snowfall_flux
  강풍        -> near_surface_wind_speed
  해수면 상승 -> sea_surface_height_above_geoid
"""
import cdsapi
from pathlib import Path

LAT, LON = 34.7979, 117.2571
AREA = [LAT+3, LON-3, LAT-3, LON+3]  # N W S E

BASE = Path("c:/Users/24jos/climada/data/scenarios")

c = cdsapi.Client()

YEARS_SSP  = [str(y) for y in range(2015, 2101)]
YEARS_RCP  = [str(y) for y in range(2006, 2101)]
MONTHS     = [f"{m:02d}" for m in range(1, 13)]

# ============================================================
# 1. CMIP6  SSP2-4.5 / SSP5-8.5
# ============================================================
CMIP6_VARS = [
    ("tasmax",  "daily_maximum_near_surface_air_temperature"),   # 폭염
    ("tasmin",  "daily_minimum_near_surface_air_temperature"),   # 한파
    ("tas",     "near_surface_air_temperature"),                 # 평균온도
    ("pr",      "precipitation"),                                # 집중호우/가뭄
    ("evspsbl", "evaporation_including_sublimation_and_transpiration"),  # 가뭄
    ("prsn",    "snowfall_flux"),                                # 폭설
    ("sfcWind", "near_surface_wind_speed"),                      # 강풍
    ("zos",     "sea_surface_height_above_geoid"),               # 해수면 상승
]

CMIP6_MODELS = ["access_cm2", "mpi_esm1_2_hr", "ipsl_cm6a_lr", "miroc6", "canesm5"]
CMIP6_SCENARIOS = ["ssp2_4_5", "ssp5_8_5"]

print("=" * 60)
print("CMIP6 SSP2-4.5 / SSP5-8.5  (2015-2100, monthly)")
print("=" * 60)

for ssp in CMIP6_SCENARIOS:
    out_dir = BASE / "cmip6" / ssp
    out_dir.mkdir(parents=True, exist_ok=True)
    for short, var in CMIP6_VARS:
        f = out_dir / f"{short}_{ssp}_2015_2100.zip"
        print(f"\n[CMIP6/{ssp}] {short}")
        if f.exists():
            print(f"  Skip: {f.name}  {f.stat().st_size/1e6:.1f} MB")
            continue
        print(f"  Downloading...", flush=True)
        try:
            c.retrieve(
                "projections-cmip6",
                {
                    "temporal_resolution": "monthly",
                    "experiment": ssp,
                    "variable": var,
                    "model": CMIP6_MODELS,
                    "year": YEARS_SSP,
                    "month": MONTHS,
                    "area": AREA,
                    "format": "zip",
                },
                str(f)
            )
            print(f"  OK: {f.stat().st_size/1e6:.1f} MB")
        except Exception as e:
            print(f"  FAIL: {e}")

# ============================================================
# 2. CMIP5  RCP4.5 / RCP8.5
# ============================================================
CMIP5_VARS = [
    ("tas",   "2m_temperature"),           # 폭염/한파/평균온도
    ("pr",    "mean_precipitation_flux"),  # 집중호우/가뭄
    ("wind",  "10m_wind_speed"),           # 강풍
]
CMIP5_MODELS  = ["bcc_csm1_1", "canesm2", "ipsl_cm5a_lr", "miroc_esm", "mpi_esm_lr"]
CMIP5_RCPS    = ["rcp_4_5", "rcp_8_5"]

print("\n" + "=" * 60)
print("CMIP5 RCP4.5 / RCP8.5  (2006-2100, monthly)")
print("=" * 60)

for rcp in CMIP5_RCPS:
    out_dir = BASE / "cmip5" / rcp
    out_dir.mkdir(parents=True, exist_ok=True)
    for short, var in CMIP5_VARS:
        f = out_dir / f"{short}_{rcp}_2006_2100.zip"
        print(f"\n[CMIP5/{rcp}] {short}")
        if f.exists():
            print(f"  Skip: {f.name}  {f.stat().st_size/1e6:.1f} MB")
            continue
        print(f"  Downloading...", flush=True)
        try:
            c.retrieve(
                "projections-cmip5-monthly-single-levels",
                {
                    "variable": var,
                    "experiment": rcp,
                    "model": CMIP5_MODELS,
                    "ensemble_member": "r1i1p1",
                    "period": "200601-210012",
                    "format": "zip",
                },
                str(f)
            )
            print(f"  OK: {f.stat().st_size/1e6:.1f} MB")
        except Exception as e:
            print(f"  FAIL: {e}")

print("\n" + "=" * 60)
print("All scenario downloads complete.")
print(f"Saved to: {BASE}")
print("=" * 60)

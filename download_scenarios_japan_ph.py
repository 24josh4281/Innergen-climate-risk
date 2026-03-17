# -*- coding: utf-8 -*-
"""
CMIP6 시나리오 추가 다운로드
- 일본 (도쿄): 경도 132-146E 범위 추가
- 필리핀 (마카티): 위도 10-22N 범위 추가
- 변수: 기존 12개 동일
- 시나리오: SSP2-4.5 / SSP5-8.5
"""
import cdsapi
from pathlib import Path

BASE = Path("c:/Users/24jos/climada/data/scenarios_v2")
BASE.mkdir(parents=True, exist_ok=True)

c = cdsapi.Client()

YEARS  = [str(y) for y in range(2015, 2101)]
MONTHS = [f"{m:02d}" for m in range(1, 13)]

MODELS = [
    "access_cm2",
    "miroc6",
    "miroc_es2l",
    "fgoals_f3_l",
    "fgoals_g3",
    "kiost_esm",
    "bcc_csm2_mr",
]

SCENARIOS = ["ssp2_4_5", "ssp5_8_5"]

VARIABLES = [
    ("tasmax",  "daily_maximum_near_surface_air_temperature"),
    ("tasmin",  "daily_minimum_near_surface_air_temperature"),
    ("tas",     "near_surface_air_temperature"),
    ("pr",      "precipitation"),
    ("evspsbl", "evaporation_including_sublimation_and_transpiration"),
    ("prsn",    "snowfall_flux"),
    ("sfcWind", "near_surface_wind_speed"),
    ("zos",     "sea_surface_height_above_geoid"),
    ("mrro",    "total_runoff"),
    ("mrsos",   "moisture_in_upper_portion_of_soil_column"),
    ("huss",    "near_surface_specific_humidity"),
    ("rsds",    "surface_downwelling_shortwave_radiation"),
]

# 지역별 설정: (이름, AREA [N W S E], 저장 서브폴더)
REGIONS = [
    ("Japan",       [42, 132, 30, 146], "japan"),
    ("Philippines", [22, 118, 10, 128], "philippines"),
]

total = len(REGIONS) * len(SCENARIOS) * len(VARIABLES)
done  = 0

for region_name, area, region_dir in REGIONS:
    print("\n" + "=" * 65)
    print(f"Region: {region_name}  |  Area: {area}")
    print("=" * 65)

    for ssp in SCENARIOS:
        out_dir = BASE / region_dir / ssp
        out_dir.mkdir(parents=True, exist_ok=True)

        for short, var in VARIABLES:
            done += 1
            f = out_dir / f"{short}_{ssp}_7models_2015_2100.zip"
            print(f"\n[{done}/{total}] {region_name} | {ssp} | {short}")

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
                        "model": MODELS,
                        "year": YEARS,
                        "month": MONTHS,
                        "area": area,
                        "format": "zip",
                    },
                    str(f)
                )
                print(f"  OK: {f.stat().st_size/1e6:.1f} MB")
            except Exception as e:
                print(f"  FAIL: {e}")
                fallback = ["miroc6", "access_cm2", "bcc_csm2_mr"]
                print(f"  Retry with fallback: {fallback}")
                try:
                    c.retrieve(
                        "projections-cmip6",
                        {
                            "temporal_resolution": "monthly",
                            "experiment": ssp,
                            "variable": var,
                            "model": fallback,
                            "year": YEARS,
                            "month": MONTHS,
                            "area": area,
                            "format": "zip",
                        },
                        str(f)
                    )
                    print(f"  OK (fallback): {f.stat().st_size/1e6:.1f} MB")
                except Exception as e2:
                    print(f"  FAIL (fallback): {e2}")

print("\n" + "=" * 65)
print("Download complete.")
print(f"Japan:       {BASE}/japan/")
print(f"Philippines: {BASE}/philippines/")
print("=" * 65)

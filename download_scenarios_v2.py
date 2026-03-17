# -*- coding: utf-8 -*-
"""
CMIP6 시나리오 전체 재다운로드 v2
- 모델: ACCESS-CM2 + MIROC6 + MIROC-ES2L + FGOALS-F3-L + FGOALS-G3 + KIOST-ESM + BCC-CSM2-MR
- 변수: 기존 8개 + 신규 4개 (total_runoff, soil_moisture, RH, radiation)
- 시나리오: SSP2-4.5 / SSP5-8.5
- 영역: 한국+중국 (30-42N, 110-132E)
"""
import cdsapi
from pathlib import Path

# 한국 + 중국 동부 커버 영역
AREA = [42, 110, 30, 132]  # N W S E

BASE = Path("c:/Users/24jos/climada/data/scenarios_v2")
BASE.mkdir(parents=True, exist_ok=True)

c = cdsapi.Client()

YEARS  = [str(y) for y in range(2015, 2101)]
MONTHS = [f"{m:02d}" for m in range(1, 13)]

MODELS = [
    "access_cm2",      # 기존
    "miroc6",          # 일본
    "miroc_es2l",      # 일본
    "fgoals_f3_l",     # 중국 LASG
    "fgoals_g3",       # 중국 LASG
    "kiost_esm",       # 한국 KIOST
    "bcc_csm2_mr",     # 중국 BCC
]

SCENARIOS = ["ssp2_4_5", "ssp5_8_5"]

# 변수 목록 (short명, CDS변수명, 설명)
VARIABLES = [
    # 기존 8개
    ("tasmax",   "daily_maximum_near_surface_air_temperature",          "폭염"),
    ("tasmin",   "daily_minimum_near_surface_air_temperature",          "한파"),
    ("tas",      "near_surface_air_temperature",                        "평균온도/Chronic Heat"),
    ("pr",       "precipitation",                                       "집중호우/Drought/Precipitation"),
    ("evspsbl",  "evaporation_including_sublimation_and_transpiration", "가뭄"),
    ("prsn",     "snowfall_flux",                                       "폭설"),
    ("sfcWind",  "near_surface_wind_speed",                             "강풍/Wind"),
    ("zos",      "sea_surface_height_above_geoid",                      "해수면상승/Coastal Inundation"),
    # 신규 4개
    ("mrro",     "total_runoff",                                        "Water Risk/Riverine Inundation"),
    ("mrsos",    "moisture_in_upper_portion_of_soil_column",            "Drought/Water Risk/Subsidence"),
    ("hurs",     "near_surface_relative_humidity",                      "Chronic Heat/Fire"),
    ("rsds",     "surface_downwelling_shortwave_radiation",             "Fire/Chronic Heat"),
]

print("=" * 65)
print("CMIP6 Download v2")
print(f"Models: {len(MODELS)}  |  Variables: {len(VARIABLES)}")
print(f"Scenarios: {SCENARIOS}")
print(f"Area: {AREA} (Korea + East China)")
print(f"Period: 2015-2100 monthly")
print("=" * 65)

total = len(SCENARIOS) * len(VARIABLES)
done = 0

for ssp in SCENARIOS:
    out_dir = BASE / ssp
    out_dir.mkdir(parents=True, exist_ok=True)

    for short, var, desc in VARIABLES:
        done += 1
        f = out_dir / f"{short}_{ssp}_7models_2015_2100.zip"
        print(f"\n[{done}/{total}] {ssp} | {short} ({desc})")

        if f.exists():
            print(f"  Skip: {f.name}  {f.stat().st_size/1e6:.1f} MB")
            continue

        print(f"  Models: {MODELS}")
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
                    "area": AREA,
                    "format": "zip",
                },
                str(f)
            )
            print(f"  OK: {f.stat().st_size/1e6:.1f} MB")
        except Exception as e:
            print(f"  FAIL: {e}")
            # 모델 일부가 해당 변수 미지원 시 지원 모델만 재시도
            if "not found" in str(e).lower() or "invalid" in str(e).lower():
                fallback_models = ["miroc6", "fgoals_g3", "bcc_csm2_mr", "access_cm2"]
                print(f"  Retry with fallback models: {fallback_models}")
                try:
                    c.retrieve(
                        "projections-cmip6",
                        {
                            "temporal_resolution": "monthly",
                            "experiment": ssp,
                            "variable": var,
                            "model": fallback_models,
                            "year": YEARS,
                            "month": MONTHS,
                            "area": AREA,
                            "format": "zip",
                        },
                        str(f)
                    )
                    print(f"  OK (fallback): {f.stat().st_size/1e6:.1f} MB")
                except Exception as e2:
                    print(f"  FAIL (fallback): {e2}")

print("\n" + "=" * 65)
print("All downloads complete.")
print(f"Saved to: {BASE}")
print("=" * 65)

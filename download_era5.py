# -*- coding: utf-8 -*-
import cdsapi
import xarray as xr
from pathlib import Path

out_dir = Path("c:/Users/24jos/climada/data/era5")
out_dir.mkdir(parents=True, exist_ok=True)

LAT, LON = 34.7979, 117.2571
area = [LAT+0.5, LON-0.5, LAT-0.5, LON+0.5]  # N W S E
MONTHS = [f"{m:02d}" for m in range(1, 13)]
DAYS   = [f"{d:02d}" for d in range(1, 32)]

c = cdsapi.Client()

def download_year(variable, statistic, year, fpath):
    """단일 연도 다운로드"""
    c.retrieve(
        "derived-era5-single-levels-daily-statistics",
        {
            "product_type": "reanalysis",
            "variable": variable,
            "daily_statistic": statistic,
            "year": [str(year)],
            "month": MONTHS,
            "day": DAYS,
            "time_zone": "utc+00:00",
            "frequency": "1_hourly",
            "area": area,
            "format": "netcdf",
        },
        str(fpath)
    )

def download_all_years(tag, fname_final, variable, statistic, start=1950, end=2023):
    """연도별로 나눠 다운로드 후 병합"""
    final = out_dir / fname_final
    if final.exists():
        print(f"  Already exists: {final.name} ({final.stat().st_size/1e6:.1f} MB)")
        return

    tmp_dir = out_dir / "tmp" / tag
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 1단계: 연도별 다운로드
    parts = []
    for yr in range(start, end + 1):
        fyr = tmp_dir / f"{tag}_{yr}.nc"
        if not fyr.exists():
            print(f"    {yr} ...", end=" ", flush=True)
            try:
                download_year(variable, statistic, yr, fyr)
                print(f"OK ({fyr.stat().st_size/1e6:.1f} MB)")
            except Exception as e:
                print(f"FAIL: {e}")
                continue
        parts.append(fyr)

    # 2단계: 병합
    existing = [p for p in parts if p.exists()]
    if not existing:
        print(f"  No files downloaded for {tag}")
        return
    print(f"  Merging {len(existing)} files -> {final.name} ...", flush=True)
    ds = xr.open_mfdataset([str(p) for p in sorted(existing)], combine="by_coords")
    ds.to_netcdf(str(final))
    print(f"  Done: {final.stat().st_size/1e6:.1f} MB")


# ============================================================
tasks = [
    # (tag,             final_fname,                              variable,                      statistic)
    ("tmax",   "era5_tmax_zaozhuang_1950_2023.nc",   "2m_temperature",               "daily_maximum"),  # 폭염
    ("precip", "era5_precip_zaozhuang_1950_2023.nc", "total_precipitation",           "daily_mean"),     # 집중호우
    ("tmin",   "era5_tmin_zaozhuang_1950_2023.nc",   "2m_temperature",               "daily_minimum"),  # 한파
    ("pet",    "era5_pet_zaozhuang_1950_2023.nc",    "potential_evaporation",         "daily_mean"),     # 가뭄
    ("snow",   "era5_snowfall_zaozhuang_1950_2023.nc","snowfall",                     "daily_mean"),     # 폭설
    ("u10",    "era5_u10_zaozhuang_1950_2023.nc",    "10m_u_component_of_wind",       "daily_maximum"),  # 강풍
    ("v10",    "era5_v10_zaozhuang_1950_2023.nc",    "10m_v_component_of_wind",       "daily_maximum"),  # 강풍
    ("tmean",  "era5_tmean_zaozhuang_1950_2023.nc",  "2m_temperature",               "daily_mean"),     # 평균온도
]

labels = ["폭염(Tmax)", "집중호우(Precip)", "한파(Tmin)", "가뭄(PET)",
          "폭설(Snow)", "강풍 U10", "강풍 V10", "평균온도(Tmean)"]

print("=" * 60)
print(f"ERA5 download  {LAT}N {LON}E  1950-2023")
print(f"Save: {out_dir}")
print("=" * 60)

for i, (tag, fname, var, stat) in enumerate(tasks):
    print(f"\n[{i+1}/{len(tasks)}] {labels[i]}")
    download_all_years(tag, fname, var, stat)

print("\n" + "=" * 60)
print("ERA5 complete. Run download_slr.py for sea level rise.")
print("=" * 60)

"""
해수면 상승 (Sea Level Rise) 데이터 다운로드
소스: Copernicus CDS — Sea level gridded data (satellite altimetry, 1993~현재)
좌표: Zaozhuang 인근 황해 (34.7979N, 117.2571E) → 가장 가까운 해안은 ~400km
      → 발해만 / 황해 대표 격자 사용
"""
import cdsapi
from pathlib import Path

out_dir = Path("c:/Users/24jos/climada/data/sea_level")
out_dir.mkdir(parents=True, exist_ok=True)

c = cdsapi.Client()

# ── 1. 위성 고도계 월별 해수면 이상 (1993~2023) ─────────────────────────────
# 데이터셋: satellite-sea-level-global (Copernicus CDS)
print("[1/2] 위성 해수면 이상 (SSH anomaly) 1993~2023 다운로드 중...")
f1 = out_dir / "slr_ssh_anomaly_global_1993_2023.nc"
if not f1.exists():
    c.retrieve(
        "satellite-sea-level-global",
        {
            "version": "vDT2021",
            "variable": "daily_mean_sea_level_anomaly",
            "year": [str(y) for y in range(1993, 2024)],
            "month": [f"{m:02d}" for m in range(1, 13)],
            "day":   [f"{d:02d}" for d in range(1, 32)],
            "format": "zip",
        },
        str(f1)
    )
    print(f"  완료: {f1.stat().st_size/1e6:.1f} MB")
else:
    print(f"  이미 존재: {f1.name} ({f1.stat().st_size/1e6:.1f} MB)")

# ── 2. CMIP6 기후 시나리오별 해수면 투영 (2015~2100) ────────────────────────
# 데이터셋: projections-cmip6 (Copernicus CDS)
# 변수: sea_surface_height_above_geoid (zos)
print("\n[2/2] CMIP6 해수면 투영 SSP2-4.5 / SSP5-8.5 다운로드 중...")

for ssp, label in [("ssp245", "SSP2-4.5"), ("ssp585", "SSP5-8.5")]:
    f = out_dir / f"slr_cmip6_{ssp}_2015_2100.nc"
    if f.exists():
        print(f"  이미 존재: {f.name} ({f.stat().st_size/1e6:.1f} MB)")
        continue
    print(f"  {label} 다운로드 중...", flush=True)
    c.retrieve(
        "projections-cmip6",
        {
            "temporal_resolution": "monthly",
            "experiment": ssp,
            "level": "single_levels",
            "variable": "sea_surface_height_above_geoid",
            "model": "awi_cm_1_1_mr",
            "date": "2015-01-01/2100-12-31",
            "area": [42, 110, 28, 130],  # 황해/발해 영역 N/W/S/E
            "format": "netcdf",
        },
        str(f)
    )
    print(f"  완료: {f.stat().st_size/1e6:.1f} MB")

print("\n해수면 상승 다운로드 완료")
print(f"저장 위치: {out_dir}")

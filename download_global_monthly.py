# -*- coding: utf-8 -*-
"""
GLOBAL Monthly CMIP6 Download
Covers: Europe, North America, Southeast Asia, South Asia,
        Middle East, South America, Australia, Africa
Variables: 12  |  Scenarios: SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5
Period: 2015-2100  |  Models: 7 ensemble
"""
import cdsapi, sys
from pathlib import Path

c = cdsapi.Client()

# ── 지역 정의 ─────────────────────────────────────────────────────────────────
# area: [N, W, S, E]  (CDS 규약)
REGIONS = {
    # Priority 1 — 유럽
    'europe_west':      {'area': [62, -12, 35,  25]},  # UK, FR, DE, ES, IT, NL
    'europe_east':      {'area': [62,  25, 35,  45]},  # PL, CZ, RO, TR (북부)

    # Priority 2 — 북미
    'north_america_east': {'area': [50, -95, 25, -60]},  # US 동부, 남동부
    'north_america_west': {'area': [50,-125, 25, -95]},  # US 서부, 텍사스

    # Priority 3 — 동남아시아
    'southeast_asia':   {'area': [25,  95,  0, 130]},  # TH, VN, MY, ID

    # Priority 4 — 남아시아
    'south_asia':       {'area': [35,  65,  5,  95]},  # IN, BD, PK, LK

    # Priority 5 — 중동
    'middle_east':      {'area': [42,  25, 12,  65]},  # SA, UAE, TR, IR, IQ

    # Priority 6 — 남미
    'south_america':    {'area': [10, -82,-40, -35]},  # BR, CL, AR, CO, PE

    # Priority 7 — 호주/오세아니아
    'australia':        {'area': [ 5, 110,-45, 155]},  # AU, NZ

    # Priority 8 — 아프리카
    'africa_north':     {'area': [38, -18, 10,  50]},  # 북아프리카 + 동아프리카
    'africa_south':     {'area': [10,  10,-35,  42]},  # 남아프리카
}

VARIABLES = [
    ('tas',     'near_surface_air_temperature'),
    ('tasmax',  'daily_maximum_near_surface_air_temperature'),
    ('tasmin',  'daily_minimum_near_surface_air_temperature'),
    ('pr',      'precipitation'),
    ('evspsbl', 'evaporation_including_sublimation_and_transpiration'),
    ('prsn',    'snowfall_flux'),
    ('sfcWind', 'near_surface_wind_speed'),
    ('zos',     'sea_surface_height_above_geoid'),
    ('mrro',    'total_runoff'),
    ('mrsos',   'moisture_in_upper_portion_of_soil_column'),
    ('huss',    'near_surface_specific_humidity'),
    ('rsds',    'surface_downwelling_shortwave_radiation'),
]
SCENARIOS = ['ssp1_2_6', 'ssp2_4_5', 'ssp3_7_0', 'ssp5_8_5']
MODELS = ['access_cm2', 'miroc6', 'miroc_es2l',
          'fgoals_f3_l', 'fgoals_g3', 'kiost_esm', 'bcc_csm2_mr']
YEARS  = [str(y) for y in range(2015, 2101)]
MONTHS = [f'{m:02d}' for m in range(1, 13)]

BASE = Path('c:/Users/24jos/climada/data/global')

# ── 지역 필터 (커맨드라인 인수로 특정 지역만 실행 가능) ────────────────────────
target_regions = sys.argv[1:] if len(sys.argv) > 1 else list(REGIONS.keys())
regions_to_run = {k: v for k, v in REGIONS.items() if k in target_regions}

total = len(regions_to_run) * len(SCENARIOS) * len(VARIABLES)
n = 0

for region_name, rconf in regions_to_run.items():
    print(f'\n{"="*65}')
    print(f'Region: {region_name}  |  Area: {rconf["area"]}')
    print(f'{"="*65}')

    for ssp in SCENARIOS:
        ssp_dir = BASE / region_name / ssp
        ssp_dir.mkdir(parents=True, exist_ok=True)

        for short, long_name in VARIABLES:
            n += 1
            fname = f'{short}_{ssp}_7models_2015_2100.zip'
            out_path = ssp_dir / fname
            print(f'\n[{n}/{total}] {region_name} | {ssp} | {short}')

            if out_path.exists() and out_path.stat().st_size > 50000:
                print(f'  Skip ({out_path.stat().st_size/1e6:.1f} MB)')
                continue

            try:
                c.retrieve('projections-cmip6', {
                    'format':               'zip',
                    'temporal_resolution':  'monthly',
                    'experiment':           ssp,
                    'level':                'single_levels',
                    'variable':             long_name,
                    'model':                MODELS,
                    'year':                 YEARS,
                    'month':                MONTHS,
                    'area':                 rconf['area'],
                }, str(out_path))
                print(f'  OK: {out_path.stat().st_size/1e6:.1f} MB')
            except Exception as e:
                print(f'  FAIL: {e}')
                # 3-model fallback
                try:
                    c.retrieve('projections-cmip6', {
                        'format':               'zip',
                        'temporal_resolution':  'monthly',
                        'experiment':           ssp,
                        'level':                'single_levels',
                        'variable':             long_name,
                        'model':                ['access_cm2','miroc6','bcc_csm2_mr'],
                        'year':                 YEARS,
                        'month':                MONTHS,
                        'area':                 rconf['area'],
                    }, str(out_path))
                    print(f'  OK (3-model fallback): {out_path.stat().st_size/1e6:.1f} MB')
                except Exception as e2:
                    print(f'  FAIL (fallback): {e2}')

print(f'\n\nGlobal monthly download complete for: {list(regions_to_run.keys())}')
print(f'Saved to: {BASE}')

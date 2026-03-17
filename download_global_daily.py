# -*- coding: utf-8 -*-
"""
GLOBAL Daily CMIP6 Download
Variables: tasmax, tasmin, pr  (daily — ETCCDI 계산용)
Scenarios: SSP2-4.5, SSP5-8.5 (핵심 2개)
Regions: 글로벌 11개 지역
"""
import cdsapi, sys
from pathlib import Path

c = cdsapi.Client()

REGIONS = {
    'europe_west':        {'area': [62, -12, 35,  25]},
    'europe_east':        {'area': [62,  25, 35,  45]},
    'north_america_east': {'area': [50, -95, 25, -60]},
    'north_america_west': {'area': [50,-125, 25, -95]},
    'southeast_asia':     {'area': [25,  95,  0, 130]},
    'south_asia':         {'area': [35,  65,  5,  95]},
    'middle_east':        {'area': [42,  25, 12,  65]},
    'south_america':      {'area': [10, -82,-40, -35]},
    'australia':          {'area': [ 5, 110,-45, 155]},
    'africa_north':       {'area': [38, -18, 10,  50]},
    'africa_south':       {'area': [10,  10,-35,  42]},
}
VARIABLES_DAILY = [
    ('tasmax', 'daily_maximum_near_surface_air_temperature'),
    ('tasmin', 'daily_minimum_near_surface_air_temperature'),
    ('pr',     'precipitation'),
]
SCENARIOS = ['ssp2_4_5', 'ssp5_8_5']
MODELS = ['access_cm2', 'miroc6', 'bcc_csm2_mr']
YEARS  = [str(y) for y in range(2015, 2101)]
MONTHS = [f'{m:02d}' for m in range(1, 13)]
DAYS   = [f'{d:02d}' for d in range(1, 32)]

BASE = Path('c:/Users/24jos/climada/data/global_daily')

target_regions = sys.argv[1:] if len(sys.argv) > 1 else list(REGIONS.keys())
regions_to_run = {k: v for k, v in REGIONS.items() if k in target_regions}

total = len(regions_to_run) * len(SCENARIOS) * len(VARIABLES_DAILY)
n = 0

for region_name, rconf in regions_to_run.items():
    print(f'\n{"="*65}')
    print(f'Region: {region_name}')
    print(f'{"="*65}')
    for ssp in SCENARIOS:
        ssp_dir = BASE / region_name / ssp
        ssp_dir.mkdir(parents=True, exist_ok=True)
        for short, long_name in VARIABLES_DAILY:
            n += 1
            fname = f'{short}_daily_{ssp}_3models_2015_2100.zip'
            out_path = ssp_dir / fname
            print(f'\n[{n}/{total}] {region_name} | {ssp} | {short}')
            if out_path.exists() and out_path.stat().st_size > 100000:
                print(f'  Skip ({out_path.stat().st_size/1e6:.1f} MB)')
                continue
            try:
                c.retrieve('projections-cmip6', {
                    'format': 'zip', 'temporal_resolution': 'daily',
                    'experiment': ssp, 'level': 'single_levels',
                    'variable': long_name, 'model': MODELS,
                    'year': YEARS, 'month': MONTHS, 'day': DAYS,
                    'area': rconf['area'],
                }, str(out_path))
                print(f'  OK: {out_path.stat().st_size/1e6:.1f} MB')
            except Exception as e:
                print(f'  FAIL: {e}')

print('Global daily download complete.')

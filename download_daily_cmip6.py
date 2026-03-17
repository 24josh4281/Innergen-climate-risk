# -*- coding: utf-8 -*-
"""
STEP 3: Daily CMIP6 download for ETCCDI indices
Variables: tasmax, tasmin, pr  (daily resolution)
Scenarios: SSP2-4.5, SSP5-8.5
Regions:   korea_china, japan, philippines
"""
import cdsapi, os
from pathlib import Path

c = cdsapi.Client()

SCENARIOS = ['ssp2_4_5', 'ssp5_8_5']
VARIABLES_DAILY = [
    ('tasmax', 'daily_maximum_near_surface_air_temperature'),
    ('tasmin', 'daily_minimum_near_surface_air_temperature'),
    ('pr',     'precipitation'),
]
MODELS = ['access_cm2', 'miroc6', 'bcc_csm2_mr']

REGIONS = {
    'korea_china': {
        'area': [42, 110, 30, 132],
        'base': Path('c:/Users/24jos/climada/data/scenarios_v2/daily'),
    },
    'japan': {
        'area': [42, 132, 30, 146],
        'base': Path('c:/Users/24jos/climada/data/scenarios_v2/daily/japan'),
    },
    'philippines': {
        'area': [22, 118, 10, 128],
        'base': Path('c:/Users/24jos/climada/data/scenarios_v2/daily/philippines'),
    },
}

YEARS  = [str(y) for y in range(2015, 2101)]
MONTHS = [f'{m:02d}' for m in range(1, 13)]
DAYS   = [f'{d:02d}' for d in range(1, 32)]

total = len(REGIONS) * len(SCENARIOS) * len(VARIABLES_DAILY)
n = 0

for region_name, rconf in REGIONS.items():
    print(f'\n{"="*60}')
    print(f'Region: {region_name}  |  Area: {rconf["area"]}')
    print(f'{"="*60}')
    for ssp in SCENARIOS:
        ssp_dir = rconf['base'] / ssp
        ssp_dir.mkdir(parents=True, exist_ok=True)
        for short, long_name in VARIABLES_DAILY:
            n += 1
            fname = f'{short}_daily_{ssp}_3models_2015_2100.zip'
            out_path = ssp_dir / fname
            print(f'\n[{n}/{total}] {region_name} | {ssp} | {short} (daily)')
            if out_path.exists() and out_path.stat().st_size > 100000:
                print(f'  Skip: {fname}  {out_path.stat().st_size/1e6:.1f} MB')
                continue
            print('  Downloading...')
            try:
                c.retrieve('projections-cmip6', {
                    'format': 'zip',
                    'temporal_resolution': 'daily',
                    'experiment': ssp,
                    'level': 'single_levels',
                    'variable': long_name,
                    'model': MODELS,
                    'year': YEARS,
                    'month': MONTHS,
                    'day': DAYS,
                    'area': rconf['area'],
                }, str(out_path))
                sz = out_path.stat().st_size
                print(f'  OK: {sz/1e6:.1f} MB')
            except Exception as e:
                print(f'  FAIL: {e}')
                try:
                    c.retrieve('projections-cmip6', {
                        'format': 'zip',
                        'temporal_resolution': 'daily',
                        'experiment': ssp,
                        'level': 'single_levels',
                        'variable': long_name,
                        'model': ['access_cm2'],
                        'year': YEARS,
                        'month': MONTHS,
                        'day': DAYS,
                        'area': rconf['area'],
                    }, str(out_path))
                    sz = out_path.stat().st_size
                    print(f'  OK (fallback): {sz/1e6:.1f} MB')
                except Exception as e2:
                    print(f'  FAIL (fallback): {e2}')

print('\n\nDaily CMIP6 download complete.')
print('Saved to: c:/Users/24jos/climada/data/scenarios_v2/daily/')

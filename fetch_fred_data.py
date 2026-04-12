"""
Fetches CPI, Mortgage Rate, and House Price Index data from FRED
and writes fred_data.json for use by housing_inflation_mortgage_v2.html.

Local usage:
    export FRED_API_KEY=your_key_here
    python3 fetch_fred_data.py

GitHub Actions: set FRED_API_KEY as a repository secret.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime
from urllib.parse import urlencode

API_KEY = os.environ.get('FRED_API_KEY', '')
if not API_KEY:
    sys.exit('Error: FRED_API_KEY environment variable is not set.')

SERIES = {
    'cpi':      {'id': 'CPIAUCSL',     'start': 1946, 'yoy': True},
    'mortgage': {'id': 'MORTGAGE30US', 'start': 1971, 'yoy': False},
    'hpi':      {'id': 'USSTHPI',      'start': 1974, 'yoy': True},
}

def fred_fetch_annual(series_id, start_year):
    params = urlencode({
        'series_id':          series_id,
        'api_key':            API_KEY,
        'file_type':          'json',
        'frequency':          'a',
        'aggregation_method': 'avg',
        'observation_start':  f'{start_year}-01-01',
        'sort_order':         'asc',
    })
    url = f'https://api.stlouisfed.org/fred/series/observations?{params}'
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = json.loads(resp.read())
    if 'error_message' in data:
        raise RuntimeError(f"FRED error for {series_id}: {data['error_message']}")
    return [
        {'year': int(obs['date'][:4]), 'value': float(obs['value'])}
        for obs in data['observations']
        if obs['value'] != '.'
    ]

def yoy(levels):
    return [
        {'year': levels[i]['year'],
         'value': round((levels[i]['value'] / levels[i-1]['value'] - 1) * 100, 3)}
        for i in range(1, len(levels))
    ]

print('Fetching data from FRED...')
output = {'fetched_at': datetime.now().strftime('%B %d, %Y')}

for key, cfg in SERIES.items():
    print(f'  {key.upper()} ({cfg["id"]})...', end=' ', flush=True)
    raw = fred_fetch_annual(cfg['id'], cfg['start'])
    output[key] = yoy(raw) if cfg['yoy'] else raw
    print(f'{output[key][0]["year"]}–{output[key][-1]["year"]}  ({len(output[key])} records)')

with open('fred_data.json', 'w') as f:
    json.dump(output, f)

print('\nSaved fred_data.json')
print(f'  CPI:      {output["cpi"][0]["year"]}–{output["cpi"][-1]["year"]}')
print(f'  Mortgage: {output["mortgage"][0]["year"]}–{output["mortgage"][-1]["year"]}')
print(f'  HPI:      {output["hpi"][0]["year"]}–{output["hpi"][-1]["year"]}')

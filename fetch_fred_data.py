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
    'cpi':      {'id': 'CPIAUCSL',     'start': 1946, 'yoy': False, 'jan_yoy': True},
    'mortgage': {'id': 'MORTGAGE30US', 'start': 1971, 'yoy': False},
    'hpi':      {'id': 'CSUSHPISA',    'start': 1986, 'yoy': False, 'jan_yoy': True},  # S&P/Case-Shiller, monthly from Jan 1987
    'nasdaq':   {'id': 'NASDAQCOM',   'start': 1970, 'yoy': False, 'jan_yoy': True},  # NASDAQ Composite (from 1971)
}

def fred_fetch_monthly(series_id, start_year):
    params = urlencode({
        'series_id':          series_id,
        'api_key':            API_KEY,
        'file_type':          'json',
        'frequency':          'm',
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
        {'date': obs['date'][:7], 'value': float(obs['value'])}  # 'YYYY-MM'
        for obs in data['observations']
        if obs['value'] != '.'
    ]

def yoy_monthly(levels):
    """YoY: compare each month to the same month 12 months prior, matched by date string."""
    lookup = {d['date']: d['value'] for d in levels}
    result = []
    for obs in levels:
        y, m = obs['date'].split('-')
        prior = f'{int(y)-1}-{m}'
        if prior in lookup and lookup[prior] != 0:
            result.append({
                'date':  obs['date'],
                'value': round((obs['value'] / lookup[prior] - 1) * 100, 3)
            })
    return result

def yoy_january(levels):
    """Forward 1-year return: labeled at entry date, value = (price_12mo_later/price_now - 1)*100."""
    lookup = {d['date']: d['value'] for d in levels}
    result = []
    for obs in levels:
        y, m = obs['date'].split('-')
        next_date = f'{int(y)+1}-{m}'
        if next_date in lookup and obs['value'] != 0:
            result.append({
                'date':  obs['date'],          # label = start of window
                'value': round((lookup[next_date] / obs['value'] - 1) * 100, 3)
            })
    return result

print('Fetching data from FRED...')
output = {'fetched_at': datetime.now().strftime('%B %d, %Y')}

for key, cfg in SERIES.items():
    print(f'  {key.upper()} ({cfg["id"]})...', end=' ', flush=True)
    raw = fred_fetch_monthly(cfg['id'], cfg['start'])
    if cfg.get('jan_yoy'):
        output[key] = yoy_january(raw)
    elif cfg['yoy']:
        output[key] = yoy_monthly(raw)
    else:
        output[key] = raw
    print(f'{output[key][0]["date"]}\u2013{output[key][-1]["date"]}  ({len(output[key])} records)')

with open('fred_data.json', 'w') as f:
    json.dump(output, f)

print('\nSaved fred_data.json')
print(f'  CPI:      {output["cpi"][0]["date"]}\u2013{output["cpi"][-1]["date"]}')
print(f'  Mortgage: {output["mortgage"][0]["date"]}\u2013{output["mortgage"][-1]["date"]}')
print(f'  HPI:      {output["hpi"][0]["date"]}\u2013{output["hpi"][-1]["date"]}')
print(f'  NASDAQ:   {output["nasdaq"][0]["date"]}\u2013{output["nasdaq"][-1]["date"]}')

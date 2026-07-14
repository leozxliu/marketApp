"""
Fetches CPI, Mortgage Rate, and House Price Index data from FRED
and writes fred_data.json for use by housing_inflation_mortgage_v2.html.

Local usage:
    export FRED_API_KEY=your_key_here
    python3 fetch_fred_data.py

GitHub Actions: set FRED_API_KEY as a repository secret.
"""

import csv
import io
import json
import os
import sys
import urllib.request
from datetime import datetime
from urllib.parse import urlencode

# Monthly S&P 500 level, auto-updated mirror of Robert Shiller's dataset (back to 1871).
# Used instead of FRED's own SP500 series, which is licensed to only ~10yr of history.
SP500_HISTORY_URL = 'https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv'
SP500_START_YEAR = 1946  # matches CPI, the earliest-starting series on the main chart

# Costco (COST) monthly close from Yahoo Finance — FRED does not carry
# individual equities. Trades since Jul 1986.
COST_SYMBOL = 'COST'
COST_START_YEAR = 1986

API_KEY = os.environ.get('FRED_API_KEY', '')
if not API_KEY:
    sys.exit('Error: FRED_API_KEY environment variable is not set.')

SERIES = {
    'cpi':      {'id': 'CPIAUCSL',     'start': 1946, 'yoy': True},
    'mortgage': {'id': 'MORTGAGE30US', 'start': 1971, 'yoy': False},
    'hpi':      {'id': 'CSUSHPISA',    'start': 1986, 'yoy': True},  # S&P/Case-Shiller, monthly from Jan 1987
    'nasdaq':   {'id': 'NASDAQCOM',   'start': 1970, 'yoy': True},  # NASDAQ Composite (from 1971)
    # Raw price levels for the Overview levels chart (same sources, no YoY transform)
    'hpi_level':    {'id': 'CSUSHPISA', 'start': 1986, 'yoy': False},
    'nasdaq_level': {'id': 'NASDAQCOM', 'start': 1970, 'yoy': False},
    # S&P 500 is fetched separately below — FRED's own SP500 series is licensed
    # to only ~10yr of trailing history, far shorter than our other series.
    # City-level HPI (trailing YoY %)
    'hpi_sf':   {'id': 'SFXRSA',         'start': 1990, 'yoy': True},            # S&P/Case-Shiller San Francisco
    'hpi_sd':   {'id': 'SDXRSA',         'start': 1990, 'yoy': True},            # S&P/Case-Shiller San Diego
    'hpi_sea':  {'id': 'SEXRSA',         'start': 1990, 'yoy': True},            # S&P/Case-Shiller Seattle
    'hpi_dal':  {'id': 'DAXRSA',         'start': 2000, 'yoy': True},            # S&P/Case-Shiller Dallas
    'hpi_atl':  {'id': 'ATXRSA',         'start': 1991, 'yoy': True},            # S&P/Case-Shiller Atlanta
    'hpi_aus':  {'id': 'ATNHPIUS12420Q', 'start': 1990, 'yoy': True, 'freq': 'q'},  # FHFA Austin (quarterly)
    'hpi_tal':  {'id': 'ATNHPIUS45220Q', 'start': 1990, 'yoy': True, 'freq': 'q'},  # FHFA Tallahassee (quarterly)
    # City-level HPI raw index levels (for the estimated-price levels chart)
    'hpi_sf_level':  {'id': 'SFXRSA',         'start': 1990, 'yoy': False},
    'hpi_sd_level':  {'id': 'SDXRSA',         'start': 1990, 'yoy': False},
    'hpi_sea_level': {'id': 'SEXRSA',         'start': 1990, 'yoy': False},
    'hpi_dal_level': {'id': 'DAXRSA',         'start': 2000, 'yoy': False},
    'hpi_atl_level': {'id': 'ATXRSA',         'start': 1991, 'yoy': False},
    'hpi_aus_level': {'id': 'ATNHPIUS12420Q', 'start': 1990, 'yoy': False, 'freq': 'q'},
    'hpi_tal_level': {'id': 'ATNHPIUS45220Q', 'start': 1990, 'yoy': False, 'freq': 'q'},
    # City-level CPI for Rent of Primary Residence (index, 1982-84=100).
    # Monthly CUUR* series; San Diego is only published semiannually (CUUS*).
    'rent_sf':  {'id': 'CUURA422SAH1', 'start': 1990, 'yoy': False},               # SF-Oakland area
    'rent_sd':  {'id': 'CUUSA424SAH1', 'start': 1990, 'yoy': False, 'freq': 'sa'}, # San Diego (semiannual)
    'rent_sea': {'id': 'CUURA423SAH1', 'start': 1990, 'yoy': False},               # Seattle-Tacoma area
    'rent_dal': {'id': 'CUURA316SAH1', 'start': 1990, 'yoy': False},               # Dallas-Fort Worth area
    'rent_atl': {'id': 'CUURA319SAH1', 'start': 1990, 'yoy': False},               # Atlanta area
    'rent_aus': {'id': 'CUUR0300SAH1', 'start': 1990, 'yoy': False},               # South urban (proxy for Austin)
}

def fred_fetch(series_id, start_year, freq='m'):
    params = urlencode({
        'series_id':          series_id,
        'api_key':            API_KEY,
        'file_type':          'json',
        'frequency':          freq,
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

def fetch_sp500_history(start_year):
    with urllib.request.urlopen(SP500_HISTORY_URL, timeout=20) as resp:
        text = resp.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))
    return [
        {'date': row['Date'][:7], 'value': float(row['SP500'])}
        for row in reader
        if row['Date'][:4].isdigit() and int(row['Date'][:4]) >= start_year and row['SP500']
    ]

def fetch_yahoo_monthly(symbol, start_year):
    """Monthly close prices from Yahoo Finance's chart API (last close per month)."""
    p1 = int(datetime(start_year, 1, 1).timestamp())
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
           f'?period1={p1}&period2=9999999999&interval=1mo')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())
    res = data['chart']['result'][0]
    ts = res['timestamp']
    close = res['indicators']['quote'][0]['close']
    by_month = {}
    for t, c in zip(ts, close):
        if c is None:
            continue
        month = datetime.utcfromtimestamp(t).strftime('%Y-%m')
        by_month[month] = round(c, 2)  # last close in the month wins
    return [{'date': m, 'value': v} for m, v in sorted(by_month.items())]

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
    try:
        raw = fred_fetch(cfg['id'], cfg['start'], cfg.get('freq', 'm'))
        if cfg.get('jan_yoy'):
            output[key] = yoy_january(raw)
        elif cfg['yoy']:
            output[key] = yoy_monthly(raw)
        else:
            output[key] = raw
        print(f'{output[key][0]["date"]}–{output[key][-1]["date"]}  ({len(output[key])} records)')
    except Exception as exc:
        print(f'SKIPPED — {exc}')
        output[key] = []

print('  SP500 (Shiller/GitHub mirror)...', end=' ', flush=True)
try:
    raw = fetch_sp500_history(SP500_START_YEAR)
    output['sp500'] = yoy_monthly(raw)
    output['sp500_level'] = raw
    print(f'{output["sp500"][0]["date"]}–{output["sp500"][-1]["date"]}  ({len(output["sp500"])} records)')
except Exception as exc:
    print(f'SKIPPED — {exc}')
    output['sp500'] = []
    output['sp500_level'] = []

print('  COST (Yahoo Finance)...', end=' ', flush=True)
try:
    raw = fetch_yahoo_monthly(COST_SYMBOL, COST_START_YEAR)
    output['cost'] = yoy_monthly(raw)
    output['cost_level'] = raw
    print(f'{output["cost"][0]["date"]}–{output["cost"][-1]["date"]}  ({len(output["cost"])} records)')
except Exception as exc:
    print(f'SKIPPED — {exc}')
    output['cost'] = []
    output['cost_level'] = []

with open('fred_data.json', 'w') as f:
    json.dump(output, f)

print('\nSaved fred_data.json')
print(f'  CPI:      {output["cpi"][0]["date"]}\u2013{output["cpi"][-1]["date"]}')
print(f'  Mortgage: {output["mortgage"][0]["date"]}\u2013{output["mortgage"][-1]["date"]}')
print(f'  HPI:      {output["hpi"][0]["date"]}\u2013{output["hpi"][-1]["date"]}')
print(f'  NASDAQ:   {output["nasdaq"][0]["date"]}\u2013{output["nasdaq"][-1]["date"]}')
print(f'  S&P 500:  {output["sp500"][0]["date"]}\u2013{output["sp500"][-1]["date"]}')
for city_key in ('hpi_sf', 'hpi_sd', 'hpi_sea', 'hpi_dal', 'hpi_atl', 'hpi_aus', 'hpi_tal'):
    d = output[city_key]
    if d:
        print(f'  {city_key.upper():10s} {d[0]["date"]}\u2013{d[-1]["date"]}  ({len(d)} records)')
    else:
        print(f'  {city_key.upper():10s} (no data)')
for rent_key in ('rent_sf', 'rent_sd', 'rent_sea', 'rent_dal', 'rent_atl', 'rent_aus'):
    d = output.get(rent_key, [])
    if d:
        print(f'  {rent_key.upper():10s} {d[0]["date"]}\u2013{d[-1]["date"]}  ({len(d)} records)')
    else:
        print(f'  {rent_key.upper():10s} (no data)')

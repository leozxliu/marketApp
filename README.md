# US Housing & Economic Indicators

An interactive chart tracking three key US economic indicators from the earliest available data through the present.

**Live site → [leozxliu.github.io/marketApp](https://leozxliu.github.io/marketApp)**

![Chart preview showing House Price Index, CPI Inflation, and 30-Year Mortgage Rate](https://leozxliu.github.io/marketApp/preview.png)

---

## Indicators

| Series | Source | Coverage |
|--------|--------|----------|
| House Price Index (YoY %) | FHFA Purchase-Only HPI — [FRED: USSTHPI](https://fred.stlouisfed.org/series/USSTHPI) | 1976 – present |
| Inflation Rate (YoY %) | BLS CPI All Urban Consumers — [FRED: CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL) | 1948 – present |
| 30-Year Mortgage Rate (%) | Freddie Mac PMMS — [FRED: MORTGAGE30US](https://fred.stlouisfed.org/series/MORTGAGE30US) | 1971 – present |

All data is fetched from the [FRED API](https://fred.stlouisfed.org/docs/api/fred/) (Federal Reserve Bank of St. Louis) and cached in `fred_data.json`.

---

## Features

- **Stat cards** showing the latest value for each indicator
- **Interactive range slider** to zoom into any time period
- **Quick presets** — 10Y, 20Y, 30Y, 50Y, All
- **Series toggles** — show or hide individual lines
- **Auto-updated weekly** via GitHub Actions (every Monday)

---

## Local Development

**1. Install dependencies** — only the Python standard library is required (no `pip install` needed).

**2. Get a free FRED API key** at [fredaccount.stlouisfed.org/apikeys](https://fredaccount.stlouisfed.org/apikeys).

**3. Fetch data:**
```bash
export FRED_API_KEY=your_key_here
python3 fetch_fred_data.py
```

**4. Serve locally:**
```bash
python3 -m http.server 8765
```
Then open [http://localhost:8765](http://localhost:8765).

---

## Automated Updates (GitHub Actions)

The workflow in `.github/workflows/update_fred_data.yml` runs every Monday at 06:00 UTC. It:
1. Fetches the latest data from FRED using the `FRED_API_KEY` repository secret
2. Commits the updated `fred_data.json` back to `main`
3. GitHub Pages redeploys automatically

To trigger a manual refresh: **Actions → Update FRED Data → Run workflow**.

To set up the secret in your own fork: `Settings → Secrets and variables → Actions → New repository secret` with name `FRED_API_KEY`.

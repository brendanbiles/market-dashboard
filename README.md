# Market Dashboard

A clean, auto-updating dashboard displaying key financial and economic indicators built around hard-to-visualize FRED data.

**Live Dashboard:** https://brendanbiles.github.io/market-dashboard/

## Features

- **Treasury Yield Curve** - Real-time visualization of all Treasury maturities (1M to 30Y) with a goldilocks log/linear hybrid X-axis
- **10Y-2Y Spread** - Recession indicator with inverted curve warnings
- **Economic Indicators** - Unemployment, CPI YoY, Fed Funds Rate — each with 52W/2Y/5Y/10Y/50Y range tables and percentile context
- **64-Year Yield Curve Time Machine** - Scrub through every month of Treasury history since 1962; jump to key historical events
- **Economic Trends** - Long-run charts for Fed Funds, CPI, Unemployment, and 2Y-10Y spread with synchronized time range control
- **Historical Inversion Periods** - Annotated reference covering every major yield curve inversion with Austrian economics commentary

### Auto-Refresh
- `data.json` updates every 15 minutes during market hours via GitHub Actions
- Historical data (`historical_data.json`) is updated manually by running the export pipeline locally

## Tech Stack

- **Data Source**: [FRED API](https://fred.stlouisfed.org/) (Federal Reserve Economic Data)
- **Frontend**: Vanilla HTML/CSS/JavaScript with Chart.js
- **Backend**: Python scripts + GitHub Actions automation
- **Hosting**: GitHub Pages (free, fast, reliable)

## Data Pipeline

### Current Data (`fetch_data.py` → `data.json`)
Runs automatically via GitHub Actions every 15 minutes on weekdays.

#### Treasury Yields (FRED)
- 11 maturities: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y
- Series: DGS1MO, DGS3MO, DGS6MO, DGS1, DGS2, DGS3, DGS5, DGS7, DGS10, DGS20, DGS30
- Calculates 10Y-2Y spread automatically

#### Economic Indicators (FRED)
- Unemployment Rate (`UNRATE`)
- CPI Year-over-Year (`CPIAUCSL`, units=pc1)
- Fed Funds Rate (`FEDFUNDS`)

### Historical Data (manual pipeline)
1. `backfill_historical_data.py` — populates local DuckDB from FRED
2. `export_historical_json.py` — exports to `historical_data.json` for the dashboard

## Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/brendanbiles/market-dashboard.git
   cd market-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your FRED API key** (get one at https://fred.stlouisfed.org/docs/api/api_key.html)
   ```bash
   # Windows
   set FRED_API_KEY=your_key_here

   # Mac/Linux
   export FRED_API_KEY=your_key_here
   ```

4. **Fetch current data**
   ```bash
   python fetch_data.py
   ```

5. **Open dashboard**
   - Simply open `index.html` in your browser
   - Or use a local server: `python -m http.server 8000`

## Deployment

### Setup Steps

1. **Fork/clone this repo to your GitHub account**

2. **Add FRED API key as a GitHub Secret**
   - Go to your repo → Settings → Secrets and variables → Actions
   - Add new secret: `FRED_API_KEY` with your key

3. **Enable GitHub Pages**
   - Go to Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main` / root
   - Save

4. **Done!** GitHub Actions will run `fetch_data.py` every 15 minutes and push updated `data.json` automatically.

## Cost

**$0/month** - Fully hosted on GitHub's free tier:
- GitHub Actions: 2,000 minutes/month free (this uses ~30 min/month)
- GitHub Pages: Free for public repos
- FRED API: Free (no rate limits for personal use)

## Design Philosophy

**Ruthlessly minimal.** Focused on hard-to-visualize economic data that takes effort to find elsewhere. Deliberately excludes market indices and tickers — those are too easy to find already.

## Author

Built by [Brendan Biles](https://github.com/brendanbiles)

---

*Data provided by Federal Reserve Economic Data (FRED). Not investment advice.*

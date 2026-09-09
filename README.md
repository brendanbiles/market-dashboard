# Market Dashboard

A clean, auto-updating dashboard displaying key financial and economic indicators built around hard-to-visualize FRED data.

**Live Dashboard:** https://markets.brendanbiles.com

## Features

- **Treasury Yield Curve** - Real-time visualization of all Treasury maturities (1M to 30Y) with a goldilocks log/linear hybrid X-axis
- **Curve shape classification** - Every curve scored normal / flat / inverted, colour-coded green / amber / red. See [Classifying the curve](#classifying-the-curve)
- **Economic Indicators** - Unemployment, CPI YoY, Fed Funds Rate — each with 52W/2Y/5Y/10Y/50Y range tables and percentile context
- **64-Year Yield Curve Time Machine** - Scrub through all 16,154 trading days since Jan 2 1962, day by day; decade-marked timeline, jump-to-event buttons, and a 30-second time-lapse on a fixed 0-18% axis so the shape is comparable across eras
- **Economic Trends** - Long-run charts for Fed Funds, CPI, Unemployment, and 2Y-10Y spread with synchronized time range control
- **Historical Inversion Periods** - Annotated reference covering every major yield curve inversion with Austrian economics commentary

## Classifying the curve

Every frame of the Time Machine is scored into one of three states, which set
the curve's colour and the badge beneath it.

| State | Spread | Colour |
|---|---|---|
| Normal | >= +0.25% | green (`--chart-1`) |
| Flat | 0 to +0.25% | amber (`--chart-3`) |
| Inverted | < 0 | red (`--neg`) |

**Why a flat band at all.** A spread of +0.13% is the same curve as one at
-0.05%, but a two-state rule paints them green and red. The 10Y-2Y spread
crosses zero constantly - 88 crossings since 1976, 64 of them reversing inside
a month, four days running in September 2024 - so a binary indicator whipsaws
between "normal" and "recession indicator" on moves that mean nothing. Every
one of those crossings passes through the flat band, so the curve never jumps
green to red.

**Why 25bp.** It is one Fed move from inversion, and days inside the band
behave like it. On 10Y-2Y, 56.8% of them invert within six months against 6.3%
of normally sloped days, over 11.3% of the record. Widening to +0.50% dilutes
the signal to 39.5% and starts calling visibly upward-sloping curves flat;
tightening to +0.15% gains little and halves the coverage.

**The band never crosses zero.** Inversion keeps its standard definition, so
the Historical Inversion Periods section still matches the colours above it.
Flat splits "normal" in two rather than softening "inverted".

**Which spread.** 10Y-2Y is the headline measure, but FRED's 2Y series starts
1976-06-01 while the record starts 1962-01-02 - the first 3,592 days, 22% of
it, have no 10Y-2Y at all. Those days fall back to **10Y-1Y**, which covers all
16,154. The badge always names the pair actually used, so the two are labelled
rather than silently mixed, and the same 25bp band holds on the fallback: 9.0%
of days, 71.8% of which invert within six months against 7.6% of normally
sloped ones.

This matters because that era is not quiet. 1,126 of those days have the 10Y
below the 1Y - the 1965-70 run and the 1973-74 inversion that ran into the
worst postwar recession to that point, deepest at -1.88% on 1974-08-23. Before
the fallback they were all painted green.

### Auto-Refresh
- `data.json` updates every 15 minutes during market hours via GitHub Actions
- `historical_data.json` and `daily_curves.json` update daily at 02:00 UTC via GitHub Actions, after FRED publishes the prior day

## Tech Stack

- **Data Source**: [FRED API](https://fred.stlouisfed.org/) (Federal Reserve Economic Data)
- **Frontend**: Vanilla HTML/CSS/JavaScript with Chart.js
- **Backend**: Python scripts + GitHub Actions automation
- **Hosting**: Cloudflare Workers static assets (`wrangler.jsonc`), served at markets.brendanbiles.com. Every push to `main` redeploys
- **Styling**: `brand.css`, the shared layer every brendanbiles.com site loads. It is byte-identical across market-dashboard, personal-site and token-data, so site-specific tokens belong in `style.css`, not there

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

### Historical Data (`update-historical.yml`, daily at 02:00 UTC)
1. `backfill_historical_data.py` — populates DuckDB from FRED
2. `export_historical_json.py` — exports `historical_data.json` (monthly curve samples, full spread and indicator series)
3. `fetch_daily_curves.py` — exports `daily_curves.json`, the columnar daily curve history the Time Machine scrubs. Tenors start at different dates: 1Y/3Y/5Y/10Y/20Y from 1962-01-02, 7Y from 1969-07-01, 2Y from 1976-06-01, 30Y from 1977-02-15 (suspended 2002-2006), 3M/6M from 1981-09-01, 1M from 2001-07-31

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

3. **Connect the repo to Cloudflare Workers**
   - `wrangler.jsonc` serves the repository root, deliberately: this repo is
     public, so every file in it is already readable on GitHub and serving it
     adds no exposure. Credentials live in Actions secrets, never in files
   - Every push to `main` redeploys

4. **Done!** GitHub Actions pushes updated `data.json` every 15 minutes, and
   each push redeploys, so the site refreshes itself.

## Cost

**$0/month**:
- GitHub Actions: 2,000 minutes/month free (this uses ~30 min/month)
- Cloudflare Workers: free tier
- FRED API: Free (no rate limits for personal use)

## Design Philosophy

**Ruthlessly minimal.** Focused on hard-to-visualize economic data that takes effort to find elsewhere. Deliberately excludes market indices and tickers — those are too easy to find already.

## Author

Built by [Brendan Biles](https://github.com/brendanbiles)

---

*Data provided by Federal Reserve Economic Data (FRED). Not investment advice.*

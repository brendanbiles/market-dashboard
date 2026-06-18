# 📊 Market Dashboard

A clean, auto-updating dashboard displaying key financial and economic indicators. Built to democratize access to important market data for personal and small investors.

**Live Dashboard:** [Coming soon - GitHub Pages URL]

## Features

- **Treasury Yield Curve** - Real-time visualization of all Treasury maturities (1M to 30Y)
- **10Y-2Y Spread** - Recession indicator with inverted curve warnings
- **Major Market Indices** - SPY, QQQ, DIA with daily changes
- **VIX (Fear Gauge)** - Market volatility indicator
- **Economic Indicators** - Unemployment, CPI, Fed Funds Rate

### Auto-Refresh
- Data updates every 15 minutes during market hours
- Client-side refresh every 60 seconds
- Zero manual intervention required

## Tech Stack

- **Data Sources**: [FRED API](https://fred.stlouisfed.org/) (Federal Reserve Economic Data) & Yahoo Finance
- **Frontend**: Vanilla HTML/CSS/JavaScript with Chart.js
- **Backend**: Python script with GitHub Actions automation
- **Hosting**: GitHub Pages (free, fast, reliable)

## Data Collection

The `fetch_data.py` script pulls:

### Treasury Yields (FRED)
- 11 maturities: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y
- Calculates 10Y-2Y spread automatically

### Economic Indicators (FRED)
- Unemployment Rate (UNRATE)
- CPI Year-over-Year (CPALTT01USM657N)
- Fed Funds Rate (FEDFUNDS)

### Market Data (Yahoo Finance)
- S&P 500 (SPY)
- Nasdaq 100 (QQQ)
- Dow Jones (DIA)
- VIX (^VIX)

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

4. **Fetch data**
   ```bash
   python fetch_data.py
   ```

5. **Open dashboard**
   - Simply open `index.html` in your browser
   - Or use a local server: `python -m http.server 8000`

## Deployment

The dashboard uses GitHub Actions to automatically update data every 15 minutes and deploys to GitHub Pages.

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

4. **Done!** GitHub Actions will:
   - Run `fetch_data.py` every 15 minutes
   - Commit updated `data.json`
   - GitHub Pages serves the dashboard automatically

Your dashboard will be live at: `https://brendanbiles.github.io/market-dashboard/`

## Design Philosophy

**Ruthlessly minimal.** This MVP focuses on:
- ✅ The most important economic indicators
- ✅ Beautiful, clear visualization (especially yield curve)
- ✅ Zero friction access (no login, no paywall)
- ✅ Auto-updates (set and forget)

**Out of scope for V1:**
- ❌ AI commentary/analysis
- ❌ User accounts/personalization
- ❌ Historical data/charting
- ❌ Alerts/notifications

These can be added later based on user feedback!

## Cost

**$0/month** - Fully hosted on GitHub's free tier:
- GitHub Actions: 2,000 minutes/month free (this uses ~30 min/month)
- GitHub Pages: Free for public repos
- FRED API: Free (no rate limits for personal use)
- Yahoo Finance: Free

## Use Cases

Perfect for:
- 📱 Quick morning market check
- 💬 Sharing with your network ("here's what matters today")
- 📊 Teaching friends/family about market indicators
- 🔗 Linking in Slack/Discord/Twitter for context

## Contributing

This is a personal project, but suggestions welcome! Open an issue or PR.

## License

MIT License - feel free to fork and customize!

## Author

Built by [Brendan Biles](https://github.com/brendanbiles)

---

*Data provided by Federal Reserve Economic Data (FRED) and Yahoo Finance. Not investment advice.*

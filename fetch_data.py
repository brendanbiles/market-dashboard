"""
Fetch financial and economic data from FRED.
Outputs to data.json for the static dashboard to consume.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

import requests


# Configuration
FRED_API_KEY = os.getenv("FRED_API_KEY")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Treasury maturities for yield curve (FRED series IDs)
TREASURY_SERIES = {
    "1M": "DGS1MO",
    "3M": "DGS3MO",
    "6M": "DGS6MO",
    "1Y": "DGS1",
    "2Y": "DGS2",
    "3Y": "DGS3",
    "5Y": "DGS5",
    "7Y": "DGS7",
    "10Y": "DGS10",
    "20Y": "DGS20",
    "30Y": "DGS30",
}

# Other economic indicators — units=pc1 fetches YoY % change from FRED
ECONOMIC_SERIES = {
    "unemployment": {"id": "UNRATE"},
    "cpi_yoy":      {"id": "CPIAUCSL", "units": "pc1"},
    "fed_funds":    {"id": "FEDFUNDS"},
}

# Market tickers - REMOVED: Too easy to find on Google
# Focusing on hard-to-visualize economic data instead
MARKET_TICKERS = {}


def fetch_fred_series(series_id: str, limit: int = 1, units: str = None) -> Dict[str, Any]:
    """Fetch the most recent observation from a FRED series."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    if units:
        params["units"] = units
    
    response = requests.get(FRED_BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()
    
    observations = data.get("observations", [])
    if not observations:
        return {"value": None, "date": None}
    
    latest = observations[0]
    return {
        "value": float(latest["value"]) if latest["value"] != "." else None,
        "date": latest["date"],
    }


def fetch_yield_curve() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Fetch the current Treasury yield curve, with each tenor's own date.

    The observation date is returned alongside the value because a curve
    without one cannot be told apart from a stale one. FRED publishes the
    daily constant-maturity series roughly one business day in arrears, so
    "today's curve" is normally yesterday's, and the page should say so.

    Tenors can differ by a day near a holiday, so dates are kept per tenor
    rather than collapsed to one.
    """
    curve, dates = {}, {}
    for maturity, series_id in TREASURY_SERIES.items():
        data = fetch_fred_series(series_id)
        curve[maturity] = data["value"]
        dates[maturity] = data["date"]

    return curve, dates


def fetch_economic_indicators() -> Dict[str, Any]:
    """Fetch key economic indicators."""
    indicators = {}
    for name, cfg in ECONOMIC_SERIES.items():
        data = fetch_fred_series(cfg["id"], units=cfg.get("units"))
        indicators[name] = {
            "value": data["value"],
            "date": data["date"],
        }

    return indicators


def fetch_market_data() -> Dict[str, Any]:
    """Fetch current market data from Yahoo Finance."""
    # REMOVED: Market indices are too easy to find elsewhere
    # Focusing on hard-to-visualize economic data
    return {}


def calculate_spread(curve: Dict[str, Any]) -> float | None:
    """Calculate 10Y-2Y spread."""
    if curve.get("10Y") and curve.get("2Y"):
        return round(curve["10Y"] - curve["2Y"], 2)
    return None


def main():
    """Fetch all data and write to data.json."""
    print(f"Fetching data at {datetime.now(timezone.utc).isoformat()}")
    
    try:
        yield_curve, yield_curve_dates = fetch_yield_curve()
        economic = fetch_economic_indicators()
        spread = calculate_spread(yield_curve)

        # The curve's vintage is the newest tenor date present. last_updated
        # is when this script ran, which is a different thing: a run can
        # succeed and still return the same data FRED published yesterday.
        observed = [d for d in yield_curve_dates.values() if d]
        curve_as_of = max(observed) if observed else None

        output = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "yield_curve": yield_curve,
            "yield_curve_as_of": curve_as_of,
            "yield_curve_dates": yield_curve_dates,
            "spread_10y_2y": spread,
            "economic": economic,
        }
        
        with open("data.json", "w") as f:
            json.dump(output, f, indent=2)
        
        print("[OK] Data updated successfully")
        print(f"   Yield curve: {len([v for v in yield_curve.values() if v])} maturities, as of {curve_as_of}")
        print(f"   10Y-2Y spread: {spread}%")
        print(f"   Economic indicators: {len(economic)} series")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        raise


if __name__ == "__main__":
    main()

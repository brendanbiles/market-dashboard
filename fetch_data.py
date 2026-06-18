"""
Fetch financial and economic data from FRED and Yahoo Finance.
Outputs to data.json for the static dashboard to consume.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

import requests
import yfinance as yf


# Configuration
FRED_API_KEY = os.getenv("FRED_API_KEY", "8528856aa881487c4b4bdb8c0d141fc4")
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

# Other economic indicators
ECONOMIC_SERIES = {
    "unemployment": "UNRATE",
    "cpi_yoy": "CPALTT01USM657N",  # CPI YoY % change
    "fed_funds": "FEDFUNDS",
}

# Market tickers
MARKET_TICKERS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "DIA": "Dow Jones",
    "^VIX": "VIX",
}


def fetch_fred_series(series_id: str, limit: int = 1) -> Dict[str, Any]:
    """Fetch the most recent observation from a FRED series."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    
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


def fetch_yield_curve() -> Dict[str, Any]:
    """Fetch current Treasury yield curve."""
    curve = {}
    for maturity, series_id in TREASURY_SERIES.items():
        data = fetch_fred_series(series_id)
        curve[maturity] = data["value"]
    
    return curve


def fetch_economic_indicators() -> Dict[str, Any]:
    """Fetch key economic indicators."""
    indicators = {}
    for name, series_id in ECONOMIC_SERIES.items():
        data = fetch_fred_series(series_id)
        indicators[name] = {
            "value": data["value"],
            "date": data["date"],
        }
    
    return indicators


def fetch_market_data() -> Dict[str, Any]:
    """Fetch current market data from Yahoo Finance."""
    market_data = {}
    
    for ticker, name in MARKET_TICKERS.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if len(hist) >= 2:
                current_price = hist["Close"].iloc[-1]
                prev_price = hist["Close"].iloc[-2]
                change_pct = ((current_price - prev_price) / prev_price) * 100
                
                market_data[ticker] = {
                    "name": name,
                    "price": round(current_price, 2),
                    "change_pct": round(change_pct, 2),
                }
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            market_data[ticker] = {
                "name": name,
                "price": None,
                "change_pct": None,
            }
    
    return market_data


def calculate_spread(curve: Dict[str, Any]) -> float | None:
    """Calculate 10Y-2Y spread."""
    if curve.get("10Y") and curve.get("2Y"):
        return round(curve["10Y"] - curve["2Y"], 2)
    return None


def main():
    """Fetch all data and write to data.json."""
    print(f"Fetching data at {datetime.now(timezone.utc).isoformat()}")
    
    try:
        yield_curve = fetch_yield_curve()
        economic = fetch_economic_indicators()
        market = fetch_market_data()
        spread = calculate_spread(yield_curve)
        
        output = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "yield_curve": yield_curve,
            "spread_10y_2y": spread,
            "economic": economic,
            "market": market,
        }
        
        with open("data.json", "w") as f:
            json.dump(output, f, indent=2)
        
        print("[OK] Data updated successfully")
        print(f"   Yield curve: {len([v for v in yield_curve.values() if v])} maturities")
        print(f"   10Y-2Y spread: {spread}%")
        print(f"   Market data: {len([v for v in market.values() if v['price']])}/{len(market)} tickers")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        raise


if __name__ == "__main__":
    main()

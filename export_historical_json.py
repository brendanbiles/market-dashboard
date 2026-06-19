"""
Export sampled historical data to JSON for dashboard visualization.

Strategy:
- For yield curves: sample every month (reduce from 16k to ~770 data points)
- For economic indicators: include all data (already monthly, only ~800 points each)
- For spreads: sample every week for last 5 years, monthly before that
- Export to historical_data.json for client-side consumption
"""

import json
import duckdb
from datetime import datetime

YIELD_DB = "yield_curve_history.duckdb"
ECONOMIC_DB = "economic_indicators.duckdb"
OUTPUT_FILE = "historical_data.json"


def export_yield_curves_monthly():
    """Export one yield curve per month (first trading day of each month)."""
    conn = duckdb.connect(YIELD_DB)
    
    # Get first trading day of each month
    query = """
        WITH monthly_first AS (
            SELECT 
                date,
                EXTRACT(YEAR FROM date) as year,
                EXTRACT(MONTH FROM date) as month,
                ROW_NUMBER() OVER (
                    PARTITION BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date) 
                    ORDER BY date ASC
                ) as rn
            FROM yields
        )
        SELECT DISTINCT date
        FROM monthly_first
        WHERE rn = 1
        ORDER BY date
    """
    
    dates = conn.execute(query).fetchall()
    
    curves = []
    for (date,) in dates:
        # Get all maturities for this date
        query = """
            SELECT maturity, yield
            FROM yields
            WHERE date = ?
            ORDER BY 
                CASE maturity
                    WHEN '1M' THEN 1
                    WHEN '3M' THEN 2
                    WHEN '6M' THEN 3
                    WHEN '1Y' THEN 4
                    WHEN '2Y' THEN 5
                    WHEN '3Y' THEN 6
                    WHEN '5Y' THEN 7
                    WHEN '7Y' THEN 8
                    WHEN '10Y' THEN 9
                    WHEN '20Y' THEN 10
                    WHEN '30Y' THEN 11
                END
        """
        
        maturities = conn.execute(query, (date,)).fetchall()
        
        if maturities:
            curve_data = {mat: round(float(yld), 2) for mat, yld in maturities}
            
            # Get spread for this date
            spread = conn.execute(
                "SELECT spread_10y_2y FROM spreads WHERE date = ?", 
                (date,)
            ).fetchone()
            
            curves.append({
                "date": str(date),
                "curve": curve_data,
                "spread": round(float(spread[0]), 2) if spread else None
            })
    
    conn.close()
    
    print(f"Exported {len(curves)} monthly yield curves")
    return curves


def export_all_spreads():
    """Export all 10Y-2Y spreads (used for trend charts)."""
    conn = duckdb.connect(YIELD_DB)
    
    query = """
        SELECT date, spread_10y_2y
        FROM spreads
        ORDER BY date
    """
    
    data = conn.execute(query).fetchall()
    conn.close()
    
    spreads = [
        {"date": str(date), "spread": round(float(spread), 2)}
        for date, spread in data
    ]
    
    print(f"Exported {len(spreads)} spread observations")
    return spreads


def export_economic_indicators():
    """Export all economic indicator data (already monthly, small dataset)."""
    conn = duckdb.connect(ECONOMIC_DB)
    
    # Get unemployment
    unemployment = conn.execute("""
        SELECT date, value
        FROM indicators
        WHERE series_id = 'UNRATE'
        ORDER BY date
    """).fetchall()
    
    # Get CPI YoY
    cpi = conn.execute("""
        SELECT date, value
        FROM indicators
        WHERE series_id = 'CPIAUCSL'
        ORDER BY date
    """).fetchall()
    
    # Get Fed Funds
    fed_funds = conn.execute("""
        SELECT date, value
        FROM indicators
        WHERE series_id = 'FEDFUNDS'
        ORDER BY date
    """).fetchall()
    
    conn.close()
    
    data = {
        "unemployment": [
            {"date": str(date), "value": round(float(value), 2)}
            for date, value in unemployment
        ],
        "cpi_yoy": [
            {"date": str(date), "value": round(float(value), 2)}
            for date, value in cpi
        ],
        "fed_funds": [
            {"date": str(date), "value": round(float(value), 2)}
            for date, value in fed_funds
        ]
    }
    
    print(f"Exported economic indicators:")
    print(f"  Unemployment: {len(data['unemployment'])} records")
    print(f"  CPI YoY: {len(data['cpi_yoy'])} records")
    print(f"  Fed Funds: {len(data['fed_funds'])} records")
    
    return data


def get_notable_dates():
    """Return notable historical dates for comparison feature."""
    return {
        "2008_financial_crisis": "2008-09-15",  # Lehman collapse
        "2020_covid": "2020-03-23",  # Market bottom
        "2022_rate_hikes": "2022-11-01",  # Peak Fed aggression
        "dot_com_bubble": "2000-03-10",  # Nasdaq peak
        "great_recession": "2007-12-01",  # Recession starts
    }


def main():
    """Export all historical data to JSON."""
    print("="*60)
    print("EXPORTING HISTORICAL DATA TO JSON")
    print("="*60)
    
    output = {
        "exported_at": datetime.now().isoformat(),
        "yield_curves_monthly": export_yield_curves_monthly(),
        "spreads_all": export_all_spreads(),
        "economic_indicators": export_economic_indicators(),
        "notable_dates": get_notable_dates(),
    }
    
    # Write to JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    
    # Calculate file size
    import os
    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    
    print(f"\n[OK] Exported to {OUTPUT_FILE}")
    print(f"[OK] File size: {size_kb:.1f} KB")
    print("\nReady for dashboard visualization!")


if __name__ == "__main__":
    main()

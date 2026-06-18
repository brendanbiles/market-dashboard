"""
Backfill historical economic and Treasury data from FRED.

Fetches data back to 1960 (or earliest available) and stores in DuckDB.
Run once to populate the database, then fetch_data.py will append new data daily.

Usage:
    python backfill_historical_data.py
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import requests
import duckdb

# Configuration
FRED_API_KEY = os.getenv("FRED_API_KEY")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Treasury yield series (same as fetch_data.py)
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

# Economic indicators
ECONOMIC_SERIES = {
    "unemployment": "UNRATE",
    "cpi_yoy": "CPALTT01USM657N",
    "fed_funds": "FEDFUNDS",
}

# Database files
YIELD_DB = "yield_curve_history.duckdb"
ECONOMIC_DB = "economic_indicators.duckdb"


def fetch_fred_series_history(
    series_id: str, 
    start_date: str = "1960-01-01"
) -> List[Tuple[str, float]]:
    """
    Fetch all historical observations for a FRED series.
    
    Returns:
        List of (date, value) tuples
    """
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "sort_order": "asc",
        "limit": 100000,  # Max allowed by FRED
    }
    
    print(f"  Fetching {series_id}...", end=" ")
    
    try:
        response = requests.get(FRED_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        observations = data.get("observations", [])
        
        # Filter out missing values (FRED uses "." for N/A)
        results = []
        for obs in observations:
            if obs["value"] != ".":
                results.append((obs["date"], float(obs["value"])))
        
        print(f"{len(results)} observations ({results[0][0] if results else 'N/A'} to {results[-1][0] if results else 'N/A'})")
        return results
        
    except Exception as e:
        print(f"ERROR: {e}")
        return []


def init_yield_curve_db():
    """Initialize the yield curve database schema."""
    conn = duckdb.connect(YIELD_DB)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS yields (
            date DATE NOT NULL,
            maturity VARCHAR NOT NULL,
            yield DECIMAL(6,2) NOT NULL,
            PRIMARY KEY (date, maturity)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS spreads (
            date DATE PRIMARY KEY,
            spread_10y_2y DECIMAL(6,2)
        )
    """)
    
    conn.close()
    print(f"[OK] Initialized {YIELD_DB}")


def init_economic_db():
    """Initialize the economic indicators database schema."""
    conn = duckdb.connect(ECONOMIC_DB)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            date DATE NOT NULL,
            series_id VARCHAR NOT NULL,
            series_name VARCHAR NOT NULL,
            value DECIMAL(10,2) NOT NULL,
            PRIMARY KEY (date, series_id)
        )
    """)
    
    conn.close()
    print(f"[OK] Initialized {ECONOMIC_DB}")


def backfill_treasury_yields():
    """Fetch and store all historical Treasury yield data."""
    print("\n[CHART] Backfilling Treasury Yields...")
    
    conn = duckdb.connect(YIELD_DB)
    
    total_records = 0
    
    for maturity, series_id in TREASURY_SERIES.items():
        history = fetch_fred_series_history(series_id)
        
        if not history:
            continue
        
        # Insert all records (use INSERT OR REPLACE to handle duplicates)
        for date, yield_value in history:
            conn.execute(
                "INSERT OR REPLACE INTO yields (date, maturity, yield) VALUES (?, ?, ?)",
                (date, maturity, yield_value)
            )
        
        total_records += len(history)
    
    conn.commit()
    
    # Calculate and store historical 10Y-2Y spreads
    print("\n  Computing 10Y-2Y spreads...")
    conn.execute("""
        INSERT OR REPLACE INTO spreads (date, spread_10y_2y)
        SELECT 
            y10.date,
            ROUND(y10.yield - y2.yield, 2) as spread_10y_2y
        FROM yields y10
        JOIN yields y2 ON y10.date = y2.date
        WHERE y10.maturity = '10Y' AND y2.maturity = '2Y'
    """)
    
    spread_count = conn.execute("SELECT COUNT(*) FROM spreads").fetchone()[0]
    print(f"  [OK] Computed {spread_count} spreads")
    
    conn.close()
    
    print(f"\n[CHECK] Treasury yields backfilled: {total_records:,} records")


def backfill_economic_indicators():
    """Fetch and store all historical economic indicator data."""
    print("\n[TREND-UP] Backfilling Economic Indicators...")
    
    conn = duckdb.connect(ECONOMIC_DB)
    
    total_records = 0
    
    for name, series_id in ECONOMIC_SERIES.items():
        history = fetch_fred_series_history(series_id)
        
        if not history:
            continue
        
        # Insert all records
        for date, value in history:
            conn.execute(
                "INSERT OR REPLACE INTO indicators (date, series_id, series_name, value) VALUES (?, ?, ?, ?)",
                (date, series_id, name, value)
            )
        
        total_records += len(history)
    
    conn.commit()
    conn.close()
    
    print(f"\n[CHECK] Economic indicators backfilled: {total_records:,} records")


def export_to_parquet():
    """Export DuckDB tables to Parquet for efficient storage and Git."""
    print("\n[PACKAGE] Exporting to Parquet...")
    
    # Yield curves
    conn = duckdb.connect(YIELD_DB)
    conn.execute("COPY yields TO 'yields_history.parquet' (FORMAT PARQUET)")
    conn.execute("COPY spreads TO 'spreads_history.parquet' (FORMAT PARQUET)")
    conn.close()
    print("  [OK] Exported yields_history.parquet")
    print("  [OK] Exported spreads_history.parquet")
    
    # Economic indicators
    conn = duckdb.connect(ECONOMIC_DB)
    conn.execute("COPY indicators TO 'economic_history.parquet' (FORMAT PARQUET)")
    conn.close()
    print("  [OK] Exported economic_history.parquet")


def print_summary():
    """Print summary statistics of the data."""
    print("\n" + "="*60)
    print("[CHART] DATABASE SUMMARY")
    print("="*60)
    
    # Yield curves
    conn = duckdb.connect(YIELD_DB)
    
    stats = conn.execute("""
        SELECT 
            MIN(date) as earliest,
            MAX(date) as latest,
            COUNT(DISTINCT date) as unique_dates,
            COUNT(*) as total_records
        FROM yields
    """).fetchone()
    
    print(f"\n[BANK] Treasury Yields:")
    print(f"   Date range: {stats[0]} to {stats[1]}")
    print(f"   Unique dates: {stats[2]:,}")
    print(f"   Total records: {stats[3]:,}")
    
    # Check for inversions
    inversions = conn.execute("""
        SELECT COUNT(*) FROM spreads WHERE spread_10y_2y < 0
    """).fetchone()[0]
    
    print(f"\n[WARNING] Yield Curve Inversions: {inversions:,} days")
    
    # Most recent inversion
    recent_inversion = conn.execute("""
        SELECT date, spread_10y_2y 
        FROM spreads 
        WHERE spread_10y_2y < 0 
        ORDER BY date DESC 
        LIMIT 1
    """).fetchone()
    
    if recent_inversion:
        print(f"   Most recent: {recent_inversion[0]} ({recent_inversion[1]}%)")
    
    conn.close()
    
    # Economic indicators
    conn = duckdb.connect(ECONOMIC_DB)
    
    for name, series_id in ECONOMIC_SERIES.items():
        stats = conn.execute("""
            SELECT 
                MIN(date) as earliest,
                MAX(date) as latest,
                COUNT(*) as records
            FROM indicators
            WHERE series_id = ?
        """, (series_id,)).fetchone()
        
        print(f"\n[TREND] {name.replace('_', ' ').title()} ({series_id}):")
        print(f"   Date range: {stats[0]} to {stats[1]}")
        print(f"   Records: {stats[2]:,}")
    
    conn.close()
    
    print("\n" + "="*60)


def main():
    """Run the complete backfill process."""
    print("="*60)
    print("[ROCKET] HISTORICAL DATA BACKFILL")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    
    # Initialize databases
    init_yield_curve_db()
    init_economic_db()
    
    # Backfill data
    backfill_treasury_yields()
    backfill_economic_indicators()
    
    # Export to Parquet
    export_to_parquet()
    
    # Print summary
    print_summary()
    
    elapsed = datetime.now() - start_time
    print(f"\n[CLOCK] Total time: {elapsed.total_seconds():.1f} seconds")
    print("\n[CHECK] Backfill complete! Databases ready for dashboard.")


if __name__ == "__main__":
    main()

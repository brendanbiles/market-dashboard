"""Build the full daily Treasury yield curve history from FRED.

Why this exists
---------------
The Time Machine has always been sampled monthly, which makes its newest point
the first business day of the current month. That is correct and it reads as
three weeks stale. Daily resolution removes the illusion and, more usefully,
lets you scrub through an actual crisis day by day rather than month by month.

What the source allows
----------------------
FRED publishes each constant-maturity tenor as its own daily series, and they
start at different times. Measured 2026-08-24:

    1Y, 3Y, 5Y, 10Y, 20Y   from 1962-01-02
    7Y                     from 1969-07-01
    2Y                     from 1976-06-01
    30Y                    from 1977-02-15   (suspended 2002-2006)
    3M, 6M                 from 1981-09-01
    1M                     from 2001-07-31

So a complete 11-point curve only exists from 2001. Before that the curve is
genuinely shorter, and this script records how many tenors each day actually
has rather than padding gaps with invented numbers. A missing tenor is null.

Output
------
data/daily_curves.json, a compact columnar shape: one dates array plus one
array per tenor. That form is roughly half the size of one object per day and
it is what the chart wants anyway.

Run: python fetch_daily_curves.py
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent

# The CSV endpoint needs no API key, which keeps this runnable by anyone and
# keeps a second copy of the key out of CI.
CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"

# Ordered short to long. The chart plots them in this order.
TENORS = [
    ("1M", "DGS1MO"),
    ("3M", "DGS3MO"),
    ("6M", "DGS6MO"),
    ("1Y", "DGS1"),
    ("2Y", "DGS2"),
    ("3Y", "DGS3"),
    ("5Y", "DGS5"),
    ("7Y", "DGS7"),
    ("10Y", "DGS10"),
    ("20Y", "DGS20"),
    ("30Y", "DGS30"),
]

TIMEOUT = 90


def fetch_series(series_id: str) -> dict[str, float]:
    """Date to value for one series. FRED writes '.' for non-trading days."""
    req = urllib.request.Request(
        CSV.format(series_id),
        headers={"User-Agent": "market-dashboard/1.0 (+https://markets.brendanbiles.com)"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    text = raw.decode("utf-8", errors="replace")

    out: dict[str, float] = {}
    for line in io.StringIO(text):
        line = line.strip()
        if not line or line.lower().startswith("observation_date") or line.lower().startswith("date"):
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        date, value = parts[0].strip(), parts[1].strip()
        if value in (".", "", "NA"):
            continue
        try:
            out[date] = float(value)
        except ValueError:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "daily_curves.json"))
    ap.add_argument("--start", default=None, help="drop observations before this date")
    args = ap.parse_args()

    series: dict[str, dict[str, float]] = {}
    for label, sid in TENORS:
        try:
            s = fetch_series(sid)
        except (urllib.error.URLError, TimeoutError) as exc:
            # One tenor failing must not destroy the other ten. The output
            # records which tenors are present, so a partial build is visible
            # rather than silently short.
            print(f"  {label:4} {sid:8} FAILED: {exc}", file=sys.stderr)
            continue
        series[label] = s
        first = min(s) if s else "-"
        last = max(s) if s else "-"
        print(f"  {label:4} {sid:8} {len(s):>6,} obs   {first} -> {last}")

    if not series:
        raise SystemExit("no series fetched; refusing to write an empty file")

    # Every date any tenor reports. A day with only some tenors is kept: a
    # 1962 curve genuinely has five points, and dropping it would throw away
    # 39 years of history to satisfy a shape.
    all_dates = sorted({d for s in series.values() for d in s})
    if args.start:
        all_dates = [d for d in all_dates if d >= args.start]

    labels = [lab for lab, _ in TENORS if lab in series]
    columns = {lab: [series[lab].get(d) for d in all_dates] for lab in labels}
    counts = [sum(1 for lab in labels if columns[lab][i] is not None)
              for i in range(len(all_dates))]

    payload = {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "source": "FRED daily constant-maturity Treasury series, unauthenticated CSV endpoint",
        "note": ("Tenors start at different dates, so early curves have fewer points. "
                 "A null means that tenor was not published that day. tenor_count "
                 "gives the number of points available for each date."),
        "tenors": labels,
        "dates": all_dates,
        "tenor_count": counts,
        "series": columns,
    }

    out = Path(args.out)
    out.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    raw_kb = out.stat().st_size // 1024
    gz_kb = len(gzip.compress(out.read_bytes(), 6)) // 1024
    full = sum(1 for c in counts if c == len(labels))
    print(f"\n  {len(all_dates):,} days, {len(labels)} tenors")
    print(f"  {all_dates[0]} -> {all_dates[-1]}")
    print(f"  {full:,} days have a complete curve ({full/len(all_dates):.0%})")
    print(f"  {out.name}: {raw_kb} KB raw, {gz_kb} KB gzipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

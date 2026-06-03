"""
Export analytics mart tables to gold parquet files.

Usage: python scripts/export_gold.py
"""

import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed")
    sys.exit(1)

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname": os.environ.get("POSTGRES_DB", "nyc_taxi"),
    "user": os.environ.get("POSTGRES_USER", "nyc_user"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nyc_password"),
}

GOLD_PATH = Path("data/gold")

# Mart tables to export as gold layer parquet
EXPORTS = [
    ("revenue_by_day", "SELECT * FROM analytics.mart_revenue_by_day ORDER BY pickup_date"),
    ("revenue_by_zone", "SELECT * FROM analytics.mart_revenue_by_zone"),
    ("trips_by_hour", "SELECT * FROM analytics.mart_trips_by_hour ORDER BY pickup_hour"),
    ("payment_type_summary", "SELECT * FROM analytics.mart_payment_type_summary ORDER BY total_revenue DESC"),
]


def main():
    print("=" * 60)
    print("Export Gold Layer Parquet Files")
    print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)

    for name, query in EXPORTS:
        out_dir = GOLD_PATH / name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{name}.parquet"

        print(f"\n  Exporting {name}...")
        df = pd.read_sql_query(query, conn)
        df.to_parquet(str(out_file), engine="pyarrow", index=False)
        print(f"  -> {out_file}: {len(df):,} rows")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()

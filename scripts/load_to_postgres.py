"""
Load silver parquet data and zone lookup into PostgreSQL.

Uses COPY protocol for fast bulk loading (~10-50x faster than to_sql).

Usage: python scripts/load_to_postgres.py
"""

import io
import os
import sys
import csv
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. pip install psycopg2-binary")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed. pip install pandas")
    sys.exit(1)


DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname": os.environ.get("POSTGRES_DB", "nyc_taxi"),
    "user": os.environ.get("POSTGRES_USER", "nyc_user"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nyc_password"),
}

ZONE_LOOKUP_PATH = "data/lookup/taxi_zone_lookup.csv"
SILVER_PATH = "data/silver/trips"

# Column order matching the silver.trips table schema
COPY_COLUMNS = [
    "trip_id", "ingestion_ts", "source_file",
    "tpep_pickup_datetime", "tpep_dropoff_datetime",
    "pickup_date", "pickup_hour", "pickup_year", "pickup_month",
    "trip_duration_minutes",
    "pulocationid", "dolocationid",
    "pickup_borough", "pickup_zone",
    "dropoff_borough", "dropoff_zone",
    "passenger_count", "trip_distance",
    "ratecodeid", "store_and_fwd_flag",
    "fare_amount", "extra", "mta_tax", "tip_amount",
    "tolls_amount", "improvement_surcharge", "total_amount",
    "payment_type", "congestion_surcharge", "airport_fee",
]

INT_COLUMNS = {
    "pickup_hour", "pickup_year", "pickup_month",
    "pulocationid", "dolocationid",
    "passenger_count", "ratecodeid", "payment_type",
}


def load_zone_lookup(conn):
    """Load zone lookup CSV into PostgreSQL."""
    cur = conn.cursor()
    cur.execute("TRUNCATE raw.zone_lookup CASCADE")

    with open(ZONE_LOOKUP_PATH, "r") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            cur.execute(
                """INSERT INTO raw.zone_lookup (location_id, borough, zone_name, service_zone)
                   VALUES (%s, %s, %s, %s)""",
                (int(row["LocationID"]), row["Borough"], row["Zone"],
                 row.get("service_zone", ""))
            )
            count += 1

    conn.commit()
    print(f"  Loaded {count} zone lookup records")
    return count


def _prepare_dataframe(df):
    """Prepare a single DataFrame for COPY loading."""
    # Keep only columns that exist and match schema
    available = [c for c in COPY_COLUMNS if c in df.columns]
    df = df[available].copy()

    # Fix timestamps — COPY needs string format
    for col in ("pickup_date", "ingestion_ts", "tpep_pickup_datetime", "tpep_dropoff_datetime"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Fix integer columns — must be clean ints, not floats
    for col in INT_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df, available


def _copy_from_buffer(cur, buf, table, columns):
    """COPY a StringIO CSV buffer into a PostgreSQL table."""
    buf.seek(0)
    col_list = ", ".join(columns)
    cur.copy_expert(
        f"COPY {table} ({col_list}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')",
        buf,
    )


def load_silver_trips(conn):
    """Load silver parquet files into PostgreSQL using COPY protocol."""
    cur = conn.cursor()

    # Clear existing data
    cur.execute("TRUNCATE silver.trips CASCADE")
    conn.commit()

    parquet_files = sorted(Path(SILVER_PATH).rglob("*.parquet"))
    if not parquet_files:
        print("  No parquet files found in silver path")
        return 0

    print(f"  Loading {len(parquet_files)} parquet files via COPY...")
    total_loaded = 0
    buffer = io.StringIO()
    first_chunk = True
    active_columns = None

    for pf in parquet_files:
        df = pd.read_parquet(str(pf), engine="pyarrow")
        df, cols = _prepare_dataframe(df)

        if first_chunk:
            active_columns = cols
            first_chunk = False

        # Write chunk to CSV buffer (max ~200k rows per buffer to limit memory)
        CHUNK = 200_000
        for start in range(0, len(df), CHUNK):
            chunk = df.iloc[start:start + CHUNK]
            # Ensure column order is consistent
            chunk = chunk[active_columns]
            chunk.to_csv(buffer, index=False, header=True, na_rep="")
            total_loaded += len(chunk)

            # Flush buffer to PostgreSQL
            _copy_from_buffer(cur, buffer, "silver.trips", active_columns)
            conn.commit()
            buffer = io.StringIO()

            print(f"    {total_loaded:,} / 9,062,115 records loaded...")

        print(f"  + {pf.name}: {len(df):,} rows")

    conn.commit()
    buffer.close()
    print(f"\n  Total loaded: {total_loaded:,} records")
    return total_loaded


def main():
    print("=" * 60)
    print("NYC Taxi - Load Data to PostgreSQL")
    print("=" * 60)

    # Check files exist
    if not Path(ZONE_LOOKUP_PATH).exists():
        print(f"\nERROR: Zone lookup file not found: {ZONE_LOOKUP_PATH}")
        return 1

    silver_files = list(Path(SILVER_PATH).rglob("*.parquet"))
    if not silver_files:
        print(f"\nERROR: No silver parquet files in {SILVER_PATH}")
        return 1

    print(f"\nConnecting to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect: {e}")
        return 1

    print("Connected.\n")

    print("[1/2] Loading zone lookup...")
    load_zone_lookup(conn)

    print("\n[2/2] Loading silver trips...")
    load_silver_trips(conn)

    conn.close()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Load silver parquet data and zone lookup into PostgreSQL.

Usage: python scripts/load_to_postgres.py
"""

import os
import sys
import csv
from pathlib import Path

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "nyc_taxi",
    "user": "nyc_user",
    "password": "nyc_password",
}

ZONE_LOOKUP_PATH = "data/lookup/taxi_zone_lookup.csv"
SILVER_PATH = "data/silver/trips"


def load_zone_lookup(conn):
    """Load zone lookup CSV into PostgreSQL."""
    cur = conn.cursor()

    # Clear existing data
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


def load_silver_trips(conn):
    """Load silver parquet files into PostgreSQL using pandas to_sql."""
    if not HAS_PANDAS:
        print("  ERROR: pandas not installed. Install with: pip install pandas")
        return 0

    cur = conn.cursor()

    # Clear existing data
    cur.execute("TRUNCATE silver.trips CASCADE")
    conn.commit()

    parquet_files = sorted(Path(SILVER_PATH).rglob("*.parquet"))
    if not parquet_files:
        print("  No parquet files found in silver path")
        return 0

    # Read each parquet file individually with pandas (avoids schema merge issues)
    print(f"  Reading {len(parquet_files)} parquet files...")
    frames = []
    for pf in parquet_files:
        try:
            df = pd.read_parquet(str(pf), engine="pyarrow")
            frames.append(df)
            print(f"    Read {len(df):,} rows from {pf.name}")
        except Exception as e:
            print(f"  WARNING: Could not read {pf}: {e}")
            continue

    if not frames:
        print("  No data loaded")
        return 0

    combined = pd.concat(frames, ignore_index=True)
    print(f"  Total records to load: {len(combined):,}")

    # Ensure column order matches table schema
    columns = [
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
    # Only use columns that exist
    available_cols = [c for c in columns if c in combined.columns]
    combined = combined[available_cols]

    # Convert types for PostgreSQL compatibility
    if "pickup_date" in combined.columns:
        combined["pickup_date"] = pd.to_datetime(combined["pickup_date"], errors="coerce")

    if "ingestion_ts" in combined.columns:
        combined["ingestion_ts"] = pd.to_datetime(combined["ingestion_ts"], errors="coerce")

    # Convert integer columns
    int_columns = [
        "pickup_hour", "pickup_year", "pickup_month",
        "pulocationid", "dolocationid",
        "passenger_count", "ratecodeid", "payment_type",
    ]
    for col in int_columns:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    # Convert float columns
    float_columns = [
        "trip_duration_minutes", "trip_distance",
        "fare_amount", "extra", "mta_tax", "tip_amount",
        "tolls_amount", "improvement_surcharge", "total_amount",
        "congestion_surcharge", "airport_fee",
    ]
    for col in float_columns:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    # Use pandas to_sql with chunksize for memory efficiency
    print("  Loading into PostgreSQL using pandas to_sql...")
    from sqlalchemy import create_engine

    engine_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
    engine = create_engine(engine_url)

    # Load in chunks
    chunk_size = 50000
    total_loaded = 0
    for i in range(0, len(combined), chunk_size):
        chunk = combined.iloc[i:i+chunk_size]
        chunk.to_sql(
            name="trips",
            schema="silver",
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=10000,
        )
        total_loaded += len(chunk)
        print(f"    Loaded {total_loaded:,} / {len(combined):,} records...")

    engine.dispose()
    print(f"  Loaded {total_loaded:,} records into silver.trips")
    return total_loaded


def main():
    print("=" * 60)
    print("NYC Taxi - Load Data to PostgreSQL")
    print("=" * 60)

    if not HAS_PSYCOPG2:
        print("\nERROR: psycopg2 not installed.")
        print("Install with: pip install psycopg2-binary")
        return 1

    if not HAS_PANDAS:
        print("\nERROR: pandas not installed.")
        print("Install with: pip install pandas")
        return 1

    # Check files exist
    if not Path(ZONE_LOOKUP_PATH).exists():
        print(f"\nERROR: Zone lookup file not found: {ZONE_LOOKUP_PATH}")
        print("Run download_data.py first.")
        return 1

    silver_files = list(Path(SILVER_PATH).rglob("*.parquet"))
    if not silver_files:
        print(f"\nERROR: No silver parquet files found in {SILVER_PATH}")
        print("Run the Spark cleaning job first.")
        return 1

    # Connect to PostgreSQL
    print("\nConnecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect to PostgreSQL: {e}")
        print("Make sure Docker containers are running: docker-compose up -d")
        return 1

    print("Connected successfully.\n")

    # Load zone lookup
    print("[1/2] Loading zone lookup...")
    load_zone_lookup(conn)

    # Load silver trips
    print("\n[2/2] Loading silver trips...")
    load_silver_trips(conn)

    conn.close()
    print("\nData loading completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
NYC Yellow Taxi Data Cleaning Job

Reads raw parquet files, applies data quality rules, cleans and transforms
the data, and outputs to silver and quarantine zones.

Uses pandas + pyarrow (no PySpark dependency — compatible with all JDK versions).
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZONE_LOOKUP_PATH = Path("data/lookup/taxi_zone_lookup.csv")
RAW_PATH = Path("data/raw/yellow_taxi")
SILVER_PATH = Path("data/silver/trips")
QUARANTINE_PATH = Path("data/quarantine/invalid_trips")
QUALITY_REPORT_PATH = Path("data/quality_report.json")


def load_zone_lookup() -> pd.DataFrame:
    """Load taxi zone lookup CSV."""
    df = pd.read_csv(ZONE_LOOKUP_PATH)
    # Normalize: lowercase, strip whitespace
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={
        "locationid": "location_id",
        "zone": "zone_name",
    })
    print(f"  Zone lookup: {len(df)} zones loaded")
    return df


def load_raw_data() -> pd.DataFrame:
    """Load all raw parquet files into a single DataFrame."""
    parquet_files = sorted(RAW_PATH.rglob("*.parquet"))
    if not parquet_files:
        print("ERROR: No parquet files found in data/raw/yellow_taxi/")
        sys.exit(1)

    print(f"  Found {len(parquet_files)} raw parquet file(s):")
    frames = []
    for pf in parquet_files:
        print(f"    - {pf}")
        df = pq.read_table(str(pf)).to_pandas()
        df["_source_file"] = pf.name
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    print(f"  Total raw records: {len(combined):,}")
    return combined


def rename_columns_lower(df: pd.DataFrame) -> pd.DataFrame:
    """Rename all columns to lowercase."""
    df.columns = [c.lower() for c in df.columns]
    return df


def add_metadata_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add trip_id, ingestion_ts, and source_file columns (vectorized)."""
    print("  Generating trip_id hashes...")
    # Vectorized string concatenation for hash input
    key = (
        df["tpep_pickup_datetime"].astype(str) + "|"
        + df["tpep_dropoff_datetime"].astype(str) + "|"
        + df["pulocationid"].astype(str) + "|"
        + df["dolocationid"].astype(str) + "|"
        + df["fare_amount"].astype(str)
    )
    df["trip_id"] = pd.util.hash_pandas_object(key, index=False).apply(lambda x: format(x, "016x"))
    df["ingestion_ts"] = datetime.now().isoformat()
    df = df.rename(columns={"_source_file": "source_file"})
    return df


def extract_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Extract pickup_date, pickup_hour, pickup_year, pickup_month."""
    pickup = pd.to_datetime(df["tpep_pickup_datetime"])
    dropoff = pd.to_datetime(df["tpep_dropoff_datetime"])

    df["pickup_date"] = pickup.dt.date
    df["pickup_hour"] = pickup.dt.hour
    df["pickup_year"] = pickup.dt.year
    df["pickup_month"] = pickup.dt.month
    df["trip_duration_minutes"] = (dropoff - pickup).dt.total_seconds() / 60.0
    return df


def join_with_zones(df: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
    """Join trip data with zone lookup for pickup and dropoff zones."""
    # Pickup zone
    pickup_zones = zones[["location_id", "borough", "zone_name"]].copy()
    pickup_zones.columns = ["pulocationid", "pickup_borough", "pickup_zone"]
    df = df.merge(pickup_zones, on="pulocationid", how="left")

    # Dropoff zone
    dropoff_zones = zones[["location_id", "borough", "zone_name"]].copy()
    dropoff_zones.columns = ["dolocationid", "dropoff_borough", "dropoff_zone"]
    df = df.merge(dropoff_zones, on="dolocationid", how="left")

    return df


def apply_quality_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data into valid and invalid records based on quality rules.
    Returns (valid_df, invalid_df).
    """
    pickup_dt = pd.to_datetime(df["tpep_pickup_datetime"], errors="coerce")
    dropoff_dt = pd.to_datetime(df["tpep_dropoff_datetime"], errors="coerce")

    # Build invalid mask: ANY condition True -> invalid
    invalid_mask = (
        # Pickup/dropoff time must not be null
        df["tpep_pickup_datetime"].isna()
        | df["tpep_dropoff_datetime"].isna()
        # Dropoff must be after pickup
        | (dropoff_dt <= pickup_dt)
        # Trip distance > 0
        | (df["trip_distance"] <= 0)
        # Fare >= 0
        | (df["fare_amount"] < 0)
        # Total >= fare
        | (df["total_amount"] < df["fare_amount"])
        # Passenger count 1-6
        | (df["passenger_count"] < 1)
        | (df["passenger_count"] > 6)
        # Pickup location must exist in zone lookup
        | df["pickup_zone"].isna()
        # Dropoff location must exist in zone lookup
        | df["dropoff_zone"].isna()
    )

    invalid_df = df[invalid_mask].copy()
    invalid_df["quarantine_reason"] = "failed_quality_checks"
    valid_df = df[~invalid_mask].copy()

    return valid_df, invalid_df


def remove_duplicate_trips(df: pd.DataFrame) -> int:
    """Remove duplicate trip_ids, keeping first occurrence. Returns count removed."""
    before = len(df)
    df.drop_duplicates(subset=["trip_id"], keep="first", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return before - len(df)


def write_silver(df: pd.DataFrame) -> None:
    """Write cleaned data to silver zone, partitioned by year/month."""
    SILVER_PATH.mkdir(parents=True, exist_ok=True)

    for (year, month), group in df.groupby(["pickup_year", "pickup_month"]):
        out_dir = SILVER_PATH / f"pickup_year={int(year)}" / f"pickup_month={int(month):02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "part-0.parquet"
        group.to_parquet(str(out_path), index=False, engine="pyarrow")
        print(f"    Written {len(group):,} records -> {out_path}")

    total = len(df)
    print(f"  Silver data: {total:,} records written to {SILVER_PATH}")


def write_quarantine(df: pd.DataFrame) -> None:
    """Write invalid records to quarantine zone."""
    QUARANTINE_PATH.mkdir(parents=True, exist_ok=True)
    if len(df) > 0:
        out_path = QUARANTINE_PATH / "part-0.parquet"
        df.to_parquet(str(out_path), index=False, engine="pyarrow")
        print(f"  Quarantine: {len(df):,} records written to {QUARANTINE_PATH}")
    else:
        print("  Quarantine: no invalid records")


def generate_quality_report(
    total_count: int,
    valid_count: int,
    invalid_count: int,
    duplicate_count: int,
    null_counts: dict,
) -> dict:
    """Generate and save a data quality report."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "input_records": total_count,
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "invalid_percentage": round(invalid_count / total_count * 100, 2) if total_count > 0 else 0,
        "duplicate_trip_ids": duplicate_count,
        "null_counts": null_counts,
        "checks_applied": [
            "pickup_time_not_null",
            "dropoff_time_not_null",
            "trip_duration_positive",
            "trip_distance_gt_zero",
            "fare_amount_gte_zero",
            "total_amount_gte_fare",
            "passenger_count_1_to_6",
            "pickup_location_in_zone_lookup",
            "dropoff_location_in_zone_lookup",
        ],
    }

    QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUALITY_REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print("DATA QUALITY REPORT")
    print(f"{'=' * 60}")
    print(f"  Input records:      {total_count:>12,}")
    print(f"  Valid records:      {valid_count:>12,}")
    print(f"  Invalid records:    {invalid_count:>12,}")
    print(f"  Invalid %:          {report['invalid_percentage']:>11.2f}%")
    print(f"  Duplicate trips:    {duplicate_count:>12,}")
    print(f"\n  Null counts (key columns):")
    for col_name, cnt in null_counts.items():
        print(f"    {col_name:<35} {cnt:>12,}")
    print(f"{'=' * 60}")

    return report


def main():
    print("=" * 60)
    print("NYC Yellow Taxi - Data Cleaning Job")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Engine: pandas + pyarrow")
    print("=" * 60)

    # 1. Load zone lookup
    print("\n[1/7] Loading zone lookup...")
    zones = load_zone_lookup()

    # 2. Load raw data
    print("\n[2/7] Loading raw data...")
    df = load_raw_data()
    total_count = len(df)

    # 3. Rename columns to lowercase
    print("\n[3/7] Renaming columns to lowercase...")
    df = rename_columns_lower(df)

    # 4. Add metadata columns
    print("\n[4/7] Adding metadata columns (trip_id, ingestion_ts, source_file)...")
    df = add_metadata_columns(df)

    # 5. Extract time columns
    print("\n[5/7] Extracting time columns...")
    df = extract_time_columns(df)

    # 6. Join with zone lookup
    print("\n[6/7] Joining with zone lookup...")
    df = join_with_zones(df, zones)

    # 7. Apply quality filters
    print("\n[7/7] Applying data quality rules...")
    valid_df, invalid_df = apply_quality_filters(df)

    valid_count = len(valid_df)
    invalid_count = len(invalid_df)
    print(f"  Valid: {valid_count:,} | Invalid: {invalid_count:,}")

    # Remove duplicates from valid set
    dupes_removed = remove_duplicate_trips(valid_df)
    valid_count = len(valid_df)
    print(f"  Duplicates removed: {dupes_removed:,} | Final valid: {valid_count:,}")

    # Null counts for report
    key_columns = [
        "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "trip_distance", "fare_amount", "total_amount",
        "passenger_count", "pulocationid", "dolocationid",
    ]
    null_counts = {col: int(df[col].isna().sum()) for col in key_columns if col in df.columns}

    # Select final columns for silver output
    silver_columns = [
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
    available = [c for c in silver_columns if c in valid_df.columns]
    valid_df = valid_df[available].copy()

    # Write outputs
    print(f"\nWriting silver data ({valid_count:,} valid records)...")
    write_silver(valid_df)

    print(f"\nWriting quarantine data ({invalid_count:,} invalid records)...")
    write_quarantine(invalid_df)

    # Generate quality report
    generate_quality_report(
        total_count=total_count,
        valid_count=valid_count,
        invalid_count=invalid_count,
        duplicate_count=dupes_removed,
        null_counts=null_counts,
    )

    print(f"\nJob completed at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()

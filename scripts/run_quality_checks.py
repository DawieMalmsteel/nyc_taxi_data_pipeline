"""
Data Quality Checks Runner

Reads silver parquet data and runs additional quality validation.
Outputs a detailed quality report.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

try:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    HAS_SPARK = True
except ImportError:
    HAS_SPARK = False


SILVER_PATH = "data/silver/trips"
QUARANTINE_PATH = "data/quarantine/invalid_trips"
REPORT_PATH = "data/quality_report.json"


def run_with_spark():
    """Run quality checks using PySpark."""
    spark = (
        SparkSession.builder
        .appName("NYC_Taxi_QualityChecks")
        .master("local[*]")
        .config("spark.driver.memory", "1g")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    # Read silver data
    silver_df = spark.read.parquet(SILVER_PATH)
    total_silver = silver_df.count()

    # Check uniqueness of trip_id
    total_trips = silver_df.count()
    unique_trips = silver_df.select("trip_id").distinct().count()
    duplicate_count = total_trips - unique_trips

    # Null counts
    key_columns = [
        "trip_id", "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "trip_distance", "fare_amount", "total_amount",
        "passenger_count", "pickup_date", "pickup_hour",
    ]
    null_counts = {}
    for col_name in key_columns:
        if col_name in silver_df.columns:
            null_counts[col_name] = silver_df.filter(F.col(col_name).isNull()).count()

    # Basic stats
    stats = {}
    if "fare_amount" in silver_df.columns:
        row = silver_df.select(
            F.avg("fare_amount").alias("avg_fare"),
            F.max("fare_amount").alias("max_fare"),
            F.min("fare_amount").alias("min_fare"),
            F.avg("trip_distance").alias("avg_distance"),
            F.avg("total_amount").alias("avg_total"),
            F.avg("tip_amount").alias("avg_tip"),
        ).collect()[0]
        stats = {
            "avg_fare": round(float(row["avg_fare"] or 0), 2),
            "max_fare": round(float(row["max_fare"] or 0), 2),
            "min_fare": round(float(row["min_fare"] or 0), 2),
            "avg_distance": round(float(row["avg_distance"] or 0), 2),
            "avg_total": round(float(row["avg_total"] or 0), 2),
            "avg_tip": round(float(row["avg_tip"] or 0), 2),
        }

    # Check quarantine exists
    quarantine_count = 0
    q_path = Path(QUARANTINE_PATH)
    if q_path.exists():
        q_df = spark.read.parquet(QUARANTINE_PATH)
        quarantine_count = q_df.count()

    spark.stop()

    return {
        "total_silver_records": total_silver,
        "unique_trip_ids": unique_trips,
        "duplicate_trip_ids": duplicate_count,
        "quarantine_records": quarantine_count,
        "null_counts": null_counts,
        "statistics": stats,
    }


def main():
    print("=" * 60)
    print("NYC Taxi - Data Quality Check Report")
    print(f"Generated at: {datetime.now().isoformat()}")
    print("=" * 60)

    if not HAS_SPARK:
        print("PySpark not available. Generating report from quality_report.json...")
        report_path = Path(REPORT_PATH)
        if report_path.exists():
            with open(report_path) as f:
                print(json.dumps(json.load(f), indent=2))
            return 0
        else:
            print("No quality report found. Run the Spark job first.")
            return 1

    results = run_with_spark()

    # Merge with existing report if available
    report_path = Path(REPORT_PATH)
    existing = {}
    if report_path.exists():
        with open(report_path) as f:
            existing = json.load(f)

    existing.update(results)
    existing["quality_check_run_at"] = datetime.now().isoformat()

    with open(report_path, "w") as f:
        json.dump(existing, f, indent=2, default=str)

    # Print report
    print(f"\n  Silver records:       {results['total_silver_records']:>12,}")
    print(f"  Unique trip IDs:      {results['unique_trip_ids']:>12,}")
    print(f"  Duplicate trip IDs:   {results['duplicate_trip_ids']:>12,}")
    print(f"  Quarantine records:   {results['quarantine_records']:>12,}")
    print(f"\n  Null counts:")
    for col, cnt in results["null_counts"].items():
        print(f"    {col:<35} {cnt:>12,}")
    if results["statistics"]:
        print(f"\n  Statistics:")
        for k, v in results["statistics"].items():
            print(f"    {k:<35} {v:>12}")
    print(f"\n  Report saved to: {REPORT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

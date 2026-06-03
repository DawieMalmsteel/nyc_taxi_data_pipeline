"""
NYC TLC Trip Data Downloader

Downloads Yellow Taxi parquet files and taxi zone lookup CSV.
Placeholders are used for failed downloads so the user can manually download.
"""

import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


def load_config():
    """Load config.yaml manually (no pyyaml dependency for download script)."""
    config = {}
    with open("config.yaml") as f:
        for line in f:
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value:
                    config[key] = value
    return config


def download_file(url: str, dest: Path) -> bool:
    """Download a file. Returns True on success, False on failure."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  [SKIP] Already exists: {dest}")
        return True
    try:
        print(f"  Downloading: {url}")
        urllib.request.urlretrieve(url, dest)
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  [OK] {dest} ({size_mb:.1f} MB)")
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"  [FAIL] {url}")
        print(f"         Error: {e}")
        if dest.exists():
            dest.unlink()  # Remove partial download
        return False


def main():
    base_url = "https://d37ci6vzurychx.cloudfront.net/trip-data"
    zone_url = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

    months = ["2024-01", "2024-02", "2024-03"]
    raw_dir = Path("data/raw/yellow_taxi")
    lookup_dir = Path("data/lookup")

    failed = []

    # Download trip data
    print("=" * 60)
    print("Downloading Yellow Taxi Trip Data")
    print("=" * 60)
    for month in months:
        year, m = month.split("-")
        filename = f"yellow_tripdata_{month}.parquet"
        url = f"{base_url}/{filename}"
        dest = raw_dir / f"year={year}" / f"month={m}" / filename
        if not download_file(url, dest):
            failed.append(("trip_data", filename, url, dest))

    # Download zone lookup
    print("\n" + "=" * 60)
    print("Downloading Taxi Zone Lookup")
    print("=" * 60)
    zone_dest = lookup_dir / "taxi_zone_lookup.csv"
    if not download_file(zone_url, zone_dest):
        failed.append(("zone_lookup", "taxi_zone_lookup.csv", zone_url, zone_dest))

    # Report
    print("\n" + "=" * 60)
    if not failed:
        print("ALL DOWNLOADS COMPLETED SUCCESSFULLY")
        print("=" * 60)
    else:
        print("SOME DOWNLOADS FAILED — Manual download needed:")
        print("=" * 60)
        for dtype, name, url, dest in failed:
            print(f"\n  [{dtype}] {name}")
            print(f"    URL:  {url}")
            print(f"    Dest: {dest}")
        print(f"\nAfter manual download, place files in the paths above.")
        print("Then re-run this script to verify.")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

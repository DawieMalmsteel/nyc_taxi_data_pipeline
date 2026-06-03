"""
Docker entrypoint: run the full pipeline in order.

1. Wait for PostgreSQL to be ready
2. Download data
3. Run cleaning job
4. Load data into PostgreSQL
5. Run dbt models
6. Print summary
"""

import sys
import time
import subprocess
from pathlib import Path


def wait_for_postgres(host: str, port: int, dbname: str, user: str, password: str, max_retries: int = 30):
    """Wait for PostgreSQL to accept connections."""
    import psycopg2

    print(f"Waiting for PostgreSQL at {host}:{port}...")
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=host, port=port, dbname=dbname,
                user=user, password=password,
            )
            conn.close()
            print("PostgreSQL is ready!")
            return True
        except psycopg2.OperationalError:
            print(f"  Attempt {i+1}/{max_retries} - PostgreSQL not ready yet...")
            time.sleep(2)

    print("ERROR: PostgreSQL did not become ready in time.")
    return False


def run_step(name: str, cmd: list[str]) -> bool:
    """Run a pipeline step. Returns True on success."""
    print(f"\n{'=' * 60}")
    print(f"STEP: {name}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, cwd="/app")
    if result.returncode != 0:
        print(f"\nFAILED: {name} (exit code {result.returncode})")
        return False
    print(f"\nCOMPLETED: {name}")
    return True


def main():
    import os

    db_host = os.environ.get("POSTGRES_HOST", "postgres")
    db_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    db_name = os.environ.get("POSTGRES_DB", "nyc_taxi")
    db_user = os.environ.get("POSTGRES_USER", "nyc_user")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "nyc_password")

    print("=" * 60)
    print("NYC Taxi Data Pipeline - Docker Entrypoint")
    print("=" * 60)

    # 1. Wait for PostgreSQL
    if not wait_for_postgres(db_host, db_port, db_name, db_user, db_pass):
        sys.exit(1)

    # 2. Download data (skip if already present)
    raw_files = list(Path("data/raw/yellow_taxi").rglob("*.parquet"))
    if len(raw_files) >= 3:
        print(f"\nRaw data already exists ({len(raw_files)} files). Skipping download.")
    else:
        if not run_step("Download Data", [sys.executable, "scripts/download_data.py"]):
            sys.exit(1)

    # 3. Run cleaning job
    silver_files = list(Path("data/silver/trips").rglob("*.parquet"))
    if silver_files:
        print(f"\nSilver data already exists. Skipping cleaning.")
    else:
        if not run_step("Data Cleaning", [sys.executable, "jobs/spark_clean.py"]):
            sys.exit(1)

    # 4. Load data into PostgreSQL (skip if already loaded)
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=db_host, port=db_port, dbname=db_name,
            user=db_user, password=db_pass,
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM silver.trips")
        existing = cur.fetchone()[0]
        cur.close()
        conn.close()
    except Exception:
        existing = 0

    if existing > 100_000:
        print(f"\nPostgreSQL already has {existing:,} silver trips. Skipping load.")
    else:
        if not run_step("Load to PostgreSQL", [sys.executable, "scripts/load_to_postgres.py"]):
            sys.exit(1)

    # 5. Run dbt
    dbt_args = ["--project-dir", "/app/dbt_project", "--profiles-dir", "/app/dbt_project"]
    if not run_step("dbt deps", ["dbt", "deps"] + dbt_args):
        sys.exit(1)
    if not run_step("dbt run", ["dbt", "run"] + dbt_args):
        sys.exit(1)
    if not run_step("dbt test", ["dbt", "test"] + dbt_args):
        print("WARNING: Some dbt tests failed, but pipeline continues.")

    # 6. Export gold layer
    if not run_step("Export Gold Parquet", [sys.executable, "scripts/export_gold.py"]):
        print("WARNING: Gold export failed, but pipeline continues.")

    # 7. Summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  PostgreSQL:  {db_host}:{db_port}/{db_name}")
    print(f"  Metabase:    http://localhost:3000")
    print("=" * 60)


if __name__ == "__main__":
    main()

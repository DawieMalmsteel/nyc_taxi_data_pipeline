"""
Run post-load optimization: add indexes and constraints after bulk data load.

This is much faster than having indexes during the load process.
"""

import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed")
    sys.exit(1)


DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname": os.environ.get("POSTGRES_DB", "nyc_taxi"),
    "user": os.environ.get("POSTGRES_USER", "nyc_user"),
    "password": os.environ.get("POSTGRES_PASSWORD", "nyc_password"),
}

SQL_FILE = Path(__file__).parent / "post_load_optimize.sql"


def main():
    print("=" * 60)
    print("Post-Load Optimization")
    print("=" * 60)

    if not SQL_FILE.exists():
        print(f"ERROR: SQL file not found: {SQL_FILE}")
        return 1

    print(f"\nConnecting to PostgreSQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True  # Use autocommit for DDL statements
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect: {e}")
        return 1

    print("Connected.\n")

    try:
        cur = conn.cursor()

        # Read and execute SQL
        sql = SQL_FILE.read_text()
        print("Executing post-load optimization SQL...")
        cur.execute(sql)

        print("\n✓ Optimization complete!")
        print("  - PRIMARY KEY added")
        print("  - Indexes created")
        print("  - ANALYZE completed")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

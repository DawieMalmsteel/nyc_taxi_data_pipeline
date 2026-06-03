"""
Run the Spark cleaning job.
Usage: python scripts/run_spark_job.py
"""

import subprocess
import sys
from pathlib import Path


def main():
    job_path = Path("jobs/spark_clean.py")
    if not job_path.exists():
        print(f"ERROR: Job file not found: {job_path}")
        sys.exit(1)

    print("Running Spark cleaning job...")
    print(f"  Job: {job_path}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(job_path)],
        cwd=str(Path.cwd()),
    )

    if result.returncode != 0:
        print(f"\nSpark job failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    print("\nSpark job completed successfully.")


if __name__ == "__main__":
    main()

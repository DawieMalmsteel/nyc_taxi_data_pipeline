# NYC Taxi Data Pipeline

## Tech Stack

| Layer | Tool |
|-------|------|
| Runtime | Docker Compose |
| Storage | Local filesystem (data lake) |
| Processing | PySpark |
| Database | PostgreSQL 16 |
| Transformation | dbt |
| Data Quality | PySpark + dbt tests |
| Dashboard | Metabase |

## Pipeline Design

```
NYC TLC Parquet Files (3 months)
        ↓
    Raw Zone (data/raw/) — files stored as-is, partitioned by year/month
        ↓
    Spark Cleaning Job
        ├── Rename columns to lowercase
        ├── Add trip_id (SHA-256 hash)
        ├── Add ingestion_ts, source_file
        ├── Extract pickup_date, pickup_hour
        ├── Join with taxi zone lookup
        ├── Apply 9 data quality rules
        └── Split valid / invalid
        ↓                    ↓
    Silver Zone          Quarantine Zone
    (data/silver/)       (data/quarantine/)
        ↓
    dbt Models
        ├── Staging: stg_trips, stg_zones
        ├── Dimensions: dim_zone, dim_date, dim_payment_type
        ├── Fact: fact_trips
        └── Marts: revenue_by_day, revenue_by_zone,
                   trips_by_hour, payment_type_summary
        ↓
    PostgreSQL (analytics schema)
        ↓
    SQL Queries / Metabase Dashboard
```

## Problems Found in the Data

During development and testing, the following data quality issues were identified:

1. **Invalid trip durations**: Records where dropoff time was before or equal to pickup time
2. **Negative trip distances**: Some records had trip_distance ≤ 0
3. **Negative fare amounts**: Some records had negative fares (likely refunds/corrections)
4. **Total amount less than fare**: Records where total_amount < fare_amount (data inconsistency)
5. **Invalid passenger counts**: Records with passenger_count outside 1-6 range
6. **Missing zone lookups**: Records with location IDs not found in the zone lookup table
7. **Duplicate trip_ids**: Potential duplicates in raw data (handled by deduplication)
8. **Null critical fields**: Missing pickup/dropoff times in some records

All invalid records are quarantined to `data/quarantine/invalid_trips/` for investigation.

## Data Quality Rules Applied

| # | Rule | Description |
|---|------|-------------|
| 1 | pickup_time_not_null | tpep_pickup_datetime must not be NULL |
| 2 | dropoff_time_not_null | tpep_dropoff_datetime must not be NULL |
| 3 | trip_duration_positive | Drop-off must be after pickup |
| 4 | trip_distance_gt_zero | Trip distance must be > 0 |
| 5 | fare_amount_gte_zero | Fare amount must be ≥ 0 |
| 6 | total_amount_gte_fare | Total amount must be ≥ fare amount |
| 7 | passenger_count_1_to_6 | Passenger count between 1 and 6 |
| 8 | pickup_location_valid | Pickup location exists in zone lookup |
| 9 | dropoff_location_valid | Dropoff location exists in zone lookup |

## Running the Pipeline

### 1. Download Data
```bash
python scripts/download_data.py
```
If downloads fail, manually download from:
- https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
- https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-02.parquet
- https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-03.parquet
- https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv

Place files in `data/raw/yellow_taxi/year=2024/month=0X/` and `data/lookup/`.

### 2. Run Spark Cleaning
```bash
python jobs/spark_clean.py
```

### 3. Run Quality Checks
```bash
python scripts/run_quality_checks.py
```

### 4. Start Infrastructure
```bash
docker-compose up -d
```

### 5. Load Data into PostgreSQL
```bash
# Load zone lookup
psql -h localhost -U nyc_user -d nyc_taxi -c "\copy raw.zone_lookup FROM 'data/lookup/taxi_zone_lookup.csv' WITH (FORMAT csv, HEADER true);"

# Load silver trips (using parquet-to-csv conversion or direct COPY)
python scripts/load_to_postgres.py
```

### 6. Run dbt Models
```bash
cd dbt_project
dbt deps
dbt run
dbt test
```

### 7. Run Analytics
```bash
psql -h localhost -U nyc_user -d nyc_taxi -f analytics/queries.sql
```

## What Could Be Improved for Production

1. **Orchestration**: Add Airflow to schedule and monitor pipeline runs
2. **Incremental Processing**: Use dbt incremental models instead of full refresh
3. **Data Partitioning**: Partition silver data by date for faster queries
4. **Schema Evolution**: Handle schema changes in raw data gracefully
5. **Monitoring**: Add alerts for data quality failures and pipeline failures
6. **Testing**: Add more comprehensive dbt tests and Great Expectations suites
7. **CI/CD**: Automated testing and deployment pipeline
8. **Data Catalog**: Add metadata documentation with tools like DataHub or Amundsen
9. **Access Control**: Implement role-based access control in PostgreSQL
10. **Scaling**: Move to cloud storage (S3/GCS) and managed Spark (EMR/Dataproc)

## File Structure

```
nyc_taxi_pipeline/
├── docker-compose.yml          # Docker infrastructure
├── config.yaml                 # Pipeline configuration
├── scripts/
│   ├── download_data.py        # Data download script
│   ├── run_spark_job.py        # Spark job runner
│   ├── run_quality_checks.py   # Quality check runner
│   └── init_db.sql             # PostgreSQL initialization
├── jobs/
│   └── spark_clean.py          # Main Spark cleaning job
├── dbt_project/
│   ├── dbt_project.yml         # dbt project config
│   ├── profiles.yml            # dbt connection profiles
│   └── models/
│       ├── staging/            # Staging models
│       └── marts/              # Dimension, fact, and mart models
├── data/
│   ├── raw/yellow_taxi/        # Raw parquet files
│   ├── lookup/                 # Zone lookup CSV
│   ├── silver/trips/           # Cleaned parquet output
│   ├── quarantine/             # Invalid records
│   └── quality_report.json     # Data quality report
└── analytics/
    └── queries.sql             # Business analytics queries
```

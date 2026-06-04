-- Initialize PostgreSQL schema for NYC Taxi Pipeline

-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Create zone lookup table
CREATE TABLE IF NOT EXISTS raw.zone_lookup (
    location_id INTEGER PRIMARY KEY,
    borough TEXT,
    zone_name TEXT,
    service_zone TEXT
);

-- Create silver trips table (will be populated by cleaning job + load script)
-- NOTE: PRIMARY KEY constraint added AFTER bulk load for performance
CREATE TABLE IF NOT EXISTS silver.trips (
    trip_id TEXT,
    ingestion_ts TIMESTAMP,
    source_file TEXT,
    tpep_pickup_datetime TIMESTAMP,
    tpep_dropoff_datetime TIMESTAMP,
    pickup_date DATE,
    pickup_hour INTEGER,
    pickup_year INTEGER,
    pickup_month INTEGER,
    trip_duration_minutes DOUBLE PRECISION,
    pulocationid INTEGER,
    dolocationid INTEGER,
    pickup_borough TEXT,
    pickup_zone TEXT,
    dropoff_borough TEXT,
    dropoff_zone TEXT,
    passenger_count INTEGER,
    trip_distance DOUBLE PRECISION,
    ratecodeid INTEGER,
    store_and_fwd_flag TEXT,
    fare_amount DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    payment_type INTEGER,
    congestion_surcharge DOUBLE PRECISION,
    airport_fee DOUBLE PRECISION
);

-- Create analytics schema tables (will be created by dbt)
-- dbt manages these, so we just ensure the schema exists
GRANT ALL ON SCHEMA analytics TO nyc_user;
GRANT ALL ON SCHEMA raw TO nyc_user;
GRANT ALL ON SCHEMA silver TO nyc_user;

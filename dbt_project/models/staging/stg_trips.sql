-- stg_trips: Staging model for cleaned taxi trip records
-- Reads from silver.parquet files loaded into PostgreSQL

with source as (
    select * from {{ source('silver', 'trips') }}
),

renamed as (
    select
        trip_id,
        ingestion_ts,
        source_file,
        tpep_pickup_datetime as pickup_datetime,
        tpep_dropoff_datetime as dropoff_datetime,
        pickup_date,
        pickup_hour,
        pickup_year,
        pickup_month,
        trip_duration_minutes,
        pulocationid as pickup_location_id,
        dolocationid as dropoff_location_id,
        pickup_borough,
        pickup_zone,
        dropoff_borough,
        dropoff_zone,
        passenger_count,
        trip_distance,
        ratecodeid as rate_code_id,
        store_and_fwd_flag,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        total_amount,
        payment_type,
        congestion_surcharge,
        airport_fee
    from source
)

select * from renamed

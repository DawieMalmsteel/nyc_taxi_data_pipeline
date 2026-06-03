-- fact_trips: One row per taxi trip

with trips as (
    select * from {{ ref('stg_trips') }}
),

fact_trips as (
    select
        trip_id,
        pickup_datetime,
        dropoff_datetime,
        pickup_date,
        pickup_hour,
        pickup_year,
        pickup_month,
        pickup_location_id,
        dropoff_location_id,
        pickup_borough,
        pickup_zone,
        dropoff_borough,
        dropoff_zone,
        passenger_count,
        trip_distance,
        trip_duration_minutes,
        rate_code_id,
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
        airport_fee,
        -- Derived columns
        case
            when tip_amount > 0 then true
            else false
        end as has_tip,
        case
            when tip_amount > 0 and fare_amount > 0
            then round(tip_amount / fare_amount * 100, 2)
            else 0
        end as tip_percentage
    from trips
)

select * from fact_trips

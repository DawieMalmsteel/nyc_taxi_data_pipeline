-- mart_revenue_by_day: Daily revenue summary

with trips as (
    select * from {{ ref('fact_trips') }}
),

revenue_by_day as (
    select
        pickup_date,
        count(*) as total_trips,
        sum(total_amount) as total_revenue,
        sum(fare_amount) as total_fare,
        sum(tip_amount) as total_tips,
        avg(total_amount) as avg_revenue_per_trip,
        avg(trip_distance) as avg_distance,
        avg(trip_duration_minutes) as avg_duration_minutes,
        count(distinct pickup_location_id) as unique_pickup_zones,
        count(distinct dropoff_location_id) as unique_dropoff_zones
    from trips
    group by pickup_date
)

select * from revenue_by_day
order by pickup_date

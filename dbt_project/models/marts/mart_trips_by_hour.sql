-- mart_trips_by_hour: Trip count by hour

with trips as (
    select * from {{ ref('fact_trips') }}
),

trips_by_hour as (
    select
        pickup_hour,
        count(*) as total_trips,
        avg(trip_distance) as avg_distance,
        avg(fare_amount) as avg_fare,
        avg(total_amount) as avg_total,
        avg(tip_amount) as avg_tip,
        avg(trip_duration_minutes) as avg_duration_minutes,
        sum(total_amount) as total_revenue
    from trips
    group by pickup_hour
)

select * from trips_by_hour
order by pickup_hour

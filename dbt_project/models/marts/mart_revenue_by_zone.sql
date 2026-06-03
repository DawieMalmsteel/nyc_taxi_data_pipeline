-- mart_revenue_by_zone: Revenue by pickup/dropoff zone

with trips as (
    select * from {{ ref('fact_trips') }}
),

revenue_by_pickup_zone as (
    select
        pickup_location_id as location_id,
        pickup_borough as borough,
        pickup_zone as zone_name,
        'pickup' as direction,
        count(*) as total_trips,
        sum(total_amount) as total_revenue,
        avg(total_amount) as avg_revenue,
        avg(trip_distance) as avg_distance,
        avg(tip_amount) as avg_tip
    from trips
    group by pickup_location_id, pickup_borough, pickup_zone
),

revenue_by_dropoff_zone as (
    select
        dropoff_location_id as location_id,
        dropoff_borough as borough,
        dropoff_zone as zone_name,
        'dropoff' as direction,
        count(*) as total_trips,
        sum(total_amount) as total_revenue,
        avg(total_amount) as avg_revenue,
        avg(trip_distance) as avg_distance,
        avg(tip_amount) as avg_tip
    from trips
    group by dropoff_location_id, dropoff_borough, dropoff_zone
),

combined as (
    select * from revenue_by_pickup_zone
    union all
    select * from revenue_by_dropoff_zone
)

select * from combined
order by total_revenue desc

-- dim_zone: Taxi zone dimension table

with zones as (
    select * from {{ ref('stg_zones') }}
),

dim_zone as (
    select
        location_id,
        borough,
        zone_name,
        service_zone
    from zones
)

select * from dim_zone

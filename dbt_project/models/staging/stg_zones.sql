-- stg_zones: Staging model for taxi zone lookup

with source as (
    select * from {{ source('raw', 'zone_lookup') }}
),

renamed as (
    select
        location_id,
        borough,
        zone_name,
        service_zone
    from source
)

select * from renamed

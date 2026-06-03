-- dim_date: Date dimension table

with trips as (
    select distinct pickup_date
    from {{ ref('stg_trips') }}
    where pickup_date is not null
),

dim_date as (
    select
        pickup_date as date_key,
        extract(year from pickup_date) as year,
        extract(month from pickup_date) as month,
        extract(day from pickup_date) as day,
        extract(dayofweek from pickup_date) as day_of_week,
        extract(dayofyear from pickup_date) as day_of_year,
        case
            when extract(dayofweek from pickup_date) in (1, 7) then true
            else false
        end as is_weekend,
        case
            when extract(dayofweek from pickup_date) in (1, 7) then 'Weekend'
            else 'Weekday'
        end as day_type,
        to_char(pickup_date, 'YYYY-MM') as year_month,
        to_char(pickup_date, 'FMMonth') as month_name,
        to_char(pickup_date, 'FMDay') as day_name
    from trips
)

select * from dim_date

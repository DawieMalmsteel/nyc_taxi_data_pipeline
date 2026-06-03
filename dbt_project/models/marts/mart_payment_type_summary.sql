-- mart_payment_type_summary: Revenue and tip summary by payment type

with trips as (
    select * from {{ ref('fact_trips') }}
),

payment_summary as (
    select
        payment_type,
        case payment_type
            when 1 then 'Credit Card'
            when 2 then 'Cash'
            when 3 then 'No Charge'
            when 4 then 'Dispute'
            when 5 then 'Unknown'
            when 6 then 'Voided Trip'
            else 'Other'
        end as payment_type_name,
        count(*) as total_trips,
        sum(total_amount) as total_revenue,
        sum(fare_amount) as total_fare,
        sum(tip_amount) as total_tips,
        avg(total_amount) as avg_total,
        avg(fare_amount) as avg_fare,
        avg(tip_amount) as avg_tip,
        avg(tip_percentage) as avg_tip_percentage,
        round(
            (count(*) * 100.0 / (select count(*) from trips))::numeric,
            2
        ) as percentage_of_trips,
        round(
            (sum(total_amount) * 100.0 / (select sum(total_amount) from trips))::numeric,
            2
        ) as percentage_of_revenue
    from trips
    group by payment_type
)

select * from payment_summary
order by total_revenue desc

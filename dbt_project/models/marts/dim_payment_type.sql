-- dim_payment_type: Payment type dimension table

with payment_types as (
    select distinct payment_type
    from {{ ref('stg_trips') }}
    where payment_type is not null
),

dim_payment_type as (
    select
        payment_type as payment_type_id,
        case payment_type
            when 1 then 'Credit Card'
            when 2 then 'Cash'
            when 3 then 'No Charge'
            when 4 then 'Dispute'
            when 5 then 'Unknown'
            when 6 then 'Voided Trip'
            else 'Other'
        end as payment_type_name
    from payment_types
)

select * from dim_payment_type

{{ config(tags=['sales']) }}
select 'customers' as entity
where (select count(*) from {{ ref('dim_customers') }}) <> (select count(*) from {{ ref('stg_thelook__users') }})
   or exists (select customer_id from {{ ref('stg_thelook__users') }} minus select customer_id from {{ ref('dim_customers') }})
union all
select 'products'
where (select count(*) from {{ ref('dim_products') }}) <> (select count(*) from {{ ref('stg_thelook__products') }})
   or exists (select product_id from {{ ref('stg_thelook__products') }} minus select product_id from {{ ref('dim_products') }})

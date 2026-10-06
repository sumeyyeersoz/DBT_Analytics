{{ config(tags=['sales']) }}
select o.order_id
from {{ ref('stg_thelook__orders') }} o
left join (select order_id, count(*) as item_count from {{ ref('fct_order_items') }} group by order_id) f
    on o.order_id = f.order_id
where o.order_item_count is distinct from coalesce(f.item_count, 0)

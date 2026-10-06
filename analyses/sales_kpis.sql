select
    count(*) as item_count,
    count(distinct order_id) as order_count,
    count(distinct customer_id) as buyer_count,
    min(order_date) as first_order_date,
    max(order_date) as last_order_date,
    sum(item_amount) as ordered_item_amount,
    sum(completed_sales_amount) as completed_sales_amount,
    sum(completed_cost_amount) as completed_cost_amount,
    sum(completed_gross_margin_amount) as completed_gross_margin_amount,
    sum(cancelled_item_amount) as cancelled_item_amount,
    sum(returned_item_amount) as returned_item_amount
from {{ ref('fct_order_items') }}

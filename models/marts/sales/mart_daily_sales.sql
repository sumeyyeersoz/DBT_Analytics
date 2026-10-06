-- Grain: one UTC order date in the selected batch. This is an order-cohort summary,
-- not cash receipts, recognized revenue, or a return-date ledger.
{% set status_names = {
    'complete': 'completed',
    'cancelled': 'cancelled',
    'returned': 'returned',
    'shipped': 'shipped',
    'processing': 'processing'
} %}

select
    order_date,
    source_batch_id,
    count(distinct order_id) as order_count,
    count(distinct customer_id) as customer_count,
    sum(item_quantity) as item_count,
    {% for status, name in status_names.items() %}
    sum(iff(order_item_status = '{{ status }}', 1, 0)) as {{ name }}_item_count,
    {% endfor %}
    sum(item_amount) as ordered_item_amount,
    sum(completed_sales_amount) as completed_sales_amount,
    sum(completed_cost_amount) as completed_cost_amount,
    sum(completed_gross_margin_amount) as completed_gross_margin_amount,
    sum(cancelled_item_amount) as cancelled_item_amount,
    sum(returned_item_amount) as returned_item_amount,
    sum(iff(is_created_after_extract, 1, 0)) as future_created_item_count
from {{ ref('fct_order_items') }}
group by order_date, source_batch_id

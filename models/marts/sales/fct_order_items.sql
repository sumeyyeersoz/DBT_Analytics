-- Grain: one source order item. Left joins preserve rows; tests reject missing parents.
-- Date allocation uses the parent order timestamp so an order belongs to one day.
with items as (
    select * from {{ ref('stg_thelook__order_items') }}
), orders as (
    select * from {{ ref('stg_thelook__orders') }}
), inventory as (
    select * from {{ ref('stg_thelook__inventory_items') }}
), joined as (
    select
        i.order_item_id,
        i.order_id,
        i.customer_id,
        i.product_id,
        i.inventory_item_id,
        o.created_at as order_created_at,
        o.created_at::date as order_date,
        i.created_at as item_created_at,
        i.shipped_at,
        i.delivered_at,
        i.returned_at,
        i.order_item_status,
        1::number(38, 0) as item_quantity,
        i.sale_price::number(18, 4) as item_amount,
        inv.cost::number(18, 4) as unit_cost,
        i.is_created_after_extract,
        i.source_batch_id,
        i.extracted_at
    from items i
    left join orders o
        on i.order_id = o.order_id and i.source_batch_id = o.source_batch_id
    left join inventory inv
        on i.inventory_item_id = inv.inventory_item_id and i.source_batch_id = inv.source_batch_id
)
select
    order_item_id, order_id, customer_id, product_id, inventory_item_id,
    order_created_at, order_date, item_created_at, shipped_at, delivered_at, returned_at,
    order_item_status, item_quantity, item_amount, unit_cost,
    iff(order_item_status = 'complete', item_amount, 0)::number(18, 4) as completed_sales_amount,
    iff(order_item_status = 'complete', unit_cost, 0)::number(18, 4) as completed_cost_amount,
    iff(order_item_status = 'complete', item_amount - unit_cost, 0)::number(18, 4) as completed_gross_margin_amount,
    iff(order_item_status = 'cancelled', item_amount, 0)::number(18, 4) as cancelled_item_amount,
    iff(order_item_status = 'returned', item_amount, 0)::number(18, 4) as returned_item_amount,
    is_created_after_extract, source_batch_id, extracted_at
from joined

{{ config(tags=['sales']) }}
with expected as (
    select o.created_at::date as order_date, i.source_batch_id,
        count(distinct o.order_id) as order_count,
        count(distinct i.customer_id) as customer_count,
        count(*) as item_count,
        sum(i.sale_price::number(18, 4)) as ordered_item_amount,
        sum(iff(i.order_item_status = 'complete', i.sale_price::number(18, 4), 0)) as completed_sales_amount,
        sum(iff(i.order_item_status = 'complete', inv.cost::number(18, 4), 0)) as completed_cost_amount,
        sum(iff(i.order_item_status = 'complete', i.sale_price::number(18, 4) - inv.cost::number(18, 4), 0)) as completed_gross_margin_amount,
        sum(iff(i.order_item_status = 'cancelled', i.sale_price::number(18, 4), 0)) as cancelled_item_amount,
        sum(iff(i.order_item_status = 'returned', i.sale_price::number(18, 4), 0)) as returned_item_amount,
        sum(iff(i.is_created_after_extract, 1, 0)) as future_created_item_count,
        sum(iff(i.order_item_status = 'complete', 1, 0)) as completed_item_count,
        sum(iff(i.order_item_status = 'cancelled', 1, 0)) as cancelled_item_count,
        sum(iff(i.order_item_status = 'returned', 1, 0)) as returned_item_count,
        sum(iff(i.order_item_status = 'shipped', 1, 0)) as shipped_item_count,
        sum(iff(i.order_item_status = 'processing', 1, 0)) as processing_item_count
    from {{ ref('stg_thelook__order_items') }} i
    join {{ ref('stg_thelook__orders') }} o on i.order_id = o.order_id and i.source_batch_id = o.source_batch_id
    join {{ ref('stg_thelook__inventory_items') }} inv on i.inventory_item_id = inv.inventory_item_id and i.source_batch_id = inv.source_batch_id
    group by o.created_at::date, i.source_batch_id
)
select coalesce(e.order_date, a.order_date) as order_date
from expected e full outer join {{ ref('mart_daily_sales') }} a
    on e.order_date = a.order_date and e.source_batch_id = a.source_batch_id
where e.order_date is null or a.order_date is null
   or a.order_count is distinct from e.order_count
   or a.customer_count is distinct from e.customer_count
   or a.item_count is distinct from e.item_count
   or a.ordered_item_amount is distinct from e.ordered_item_amount
   or a.completed_sales_amount is distinct from e.completed_sales_amount
   or a.completed_cost_amount is distinct from e.completed_cost_amount
   or a.completed_gross_margin_amount is distinct from e.completed_gross_margin_amount
   or a.cancelled_item_amount is distinct from e.cancelled_item_amount
   or a.returned_item_amount is distinct from e.returned_item_amount
   or a.future_created_item_count is distinct from e.future_created_item_count
   or a.completed_item_count is distinct from e.completed_item_count
   or a.cancelled_item_count is distinct from e.cancelled_item_count
   or a.returned_item_count is distinct from e.returned_item_count
   or a.shipped_item_count is distinct from e.shipped_item_count
   or a.processing_item_count is distinct from e.processing_item_count

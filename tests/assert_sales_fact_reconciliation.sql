{{ config(tags=['sales']) }}
-- Per-key reconciliation, not just total amounts: catches omitted, duplicated or mismatched joins.
select coalesce(f.order_item_id, s.order_item_id) as order_item_id
from {{ ref('fct_order_items') }} f
full outer join {{ ref('stg_thelook__order_items') }} s on f.order_item_id = s.order_item_id
left join {{ ref('stg_thelook__orders') }} o on s.order_id = o.order_id
left join {{ ref('stg_thelook__inventory_items') }} i on s.inventory_item_id = i.inventory_item_id
where f.order_item_id is null or s.order_item_id is null
   or f.order_id is distinct from s.order_id
   or f.customer_id is distinct from s.customer_id
   or f.product_id is distinct from s.product_id
   or f.inventory_item_id is distinct from s.inventory_item_id
   or f.order_item_status is distinct from s.order_item_status
   or f.item_amount is distinct from s.sale_price::number(18, 4)
   or f.unit_cost is distinct from i.cost::number(18, 4)
   or f.order_date is distinct from o.created_at::date
   or f.source_batch_id is distinct from s.source_batch_id
   or f.source_batch_id is distinct from o.source_batch_id
   or f.source_batch_id is distinct from i.source_batch_id
   or f.customer_id is distinct from o.customer_id
   or f.product_id is distinct from i.product_id
   or f.completed_sales_amount is distinct from iff(s.order_item_status = 'complete', s.sale_price::number(18, 4), 0)
   or f.completed_cost_amount is distinct from iff(s.order_item_status = 'complete', i.cost::number(18, 4), 0)
   or f.cancelled_item_amount is distinct from iff(s.order_item_status = 'cancelled', s.sale_price::number(18, 4), 0)
   or f.returned_item_amount is distinct from iff(s.order_item_status = 'returned', s.sale_price::number(18, 4), 0)
   or f.completed_gross_margin_amount <> f.completed_sales_amount - f.completed_cost_amount

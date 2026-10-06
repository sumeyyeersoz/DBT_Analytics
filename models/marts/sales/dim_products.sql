-- Current selected-batch attributes; not a historical product dimension.
select
    product_id,
    product_name,
    brand,
    category,
    department,
    sku,
    retail_price::number(18, 4) as current_retail_price,
    cost::number(18, 4) as current_unit_cost,
    distribution_center_id,
    source_batch_id,
    extracted_at
from {{ ref('stg_thelook__products') }}

-- One row per source key in the explicitly selected complete batch.
select
    id::number(38, 0) as inventory_item_id,
    product_id::number(38, 0) as product_id,
    convert_timezone('UTC', created_at)::timestamp_ntz as created_at,
    convert_timezone('UTC', sold_at)::timestamp_ntz as sold_at,
    cost::float as cost,
    product_category::varchar as product_category,
    product_name::varchar as product_name,
    product_brand::varchar as product_brand,
    product_retail_price::float as product_retail_price,
    product_department::varchar as product_department,
    product_sku::varchar as product_sku,
    product_distribution_center_id::number(38, 0) as distribution_center_id,
    _batch_id::varchar as source_batch_id,
    convert_timezone('UTC', _extracted_at)::timestamp_ntz as extracted_at,
    created_at > _extracted_at as is_created_after_extract
from {{ source('thelook', 'inventory_items') }}
where _batch_id = {{ thelook_batch_literal() }}

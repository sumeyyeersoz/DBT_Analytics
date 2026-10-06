-- One row per source key in the explicitly selected complete batch.
select
    id::number(38, 0) as order_item_id,
    order_id::number(38, 0) as order_id,
    user_id::number(38, 0) as customer_id,
    product_id::number(38, 0) as product_id,
    inventory_item_id::number(38, 0) as inventory_item_id,
    lower(status::varchar) as order_item_status,
    convert_timezone('UTC', created_at)::timestamp_ntz as created_at,
    convert_timezone('UTC', shipped_at)::timestamp_ntz as shipped_at,
    convert_timezone('UTC', delivered_at)::timestamp_ntz as delivered_at,
    convert_timezone('UTC', returned_at)::timestamp_ntz as returned_at,
    sale_price::float as sale_price,
    _batch_id::varchar as source_batch_id,
    convert_timezone('UTC', _extracted_at)::timestamp_ntz as extracted_at,
    created_at > _extracted_at as is_created_after_extract
from {{ source('thelook', 'order_items') }}
where _batch_id = {{ thelook_batch_literal() }}

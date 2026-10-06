-- One row per source key in the explicitly selected complete batch.
select
    id::number(38, 0) as product_id,
    cost::float as cost,
    category::varchar as category,
    name::varchar as product_name,
    brand::varchar as brand,
    retail_price::float as retail_price,
    department::varchar as department,
    sku::varchar as sku,
    distribution_center_id::number(38, 0) as distribution_center_id,
    _batch_id::varchar as source_batch_id,
    convert_timezone('UTC', _extracted_at)::timestamp_ntz as extracted_at
from {{ source('thelook', 'products') }}
where _batch_id = {{ thelook_batch_literal() }}

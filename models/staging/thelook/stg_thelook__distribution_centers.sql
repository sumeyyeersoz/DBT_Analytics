-- One row per source key in the explicitly selected complete batch.
select
    id::number(38, 0) as distribution_center_id,
    name::varchar as distribution_center_name,
    latitude::float as latitude,
    longitude::float as longitude,
    distribution_center_geom::varchar as distribution_center_geom,
    _batch_id::varchar as source_batch_id,
    convert_timezone('UTC', _extracted_at)::timestamp_ntz as extracted_at
from {{ source('thelook', 'distribution_centers') }}
where _batch_id = {{ thelook_batch_literal() }}

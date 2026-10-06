-- One row per source key in the explicitly selected complete batch.
select
    id::number(38, 0) as customer_id,
    first_name::varchar as first_name,
    last_name::varchar as last_name,
    email::varchar as email,
    age::number(38, 0) as age,
    gender::varchar as gender,
    state::varchar as state,
    street_address::varchar as street_address,
    postal_code::varchar as postal_code,
    city::varchar as city,
    country::varchar as country,
    latitude::float as latitude,
    longitude::float as longitude,
    traffic_source::varchar as traffic_source,
    convert_timezone('UTC', created_at)::timestamp_ntz as created_at,
    user_geom::varchar as user_geom,
    _batch_id::varchar as source_batch_id,
    convert_timezone('UTC', _extracted_at)::timestamp_ntz as extracted_at,
    created_at > _extracted_at as is_created_after_extract
from {{ source('thelook', 'users') }}
where _batch_id = {{ thelook_batch_literal() }}

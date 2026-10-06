-- One row per source key in the explicitly selected complete batch.
select
    id::number(38, 0) as event_id,
    user_id::number(38, 0) as customer_id,
    sequence_number::number(38, 0) as sequence_number,
    session_id::varchar as session_id,
    convert_timezone('UTC', created_at)::timestamp_ntz as created_at,
    ip_address::varchar as ip_address,
    city::varchar as city,
    state::varchar as state,
    postal_code::varchar as postal_code,
    browser::varchar as browser,
    traffic_source::varchar as traffic_source,
    uri::varchar as uri,
    event_type::varchar as event_type,
    _batch_id::varchar as source_batch_id,
    convert_timezone('UTC', _extracted_at)::timestamp_ntz as extracted_at,
    created_at > _extracted_at as is_created_after_extract
from {{ source('thelook', 'events') }}
where _batch_id = {{ thelook_batch_literal() }}

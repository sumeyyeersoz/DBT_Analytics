-- Current selected-batch attributes; one row per source user, including non-buyers.
select
    customer_id,
    first_name,
    last_name,
    age,
    gender,
    city,
    state,
    country,
    traffic_source as acquisition_channel,
    created_at as registered_at,
    source_batch_id,
    extracted_at
from {{ ref('stg_thelook__users') }}

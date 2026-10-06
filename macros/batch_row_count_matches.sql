{% test batch_row_count_matches(model, source_table) %}
with raw_count as (
    select count(*) as n from {{ source('thelook', source_table) }}
    where _batch_id = {{ thelook_batch_literal() }}
), staged_count as (
    select count(*) as n from {{ model }}
)
select raw_count.n as raw_rows, staged_count.n as staged_rows
from raw_count cross join staged_count
where raw_count.n = 0 or raw_count.n <> staged_count.n
{% endtest %}

-- One-time setup for the RAW landing layer. Run manually in a Snowsight worksheet.
-- Creates objects inside the existing DBT_PROJECT database only: no new warehouses, users, or roles.
-- Replace <DBT_CLOUD_ROLE> with the role used by the dbt Cloud connection.

use database dbt_project;

create schema if not exists raw
    comment = 'Landing zone for TheLook eCommerce extracts. Append-only; one batch per extract.';

create file format if not exists raw.parquet_format
    type = parquet
    use_logical_type = true;  -- read Parquet timestamps as timestamps, not integers

create stage if not exists raw.thelook_stage
    file_format = raw.parquet_format
    comment = 'Internal stage for TheLook Parquet extracts, organised as <table>/<batch_id>/';

-- dbt reads RAW but never writes to it.
-- Skip these grants if the loading role and the dbt Cloud role are the same role.
grant usage on schema raw to role <DBT_CLOUD_ROLE>;
grant select on all tables in schema raw to role <DBT_CLOUD_ROLE>;
grant select on future tables in schema raw to role <DBT_CLOUD_ROLE>;

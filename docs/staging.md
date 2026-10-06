# TheLook staging

Seven views in DBT_PROJECT.ANALYTICS_STAGING select the complete batch configured by `thelook_batch_id` in dbt_project.yml (currently 20261005T161059Z). The default dbt schema naming rule appends `_staging` to the target schema. No custom schema override is used.

## Transformations

- Each source table maps to one stg_thelook__* view, with the source grain unchanged.
- Source id fields become descriptive identifiers, and user_id becomes customer_id. The users model still represents source users, not a customer dimension.
- Timestamps are converted to UTC TIMESTAMP_NTZ. Status values use lowercase. Monetary floats retain source precision; rounding and revenue definitions belong in downstream models.
- Null values are preserved, including anonymous event users and missing product attributes. Source geography is retained as text.
- source_batch_id and extracted_at preserve lineage. is_created_after_extract flags future creation timestamps without dropping rows.
- No joins, aggregation, silent deduplication, incremental processing or SCD2 is introduced.

## Validation

On 2026-10-06, local dbt Core built all 7 views in Snowflake and all 58 data tests passed (0 warnings/errors/skips). Tests cover primary keys, required foreign keys, 9 relationships, status/event domains, lineage nulls, and nonempty per-table RAW/staging count reconciliation. See staging_validation_20261006.json for individual results.

Starter models remain in Git but are disabled in dbt_project.yml, so their intentional null-key failure is excluded. This is a successful staging build, not a validation of those starter models or a dbt Cloud run.

## Running

In dbt Cloud, synchronize this branch and run `dbt build --select tag:staging` using the existing connection. Locally run `.venv/Scripts/python.exe scripts/dbt_local.py build --select tag:staging`. The local wrapper loads the ignored .env and uses the keypair profile target; it does not print credentials.

To switch batches, first validate a complete seven-table load with ingestion/profile_batch.py, then update thelook_batch_id and rebuild all staging views together. A newest batch per table is deliberately not selected automatically. Zero-row/missing batches fail the reconciliation tests; the selected batch must still be verified before deployment.

Full local manifest/run_results evidence is preserved under ignored data/validation/staging_20261006. Never commit credentials or raw datasets.

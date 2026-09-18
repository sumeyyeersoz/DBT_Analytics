# Development workflow

All project code, comments, documentation, and commit messages are written in English.

## Repository and execution

- Repository: https://github.com/sumeyyeersoz/DBT_Analytics
- Local project root: `D:\projects\dbt\_analytics\_101`
- Edit and review files in VS Code; execute dbt in the existing dbt Cloud project.
- Do not install dbt Core locally for this workflow.
- Use feature branches and focused commits. Synchronize the same branch between local Git and dbt Cloud before editing in either location.
- Never discard uncommitted Cloud or local changes to resolve synchronization problems.

## Existing Snowflake configuration

- Database: `DBT_PROJECT`
- Development schema: `ANALYTICS`
- Warehouse: `COMPUTE_WH`
- The existing dbt Cloud connection test passed on 2026-09-18. This validates connectivity, not model correctness or every required database privilege.
- Retain the existing connection. Do not create additional warehouses, roles, or users as part of the initial setup.

## Credentials and data

Keep credentials outside Git. If the optional dbt platform CLI is configured later, its credentials file belongs in the user-level `.dbt` directory, never in this repository.

Downloaded public datasets belong in the ignored `data/` directory. Only small, reviewed reference mappings belong in `seeds/`.

## Current baseline and verification

The initial dbt Cloud starter files were preserved before customization. They are examples, not the implemented e-commerce model.

The starter `my_first_dbt_model` deliberately contains a null `id`, while its schema declares a `not_null` test. A full starter build is therefore expected to report a test failure. Do not claim that the baseline has passed all tests.

For syntax and project parsing in dbt Cloud, run:

```sh
dbt parse
```

No local dbt execution has been performed. TheLook ingestion, dimensional models, incremental processing, and SCD2 are not implemented yet.

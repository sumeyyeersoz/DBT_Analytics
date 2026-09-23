# Development workflow

All project code, comments, documentation, and commit messages are written in English.

## Repository and execution

- Repository: https://github.com/sumeyyeersoz/DBT_Analytics
- Local project root: the Git repository root (on macOS: `~/VScode Projects/personal/DBT_Analytics`).
- Edit and review files in VS Code; execute models, tests, and snapshots in the existing dbt Cloud project.
- Local dbt Core is used only for offline validation (`dbt parse`, `dbt compile` without a warehouse connection). See "Local dbt Core" below.
- Branch names describe the work (`feature/...`, `fix/...`, `docs/...`) and do not reference tools.
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

## Local dbt Core

dbt Core runs from a project-local virtual environment (`.venv/`, git-ignored), isolated from any globally installed dbt:

```sh
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements-dev.txt
cp profiles.example.yml profiles.yml   # git-ignored; holds env_var() references only
.venv/bin/dbt parse --profiles-dir .
```

Connection values are read from `SNOWFLAKE_*` environment variables. Never write real credentials into `profiles.yml` or any tracked file.

## Current baseline and verification

The initial dbt Cloud starter files were preserved before customization. They are examples, not the implemented e-commerce model.

The starter `my_first_dbt_model` deliberately contains a null `id`, while its schema declares a `not_null` test. A full starter build is therefore expected to report a test failure. Do not claim that the baseline has passed all tests.

For syntax and project parsing, run `dbt parse` in dbt Cloud or locally as shown above. Parsing validates project structure, YAML, and Jinja; it does not connect to Snowflake or run tests.

TheLook ingestion, dimensional models, incremental processing, and SCD2 are not implemented yet.

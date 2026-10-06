# Development workflow

All project code, comments, documentation, and commit messages are written in English.

## Repository and execution

- Repository: https://github.com/sumeyyeersoz/DBT_Analytics
- Local project root: the Git repository root (on Windows: D:/projects/dbt_analytics_101; on macOS: `~/VScode Projects/personal/DBT_Analytics`).
- Edit and review files in VS Code. The existing dbt Cloud project remains supported; local dbt Core can also execute approved builds using the keypair target. See staging.md for the local command.
- Use local `dbt parse` for offline validation and the keypair target for warehouse builds. Do not assume `dbt compile` is offline: compilation can require a warehouse connection. See "Local dbt Core" below.
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

dbt Core runs from a project-local virtual environment (`.venv/`, git-ignored), isolated from any globally installed dbt. Install uv first, then run these commands from the repository root.

Windows (PowerShell):

```powershell
uv python install 3.12
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt -r requirements-ingestion.txt
if (-not (Test-Path profiles.yml)) { Copy-Item profiles.example.yml profiles.yml }
.\.venv\Scripts\dbt.exe parse --profiles-dir .
.\.venv\Scripts\python.exe ingestion\thelook.py --help
```

If uv is not found after installation, restart the terminal or invoke it at `$env:USERPROFILE\.local\bin\uv.exe`. Select `.venv\Scripts\python.exe` as the interpreter in VS Code. Direct executable paths work without activating the environment or changing PowerShell execution policy.

macOS:

```sh
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements-dev.txt
cp profiles.example.yml profiles.yml   # git-ignored; holds env_var() references only
.venv/bin/dbt parse --profiles-dir .
```

Connection values are read from `SNOWFLAKE_*` environment variables. Never write real credentials into `profiles.yml` or any tracked file.

## Current baseline and verification

### Windows ingestion credentials and smoke test

1. Copy `.env.example` to `.env` only if `.env` does not already exist. Fill in the personal Google project ID and Snowflake connection values locally. Never paste private keys or passwords into chat.
2. With the Google Cloud CLI installed, run the following in PowerShell and sign in with the personal Google account that has access to the project:

   ```powershell
   & "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd" auth application-default login
   ```

3. Set `SNOWFLAKE_PRIVATE_KEY_PATH` in `.env` to an existing key outside the repository. Its public key must already be registered to the configured Snowflake user. The key-pair login used by ingestion is separate from the dbt Cloud connection.
4. Check the existing RAW objects before running `ingestion/snowflake_setup.sql` in Snowflake. Replace the role placeholder before executing grants; skip grants if both roles are the same.
5. Start with one table:

   ```powershell
   .\.venv\Scripts\python.exe ingestion\thelook.py extract --tables distribution_centers
   # Substitute the batch ID printed by extract:
   .\.venv\Scripts\python.exe ingestion\thelook.py load --batch-id <batch_id>
   ```

6. Compare the Parquet and RAW row counts for that batch. Repeat the load for the same batch and confirm the RAW count is unchanged before extracting all seven tables.

Credential setup, successful extraction, and successful loading are separate checks; local CLI/import checks do not validate cloud access.

The initial dbt Cloud starter files were preserved before customization. They are examples, not the implemented e-commerce model.

The starter `my_first_dbt_model` deliberately contains a null `id`, while its schema declares a `not_null` test. A full starter build is therefore expected to report a test failure. Do not claim that the baseline has passed all tests.

For syntax and project parsing, run `dbt parse` in dbt Cloud or locally as shown above. Parsing validates project structure, YAML, and Jinja; it does not connect to Snowflake or run tests.

TheLook extract/load code and Snowflake RAW setup SQL are implemented in `ingestion/`. On 2026-10-05, a Windows smoke test extracted and loaded all 10 distribution_centers rows in batch 20261005T090850Z. Snowflake contained 10 rows and 10 distinct IDs for that batch before and after repeating the load; the repeat skipped the already loaded file. The full seven-table batch 20261005T161059Z was extracted on 2026-10-05 and loaded and profiled on 2026-10-06. All Parquet/RAW counts matched, candidate keys were non-null and unique within the batch, all nine checked relationships had no non-null orphans, and both order consistency checks passed. See [the batch profile](thelook_profile_20261005T161059Z.md) for nullable fields, future timestamps, and modeling limitations. Reproduce the aggregate checks with `.venv/Scripts/python.exe ingestion/profile_batch.py --batch-id 20261005T161059Z`. Configure Google credentials and the ignored `.env` before running ingestion; store the Snowflake private key outside the repository. Use a Windows path such as `C:/Users/your-user/.keys/snowflake.p8` for `SNOWFLAKE_PRIVATE_KEY_PATH`.

Sales dimensions and marts are implemented and validated; see sales_models.md. Incremental processing and SCD2 remain deferred until source change behavior is established.

## Staging milestone

On 2026-10-06, seven staging views and 58 data tests passed in Snowflake via local dbt Core. See [staging design and validation](staging.md). Sales marts were subsequently implemented and validated; see [sales models](sales_models.md).

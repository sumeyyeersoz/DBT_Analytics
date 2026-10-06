"""Extract TheLook eCommerce from BigQuery and load it into Snowflake RAW.

Two steps, run separately so a failed load never forces a new extract:

    python ingestion/thelook.py extract            # BigQuery -> data/thelook/<batch_id>/*.parquet
    python ingestion/thelook.py load               # latest local batch -> DBT_PROJECT.RAW
    python ingestion/thelook.py load --batch-id 20260923T142233Z

Every extract is an immutable batch. Each row carries _BATCH_ID and _EXTRACTED_AT, and RAW tables
are append-only, so the history of a record across daily extracts is preserved for dbt to model.
Loads are idempotent: Snowflake's COPY load metadata skips files that were already loaded.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv

SOURCE_DATASET = "bigquery-public-data.thelook_ecommerce"
TABLES = (
    "distribution_centers",
    "events",
    "inventory_items",
    "order_items",
    "orders",
    "products",
    "users",
)
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "thelook"
BATCH_ID_FORMAT = "%Y%m%dT%H%M%SZ"
BATCH_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")
SUCCESS_MARKER = "_SUCCESS"  # written only after every table in a batch extracted cleanly
BIGQUERY_PAGE_SIZE = 50_000  # rows per API page; bounds memory use for the 2.4M-row events table

RAW_SCHEMA = "RAW"
STAGE = f"{RAW_SCHEMA}.THELOOK_STAGE"
FILE_FORMAT = f"{RAW_SCHEMA}.PARQUET_FORMAT"

log = logging.getLogger("thelook")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Environment variable {name} is not set. See .env.example.")
    return value


# --------------------------------------------------------------------------- extract


def add_batch_columns(batch: pa.RecordBatch, batch_id: str, extracted_at: datetime) -> pa.RecordBatch:
    """Upper-case column names (Snowflake's default identifier case) and append lineage columns."""
    columns = list(batch.columns) + [
        pa.array([batch_id] * batch.num_rows, type=pa.string()),
        pa.array([extracted_at] * batch.num_rows, type=pa.timestamp("us", tz="UTC")),
    ]
    names = [name.upper() for name in batch.schema.names] + ["_BATCH_ID", "_EXTRACTED_AT"]
    return pa.RecordBatch.from_arrays(columns, names=names)


def extract_table(client, table_name: str, batch_dir: Path, batch_id: str, extracted_at: datetime) -> int:
    table = client.get_table(f"{SOURCE_DATASET}.{table_name}")
    # list_rows reads table data directly (tabledata.list): no query is run, so no bytes are billed.
    rows = client.list_rows(table, page_size=BIGQUERY_PAGE_SIZE)

    target = batch_dir / f"{table_name}.parquet"
    partial = target.with_suffix(".parquet.partial")
    written = 0
    writer = None
    try:
        for record_batch in rows.to_arrow_iterable():
            record_batch = add_batch_columns(record_batch, batch_id, extracted_at)
            if writer is None:
                writer = pq.ParquetWriter(partial, record_batch.schema, compression="snappy")
            writer.write_batch(record_batch)
            written += record_batch.num_rows
    finally:
        if writer is not None:
            writer.close()

    if written == 0:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"{table_name}: source returned no rows")
    if written != table.num_rows:
        # The source refreshes daily; a mismatch means it changed mid-extract. Fail rather than land a torn batch.
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"{table_name}: wrote {written} rows but table metadata reports {table.num_rows}")

    partial.rename(target)  # only complete files ever carry the .parquet name
    return written


def run_extract(tables: list[str]) -> None:
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud import bigquery

    try:
        client = bigquery.Client(project=require_env("GCP_PROJECT_ID"))
    except DefaultCredentialsError as exc:
        raise ConfigError("No Google credentials found. Run: gcloud auth application-default login") from exc

    extracted_at = datetime.now(timezone.utc).replace(microsecond=0)
    batch_id = extracted_at.strftime(BATCH_ID_FORMAT)
    batch_dir = DATA_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=False)
    log.info("Extracting batch %s into %s", batch_id, batch_dir.relative_to(REPO_ROOT))

    for table_name in tables:
        row_count = extract_table(client, table_name, batch_dir, batch_id, extracted_at)
        log.info("  %-22s %10d rows", table_name, row_count)

    (batch_dir / SUCCESS_MARKER).touch()  # load refuses batches without it
    log.info("Extract complete. Load it with: python ingestion/thelook.py load --batch-id %s", batch_id)


# --------------------------------------------------------------------------- load


def latest_batch_id() -> str:
    batches = sorted(p.name for p in DATA_DIR.glob("*") if p.is_dir() and BATCH_ID_PATTERN.match(p.name))
    if not batches:
        raise ConfigError(f"No extracted batches found in {DATA_DIR.relative_to(REPO_ROOT)}. Run extract first.")
    return batches[-1]


def connect_snowflake():
    import snowflake.connector

    key_path = Path(require_env("SNOWFLAKE_PRIVATE_KEY_PATH")).expanduser()
    if not key_path.is_file():
        raise ConfigError(f"SNOWFLAKE_PRIVATE_KEY_PATH does not point to a file: {key_path}")
    if REPO_ROOT in key_path.resolve().parents:
        raise ConfigError("The Snowflake private key must be stored outside the repository.")

    return snowflake.connector.connect(
        account=require_env("SNOWFLAKE_ACCOUNT"),
        user=require_env("SNOWFLAKE_USER"),
        role=require_env("SNOWFLAKE_ROLE"),
        warehouse=require_env("SNOWFLAKE_WAREHOUSE"),
        database=require_env("SNOWFLAKE_DATABASE"),
        schema=RAW_SCHEMA,
        authenticator="SNOWFLAKE_JWT",
        private_key_file=str(key_path),
        private_key_file_pwd=os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None,
        session_parameters={"QUERY_TAG": "thelook_ingestion"},
    )


def load_table(cursor, table_name: str, parquet_file: Path, batch_id: str) -> int:
    stage_path = f"@{STAGE}/{table_name}/{batch_id}/"
    raw_table = f"{RAW_SCHEMA}.{table_name.upper()}"

    # OVERWRITE = FALSE keeps a re-run from replacing an already staged file.
    cursor.execute(f"put 'file://{parquet_file.as_posix()}' {stage_path} auto_compress = false overwrite = false")

    # First load creates the table from the Parquet schema; later loads append to it.
    cursor.execute(
        f"""
        create table if not exists {raw_table} using template (
            select array_agg(object_construct(*)) within group (order by order_id)
            from table(infer_schema(location => '{stage_path}', file_format => '{FILE_FORMAT}'))
        )
        """
    )

    # COPY skips files already recorded in the table's load metadata, which makes re-runs safe.
    cursor.execute(
        f"""
        copy into {raw_table}
        from {stage_path}
        file_format = (format_name = '{FILE_FORMAT}')
        match_by_column_name = case_insensitive
        on_error = abort_statement
        """
    )
    results = cursor.fetchall()
    column_names = [col[0].lower() for col in cursor.description]
    if "rows_loaded" not in column_names:
        return 0  # "Copy executed with 0 files processed": this batch was already loaded
    rows_loaded_index = column_names.index("rows_loaded")
    return sum(int(row[rows_loaded_index]) for row in results)


def run_load(batch_id: str | None) -> None:
    batch_id = batch_id or latest_batch_id()
    if not BATCH_ID_PATTERN.match(batch_id):
        raise ConfigError(f"Invalid batch id: {batch_id!r}")
    batch_dir = DATA_DIR / batch_id
    if not (batch_dir / SUCCESS_MARKER).is_file():
        raise ConfigError(f"Batch {batch_id} is incomplete (no {SUCCESS_MARKER} marker). Re-run extract.")
    parquet_files = {p.stem: p for p in batch_dir.glob("*.parquet")}
    unknown = set(parquet_files) - set(TABLES)
    if unknown:
        raise ConfigError(f"Unexpected files in batch {batch_id}: {sorted(unknown)}")
    if not parquet_files:
        raise ConfigError(f"Batch {batch_id} contains no Parquet files")

    log.info("Loading batch %s into %s", batch_id, RAW_SCHEMA)
    with connect_snowflake() as connection, connection.cursor() as cursor:
        for table_name in sorted(parquet_files):
            rows_loaded = load_table(cursor, table_name, parquet_files[table_name], batch_id)
            status = f"{rows_loaded:10d} rows" if rows_loaded else "   already loaded, skipped"
            log.info("  %-22s %s", table_name, status)
    log.info("Load complete.")


# --------------------------------------------------------------------------- cli


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subcommands = parser.add_subparsers(dest="command", required=True)

    extract_parser = subcommands.add_parser("extract", help="BigQuery -> local Parquet batch")
    extract_parser.add_argument("--tables", nargs="+", choices=TABLES, default=list(TABLES))

    load_parser = subcommands.add_parser("load", help="local Parquet batch -> Snowflake RAW")
    load_parser.add_argument("--batch-id", help="defaults to the most recent local batch")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv(REPO_ROOT / ".env")

    try:
        if args.command == "extract":
            run_extract(args.tables)
        else:
            run_load(args.batch_id)
    except ConfigError as exc:
        log.error("%s", exc)
        return 2
    except Exception:
        log.exception("%s failed", args.command)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

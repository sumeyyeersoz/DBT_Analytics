"""Validate a complete local batch against Snowflake RAW and write aggregate profiles."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
from dotenv import load_dotenv
from thelook import REPO_ROOT, DATA_DIR, TABLES, BATCH_ID_PATTERN, connect_snowflake

KEYS = {name: 'ID' for name in TABLES} | {'orders': 'ORDER_ID'}
RELATIONSHIPS = [
    ('orders', 'USER_ID', 'users', 'ID'),
    ('order_items', 'ORDER_ID', 'orders', 'ORDER_ID'),
    ('order_items', 'USER_ID', 'users', 'ID'),
    ('order_items', 'PRODUCT_ID', 'products', 'ID'),
    ('order_items', 'INVENTORY_ITEM_ID', 'inventory_items', 'ID'),
    ('inventory_items', 'PRODUCT_ID', 'products', 'ID'),
    ('inventory_items', 'PRODUCT_DISTRIBUTION_CENTER_ID', 'distribution_centers', 'ID'),
    ('products', 'DISTRIBUTION_CENTER_ID', 'distribution_centers', 'ID'),
    ('events', 'USER_ID', 'users', 'ID'),
]


def profile(batch_id):
    if not BATCH_ID_PATTERN.fullmatch(batch_id):
        raise ValueError('Invalid batch ID')
    directory = DATA_DIR / batch_id
    if not (directory / '_SUCCESS').is_file():
        raise ValueError('Batch is incomplete')
    if {p.stem for p in directory.glob('*.parquet')} != set(TABLES):
        raise ValueError('A complete seven-table batch is required')
    result = {'batch_id': batch_id, 'profiled_at_utc': datetime.now(timezone.utc).isoformat(),
              'tables': {}, 'relationships': [], 'business_checks': {}}
    with connect_snowflake() as connection, connection.cursor() as cursor:
        cursor.execute('ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 180')
        cursor.execute("ALTER SESSION SET TIMEZONE = 'UTC'")
        cursor.execute("ALTER SESSION SET QUERY_TAG = 'thelook_batch_profile'")
        for name in TABLES:
            parquet = pq.ParquetFile(directory / f'{name}.parquet')
            schema = parquet.schema_arrow
            key = KEYS[name]
            expressions = ['COUNT(*)', f'COUNT(DISTINCT "{key}")']
            expressions += [f'COUNT(*) - COUNT("{f.name}")' for f in schema]
            dates = [f.name for f in schema if 'timestamp' in str(f.type) or str(f.type).startswith('date')]
            for column in dates:
                expressions += [f'MIN("{column}")', f'MAX("{column}")']
            expressions += [f'COALESCE(COUNT_IF("{column}" > _EXTRACTED_AT), 0)' for column in dates if not column.startswith('_')]
            cursor.execute(f'SELECT {", ".join(expressions)} FROM RAW.{name.upper()} WHERE _BATCH_ID = %s', (batch_id,))
            row = cursor.fetchone()
            nulls = dict(zip(schema.names, row[2:2 + len(schema)]))
            offset = 2 + len(schema)
            ranges = {column: {'min': row[offset + 2*i], 'max': row[offset + 2*i + 1]} for i, column in enumerate(dates)}
            table = {'parquet_rows': parquet.metadata.num_rows, 'snowflake_rows': row[0], 'key': key,
                     'distinct_keys': row[1], 'duplicate_key_rows': row[0] - nulls[key] - row[1],
                     'null_counts': nulls, 'date_ranges': ranges,
                     'schema': {f.name: str(f.type) for f in schema}}
            business_dates = [column for column in dates if not column.startswith('_')]
            table['timestamps_after_extract'] = dict(zip(business_dates, row[offset + 2 * len(dates):]))
            table['row_count_match'] = table['parquet_rows'] == table['snowflake_rows']
            for category in ('STATUS', 'EVENT_TYPE'):
                if category in schema.names:
                    cursor.execute(f'SELECT "{category}", COUNT(*) FROM RAW.{name.upper()} WHERE _BATCH_ID = %s GROUP BY 1 ORDER BY 2 DESC', (batch_id,))
                    table[category.lower() + '_counts'] = dict(cursor.fetchall())
            result['tables'][name] = table
            print(f'{name}: local={table["parquet_rows"]}, RAW={row[0]}, distinct {key}={row[1]}', flush=True)
        for child, fk, parent, pk in RELATIONSHIPS:
            cursor.execute(f'''SELECT COUNT(*) FROM RAW.{child.upper()} c
                WHERE c._BATCH_ID = %s AND c."{fk}" IS NOT NULL AND NOT EXISTS
                (SELECT 1 FROM RAW.{parent.upper()} p WHERE p._BATCH_ID = %s AND p."{pk}" = c."{fk}")''', (batch_id, batch_id))
            missing = cursor.fetchone()[0]
            result['relationships'].append({'child': child, 'foreign_key': fk, 'parent': parent, 'parent_key': pk, 'orphan_rows': missing})
            print(f'{child}.{fk} -> {parent}.{pk}: {missing} orphan rows', flush=True)
        cursor.execute('''SELECT COUNT(*) FROM RAW.ORDER_ITEMS i JOIN RAW.ORDERS o
            ON i.ORDER_ID = o.ORDER_ID AND o._BATCH_ID = %s
            WHERE i._BATCH_ID = %s AND i.USER_ID <> o.USER_ID''', (batch_id, batch_id))
        result['business_checks']['order_item_user_mismatches'] = cursor.fetchone()[0]
        cursor.execute('''SELECT COUNT(*) FROM RAW.ORDERS o LEFT JOIN
            (SELECT ORDER_ID, COUNT(*) AS N FROM RAW.ORDER_ITEMS WHERE _BATCH_ID = %s GROUP BY ORDER_ID) i
            ON o.ORDER_ID = i.ORDER_ID WHERE o._BATCH_ID = %s AND o.NUM_OF_ITEM <> COALESCE(i.N, 0)''', (batch_id, batch_id))
        result['business_checks']['order_item_count_mismatches'] = cursor.fetchone()[0]
    output = directory / 'profile.json'
    output.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    print(f'Aggregate profile saved: {output}', flush=True)
    failures = [name for name, t in result['tables'].items()
                if not t['row_count_match'] or t['null_counts'][t['key']] or t['duplicate_key_rows']]
    if failures:
        raise RuntimeError(f'Count or primary-key validation failed: {failures}')
    return result


def write_report(result):
    batch = result['batch_id']
    lines = [f'# TheLook batch profile: {batch}', '',
             f"Profiled at UTC: {result['profiled_at_utc']}", '',
             'Scope: all seven tables in one extract batch, compared with Snowflake RAW. All checks filter by this batch ID; earlier batches are excluded.', '',
             '## Row counts and candidate primary keys', '',
             '| Table | Parquet rows | RAW rows | Key | Distinct keys | Null keys | Duplicate key rows |',
             '|---|---:|---:|---|---:|---:|---:|']
    for name, t in result['tables'].items():
        lines.append(f"| {name} | {t['parquet_rows']:,} | {t['snowflake_rows']:,} | {t['key']} | {t['distinct_keys']:,} | {t['null_counts'][t['key']]:,} | {t['duplicate_key_rows']:,} |")
    lines += ['', '## Nullable fields and temporal coverage (UTC)', '']
    for name, t in result['tables'].items():
        lines += [f'### {name}', '']
        nulls = [f'{k}: {v:,}' for k, v in t['null_counts'].items() if v]
        lines += ['Observed null counts: ' + ('; '.join(nulls) if nulls else 'none') + '.', '']
        for column, dates in t['date_ranges'].items():
            if not column.startswith('_'):
                lines.append(f"- {column}: {dates['min']} through {dates['max']}")
        for column, count in t['timestamps_after_extract'].items():
            if count:
                lines.append(f'- {column} after extraction time: {count:,} rows')
        for category in ('status_counts', 'event_type_counts'):
            if category in t:
                lines += ['', category.replace('_', ' ').capitalize() + ': ' + '; '.join(f'{k}: {v:,}' for k, v in t[category].items()) + '.']
        lines.append('')
    lines += ['## Relationships', '', '| Child key | Parent key | Non-null orphan rows |', '|---|---|---:|']
    for r in result['relationships']:
        lines.append(f"| {r['child']}.{r['foreign_key']} | {r['parent']}.{r['parent_key']} | {r['orphan_rows']:,} |")
    lines += ['', 'Null foreign keys are reported separately above and are not counted as orphans.', '', '## Business consistency', '']
    lines += [f'- {k}: {v:,}' for k, v in result['business_checks'].items()]
    lines += ['', '## Modeling implications and limits', '',
              '- RAW is append-only. Candidate keys apply within a batch; use (_BATCH_ID, source key) for RAW tests. Staging must explicitly select a complete batch before enforcing source-key uniqueness.',
              '- Tables were read sequentially. A shared batch ID does not provide a transactionally consistent source snapshot. Count equality cannot detect every concurrent source change.',
              '- Source timestamps can be later than extraction time. Preserve them, flag them for business interpretation, and avoid assuming that all source timestamps are bounded by the ingestion date.',
              '- One full snapshot does not establish source update/delete behavior or provide historical dimension changes. Incremental loading and SCD2 need evidence from subsequent extracts.',
              '- Nullable lifecycle timestamps and anonymous event users must be assessed before adding not_null tests.',
              '- This profile checks counts, candidate keys, nulls, temporal ranges and listed relationships; it does not prove full row-by-row equality or validate all business rules.',
              '- No dbt business models or data tests were executed in this profiling step.', '']
    output = REPO_ROOT / 'docs' / f'thelook_profile_{batch}.md'
    output.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Report saved: {output}', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-id', required=True)
    args = parser.parse_args()
    load_dotenv(REPO_ROOT / '.env')
    write_report(profile(args.batch_id))

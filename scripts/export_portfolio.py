"""Export validated portfolio outputs and object DDL before warehouse access expires."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ingestion.thelook import connect_snowflake


def export():
    load_dotenv(ROOT / '.env')
    manifest = json.loads((ROOT / 'target/manifest.json').read_text(encoding='utf-8'))
    batch = manifest['metadata'].get('generated_at')
    destination = ROOT / 'data/portfolio_backup' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination.mkdir(parents=True, exist_ok=False)
    relation = manifest['nodes']['model.my_new_project.mart_daily_sales']['relation_name']
    with connect_snowflake() as connection, connection.cursor() as cursor:
        cursor.execute("ALTER SESSION SET QUERY_TAG = 'portfolio_backup'")
        cursor.execute("ALTER SESSION SET TIMEZONE = 'UTC'")
        cursor.execute('ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 180')
        cursor.execute(f'SELECT * FROM {relation} ORDER BY ORDER_DATE')
        names = [c[0].lower() for c in cursor.description]
        rows = [dict(zip(names, row)) for row in cursor.fetchall()]
        assert rows, 'Daily mart is empty'
        batches = sorted({r['source_batch_id'] for r in rows})
        assert len(batches) == 1, 'Expected a single batch'
        pq.write_table(pa.Table.from_pylist(rows), destination / 'mart_daily_sales.parquet', compression='snappy')
        (destination / 'mart_daily_sales.json').write_text(json.dumps(rows, indent=2, default=str), encoding='utf-8')
        cursor.execute(f'SELECT COUNT(*), SUM(ITEM_COUNT), SUM(ORDER_COUNT) FROM {relation}')
        remote = cursor.fetchone()
        local = (len(rows), sum(r['item_count'] for r in rows), sum(r['order_count'] for r in rows))
        assert local == remote, (local, remote)
        ddl = []
        resources = list(manifest['sources'].values()) + [n for n in manifest['nodes'].values() if n['resource_type'] == 'model']
        for n in resources:
            object_name = n['relation_name']
            cursor.execute("SELECT GET_DDL('TABLE', %s, TRUE)", (object_name,))
            ddl.append('-- ' + object_name + '\n' + cursor.fetchone()[0] + '\n')
        (destination / 'objects.sql').write_text('\n'.join(ddl), encoding='utf-8')
    for name in ['manifest.json', 'catalog.json', 'static_index.html', 'index.html']:
        p = ROOT / 'target' / name
        if p.exists():
            shutil.copy2(p, destination / name)
    # Original build evidence is archived separately; docs generation overwrites target artifacts.
    shutil.copytree(ROOT / 'data/validation', destination / 'validation')
    verification = {'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'batch_id': batches[0],
                    'daily_rows': len(rows), 'order_items': int(local[1]), 'orders': int(local[2]),
                    'ddl_objects': len(ddl), 'dbt_manifest_generated_at': batch,
                    'daily_parquet_rows': pq.ParquetFile(destination / 'mart_daily_sales.parquet').metadata.num_rows}
    verification['sha256'] = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}
    (destination / 'verification.json').write_text(json.dumps(verification, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in verification.items() if k != 'sha256'}, indent=2))
    print('Backup:', destination)


if __name__ == '__main__':
    export()

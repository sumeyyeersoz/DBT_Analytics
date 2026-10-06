"""Run local dbt with the ignored .env and the key-pair profile."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from dbt.cli.main import dbtRunner

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    load_dotenv(root / ".env")
    os.environ.setdefault("DBT_SEND_ANONYMOUS_USAGE_STATS", "false")
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/dbt_local.py <dbt command> [options]")
    result = dbtRunner().invoke(sys.argv[1:] + ["--profiles-dir", str(root), "--target", "keypair"])
    raise SystemExit(0 if result.success else 1)

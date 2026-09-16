"""Test isolation: both stores point at throwaway databases, never a live one.

Three stores, and every one of them is destructive if it is the wrong one.

`UNITI_DSN` names the log the tests write to. `UNITI_OPS_DSN` matters just as
much and is easier to forget: compiling a projection *drops and rebuilds* its
table, so a test run that inherits somebody's operational store silently
empties it. `UNITI_P2_KERNEL_DSN` is the sharpest of the three — the bootstrap
test re-applies `001_schema.sql`, which begins by dropping all three kernel
tables, so a run pointed at a live modular kernel destroys every module sealed
into it and still reports green.

All three are pinned here, before any component is imported, because a
component reads its DSN when it is imported or constructed.
"""

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
import psycopg

CHECK_DSN = 'postgresql://uniti:uniti@localhost:5433/uniti_check'
CHECK_OPS_DSN = 'postgresql://uniti:uniti@localhost:5433/uniti_check_ops'
CHECK_P2_DSN = 'postgresql://uniti:uniti@localhost:5433/uniti_check_p2'

os.environ.setdefault('UNITI_DSN', CHECK_DSN)
os.environ.setdefault('UNITI_OPS_DSN', CHECK_OPS_DSN)
os.environ.setdefault('UNITI_P2_KERNEL_DSN', CHECK_P2_DSN)

try:
    import components.kernel.perform as perform
    perform.DSN = os.environ['UNITI_DSN']
except Exception:
    pass


def _ensure_database(dsn):
    """Create the database this DSN names, if it is not there yet."""
    parts = urlsplit(dsn)
    name = parts.path.lstrip('/')
    if not name:
        return
    admin = urlunsplit((parts.scheme, parts.netloc, '/postgres', '', ''))
    try:
        with psycopg.connect(admin, autocommit=True, connect_timeout=2) as conn:
            exists = conn.execute(
                'SELECT 1 FROM pg_database WHERE datname = %s', (name,)
            ).fetchone()
            if not exists:
                conn.execute(f'CREATE DATABASE "{name}"')
    except Exception:
        pass


@pytest.fixture(scope='session', autouse=True)
def reset_test_db():
    dsn = os.environ.get('UNITI_DSN', CHECK_DSN)
    ops_dsn = os.environ.get('UNITI_OPS_DSN', CHECK_OPS_DSN)
    p2_dsn = os.environ.get('UNITI_P2_KERNEL_DSN', CHECK_P2_DSN)

    # Refuse to run against a store that is not a throwaway. A green test run
    # that quietly rebuilt an operational store is worse than a failing one.
    if 'uniti_check' not in ops_dsn:
        raise pytest.UsageError(
            f"UNITI_OPS_DSN points at {ops_dsn!r}, which is not a throwaway "
            f"store. Compiling a projection drops and rebuilds its table, so "
            f"this run would overwrite it. Use {CHECK_OPS_DSN!r}."
        )

    if 'uniti_check' not in p2_dsn:
        raise pytest.UsageError(
            f"UNITI_P2_KERNEL_DSN points at {p2_dsn!r}, which is not a throwaway "
            f"kernel. The bootstrap test re-applies the schema, which drops the "
            f"log, so this run would destroy every module sealed into it. "
            f"Use {CHECK_P2_DSN!r}."
        )

    if 'uniti_check' in dsn:
        _ensure_database(dsn)
        _ensure_database(ops_dsn)
        _ensure_database(p2_dsn)
        root = Path(__file__).resolve().parent.parent
        schema_sql = (root / 'components' / 'kernel' / '001_schema.sql').read_text(encoding='utf-8')
        try:
            with psycopg.connect(dsn, autocommit=True, connect_timeout=2) as conn:
                conn.execute(schema_sql)
        except Exception:
            pass

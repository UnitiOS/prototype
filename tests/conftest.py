"""Test isolation: both stores point at throwaway databases, never a live one.

Two stores, and each is destructive if it is the wrong one.

`UNITI_DSN` names the log the tests write to, and this file re-applies
`001_schema.sql` to it, which begins by dropping all three kernel tables.
`UNITI_OPS_DSN` is easier to forget: compiling a projection *drops and
rebuilds* its table, so a test run that inherits somebody's operational store
silently empties it.

Both are pinned here, before any component is imported, because a
component reads its DSN when it is imported or constructed.
"""

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
import psycopg

CHECK_DSN = 'postgresql://uniti:uniti@localhost:5433/uniti_check'
CHECK_OPS_DSN = 'postgresql://uniti:uniti@localhost:5433/uniti_check_ops'

os.environ.setdefault('UNITI_DSN', CHECK_DSN)
os.environ.setdefault('UNITI_OPS_DSN', CHECK_OPS_DSN)

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

    # Refuse to run against a store that is not a throwaway. A green test run
    # that quietly rebuilt an operational store is worse than a failing one.
    if 'uniti_check' not in ops_dsn:
        raise pytest.UsageError(
            f"UNITI_OPS_DSN points at {ops_dsn!r}, which is not a throwaway "
            f"store. Compiling a projection drops and rebuilds its table, so "
            f"this run would overwrite it. Use {CHECK_OPS_DSN!r}."
        )

    if 'uniti_check' not in dsn:
        raise pytest.UsageError(
            f"UNITI_DSN points at {dsn!r}, which is not a throwaway log. This "
            f"run re-applies the kernel schema, which drops every table in it. "
            f"Use {CHECK_DSN!r}."
        )

    if 'uniti_check' in dsn:
        _ensure_database(dsn)
        _ensure_database(ops_dsn)
        root = Path(__file__).resolve().parent.parent
        schema_sql = (root / 'components' / 'kernel' / '001_schema.sql').read_text(encoding='utf-8')
        try:
            with psycopg.connect(dsn, autocommit=True, connect_timeout=2) as conn:
                conn.execute(schema_sql)
        except Exception:
            pass

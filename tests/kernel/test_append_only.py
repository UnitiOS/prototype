"""The log is append-only, and the database is what enforces it.

`components/kernel/002_guard_test.sql` proves this from psql. This file proves it from the
same client the rest of the code uses, so `pytest tests` covers it.

Run: .venv/Scripts/python.exe -m pytest tests/test_append_only.py
"""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "components" / "kernel"))

from perform import connect, perform  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    with connect() as c:
        yield c


@pytest.fixture(scope="module")
def written(conn):
    """One assertion through the front door, to try to mutate afterwards."""
    _, _, assertion_ids = perform(
        conn,
        actor_id="test",
        action_name="append_only_fixture",
        mint=["student", "monthly_fee"],
        assertions=[
            {
                "subject": "student",
                "predicate": "monthly_fee",
                "value": "before",
                "valid_from": "2026-01-01T00:00:00Z",
                "source": "human_stated",
            }
        ],
    )
    conn.commit()
    return conn, assertion_ids[0]


# TRUNCATE fires a statement trigger, the other two fire row triggers. All
# three land in the same kernel_deny().
@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE assertion SET value_literal = 'after' WHERE id = %s",
        "DELETE FROM assertion WHERE id = %s",
        "TRUNCATE assertion",
    ],
    ids=["update", "delete", "truncate"],
)
def test_mutating_assertion_raises(written, sql):
    conn, assertion_id = written
    params = () if sql.startswith("TRUNCATE") else (assertion_id,)
    with pytest.raises(psycopg.errors.RaiseException) as caught:
        # A savepoint, so the failure does not poison the module's connection.
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(sql, params)
    assert "kernel is append-only" in str(caught.value)


def test_the_row_still_reads_before(written):
    """Three refused mutations later, the value is the one that was written."""
    conn, assertion_id = written
    with conn.cursor() as cur:
        cur.execute(
            "SELECT value_literal FROM assertion WHERE id = %s", (assertion_id,)
        )
        (value,) = cur.fetchone()
    assert value == "before"

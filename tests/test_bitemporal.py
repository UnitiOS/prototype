"""The PoC's definition of done: one fact, corrected late, read at four
combinations of valid time and record time, gives four correct and distinct
answers.

The fixture is one entity, one predicate, three assertions on a monthly fee:

    recorded 10 Jan, valid_from 1 Jan, 5000000
    recorded  5 Feb, valid_from 1 Jan, 5500000   a correction — we were wrong
    recorded  1 Mar, valid_from 1 Mar, 6000000   a change — the world moved

Run: .venv/Scripts/python.exe -m pytest tests/test_bitemporal.py
"""

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kernel"))

from perform import connect, perform  # noqa: E402
from resolve import resolve_single  # noqa: E402

# recorded_at is a column default and perform() does not take it, so the
# fixture inserts its three rows with direct SQL.
_FIXTURE_SQL = """
INSERT INTO assertion (
    id, subject_id, predicate_id, value_literal, valid_from, recorded_at,
    intent_id, source, ontology_version)
VALUES (%s, %s, %s, %s, %s, %s, %s, 'human_stated', 'v0')
"""

_ROWS = [
    ("2026-01-01T00:00:00Z", "2026-01-10T00:00:00Z", "5000000"),
    ("2026-01-01T00:00:00Z", "2026-02-05T00:00:00Z", "5500000"),
    ("2026-03-01T00:00:00Z", "2026-03-01T00:00:00Z", "6000000"),
]


@pytest.fixture(scope="module")
def fact():
    """Mint the subject and predicate, then write the three assertions."""
    with connect() as conn:
        intent_id, names, _ = perform(
            conn,
            actor_id="test",
            action_name="seed_bitemporal_fixture",
            mint=["student", "monthly_fee"],
        )
        with conn.cursor() as cur:
            for valid_from, recorded_at, value in _ROWS:
                cur.execute(
                    _FIXTURE_SQL,
                    (uuid.uuid4(), names["student"], names["monthly_fee"],
                     value, valid_from, recorded_at, intent_id),
                )
        conn.commit()
        yield conn, names["student"], names["monthly_fee"]


# The last row is the one a naive implementation gets wrong: read today,
# about mid-January, it must not return the March change.
@pytest.mark.parametrize(
    "valid_at, as_of, expected",
    [
        ("2026-01-15T00:00:00Z", "2026-03-20T00:00:00Z", "5500000"),
        ("2026-01-15T00:00:00Z", "2026-01-20T00:00:00Z", "5000000"),
        ("2026-01-15T00:00:00Z", "2026-02-10T00:00:00Z", "5500000"),
        ("2026-03-15T00:00:00Z", "2026-03-20T00:00:00Z", "6000000"),
    ],
)
def test_four_reads(fact, valid_at, as_of, expected):
    conn, subject_id, predicate_id = fact
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at=valid_at,
        as_of=as_of,
    )
    assert row is not None
    assert row["value_literal"] == expected


def test_nothing_stood_before_the_first_record(fact):
    """Read as of 5 Jan: the fee had been agreed but nobody had written it."""
    conn, subject_id, predicate_id = fact
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-01-05T00:00:00Z",
    )
    assert row is None

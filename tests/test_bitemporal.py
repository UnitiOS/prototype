"""The PoC's definition of done: one fact, corrected late, read at four
combinations of valid time and record time, gives four correct and distinct
answers.

Three fixtures, all on a monthly fee. The base is:

    recorded 10 Jan, valid_from 1 Jan, 5000000
    recorded  5 Feb, valid_from 1 Jan, 5500000   a correction — we were wrong
    recorded  1 Mar, valid_from 1 Mar, 6000000   a change — the world moved

`fact` adds a retro-dated row (valid_from 1 Dec 2025, recorded 10 Mar) so the
log's latest-recorded row is also its earliest-valid row.

`retracted` adds a pure retraction instead: recorded 10 Mar, revoking the 5 Feb
correction and stating no value at all.

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
# fixtures insert their rows with direct SQL.
_INSERT_SQL = """
INSERT INTO assertion (
    id, subject_id, predicate_id, value_literal, valid_from, recorded_at,
    revokes, intent_id, source, ontology_version)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'human_stated', 'v0')
"""

# (valid_from, recorded_at, value, revokes) — `revokes` is the index of an
# earlier row in the same list, or None.
_BASE = [
    ("2026-01-01T00:00:00Z", "2026-01-10T00:00:00Z", "5000000", None),
    ("2026-01-01T00:00:00Z", "2026-02-05T00:00:00Z", "5500000", None),
    ("2026-03-01T00:00:00Z", "2026-03-01T00:00:00Z", "6000000", None),
]

_RETRO = ("2025-12-01T00:00:00Z", "2026-03-10T00:00:00Z", "4000000", None)
_RETRACTION = ("2026-01-01T00:00:00Z", "2026-03-10T00:00:00Z", None, 1)


def _seed(conn, rows):
    """Mint a fresh subject and predicate, then write `rows` in order.

    Every run mints new uuids, so rows appended by earlier runs are invisible
    to the queries below. Append-only makes test isolation free.
    """
    intent_id, names, _ = perform(
        conn,
        actor_id="test",
        action_name="seed_bitemporal_fixture",
        mint=["student", "monthly_fee"],
    )
    ids = []
    with conn.cursor() as cur:
        for valid_from, recorded_at, value, revokes in rows:
            assertion_id = uuid.uuid4()
            cur.execute(
                _INSERT_SQL,
                (assertion_id, names["student"], names["monthly_fee"], value,
                 valid_from, recorded_at,
                 None if revokes is None else ids[revokes], intent_id),
            )
            ids.append(assertion_id)
    conn.commit()
    return names["student"], names["monthly_fee"]


@pytest.fixture(scope="module")
def conn():
    with connect() as c:
        yield c


@pytest.fixture(scope="module")
def fact(conn):
    """The three rows plus the retro-dated one."""
    return (conn,) + _seed(conn, _BASE + [_RETRO])


@pytest.fixture(scope="module")
def retracted(conn):
    """The three rows plus a pure retraction of the 5 Feb correction."""
    return (conn,) + _seed(conn, _BASE + [_RETRACTION])


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


# --- the retro-dated row ------------------------------------------------

def test_retro_dated_row_does_not_win_on_record_order(fact):
    """The latest-recorded row is the earliest-valid row, and loses.

    An implementation that ordered by recorded_at would answer 4000000 here;
    the winner is max valid_from, not max recorded_at.
    """
    conn, subject_id, predicate_id = fact
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-03-20T00:00:00Z",
    )
    assert row["value_literal"] == "5500000"


# The variant this fixture exists to kill: same candidate set, ordered by
# recorded_at instead of valid_from.
_BY_RECORDED_AT_SQL = """
SELECT a.value_literal
FROM assertion a
WHERE a.subject_id   = %(subject_id)s
  AND a.predicate_id = %(predicate_id)s
  AND a.valid_from  <= %(valid_at)s
  AND a.recorded_at <= %(as_of)s
ORDER BY a.recorded_at DESC, a.seq DESC
LIMIT 1
"""


def test_record_ordered_variant_gets_it_wrong(fact):
    conn, subject_id, predicate_id = fact
    with conn.cursor() as cur:
        cur.execute(
            _BY_RECORDED_AT_SQL,
            {"subject_id": subject_id, "predicate_id": predicate_id,
             "valid_at": "2026-01-15T00:00:00Z",
             "as_of": "2026-03-20T00:00:00Z"},
        )
        (wrong,) = cur.fetchone()
    assert wrong == "4000000"


# --- the pure retraction ------------------------------------------------

# BLOCKED, not a fixture problem. The 2026-08-22 resolve rule picks the winner
# from all unrevoked candidates, and a pure retraction is itself a candidate:
# valid_from 1 Jan, highest seq, so it wins and answers with no value at all.
# Dating it 10 Mar instead only moves the hole — every read at valid_at >= 10 Mar
# then answers nothing. The rule predates the relaxed constraint and never says
# a candidate must carry a value. resolve_single() is not being changed here.
@pytest.mark.xfail(
    strict=True,
    reason="pure retraction wins as a candidate; resolve rule has no "
           "value-carrying filter (open decision, not code)",
)
def test_retraction_resurfaces_the_earlier_row(retracted):
    """Read after the retraction: the correction is gone, seq 1 stands again."""
    conn, subject_id, predicate_id = retracted
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-03-20T00:00:00Z",
    )
    assert row is not None
    assert row["value_literal"] == "5000000"


def test_retraction_had_not_happened_yet(retracted):
    """Read before the retraction was written: the correction still stands."""
    conn, subject_id, predicate_id = retracted
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-03-01T00:00:00Z",
    )
    assert row is not None
    assert row["value_literal"] == "5500000"

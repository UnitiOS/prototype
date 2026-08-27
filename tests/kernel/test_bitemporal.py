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

`backfilled` adds an import instead: the same valid_from as the 5 Feb
correction, but recorded 20 Jan — knowledge older than the correction's,
inserted later, so its seq is higher.

Run: .venv/Scripts/python.exe -m pytest tests/test_bitemporal.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "components" / "kernel"))

from perform import connect, perform  # noqa: E402
from resolve import resolve_single  # noqa: E402

# (valid_from, recorded_at, value, revokes) — `revokes` is the index of an
# earlier row in the same list, or None.
_BASE = [
    ("2026-01-01T00:00:00Z", "2026-01-10T00:00:00Z", "5000000", None),
    ("2026-01-01T00:00:00Z", "2026-02-05T00:00:00Z", "5500000", None),
    ("2026-03-01T00:00:00Z", "2026-03-01T00:00:00Z", "6000000", None),
]

_RETRO = ("2025-12-01T00:00:00Z", "2026-03-10T00:00:00Z", "4000000", None)
_RETRACTION = ("2026-01-01T00:00:00Z", "2026-03-10T00:00:00Z", None, 1)
# A backfilled import: last in, so highest seq, but it knew less than the
# 5 Feb correction did. It ties on valid_from and must lose on recorded_at.
_BACKFILL = ("2026-01-01T00:00:00Z", "2026-01-20T00:00:00Z", "5100000", None)
# A row that revokes and replaces in one move: it takes the 5 Feb correction
# out and states 5700000 in its place. `revokes IS NULL` would throw it away.
_REPLACEMENT = ("2026-01-01T00:00:00Z", "2026-03-10T00:00:00Z", "5700000", 1)
# Two rows that agree on both clocks — same valid_from, same recorded_at,
# recorded in two acts that claim the same instant. Only insertion order
# separates them.
_SIMULTANEOUS = ("2026-01-01T00:00:00Z", "2026-02-05T00:00:00Z", "5600000", None)
# Neighbours in the log. Each ties the 5 Feb correction on valid_from and beats
# it on recorded_at, so it wins a read of student/monthly_fee the moment its
# own filter is dropped.
_OTHER_SUBJECT = ("sibling", "monthly_fee", "2026-01-01T00:00:00Z",
                  "2026-02-20T00:00:00Z", "9900000", None)
_OTHER_PREDICATE = ("student", "enrolment_date", "2026-01-01T00:00:00Z",
                    "2026-02-25T00:00:00Z", "9800000", None)


def _seed(conn, rows, mint=("student", "monthly_fee")):
    """Mint fresh entities, then write `rows` in order, and return the labels.

    A row is `(valid_from, recorded_at, value, revokes)` against
    `mint[0]`/`mint[1]`, or `(subject, predicate, valid_from, recorded_at,
    value, revokes)` to name a different pair out of `mint`.

    One row is one act of recording, so one row is one `perform()` call with
    its own `recorded_at`. Nothing here writes SQL: the fixtures go through the
    same write gate as the application does.

    Every run mints new uuids, so rows appended by earlier runs are invisible
    to the queries below. Append-only makes test isolation free.
    """
    _, names, _ = perform(
        conn,
        actor_id="test",
        action_name="mint_bitemporal_fixture",
        ontology_version="v0",
        mint=list(mint),
    )
    ids = []
    for row in rows:
        if len(row) == 4:
            subject, predicate = mint[0], mint[1]
            valid_from, recorded_at, value, revokes = row
        else:
            subject, predicate, valid_from, recorded_at, value, revokes = row
        _, _, assertion_ids = perform(
            conn,
            actor_id="test",
            action_name="seed_bitemporal_fixture",
            ontology_version="v0",
            occurred_at=recorded_at,
            recorded_at=recorded_at,
            assertions=[{
                "subject": names[subject],
                "predicate": names[predicate],
                "value": value,
                "valid_from": valid_from,
                "revokes": None if revokes is None else ids[revokes],
                "source": "human_stated",
            }],
        )
        ids.append(assertion_ids[0])
    return names


@pytest.fixture(scope="module")
def conn():
    with connect() as c:
        yield c


@pytest.fixture(scope="module")
def fact(conn):
    """The three rows plus the retro-dated one."""
    names = _seed(conn, _BASE + [_RETRO])
    return conn, names["student"], names["monthly_fee"]


@pytest.fixture(scope="module")
def retracted(conn):
    """The three rows plus a pure retraction of the 5 Feb correction."""
    names = _seed(conn, _BASE + [_RETRACTION])
    return conn, names["student"], names["monthly_fee"]


@pytest.fixture(scope="module")
def backfilled(conn):
    """The three rows plus a late-inserted, early-recorded import."""
    names = _seed(conn, _BASE + [_BACKFILL])
    return conn, names["student"], names["monthly_fee"]


@pytest.fixture(scope="module")
def replaced(conn):
    """The three rows plus a row that revokes the 5 Feb correction and
    states a replacement value in the same breath."""
    names = _seed(conn, _BASE + [_REPLACEMENT])
    return conn, names["student"], names["monthly_fee"]


@pytest.fixture(scope="module")
def simultaneous(conn):
    """The three rows plus one that ties the 5 Feb correction on both clocks."""
    names = _seed(conn, _BASE + [_SIMULTANEOUS])
    return conn, names["student"], names["monthly_fee"]


@pytest.fixture(scope="module")
def crowded_subject(conn):
    """The three rows plus another student's fee, under the same predicate."""
    names = _seed(conn, _BASE + [_OTHER_SUBJECT],
                  mint=("student", "monthly_fee", "sibling"))
    return conn, names["student"], names["monthly_fee"]


@pytest.fixture(scope="module")
def crowded_predicate(conn):
    """The three rows plus another predicate about the same student."""
    names = _seed(conn, _BASE + [_OTHER_PREDICATE],
                  mint=("student", "monthly_fee", "enrolment_date"))
    return conn, names["student"], names["monthly_fee"]


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

# The pure retraction is a candidate on every axis except the one that counts:
# it states nothing about the world. num_nonnulls(value_literal, value_ref) = 1
# takes it out of the running, so it removes the 5 Feb correction without
# putting itself in its place.
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


# --- the backfilled import ----------------------------------------------

def test_backfill_does_not_win_the_tie_on_seq(backfilled):
    """Two rows tie on valid_from. The one that knew more wins.

    seq is insertion order, not knowledge order. The import went in last, so
    it holds the highest seq, but it was recorded 20 Jan and the correction it
    ties with was recorded 5 Feb. An implementation that broke the tie on seq
    would answer 5100000.
    """
    conn, subject_id, predicate_id = backfilled
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-03-20T00:00:00Z",
    )
    assert row["value_literal"] == "5500000"


# The variant this fixture exists to kill: same candidate set, same first
# ordering key, tie broken on seq instead of recorded_at.
_BY_SEQ_SQL = """
SELECT a.value_literal
FROM assertion a
WHERE a.subject_id   = %(subject_id)s
  AND a.predicate_id = %(predicate_id)s
  AND a.valid_from  <= %(valid_at)s
  AND a.recorded_at <= %(as_of)s
  AND num_nonnulls(a.value_literal, a.value_ref) = 1
ORDER BY a.valid_from DESC, a.seq DESC
LIMIT 1
"""


def test_seq_ordered_variant_gets_it_wrong(backfilled):
    conn, subject_id, predicate_id = backfilled
    with conn.cursor() as cur:
        cur.execute(
            _BY_SEQ_SQL,
            {"subject_id": subject_id, "predicate_id": predicate_id,
             "valid_at": "2026-01-15T00:00:00Z",
             "as_of": "2026-03-20T00:00:00Z"},
        )
        (wrong,) = cur.fetchone()
    assert wrong == "5100000"


# --- revoke and replace in one row --------------------------------------

def test_a_revoking_row_that_carries_a_value_still_wins(replaced):
    """"We were wrong, and here is the right number" is one row, not two.

    It revokes the 5 Feb correction *and* states 5700000. The candidate clause
    asks whether a row states something about the world, not whether it also
    withdraws something — so this row stays in the running and wins.
    """
    conn, subject_id, predicate_id = replaced
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-03-20T00:00:00Z",
    )
    assert row is not None
    assert row["value_literal"] == "5700000"


# The variant this fixture exists to kill: the candidate clause written as
# `revokes IS NULL` instead of `num_nonnulls(...) = 1`. It excludes the
# replacement along with the pure retraction, and falls back two steps.
_BY_REVOKES_IS_NULL_SQL = """
SELECT a.value_literal
FROM assertion a
WHERE a.subject_id   = %(subject_id)s
  AND a.predicate_id = %(predicate_id)s
  AND a.valid_from  <= %(valid_at)s
  AND a.recorded_at <= %(as_of)s
  AND a.revokes IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM assertion r
      WHERE r.revokes = a.id
        AND r.recorded_at <= %(as_of)s
  )
ORDER BY a.valid_from DESC, a.recorded_at DESC, a.seq DESC
LIMIT 1
"""


def test_revokes_is_null_variant_gets_it_wrong(replaced):
    conn, subject_id, predicate_id = replaced
    with conn.cursor() as cur:
        cur.execute(
            _BY_REVOKES_IS_NULL_SQL,
            {"subject_id": subject_id, "predicate_id": predicate_id,
             "valid_at": "2026-01-15T00:00:00Z",
             "as_of": "2026-03-20T00:00:00Z"},
        )
        (wrong,) = cur.fetchone()
    assert wrong == "5000000"


# --- both clocks tied ---------------------------------------------------

def test_insertion_order_breaks_a_tie_on_both_clocks(simultaneous):
    """Same valid_from, same recorded_at: seq is the only thing left.

    Two rows can be recorded at the same instant. Neither clock separates
    them, so the last one written stands. Without `seq DESC` the query has no
    total order and the answer is whichever row the plan happens to reach
    first.
    """
    conn, subject_id, predicate_id = simultaneous
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-03-20T00:00:00Z",
    )
    assert row["value_literal"] == "5600000"


# --- the neighbours -----------------------------------------------------

def test_another_subject_under_the_same_predicate_is_invisible(crowded_subject):
    """A sibling's fee is a fact about the sibling, not about this student."""
    conn, subject_id, predicate_id = crowded_subject
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-03-20T00:00:00Z",
    )
    assert row["value_literal"] == "5500000"


def test_another_predicate_about_the_same_subject_is_invisible(crowded_predicate):
    """resolve_single answers one slot. The student's other slots are not it."""
    conn, subject_id, predicate_id = crowded_predicate
    row = resolve_single(
        conn,
        subject_id=subject_id,
        predicate_id=predicate_id,
        valid_at="2026-01-15T00:00:00Z",
        as_of="2026-03-20T00:00:00Z",
    )
    assert row["value_literal"] == "5500000"

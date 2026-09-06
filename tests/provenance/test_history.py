"""What `provenance` must return, and what it must not do.

The component is the one reader of the kernel outside the compiler, and the
whole of its contract is that it hides nothing. Four rows go in under one
(subject, predicate) pair:

    valid_from 1 Jan, recorded 10 Jan, 5000000
    valid_from 1 Jan, recorded  5 Feb, 5500000    a correction
    valid_from 1 Mar, recorded  1 Mar, 6000000    a change — the world moved
    valid_from 1 Jan, recorded 10 Mar, no value   a pure retraction of the
                                                  correction

and all four come back, oldest first, with the retraction carrying no value and
the row it took out saying which row took it. `resolve_single` answers a
different question — which one *stands* — and nothing here resolves anything.

A pair is asked for by URI, because a URI is what a page has. One the log has
never registered is refused rather than answered empty: "nothing was said about
this" and "this is not a thing" are different answers.

Run: .venv/Scripts/python.exe -m pytest tests/provenance -q
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "provenance"))

from perform import connect, perform  # noqa: E402
from provenance import URI_PREDICATE, UnknownURI  # noqa: E402
from provenance import _registry as registry  # noqa: E402
from provenance import history, window  # noqa: E402

SUBJECT = "test:provenance_subject"
PREDICATE = "test:provenance_predicate"

# (valid_from, recorded_at, value, revokes) — `revokes` is the index of an
# earlier row of this list, or None.
ROWS = [
    ("2026-01-01T00:00:00Z", "2026-01-10T00:00:00Z", "5000000", None),
    ("2026-01-01T00:00:00Z", "2026-02-05T00:00:00Z", "5500000", None),
    ("2026-03-01T00:00:00Z", "2026-03-01T00:00:00Z", "6000000", None),
    ("2026-01-01T00:00:00Z", "2026-03-10T00:00:00Z", None, 1),
]


@pytest.fixture(scope="module")
def conn():
    with connect() as c:
        yield c


@pytest.fixture(scope="module")
def pair(conn):
    """Two URIs registered the way `seal` registers one, and four rows.

    Fresh URIs on every run, so rows written by an earlier run are under a
    different pair and invisible here. Append-only makes isolation free.
    """
    import uuid

    subject = f"{SUBJECT}_{uuid.uuid4().hex[:8]}"
    predicate = f"{PREDICATE}_{uuid.uuid4().hex[:8]}"

    # `uniti:uri` is registered once per log, by whoever wrote to it first.
    # Registering a second one would mint a second identity for the predicate
    # the whole registry is keyed on, and every URI written under it would be
    # invisible to a reader that found the first.
    held, _ = registry(conn)
    fresh = [subject, predicate]
    if URI_PREDICATE not in held:
        fresh.insert(0, URI_PREDICATE)

    _, names, _ = perform(
        conn,
        actor_id="test",
        action_name="mint_provenance_fixture",
        ontology_version="v0",
        mint=fresh,
        assertions=[
            {"subject": uri, "predicate": held.get(URI_PREDICATE, URI_PREDICATE),
             "value": uri, "valid_from": "2026-01-01T00:00:00Z",
             "source": "system_derived"}
            for uri in fresh
        ],
    )

    written = []
    for valid_from, recorded_at, value, revokes in ROWS:
        _, _, ids = perform(
            conn,
            actor_id="marina",
            action_name="state_the_fee",
            ontology_version="v0",
            occurred_at=recorded_at,
            recorded_at=recorded_at,
            assertions=[{
                "subject": names[subject],
                "predicate": names[predicate],
                "value": value,
                "valid_from": valid_from,
                "revokes": None if revokes is None else written[revokes],
                "source": "human_stated",
                "authority": "the fee letter",
                "confidence": "high",
            }],
        )
        written.append(ids[0])
    return conn, subject, predicate, written


def test_every_row_comes_back_oldest_first(pair):
    conn, subject, predicate, _ = pair
    rows = history(conn, subject=subject, predicate=predicate)["rows"]
    assert len(rows) == len(ROWS)
    assert [row["value"] for row in rows] == ["5000000", "5500000", None,
                                              "6000000"]
    clocks = [(row["valid_from"], row["recorded_at"]) for row in rows]
    assert clocks == sorted(clocks)


def test_a_retraction_carries_no_value_and_names_what_it_took_out(pair):
    conn, subject, predicate, written = pair
    rows = {row["id"]: row for row
            in history(conn, subject=subject, predicate=predicate)["rows"]}
    retraction = rows[written[3]]
    assert retraction["value"] is None
    assert retraction["revokes"] == written[1]
    # And the row it took out is still here, saying so.
    assert rows[written[1]]["revoked_by"] == written[3]
    assert rows[written[0]]["revoked_by"] is None


def test_provenance_comes_back_with_every_row(pair):
    conn, subject, predicate, _ = pair
    for row in history(conn, subject=subject, predicate=predicate)["rows"]:
        assert row["source"] == "human_stated"
        assert row["authority"] == "the fee letter"
        assert row["confidence"] == "high"
        assert row["actor_id"] == "marina"
        assert row["action_name"] == "state_the_fee"
        assert row["intent_id"] is not None


def test_a_uri_the_log_never_registered_is_refused(pair):
    conn, subject, _, _ = pair
    with pytest.raises(UnknownURI):
        history(conn, subject=subject, predicate="test:never_registered")
    with pytest.raises(UnknownURI):
        history(conn, subject="test:never_registered", predicate=subject)


def test_the_window_spans_what_was_written(pair):
    conn, _, _, _ = pair
    held = window(conn)
    assert held["assertions"] >= len(ROWS)
    assert held["intents"] >= len(ROWS)
    earliest = datetime(2026, 1, 1, tzinfo=timezone.utc)
    latest = datetime(2026, 3, 1, tzinfo=timezone.utc)
    assert held["first_valid_from"] <= earliest
    assert held["last_valid_from"] >= latest
    assert held["first_recorded_at"] <= held["last_recorded_at"]

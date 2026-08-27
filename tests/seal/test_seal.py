"""Sealing a draft: one file, one intent, and one entity per URI.

Two fixture drafts describe the same ice cream shop twice. `draft_two` renames
`freezer_location` to `freezer_place` while keeping its `slot_uri`, and adds
`batch_litres` — so the second seal shares four predicates with the first,
one of them under a new name, and brings one of its own.

The seals land in a temporary directory rather than in `business/`: a test that
wrote there would leave a v3 behind every time `make check` ran. What
`business/` itself holds is checked separately, by reading it.

Run: .venv/Scripts/python.exe -m pytest tests/seal -q
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components"))

from ontology.resolve import load_versions, resolve_version  # noqa: E402
from seal import URI_PREDICATE, DraftError, main, seal  # noqa: E402
from seal import connect  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BUSINESS = ROOT / "business"

SEALED_ONE = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
SEALED_TWO = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)
BACKDATED = "2026-01-15T09:00:00Z"


@pytest.fixture(scope="module")
def conn():
    with connect() as c:
        yield c


@pytest.fixture(scope="module")
def sealed(conn, tmp_path_factory):
    """Both drafts sealed into one empty directory, in order."""
    into = tmp_path_factory.mktemp("business")
    first = seal(conn, FIXTURES / "draft_one.yaml", actor_id="test",
                 into=into, sealed_at=SEALED_ONE)
    second = seal(conn, FIXTURES / "draft_two.yaml", actor_id="test",
                  into=into, sealed_at=SEALED_TWO)
    return into, first, second


def _rows(conn, intent_id):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT subject_id, predicate_id, value_literal, valid_from,
                   recorded_at, source, ontology_version
            FROM assertion WHERE intent_id = %s ORDER BY seq
            """,
            (intent_id,),
        )
        return cur.fetchall()


def _entities_named(conn, uri):
    """Every entity the log has ever registered under this URI."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT subject_id FROM assertion
            WHERE predicate_id = (
                    SELECT subject_id FROM assertion
                    WHERE subject_id = predicate_id AND value_literal = %s
                    ORDER BY seq LIMIT 1)
              AND value_literal = %s
            """,
            (URI_PREDICATE, uri),
        )
        return [row[0] for row in cur.fetchall()]


def test_sealing_a_draft_twice_leaves_v1_and_v2(sealed):
    into, first, second = sealed
    assert sorted(p.name for p in into.glob("*.yaml")) == ["v1.yaml", "v2.yaml"]
    assert (first["version"], second["version"]) == ("v1", "v2")
    assert second["supersedes"] == "v1"
    # And the ontology component reads back what seal wrote.
    winner = resolve_version(into, valid_at="2026-06-01T00:00:00Z",
                             as_of="2026-06-01T00:00:00Z")
    assert winner["version"] == "v2"


def test_every_assertion_from_one_seal_shares_the_sealed_at(conn, sealed):
    _, first, second = sealed
    for result in (first, second):
        recorded = {row[4] for row in _rows(conn, result["intent_id"])}
        assert recorded == {result["sealed_at"]}
        assert result["sealed_at"] == _stamped(result["path"], "sealed_at")


def test_a_slot_uri_in_both_versions_yields_one_predicate_entity(conn, sealed):
    _, first, second = sealed
    # Shared outright, and shared under a new name: draft_two calls
    # uniti:freezer_location `freezer_place`.
    for uri in ("uniti:freezer_label", "uniti:freezer_location"):
        assert first["entities"][uri] == second["entities"][uri]
        assert len(_entities_named(conn, uri)) == 1
        # The second seal reused them rather than minting twins. The registry
        # is global, so what a seal mints depends on what the log already
        # holds; what it must never do is mint a URI a second time.
        assert uri not in second["minted"]
    assert len(_entities_named(conn, "uniti:batch_litres")) == 1
    # The registry predicate registers itself: one row, subject == predicate.
    assert len(_entities_named(conn, URI_PREDICATE)) == 1


def test_facts_carry_the_versions_valid_from_not_the_seal_instant(conn, sealed):
    _, first, second = sealed
    for result, expected in ((first, "2026-01-01"), (second, "2026-02-01")):
        rows = _rows(conn, result["intent_id"])
        valid = {row[3] for row in rows}
        assert valid == {result["valid_from"]}
        assert result["valid_from"].date().isoformat() == expected
        assert result["valid_from"] < result["sealed_at"]
        assert {row[6] for row in rows} == {result["version"]}


def test_the_stated_facts_reach_the_log_and_leave_the_map(conn, sealed):
    into, first, _ = sealed
    stated = [row for row in _rows(conn, first["intent_id"]) if row[5] == "human_stated"]
    assert [row[2] for row in stated] == ["Freezer A", "Front of shop", "Freezer B"]
    assert stated[0][0] == first["entities"]["uniti:freezer_a"]
    assert stated[0][1] == first["entities"]["uniti:freezer_label"]
    assert "facts" not in (into / "v1.yaml").read_text(encoding="utf-8")


def test_an_invalid_draft_leaves_the_database_and_the_directory_untouched(conn, tmp_path):
    before = _counts(conn)
    with pytest.raises(DraftError):
        seal(conn, FIXTURES / "invalid.yaml", actor_id="test", into=tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert _counts(conn) == before


def test_a_slot_without_a_slot_uri_is_refused(conn, tmp_path):
    with pytest.raises(DraftError, match="freezer_location"):
        seal(conn, FIXTURES / "no_slot_uri.yaml", actor_id="test", into=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_draft_without_a_valid_from_is_refused(conn, tmp_path):
    before = _counts(conn)
    with pytest.raises(DraftError, match="valid_from"):
        seal(conn, FIXTURES / "no_valid_from.yaml", actor_id="test", into=tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert _counts(conn) == before


def test_the_transcript_lands_beside_its_version(sealed):
    into, first, second = sealed
    for result, draft in ((first, "draft_one.txt"), (second, "draft_two.txt")):
        landed = into / f"{result['version']}.txt"
        assert result["transcript"] == landed
        assert landed.read_text(encoding="utf-8") == (
            FIXTURES / draft).read_text(encoding="utf-8")
        # The sealed annotation names the copy, not the draft it came from.
        assert _annotations(result["path"])["transcript"] == landed.name
        # And the draft's own transcript is still where the interview left it.
        assert (FIXTURES / draft).is_file()


def test_a_draft_with_no_transcript_is_refused(conn, tmp_path):
    before = _counts(conn)
    with pytest.raises(DraftError, match="transcript"):
        seal(conn, FIXTURES / "no_transcript.yaml", actor_id="test", into=tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert _counts(conn) == before


def test_a_transcript_that_is_not_there_is_refused(conn, tmp_path):
    before = _counts(conn)
    with pytest.raises(DraftError, match="never_written.txt"):
        seal(conn, FIXTURES / "missing_transcript.yaml", actor_id="test", into=tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert _counts(conn) == before


def test_a_mapping_nested_under_annotations_is_refused(conn, tmp_path):
    """The leak this guards: the version resolver's scanner tracks no depth."""
    before = _counts(conn)
    with pytest.raises(DraftError, match="session"):
        seal(conn, FIXTURES / "nested_annotation.yaml", actor_id="test", into=tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert _counts(conn) == before


def test_the_cli_seals_at_the_instant_it_is_given(conn, tmp_path):
    """A dated episode: `--sealed-at` reaches both stores or neither."""
    before = _max_seq(conn)
    code = main([str(FIXTURES / "draft_one.yaml"), "--actor", "test",
                 "--into", str(tmp_path), "--sealed-at", BACKDATED])
    assert code == 0

    instant = datetime.fromisoformat(BACKDATED)
    version = load_versions(tmp_path)[0]
    assert version["sealed_at"] == instant
    assert version["valid_from"] < instant

    with conn.cursor() as cur:
        cur.execute(
            "SELECT recorded_at, source, intent_id FROM assertion "
            "WHERE seq > %s ORDER BY seq",
            (before,),
        )
        rows = cur.fetchall()
    # How many URIs this seal had to mint depends on what the log already
    # holds, but the three stated facts are its own, and one seal is one intent.
    assert len([row for row in rows if row[1] == "human_stated"]) == 3
    assert len({row[2] for row in rows}) == 1
    assert {row[0] for row in rows} == {instant}


def test_business_holds_the_two_sealed_versions():
    """The repo's own map store, read the way every reader will read it."""
    assert resolve_version(BUSINESS, valid_at="2026-06-01T00:00:00Z",
                           as_of="2026-01-15T00:00:00Z") is None
    winner = resolve_version(BUSINESS, valid_at="2026-06-01T00:00:00Z",
                             as_of="2026-12-31T00:00:00Z")
    assert winner["version"] == "v2"
    assert winner["supersedes"] == "v1"


def _counts(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT (SELECT count(*) FROM intent), (SELECT count(*) FROM entity),"
            "       (SELECT count(*) FROM assertion)"
        )
        return cur.fetchone()


def _max_seq(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT coalesce(max(seq), 0) FROM assertion")
        return cur.fetchone()[0]


def _annotations(path):
    """The sealed file's own annotations block."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))["annotations"]


def _stamped(path, key):
    """One metadata scalar, read out of the sealed file itself."""
    return datetime.fromisoformat(_annotations(path)[key])

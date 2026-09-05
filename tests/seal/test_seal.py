"""Sealing a draft: one file, one intent, and one entity per URI.

Two fixture drafts describe the same ice cream shop twice. `draft_two` renames
`freezer_location` to `freezer_place` while keeping its `slot_uri`, and adds
`batch_litres` — so the second seal shares four predicates with the first,
one of them under a new name, and brings one of its own.

A third, `draft_ranges`, is about one rule and nothing else: which column a
value lands in. It declares a class-ranged slot beside a type-ranged one and an
unranged one, and names one freezer only on the value side.

A fourth, `draft_confidence`, is about the optional fourth fact key: one fact
weighed, one estimated, one silent — and the silent one has to reach the log as
NULL rather than as a level nobody stated.

The seals land in a temporary directory rather than in `business/`: a test that
wrote there would leave a v3 behind every time `make check` ran, and a test that
merely read there would make the production map store a fixture. Nothing here
touches `business/` — what the two seals prove is that `resolve` can read what
`seal` wrote, and two files in a temp directory prove that better.

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
from seal import URI_PREDICATE, DraftError, main, register, seal  # noqa: E402
from seal import connect  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The two seals differ on both axes: v1 is valid from 1 Jan and sealed 1 Mar,
# v2 valid from 1 Feb and sealed 1 Apr. So each axis can hide v2 on its own.
SEALED_ONE = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
SEALED_TWO = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)
SEALED_RANGES = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
SEALED_CONFIDENCE = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
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


@pytest.fixture(scope="module")
def ranged(conn, tmp_path_factory):
    """The class-range draft, sealed into a directory of its own."""
    into = tmp_path_factory.mktemp("ranges")
    return seal(conn, FIXTURES / "draft_ranges.yaml", actor_id="test",
                into=into, sealed_at=SEALED_RANGES)


@pytest.fixture(scope="module")
def confident(conn, tmp_path_factory):
    """The confidence draft, sealed into a directory of its own."""
    into = tmp_path_factory.mktemp("confidence")
    return seal(conn, FIXTURES / "draft_confidence.yaml", actor_id="test",
                into=into, sealed_at=SEALED_CONFIDENCE)


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


def test_resolve_reads_back_what_seal_wrote(sealed):
    """The seal-to-resolve join, across both axes and no store but this one."""
    into, first, second = sealed
    late = "2026-06-01T00:00:00Z"

    def winner(valid_at, as_of):
        return resolve_version(into, valid_at=valid_at, as_of=as_of)

    # Before the first seal there is no map at all, which is not an error.
    assert winner(late, "2026-02-01T00:00:00Z") is None
    # Record time hides v2: it was sealed a month after this as_of.
    assert winner(late, "2026-03-15T00:00:00Z")["version"] == first["version"]
    # Valid time hides v2: it does not take effect until 1 Feb.
    assert winner("2026-01-15T00:00:00Z", late)["version"] == first["version"]
    # Past both seals on both axes: the later one wins, and names what it
    # replaced — read out of the file, not out of what seal() returned.
    latest = winner(late, late)
    assert latest["version"] == second["version"]
    assert latest["supersedes"] == first["version"]


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


def _stated(conn, intent_id):
    """The facts of one seal, as (predicate_uri, literal, ref), in order."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.value_literal, a.value_literal, a.value_ref
            FROM assertion a
            JOIN assertion p ON p.subject_id = a.predicate_id
                            AND p.subject_id <> p.predicate_id
                            AND p.value_literal IS NOT NULL
            WHERE a.intent_id = %s AND a.source = %s
            ORDER BY a.seq
            """,
            (intent_id, "human_stated"),
        )
        return cur.fetchall()


def test_a_class_ranged_fact_lands_as_a_ref_and_a_type_range_as_a_literal(conn, ranged):
    """The one rule: the map's range decides the column, not the value's shape.

    `uniti:stored_in` names a class, so its values are entity ids even though
    they were written in the draft as the same kind of string as any other.
    """
    stated = _stated(conn, ranged["intent_id"])
    literals = {p: lit for p, lit, ref in stated if ref is None}
    refs = [(p, ref) for p, lit, ref in stated if ref is not None]

    # A type range and no range at all: both literal, and no ref beside them.
    assert literals == {
        "uniti:freezer_label": "Freezer D",
        "uniti:batch_flavour": "Stracciatella",
        "uniti:batch_litres": "18.5",
    }
    # The class range: three refs, and every one of them with a null literal.
    assert [p for p, ref in refs] == ["uniti:stored_in"] * 3
    assert all(lit is None for p, lit, ref in stated if ref is not None)


def test_two_facts_naming_one_uri_reach_one_entity(conn, ranged):
    """One entity, whether the URI arrives as a subject or as a value."""
    freezer_d = ranged["entities"]["uniti:freezer_d"]
    refs = [ref for _, lit, ref in _stated(conn, ranged["intent_id"]) if ref]

    # Two batches stored in the same freezer point at the same row, and it is
    # the same entity the freezer's own label was asserted about.
    assert refs.count(freezer_d) == 2
    assert len(_entities_named(conn, "uniti:freezer_d")) == 1


def test_a_class_ranged_value_registers_a_uri_nothing_else_names(conn, ranged):
    """`uniti:freezer_e` appears only on the value side, and still gets an id."""
    freezer_e = ranged["entities"]["uniti:freezer_e"]
    assert freezer_e in ranged["minted"].values()
    assert len(_entities_named(conn, "uniti:freezer_e")) == 1

    refs = [ref for _, lit, ref in _stated(conn, ranged["intent_id"]) if ref]
    assert refs.count(freezer_e) == 1


def _confidences(conn, intent_id):
    """The facts of one seal, as (predicate_uri, confidence), in order."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.value_literal, a.confidence
            FROM assertion a
            JOIN assertion p ON p.subject_id = a.predicate_id
                            AND p.subject_id <> p.predicate_id
                            AND p.value_literal IS NOT NULL
            WHERE a.intent_id = %s AND a.source = %s
            ORDER BY a.seq
            """,
            (intent_id, "human_stated"),
        )
        return cur.fetchall()


def test_a_stated_confidence_reaches_the_log_and_silence_stays_null(conn, confident):
    """Absent is NULL, not `high`: a default would claim what nobody said."""
    stated = _confidences(conn, confident["intent_id"])
    assert stated == [
        ("uniti:material_kilograms", "high"),
        ("uniti:material_kilograms", "low"),
        ("uniti:material_label", None),
    ]
    # The minted URI rows are the tool's own act and state nothing either.
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT confidence FROM assertion "
            "WHERE intent_id = %s AND source = %s",
            (confident["intent_id"], "system_derived"),
        )
        assert cur.fetchall() == [(None,)]


def test_a_confidence_the_kernel_does_not_know_is_refused(conn, tmp_path):
    """Refused here rather than by the check constraint, and non-zero at the CLI."""
    before = _counts(conn)
    with pytest.raises(DraftError, match="fairly sure"):
        seal(conn, FIXTURES / "bad_confidence.yaml", actor_id="test", into=tmp_path)
    assert main([str(FIXTURES / "bad_confidence.yaml"), "--actor", "test",
                 "--into", str(tmp_path)]) != 0
    assert list(tmp_path.iterdir()) == []
    assert _counts(conn) == before


def test_a_fifth_key_on_a_fact_is_still_refused(conn, tmp_path):
    """The set is closed, not loosened: one key was added, not the door."""
    before = _counts(conn)
    with pytest.raises(DraftError, match="authority"):
        seal(conn, FIXTURES / "extra_fact_key.yaml", actor_id="test", into=tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert _counts(conn) == before


def test_register_names_every_slot_uri_and_writes_no_file(conn, sealed):
    """A sealed version's vocabulary reaches a log without a version being cut.

    The directory is read before and after: registering is a write into the
    log and nowhere else, so a second log costs no `vN+1` in the map store.
    """
    into, first, _ = sealed
    before = sorted(p.name for p in into.iterdir())

    result = register(conn, into / "v1.yaml", actor_id="test")

    assert sorted(p.name for p in into.iterdir()) == before
    assert result["version"] == first["version"]
    declared = _slot_uris(into / "v1.yaml")
    assert declared
    for uri in declared:
        assert _entities_named(conn, uri), f"{uri} is in no log row"


def test_register_mints_nothing_the_log_already_holds(conn, sealed):
    """The second call writes nothing and reuses what the first one minted.

    Registering the same version into the same log twice is how a seeding
    script that is re-run behaves, and it must not leave a second entity
    behind every URI.
    """
    into, _, _ = sealed
    first = register(conn, into / "v1.yaml", actor_id="test")
    again = register(conn, into / "v1.yaml", actor_id="test")

    assert again["minted"] == {}
    assert again["assertions"] == []
    declared = _slot_uris(into / "v1.yaml")
    assert {uri: again["entities"][uri] for uri in declared} == {
        uri: first["entities"][uri] for uri in declared
    }


def _slot_uris(path):
    """Every slot_uri a version file declares, read out of the file itself."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return sorted(
        slot["slot_uri"] for slot in (document.get("slots") or {}).values()
    )


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

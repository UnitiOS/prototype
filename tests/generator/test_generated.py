"""Generating a table and a form from a sealed map and the log.

One fixture draft, sealed into a temporary directory so the production map
store is left alone, describes five classes:

    Tub      three slots of its own, two inherited from Held
    Held     the parent, two slots, one of them `g_class`
    Flavour  one slot, and one entity — what a class-ranged field offers
    Rumour   declared, and nobody ever said a thing under it
    Tally    declared with no `g_class` slot: a table, and no form

and four entities, each with its class stated: a tub with every cell filled, a
tub with only its name, a crate that is a Held and not a Tub, and a flavour.

The crate is the point of the fixture. `g_place` is a column of Tub by
inheritance, so a rule that made an entity a row of every table one of whose
columns it had a fact under would put the crate in the tub table. It says it
is a Held; the log is read, and it is a row of the parent's table only. The
tubs are rows of both, which is what `is_a` means.

The reads sit at as_of 1 June and the form writes are recorded 1 August, so
these tests do not depend on the order they run in.

Run: .venv/Scripts/python.exe -m pytest tests/generator -q
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components"))

from generate import (  # noqa: E402
    MapError, columns, connect, form, read_map, render_form, render_table,
    submit, table, verify,
)
from resolve import resolve_single  # noqa: E402
from seal import seal  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

SEALED = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
# Both clocks sit after the seal and before anything a form writes.
READ = "2026-06-01T00:00:00Z"
# What the forms below claim, and when the log learns it.
ENTERED_FROM = "2026-07-01T00:00:00Z"
ENTERED_AT = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)
LATER = "2026-09-01T00:00:00Z"


@pytest.fixture(scope="module")
def conn():
    with connect() as c:
        yield c


@pytest.fixture(scope="module")
def map_(conn, tmp_path_factory):
    """The fixture draft, sealed, and the sealed file read back as a map."""
    into = tmp_path_factory.mktemp("generator")
    result = seal(conn, FIXTURES / "draft_shop.yaml", actor_id="test",
                  into=into, sealed_at=SEALED)
    return read_map(result["path"])


def built(conn, map_, class_name, valid_at=READ, as_of=READ):
    return table(conn, map_, class_name, valid_at=valid_at, as_of=as_of)


def cells(t):
    return {row["uri"]: row["cells"] for row in t["rows"]}


def test_a_draft_is_not_a_map():
    """It carries no version, and every assertion has to name one."""
    with pytest.raises(MapError, match="not a sealed map"):
        read_map(FIXTURES / "draft_shop.yaml")


def test_the_columns_are_the_classs_induced_slots(map_):
    cols = columns(map_, "Tub")
    assert [c["name"] for c in cols] == [
        "g_tub_name", "g_tub_kilograms", "g_tub_flavour", "g_class", "g_place"
    ]
    assert [c["uri"] for c in cols] == [
        "uniti:g_tub_name", "uniti:g_tub_kilograms", "uniti:g_tub_flavour",
        "uniti:g_class", "uniti:g_place",
    ]
    # Straight off the map: an identifier induces required, and a class range
    # is the same test seal makes when it picks value_ref over value_literal.
    assert [c["required"] for c in cols] == [True, True, False, False, False]
    assert [c["ref"] for c in cols] == [False, False, True, False, False]
    # The parent's own table is the two slots it declares. The class column is
    # one of them, so a class's own table always shows what put a row in it.
    assert [c["name"] for c in columns(map_, "Held")] == ["g_class", "g_place"]
    with pytest.raises(MapError, match="declares no class"):
        columns(map_, "Sundae")


def test_the_table_is_what_the_log_says_at_those_clocks(conn, map_):
    t = built(conn, map_, "Tub")
    assert cells(t) == {
        "uniti:g_tub_1": ["Tub 1", "4.8", "uniti:g_vanilla", "Tub",
                          "Display cabinet"],
        "uniti:g_tub_2": ["Tub 2", None, None, "Tub", None],
    }
    # Rows come out in one order whatever the log's insertion order was.
    assert [r["uri"] for r in t["rows"]] == ["uniti:g_tub_1", "uniti:g_tub_2"]


def test_the_rows_equal_a_direct_read_of_the_log(conn, map_):
    """Every cell, against one SQL statement that never calls resolve_single.

    The table is built one pair at a time through the kernel's own read; the
    check re-derives the same cells with a single DISTINCT ON. What is being
    compared is the generator's pivot — which entity is a row, which value
    lands in which column — not the read rule against itself.
    """
    for class_name in ("Tub", "Held", "Flavour", "Rumour", "Tally"):
        t = built(conn, map_, class_name)
        assert verify(conn, t) == [], class_name


def test_a_row_is_what_the_log_says_the_entity_is(conn, map_):
    """The crate has a fact under one of Tub's columns and is not a Tub.

    `g_place` is a column of Tub by inheritance, and the crate has a g_place.
    What keeps it out is the only thing that should: it says it is a Held.
    """
    assert "uniti:g_crate" not in cells(built(conn, map_, "Tub"))
    # The parent's table holds all three, because `is_a` is walked downward
    # for rows exactly as `columns()` walks it upward for columns. A tub is a
    # row of two tables, which is what the relation means.
    assert cells(built(conn, map_, "Held")) == {
        "uniti:g_crate": ["Held", "Dry store"],
        "uniti:g_tub_1": ["Tub", "Display cabinet"],
        "uniti:g_tub_2": ["Tub", None],
    }


def test_a_class_nobody_spoke_about_generates_an_empty_table(conn, map_):
    """A real outcome. The map declares Rumour; the log holds no rumour."""
    t = built(conn, map_, "Rumour")
    assert [c["name"] for c in t["columns"]] == ["g_class", "g_rumour_text"]
    assert t["rows"] == []
    assert "0 rows, 2 columns" in render_table(t)


def test_a_class_with_no_class_slot_is_a_table_and_not_a_form(conn, map_):
    """Nothing can say an entity is a Tally, so no form can ask for one.

    It keeps its table — a class whose rows are counted up rather than
    written down is still a set of columns — and that table is empty.
    """
    t = built(conn, map_, "Tally")
    assert [c["name"] for c in t["columns"]] == ["g_tally_total"]
    assert t["rows"] == []
    with pytest.raises(MapError, match="designates_type"):
        form(conn, map_, "Tally")


def test_a_form_is_generated_for_one_class(conn, map_):
    f = form(conn, map_, "Tub", valid_at=READ, as_of=READ)
    fields = {field["name"]: field for field in f["fields"]}
    assert list(fields) == [
        "g_tub_name", "g_tub_kilograms", "g_tub_flavour", "g_class", "g_place"
    ]
    assert fields["g_tub_kilograms"]["range"] == "decimal"
    assert fields["g_tub_kilograms"]["required"] is True
    assert fields["g_place"]["required"] is False
    # A class-ranged field offers entities, labelled by the slot the map says
    # identifies them — so choosing one writes an edge, not a string.
    assert fields["g_tub_flavour"]["options"] == [("uniti:g_vanilla", "Vanilla")]
    assert fields["g_tub_name"]["options"] == []
    assert "-> Flavour" in render_form(f)
    # A class nobody has spoken about still has a form: it carries the slot
    # that could say so. It is the empty table that is the finding.
    assert len(form(conn, map_, "Rumour")["fields"]) == 2


def test_a_value_entered_through_the_form_reaches_the_log(conn, map_):
    """One literal and one edge, on a subject the log already holds."""
    result = submit(
        conn, map_, "Tub",
        subject="uniti:g_tub_2",
        values={"g_tub_kilograms": "5.1", "g_tub_flavour": "uniti:g_vanilla"},
        actor_id="test", valid_from=ENTERED_FROM, recorded_at=ENTERED_AT,
    )
    # Neither the subject nor the flavour is new, so the form minted nothing.
    assert result["minted"] == {}
    assert len(result["assertions"]) == 2

    def back(field, valid_at=LATER, as_of=LATER):
        return resolve_single(conn, subject_id=result["subject_id"],
                              predicate_id=result["predicates"][field],
                              valid_at=valid_at, as_of=as_of)

    assert back("g_tub_kilograms")["value_literal"] == "5.1"
    assert back("g_tub_kilograms")["ontology_version"] == map_["version"]
    assert back("g_tub_flavour")["value_literal"] is None
    assert back("g_tub_flavour")["value_ref"] is not None

    # And the generated table is a read, not a store: at the as_of the other
    # tests use, the log had not learned any of this yet.
    assert cells(built(conn, map_, "Tub"))["uniti:g_tub_2"] == [
        "Tub 2", None, None, "Tub", None
    ]
    assert cells(built(conn, map_, "Tub", LATER, LATER))["uniti:g_tub_2"] == [
        "Tub 2", "5.1", "uniti:g_vanilla", "Tub", None
    ]


def test_a_form_naming_an_entity_the_log_has_never_held_mints_it(conn, map_):
    """And the class field is what puts the new entity in a table.

    The form asks for it like any other field. A submission that left it out
    would mint an entity that is a row of nothing, which is the rule being
    honest rather than a defect.
    """
    result = submit(
        conn, map_, "Tub",
        subject="uniti:g_tub_3",
        values={"g_tub_name": "Tub 3", "g_class": "Tub"},
        actor_id="test", valid_from=ENTERED_FROM, recorded_at=ENTERED_AT,
    )
    assert list(result["minted"]) == ["uniti:g_tub_3"]
    assert cells(built(conn, map_, "Tub", LATER, LATER))["uniti:g_tub_3"] == [
        "Tub 3", None, None, "Tub", None
    ]


def test_a_field_the_map_does_not_declare_is_refused(conn, map_):
    with pytest.raises(MapError, match="g_colour"):
        submit(conn, map_, "Tub", subject="uniti:g_tub_1",
               values={"g_colour": "white"}, actor_id="test")

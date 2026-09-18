"""Composition: several pinned modules, compiled as one application.

Slice 1 proved that a pin keeps its meaning. This is the claim on top of it:

    a table declared in one module is computed from events stated in another,
    joined by nothing but the predicate URIs in the one registry.

`@demo/stock@v1` declares `IngredientStock` and owns none of what fills it.
The rows come from `StockMovement`, which is `@demo/inventory`'s. The grouping
value names an `Ingredient`, which is `@demo/catalog`'s. The reorder level is a
fact somebody stated under `@demo/catalog`'s predicate. Three modules, one
number, and no module was changed to make it work.

These tests execute the compiler rather than reading its plan, which is what
the compiler had no test for until now: log in, numbers out.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

import dev_modules  # noqa: E402
import load_facts  # noqa: E402
from compile import MapError, compile_class, plan_for  # noqa: E402
from components.api import application  # noqa: E402
from components.modules import read  # noqa: E402
from generate import read_map  # noqa: E402
from perform import connect  # noqa: E402

CATALOG, INVENTORY, STOCK = dev_modules.CATALOG, dev_modules.INVENTORY, dev_modules.STOCK
APP_NAME, APP_VERSION = dev_modules.APPLICATION
DATA = dev_modules.FIXTURES / "demo_data.yaml"

# A record clock late enough to hold whatever this run writes. A submission is
# recorded when it happens, which is a moment from now, so reading it back at
# `as_of` today would be reading the log as it stood before the write.
AFTER_THIS_RUN = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

# What the demonstration data adds up to, at three pairs of clocks. Worked out
# from the data file by hand, not from a run of this code.
#
#   valid_at 30 June, as_of today       everything that had happened by then,
#                                       including the delivery note found in
#                                       July for a delivery on 12 June.
#   valid_at 30 June, as_of 1 July      the same world, known worse: the late
#                                       note has not been found yet, so 25 kg
#                                       of flour is missing.
#   valid_at 5 July,  as_of today       the same facts, but the reorder level
#                                       somebody raised on 1 July now stands.
EXPECTED = {
    ("2026-06-30", "2026-09-18"): {
        "cat:ing_flour": ("86", "40", "46"),
        "cat:ing_sugar": ("37", "20", "17"),
        "cat:ing_butter": ("5", "10", "-5"),
        "cat:ing_milk": ("9", "15", "-6"),
        "cat:ing_salt": ("5", None, None),
        "cat:ing_yeast": ("2", None, None),
        "cat:ing_egg": ("100", None, None),
        "cat:ing_box": ("200", None, None),
    },
    ("2026-06-30", "2026-07-01"): {"cat:ing_flour": ("61", "40", "21")},
    ("2026-07-05", "2026-09-18"): {"cat:ing_flour": ("86", "60", "26")},
}


@pytest.fixture(scope="module")
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn


@pytest.fixture(scope="module")
def world(conn, tmp_path_factory):
    """The whole slice in one place: modules sealed, then the facts loaded."""
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    data = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    load_facts.load(conn, data, store, actor_id="test")
    # The API opens a connection of its own, so what this fixture wrote has to
    # be committed before anything outside this transaction can read it.
    conn.commit()
    return store


@pytest.fixture(scope="module")
def app_map(world):
    return read_map(world.path(APP_NAME, APP_VERSION), world)


def _rows(conn, world, valid_at, as_of):
    out = application.projection(conn, world, APP_NAME, APP_VERSION,
                                 "IngredientStock", valid_at=valid_at, as_of=as_of)
    names = [c["name"] for c in out["columns"]]
    assert names == ["stock_ingredient", "quantity_on_hand", "reorder_level", "headroom"]
    return out, {row[0]: tuple(None if c is None else str(c) for c in row[1:])
                 for row in out["rows"]}


@pytest.mark.parametrize("clocks", sorted(EXPECTED))
def test_a_projection_computes_from_another_module_s_events(conn, world, clocks):
    _, rows = _rows(conn, world, *clocks)
    for uri, expected in EXPECTED[clocks].items():
        assert rows[uri] == expected, uri


def test_an_empty_cell_is_not_a_nought(conn, world):
    """Four of the eight ingredients have no reorder level, and say so.

    A sum over no rows is nought, because that is what the operator is over an
    empty set. A parameter nobody stated is not: it is the absence of a rule,
    and a nought there would be somebody's judgement invented by the compiler.
    """
    _, rows = _rows(conn, world, "2026-06-30", "2026-09-18")
    assert rows["cat:ing_salt"] == ("5", None, None)
    assert rows["cat:ing_flour"][1] == "40"


def test_the_numbers_move_with_both_clocks(conn, world):
    """The two clocks are independent, and each one alone changes the answer."""
    _, at_june = _rows(conn, world, "2026-06-30", "2026-09-18")
    _, as_known_then = _rows(conn, world, "2026-06-30", "2026-07-01")
    _, later = _rows(conn, world, "2026-07-05", "2026-09-18")

    # Same world, worse knowledge: a delivery note found in July.
    assert at_june["cat:ing_flour"][0] == "86"
    assert as_known_then["cat:ing_flour"][0] == "61"
    # Same knowledge, later world: a level somebody raised on 1 July.
    assert at_june["cat:ing_flour"][1] == "40"
    assert later["cat:ing_flour"][1] == "60"


def test_every_rule_names_the_module_it_reads(conn, world):
    """The three derived columns are three kinds of derivation, and cross-module."""
    out, _ = _rows(conn, world, "2026-06-30", "2026-09-18")
    by_name = {c["name"]: c for c in out["columns"]}

    assert by_name["quantity_on_hand"]["kind"] == "aggregate"
    assert by_name["quantity_on_hand"]["rule"]["over"] == "StockMovement"
    assert by_name["quantity_on_hand"]["rule"]["measure"] == "inv:movement_quantity"
    assert by_name["reorder_level"]["kind"] == "parameter"
    assert by_name["reorder_level"]["rule"]["slot_uri"] == "cat:ingredient_reorder_level"
    assert by_name["headroom"]["kind"] == "expression"

    # None of the three predicates belongs to the module that declares the
    # table. That is the composition, stated as plainly as it can be.
    classes = read.class_graph(world, APP_NAME, APP_VERSION)
    owner = {n["name"]: n["module"]["name"] for n in classes["nodes"]}
    assert owner["IngredientStock"] == STOCK
    assert owner["StockMovement"] == INVENTORY
    assert owner["Ingredient"] == CATALOG


def test_the_class_graph_says_what_is_joined_to_what(world):
    graph = read.class_graph(world, APP_NAME, APP_VERSION)
    assert [m["name"] for m in graph["modules"]] == [
        "@uniti/core", CATALOG, INVENTORY, STOCK]
    assert {m["name"] for m in graph["modules"] if m["purpose"] == "demonstration"} == {
        CATALOG, INVENTORY, STOCK}

    edges = {(e["from"], e["to"], e["kind"]) for e in graph["edges"]}
    assert ("IngredientStock", "StockMovement", "aggregate") in edges
    assert ("IngredientStock", "Ingredient", "parameter") in edges
    assert ("StockMovement", "Ingredient", "reference") in edges
    assert ("Ingredient", "Category", "reference") in edges

    shapes = {n["name"]: n["shape"] for n in graph["nodes"]}
    assert shapes["IngredientStock"] == "derived"
    assert shapes["StockMovement"] == "stated"


def test_the_application_lists_every_table_it_can_fill(world):
    read_out = application.application(world, APP_NAME, APP_VERSION)
    assert read_out["purpose"] == "demonstration"
    by_class = {t["class"]: t for t in read_out["tables"]}
    assert by_class["IngredientStock"]["shape"] == "grouped"
    assert by_class["IngredientStock"]["table"] == "p_ingredient_stock"
    # The application fills tables for classes it never declared.
    assert by_class["StockMovement"]["shape"] == "entities"
    assert by_class["StockMovement"]["module"]["name"] == INVENTORY
    assert by_class["Ingredient"]["module"]["name"] == CATALOG


def test_the_operational_store_holds_what_the_log_derived(conn, world, app_map):
    """The last step: the numbers land in a database of their own.

    Two databases and no join between them — the rows come back from the
    operational store, which holds no assertion and cannot reach one.
    """
    with psycopg.connect(os.environ["UNITI_OPS_DSN"]) as ops:
        built = compile_class(conn, ops, app_map, "IngredientStock",
                              valid_at="2026-06-30", as_of="2026-09-18")
        assert built["plan"]["table"] == "p_ingredient_stock"
        stored = {row[0]: tuple(None if c is None else str(c) for c in row[1:])
                  for row in built["rows"]}
        assert stored["cat:ing_flour"] == ("86", "40", "46")

        # And the entity-shaped tables the same application fills.
        ingredients = compile_class(conn, ops, app_map, "Ingredient",
                                    valid_at="2026-06-30", as_of="2026-09-18")
        names = [c["name"] for c in ingredients["plan"]["columns"]]
        assert names[0] == "entity_uri" and "ingredient_name" in names
        assert len(ingredients["rows"]) == 8

        with ops.cursor() as cur:
            cur.execute("SELECT quantity_on_hand FROM p_ingredient_stock "
                        "WHERE stock_ingredient = 'cat:ing_flour'")
            assert str(cur.fetchone()[0]) == "86"


def test_a_map_without_the_store_cannot_be_read(world):
    """An application's version file is not readable on its own, and says so.

    It pins three modules; without the store there is nothing to resolve them
    against. This is the refusal that keeps a half-resolved map from being
    compiled as if it were whole.
    """
    with pytest.raises(MapError, match="only whole in a module store"):
        read_map(world.path(APP_NAME, APP_VERSION))


def test_a_class_nothing_can_be_an_instance_of_has_no_table(app_map):
    """IngredientStock is an answer, not a thing, and only one shape fits it."""
    assert plan_for(app_map, "IngredientStock")["shape"] == "grouped"
    with pytest.raises(MapError, match="designates_type"):
        from compile import plan_entities
        plan_entities(app_map, "IngredientStock")


def test_the_api_serves_the_application(conn, world, monkeypatch):
    from starlette.testclient import TestClient
    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    client = TestClient(app)

    listing = client.get("/api/app", params={"name": APP_NAME, "version": APP_VERSION})
    assert listing.status_code == 200
    assert listing.json()["purpose"] == "demonstration"

    table = client.get("/api/app/projection", params={
        "name": APP_NAME, "version": APP_VERSION, "class": "IngredientStock",
        "valid_at": "2026-06-30", "as_of": "2026-09-18"})
    body = table.json()
    rows = {row[0]: row[1] for row in body["rows"]}
    assert rows["cat:ing_flour"] == "86"
    assert "p_ingredient_stock" in body["sql"]

    classes = client.get("/api/modules/classes",
                         params={"name": APP_NAME, "version": APP_VERSION})
    assert any(e["kind"] == "aggregate" for e in classes.json()["edges"])

    unknown = client.get("/api/app/projection", params={
        "name": APP_NAME, "version": APP_VERSION, "class": "Nothing"})
    assert unknown.status_code == 400
    assert client.get("/api/app", params={"name": APP_NAME}).status_code == 400


def test_a_data_file_is_refused_when_it_names_what_the_map_has_not(conn, world):
    """The loader knows no words of its own; everything is checked in the map."""
    data = {"map": f"{APP_NAME}@{APP_VERSION}", "actions": [
        {"action": "x", "valid_from": "2026-01-01T00:00:00+00:00",
         "entities": [{"uri": "x:one", "facts": {"no_such_slot": "1"}}]}]}
    with pytest.raises(load_facts.DataError, match="no slot for"):
        load_facts.load(conn, data, world, actor_id="test")

    data["actions"][0]["entities"][0] = {"uri": "x:one", "class": "NoSuchClass"}
    with pytest.raises(load_facts.DataError, match="no class for"):
        load_facts.load(conn, data, world, actor_id="test")


# ---------------------------------------------------------------- provenance


def test_a_cell_can_be_taken_apart(conn, world):
    """The five statements that make flour 86, and the one that makes it 40.

    A projection is a claim. This is the claim taken apart: the same map, the
    same two clocks, and every statement underneath one cell, each one naming
    the assertion and the intent that wrote it.
    """
    keys = {"stock_ingredient": "cat:ing_flour"}
    total = application.cell(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                             "quantity_on_hand", keys,
                             valid_at="2026-06-30", as_of="2026-09-18")
    assert total["kind"] == "aggregate"
    assert total["operator"] == "sum" and total["over"] == "StockMovement"
    assert not total["cut_off"]

    # The parts add up to the whole, which is the only thing worth checking.
    assert sum(int(s["value"]) for s in total["statements"]) == 86
    assert {s["subject_uri"] for s in total["statements"]} == {
        "inv:mv_0001", "inv:mv_0009", "inv:mv_0015", "inv:mv_0022", "inv:mv_0023"}
    assert all(s["assertion_id"] and s["intent_id"] for s in total["statements"])

    # And the late-found delivery note is in there, dated on both clocks.
    late = next(s for s in total["statements"] if s["subject_uri"] == "inv:mv_0022")
    assert str(late["valid_from"])[:7] == "2026-06"
    assert str(late["recorded_at"])[:7] == "2026-07"


def test_a_cell_knows_when_it_was_not_yet_known(conn, world):
    """Move the record clock back and the same cell stands on one fewer."""
    keys = {"stock_ingredient": "cat:ing_flour"}
    then = application.cell(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                            "quantity_on_hand", keys,
                            valid_at="2026-06-30", as_of="2026-07-01")
    assert sum(int(s["value"]) for s in then["statements"]) == 61
    assert "inv:mv_0022" not in {s["subject_uri"] for s in then["statements"]}


def test_a_parameter_cell_names_the_one_who_said_so(conn, world):
    keys = {"stock_ingredient": "cat:ing_flour"}
    held = application.cell(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                            "reorder_level", keys,
                            valid_at="2026-06-30", as_of="2026-09-18")
    assert held["kind"] == "parameter" and held["of"] == "stock_ingredient"
    assert len(held["statements"]) == 1
    only = held["statements"][0]
    assert only["value"] == "40"
    assert only["predicate"] == "cat:ingredient_reorder_level"
    assert only["source"] == "human_stated"

    # The same cell after somebody raised it: a different statement, and the
    # earlier one is neither edited nor gone.
    later = application.cell(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                             "reorder_level", keys,
                             valid_at="2026-07-05", as_of="2026-09-18")
    assert later["statements"][0]["value"] == "60"
    assert later["statements"][0]["assertion_id"] != only["assertion_id"]


def test_an_expression_cell_names_the_columns_it_reads(conn, world):
    read_back = application.cell(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                                 "headroom", {"stock_ingredient": "cat:ing_flour"},
                                 valid_at="2026-06-30", as_of="2026-09-18")
    assert read_back["kind"] == "expression"
    assert read_back["reads"] == ["quantity_on_hand", "reorder_level"]
    assert read_back["statements"] == []


def test_a_cell_of_an_entity_table_is_one_statement(conn, world):
    held = application.cell(conn, world, APP_NAME, APP_VERSION, "Ingredient",
                            "ingredient_name", {"entity_uri": "cat:ing_flour"},
                            valid_at="2026-06-30", as_of="2026-09-18")
    assert held["entity"]["uri"] == "cat:ing_flour"
    assert held["statements"][0]["value"] == "Wheat flour"
    # The slot was renamed in the catalog v2 and the predicate never moved, so
    # the fact stated under the v1 name is the fact the v2 name reads.
    assert held["statements"][0]["predicate"] == "cat:ingredient_label"


def test_a_column_that_is_not_there_is_refused(conn, world):
    with pytest.raises(MapError, match="no column"):
        application.cell(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                         "nothing", {}, valid_at="2026-06-30", as_of="2026-09-18")


# ----------------------------------------------------------------- the form


def test_a_form_is_the_map_asked_for_rather_than_reported(conn, world):
    built = application.form_of(conn, world, APP_NAME, APP_VERSION, "StockMovement",
                                valid_at="2026-06-30", as_of="2026-09-18")
    assert built["label"] == f"{APP_NAME}@{APP_VERSION}"
    fields = {f["name"]: f for f in built["fields"]}

    # The class fact is not a field. The map says which slot carries it and
    # submitting states it, so nobody types the class in.
    assert built["type_slot"] == "entity_class"
    assert "entity_class" not in fields

    # A field over a class range offers entities, so choosing one writes an
    # edge rather than a string, and the slot belongs to the module that
    # declared it.
    assert fields["movement_ingredient"]["ref"] is True
    assert len(fields["movement_ingredient"]["options"]) == 8
    assert fields["movement_quantity"]["ref"] is False
    assert fields["movement_quantity"]["options"] == []
    assert fields["movement_ingredient"]["module"]["name"] == INVENTORY


def test_a_form_submission_is_one_intent_and_comes_straight_back(conn, world):
    """The whole round trip: typed in, written once, read back out of the log.

    The movement is dated August, so every earlier clock in this file and every
    number asserted at one is untouched by it.
    """
    written = application.state(
        conn, world, APP_NAME, APP_VERSION, "StockMovement",
        subject="inv:mv_0101",
        values={"movement_code": "MV-0101", "movement_ingredient": "cat:ing_salt",
                "movement_location": "inv:loc_store", "movement_quantity": "12",
                "movement_happened_on": "2026-08-03", "movement_reason": "delivery"},
        actor_id="test", valid_from="2026-08-03T00:00:00+00:00")
    assert written["assertions"] >= 7
    assert written["ontology_version"] == f"{APP_NAME}@{APP_VERSION}"

    # A fact typed into a demonstration is marked as one, exactly like a fact
    # that was sealed or loaded into it.
    with conn.cursor() as cur:
        cur.execute("SELECT reason_code, action_name FROM intent WHERE id = %s",
                    (written["intent_id"],))
        assert cur.fetchone() == ("demonstration", "submit_StockMovement")

    # Nothing was compiled in between: the aggregate reads the log. The record
    # clock has to be after now, because a submission is recorded when it
    # happens and this one happened a moment ago.
    _, august = _rows(conn, world, "2026-08-31", AFTER_THIS_RUN)
    assert august["cat:ing_salt"][0] == "17"
    _, june = _rows(conn, world, "2026-06-30", "2026-09-18")
    assert june["cat:ing_salt"][0] == "5"

    # And it can be taken apart like any other cell.
    parts = application.cell(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                             "quantity_on_hand", {"stock_ingredient": "cat:ing_salt"},
                             valid_at="2026-08-31", as_of=AFTER_THIS_RUN)
    assert {s["subject_uri"] for s in parts["statements"]} == {"inv:mv_0003", "inv:mv_0101"}


def test_a_form_is_refused_for_a_class_nothing_can_be(conn, world):
    with pytest.raises(MapError, match="designates_type"):
        application.form_of(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                            valid_at="2026-06-30", as_of="2026-09-18")


def test_the_api_takes_a_form_and_gives_back_the_cell(conn, world, monkeypatch):
    from starlette.testclient import TestClient
    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    conn.commit()
    client = TestClient(app)

    built = client.get("/api/app/form", params={
        "name": APP_NAME, "version": APP_VERSION, "class": "StockMovement"})
    assert built.status_code == 200
    assert any(f["ref"] for f in built.json()["fields"])

    posted = client.post("/api/app/state", json={
        "name": APP_NAME, "version": APP_VERSION, "class": "StockMovement",
        "subject": "inv:mv_0102", "actor": "test",
        "valid_from": "2026-08-04T00:00:00+00:00",
        "values": {"movement_code": "MV-0102", "movement_ingredient": "cat:ing_yeast",
                   "movement_location": "inv:loc_store", "movement_quantity": "3"},
    })
    assert posted.status_code == 200, posted.json()
    assert posted.json()["intent_id"]

    taken_apart = client.get("/api/app/cell", params={
        "name": APP_NAME, "version": APP_VERSION, "class": "IngredientStock",
        "column": "quantity_on_hand", "key.stock_ingredient": "cat:ing_yeast",
        "valid_at": "2026-08-31", "as_of": AFTER_THIS_RUN})
    values = sorted(int(s["value"]) for s in taken_apart.json()["statements"])
    assert values == [2, 3]

    assert client.post("/api/app/state", json={"name": APP_NAME}).status_code == 400
    missing = client.get("/api/app/cell", params={
        "name": APP_NAME, "version": APP_VERSION, "class": "IngredientStock"})
    assert missing.status_code == 400

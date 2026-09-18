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

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
RIVAL = dev_modules.RIVAL
APP_NAME, APP_VERSION = dev_modules.APPLICATION
SWAP_NAME, SWAP_VERSION = dev_modules.SWAPPED
DATA = dev_modules.FIXTURES / "demo_data.yaml"
RIVAL_DATA = dev_modules.FIXTURES / "rival_data.yaml"

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
    """The whole slice in one place: modules sealed, then the facts loaded.

    Both sets of facts. The same twenty-four movements are stated twice, once
    in @demo/inventory's words and once in @rival/stock-moves', so that the two
    applications can be compared against one log rather than two.
    """
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    for path in (DATA, RIVAL_DATA):
        load_facts.load(conn, yaml.safe_load(path.read_text(encoding="utf-8")),
                        store, actor_id="test")
    # The API opens a connection of its own, so what this fixture wrote has to
    # be committed before anything outside this transaction can read it.
    conn.commit()
    return store


@pytest.fixture(scope="module")
def app_map(world):
    return read_map(world.path(APP_NAME, APP_VERSION), world)


def _rows(conn, world, valid_at, as_of, version=None):
    out = application.projection(conn, world, APP_NAME, version or APP_VERSION,
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
    """The three derived columns are three kinds of derivation, and cross-module.

    The aggregate now names a role rather than a class, which is the whole of
    what makes the application swappable: `Flow` belongs to core, and so does
    `amount`. What it *reads* is still @demo/inventory's own predicate, and the
    rule says both — what it was written against, and what it reached.
    """
    out, _ = _rows(conn, world, "2026-06-30", "2026-09-18")
    by_name = {c["name"]: c for c in out["columns"]}

    rule = by_name["quantity_on_hand"]["rule"]
    assert by_name["quantity_on_hand"]["kind"] == "aggregate"
    assert (rule["over"], rule["measure"]) == ("Flow", "amount")
    assert rule["covers"] == ["StockMovement"]
    assert rule["measure_uris"] == ["inv:movement_quantity"]
    assert rule["by_uris"] == {"stock_ingredient": ["inv:movement_ingredient"]}

    assert by_name["reorder_level"]["kind"] == "parameter"
    assert by_name["reorder_level"]["rule"]["slot_uris"] == ["cat:ingredient_reorder_level"]
    assert by_name["headroom"]["kind"] == "expression"

    # None of the three predicates belongs to the module that declares the
    # table. That is the composition, stated as plainly as it can be.
    classes = read.class_graph(world, APP_NAME, APP_VERSION)
    owner = {n["name"]: n["module"]["name"] for n in classes["nodes"]}
    assert owner["IngredientStock"] == STOCK
    assert owner["StockMovement"] == INVENTORY
    assert owner["Ingredient"] == CATALOG


def test_an_application_written_against_roles_survives_replacing_a_module(conn, world):
    """The claim this whole slice exists to make.

    Two inventory modules that share no word at all — different class names,
    different slot names, different prefix, different author — and one
    application that moves its pin from the first to the second without a
    single rule being touched. If the numbers are equal, it is because both
    modules answered core's questions, not because anything was translated.
    """
    _, mine = _rows(conn, world, "2026-06-30", "2026-09-18")
    _, theirs = _rows(conn, world, "2026-06-30", "2026-09-18", version=SWAP_VERSION)
    assert theirs == mine
    assert mine["cat:ing_flour"] == ("86", "40", "46")

    # And the second reading really did come from somewhere else. Same rule,
    # different predicates — which is what makes the equality mean anything.
    swapped = application.projection(conn, world, SWAP_NAME, SWAP_VERSION,
                                     "IngredientStock",
                                     valid_at="2026-06-30", as_of="2026-09-18")
    rule = {c["name"]: c["rule"] for c in swapped["columns"]}["quantity_on_hand"]
    assert (rule["over"], rule["measure"]) == ("Flow", "amount")
    assert rule["covers"] == ["Movement"]
    assert rule["measure_uris"] == ["rv:qty_delta"]
    assert "inv:movement_quantity" not in swapped["sql"]
    assert "rv:qty_delta" in swapped["sql"]


def test_the_swapped_application_changed_nothing_but_its_pin(world):
    """Not "equivalent rules" — the same bytes.

    A rewritten rule that happens to agree would prove only that two maps can
    be made to match. What is being claimed is stronger: there was nothing in
    the rules to rewrite.
    """
    def rules(version):
        text = world.path(APP_NAME, version).read_text(encoding="utf-8")
        return text.split("classes:\n", 1)[1].split("\nannotations:")[0]

    assert rules(APP_VERSION) == rules(SWAP_VERSION)

    pins = {v: {n for n, _ in world.closure(APP_NAME, v)}
            for v in (APP_VERSION, SWAP_VERSION)}
    assert INVENTORY in pins[APP_VERSION] and RIVAL not in pins[APP_VERSION]
    assert RIVAL in pins[SWAP_VERSION] and INVENTORY not in pins[SWAP_VERSION]


def test_replacing_a_module_leaves_its_statements_in_the_log(conn, world):
    """Nothing is migrated and nothing is lost: they stop being read, that is all.

    This is the property that makes an app store bearable. Uninstalling a
    module in an ordinary system drops its tables or strands them; here the
    facts live below the schema, so the only thing a swap changes is which
    predicates any rule reaches.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM assertion a JOIN entity e "
                    "ON e.id = a.predicate_id JOIN assertion u "
                    "ON u.subject_id = e.id AND u.value_literal = %s",
                    ("inv:movement_quantity",))
        (held,) = cur.fetchone()
    assert held == 24

    swapped = application.projection(conn, world, SWAP_NAME, SWAP_VERSION,
                                     "IngredientStock",
                                     valid_at="2026-06-30", as_of="2026-09-18")
    assert "inv:movement_quantity" not in swapped["sql"]

    # And the fit report counts them rather than leaving anybody to wonder.
    from components.modules import roles as roles_read
    report = roles_read.fit(world, APP_NAME, APP_VERSION, SWAP_VERSION, conn=conn)
    orphans = {o["uri"]: o["held"] for o in report["orphaned"]}
    assert orphans["inv:movement_quantity"] == 24
    assert report["orphaned_statements"] == sum(orphans.values())


def test_the_class_graph_says_what_is_joined_to_what(world):
    graph = read.class_graph(world, APP_NAME, APP_VERSION)
    assert [m["name"] for m in graph["modules"]] == [
        "@uniti/core", CATALOG, INVENTORY, STOCK]
    assert {m["name"] for m in graph["modules"] if m["purpose"] == "demonstration"} == {
        CATALOG, INVENTORY, STOCK}

    edges = {(e["from"], e["to"], e["kind"]) for e in graph["edges"]}
    # The aggregate points at the role, not at anybody's class. Reaching the
    # class is one more hop, and the picture should show that hop rather than
    # collapse it: that hop is the seam a module can be swapped at.
    assert ("IngredientStock", "Flow", "aggregate") in edges
    assert ("StockMovement", "Flow", "fills") in edges
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
    with pytest.raises(MapError) as caught:
        read_map(world.path(APP_NAME, APP_VERSION))
    assert caught.value.code == "pins_need_a_store"


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
    assert total["operator"] == "sum" and total["over"] == "Flow"
    assert total["covers"] == ["StockMovement"]
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
    """And the refusal hands back the columns that are, not just a complaint."""
    with pytest.raises(MapError) as caught:
        application.cell(conn, world, APP_NAME, APP_VERSION, "IngredientStock",
                         "nothing", {}, valid_at="2026-06-30", as_of="2026-09-18")
    assert caught.value.code == "no_such_column"
    assert "quantity_on_hand" in caught.value.repairs[0].options


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


def test_a_form_can_correct_and_withdraw_what_it_wrote(conn, world, monkeypatch):
    """A mistake typed into a form is taken back through the same form.

    The kernel has held `revokes` since P1 and `submit` takes it; the API did
    not pass it on, so a person who typed 30 for 3 had no way to say so from
    the screen. A correction names the row it replaces, and the log keeps
    both: read before the correction, the number is the mistaken one.
    """
    from starlette.testclient import TestClient
    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    conn.commit()
    client = TestClient(app)

    def box_on_hand(as_of):
        _, rows = _rows(conn, world, "2026-08-31", as_of)
        return rows["cat:ing_box"][0]

    typed = client.post("/api/app/state", json={
        "name": APP_NAME, "version": APP_VERSION, "class": "StockMovement",
        "subject": "inv:mv_0103", "actor": "test",
        "valid_from": "2026-08-06T00:00:00+00:00",
        "values": {"movement_code": "MV-0103", "movement_ingredient": "cat:ing_box",
                   "movement_location": "inv:loc_store", "movement_quantity": "30"},
    })
    assert typed.status_code == 200, typed.json()
    stated = typed.json()["stated"]
    assert set(stated) >= {"movement_code", "movement_quantity"}
    between = datetime.now(timezone.utc).isoformat()

    corrected = client.post("/api/app/state", json={
        "name": APP_NAME, "version": APP_VERSION, "class": "StockMovement",
        "subject": "inv:mv_0103", "actor": "test",
        "valid_from": "2026-08-06T00:00:00+00:00",
        "values": {"movement_quantity": "3"},
        "revokes": {"movement_quantity": stated["movement_quantity"]},
        "note": "30 was a typing mistake for 3",
    })
    assert corrected.status_code == 200, corrected.json()
    assert box_on_hand(AFTER_THIS_RUN) == "203"
    assert box_on_hand(between) == "230"

    # A withdrawal says "we were wrong" with nothing in its place, and only
    # that: the class is not stated a second time alongside it.
    withdrawn = client.post("/api/app/state", json={
        "name": APP_NAME, "version": APP_VERSION, "class": "StockMovement",
        "subject": "inv:mv_0103", "actor": "test",
        "valid_from": "2026-08-06T00:00:00+00:00",
        "revokes": {"movement_quantity": corrected.json()["stated"]["movement_quantity"]},
    })
    assert withdrawn.status_code == 200, withdrawn.json()
    assert withdrawn.json()["assertions"] == 1
    assert box_on_hand(AFTER_THIS_RUN) == "200"

    not_a_mapping = client.post("/api/app/state", json={
        "name": APP_NAME, "version": APP_VERSION, "class": "StockMovement",
        "subject": "inv:mv_0103", "actor": "test", "revokes": ["x"]})
    assert not_a_mapping.status_code == 400


def test_a_form_offers_what_the_log_holds_at_its_clocks(conn, world, app_map):
    """An entity added through one form is a choice in the next one at once.

    Choices used to come out of the operational store whenever it held a
    table for the class, and nothing but a compile fills that store — so an
    ingredient added a minute ago could not be chosen, and the screen forces a
    choice from the list. The operational store also stands at whatever clocks
    it was last filled at, while a form is asked at a pair of its own. The log
    answers at the pair asked, which is how every projection is already read.
    """
    with psycopg.connect(os.environ["UNITI_OPS_DSN"]) as ops:
        compile_class(conn, ops, app_map, "Ingredient",
                      valid_at="2026-06-30", as_of="2026-09-18")

    application.state(conn, world, APP_NAME, APP_VERSION, "Ingredient",
                      subject="cat:ing_cocoa",
                      values={"ingredient_code": "ING-COCOA", "ingredient_name": "Cocoa"},
                      actor_id="test", valid_from="2026-08-01T00:00:00+00:00")

    def offered(valid_at):
        built = application.form_of(conn, world, APP_NAME, APP_VERSION, "StockMovement",
                                    valid_at=valid_at, as_of=AFTER_THIS_RUN)
        field = next(f for f in built["fields"] if f["name"] == "movement_ingredient")
        return field, {o["uri"]: o["label"] for o in field["options"]}

    field, august = offered("2026-08-31")
    assert august["cat:ing_cocoa"] == "ING-COCOA"
    assert field["options_from"] == "the log"
    _, june = offered("2026-06-30")
    assert "cat:ing_cocoa" not in june and "cat:ing_flour" in june


def _counts(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM assertion), (SELECT count(*) FROM entity)")
        return cur.fetchone()


def _refused_at_the_door(conn, world, code, **submission):
    before = _counts(conn)
    with pytest.raises(MapError) as raised:
        application.state(conn, world, APP_NAME, APP_VERSION, "StockMovement",
                          actor_id="test", **submission)
    assert raised.value.code == code, str(raised.value)
    assert _counts(conn) == before
    return raised.value


def test_a_value_its_field_cannot_hold_is_refused_at_the_door(conn, world):
    """"twenty" in a number field used to reach the log as text and break the
    whole table at the next compile. The door asks the same cast the compiler
    will make, and refuses before anything is written."""
    refused = _refused_at_the_door(
        conn, world, "value_not_of_type", subject="inv:mv_0110",
        values={"movement_code": "MV-0110", "movement_quantity": "twenty"},
        valid_from="2026-08-10T00:00:00+00:00")
    assert refused.where == "StockMovement.movement_quantity"
    _refused_at_the_door(
        conn, world, "value_not_of_type", subject="inv:mv_0110",
        values={"movement_code": "MV-0110", "movement_happened_on": "10/08/2026x"},
        valid_from="2026-08-10T00:00:00+00:00")


def test_a_reference_must_be_one_of_the_choices_the_form_offers(conn, world):
    """An entity field names an entity the form would have offered at the same
    clocks — never a URI minted on the spot because nobody recognised it."""
    unknown = _refused_at_the_door(
        conn, world, "not_among_the_choices", subject="inv:mv_0111",
        values={"movement_code": "MV-0111", "movement_ingredient": "cat:ing_nothing"},
        valid_from="2026-08-11T00:00:00+00:00")
    assert "cat:ing_flour" in unknown.repairs[0].options

    # Something the log holds, but not one of these.
    _refused_at_the_door(
        conn, world, "not_among_the_choices", subject="inv:mv_0111",
        values={"movement_code": "MV-0111", "movement_ingredient": "inv:loc_store"},
        valid_from="2026-08-11T00:00:00+00:00")

    # One of these, but not yet at the moment the movement happened.
    application.state(conn, world, APP_NAME, APP_VERSION, "Ingredient",
                      subject="cat:ing_vanilla", values={"ingredient_code": "ING-VAN"},
                      actor_id="test", valid_from="2026-09-01T00:00:00+00:00")
    _refused_at_the_door(
        conn, world, "not_among_the_choices", subject="inv:mv_0111",
        values={"movement_code": "MV-0111", "movement_ingredient": "cat:ing_vanilla"},
        valid_from="2026-08-11T00:00:00+00:00")
    application.state(conn, world, APP_NAME, APP_VERSION, "StockMovement",
                      subject="inv:mv_0111", actor_id="test",
                      values={"movement_code": "MV-0111",
                              "movement_ingredient": "cat:ing_vanilla"},
                      valid_from="2026-09-02T00:00:00+00:00")


def test_a_withdrawal_names_a_statement_of_this_field_on_this_subject(conn, world):
    """An id from somewhere else would withdraw somebody else's row, silently."""
    first = application.state(
        conn, world, APP_NAME, APP_VERSION, "StockMovement", subject="inv:mv_0112",
        actor_id="test", values={"movement_code": "MV-0112", "movement_quantity": "4"},
        valid_from="2026-08-12T00:00:00+00:00")
    other = application.state(
        conn, world, APP_NAME, APP_VERSION, "StockMovement", subject="inv:mv_0113",
        actor_id="test", values={"movement_code": "MV-0113", "movement_quantity": "5"},
        valid_from="2026-08-12T00:00:00+00:00")

    elsewhere = _refused_at_the_door(
        conn, world, "revokes_another_statement", subject="inv:mv_0112",
        values={"movement_quantity": "6"},
        revokes={"movement_quantity": other["stated"]["movement_quantity"]},
        valid_from="2026-08-12T00:00:00+00:00")
    assert elsewhere.repairs[0].options == (first["stated"]["movement_quantity"],)
    _refused_at_the_door(
        conn, world, "revokes_another_statement", subject="inv:mv_0112", values={},
        revokes={"movement_quantity": first["stated"]["movement_code"]},
        valid_from="2026-08-12T00:00:00+00:00")
    _refused_at_the_door(
        conn, world, "revokes_another_statement", subject="inv:mv_0112", values={},
        revokes={"movement_quantity": "not-an-id"},
        valid_from="2026-08-12T00:00:00+00:00")


def test_the_api_sends_a_refusal_at_the_door_as_one(conn, world, monkeypatch):
    from starlette.testclient import TestClient
    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    conn.commit()
    posted = TestClient(app).post("/api/app/state", json={
        "name": APP_NAME, "version": APP_VERSION, "class": "StockMovement",
        "subject": "inv:mv_0114", "actor": "test",
        "values": {"movement_quantity": "a lot"}})
    assert posted.status_code == 400
    assert posted.json()["refusal"]["code"] == "value_not_of_type"

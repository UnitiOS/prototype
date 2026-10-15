"""The seal stops depending on what the compiler can do (ECOSYSTEM_PLAN.md,
step 6; story 7).

A construct enters the graph with its written meaning, an example, and a
sketch showing the compiler can follow it boundedly; its executor may come
later. So a refusal is one of two things:

    meaning      the graph is wrong — a slot that is not there, a key of the
                 wrong kind. It still stops the seal, as it always did.
    capability   the graph is sound and the compiler cannot compute it yet: a
                 total of only the rows whose value meets a condition, a key
                 more than one record away, a slot holding several values.
                 The column is written, sealed, shown as not computed yet, and
                 its example waits for the executor instead of failing.

The vocabulary stays closed: a value filter is one of six comparisons, in the
fixed words, and anything else under `where` is still refused.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from components.api import application as app_api  # noqa: E402
from components.examples import examples  # noqa: E402
from components.modules import catalogue as cat  # noqa: E402
from components.modules import read as modules_read  # noqa: E402
from components.modules.check import check  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
import compile as compiler  # noqa: E402
from compile import CompileError, _read_aggregate, plan_for  # noqa: E402
from perform import connect  # noqa: E402
from seal import register, seal  # noqa: E402

REGISTERED = [("@uniti/core", "v1"), ("@uniti/core", "v2"), ("@uniti/item", "v1")]
DAMAGE, TAGS = "@probe/rusak", "@probe/label"


@pytest.fixture(scope="module")
def conn():
    """One connection, never committed: the seals here are rolled back."""
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def store(conn, tmp_path_factory):
    held = Store([tmp_path_factory.mktemp("packages"), ROOT / "packages"])
    for name, version in REGISTERED:
        register(conn, held.path(name, version), actor_id="dev", store=held)
    return held


def step(store, name, op, **args):
    return studio.apply(store, name, op, args)


def _awaiting(store, conn, name):
    return sorted(h["where"] for h in reading.state(store, name, conn)["holes"]
                  if h["kind"] == "not_computed_yet")


def _blocking(store, conn, name):
    return [(h["kind"], h["where"]) for h in reading.state(store, name, conn)["holes"]
            if h["blocking"]]


@pytest.fixture(scope="module")
def damage(store, conn):
    """Damaged items: every unit damaged, and the units on lines that cost more
    than a hundred thousand — a total of only the rows whose value meets a
    condition, which the compiler does not compute yet."""
    name = DAMAGE
    step(store, name, "start", title="Damage",
         description="Items damaged while out, line by line.")
    step(store, name, "pin", module="@uniti/item@v1")
    step(store, name, "add_class", **{"class": "DamageLine",
                                      "description": "One item found damaged."})
    step(store, name, "add_class", **{"class": "ItemDamage",
                                      "description": "Damage per item."})
    step(store, name, "add_class", **{"class": "DamageNote",
                                      "description": "The note damage is written on."})
    step(store, name, "fill_role", **{"class": "DamageLine", "role": "Thing"})
    step(store, name, "fill_role", **{"class": "DamageNote", "role": "Thing"})
    for class_name, slot, kind, said, meant in (
        ("DamageLine", "damage_number", "string", "The number on the note.", {}),
        ("DamageLine", "damage_item", "Item", "The item damaged.", {}),
        ("DamageLine", "damage_note", "DamageNote", "The note it is written on.", {}),
        ("DamageNote", "note_number", "string", "The note's number.", {}),
        ("DamageNote", "note_item", "Item", "The item the note is about.", {}),
        ("DamageLine", "damage_quantity", "integer", "How many were damaged.",
         {"unit": "unit", "direction": "decrease"}),
        ("DamageLine", "damage_cost", "decimal", "What the repair costs.",
         {"unit": "IDR", "direction": "increase"}),
        ("ItemDamage", "item_damage_item", "Item", "The item.", {}),
        ("ItemDamage", "item_damage_units", "integer", "Units damaged.",
         {"unit": "unit", "direction": "level"}),
        ("ItemDamage", "item_damage_heavy", "integer",
         "Units damaged on lines costing more than 100000.",
         {"unit": "unit", "direction": "level"}),
        ("ItemDamage", "item_damage_twice", "integer",
         "Units damaged, the heavy ones counted twice.",
         {"unit": "unit", "direction": "level"}),
    ):
        step(store, name, "add_slot", slot=slot, range=kind, description=said, **meant)
        step(store, name, "attach", **{"class": class_name, "slot": slot})
    step(store, name, "set_slot", slot="damage_number", field="identifier", value="true")
    step(store, name, "set_slot", slot="note_number", field="identifier", value="true")
    by = "item_damage_item=damage_item"
    step(store, name, "aggregate", **{"class": "ItemDamage", "column": "item_damage_units",
                                      "over": "DamageLine", "sum": "damage_quantity",
                                      "by": by})
    step(store, name, "aggregate", **{"class": "ItemDamage", "column": "item_damage_heavy",
                                      "over": "DamageLine", "sum": "damage_quantity",
                                      "by": by, "where": "damage_cost>100000"})
    step(store, name, "expression", **{
        "class": "ItemDamage", "column": "item_damage_twice",
        "expression": "{item_damage_units} + {item_damage_heavy}"})

    step(store, name, "add_example", example="rusak",
         says="A tent comes back with two units badly torn and one scratched.")
    step(store, name, "record", example="rusak", record="tenda", **{"class": "Item"},
         facts="item_name=Tenda")
    for record, quantity, cost in (("d1", 2, 150000), ("d2", 1, 50000)):
        step(store, name, "record", example="rusak", record=record,
             **{"class": "DamageLine"}, when="2026-10-06",
             facts=f"damage_number={record.upper()}, damage_item=tenda, "
                   f"damage_quantity={quantity}, damage_cost={cost}")
    step(store, name, "expect", example="rusak", table="ItemDamage", row="tenda",
         values="item_damage_units=3, item_damage_heavy=2, item_damage_twice=5")
    step(store, name, "agree_example", example="rusak")

    step(store, name, "add_example", example="berat",
         says="Only the badly torn units count as heavy damage.")
    step(store, name, "record", example="berat", record="tenda", **{"class": "Item"},
         facts="item_name=Tenda")
    step(store, name, "record", example="berat", record="d1",
         **{"class": "DamageLine"}, when="2026-10-06",
         facts="damage_number=D1, damage_item=tenda, damage_quantity=2, "
               "damage_cost=150000")
    step(store, name, "expect", example="berat", table="ItemDamage", row="tenda",
         values="item_damage_heavy=2")
    step(store, name, "agree_example", example="berat")
    return name


# ---- written in the vocabulary's words -------------------------------------

def test_a_value_filter_is_written_in_the_vocabularys_fixed_words(store, damage):
    held = studio.open_draft(store, damage)["slots"]["item_damage_heavy"]
    spec = held["annotations"]["aggregate"]["value"]
    assert spec["where"] == {"damage_cost": {"above": 100000}}
    # Each comparison has one word; `slot=Class` still narrows by what a thing is.
    for written, said in (("damage_cost>=5", {"at_least": 5}),
                          ("damage_cost<=5", {"at_most": 5}),
                          ("damage_cost<5", {"below": 5}),
                          ("damage_cost==5", {"equals": 5}),
                          ("damage_cost!=5", {"not_equals": 5}),
                          ("damage_item=Item", {"is_a": "Item"})):
        step(store, damage, "aggregate", **{
            "class": "ItemDamage", "column": "item_damage_heavy", "over": "DamageLine",
            "sum": "damage_quantity", "by": "item_damage_item=damage_item",
            "where": written})
        spec = studio.open_draft(store, damage)["slots"]["item_damage_heavy"][
            "annotations"]["aggregate"]["value"]
        assert list(spec["where"].values()) == [said], written
    step(store, damage, "aggregate", **{
        "class": "ItemDamage", "column": "item_damage_heavy", "over": "DamageLine",
        "sum": "damage_quantity", "by": "item_damage_item=damage_item",
        "where": "damage_cost>100000"})


def test_words_outside_the_vocabulary_are_still_refused(store, damage):
    map_ = reading._map(store, damage, studio.open_draft(store, damage))

    def refused(**spec):
        with pytest.raises(CompileError) as caught:
            _read_aggregate(map_, "ItemDamage.item_damage_heavy", {
                "over": "DamageLine", "sum": "damage_quantity",
                "by": {"item_damage_item": "damage_item"}, **spec})
        return caught.value.code

    # A word the vocabulary does not have, two at once, or a value that is not one.
    assert refused(where={"damage_cost": {"like": "1%"}}) == "where_not_is_a"
    assert refused(where={"damage_cost": {"above": 1, "below": 9}}) == "where_not_is_a"
    assert refused(where={"damage_cost": {"above": [1, 2]}}) == "where_not_is_a"
    # Order means nothing for a reference: a thing is narrowed by what it is.
    assert refused(where={"damage_item": {"above": 3}}) == "where_not_is_a"
    # A slot that is not there is the graph being wrong, filter or no filter.
    assert refused(where={"damage_price": {"above": 3}}) == "no_such_slot"


# ---- sealed, and shown as not computed yet ---------------------------------

def test_a_column_the_compiler_cannot_compute_yet_is_shown_not_refused(
        store, conn, damage):
    assert _blocking(store, conn, damage) == []
    # The column, and the expression reading it: neither can be computed.
    assert _awaiting(store, conn, damage) == ["ItemDamage.item_damage_heavy",
                                              "ItemDamage.item_damage_twice"]
    report = reading.state(store, damage, conn)
    hole = next(h for h in report["holes"] if h["kind"] == "not_computed_yet")
    assert hole["blocking"] is False
    assert hole["refusal"]["code"] == "not_possible_yet"

    map_ = reading._map(store, damage, studio.open_draft(store, damage))
    planned = plan_for(map_, "ItemDamage")
    kinds = {c["name"]: (c["kind"], c.get("awaiting", {}).get("code"))
             for c in planned["columns"]}
    assert kinds == {"item_damage_item": ("key", None),
                     "item_damage_units": ("aggregate", None),
                     "item_damage_heavy": ("aggregate", "not_possible_yet"),
                     "item_damage_twice": ("expression", "not_possible_yet")}
    # The rule stays readable as written: only its execution waits.
    [narrowing] = planned["aggregates"]["item_damage_heavy"]["where"]
    assert (narrowing["slot_name"], narrowing["compare"], narrowing["value"]) == (
        "damage_cost", "above", 100000)

    [table] = [t for t in check(store, damage, "draft", map_=map_)["tables"]
               if t["class"] == "ItemDamage"]
    assert table["holds"] is True
    assert sorted(table["awaiting"]) == ["item_damage_heavy", "item_damage_twice"]


def test_an_example_of_columns_not_computed_yet_is_pending_not_failed(
        store, conn, damage):
    results = {e["name"]: e for e in reading.state(store, damage, conn)["examples"]}
    # Every number it checks waits for the executor: pending, and no refusal.
    assert results["berat"]["pending"] is True
    assert results["berat"]["passed"] is False
    assert results["berat"]["refusals"] == []
    # The numbers that compute are checked as always; the rest wait beside them.
    assert results["rusak"]["passed"] is True, results["rusak"]
    assert results["rusak"]["pending"] is False
    checks = {c["column"]: c for c in results["rusak"]["checks"]}
    assert checks["item_damage_units"]["holds"] is True
    assert checks["item_damage_heavy"]["pending"] is True
    assert checks["item_damage_twice"]["pending"] is True


def test_an_awaiting_column_still_owes_an_example(store, conn, damage):
    step(store, damage, "remove_example", example="berat")
    step(store, damage, "unexpect", example="rusak", table="ItemDamage", row="tenda")
    step(store, damage, "expect", example="rusak", table="ItemDamage", row="tenda",
         values="item_damage_units=3, item_damage_twice=5")
    assert ("column_unchecked", "ItemDamage.item_damage_heavy") in _blocking(
        store, conn, damage)
    step(store, damage, "expect", example="rusak", table="ItemDamage", row="tenda",
         values="item_damage_heavy=2")
    step(store, damage, "agree_example", example="rusak")
    assert _blocking(store, conn, damage) == []


def test_a_meaning_refusal_still_stops_the_seal(store, conn, damage):
    step(store, damage, "aggregate", **{
        "class": "ItemDamage", "column": "item_damage_heavy", "over": "DamageLine",
        "sum": "damage_quantity", "by": "item_damage_item=damage_item",
        "where": "damage_price>100000"})
    assert ("no_such_slot", "ItemDamage.item_damage_heavy: where.damage_price") in \
        _blocking(store, conn, damage)
    with pytest.raises(Refusal) as caught:
        seal(conn, studio.path(store, damage), actor_id="dev",
             into=store.directory(damage), store=store)
    assert caught.value.code == "no_such_slot"
    step(store, damage, "aggregate", **{
        "class": "ItemDamage", "column": "item_damage_heavy", "over": "DamageLine",
        "sum": "damage_quantity", "by": "item_damage_item=damage_item",
        "where": "damage_cost>100000"})
    assert _blocking(store, conn, damage) == []


def test_only_capability_refusals_wait_for_an_executor():
    # Section 11.1 as confirmed: everything else is the graph being wrong.
    assert compiler.AWAITING == {"multivalued_not_read", "not_possible_yet"}


# ---- sealed, installed, catalogued ------------------------------------------

def test_the_module_seals_and_its_columns_show_empty_and_labelled(store, conn, damage):
    out = seal(conn, studio.path(store, damage), actor_id="dev",
               into=store.directory(damage), store=store)
    assert out["version"] == "v1"
    sealed = store.document(damage, "v1")
    assert sealed["slots"]["item_damage_heavy"]["annotations"]["aggregate"]["value"][
        "where"] == {"damage_cost": {"above": 100000}}

    map_ = reading._map(store, damage, sealed)
    held = examples.load(store.directory(damage) / "v1.examples.yaml")["rusak"]
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn.transaction():
            examples._scratch(conn)
            examples._state(conn, map_, "rusak", held.get("records") or [])
            projection = app_api.projection(conn, store, damage, "v1", "ItemDamage",
                                            valid_at="2026-10-07", as_of=now)
            tenda = projection["rows"][0][0]
            cell = app_api.cell(conn, store, damage, "v1", "ItemDamage",
                                "item_damage_heavy", {"item_damage_item": tenda},
                                valid_at="2026-10-07", as_of=now)
            raise psycopg.Rollback()
    finally:
        examples._gone(conn)

    columns = {c["name"]: c for c in projection["columns"]}
    assert columns["item_damage_heavy"]["awaiting"]["code"] == "not_possible_yet"
    assert columns["item_damage_heavy"]["rule"]["kind"] == "aggregate"
    assert columns["item_damage_units"].get("awaiting") is None
    [row] = [dict(zip(columns, r)) for r in projection["rows"]]
    assert row["item_damage_units"] == 3
    assert row["item_damage_heavy"] is None and row["item_damage_twice"] is None
    # A cell not computed yet stands on nothing, and says so.
    assert cell["awaiting"]["code"] == "not_possible_yet"
    assert cell["statements"] == []

    rules = {r["rule"]: r for r in cat.readers(map_)[0]}
    assert rules["ItemDamage.item_damage_heavy"]["awaiting"] is True
    assert rules["ItemDamage.item_damage_units"]["awaiting"] is False

    drawn = modules_read.class_graph(store, damage, "v1")
    edges = {e["label"]: e for e in drawn["edges"] if e["kind"] == "aggregate"}
    assert edges["item_damage_heavy"]["awaiting"] is True
    assert edges["item_damage_units"]["awaiting"] is False


# ---- a key further away, a slot holding several -----------------------------

def test_a_key_two_records_away_waits_and_a_wrong_hop_is_still_refused(store, damage):
    map_ = reading._map(store, damage, store.document(damage, "v1"))

    def read(by):
        return _read_aggregate(map_, "ItemDamage.item_damage_units", {
            "over": "DamageLine", "sum": "damage_quantity", "by": {"item_damage_item": by}})

    def refused(by):
        with pytest.raises(CompileError) as caught:
            read(by)
        return caught.value.code

    # One record away is computed today; two is sound, and waits.
    assert read("damage_note.note_item")["awaits"] == []
    [waits] = read("damage_note.note_item.item_name")["awaits"]
    assert waits["code"] == "not_possible_yet"
    assert waits["where"] == "ItemDamage.item_damage_units: by"
    # Every hop is held to what one hop is: a slot there, pointing at a record.
    assert refused("damage_note.note_thing.item_name") == "no_such_slot"
    assert refused("damage_note.note_number.item_name") == "not_a_reference"
    assert refused("damage_note.note_item.item_colour") == "no_such_slot"


def test_a_slot_holding_several_values_seals_and_its_column_waits(store, conn):
    name = TAGS
    step(store, name, "start", title="Labels", description="Things with labels.")
    step(store, name, "pin", module="@uniti/item@v1")
    step(store, name, "add_class", **{"class": "Tagged", "description": "Tagged."})
    step(store, name, "fill_role", **{"class": "Tagged", "role": "Thing"})
    for slot, said in (("tagged_code", "Its code."), ("tagged_label", "A label it has.")):
        step(store, name, "add_slot", slot=slot, description=said)
        step(store, name, "attach", **{"class": "Tagged", "slot": slot})
    step(store, name, "set_slot", slot="tagged_code", field="identifier", value="true")
    step(store, name, "set_slot", slot="tagged_label", field="multivalued", value="true")

    assert _blocking(store, conn, name) == []
    assert _awaiting(store, conn, name) == ["Tagged.tagged_label"]
    out = seal(conn, studio.path(store, name), actor_id="dev",
               into=store.directory(name), store=store)
    assert out["version"] == "v1"

    map_ = reading._map(store, name, store.document(name, "v1"))
    planned = plan_for(map_, "Tagged")
    awaiting = {c["name"]: c.get("awaiting", {}).get("code") for c in planned["columns"]}
    assert awaiting["tagged_label"] == "multivalued_not_read"
    assert awaiting["tagged_code"] is None
    # The rest of the table is read as always; the column waiting is empty.
    built = compiler.preview(conn, map_, "Tagged", valid_at=datetime.now(timezone.utc),
                             as_of=datetime.now(timezone.utc))
    assert 'NULL::text AS "tagged_label"' in built["select"]
    assert '"tagged_code"' in built["select"].split("FROM source_0")[0]

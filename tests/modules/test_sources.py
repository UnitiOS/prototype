"""One rule, several sources (ECOSYSTEM_PLAN.md, step 5; story 6).

A business that moves from one till to another holds its numbers in two
modules at once: units out are the rental lines of Rudi's module plus the
booking lines of the till's. Before, that was three columns — one total per
module and an expression adding them, written three times over for every
number of the stock table. Now one column says it, once:

    one column      `aggregate` writes the first source and `add_source` each
                    next one; the column is the total over every source, and
                    its numbers are the three columns' numbers
    guarded         every source totals in the same unit and runs the same
                    way, and groups by the same keys
    taken apart     what a combined cell stands on is the statements of every
                    source, each read back to its own module
    kept whole      a renamed slot is renamed in every source; the sealed
                    rule keeps every source under the names it composed
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
from components.business import declare  # noqa: E402
from components.examples import examples  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from compile import plan_for  # noqa: E402
from perform import connect  # noqa: E402
from seal import register, seal  # noqa: E402

BUSINESS = "demo"
REGISTERED = [("@uniti/core", "v1"), ("@uniti/core", "v2"), ("@uniti/item", "v1")]
RUDI, TILL, APP = "@rudi/sewa", "@lain/kasir", "@demo/gudang"
OLD, NEW = "rudi_sewa", "lain_kasir"
CLASS = {"rental_line": "RentalLine", "booking_item": "BookingItem"}


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
    declare(conn, BUSINESS, actor_id="dev")
    return held


def step(store, name, op, **args):
    return studio.apply(store, name, op, args)


def refused(store, name, op, **args):
    with pytest.raises(Refusal) as caught:
        step(store, name, op, **args)
    return caught.value


def _lines(store, conn, name, line, out, stem, total):
    """A module whose lines take items out, and its own count of them: the
    same shape each author would build, under names of their own."""
    step(store, name, "start", title=line,
         description="Items going out to customers, line by line.")
    step(store, name, "pin", module="@uniti/item@v1")
    step(store, name, "add_class", **{"class": line, "description": "One item going out."})
    step(store, name, "add_class", **{"class": out, "description": "Units out per item."})
    step(store, name, "fill_role", **{"class": line, "role": "Thing"})
    for class_name, slot, kind, said, meant in (
        (line, f"{stem}_number", "string", "The number on the note.", {}),
        (line, f"{stem}_item", "Item", "The item going out.", {}),
        (line, f"{stem}_quantity", "integer", "How many went out.",
         {"unit": "unit", "direction": "decrease"}),
        (line, f"{stem}_back", "integer", "How many came back.",
         {"unit": "unit", "direction": "increase"}),
        (line, f"{stem}_deposit", "decimal", "Money left against it.",
         {"unit": "IDR", "direction": "increase"}),
        (out, f"{total}_item", "Item", "The item.", {}),
        (out, f"{total}_units", "integer", "Units gone out.",
         {"unit": "unit", "direction": "level"}),
    ):
        step(store, name, "add_slot", slot=slot, range=kind, description=said, **meant)
        step(store, name, "attach", **{"class": class_name, "slot": slot})
    step(store, name, "set_slot", slot=f"{stem}_number", field="identifier", value="true")
    step(store, name, "aggregate", **{
        "class": out, "column": f"{total}_units", "over": line,
        "sum": f"{stem}_quantity", "by": f"{total}_item={stem}_item"})
    step(store, name, "add_example", example="tenda", says="Two tents go out.")
    step(store, name, "record", example="tenda", record="tenda", **{"class": "Item"},
         facts="item_name=Tenda")
    step(store, name, "record", example="tenda", record="l1", **{"class": line},
         when="2026-10-06", facts=f"{stem}_number=L1, {stem}_item=tenda, "
                                  f"{stem}_quantity=2, {stem}_back=0, {stem}_deposit=0")
    step(store, name, "expect", example="tenda", table=out, row="tenda",
         values=f"{total}_units=2")
    step(store, name, "agree_example", example="tenda")
    seal(conn, studio.path(store, name), actor_id="dev",
         into=store.directory(name), store=store)
    return name


@pytest.fixture(scope="module")
def modules(store, conn):
    """Rudi's rental lines and the till's booking lines, sealed apart."""
    return (_lines(store, conn, RUDI, "RentalLine", "RentalOut", "rental_line", "rental_out"),
            _lines(store, conn, TILL, "BookingItem", "BookedOut", "booking_item", "booked_out"))


@pytest.fixture(scope="module")
def application(store, conn, modules):
    """The stock table as the two-round test's v4 wrote it — a total per module
    and an expression adding them — beside the one column that says it once."""
    step(store, APP, "start", title="Stock", kind="application", business=BUSINESS,
         description="Units out per item, under the old module and the new till.")
    step(store, APP, "pin", module=f"{RUDI}@v1")
    step(store, APP, "pin", module=f"{TILL}@v1")
    step(store, APP, "add_class", **{"class": "ItemOut",
                                     "description": "Units out per item, both modules."})
    for slot, kind, said, meant in (
        ("item_out_item", "Item", "The item.", {}),
        ("item_out_old", "integer", "Units out on the old module.",
         {"unit": "unit", "direction": "level"}),
        ("item_out_new", "integer", "Units out at the new till.",
         {"unit": "unit", "direction": "level"}),
        ("item_out_total", "integer", "Units out, the two added.",
         {"unit": "unit", "direction": "level"}),
        ("item_out_units", "integer", "Units out, one rule.",
         {"unit": "unit", "direction": "level"}),
    ):
        step(store, APP, "add_slot", slot=slot, range=kind, description=said, **meant)
        step(store, APP, "attach", **{"class": "ItemOut", "slot": slot})
    for column, tag, line in (("item_out_old", OLD, "rental_line"),
                              ("item_out_new", NEW, "booking_item")):
        step(store, APP, "aggregate", **_source(column, tag, line))
    step(store, APP, "expression", **{"class": "ItemOut", "column": "item_out_total",
                                      "expression": "{item_out_old} + {item_out_new}"})
    return APP


def _source(column, tag, line, measure="quantity", key="item_out_item", by="item"):
    return {"class": "ItemOut", "column": column,
            "over": f"{tag}__{CLASS[line]}", "sum": f"{tag}__{line}_{measure}",
            "by": f"{key}={tag}__{line}_{by}"}


def _example(store):
    """Tents go out under both modules, stoves only at the new till."""
    step(store, APP, "add_example", example="week",
         says="Two tents go out on the old notes, one tent and two stoves at the new till.")
    for record, said in (("tenda", "Tenda"), ("kompor", "Kompor")):
        step(store, APP, "record", example="week", record=record, **{"class": "Item"},
             facts=f"item_name={said}")
    for record, tag, line, item, quantity in (
        ("r1", OLD, "rental_line", "tenda", 2),
        ("b1", NEW, "booking_item", "tenda", 1),
        ("b2", NEW, "booking_item", "kompor", 2),
    ):
        step(store, APP, "record", example="week", record=record,
             **{"class": f"{tag}__{CLASS[line]}"}, when="2026-10-06",
             facts=f"{line}_number={record.upper()}, {line}_item={item}, "
                   f"{line}_quantity={quantity}, {line}_back=0, {line}_deposit=0")
    step(store, APP, "expect", example="week", table="ItemOut", row="tenda",
         values="item_out_old=2, item_out_new=1, item_out_total=3, item_out_units=3")
    step(store, APP, "expect", example="week", table="ItemOut", row="kompor",
         values="item_out_old=0, item_out_new=2, item_out_total=2, item_out_units=2")
    step(store, APP, "agree_example", example="week")


def _holes(store, conn):
    return [(h["kind"], h["where"]) for h in reading.state(store, APP, conn)["holes"]
            if h["blocking"]]


# ---- one column ------------------------------------------------------------

def test_a_source_is_added_to_a_column_that_has_an_aggregate(store, application):
    caught = refused(store, APP, "add_source",
                     **_source("item_out_units", NEW, "booking_item"))
    assert caught.code == "no_aggregate"
    assert "aggregate" in caught.repairs[0].options

    step(store, APP, "aggregate", **_source("item_out_units", OLD, "rental_line"))
    step(store, APP, "add_source", **_source("item_out_units", NEW, "booking_item"))
    body = studio.open_draft(store, APP)["slots"]["item_out_units"]
    spec = body["annotations"]["aggregate"]["value"]
    assert set(spec) == {"sources"}
    assert [s["over"] for s in spec["sources"]] == [f"{OLD}__RentalLine",
                                                    f"{NEW}__BookingItem"]
    assert spec["sources"][1] == {"over": f"{NEW}__BookingItem",
                                  "sum": f"{NEW}__booking_item_quantity",
                                  "by": {"item_out_item": f"{NEW}__booking_item_item"}}
    # A plain aggregate keeps the shape every sealed version already has.
    plain = studio.open_draft(store, APP)["slots"]["item_out_old"]
    assert "sources" not in plain["annotations"]["aggregate"]["value"]


def test_one_column_gives_the_numbers_three_columns_gave(store, conn, application):
    _example(store)
    assert _holes(store, conn) == []
    [example] = reading.state(store, APP, conn)["examples"]
    assert example["passed"] is True, example

    map_ = reading._map(store, APP, studio.open_draft(store, APP))
    spec = plan_for(map_, "ItemOut")["aggregates"]["item_out_units"]
    assert [s["over"] for s in spec["sources"]] == [f"{OLD}__RentalLine",
                                                    f"{NEW}__BookingItem"]
    # A single source is a list of one, so a reader walks every rule alike.
    assert len(plan_for(map_, "ItemOut")["aggregates"]["item_out_old"]["sources"]) == 1


def test_sources_must_total_in_one_unit_and_run_one_way(store, conn, application):
    for measure, said in (("back", "direction"), ("deposit", "unit")):
        step(store, APP, "aggregate", **_source("item_out_units", OLD, "rental_line"))
        step(store, APP, "add_source",
             **_source("item_out_units", NEW, "booking_item", measure=measure))
        assert ("sources_disagree", "ItemOut.item_out_units") in _holes(store, conn), said
        state = reading.state(store, APP, conn)
        hole = next(h for h in state["holes"] if h["kind"] == "sources_disagree")
        assert said in hole["refusal"]["expected"]
    step(store, APP, "aggregate", **_source("item_out_units", OLD, "rental_line"))
    step(store, APP, "add_source", **_source("item_out_units", NEW, "booking_item"))
    assert _holes(store, conn) == []


def test_sources_must_group_by_the_same_keys(store, conn, application):
    step(store, APP, "add_source", **_source(
        "item_out_units", NEW, "booking_item", key="item_out_total"))
    assert ("groupings_disagree", "ItemOut.item_out_units") in _holes(store, conn)
    step(store, APP, "aggregate", **_source("item_out_units", OLD, "rental_line"))
    step(store, APP, "add_source", **_source("item_out_units", NEW, "booking_item"))
    assert _holes(store, conn) == []


def test_a_renamed_slot_is_renamed_in_every_source(store, conn, application):
    step(store, APP, "rename_slot", slot="item_out_item", to="item_out_thing")
    spec = studio.open_draft(store, APP)["slots"]["item_out_units"]["annotations"][
        "aggregate"]["value"]
    assert [list(s["by"]) for s in spec["sources"]] == [["item_out_thing"]] * 2
    step(store, APP, "rename_slot", slot="item_out_thing", to="item_out_item")
    assert _holes(store, conn) == []


# ---- sealed, and taken apart ----------------------------------------------

def test_the_combined_column_seals_and_a_cell_stands_on_both_modules(
        store, conn, application):
    report = reading.state(store, APP, conn)
    assert [example["passed"] for example in report["examples"]] == [True]
    out = seal(conn, studio.path(store, APP), actor_id="dev",
               into=store.directory(APP), store=store)
    assert out["version"] == "v1"
    sealed = store.document(APP, "v1")
    spec = sealed["slots"]["item_out_units"]["annotations"]["aggregate"]["value"]
    assert [s["over"] for s in spec["sources"]] == [f"{OLD}__RentalLine",
                                                    f"{NEW}__BookingItem"]

    map_ = reading._map(store, APP, sealed)
    week = examples.load(store.directory(APP) / "v1.examples.yaml")["week"]
    now = datetime.now(timezone.utc).isoformat()
    try:
        with conn.transaction():
            examples._scratch(conn)
            examples._state(conn, map_, "week", week.get("records") or [])
            projection = app_api.projection(conn, store, APP, "v1", "ItemOut",
                                            valid_at="2026-10-07", as_of=now)
            names = [c["name"] for c in projection["columns"]]
            rows = [dict(zip(names, row)) for row in projection["rows"]]
            tenda = next(r["item_out_item"] for r in rows if r["item_out_units"] == 3)
            cell = app_api.cell(conn, store, APP, "v1", "ItemOut", "item_out_units",
                                {"item_out_item": tenda},
                                valid_at="2026-10-07", as_of=now)
            raise psycopg.Rollback()
    finally:
        examples._gone(conn)

    # The same numbers the three columns give, row by row.
    assert all(r["item_out_units"] == r["item_out_total"] for r in rows)
    assert sorted(r["item_out_units"] for r in rows) == [2, 3]
    rule = next(c for c in projection["columns"] if c["name"] == "item_out_units")["rule"]
    assert [s["over"] for s in rule["sources"]] == [f"{OLD}__RentalLine",
                                                    f"{NEW}__BookingItem"]
    # Both modules' lines, the one total they make: 2 on the old notes, 1 new.
    assert sorted(int(s["value"]) for s in cell["statements"]) == [1, 2]
    assert cell["sources"] == [f"{OLD}__RentalLine", f"{NEW}__BookingItem"]


"""The catalogue and the graph's health: computed from what was sealed, never written.

Two reads, and neither is maintained by anybody.

The catalogue is what the store offers: modules, roles, classes and slots, who
fills which role, and which rules anywhere read what. It is asked, not loaded —
by text, by kind, by the role an entry fills, by who declares it, by who pins
it.

The health report is six things about one application that are not refusals:
nothing stops, and something is doing nothing. The claim this slice rests on is
that the first of them turns up on its own:

    inv:movement_happened_on is stated for every movement, fills core's
    `moment`, and no rule anywhere reads it.

Nobody wrote that down. No fixture, no test, no code names it as dead; it is
found by comparing what the log holds with what the rules read.

Counts are asked to be there, not to be a particular number: the test log is
shared by every module of this run, and earlier ones load the same facts and
submit forms of their own.
"""

import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

import dev_modules  # noqa: E402
import load_facts  # noqa: E402
from components.modules.catalogue import catalogue, find  # noqa: E402
from components.modules.health import DIAGNOSES, health  # noqa: E402
from components.modules.store import MANIFEST  # noqa: E402
from perform import connect  # noqa: E402
from seal import seal  # noqa: E402

CATALOG, INVENTORY, STOCK = dev_modules.CATALOG, dev_modules.INVENTORY, dev_modules.STOCK
RIVAL, CORE = dev_modules.RIVAL, dev_modules.CORE
APP_NAME, APP_VERSION = dev_modules.APPLICATION
SWAP_NAME, SWAP_VERSION = dev_modules.SWAPPED
PROBE = "@probe/health"
# The business the demonstration log belongs to: its catalogue shows its own
# application beside everything shared.
BUSINESS = dev_modules.BUSINESS


@pytest.fixture(scope="module")
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn


@pytest.fixture(scope="module")
def world(conn, tmp_path_factory):
    """The demonstration store, both sets of facts, and one probe module.

    The probe is written to have one of each of the three diagnoses the
    demonstration content happens not to: a class nothing is ever stated to be,
    a role nothing fills, and a column no rule reaches.

    The demonstration is committed, because the API reads it through a
    connection of its own. The probe is not: sealing it writes to the log every
    later test shares, so it is seen only through this connection and rolled
    back when the module is done.
    """
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    for data in ("demo_data.yaml", "rival_data.yaml"):
        load_facts.load(conn, yaml.safe_load((dev_modules.FIXTURES / data)
                                             .read_text(encoding="utf-8")),
                        store, actor_id="test")
    conn.commit()

    directory = store.roots[0] / PROBE
    directory.mkdir(parents=True)
    (directory / MANIFEST).write_text(
        yaml.safe_dump({"name": PROBE, "title": "Probe", "purpose": "demonstration"}),
        encoding="utf-8")
    drafts = tmp_path_factory.mktemp("probe")
    draft = {
        "id": "https://probe.example/health",
        "name": "probe_health",
        "title": "Probe",
        "description": "A module written for one test.",
        "prefixes": {"linkml": "https://w3id.org/linkml/", "pb": "https://probe.example/"},
        "default_prefix": "pb",
        "default_range": "string",
        "imports": ["linkml:types", f"{CORE}@v2"],
        "classes": {
            "Keeper": {"abstract": True, "mixin": True, "is_a": "Thing",
                       "description": "A role nothing here fills."},
            "Widget": {"mixins": ["Thing"], "slots": ["widget_ref", "widget_weight"],
                       "description": "A thing that is weighed."},
            "Tally": {"slots": ["tally_widget", "tally_weight", "tally_note"],
                      "description": "The weight of each widget, added up."},
        },
        "slots": {
            "widget_ref": {"slot_uri": "pb:widget_ref", "identifier": True,
                           "description": "The code a widget is known by."},
            "widget_weight": {"slot_uri": "pb:widget_weight", "range": "decimal",
                              "description": "How much the widget weighs.",
                              "unit": {"symbol": "kg"},
                              "annotations": {"direction": "level"}},
            "tally_widget": {"slot_uri": "pb:tally_widget",
                             "description": "The widget this row is about."},
            "tally_weight": {
                "slot_uri": "pb:tally_weight", "range": "decimal",
                "description": "Every weight of the widget, added up.",
                "unit": {"symbol": "kg"},
                "annotations": {"direction": "level", "aggregate": {"value": {
                    "over": "Widget", "sum": "widget_weight",
                    "by": {"tally_widget": "widget_ref"}}}}},
            "tally_note": {"slot_uri": "pb:tally_note",
                           "description": "Anything said about the tally."},
        },
        "annotations": {"valid_from": "2026-09-01T00:00:00+00:00",
                        "transcript": "probe.txt"},
    }
    path = drafts / "draft.yaml"
    path.write_text(yaml.safe_dump(draft, sort_keys=False), encoding="utf-8")
    (drafts / "probe.txt").write_text("probe", encoding="utf-8")
    # The tally is computed, and a computed column owes a number to an example.
    (drafts / "draft.examples.yaml").write_text(yaml.safe_dump({"examples": {
        "one_widget": {
            "says": "One widget weighing 2.",
            "records": [{"record": "w1", "class": "Widget",
                         "facts": {"widget_ref": "W1", "widget_weight": 2}}],
            "expect": [{"table": "Tally", "row": "W1",
                        "values": {"tally_weight": 2}}],
        }}}, sort_keys=False), encoding="utf-8")
    seal(conn, path, actor_id="probe", into=directory, store=store)

    yield store
    conn.rollback()


def _diagnosis(report, code):
    return next(d for d in report["diagnoses"] if d["code"] == code)["findings"]


def _term(report, uri):
    return next(t for t in report["terms"] if t["uri"] == uri)


# ---- the claim -----------------------------------------------------------

def test_a_term_stated_and_never_read_is_found_without_anyone_naming_it(conn, world):
    report = health(world, APP_NAME, APP_VERSION, conn=conn)
    dead = _diagnosis(report, "dead_term")
    uris = [f["uri"] for f in dead]

    assert "https://uniti.example/inventory/movement_happened_on" in uris
    finding = dead[uris.index("https://uniti.example/inventory/movement_happened_on")]
    assert finding["fills"] == "moment"
    assert finding["on"] == ["StockMovement"]
    assert finding["module"] == {"name": INVENTORY, "version": "v3"}
    # Stated for the movements, like the quantity beside it — which is read.
    quantity = _term(report, "https://uniti.example/inventory/movement_quantity")
    assert finding["held"] > 0 and quantity["held"] > 0
    assert [r["rule"] for r in quantity["read_by"]] == ["IngredientStock.quantity_on_hand"]
    # A term that fills a binding was put there to be computed on, so it comes
    # before the ones that were only ever meant to be read by a person.
    assert all(f["fills"] for f in dead[:uris.index("https://uniti.example/inventory/movement_happened_on") + 1])
    assert "`moment`" in finding["sentence"]


def test_a_term_read_only_by_a_mechanism_is_not_dead(conn, world):
    """The generator names subjects by their identifier; that is a reader."""
    report = health(world, APP_NAME, APP_VERSION, conn=conn)
    dead = {f["uri"] for f in _diagnosis(report, "dead_term")}

    code = _term(report, "https://uniti.example/inventory/movement_code")
    assert {(r["kind"], r["reader"]) for r in code["read_by"]} == {
        ("identifier", "the generator")}
    kind = _term(report, "https://w3id.org/uniti/core#entity_class")
    assert {r["kind"] for r in kind["read_by"]} >= {"type", "aggregate"}
    assert not {"https://uniti.example/inventory/movement_code", "https://w3id.org/uniti/core#entity_class"} & dead


def test_after_the_swap_the_same_term_is_a_fact_the_application_cannot_see(conn, world):
    """After the swap the log still holds it, and the report says whose it is."""
    report = health(world, SWAP_NAME, SWAP_VERSION, conn=conn)
    orphaned = {f["uri"]: f for f in _diagnosis(report, "orphaned_fact")}

    finding = orphaned["https://uniti.example/inventory/movement_happened_on"]
    assert finding["declared_by"] == [{"name": INVENTORY,
                                       "versions": ["v1", "v2", "v3", "v4"]}]
    assert finding["held"] > 0
    assert "does not pin it" in finding["sentence"]
    # The rival's own moment is dead there for the same reason: nothing reads it.
    dead = {f["uri"]: f for f in _diagnosis(report, "dead_term")}
    assert dead["https://rival.example/stock-moves/happened"]["fills"] == "moment"


def test_an_old_application_is_told_what_the_store_has_moved_past(conn, world):
    lagging = _diagnosis(health(world, APP_NAME, "v1", conn=conn), "lagging_pin")
    assert {(f["module"], f["pinned"], f["latest"]) for f in lagging} == {
        (CORE, "v1", "v2"), (CATALOG, "v2", "v4"), (INVENTORY, "v2", "v4")}
    inventory = next(f for f in lagging if f["module"] == INVENTORY)
    assert inventory["newer"] == ["v3", "v4"]
    assert {"name": APP_NAME, "version": "v1"} in inventory["pinned_by"]

    # The current application lags only the versions that brought its modules
    # to the recording standard.
    lagging = _diagnosis(health(world, APP_NAME, APP_VERSION, conn=conn), "lagging_pin")
    assert {(f["module"], f["pinned"], f["latest"]) for f in lagging} == {
        (CATALOG, "v3", "v4"), (INVENTORY, "v3", "v4")}


def test_the_three_the_demonstration_does_not_have_are_found_in_a_probe(conn, world):
    report = health(world, PROBE, "v1", conn=conn)
    assert report["refusals"] == []

    assert _diagnosis(report, "empty_column") == [{
        "class": "Tally", "column": "tally_note",
        "sentence": "Tally.tally_note is reached by no rule"}]

    empty = {f["class"]: f for f in _diagnosis(report, "empty_class")}
    assert set(empty) == {"Widget"}
    assert empty["Widget"]["read_by"] == ["Tally.tally_weight"]

    # Its own role, and core's three it can see and has no class for: a widget
    # is a Thing and nothing else.
    unfilled = {f["role"]: f for f in _diagnosis(report, "unfilled_role")}
    assert set(unfilled) == {"Keeper", "Event", "Flow", "Resource"}
    assert unfilled["Keeper"]["candidates"] == ["Widget"]
    assert unfilled["Flow"]["bindings"] == ["amount", "affects", "moment"]

    # Nothing has been stated about a widget, so nothing of the probe's is dead:
    # a term the log does not hold is unused, not dead.
    assert _diagnosis(report, "dead_term") == []


def test_without_a_log_nothing_counted_is_reported_as_empty(world):
    report = health(world, APP_NAME, "v1", conn=None)
    assert report["counted"] is False
    for code in ("dead_term", "empty_class", "orphaned_fact"):
        assert _diagnosis(report, code) is None
    assert len(_diagnosis(report, "lagging_pin")) == 3
    assert [d["code"] for d in report["diagnoses"]] == list(DIAGNOSES)


# ---- the catalogue -------------------------------------------------------

def test_the_catalogue_says_who_fills_a_role_across_the_store(world):
    entries = catalogue(world, business=BUSINESS)
    found = find(entries, fills="Flow")
    assert {(e["kind"], e["name"], e["module"]["name"]) for e in found["entries"]} == {
        ("class", "StockMovement", INVENTORY), ("class", "Movement", RIVAL)}

    flow = find(entries, kind="role", text="flow")["entries"]
    flow = next(e for e in flow if e["name"] == "Flow")
    assert {f["class"] for f in flow["filled_by"]} == {"StockMovement", "Movement"}
    assert {(r["module"]["version"], r["rule"]) for r in flow["read_by"]} == {
        ("v2", "IngredientStock.quantity_on_hand"),
        ("v3", "IngredientStock.quantity_on_hand"),
        ("v4", "IngredientStock.stock_quantity_on_hand")}


def test_the_catalogue_says_nothing_anywhere_reads_a_binding(world):
    """Across every sealed version, not only one application."""
    found = find(catalogue(world, business=BUSINESS), kind="slot", fills="moment")["entries"]
    assert {(e["name"], e["module"]["name"]) for e in found} == {
        ("movement_happened_on", INVENTORY), ("move_happened_on", RIVAL)}
    assert all(e["read_by"] == [] for e in found)

    amount = find(catalogue(world, business=BUSINESS), kind="slot", fills="amount")["entries"]
    assert all(e["read_by"] for e in amount)


def test_an_application_is_in_its_own_business_s_catalogue_only(world):
    """One business's application is private: another business's catalogue,
    and one asked for no business, holds the modules and not the application,
    nor the rules it wrote."""
    own = catalogue(world, business=BUSINESS)
    assert STOCK in {e["name"] for e in find(own, kind="module")["entries"]}
    assert next(e for e in own if e["name"] == STOCK)["of_kind"] == "application"
    for other in (catalogue(world, business="another"), catalogue(world)):
        names = {e["name"] for e in find(other, kind="module")["entries"]}
        assert STOCK not in names and {CATALOG, INVENTORY, RIVAL} <= names
        flow = next(e for e in find(other, kind="role")["entries"] if e["name"] == "Flow")
        assert flow["read_by"] == []


def test_the_catalogue_is_asked_not_loaded(world):
    entries = catalogue(world, business=BUSINESS)
    assert {e["name"] for e in find(entries, pins=CATALOG)["entries"]} == {INVENTORY, STOCK}
    assert {e["kind"] for e in find(entries, module=CORE)["entries"]} == {"module", "role", "slot"}
    nothing = find(entries, text="no entry is called this")
    assert nothing["entries"] == [] and sum(nothing["counts"].values()) == 0
    assert nothing["held"]["module"] == len(world.names())
    slot = find(entries, text="https://uniti.example/inventory/movement_quantity")["entries"]
    assert [e["name"] for e in slot] == ["movement_quantity"]


def test_the_api_serves_both(conn, world, monkeypatch):
    from starlette.testclient import TestClient
    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    client = TestClient(app)

    found = client.get("/api/catalogue", params={"fills": "Flow"})
    assert found.status_code == 200
    assert found.json()["counts"]["class"] == 2
    assert client.get("/api/catalogue", params={"kind": "nothing"}).status_code == 400

    report = client.get("/api/app/health", params={"name": APP_NAME, "version": APP_VERSION})
    assert report.status_code == 200
    body = report.json()
    assert [d["code"] for d in body["diagnoses"]] == list(DIAGNOSES)
    assert "https://uniti.example/inventory/movement_happened_on" in {f["uri"] for f in body["diagnoses"][0]["findings"]}

    missing = client.get("/api/app/health", params={"name": "@nobody/nothing", "version": "v1"})
    assert missing.status_code == 404
    assert missing.json()["refusal"]["code"] == "no_such_module"

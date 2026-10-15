"""A module adds facts to another module's thing (ECOSYSTEM_PLAN.md, step 2).

Rudi says "items get a rate per day". The item is the library's, and stays
the library's: `@uniti/item` is never touched and no second record exists.
Rudi's module declares the slot, `rental_rate`, and attaches it to `Item` —
a facet. Whoever pins Rudi's module sees `Item` carry it; nobody else does.
What has to hold, and is asserted here:

    one thing       one entity "Tent" carries the library's `item_name` and
                    Rudi's `rental_rate`, each under its own module's predicate
    in sight        only in a composition that pins the facet's module
    read by rules   a `parameter` reads the facet like any column, and the
                    application's example and seal hold
    on screen       the item form carries the field under Rudi's module's
                    title; the studio does not call the facet module empty
                    or its slot loose, and its map draws the facet on `Item`
    refused         a facet that obliges (required, identifier, type), one on
                    a role, one slot in two places
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from components.api import application as app_api  # noqa: E402
from components.business import declare  # noqa: E402
from components.modules import read as modules_read  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from generate import form, read_map, submit, table  # noqa: E402
from perform import connect  # noqa: E402
from seal import predicate, register, seal  # noqa: E402

BUSINESS = "demo"
REGISTERED = [("@uniti/core", "v1"), ("@uniti/core", "v2"),
              ("@uniti/party", "v1"), ("@uniti/item", "v1"), ("@uniti/item", "v2")]
TARIF, APP = "@rudi/tarif", "@demo/income"
RATE = "https://uniti.example/rudi/tarif/rental_rate"


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


def holes_of(store, name, conn=None):
    return reading.state(store, name, conn)["holes"]


@pytest.fixture(scope="module")
def tarif(store):
    """Rudi's rates, as a draft: one slot, on the library's `Item`."""
    step(store, TARIF, "start", title="Rental rates",
         description="What one day of renting an item costs.")
    step(store, TARIF, "pin", module="@uniti/item@v2")
    step(store, TARIF, "add_slot", slot="rental_rate", range="decimal",
         description="What one day of renting this item costs.",
         unit="IDR", direction="level")
    return TARIF


@pytest.fixture(scope="module")
def sealed(store, conn, tarif):
    step(store, TARIF, "attach", **{"class": "Item", "slot": "rental_rate"})
    seal(conn, studio.path(store, TARIF), actor_id="rudi",
         into=store.directory(TARIF), store=store)
    return TARIF


@pytest.fixture(scope="module")
def application(store, conn, sealed):
    """Sari's income per item: days hired, from her own records, times
    Rudi's rate, read off the item."""
    step(store, APP, "start", title="Income", kind="application", business=BUSINESS,
         description="Rental income per item, at Rudi's rates.")
    step(store, APP, "pin", module="@uniti/item@v2")
    step(store, APP, "pin", module=f"{TARIF}@v1")
    step(store, APP, "add_class", **{"class": "Hire", "description": "One item out for days."})
    step(store, APP, "fill_role", **{"class": "Hire", "role": "Thing"})
    step(store, APP, "add_class", **{"class": "ItemIncome",
                                     "description": "Rental income per item."})
    for class_name, slot, kind, said, meant in (
        ("Hire", "hire_item", "Item", "The item hired.", {}),
        ("Hire", "hire_days", "integer", "Days it was out.",
         {"unit": "piece", "direction": "increase"}),
        ("ItemIncome", "income_item", "Item", "The item.", {}),
        ("ItemIncome", "income_days", "integer", "Item-days hired.",
         {"unit": "piece", "direction": "level"}),
        ("ItemIncome", "income_rate", "decimal", "Rate per day.",
         {"unit": "IDR", "direction": "level"}),
        ("ItemIncome", "income_total", "decimal", "Income.",
         {"unit": "IDR", "direction": "level"}),
    ):
        step(store, APP, "add_slot", slot=slot, range=kind, description=said, **meant)
        step(store, APP, "attach", **{"class": class_name, "slot": slot})
    step(store, APP, "aggregate", **{"class": "ItemIncome", "column": "income_days",
                                     "over": "Hire", "sum": "hire_days",
                                     "by": "income_item=hire_item"})
    # The facet is read by its plain name: one module in sight declares it.
    step(store, APP, "parameter", **{"class": "ItemIncome", "column": "income_rate",
                                     "of": "income_item", "slot": "rental_rate"})
    step(store, APP, "expression", **{"class": "ItemIncome", "column": "income_total",
                                      "expression": "{income_days} * {income_rate}"})
    step(store, APP, "add_example", example="tent",
         says="A tent goes out for two days; a tent costs 25000 a day.")
    step(store, APP, "record", example="tent", record="tent", **{"class": "Item"},
         facts="item_name=Tent, rental_rate=25000")
    step(store, APP, "record", example="tent", record="h1", **{"class": "Hire"},
         when="2026-10-06", facts="hire_item=tent, hire_days=2")
    step(store, APP, "expect", example="tent", table="ItemIncome", row="tent",
         values="income_days=2, income_rate=25000, income_total=50000")
    step(store, APP, "agree_example", example="tent")
    return APP


# ---- the facet module -------------------------------------------------------

def test_attaching_a_slot_to_another_modules_class_makes_a_facet(store, tarif):
    # Loose, it is asked about — and the answer offers the item as well as
    # the module's own classes, which it has none of.
    loose = [h for h in holes_of(store, TARIF) if h["kind"] == "slot_is_loose"]
    assert [h["where"] for h in loose] == ["rental_rate"]
    assert "Item" in loose[0]["step"]["options"]

    step(store, TARIF, "attach", **{"class": "Item", "slot": "rental_rate"})
    document = studio.open_draft(store, TARIF)
    assert document["slots"]["rental_rate"]["domain"] == "Item"
    assert "classes" not in document

    kinds = {h["kind"] for h in holes_of(store, TARIF)}
    assert "slot_is_loose" not in kinds
    assert "nothing_declared" not in kinds

    # The draft's own composition carries it on the item; the library's
    # own reading never does.
    classes, _ = studio.seen(store, document)
    assert classes["Item"]["slots"] == ["item_name", "rental_rate"]
    assert store.document("@uniti/item", "v2")["classes"]["Item"]["slots"] == ["item_name"]

    # Taken back off, it is loose again.
    step(store, TARIF, "detach", **{"class": "Item", "slot": "rental_rate"})
    assert "domain" not in studio.open_draft(store, TARIF)["slots"]["rental_rate"]
    assert "slot_is_loose" in {h["kind"] for h in holes_of(store, TARIF)}


def test_the_studio_shows_the_facet_on_the_thing_it_adds_to(store, tarif):
    step(store, TARIF, "attach", **{"class": "Item", "slot": "rental_rate"})
    state = reading.state(store, TARIF)
    [slot] = state["slots"]
    assert slot["adds_to"] == "Item"
    assert slot["on"] == []
    item = {b["name"]: b for b in state["borrowed"]}["Item"]
    assert [s["name"] for s in item["slots"]] == ["item_name", "rental_rate"]
    step(store, TARIF, "detach", **{"class": "Item", "slot": "rental_rate"})


def test_a_facet_obliges_nothing_of_the_thing(store, tarif):
    step(store, TARIF, "attach", **{"class": "Item", "slot": "rental_rate"})
    for field in ("required", "identifier", "designates_type"):
        caught = refused(store, TARIF, "set_slot", slot="rental_rate",
                         field=field, value="true")
        assert caught.code == "facet_obliges", field
    assert "required" not in studio.open_draft(store, TARIF)["slots"]["rental_rate"]
    step(store, TARIF, "detach", **{"class": "Item", "slot": "rental_rate"})

    # Nor is a slot that already obliges made one.
    step(store, TARIF, "set_slot", slot="rental_rate", field="required", value="true")
    caught = refused(store, TARIF, "attach", **{"class": "Item", "slot": "rental_rate"})
    assert caught.code == "facet_obliges"
    step(store, TARIF, "set_slot", slot="rental_rate", field="required", value="false")


def test_a_facet_is_on_a_thing_and_in_one_place(store, tarif):
    # A role has no records of its own to carry a fact.
    caught = refused(store, TARIF, "attach", **{"class": "Resource", "slot": "rental_rate"})
    assert caught.code == "facet_on_role"

    step(store, TARIF, "attach", **{"class": "Item", "slot": "rental_rate"})
    # One slot, one place: not on a class of the module's own as well, and
    # not on a second thing.
    step(store, TARIF, "add_class", **{"class": "RateCard", "description": "A card."})
    caught = refused(store, TARIF, "attach", **{"class": "RateCard", "slot": "rental_rate"})
    assert caught.code == "facet_elsewhere"
    assert "detach" in caught.repairs[0].options
    step(store, TARIF, "remove_class", **{"class": "RateCard"})
    step(store, TARIF, "pin", module="@uniti/party@v1")
    caught = refused(store, TARIF, "attach", **{"class": "Party", "slot": "rental_rate"})
    assert caught.code == "facet_elsewhere"
    step(store, TARIF, "unpin", module="@uniti/party@v1")
    # Another module's slot is that module's to place.
    caught = refused(store, TARIF, "attach", **{"class": "Item", "slot": "item_name"})
    assert caught.code == "not_yours"
    step(store, TARIF, "detach", **{"class": "Item", "slot": "rental_rate"})


def test_the_seal_holds_a_written_facet_to_the_same_rules(store, conn, tarif):
    probe = "@rudi/handwritten"
    step(store, probe, "start", title="Hand", description="Written by hand.")
    step(store, probe, "pin", module="@uniti/item@v2")
    step(store, probe, "add_slot", slot="hand_rate", range="decimal",
         description="A rate.", unit="IDR", direction="level")
    where = studio.path(store, probe)
    document = yaml.safe_load(where.read_text(encoding="utf-8"))
    document["slots"]["hand_rate"].update({"domain": "Item", "required": True})
    where.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    blocking = [h["kind"] for h in holes_of(store, probe) if h["blocking"]]
    assert "facet_obliges" in blocking
    with pytest.raises(Refusal) as caught:
        seal(conn, where, actor_id="rudi", into=store.directory(probe), store=store)
    assert caught.value.code == "facet_obliges"
    step(store, probe, "discard")


def test_the_facet_module_seals_and_the_library_is_untouched(store, sealed):
    version = store.document(TARIF, "v1")
    assert version["slots"]["rental_rate"]["domain"] == "Item"
    assert store.document("@uniti/item", "v2")["classes"]["Item"]["slots"] == ["item_name"]
    # Only a composition pinning the facet's module carries it.
    alone = dict(store.version_composition("@uniti/item", "v2"))
    assert alone[("@uniti/item", "v2")]["classes"]["Item"]["slots"] == ["item_name"]
    composed = dict(store.version_composition(TARIF, "v1"))
    assert composed[("@uniti/item", "v2")]["classes"]["Item"]["slots"] == \
        ["item_name", "rental_rate"]


# ---- inside an application ------------------------------------------------

def test_a_rule_reads_the_facet_and_the_application_seals(store, conn, application):
    report = reading.state(store, APP, conn)
    blocking = [(h["kind"], h["where"]) for h in report["holes"] if h["blocking"]]
    assert blocking == []
    [example] = report["examples"]
    assert example["passed"] is True, example
    spec = studio.open_draft(store, APP)["slots"]["income_rate"]["annotations"][
        "parameter"]["value"]
    assert spec["slot"] == "rudi_tarif__rental_rate"

    out = seal(conn, studio.path(store, APP), actor_id="dev",
               into=store.directory(APP), store=store)
    assert out["version"] == "v1"


def test_one_item_carries_the_facet_under_rudis_predicate(store, conn, application):
    if not store.versions(APP):
        seal(conn, studio.path(store, APP), actor_id="dev",
             into=store.directory(APP), store=store)
    map_ = read_map(store.path(APP, "v1"), store)
    view = map_["view"]
    assert predicate(view, view.induced_slot("rudi_tarif__rental_rate", "Item")) == RATE

    built = form(conn, map_, "Item")
    assert [f["name"] for f in built["fields"]] == ["item_name", "rudi_tarif__rental_rate", "entity_class"]
    now = datetime.now(timezone.utc)
    shown = app_api.form_of(conn, store, APP, "v1", "Item", valid_at=now, as_of=now)
    by_name = {f["name"]: f for f in shown["fields"]}
    assert by_name["item_name"]["section"] is None
    assert by_name["rudi_tarif__rental_rate"]["section"] == "Rental rates"

    subject = "https://uniti.example/demo/rec/tent"
    submit(conn, map_, "Item", subject=subject,
           values={"entity_class": "Item", "item_name": "Tent",
                   "rudi_tarif__rental_rate": 25000},
           actor_id="staff", valid_from="2026-10-07T09:00:00Z")
    later = datetime(2030, 1, 1, tzinfo=timezone.utc)
    built = table(conn, map_, "Item", valid_at=later, as_of=later)
    [tent] = [r for r in built["rows"] if r["uri"] == subject]
    # One entity, each fact under its own module's predicate.
    cells = {c["uri"]: cell for c, cell in zip(built["columns"], tent["cells"])}
    assert cells["https://w3id.org/uniti/item/item_name"] == "Tent"
    assert float(cells[RATE]) == 25000


def test_the_connection_lens_shows_what_the_facet_adds_to(store, sealed):
    graph = modules_read.class_graph(store, TARIF, "v1")
    item = {n["name"]: n for n in graph["nodes"]}["Item"]
    assert item["slots"][:2] == ["item_name", "rental_rate"]
    assert {"slot": "rental_rate", "module": {"name": TARIF, "version": "v1"}} in \
        item["facets"]


def test_the_catalogue_says_a_facet_is_on_the_thing_it_adds_to(store, sealed):
    # The ecosystem test (§7.5): Sari's agent read Rudi's rate as "on no
    # class", and declared a rate of her own beside the one his pin carries.
    from components.agent import tools
    from components.modules import catalogue as catalogue_read
    everything = catalogue_read.catalogue(store, business=BUSINESS)
    [rate] = [e for e in everything if e["kind"] == "slot" and e["name"] == "rental_rate"]
    assert rate["facet_on"] == {"class": "Item", "module": "@uniti/item",
                                "as": "rudi_tarif__rental_rate"}
    assert "; on Item of @uniti/item, a facet: whatever pins @rudi/tarif has it " \
           "there as rudi_tarif__rental_rate" in tools._entry(rate)
    [item] = [e for e in everything if e["kind"] == "class" and e["name"] == "Item"
              and e["module"]["name"] == "@uniti/item"]
    assert item["facets"] == [{"slot": "rental_rate", "as": "rudi_tarif__rental_rate",
                               "module": {"name": TARIF, "version": "v1"}}]
    assert "; others add: rudi_tarif__rental_rate (@rudi/tarif@v1)" in tools._entry(item)
    # A slot on a class of its own module's is no facet, and says so as before.
    [name] = [e for e in everything if e["kind"] == "slot" and e["name"] == "item_name"
              and e["module"]["name"] == "@uniti/item"]
    assert name["facet_on"] is None and "; on Item" in tools._entry(name)

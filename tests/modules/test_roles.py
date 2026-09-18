"""Roles: what core obliges, and what happens when a module does not honour it.

A role is a class core declares abstract, carrying abstract slots that are
bindings rather than predicates. A module mixes one in and thereby promises to
name a slot of its own for each binding. The promise is worth something only if
something refuses when it is broken, so most of what is here is refusals.

The claim the rest of the slice rests on is one line long:

    a rule written against a role reaches whichever class kept the promise, in
    whichever module, under whatever names that module chose.

What is deliberately *not* here: a test that the numbers come out the same
after a swap. That lives in tests/application, because it needs a log.
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
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

import dev_modules  # noqa: E402
from compile import MapError, _bound, plan_for, tables  # noqa: E402
from components.modules import read  # noqa: E402
from generate import columns, form, read_map  # noqa: E402
from perform import connect  # noqa: E402
from seal import DraftError, seal  # noqa: E402

CATALOG, INVENTORY, STOCK = dev_modules.CATALOG, dev_modules.INVENTORY, dev_modules.STOCK
RIVAL, CORE = dev_modules.RIVAL, dev_modules.CORE
APP_NAME, APP_VERSION = dev_modules.APPLICATION
SWAP_NAME, SWAP_VERSION = dev_modules.SWAPPED


@pytest.fixture(scope="module")
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn


@pytest.fixture(scope="module")
def built(conn, tmp_path_factory):
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    return store


def _draft(tmp_path, classes, slots, imports=None, name="probe"):
    """A one-off module, written straight rather than copied from a fixture."""
    document = {
        "id": f"https://probe.example/{name}",
        "name": f"probe_{name}",
        "title": "Probe",
        "description": "A draft written for one test.",
        "prefixes": {"linkml": "https://w3id.org/linkml/",
                     "pb": "https://probe.example/"},
        "default_prefix": "pb",
        "default_range": "string",
        "imports": imports or ["linkml:types", f"{CORE}@v2"],
        "classes": classes,
        "slots": slots,
        "annotations": {"valid_from": "2026-09-01T00:00:00+00:00",
                        "transcript": "t.txt"},
    }
    path = tmp_path / f"{name}.draft.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    (tmp_path / "t.txt").write_text("probe", encoding="utf-8")
    return path


# ---- what core is ---------------------------------------------------------

def test_core_holds_roles_and_not_a_vocabulary(built):
    """Four classes and four slots, and every one of them is executed."""
    detail = read.version(built, CORE, "v2")
    assert {c["name"] for c in detail["classes"]} == {
        "Thing", "Resource", "Event", "Flow"}
    assert sorted(s["name"] for s in detail["slots"]) == [
        "affects", "amount", "entity_class", "moment"]

    graph = read.class_graph(built, CORE, "v2")
    assert all(n["abstract"] for n in graph["nodes"])
    assert all(n["shape"] == "role" for n in graph["nodes"])


def test_a_binding_is_not_a_predicate(built):
    """Nothing is ever stated under a role, which is why roles can change.

    `slot_uri` is not inherited, so a class filling `amount` keeps its own
    predicate and the log never learns the binding exists. That is the whole
    reason re-binding an orphaned fact is possible at all, and the reason
    altering a role invalidates nothing.
    """
    document = built.document(CORE, "v2")
    assert document["slots"]["amount"]["abstract"] is True
    assert "slot_uri" not in document["slots"]["amount"]
    assert document["slots"]["entity_class"]["slot_uri"] == "uniti:entity_class"

    inventory = built.document(INVENTORY, "v3")
    quantity = inventory["slots"]["movement_quantity"]
    assert quantity["is_a"] == "amount"
    assert quantity["slot_uri"] == "inv:movement_quantity"


# ---- the refusals ---------------------------------------------------------

def test_claiming_a_role_and_not_filling_it_is_refused(conn, built, tmp_path):
    draft = _draft(
        tmp_path,
        classes={"Delivery": {"mixins": ["Flow"], "slots": ["delivery_ref"]}},
        slots={"delivery_ref": {"slot_uri": "pb:delivery_ref", "identifier": True}},
    )
    with pytest.raises(DraftError, match="obliges it to name one slot as 'amount'"):
        seal(conn, draft, actor_id="test", into=tmp_path / "out", store=built)
    assert not (tmp_path / "out").exists()


def test_two_slots_filling_one_binding_is_refused(conn, built, tmp_path):
    """Which of two is *the* amount is a question only the author can answer.

    Guessing would be a wrong number that looks right, which is the one kind of
    mistake this system is built to make impossible.
    """
    draft = _draft(
        tmp_path,
        classes={"Delivery": {"mixins": ["Flow"],
                              "slots": ["gross", "net", "item", "day"]}},
        slots={
            "gross": {"is_a": "amount", "slot_uri": "pb:gross", "range": "decimal"},
            "net": {"is_a": "amount", "slot_uri": "pb:net", "range": "decimal"},
            "item": {"is_a": "affects", "slot_uri": "pb:item"},
            "day": {"is_a": "moment", "slot_uri": "pb:day", "range": "date"},
        },
    )
    with pytest.raises(DraftError, match="2 slots filling 'amount' — gross, net"):
        seal(conn, draft, actor_id="test", into=tmp_path / "out", store=built)


def test_one_closure_holds_one_version_of_a_module(conn, built, tmp_path):
    """The diamond. Two cores in one closure would be two Flows, silently.

    Refusing means the ecosystem has to move together on core — which is the
    property a foundation is for, and one more reason for core to stay small.
    """
    draft = _draft(
        tmp_path,
        classes={"Thin": {"mixins": ["Thing"], "slots": ["thin_ref"]}},
        slots={"thin_ref": {"slot_uri": "pb:thin_ref", "identifier": True}},
        # @demo/catalog@v2 pins core v1; this draft pins core v2 itself.
        imports=["linkml:types", f"{CORE}@v2", f"{CATALOG}@v2"],
    )
    with pytest.raises(DraftError, match=f"reaches {CORE} at two versions"):
        seal(conn, draft, actor_id="test", into=tmp_path / "out", store=built)


def test_a_rule_naming_a_binding_the_source_does_not_carry_is_refused(built):
    """The compiler's half of the same promise, for a map it did not seal.

    `Resource` carries no `amount`: only a Flow does. So a rule totalling
    resources by amount is refused before any SQL is emitted, and the refusal
    names the class rather than the missing predicate.

    The other two refusals in `_bound` — a binding nothing fills, and a binding
    two slots fill — are a second line of defence rather than the first: `seal`
    will not let such a module into the store at all, which is what the two
    tests above assert. They are kept because the compiler reads maps it did
    not seal.
    """
    map_ = read_map(built.path(APP_NAME, APP_VERSION), built)
    with pytest.raises(MapError, match="which Resource has no slot for"):
        _bound(map_, "probe", "Resource", "amount", "sum")


# ---- a binding is a hole, not a column ------------------------------------

def test_a_binding_never_becomes_a_column_or_a_field(conn, built):
    """The trap that would otherwise show up far from its cause.

    `class_induced_slots` hands back the role's abstract slots alongside the
    class's own. Left in, every projection would carry columns of nulls named
    after bindings and every form an empty field, because nothing is ever
    stated under one.
    """
    map_ = read_map(built.path(APP_NAME, APP_VERSION), built)
    names = [c["name"] for c in columns(map_, "StockMovement")]
    assert "movement_quantity" in names
    assert not ({"amount", "affects", "moment"} & set(names))

    plan_ = plan_for(map_, "StockMovement")
    assert not ({"amount", "affects", "moment"}
                & {c["name"] for c in plan_["columns"]})

    fields = {f["name"] for f in form(conn, map_, "StockMovement")["fields"]}
    assert "movement_happened_on" in fields
    assert not ({"amount", "affects", "moment"} & fields)


def test_a_role_gets_no_table_of_its_own(built):
    """Nothing in the log is ever a Flow, so a table of them would have no rows."""
    map_ = read_map(built.path(APP_NAME, APP_VERSION), built)
    assert "IngredientStock" in tables(map_)
    assert not ({"Thing", "Resource", "Event", "Flow"} & set(tables(map_)))


# ---- what it buys ---------------------------------------------------------

def test_a_rule_reaches_a_class_the_application_never_named(built):
    """Written against core, resolved to somebody else's private predicate."""
    for version, klass, measure, group in (
        (APP_VERSION, "StockMovement", "inv:movement_quantity", "inv:movement_ingredient"),
        (SWAP_VERSION, "Movement", "rv:qty_delta", "rv:item"),
    ):
        map_ = read_map(built.path(APP_NAME, version), built)
        spec = plan_for(map_, "IngredientStock")["aggregates"]["quantity_on_hand"]
        assert spec["over"] == "Flow"
        assert spec["measure"] == "amount"
        assert spec["covers"] == [klass]
        assert spec["measure_uris"] == [measure]
        assert spec["by"] == {"stock_ingredient": [group]}


def test_the_rival_module_names_nothing_of_anybody_else_s(built):
    """The swap only proves something if the two modules share no vocabulary."""
    rival = built.document(RIVAL, "v1")
    inventory = built.document(INVENTORY, "v3")

    assert [i for i in rival["imports"] if str(i).startswith("@")] == [f"{CORE}@v2"]
    assert not (set(rival["classes"]) & set(inventory["classes"]))
    assert not (set(rival["slots"]) & set(inventory["slots"]))

    mine = {s["slot_uri"] for s in rival["slots"].values()}
    theirs = {s["slot_uri"] for s in inventory["slots"].values()}
    assert not (mine & theirs)
    assert all(uri.startswith("rv:") for uri in mine)

    # What they do share: the three answers core asked for, and nothing else.
    def fills(document, class_name):
        return {name for name, slot in document["slots"].items()
                if slot.get("is_a") in ("amount", "affects", "moment")
                and name in document["classes"][class_name]["slots"]}

    assert len(fills(rival, "Movement")) == 3
    assert len(fills(inventory, "StockMovement")) == 3


def test_a_generic_module_leaves_its_range_at_the_role(built):
    """@rival can serve a business it has never heard of; @demo/inventory cannot.

    Both fill `affects`. One narrowed the range to its own catalogue's class
    and one left it at Resource, and that single line is the difference between
    a module for bakeries and a module for anyone.
    """
    assert built.document(INVENTORY, "v3")["slots"]["movement_ingredient"]["range"] \
        == "Ingredient"
    assert "range" not in built.document(RIVAL, "v1")["slots"]["item"]

    swapped = read_map(built.path(APP_NAME, SWAP_VERSION), built)
    item = next(c for c in columns(swapped, "Movement") if c["name"] == "item")
    assert item["range"] == "Resource" and item["ref"] is True


# ---- the fit report -------------------------------------------------------

def test_the_fit_report_says_a_name_coupled_application_cannot_move(conn, built):
    """The argument for roles, in one comparison.

    @demo/stock@v1 names @demo/inventory's own words. @v2 names core's roles
    and nothing else. Asked to move to the rival's module, the first cannot and
    the second can — and the report works it out from the two closures rather
    than from anybody's opinion.
    """
    from components.modules import roles as roles_read

    coupled = roles_read.fit(built, STOCK, "v1", SWAP_VERSION, conn=conn)
    assert not coupled["clean"]
    assert any("StockMovement" in d["why"] for d in coupled["dark"])

    free = roles_read.fit(built, STOCK, APP_VERSION, SWAP_VERSION, conn=conn)
    assert free["clean"]
    assert free["dark"] == []


def test_the_fit_report_names_what_moved_and_what_was_rebound(conn, built):
    from components.modules import roles as roles_read

    report = roles_read.fit(built, STOCK, APP_VERSION, SWAP_VERSION, conn=conn)
    assert report["pins"]["removed"] == [{"name": INVENTORY, "version": "v3"}]
    assert report["pins"]["added"] == [{"name": RIVAL, "version": "v1"}]

    flow = next(r for r in report["roles"] if r["name"] == "Flow")
    assert (flow["status"], flow["before"], flow["after"]) == (
        "replaced", ["StockMovement"], ["Movement"])

    by_column = {r["column"]: r for r in report["rules"]}
    assert by_column["quantity_on_hand"]["status"] == "rebound"
    assert by_column["quantity_on_hand"]["reads_after"] == ["rv:item", "rv:qty_delta"]
    # The bakery's own judgement is read from the same place either way, because
    # it was never written against a role in the first place.
    assert by_column["reorder_level"]["status"] == "unchanged"


def test_the_report_names_the_predicates_that_stop_being_read(conn, built):
    """Which predicates lose their reader, and which module used to own them.

    How many statements stand under each is counted against the log, and that
    is asserted in tests/application where there is one. This is the half that
    is decided by the two closures alone.
    """
    from components.modules import roles as roles_read

    report = roles_read.fit(built, STOCK, APP_VERSION, SWAP_VERSION, conn=conn)
    orphans = {o["uri"]: o for o in report["orphaned"]}
    assert "inv:movement_quantity" in orphans
    assert orphans["inv:movement_quantity"]["module"] == {"name": INVENTORY, "version": "v3"}

    # And the other way: nothing @demo/catalog declares is orphaned, because
    # both versions pin it.
    assert not any(o["uri"].startswith("cat:") for o in report["orphaned"])


def test_filling_a_role_fills_the_roles_above_it(built):
    """A class mixing in Flow is an Event, and the catalogue says so.

    Not a detail: a rule written against Event has to reach it, and a reader
    asking who answers Event would otherwise be told nobody.
    """
    from components.modules import roles as roles_read

    catalogue = {r["name"]: r for r in roles_read.roles(built, STOCK, APP_VERSION)["roles"]}
    assert [f["class"] for f in catalogue["Flow"]["filled_by"]] == ["StockMovement"]
    assert [f["class"] for f in catalogue["Event"]["filled_by"]] == ["StockMovement"]
    assert catalogue["Event"]["filled_by"][0]["bindings"] == {
        "moment": "movement_happened_on"}
    assert "Ingredient" in [f["class"] for f in catalogue["Thing"]["filled_by"]]

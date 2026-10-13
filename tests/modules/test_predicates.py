"""A module writes only under its own predicates (ECOSYSTEM_PLAN.md, step 3).

A predicate is a module's word in the log: every fact recorded under
`https://w3id.org/uniti/item/item_name` is the library's saying of an item's
name. A module that declared a slot under that URI would write its own facts
into the library's word, and nothing would tell them apart afterwards. So:

    own words       every predicate a module declares is inside its own
                    namespace, the one its `id` names; a facet is too, by
                    construction
    refused         a slot under another module's prefix, under a prefix of
                    the module's own that means somebody else's namespace, or
                    written as another module's full URI: at the step, at the
                    seal, and as a blocking hole; the repairs are a facet, a
                    slot pointing at the record, or the module's own prefix
    own namespace   one module's namespace is nobody else's: an `id` equal
                    to another module's, inside it or around it is refused
                    when the module starts and when it is sealed, and a
                    module's own earlier versions are not another module
"""

import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from components.modules.store import Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from perform import connect  # noqa: E402
from seal import register, seal  # noqa: E402

REGISTERED = [("@uniti/core", "v1"), ("@uniti/core", "v2"),
              ("@uniti/party", "v1"), ("@uniti/item", "v1")]
ITEM_NAME = "https://w3id.org/uniti/item/item_name"


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


def refused(store, name, op, **args):
    with pytest.raises(Refusal) as caught:
        step(store, name, op, **args)
    return caught.value


def begin(store, name, **args):
    step(store, name, "start", title="Rentals", description="What is rented out.", **args)
    step(store, name, "pin", module="@uniti/item@v1")


def by_hand(store, name, change):
    """Edit a draft's file directly, the way only a person with the file can."""
    where = studio.path(store, name)
    document = yaml.safe_load(where.read_text(encoding="utf-8"))
    change(document)
    where.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return where


def blocking(store, name):
    return [h["kind"] for h in reading.state(store, name)["holes"] if h["blocking"]]


def sealing(conn, store, name, actor="sari"):
    return seal(conn, studio.path(store, name), actor_id=actor,
                into=store.directory(name), store=store)


def options(refusal):
    return {o for r in refusal.repairs for o in (r.options or ())}


# ---- own words ------------------------------------------------------------

def test_a_slot_under_another_modules_prefix_is_refused_at_the_step(store):
    name = "@sari/sewa"
    begin(store, name)
    caught = refused(store, name, "add_slot", slot="label",
                     slot_uri="item:item_name", range="string")
    assert caught.code == "foreign_predicate"
    assert ITEM_NAME in caught.got and "@uniti/item" in caught.got
    # A facet, a slot pointing at the record, or the module's own word.
    assert {"attach", "add_slot", "set_slot"} <= options(caught)
    assert "label" not in (studio.open_draft(store, name).get("slots") or {})

    step(store, name, "add_slot", slot="label", range="string", description="A label.")
    caught = refused(store, name, "set_slot", slot="label", field="slot_uri",
                     value="item:item_name")
    assert caught.code == "foreign_predicate"
    assert studio.open_draft(store, name)["slots"]["label"]["slot_uri"] == "sewa:label"
    step(store, name, "discard")


@pytest.mark.parametrize("written", [
    {"slot_uri": ITEM_NAME},
    {"slot_uri": "itm:item_name", "prefix": ("itm", "https://w3id.org/uniti/item/")},
    {"slot_uri": "item:item_name"},
])
def test_the_seal_holds_a_predicate_written_by_hand_to_the_same_rule(store, conn, written):
    name = "@sari/tangan"
    begin(store, name)
    step(store, name, "add_slot", slot="label", range="string", description="A label.")

    def change(document):
        document["slots"]["label"]["slot_uri"] = written["slot_uri"]
        if "prefix" in written:
            document["prefixes"][written["prefix"][0]] = written["prefix"][1]
    by_hand(store, name, change)

    assert "foreign_predicate" in blocking(store, name)
    with pytest.raises(Refusal) as caught:
        sealing(conn, store, name)
    assert caught.value.code == "foreign_predicate"
    assert ITEM_NAME in caught.value.got
    step(store, name, "discard")


def test_own_predicates_and_a_facet_seal(store, conn):
    name = "@rudi/sewa"
    begin(store, name)
    step(store, name, "add_slot", slot="daily_rate", range="decimal",
         description="What one day costs.", unit="IDR", direction="level")
    step(store, name, "attach", **{"class": "Item", "slot": "daily_rate"})
    assert blocking(store, name) == []
    assert sealing(conn, store, name, actor="rudi")["version"] == "v1"

    # A revision says its words again: its own v1 is not somebody else.
    step(store, name, "discard")
    step(store, name, "revise")
    step(store, name, "set", field="description", value="What a day of renting costs.")
    assert sealing(conn, store, name, actor="rudi")["version"] == "v2"


# ---- one namespace, one module --------------------------------------------

@pytest.mark.parametrize("base", [
    "https://w3id.org/uniti/item",           # the same
    "https://w3id.org/uniti/item/rentals",   # inside it
    "https://w3id.org/uniti",                # around it, and around core's
])
def test_a_namespace_another_module_holds_is_refused_at_start(store, base):
    caught = refused(store, "@mira/barang", "start", title="Items",
                     description="Items again.", base=base)
    assert caught.code == "namespace_taken"
    assert "@uniti/" in caught.got
    assert not studio.path(store, "@mira/barang").is_file()


def test_a_namespace_of_its_own_starts(store):
    step(store, "@mira/barang", "start", title="Items", description="Items again.",
         base="https://mira.example/barang")
    step(store, "@mira/barang", "discard")


def test_the_seal_holds_a_namespace_written_by_hand_to_the_same_rule(store, conn):
    name = "@mira/salinan"
    begin(store, name)

    def change(document):
        document["id"] = "https://w3id.org/uniti/item"
        prefix = document["default_prefix"]
        document["prefixes"][prefix] = "https://w3id.org/uniti/item/"
    by_hand(store, name, change)

    assert "namespace_taken" in blocking(store, name)
    with pytest.raises(Refusal) as caught:
        sealing(conn, store, name, actor="mira")
    assert caught.value.code == "namespace_taken"
    step(store, name, "discard")

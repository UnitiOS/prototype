"""The basic guards: what two authors who never met can get wrong, refused.

Every case here happened in the composition experiment, among authors who
worked alone and could not see each other's modules:

    one name, two meanings    two modules both declared `Warehouse`, and LinkML
                              kept whichever it read last without a word.
    one prefix, two modules   two authors both chose `stock:`, and a predicate
                              registered as the CURIE `stock:code` was the
                              same predicate for both.
    one class name, two       a class fact recorded as the bare name `Item`
    classes                   made one module's items rows of the other's table.

The first is no longer refused: the store reads each module under its own
tag, `alpha_stock__Warehouse` beside `beta_stock__Warehouse`
(tests/modules/test_compose.py). What is refused is two modules with one tag,
which the store could not tell apart; only a `-` read like the `_` between
scope and name still makes one, `@a-b/c` beside `@a/b-c`. The other two are
not refused, because nothing is wrong with them: they are recorded under full
URIs, so they never meet in the log.
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
sys.path.insert(0, str(ROOT / "components" / "generator"))

import dev_modules  # noqa: E402
from components.modules.store import ModuleError  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from generate import _row_subjects, _registry, read_map, submit  # noqa: E402
from perform import connect  # noqa: E402
from seal import DraftError, seal  # noqa: E402

NOW = "2026-09-29T00:00:00+00:00"


@pytest.fixture(scope="module")
def conn():
    """Never committed, like every studio test: the seals here are rolled back."""
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def world(conn, tmp_path_factory):
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    return store


def step(store, name, op, **args):
    return studio.apply(store, name, op, args)


def warehouses(store, name, code_slot):
    """A module declaring `Warehouse`, under the prefix `stock:`, as both authors did."""
    step(store, name, "start", title="Stock", prefix="stock",
         description="Where goods are kept.")
    step(store, name, "add_class", **{"class": "Warehouse",
                                      "description": "A place goods are kept."})
    step(store, name, "fill_role", **{"class": "Warehouse", "role": "Thing"})
    # Two different slot names, one CURIE: the case a prefix used to hide.
    step(store, name, "add_slot", slot=code_slot, slot_uri="stock:code",
         description="What the warehouse is called.")
    step(store, name, "attach", **{"class": "Warehouse", "slot": code_slot})
    step(store, name, "set_slot", slot=code_slot, field="identifier", value="true")
    return name


@pytest.fixture(scope="module")
def two(world, conn):
    """Two modules by two authors, sealed into one log."""
    sealed = {}
    for name, slot in (("@alpha/stock", "alpha_code"), ("@beta/stock", "beta_code")):
        warehouses(world, name, slot)
        sealed[name] = seal(conn, studio.path(world, name), actor_id="probe",
                            into=studio.directory(world, name), store=world,
                            sealed_at=NOW)
    return sealed


# ---- one tag, two modules: refused ---------------------------------------

def test_two_modules_of_one_name_are_pinned_together(world, two):
    """The tag is the scope and the name: both authors' `stock` are in sight,
    each under its own."""
    name = "@probe/both"
    step(world, name, "start", title="Both", description="Pins two stock modules.")
    step(world, name, "pin", module="@alpha/stock@v1")
    step(world, name, "pin", module="@beta/stock@v1")
    classes = set(world.view(studio.path(world, name)).all_classes())
    assert {"alpha_stock__Warehouse", "beta_stock__Warehouse"} <= classes


def test_two_pins_sharing_a_tag_are_refused_where_both_are_in_sight(world, conn, two):
    """`@gamma/stock-x` and `@gamma-stock/x` read as one tag:
    `gamma_stock_x__Warehouse` would be either."""
    for module, slot in (("@gamma/stock-x", "gamma_code"), ("@gamma-stock/x", "gamma_id")):
        warehouses(world, module, slot)
        seal(conn, studio.path(world, module), actor_id="probe",
             into=studio.directory(world, module), store=world, sealed_at=NOW)
    name = "@probe/clash"
    step(world, name, "start", title="Clash", description="Pins two stock modules.")
    step(world, name, "pin", module="@gamma/stock-x@v1")
    with pytest.raises(ModuleError) as refused:
        step(world, name, "pin", module="@gamma-stock/x@v1")
    assert refused.value.code == "tag_taken"
    assert list(refused.value.repairs[0].options) == ["@gamma/stock-x", "@gamma-stock/x"]
    assert studio.open_draft(world, name)["imports"][-1] == "@gamma/stock-x@v1"

    # Written in by hand, it is a hole, and the seal says the same.
    where = studio.path(world, name)
    document = yaml.safe_load(where.read_text(encoding="utf-8"))
    document["imports"].append("@gamma-stock/x@v1")
    where.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    report = reading.state(world, name)
    [hole] = [h for h in report["holes"] if h["kind"] == "tag_taken"]
    assert hole["blocking"] and not report["sealable"]
    with pytest.raises(ModuleError) as refused:
        seal(None, where, actor_id="probe",
             into=studio.directory(world, name), store=world)
    assert refused.value.code == "tag_taken"


def test_a_draft_naming_what_a_pin_declares_is_asked_to_rename(world, two):
    name = "@probe/mine"
    step(world, name, "start", title="Mine", description="Declares its own Warehouse.")
    step(world, name, "add_class", **{"class": "Warehouse", "description": "Mine."})
    step(world, name, "pin", module="@alpha/stock@v1")

    hole = next(h for h in reading.state(world, name)["holes"]
                if h["kind"] == "name_clash")
    assert hole["step"] == {"op": "rename_class", "args": {"class": "Warehouse"},
                            "choose": "to", "options": []}

    step(world, name, "rename_class", **{"class": "Warehouse", "to": "Depot"})
    assert not [h for h in reading.state(world, name)["holes"]
                if h["kind"] == "name_clash"]


# ---- one prefix, two modules: two predicates ------------------------------

def test_one_prefix_in_two_modules_is_two_predicates(two):
    alpha, beta = two["@alpha/stock"], two["@beta/stock"]
    assert "https://uniti.example/alpha/stock/code" in alpha["minted"]
    assert "https://uniti.example/beta/stock/code" in beta["minted"]
    assert (alpha["entities"]["https://uniti.example/alpha/stock/code"]
            != beta["entities"]["https://uniti.example/beta/stock/code"])
    # And the CURIE both of them wrote names nothing in the log.
    assert "stock:code" not in {**alpha["entities"], **beta["entities"]}


# ---- one class name, two classes: two tables ------------------------------

def test_a_class_fact_says_whose_class_it_is(world, conn, two):
    maps = {name: read_map(world.path(name, "v1"), world) for name in two}
    for name, slot, subject in (("@alpha/stock", "alpha_code", "probe:wh_a"),
                                ("@beta/stock", "beta_code", "probe:wh_b")):
        written = submit(conn, maps[name], "Warehouse", subject=subject,
                         values={slot: subject[-4:], "entity_class": "Warehouse"},
                         actor_id="probe", valid_from=NOW, recorded_at=NOW)
        with conn.cursor() as cur:
            cur.execute("SELECT value_literal FROM assertion WHERE id = %s",
                        (written["stated"]["entity_class"],))
            (said,) = cur.fetchone()
        assert said == f"https://uniti.example/{name[1:].split('/')[0]}/stock/Warehouse"

    by_uri, by_id = _registry(conn)
    rows = {name: [by_id[s] for s in _row_subjects(conn, maps[name], "Warehouse",
                                                    by_uri, valid_at=NOW, as_of=NOW)]
            for name in two}
    # Each module's Warehouse table holds its own, and only its own.
    assert rows == {"@alpha/stock": ["probe:wh_a"], "@beta/stock": ["probe:wh_b"]}


# ---- what LinkML could always say, and the studio could not ---------------

@pytest.fixture(scope="module")
def lists(world, conn):
    """A closed list, a slot one class requires and another does not."""
    name = "@probe/lists"
    step(world, name, "start", title="Lists", description="Materials and batches.")
    step(world, name, "add_enum", enum="Unit", values="kg, sack, box",
         description="How a material is counted.")
    for class_name in ("Material", "Batch"):
        step(world, name, "add_class", **{"class": class_name,
                                          "description": f"A {class_name.lower()}."})
        step(world, name, "fill_role", **{"class": class_name, "role": "Thing"})
    for slot, kind in (("material_code", "string"), ("material_unit", "Unit"),
                       ("batch_note", "string")):
        step(world, name, "add_slot", slot=slot, range=kind,
             description=f"The {slot.replace('_', ' ')}.")
        step(world, name, "attach", **{"class": "Material", "slot": slot})
    step(world, name, "attach", **{"class": "Batch", "slot": "batch_note"})
    step(world, name, "set_slot", slot="material_code", field="identifier", value="true")
    step(world, name, "set_usage", **{"class": "Material", "slot": "batch_note",
                                      "field": "required", "value": "true"})

    report = reading.state(world, name)
    assert report["sealable"], [h["where"] for h in report["holes"] if h["blocking"]]
    assert report["enums"][0]["values"] == ["kg", "sack", "box"]
    assert {c["name"]: c["usage"] for c in report["classes"]} == {
        "Batch": {}, "Material": {"batch_note": {"required": True}}}
    seal(conn, studio.path(world, name), actor_id="probe",
         into=studio.directory(world, name), store=world, sealed_at=NOW)
    return read_map(world.path(name, "v1"), world)


def test_a_closed_list_is_offered_from_the_map_and_held_to(conn, lists):
    from generate import MapError, form
    unit = next(f for f in form(conn, lists, "Material")["fields"]
                if f["name"] == "material_unit")
    assert unit["options"] == [("kg", "kg"), ("sack", "sack"), ("box", "box")]
    assert unit["options_from"] == "the map"

    with pytest.raises(MapError) as refused:
        submit(conn, lists, "Material", subject="probe:flour",
               values={"material_code": "FLR", "material_unit": "litre",
                       "batch_note": "dry", "entity_class": "Material"},
               actor_id="probe", valid_from=NOW, recorded_at=NOW)
    assert refused.value.code == "not_among_the_choices"
    assert refused.value.repairs[0].options == ("kg", "sack", "box")


def test_what_one_class_requires_another_may_leave_out(conn, lists):
    from generate import MapError
    with pytest.raises(MapError) as refused:
        submit(conn, lists, "Material", subject="probe:sugar",
               values={"material_code": "SGR", "material_unit": "kg",
                       "entity_class": "Material"},
               actor_id="probe", valid_from=NOW, recorded_at=NOW)
    assert refused.value.code == "required_missing"
    assert refused.value.repairs[0].options == ("batch_note",)

    # A batch carries the same slot and is not obliged to fill it.
    submit(conn, lists, "Batch", subject="probe:batch_1",
           values={"entity_class": "Batch"},
           actor_id="probe", valid_from=NOW, recorded_at=NOW)
    # And an entity the log already holds is not asked for everything again.
    submit(conn, lists, "Material", subject="probe:sugar",
           values={"material_code": "SGR", "batch_note": "fine", "entity_class": "Material"},
           actor_id="probe", valid_from=NOW, recorded_at=NOW)
    submit(conn, lists, "Material", subject="probe:sugar",
           values={"material_unit": "sack"},
           actor_id="probe", valid_from=NOW, recorded_at=NOW)


def test_a_slot_holding_several_values_is_refused_until_a_table_can_read_it(world):
    name = "@probe/several"
    step(world, name, "start", title="Several", description="Tags.")
    step(world, name, "add_class", **{"class": "Tagged", "description": "Tagged."})
    step(world, name, "fill_role", **{"class": "Tagged", "role": "Thing"})
    step(world, name, "add_slot", slot="tagged_label", description="A label it has.")
    step(world, name, "attach", **{"class": "Tagged", "slot": "tagged_label"})
    assert reading.state(world, name)["sealable"]

    step(world, name, "set_slot", slot="tagged_label", field="multivalued", value="true")
    report = reading.state(world, name)
    assert [h["kind"] for h in report["holes"] if h["blocking"]] == [
        "multivalued_not_read"]
    # The compiler's refusal, carried through the seal as it is.
    with pytest.raises(Refusal) as refused:
        seal(None, studio.path(world, name), actor_id="probe",
             into=studio.directory(world, name), store=world)
    assert refused.value.code == "multivalued_not_read"


def test_a_range_left_naming_nothing_is_a_question_with_its_answers(world):
    name = "@probe/dangling"
    step(world, name, "start", title="Dangling", description="A range left behind.")
    step(world, name, "add_class", **{"class": "Shelf", "description": "Shelf."})
    step(world, name, "add_class", **{"class": "Box", "description": "Box."})
    step(world, name, "fill_role", **{"class": "Box", "role": "Thing"})
    step(world, name, "add_slot", slot="kept_on", range="Shelf", description="Where.")
    step(world, name, "attach", **{"class": "Box", "slot": "kept_on"})
    step(world, name, "remove_class", **{"class": "Shelf"})

    hole = next(h for h in reading.state(world, name)["holes"]
                if h["kind"] == "range_unknown")
    assert hole["where"] == "draft.yaml: kept_on"
    assert hole["step"]["op"] == "set_slot"
    assert hole["step"]["args"] == {"slot": "kept_on", "field": "range"}
    assert "Box" in hole["step"]["options"] and "Shelf" not in hole["step"]["options"]

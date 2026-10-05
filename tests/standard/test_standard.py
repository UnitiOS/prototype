"""The recording standard: one way every module is written down.

What is asserted here:

    one source        what the seal refuses, what the studio shows and what an
                      agent is taught are read from components/standard, and
                      a break of it is a blocking hole whose step mends it.
    one language      English for what a module says; the person's words kept
                      as labels in their language, shown and searched.
    meaning           a number says its unit and which way it runs, a date
                      what moment it is — from closed lists.
    history stands    a version sealed before the standard is not changed; it
                      is brought to the standard by sealing a new one.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

import dev_modules  # noqa: E402
from components import standard  # noqa: E402
from components.agent import guide  # noqa: E402
from components.modules.catalogue import catalogue, find  # noqa: E402
from components.refusal import CODES  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from components.studio.draft import StudioError  # noqa: E402
from perform import connect  # noqa: E402
from seal import seal  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def world(conn, tmp_path_factory):
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    return store


def step(store, name, op, **args):
    return studio.apply(store, name, op, args)


def blocking(store, name):
    return {(h["kind"], h["where"]): h for h in reading.state(store, name)["holes"]
            if h["blocking"]}


# ---- reading words ---------------------------------------------------------

@pytest.mark.parametrize("text, said", [
    ("One row per ingredient anything has moved for.", "yes"),
    ("IngredientStock", "yes"),
    ("movement_happened_on", "yes"),
    ("Jumlah stok bahan yang tersisa di gudang.", "no"),
    ("StokBahan", "no"),
    ("sisa_stok", "no"),
    ("La cantidad de producto en el almacén.", "no"),
    ("Headroom.", "unsure"),
])
def test_english_is_read_from_words_and_says_when_it_cannot_tell(text, said):
    assert standard.english(text) == said


def test_a_script_that_is_not_latin_is_not_english():
    assert standard.english("库存数量") == "no"


# ---- a draft that breaks it ------------------------------------------------

def _careless(store, name):
    """A module written the way session 1 wrote one: the person's words as names,
    nothing said about what the numbers mean."""
    step(store, name, "start", title="Stok bahan", description="Stok bahan per hari.")
    step(store, name, "pin", module=f"{dev_modules.CATALOG}@v4")
    step(store, name, "add_class", **{"class": "StokBahan"})
    step(store, name, "add_slot", slot="bahan", range="Ingredient",
         description="Bahan yang dihitung.")
    step(store, name, "add_slot", slot="stock_counted", range="decimal",
         description="How much was counted.")
    step(store, name, "add_slot", slot="count_day", range="date",
         description="The day it was counted.")
    for slot in ("bahan", "stock_counted", "count_day"):
        step(store, name, "attach", **{"class": "StokBahan", "slot": slot})
    return name


def test_every_break_is_a_blocking_hole_with_the_step_that_mends_it(world):
    name = _careless(world, "@probe/careless")
    holes = blocking(world, name)
    assert ("not_in_english", "class StokBahan") in holes
    assert ("description_missing", "class StokBahan") in holes
    assert ("name_not_standard", "slot bahan") in holes
    assert ("not_in_english", "slot bahan description") in holes
    assert ("prefix_not_shared", "slot count_day") in holes
    assert ("unit_missing", "slot stock_counted") in holes
    assert ("direction_missing", "slot stock_counted") in holes
    assert ("time_meaning_missing", "slot count_day") in holes
    assert ("not_in_english", "module title") in holes
    assert reading.state(world, name)["sealable"] is False

    # Each names its step, and a closed list comes with its answers.
    assert holes[("not_in_english", "class StokBahan")]["step"]["op"] == "rename_class"
    assert holes[("description_missing", "class StokBahan")]["step"] == {
        "op": "set_class", "args": {"class": "StokBahan", "field": "description"},
        "choose": "value", "options": []}
    assert holes[("prefix_not_shared", "slot count_day")]["step"]["options"] == [
        "stock_count_day"]
    assert holes[("direction_missing", "slot stock_counted")]["step"]["options"] == \
        list(standard.DIRECTIONS)
    assert holes[("time_meaning_missing", "slot count_day")]["step"]["args"] == {
        "slot": "count_day", "field": "time_meaning"}


def test_the_seal_refuses_what_the_studio_shows(world, conn):
    name = _careless(world, "@probe/refused")
    with pytest.raises(standard.StandardError) as refused:
        seal(conn, studio.path(world, name), actor_id="probe",
             into=studio.directory(world, name), store=world)
    assert refused.value.code in standard.CHECKS
    assert (refused.value.code, refused.value.where) in blocking(world, name)


def test_mended_by_its_own_steps_it_seals_with_the_persons_words_kept(world, conn):
    name = _careless(world, "@probe/mended")
    step(world, name, "set", field="title", value="Ingredient counts")
    step(world, name, "set", field="description", value="What was counted, per day.")
    step(world, name, "label", term="module", language="id", label="Stok bahan")
    step(world, name, "rename_class", **{"class": "StokBahan", "to": "StockCount"})
    step(world, name, "set_class", **{"class": "StockCount", "field": "description",
                                      "value": "One count of one ingredient."})
    step(world, name, "label", term="StockCount", language="id", label="Stok bahan")
    step(world, name, "rename_slot", slot="bahan", to="stock_ingredient")
    step(world, name, "set_slot", slot="stock_ingredient", field="description",
         value="The ingredient counted.")
    step(world, name, "label", term="stock_ingredient", language="id", label="Bahan")
    step(world, name, "rename_slot", slot="count_day", to="stock_count_day")
    step(world, name, "set_slot", slot="stock_count_day", field="time_meaning",
         value="happened")
    step(world, name, "set_slot", slot="stock_counted", field="unit", value="kg")
    step(world, name, "set_slot", slot="stock_counted", field="direction", value="level")
    step(world, name, "fill_role", **{"class": "StockCount", "role": "Thing"})

    report = reading.state(world, name)
    assert [h for h in report["holes"] if h["blocking"]] == []
    assert report["sealable"] is True
    assert report["labels"] == {"id": "Stok bahan"}
    counted = next(c for c in report["classes"] if c["name"] == "StockCount")
    assert counted["labels"] == {"id": "Stok bahan"}
    slots = {s["name"]: s for s in report["slots"]}
    assert (slots["stock_counted"]["unit"], slots["stock_counted"]["direction"]) == \
        ("kg", "level")
    assert slots["stock_count_day"]["time_meaning"] == "happened"

    out = seal(conn, studio.path(world, name), actor_id="probe",
               into=studio.directory(world, name), store=world)
    sealed = world.document(name, out["version"])
    assert sealed["classes"]["StockCount"]["structured_aliases"] == [
        {"literal_form": "Stok bahan", "in_language": "id", "predicate": "EXACT_SYNONYM"}]
    # Somebody looking in their own words finds it.
    found = find(catalogue(world), text="stok bahan")["entries"]
    assert ("class", "StockCount") in {(e["kind"], e["name"]) for e in found}


def test_a_closed_list_refuses_what_is_not_on_it(world):
    name = _careless(world, "@probe/listed")
    with pytest.raises(StudioError) as refused:
        step(world, name, "set_slot", slot="stock_counted", field="direction",
             value="up")
    assert refused.value.code == "operation_arguments"
    assert list(refused.value.repairs[0].options) == list(standard.DIRECTIONS)


def test_a_text_it_cannot_place_is_asked_and_blocks_nothing(world):
    name = "@probe/doubted"
    step(world, name, "start", title="Doubted", description="A module for one test.")
    step(world, name, "add_class", **{"class": "Widget",
                                      "description": "Frobnicated gizmos, zorbled daily."})
    holes = {(h["kind"], h["where"]): h for h in reading.state(world, name)["holes"]}
    assert not holes[("maybe_not_english", "class Widget")]["blocking"]


def test_a_module_is_named_to_the_standard_when_it_is_started(world):
    with pytest.raises(StudioError) as refused:
        step(world, "@probe/stock_counts", "start", title="Counts",
             description="Counts.")
    assert refused.value.code == "name_not_standard"
    assert list(refused.value.repairs[0].options) == ["@probe/stock-counts"]


def test_an_example_is_said_in_english_and_keeps_the_persons_words(world):
    name = "@probe/said"
    step(world, name, "start", title="Said", description="A module for one test.")
    step(world, name, "add_example", example="flour",
         says="Tepung masuk 25 kg dan dipakai 5 kg, jadi stoknya 20 kg.")
    assert ("not_in_english", "example flour") in blocking(world, name)

    step(world, name, "set_example", example="flour", field="says",
         value="25 kg of flour came in and 5 kg were used, so 20 kg are on hand.")
    step(world, name, "label", term="flour", language="id",
         label="Tepung masuk 25 kg dan dipakai 5 kg, jadi stoknya 20 kg.")
    assert ("not_in_english", "example flour") not in blocking(world, name)
    assert studio.examples_of(world, name)["flour"]["labels"] == {
        "id": "Tepung masuk 25 kg dan dipakai 5 kg, jadi stoknya 20 kg."}


# ---- history stands ---------------------------------------------------------

def test_a_version_sealed_before_the_standard_is_brought_to_it_by_a_new_one(world):
    # The demonstration's v3 stays as it was sealed, and v4 meets the standard.
    v3 = world.document(dev_modules.STOCK, "v3")
    assert "quantity_on_hand" in v3["slots"]
    assert list(standard.refusals(v3)) != []
    v4 = world.document(dev_modules.STOCK, "v4")
    assert list(standard.refusals(v4)) == []

    # Revising the latest version starts from one that already holds.
    name = dev_modules.RIVAL
    step(world, name, "revise")
    try:
        assert blocking(world, name) == {}
    finally:
        step(world, name, "discard")


# ---- one source --------------------------------------------------------------

def test_what_the_seal_refuses_is_what_the_guide_teaches():
    taught = guide.instructions()
    assert standard.teach() in taught
    for direction in standard.DIRECTIONS:
        assert direction in taught
    for meaning in standard.TIME_MEANINGS:
        assert meaning in taught
    # Every check is a refusal code, with one meaning, written once.
    assert all(standard.CHECKS[code] == CODES[code] for code in standard.CHECKS)
    # And the studio has a step for every one of them.
    assert set(standard.CHECKS) <= set(reading.ANSWERS)

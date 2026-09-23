"""The studio: a module built by choosing steps, and never by writing YAML.

What this slice has to hold, and what is asserted here:

    one judge           whatever the studio calls clean, `seal` seals; whatever
                        it calls blocked, `seal` refuses, with the same code.
                        A second opinion is how the first attempt at this
                        layer went wrong, so the studio runs the gates' own
                        readers and collects instead of re-deciding.
    the hole is finite  a role claimed and a binding unnamed comes back as one
                        question with the slots that would fit — judged by
                        range, not by every slot in the module.
    the steps are the   the list a form draws and the list an agent chooses
    same list           from are one list, and everything in it is performed.
    nothing is written  a draft is a file. Stepping through a whole module
                        leaves the log exactly as it was.

The module built here is deliberately thin and says so: two classes and a
handful of slots, named after nothing in particular. The point is the
mechanism, and the content is the least that exercises it.
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
from components.modules import diff as diff_read  # noqa: E402
from components.modules.store import ModuleError  # noqa: E402
from components.refusal import CODES  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from components.studio.draft import _PERFORM, OPERATIONS, StudioError  # noqa: E402
from components.studio.read import OPEN  # noqa: E402
from perform import connect  # noqa: E402
from seal import DraftError, seal  # noqa: E402

CORE = dev_modules.CORE


@pytest.fixture(scope="module")
def conn():
    """One connection, never committed: a studio test states nothing.

    The demonstration store has to be sealed to exist, and those seals are
    writes. They are rolled back at the end, so no other test module ever sees
    a version this one made.
    """
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def world(conn, tmp_path_factory):
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    return store


def step(store, name, op, **args):
    return studio.apply(store, name, op, args)


def build_a_module(store, name="@probe/parts"):
    """One whole module, start to sealable, by choosing steps and nothing else."""
    step(store, name, "start", title="Parts",
         description="A module built by the studio, to prove it can be.")
    step(store, name, "add_class", **{"class": "Movement",
                                      "description": "Something moving."})
    step(store, name, "fill_role", **{"class": "Movement", "role": "Flow"})
    for slot, kind, said in (
        ("movement_code", "string", "What names this one."),
        ("movement_size", "decimal", "How much moved, signed."),
        ("movement_thing", "Resource", "What moved."),
        ("movement_day", "date", "The day it moved."),
    ):
        step(store, name, "add_slot", slot=slot, range=kind, description=said)
        step(store, name, "attach", **{"class": "Movement", "slot": slot})
    step(store, name, "set_slot", slot="movement_code",
         field="identifier", value="true")
    return name


def fill_the_bindings(store, name):
    step(store, name, "bind", slot="movement_size", binding="amount")
    step(store, name, "bind", slot="movement_thing", binding="affects")
    step(store, name, "bind", slot="movement_day", binding="moment")


# ---- the hole -------------------------------------------------------------

def test_a_claimed_role_leaves_one_question_per_binding(world):
    """Three bindings unfilled is three questions, not the first one."""
    name = build_a_module(world, "@probe/holes")
    report = reading.state(world, name)

    blocking = [h for h in report["holes"] if h["blocking"]]
    assert [h["where"] for h in blocking] == [
        "Movement.affects", "Movement.amount", "Movement.moment"]
    assert all(h["kind"] == "binding_unfilled" for h in blocking)
    assert report["sealable"] is False

    # The seal, asked the same thing, stops at the first: that is what a gate
    # does, and it is exactly the difference this page exists for.
    with pytest.raises(DraftError) as raised:
        seal(None, studio.path(world, name), actor_id="probe",
             into=studio.directory(world, name), store=world)
    assert raised.value.code == "binding_unfilled"


def test_the_answers_are_the_slots_that_fit_and_not_the_others(world):
    """The finite set, judged by range. A blank page is what this replaces."""
    name = build_a_module(world, "@probe/fits")
    holes = {h["where"]: h for h in reading.state(world, name)["holes"]
             if h["blocking"]}

    assert holes["Movement.amount"]["step"]["op"] == "bind"
    assert holes["Movement.amount"]["step"]["options"] == ["movement_size"]
    assert holes["Movement.moment"]["step"]["options"] == ["movement_day"]
    assert holes["Movement.affects"]["step"]["options"] == ["movement_thing"]
    assert holes["Movement.amount"]["question"] == \
        "which slot of Movement is its amount?"

    # The studio reads the class and the binding out of the gate's own `where`,
    # rather than the refusal carrying a field only the studio would use. So the
    # shape of `where` is a promise, and this is where it is held.
    assert holes["Movement.amount"]["refusal"]["where"] == "Movement.amount"

    # And the step that answers it is the step that answers it.
    step(world, name, **{**holes["Movement.amount"]["step"]["args"],
                         "op": "bind", "slot": "movement_size"})
    assert "Movement.amount" not in {
        h["where"] for h in reading.state(world, name)["holes"] if h["blocking"]}


def test_a_hole_that_nothing_refuses_is_still_a_hole(world):
    """The openings: nothing is blocked and something is unfinished."""
    name = "@probe/openings"
    step(world, name, "start", title="Openings",
         description="A module with loose ends and nothing refused.")
    step(world, name, "add_class", **{"class": "Thing_of_mine"})
    step(world, name, "add_slot", slot="loose_one")

    holes = {(h["kind"], h["where"]) for h in reading.state(world, name)["holes"]}
    assert ("class_is_empty", "Thing_of_mine") in holes
    assert ("slot_is_loose", "loose_one") in holes
    assert ("nothing_said_about_it", "Thing_of_mine") in holes
    assert ("nothing_said_about_it", "loose_one") in holes
    assert all(not h["blocking"] for h in reading.state(world, name)["holes"])
    assert reading.state(world, name)["sealable"] is True


def test_a_class_nothing_can_ever_be_says_so(world):
    """A class with slots, no role, and no rule: it compiles, and it is empty."""
    name = "@probe/rowless"
    step(world, name, "start", title="Rowless", description="One class, no rows.")
    step(world, name, "add_class", **{"class": "Item", "description": "A thing."})
    step(world, name, "add_slot", slot="item_name", description="Its name.")
    step(world, name, "attach", **{"class": "Item", "slot": "item_name"})

    report = reading.state(world, name)
    hole = next(h for h in report["holes"] if h["kind"] == "class_has_no_rows")
    assert hole["where"] == "Item"
    assert hole["question"] == "how would anything ever become a Item?"
    # The answer is a role that brings the predicate saying which class an
    # entity is — computed, not named here.
    assert hole["step"]["op"] == "fill_role"
    assert "Thing" in hole["step"]["options"]
    assert report["classes"][0]["has_rows"] is False

    step(world, name, "fill_role", **{"class": "Item", "role": "Thing"})
    after = reading.state(world, name)
    assert after["classes"][0]["has_rows"] is True
    assert not [h for h in after["holes"] if h["kind"] == "class_has_no_rows"]


# ---- the map --------------------------------------------------------------

def test_the_map_carries_what_the_draft_points_at_and_stops_there(world):
    """The neighbourhood a module sits in, not the whole of what it pins.

    A module pins a vocabulary and uses a corner of it. What belongs on a map
    beside your own classes is what you point at, and what those point at in
    turn — so Category and Supplier arrive because Ingredient names them, not
    because the same module happens to declare them.

    Roles are never on it. A role is a shape a class claims, and it belongs
    drawn on that class rather than standing beside it as another thing.
    """
    name = "@probe/neighbours"
    step(world, name, "start", title="Neighbours",
         description="A module that points at somebody else's.")
    step(world, name, "add_class", **{"class": "Movement",
                                      "description": "Something moving."})
    step(world, name, "add_slot", slot="movement_thing",
         description="What moved.")
    step(world, name, "attach", **{"class": "Movement", "slot": "movement_thing"})

    # Nothing pointed at yet, so nothing stands beside it.
    assert reading.state(world, name)["borrowed"] == []

    step(world, name, "pin", module=f"{dev_modules.CATALOG}@v3")
    step(world, name, "set_slot", slot="movement_thing",
         field="range", value="Ingredient")

    report = reading.state(world, name)
    assert [held["name"] for held in report["borrowed"]] == [
        "Category", "Ingredient", "Supplier"]
    assert {held["module"]["name"] for held in report["borrowed"]} == {
        dev_modules.CATALOG}
    # Ingredient is pointed at; the other two are reached through it.
    ingredient = next(h for h in report["borrowed"] if h["name"] == "Ingredient")
    assert "Category" in [s["range"] for s in ingredient["slots"]]
    assert ingredient["fills"] == ["Resource"]
    # Sight is wider than the map, and that is the point of the map.
    assert report["sees"]["classes"] > len(report["borrowed"]) + 1
    assert not {"Thing", "Resource", "Flow", "Event"} & {
        held["name"] for held in report["borrowed"]}

    step(world, name, "discard")


# ---- one judge ------------------------------------------------------------

def test_what_the_studio_calls_clean_is_what_seal_seals(world, conn):
    """The whole claim of the slice: a module made of steps, and no YAML.

    It is sealed here as well, because "the studio says it is fine" is worth
    nothing unless the gate agrees — and the gate is the one that writes.
    """
    name = build_a_module(world, "@probe/sealed")
    fill_the_bindings(world, name)

    report = reading.state(world, name)
    assert report["holes"] == [] and report["sealable"] is True
    assert report["becomes"] == "v1" and report["revises"] is None
    assert [t["class"] for t in report["tables"]] == ["Movement"]

    out = seal(conn, studio.path(world, name), actor_id="probe",
               into=studio.directory(world, name), store=world)
    assert out["version"] == "v1"
    assert world.versions(name)[-1]["version"] == "v1"

    # And what the store now holds is a module like any other: its predicates
    # are declared, its role is filled, and the closure resolves.
    sealed = world.document(name, "v1")
    assert sealed["classes"]["Movement"]["mixins"] == ["Flow"]
    assert sealed["slots"]["movement_size"]["is_a"] == "amount"
    assert [p[0] for p in world.closure(name, "v1")] == [CORE, name]


def test_the_steps_taken_become_the_transcript(world, conn):
    """Nobody writes the transcript either: it is the list of steps."""
    name = build_a_module(world, "@probe/evidence")
    fill_the_bindings(world, name)
    taken = studio.transcript(world, name)
    assert "start  title=Parts" in taken
    assert "bind  slot=movement_size binding=amount" in taken

    seal(conn, studio.path(world, name), actor_id="probe",
         into=studio.directory(world, name), store=world)
    beside = studio.directory(world, name) / "v1.txt"
    assert beside.read_text(encoding="utf-8") == taken


def test_stepping_through_a_module_writes_nothing_to_the_log(world, conn):
    """A draft is a file. Nothing about it reaches the kernel until a seal."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM assertion")
        before = cur.fetchone()[0]
    name = build_a_module(world, "@probe/quiet")
    fill_the_bindings(world, name)
    reading.state(world, name)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM assertion")
        assert cur.fetchone()[0] == before


def test_an_application_is_built_the_same_way_a_module_is(world):
    """The full case, and the one the slice is measured by.

    An application is a sealed version that pins others and declares the
    tables somebody wants to see. Nothing about building one is special: the
    same steps, and the three kinds of rule the compiler reads — a total over
    a role, a fact read off a key, and arithmetic on two columns of the same
    table. Written here without a line of YAML.
    """
    name = "@probe/application"
    step(world, name, "start", title="An application",
         description="Totals every flow by what it affects, and says how far "
                     "above the level that leaves it.")
    step(world, name, "pin", module=f"{dev_modules.CATALOG}@v3")
    step(world, name, "pin", module=f"{dev_modules.INVENTORY}@v3")
    step(world, name, "add_class", **{"class": "Balance",
                                      "description": "One row per resource anything moved."})
    for slot, kind, said in (
        ("balance_thing", "Ingredient", "The resource this row is about."),
        ("balance_on_hand", "decimal", "Every flow affecting it, added up."),
        ("balance_level", "decimal", "What somebody said the level is."),
        ("balance_headroom", "decimal", "How far above the level that leaves it."),
    ):
        step(world, name, "add_slot", slot=slot, range=kind, description=said)
        step(world, name, "attach", **{"class": "Balance", "slot": slot})

    # A rule written against the role, not against anybody's class: this is
    # what survives the module under it being replaced.
    step(world, name, "aggregate", **{
        "class": "Balance", "column": "balance_on_hand",
        "over": "Flow", "sum": "amount", "by": "balance_thing=affects"})
    step(world, name, "parameter", **{
        "class": "Balance", "column": "balance_level",
        "of": "balance_thing", "slot": "ingredient_reorder_level"})
    step(world, name, "expression", **{
        "class": "Balance", "column": "balance_headroom",
        "expression": "{balance_on_hand} - {balance_level}"})

    report = reading.state(world, name)
    assert report["holes"] == [] and report["sealable"] is True
    balance = next(t for t in report["tables"] if t["class"] == "Balance")
    assert balance["shape"] == "grouped"
    assert balance["columns"] == 4 and balance["unfilled"] == []
    assert {s["name"]: (s["rule"] or {}).get("kind") for s in report["slots"]} == {
        "balance_thing": None, "balance_on_hand": "aggregate",
        "balance_level": "parameter", "balance_headroom": "expression"}


# ---- the steps ------------------------------------------------------------

def test_every_step_is_performed_and_offered(world):
    """The closed list is closed at both ends.

    A step nothing performs is a promise to a caller who will wait for it
    forever, and a step the list does not offer is a step only somebody
    reading the source would find.
    """
    assert set(OPERATIONS) == set(_PERFORM)
    name = build_a_module(world, "@probe/offered")
    offered = reading.steps(world, name, studio.open_draft(world, name))
    assert [s["op"] for s in offered] == list(OPERATIONS)
    assert all(s["does"] for s in offered)

    by_op = {s["op"]: s for s in offered}
    fills = {t["name"]: t for t in by_op["fill_role"]["takes"]}
    assert fills["class"]["options"] == ["Movement"]
    assert "Flow" in fills["role"]["options"] and "Movement" not in fills["role"]["options"]
    binds = {t["name"]: t for t in by_op["bind"]["takes"]}
    assert binds["binding"]["options"] == ["affects", "amount", "moment"]
    assert {t["name"]: t for t in by_op["set_slot"]["takes"]}["field"]["options"] \
        == list(studio.SLOT_FIELDS)


def test_a_step_that_is_not_one_is_refused_with_the_ones_that_are(world):
    name = build_a_module(world, "@probe/refused")
    with pytest.raises(StudioError) as raised:
        studio.apply(world, name, "invent_something", {})
    assert raised.value.code == "not_an_operation"
    assert "bind" in raised.value.repairs[0].options

    with pytest.raises(StudioError) as raised:
        step(world, name, "bind", slot="movement_size", binding="movement_day")
    assert raised.value.code == "not_a_binding"
    assert raised.value.repairs[0].options == ("affects", "amount", "moment")

    with pytest.raises(StudioError) as raised:
        step(world, name, "attach", **{"class": "Ingredient", "slot": "movement_code"})
    assert raised.value.code == "not_yours"

    with pytest.raises(StudioError) as raised:
        step(world, name, "add_class", **{"class": "Movement"})
    assert raised.value.code == "name_taken"

    with pytest.raises(StudioError) as raised:
        step(world, name, "fill_role", **{"class": "Movement", "role": "Nothing"})
    assert raised.value.code == "not_a_role"


def test_every_opening_is_written_down_like_a_refusal_is(world):
    """`OPEN` is a closed list too, and each line says what it means."""
    name = build_a_module(world, "@probe/vocabulary")
    kinds = {h["kind"] for h in reading.state(world, name)["holes"]}
    assert kinds <= set(OPEN) | set(CODES)
    assert all(isinstance(means, str) and means for means in OPEN.values())


# ---- revising, renaming, discarding ---------------------------------------

def test_a_rename_keeps_the_predicate_and_follows_every_reference(world):
    """A rename is not a new predicate: the kernel sees one, and so does the diff."""
    name = build_a_module(world, "@probe/renamed")
    fill_the_bindings(world, name)
    before = studio.open_draft(world, name)["slots"]["movement_size"]["slot_uri"]

    step(world, name, "rename_slot", slot="movement_size", to="movement_amount")
    document = studio.open_draft(world, name)
    assert "movement_size" not in document["slots"]
    assert document["slots"]["movement_amount"]["slot_uri"] == before
    assert document["slots"]["movement_amount"]["is_a"] == "amount"
    assert "movement_amount" in document["classes"]["Movement"]["slots"]
    assert reading.state(world, name)["sealable"] is True

    step(world, name, "rename_class", **{"class": "Movement", "to": "Move"})
    document = studio.open_draft(world, name)
    assert "Move" in document["classes"] and "Movement" not in document["classes"]
    assert document["classes"]["Move"]["mixins"] == ["Flow"]


def test_a_revision_starts_from_the_last_version_without_its_stamps(world, conn):
    name = build_a_module(world, "@probe/again")
    fill_the_bindings(world, name)
    seal(conn, studio.path(world, name), actor_id="probe",
         into=studio.directory(world, name), store=world)
    studio.apply(world, name, "discard", {})

    with pytest.raises(StudioError) as raised:
        step(world, name, "start", title="Again", description="x")
    assert raised.value.code == "module_exists"

    studio.apply(world, name, "revise", {})
    document = studio.open_draft(world, name)
    assert "version" not in document
    assert set(document["annotations"]) == {"valid_from", "transcript"}
    report = reading.state(world, name)
    assert report["revises"] == "v1" and report["becomes"] == "v2"
    assert report["diff"]["classes"]["added"] == []

    step(world, name, "add_slot", slot="movement_note", description="Why.")
    step(world, name, "attach", **{"class": "Movement", "slot": "movement_note"})
    assert reading.state(world, name)["diff"]["slots"]["added"] == ["movement_note"]


def test_a_discarded_draft_leaves_nothing_behind(world):
    name = "@probe/gone"
    step(world, name, "start", title="Gone", description="Never sealed.")
    where = studio.directory(world, name)
    assert where.is_dir()

    studio.apply(world, name, "discard", {})
    assert not where.exists()
    with pytest.raises(ModuleError) as raised:
        world.versions(name)
    assert raised.value.code == "no_such_module"


def test_a_draft_is_listed_while_it_is_open(world):
    name = "@probe/listed"
    step(world, name, "start", title="Listed", description="Open now.")
    step(world, name, "add_class", **{"class": "One", "description": "A thing."})
    held = {d["name"]: d for d in studio.drafts(world)}
    assert held[name]["revises"] is None
    assert held[name]["steps"] == 2
    studio.apply(world, name, "discard", {})
    assert name not in {d["name"] for d in studio.drafts(world)}


# ---- the API --------------------------------------------------------------

def test_the_api_takes_a_step_and_answers_with_the_draft(world, monkeypatch):
    from starlette.testclient import TestClient

    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    client = TestClient(app)
    name = "@probe/served"

    made = client.post("/api/studio/step", json={
        "name": name, "step": "start",
        "args": {"title": "Served", "description": "Built over HTTP."}})
    assert made.status_code == 200
    assert made.json()["becomes"] == "v1"

    client.post("/api/studio/step", json={
        "name": name, "step": "add_class",
        "args": {"class": "Move", "description": "Something moving."}})
    after = client.post("/api/studio/step", json={
        "name": name, "step": "fill_role", "args": {"class": "Move", "role": "Flow"}})
    holes = [h for h in after.json()["holes"] if h["blocking"]]
    assert {h["where"] for h in holes} == {"Move.amount", "Move.affects", "Move.moment"}

    listed = client.get("/api/studio/drafts").json()
    assert name in {d["name"] for d in listed}
    assert client.get("/api/studio/draft", params={"name": name}).json()["title"] \
        == "Served"

    # A step the studio does not perform is refused whole, with the structure
    # beside the sentence, and nothing is written.
    refused = client.post("/api/studio/step", json={
        "name": name, "step": "bind",
        "args": {"slot": "nothing_here", "binding": "amount"}})
    assert refused.status_code == 400
    assert refused.json()["refusal"]["code"] == "not_yours"
    assert refused.json()["refusal"]["gate"] == "the studio"

    assert client.get("/api/studio/draft",
                      params={"name": "@nobody/nothing"}).status_code == 404
    assert client.post("/api/studio/step",
                       json={"name": name, "step": "discard"}).json()["discarded"]


# ---- the diff the studio shows --------------------------------------------

def test_the_diff_is_the_same_one_the_store_shows_between_versions(world):
    """Not a second diff: the draft is compared with the module's own reader."""
    name = "@probe/compared"
    step(world, name, "start", title="Compared", description="x")
    step(world, name, "add_class", **{"class": "One", "description": "A thing."})
    document = studio.open_draft(world, name)
    assert reading.state(world, name)["diff"] == diff_read.compare({}, document)

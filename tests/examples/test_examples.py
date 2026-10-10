"""Business examples: the numbers a map must come to, held on every change.

What this slice has to hold, and what is asserted here:

    a contract     an example says, in the business's words, what a handful
                   of records must add up to; a number that comes out
                   different refuses the seal, and nothing is written.
    its own log    an example runs in a scratch log that is rolled back. It
                   sees none of the real log and leaves nothing in it.
    one door       its records go in through the form's own door, so what the
                   form refuses the example refuses, in the form's words.
    every change   the studio runs the examples on every read of a draft, a
                   failing one is a blocking hole, a revision starts from the
                   examples of the version it revises, and a rename reaches
                   them as it reaches every rule.
    owed           every column a draft computes needs a number in some
                   example before it can be sealed.
    whose word     an example an agent writes is a proposal until a person
                   agrees to it, and an agent cannot change one a person
                   agreed to. The transcript says who took each step.
"""

import os
import shutil
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
import load_facts  # noqa: E402
from components.examples import examples as business  # noqa: E402
from components.examples.examples import ExampleError  # noqa: E402
from components.modules.__main__ import main as modules_main  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from components.studio.draft import StudioError  # noqa: E402
from generate import read_map  # noqa: E402
from perform import connect  # noqa: E402
from seal import seal  # noqa: E402

STOCK = dev_modules.STOCK
FIXTURE = dev_modules.FIXTURES / STOCK


@pytest.fixture(scope="module")
def conn():
    """One connection, never committed: the store has to be sealed to exist,
    and those seals are rolled back at the end."""
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def world(conn, tmp_path_factory):
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    return store


def _log_size(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM assertion), "
                    "(SELECT count(*) FROM intent)")
        return cur.fetchone()


def _demo(world):
    map_ = read_map(world.path(STOCK, "v2"), world)
    return map_, business.load(business.path_for(map_["path"]))


def step(store, name, op, actor="person", **args):
    return studio.apply(store, name, op, args, actor=actor)


# ---- the contract ---------------------------------------------------------

def test_the_demonstration_application_holds_to_its_examples(world, conn):
    """Sealed with its examples, which travelled beside it and are not a version."""
    beside = world.directory(STOCK) / "v2.examples.yaml"
    assert beside.is_file()
    assert [v["version"] for v in world.versions(STOCK)] == ["v1", "v2", "v3", "v4"]

    map_, held = _demo(world)
    results = {r["name"]: r for r in business.run(conn, map_, held)}
    assert all(r["passed"] for r in results.values())

    flour = results["flour_in_and_out"]["checks"]
    # The same row on two days: what was known of the level by each.
    assert [(c["at"], c["column"], c["got"]) for c in flour] == [
        ("2026-06-30", "quantity_on_hand", "36"),
        ("2026-06-30", "reorder_level", "20"),
        ("2026-06-30", "headroom", "16"),
        ("2026-07-05", "quantity_on_hand", "36"),
        ("2026-07-05", "reorder_level", "30"),
        ("2026-07-05", "headroom", "6"),
    ]
    # And the numbers are there to see when they are right, too.
    stock = next(t for t in results["flour_in_and_out"]["tables"]
                 if t["table"] == "IngredientStock")
    assert stock["rows"] == [["flour", "36", "30", "6"]]


def test_an_empty_cell_is_expected_as_empty_and_not_as_nought(world, conn):
    map_, held = _demo(world)
    [salt] = business.run(conn, map_, {"salt": held["no_level_no_headroom"]})
    assert [(c["column"], c["expected"], c["got"]) for c in salt["checks"]] == [
        ("quantity_on_hand", "5", "5"), ("reorder_level", "empty", "empty"),
        ("headroom", "empty", "empty")]

    nought = yaml.safe_load(yaml.safe_dump(held["no_level_no_headroom"]))
    nought["expect"][0]["values"]["headroom"] = 0
    [salt] = business.run(conn, map_, {"salt": nought})
    assert salt["passed"] is False
    [refusal] = salt["refusals"]
    assert refusal.code == "example_failed"
    assert (refusal.expected.split(",")[0], refusal.got) == ("0", "empty")


def test_an_example_sees_its_own_records_and_leaves_nothing(world, conn):
    """The real log holds the whole demonstration; the example sees one sack."""
    load_facts.load(conn, yaml.safe_load(
        (dev_modules.FIXTURES / "demo_data.yaml").read_text(encoding="utf-8")),
        world, actor_id="test")
    before = _log_size(conn)

    map_, held = _demo(world)
    [flour] = business.run(conn, map_, {"flour": held["flour_in_and_out"]})
    assert flour["passed"] is True
    ingredients = next(t for t in flour["tables"] if t["table"] == "catalog__Ingredient")
    assert [row[0] for row in ingredients["rows"]] == ["flour"]

    assert _log_size(conn) == before
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM intent WHERE actor_id = %s",
                    (business.ACTOR,))
        assert cur.fetchone()[0] == 0


def test_a_wrong_number_refuses_the_seal_and_writes_nothing(world, conn, tmp_path):
    here = tmp_path / "draft"
    here.mkdir()
    for leaf in ("v2.draft.yaml", "v2.draft.txt"):
        shutil.copyfile(FIXTURE / leaf, here / leaf)
    held = yaml.safe_load((FIXTURE / "v2.draft.examples.yaml").read_text(encoding="utf-8"))
    held["examples"]["flour_in_and_out"]["expect"][0]["values"]["quantity_on_hand"] = 50
    (here / "v2.draft.examples.yaml").write_text(yaml.safe_dump(held), encoding="utf-8")

    into = tmp_path / "into"
    before = _log_size(conn)
    with pytest.raises(ExampleError) as raised:
        seal(conn, here / "v2.draft.yaml", actor_id="probe", into=into, store=world)
    refusal = raised.value
    assert refusal.code == "example_failed"
    assert refusal.where == ("example flour_in_and_out: IngredientStock flour, "
                             "quantity_on_hand on 2026-06-30")
    assert refusal.got == "36"
    assert refusal.expected.startswith("50, because: Flour came in twice")
    # The way out is the rule, or the person who gave the example — never
    # quietly rewriting the number to match.
    assert refusal.repairs[-1].options == ("expect",)

    assert not into.exists()
    assert _log_size(conn) == before


def test_a_record_the_form_refuses_is_refused_in_the_forms_words(world, conn):
    map_, held = _demo(world)
    body = yaml.safe_load(yaml.safe_dump(held["flour_in_and_out"]))
    body["records"][1]["facts"]["movement_quantity"] = "lots"
    [result] = business.run(conn, map_, {"bad": body})
    [refusal] = result["refusals"]
    assert (refusal.code, refusal.gate) == ("value_not_of_type", "the generator")
    assert refusal.where == ("example bad: record flour_in_1, "
                             "inventory__StockMovement.inventory__movement_quantity")

    body = yaml.safe_load(yaml.safe_dump(held["flour_in_and_out"]))
    body["records"][1]["facts"]["movement_ingredient"] = "sugar"
    [result] = business.run(conn, map_, {"bad": body})
    [refusal] = result["refusals"]
    assert refusal.code == "not_among_the_choices"
    assert refusal.repairs[0].options == ("flour",)


def test_a_record_first_stated_must_say_what_it_is(world, conn):
    map_, _ = _demo(world)
    body = {"says": "Something with no class.",
            "records": [{"record": "thing", "facts": {"ingredient_code": "X"}}],
            "expect": []}
    [result] = business.run(conn, map_, {"nameless": body})
    [refusal] = result["refusals"]
    assert refusal.code == "record_without_class"
    assert "catalog__Ingredient" in refusal.repairs[0].options


def test_an_examples_file_is_held_to_its_shape(tmp_path):
    """A typo in a contract must not pass. `on:` is YAML 1.1's `true`."""
    written = tmp_path / "v1.examples.yaml"
    written.write_text("examples:\n  one:\n    says: x\n    records:\n"
                       "      - record: a\n        on: '2026-01-01'\n",
                       encoding="utf-8")
    with pytest.raises(ExampleError) as raised:
        business.load(written)
    assert raised.value.code == "examples_not_understood"

    # `agreed` is only ever `false`, on a proposal: an agreed example is one
    # without it, so a hand-written `true` is not a way of agreeing.
    written.write_text("examples:\n  one:\n    says: x\n    agreed: true\n",
                       encoding="utf-8")
    with pytest.raises(ExampleError) as raised:
        business.load(written)
    assert raised.value.where.endswith("one.agreed")

    written.write_text("examples:\n  one:\n    records: []\n", encoding="utf-8")
    with pytest.raises(ExampleError) as raised:
        business.load(written)
    assert raised.value.where.endswith("one.says")
    assert business.load(tmp_path / "absent.examples.yaml") == {}


def test_the_examples_of_a_sealed_version_run_from_a_terminal(world, monkeypatch, capsys):
    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    assert modules_main(["examples", STOCK, "v2"]) == 0
    printed = capsys.readouterr().out
    assert "[holds] flour_in_and_out" in printed
    assert "ok IngredientStock flour on 2026-07-05, headroom: expected 6, got 6" in printed


# ---- the studio -----------------------------------------------------------

def _ruled(store, name):
    """A total, a level and a headroom, and not a word about what they come to."""
    step(store, name, "start", title="Balances",
         description="What is on hand, and how far above the level.")
    step(store, name, "pin", module=f"{dev_modules.CATALOG}@v3")
    step(store, name, "pin", module=f"{dev_modules.INVENTORY}@v3")
    step(store, name, "add_class", **{"class": "Balance",
                                      "description": "One row per ingredient."})
    for slot, kind in (("balance_thing", "Ingredient"), ("balance_on_hand", "decimal"),
                       ("balance_level", "decimal"), ("balance_headroom", "decimal")):
        # Every number says its unit and which way it runs.
        meant = ({"unit": "the unit of the ingredient", "direction": "level"}
                 if kind == "decimal" else {})
        step(store, name, "add_slot", slot=slot, range=kind,
             description=f"The {slot.replace('_', ' ')}.", **meant)
        step(store, name, "attach", **{"class": "Balance", "slot": slot})
    step(store, name, "aggregate", **{
        "class": "Balance", "column": "balance_on_hand",
        "over": "Flow", "sum": "amount", "by": "balance_thing=affects"})
    step(store, name, "parameter", **{
        "class": "Balance", "column": "balance_level",
        "of": "balance_thing", "slot": "ingredient_reorder_level"})
    step(store, name, "expression", **{
        "class": "Balance", "column": "balance_headroom",
        "expression": "{balance_on_hand} - {balance_level}"})
    return name


def _planned(store, name):
    """A plan the person agreed to, without which an agent takes no step."""
    studio.propose_plan(store, name, {"builds": "Balances."})
    studio.apply(store, name, "agree_plan", {})
    return name


def _flour(store, name, *, actor="person", headroom=True):
    """One example of what the rules come to, written by `actor`."""
    step(store, name, "add_example", actor, example="flour",
         says="25 kg came in and 5 were used: 20 on hand, 10 above a level of 10.")
    step(store, name, "record", actor, example="flour", record="flour",
         **{"class": "Ingredient"},
         facts="ingredient_code=FLR, ingredient_name=Flour, ingredient_unit=kg, "
               "ingredient_reorder_level=10")
    for record, code, quantity in (("in_1", "M1", "25"), ("used", "M2", "-5")):
        step(store, name, "record", actor, example="flour", record=record,
             **{"class": "StockMovement"},
             facts=f"movement_code={code}, movement_ingredient=flour, "
                   f"movement_quantity={quantity}, movement_happened_on=2026-06-02")
    step(store, name, "expect", actor, example="flour", table="Balance", row="flour",
         values="balance_on_hand=20, balance_level=10")
    if headroom:
        step(store, name, "expect", actor, example="flour", table="Balance",
             row="flour", values="balance_headroom=10")
    return name


def _an_application(store, name):
    """The rules, and one example of what they come to, a person's own."""
    return _flour(store, _ruled(store, name))


def test_the_studio_holds_every_change_to_the_examples(world, conn):
    name = _an_application(world, "@probe/balances")
    held = studio.examples_of(world, name)
    # The second `expect` of the same row added to the first.
    assert held["flour"]["expect"] == [{"table": "Balance", "row": "flour", "values": {
        "balance_on_hand": "20", "balance_level": "10", "balance_headroom": "10"}}]
    assert "expect  example=flour table=Balance row=flour" in studio.transcript(world, name)

    report = reading.state(world, name, conn)
    assert report["examples_run"] is True and report["sealable"] is True
    assert report["examples"][0]["passed"] is True

    # A change to a rule the example reads: the example catches it, and the
    # draft cannot be sealed while it does.
    step(world, name, "unrule", slot="balance_level")
    report = reading.state(world, name, conn)
    blocking = [h for h in report["holes"] if h["blocking"]]
    assert {h["kind"] for h in blocking} == {"example_failed"}
    assert {h["where"] for h in blocking} == {
        "example flour: Balance flour, balance_level",
        "example flour: Balance flour, balance_headroom"}
    assert report["sealable"] is False
    with pytest.raises(ExampleError) as raised:
        seal(conn, studio.path(world, name), actor_id="probe",
             into=studio.directory(world, name), store=world)
    assert raised.value.code == "example_failed"

    step(world, name, "parameter", **{
        "class": "Balance", "column": "balance_level",
        "of": "balance_thing", "slot": "ingredient_reorder_level"})
    out = seal(conn, studio.path(world, name), actor_id="probe",
               into=studio.directory(world, name), store=world)
    assert out["examples"].name == "v1.examples.yaml"
    assert business.load(out["examples"]) == held

    # A revision starts from the examples of the version it revises.
    step(world, name, "discard")
    assert studio.examples_of(world, name) == {}
    step(world, name, "revise")
    assert studio.examples_of(world, name) == held
    # A rename reaches the examples, as it reaches every rule.
    step(world, name, "rename_slot", slot="balance_on_hand", to="balance_stock")
    assert "balance_stock" in studio.examples_of(world, name)["flour"]["expect"][0]["values"]
    assert reading.state(world, name, conn)["examples"][0]["passed"] is True
    step(world, name, "discard")


def test_without_a_log_the_examples_are_listed_and_nothing_is_sealable(world):
    name = _an_application(world, "@probe/unrun")
    report = reading.state(world, name)
    assert report["examples_run"] is False
    assert report["examples"][0]["passed"] is None
    assert report["sealable"] is False
    step(world, name, "discard")
    assert not (world.place(name) / studio.EXAMPLES).exists()


def test_an_example_that_expects_nothing_is_an_open_question(world, conn):
    name = _an_application(world, "@probe/vague")
    step(world, name, "add_example", example="vague", says="Nothing in particular.")
    holes = {h["kind"]: h for h in reading.state(world, name, conn)["holes"]}
    assert holes["example_expects_nothing"]["blocking"] is False
    assert holes["example_expects_nothing"]["step"]["op"] == "expect"
    assert "Balance" in holes["example_expects_nothing"]["step"]["options"]
    step(world, name, "discard")


def test_the_example_steps_refuse_what_they_cannot_do(world):
    name = _an_application(world, "@probe/refused")
    with pytest.raises(StudioError) as raised:
        step(world, name, "record", example="nothing", record="x",
             **{"class": "Ingredient"})
    assert raised.value.code == "no_such_example"
    assert raised.value.repairs[0].options == ("flour",)

    with pytest.raises(StudioError) as raised:
        step(world, name, "unrecord", example="flour", record="sugar")
    assert raised.value.code == "not_in_example"
    assert raised.value.repairs[0].options == ("flour", "in_1", "used")

    with pytest.raises(StudioError) as raised:
        step(world, name, "unexpect", example="flour", table="Balance", row="sugar")
    assert raised.value.code == "not_in_example"
    assert raised.value.repairs[0].options == ("Balance flour",)

    with pytest.raises(StudioError) as raised:
        step(world, name, "record", example="flour", record="empty")
    assert raised.value.code == "nothing_entered"

    offered = {s["op"]: s for s in reading.steps(world, name, studio.open_draft(world, name))}
    takes = {t["name"]: t for t in offered["unrecord"]["takes"]}
    assert takes["example"]["options"] == ["flour"]
    assert takes["record"]["depends"] == "example"
    step(world, name, "discard")


def test_a_record_is_refused_without_what_its_class_requires_and_corrected_on_the_day(
        world, conn):
    name = _an_application(world, "@probe/corrected")
    step(world, name, "add_example", example="late", says="Sugar came in.")
    step(world, name, "record", example="late", record="sugar",
         **{"class": "Ingredient"}, facts="ingredient_code=SUG, ingredient_unit=kg")
    # The first time a record is stated, its class's required facts are asked
    # for at the step, not found later in a failing example.
    with pytest.raises(StudioError) as raised:
        step(world, name, "record", example="late", record="in", when="2026-06-02",
             **{"class": "StockMovement"},
             facts="movement_code=S1, movement_ingredient=sugar, movement_quantity=4")
    assert raised.value.code == "required_missing"
    assert raised.value.repairs[0].options == ("inventory__movement_happened_on",)
    assert [r["record"] for r in studio.examples_of(world, name)["late"]["records"]] == ["sugar"]

    # Stated again on the same day, a record is that statement corrected: one
    # statement, keeping the class it was given before.
    step(world, name, "record", example="late", record="sugar",
         facts="ingredient_code=SUG, ingredient_name=Sugar, ingredient_unit=kg")
    records = studio.examples_of(world, name)["late"]["records"]
    # Kept under the catalog's full names, as the draft keeps them.
    assert records == [{"record": "sugar", "class": "catalog__Ingredient", "facts": {
        "catalog__ingredient_code": "SUG", "catalog__ingredient_name": "Sugar",
        "catalog__ingredient_unit": "kg"}}]

    # A later day is that record changing, and need not say everything again.
    step(world, name, "record", example="late", record="in", when="2026-06-02",
         **{"class": "StockMovement"},
         facts="movement_code=S1, movement_ingredient=sugar, movement_quantity=4, "
               "movement_happened_on=2026-06-02")
    step(world, name, "record", example="late", record="in", when="2026-06-03",
         facts="movement_quantity=5")
    step(world, name, "expect", example="late", table="Balance", row="sugar",
         values="balance_on_hand=5")
    report = reading.state(world, name, conn)
    assert {e["name"]: e["passed"] for e in report["examples"]} == {"flour": True, "late": True}
    step(world, name, "discard")


def test_the_api_answers_a_step_with_the_examples_run(world, monkeypatch):
    """Over HTTP the examples run too, on a connection of the API's own."""
    from starlette.testclient import TestClient

    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    name = _an_application(world, "@probe/served-examples")
    client = TestClient(app)
    after = client.post("/api/studio/step", json={
        "name": name, "step": "expect",
        "args": {"example": "flour", "table": "Balance", "row": "flour",
                 "values": {"balance_on_hand": "21"}}}).json()
    assert after["examples_run"] is True
    [example] = after["examples"]
    assert example["passed"] is False
    [refusal] = example["refusals"]
    assert (refusal["code"], refusal["got"]) == ("example_failed", "20")
    assert after["sealable"] is False
    # Over HTTP it is a person's step: the page is what a person uses.
    assert "  person  expect  example=flour" in studio.transcript(world, name)
    step(world, name, "discard")


# ---- whose word it is, and what the examples owe the map ------------------

def _owed(report):
    return [h for h in report["holes"] if h["kind"] == "column_unchecked"]


def test_every_computed_column_owes_a_number_to_an_example(world, conn, tmp_path):
    """A map that computes a column claims some number is right. Until an
    example says which, nothing holds the rule to anything, and the draft
    cannot be sealed. A vocabulary computes nothing and owes nothing."""
    name = _ruled(world, "@probe/owing")
    report = reading.state(world, name, conn)
    owed = _owed(report)
    assert [h["where"] for h in owed] == [
        "Balance.balance_headroom", "Balance.balance_level", "Balance.balance_on_hand"]
    assert all(h["blocking"] for h in owed)
    assert owed[0]["question"] == ("what number should Balance's balance_headroom "
                                   "come to, in an example the business agrees with?")
    # With no example yet, the answer is to write one; the opening that asks
    # for examples in general would only say the same thing again.
    assert owed[0]["step"]["op"] == "add_example"
    assert "no_examples" not in {h["kind"] for h in report["holes"]}
    assert report["sealable"] is False

    into = tmp_path / "into"
    before = _log_size(conn)
    with pytest.raises(ExampleError) as raised:
        seal(conn, studio.path(world, name), actor_id="probe", into=into, store=world)
    assert raised.value.code == "column_unchecked"
    assert raised.value.where.startswith("Balance.")
    assert not into.exists()
    assert _log_size(conn) == before

    # An example checking two of the three leaves the third owed, and the step
    # that answers it now names the example it can go in.
    _flour(world, name, headroom=False)
    owed = _owed(reading.state(world, name, conn))
    assert [h["where"] for h in owed] == ["Balance.balance_headroom"]
    assert owed[0]["step"] == {"op": "expect", "args": {"table": "Balance"},
                               "choose": "example", "options": ["flour"]}
    step(world, name, "expect", example="flour", table="Balance", row="flour",
         values="balance_headroom=10")
    report = reading.state(world, name, conn)
    assert _owed(report) == [] and report["sealable"] is True
    step(world, name, "discard")


def test_an_example_an_agent_writes_is_a_proposal_until_a_person_agrees(world, conn):
    name = _planned(world, _ruled(world, "@probe/proposed"))
    name = _flour(world, name, actor="agent", headroom=False)
    assert studio.examples_of(world, name)["flour"]["agreed"] is False
    # The transcript says who took every step.
    said = studio.transcript(world, name)
    assert "  person  add_class  class=Balance" in said
    assert "  agent  add_example  example=flour" in said

    # A proposal runs and its numbers show: a person agrees to numbers they can
    # see. It cannot be sealed until they do.
    report = reading.state(world, name, conn)
    [example] = report["examples"]
    assert (example["passed"], example["agreed"]) == (True, False)
    blocking = {h["kind"]: h for h in report["holes"] if h["blocking"]}
    assert set(blocking) == {"example_not_agreed", "column_unchecked"}
    assert blocking["example_not_agreed"]["step"] == {
        "op": "agree_example", "args": {"example": "flour"},
        "choose": "example", "options": ["flour"]}
    assert blocking["example_not_agreed"]["question"] == (
        "is the example flour what the business does, and are its numbers right?")

    # Its own proposal the agent may go on changing.
    step(world, name, "expect", "agent", example="flour", table="Balance",
         row="flour", values="balance_headroom=10")
    with pytest.raises(ExampleError) as raised:
        seal(conn, studio.path(world, name), actor_id="probe",
             into=studio.directory(world, name), store=world)
    assert raised.value.code == "example_not_agreed"

    # Only a person agrees.
    with pytest.raises(StudioError) as raised:
        step(world, name, "agree_example", "agent", example="flour")
    assert raised.value.code == "person_only"
    step(world, name, "agree_example", example="flour")
    assert "agreed" not in studio.examples_of(world, name)["flour"]
    assert "  person  agree_example  example=flour" in studio.transcript(world, name)

    assert reading.state(world, name, conn)["sealable"] is True
    out = seal(conn, studio.path(world, name), actor_id="probe",
               into=studio.directory(world, name), store=world)
    assert "agreed" not in business.load(out["examples"])["flour"]
    step(world, name, "discard")


def test_an_agent_cannot_change_an_example_a_person_agreed_to(world):
    """Otherwise a failing map could be made to pass by changing the answer
    rather than the rule. Not the agent's judgement: who it is."""
    name = _planned(world, _an_application(world, "@probe/agreed"))
    before = studio.examples_of(world, name)
    said = studio.transcript(world, name)
    for op, args in (
            ("set_example", {"example": "flour", "field": "says", "value": "x"}),
            ("remove_example", {"example": "flour"}),
            ("record", {"example": "flour", "record": "extra", "class": "Ingredient"}),
            ("unrecord", {"example": "flour", "record": "used"}),
            ("expect", {"example": "flour", "table": "Balance", "row": "flour",
                        "values": "balance_on_hand=21"}),
            ("unexpect", {"example": "flour", "table": "Balance", "row": "flour"})):
        with pytest.raises(StudioError) as raised:
            studio.apply(world, name, op, args, actor="agent")
        assert (raised.value.code, raised.value.where) == ("example_agreed", f"{op}: flour")
        assert raised.value.repairs[0].options == ("add_example",)
    assert studio.examples_of(world, name) == before
    assert studio.transcript(world, name) == said

    # A rename is not a change to what the business said, and reaches every
    # example whoever makes it.
    step(world, name, "rename_slot", "agent", slot="balance_on_hand", to="balance_stock")
    assert "balance_stock" in studio.examples_of(world, name)["flour"]["expect"][0]["values"]
    # A person changes their own word.
    step(world, name, "expect", example="flour", table="Balance", row="flour",
         values="balance_stock=20")

    with pytest.raises(ValueError):
        studio.apply(world, name, "discard", {}, actor="somebody")
    step(world, name, "discard")

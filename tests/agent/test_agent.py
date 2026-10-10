"""The agent's tools, its guide, and the agent played from a script.

What has to hold with no model anywhere:

    its tools      six, and none that seals or agrees; every step through them
                   is an agent's step, held to what an agent may do.
    the order      no rule before the person agreed to a plan and to an
                   example for its table; an example waiting for its rules
                   can be put to them, one that has not run cannot.
    a plan         kept beside the draft as the person was shown it, agreed
                   to only by them, and said to the agent with every request.
    their text     what comes back says what the draft is standing in and how
                   to get out, and is short enough to read on every turn.
    their shape    flat: a model on any provider, or one run at home, can
                   write the arguments.
    the guide      generated from the system, and naming every step, every
                   refusal and every opening in it.
    a rehearsal    a scripted builder, through the same agent a model would
                   drive, builds an application in three requests — a plan,
                   the examples, the rules — is held to that order, is caught
                   making a mistake, is sent back for proposing too early and
                   for numbers it chose itself, and ends with a proposal a
                   person seals.
    the accountant reads the person's words and the situation, nothing else;
                   a proposal carries its numbers or does not go out.
    a session      stops at the budget, keeps the conversation beside the
                   draft, and hands a model earlier turns as they were said.
"""

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))

import dev_modules  # noqa: E402
from compile import SYNTAX  # noqa: E402
from components.agent import builder as building  # noqa: E402
from components.agent import guide as guide_read  # noqa: E402
from components.agent import config as configuration  # noqa: E402
from components.agent import conversation as kept  # noqa: E402
from components.agent import rehearsal, tools  # noqa: E402
from components.agent.session import Session, Stopped, person_agrees  # noqa: E402
from components.agent.__main__ import main as agent_main  # noqa: E402
from components.examples import examples as business  # noqa: E402
from components.modules.roles import NOT_TAUGHT  # noqa: E402
from components.refusal import CODES  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio.read import ANSWERS, OPEN  # noqa: E402
from perform import connect  # noqa: E402
from seal import seal  # noqa: E402

SCRIPT = Path(__file__).parent / "fixtures" / "rehearsal.yaml"


@pytest.fixture(scope="module")
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def world(conn, tmp_path_factory):
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    return store


@pytest.fixture(scope="module")
def bench(world):
    return tools.Bench(world, dsn=os.environ["UNITI_DSN"])


def step(op, **args):
    return {"op": op, "args": [{"name": k, "value": v} for k, v in args.items()]}


ON_HAND = step("aggregate", **{"class": "Level", "column": "level_on_hand", "over": "Flow",
                                "sum": "amount", "by": "level_thing=affects"})


def _planned(store, name):
    """A plan the person agreed to: nothing is built by an agent before one."""
    studio.propose_plan(store, name, {"builds": "On hand per ingredient."})
    studio.apply(store, name, "agree_plan", {})


def _started(bench, name, *, ruled=True):
    """Level, by the agent once the person agreed to its plan; with `ruled`,
    its on-hand total too, which the agent writes once the person agreed to
    an example for Level as well."""
    _planned(bench.store, name)
    said = tools.do(bench, name, [
        step("start", title="Levels", description="What is on hand."),
        step("pin", module=f"{dev_modules.CATALOG}@v3"),
        step("pin", module=f"{dev_modules.INVENTORY}@v3"),
        step("add_class", **{"class": "Level", "description": "One row per ingredient."}),
        step("add_slot", slot="level_thing", range="Ingredient", description="The thing."),
        step("attach", **{"class": "Level", "slot": "level_thing"}),
        step("add_slot", slot="level_on_hand", range="decimal", description="On hand.",
             unit="the unit of the ingredient", direction="level"),
        step("attach", **{"class": "Level", "slot": "level_on_hand"}),
    ])
    if not ruled:
        return said
    _agreed(bench.store, name)
    return tools.do(bench, name, [ON_HAND])


def _agreed(store, name):
    """An example for Level, agreed to by the person, as was the plan."""
    for op, args in (
            ("add_example", {"example": "base", "says": "Two came in."}),
            ("record", {"example": "base", "record": "base_thing", "class": "Ingredient",
                        "facts": "ingredient_code=B, ingredient_name=Base, ingredient_unit=kg"}),
            ("record", {"example": "base", "record": "base_in", "class": "StockMovement",
                        "facts": "movement_code=M0, movement_ingredient=base_thing, "
                                 "movement_quantity=2, movement_happened_on=2026-06-01"}),
            ("expect", {"example": "base", "table": "Level", "row": "base_thing",
                        "values": "level_on_hand=2"})):
        studio.apply(store, name, op, args)


# ---- the tools -------------------------------------------------------------

def _offered():
    """The tools and the endings the agent offers a model, as a model sees them."""
    from pydantic_ai import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel
    seen = {}

    def peek(messages, info):
        seen["tools"] = {t.name: t.parameters_json_schema for t in info.function_tools}
        seen["endings"] = {t.name: t.parameters_json_schema for t in info.output_tools}
        return ModelResponse(parts=[ToolCallPart(
            next(t for t in seen["endings"] if t.endswith("_Reply")), {"message": "ok"})])

    building.builder(FunctionModel(peek)).run_sync("hello", deps=building.Work(bench=None))
    return seen


def test_the_agent_has_six_tools_and_none_that_seals_or_agrees():
    offered = _offered()
    assert set(offered["tools"]) == {"look", "options", "do", "catalogue", "guide", "reckon"}
    assert set(offered["endings"]) == {"final_result_Reply", "final_result_Question",
                                       "final_result_Plan", "final_result_Proposal"}


def _example_one(bench, name):
    """The agent's own example for Level: one thing, two of it in."""
    return tools.do(bench, name, [
        step("add_example", example="one", says="Two in."),
        step("record", example="one", record="thing", **{"class": "Ingredient"},
             facts="ingredient_code=T, ingredient_name=Thing, ingredient_unit=kg"),
        step("record", example="one", record="in", **{"class": "StockMovement"},
             facts="movement_code=M1, movement_ingredient=thing, movement_quantity=2, "
                   "movement_happened_on=2026-06-02"),
        step("expect", example="one", table="Level", row="thing", values="level_on_hand=2"),
    ])


def test_every_step_through_the_tools_is_an_agents(bench, world):
    name = "@probe/agents-own"
    _started(bench, name, ruled=False)
    lines = [line for line in studio.transcript(world, name).splitlines()
             if line and not line.startswith((" ", "#"))]
    # The person's agreement to the plan first, and every step after it the agent's.
    assert "  person  agree_plan" in lines[0]
    assert lines[1:] and all("  agent  " in line for line in lines[1:])

    # An agent cannot agree, through this or any tool.
    said = _example_one(bench, name)
    assert "[waits for its rules] one (proposed, not agreed yet)" in said
    said = tools.do(bench, name, [step("agree_example", example="one")])
    assert "1. refused: agree_example example=one" in said
    assert "[person_only]" in said
    assert studio.examples_of(world, name)["one"]["agreed"] is False

    # An example a person agreed to stays theirs.
    studio.apply(world, name, "agree_example", {"example": "one"})
    said = tools.do(bench, name, [step("set_example", example="one", field="says",
                                       value="Something else.")])
    assert "[example_agreed]" in said
    assert studio.examples_of(world, name)["one"]["says"] == "Two in."
    tools.do(bench, name, [step("discard")])


def test_nothing_is_built_before_the_person_agreed_to_a_plan(bench, world):
    # Not even the draft: what is built is the person's to agree to first.
    name = "@probe/unplanned-build"
    said = tools.do(bench, name, [step("start", title="Levels", description="D.")])
    assert "[plan_not_agreed] start" in said and "got no plan yet" in said
    assert not studio.path(world, name).exists()
    studio.propose_plan(world, name, {"builds": "On hand per ingredient."})
    said = tools.do(bench, name, [step("start", title="Levels", description="D.")])
    assert "got a plan the person has not agreed to yet" in said
    # Only the person agrees to a plan.
    assert "[person_only]" in tools.do(bench, name, [step("agree_plan")])
    studio.apply(world, name, "agree_plan", {})
    assert "1. done: start" in tools.do(bench, name, [step("start", title="Levels",
                                                               description="D.")])
    # A plan put forward again stops the building until it is agreed anew.
    studio.propose_plan(world, name, {"builds": "Something else."})
    said = tools.do(bench, name, [step("add_class", **{"class": "Level",
                                                       "description": "A row."})])
    assert "[plan_not_agreed] add_class" in said
    # A person building by hand is not held to it.
    studio.apply(world, name, "add_class", {"class": "Level", "description": "A row."})
    studio.apply(world, name, "discard", {})


def test_no_rule_before_the_person_agreed_to_a_plan_and_an_example(bench, world):
    # The order is the system's to keep: first what is built, then what the
    # numbers must be, then how they are worked out.
    name = "@probe/in-order"
    _started(bench, name, ruled=False)
    said = tools.do(bench, name, [ON_HAND])
    assert "[no_agreed_example] aggregate: Level.level_on_hand" in said
    # An example the agent proposed is not one the person agreed to.
    said = _example_one(bench, name)
    assert "An example waiting for its rules is put to the person as it is" in said
    assert "[no_agreed_example]" in tools.do(bench, name, [ON_HAND])
    studio.apply(world, name, "agree_example", {"example": "one"})
    said = tools.do(bench, name, [ON_HAND])
    assert "1. done: aggregate class=Level column=level_on_hand" in said
    assert "[holds] one: Two in." in said
    # A person building by hand is not held to it.
    studio.apply(world, name, "unrule", {"slot": "level_on_hand"})
    studio.propose_plan(world, name, {"builds": "Something else."})
    studio.apply(world, name, "aggregate", {"class": "Level", "column": "level_on_hand",
                                            "over": "Flow", "sum": "amount",
                                            "by": "level_thing=affects"})
    # The agreements are in the transcript, the person's among the agent's.
    people = [line.split("  ")[2] for line in studio.transcript(world, name).splitlines()
              if "  person  " in line]
    assert people == ["agree_plan", "agree_example", "unrule", "aggregate"]
    # A plan put forward again stops the agent, even from discarding; a person may.
    assert "[plan_not_agreed] discard" in tools.do(bench, name, [step("discard")])
    studio.apply(world, name, "discard", {})
    assert studio.plan_of(world, name) is None


def test_a_batch_stops_at_the_first_refusal_and_says_how_to_fix_it(bench, world):
    name = "@probe/stopped"
    _started(bench, name, ruled=False)
    said = tools.do(bench, name, [
        step("add_slot", slot="level_note", description="A note."),
        step("attach", **{"class": "Nothing", "slot": "level_note"}),
        step("attach", **{"class": "Level", "slot": "level_note"}),
    ])
    assert "1. done: add_slot slot=level_note" in said
    assert "2. refused: attach class=Nothing slot=level_note" in said
    assert "[not_yours]" in said and "one of: Level" in said
    assert "Step 3 was not taken." in said
    assert "level_note" not in studio.open_draft(world, name)["classes"]["Level"]["slots"]
    # What the draft is standing in comes back after a refusal too.
    assert "Holes:" in said
    tools.do(bench, name, [step("discard")])


def test_the_tools_answer_in_text_short_enough_to_read_every_turn(bench):
    name = "@probe/short"
    _started(bench, name)
    looked = tools.look(bench, name)
    assert looked.startswith("@probe/short — Levels: draft of v1, a new module")
    assert ("level_on_hand: decimal, unit the unit of the ingredient, level = aggregate "
            "over Flow, sum amount, by level_thing=affects") in looked
    assert len(looked) < 2500
    around = tools.look(bench, name, "around")
    assert "Ingredient (" in around and "Resource: binds no binding" in around
    # A role no new module is asked to fill is not in sight, though the
    # draft totals over it: nothing here fills it.
    assert "  Flow:" not in around and "  Event:" not in around
    offered = tools.options(bench, name, "parameter")
    assert "of (a slot of the class named), depends on class" in offered
    assert len(offered) < 3000
    assert "no part 'everything'" in tools.look(bench, name, "everything")
    assert "no step 'fly'" in tools.options(bench, name, "fly")
    # Several steps in one call, each as it would be alone.
    both = tools.options(bench, name, "parameter, expression")
    assert both == offered + "\n" + tools.options(bench, name, "expression")
    found = tools.catalogue(bench, kind="role")
    # Still found, so a module sealed under it can still be read and totalled,
    # but said to be no role for new work, and without the text teaching it.
    assert ("role Flow (@uniti/core@v2), kept for the modules sealed under it: fill "
            "no new class with it; binds amount, affects, moment" in found)
    assert "the role that makes a balance possible" not in found
    assert "Nothing matches" in tools.catalogue(bench, text="zzz-nothing")
    # A pinned version reads as its module, and several modules go in one call.
    assert "role Transaction (@uniti/transaction@v1)" in found
    core = tools.catalogue(bench, kind="role", module="@uniti/core@v2")
    assert "role Flow (@uniti/core@v2)" in core and "Transaction" not in core
    assert tools.catalogue(bench, kind="role", module="@uniti/core, @nobody/here") == core
    # Each module says its kind, so the library is told from the rest.
    assert "(standard library) — " in tools.catalogue(bench, kind="module",
                                                      module="@uniti/party")
    assert "(community module) — " in tools.catalogue(bench, kind="module",
                                                      module="@demo/inventory")
    # A class says what a new record of it must be given.
    assert ("a new one must be given movement_code, movement_ingredient, "
            "movement_quantity, movement_happened_on"
            in tools.catalogue(bench, text="StockMovement", kind="class"))
    tools.do(bench, name, [step("discard")])


def test_the_note_opening_a_request_says_which_kind_is_open_and_whom_it_helps(world):
    opened = guide_read.opened
    assert "standard library: you help its keepers." in opened(world, "@uniti/party")
    assert "community module: you help its author." in opened(world, "@demo/inventory")
    assert ("an application of the business demo: you help its composer."
            in opened(world, "@demo/stock"))
    # Not started yet: the library by its name; otherwise the person is asked.
    assert "`start` it as a library." in opened(world, "@uniti/brand-new")
    asked = opened(world, "@kemah/rental", business="kemah")
    assert "ask whether it serves this business alone" in asked
    assert "named @kemah/..." in asked
    assert "it will be a community module." in opened(world, "@kemah/rental")
    # The guide every request starts with is the same whichever kind is open.
    assert guide_read.KINDS_OF_MODULE in guide_read.instructions()


def test_a_module_not_started_yet_is_said_so_in_the_agents_terms(bench):
    # Not the store's refusal, which speaks of roots and environment variables.
    said = tools.look(bench, "@probe/unborn")
    assert said.startswith("There is no module @probe/unborn yet. The step `start`")
    assert "UNITI_PACKAGES" not in said
    # Started and empty, it is no reason to stop.
    _planned(bench.store, "@probe/unborn")
    said = tools.do(bench, "@probe/unborn", [step("start", title="T", description="D.")])
    assert "It declares nothing yet; build what the person asked for." in said
    assert "Propose it" not in said
    tools.do(bench, "@probe/unborn", [step("discard")])


def test_what_the_system_cannot_do_yet_is_refused_as_such(bench):
    # Not as a misspelt argument, which only sends a builder to try another.
    name = "@probe/not-yet"
    _started(bench, name)
    for extra, where in (({"where": "level_thing>0"}, "aggregate: where"),
                         ({"by": "level_thing=affects.ingredient_supplier.supplier_name"},
                          "aggregate: by")):
        said = tools.do(bench, name, [step("aggregate", **{
            "class": "Level", "column": "level_on_hand", "over": "Flow", "sum": "amount",
            "by": "level_thing=affects", **extra})])
        assert f"[not_possible_yet] {where}" in said
        assert "tell the person so" in said
    tools.do(bench, name, [step("discard")])


def _defects(schema, where="$"):
    """Every construct in a JSON schema some provider or small model trips on."""
    out = []
    if isinstance(schema, dict):
        for key in ("anyOf", "oneOf", "allOf"):
            if key in schema:
                out.append(f"{where}: {key}")
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict) or extra is True:
            out.append(f"{where}: a map with free keys")
        for key, value in schema.items():
            out += _defects(value, f"{where}.{key}")
    elif isinstance(schema, list):
        for i, value in enumerate(schema):
            out += _defects(value, f"{where}[{i}]")
    return out


def test_every_tool_and_every_ending_is_flat_enough_for_any_model():
    offered = _offered()
    for name, schema in {**offered["tools"], **offered["endings"]}.items():
        assert _defects(schema) == [], name
    # The step names are offered as a closed list.
    do_schema = str(offered["tools"]["do"])
    assert "agree_example" in do_schema and "aggregate" in do_schema


# ---- the guide -------------------------------------------------------------

def test_the_guide_names_everything_the_system_has(world):
    everything = "\n".join(guide_read.section(t, world) for t in guide_read.TOPICS)
    for op in studio.OPERATIONS:
        assert f"\n{op}: " in everything, op
    for code in CODES:
        assert f"    {code}: " in everything, code
    for kind in OPEN:
        assert f"    {kind}: " in everything, kind
    for code in ANSWERS:
        assert code in everything, code
    for kind in business.COMPUTED:
        assert f"`{kind}`" in everything, kind
    assert SYNTAX in everything
    # Every role in the store: those a new module fills with what they bind,
    # and core's retired ones named once, as kept and not to be filled.
    assert "Transaction (@uniti/transaction@v1, a kind of Event, Thing)" in everything
    assert "binding transaction_counterparty: Party" in everything
    assert "Resource (@uniti/core@v2, a kind of Thing)" in everything
    assert ("Kept only for the modules sealed under them, and filled by no new "
            "class: Event (@uniti/core@v2), Flow (@uniti/core@v2).") in everything
    assert "There is no topic 'nope'" in guide_read.section("nope")


def test_no_new_module_is_asked_to_fill_what_core_v3_may_remove(bench, world):
    """ECOSYSTEM_PLAN.md step 0: `Flow` and `Event`'s `moment` are no longer
    taught or offered, so nothing is built on them that core v3 may remove.
    Core is unchanged, and what was sealed under them still reads."""
    retired = NOT_TAUGHT
    text = guide_read.instructions()
    # Said once, and as what not to do; a date says its moment otherwise.
    assert ("Core's `Event` and `Flow` stay only for modules sealed under them: "
            "fill neither directly.") in " ".join(text.split())
    assert "`time_meaning`" in text
    assert "Fill the shared roles" not in text and "Fill the library's roles" in text
    roles = guide_read.section("roles", world)
    for role in retired:
        assert f"\n{role} (" not in roles and f"binding {role}" not in roles
    assert "binding amount" not in roles and "binding affects" not in roles

    # Neither is offered where a role is chosen, and choosing one still works:
    # a module sealed under it is revised as before.
    name = "@probe/retired"
    _planned(bench.store, name)
    tools.do(bench, name, [
        step("start", title="Retired", description="D."),
        step("pin", module=f"{dev_modules.INVENTORY}@v3"),
        step("add_class", **{"class": "Gift", "description": "A gift."}),
        step("add_slot", slot="gift_note", description="What it says."),
        step("attach", **{"class": "Gift", "slot": "gift_note"})])
    offered = tools.options(bench, name, "fill_role")
    looked = tools.look(bench, name)
    for role in retired:
        assert not re.search(rf"one of: [^\n]*\b{role}\b", offered + looked), role
    assert re.search(r"one of: [^\n]*\bResource\b", offered + looked)
    said = tools.do(bench, name, [step("fill_role", **{"class": "Gift", "role": "Nope"})])
    assert "[not_a_role]" in said and "Resource" in said
    assert not re.search(r"one of: [^\n]*\bFlow\b", said)
    said = tools.do(bench, name, [step("fill_role", **{"class": "Gift", "role": "Flow"})])
    assert "1. done: fill_role" in said
    tools.do(bench, name, [step("discard")])


def test_the_instructions_are_what_every_build_needs_and_a_list_of_the_rest():
    text = guide_read.instructions()
    assert text.startswith(guide_read.WORKFLOW)
    # The topics every build reads are given, so no call is spent on them.
    for topic in guide_read.GIVEN:
        assert guide_read.section(topic) in text
    for topic in guide_read.TOPICS:
        if topic not in guide_read.GIVEN:
            assert f"    {topic}: " in text
    # Short enough to sit at the top of every call: about five and a half
    # thousand tokens, the recording standard and the kinds of module
    # included, which every build follows.
    assert len(text) < 22500


# ---- a proposal is checked -------------------------------------------------

def test_a_proposal_says_no_more_than_the_draft_bears_out(bench, world):
    name = "@probe/proposed"
    _started(bench, name)
    work = building.Work(bench=bench)
    unsupported = building.unsupported
    proposal = building.Proposal
    assert "is not an example" in unsupported(
        work, proposal(module=name, message="m", agree=["ghost"]))
    _example_one(bench, name)
    tools.do(bench, name, [step("expect", example="one", table="Level", row="thing",
                                values="level_on_hand=3")])
    assert "it is not ready" in unsupported(
        work, proposal(module=name, message="m", seal=True))
    assert "fails" in unsupported(work, proposal(module=name, message="m", agree=["one"]))
    # An example nobody ran cannot go to the person: nobody knows what it does.
    unrun = building.Work(bench=tools.Bench(world))
    assert "one has not run" in unsupported(
        unrun, proposal(module=name, message="m", agree=["one"]))
    tools.do(bench, name, [step("expect", example="one", table="Level", row="thing",
                                values="level_on_hand=2")])
    ready = proposal(module=name, message="m", agree=["one"], seal=True)

    # Passing is not enough: the numbers must be the accountant's.
    assert "nobody but you worked out the numbers of one" in unsupported(work, ready)
    reckonings = work.conversation.reckonings
    reckonings["one"] = {"happened": [], "wanted": [], "question": "Which way?",
                         "figures": [], "by": "test"}
    assert "left a question open about one: Which way?" in unsupported(work, ready)
    reckonings["one"].update(question="", figures=[
        {"figure": "on hand", "value": "3", "working": "a guess"}])
    assert "expects Level thing level_on_hand = 2, which the accountant did not" \
        in unsupported(work, ready)
    reckonings["one"]["figures"][0]["value"] = "2.00"
    assert unsupported(work, ready) is None
    shown = building.put_before(work, ready)
    assert "worked out by the accountant, from your words:" in shown
    assert "on hand = 2.00: a guess" in shown

    studio.apply(world, name, "agree_example", {"example": "one"})
    assert "agreed already" in unsupported(
        work, proposal(module=name, message="m", agree=["one"]))
    tools.do(bench, name, [step("discard")])


# ---- a plan -----------------------------------------------------------------

def test_a_plan_is_kept_beside_the_draft_and_only_the_person_agrees_to_it(bench, world):
    name = "@probe/planned"
    plan = {"end": "Plan", "args": {
        "message": "Shall I?", "builds": "On hand per ingredient.",
        "records": ["Stock movements, as recorded already."],
        "reuses": ["Ingredients, from a community module."],
        "elsewhere": ["Suppliers belong in the standard library."],
        "numbers": ["On hand per ingredient."], "cannot": []}}
    # A plan before the catalogue is searched is sent back; after it, it goes.
    turn = Session(bench, name, _scripted([
        plan, {"tool": "catalogue", "args": {"text": "stock"}}, plan,
    ])).ask("What is on hand?")
    assert turn.ended == "Plan" and turn.output.builds == "On hand per ingredient."
    sent_back = "\n".join(rehearsal.trace(turn.messages))
    assert "search the catalogue for what they described first" in sent_back
    # Kept as the person was shown it, before there is a draft, and not agreed.
    held = studio.plan_of(world, name)
    assert held["builds"] == "On hand per ingredient." and held["agreed"] is False
    assert held["reuses"] == ["Ingredients, from a community module."]
    assert held["elsewhere"] == ["Suppliers belong in the standard library."]
    assert "message" not in held and not studio.path(world, name).exists()
    assert guide_read.opened(world, name).endswith(
        "Your plan waits for the person's agreement: nothing is built until then.)")
    # The person agrees — before the module is started — and the agent is told.
    assert person_agrees(world, name, turn.output) == ["plan"]
    held = studio.plan_of(world, name)
    assert held["agreed"] is True and held["agreed_at"]
    assert guide_read.opened(world, name).endswith("The person agreed to your plan.)")
    assert "  person  agree_plan" in studio.transcript(world, name)
    # A plan put forward again is the one in front of the person: agreed anew.
    Session(bench, name, _scripted([plan])).ask("Change it.")
    assert studio.plan_of(world, name)["agreed"] is False
    with pytest.raises(studio.StudioError) as refused:
        studio.apply(world, name, "agree_plan", {}, actor="agent")
    assert refused.value.code == "person_only"
    with pytest.raises(studio.StudioError) as refused:
        studio.apply(world, "@probe/unplanned", "agree_plan", {})
    assert refused.value.code == "no_plan"


# ---- a rehearsal ------------------------------------------------------------

def test_a_scripted_builder_builds_an_application_a_person_then_seals(bench, world, conn):
    script = rehearsal.load(SCRIPT)
    name = script["module"]
    turns = rehearsal.play_through(bench, script)
    assert [t.ended for t in turns] == ["Plan", "Proposal", "Proposal"]
    planned, proposed, ready = turns
    lines = ["\n".join(rehearsal.trace(t.messages)) for t in turns]

    # First a plan, which the person agreed to.
    assert planned.output.numbers[0] == "On hand per ingredient, every movement added up."
    assert studio.plan_of(world, name)["agreed"] is True
    # Then the examples. A rule written before any was agreed to was refused,
    # saying what comes first; numbers the builder chose itself were sent back.
    assert "[no_agreed_example] aggregate: Level.level_on_hand" in lines[1]
    assert "nobody but you worked out the numbers of flour" in lines[1]
    assert "flour on hand = 20 — 25 kg came in and 5 kg were used" in lines[1]
    assert proposed.output.agree == ["flour"] and not proposed.output.seal
    assert "[waits for its rules] flour (proposed, not agreed yet)" in proposed.shown
    assert ".. Level flour, level_headroom: expected 10, no rule computes it yet" \
        in proposed.shown
    assert "how far flour is above its reorder level = 10: 20 kg on hand less" \
        in proposed.shown
    # Then the rules, once the person agreed. The mistake was caught by the
    # next read, with the fix in hand; proposing too early was sent back.
    assert "one of: {level_on_hand} - {level_reorder}" in lines[2]
    assert "sent back: That proposal cannot go to the person: it is not ready" in lines[2]
    assert (ready.output.agree, ready.output.seal) == ([], True)
    assert ready.shown.endswith("Ready to be sealed as v1.")
    # Nothing it was shown asks for a role core v3 may remove: neither is
    # offered as a choice nor taught, and the total names the class it counts.
    shown = guide_read.instructions() + "\n" + "\n".join(lines)
    for role in NOT_TAUGHT:
        assert not re.search(rf"one of: [^\n]*\b{role}\b", shown), role
        assert not re.search(rf"over[=:] ?{role}\b", shown), role
        for line in shown.splitlines():
            if f"role {role} (" in line:
                assert "fill no new class with it" in line, line
    assert "binding moment" not in shown and "bind moment" not in shown
    assert "over=StockMovement sum=movement_quantity" in lines[2]

    # The conversation is beside the draft: each request, how it ended, and
    # what the accountant worked out.
    held = kept.load(world, name)
    assert [t["ended"] for t in held.turns] == ["Plan", "Proposal", "Proposal"]
    assert [t["person"] for t in held.turns] == [r["says"] for r in script["requests"]]
    assert held.reckonings["flour"]["figures"][0]["value"] == "20"
    assert [t["spent"]["requests"] for t in held.turns] == [
        len(r["moves"]) + (1 if any(m.get("tool") == "reckon" for m in r["moves"]) else 0)
        for r in script["requests"]]

    # Every step was the agent's but the two agreements; the person seals.
    people = [line.split("  ")[2] for line in studio.transcript(world, name).splitlines()
              if "  person  " in line]
    assert people == ["agree_plan", "agree_example"]
    out = seal(conn, studio.path(world, name), actor_id="probe",
               into=studio.directory(world, name), store=world)
    assert out["version"] == "v1"
    assert "  person  agree_example  example=flour" in out["transcript"].read_text(
        encoding="utf-8")
    assert list(business.load(out["examples"])) == ["flour"]
    # The draft closed, its plan stays beside the version, and is not one.
    studio.closed(world, name, "v1")
    where = studio.directory(world, name)
    assert (where / "v1.plan.yaml").is_file() and not (where / studio.PLAN).exists()
    assert [v["version"] for v in world.versions(name)] == ["v1"]


# ---- the accountant, the budget, the conversation ---------------------------

def _scripted(moves, answers=()):
    """A configuration whose builder and accountant play the given moves."""
    script = {"moves": [dict(m) for m in moves], "accountant": list(answers)}
    return configuration.unlimited(builder=rehearsal.model(script),
                                   accountant=rehearsal.accountant(script))


def _ending(info, kind):
    return next(t.name for t in info.output_tools if t.name.endswith(f"_{kind}"))


def test_the_accountant_reads_the_persons_words_and_nothing_of_the_graph(bench, world):
    from pydantic_ai import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel
    name = "@probe/reckoned"
    _started(bench, name)
    read = []

    def accountant(messages, info):
        read.append("\n".join(str(p.content) for m in messages for p in m.parts
                              if hasattr(p, "content")))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "figures": [{"figure": "on hand", "value": "2", "working": "two came in"}]})])

    parts = _scripted([
        {"tool": "look", "args": {"module": name}},
        {"tool": "reckon", "args": {"example": "one", "happened": ["Two came in."],
                                    "wanted": ["on hand"]}},
        {"end": "Reply", "args": {"message": "Worked out."}},
    ]).with_models(accountant=FunctionModel(accountant))
    session = Session(bench, name, parts)
    session.conversation.turns.append({
        "person": "We keep flour.", "ended": "Question", "spent": {},
        "said": {"question": "Is a return stock coming in?", "choices": []}})
    turn = session.ask("Yes, a return comes in.")

    assert turn.ended == "Reply"
    (prompt,) = read
    assert "The person said: We keep flour." in prompt
    assert "They were asked: Is a return stock coming in?" in prompt
    assert "The person said: Yes, a return comes in." in prompt
    assert "- Two came in." in prompt and "- on hand" in prompt
    # What the builder read in between never reaches it.
    assert "Level" not in prompt and "aggregate" not in prompt
    assert session.conversation.reckonings["one"]["figures"][0]["value"] == "2"
    tools.do(bench, name, [step("discard")])


def test_a_request_stops_at_its_budget_and_the_next_one_goes_on(bench, world):
    import dataclasses

    from pydantic_ai import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel
    name = "@probe/budget"
    _started(bench, name)
    looking = [{"tool": "look", "args": {"module": name}}] * 10
    parts = dataclasses.replace(_scripted(looking),
                                budget=configuration.Budget(requests=3))
    turn = Session(bench, name, parts).ask("Look, and keep looking.")
    # The last call the budget had room for was the builder's, to say so.
    assert isinstance(turn.output, Stopped) and turn.output.cause == "budget"
    assert turn.output.message == rehearsal.FAREWELL
    assert turn.spent["requests"] == 3
    assert [t["ended"] for t in kept.load(world, name).turns] == ["Stopped"]

    # The next request goes on from there, handed the first whole — what it
    # read is not read again — and ending on what the person was told.
    seen = []

    def remember(messages, info):
        seen.extend(messages)
        return ModelResponse(parts=[ToolCallPart(_ending(info, "Reply"),
                                                 {"message": "Going on."})])

    again = Session(bench, name, configuration.unlimited(builder=FunctionModel(remember)))
    assert again.ask("Go on.").ended == "Reply"
    calls = [p.tool_name for m in seen for p in m.parts if type(p).__name__ == "ToolCallPart"]
    assert calls == ["look", "look", "final_result_Reply"]
    said = [str(p.content) for m in seen for p in m.parts
            if type(p).__name__ == "UserPromptPart"]
    assert said[0].endswith("\n\nLook, and keep looking.")
    assert said[1].startswith("(From the system, not the person: this request has "
                              "reached its budget")
    assert said[2].endswith("\n\nGo on.")
    assert [t["ended"] for t in kept.load(world, name).turns] == ["Stopped", "Reply"]

    # A discarded draft takes its conversation with it.
    tools.do(bench, name, [step("discard")])
    assert not kept.path(world, name).exists()


def test_a_stop_puts_what_waits_for_the_person_before_them(bench, world):
    # The agent wrote an example and ran out before proposing it: the system
    # reads what waits off the draft and puts it before the person with the
    # stop, as a proposal would — not left for them to find.
    import dataclasses
    name = "@probe/stopped-waiting"
    _started(bench, name)
    _example_one(bench, name)
    # What it says, in the person's words, reaches the page beside the English.
    tools.do(bench, name, [step("label", term="one", language="id", label="Dua masuk.")])
    (one,) = [e for e in bench.state(name)["examples"] if e["name"] == "one"]
    assert (one["says"], one["labels"]) == ("Two in.", {"id": "Dua masuk."})
    looking = [{"tool": "look", "args": {"module": name}}] * 10
    parts = dataclasses.replace(_scripted(looking),
                                budget=configuration.Budget(requests=3))
    session = Session(bench, name, parts)
    session.conversation.reckonings["one"] = {
        "happened": ["Two came in."], "wanted": ["on hand"],
        "figures": [{"figure": "on hand", "value": "2", "working": "two in"}],
        "question": "", "by": "test"}
    turn = session.ask("Go on.")
    assert isinstance(turn.output, Stopped)
    assert (turn.output.agree, turn.output.seal) == (["one"], True)
    assert "Examples to agree to:" in turn.shown
    assert turn.shown.endswith("Ready to be sealed as v1 once they are agreed.")
    held = kept.load(world, name).turns[-1]
    assert held["said"]["agree"] == ["one"] and held["shown"] == turn.shown
    assert kept.spoken(held).startswith(
        "[stopped; the system put one before them to agree to and that it is ready")
    # A person who agrees to what is put before them agrees to it there.
    assert person_agrees(world, name, turn.output) == ["one"]
    # An example nobody but the agent worked out is not put before anybody.
    tools.do(bench, name, [step("discard")])
    _started(bench, name)
    _example_one(bench, name)
    turn = Session(bench, name, parts).ask("Go on.")
    assert turn.output.agree == [] and turn.output.seal is False and turn.shown is None
    tools.do(bench, name, [step("discard")])


def test_a_draft_that_declares_nothing_is_not_ready(bench, world):
    name = "@probe/nothing-yet"
    _planned(world, name)
    tools.do(bench, name, [step("start", title="T", description="D.")])
    report = bench.state(name)
    assert report["empty"] is True and report["sealable"] is False
    from components.agent.builder import Proposal, Work, unsupported
    said = unsupported(Work(bench=bench), Proposal(module=name, message="", seal=True))
    assert said == "it is not ready: the draft declares nothing yet"
    tools.do(bench, name, [step("discard")])


def test_every_call_of_every_part_is_written_down_whole(bench, world, tmp_path):
    import json

    from components.agent.watch import Watch, render
    script = rehearsal.load(SCRIPT)
    script["module"] = "@probe/watched"
    for request in script["requests"]:
        for move in request["moves"]:
            args = move.get("args") or {}
            if args.get("module") == "@rehearsal/levels":
                args["module"] = "@probe/watched"
    watch = Watch(tmp_path / "calls.jsonl")
    parts = configuration.unlimited(builder=rehearsal.model(script),
                                    accountant=rehearsal.accountant(script))
    played = script["requests"][:2]
    for request in played:
        turn = Session(bench, script["module"], parts, watch=watch).ask(request["says"])
        person_agrees(world, script["module"], turn.output)
    assert turn.ended == "Proposal"

    events = [json.loads(line) for line in watch.path.read_text(encoding="utf-8").splitlines()]
    assert events[0]["event"] == "note" and events[0]["text"].startswith("request on @probe")
    calls = [e for e in events if e["event"] == "call"]
    # One line per call, the accountant's among the builder's.
    assert len(calls) == sum(len(r["moves"]) for r in played) + 1
    assert [c["part"] for c in calls].count("accountant") == 1
    first = calls[0]
    (sent,) = first["sent"]
    assert sent["person"].startswith("(From the system, not the person: they have "
                                     "@probe/watched open. ")
    assert "It does not exist yet" in sent["person"]
    assert sent["person"].endswith(f"\n\n{played[0]['says']}")
    assert first["received"] == [{"call": "catalogue", "args": {"kind": "role"}}]
    assert {"input", "output"} <= set(first["tokens"])
    # What the system sent back is there, in full.
    assert any(p.get("sent_back") == "final_result_Proposal"
               and "nobody but you worked out the numbers" in p["content"]
               for c in calls for p in c["sent"])
    read = "\n".join(render(watch.path))
    assert "accountant call 1:" in read and "got  call reckon" in read
    assert read.splitlines()[-1].startswith(f"{len(calls)} calls, ")
    tools.do(bench, "@probe/watched", [step("discard")])

def test_a_call_the_provider_fails_for_a_moment_is_made_again(bench, world, tmp_path,
                                                              monkeypatch):
    from pydantic_ai import ModelResponse, ToolCallPart
    from pydantic_ai.exceptions import ModelHTTPError
    from pydantic_ai.models.function import FunctionModel

    from components.agent import steady
    from components.agent.watch import Watch
    monkeypatch.setattr(steady, "WAIT", (0.0, 0.0))
    failures = [500, 503]

    def flaky(messages, info):
        if failures:
            raise ModelHTTPError(failures.pop(0), "flaky", body={"error": "internal"})
        return ModelResponse(parts=[ToolCallPart(_ending(info, "Reply"), {"message": "Here."})])

    watch = Watch(tmp_path / "calls.jsonl")
    name = "@probe/flaky"
    turn = Session(bench, name, configuration.unlimited(builder=FunctionModel(flaky)),
                   watch=watch).ask("Hello.")
    assert turn.ended == "Reply"
    written = watch.path.read_text(encoding="utf-8")
    assert written.count("failed (ModelHTTPError") == 2

    # Past the tries, or a failure that is not the provider's for a moment: the
    # request stops, and says whose failure it was.
    failures[:] = [500, 500, 500]
    turn = Session(bench, name, configuration.unlimited(builder=FunctionModel(flaky))
                   ).ask("Hello again.")
    assert isinstance(turn.output, Stopped) and turn.output.cause == "provider"
    failures[:] = [400]
    turn = Session(bench, name, configuration.unlimited(builder=FunctionModel(flaky))
                   ).ask("And again.")
    assert turn.output.cause == "provider" and not failures


def test_the_configuration_names_a_model_per_part_and_prices_them(tmp_path):
    loaded = configuration.load()
    assert set(loaded.parts) == set(configuration.PARTS)
    assert all(":" in str(part.model) for part in loaded.parts.values())
    written = tmp_path / "agent.yaml"
    written.write_text(
        "parts:\n  builder: {model: 'x:small'}\n"
        "  accountant: {model: 'x:big', settings: {thinking: high}}\n"
        "budget: {requests: 5, dollars: 0.5}\n"
        "prices:\n  'x:small': {input: 1, cached: 0.1, output: 2}\n", encoding="utf-8")
    config = configuration.load(written)
    assert config.budget == configuration.Budget(requests=5, dollars=0.5)
    from pydantic_ai.usage import RunUsage
    used = RunUsage(input_tokens=1_000_000, output_tokens=500_000)
    assert config.cost("builder", used) == 2.0
    # What the provider served from its cache is charged at the cached price.
    used = RunUsage(input_tokens=1_000_000, output_tokens=500_000,
                    details={"cached_content_tokens": 500_000})
    assert config.cost("builder", used) == pytest.approx(1.55)
    assert config.cost("accountant", used) is None
    assert config.part("accountant").settings == {"thinking": "high"}
    # Another model for one run leaves the file's settings behind.
    other = config.with_models(accountant="x:other")
    assert (other.part("accountant").label, other.part("accountant").settings) \
        == ("x:other", {})
    written.write_text("parts:\n  builder: {model: 'x:small'}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no model for accountant"):
        configuration.load(written)


def test_the_terminal_prints_what_the_agent_reads(world, monkeypatch, capsys):
    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    assert agent_main(["guide", "rules"]) == 0
    assert "Two kinds of table come out" in capsys.readouterr().out
    assert agent_main(["catalogue", "--kind", "role"]) == 0
    assert "role Flow" in capsys.readouterr().out

"""The agent's tools, its guide, and the agent played from a script.

What this stage has to hold, with no model anywhere:

    its tools      five, and none that seals or agrees; every step through them
                   is an agent's step, held to what an agent may do.
    their text     what comes back says what the draft is standing in and how
                   to get out, and is short enough to read on every turn.
    their shape    flat: a model on any provider, or one run at home, can
                   write the arguments.
    the guide      generated from the system, and naming every step, every
                   refusal and every opening in it.
    a rehearsal    a scripted builder, through the same agent a model would
                   drive, builds an application, is caught making a mistake,
                   is sent back for proposing too early, and ends with a
                   proposal a person agrees to and seals.
"""

import os
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
from components.agent import rehearsal, tools  # noqa: E402
from components.agent.__main__ import main as agent_main  # noqa: E402
from components.examples import examples as business  # noqa: E402
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


def _started(bench, name):
    return tools.do(bench, name, [
        step("start", title="Levels", description="What is on hand."),
        step("pin", module=f"{dev_modules.CATALOG}@v3"),
        step("pin", module=f"{dev_modules.INVENTORY}@v3"),
        step("add_class", **{"class": "Level", "description": "One row per ingredient."}),
        step("add_slot", slot="level_thing", range="Ingredient", description="The thing."),
        step("attach", **{"class": "Level", "slot": "level_thing"}),
        step("add_slot", slot="level_on_hand", range="decimal", description="On hand."),
        step("attach", **{"class": "Level", "slot": "level_on_hand"}),
        step("aggregate", **{"class": "Level", "column": "level_on_hand", "over": "Flow",
                             "sum": "amount", "by": "level_thing=affects"}),
    ])


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

    building.builder(FunctionModel(peek)).run_sync("hello", deps=None)
    return seen


def test_the_agent_has_five_tools_and_none_that_seals_or_agrees():
    offered = _offered()
    assert set(offered["tools"]) == {"look", "options", "do", "catalogue", "guide"}
    assert set(offered["endings"]) == {"final_result_Reply", "final_result_Question",
                                       "final_result_Proposal"}


def test_every_step_through_the_tools_is_an_agents(bench, world):
    name = "@probe/agents_own"
    said = _started(bench, name)
    assert "9. done: aggregate class=Level" in said
    # The one hole left says what to do about it, with the step.
    assert "what number should Level's level_on_hand come to" in said
    assert "step: add_example, choosing example" in said
    lines = [line for line in studio.transcript(world, name).splitlines()
             if line and not line.startswith((" ", "#"))]
    assert lines and all("  agent  " in line for line in lines)

    # An agent cannot agree, through this or any tool.
    tools.do(bench, name, [step("add_example", example="one", says="One thing.")])
    said = tools.do(bench, name, [step("agree_example", example="one")])
    assert "1. refused: agree_example example=one" in said
    assert "[person_only]" in said
    assert studio.examples_of(world, name)["one"]["agreed"] is False

    # An example a person agreed to stays theirs.
    studio.apply(world, name, "agree_example", {"example": "one"})
    said = tools.do(bench, name, [step("set_example", example="one", field="says",
                                       value="Something else.")])
    assert "[example_agreed]" in said
    assert studio.examples_of(world, name)["one"]["says"] == "One thing."
    tools.do(bench, name, [step("discard")])


def test_a_batch_stops_at_the_first_refusal_and_says_how_to_fix_it(bench, world):
    name = "@probe/stopped"
    _started(bench, name)
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
    assert "level_on_hand: decimal = aggregate over Flow, sum amount, by level_thing=affects" in looked
    assert len(looked) < 2500
    around = tools.look(bench, name, "around")
    assert "Ingredient (" in around and "Flow: binds amount, affects, moment" in around
    offered = tools.options(bench, name, "parameter")
    assert "of (a slot of the class named), depends on class" in offered
    assert len(offered) < 3000
    assert "no part 'everything'" in tools.look(bench, name, "everything")
    assert "no step 'fly'" in tools.options(bench, name, "fly")
    found = tools.catalogue(bench, kind="role")
    assert "role Flow (@uniti/core@v2): binds amount, affects, moment" in found
    assert "Nothing matches" in tools.catalogue(bench, text="zzz-nothing")
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
    assert "Flow (@uniti/core@v2, a kind of Event, Thing)" in everything
    assert "There is no topic 'nope'" in guide_read.section("nope")


def test_the_instructions_are_the_workflow_and_a_list_of_topics():
    text = guide_read.instructions()
    assert text.startswith(guide_read.WORKFLOW)
    for topic in guide_read.TOPICS:
        if topic != "workflow":
            assert f"    {topic}: " in text
    # Short enough to sit at the top of every turn.
    assert len(text) < 4500


# ---- a proposal is checked -------------------------------------------------

def test_a_proposal_says_no_more_than_the_draft_bears_out(bench, world):
    name = "@probe/proposed"
    _started(bench, name)
    unsupported = building.unsupported
    proposal = building.Proposal
    assert "is not an example" in unsupported(
        bench, proposal(module=name, message="m", agree=["ghost"]))
    assert "it is not ready" in unsupported(
        bench, proposal(module=name, message="m", seal=True))
    tools.do(bench, name, [
        step("add_example", example="one", says="Two in."),
        step("record", example="one", record="thing", **{"class": "Ingredient"},
             facts="ingredient_code=T, ingredient_name=Thing, ingredient_unit=kg"),
        step("record", example="one", record="in", **{"class": "StockMovement"},
             facts="movement_code=M1, movement_ingredient=thing, movement_quantity=2, "
                   "movement_happened_on=2026-06-02"),
        step("expect", example="one", table="Level", row="thing", values="level_on_hand=3"),
    ])
    assert "fails" in unsupported(bench, proposal(module=name, message="m", agree=["one"]))
    tools.do(bench, name, [step("expect", example="one", table="Level", row="thing",
                                values="level_on_hand=2")])
    assert unsupported(bench, proposal(module=name, message="m", agree=["one"],
                                       seal=True)) is None
    studio.apply(world, name, "agree_example", {"example": "one"})
    assert "agreed already" in unsupported(
        bench, proposal(module=name, message="m", agree=["one"]))
    tools.do(bench, name, [step("discard")])


# ---- a rehearsal ------------------------------------------------------------

def test_a_scripted_builder_builds_an_application_a_person_then_seals(bench, world, conn):
    script = rehearsal.load(SCRIPT)
    name = script["module"]
    result = rehearsal.rehearse(bench, script)
    lines = "\n".join(rehearsal.trace(result.all_messages()))

    # The mistake was caught by the next read, with the fix in hand.
    assert "one of: {level_on_hand} - {level_reorder}" in lines
    # Proposing before the person had agreed was sent back, saying why.
    assert "sent back: That proposal cannot go to the person: it is not ready" in lines

    output = result.output
    assert isinstance(output, building.Proposal)
    assert (output.agree, output.seal) == (["flour"], True)
    shown = building.put_before(bench, output)
    assert "[holds] flour (proposed, not agreed yet)" in shown
    assert "ok Level flour, level_headroom: expected 10, got 10" in shown
    assert "Ready to be sealed as v1 once they are agreed." in shown

    # Every step was the agent's; the person agrees, and the person seals.
    taken = [line for line in studio.transcript(world, name).splitlines()
             if line and not line.startswith((" ", "#"))]
    assert all("  agent  " in line for line in taken)
    studio.apply(world, name, "agree_example", {"example": "flour"})
    out = seal(conn, studio.path(world, name), actor_id="probe",
               into=studio.directory(world, name), store=world)
    assert out["version"] == "v1"
    assert "  person  agree_example  example=flour" in out["transcript"].read_text(
        encoding="utf-8")
    assert list(business.load(out["examples"])) == ["flour"]


def test_the_terminal_prints_what_the_agent_reads(world, monkeypatch, capsys):
    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    assert agent_main(["guide", "rules"]) == 0
    assert "Two kinds of table come out" in capsys.readouterr().out
    assert agent_main(["catalogue", "--kind", "role"]) == 0
    assert "role Flow" in capsys.readouterr().out

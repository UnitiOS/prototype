"""The whole conversation, sent cheaply.

What has to hold with no model anywhere:

    fixed instructions   the instructions are the same on every call, before a
                         module exists and after; where it stands is said with
                         the person's message instead.
    kept from the start  questions asked before anything was built are part of
                         the conversation the next request is handed.
    read once            a reading that comes out as before is answered in one
                         line; once it differs it is answered in full.
    cleared when long    past `clear_above`, a reading read again since is one
                         line; the person's words, the agent's answers and its
                         steps never are.
    a goodbye            the budget keeps the last call for the agent to say
                         where it stopped, with only a reply allowed; a model
                         that will not is stopped all the same.
"""

import dataclasses
import os
import sys
from pathlib import Path

import pytest
from pydantic_ai import ModelResponse, ToolCallPart
from pydantic_ai.messages import (
    ModelRequest, TextPart, ToolReturnPart, UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

import dev_modules  # noqa: E402
from components.agent import builder as building  # noqa: E402
from components.agent import config as configuration  # noqa: E402
from components.agent import conversation as kept  # noqa: E402
from components.agent import guide as guide_read  # noqa: E402
from components.agent import rehearsal, tools  # noqa: E402
from components.agent.session import Session, Stopped  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from perform import connect  # noqa: E402


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


def _scripted(moves, **budget):
    script = {"moves": [dict(m) for m in moves], "accountant": []}
    config = configuration.unlimited(builder=rehearsal.model(script),
                                     accountant=rehearsal.accountant(script))
    return dataclasses.replace(config, budget=configuration.Budget(**budget)) \
        if budget else config


def _answers(turn):
    """What each tool answered in a turn, in order."""
    return [str(p.content) for m in turn.messages for p in m.parts
            if isinstance(p, ToolReturnPart)]


def _ending(info, kind):
    return next(t.name for t in info.output_tools if t.name.endswith(f"_{kind}"))


def _planned(store, name):
    """A plan the person agreed to: nothing is built by an agent before one."""
    studio.propose_plan(store, name, {"builds": "A test."})
    studio.apply(store, name, "agree_plan", {})


# ---- the instructions do not move ------------------------------------------

def test_the_instructions_are_the_same_on_every_call_and_the_state_comes_with_the_message(
        bench, world):
    name = "@probe/fixed"
    seen = []
    moves = iter([
        ("do", {"module": name, "steps": [
            {"op": "start", "args": [{"name": "title", "value": "Fixed"},
                                     {"name": "description", "value": "A test."}]}]}),
        ("look", {"module": name}),
    ])

    def model(messages, info):
        seen.append((info.instructions, messages))
        move = next(moves, None)
        if move is None:
            return ModelResponse(parts=[ToolCallPart(_ending(info, "Reply"), {"message": "Done."})])
        return ModelResponse(parts=[ToolCallPart(*move)])

    studio.propose_plan(world, name, {"builds": "A test."})
    studio.apply(world, name, "agree_plan", {})
    Session(bench, name, configuration.unlimited(builder=FunctionModel(model))).ask(
        "Start it.")
    # Before the module existed and after `start`, the same instructions.
    assert len(seen) == 3
    assert len({instructions for instructions, _ in seen}) == 1
    assert seen[0][0] == guide_read.instructions()
    # Where it stood came with the person's words, read as the request began.
    (first,) = [p.content for p in seen[0][1][0].parts if isinstance(p, UserPromptPart)]
    assert first == (f"(From the system, not the person: they have {name} open. This log "
                     f"belongs to no business yet, so it will be a community module. It does "
                     f"not exist yet: `start` creates it and opens its draft. The person "
                     f"agreed to your plan.)\n\nStart it.")
    # The conversation keeps the person's words as they said them.
    assert kept.load(world, name).turns[0]["person"] == "Start it."
    tools.do(bench, name, [{"op": "discard", "args": []}])


def test_what_was_asked_before_anything_was_built_is_kept(bench, world):
    name = "@probe/asked-first"
    parts = _scripted([{"end": "Question", "args": {"question": "Which shop?",
                                                    "choices": ["North", "South"]}}])
    turn = Session(bench, name, parts).ask("I want my stock.")
    assert turn.ended == "Question"
    # Kept where the draft will be, without making it a module of the store.
    assert kept.path(world, name).is_file()
    assert name not in world.names()

    seen = []

    def model(messages, info):
        seen.extend(messages)
        return ModelResponse(parts=[ToolCallPart(_ending(info, "Reply"), {"message": "North."})])

    Session(bench, name, configuration.unlimited(builder=FunctionModel(model))).ask(
        "The north one.")
    said = "\n".join(str(p.content) for m in seen for p in m.parts
                     if isinstance(p, (UserPromptPart, TextPart)))
    assert "I want my stock." in said and "Which shop?" in said
    assert [t["ended"] for t in kept.load(world, name).turns] == ["Question", "Reply"]
    kept.path(world, name).unlink()


# ---- read once -------------------------------------------------------------

def test_a_reading_that_comes_out_as_before_is_answered_in_one_line(bench, world):
    name = "@probe/read-once"
    _planned(world, name)
    tools.do(bench, name, [{"op": "start", "args": [
        {"name": "title", "value": "Once"}, {"name": "description", "value": "A test."}]}])
    looking = {"tool": "look", "args": {"module": name}}
    turn = Session(bench, name, _scripted([
        looking, looking,
        {"tool": "catalogue", "args": {"kind": "role"}},
        {"tool": "catalogue", "args": {"kind": "role", "text": ""}},
        {"tool": "do", "args": {"module": name, "steps": [
            {"op": "set", "args": [{"name": "field", "value": "title"},
                                   {"name": "value", "value": "Read once"}]}]}},
        looking,
        {"end": "Reply", "args": {"message": "Read."}},
    ])).ask("Read it.")
    answers = _answers(turn)
    assert answers[0].startswith(f"{name} — Once")
    assert answers[1] == (f"{kept.UNCHANGED} look(module={name}, part=draft) reads exactly "
                          f"as it did the last time you read it in this conversation: "
                          f"nothing has changed since. Work from that reading.")
    # The same search, written another way, is the same reading.
    assert "role Flow" in answers[2]
    assert answers[3].startswith(kept.UNCHANGED)
    # Changed since, it is read in full again.
    assert answers[5].startswith(f"{name} — Read once")

    # And in the next request too: the conversation still holds the reading.
    turn = Session(bench, name, _scripted([looking, {"end": "Reply", "args": {
        "message": "Same."}}])).ask("Look again.")
    assert _answers(turn)[0].startswith(kept.UNCHANGED)
    tools.do(bench, name, [{"op": "discard", "args": []}])


# ---- cleared when long -----------------------------------------------------

def _call(tool, args, call_id, tokens=0):
    return ModelResponse(parts=[ToolCallPart(tool, args, tool_call_id=call_id)],
                                  usage=RequestUsage(input_tokens=tokens))


def _answer(tool, content, call_id):
    return ModelRequest(parts=[ToolReturnPart(tool, content, tool_call_id=call_id)])


def test_a_long_conversation_clears_what_was_read_again_and_nothing_else():
    messages = [
        ModelRequest(parts=[UserPromptPart("Build it.")]),
        _call("look", {"module": "@a/b"}, "1", 100),
        _answer("look", "the draft, first", "1"),
        _call("do", {"module": "@a/b", "steps": []}, "2", 200),
        _answer("do", "done, and where it stands", "2"),
        _call("catalogue", {"kind": "role"}, "3", 300),
        _answer("catalogue", "the roles", "3"),
        _call("look", {"module": "@a/b", "part": "draft"}, "4", 400),
        _answer("look", "the draft, second", "4"),
    ]
    # Short, nothing goes: the start of what is sent stays as the cache has it.
    assert kept.cleared(messages, 1000) is messages
    out = kept.cleared(messages, 400)
    contents = [str(p.content) for m in out for p in m.parts
                if isinstance(p, (ToolReturnPart, UserPromptPart))]
    assert contents == [
        "Build it.",
        f"{kept.CLEARED} This was read again later in the conversation; that later "
        f"reading is the one that holds.",
        "done, and where it stands", "the roles", "the draft, second"]
    # Every call stays, and clearing twice is clearing once.
    assert [p.tool_name for m in out for p in m.parts if isinstance(p, ToolCallPart)] \
        == ["look", "do", "catalogue", "look"]
    assert kept.cleared(out, 400) == out
    assert messages[2].parts[0].content == "the draft, first"


def test_a_session_past_the_threshold_keeps_the_conversation_cleared(bench, world):
    name = "@probe/cleared"
    _planned(world, name)
    tools.do(bench, name, [{"op": "start", "args": [
        {"name": "title", "value": "Cleared"}, {"name": "description", "value": "A test."}]}])
    looking = {"tool": "look", "args": {"module": name}}
    renamed = {"tool": "do", "args": {"module": name, "steps": [
        {"op": "set", "args": [{"name": "field", "value": "title"},
                               {"name": "value", "value": "Cleared again"}]}]}}
    parts = dataclasses.replace(
        _scripted([looking, renamed, looking, {"end": "Reply", "args": {"message": "Ok."}}]),
        clear_above=1)
    Session(bench, name, parts).ask("Read, change, read.")
    stored = kept.load(world, name).turns[0]["messages"]
    answers = [p["content"] for m in stored for p in m["parts"]
               if p.get("part_kind") == "tool-return"]
    assert answers[0].startswith(kept.CLEARED)
    assert answers[1].startswith("1. done: set field=title")
    assert answers[2].startswith(f"{name} — Cleared again")
    tools.do(bench, name, [{"op": "discard", "args": []}])


# ---- a goodbye -------------------------------------------------------------

def test_the_budget_keeps_the_last_call_for_the_agent_to_say_where_it_stopped(bench, world):
    name = "@probe/goodbye"
    _planned(world, name)
    tools.do(bench, name, [{"op": "start", "args": [
        {"name": "title", "value": "Goodbye"}, {"name": "description", "value": "A test."}]}])
    seen = []

    def model(messages, info):
        seen.append(((info.model_settings or {}).get("tool_choice"), messages[-1]))
        if (info.model_settings or {}).get("tool_choice"):
            return ModelResponse(parts=[ToolCallPart(_ending(info, "Reply"), {
                "message": "Saya berhenti di sini: drafnya sudah dibuat, rumusnya belum."})])
        return ModelResponse(parts=[ToolCallPart("look", {"module": name, "part": "history"})])

    config = dataclasses.replace(configuration.unlimited(builder=FunctionModel(model)),
                                 budget=configuration.Budget(requests=3))
    turn = Session(bench, name, config).ask("Bangun semuanya.")
    # Two calls to work in, the third kept for the goodbye, in their words.
    assert isinstance(turn.output, Stopped) and turn.output.cause == "budget"
    assert turn.output.message.startswith("Saya berhenti di sini")
    assert turn.spent["requests"] == 3
    assert [allowed for allowed, _ in seen] == [None, None, ["final_result_Reply"]]
    told = seen[-1][1].parts[-1]
    assert isinstance(told, UserPromptPart)
    assert told.content.startswith("(From the system, not the person: this request has "
                                   "reached its budget — 2 of its 3 model calls are used.")
    assert kept.load(world, name).turns[-1]["ended"] == "Stopped"

    # A model that will not say goodbye is stopped all the same, by the system.
    parts = _scripted([{"tool": "look", "args": {"module": name}}] * 5, requests=2)
    stubborn = FunctionModel(lambda messages, info: ModelResponse(parts=[
        ToolCallPart("look", {"module": name})]))
    turn = Session(bench, name, parts.with_models(builder=stubborn)).ask("Go on.")
    assert isinstance(turn.output, Stopped)
    assert "spent its budget: 2 model calls, the budget is 2" in turn.output.message
    tools.do(bench, name, [{"op": "discard", "args": []}])


def test_the_last_call_is_judged_on_the_size_of_the_last_one():
    config = dataclasses.replace(
        configuration.unlimited(builder="x:model"),
        budget=configuration.Budget(dollars=0.10),
        prices={"x:model": {"input": 1.0, "output": 1.0}})
    work = building.Work(bench=None, config=config)
    from pydantic_ai.usage import RunUsage
    # $0.06 spent, the last call cost $0.02: room for two, so not the last.
    used, last = RunUsage(input_tokens=50_000, output_tokens=10_000), \
        RequestUsage(input_tokens=15_000, output_tokens=5_000)
    assert work.last_call(used, last) is None
    # $0.08 spent: room for one, which is kept for the goodbye.
    used = RunUsage(input_tokens=70_000, output_tokens=10_000)
    assert work.last_call(used, last) == "$0.08 of its $0.10 is spent"

    # The next call is reckoned at what the last one cost, the cache's share
    # included; only the goodbye is kept at the full price, since the cache
    # may not serve it. $0.07 spent, the last call cost $0.0065 served from
    # the cache, the goodbye $0.02 at most: both fit in the $0.03 left.
    cheap = dataclasses.replace(config, prices={
        "x:model": {"input": 1.0, "cached": 0.1, "output": 1.0}})
    work = building.Work(bench=None, config=cheap)
    used = RunUsage(input_tokens=60_000, output_tokens=10_000)
    served = RequestUsage(input_tokens=15_000, output_tokens=5_000,
                          details={"cached_content_tokens": 15_000})
    assert work.last_call(used, served) is None
    # At $0.09, one more call and a goodbye would not fit: this one is it.
    used = RunUsage(input_tokens=80_000, output_tokens=10_000)
    assert work.last_call(used, served) == "$0.09 of its $0.10 is spent"
    # A long conversation, the way the two-round test had them: 110,000 tokens
    # a call, nearly all from the cache, on a $0.30 budget. The old reckoning
    # stopped once $0.11 was spent; this one goes on to $0.18.
    flash = dataclasses.replace(config, budget=configuration.Budget(dollars=0.30),
                                prices={"x:model": {"input": 0.825, "cached": 0.0825,
                                                    "output": 4.125}})
    work = building.Work(bench=None, config=flash)
    long = RequestUsage(input_tokens=110_000, output_tokens=1_500,
                        details={"cached_content_tokens": 100_000})
    spent = lambda dollars: RunUsage(input_tokens=int(dollars / 0.825 * 1e6))  # noqa: E731
    assert work.last_call(spent(0.15), long) is None
    assert work.last_call(spent(0.17), long) is None
    assert work.last_call(spent(0.19), long) == "$0.19 of its $0.30 is spent"

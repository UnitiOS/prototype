"""The agent's eval: its tasks can be passed, and its harness judges honestly.

No model is called here. What has to hold before a model's score means
anything:

    the tasks      every buildable task's truth is met by a plain build of it
                   (`evals/reference.yaml`), so a failing run is the model's
                   failure and never the task's.
    the harness    plays the person — agrees to the plan, then the examples,
                   then sees the draft called ready — grades by the truth, and
                   tells a run that built the wrong thing from one that built
                   the right thing, even when the wrong one's own example
                   passes.
    the accountant is judged figure by figure, several at once.
"""

import os
import re
import sys
from pathlib import Path

import pytest
import yaml
from pydantic_ai import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

import dev_modules  # noqa: E402
from components import standard  # noqa: E402
from components.agent import config as configuration  # noqa: E402
from components.agent import evals, rehearsal, tools  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from perform import connect  # noqa: E402

HERE = Path(__file__).parent / "evals"
TASKS, ANSWER = evals.load(HERE / "tasks.yaml")
REFERENCE = yaml.safe_load((HERE / "reference.yaml").read_text(encoding="utf-8"))
BY_NAME = {task["name"]: task for task in TASKS}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    with connect(os.environ["UNITI_DSN"]) as conn:
        store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
        yield store
        conn.rollback()


@pytest.fixture(scope="module")
def bench(world):
    return tools.Bench(world, dsn=os.environ["UNITI_DSN"])


def _steps(written):
    """Steps as a script writes them, shaped as a model writes them."""
    return rehearsal.load_steps(written)


def _facts(facts):
    return ", ".join(f"{k}={v}" for k, v in facts.items())


def _values(values):
    return ", ".join(f"{k}={'' if v is None else v}" for k, v in values.items())


def _row(row):
    return _facts(row) if isinstance(row, dict) else str(row)


def _example(task, name="checked"):
    """The truth, written by the builder as its own example: recorded in
    English, with the person's words kept as its label when they are not."""
    truth = task["truth"]
    said = truth["says"]
    if standard.english(said) != "no":
        steps = [{"op": "add_example", "args": {"example": name, "says": said}}]
    else:
        steps = [{"op": "add_example", "args": {
                     "example": name, "says": "What the person said the numbers come to."}},
                 {"op": "label", "args": {"term": name, "language": "id", "label": said}}]
    for record in truth["records"]:
        args = {"example": name, "record": record["record"], "facts": _facts(record["facts"])}
        if "class" in record:
            args["class"] = record["class"]
        if "when" in record:
            args["when"] = record["when"]
        steps.append({"op": "record", "args": args})
    for expectation in truth["expect"]:
        args = {"example": name, "table": expectation["table"],
                "row": _row(expectation["row"]), "values": _values(expectation["values"])}
        if "at" in expectation:
            args["at"] = expectation["at"]
        steps.append({"op": "expect", "args": args})
    return steps


def test_the_tasks_are_ten_and_each_says_where_it_comes_from():
    assert len(TASKS) == 10
    assert set(REFERENCE) == {t["name"] for t in TASKS if t.get("buildable", True)}
    for task in TASKS:
        assert task["from"] and task["says"] and task["module"].startswith("@")
        assert len(task["truth"]["figures"]) >= 1


@pytest.mark.parametrize("name", sorted(REFERENCE))
def test_every_buildable_truth_is_met_by_a_plain_build(bench, name):
    # Built by hand, as a person builds: the order a builder is held to is
    # not what is being shown here.
    task = BY_NAME[name]
    module = task["module"]
    for step in REFERENCE[name]:
        studio.apply(bench.store, module, step["op"], {k: str(v) for k, v in (step.get("args") or {}).items()})
    truth = evals._truth(task, bench, module)
    assert truth["passed"], "\n".join(evals.business.render([truth]))
    studio.apply(bench.store, module, "discard", {})


# ---- the harness, with the builder and the accountant scripted -------------

def _believed(task, rows):
    """The builder's own example: the truth's records, and the numbers it
    believes for each row — every column it computes, as the contract asks."""
    truth = yaml.safe_load(yaml.safe_dump(task["truth"]))
    table = truth["expect"][0]["table"]
    truth["expect"] = [{"table": table, "row": row, "values": values}
                       for row, values in rows.items()]
    return truth


def _played(task, steps, believed):
    """A configuration whose builder works as it is held to, a request each:
    puts a plan forward; builds with `steps` all but the rules, asks the
    accountant, writes `believed` as its example and proposes it; writes the
    rules and calls the draft ready. The accountant gives back exactly the
    believed numbers."""
    module = task["module"]
    figures = {f"{e['row']} {k}": v for e in believed["expect"]
               for k, v in e["values"].items()}
    rules = [s for s in steps if s["op"] in studio.RULED]
    rest = [s for s in steps if s["op"] not in studio.RULED]
    requests = [
        {"says": task["says"], "moves": [
            {"end": "Plan", "args": {"message": "Shall I?", "builds": "What was asked.",
                                     "numbers": list(figures)}}]},
        {"says": evals.AGREED, "moves": [
            {"tool": "do", "args": {"module": module, "steps": _steps(rest)}},
            {"tool": "reckon", "args": {"example": "checked",
                                        "happened": believed["happened"],
                                        "wanted": list(figures)}},
            {"tool": "do", "args": {"module": module,
                                    "steps": _steps(_example({"truth": believed}))}},
            {"end": "Proposal", "args": {"module": module, "message": "Agree?",
                                         "agree": ["checked"]}}]},
        {"says": evals.AGREED, "moves": [
            {"tool": "do", "args": {"module": module, "steps": _steps(rules)}},
            {"end": "Proposal", "args": {"module": module, "message": "Ready.",
                                         "agree": [], "seal": True}}]},
    ]
    answer = {"figures": [{"figure": f, "value": str(v), "working": "counted"}
                          for f, v in figures.items()]}
    script = {"module": module, "requests": requests, "accountant": [answer]}
    return configuration.unlimited(builder=rehearsal.model(script),
                                   accountant=rehearsal.accountant(script))


SHORTFALL = {"flour": {"shortfall_on_hand": 6, "shortfall_level": 10, "shortfall_amount": 4},
             "sugar": {"shortfall_on_hand": 15, "shortfall_level": 10, "shortfall_amount": -5}}


def test_a_run_that_builds_the_right_thing_passes(world):
    task = BY_NAME["shortfall"]
    believed = _believed(task, SHORTFALL)
    run = evals.attempt(task, _played(task, REFERENCE["shortfall"], believed),
                        world, os.environ["UNITI_DSN"], ANSWER)
    assert run["passed"], run["why"]
    assert run["why"] == "sealable, and the truth holds"
    # A plan, the examples, the rules: three requests, the accountant once.
    assert [t["ended"] for t in run["turns"]] == ["Plan", "Proposal", "Proposal"]
    assert [t["person"] for t in run["turns"]] == [task["says"], evals.AGREED, evals.AGREED]
    assert (run["ended"], run["requests"], run["calls"], run["refused"],
            run["sent_back"]) == ("Proposal", 8, 4, 0, 0)
    assert run["steps"] == len(REFERENCE["shortfall"]) + len(_example({"truth": believed}))


def test_a_run_whose_own_example_agrees_with_a_wrong_build_still_fails(world):
    # The sign the other way round, and an example that believes it: sealable,
    # and wrong. Only the truth, which the builder never saw, catches it.
    task = BY_NAME["shortfall"]
    wrong = [dict(s) for s in REFERENCE["shortfall"]]
    wrong[-1] = {"op": "expression", "args": {
        "class": "Shortfall", "column": "shortfall_amount",
        "expression": "{shortfall_on_hand} - {shortfall_level}"}}
    believed = _believed(task, {row: {**v, "shortfall_amount": -v["shortfall_amount"]}
                                for row, v in SHORTFALL.items()})
    run = evals.attempt(task, _played(task, wrong, believed), world,
                        os.environ["UNITI_DSN"], ANSWER)
    assert not run["passed"]
    assert run["why"].startswith("sealable, but the truth fails")
    assert "expected 4, got -4" in run["why"]


def test_a_run_that_builds_what_cannot_be_built_fails_and_one_that_says_so_passes(world):
    task = BY_NAME["received_only"]
    # A total of everything, called ready: the thing the person said not to do.
    steps = [dict(s) for s in REFERENCE["on_hand"]]
    renamed = yaml.safe_load(re.sub(r"\bStock\b", "Received", yaml.safe_dump(steps))
                             .replace("stock_", "received_")
                             .replace("received_on_hand", "received_total"))
    played = _played(task, renamed, _believed(task, {"flour": {"received_total": 20}}))
    run = evals.attempt(task, played, world, os.environ["UNITI_DSN"], ANSWER)
    assert not run["passed"]
    assert run["why"].startswith("called something ready the system cannot build")

    honest = configuration.unlimited(builder=rehearsal.model({"moves": [
        {"tool": "catalogue", "args": {"kind": "role"}},
        {"end": "Reply", "args": {"message": "That cannot be built yet."}},
    ] * evals.TURNS}))
    run = evals.attempt(task, honest, world, os.environ["UNITI_DSN"], ANSWER)
    assert run["passed"] and run["why"] == "told the person, and called nothing ready"
    # Told, the person has nothing to add: the run ends on the reply.
    assert len(run["turns"]) == 1


def test_a_run_that_tells_nobody_cannot_be_built_fails(world):
    # Out of budget while trying is not telling the person anything.
    import dataclasses

    task = BY_NAME["per_supplier"]
    trying = configuration.unlimited(builder=rehearsal.model({"moves": [
        {"tool": "catalogue", "args": {"kind": "role"}},
    ] * 3 + [{"end": "Reply", "args": {"message": "Done."}}]}))
    label = trying.part("builder").label
    priced = dataclasses.replace(trying, prices={label: {"input": 1e6, "output": 0}})
    run = evals.attempt(task, priced, world, os.environ["UNITI_DSN"], ANSWER, limit=0.5)
    assert not run["passed"]
    assert run["why"].startswith("called nothing ready, and told the person nothing")


def test_a_run_starts_from_the_sealed_versions_not_from_a_draft_left_open(world):
    from components.studio import draft as studio

    studio.apply(world, "@demo/stock", "revise", {})
    try:
        looking = configuration.unlimited(builder=rehearsal.model({"moves": [
            {"tool": "look", "args": {"module": "@demo/stock"}},
            {"end": "Reply", "args": {"message": "Looked."}},
        ]}))
        run = evals.attempt(BY_NAME["revise_existing"], looking, world,
                            os.environ["UNITI_DSN"], ANSWER)
        assert "is sealed and has no draft" in str(run["turns"][0]["trace"])
    finally:
        studio.apply(world, "@demo/stock", "discard", {})


def test_what_a_run_the_network_broke_had_spent_is_counted(monkeypatch):
    results = iter([
        {"passed": False, "why": "crashed", "broken": True, "dollars": 0.3,
         "requests": 3, "tokens": 9, "seconds": 1.0},
        {"passed": True, "why": "fine", "dollars": 0.1, "requests": 2, "tokens": 5,
         "seconds": 1.0},
    ])

    async def attempting(*args, **kwargs):
        return next(results)

    monkeypatch.setattr(evals, "attempt_async", attempting)
    parts = configuration.unlimited(builder=rehearsal.model({"moves": []}))
    report = evals.run([BY_NAME["on_hand"]], parts, "builder", repeat=1, dollars=5)
    run = report["tasks"][0]["runs"][0]
    assert run["passed"] and run["again"] == 1 and run["broken_dollars"] == 0.3
    said = "\n".join(evals.render(report))
    assert "$0.40 in all; 1 runs had to be started again after the network "            "failed, which had spent $0.30" in said


def test_the_accountant_is_judged_figure_by_figure_several_at_once():
    def answering(messages, info):
        prompt = "\n".join(str(p.content) for m in messages for p in m.parts
                           if hasattr(p, "content"))
        task = next(t for t in TASKS if t["truth"]["happened"][-1] in prompt)
        figures = dict(task["truth"]["figures"])
        if task["name"] == "headroom":
            figures["salt's headroom"] = "0"  # nought where there is nothing
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "figures": [{"figure": f, "value": v, "working": "counted"}
                        for f, v in figures.items()]})])

    parts = configuration.unlimited(accountant=FunctionModel(answering))
    chosen = [BY_NAME["on_hand"], BY_NAME["headroom"], BY_NAME["two_shops"]]
    report = evals.run(chosen, parts, "accountant", repeat=2, workers=3)
    passed = {t["name"]: t["passed"] for t in report["tasks"]}
    assert passed == {"on_hand": True, "headroom": False, "two_shops": True}
    why = report["tasks"][1]["runs"][0]["why"]
    assert why == "salt's headroom: expected , got 0 (counted)"
    lines = evals.render(report)
    assert lines[1].split() == ["task", "pass", "runs", "req", "tokens", "dollars",
                                "seconds"]
    assert "2 of 3 tasks passed every run; 4 of 6 runs passed" in "\n".join(lines)


def test_an_eval_stops_starting_runs_once_its_budget_is_spent_and_watches_them(tmp_path):
    import dataclasses

    from components.agent.watch import Watch

    def answering(messages, info):
        figures = BY_NAME["on_hand"]["truth"]["figures"]
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "figures": [{"figure": f, "value": v, "working": "counted"}
                        for f, v in figures.items()]})])

    parts = configuration.unlimited(accountant=FunctionModel(answering))
    label = parts.part("accountant").label
    priced = dataclasses.replace(parts, prices={label: {"input": 1e6, "output": 0}})
    heard = []
    watch = Watch(tmp_path / "calls.jsonl")
    report = evals.run([BY_NAME["on_hand"]], priced, "accountant", repeat=3,
                       dollars=0.5, watch=watch, told=heard.append)
    runs = report["tasks"][0]["runs"]
    # Every call costs more than the whole budget: the first run is made, the
    # others are not started, and the report says so.
    assert runs[0]["passed"] and runs[0]["dollars"] > 0.5
    assert [r.get("skipped", False) for r in runs] == [False, True, True]
    assert "2 runs not started, the eval's budget being spent" in "\n".join(evals.render(report))
    assert len(heard) == 1 and heard[0].startswith("on_hand run 1: passed, 1 calls")
    written = watch.path.read_text(encoding="utf-8")
    assert written.count('"event": "call"') == 1 and "eval: on_hand run 1" in written


def test_a_run_stops_after_the_request_that_spends_what_the_eval_had_left(world):
    import dataclasses

    task = BY_NAME["received_only"]
    talking = configuration.unlimited(builder=rehearsal.model({"moves": [
        {"end": "Reply", "args": {"message": "Tell me more."}},
    ] * evals.TURNS}))
    label = talking.part("builder").label
    priced = dataclasses.replace(talking, prices={label: {"input": 1e6, "output": 0}})
    run = evals.attempt(task, priced, world, os.environ["UNITI_DSN"], ANSWER, limit=0.5)
    assert len(run["turns"]) == 1 and run["ended"] == "Stopped"
    assert run["turns"][0]["said"]["message"].startswith("the eval's budget was spent")

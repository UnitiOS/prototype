"""evals — whether a model can play a part, judged by code, every run.

A model is supported for a part when it passes that part's eval, not because
a provider says so. Each task is run several times and passes only when every
run passes (pass^k): a builder that is right two times in three is wrong one
time in three in front of a person.

The tasks are data, and live with the test data, because they name a
business. Each is a request in the person's words and a hidden truth:

    name, module     the task, and the module the builder is asked to build
    says             the request
    answers          what the person says when asked, in order; after them,
                     the file's `answer`
    buildable        false when the system cannot yet do what is asked: then
                     the builder passes by not proposing something else
    truth            an example the builder never sees:
        says, records, expect    written into the finished draft and run, the
                                 same way any example runs
        happened, figures        the same example in business words, and its
                                 numbers, for the accountant's eval

**The builder's eval.** A session on a copy of the store's sealed versions:
drafts somebody has open are left behind, so every task starts as it is
written. The harness plays the person as the system has every builder work
with one: it answers questions, agrees to the plan and to every example
proposed and says to go on (`AGREED`), and stops at a proposal that says the
draft is ready, at a reply — something said to the person, who has nothing to
add — or after `TURNS` requests. A plan, the examples and the rules are a
request each, so a task takes three at the least. A buildable task passes when the draft is then sealable and
the truth example, added to it as a person would add one, holds. A task that
is not buildable passes when the builder told the person so and called
nothing ready; a builder that ran out of budget trying has told nobody.
Nothing is sealed: sealing writes to the log, and "sealable" is the same
judge without the writing.

**The accountant's eval.** The accountant alone, given the request, the
answers, and the truth's situation in business words; it passes when every
figure matches and it asked nothing.

Measured on every run: requests to the model, tokens, dollars where the model
has a price, seconds, tool calls, steps refused, and proposals sent back. The
report keeps every turn's trace, so a failing run can be read call by call.

Runs go one at a time unless asked otherwise, so each can be followed as it
happens: with a `watch`, every call every run makes is written down whole, and
a line per run is printed as it ends. An eval has a budget of its own
(`dollars`): a run stops after the request that reaches it, and once it is
reached the runs not yet started are not started; the report says which. So an
eval spends at most its budget and one request's (config/agent.yaml). A run the network broke — a timeout, a
provider that was busy — is not the model's failure: it is run again, up to
`AGAIN` times, and the report says how many runs needed it and what the runs
it broke had spent, which counts towards the budget like any other.
"""

import asyncio
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml
from pydantic_ai.messages import RetryPromptPart, ToolCallPart, ToolReturnPart

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.agent import accountant as accounting  # noqa: E402
from components.agent import rehearsal  # noqa: E402
from components.agent.builder import Plan, Proposal, Reply  # noqa: E402
from components.agent.session import Session, Stopped, person_agrees, settle  # noqa: E402
from components.agent.steady import passing  # noqa: E402
from components.agent.tools import Bench  # noqa: E402
from components.examples import examples as business  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components import standard  # noqa: E402
from components.studio import draft as studio  # noqa: E402

TURNS = 8
AGAIN = 2
TRUTH = "eval_truth"
AGREED = "I agree. Go on."


def load(path):
    """The tasks in a file, and the answer the person gives when out of answers."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return raw["tasks"], raw.get("answer") or "Go on."


# ---- the builder -------------------------------------------------------------

def attempt(task, config, store, dsn, answer, watch=None, limit=None):
    """One run of one task on a copy of the store's first root, stopped after
    the request that spends `limit` dollars."""
    return settle(attempt_async(task, config, store, dsn, answer, watch, limit))


async def attempt_async(task, config, store, dsn, answer, watch=None, limit=None):
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as scratch:
        first = Path(scratch) / "store"
        await asyncio.to_thread(shutil.copytree, store.roots[0], first,
                                ignore=shutil.ignore_patterns("draft.*"))
        copy = Store([first, *store.roots[1:]])
        bench = Bench(copy, dsn)
        try:
            run = await _converse(task, config, bench, answer, watch, limit)
            run.update(await asyncio.to_thread(_grade, task, bench, run))
        except Exception as exc:  # a run that crashes is a run that failed
            # What it spent before it broke was spent all the same.
            run = {"passed": False, "why": f"crashed: {type(exc).__name__}: {exc}",
                   "turns": getattr(exc, "turns", []), "ended": "Crashed",
                   "broken": _broken(exc)}
    run["seconds"] = round(time.monotonic() - started, 1)
    run.update(_totals(run["turns"]))
    return run


def _broken(exc):
    """Whether it was the network or the provider, not the model, that failed."""
    return passing(exc)


async def _converse(task, config, bench, answer, watch=None, limit=None):
    session = Session(bench, task["module"], config, watch=watch)
    answers = iter(task.get("answers") or [])
    say = task["says"]
    turns = []
    ready = False
    spent = 0.0
    for _ in range(TURNS):
        turn = await session.ask_async(say)
        turns.append(_measured(turn))
        spent += turn.spent.get("dollars") or 0.0
        if isinstance(turn.output, Stopped):
            if turn.output.cause == "provider":
                raise ProviderFailed(turn.output.message, turns)
            break
        if limit is not None and spent >= limit and not (
                isinstance(turn.output, Proposal) and turn.output.seal):
            turns[-1]["ended"] = "Stopped"
            turns[-1]["said"] = {"message": f"the eval's budget was spent (${spent:.4f})"}
            break
        if isinstance(turn.output, (Plan, Proposal)):
            await asyncio.to_thread(person_agrees, bench.store, task["module"], turn.output)
            if isinstance(turn.output, Proposal) and turn.output.seal:
                ready = True
                break
            say = AGREED
            continue
        if isinstance(turn.output, Reply):
            # Said to the person, who has nothing to add to it.
            break
        say = next(answers, answer)
    return {"turns": turns, "ready": ready, "ended": turns[-1]["ended"]}


def _measured(turn):
    calls = [p for m in turn.messages for p in m.parts
             if isinstance(p, ToolCallPart) and not p.tool_name.startswith("final_result")]
    returns = [p for m in turn.messages for p in m.parts if isinstance(p, ToolReturnPart)]
    return {
        "person": turn.person,
        "ended": turn.ended,
        "said": turn.output.model_dump(),
        "spent": turn.spent,
        "calls": len(calls),
        "steps": sum(len(p.args_as_dict().get("steps") or []) for p in calls
                     if p.tool_name == "do"),
        "refused": sum(str(p.content).count(". refused: ") for p in returns
                       if p.tool_name == "do"),
        "sent_back": sum(1 for m in turn.messages for p in m.parts
                         if isinstance(p, RetryPromptPart)),
        "trace": rehearsal.trace(turn.messages),
    }


class ProviderFailed(TimeoutError):
    """A run the provider broke: made again, not counted against the model.
    It carries the turns it had, which spent what they spent."""

    def __init__(self, message, turns=()):
        super().__init__(message)
        self.turns = list(turns)


def _grade(task, bench, run):
    module = task["module"]
    if not run["ready"]:
        if task.get("buildable", True):
            return {"passed": False, "why": f"never called the draft ready "
                                            f"(the last turn ended {run['ended']})"}
        if run["ended"] != "Reply":
            return {"passed": False, "why": f"called nothing ready, and told the person "
                                            f"nothing (the last turn ended {run['ended']})"}
        return {"passed": True, "why": "told the person, and called nothing ready"}
    report = bench.state(module)
    blocking = [h for h in report["holes"] if h["blocking"]]
    # The recording standard is judged as every module is: a draft that breaks
    # it is not sealable. Said apart, because it is the one thing a new model
    # has to show it can do whatever the task is.
    unrecorded = [h for h in blocking if h["kind"] in standard.CHECKS]
    if unrecorded:
        return {"passed": False, "why": "called ready, but not to the recording standard:\n"
                + "\n".join(h["question"] for h in unrecorded)}
    if not report["sealable"]:
        return {"passed": False, "why": "called ready, but not sealable once agreed:\n"
                + "\n".join(h["question"] for h in blocking)}
    truth = _truth(task, bench, module)
    if truth["passed"]:
        return {"passed": True, "why": "sealable, and the truth holds"}
    lines = business.render([truth])
    if task.get("buildable", True):
        return {"passed": False, "why": "sealable, but the truth fails:\n" + "\n".join(lines)}
    return {"passed": False, "why": "called something ready the system cannot "
                                    "build, and the truth fails:\n" + "\n".join(lines)}


def _truth(task, bench, module):
    """The truth example, added to the finished draft by the person, and run."""
    where = studio.directory(bench.store, module) / studio.EXAMPLES
    held = business.load(where)
    truth = task["truth"]
    held[TRUTH] = {"says": truth["says"], "records": truth["records"],
                   "expect": truth["expect"]}
    where.write_text(business.dump(held), encoding="utf-8", newline="\n")
    report = bench.state(module)
    return next(e for e in report["examples"] if e["name"] == TRUTH)


def _totals(turns):
    spent = [t["spent"] for t in turns]
    dollars = [s.get("dollars") for s in spent]
    return {
        "requests": sum(s.get("requests", 0) for s in spent),
        "tokens": sum(s.get("input", 0) + s.get("output", 0) for s in spent),
        "dollars": None if any(d is None for d in dollars) else round(sum(dollars), 4),
        "calls": sum(t["calls"] for t in turns),
        "steps": sum(t["steps"] for t in turns),
        "refused": sum(t["refused"] for t in turns),
        "sent_back": sum(t["sent_back"] for t in turns),
    }


# ---- the accountant ----------------------------------------------------------

def reckoning(task, config, answer, watch=None):
    """One run of the accountant on one task's truth."""
    return settle(reckoning_async(task, config, answer, watch))


async def reckoning_async(task, config, answer, watch=None):
    started = time.monotonic()
    truth = task["truth"]
    said = [f"The person said: {task['says']}"]
    said += [f"The person said: {a}" for a in task.get("answers") or []]
    wanted = list(truth["figures"])
    part = config.part("accountant")
    try:
        result = await accounting.accountant(part.model, watch=watch).run(
            accounting.prompt(said, truth["happened"], wanted),
            model_settings=config.settings("accountant"))
        given = result.output
        usage = result.usage
        by_name = {f.figure.strip().lower(): f for f in given.figures}
        wrong = []
        for i, figure in enumerate(wanted):
            got = by_name.get(figure.strip().lower()) or (
                given.figures[i] if i < len(given.figures) else None)
            if got is None or _number(got.value) != _number(truth["figures"][figure]):
                wrong.append(f"{figure}: expected {truth['figures'][figure]}, "
                             f"got {got.value if got else 'nothing'}"
                             + (f" ({got.working})" if got else ""))
        passed = not wrong and not given.question
        why = "every figure right" if passed else "; ".join(
            wrong + ([f"asked: {given.question}"] if given.question else []))
        run = {"passed": passed, "why": why, "requests": usage.requests,
               "tokens": usage.input_tokens + usage.output_tokens,
               "dollars": config.cost("accountant", usage)}
    except Exception as exc:
        run = {"passed": False, "why": f"crashed: {type(exc).__name__}: {exc}",
               "requests": 0, "tokens": 0, "dollars": 0.0, "broken": _broken(exc)}
    run["seconds"] = round(time.monotonic() - started, 1)
    return run


def _number(value):
    if value is None or str(value).strip() in ("", "~"):
        return None
    try:
        return Decimal(str(value).strip()).normalize()
    except InvalidOperation:
        return str(value).strip()


# ---- a whole eval ------------------------------------------------------------

def run(tasks, config, part, *, store=None, dsn=None, answer="Go on.", repeat=3,
        workers=1, dollars=None, watch=None, told=None):
    """Every task, `repeat` times, `workers` at a time, until `dollars` are
    spent. `told`, when given, hears one line per run as it ends. The report."""
    jobs = [(task, n) for task in tasks for n in range(1, repeat + 1)]
    spent = [0.0]

    async def every():
        room = asyncio.Semaphore(workers)

        async def one(task, n):
            async with room:
                if dollars is not None and spent[0] >= dollars:
                    return {"passed": False, "skipped": True, "seconds": 0.0,
                            "why": f"not run: the eval had spent its ${dollars:.2f}",
                            "requests": 0, "tokens": 0, "dollars": 0.0}
                broke = 0.0
                for again in range(AGAIN + 1):
                    if watch:
                        watch.note(f"eval: {task['name']} run {n}"
                                   + (f", again ({again})" if again else ""))
                    if part == "builder":
                        left = None if dollars is None else dollars - spent[0]
                        result = await attempt_async(task, config, store, dsn, answer,
                                                     watch, left)
                    else:
                        result = await reckoning_async(task, config, answer, watch)
                    spent[0] += result.get("dollars") or 0.0
                    if not result.pop("broken", False) or again == AGAIN:
                        result["again"] = again
                        result["broken_dollars"] = round(broke, 4)
                        break
                    broke += result.get("dollars") or 0.0
                line = (f"{task['name']} run {n}: {'passed' if result['passed'] else 'FAILED'}"
                        f", {result.get('requests', 0)} calls, "
                        f"${result.get('dollars') or 0:.4f}, {result['seconds']} s"
                        f" (eval so far ${spent[0]:.4f})")
                if watch:
                    watch.note(line + f" — {result['why']}")
                if told:
                    told(line)
                return result

        return await asyncio.gather(*(one(task, n) for task, n in jobs))

    results = settle(every())
    report = {"part": part, "model": config.part(part).label,
              "settings": config.part(part).settings, "budget": dollars,
              "with": {name: p.label for name, p in config.parts.items() if name != part},
              "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "repeat": repeat, "tasks": []}
    for i, task in enumerate(tasks):
        runs = results[i * repeat:(i + 1) * repeat]
        report["tasks"].append({"name": task["name"], "passed": all(r["passed"] for r in runs),
                                "runs": runs})
    return report


def render(report):
    """The report as a table a person reads, one line per task."""
    lines = [f"{report['part']} on {report['model']}"
             + (f" {report['settings']}" if report["settings"] else "")
             + f", each task {report['repeat']} times"]
    head = ("task", "pass", "runs", "req", "tokens", "dollars", "seconds")
    extra = ("calls", "steps", "refused", "sent back") if report["part"] == "builder" else ()
    rows = []
    for task in report["tasks"]:
        runs = task["runs"]
        n = len(runs)
        row = [task["name"], "yes" if task["passed"] else "no",
               f"{sum(r['passed'] for r in runs)}/{n}",
               _mean(runs, "requests"), _mean(runs, "tokens"),
               _mean(runs, "dollars", 3), _mean(runs, "seconds")]
        if extra:
            row += [_mean(runs, "calls"), _mean(runs, "steps"), _mean(runs, "refused"),
                    _mean(runs, "sent_back")]
        rows.append(row)
    widths = [max(len(str(x)) for x in col) for col in zip(head + extra, *rows)]
    for row in [list(head + extra), *rows]:
        lines.append("  ".join(str(x).ljust(w) for x, w in zip(row, widths)).rstrip())
    passed = sum(t["passed"] for t in report["tasks"])
    every = [r for t in report["tasks"] for r in t["runs"]]
    dollars = [r["dollars"] for r in every]
    again = sum(1 for r in every if r.get("again"))
    broke = sum(r.get("broken_dollars") or 0.0 for r in every)
    skipped = sum(1 for r in every if r.get("skipped"))
    lines.append(f"{passed} of {len(report['tasks'])} tasks passed every run; "
                 f"{sum(r['passed'] for r in every)} of {len(every)} runs passed; "
                 + (f"${sum(dollars) + broke:.2f} in all" if None not in dollars
                    else "cost unknown for an unpriced model")
                 + (f"; {again} runs had to be started again after the network "
                    f"failed, which had spent ${broke:.2f}" if again else "")
                 + (f"; {skipped} runs not started, the eval's budget being spent"
                    if skipped else ""))
    lines.append("means per run. Why each failing run failed:")
    for task in report["tasks"]:
        for n, r in enumerate(task["runs"], 1):
            if not r["passed"]:
                why = r["why"].replace("\n", "\n        ")
                lines.append(f"  {task['name']} run {n}: {why}")
    return lines


def _mean(runs, key, places=1):
    values = [r.get(key) for r in runs]
    if any(v is None for v in values):
        return "—"
    mean = sum(values) / len(values)
    return f"{mean:.{places}f}" if places != 1 or mean % 1 else f"{mean:.0f}"


def save(report, into):
    """Write the report where reports are kept; the path back."""
    into = Path(into)
    into.mkdir(parents=True, exist_ok=True)
    stamp = report["at"].replace(":", "").replace("-", "")[:15]
    path = into / f"{stamp}-{report['part']}.yaml"
    path.write_text(yaml.safe_dump(report, sort_keys=False, allow_unicode=True, width=100),
                    encoding="utf-8", newline="\n")
    return path


__all__ = ["AGAIN", "TURNS", "attempt", "load", "reckoning", "render", "run", "save"]

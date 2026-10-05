"""The agent from a terminal.

    python -m components.agent guide [topic]
    python -m components.agent look @scope/name [part]
    python -m components.agent catalogue [text] [--kind K]
    python -m components.agent rehearse SCRIPT
    python -m components.agent ask @scope/name "what the person says" [--scratch]
    python -m components.agent watch FILE
    python -m components.agent eval TASKS [--part builder|accountant] [--repeat 3]
                                          [--only NAME ...] [--builder M] [--accountant M]
                                          [--workers 1] [--dollars 0.50]

`guide`, `look` and `catalogue` print exactly what the agent reads: the same
functions, the same text. `rehearse` plays a scripted builder and accountant
through a session with no model behind them, on a copy of the store's first
root, so the store itself is left as it was; examples run in scratch logs on
`UNITI_DSN`. Every request of the script is played in turn, and between them
the person agrees to what each put before them — the plan, the examples — as
an eval's person does. Nothing is sealed: that is the person's.

`ask` is one request to the real agent, on the models `config/agent.yaml`
names, about one module's draft in the store itself. It prints every call and
answer, how the turn ended, and what the person would be shown; the
conversation is kept beside the draft, so the next `ask` goes on from it.
With `--scratch` it works on a copy of the store's first root instead, and
nothing it does stays. Every call to a model is written down whole in a watch
file under build/calls (`watch`), and `watch FILE` prints one for a person:
each call's time, tokens, thoughts, what it was sent and what it answered, and
every HTTP request the connection made.

`eval` runs a part's eval (`evals`) and writes the report under
build/evals. `--builder` and `--accountant` put another model on a part for
this run only. Runs go one at a time unless `--workers` says otherwise, a line
is printed as each ends, and no run starts once the eval has spent `--dollars`.
Every call is written down in a watch file under build/calls, as for `ask`.

Provider credentials are read from the environment, and from `.env` for
whatever the environment does not already say.
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.agent import config as configuration  # noqa: E402
from components.agent import evals, rehearsal, tools  # noqa: E402
from components.agent.session import Session  # noqa: E402
from components.agent.watch import Watch  # noqa: E402
from components.agent.watch import render as render_watch  # noqa: E402
from components.modules.store import Store  # noqa: E402

REPORTS = ROOT / "build" / "evals"
CALLS = ROOT / "build" / "calls"


def _environment():
    """Credentials from .env, never over what the environment already says."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env", override=False)


def _told(turn):
    for line in rehearsal.trace(turn.messages):
        print(line)
    print()
    if turn.shown:
        print("what the person is shown:")
        print(turn.shown)
    said = turn.output.model_dump()
    text = said.get("message") or said.get("question") or ""
    print(f"\nthe turn ended with {turn.ended}: {text}")
    if turn.ended == "Plan":
        print(f"it will build: {said['builds']}")
        for key in ("records", "numbers", "cannot"):
            for line in said.get(key) or []:
                print(f"  {key}: {line}")
    if said.get("choices"):
        print("choices: " + " | ".join(said["choices"]))
    spent = turn.spent
    dollars = "cost unknown" if spent["dollars"] is None else f"${spent['dollars']:.4f}"
    print(f"spent: {spent['requests']} model calls, {spent['input']} tokens in, "
          f"{spent['output']} out, {dollars}, {spent['seconds']} s")


def _rehearse(script_path):
    script = rehearsal.load(script_path)
    store = Store.from_env()
    with tempfile.TemporaryDirectory() as scratch:
        first = Path(scratch) / "store"
        shutil.copytree(store.roots[0], first)
        copy = Store([first, *store.roots[1:]])
        for n, turn in enumerate(rehearsal.play_through(tools.Bench.from_env(copy), script), 1):
            print(f"==== request {n}")
            _told(turn)
    return 0


def _watch(name):
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Watch(CALLS / f"{stamp}-{name.replace('@', '').replace('/', '-')}.jsonl").http()


def _ask(module, text, scratch):
    watch = _watch(module)
    store = Store.from_env()
    try:
        if not scratch:
            _told(Session(tools.Bench.from_env(store), module, watch=watch).ask(text))
            return 0
        with tempfile.TemporaryDirectory() as place:
            first = Path(place) / "store"
            shutil.copytree(store.roots[0], first)
            copy = Store([first, *store.roots[1:]])
            _told(Session(tools.Bench.from_env(copy), module, watch=watch).ask(text))
        return 0
    finally:
        watch.stop()
        print(f"every call: {watch.path}")


def _eval(args):
    tasks, answer = evals.load(args.tasks)
    if args.only:
        unknown = set(args.only) - {t["name"] for t in tasks}
        if unknown:
            print(f"no task called {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        tasks = [t for t in tasks if t["name"] in args.only]
    config = configuration.load().with_models(builder=args.builder,
                                              accountant=args.accountant)
    store = Store.from_env() if args.part == "builder" else None
    watch = _watch(f"eval-{args.part}")
    print(f"every call: {watch.path}", flush=True)
    try:
        report = evals.run(tasks, config, args.part, store=store,
                           dsn=os.environ.get("UNITI_DSN"), answer=answer,
                           repeat=args.repeat, workers=args.workers,
                           dollars=args.dollars, watch=watch,
                           told=lambda line: print(line, flush=True))
    finally:
        watch.stop()
    print()
    for line in evals.render(report):
        print(line)
    print(f"\nreport: {evals.save(report, REPORTS)}")
    return 0 if all(t["passed"] for t in report["tasks"]) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m components.agent")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("guide")
    one.add_argument("topic", nargs="?", default="workflow")
    one = sub.add_parser("look")
    one.add_argument("module")
    one.add_argument("part", nargs="?", default="draft")
    one = sub.add_parser("catalogue")
    one.add_argument("text", nargs="?", default="")
    one.add_argument("--kind", default="")
    one = sub.add_parser("rehearse")
    one.add_argument("script")
    one = sub.add_parser("ask")
    one.add_argument("module")
    one.add_argument("text")
    one.add_argument("--scratch", action="store_true")
    one = sub.add_parser("watch")
    one.add_argument("file")
    one = sub.add_parser("eval")
    one.add_argument("tasks")
    one.add_argument("--part", choices=configuration.PARTS, default="builder")
    one.add_argument("--repeat", type=int, default=3)
    one.add_argument("--workers", type=int, default=1)
    one.add_argument("--dollars", type=float, default=0.50)
    one.add_argument("--only", nargs="*")
    one.add_argument("--builder")
    one.add_argument("--accountant")
    args = parser.parse_args(argv)

    if args.command == "rehearse":
        return _rehearse(args.script)
    if args.command == "watch":
        for line in render_watch(args.file):
            print(line)
        return 0
    if args.command in ("ask", "eval"):
        _environment()
    if args.command == "eval":
        return _eval(args)
    if args.command == "ask":
        return _ask(args.module, args.text, args.scratch)
    bench = tools.Bench(Store.from_env(), dsn=os.environ.get("UNITI_DSN"))
    if args.command == "guide":
        print(tools.guide(bench, args.topic))
    elif args.command == "look":
        print(tools.look(bench, args.module, args.part))
    else:
        print(tools.catalogue(bench, args.text, args.kind))
    return 0


if __name__ == "__main__":
    sys.exit(main())

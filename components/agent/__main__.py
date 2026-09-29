"""The agent's tools from a terminal.

    python -m components.agent guide [topic]
    python -m components.agent look @scope/name [part]
    python -m components.agent catalogue [text] [--kind K]
    python -m components.agent rehearse SCRIPT

`guide`, `look` and `catalogue` print exactly what the agent reads: the same
functions, the same text. `rehearse` plays a scripted builder through the
agent with no model behind it, on a copy of the store's first root, so the
store itself is left as it was; examples run in scratch logs on `UNITI_DSN`.
It prints every call and every answer, and then what the person would be
shown. Nothing is sealed and nothing is agreed: those are the person's.
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.agent import rehearsal, tools  # noqa: E402
from components.agent.builder import Proposal, put_before  # noqa: E402
from components.modules.store import Store  # noqa: E402


def _rehearse(script_path):
    script = rehearsal.load(script_path)
    store = Store.from_env()
    with tempfile.TemporaryDirectory() as scratch:
        first = Path(scratch) / "store"
        shutil.copytree(store.roots[0], first)
        copy = Store([first, *store.roots[1:]])
        bench = tools.Bench.from_env(copy)
        result = rehearsal.rehearse(bench, script)
        for line in rehearsal.trace(result.all_messages()):
            print(line)
        print()
        output = result.output
        if isinstance(output, Proposal):
            print("what the person is shown:")
            print(put_before(bench, output))
        print(f"\nthe turn ended with {type(output).__name__}: "
              f"{getattr(output, 'message', None) or getattr(output, 'question', '')}")
    return 0


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
    args = parser.parse_args(argv)

    if args.command == "rehearse":
        return _rehearse(args.script)
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

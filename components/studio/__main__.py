"""The studio from a terminal.

    python -m components.studio drafts
    python -m components.studio show @scope/name
    python -m components.studio steps @scope/name
    python -m components.studio do @scope/name <step> [key=value ...]

`show` is the studio's three columns as text: what is being built, the holes to
stand in, and what the gates and the business examples say about it. The
examples run against `UNITI_DSN`, each in a scratch log that is rolled back. `steps` is the same list a form
draws and an agent chooses from — every operation with the answers that fit
right now. `do` performs one of them.

Nothing here writes to the kernel. A draft is a file until somebody seals it,
and `python -m components.modules seal` is what does that.
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

from components.examples.examples import render  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio.draft import (  # noqa: E402
    OPERATIONS, apply, drafts, open_draft,
)
from components.studio.read import state, steps  # noqa: E402
from perform import connect  # noqa: E402

MARK = {True: "!", False: " "}


def _print_drafts(found):
    for held in found:
        was = f"revising {held['revises']}" if held["revises"] else "new module"
        print(f"{held['name']:<28} {was:<16} {held['steps']} steps")
    if not found:
        print("no draft open")


def _print_state(report):
    print(f"{report['name']} — {report['title'] or 'untitled'}")
    print(f"  becomes {report['becomes']}"
          + (f", superseding {report['revises']}" if report["revises"] else "")
          + f"; pins {', '.join(p['name'] + '@' + p['version'] for p in report['pins']) or 'nothing'}")

    print("\nwhat is being built")
    for c in report["classes"]:
        fills = f"  fills {', '.join(c['fills'])}" if c["fills"] else ""
        rows = "" if c["has_rows"] else "  (no rows: nothing can be one)"
        print(f"  class {c['name']}{fills}{rows}")
        for slot_name in c["slots"]:
            slot = next((s for s in report["slots"] if s["name"] == slot_name), None)
            if slot is None:
                print(f"      {slot_name}  (pinned)")
                continue
            marks = [slot["range"] or "string"]
            if slot["identifier"]:
                marks.append("identifier")
            if slot["binds"]:
                marks.append(f"is a {slot['binds']}")
            if slot["rule"]:
                marks.append(slot["rule"]["kind"])
            print(f"      {slot_name:<24} {', '.join(marks)}")
    loose = [s for s in report["slots"] if not s["on"]]
    for slot in loose:
        print(f"  slot {slot['name']}  (on no class)")

    print("\nwhere you are standing")
    for hole in report["holes"]:
        print(f"  [{MARK[hole['blocking']]}] {hole['question']}")
        step = hole["step"]
        if step and step["options"]:
            print(f"      do {step['op']} {step['choose']}=<one of "
                  f"{', '.join(step['options'])}>")
        elif step:
            print(f"      do {step['op']} {step['choose']}=...")
    if not report["holes"]:
        print("  nothing: every obligation is met and every term is described")

    print("\nwhat it would do")
    for table in report["tables"]:
        unfilled = (f", {len(table['unfilled'])} column(s) no rule reaches"
                    if table["unfilled"] else "")
        print(f"  table {table['class']} ({table['shape']}, "
              f"{table['columns']} columns{unfilled})")
    for refusal in report["refusals"]:
        print(f"  refused by {refusal['gate']}: {refusal['sentence']}")

    print("\nthe business examples")
    for line in render(report["examples"]):
        print(f"  {line}")
    if not report["examples"]:
        print("  none yet: nothing says what the numbers must be")
    elif not report["examples_run"]:
        print("  not run: no log to run them in")
    print(f"\n{'sealable' if report['sealable'] else 'not sealable yet'}")


def _state(store, name):
    """The draft, with its examples run when there is a log to run them in."""
    try:
        conn = connect(os.environ.get("UNITI_DSN"), connect_timeout=3)
    except psycopg.OperationalError:
        return state(store, name)
    with conn:
        try:
            return state(store, name, conn)
        finally:
            conn.rollback()


def _print_steps(found):
    for step in found:
        print(f"{step['op']:<14} {step['does']}")
        for takes in step["takes"]:
            shown = ", ".join(takes["options"][:8])
            if len(takes["options"]) > 8:
                shown += f", and {len(takes['options']) - 8} more"
            mark = "" if takes["required"] else " (optional)"
            print(f"    {takes['name']:<12} {takes['kind']}{mark}"
                  + (f": {shown}" if shown else ""))


def _pairs(given):
    out = {}
    for pair in given:
        if "=" not in pair:
            print(f"{pair!r} is not KEY=VALUE", file=sys.stderr)
            raise SystemExit(2)
        key, _, value = pair.partition("=")
        out[key] = value
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m components.studio")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("drafts")
    for command in ("show", "steps"):
        one = sub.add_parser(command)
        one.add_argument("name")
    do = sub.add_parser("do")
    do.add_argument("name")
    do.add_argument("step", choices=sorted(OPERATIONS))
    do.add_argument("args", nargs="*")
    args = parser.parse_args(argv)

    store = Store.from_env()
    try:
        if args.command == "drafts":
            _print_drafts(drafts(store))
        elif args.command == "show":
            _print_state(_state(store, args.name))
        elif args.command == "steps":
            _print_steps(steps(store, args.name,
                               open_draft(store, args.name)))
        else:
            apply(store, args.name, args.step, _pairs(args.args))
            if args.step == "discard":
                print(f"discarded the draft of {args.name}")
            else:
                _print_state(_state(store, args.name))
        return 0
    except Refusal as exc:
        print(f"refused by {exc.gate}: {exc.explain()}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

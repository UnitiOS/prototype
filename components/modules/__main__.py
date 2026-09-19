"""The module store from a terminal.

    python -m components.modules list
    python -m components.modules find [TEXT] [--kind K] [--fills ROLE] [--module M] [--pins M]
    python -m components.modules health @scope/name v1
    python -m components.modules seal @scope/name --actor <who> [--draft FILE] [--sealed-at ISO]
    python -m components.modules register @scope/name v1 --actor <who>

`find` asks the catalogue: every module, role, class and slot the store offers
now, narrowed by whatever is given. `health` reads one application's six
diagnoses against the log at `UNITI_DSN`. `seal` seals the module's
`draft.yaml` (or `--draft`) into the module's own directory, with its imports
resolved through the store. `register` writes an already sealed version's URIs
into another log. Both write to `UNITI_DSN`.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from components.modules.catalogue import catalogue, find  # noqa: E402
from components.modules.health import health  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from perform import connect  # noqa: E402
from seal import register, seal  # noqa: E402


def _pin(pin):
    return f"{pin['name']}@{pin['version']}"


def _print_found(found):
    for entry in found["entries"]:
        line = f"{entry['kind']:<7} {entry['name']:<28} {_pin(entry['module'])}"
        if entry.get("uri"):
            line += f"  {entry['uri']}"
        if entry.get("fills"):
            # A role's "fills" are the roles above it; a class's and a slot's
            # are the promises it keeps.
            verb = "is a" if entry["kind"] == "role" else "fills"
            line += f"  {verb} {', '.join(entry['fills'])}"
        print(line)
        if entry["kind"] == "role":
            for filler in entry["filled_by"]:
                print(f"        filled by {filler['class']} ({_pin(filler['module'])})")
        for rule in entry.get("read_by", []):
            print(f"        read by {_pin(rule['module'])} {rule['rule']} ({rule['kind']})")
    plural = {"class": "classes"}
    counts = ", ".join(f"{n} {plural.get(k, k + 's') if n != 1 else k}"
                       for k, n in found["counts"].items() if n)
    print(f"-- {counts or 'nothing'} found")


def _print_health(report):
    print(f"{report['name']}@{report['version']}: "
          f"{', '.join(_pin(p) for p in report['modules'])}")
    for refusal in report["refusals"]:
        print(f"  refused: {refusal['sentence']}")
    for diagnosis in report["diagnoses"]:
        findings = diagnosis["findings"]
        told = "not counted: no log" if findings is None else str(len(findings))
        print(f"\n{diagnosis['code']} ({told}) — {diagnosis['means']}")
        for finding in findings or []:
            print(f"  {finding['sentence']}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m components.modules")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    f = sub.add_parser("find")
    f.add_argument("text", nargs="?", default=None)
    f.add_argument("--kind", choices=["module", "role", "class", "slot"])
    f.add_argument("--fills")
    f.add_argument("--module")
    f.add_argument("--pins")
    h = sub.add_parser("health")
    h.add_argument("name")
    h.add_argument("version")
    s = sub.add_parser("seal")
    s.add_argument("name")
    s.add_argument("--actor", required=True)
    s.add_argument("--draft", default=None)
    s.add_argument("--sealed-at", default=None)
    r = sub.add_parser("register")
    r.add_argument("name")
    r.add_argument("version")
    r.add_argument("--actor", required=True)
    args = parser.parse_args(argv)

    store = Store.from_env()
    try:
        if args.command == "list":
            for name in store.names():
                versions = ", ".join(v["version"] for v in store.versions(name)) or "no version"
                print(f"{name}  {versions}")
            return 0

        if args.command == "find":
            _print_found(find(catalogue(store), text=args.text, kind=args.kind,
                              fills=args.fills, module=args.module, pins=args.pins))
            return 0

        with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
            if args.command == "health":
                _print_health(health(store, args.name, args.version, conn=conn))
            elif args.command == "seal":
                directory = store.directory(args.name)
                draft = Path(args.draft) if args.draft else directory / "draft.yaml"
                out = seal(conn, draft, actor_id=args.actor, into=directory,
                           sealed_at=args.sealed_at, store=store)
                print(f"sealed {args.name}@{out['version']} -> {out['path']} "
                      f"({len(out['minted'])} URIs minted)")
            else:
                out = register(conn, store.path(args.name, args.version),
                               actor_id=args.actor, store=store)
                print(f"registered {args.name}@{args.version} ({len(out['minted'])} URIs minted)")
        return 0
    except Refusal as exc:
        print(f"refused by {exc.gate}: {exc.explain()}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""The module store from a terminal.

    python -m components.modules list
    python -m components.modules seal @scope/name --actor <who> [--draft FILE] [--sealed-at ISO]
    python -m components.modules register @scope/name v1 --actor <who>

`seal` seals the module's `draft.yaml` (or `--draft`) into the module's own
directory, with its imports resolved through the store. `register` writes an
already sealed version's URIs into another log. Both write to `UNITI_DSN`.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from components.modules.store import ModuleError, Store  # noqa: E402
from perform import connect  # noqa: E402
from seal import DraftError, register, seal  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m components.modules")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
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

        with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
            if args.command == "seal":
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
    except (ModuleError, DraftError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

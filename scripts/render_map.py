"""render_map — every class of a sealed map, rendered once, into a directory.

`generate.py` renders one class. This asks it for all of them, so what a person
opens is the whole map rather than the one class someone remembered to name.
It is the same generator, called in a loop: no class is named here, and the
list comes from the map.

A class the map gives no `designates_type` slot has a table and no form. That
is the generator's rule, not this script's — the refusal is caught, reported on
stderr and counted, and the run still succeeds.

    render_map.py business/sorella/v1.yaml table --into build/sorella/v1/tables
    render_map.py business/sorella/v1.yaml form  --into build/sorella/v1/forms
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))

from generate import (MapError, connect, form, read_map,  # noqa: E402
                      render_form, render_table, table)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("map", help="a sealed version, e.g. business/sorella/v1.yaml")
    parser.add_argument("kind", choices=("table", "form"))
    parser.add_argument("--into", required=True)
    args = parser.parse_args(argv)

    map_ = read_map(args.map)
    into = Path(args.into)
    into.mkdir(parents=True, exist_ok=True)

    written, refused = 0, []
    with connect() as conn:
        for name in sorted(map_["view"].all_classes()):
            try:
                if args.kind == "table":
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc).isoformat()
                    text = render_table(table(conn, map_, name, valid_at=now, as_of=now))
                else:
                    text = render_form(form(conn, map_, name))
            except MapError as exc:
                refused.append(name)
                print(f"{name}: {exc}", file=sys.stderr)
                continue
            (into / f"{name}.txt").write_text(text, encoding="utf-8", newline="\n")
            written += 1

    total = len(map_["view"].all_classes())
    print(f"{args.kind}: {written} of {total} classes into {into}"
          + (f", {len(refused)} refused: {', '.join(refused)}" if refused else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Probe: three row rules a generator could read off the map, side by side.

Nothing in the map says an entity is a Material, so which entities are a
table's rows has to come from somewhere. Three candidates, all readable from
what already exists, none of them stated:

  any    subject of ANY of this table's columns          (what generate.py does)
  own    subject of a column this class declares itself
  ident  subject of the class's identifier slot

Read-only. Throwaway.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

from generate import read_map, columns, _registry, _subjects, _identifier  # noqa: E402
from perform import connect  # noqa: E402

CLOCK = datetime(2025, 9, 1, tzinfo=timezone.utc)
m = read_map("business/v1.yaml")
view = m["view"]
own_slots = {c: set(view.class_slots(c, direct=True)) for c in view.all_classes()}

print(f"{'class':<16}{'any':>6}{'own':>6}{'ident':>7}   note")
print("-" * 62)
with connect() as conn:
    by_uri, _ = _registry(conn)
    for name in sorted(view.all_classes()):
        cols = columns(m, name)
        pid = lambda cs: [by_uri[c["uri"]] for c in cs if c["uri"] in by_uri]

        n_any = len(_subjects(conn, pid(cols)))
        n_own = len(_subjects(conn, pid([c for c in cols if c["name"] in own_slots[name]])))

        ident = _identifier(m, name)
        n_id = len(_subjects(conn, pid([c for c in cols if ident and c["name"] == ident.name])))

        note = ""
        if n_any and not n_own:
            note = "all rows borrowed"
        elif n_own and not n_id:
            note = "no identifier declared"
        print(f"{name:<16}{n_any:>6}{n_own:>6}{n_id:>7}   {note}")

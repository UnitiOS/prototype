"""Probe: run the generator over every class in v1 and count what comes out.

Two tables were ever generated. The row rule is a guess, so the interesting
number is how the guess behaves across all nineteen classes at once — which
tables are right, which are empty, and which hold somebody else's rows.

Read-only. Throwaway.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

from generate import read_map, columns, table  # noqa: E402
from perform import connect  # noqa: E402

CLOCK = datetime(2025, 9, 1, tzinfo=timezone.utc)
m = read_map("business/v1.yaml")
view = m["view"]

# Which slots does a class own outright, and which does it inherit?
own = {c: set(view.class_slots(c, direct=True)) for c in view.all_classes()}

print(f"{'class':<16}{'rows':>5}{'cols':>5}{'blank%':>8}  {'inherited-only rows':<20}")
print("-" * 70)
with connect() as conn:
    for name in sorted(view.all_classes()):
        cols = columns(m, name)
        built = table(conn, m, name, valid_at=CLOCK, as_of=CLOCK)
        rows, ncol = len(built["rows"]), len(cols)
        cells = rows * ncol
        blank = sum(1 for r in built["rows"] for c in r["cells"] if c is None)
        pct = f"{100 * blank / cells:.0f}%" if cells else "-"

        # A row that only answers under inherited columns is a row of some
        # ancestor, not of this class.
        owncols = [i for i, c in enumerate(cols) if c["name"] in own[name]]
        borrowed = sum(
            1 for r in built["rows"]
            if owncols and all(r["cells"][i] is None for i in owncols)
        )
        flag = f"{borrowed} of {rows}" if borrowed else ""
        print(f"{name:<16}{rows:>5}{ncol:>5}{pct:>8}  {flag:<20}")

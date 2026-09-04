"""Part 1 — what the working log can answer about one real fact. Read-only.

Fresh milk, 38 litres, valid from 1 September, recorded at 21:00 on 31 August.
One row. Nothing has ever been recorded twice, so the as_of axis can only flip
between "nothing yet" and "38" — it cannot show a number moving.

Writes nothing. Throwaway probe.
"""

import sys
from datetime import datetime, timezone

sys.path.insert(0, "components/kernel")
from perform import connect          # noqa: E402
from resolve import resolve_single   # noqa: E402

URI = "uniti:uri"

FIND = """
SELECT a.subject_id FROM assertion a
WHERE a.predicate_id = (SELECT subject_id FROM assertion
                        WHERE subject_id = predicate_id AND value_literal = %s
                        ORDER BY seq LIMIT 1)
  AND a.value_literal = %s
"""


def t(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


with connect() as c:
    subj = c.execute(FIND, (URI, "uniti:fresh_milk")).fetchone()[0]
    pred = c.execute(FIND, (URI, "uniti:material_quantity")).fetchone()[0]

    print("subject   uniti:fresh_milk")
    print("predicate uniti:material_quantity")
    print()
    print(f"{'valid_at':<22} {'as_of':<22} {'answer':<8} {'what this is'}")
    print("-" * 88)

    reads = [
        ("2025-09-01T00:00", "2026-08-31T12:00", "today"),
        ("2025-09-01T00:00", "2025-12-31T00:00", "at the end of the year"),
        ("2025-09-01T00:00", "2025-08-31T21:00", "the seal instant itself"),
        ("2025-09-01T00:00", "2025-08-31T20:59", "one minute before the seal"),
        ("2025-08-31T22:00", "2026-08-31T12:00", "the evening of the count"),
    ]
    for valid_at, as_of, label in reads:
        row = resolve_single(c, subject_id=subj, predicate_id=pred,
                             valid_at=t(valid_at), as_of=t(as_of))
        answer = row["value_literal"] if row else "None"
        print(f"{valid_at:<22} {as_of:<22} {answer:<8} {label}")

    n = c.execute(
        "SELECT count(*) FROM assertion WHERE subject_id=%s AND predicate_id=%s",
        (subj, pred)).fetchone()[0]
    print()
    print(f"rows in the raw log for this exact pair: {n}")

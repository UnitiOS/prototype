"""Part 2 — the same fact, recorded three times, read at four moments.

Written to uniti_check, the throwaway database. `make check` drops and recreates
it on every run, so nothing here can touch the 301 rows of real evidence in
`uniti`. Entities are minted fresh, so the 200 synthetic tutoring rows already
sitting there are invisible to every query below.

Three acts, each one perform() call at its own recorded_at:

  1. 31 Aug 21:00   fresh milk is 38 litres from 1 September   the opening count
  2.  5 Oct 09:00   we were wrong, it was 34                   a correction
  3. 20 Oct 08:00   from 15 October it is 50                   the world moved

Act 2 revokes act 1's row and carries a replacement value, so it stays a
candidate. Act 3 revokes nothing: it is a later valid_from, not a correction.

Throwaway probe. Writes only to uniti_check.
"""

import sys
from datetime import datetime, timezone

sys.path.insert(0, "components/kernel")
from perform import connect, perform   # noqa: E402
from resolve import resolve_single     # noqa: E402

DSN = "postgresql://uniti:uniti@localhost:5433/uniti_check"
V = "v1"


def t(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


with connect(DSN) as c:
    _, names, first = perform(
        c, actor_id="marta", action_name="opening_count", ontology_version=V,
        mint=["milk", "qty"], recorded_at=t("2025-08-31T21:00"),
        note="the opening count, entered the same evening",
        assertions=[{"subject": "milk", "predicate": "qty", "value": "38",
                     "valid_from": t("2025-09-01T00:00"),
                     "source": "human_stated", "confidence": "high"}])
    milk, qty = names["milk"], names["qty"]

    perform(c, actor_id="marta", action_name="correct", ontology_version=V,
            recorded_at=t("2025-10-05T09:00"),
            note="miscounted in August, it was 34 all along",
            assertions=[{"subject": milk, "predicate": qty, "value": "34",
                         "valid_from": t("2025-09-01T00:00"),
                         "revokes": first[0],
                         "source": "human_stated", "confidence": "high"}])

    perform(c, actor_id="marta", action_name="stock_change", ontology_version=V,
            recorded_at=t("2025-10-20T08:00"),
            note="delivery on the 15th took it to 50",
            assertions=[{"subject": milk, "predicate": qty, "value": "50",
                         "valid_from": t("2025-10-15T00:00"),
                         "source": "human_stated", "confidence": "high"}])

    print("RAW LOG for this one (subject, predicate) pair")
    print(f"{'seq':<6} {'value':<7} {'valid_from':<12} {'recorded_at':<12} revokes")
    print("-" * 58)
    rows = c.execute(
        "SELECT seq, value_literal, valid_from, recorded_at, revokes FROM assertion"
        " WHERE subject_id=%s AND predicate_id=%s ORDER BY seq", (milk, qty)).fetchall()
    for seq, val, vf, ra, rev in rows:
        print(f"{seq:<6} {val:<7} {str(vf)[:10]:<12} {str(ra)[:10]:<12}"
              f" {'yes' if rev else '-'}")

    print()
    print("THE SAME FACT, READ AT FOUR MOMENTS")
    print(f"{'valid_at':<12} {'as_of':<12} {'answer':<8} {'what a person would call this'}")
    print("-" * 78)
    reads = [
        ("2025-09-01", "2025-09-30", "the September close, as it was read then"),
        ("2025-09-01", "2025-10-31", "the same September, re-opened in November"),
        ("2025-10-20", "2025-10-31", "today's stock, today"),
        ("2025-10-20", "2025-10-10", "today's stock, before the delivery was known"),
    ]
    for valid_at, as_of, label in reads:
        row = resolve_single(c, subject_id=milk, predicate_id=qty,
                             valid_at=t(valid_at + "T12:00"), as_of=t(as_of + "T12:00"))
        print(f"{valid_at:<12} {as_of:<12} {(row['value_literal'] if row else 'None'):<8} {label}")

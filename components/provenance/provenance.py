"""provenance — every assertion ever made about one subject and one predicate.

The one thing outside the compiler that reads the kernel, and it reads it for
one purpose: who said this, when, on what authority, and what was later
withdrawn. It computes nothing. There is no aggregation here, no resolution to
a winner, and no judgement about which row a reader should believe — the rows
come back in the order the log holds them and the reader decides.

    history(conn, subject=..., predicate=...)
        every row under that pair, oldest first, with both clocks, the whole
        of its provenance, and what revokes what. A pure retraction — a row
        carrying no value at all — comes back like any other, because "we were
        wrong" is a thing that was said.

    window(conn)
        what the log holds at all: how many intents and assertions, and the
        span of each of the two clocks. It answers the question a reader asks
        when a page comes back empty — not "why is this wrong" but "is the
        clock I set inside what was ever written down".

Both take URIs, not entity ids. A URI is what a page has and what a person can
read; the registry translation is one query and it belongs here rather than in
every caller.

Two doors, one implementation: `/why` is a page and the agent's MCP is a tool,
and neither of them is this file's problem.

    UNITI_DSN=... provenance.py <subject-uri> <predicate-uri>
    UNITI_DSN=... provenance.py --window
"""

import argparse
import sys
from pathlib import Path

from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from perform import DSN, connect  # noqa: E402
from seal import URI_PREDICATE  # noqa: E402

# Every URI the log has registered. The same read `generate._registry` makes,
# written again rather than imported: the generator is not a dependency of the
# thing that reads the log, and one SELECT is cheaper than that edge.
_REGISTRY_SQL = """
SELECT a.subject_id, a.value_literal
FROM assertion a
WHERE a.predicate_id = (
        SELECT subject_id FROM assertion
        WHERE subject_id = predicate_id AND value_literal = %s
        ORDER BY seq LIMIT 1)
  AND a.value_literal IS NOT NULL
"""

# Everything ever said under one pair, and nothing filtered. Neither clock
# appears in the WHERE: a row recorded tomorrow about last year is part of the
# history of this pair, and hiding it would be the resolution rule, which is
# not what this is.
_HISTORY_SQL = """
SELECT a.id, a.seq, a.value_literal, a.value_ref,
       a.valid_from, a.recorded_at, a.revokes,
       a.intent_id, a.source, a.confidence, a.authority, a.ontology_version,
       i.actor_id, i.agent_id, i.action_name, i.occurred_at, i.note
FROM assertion a
JOIN intent i ON i.id = a.intent_id
WHERE a.subject_id = %(subject_id)s AND a.predicate_id = %(predicate_id)s
ORDER BY a.valid_from, a.recorded_at, a.seq
"""

_WINDOW_SQL = """
SELECT count(*)          AS assertions,
       min(valid_from)   AS first_valid_from,
       max(valid_from)   AS last_valid_from,
       min(recorded_at)  AS first_recorded_at,
       max(recorded_at)  AS last_recorded_at
FROM assertion
"""

_INTENTS_SQL = "SELECT count(*) AS intents FROM intent"

_RECENT_SQL = """
SELECT a.id, a.seq, a.subject_id, a.predicate_id, a.value_literal, a.value_ref,
       a.valid_from, a.recorded_at, a.revokes,
       i.actor_id, i.action_name, a.intent_id
FROM assertion a
JOIN intent i ON i.id = a.intent_id
ORDER BY a.seq DESC
LIMIT %(limit)s
"""


class UnknownURI(LookupError):
    """A URI the log has never registered. Nothing was ever said under it."""


def _registry(conn):
    """uri -> entity id, and entity id -> uri."""
    with conn.cursor() as cur:
        cur.execute(_REGISTRY_SQL, (URI_PREDICATE,))
        rows = cur.fetchall()
    return {uri: eid for eid, uri in rows}, {eid: uri for eid, uri in rows}


def history(conn, *, subject, predicate):
    """Every assertion ever made about one (subject, predicate), oldest first.

    The value comes back under one key whichever column held it, with `ref`
    saying which it was, so a caller need not know that the kernel stores a
    literal and a reference in two places. A row with no value at all — a pure
    retraction — has `value` None and `ref` False, and is told apart from a
    row that states nothing by nothing, because there is no such row: the
    schema refuses one.

    `revoked_by` is filled in from the same set of rows, so a reader sees both
    ends of a withdrawal without a second query and without either row being
    hidden.
    """
    by_uri, by_id = _registry(conn)
    for uri in (subject, predicate):
        if uri not in by_uri:
            raise UnknownURI(f"the log has never registered {uri!r}")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_HISTORY_SQL, {"subject_id": by_uri[subject],
                                   "predicate_id": by_uri[predicate]})
        raw = cur.fetchall()

    revoked_by = {row["revokes"]: row["id"] for row in raw if row["revokes"]}
    rows = []
    for row in raw:
        rows.append({
            **row,
            "value": (by_id.get(row["value_ref"], str(row["value_ref"]))
                      if row["value_ref"] else row["value_literal"]),
            "ref": row["value_ref"] is not None,
            "revoked_by": revoked_by.get(row["id"]),
        })
    return {"subject": subject, "predicate": predicate, "rows": rows}


def window(conn):
    """What the log holds at all: how much, and between which clocks."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_WINDOW_SQL)
        held = cur.fetchone()
        cur.execute(_INTENTS_SQL)
        held.update(cur.fetchone())
        cur.execute("SELECT count(*) AS revocations FROM assertion WHERE revokes IS NOT NULL")
        held.update(cur.fetchone())
    return held


def recent_assertions(conn, limit=40, filter_type=None, actor=None, search=None):
    """Recent assertions recorded in the kernel, with resolved URIs and actors.

    Supports filtering by:
    - filter_type: 'all', 'revocations', 'master', 'stocktake', 'movement'
    - actor: filter by specific actor_id
    - search: filter by substring matching subject, predicate, or value
    """
    by_uri, by_id = _registry(conn)
    clauses = ["1=1"]
    params = {"limit": limit}

    if filter_type == "revocations":
        clauses.append("(a.revokes IS NOT NULL OR EXISTS (SELECT 1 FROM assertion r WHERE r.revokes = a.id))")
    elif filter_type == "master":
        clauses.append("i.action_name IN ('submit_Ingredient', 'submit_InternalLocation', 'submit_Supplier', 'submit_Person', 'submit_Unit', 'submit_UnitConversion', 'submit_MovementKind')")
    elif filter_type == "stocktake":
        clauses.append("i.action_name IN ('submit_StockCount', 'submit_StockCountLine')")
    elif filter_type == "movement":
        clauses.append("i.action_name = 'submit_StockMovement'")

    if actor:
        clauses.append("i.actor_id = %(actor)s")
        params["actor"] = actor

    where = " AND ".join(clauses)
    query = f"""
    SELECT a.id, a.seq, a.subject_id, a.predicate_id, a.value_literal, a.value_ref,
           a.valid_from, a.recorded_at, a.revokes,
           (SELECT r.id FROM assertion r WHERE r.revokes = a.id LIMIT 1) AS revoked_by,
           i.actor_id, i.action_name, a.intent_id, i.note
    FROM assertion a
    JOIN intent i ON i.id = a.intent_id
    WHERE {where}
    ORDER BY a.seq DESC
    LIMIT %(limit)s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    out = []
    for r in rows:
        sub = by_id.get(r["subject_id"], str(r["subject_id"]))
        pred = by_id.get(r["predicate_id"], str(r["predicate_id"]))
        val = (by_id.get(r["value_ref"], str(r["value_ref"]))
               if r["value_ref"] else r["value_literal"])

        if search:
            s_low = search.lower()
            if (s_low not in sub.lower() and s_low not in pred.lower()
                    and (val is None or s_low not in str(val).lower())):
                continue

        out.append({
            "id": r["id"],
            "seq": r["seq"],
            "subject": sub,
            "predicate": pred,
            "value": val,
            "valid_from": r["valid_from"],
            "recorded_at": r["recorded_at"],
            "actor_id": r["actor_id"],
            "action_name": r["action_name"],
            "intent_id": r["intent_id"],
            "note": r["note"],
            "revokes": r["revokes"],
            "revoked_by": r["revoked_by"],
        })
    return out


def _print_history(built):
    rows = built["rows"]
    print(f"{built['subject']}  {built['predicate']}  — {len(rows)} assertion(s)")
    for row in rows:
        value = "(retraction)" if row["value"] is None else row["value"]
        print(f"  valid_from {row['valid_from']}  recorded_at {row['recorded_at']}")
        print(f"    {value}")
        print(f"    source {row['source']}  authority {row['authority']}  "
              f"confidence {row['confidence']}")
        print(f"    intent {row['intent_id']}  actor {row['actor_id']}  "
              f"{row['action_name']}")
        if row["revokes"]:
            print(f"    revokes {row['revokes']}")
        if row["revoked_by"]:
            print(f"    revoked by {row['revoked_by']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("subject", nargs="?")
    parser.add_argument("predicate", nargs="?")
    parser.add_argument("--window", action="store_true",
                        help="what the log holds, rather than one pair")
    args = parser.parse_args(argv)

    with connect() as conn:
        if args.window:
            for key, value in window(conn).items():
                print(f"{key:18} {value}")
            return 0
        if not (args.subject and args.predicate):
            parser.error("a subject and a predicate, or --window")
        try:
            _print_history(history(conn, subject=args.subject,
                                   predicate=args.predicate))
        except UnknownURI as exc:
            print(f"{exc}  ({DSN})", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""kernel — what the log holds, read for a person looking at it.

Nothing here writes, and nothing here decides which fact stands. The winner of
a (subject, predicate) pair at a pair of clocks is whatever `resolve_single`
returns; this file only says, for every other row, *why* it is not the winner:

    not_recorded   recorded after `as_of` — the log did not know it yet
    retraction     a pure retraction: it withdraws a row and states nothing
    revoked        withdrawn by a row the log knew of at `as_of`
    not_yet_valid  it describes the world from after `valid_at`
    winner         what `resolve_single` returns for the pair
    outranked      a candidate, beaten by a later valid_from or record time

Everything is named through the registry `seal` writes: an entity's URI is
its assertion under `uniti:uri`. An entity with no URI is shown by its id.
"""

import sys
from pathlib import Path

from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent.parent
for part in ("kernel", "seal", "provenance"):
    sys.path.insert(0, str(ROOT / "components" / part))

from provenance import _registry, window  # noqa: E402
from resolve import resolve_single  # noqa: E402

_COLUMNS = """
a.id, a.seq, a.subject_id, a.predicate_id, a.value_literal, a.value_ref,
a.valid_from, a.recorded_at, a.revokes, a.intent_id, a.source, a.confidence,
a.authority, a.ontology_version
"""

# Which rows withdraw which, with when the withdrawal was recorded. A row is
# revoked at `as_of` only by a withdrawal the log already held then.
_REVOCATIONS_SQL = """
SELECT revokes, id, recorded_at FROM assertion
WHERE revokes = ANY(%(ids)s)
"""


class NotFound(LookupError):
    """Nothing in the log has this id."""


def _names(conn):
    return _registry(conn)[1]


def _named(names, entity_id):
    if entity_id is None:
        return None
    return {"id": entity_id, "uri": names.get(entity_id)}


def _revocations(conn, ids):
    if not ids:
        return {}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_REVOCATIONS_SQL, {"ids": list(ids)})
        rows = cur.fetchall()
    held = {}
    for row in rows:
        held.setdefault(row["revokes"], []).append(
            {"id": row["id"], "recorded_at": row["recorded_at"]})
    return held


def _status(row, revocations, valid_at, as_of, winner_id=None):
    """Why this row does or does not stand at (valid_at, as_of)."""
    if row["recorded_at"] > as_of:
        return "not_recorded"
    if row["value_literal"] is None and row["value_ref"] is None:
        return "retraction"
    if any(r["recorded_at"] <= as_of for r in revocations.get(row["id"], ())):
        return "revoked"
    if row["valid_from"] > valid_at:
        return "not_yet_valid"
    if winner_id is None:
        return "candidate"
    return "winner" if row["id"] == winner_id else "outranked"


def _row(row, names, revocations, status):
    return {
        "id": row["id"],
        "seq": row["seq"],
        "subject": _named(names, row["subject_id"]),
        "predicate": _named(names, row["predicate_id"]),
        "value": row["value_literal"],
        "ref": _named(names, row["value_ref"]),
        "valid_from": row["valid_from"],
        "recorded_at": row["recorded_at"],
        "revokes": row["revokes"],
        "revoked_by": [r["id"] for r in revocations.get(row["id"], ())],
        "intent_id": row["intent_id"],
        "source": row["source"],
        "confidence": row["confidence"],
        "authority": row["authority"],
        "ontology_version": row["ontology_version"],
        "status": status,
    }


def summary(conn):
    """How much the log holds, and the span of each clock."""
    held = window(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM entity")
        (entities,) = cur.fetchone()
    held["entities"] = entities
    held["registered"] = len(_names(conn))
    return held


def entities(conn, *, search=None):
    """Every entity, with its URI and how much the log says about it."""
    names = _names(conn)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT e.id, e.minted_at, e.intent_id,
                   count(a.id) AS assertions,
                   count(DISTINCT a.predicate_id) AS predicates
            FROM entity e
            LEFT JOIN assertion a ON a.subject_id = e.id
            GROUP BY e.id
        """)
        rows = cur.fetchall()
    out = []
    for row in rows:
        uri = names.get(row["id"])
        if search and search.lower() not in (uri or str(row["id"])).lower():
            continue
        out.append({**row, "uri": uri})
    out.sort(key=lambda r: (r["uri"] is None, r["uri"] or "", str(r["id"])))
    return out


def entity(conn, entity_id, *, valid_at, as_of):
    """Everything said about one entity, pair by pair, read at two clocks."""
    names = _names(conn)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, minted_at, intent_id FROM entity WHERE id = %s",
                    (entity_id,))
        found = cur.fetchone()
        if found is None:
            raise NotFound(f"no entity {entity_id}")
        cur.execute(f"SELECT {_COLUMNS} FROM assertion a WHERE a.subject_id = %s "
                    f"ORDER BY a.predicate_id, a.valid_from, a.recorded_at, a.seq",
                    (entity_id,))
        said = cur.fetchall()
        cur.execute(f"SELECT {_COLUMNS} FROM assertion a WHERE a.value_ref = %s "
                    f"ORDER BY a.seq", (entity_id,))
        pointed = cur.fetchall()

    revocations = _revocations(conn, [r["id"] for r in said + pointed])

    by_predicate = {}
    for row in said:
        by_predicate.setdefault(row["predicate_id"], []).append(row)

    facts = []
    for predicate_id, rows in by_predicate.items():
        winner = resolve_single(conn, subject_id=entity_id,
                                predicate_id=predicate_id,
                                valid_at=valid_at, as_of=as_of)
        winner_id = winner["id"] if winner else None
        facts.append({
            "predicate": _named(names, predicate_id),
            "standing": winner_id,
            "rows": [_row(r, names, revocations,
                          _status(r, revocations, valid_at, as_of, winner_id))
                     for r in rows],
        })
    facts.sort(key=lambda f: (f["predicate"]["uri"] is None,
                              f["predicate"]["uri"] or "", str(f["predicate"]["id"])))

    return {
        "id": found["id"],
        "uri": names.get(found["id"]),
        "minted_at": found["minted_at"],
        "intent_id": found["intent_id"],
        "facts": facts,
        "referenced_by": [_row(r, names, revocations,
                               _status(r, revocations, valid_at, as_of))
                          for r in pointed],
    }


def intents(conn, *, limit=50, offset=0):
    """User actions, newest first, with what each of them wrote."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT count(*) AS n FROM intent")
        total = cur.fetchone()["n"]
        cur.execute("""
            SELECT i.id, i.occurred_at, i.actor_id, i.agent_id, i.action_name,
                   i.reason_code, i.note,
                   (SELECT count(*) FROM assertion a WHERE a.intent_id = i.id) AS assertions,
                   (SELECT count(*) FROM entity e WHERE e.intent_id = i.id) AS minted,
                   (SELECT max(a.recorded_at) FROM assertion a WHERE a.intent_id = i.id) AS recorded_at
            FROM intent i
            ORDER BY i.occurred_at DESC, i.id
            LIMIT %(limit)s OFFSET %(offset)s
        """, {"limit": limit, "offset": offset})
        rows = cur.fetchall()
    return {"total": total, "limit": limit, "offset": offset, "intents": rows}


def intent(conn, intent_id, *, valid_at, as_of):
    """One action: who took it, and every entity and assertion it wrote."""
    names = _names(conn)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM intent WHERE id = %s", (intent_id,))
        found = cur.fetchone()
        if found is None:
            raise NotFound(f"no intent {intent_id}")
        cur.execute("SELECT id FROM entity WHERE intent_id = %s ORDER BY id",
                    (intent_id,))
        minted = [_named(names, r["id"]) for r in cur.fetchall()]
        cur.execute(f"SELECT {_COLUMNS} FROM assertion a WHERE a.intent_id = %s "
                    f"ORDER BY a.seq", (intent_id,))
        rows = cur.fetchall()
    revocations = _revocations(conn, [r["id"] for r in rows])
    return {
        **found,
        "minted": minted,
        "assertions": [_row(r, names, revocations,
                            _status(r, revocations, valid_at, as_of))
                       for r in rows],
    }


def log(conn, *, valid_at, as_of, limit=100, offset=0):
    """The assertion table itself, newest first."""
    names = _names(conn)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT count(*) AS n FROM assertion")
        total = cur.fetchone()["n"]
        cur.execute(f"SELECT {_COLUMNS} FROM assertion a ORDER BY a.seq DESC "
                    f"LIMIT %(limit)s OFFSET %(offset)s",
                    {"limit": limit, "offset": offset})
        rows = cur.fetchall()
    revocations = _revocations(conn, [r["id"] for r in rows])
    return {
        "total": total, "limit": limit, "offset": offset,
        "assertions": [_row(r, names, revocations,
                            _status(r, revocations, valid_at, as_of))
                       for r in rows],
    }


def plane(conn, *, valid_at, as_of, limit=5000):
    """Every assertion as a point on the two clocks, with its status there.

    Enough to draw the whole log at once: which rows the log knew of at `as_of`
    and which describe the world as it stood at `valid_at`. No winner is named
    here; that needs one pair at a time, and `entity` does it.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT count(*) AS n FROM assertion")
        total = cur.fetchone()["n"]
        cur.execute(f"SELECT {_COLUMNS} FROM assertion a ORDER BY a.seq LIMIT %s",
                    (limit,))
        rows = cur.fetchall()
    revocations = _revocations(conn, [r["id"] for r in rows])
    return {
        "total": total,
        "points": [{
            "id": r["id"], "seq": r["seq"], "subject_id": r["subject_id"],
            "valid_from": r["valid_from"], "recorded_at": r["recorded_at"],
            "status": _status(r, revocations, valid_at, as_of),
        } for r in rows],
    }

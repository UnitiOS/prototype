"""perform() — the only write gate into the kernel.

One user action becomes one `intent` row, zero or more minted `entity` rows,
and N `assertion` rows, in one transaction. Nothing here judges the facts:
the log stores what was said, not what it means.

Validation is deliberately absent. The check constraints in 001_schema.sql are
the only gate; slot-name validation arrives with the ontology (NEXT item 5).
"""

import os
import uuid

import psycopg

DSN = os.environ.get(
    "UNITI_DSN", "postgresql://uniti:uniti@localhost:5433/uniti"
)

# TODO: content hash of an ontology file, or "as of seq"? Open in OPEN.md (T3).
# The column is NOT NULL, so it carries a constant until that is decided.
ONTOLOGY_VERSION = "v0"

_INTENT_SQL = """
INSERT INTO intent (id, occurred_at, actor_id, agent_id,
                    action_name, reason_code, note)
VALUES (%s, COALESCE(%s, now()), %s, %s, %s, %s, %s)
RETURNING occurred_at
"""

_ENTITY_SQL = "INSERT INTO entity (id, intent_id) VALUES (%s, %s)"

_ASSERTION_SQL = """
INSERT INTO assertion (
    id, subject_id, predicate_id, value_literal, value_ref,
    valid_from, recorded_at, revokes, intent_id, source, confidence, authority,
    ontology_version, subject_key_id)
VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, now()), %s, %s, %s, %s, %s, %s, NULL)
"""
# subject_key_id stays NULL: its meaning is unresolved (OPEN.md, T1).


def connect(dsn=None):
    return psycopg.connect(dsn or DSN)


def _ref(value, names):
    """A label minted in this call, a uuid, or a uuid string."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if value in names:
        return names[value]
    return uuid.UUID(str(value))


def perform(
    conn,
    *,
    actor_id,
    action_name,
    mint=(),
    assertions=(),
    agent_id=None,
    reason_code=None,
    note=None,
    occurred_at=None,
    recorded_at=None,
):
    """Write one intent, its minted entities and its assertions.

    `mint` is a sequence of labels; each mints one entity under this intent.
    Inside `assertions`, `subject`, `predicate` and `ref` may name one of those
    labels instead of a uuid.

    An assertion is a dict:
        subject, predicate            required — label or uuid
        value                         text, xor with `ref`
        ref                           label or uuid, xor with `value`
        valid_from                    defaults to the intent's occurred_at
        source                        required — see the source_known constraint
        confidence, authority         optional
        revokes                       assertion uuid this one supersedes

    `recorded_at` is when the log learned all of this. It defaults to now(),
    which is the truth for every real write; passing it is how history that
    happened before this database existed is written. It belongs to the intent,
    not to the assertion: one act of recording lands at one instant, so rows
    recorded at different times are different intents.

    Returns (intent_id, names, assertion_ids).
    """
    intent_id = uuid.uuid4()

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                _INTENT_SQL,
                (intent_id, occurred_at, actor_id, agent_id,
                 action_name, reason_code, note),
            )
            (intent_occurred_at,) = cur.fetchone()

            names = {label: uuid.uuid4() for label in mint}
            for entity_id in names.values():
                cur.execute(_ENTITY_SQL, (entity_id, intent_id))

            assertion_ids = []
            for a in assertions:
                assertion_id = uuid.uuid4()
                cur.execute(
                    _ASSERTION_SQL,
                    (
                        assertion_id,
                        _ref(a["subject"], names),
                        _ref(a["predicate"], names),
                        a.get("value"),
                        _ref(a.get("ref"), names),
                        a.get("valid_from") or intent_occurred_at,
                        recorded_at,
                        a.get("revokes"),
                        intent_id,
                        a["source"],
                        a.get("confidence"),
                        a.get("authority"),
                        ONTOLOGY_VERSION,
                    ),
                )
                assertion_ids.append(assertion_id)

    return intent_id, names, assertion_ids

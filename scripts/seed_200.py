"""Reset the kernel and write 200 synthetic assertions.

Deterministic: one RNG seed, so the same log comes out every time. The seed is
a small tutoring business — students, cohorts, fees, phone numbers — stated,
corrected, changed and revoked over 2026.

Four kinds of event, one of which is a pure retraction: a row that names an
earlier row and states no value at all — "we were wrong", said without
inventing a replacement. resolve_single() drops it from the candidate set
(num_nonnulls(value_literal, value_ref) = 1), so it removes its target and
lets whatever stood before that stand again.

Run: .venv/Scripts/python.exe scripts/seed_200.py
"""

import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kernel"))

from perform import connect, perform  # noqa: E402

TOTAL = 200
RNG_SEED = 20260822
EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)

STUDENTS = [f"student_{i:02d}" for i in range(1, 13)]
COHORTS = ["cohort_a", "cohort_b", "cohort_c"]
PREDICATES = ["has_label", "monthly_fee", "member_of", "guardian_phone"]

_INSERT_SQL = """
INSERT INTO assertion (
    id, subject_id, predicate_id, value_literal, value_ref, valid_from,
    recorded_at, revokes, intent_id, source, confidence, ontology_version)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'v0')
"""

SOURCES = ["human_stated", "human_confirmed", "document_extracted", "imported"]


def _days(n):
    return EPOCH + timedelta(days=n)


def reset(conn):
    """Drop and recreate. PoC data is synthetic; this costs 30 seconds."""
    schema = (ROOT / "kernel" / "001_schema.sql").read_text(encoding="utf-8")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(schema)
    conn.autocommit = False


def build_rows(rng, names):
    """Return 200 assertion tuples, in insertion order.

    A row is a dict; `revokes` holds the index of an earlier row in this same
    list, resolved to a uuid at insert time.
    """
    rows = []

    # Every entity says what it is called. A projection can then be read
    # without a lookup table outside the log.
    for label in STUDENTS + COHORTS + PREDICATES:
        rows.append({
            "subject": label, "predicate": "has_label", "value": label,
            "ref": None, "valid_from": 0, "recorded_at": 0,
            "revokes": None, "source": "human_stated", "confidence": "high",
        })

    pairs = [(s, p) for s in STUDENTS
             for p in ("monthly_fee", "member_of", "guardian_phone")]

    # Where each pair currently stands, so later events can build on it.
    state = {pair: {"indices": [], "max_valid": 0, "max_recorded": 0,
                    "revoked": set()} for pair in pairs}

    def value_for(predicate):
        if predicate == "monthly_fee":
            return str(rng.randrange(30, 90) * 100_000), None
        if predicate == "guardian_phone":
            return f"08{rng.randrange(10**9, 10**10)}", None
        return None, rng.choice(COHORTS)

    def emit(pair, valid_from, recorded_at, revokes=None, pure=False):
        """Append one row. `pure` writes a retraction: no value, no ref.

        A pure retraction is not added to the pair's index list, so it never
        becomes the target of a later revocation. It is a leaf.
        """
        subject, predicate = pair
        value, ref = (None, None) if pure else value_for(predicate)
        rows.append({
            "subject": subject, "predicate": predicate, "value": value,
            "ref": ref, "valid_from": valid_from, "recorded_at": recorded_at,
            "revokes": revokes, "source": rng.choice(SOURCES),
            "confidence": rng.choice(["high", "medium", "low", None]),
        })
        st = state[pair]
        if not pure:
            st["indices"].append(len(rows) - 1)
            st["max_valid"] = max(st["max_valid"], valid_from)
        st["max_recorded"] = max(st["max_recorded"], recorded_at)

    for pair in pairs:
        valid_from = rng.randrange(0, 21)
        emit(pair, valid_from, valid_from + rng.randrange(0, 6))

    while len(rows) < TOTAL:
        pair = pairs[len(rows) % len(pairs)]
        st = state[pair]
        kind = rng.choice(["correction", "change", "revoke_replace", "retract"])

        if kind == "change":
            # The world moved: a later valid_from, written about when it moved.
            valid_from = st["max_valid"] + rng.randrange(10, 61)
            emit(pair, valid_from, valid_from + rng.randrange(0, 8))
            continue

        target = rng.choice(st["indices"])
        valid_from = rows[target]["valid_from"]

        if kind == "correction":
            # We were wrong: same valid_from, a later record time.
            emit(pair, valid_from, st["max_recorded"] + rng.randrange(1, 16))
        elif kind == "retract" and target not in st["revoked"]:
            # We were wrong, and we have nothing to put in its place.
            st["revoked"].add(target)
            emit(pair, valid_from, st["max_recorded"] + rng.randrange(1, 21),
                 revokes=target, pure=True)
        elif kind != "retract" and target not in st["revoked"]:
            # Same, said explicitly: the old row is named and replaced.
            st["revoked"].add(target)
            emit(pair, valid_from, st["max_recorded"] + rng.randrange(1, 21),
                 revokes=target)
        else:
            emit(pair, valid_from, st["max_recorded"] + rng.randrange(1, 16))

    return rows


def main():
    rng = random.Random(RNG_SEED)
    labels = STUDENTS + COHORTS + PREDICATES

    with connect() as conn:
        reset(conn)

        intent_id, names, _ = perform(
            conn,
            actor_id="seed",
            action_name="seed_200",
            note="synthetic tutoring business, 200 assertions",
            occurred_at=EPOCH,
            mint=labels,
        )

        rows = build_rows(rng, names)
        assert len(rows) == TOTAL, f"expected {TOTAL} rows, built {len(rows)}"

        ids = []
        with conn.cursor() as cur:
            for row in rows:
                assertion_id = uuid.uuid4()
                cur.execute(
                    _INSERT_SQL,
                    (assertion_id,
                     names[row["subject"]],
                     names[row["predicate"]],
                     row["value"],
                     names[row["ref"]] if row["ref"] else None,
                     _days(row["valid_from"]),
                     _days(row["recorded_at"]),
                     None if row["revokes"] is None else ids[row["revokes"]],
                     intent_id,
                     row["source"],
                     row["confidence"]),
                )
                ids.append(assertion_id)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*), count(revokes), count(value_ref), "
                "count(*) FILTER (WHERE num_nonnulls(value_literal, "
                "value_ref) = 0) FROM assertion")
            total, revoking, refs, pure = cur.fetchone()

    print(f"seeded {total} assertions "
          f"({revoking} revoking, {pure} of them pure retractions; "
          f"{refs} pointing at an entity), "
          f"{len(labels)} entities, 1 intent")


if __name__ == "__main__":
    main()

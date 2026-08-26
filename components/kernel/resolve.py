"""resolve_single() — the read side. Writes nothing.

One subject, one predicate, two clocks: what did we believe on `as_of` about
how the world stood on `valid_at`? The rule is the 2026-08-22 line in
DECISIONS.md and nothing more:

    candidates are valid_from <= :valid_at AND recorded_at <= :as_of,
    minus those revoked by a row whose recorded_at is also <= :as_of;
    winner is max valid_from, ties broken by max recorded_at, then max seq.

The revokes filter is evaluated at the query's as_of, not globally: a
retraction written after `as_of` had not happened yet, so it does not count.

A candidate must state something about the world: num_nonnulls(value_literal,
value_ref) = 1. That is not the same as `revokes IS NULL` — a row that revokes
an earlier row *and* carries a replacement value is still a candidate. Only the
pure retraction, which carries nothing, is excluded, so it removes its target
without putting itself in its place.

Ties break on recorded_at before seq. seq is insertion order, not knowledge
order: a backfilled import lands with a high seq and an old recorded_at, and on
seq alone it would win a tie it did not earn.
"""

from psycopg.rows import dict_row

_RESOLVE_SQL = """
SELECT a.id, a.seq, a.subject_id, a.predicate_id,
       a.value_literal, a.value_ref,
       a.valid_from, a.recorded_at, a.revokes,
       a.intent_id, a.source, a.confidence, a.authority,
       a.ontology_version
FROM assertion a
WHERE a.subject_id   = %(subject_id)s
  AND a.predicate_id = %(predicate_id)s
  AND a.valid_from  <= %(valid_at)s
  AND a.recorded_at <= %(as_of)s
  AND num_nonnulls(a.value_literal, a.value_ref) = 1
  AND NOT EXISTS (
      SELECT 1 FROM assertion r
      WHERE r.revokes = a.id
        AND r.recorded_at <= %(as_of)s
  )
ORDER BY a.valid_from DESC, a.recorded_at DESC, a.seq DESC
LIMIT 1
"""


def resolve_single(conn, *, subject_id, predicate_id, valid_at, as_of):
    """Return the winning assertion as a dict, or None if nothing stands."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            _RESOLVE_SQL,
            {
                "subject_id": subject_id,
                "predicate_id": predicate_id,
                "valid_at": valid_at,
                "as_of": as_of,
            },
        )
        return cur.fetchone()

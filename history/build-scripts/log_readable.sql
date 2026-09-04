-- The log, readable. Paste into DBeaver and run against uniti @ localhost:5433.
--
-- assertion holds uuids and entity has no name column: a URI is itself an
-- assertion, recorded under the well-known predicate uniti:uri, which registers
-- itself (one row whose subject, predicate and value all name uniti:uri).
-- The CTE below rebuilds uuid -> URI from that one row, then joins it three
-- times: once for the subject, once for the predicate, once for a value_ref.
--
-- This is the raw log, not a read. Every row ever written is here, superseded
-- ones included. To ask what stood at a moment, use resolve_single().

WITH uri AS (
    SELECT a.subject_id AS id, a.value_literal AS uri
    FROM assertion a
    WHERE a.predicate_id = (
            SELECT subject_id FROM assertion
            WHERE subject_id = predicate_id AND value_literal = 'uniti:uri'
            ORDER BY seq LIMIT 1)
      AND a.value_literal IS NOT NULL
)
SELECT a.seq,
       s.uri                              AS subject,
       p.uri                              AS predicate,
       COALESCE(a.value_literal, r.uri)   AS value,
       (a.value_ref IS NOT NULL)          AS is_ref,
       a.valid_from,
       a.recorded_at,
       a.confidence,
       a.source,
       a.ontology_version,
       a.revokes,
       i.action_name,
       i.actor_id
FROM assertion a
JOIN intent i     ON i.id = a.intent_id
LEFT JOIN uri s   ON s.id = a.subject_id
LEFT JOIN uri p   ON p.id = a.predicate_id
LEFT JOIN uri r   ON r.id = a.value_ref
ORDER BY a.seq;

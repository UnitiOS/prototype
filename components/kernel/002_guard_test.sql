-- Done condition for NEXT.md item 1: an UPDATE on assertion raises.
-- Insert one row through the front door, then try to mutate it.

BEGIN;

INSERT INTO intent (id, actor_id, action_name)
VALUES ('00000000-0000-0000-0000-000000000011'::uuid, 'guard_test', 'guard_test');

INSERT INTO entity (id, intent_id) VALUES
    ('00000000-0000-0000-0000-0000000000e1'::uuid, '00000000-0000-0000-0000-000000000011'::uuid),
    ('00000000-0000-0000-0000-0000000000e2'::uuid, '00000000-0000-0000-0000-000000000011'::uuid);

INSERT INTO assertion (
    id, subject_id, predicate_id, value_literal,
    valid_from, intent_id, source, ontology_version)
VALUES (
    '00000000-0000-0000-0000-0000000000a1'::uuid,
    '00000000-0000-0000-0000-0000000000e1'::uuid,
    '00000000-0000-0000-0000-0000000000e2'::uuid,
    'before',
    '2026-01-01T00:00:00Z', '00000000-0000-0000-0000-000000000011'::uuid,
    'human_stated', 'test');

COMMIT;

\echo '--- UPDATE on assertion (must raise) ---'
UPDATE assertion SET value_literal = 'after'
WHERE id = '00000000-0000-0000-0000-0000000000a1'::uuid;

\echo '--- DELETE on assertion (must raise) ---'
DELETE FROM assertion WHERE id = '00000000-0000-0000-0000-0000000000a1'::uuid;

\echo '--- TRUNCATE assertion (must raise) ---'
TRUNCATE assertion;

\echo '--- the row is unchanged ---'
SELECT value_literal FROM assertion
WHERE id = '00000000-0000-0000-0000-0000000000a1'::uuid;

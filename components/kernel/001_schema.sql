-- Uniti kernel — three tables, closed column list.
-- Run: psql -f components/kernel/001_schema.sql
-- Re-runnable: drops and recreates. PoC data is synthetic.

BEGIN;

DROP TABLE IF EXISTS assertion CASCADE;
DROP TABLE IF EXISTS entity    CASCADE;
DROP TABLE IF EXISTS intent    CASCADE;
DROP FUNCTION IF EXISTS kernel_deny() CASCADE;


-- One row per user action, not per field written.
CREATE TABLE intent (
    id            uuid PRIMARY KEY,
    occurred_at   timestamptz NOT NULL DEFAULT now(),
    actor_id      text        NOT NULL,
    agent_id      text,
    action_name   text        NOT NULL,
    reason_code   text,
    note          text
);


-- A registry of identity, nothing more. There is no class column:
-- class membership is an assertion.
CREATE TABLE entity (
    id         uuid PRIMARY KEY,
    minted_at  timestamptz NOT NULL DEFAULT now(),
    intent_id  uuid        NOT NULL REFERENCES intent(id)
);


-- Fifteen columns. This list is closed.
CREATE TABLE assertion (
    id               uuid PRIMARY KEY,
    seq              bigint GENERATED ALWAYS AS IDENTITY,

    subject_id       uuid        NOT NULL REFERENCES entity(id),
    predicate_id     uuid        NOT NULL REFERENCES entity(id),
    value_literal    text,
    value_ref        uuid        REFERENCES entity(id),

    valid_from       timestamptz NOT NULL,
    recorded_at      timestamptz NOT NULL DEFAULT now(),
    revokes          uuid        REFERENCES assertion(id),

    intent_id        uuid        NOT NULL REFERENCES intent(id),
    source           text        NOT NULL,
    confidence       text,
    authority        text,
    ontology_version text        NOT NULL,
    subject_key_id   uuid,

    -- A pure retraction carries no value: "we were wrong" can be said
    -- without inventing a replacement. Everything else states exactly one.
    CONSTRAINT value_exactly_one
        CHECK (num_nonnulls(value_literal, value_ref) = 1
               OR (revokes IS NOT NULL
                   AND num_nonnulls(value_literal, value_ref) = 0)),
    CONSTRAINT confidence_levels
        CHECK (confidence IS NULL OR confidence IN ('high','medium','low')),
    CONSTRAINT source_known
        CHECK (source IN ('human_stated','human_confirmed','document_extracted',
                          'imported','llm_inferred','llm_recommended',
                          'model_inferred','system_derived'))
);


CREATE INDEX idx_assertion_resolve
    ON assertion (subject_id, predicate_id, valid_from DESC, recorded_at DESC, seq DESC);

CREATE INDEX idx_assertion_revokes
    ON assertion (revokes) WHERE revokes IS NOT NULL;

CREATE INDEX idx_assertion_value_ref
    ON assertion (value_ref) WHERE value_ref IS NOT NULL;

CREATE INDEX idx_assertion_predicate
    ON assertion (predicate_id);

CREATE INDEX idx_assertion_intent
    ON assertion (intent_id);

CREATE INDEX idx_assertion_seq
    ON assertion (seq);


-- Guards. The log is append-only, without exception.

CREATE FUNCTION kernel_deny() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'kernel is append-only: % on % is not permitted',
        TG_OP, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_mutation_intent
    BEFORE UPDATE OR DELETE ON intent
    FOR EACH ROW EXECUTE FUNCTION kernel_deny();

CREATE TRIGGER no_truncate_intent
    BEFORE TRUNCATE ON intent
    FOR EACH STATEMENT EXECUTE FUNCTION kernel_deny();

CREATE TRIGGER no_mutation_entity
    BEFORE UPDATE OR DELETE ON entity
    FOR EACH ROW EXECUTE FUNCTION kernel_deny();

CREATE TRIGGER no_truncate_entity
    BEFORE TRUNCATE ON entity
    FOR EACH STATEMENT EXECUTE FUNCTION kernel_deny();

CREATE TRIGGER no_mutation_assertion
    BEFORE UPDATE OR DELETE ON assertion
    FOR EACH ROW EXECUTE FUNCTION kernel_deny();

CREATE TRIGGER no_truncate_assertion
    BEFORE TRUNCATE ON assertion
    FOR EACH STATEMENT EXECUTE FUNCTION kernel_deny();

-- Triggers catch mistakes; revocation catches paths nobody thought about.
REVOKE UPDATE, DELETE, TRUNCATE ON intent, assertion, entity FROM PUBLIC;

COMMIT;

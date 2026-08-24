# Decisions

Append-only. One line each. Never edited, never amended.
If a decision does not fit on one line, it is not yet a decision.

Reopening a line here requires a reason from **code or a user**, never from a
better argument.

Lines marked `(inherited)` were decided in the archived corpus, not here. Their
reasoning lives in `../archived/`. They are closed, which means not re-discussed
— it does not mean proven.

---

2026-08-21 · Old design corpus archived to `../archived/`. No longer a reference.
2026-08-21 · (inherited) Kernel is three tables: intent, assertion, entity.
2026-08-21 · (inherited) Build the kernel, do not adopt XTDB — per-statement versioning.
2026-08-21 · (inherited) Point-based valid time. No valid_to column.
2026-08-21 · (inherited) confidence has three levels (high/medium/low), not a number.
2026-08-21 · (inherited) Constraint violations are projections, not assertions.
2026-08-21 · (inherited) Neo4j deferred with no date.
2026-08-21 · Work order: vertical slice -> time-travel demo -> real user.
             Compiler and UI generator come after.

2026-08-21 · A retraction is itself an assertion; the revokes filter is evaluated at the query's as_of, not globally.
2026-08-22 · resolve_single: candidates are valid_from <= :valid_at AND
             recorded_at <= :as_of, minus those revoked by a row whose
             recorded_at is also <= :as_of; winner is max valid_from, ties
             broken by max seq.
2026-08-22 · A pure retraction carries no value. value_exactly_one is relaxed
             to allow zero values when revokes IS NOT NULL, so "we were wrong"
             can be said without inventing a replacement.
2026-08-22 · A candidate must state something about the world: resolve_single
             filters on num_nonnulls(value_literal, value_ref) = 1, not on
             revokes IS NULL. A valued row that also revokes stays a candidate.

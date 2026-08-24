# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.

Adding a sixth item means removing one.

---

- [x] Postgres running, three tables, deny triggers on UPDATE/DELETE
      done when: `psql -f kernel/001_schema.sql` succeeds and an UPDATE on
      assertion raises an exception

- [x] Minimal `perform()`, ~100 lines, no elaborate validation
      done when: one script writes 1 intent + 3 assertions and exits clean

- [x] `resolve_single()` with both time parameters
      done when: `pytest tests/test_bitemporal.py` is green (the 4-row table)

- [x] Seed 200 synthetic assertions, build one projection by replay
      done when: `make replay` produces an identical table twice in a row
      also: relax `value_exactly_one` to allow zero values when revokes IS NOT
      NULL, and cover a pure retraction in the tests
      also: add a retro-dated row (valid_from 1 Dec 2025, recorded 10 Mar 2026)
      so the fixture separates max valid_from from max recorded_at

- [ ] Pure retractions must not win: add the candidate-must-carry-a-value
      clause to resolve.py, drop the xfail, and put pure retractions into
      seed_200.py
      done when: `pytest tests` is green with no xfail and `make replay` is
      still identical twice in a row
      also: break ties on recorded_at before seq — seq is insertion order, so
      a backfilled import wins the tie today. Move the index with it.

- [ ] Domain ontology written **by hand** as YAML — no LLM, no compiler
      done when: the file exists and perform() uses it to validate slot names

---

Target this week: a commit someone else can run.
Not a tidy setup.

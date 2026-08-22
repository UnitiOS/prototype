# Now

Max 5 items. Every item needs a done condition that can be **executed**.
If the done condition cannot be written as a command, the item is not ready.

Adding a sixth item means removing one.

---

- [ ] Postgres running, three tables, deny triggers on UPDATE/DELETE
      done when: `psql -f kernel/001_schema.sql` succeeds and an UPDATE on
      assertion raises an exception

- [ ] Minimal `perform()`, ~100 lines, no elaborate validation
      done when: one script writes 1 intent + 3 assertions and exits clean

- [ ] `resolve_single()` with both time parameters
      done when: `pytest tests/test_bitemporal.py` is green (the 4-row table)

- [ ] Seed 200 synthetic assertions, build one projection by replay
      done when: `make replay` produces an identical table twice in a row

- [ ] Domain ontology written **by hand** as YAML — no LLM, no compiler
      done when: the file exists and perform() uses it to validate slot names

---

Target this week: a commit someone else can run.
Not a tidy setup.

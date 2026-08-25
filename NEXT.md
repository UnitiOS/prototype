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

- [x] Pure retractions must not win: add the candidate-must-carry-a-value
      clause to resolve.py, drop the xfail, and put pure retractions into
      seed_200.py
      done when: `pytest tests` is green with no xfail and `make replay` is
      still identical twice in a row
      also: break ties on recorded_at before seq — seq is insertion order, so
      a backfilled import wins the tie today. Move the index with it.

- [x] Adversarial pass over the kernel rules: every clause guarded, every
      unguarded behaviour written down
      done when: removing any single clause from resolve_single's WHERE or
      ORDER BY makes at least one test fail, the append-only guards run under
      pytest, and anything found but not fixed is a line in OPEN.md

- [x] One README that points instead of copying
      done when: someone who has never seen the repo can clone it, get
      `pytest tests` green, and say why as_of exists — from README.md and the
      files it points at, without reading LOG.md

- [x] `perform()` takes `recorded_at`, so a backdated row goes through the
      write gate instead of around it
      done when: `grep -rn "INSERT INTO assertion" tests scripts` returns
      nothing, `pytest tests` is green, and `make replay` is still identical
      twice in a row

- [x] `make check` — one command that runs pytest and replays twice
      done when: `make check` exits 0 on a clean clone and fails if either the
      tests fail or the two projections differ

- [x] README points at the eight stages and the current one
      done when: README.md names all eight stages and which is active, still
      without restating a rule that lives in another file

---

Stage 2 is blocked on two T3 lines in OPEN.md. Nothing else is added to this
file until they are closed.

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

- [x] Rewrite README for named stages and the component list
      done when: `grep -rniE "stage [0-9]|eight stages" README.md` returns
      nothing, all seven stage names and all seven component names from
      CLAUDE.md appear in README.md, `kernel` is the only component the file
      calls built, and `make check` exits 0 on a clean clone following only
      README.md

- [x] Directory tree named after the components in CLAUDE.md
      move only: `kernel/` -> `components/kernel/`, `tests/*.py` ->
      `tests/kernel/`. `scripts/`, `build/` and the root files stay where they
      are. Fix the paths that break — Makefile, docker-compose mount, sys.path
      inserts, README — and nothing else.
      done when: no `.py` or `.sql` file sits at the repo root or directly
      under `tests/`, every directory under `components/` is a name that
      appears in CLAUDE.md's component table, `make check` exits 0 on a clean
      clone, `build/projection_a.txt` is still **5334 bytes**, and
      `git show --stat -M HEAD` lists the moved files as renames rather than
      delete-plus-add

- [x] LinkML probe: does the map's escape hatch survive the generators
      done when: a throwaway schema — two classes, one slot with an explicit
      `slot_uri`, one slot `required: true`, one slot carrying `annotations`
      — runs clean through `gen-sqltables`, `gen-shacl`, `gen-erdiagram` and
      `gen-owl`; the SHACL output carries a `minCount` for the required slot;
      the `slot_uri` appears verbatim in the OWL output; and the annotation is
      still readable through `SchemaView` after a YAML round-trip. Findings go
      to LOG.md, the schema is deleted, and `linkml` is **not** added to the
      Makefile's venv target — it is a probe, not a dependency yet.

- [ ] `ontology`: which version applies at (valid_at, as_of)
      `components/ontology/resolve.py`. Pure — a directory of sealed files in,
      one version out. No database, no LinkML runtime; read the annotations as
      plain YAML.
      done when: `tests/ontology/` proves from fixture files alone that a
      version sealed after `as_of` is invisible; that among versions valid at
      `valid_at` the one sealed last wins; that a retroactive version beats the
      one it supersedes at the same `valid_at`; that an `as_of` before the first
      seal returns nothing rather than raising; and `make check` exits 0

- [ ] `perform()` takes ontology_version instead of hardcoding it
      the constant at `components/kernel/perform.py:22` is the last `# TODO`
      standing between the kernel and a real map.
      done when: `ONTOLOGY_VERSION` is gone, the parameter is required rather
      than defaulted, every existing caller passes `"v0"` explicitly, the write
      gate still rejects what it rejected before, `make check` exits 0 with 20
      passed, and `build/projection_a.txt` is still 5334 bytes

- [ ] `seal`: a draft becomes a version
      `components/seal/seal.py`. Validate the draft as LinkML and exit non-zero
      writing nothing if it is not. Assign the next version number, stamp
      `valid_from` and `sealed_at` into the schema's annotations, mint one
      predicate entity per `slot_uri`, then call `perform()` **once** with every
      stated fact — one seal is one intent.
      done when: sealing a fixture draft twice leaves `business/v1.yaml` and
      `business/v2.yaml`; every assertion from one seal shares one `recorded_at`
      and it equals that version's `sealed_at`; a `slot_uri` present in both
      versions yields one predicate entity, not two; facts carry the version's
      `valid_from`, not the seal instant; an invalid draft leaves the database
      and `business/` untouched; and `make check` exits 0

- [ ] T1: does `required: true` beside `identifier: true` give a `minCount`
      done when: LOG.md records what `gen-shacl` does, and if the answer is no,
      a line is appended to OPEN.md naming what enforces it instead

---

Nothing is blocked. `report` is deliberately partial until the shape of a
derived rule is decided from real stated rules, so only version resolution
belongs here — not the computation.

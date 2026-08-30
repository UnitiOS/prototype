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

- [x] `ontology`: which version applies at (valid_at, as_of)
      `components/ontology/resolve.py`. Pure — a directory of sealed files in,
      one version out. No database, no LinkML runtime; read the annotations as
      plain YAML.
      done when: `tests/ontology/` proves from fixture files alone that a
      version sealed after `as_of` is invisible; that among versions valid at
      `valid_at` the one sealed last wins; that a retroactive version beats the
      one it supersedes at the same `valid_at`; that an `as_of` before the first
      seal returns nothing rather than raising; and `make check` exits 0

- [x] `perform()` takes ontology_version instead of hardcoding it
      the constant at `components/kernel/perform.py:22` is the last `# TODO`
      standing between the kernel and a real map.
      done when: `ONTOLOGY_VERSION` is gone, the parameter is required rather
      than defaulted, every existing caller passes `"v0"` explicitly, the write
      gate still rejects what it rejected before, `make check` exits 0 with 20
      passed, and `build/projection_a.txt` is still 5334 bytes

- [x] `seal`: a draft becomes a version
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

- [x] T1: does `required: true` beside `identifier: true` give a `minCount`
      done when: LOG.md records what `gen-shacl` does, and if the answer is no,
      a line is appended to OPEN.md naming what enforces it instead

- [x] `valid_from` is required, not defaulted
      `components/seal/seal.py` falls back to the seal instant when a draft
      carries no `valid_from`. Remove the fallback: refuse the draft, exit
      non-zero, write nothing — the same shape as the `slot_uri` refusal a
      hundred lines above it.
      done when: a draft with no `valid_from` leaves `business/` and the
      database untouched and exits non-zero; every fixture that leaned on the
      fallback now states its own `valid_from`; no default is reintroduced
      anywhere in the file; and `make check` exits 0

- [x] README describes what is built now
      it still calls `kernel` the only component built. `ontology` and `seal`
      exist, `business/` exists, and CLAUDE.md's component table has eight rows.
      done when: README.md names `kernel`, `ontology` and `seal` as built and no
      other component as built, every directory under `components/` is
      mentioned, and `make check` exits 0 on a clean clone following only
      README.md

- [x] Two leaks that destroy evidence, and one instant the CLI cannot set
      `make check` wipes the working database twice: `schema` runs
      `001_schema.sql`, which drops and recreates, and `replay` reseeds on top.
      A real seal's assertions do not survive one run. `seal` never writes the
      transcript the 26 Aug decision requires. And `seal()` accepts `sealed_at`
      while its CLI does not, so a dated episode cannot be run from the command
      line.
      done when: `make check` run twice against a database holding a sealed
      version leaves that seal's assertion count unchanged both times; a draft
      whose `annotations.transcript` is missing, or names a file that does not
      exist, exits non-zero leaving the target directory and the three table
      counts untouched; a draft whose top-level `annotations` nests any mapping
      other than `facts` is refused the same way; the named transcript sits
      beside its version after a successful seal;
      `--sealed-at 2026-01-15T09:00:00Z` stamps that instant into both the
      version's `sealed_at` and every assertion's `recorded_at`; and
      `make check` exits 0

- [x] Empty the map store, and stop a test depending on what it holds
      `business/v1.yaml` and `v2.yaml` are fixture drafts sealed for real. Left
      there, the first role-played interview lands as v3 superseding a business
      nobody described. They cannot simply be deleted:
      `test_business_holds_the_two_sealed_versions` reads `business/` and
      asserts v2 supersedes v1, so the production map store is doing a fixture's
      job. What that test is really worth checking is that `resolve` can read
      what `seal` wrote — which two seals into a temp directory check better,
      and without the dependency.
      The working log has to be emptied in the same breath: it still holds the
      200 synthetic tutoring assertions and the seals made while validating, so
      "every predicate in the log has a home in the map" would be measured
      against a business nobody is describing. Both stores are cleared or
      neither is.
      done when: `business/` holds no `v*.yaml`; no test reads `business/`;
      a test still covers `seal` writing two versions and `resolve` picking the
      later one across both `valid_at` and `as_of`; the working database named
      by the default DSN reports zero rows in all three tables; and `make check`
      exits 0

- [x] Keep the first session's evidence, then empty both stores again
      done: eceada6 committed the four files, cc747f7 removed them, both stores
      empty, `make check` exits 0 at 41 passed and 5334 bytes twice.

- [x] The business profile, one page, frozen before the map is written
      done: `business/profile.md`, 286 lines. Marlow Gelato, single branch,
      north London, adopting the system 2025-09-01. Nine stock movements of
      which three are never recorded; two readings of "the vanilla"; shrinkage
      computed two ways that differ by two to four points every month. Frozen
      when `business/draft.yaml` is created.

- [x] `seal` writes `value_ref` from the slot's `range`
      done: ffb08eb, verified 4e4b457. 44 passed, `make check` exits 0. The
      kernel needed nothing — `perform()` had accepted refs since the first
      hundred lines; it was seven lines of `seal` calling `str()` on everything.
      Two gaps found and left as OPEN lines rather than fixed here: two slots
      sharing a `slot_uri` with different ranges, and an `any_of` slot of all
      classes reading as a literal. The second blocks the map.

- [x] Competency questions, frozen before any history is curated
      done: `business/questions.md`, six questions, Q6 expected to fail.

- [x] `seal` carries `confidence` on a fact
      done: d5601e7. 47 passed, three tests added. `FACT_OPTIONAL` holds the one
      name; the key check went from equality to two subset tests, so the set is
      widened by exactly one rather than opened. No default, and the kernel
      needed nothing.

- [x] The inventory map v1 draft, written and rendered, not sealed
      done: 94a01b1. 18 classes, 45 slots, 127 facts, `gen-owl` and
      `gen-erdiagram` both exit 0. Its done condition was wrong, not its
      execution — see the next item.

- [x] The draft's facts reach the master data the profile states
      done: b3b4f7b, verified here clause by clause rather than from LOG.
      Facts 127 → 176, subjects 40 → 48, slots carrying facts 10 → 19, empty
      slots 35 → 26. Five §8 locations with their temperatures, three bases,
      Marta and Dan, sixteen rotation flags with the right six false, one
      `flavour_base`, and no forbidden individual anywhere. The 26 slots that
      stay empty each need an event that has not happened or an instance the
      profile refuses to name, and the note pairs every one with its section.
      `make check` ok, 47 passed. `gen-owl` exits 0 only with a UTF-8 stdout —
      see OPEN.

- [ ] §10's rules, and keys for the things the business identifies
      Two gaps found by auditing the draft against the whole profile rather than
      against the item that produced it. §10 has no home anywhere, and eleven
      event classes carry neither a key nor a required slot. Both are cheap now
      and cost a v2 later. Nothing here enforces anything or computes anything.
      done when: a `Policy` class exists carrying the rule as Marta states it,
      with an optional threshold and an optional unit, and all six §10 rules are
      facts on it effective 2025-09-01; the five-litre rule carries its
      threshold and no unit, because §12 leaves that unstated; `MixBatch`,
      `StockCount` and `Sale` each declare a `unique_keys` over exactly the
      slots §4 names as identifying, and those slots become required; `Pan`
      declares no key and the provenance note says why; the five movement
      classes keep no key and no required slot; a `base_ingredients` slot exists
      on `Base`, range `Material`, multivalued, and receives no fact at all,
      because §3 names six ingredients for "a base mix" without saying which of
      the three and §6 omits the relationship; the note records the eggs of §8
      as a material named in one section and counted in none; `SchemaView` loads
      clean; `gen-doc` and `gen-mermaid-class-diagram` exit 0, and `gen-owl
      --no-use-native-uris` exits 0 under `PYTHONIOENCODING=utf-8`; `business/`
      still holds no `v*.yaml`; and `make check` exits 0

- [ ] Seal v1, and look at what landed
      Sealed at the evening the count was taken (§2, §9), never at today's
      clock: the record-time axis starts where the business learned it. The
      balances take effect the next morning, so `recorded_at` precedes
      `valid_from` here — correct, and nothing in the kernel forbids it.
      done when: `--sealed-at 2025-08-31T21:00:00Z` stamps both the version and
      every assertion; `business/v1.yaml` carries no `facts` block and its transcript
      sits beside it; every predicate in the log resolves to exactly one entity;
      every §6 relationship fact landed in `value_ref` and not
      `value_literal`; the six estimated quantities read `confidence = 'low'`;
      every assertion from the seal shares one `recorded_at` equal to the
      version's `sealed_at`; the facts carry 2025-09-01 rather than the seal
      instant; `make check` run twice leaves that seal's assertion count
      unchanged; and the three table counts and anything surprising are in
      LOG.md

- [ ] `generator`: one projection table and one form from v1 alone
      The first look at whether the map is worth anything. Reads the sealed v1
      and the log; generates, does not hand-write.
      done when: a projection table is generated from `business/v1.yaml` alone
      and its rows equal a direct read of the log at the same (valid_at, as_of);
      a form is generated for one class from the same file; a value entered
      through that form reaches the log via `perform()` and is returned by
      `resolve_single`; and `make check` exits 0

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.
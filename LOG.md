# Execution Log

Written **only by Claude Code**, after something has actually been run.
Desktop reads this at the start of a session and never writes to it.

Format: date · what was run · the result · what was surprising.
Plans do not go here. Only what already happened.

---

## 2026-08-22 · `git init`

Ran `git init -b main` in `PoC/` and added a `.gitignore` (Python, `.env`,
editor noise, `.claude/settings.local.json`). Repository is empty — no commit
yet, the five `.md` files are untracked.

Surprising: nothing. The repo did not exist before today; `../archived/` and
`../doc/` sit outside it and are therefore not versioned by this repo.

## 2026-08-22 · NEXT item 1 — schema + deny triggers

Ran `docker compose up -d` (postgres:17, host port 5433) then
`psql -f kernel/001_schema.sql` inside the container. Exit 0. Three tables,
15 columns on `assertion`, three check constraints, six indexes,
`kernel_deny()` with BEFORE UPDATE/DELETE and BEFORE TRUNCATE triggers on all
three tables, `REVOKE UPDATE, DELETE, TRUNCATE ... FROM PUBLIC`.

Ran `kernel/002_guard_test.sql`: inserted 1 intent + 2 entities + 1 assertion,
then UPDATE, DELETE and TRUNCATE on `assertion`. All three raised
`kernel is append-only: <OP> on assertion is not permitted`. The row still
reads `before`. Re-ran `001_schema.sql` a second time with data present —
exit 0, so the script is re-runnable.

Column list taken from `../archived/kernel-spec-source.md` §4, which is where
the closed 15-column list actually lives. Read only that section, only to
recover the closed list.

Surprising, three things:
- Docker Desktop had auto-updated at 04:25 and would not start; `wsl -l -v`
  reported no installed distributions. It came up on its own several minutes
  later, without intervention. Roughly 25 minutes lost to this.
- Git Bash rewrites `/kernel/001_schema.sql` into `C:/Program Files/Git/...`
  when passed through `docker exec`. Needs `MSYS_NO_PATHCONV=1`.
- The spec puts guards in `002_guards.sql`, but the done condition requires
  one file, so guards live in `001_schema.sql`. `002_guard_test.sql` is the
  test, not the guards.

## 2026-08-22 · NEXT item 2 — minimal `perform()`

Created `.venv` and installed `psycopg[binary]` 3.3.4 (Python 3.12.10). Wrote
`kernel/perform.py`, 124 lines: one call writes one `intent`, mints N `entity`
rows and inserts N `assertion` rows inside a single `conn.transaction()`.
`mint` takes a list of labels and returns label -> uuid, so an assertion can
name its subject, predicate or `ref` by label instead of a uuid. No validation
beyond the check constraints — slot names are item 5.

`ontology_version` is the constant `"v0"` with a `# TODO` pointing at the open
T3. `subject_key_id` is inserted as NULL.

Ran `.venv/Scripts/python.exe scripts/write_three.py`: exit 0. One intent, five
entities, three assertions — seq 1..3, one `value_ref` row, two `value_literal`
rows, all `ontology_version='v0'`, all `subject_key_id=NULL`. `recorded_at` came
from the column default; identical to the microsecond across the three rows.

Also checked the gate is atomic: a second assertion with `source='not_a_source'`
raised `CheckViolation` on `source_known` and the intent count was unchanged, so
the whole call rolled back.

Surprising, two things:
- Predicates are entities, so nothing can be asserted before something mints
  the predicate. The demo mints five entities to write three assertions. That
  is the schema working as designed, but it means `perform()` cannot be called
  usefully without a minting step until the ontology exists.
- `psycopg` returns `timestamptz` as `zoneinfo.ZoneInfo('Etc/UTC')`, not
  `datetime.timezone.utc`. Equality still holds; identity comparisons will not.

## 2026-08-22 · NEXT item 3 — `resolve_single()`

Installed `pytest` 9.1.1 into `.venv`. Wrote `kernel/resolve.py` (48 lines,
one SQL statement) and `tests/test_bitemporal.py`.

`resolve_single(conn, subject_id, predicate_id, valid_at, as_of)` returns the
winning assertion as a dict, or `None`. Reads only, writes nothing. The
statement is the 2026-08-22 decision line verbatim: `valid_from <= :valid_at
AND recorded_at <= :as_of`, `NOT EXISTS` a revoking row with `recorded_at <=
:as_of`, `ORDER BY valid_from DESC, seq DESC LIMIT 1`.

The fixture mints its subject and predicate through `perform()`, then inserts
its three assertions with direct SQL because `recorded_at` is a column default
that `perform()` does not accept. No retraction row was written — that is item 4.

Ran `.venv/Scripts/python.exe -m pytest tests/test_bitemporal.py -q`:
**5 passed**. The four-row table:

| valid_at | as_of | answer |
|---|---|---|
| 15 Jan | 20 Mar | 5500000 |
| 15 Jan | 20 Jan | 5000000 |
| 15 Jan | 10 Feb | 5500000 |
| 15 Mar | 20 Mar | 6000000 |

Plus a fifth: as_of 5 Jan, before anything was recorded, returns `None`.

Checked the first row actually bites — a naive as-of-only query
(`recorded_at <= '2026-03-20' ORDER BY recorded_at DESC LIMIT 1`) answers
6000000 where the correct answer is 5500000.

Surprising, two things:
- Nothing about the rule needed adjusting. The decision line was directly
  executable as SQL; the whole of item 3 is one `SELECT` and a `NOT EXISTS`.
- The fixture needs no database reset between runs. Every run mints fresh
  subject and predicate uuids, so the appended rows from earlier runs are
  invisible to the query. Append-only turns out to make test isolation free.

## 2026-08-22 · NEXT item 4 — retraction, retro-dated row, replay

Relaxed `value_exactly_one` in `001_schema.sql` to
`num_nonnulls(...) = 1 OR (revokes IS NOT NULL AND num_nonnulls(...) = 0)`
and re-ran the schema: exit 0.

Rewrote `tests/test_bitemporal.py` around a `_seed(conn, rows)` helper and two
fixtures over the same three-row base. `fact` adds the retro-dated row
(valid_from 1 Dec 2025, recorded 10 Mar 2026, 4000000); `retracted` adds a
pure retraction of the 5 Feb correction instead.

`.venv/Scripts/python.exe -m pytest tests -q`: **8 passed, 1 xfailed.**

The retro-dated row bites. `test_record_ordered_variant_gets_it_wrong` runs the
same candidate set ordered by `recorded_at DESC` and asserts it answers
4000000 where the correct answer is 5500000. Checked before moving on.

`make` did not exist on this machine. Installed GNU Make 4.4.1 via
`scoop install make`. It picks up Git's `sh.exe` from PATH, so the Makefile
works unchanged from both Git Bash and PowerShell.

`make replay` = `seed_200.py` (reset + 200 assertions) then `project.py` twice
then a byte comparison. Result: **5335 bytes both times, identical.** Also
identical between two separate `make replay` invocations, because the seed is
deterministic and the projection carries labels rather than uuids. The seed is
200 assertions over 12 students, 3 cohorts and 4 predicates; 40 rows revoke an
earlier row, 61 point at an entity.

Surprising, three things:
- **The pure retraction does not resolve, and `resolve_single()` cannot fix it
  without a rule change.** The retraction is itself a candidate: same subject,
  same predicate, `valid_from` 1 Jan, highest `seq`, not revoked by anything.
  It wins, and answers with no value. Dating it 10 Mar instead makes the two
  required cases pass but moves the hole: every read at `valid_at >= 10 Mar`
  then answers nothing. Probed both variants side by side before concluding.
  The 2026-08-22 resolve line was written when every row carried a value and
  never says a candidate must carry one. Left as
  `xfail(strict=True)`; `resolve_single()` untouched.
- The `has_label` predicate is the only entity that labels itself
  (`subject_id = predicate_id`), which is enough for the projection to find it
  from the log alone. No lookup table outside the kernel, and no uuids in the
  output.
- Deterministic output required removing wall-clock time from the projection
  header, not just seeding the RNG. The first instinct — a "generated at" line
  — would have broken byte-identity on its own.

## 2026-08-24 · NEXT item 5 — pure retractions must not win

Three changes, one commit.

**resolve.py, candidate clause.** Added `num_nonnulls(a.value_literal,
a.value_ref) = 1` to the WHERE. Not `revokes IS NULL`: a row that revokes an
earlier row *and* carries a replacement stays a candidate, and the seed has 40
of those. Dropped the `xfail(strict=True)` on
`test_retraction_resurfaces_the_earlier_row`; it passes.

**resolve.py, tie-break.** `ORDER BY valid_from DESC, recorded_at DESC,
seq DESC`. Moved `idx_assertion_resolve` in `001_schema.sql` to the same five
columns and re-ran the schema; `\d idx_assertion_resolve` confirms the new
column order.

New fixture `backfilled`: the three base rows plus an import at valid_from
1 Jan, recorded 20 Jan, 5100000 — inserted last, so highest seq, but it knew
less than the 5 Feb correction it ties with. Two tests, the same shape as the
retro-dated pair: `test_backfill_does_not_win_the_tie_on_seq` and
`test_seq_ordered_variant_gets_it_wrong`.

Probed both clauses by removing them one at a time before moving on:
- seq-first ordering: `test_backfill_does_not_win_the_tie_on_seq` fails,
  answering 5100000 where 5500000 is correct. 1 failed, 10 passed.
- no value clause: `test_retraction_resurfaces_the_earlier_row` fails,
  answering `None`. 1 failed, 10 passed.

Each clause kills exactly one test and nothing else.

**seed_200.py, pure retractions.** Fourth event kind, `retract`: names an
unrevoked earlier row and states no value. `emit(pure=True)` skips
`value_for()` and does not add the row to the pair's index list, so a pure
retraction never becomes the target of a later revocation — it is a leaf.
Seed now reports 200 assertions, **56 revoking, 31 of them pure**, 51 pointing
at an entity (was 40 revoking, none pure, 61 refs).

`pytest tests -q`: **11 passed**, no xfail, no xpass.
`make replay`: identical twice in a row, and identical across two separate
`make replay` invocations.

Projection: **5335 bytes before, 5334 after.** Still 55 rows over 55 distinct
(subject, predicate) pairs — nothing dropped out and nothing crashed on a
value-less row.

Surprising, three things:
- **Parts 1 and 2 did not move the projection at all** — still exactly 5335
  bytes. The old seed had no pure retraction to exclude and no tie where
  recorded_at and seq disagree, so both rule changes were invisible to replay.
  Only the seed change made them observable. A byte-identity check does not
  detect a rule change the fixture never exercises.
- The one-byte difference is not the retractions trimming a byte. Adding a
  fourth branch to `rng.choice` shifts the whole RNG stream, so it is a
  different log of the same shape: 36 of the 55 projection rows changed value,
  date or source. The byte count landing one apart is a coincidence.
- Of the 55 projected pairs, **4 resolve differently because of a pure
  retraction** — checked with a query comparing the winner against the winner
  computed while ignoring value-less revocations. The other 27 retractions hit
  rows that were not the standing winner at the projection's clocks.

Also: Docker Desktop was not running at the start of the session and had to be
started by hand. The container came back recreated rather than restarted, so
the database was empty; `seed_200.py` resets anyway, so nothing was lost.

## 2026-08-24 · NEXT item 6 — adversarial pass over the kernel rules

`resolve_single()` was not touched. This run wrote tests and three OPEN.md
lines.

**Clause coverage.** A throwaway script patched `kernel/resolve.py` one clause
at a time and ran `pytest tests` against each mutant, restoring the file
afterwards. Ten mutants: six WHERE conditions (counting the `NOT EXISTS` and
its inner `recorded_at <= :as_of` separately) and three ORDER BY keys.

Before — 11 tests. Three clauses could be deleted with the suite still green:

| clause removed | before (11 tests) | after (20 tests) |
|---|---|---|
| `subject_id =` | **green — unguarded** | `test_another_subject_under_the_same_predicate_is_invisible` |
| `predicate_id =` | **green — unguarded** | `test_another_predicate_about_the_same_subject_is_invisible` |
| `valid_from <= :valid_at` | 5 fail | 9 fail |
| `recorded_at <= :as_of` | `test_four_reads`, `test_nothing_stood_before_the_first_record` | same two |
| `num_nonnulls(...) = 1` | `test_retraction_resurfaces_the_earlier_row` | same |
| `NOT EXISTS` revoker | `test_retraction_resurfaces_the_earlier_row` | same |
| revoker's `recorded_at <= :as_of` | `test_retraction_had_not_happened_yet` | same |
| `ORDER BY valid_from DESC` | `test_four_reads`, `test_retro_dated_row_does_not_win_on_record_order` | same |
| `ORDER BY recorded_at DESC` | `test_backfill_does_not_win_the_tie_on_seq` | same |
| `ORDER BY seq DESC` | **green — unguarded** | `test_insertion_order_breaks_a_tie_on_both_clocks` |

Two new fixtures for the identity clauses, `crowded_subject` and
`crowded_predicate`: the base three rows plus one neighbour that ties the 5 Feb
correction on `valid_from` and beats it on `recorded_at`, so it takes the read
the moment its filter goes. Separate fixtures because one fixture holding both
neighbours makes a single test die for either removal and the table stops
attributing.

One new fixture for `seq`, `simultaneous`: a row with the same `valid_from`
**and** the same `recorded_at` as the 5 Feb correction, written after it. No
clock separates them, so insertion order decides and the answer is 5600000.

**Revoke-and-replace.** New fixture `replaced`: the base plus a row at
valid_from 1 Jan, recorded 10 Mar, 5700000, revoking the 5 Feb correction.
Read at valid 15 Jan / as_of 20 Mar answers **5700000**, as the 2026-08-22
decision line requires. Plus `test_revokes_is_null_variant_gets_it_wrong`, the
same shape as the other two variant tests: a candidate clause written as
`revokes IS NULL` throws the replacement away and falls back two steps to
5000000.

**Append-only under pytest.** New `tests/test_append_only.py`: one assertion
through `perform()`, then UPDATE, DELETE and TRUNCATE on `assertion`,
parametrised, each expecting `psycopg.errors.RaiseException` with
`kernel is append-only` in the message, each inside `conn.transaction()` so the
savepoint keeps the module connection usable. A fourth test re-reads the row
and gets `before`. `002_guard_test.sql` unchanged.

`_seed()` in `tests/test_bitemporal.py` now takes a `mint` tuple, accepts a
6-tuple row that names its own subject and predicate, and returns the whole
`names` dict. The three existing fixtures changed one line each.

`pytest tests -q`: **20 passed.** `make replay`: 5334 bytes, identical twice in
a row, unchanged from the last run — as expected, since nothing in the read
rule moved.

**Written to OPEN.md, not fixed.** Both revocation lines were probed before
being written down:
- Revoking a retraction does not resurface its target. Log: 5000000 (10 Jan),
  5500000 (5 Feb), a pure retraction of the 5 Feb row (10 Mar), then a row
  revoking that retraction (15 Mar). Reads at valid 15 Jan answer 5500000 /
  5000000 / 5000000 at as_of 5 Mar / 12 Mar / 20 Mar. The 5500000 never comes
  back. `seed_200.py` keeps pure retractions as leaves, so replay never sees
  this.
- Nothing ties `revokes` to the same (subject, predicate). A row asserting
  Bob's fee and revoking Alice's makes `resolve_single` answer `None` for
  Alice. Confirmed against the live database.
- `perform()` has no `recorded_at` parameter. Every backdated row in this
  repo — the fixtures and all 200 seed rows — goes in by direct SQL, around
  the write gate.

Surprising, three things:
- **`ORDER BY seq DESC` is only probabilistically guarded.** Ran the mutant six
  times: five failed, one passed. With the key gone the query has no total
  order, and `idx_assertion_resolve` already ends in `seq DESC` — so whenever
  the planner takes the index it hands back the right row anyway and the mutant
  survives. The clause is correct and the test asserts the right answer; it is
  the *detection* that is a coin flip, and no fixture shape fixes that while
  the index carries the missing key.
- **Both identity clauses were unguarded for the same reason**: every fixture
  mints a fresh subject *and* a fresh predicate, so either filter alone was
  enough to isolate it. The property that made test isolation free — append-only,
  new uuids per run — is exactly what hid the two clauses.
- Cross-slot revocation is not an edge case that needs a strange log to reach.
  Two ordinary rows written through `perform()` in one intent are enough, and
  the victim's read goes to `None` with nothing in its own slot having changed.

## 2026-08-24 · One README

Wrote `README.md` at the repo root, 120 lines. No other file created, no code
touched.

Verified the instructions it gives, in the order it gives them, against the
running stack: `docker compose ps` (uniti-db up, port 5433), then
`MSYS_NO_PATHCONV=1 docker compose exec -T db psql -U uniti -d uniti
-v ON_ERROR_STOP=1 -f /kernel/001_schema.sql` — exit 0 with data present, so
re-runnable holds. `.venv/Scripts/python.exe -m pytest tests -q`: **20 passed**.
`make replay`: 5334 bytes, identical twice in a row.

The README states no rule of its own. Every rule is a pointer: `DECISIONS.md`
for what is closed, `resolve.py`'s docstring for the read rule, `perform.py`'s
for the write gate, `001_schema.sql` for the columns and guards, `tests/` for
the spec, `OPEN.md` for what is known-broken and left alone.

Surprising, three things:
- **The NEXT.md item does not exist.** The unchecked items are the adversarial
  pass (done in commit ad78a21, still unticked) and the hand-written ontology.
  "One README" was given directly in the session prompt, with its own done
  condition. Built it as specified; NEXT.md not touched.
- **`make replay` resets the database**, and nothing in the repo said so out
  loud. A newcomer following the run section top to bottom would seed, then
  read, and never notice — but one who ran it against a database holding
  anything else would. It is now a bold line in the README.
- **The `Makefile` hard-codes `.venv/Scripts/python.exe`.** The repo is
  Windows-only by accident, not by decision. One line in the README, not a fix.

## 2026-08-25 · NEXT item — `make check`

`Makefile` only. No Python, no SQL, no test touched.

`check: venv schema test replay`, plus `@echo "check: ok"`. Two new targets:

- `venv` — a file target on `.venv/Scripts/python.exe`. Missing, it runs
  `python -m venv .venv` and installs `psycopg[binary]` and `pytest`. Present,
  make skips it. `test` and `replay` now depend on it.
- `schema` — `docker compose up -d`, a bounded `pg_isready` wait (60 × 1s, then
  it gives up with a message), then `001_schema.sql` through
  `docker compose exec`, `MSYS_NO_PATHCONV=1` and `ON_ERROR_STOP=1`.

**Clean clone.** `docker compose down` in `PoC/` (the container name is fixed,
so two compose projects cannot both hold `uniti-db`), `git clone` into the
scratchpad, `make check` there:

| run | wall clock | result |
|---|---|---|
| cold — no `.venv`, no image container, empty database | **33.7 s** | exit 0 |
| second run in the same clone | **2.5 s** | exit 0 |

Cold run did the whole path: venv created, two packages installed, container
created, postgres initialised, `DROP TABLE ... does not exist, skipping` three
times, 20 passed, 200 assertions seeded, 5334 bytes twice, identical. Same
5334 bytes as `PoC/` — the projection does not depend on the checkout.

**Both failure modes probed, both reverted.**

| probe | where it stopped | exit |
|---|---|---|
| `tests/test_zz_probe.py` with `assert False` | `test` target, before `replay` ran | 2 |
| `random.random()` in `project.py`'s `render()` | the `--compare` line, 5353 vs 5354 bytes | 2 |

Surprising, three things:
- **A clean clone checks the `Makefile` out with CRLF** — `core.autocrlf` is
  `true` globally, confirmed with `od -c` on the clone. GNU Make 4.4.1 for
  Windows runs it anyway, backslash continuations and the multi-line `until`
  loop included. No `.gitattributes` needed; this was the one thing expected to
  break the clean-clone run and it did not.
- **The readiness wait is not defensive padding.** Measured directly:
  `docker compose down`, `up -d`, then `psql` immediately — `connection to
  server on socket ... failed: No such file or directory`. The loop then
  reported **2 iterations**. On an already-created container it passes on the
  first try, which is why nothing before today noticed.
- The `until` loop had to end its body with `sleep 1`. A body ending in a false
  `[ $n -ge 60 ] && { ...; }` makes the whole loop exit 1 when the test is
  false, so make would have failed the target on the *successful* path.

Also: `README.md` still documents the manual four-step run and does not mention
`make check`. Left alone — the README is a separate NEXT item.

## 2026-08-25 · NEXT item — `perform()` takes `recorded_at`

`kernel/perform.py`, `tests/test_bitemporal.py`, `scripts/seed_200.py`. No
schema change, no new column, `resolve.py` untouched.

`perform()` gains one keyword, `recorded_at`, next to `occurred_at`. The
assertion insert writes `COALESCE(%s, now())`, so the default is unchanged and
every real write still gets the database's clock. **It is per call, not per
assertion.** One transaction lands at one instant; letting a caller give two
rows in the same transaction two different record times would manufacture a
record-time ordering that never happened.

That choice cost both callers their batching, because a row's `revokes` names
another row's id and ids are only known after the call that wrote them:

- `_seed()` in the fixtures: one `perform()` per row, plus one call up front
  that mints the entities. 4–5 intents per fixture instead of 1.
- `seed_200.py`: one `perform()` per row. **201 intents for 200 assertions**,
  where there was 1. Each row already knew what act produced it — the seed
  generates corrections, changes, revoke-replaces and retractions — so the kind
  is now carried on the row and becomes that intent's `action_name`
  (`state`, `correct`, `change`, `revoke_replace`, `retract`).

Done condition: `grep -rn "INSERT INTO assertion" tests scripts` returns
nothing, `pytest tests` **20 passed**, `make replay` identical twice
(5334 bytes). `make check` exits 0.

Surprising, three things:
- **The projection is byte-for-byte the one from before the change** — same
  5334 bytes, diffed against the pre-change `projection_a.txt`. 200 single-row
  transactions produce the same `seq` values as 200 inserts in one, because the
  identity sequence counts inserts and nothing rolled back. The counts held too
  (56 revoking, 31 pure, 51 refs): no `rng` call was added or moved.
- **200 separate transactions cost nothing measurable.** `seed_200.py` runs in
  **0.84 s** wall clock against the containerised Postgres, commit per row
  included. The batching that was given up was not buying speed.
- **The fixtures now guard `recorded_at` end to end.** Probe: replace the
  parameter with `None` in the insert, so every row falls back to `now()`.
  **15 of 20 tests fail** — not just the backfill and retraction cases, but the
  four-reads table itself, because with every row recorded now, an `as_of` of
  20 Jan sees either all of them or none. Probe reverted.

Proposed `DECISIONS.md` line, for Desktop to accept or reword:

> 2026-08-25 · `recorded_at` is a property of the intent, not of the
> assertion. `perform()` takes it once per call and it defaults to `now()`.
> One act of recording lands at one instant, so two rows that claim different
> record times are two intents. Synthetic history is written by replaying the
> acts, not by handing the gate a column value per row.

Also: the `[T1]` line in `OPEN.md` — "perform() cannot set recorded_at, so a
backdated import cannot go through the write gate; tests and seed_200.py bypass
it with direct SQL" — is answered by this change. Left in place; `OPEN.md` is
Desktop's to prune.

`kernel/002_guard_test.sql` still contains a direct `INSERT INTO assertion`.
That is deliberate and outside the grep: it is the psql-level proof that the
guards fire, and it must not depend on Python.

## 2026-08-25 · NEXT item — README names the eight stages

`README.md` only. No code touched; `make check` run to confirm the file's own
instructions still hold.

New `## The eight stages` section between the intro and `## Run it`: the eight
names, stage 1 marked as the active one, stage 4 marked as what this repo
holds. Names only — the section says outright that `CLAUDE.md` holds the list
that counts and wins any disagreement, and that the reasons live in
`DECISIONS.md`. The sentence about which stage decides the premise is a pointer
to `DECISIONS.md`, not a copy of it, on the same rule the file is built on: a
restated rule drifts from the one it restates.

Three things in the README had gone stale against the current `CLAUDE.md` and
would have contradicted the new section:

- **The definition of done.** The README claimed the PoC's definition of done
  was the four reads. `CLAUDE.md` now says it is the shrinkage report. Reworded
  to "what the kernel must do", with the PoC-level bar pointed at rather than
  restated. `test_four_reads` is still named as the specification.
- **The "not built" list.** It listed DDL compiler, UI generator and MCP
  alongside the stop-list. Those three are stages 5 and 8, not stop-listed, so
  the section now separates "later stage" from "stop-list" and points at
  `CLAUDE.md` for the list itself instead of copying it.
- **`make check` was missing** from `## Run it`. The previous item's log left
  it to this one. It is now the first block, with the by-hand steps kept below
  it for running one step alone.

Done condition: every one of the eight names is in `README.md`, the numbered
list is 1-8, and the active stage is named twice — in the list and in the
paragraph under it. `make check` exits 0 from this tree: 20 passed, 5334 bytes
twice.

Surprising: the stale lines, not the missing ones. The README was written on
24 Aug and `CLAUDE.md` changed the same day; a file whose whole discipline is
"point, never restate" still had three restatements in it, and all three were
already wrong. The two that mattered were both *definitions of done* — the
file's and the PoC's — which is the one thing a newcomer reads first.


## 2026-08-26 · README rewritten for named stages and the component list

`CLAUDE.md` was rewritten today: the stages are named instead of numbered,
interview and mapping merged into one stage, and a `## The components` section
appeared. The README still carried the eight numbered stages and an active-stage
marker, so it contradicted the constitution in three places at once.

What changed in `README.md`:

- **`## The eight stages` became `## The stages, and what is built`.** The
  numbered list is gone. The seven names run in one sentence and nothing else
  about them is copied — what each one means, and which one can kill the
  premise, are pointed at in `CLAUDE.md`, and why they are named rather than
  numbered is pointed at in `DECISIONS.md`.
- **The active-stage marker is gone.** Under a flow reading nobody is "at" a
  stage, so the paragraph explaining why the repo "runs ahead of the stage
  marker" was explaining a thing that no longer exists. What replaces it is
  checkable: the seven component names, and only `kernel` called built.
- **The many-to-many table is not repeated.** Which component serves which
  stage lives in `CLAUDE.md`; the README says so and stops.
- **Two stage numbers elsewhere.** "a stage 7 result" became "a **definition
  change** result"; "later stages — 5 and 8" in `## Not built` became the
  `generator` and the `agent MCP` named as components. The question table row
  "What are the eight stages, and which one is active?" became "What are the
  stages, and which components serve them?".

Deliberately not touched: the stage numbers in entries dated before 26 Aug in
this file and in `DECISIONS.md`. Both files are append-only and those entries
are history, not a contradiction.

Done condition: `grep -rniE "stage [0-9]|eight stages" README.md` returns
nothing (exit 1); all seven stage names and all seven component names appear;
`built` appears against `kernel` only. `make check` exits 0: 20 passed, 5334
bytes twice.

Surprising: Docker Desktop was not running, so the first `make check` failed at
`docker compose up -d` before any of the README work could be verified — the
one command the README promises works from a clean clone has a prerequisite the
README states in prose ("Needs Docker") and the Makefile does not check.

Also surprising: the whole edit was four replacements and the file got shorter.
The previous rewrite had to add explanation for why a kernel exists before its
own stage is reached. Naming the components instead of the stage the project is
"at" deleted the need for that explanation entirely — the awkward paragraph was
a symptom of the numbering, not of the repo.

---

## 2026-08-26 · Directory tree named after the components

Ran: `git mv kernel components/kernel`, `git mv tests/*.py tests/kernel/`, then
`make check`.

Six paths broke, one more than the item named. In order of discovery:

- five `sys.path.insert` lines — `scripts/project.py`, `scripts/seed_200.py`,
  `scripts/write_three.py`, and both test files. The two tests needed
  `parent.parent.parent`, not `parent.parent`: they sit one level deeper now.
- the compose mount, `./kernel` -> `./components/kernel`. The container path
  stays `/kernel`, so the Makefile's `-f /kernel/001_schema.sql` and the same
  line in README.md needed no change.
- `scripts/seed_200.py:47` reads `001_schema.sql` off disk to reset the
  database. This is not a `sys.path` insert and was not in the item's list; the
  first `make check` found it — tests were already green when replay died.

The Makefile itself changed by nothing. `pytest tests` still collects, and the
schema is applied through the container path.

Also fixed, both stale paths broken by the move rather than tidying: the `Run:`
comment in `001_schema.sql`, and the `002_guard_test.sql` reference in
`test_append_only.py`'s docstring. Nine README references followed the files.

Done condition: no `.py` or `.sql` at the root or directly under `tests/`;
`components/` holds only `kernel`, which is in CLAUDE.md's table; `make check`
exits 0 with 20 passed; `build/projection_a.txt` is 5334 bytes, unchanged;
`git diff --cached --stat -M` renders all six moves as renames.

Surprising: the byte-identical check caught nothing, because the one real break
stopped the run before a projection was written. The 5334 bytes proved the move
was complete, not that it was correct — `seed_200.py` failing loudly was worth
more than the byte count.

---

## 2026-08-26 · LinkML probe — does the escape hatch survive the generators

Ran: `pip install linkml` into `.venv` by hand (1.11.1, with linkml-runtime
1.11.1). A throwaway schema — `Batch` and `Freezer`; `batch_code` an identifier,
`quantity_on_hand` `required: true`, `shrinkage_rate` carrying an explicit
`slot_uri: uniti:shrinkage_rate_v1` and two `annotations`, `stored_in` a range
of `Freezer`. Schema, outputs and two probe scripts written outside the repo and
deleted. `linkml` is **not** in the Makefile.

All four generators exit 0. `gen-sqltables` gives `NOT NULL` on the required
slot and a real foreign key from `stored_in` to `Freezer(freezer_code)`.
`gen-erdiagram` gives mermaid with the relation. `gen-owl` prints a deprecation
warning about `consolidate_cardinality_axioms` to stderr and still exits 0.

The three checks:

- **`minCount` for the required slot** — yes. `sh:minCount 1` on
  `quantity_on_hand`, and only on it.
- **`slot_uri` verbatim in OWL** — **only with a flag.** By default `gen-owl`
  emits `probe:shrinkage_rate`; the `uniti:` URI is nowhere in the output. With
  `--no-use-native-uris` the subject becomes `uniti:shrinkage_rate_v1` and the
  prefix is declared. The default is `--use-native-uris`.
- **Annotation through `SchemaView` after a YAML round-trip** — yes. Dumped the
  schema with `yaml_dumper`, re-read it, and both the annotation value and
  `slot_uri` compare equal to the first pass.

Three things found that were not asked for:

- **`gen-shacl` honours `slot_uri` by default**, without a flag: `sh:path` on
  the shrinkage shape is `uniti:shrinkage_rate_v1` while its neighbours are
  `probe:`. So the two RDF generators disagree on the default, and the one that
  matters for the join is the one that needs the flag.
- **Annotations reach OWL as ordinary triples** — `probe:derived_rule "..."`
  hangs off the property. Not asked for, and useful: the escape hatch is not
  lost at the RDF boundary.
- **`identifier: true` is `required` in the model but has no `minCount` in
  SHACL.** `induced_slot("batch_code", "Batch").required` is `True`, yet its
  SHACL shape carries `sh:maxCount 1` and no `sh:minCount`. A validator reading
  only the SHACL will accept a `Batch` with no `batch_code`.

Mechanics for whoever writes the generator: read slots through
`SchemaView.induced_slot(slot, class)` — it carries `slot_uri`, `required` and
the annotations together. Its `.annotations` is a `JsonObj`, not the mapping
`get_slot()` returns: `.items()` and `.get()` raise `AttributeError` (they are
`_items()` and `_get()`), while `annots.derived_rule.value` and
`annots["derived_rule"].value` both work.

Conclusion: the escape hatch survives, and the decision that a predicate's
identity is its `slot_uri` holds — but "LinkML gives every slot a stable URI"
is only true of the output if the OWL generator is called with
`--no-use-native-uris`. That flag is now part of what the ontology store has to
remember, not a detail of one command.

`make check` still exits 0 with linkml sharing the virtualenv: 20 passed, 5334
bytes twice. linkml was left installed in `.venv` — gitignored, and removing it
proves nothing.

Surprising: the probe was aimed at whether `annotations` survive, and they did,
everywhere, unasked. What nearly failed was the part assumed safe — the
`slot_uri`, which a decision made today already depends on.

---

## 2026-08-27 · `ontology`: which version applies at (valid_at, as_of)

Ran: `make check` — 27 passed (20 kernel, 7 new), replay identical twice at
5334 bytes. The Makefile changed by nothing: `pytest tests` already collects
`tests/ontology/`, and the new code imports `re`, `datetime` and `pathlib` and
nothing else, so a clean clone's virtualenv — psycopg and pytest — still runs
it. PyYAML is in `.venv` only because the LinkML probe dragged it in; reading
four metadata keys with it would have made `make check` fail on a clean clone.

`components/ontology/resolve.py`. A directory of `vN.yaml` in, one dict out, or
`None`. The reader is a 20-line scan for top-level scalars and the immediate
children of `annotations` — it skips anything nested deeper, which the
`classes:` block in one fixture exercises.

Two things the item did not name, both forced by what was already there:

- **The two `resolve.py` files collide.** `components/kernel/resolve.py` is
  imported as top-level `resolve` by the kernel tests. A matching
  `sys.path.insert` for the ontology would return whichever pytest imported
  first. The ontology test inserts `components/` instead and imports
  `ontology.resolve` — a namespace package, no `__init__.py` added.
- **`draft.yaml` sits in the same directory as the sealed versions** (the
  2026-08-26 line on `business/`). The glob is `v*.yaml`, so a draft is never a
  candidate. The `chain` fixture carries a draft with a `valid_from` and no
  `sealed_at`: under a `*.yaml` glob it does not lose the resolution quietly,
  it raises.

Surprising: the rule is **not** the kernel's rule, though the decision says the
map is read the way the log is. The kernel orders on max `valid_from` first and
only then on record time; the map orders on `sealed_at` alone. With two
fixtures the difference was invisible — ordering on `valid_from` passed all six
tests, because in both of them the last-sealed version is also the
latest-starting one. A third fixture (`reseal/`: v2 starts 1 Feb, v3 starts
1 Jan and is sealed a month after v2) separates them, and only then does the
clause carry its weight. A mutation pass over the finished file — drop either
filter, order on `valid_from`, take the first candidate instead of the last,
glob `*.yaml`, drop the empty-set `None` — fails at least one test in every
case.

The divergence is right, not a slip in the decision: a fact is one claim among
many that vary across valid time, so the latest-starting one wins; a map
version applies whole, so the later seal supersedes whatever period it claims.
That is what makes a retroactive definition beat the one it supersedes.

For whoever writes `seal`: this reads the version's own name from a **top-level
`version:` key** inside the file, not from the filename — the 2026-08-26 line
says ontology_version is written inside the file. `version` is LinkML's own
schema slot, so it costs no annotation. A file carrying none is malformed and
raises by name. Proposed wording, if it deserves a decision: *the version
identifier is the schema's top-level `version`; the filename is a convenience
for humans and the resolver never trusts it.*

Left unguarded and written down here rather than fixed: two versions sharing a
`sealed_at` fall back to filename order, because the sort is stable. Seals are
sequential acts, so the collision needs two seals inside the same instant.

## 2026-08-27 — `perform()` takes `ontology_version`, and the constant is gone

Ran: `make check`.

`ONTOLOGY_VERSION = "v0"` and its `# TODO` are deleted from
`components/kernel/perform.py`. `ontology_version` is a keyword-only parameter
with no default — omitting it raises `TypeError` at the call, not a NOT NULL
violation in Postgres. Six call sites now pass `"v0"` explicitly: two in
`scripts/seed_200.py`, one in `scripts/write_three.py`, one in
`tests/kernel/test_append_only.py`, two in `tests/kernel/test_bitemporal.py`.
The column in `001_schema.sql` is untouched; only the Python constant moved.

`make check` exits 0. `build/projection_a.txt` is still **5334 bytes** and
still identical twice in a row — the seed writes the same `"v0"` the constant
wrote, so nothing about the recorded facts changed.

Surprising, mildly: the done condition asks for **20 passed** and the run is
**27 passed**. Nothing was skipped and no test was added here — the seven tests
in `tests/ontology/` landed with the previous item, which was written after that
number. The count is stale, not the condition. Note also that the ontology
item's checkbox in `NEXT.md` is still `[ ]` although its code is committed at
`b70075d`; Claude Code does not write that file.

Not touched, in scope only by adjacency: the module docstring of `perform.py`
still says slot-name validation "arrives with the ontology (NEXT item 5)" — a
numbered stage reference that the named-stages decision killed. It is one line
and belongs to whoever writes `seal`.

---

## 2026-08-27 · `seal`: a draft becomes a version

Ran: `make check` — **35 passed** (27 before, 8 new in `tests/seal/`), replay
identical twice at **5334 bytes**. Confirmed the two items this one depends on
were green before starting: `make check` at 27 passed, and `ontology_version` a
keyword-only parameter of `perform()` with no default.

`linkml` is now in the Makefile's venv target, as the item said. Verified by
building a throwaway virtualenv from that line alone —
`pip install "psycopg[binary]" pytest linkml` — and importing `psycopg`,
`pytest`, `yaml` and `linkml_runtime.SchemaView` from it. `linkml` pulls
`linkml-runtime` and PyYAML in with it, so `seal` needs no second line.

`components/seal/seal.py`, one file, plus four fixture drafts and one test
file. The CLI writes `business/vN.yaml` and exits 2 on a draft it will not
seal. Sealed the two fixture drafts into `business/` for real: `business/v1.yaml`
and `business/v2.yaml` are committed.

**Validation** is `SchemaView(text)` and nothing more, which is what the item
asked for. Probed what that catches: malformed YAML, a missing `id`, a missing
`name`, and any key the metamodel does not know (`TypeError` out of
`SchemaDefinition.__init__`). It does **not** catch a class naming a slot that
is not defined, or a range that is not a type — those load clean. That is the
line between parsing and resolving, and the generator will meet the second half.

Four things the item did not name, decided to keep going rather than to sit:

- **Where a fact is stated.** LinkML has no place for instance data in a
  schema, and it refuses unknown top-level keys, so the only hatch is
  `annotations`. Facts sit in `annotations.facts` as a list of three-key
  mappings — `subject`, `predicate`, `value`. Probed first that a nested list
  of mappings survives `SchemaView`: it does, and comes back as plain `list`
  and `dict`, not `JsonObj`.
- **Facts are stripped from the sealed version.** The map holds the logic, the
  log holds the history — a fact left in `vN.yaml` is a fact living outside the
  log. `v1.yaml` therefore contains no `facts` block, and the test asserts it.
- **Identity is a URI, registered by an assertion.** `entity` has no name
  column, so "the entity for `uniti:freezer_label`" has to be a fact like
  everything else. One well-known predicate, `uniti:uri`, registers every URI —
  and registers itself, one row whose subject, predicate and value all name
  `uniti:uri`. One query then finds every entity the map has ever named:
  `WHERE predicate_id = (SELECT subject_id FROM assertion WHERE subject_id =
  predicate_id AND value_literal = 'uniti:uri')`. On an empty log the subquery
  is NULL, the outer filter matches nothing, and the bootstrap row is minted by
  that same seal — no special case in the code.
- **An explicit `slot_uri` is mandatory.** A slot without one has no identity a
  fact can point at, and a derived URI would move on every rename. `seal`
  refuses the draft by slot name.

Sources: minted registry rows carry `system_derived` (the tool's act), stated
facts carry `human_stated` (the interviewee's).

Proposed wordings, if these deserve `DECISIONS.md` lines:

- *Facts stated in an interview live in the draft's `annotations.facts`, and are
  stripped from the sealed version. LinkML has no home for instance data and no
  other extension point; keeping them in the sealed file would put facts outside
  the log.*
- *An entity's identity in the kernel is a URI, recorded as an assertion under
  the well-known predicate `uniti:uri`, which registers itself. A predicate's
  URI is its LinkML `slot_uri`. `entity` has no name column, so a registry that
  is not an assertion would be a fourth store.*
- *`seal` refuses a draft in which any top-level slot declares no `slot_uri`.
  A skill can ask for one; only `seal` can guarantee it.*

Done condition, item by item: sealing a fixture draft twice leaves `v1.yaml` and
`v2.yaml` with `supersedes: v1` on the second; every assertion from one seal
shares one `recorded_at`, equal to that version's stamped `sealed_at`;
`uniti:freezer_label` and `uniti:freezer_location` each resolve to exactly one
entity across both seals — the second draft renames `freezer_location` to
`freezer_place` and keeps its `slot_uri`, and the entity does not move; facts
carry 2026-01-01 and 2026-02-01, not the seal instant; an invalid draft leaves
the three table counts and the target directory untouched; `make check` exits 0.

Surprising: the second real seal into `business/` minted **zero** entities. The
registry had been filled by an earlier run of the same command, so idempotency
by URI worked across two processes and a deleted pair of files without anything
being written to hold it — which is the point, but it is unsettling to watch a
seal record five facts and mint nothing.

Also surprising, and closed rather than left open: the ontology resolver's
annotation reader is shallow but not depth-limited — it takes any `key: value`
line under `annotations:` at any indent. A fact key called `valid_from` would
have been read as version metadata. `seal` rejecting any fact key outside
`subject/predicate/value` closes it; a future nested annotation block reopens it.

Not touched: `README.md` still calls `kernel` the only component built, which
two items ago was a done condition and is now false — `ontology` and `seal` both
exist. It is not this item's scope and belongs in `NEXT.md`.

Taken from the previous entry's hand-off: `perform.py`'s docstring no longer
points at "NEXT item 5" for slot-name validation; it points at `seal`.

---

## 2026-08-27 · T1 — does `required: true` beside `identifier: true` give a `minCount`

**No.** Adding an explicit `required: true` next to `identifier: true` changes
the `gen-shacl` output by nothing. Three throwaway one-class schemas written
outside the repo and deleted, run through the `linkml` 1.11.1 already sitting in
`.venv` from the 26 Aug probe; `linkml` is still not in the Makefile.

- **A** — `batch_code: identifier: true`, plus a plain `quantity_on_hand:
  required: true` as a control.
- **B** — the same, with `required: true` added beside `identifier: true`.
- **C** — B with `identifier: true` swapped for `key: true`.

A and B are byte-identical modulo the schema id: `batch_code` gets
`sh:maxCount 1` and no `sh:minCount`, while the control slot next to it gets
both. C differs: `key: true` **does** emit `sh:minCount 1` on `batch_code`.

`SchemaView.induced_slot("batch_code", "Batch").required` is `True` in all
three, so the model is not the thing that differs — `gen-shacl` reads
`identifier` and suppresses the `minCount` on purpose, and `required: true` is
not an override. There is no flag involved; C proves the generator can emit the
constraint and chooses not to for an identifier.

`gen-sqltables` on B gives `batch_code TEXT NOT NULL` and `PRIMARY KEY
(batch_code)`, unchanged from the 26 Aug run without the explicit `required`.

So the gap named on 26 Aug stands and cannot be closed inside the map by saying
`required: true`: a validator reading only the SHACL accepts an instance with no
identifier. What does enforce it is the generated DDL — or `key: true`, at the
cost of the slot no longer forming the instance URI, which is what the
`uniti:uri` decision rests on. One line appended to `OPEN.md`, nothing fixed.

Surprising: `key` and `identifier` are both `required` in the model, differ in
one documented way — whether the value forms the URI — and disagree in the SHACL
output about a constraint that has nothing to do with URIs.

## 2026-08-27 · `valid_from` is required, not defaulted

`make check` — 36 passed, replay identical twice, `build/projection_a.txt`
still 5334 bytes.

`components/seal/seal.py` fell back to the seal instant when a draft carried no
`valid_from`. The fallback is gone, replaced by `_valid_from()` — one refusal in
the same shape as `_slot_uris()`: raise `DraftError`, before the version file is
written and before `perform()` is reached, so nothing lands in `business/` or in
the log. The CLI prints `not sealed: …` and exits 2, as it already did for a
slot with no `slot_uri`.

New fixture `tests/seal/fixtures/no_valid_from.yaml` — valid LinkML, one slot
with a `slot_uri`, one stated fact, no `valid_from` — and
`test_a_draft_without_a_valid_from_is_refused`, which asserts the temp directory
is empty and the three table counts are unchanged. 35 tests became 36.

No fixture had to be changed: `draft_one`, `draft_two`, `invalid` and
`no_slot_uri` all already stated their own `valid_from`, and so does
`tests/ontology/fixtures/chain/draft.yaml`. The fallback was reachable only from
a draft nobody had written.

Surprising: nothing. The refusal cost four lines of code and the branch it
replaced was dead in every test that existed.

## 2026-08-27 · README describes what is built now

`make check` — 36 passed, replay identical twice, 5334 bytes.

README still named seven components under their old descriptive names
(`ontology store`, `interview chatbot`, `graph exporter`, `report + diff`,
`agent MCP`) and called `kernel` the only one built. It now says three are
built — `kernel`, `ontology`, `seal`, one directory each under `components/` —
and that `business/` beside them holds one file per sealed version. The
component table itself stays in `CLAUDE.md`; README says how many rows it has
and which of them exist, not what they do.

Two rows added to the "which file answers which question" table, pointing at
`components/ontology/resolve.py` and `components/seal/seal.py` docstrings. Two
stale facts in "Run it" corrected: the by-hand pytest line said 20 passed, and
the by-hand pip line did not install `linkml`, which `seal` imports — so the
Makefile path worked and the path README described did not.

Surprising: nothing in the wording drifted, only the counts. The file had no
copy of a rule that lives elsewhere to go stale — the stale things were all
inventories: how many components, how many tests, which packages.

## 2026-08-28 · Two evidence leaks, and the instant the CLI could not set

`make check` — 41 passed, replay identical twice, 5334 bytes.

**The wipe.** Both halves of `make check` reset the database: `schema` runs
`001_schema.sql`, which drops and recreates, and `replay` runs `seed_200.py`,
which does the same before seeding. A seal did not survive one check. The
Makefile now declares `CHECK_DB := uniti_check` and exports `UNITI_DSN` at the
top, so every target — schema, tests, replay — runs against a throwaway
database created on first use. Nothing in Python changed: everything already
routed through `connect()`. The `schema` target waits on `-d postgres` instead
of `-d uniti` and creates `uniti_check` if `pg_database` does not list it.

Verified by hand: sealed `draft_one.yaml` into the working database from the
CLI with `--sealed-at 2026-01-15T09:00:00Z` (10 assertions, one intent),
then ran `make check` twice. Both exited 0; that intent still had 10 assertions
after each, and the working log stayed at 210 rows.

**The transcript.** `annotations.transcript` is now required and is a path
relative to the draft's own directory. `seal` refuses when the key is absent or
the file is not there, before anything is written. On success the file is
copied beside the version as `vN.txt` and the sealed annotation is rewritten to
name the copy — copied, not moved, so a fixture transcript is not deleted by
the test that seals it. `components/interview/SKILL.md` said "moves"; it now
says what the code does.

**The nested annotation.** `_flat()` refuses any annotation other than `facts`
whose value is a mapping or a list. `facts` is exempt by construction: it is
stripped at seal, so its keys never reach a reader. The scanner in
`components/ontology/resolve.py` is untouched, and slot-level annotations are
untouched with it.

The leak is real and silent. `_read_header` on a draft carrying

    annotations:
      valid_from: '2026-01-01T00:00:00Z'
      session:
        value: the second interview
        annotations:
          valid_from: '2020-01-01T00:00:00Z'

returns `valid_from = 2020-01-01` — six years wrong, no error, wrong version
resolved for every reader.

**`--sealed-at`.** One argparse argument, parsed through the same `_utc()` the
draft's own instants go through, refused with exit 2 if it is not an instant.
`seal()` needed no change; only its CLI did.

Five fixtures and four tests: `draft_one.txt` and `draft_two.txt` beside the
drafts that now name them, `no_transcript.yaml`, `missing_transcript.yaml`,
`nested_annotation.yaml`. 36 tests became 41.

Surprising, and it moved the fixture: LinkML's own metamodel refuses a nested
mapping with arbitrary keys — `Annotation.__init__() got an unexpected keyword
argument 'valid_from'` — so the first `nested_annotation.yaml` never reached
the guard at all. The shape that does reach it is the one LinkML endorses,
`value` plus a nested `annotations` block, which is exactly the shape an author
following LinkML's own documentation would write. The guard is not defending
against a typo; it is defending against correct LinkML.

## 28 Aug — both stores emptied, and the test that depended on one

`make check` · 41 passed · replay identical twice · `build/projection_a.txt`
still 5334 bytes.

**The test first, because it is why this is not a delete.**
`test_business_holds_the_two_sealed_versions` called `resolve_version` against
the real `business/` directory. What it was worth testing is that `resolve` can
read what `seal` wrote — a seal-to-resolve integration, and the production map
store was doing a fixture's job to prove it. The module already seals both
fixture drafts into a `tmp_path_factory` directory, and those two differ on
both axes: v1 valid from 1 Jan, sealed 1 Mar; v2 valid from 1 Feb, sealed
1 Apr. So each axis can hide v2 on its own, and the replacement
`test_resolve_reads_back_what_seal_wrote` walks four points through them —
before the first seal (None), an `as_of` between the seals (v1), a `valid_at`
before v2 takes effect (v1), and past both (v2, naming v1 as superseded). More
coverage than the old test, no dependency on what `business/` happens to hold.
Test count unchanged at 41: one out, one in.

**`business/`.** `git rm business/v1.yaml business/v2.yaml`. Git deleted the
directory with them — it tracks no empty directory — so a `.gitkeep` holds it
open: `seal`'s default `--into` and the interview skill both write there by
path, and a clean clone has to have somewhere to write. README said the store
holds `v1.yaml` and `v2.yaml` today; it now says the store is empty and the
first interview seals `v1.yaml` into it.

**The working log.** 203 intents, 26 entities, 213 assertions at the default
DSN — the 200 synthetic tutoring rows from before `make` owned its own
database, plus the seals made while validating the last item. Emptied by
re-applying `001_schema.sql` to it, which is the only way: the deny triggers
refuse TRUNCATE as well as UPDATE and DELETE, so `DROP TABLE` is the sole
route in. Zero rows in all three tables, and `make check` leaves them at zero —
it runs entirely against `uniti_check`.

Surprising, and only visible because the wipe was the moment to look: the two
databases have not diverged at all. Before the drop, `uniti`'s indexes, check
constraints, foreign keys and deny triggers matched `uniti_check` line for
line — including `idx_assertion_resolve` with `recorded_at DESC` ahead of
`seq DESC`, the index that moved when the tie-break moved. So re-applying the
schema migrated nothing; it only wiped. The `make schema` line in `OPEN.md`
warns that the working log is never migrated and the two will diverge silently.
That is still true, and today's run is not evidence against it — it is a
one-off, by hand, prompted by a task that happened to need the same command.
The next schema change with real evidence in that database has no safe path:
migration and destruction are the same `psql -f`.

## 2026-08-29 · The first session kept, then both stores emptied again

`make check` · 41 passed · replay identical twice · `build/projection_a.txt`
still 5334 bytes.

**Committed first, because it is the only copy.** `business/draft.yaml`,
`draft.txt`, `v1.yaml` and `v1.txt` were untracked — the draft composed during
the 28 Aug interview with its transcript, and the version `seal` wrote from it
with the transcript copied beside it as `v1.txt`. One commit touching nothing
else (`git add` of the four paths, not `-a`; `CLAUDE.md`, `DECISIONS.md`,
`NEXT.md` and `OPEN.md` were modified in the working tree and stayed there).
Then `git rm` of the same four, `.gitkeep` left holding the directory open.

What the version actually held, since it is now only in history: three classes —
`Toko`, `Rasa`, `BahanBaku` — six slots, every one with a `slot_uri`, valid from
1 Feb 2026, sealed 28 Aug 09:02 UTC, `supersedes: null`. Neither stock slot
carries a unit; both say `Satuan belum ditanyakan`. That is the vocabulary the
29 Aug decision refused to build the proper map on top of.

**The working log.** 1 intent, 7 entities, 8 assertions at the default DSN —
what `seal` wrote from that draft, and the whole of it. Emptied the same way as
28 Aug: `psql -f /kernel/001_schema.sql` against `uniti`, because the deny
triggers refuse TRUNCATE and `DROP TABLE` is the only route in. Zero rows in all
three tables, and still zero after `make check`, which runs entirely against
`uniti_check`.

No code changed and no test changed. The 28 Aug item had already cut the last
test that read `business/`, so emptying the store again broke nothing — the
directory is now a store with one writer and no reader.

Surprising, and it is the shape of the loss rather than a fact about the code:
the transcript is worth more than the version. `v1.yaml` is six slots anyone
could rewrite in ten minutes; `v1.txt` records four questions asked, the two
that went unanswered, and a seal that failed because Docker was down — none of
which survives anywhere else, and none of which any generator would have
reproduced. The 29 Aug decision requiring a provenance note as the transcript of
the hand-authored map is buying the same thing deliberately.

Also surprising, and it cost an amend: Docker Desktop was down again at the
start of this run — the same failure the 28 Aug transcript records mid-session —
and came up in ten seconds once started, so the two-minute cost is starting it,
not waiting for it.

---

## 2026-08-29 · `seal` writes `value_ref` from the slot's `range`

Ran: `make check` — 44 passed (41 before, three new in `tests/seal/`), replay
identical twice at 5334 bytes, exit 0. The working `uniti` database still reads
0/0/0 in all three tables; everything here ran against `uniti_check`.

`_slot_uris` became `_slot_ranges` and returns `{slot_uri: is_class_range}`
instead of a list. Every caller changed with it: `_facts` looks the flag up and
carries it on each fact as `ref`, minting takes `list(ranges)` where it took the
list, and the assertion dict passes `ref=` instead of `value=` when the flag is
set. `perform()` was not touched — it has taken a `ref` key since it was
written, and the assertion column list is unchanged.

The class test is `slot.range in view.all_classes()`. Everything else — a type,
an enum, `default_range`, or no range at all — is a literal, which is what the
old code did to every value, so no existing fixture moved.

Three things the probe settled before any code was written:

- **`induced_slot(name)` works without a class.** It applies `default_range`
  and inheritance, and returns the class name verbatim for a class range. The
  26 Aug note gives it as `induced_slot(slot, class)`; the class argument is
  optional and a top-level slot needs none.
- **An absent `slot_uri` is not synthesised by `induced_slot`.** It returns
  `None`, so the refusal that `_slot_uris` carried survives the move unchanged
  and `no_slot_uri.yaml` still fails on the same slot name.
- **No `default_range` means `range` is `None`, not `string`.** So the rule has
  to be "is it a class", never "is it not a type" — the latter would have made
  every unranged slot in a schema without a `default_range` a ref.

A class-ranged value naming a URI nothing else names registers it exactly as a
subject does: the value URIs are appended to the same list the subjects are
deduped through, so two facts naming `uniti:freezer_d` — one as a subject, one
as a value — reach one entity. The database was already enforcing half of this:
`value_ref` has a foreign key to `entity(id)`, so a ref to an unregistered URI
could not have been written at all, it would have raised.

New fixture `tests/seal/fixtures/draft_ranges.yaml` and its provenance note.
`stored_in` ranges on `Freezer`, `batch_litres` on `decimal`, `batch_flavour` on
nothing; six facts, three of them refs, and `uniti:freezer_e` named only on the
value side. `draft_one` and `draft_two` were left alone — both have tests
counting their facts exactly, and a third draft reads better than a fourth
assertion bolted onto the first.

Not guarded, and now a line in OPEN.md: two slots sharing one `slot_uri` while
declaring different ranges. `setdefault` lets the first win. Sharing a
`slot_uri` is legal because that is how a rename keeps its identity —
`draft_two` does exactly that — and no draft has yet disagreed about the range,
so the refusal has no case to be written against.

Surprising: the kernel needed nothing. `perform()` has accepted `ref` and
resolved a minted label through it since the first hundred lines, and
`value_exactly_one` and the foreign key were both already sitting there waiting.
The gap the item names — a map declaring relationships the log cannot honour —
was never in the log. It was seven lines of `seal` calling `str()` on everything
it saw.

---

## 2026-08-30 · Verifying the `value_ref` item, and one range shape it misses

Ran: `make check` — 44 passed, replay identical twice at 5334 bytes, exit 0.
`ffb08eb` already carries the item; this run re-ran it against the committed
tree and read the 29 Aug decisions in order to check the entry above was written
against what stands. It was: the interview is deferred, the map is hand-authored
and goes through the same gate, `value_ref` is required before v1 rather than
after, and the morning's episode runner was undecided again by evening — none of
which changes what `seal` does with a range.

Probed one shape the item does not cover, because the next item needs it. A slot
whose ranges are all classes but stated as `any_of` — no top-level `range` —
comes back from `induced_slot` with `range='string'` (the schema's
`default_range`) and the two classes under `.any_of`. So `slot.range in classes`
is `False` and the fact lands as a literal. No refusal, no warning: the wrong
column, silently.

That is not hypothetical for the map. Profile §6 lists "Stock count counted
Material or Pan", which is exactly that shape. The map can avoid it — give the
two a common superclass, which the flat `is_a`-only decision of 29 Aug allows —
or `seal` learns to read `any_of`. Choosing between those is the map's decision,
not this item's, so it is a line in OPEN.md blocking `map` rather than a change
here.

Surprising: `default_range` makes the miss silent rather than loud. Without one,
`range` would be `None` and an `any_of` slot would at least be visibly unranged;
with `string` declared at the top of the schema, an unranged slot and a
class-union slot are indistinguishable to the rule as written.

## 2026-08-30 · `seal` carries `confidence` on a fact

Ran `make check`: **47 passed**, replay identical twice at 5334 bytes, exit 0.
Three tests added, from 44.

`seal` now takes an optional fourth fact key. `FACT_KEYS` stays the three
required ones and a new `FACT_OPTIONAL` holds `confidence`; the key check went
from equality to two subset tests, so the set is widened by exactly one name
rather than opened. The level is checked against `CONFIDENCE_LEVELS`
— `high`, `medium`, `low`, copied from the kernel's `confidence_levels`
constraint — and refused with the fact's number if it is anything else. No
default: `fact.get("confidence")` is `None` when the fact is silent, and
`perform()` has read `a.get("confidence")` since it was written, so the
pass-through is one dict key. Fourteen lines of `seal`, nothing in the kernel.

Fixtures: `draft_confidence.yaml` states three facts — one `high`, one `low`,
one silent — and `bad_confidence.yaml` and `extra_fact_key.yaml` are that same
draft with `fairly sure` and with an added `authority: Marta`. Both refusals
land in `_facts`, which runs before the `valid_from`, `_flat` and transcript
checks, so nothing is written before either is raised; the bad-confidence test
also runs the CLI to check the exit code is non-zero rather than only that the
exception is raised.

Mutation-checked the three clauses. Dropping the pass-through, replacing the
level check with `if False`, and dropping the upper subset test each turn at
least one new test red. The second and third also break the first test as
collateral: a bad draft that is no longer refused writes assertions, and the
seal fixtures are module-scoped against a shared database.

Surprising: nothing, which is itself the point — the column has existed since
`001_schema.sql` and no writer had ever set it, and the whole cost of the first
one was a subset test and a dict key. The 27 Aug `valid_from` refusal is what
made the no-default choice cheap to make: the shape was already in the file.

---

## 2026-08-30 · The v1 draft, written and rendered, not sealed

Ran: `make check` — **47 passed**, replay identical twice at 5334 bytes, exit 0.
`gen-owl --no-use-native-uris business/draft.yaml` and
`gen-erdiagram business/draft.yaml` both exit 0. The working `uniti` database
still reads 0/0/0 and `business/` holds no `v*.yaml`: nothing here touched the
kernel, because every check ran `seal`'s own validators as functions rather than
through `seal()`.

Two files: `business/draft.yaml` and `business/draft.txt`, the provenance note
that stands where a transcript would. 18 classes, 45 top-level slots, 127 facts,
7 identifier slots, 6 `stated_rule` annotations. Every done condition checked by
running it, not by reading:

    SchemaView loads clean; all 45 slots declare a slot_uri; all 11 section-6
    relationships are class-ranged and Pan inherits a Location-ranged slot;
    no any_of anywhere, in the parse or in the text; 19 materials each with a
    quantity, a unit and a location; 10 pan-table flavours each with a
    kilogram fact; exactly 6 `low` and 13 `high`; no fact whose predicate is
    declared by Pan, StockCount, MixBatch, Sale, Base or Supplier.

The pans reconcile: 12 on display, 9 in storage, 21 in all, 57.6 kg.

Three findings about the renders, all now lines in OPEN.md. `gen-owl` carries
the draft's entire `facts` block into the TTL as one 12,176-character string
literal on the ontology node — a quarter of the file — because facts live under
`annotations` and gen-owl renders annotations as triples. It disappears on seal.
`gen-erdiagram` flattens `is_a`, so the five movement subclasses repeat their
parent's six relationships and 20 of the 32 edges are the same six seen five
times. And slot-level `unit` reaches nothing: `ucum_code` and `symbol` appear
zero times in the TTL, so half of the 30 Aug unit decision survives a generator
and half does not.

Nine choices the profile underdetermines are recorded in the note with the
alternative rejected, not as comments in the draft. The one that most deserves
a second look before the seal, and a proposed wording for it:

> 2026-08-30 · Section 7's movements are five classes in v1, not nine and not
> none. Four of the nine rows are already section 4 things — "base made" is a
> MixBatch, "pan filled" is a Pan, "scoop sold" is a Sale, "stock counted" is a
> StockCount — so only GoodsReceived, PanMoved, PanPulled, ThrownOut and
> TastingGiven are new, under one StockMovement parent carrying what section 7's
> table states. The done condition names sections 4 and 6 only, but it also sets
> a floor — at least what an ERP inventory module holds — and an inventory
> module with no stock movements does not clear it. Three of the five are the
> movements nobody records, which is the finding the profile insists on
> preserving; as values of a `movement_kind` enum they would be three strings
> rather than three things a reader can see are empty.

Surprising: the profile's own read order says "movements become classes of their
own", and following it turned out to add five classes rather than nine, because
four of section 7's rows are section 4 things seen from the other side. The
overlap is not stated anywhere in the profile — it only appears when both tables
are translated at once.

Also surprising, and it decided the URI scheme: exactly one name collides.
"Dark chocolate" is 8 kg in the dry store and a flavour in the cabinet, and
nothing else in section 13 collides at all, so prefixing every URI with its
class would have been a scheme built for one case — and would have hidden the
case it was built for.

## 2026-08-30 · The draft's facts reach the master data, still not sealed

Ran: 49 facts added to `business/draft.yaml`, 127 -> 176. `make check` —
**47 passed**, replay identical twice at 5334 bytes, exit 0. The working `uniti`
database still reads 0/0/0 and `business/` holds no `v*.yaml`: nothing here
touched the kernel. No class and no slot changed; the item was facts only.

What arrived, and the section each came from:

    §8   the five places stock sits, each with a name and a temperature —
         three of them, the blast freezer, the storage freezer and the display
         cabinet, are named and pointed at by nothing
    §3   the white, chocolate and sorbet bases
    §1   Marta and Dan, and no counter staff
    §5   sixteen `flavour_in_rotation`, sixteen scoop prices, pistachio's base,
         fresh milk's three-day shelf life, cream's one-litre pack and £2.80

Every clause of the done condition checked by running it, not by reading:

    five locations with a name and a temperature; three bases; two people;
    16 flavours each stating rotation, the 6 stickered false and the other 10
    true; 16 prices with peach and gingerbread at 5.50 and the rest at 4.20;
    `flavour_base` on pistachio and nothing else; shelf life on fresh milk and
    nothing else; pack size and price on double cream and nothing else; no
    fact whose predicate is declared by Supplier, Pan, MixBatch, Sale or
    StockCount; confidence still exactly 6 `low` and 13 `high`.

Slots receiving a fact: 19 of 45, was 10. Slots receiving none: 26, was 35, and
the provenance note now lists all 26 beside the section that leaves each empty.
Class-ranged slots exercised: 3 of 16, was 2 — `flavour_base` joined
`stock_location` and `material_unit`. Subjects: 48, was 40.

`gen-owl --no-use-native-uris`, `gen-doc` and `gen-mermaid-class-diagram` all
exit 0. `gen-mermaid-class-diagram` requires `-d` like `gen-doc` and writes one
file per class: 18 diagrams, 84 doc pages. The TTL's facts literal grew from
12,176 characters to 16,673 on one line, now a third of the file.

`seal`'s validators run as functions accept all 176 facts; 39 would land in
`value_ref` (19 `material_unit`, 19 `stock_location`, 1 `flavour_base`).
Nothing was sealed.

Surprising: `seal` stringifies with `str()`, so the first boolean in the PoC
reads `True` rather than `true` and `4.20` reads `4.2`. The draft states a
boolean where the map says `range: boolean`, so the draft is not the place to
fix it — appended to OPEN.md as a T1 line blocking `generator`.

Also surprising: the profile states the base of exactly one flavour. Dark
chocolate, stracciatella and the three sorbets announce their base in their own
names, and writing those down would have been the one invention nothing
downstream could detect — fifteen inferred facts indistinguishable from the one
stated fact. It is recorded as choice 10 in the note for that reason.

## 2026-08-31 · §10's rules, and keys for the things the business identifies

Ran: `business/draft.yaml`, 18 facts added, 176 -> 194. `make check` — **47
passed**, replay identical twice at 5334 bytes, exit 0, run again after the note
was written and the same. `business/` still holds no `v*.yaml` and the working
`uniti` database still reads 0/0/0: nothing here touched the kernel, and nothing
was sealed.

What changed in the map:

    +1 class    Policy, no key, no required slot — the shop identifies a rule
                by nothing
    +4 slots    policy_rule (string), policy_threshold (decimal, no unit fixed
                on the slot), policy_unit (range Unit, a value_ref) and
                base_ingredients (range Material, multivalued)
    +3 keys     MixBatch (mix_pasteurised_on + mix_base), StockCount
                (count_taken_on + count_location), Sale (sale_date +
                sale_flavour), as `unique_keys`, and those six slots required
    +18 facts   six rules, six thresholds, three rules pointing at a unit, and
                day, week and percent as three more Unit individuals

18 classes -> 19, 45 slots -> 49, 48 subjects -> 57, slots carrying a fact
19 -> 22, empty 26 -> 27, class-ranged slots 16 -> 18 with 4 of them exercised.

Every clause of the done condition checked by running it. The six sentences were
compared byte for byte against profile.md §10's own bullet list rather than
against what the draft says they are: `stated == recorded` for all six. All six
carry a threshold — 0, 5, 3, 3, 8, 5 — and three carry a unit: day, week,
percent. The five-litre rule carries 5 and nothing points at `uniti:litre` from
any rule; "never fewer than eight flavours" carries 8 and no unit either, on the
narrower ground that the map counts things without a unit elsewhere. Pan and the
five movement classes hold no key, no identifier and no required slot, and so
does Policy. `base_ingredients` is on Base, ranges Material, is multivalued and
receives no fact.

`SchemaView` loads clean. `gen-owl --no-use-native-uris`, `gen-doc` and
`gen-mermaid-class-diagram` all exit 0 with `PYTHONIOENCODING=utf-8` set: 58,525
bytes of TTL, 89 doc pages, 19 diagrams.

Surprising: `unique_keys` reaches the OWL as `owl:hasKey`, and `required: true`
as an `owl:minCardinality 1` beside the `maxCardinality 1` a single-valued slot
already had. Three keys and six minimums are the first thing in this map a
reasoner could act on, and nothing in the PoC reads OWL. Not the same question
as the 27 Aug T1, which found `gen-shacl` suppressing `minCount` on an
`identifier` slot: none of these six is an identifier, and this is `gen-owl`.

Also surprising: the earlier note's Mermaid count did not reproduce. It said
twenty of thirty-two edges were "the same six seen five times"; the actual
arrows are the four class-ranged slots of StockMovement, drawn once on the
parent and once on each of five children, and the current render has 40 arrows
of which 24 are those. The 20 in the old sentence was right and the "six" was
not. Restated in the note against a render that was run.

Found and not fixed: each of the six rules is now in the map twice — as a
`Policy` fact and as the `stated_rule` annotation that has sat on the slot since
the first draft. The annotation carries the number, so it goes stale the first
time Marta moves a threshold, and a sealed version cannot be corrected without a
v2. Removing it was not in this item and it is a line in OPEN.md instead.

## 2026-08-31 · Seal v1, and look at what landed

Ran: `components/seal/seal.py business/draft.yaml --actor fareza --sealed-at
2025-08-31T21:00:00Z` against the working `uniti` database, which read 0/0/0
beforehand, with `business/` holding no `v*.yaml`. Then `make check` twice —
**47 passed**, replay identical at 5334 bytes, exit 0 both times — and a
read-back through `resolve_single` and `resolve_version`.

The three table counts after the seal, and unchanged after both `make check`
runs:

    intent          1
    entity        107   = 1 uniti:uri + 49 declared slot_uris + 57 subjects
    assertion     301   = 107 URI registrations + 194 stated facts

Every clause checked against the tables rather than against what `seal` is
supposed to do:

    sealed-at stamps both    v1.yaml carries sealed_at 2025-08-31T21:00:00+00:00;
                             all 301 assertions carry one recorded_at equal to
                             it; intent.occurred_at is the same instant
    no facts block           v1.yaml's annotations hold valid_from, sealed_at,
                             supersedes: null and transcript: v1.txt, nothing
                             else. 42,342 bytes of draft sealed to 17,200
    transcript beside it     v1.txt sits in business/ and is byte-identical to
                             draft.txt
    194 over 57              NOT as written — see below
    one entity per predicate 23 predicate URIs in use (22 slots + uniti:uri),
                             each resolving to exactly one entity id; no URI
                             registered twice; no predicate row unregistered
    four slots in value_ref  flavour_base 1, material_unit 19, policy_unit 3,
                             stock_location 19 = 42 refs and zero literals on
                             those four; no other predicate carries a ref at
                             all; all 42 targets are registered entities
    six read low             six low, thirteen high, 282 NULL. The six are
                             sugar, lemons, cones, cups 3 oz, cups 5 oz and
                             spoons — exactly profile §13's "estimated" rows,
                             compared row by row against the table there
    facts carry 2025-09-01   one valid_from across all 301 rows
    make check twice         301 before, 301 after each run

The read rule was exercised on real data rather than on the fixture: fresh milk
reads `('38', 'high')` at valid_at 1 Sep as_of today and as_of the seal instant,
`None` one second before the seal, and `material_unit` returns a `value_ref`
that hops to `litre`. `resolve_version` returns v1 for any valid_at from 1 Sep
seen after 21:00 on 31 Aug, and nothing before either bound. `gen-owl` and
`gen-erdiagram` both exit 0 on the sealed file — 39,768 and 3,223 bytes — so
what the generator will read next is a file the generators can still read.

Surprising, and the reason the fourth clause is marked: **194 over 57 counts
facts, and the log is a table.** It holds 301 assertions over 107 entities. The
194 and the 57 are both exactly right as a subset — 194 rows carry
`source = 'human_stated'` over 57 distinct subjects — but 107 rows register a
URI and 50 entities are not subjects of anything. Nothing malfunctioned:
registering every URI under `uniti:uri` has been in `seal` since it was written
and is documented in its own docstring. The clause was written about the draft's
facts and read back against the tables, and those are two different counts.

Also surprising: **28 of the 107 entities are never the subject or the predicate
of a stated fact** — the 27 declared `slot_uri`s that carry no fact, plus
`uniti:uri` itself. `seal` mints one predicate entity per declared slot whether
or not anything says it, so the map's whole vocabulary enters the log at seal
time, not the exercised part of it. "Every predicate in the log has a home in
the map" is therefore true by construction and measures nothing; the question
with content is the other direction, and 27 of 49 slots have never been used.

Also surprising: **the evening of the count is the one evening the system cannot
answer for.** `recorded_at` 21:00 on 31 August precedes `valid_from` midnight on
1 September, deliberately, and nothing in the kernel objected — no constraint
compares the two columns. The consequence only shows on a read: at valid_at
22:00 on 31 August, `resolve_single` returns None for fresh milk and
`resolve_version` returns no version at all. For three hours the shop has just
counted its stock, `seal` has written all 301 rows, and the log answers nothing
about either the stock or the map that describes it.

Two smaller facts. Unicode survived the round trip into Postgres intact: −35 °C
is 6 characters in 9 bytes with U+2212 rather than a hyphen, and 2–4 °C keeps
its en dash. And no `(subject, predicate)` pair occurs twice in the whole log,
so nothing in v1 competes — which is also why Q6 cannot fail yet: it needs the
second count.

## 2026-08-31 · `generator`: one projection table and one form from v1 alone

Built `components/generator/generate.py` and `tests/generator/`. Ran
`make check` — **57 passed** (47 before, 10 new), replay identical at 5334
bytes, exit 0. Then ran the CLI against `business/v1.yaml` and the working
`uniti` database, which still reads 1 / 107 / 301 afterwards: nothing here
wrote to it.

What was generated, from the sealed `v1.yaml` and nothing else — not
`draft.yaml`, not `profile.md`:

    table Material   19 rows, 8 columns, 73 of 152 cells blank
                     verified: 152 cells equal a direct read of the log
    table Pan        19 rows, 7 columns, 114 of 133 cells blank
                     verified: 133 cells equal a direct read of the log
    form  Material   8 fields, 3 of them over a class range
    form  Pan        7 fields, 3 of them over a class range

Columns are the class's *induced* slots read through `SchemaView`, so `is_a`
and `default_range` apply. Every cell is one `resolve_single()` call at the
same (valid_at, as_of) — the table is a read of the kernel, never a store.
`--verify` re-derives every cell with one `DISTINCT ON` statement that never
calls `resolve_single`, so what the equality proves is the generator's pivot —
which entity is a row, which value lands in which column — rather than the read
rule against itself.

**The map does not say which entities are a class's rows, and that is the
result of this item.** A class is a set of slots; the log is (subject,
predicate, value); no assertion anywhere states that an entity is a Material.
CLAUDE.md's third closed finding says class membership is an assertion, and v1
asserts none for any of its 19 classes. So the generator guesses, on the only
rule the two files support: a row is an entity that is the subject of a fact
under one of that table's own columns and has at least one value standing at
those clocks. Nothing was reached for outside the map to patch this.

The guess is visibly wrong the first time it is asked a second question. The
Pan table above holds **nineteen materials** — cocoa powder, cones, lemons —
each with `stock_location` filled and all six pan columns blank, because
`stock_location` is declared on `StockItem` and inherited by both Material and
Pan. Two classes, one shared column, one indistinguishable row set. It is a
line in OPEN.md rather than a fix, because fixing it means inventing a class
assertion the business never made. The fixture test suite records the same
shape deliberately: a crate that nobody called a tub is a row of the tub table.

Surprising: **the generated form is the first thing that made an OPEN line
visible rather than argued.** `material_unit` offers six options read from the
log — day, kg, litre, percent, piece, week — so the dropdown for how much milk
is measured in offers "week". That is the 31 Aug line about `Unit` widened to
six by §10's thresholds, and it took a rendered form to make it a thing you can
see rather than a thing you can reason about.

Two more absences the form showed without being asked. `material_supplier`
offers nothing at all: §5 names four suppliers, the draft states none, so the
column is empty in the table and the dropdown is empty in the form — one of the
27 slots carrying no fact, working exactly as it should. And `pan_mix` offers
nothing for the same reason, while `pan_flavour` offers all sixteen flavours,
so one form shows both halves of that defect side by side.

Not done, and why. **No value was entered into the working log.** The form's
write path is exercised in `tests/generator` against the check database — a
literal and an edge on an existing subject, a new subject minted, both read
back through `resolve_single`, and the same table shown before and after the
`as_of` the entry was recorded at. Writing into `uniti` would append rows that
`git revert` cannot take back, to the log whose 301 rows are the evidence the
last item measured, and entering data is the next stage rather than this one.
One command does it if that is wanted.

Three decisions taken inside the item, none of which needed a new column or a
new rule. A row with nothing standing at those clocks is not a row, so an
entity the log has gone quiet about disappears rather than showing as a line of
blanks. A `value_ref` renders as the target's URI, not as a label, because
resolving a label needs the range class's identifier slot and the URIs are
legible as they stand. And `submit()` does not read the six `stated_rule`
annotations: the same rules are in the log as `Policy` facts, and the 31 Aug
OPEN line says the annotation goes stale the first time Marta moves a
threshold — a generated form that repeated it would put the stale copy in front
of the user.

## 2026-08-31 · Desktop's session: what the first full loop showed

The loop closed today for the first time: a frozen profile, a hand-authored
draft, a seal, a log, and a table generated back out of the sealed map. Four
components run — kernel, ontology, seal, generator — and `interview` is still a
SKILL.md with no code. Written here as material for the re-evaluation Fareza
opened at the end of the day, so a later session has the state without reading
the whole LOG.

Measured, not recalled. Every number below was re-checked this session against
Postgres or by re-running the tool, not taken from the entry above it.

    log            1 intent, 107 entities, 301 assertions
                   one recorded_at 2025-08-31T21:00Z, one valid_from 2025-09-01
                   194 stated facts over 57 subjects, 42 refs, 6 low, 13 high
    v1             19 classes, 49 slots; draft 42,342 bytes sealed to 17,200
                   22 of 49 slots have ever carried a fact, 27 never have
    tests          57 passed, replay identical twice at 5334 bytes
    generated      Material 19 rows / 8 cols / 73 blank cells
                   Pan      19 rows / 7 cols / 114 blank cells

Four sessions of Claude Code work in two days, each verified here clause by
clause rather than accepted from LOG. Every clause passed except two, and both
of those were clauses written here, not work done there: "194 over 57" counted
the draft's facts and was read back against a table that also registers a URI
per entity, and "reaches the log" never said which log, so the form's write path
went to the check database instead — the better reading, and the safer one,
since the working log's 301 rows are the evidence the seal item measured.

### What the loop exposed, in weight order

**The log cannot say what a thing is.** No assertion states a type, so a
generator asking which entities are a class's rows has to guess. Its rule is
the only one the map and the log support: a row is a subject of one of that
table's own columns. `stock_location` is declared on `StockItem` and inherited
by both Material and Pan, so the Pan table holds nineteen materials with every
pan column blank. CLAUDE.md's third closed finding already says class
membership is an assertion; v1 states none, and no done condition written here
across four sessions ever asked for one. That is this desk's miss, not Claude
Code's.

**The map describes and does not bind.** `required: true` reaches a generated
form as a label and stops nothing. §10's six rules are in the log and inert.
No constraint anywhere compares a fact against the map, which is deliberate —
the log is not meant to judge at write time — but it means the first of Marta's
rules, that stock never goes below zero, currently prevents nothing.

**There is one writer, and it writes map versions.** `seal` is it. Adding 57
type assertions therefore means bumping a map version for a purely data
reason. For v2 that happens to be honest, since six annotations need removing
anyway, but the pattern does not survive contact with episodes.

Everything else found this week is downstream of one of those three, or is a
correction to something written here: §10's rules sealed in two homes at once,
coverage measuring nothing because `seal` registers every declared slot whether
used or not, the three-hour hole between a 21:00 seal and a midnight
`valid_from`, `Unit` widened to six so a material's unit dropdown offers
"week", and a `stated_rule` annotation nobody had noticed since the first
draft.

### What was not done, and why

No v2. Last session this desk argued for running the generator first so v2
would carry more than one fix; the generator answered, and v2 now has three
clear payloads — type assertions, the six annotations removed, and a decision
on `Unit`. It was not started because Fareza opened the re-evaluation, and
building v2 during it would be building past the question.

NEXT is empty on purpose. DECISIONS carries a line bounding the re-evaluation
to three joints and explicitly excluding the kernel, on the grounds that
nothing has complained about it: three tables, append-only, a replay identical
twice, 301 rows unchanged across a seal and two check runs, and Unicode intact
through Postgres. That bound is one sentence to widen and exists only so this
cycle does not end the way the previous four did.

### Two things worth keeping in view

The generator was the first thing all week to make an OPEN line visible rather
than arguable. The `Unit` widening had been reasoned about the day before; it
took a rendered dropdown offering "week" for how milk is measured to make it a
thing anyone could see. Whatever the re-evaluation concludes, generating early
and looking at the output earned its place.

And commit f25c4eb swept up uncommitted DECISIONS.md and NEXT.md edits made at
this desk, so git history shows Claude Code touching files it does not own.
Commit before handing over a session.

## 2026-09-01 · The eight document forms, rendered and looked at

`[T1]`. Ran, once per class, against `business/v1.yaml` and the working `uniti`
database:

    .venv/Scripts/python.exe -m components.generator.generate form \
        business/v1.yaml <CLASS> --out build/<class>_form.txt

All eight exited 0. Eight files in `build/`: `stockcount_form.txt`,
`goodsreceived_form.txt`, `panmoved_form.txt`, `panpulled_form.txt`,
`thrownout_form.txt`, `tastinggiven_form.txt`, `mixbatch_form.txt`,
`sale_form.txt`. **No class failed to render**, which was the outcome this item
was prepared to record as its finding. `make check` after: 57 passed, replay
identical at 5334 bytes, exit 0. The working log reads **1 / 107 / 301** before
and after — nothing here wrote to it, and `form` has no write path.

| class | fields | pickers over a class range | of those, offering zero |
|---|---|---|---|
| StockCount | 4 | 2 | 0 |
| GoodsReceived | 7 | 5 | 1 |
| PanMoved | 6 | 4 | 0 |
| PanPulled | 6 | 4 | 0 |
| ThrownOut | 6 | 4 | 0 |
| TastingGiven | 6 | 4 | 0 |
| MixBatch | 4 | 2 | 0 |
| Sale | 3 | 1 | 0 |

Option counts, the same across every form that offers them: `movement_of` and
`count_of` 19, `movement_out_of` / `movement_into` / `count_location` 5,
`movement_recorded_by` / `mix_made_by` 2, `mix_base` 3, `sale_flavour` 16,
`received_from` 0.

**The four pan and waste forms are byte-identical apart from their own name.**
`panmoved_form.txt` is 1511 bytes, `panpulled_form.txt` and `thrownout_form.txt`
1512, `tastinggiven_form.txt` 1515 — exactly the difference in the length of the
class name in the header line. All four are `StockMovement` with nothing added,
so the six fields, the four pickers and the option lists are the same character
for character. Filling one and filling another produces the same facts; the only
place the class survives is `intent.action_name`, which `submit()` writes as
`submit_<Class>`. GoodsReceived is the one subclass that adds a slot
(`received_from`), and it is the one whose picker is empty.

**A pan movement cannot name a pan.** `movement_of` ranges over `StockItem`,
whose subclasses are Material and Pan, and the picker offers nineteen materials
— cocoa powder, cones, lemons — because no pan entity exists in the log for the
options rule to find. `count_of` on StockCount is the same nineteen, so the
stock count cannot count a pan either. This is the 31 Aug row-rule line seen
from the other side: there it put materials into the Pan *table*, here it keeps
pans out of the pan *form*.

Surprising, and not what was expected going in: the forms that read worst are
the ones with the fewest empty pickers. StockCount and Sale are clean and
usable. GoodsReceived, the only form with a zero-option picker, is also the only
one where the empty picker is the point — a delivery comes from outside the
shop, `received_from` offers nothing, and `movement_out_of` offers only the five
internal locations, so the outside of the business is unrepresentable twice over
in one form. Nothing about that shows up in the field count.

Also visible without being asked: `required` renders as a column and enforces
nothing. `count_location` and `count_taken_on` are marked required in the
StockCount form; reading `submit()`, it rejects an unknown field name and an
empty submission and checks nothing else, so a StockCount naming only
`count_quantity` would be written. Left as a line, not a fix.

Four lines appended to OPEN.md. Nothing was repaired, no map was touched, and
no second case was generalised.

## 2026-09-01 · Which LinkML features survive the seal, and which can compute

An investigation. Nothing was made to work, and no feature that failed was
repaired. LinkML 1.11.1 and linkml-runtime 1.11.1 throughout — everything below
was run, not read from documentation.

A throwaway map, `business/trial/draft.yaml`: two classes, six slots, ten
stated facts, no business vocabulary anywhere. It carries the five features
under trial and nothing else. Sealed against the **throwaway** database, into
its own directory:

    UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check \
        .venv/Scripts/python.exe components/seal/seal.py business/trial/draft.yaml \
        --actor trial --into business/trial --sealed-at 2026-02-01T09:00:00Z

**`seal` accepted it.** No refusal to record. 9 entities minted, 19 assertions,
`business/trial/v1.yaml` and `v1.txt` written. All five features are still in
the sealed file, character for character, because `seal` copies the schema
through `yaml.safe_load` -> `yaml.safe_dump` and strips only
`annotations.facts` — none of the five is a fact, so none of them was ever a
candidate for stripping. That is the whole reason they survive, and it means
the answer would be the same for any metamodel key that is not called `facts`.

Read back from the sealed file through `SchemaView`, seven tests, no database:

    .venv/Scripts/python.exe -m pytest tests/trial -q          # 7 passed

Each of the five is asserted both on the raw slot and on the **induced** slot,
because `class_induced_slots` is the door the generator uses and a feature that
survived the file but not induction would be invisible to every reader we have.
All five survive induction too.

### The table

Usable means it survives the seal **and** something can act on it today.
Unusable means it survives and nothing can. Untried means exactly that.

| feature | seal | reads back | computes | verdict | what it would serve |
|---|---|---|---|---|---|
| `equals_expression` (slot) | kept | yes, incl. induced | yes, via `generate_slot_value` | **usable, with a trap** | derivation within one row — the half of the 1 Sep split that is LinkML's |
| `rules` + `preconditions` / `postconditions` (class) | kept | yes, whole block | **no** | **unusable** | §10's stated rules, as something checked rather than recited |
| `unit` with `ucum_code` (slot) | kept | yes, incl. induced | n/a — metadata | **usable as declaration only** | a fixed unit on a slot, so a quantity is not a bare number |
| `unique_keys` (class) | kept | yes | n/a — nothing enforces | **usable as declaration only** | identity for the three things §4 says the business identifies |
| `designates_type` (slot) | kept | yes, incl. induced | n/a — nothing reads it | **usable as declaration only** | the open class-membership question: a row saying which class it is |
| `multivalued` as an expression input | kept | yes | partly — `len`/`max` yes, `sum` no | **unusable for a total** | the collection a cross-row number would be computed over |
| `minimum_value` / `required` inside a rule condition | kept | yes | no — the rule never runs | **unusable** | the constraint half of a stated rule |
| `eval_expr` functions `max` `min` `len` `str` `strlen` `case` | n/a | n/a | yes | **usable** | the only aggregation LinkML brings; `case` is a conditional value |
| `eval_expr` `sum` | n/a | n/a | **no** | **unusable** | the one aggregate an inventory actually needs |
| `infer_all_slot_values` | n/a | n/a | **no-op, silently** | **unusable here** | the documented entry point; see below |
| `string_serialization` (slot) | untried | untried | untried | **untried** | a computed *string* — the sibling of `equals_expression`, and the path `Config` enables by default |
| `classification_rules` (class) | untried | untried | untried | **untried** | inferring which class a row belongs to, which is the 31 Aug row-rule question |
| `any_of` / `all_of` / `none_of` | untried here | — | — | **untried** | a slot ranging over two classes; already known broken for `seal` (OPEN, 30 Aug) |
| `pattern` / `structured_pattern` | untried | — | — | **untried** | the shape of an identifier, e.g. a pan number |
| `enum` / `permissible_values` | untried | — | — | **untried** | a closed vocabulary as map structure instead of as entities |
| `slot_usage` | untried | — | — | **untried** | narrowing an inherited slot per subclass — the five movement classes |
| `abstract` / `mixin` | untried | — | — | **untried** | saying `StockItem` is never itself a row |

### Evaluating one over a row this system assembles

    UNITI_DSN=.../uniti_check .venv/Scripts/python.exe scripts/trial_equals_expression.py

The row is not an object. It is `components/generator`'s `table()` output at a
stated `(valid_at, as_of)` — every cell one `resolve_single()` call. For
`trial:reading_one` at valid_at and as_of 2026-03-01:

    row as assembled     {'left_amount': '3', 'right_amount': '4', 'total_amount': None,
                          'held_amount': '5.5', 'thing_id': 'reading_one',
                          'thing_kind': 'Reading'}
    computed from it     '34'   (str)
    row cast to the map  {'left_amount': 3, 'right_amount': 4, ...}
    computed from that   7      (int)

**This is the finding of the item.** The expression evaluates, at the right
clocks, over a bitemporal read — the mechanism is there. But
`assertion.value_literal` is text, nothing between the kernel and the evaluator
consults the map's `range`, and `eval_expr` dispatches `+` on Python types. So
`{left_amount} + {right_amount}` over a real row returns `'34'` and raises
nothing. The second row gives `'102'` for 10 + 2. A total that is silently a
concatenation is worse than one that fails, and no test anywhere would have
caught it: `'34'` is a perfectly good `str`.

Casting each cell to the range the map already declares gives 7 and 12. The map
has the information; nobody applies it. Who applies it is the OPEN line.

Two mechanics worth not re-deriving:

- `generate_slot_value` requires a `jsonasobj2.JsonObj`, and `Config` must be
  built with `use_expressions=True` — the default is False (as is `use_rules`).
- `infer_all_slot_values`, the documented walker, **does nothing at all** on a
  row that is not a `YAMLRoot`. `traverse_object_tree` calls its `infer` on
  every node, `infer` tests `isinstance(in_obj, YAMLRoot)` and falls through,
  and the call returns cleanly having changed nothing. A generator row is a
  dict; a `YAMLRoot` only comes from `gen-python`. So the obvious entry point
  is a silent no-op and `generate_slot_value` is the one to call.

### Trying to sum across rows, in LinkML alone

    UNITI_DSN=.../uniti_check .venv/Scripts/python.exe scripts/trial_sum_across_rows.py

Seven attempts over the two rows' `held_amount`, `[5.5, 1.25]`, whose sum is
6.75. Errors verbatim, nothing worked around:

| attempt | result |
|---|---|
| `sum([1, 2, 3])` | `NotImplementedError: Call <ast.Name object at 0x...> not implemented. node = <ast.Call object at 0x...>` |
| `sum({amounts})` over the rows' own values | the same `NotImplementedError` |
| `{a} + {b}`, arity fixed when the map was written | `Decimal('6.75')` |
| `max({amounts})` | `Decimal('5.5')` |
| a schema slot `batch_total: sum({parts})` over a multivalued slot | the same `NotImplementedError` |
| the same shape, `batch_count: len({parts})` | `2` |
| the sealed map's `rules` block, `use_rules=True` | `NotImplementedError: Rules not implemented for Config(use_string_serialization=False, parse_string_serialization=False, use_rules=True, use_expressions=False, resolve_function=None)` |

`eval_utils.funcs` holds exactly six names — `max`, `min`, `len`, `str`,
`strlen`, `case` — and `sum` is not one of them. The shape is legal LinkML and
the schema loads; it fails at evaluation. So the 1 Sep split is confirmed from
below, and more narrowly than it was stated: LinkML can count a collection and
take its maximum, and cannot add it up.

`rules` is the sharper half. The block survives the seal perfectly, reads back
with its precondition and postcondition intact, and `linkml_runtime` raises
`NotImplementedError` the first time it is asked to apply one — not for our
rule, for any rule. A map may therefore carry §10's six rules as structure that
no reader in this stack can execute.

### After

    make check          # 64 passed, replay identical twice at 5334 bytes, exit 0

Working log named by the default DSN: **1 / 107 / 301** before the session and
1 / 107 / 301 after, checked directly against Postgres both times. Every write
here went to `uniti_check`, and `make schema` wiped that database during the
final `make check` — so the trial seal's 19 assertions are gone and only the
sealed file remains, which is why `tests/trial` was written to need no database.

One clause of the done condition cannot hold: it asks for a test under `tests/`
**and** for `make check` to still exit 0 "at 57 passed". Adding tests changes
the count. 57 was the number before; it is 64 now, all 57 originals still
passing, and nothing existing was touched. Reported, not worked around by
hiding the tests somewhere `pytest tests` does not look.

Surprising, in order:

1. **All five survived, and that is not evidence of anything.** `seal` strips
   one key and copies the rest, so "does it survive the seal" has the same
   answer for every metamodel feature there will ever be. The interesting
   question was never survival; it is what can act on what survived, and there
   the five split three ways.
2. **The trap is silent.** `'3' + '4' = '34'`, no exception, right type, wrong
   number. The one place a computed value could have been trusted turns out to
   be the one place a wrong value looks most like a right one.
3. **`infer_all_slot_values` is a no-op, not an error.** The documented
   function ran cleanly on our row and changed nothing.
4. `len()` and `max()` work across a collection and `sum()` does not. The
   boundary is not "LinkML cannot aggregate" — it is a six-name dictionary that
   happens to omit the one aggregate an inventory is made of.

## 2026-09-02 · Prove or break the `derive` idea with a throwaway

The claim held. A computation declared in a sealed map, executed against the
log at a stated pair of clocks, produced the right number — and produced a
different right number when the same question was asked at a later `as_of`,
because one movement had been recorded five weeks late. Nothing under
`components/` was created or changed. `scripts/trial_derive.py` is **292 lines**
(38 of them the opening docstring, 49 blank) and is expected to be deleted.

One thing broke on the way, and it broke first.

### The declaration is not spelled the way anyone would spell it

The obvious shape — a mapping directly under an annotation tag — is refused by
LinkML before any of this starts:

    in_total:
      annotations:
        aggregate:
          over: Movement
          sum: movement_quantity

    TypeError: Annotation.__init__() got an unexpected keyword argument 'over'

`Annotation` is a metamodel class with `tag`, `value`, `annotations` and
`extensions`, so a mapping under the tag is read as that class's own keyword
arguments. Four spellings were tried and three are accepted:

| spelling | SchemaView | reads back as |
|---|---|---|
| `aggregate: {over: ...}` | **TypeError**, above | — |
| `aggregate: {value: {over: ...}}` | accepted | one `JsonObj`, structure intact |
| `aggregate: {annotations: {over: {...}}}` | accepted | nested `Annotation` per key |
| `aggregate_over: ...`, `aggregate_sum: ...` | accepted | four flat tags, structure gone |

The second was used. It is one word away from the shape the item named and
keeps `over`, `sum` and the named `by` dimensions where a reader expects them.
Read back with `jsonasobj2.as_dict(slot.annotations["aggregate"].value)`, which
returns a plain nested dict; `.items()` on an annotation block raises
`AttributeError: 'JsonObj' object has no attribute 'items'`, and so does
`.get()`.

### The declaration, verbatim from `business/trial2/v1.yaml`

    in_total:
      slot_uri: trial2:in_total
      range: decimal
      description: Everything that arrived, for this pair. Computed, never stated.
      annotations:
        aggregate:
          value:
            over: Movement
            sum: movement_quantity
            by:
              holding_thing: movement_thing
              holding_place: movement_into
    out_total:
      slot_uri: trial2:out_total
      range: decimal
      description: Everything that left, for this pair. Computed, never stated.
      annotations:
        aggregate:
          value:
            over: Movement
            sum: movement_quantity
            by:
              holding_thing: movement_thing
              holding_place: movement_out_of
    net_total:
      slot_uri: trial2:net_total
      range: decimal
      equals_expression: '{in_total} - {out_total}'

`Holding` is a class nobody ever states a value for. Its two dimensions come
from the `by` keys, its two totals from the `by` values, and its third column
from LinkML's own within-a-row derivation standing on two sums LinkML cannot
compute. The script holds two literals about this map — the class name
`Holding` and the annotation key `aggregate`. `Movement`, `movement_quantity`,
`movement_into` and `movement_out_of` appear nowhere in it; all four are read
out of the sealed file at run time and are printed in the header of every run.

### The commands

Two seals of the same schema into the same directory, five weeks apart, both
against the **throwaway** database:

    UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check \
        .venv/Scripts/python.exe components/seal/seal.py business/trial2/draft.yaml \
        --actor trial2 --into business/trial2 --sealed-at 2026-03-05T09:00:00Z

    UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check \
        .venv/Scripts/python.exe components/seal/seal.py business/trial2/late.yaml \
        --actor trial2 --into business/trial2 --sealed-at 2026-04-10T09:00:00Z

    UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check \
        .venv/Scripts/python.exe scripts/trial_derive.py

`seal` accepted both. v1: 19 entities minted, 39 assertions, one `recorded_at`
of 2026-03-05T09:00Z. v2: **1** entity minted, 5 assertions, one `recorded_at`
of 2026-04-10T09:00Z — the ten `slot_uri` predicates and `uniti:uri` were
reused, so only `trial2:move_late` was new. Both versions state
`valid_from: 2026-03-01`, so both seals describe the same day.

The map states 8 hand-written class-membership assertions under a slot carrying
`designates_type: true`, and four movements across two places, one of which
(`trial2:move_four`) states no quantity at all.

### The two tables

Same `valid_at`. Same map, byte-identical apart from its annotations. Two
`as_of` values, five weeks apart.

    the map itself resolves to v1 at as_of 2026-03-06T00:00:00Z

    Holding  (v1, v1.yaml)
    valid_at   2026-03-01T00:00:00Z
    as_of      2026-03-06T00:00:00Z

    holding_thing       holding_place     in_total  out_total  net_total
    ------------------  ----------------  --------  ---------  ---------
    trial2:thing_alpha  trial2:place_one  10        4          6
    trial2:thing_alpha  trial2:place_two  4         0          4
    trial2:thing_beta   trial2:place_two  7         0          7

    Movement: the generator offered 8 rows, the log states 4 of them are one
      (trial2:thing_alpha, trial2:place_one).in_total = 10 from 1 movement(s)
      (trial2:thing_alpha, trial2:place_one).out_total = 4 from 1 movement(s), and 1 that matched but stated no quantity and added nothing: trial2:move_four
      (trial2:thing_alpha, trial2:place_two).in_total = 4 from 1 movement(s)
      (trial2:thing_alpha, trial2:place_two).out_total = 0 from 0 movement(s)
      (trial2:thing_beta, trial2:place_two).in_total = 7 from 1 movement(s)
      (trial2:thing_beta, trial2:place_two).out_total = 0 from 0 movement(s)

    the map itself resolves to v2 at as_of 2026-04-11T00:00:00Z

    Holding  (v2, v2.yaml)
    valid_at   2026-03-01T00:00:00Z
    as_of      2026-04-11T00:00:00Z

    holding_thing       holding_place     in_total  out_total  net_total
    ------------------  ----------------  --------  ---------  ---------
    trial2:thing_alpha  trial2:place_one  10        7          3
    trial2:thing_alpha  trial2:place_two  4         0          4
    trial2:thing_beta   trial2:place_two  7         0          7

    Movement: the generator offered 9 rows, the log states 5 of them are one
      (trial2:thing_alpha, trial2:place_one).in_total = 10 from 1 movement(s)
      (trial2:thing_alpha, trial2:place_one).out_total = 7 from 2 movement(s), and 1 that matched but stated no quantity and added nothing: trial2:move_four
      (trial2:thing_alpha, trial2:place_two).in_total = 4 from 1 movement(s)
      (trial2:thing_alpha, trial2:place_two).out_total = 0 from 0 movement(s)
      (trial2:thing_beta, trial2:place_two).in_total = 7 from 1 movement(s)
      (trial2:thing_beta, trial2:place_two).out_total = 0 from 0 movement(s)

    what the two tables say to each other
      Movements visible at the later as_of and not the earlier: ['trial2:move_late']
      their quantity, resolved at the later as_of: 3
      pairs in both tables whose net_total differs: {'trial2:thing_alpha/trial2:place_one': (Decimal('6'), Decimal('3'))}
      pairs in one table and not the other: none
      asserted: exactly one movement arrived late, exactly one pair moved (trial2:thing_alpha/trial2:place_one net_total 6 -> 3), and |6 - 3| == 3, that movement's own quantity

The script asserts three things and does not leave them to the eye: exactly one
movement is visible at the later `as_of` and not the earlier; exactly one pair's
`net_total` moved; and the size of that move equals the late movement's own
quantity, **resolved from the log at the later `as_of`** rather than typed into
the script. It exits 0.

### The movement with no quantity

`trial2:move_four` — thing_alpha out of place_one, no `movement_quantity` fact
anywhere. It matches the `out_total` group for its pair, so it is not invisible;
it contributes nothing, so the total behaves as though it were zero. The script
prints that in the breakdown under every table (`1 that matched but stated no
quantity and added nothing`) and decides nothing. The table itself shows `4`,
then `7`, with no mark of any kind. What it should mean is already an OPEN line
from 1 Sep and is a question for profile v2, not for this desk.

### After

    make check          # 64 passed, replay identical twice at 5334 bytes, exit 0

Working log named by the default DSN: **1 / 107 / 301** before this session,
1 / 107 / 301 after, read straight from Postgres both times. Every write went to
`uniti_check`. `make schema` inside the final `make check` dropped and recreated
that database, so trial2's 44 assertions are gone and only the four sealed files
remain — re-running the script needs both seals run again first. The script
refuses to start unless `UNITI_DSN` is set, and refuses a DSN ending in
`/uniti`.

Four lines appended to OPEN.md. Nothing was repaired and no map was changed.

A wording proposed for DECISIONS.md, because someone will ask why it is spelled
this way: *a computation declared in a map is one annotation whose tag names the
computation and whose `value:` carries a mapping. LinkML refuses a mapping
placed directly under the tag — `Annotation` reads it as its own constructor
arguments — and the two other accepted spellings either lose the structure
(flat tags) or bury it two levels deep (nested `annotations`).*

Surprising, in order:

1. **The break was in the spelling, not the mechanism.** Everything expected to
   be hard — reading a declaration out of a sealed file, summing across a
   bitemporal read, getting two different right answers — worked first time.
   The one refusal came from writing `over:` where LinkML wanted
   `value: {over: ...}`.
2. **The generator offered 8 rows and the log says 4 are Movements.** The
   31 Aug row-rule defect showed up unprompted in a map with no inheritance at
   all: `entity_class` is a column of Movement, Thing and Place alike, so every
   entity in the trial is a candidate row of the Movement table. Reading the
   `designates_type` slot as the membership assertion filtered it in three lines
   — the first time that open question has had an answer tried rather than
   argued.
3. **A late fact needed a new map version.** `seal` writes one `recorded_at` per
   intent, so the only way to state a fact later than the rest through the map
   is a second seal — and v2's schema is byte-identical to v1's. The version
   number counted a seal, not a change of definition, and nothing in the sealed
   store says which it was.
4. `net_total` came back as `Decimal('6')`, not `'104'`. The 1 Sep concatenation
   trap is entirely a question of who casts: cast both operands to the range the
   map declares and LinkML's `equals_expression` is arithmetic; skip the cast and
   `-` would have raised `TypeError` on two strings rather than returning a
   plausible number, which is the one mercy of subtraction over addition.

## 2026-09-02 · Sorella's profile, session 1: the frame and the master data

`business/sorella/profile.md`, rewritten from the version at `44a32e6`.
496 lines in, 944 out. Session 1 written; sessions 2, 3 and 4 exist as headings
holding the previous version's material carried across word for word.

### What was written

Nine sections, `## 1.1` to `## 1.9`. Renumbered from `## 1`–`## 9` because the
carried blocks keep their own `## 4`, `## 6`, `## 8`, `## 9` and two sets of the
same numbers in one file is unreadable.

- **1.1 The business.** Premises, and sixteen named people with what each is
  responsible for. The previous version named three of the sixteen and gave the
  other thirteen as a headcount with a role breakdown.
- **1.2 The adoption date.** Monday 15 June 2026, as the brief specified.
  Nothing in the business argued against it.
- **1.3 Where stock can sit.** 27 places. Seven in the kitchen, five at Cotham,
  three at Gloucester Road, three that move (the van, Marina's cool box, the
  festival trailer), the Avonmouth container, nine supplier origins, and ten
  destinations outside the business — the walk-in customer, the wholesale
  account, staff, comps, donations, tastings, Marina's house, and three bins.
  Three bins and not one, because there are three waste sheets.
- **1.4 The range.** 14 core, 8 seasonal with their months, and 3 in the recipe
  book with no season. The third group exists because the carried count sheet
  has a struck-through line for coconut, "on the cabinet plan but none found",
  and the previous version's range had no coconut in it.
- **1.5 The units.** 24 units, 22 items whose ordered / counted / worked units
  differ, and nine terms two people in the building use for different things.
- **1.6 Everything the business buys.** 78 items, each with the unit it is
  counted in, the pack it arrives in, a price per pack and a supplier. Five
  price movements dated.
- **1.7 Everything the business sells.** 21 products with a format and a price
  at each place sold.
- **1.8 The suppliers.** Nine, each with a lead time and a minimum order.
- **1.9 The wholesale accounts.** 31 named, with credit terms. Two on thirty
  days — The Hollow and The Regent Picture House.

### What was carried, untouched

Extracted with `sed` from `git show 44a32e6:...` so the bytes are the file's own,
not retyped: §4 and its batch sheets and yield (session 2); the year-shape
bullets, the specials-rate sentence, "constraints that bite", §6 movements, §7
documents, §8 rules, §9 what Marina measures, §10 what the staff argue about,
§11 what nobody measures (session 3); the whole of Tuesday 16 June (session 4).

Loss check: of 496 old lines, 75 non-blank lines are not present verbatim in the
new file. All 75 fall in old §1 (7–21), §2 (24–54), §3 (56–104) and §5
(183–212) — the four sections session 1 rewrites. Nothing from §4, §6–§11 or the
Tuesday is missing. Line 44 is the only line inside a carried range that is not
verbatim: its flavour list became the §1.4 tables and its first sentence is
quoted word for word under session 3.

### What was invented

- Thirteen people's names, and every person's responsibilities.
- A ninth supplier, **Bristol Cash & Carry**, because the previous version said
  the coffee side is "bought locally on the shop's own card" and named no
  supplier for it. Without one, eleven bought items had nowhere to come from.
- Every price in the file. The previous version carried exactly one — pistachio
  paste at £58/kg — and no sell price at all.
- Lead times and minimum orders for six of the nine suppliers. Three were
  already stated in "constraints that bite" and are repeated unchanged.
- 26 wholesale accounts. Five were already named in the Tuesday.
- About 40 bought items that no previous section mentioned but that the carried
  recipes and the range require — vanilla paste, peppermint extract, caramel
  variegate, six more purées, the seasonal ingredients, cleaning chemicals, cake
  boxes and boards, and the whole coffee bar.

### Numbers that check against each other

- **Gloucester Road's Tuesday reconciles.** Its 149/63/8 scoops, 11 tubs and
  14 minis come to £1,103.60 at the new prices against the £1,106 the carried
  day states. That fit is what set the scoop prices; it was not designed for.
- **Cotham's does not**, and the failure is informative — see OPEN.
- **The costing tab is wrong by the amount the file says it is.** §9 (carried)
  says the November 2023 tab puts a pistachio pan at £14.80. At the November
  2023 prices now stated in prose it works out near that; at 15 June 2026 prices
  it does not, which is exactly what "pistachio paste has gone up twice since"
  should do to it.
- **The free-delivery threshold bites.** The carried §8 raised it from £80 to
  £120 in April 2026 and sets the wholesale minimum at 4 pans. At £28.50 a pan
  the minimum order is £114, so the threshold is reached at five pans and the
  April change moved it from three. A higher pan price would have made the rule
  dead on arrival.
- **The deliberate one:** at £28.50 a pan, wholesale pistachio is close to its
  own ingredient cost while fior di latte is not, and nothing in the business
  would tell Marina that. It is why "the shops are where the margin is" and why
  Dan has twice said pistachio should not cost a café the same as fior di latte.

### What was resolved, and what was left alone

The previous version said Cotham "does coffee" in §1 and "the coffee side of
both shops" in §2, with Coldharbour delivering "direct to each shop" in §3 —
while the Tuesday records 96 coffees at Cotham and no drink of any kind at
Gloucester Road. Session 1 resolves it: Cotham has the only machine, Gloucester
Road has a drinks fridge, Coldharbour delivers to Cotham. §11 stays carried and
still says "the shops", which session 2 owns.

Two figures were dropped rather than restated, because both are sums of things
the file now lists and the done condition forbids a derived figure: the
headcount of 16, replaced by sixteen named people; and turnover of £940k,
replaced by Marina's own description of the split. The Whitehall dairy delivery
on Tuesday 16 June was left standing as instructed.

### Surprising

1. **The Gloucester Road fit.** Scoop prices were set from what Bristol charges
   in 2026 and from a plain guess that the cheaper parade sells 20p under
   Cotham. Multiplied out against a day written weeks ago by someone else, they
   land £2.40 from its stated takings. Cotham's, priced from the same guess,
   lands £400 out, and the residual is almost exactly the 18% that §11 says the
   coffee side is. One shop's numbers were written from a price list and the
   other's were not.
2. **The count sheet was the only thing that knew about coconut.** A struck-out
   line in the carried Tuesday named a flavour the range did not contain. A
   whole category — in the book, on the cabinet plan, not core, no season — came
   out of one crossed-out line.
3. **A profile with no prices had also lost its recipes' ingredients.** The
   carried batch sheets call for sea salt, lemon juice and water; the range
   calls for vanilla, mint, caramel, coffee, ricotta, figs, rhubarb, pumpkin,
   amaretti, panettone, marsala and elderflower. None of them appeared anywhere
   in the previous version's buying sections. The gap that killed v1 was not one
   missing table, it was the same absence in five places.

## 2026-09-02 · Sorella's profile, session 2: how a product is made and sold

`business/sorella/profile.md`, session 2 rewritten in place. 944 lines in,
1,459 out; the session 2 block is 595 lines against the 85 it replaced. Sessions 3
and 4 are byte-identical to `9320fea` from the `# Session 3` heading to the end
of the file, checked by comparing the two slices rather than by reading a diff.

### What was written

Seven sections, `## 2.1` to `## 2.7`, renumbered from the carried `## 4` for the
same reason session 1 renumbered: sessions 3 and 4 still hold their own `## 4`,
`## 6`, `## 8` and `## 9`.

- **2.1 How a product gets made.** The carried six-step flow, reflowed to the
  file's width, with the two batch freezers and the water exception added.
- **2.2 What is made once and drawn from many times.** Six pages: white base
  (carried), and new ones for sorbet syrup, biscuit base, the coffee brew, the
  custard and the stewed rhubarb.
- **2.3 The batch sheets.** Twenty flavour pages covering twenty-two of the
  twenty-five flavours in `§1.4`; the fruit sorbet page carries three of them
  and the hazelnut page carries gianduja under the same name. Three flavours
  have no page and say so.
- **2.4 What a batch fills.** Per format, with the fill weight and what Dan
  expects off a 12 kg mix; the carried yield paragraph; the scoop; and the
  disagreement between what is expected and what the production sheet records.
- **2.5 Which flavours go in which format.** All seven `§1.7` products that hold
  gelato, each with who sets the limit.
- **2.6 What the packaging consumes.** Fourteen units, per unit filled or sold,
  and three paragraphs on the pan, the label, and the tub-and-lid mismatch.
- **2.7 The coffee side.** Eight drinks with what Yusuf says goes in each, and
  the statement that no page exists to check him against.

Two corrections outside the section, both named in `NEXT.md`. `§1.9`'s prose now
matches its own table: 14 days as the standard with most of the book on it,
three cafés on seven days, two pro forma, two on thirty. The table is untouched.
The status table at the head of the file moves session 2 to *Written* — the only
edit outside `§1.9` and the section, and it is bookkeeping, not content.

### The place count, corrected

Session 1's `LOG.md` entry says `§1.3` holds **27 places**. It holds **38**, and
that entry's own list in the same paragraph adds to 38: seven in the kitchen,
five at Cotham, three at Gloucester Road, three that move, the container, nine
supplier origins and ten destinations outside the business. Counted here from
the file's own table rows. The old entry is left as it stands.

### What was carried, untouched

Seven pages, cut with `sed` out of the working file so the bytes are the file's
own rather than retyped, and verified present verbatim afterwards: white base,
pistachio, stracciatella, dark chocolate, fruit sorbet, fresh-season strawberry,
the cake, and the yield paragraph. Of the non-blank lines in `9320fea`, 18 are
now absent verbatim: 11 inside session 2 — the "not yet written" note, the old
`## 4` heading, `### Batch sheets`, and the six numbered flow steps, all
rewritten — and 7 outside it, which are exactly the `§1.9` prose and the
status-table bookkeeping. Nothing else moved.

### What was invented

- Fifteen new flavour pages and five new intermediate pages, with quantities.
- **Two bought items in `§1.6`**, which the item's own instruction sanctions:
  ground cinnamon, for pumpkin and amaretti, and blank freezer labels, which is
  what a pan and a catering tub carry. 78 items to 80.
- The coffee brew as a thing that exists. `§1.8` says Coldharbour's beans are
  "for the shop and for the coffee gelato" and nothing said how a bean became a
  gelato. It is cold-steeped in a bucket, which is the only method that fits both
  "grams in the kitchen" and a flavour made at the batch freezer rather than in
  the pasteuriser.
- That the printed sleeve is why the 500 ml tub is core flavours only. The tub
  had to be limited to something, and a printed list with a 10–12 week lead time
  is a limit the business already owns rather than a rule invented for it.
- Every fill weight and every per-format expectation.

### Which flavours have no written recipe, and why

Three, all in the seasonal rotation, all running six to eight weeks a year:
**ricotta and fig**, **panettone and marsala**, **peach and basil**. Each states
what Dan does instead — the whole ricotta tub and about half the cream cheese,
honey until it tastes right; a panettone and a good glug; most of a 100 g pack
of basil torn in and smelled. They are by feel because a flavour made twice a
year never earns a page, and because in all three the quantity genuinely depends
on the fruit or the cheese in front of him. The three in `§1.4`'s "in the book"
group are *not* among them: being in the book is what that group means, so
coconut, amarena cherry and pink grapefruit each have a page.

### Numbers that check against each other

- **The sorbet syrup reconciles with the carried fruit sorbet page.** That page
  lists water, sucrose, dextrose and stabiliser rather than syrup. The new syrup
  page is in the same proportions, so the two agree without either being changed,
  and the file says the page was written that way in 2021 and never retyped.
- **The carried fresh-strawberry page already referenced a syrup** — "5.90 kg
  chilled syrup" — that had no page anywhere. It has one now.
- **Glucose had no home.** `§1.5`, `§1.6` and `§1.8` all buy and describe glucose
  syrup DE38 and not one carried recipe uses it. It went to the three sharp
  sorbets, which is the only place it could go without contradicting a carried
  page, and `§1.5`'s "scooped warm" is what a hot syrup does to it.
- **Vanilla paste costs more per kilo than pistachio paste.** £118.00 a 1 kg tub
  against the £58 a kilo `§1.6` records Terra Nostra quoting, while everyone in
  the building calls the pistachio the expensive one because a tin is £203.00.
  Stated in `§2.3` and not resolved, because the business does not resolve it.
- **A napoli pan costs more than the gelato in it sells for.** £38.00 for steel
  against £28.50 for a pan of gelato, both figures session 1's.
- **The deliberate one, and the largest thing this session found:** a 12 kg mix
  fills three pans and a part, and the carried Tuesday writes five and six pans
  against 12.0 kg. See OPEN.

### The one clause not satisfied literally

The done condition asks that every ingredient named in any recipe appear in
`§1.6`'s buying table. **Water does not, and cannot.** `§1.6` says in its own
preamble that water is not tracked against product; nobody buys it by the pack,
and inventing a supplier and a price for it would break the rule that every
number is one a person in the business would say. It is named as the exception
in `§2.1` under a heading of its own so it cannot be read as an oversight, and it
is in OPEN. Every other ingredient on every page resolves to a `§1.6` row,
checked by script; the only other name that does not match a row literally is
*stabiliser base*, which `§2.2` states is the same bag of Base 50 as *Base 50
stabiliser/emulsifier* — the two names the carried pages already use.

### Surprising

1. **The mess was already in the file and nobody had put two numbers together.**
   Three of the checks above are between figures session 1 wrote in one sitting.
   The pan that costs more than its contents, the vanilla that costs more per
   kilo than the pistachio, and the syrup with no page were all sitting there.
   Writing consumption did not create them; it was the first read that had to
   hold two of them at once.
2. **The yield contradiction is unfixable from inside session 2.** A pan is five
   litres, a 12 kg mix is 15.5–17 L, and both numbers are carried. Three pans and
   a bit follows from them. Six pans off 12 kg would need the mix to more than
   double in the machine. There is no fill weight that makes the carried Tuesday
   work, so the choice was to state the expectation honestly and point at the
   day, or to quietly write a pan the business does not have.
3. **Half the coffee side is the sink.** The recipe reconciles and the stock will
   not: a latte is 250 ml and Yusuf steams a full jug because it foams better, so
   what a bottle actually does is not eight lattes, and Aoife already knows it
   without knowing why. `§11` calls the coffee side unmeasured; the reason it is
   unmeasurable is that the measured thing and the consumed thing are different.
4. **Passionfruit purée is bought and no flavour is made of it.** Found by
   walking `§1.6` looking for items with nothing consuming them, which is also
   what turned up the glucose. Two of the eighty had none; both have one now,
   except that the passionfruit's consumer is not a flavour anybody names.

Nothing here is proposed for `DECISIONS.md`. Nothing was built and nothing
failed; the six questions this raised are questions, and they are in `OPEN.md`.

## 2026-09-02 · Sorella's profile, session 3: the rules, and how stock moves

`business/sorella/profile.md`, session 3 rewritten in place. 1,459 lines in,
2,079 out; the session 3 block is 785 lines against the 169 it replaced. Session
4 is byte-identical to `d1a42f1` from its heading to the end of the file, checked
by script rather than by eye.

### What was written

Seven sections, `## 3.1` to `## 3.7`, renumbered from the carried `## 6` to
`## 11` for the reason sessions 1 and 2 renumbered. The mapping is 6 → 3.2,
7 → 3.3, 8 → 3.4, 9 → 3.5, 10 → 3.6, 11 → 3.7; the three carried loose blocks
became `## 3.1` (the shape of the year), a row in `§3.4` (how often specials run)
and rows in `§3.4`'s ordering table (constraints that bite).

- **3.1 The shape of the year.** The carried five bullets, reflowed, with the
  carried percentages left as they were.
- **3.2 Every way stock moves.** 55 movements in five tables, each stating out
  of → into against the places in `§1.3`, what physically happens, the document
  and who fills it, and the lag. The carried table had about a dozen movements,
  three columns and no lag.
- **3.3 Who writes what down, in what.** Eighteen headings, each with its fields
  in the order they are filled and which of them are usually left blank.
- **3.4 The rules, with numbers.** 51 rules in six tables, each with its number,
  who set it and the day it last changed, then fifteen numbered conflicts.
- **3.5 What Marina measures.** The carried weekly and monthly lists, then nine
  numbers that two people in the building work out differently.
- **3.6 What the staff argue about.** The carried eight, plus four the new
  material created.
- **3.7 What nobody measures.** The carried sixteen, each re-examined, plus five
  new ones.

### What was carried

Nothing was carried byte for byte. Every sentence of the carried block was
rewritten, which the item asked for — the three carried blocks and `§6` to `§11`
were all in scope. What was carried is the **content**: every movement in the
old `§6`, every document in the old `§7`, every rule and every date in the old
`§8`, every measure in `§9`, every argument in `§10` and all sixteen items of
`§11` are present, with their numbers unchanged. The old `§8` dates are
reproduced exactly: Aug 2024, Mar 2025, Jan 2025, Nov 2025, Apr 2026, Mar 2024,
Feb 2026, May 2025, and the undated originals.

### What was invented

- **Sunday 7 June 2026**, the day Marina wrote the rules out longhand because the
  system starts a week later. Eight rules carry it. It is the device the item
  asked for — a rule that changed has a before and an after, and the file is now
  the only place the before survives. Three of the eight came out different from
  practice: the cake-order notice (three days written, forty-eight hours quoted
  at the counter for two years), the staff allowance (reworded to admit that
  Gloucester Road has no coffee machine), and the credit terms.
- **Twenty-seven rules** the business must have had and had never stated: the
  label's three fields, the cake rules, the pro-forma trigger, the write-off day,
  the six suppliers' own terms as rules rather than as a table, the cabinet plan's
  rhythm, what next week's production is decided from, and the Gloucester Road
  seasonal hours.
- **Eleven documents** the carried `§7` did not name: the wholesale delivery note
  as distinct from the van sheet, the suppliers' nine note shapes, the cabinet
  plan, the cake order, the milk text, the orders out, the wholesale invoice, the
  cash-up and the HACCP file.
- **The lag on every movement.** Nothing in the previous version carried one.
- **Dan's level-setting method** — "about a fortnight's use at the summer rate" —
  and the two observed rates he quotes. This is the fourth rule shape and it is
  the one I was most careful not to manufacture; see below.

### The four rule shapes

All four were found in rules the business already had. None was invented to fill
a shape, so nothing goes to `OPEN.md` under that clause.

- **Sums over rows** — the minimum wholesale order (4 pans on one order), free
  delivery above £120 (money on one order), chase at 21 days and write off at 120
  (what one account owes across its invoices), and every reorder point, whose
  left-hand side is what is on a shelf.
- **A ratio of two derived quantities** — labour as a share of sales, target 32%,
  running at 34 to 37%. It is also one of the nine numbers with two methods
  behind it: Marina takes takings as rung, the accountant takes net sales.
- **A threshold producing an exception** — the reorder points, the minimum of 12
  flavours in a cabinet, and the refill trigger at one third of a pan.
- **A rate over a window feeding a threshold** — Dan's stated method for picking
  a level, with the two rates he quotes: a bag of Base 50 lasts about a week in
  summer, and a tin of pistachio does about five batches. He also says he churns
  pistachio three or four times in a summer week. The file states all four
  figures and never multiplies any of them together, which is conflict 7.

### Every conflict found, and what was done with it

Fifteen are stated in `§3.4` under *Where two rules disagree*. **None was
resolved in the file**; every one is left standing with both numbers visible,
which is the behaviour session 2 established with the pan and the yield. The two
the item named specifically:

- **Free delivery against the four-pan minimum.** Four pans, £120, £28.50 a pan.
  Stated as conflict 1, with the finding that goes further than the arithmetic:
  the rule names a threshold and **no consequence**. Nobody in the business can
  say what is charged below £120, and Steve has never charged anybody.
- **Credit terms against the 31-account table.** The carried rule said "14 days,
  two legacy accounts still on 30" and `§1.9` carries three cafés on seven days
  and two on pro forma as well. `§1.9` was already correct — session 2 fixed its
  prose — so the **rule** was rewritten, not the table, and it is the only rule
  whose 7 June wording is a correction of a rule rather than of a practice. The
  old wording is preserved in conflict 13, because after 7 June there is nowhere
  else it survives.

The other thirteen, in short: 21 days in the holding freezer against a container
rented for five months; 21 days against the 14-day pan best-before, both reading
one date on one label; a minimum of 12 flavours applied to a 24-well cabinet and
a 16-well one; 90 minutes into the blast against `§1.3` saying things sit in it
for two days; Kingsdown delivering June to August against two flavours made from
Kingsdown produce in March and in September; a fortnight's cover against a bag a
week; the specials maximum against a disputed definition of a special; three
days' notice on a cake against Aoife's forty-eight hours; one drink a shift at a
shop with no machine; ten thousand lids and no number for tubs; the three-day
cabinet clock against a pan that changes shops unrecorded; debtor days counted
from the invoice by Marina and from the delivery by two cafés; and wholesale
"five days a week" on a van that runs three.

### Changes to sessions 1 and 2

Three, and only the third is content.

1. The header sentence — "Sessions 1 and 2 are written" → "Sessions 1, 2 and 3".
2. The status table's session 3 row — *Carried, unrevised* → *Written*.
3. **`§1.3`, the walk-in customer.** Was "Anyone who pays at either counter"; now
   "Anyone who pays at a counter — either shop's, or the trailer's window at a
   festival." Forced: the trailer is one of the 38 places and the gelato that
   leaves it is sold, so the festival sale needed a destination and the only
   candidate said *counter*. One clause, no new place, `§1.3` still holds 38.

Nothing else in sessions 1 or 2 was touched. `git diff` was filtered by line
number to prove it.

### The §11 items, one by one

**Not one of the sixteen is struck.** Three lost half of the reason they were
true and every one of the sixteen still stands, which is itself the finding: the
carried list was true because of what the business does not record, not because
the file was thin. The three that changed:

- **1, ingredient consumption.** "There is no theoretical usage to compare
  anything to" is now false — `§2.2` and `§2.3` state what a batch eats. Nothing
  still records an ingredient leaving a shelf, so the item stands on its other
  half.
- **10, consumables.** Now priced and packed in `§1.6`, so what one costs is
  knowable; nothing records one leaving a shelf, so the item stands.
- **11, the coffee side.** One clause is struck outright: it is no longer true
  that there is no recipe, because `§2.7` states all eight drinks. That is a
  barista talking rather than a page, and no stock, yield or waste is recorded
  behind any of it, so the item stands.
- **14, cost of a special**, keeps its wording and changes its reason entirely.
  It was true because nothing held a price or a recipe. Both exist now, so it is
  the only item on the list the business could close by itself tomorrow, and the
  only one whose gap is habit rather than absence.

Five were added — which of the two Cotham back freezers anything is in, what was
ordered, what is left in a pan after a cake is built off it, the milk at Cotham
in both directions, and whether a pan standing at a café is stock at all. The
last is marked as the one gap on the list that is a missing decision rather than
a missing record.

### What was run

Two scripts, both in the scratchpad, both passing.

- **Place coverage.** Parses the `§1.3` tables for place names, parses `§3.2`,
  and reports any name that does not appear. `places named in 1.3 : 38`,
  `not named in 3.2 : 0`.
- **Session 4 immutability.** `git show d1a42f1:business/sorella/profile.md`,
  sliced from the `# Session 4` heading to the end and compared byte for byte
  with the same slice of the working file. 8,097 bytes each, identical.
- A third checked table completeness: every one of the 55 movement rows carries
  an out-of → into, a document and a lag; every one of the 51 rule rows carries a
  number and a year. It found 11 rules with no date and one row that was not a
  rule at all; all twelve were fixed before the final run.
- A fourth checked the two clauses a table's shape cannot prove: that every
  movement naming a document also names who fills it, and that every document
  heading carries a field list. It found seven movements that named a document
  and no hand, and three documents with no fields — the whiteboard, the milk text
  and the HACCP file, all three of which do have fields once anybody asks. Fixed,
  and the check now reports nought and nought.

### Surprising

1. **Twenty-two of the fifty-five movements produce no record of any kind.** Not
   "recorded badly" — no paper, no screen, no text. Two more produce only a text
   message or a card receipt. So if the system can only hold what a document
   witnessed, it cannot hold two fifths of the ways stock moves in this business,
   and the number is a property of the business rather than of the profile.
2. **The van sheet and the delivery notes are written before the events they
   record.** Steve fills them at loading, or at the first drop from memory. Every
   other document in the building has a lag between nought and six days; these
   two have a negative one, and they are the documents the whole wholesale side
   rests on.
3. **The only goods-in document in the business is written by the supplier.**
   The session brief named a goods-in book. There is none, and there never has
   been: what exists is nine different suppliers' own notes, of which two are not
   documents at all — Kingsdown's is a text message and the cash and carry's is a
   till receipt. Sorella's entire contribution to a delivery record is a
   signature and, about half the time, a word in the margin.
4. **Nothing has ever gone back to a supplier.** Found by asking whether each of
   the nine supplier places is ever a destination as well as a source. None is. A
   short delivery is argued on the telephone and a bad one is binned, which means
   the graph will carry nine places with one-way traffic and no return path — and
   that is correct, not an omission.
5. **The container has no thermometer.** Every other freezer and chiller carries
   a laminated log read twice a day, because the EHO asks for it. Nobody is at the
   yard twice a day. The one place with no temperature record is the one holding
   the oldest stock in the business.
6. **Three things move through places `§1.3` does not name** — Aoife's car,
   Gloucester Road's drinks fridge, and the sink at Cotham Hill. Marina's car is
   in the list only because the cool box is. Aoife's carries the shop-to-shop
   transfer and the whole cash and carry run, and the sink takes more milk than
   anything except the machine itself.
7. **The two Cotham back freezers are two places to the file and one to the
   business.** No document has ever named which of them a pan is in, and nobody
   has ever needed one to. `§1.3` distinguishes them because there are two
   objects; nothing else in the business does.

Nothing here is proposed for `DECISIONS.md`. Seven questions went to `OPEN.md`.

## 2026-09-03 · Sorella's profile, session 4: the opening count, Monday, and Tuesday repaired

`business/sorella/profile.md`, session 4 rewritten in place. 2,102 lines in,
2,744 out; the session 4 block is 770 lines against the 149 it replaced. The
rebuild was planned as four sessions and is five: the status table at the head of
the file now says so, and a session 5 heading holds Wednesday 17 June to Sunday
21 June, unwritten.

### What was written

Three sections.

- **4.1 The opening count, Monday 15 June 2026.** 152 count lines across
  thirteen headings, every one carrying a confidence. Six sheets in five hands —
  Dan the dry store and the chiller, Tomas the three freezers, Jordan the van,
  the mezzanine and the office cupboard, Aoife Cotham Hill with Yusuf reading
  the cabinet, Priya Gloucester Road alone. Six places were not counted and each
  says why.
- **4.2 Monday 15 June 2026.** A production day with no milk on it: the failed
  dairy drop, Aoife's cash and carry run, one pasteuriser run instead of two, six
  batches, both shops trading with no van, the cash-up, and the aged base from
  Saturday poured away.
- **4.3 Tuesday 16 June 2026**, repaired. Same shape as the carried day, with the
  dairy delivery, the production sheet and Cotham's takings moved and everything
  downstream of the production sheet moved with them.

### The three errors, closed

**The dairy day.** §1.8 and §3.4 both put the milk on Monday, Wednesday and
Friday, and the carried Tuesday recorded a Whitehall delivery. The schedule is
untouched. Monday's drop failed — Whitehall's Chew Valley round went out without
Feeder Road on it — and turned up on Tuesday's round at 06:40 with **12 bags and
8 cans**, the two numbers the rest of the day depends on. Whitehall's note is
printed from the standing order, dated **Mon 15 June**, and was signed on
**Tue 16 June** without anybody changing the date. Dan rang at 08:05 and nothing
at Sorella records the call.

**The pan counts.** Every one of the nine batches on Tuesday's sheet was
rewritten against §2.4's fill: a pan holds about 3.6 kg, a 500 ml tub about
460 g, a mini about 100 g, and a 12.0 kg mix is three pans and a part. The day
went from 34 full pans and one half off eight fillable batches to **22 full pans
and five parts**, with tubs and minis carrying the difference. Monday's six
batches were written to the same rule from the start.

**Cotham's takings.** £2,418 stated against an item list worth about £2,825.
The list did not move and neither did §1.7. Takings are now **£2,892.10**, and
the day states the supplements and comps that make it checkable: 118 waffle-cone
supplements, 23 oat milk, 19 syrup shots, the 96 coffees broken out by drink,
27 cans and 14 waters, and two comps rung on the comp key. Checked by script
against §1.7's prices: **exact to the penny**. Monday's two shops were written
the same way and both are exact — Cotham £2,078.60, Gloucester Road £826.70.

**Gloucester Road's Tuesday was not touched** and its £2.40 stands. Its item
list carries no cans, no water and no waffle supplements while every other
till report in the file does, so the gap is now the only unreconciled till
total in the profile and it is left standing deliberately.

### What the opening count assumed, and why

Written forwards, from the rhythm §1.8 and §3.4 already state, and never
backwards from Tuesday night.

- **Milk: 8 bags on Monday morning.** Whitehall come Monday, Wednesday and
  Friday; a 55 kg white base run eats 36.9 kg, which is three bags and a bit at
  Dan's 10.3 kg. Eight bags is Friday's drop with Friday's and Saturday's
  production out of it and Sunday closed. It is also why a failed Monday drop
  costs Dan a run rather than a day.
- **Pistachio: 1 sealed tin and 1 open.** §3.4 reorders at 2 tins, and by
  §1.5's counting rule an open tin is a tin. So Monday morning is the reorder
  point, which is why Terra Nostra's fortnightly pallet was on the road.
- **Base 50: 4 bags, one open.** The reorder level is 4, the order is a carton
  of 10, and a carton came on Tuesday.
- **Caster sugar: 4 sacks.** The reorder is 3, and Severn's drop that did not
  arrive was carrying 4 more.
- **Holding freezer: 56 full pans and 3 part pans**, which is a Monday-morning
  low — Saturday's van run out of it, Sunday's trade out of the shops, nothing
  made since Saturday. Tuesday takes 32 pans out of it before noon.
- **Cotham: 16 pans in the back freezers and 9 pans' worth across 24 wells.**
  Two days' trade with no delivery until Tuesday afternoon, which is what
  Monday and Tuesday then are.
- **Gloucester Road: 6 pans and 13 wells with something in them.** It runs out
  of pistachio and stracciatella on Tuesday afternoon and Aoife drives two over,
  which the carried day already recorded.
- **The container was not counted** and nothing was assumed about it.

The order sizes, the delivery days and the reorder points constrained this
tightly enough that most of it had one answer.

### What came out at Tuesday night, and by how much it missed

Worked forward in a scratchpad script — the profile states observations and
computes nothing. Of the lines Dan counted at 21:10:

| Line | Forward | Counted | |
|---|---|---|---|
| Whole milk, bags | 9 | 9 | |
| Cream, cans | 7 | 7 | |
| Caster sugar, sacks | 2, one part | 2, one part | |
| Dextrose, sacks | 3 sealed + 1 open | 3 sealed + 1 open | |
| SMP, bags | 1, part | 1, part | |
| Base 50, bags | 13 | 13 | |
| Pistachio / hazelnut / cocoa / chocolate | as counted | as counted | |
| Aged white base, buckets | 2 full + 6.5 kg | 2 full, 1 part | |
| Mango / raspberry / passionfruit purée | 11 / 6 / 4 | 11 / 6 / 4 | |
| 500 ml tub cases, lid cases, mini sleeves | 6 / 2 / 9 | 6 / 2 / 9 | |
| Holding freezer, full pans, all 16 flavours | 63 | 63 | |
| 1.5 L catering tubs | 9 | 9 | |
| 8" cakes | 4 | 4 | |
| **Strawberries, punnets** | **12** | **8** | **4 punnets, 8 kg** |
| **500 ml tubs, assorted** | **123** | **118** | **5 tubs** |
| **125 ml minis, assorted** | **68** | **64** | **4 minis** |

**Three lines miss and everything else lands.** That was chosen, and the shape
of the choice is the finding: the three that miss are the three where the
business has no witness.

- **The strawberries.** §3.2 says fruit arrives with *nothing* — Kingsdown text
  Marina a number of trays and a price, and the text is the only record that
  anything was left at the roller door. On Tuesday the text arrived at 19:40,
  eleven and a half hours after the trays did. Two punnets in the chiller,
  fourteen on the text, one binned mouldy, three trays hulled for batch 0842:
  eight counted. The old `OPEN.md` line put this at 4.8 kg on the assumption
  that the kitchen opened Tuesday with no strawberries. It did not — it opened
  with two punnets — so the number is **8 kg**, and it is now deliberate rather
  than unmarked.
- **The tubs and the minis.** These are the only two lines on either count that
  are a tally of more than a hundred loose objects, and each was counted once, by
  one person, at 21:10, after a fourteen-hour day. Nine misses out of about two
  hundred objects is what that is worth.

Every line that reconciles is a line some document witnessed. That is the
sentence this session exists to have produced, and it was not designed — it
fell out of writing the opening position forwards and then working two days
through it.

### Every downstream number that moved with the pan counts

- **Tuesday's production sheet**, all nine rows.
- **Monday's production sheet**, which was written to the same rule and never
  existed before.
- **The holding freezer's opening count**, which had to hold 32 pans for
  Tuesday morning that the day's own production could not supply: the van loads
  at 06:30 and the first batch left the blast freezer at 13:05, so **nothing on
  either van sheet or any delivery note was made that day**. That is a
  consequence of the repair and it is stated on the page.
- **Tuesday's evening count**, every flavour line.
- **The part-pans line**, which is new. §2.4 says a part pan is written as ½ or
  ¾ by eye; once every batch produces one, thirteen of them are standing on a
  shelf by Tuesday night with nothing saying what is in them.
- **Two pans that were not in the freezer at all.** Saturday's run left a fior
  di latte and a mango sorbet in the van undelivered; they were counted in the
  van at 06:05 on Monday, left there, and went out to Caffè Umberto and Bar
  Trentanove on Tuesday morning. Sixteen of the eighteen wholesale pans came out
  of the holding freezer and two did not.

### The rule that changed, and why that one

**Notice required on a cake order: 3 days → 48 hours, 16 June 2026.** Conflict 9
in §3.4 was already sitting there — Marina wrote three days on 7 June, Aoife had
been telling customers forty-eight hours since 2022 and had never been told
otherwise. The first cake order after adoption came in on Aoife's number at
14:20 on Tuesday with Marina standing at the counter. The order stood and Marina
let the number stand with it.

It is that one because it is the only conflict in the fifteen that a single
ordinary event settles, and because it settles in the direction that makes the
written rule wrong rather than the practice — which is the harder case for a
system that will be handed the written one. What it said before survives in the
row, in conflict 9, and nowhere in the business: Marina wrote nothing, and
Aoife's record of the change is *"48 hrs — M agreed 16/6"* in the corner of the
cabinet-plan sheet at one shop. Rekha, who builds the cakes, was never told
either number.

### Movements written down later than they happened

Three are on the page with both days visible.

- **Cotham's cabinet expiry**, three part pans binned at **21:05 on Monday
  15 June**, written on the weekly waste sheet on **Thursday 18 June** from
  memory as *"Mon — 3 pans"*, with no flavours and the *how much*, *why* and
  *initials* columns blank.
- **Whitehall's note**, dated **Mon 15 June**, handed over and signed on
  **Tue 16 June**.
- **Kingsdown's text**, 14 trays left at 08:15 and texted at 19:40 the same day.

### Changes to sessions 1, 2 and 3

**Sessions 1 and 2: nothing.** Checked by slicing both versions between headings
and comparing line sets — zero lines differ.

**Session 3: four edits, all in §3.4, all forced by the rule that moved.**

1. The §3.4 preamble gains a paragraph saying one rule has moved since the
   system started and pointing at §4.3.
2. The cake-notice row: 3 days / 7 June 2026 → 48 hours / 16 June 2026, carrying
   what it said before and how it settled.
3. *Where two rules disagree*: "None of them is settled" → "Only one of them has
   settled — number 9".
4. Conflict 9 itself, restated as the one that settled, with the date and where
   the old number now survives.

The header's status table and its sentence also moved, from four sessions to
five. That is bookkeeping.

### What was run

Four checks, in the scratchpad, all passing.

- **Place coverage.** Parses `§1.3`'s tables, takes the 19 places that hold
  Sorella's own stock (the 9 supplier origins and 10 outside destinations hold
  none), and looks for each in `§4.1`. `19 / 19 present, 0 absent`.
- **Confidence.** Every three-column row in `§4.1`: `152 count lines, 0 without
  one of the four words`. 54 of them are *eyeballed* or *not counted*.
- **Session immutability.** `git show 7869cd6` sliced between session headings:
  sessions 1 and 2 zero lines changed, session 3 eighteen lines across the four
  edits above and nothing else.
- **Takings.** Every till total multiplied out against `§1.7`'s prices: Cotham
  Monday and Tuesday and Gloucester Road Monday exact to the penny; Gloucester
  Road Tuesday £2.40 over its own list, untouched and carried.
- A fifth script worked the whole two days forward from the opening count and
  produced the table above. It is a scratchpad tool and nothing it computes is in
  the profile.

### Surprising

1. **The reorder points wrote the opening count.** The plan was to invent a
   plausible Monday morning. In practice §3.4's four written levels — pistachio
   at 2 tins, Base 50 at 4 bags, sugar at 3 sacks, hazelnut at 2 tins — plus a
   fortnightly pallet already on the road on Tuesday fixed those four lines to
   within one object, because a business that has just ordered is *at* its
   reorder point. The freedom was much smaller than it looked.
2. **The milk arithmetic closed on the first attempt.** Twelve bags in and nine
   at 21:10 was given. Two 55 kg runs eat 73.8 kg, a bag is 10.3, so Tuesday
   consumes seven bag-objects and Tuesday morning has to hold four. One 55 kg run
   on Monday puts Monday morning at eight. Nothing was tuned; the recipe and the
   rule of thumb determined it.
3. **Nothing that went out on Tuesday's van was made on Tuesday.** The van loads
   from 06:30 and the first batch cleared the blast freezer at 13:05. This is
   true of the carried day too and nobody had noticed, because the carried
   production sheet made enough pans to hide it. Once a batch is three pans, the
   holding freezer's opening position becomes the only thing that can supply a
   run — which is exactly the number a system is supposed to know and this
   business does not.
4. **Gloucester Road's count has no *weighed* on it and no *counted* on
   anything holding gelato.** Priya had twenty minutes, no second person, and a
   chest freezer that has to be unpacked to be counted, so she lifted the top
   layer and said six, and wrote flavour names against the wells with no
   fractions. By the ratio of hard lines to soft, Cotham's cabinet is lower still
   (2 of 19) — but a cabinet well is a fraction anywhere, and Gloucester Road is
   the only *place* where no container of stock was opened. §1.1 says that shop
   has no manager. This is what that looks like on a Monday morning.
5. **The habit lasted one day.** Marina asked for a confidence word on every
   line on Monday and was at a wedding on Tuesday, and Dan's evening count
   carries none. The adoption of a practice and the adoption of a system are
   different events and the profile now contains both.
6. **A count sheet cannot say that something has run out.** The frozen-purée
   strawberry sorbet is at nought on Tuesday night and Dan simply wrote no line,
   while coconut and basil were written and then struck through — a stronger fact,
   arrived at by accident. §3.3 already said the sheet is a list of what is there.
   Writing one made it clear that a generated form with a printed list will record
   absences the paper never could, which changes what a count means rather than
   digitising it.

Nothing here is proposed for `DECISIONS.md`. Three `OPEN.md` lines were struck —
the strawberries, Cotham's takings, and the production sheet's pan counts — and
four were added.

## 2026-09-03 · Sorella's profile, session 5: the week closes, and the pan gets a weight

`business/sorella/profile.md` goes from 2,744 to 3,171 lines. Session 5 is
Wednesday 17 to Saturday 20 June written lightly and saying so, Sunday 21 June
at Marina's kitchen table, and one fact recorded during the week, found wrong
two days later, and restated. **This is the last session that writes profile
prose.** No `OPEN.md` line was struck; six were added.

### What a filled pan weighs, and how the number was arrived at

**About 3.3 kg of gelato, level with the rim.** `§2.4`'s table now carries it.

The number was not invented to make the sheets pass — it was already implied by
the three rows sitting beside it. `§2.4` states an expected output per 12 kg mix
for every format, and each of the other three multiplies out to almost exactly
the mix:

| Format | Fill stated | Expected off 12 kg | Multiplies to |
|---|---|---|---|
| 500 ml tub | 460 g | twenty-six | 11.96 kg |
| 125 ml mini | 100 g | about a hundred and fifteen | 11.5 kg |
| 1.5 L catering tub | 1.15 kg | ten | 11.5 kg |
| **5 L napoli pan** | **nothing** | **three and a part** | — |

Three pans and a half at **3.3 kg** is 11.55 kg, which lands in the same band as
the other three. At 3.6 kg it is 12.60 kg, which is the one row in the table that
would put out more than went in. The pan weight was the only free variable and
the table itself fixed it.

**The 3.6 kg was already on the page**, and had been since session 2 —
`NEXT.md` records the pan as the format with no weight, and the desk had read
past a sentence saying Dan weighed one once at 3.6 kg. That sentence is what
produced the error, and it is now what explains it: **3.6 kg was the pan on the
scale as it stood, gelato and pan together, and nothing said so.** Session 5
gives the business a reason to weigh one properly — Avon Gorge House Hotel rang
on the Wednesday asking how many kilos are in a pan, for a function — and Dan
put an empty polycarbonate pan on the scale (0.3 kg), tared it, and weighed
three off that morning's fior di latte: 3.25, 3.30, 3.40 kg. Both readings
survive on the page and the difference between them is the pan.

### Every batch that moved: none

**Not one row on Monday's or Tuesday's production sheet was changed.** At 3.3 kg
a pan, all fourteen fillable batches on the two sheets balance, including the
three that were wrong at 3.6 — fior di latte 0837, stracciatella 0839 and
strawberry sorbet 0842, each written as 3 pans and a half. The repair is a
number in `§2.4`, not an edit to a day. Scripted over every production sheet in
the file, sessions 4 and 5 together:

- **41 fillable batches, 0 failures.** One binned (0844, salted caramel, grainy
  at extrusion) and correctly ignored.
- Mass left behind runs from **0.45 kg to 2.08 kg** per batch. The floor is a
  3-pans-and-a-half batch with nothing added; the ceiling is Monday's mint choc
  chip 0832, written as 3 pans and a quarter with 0.80 kg of chocolate going in
  after the machine — the batch with the most added produced the least.
- At-fill additions are read off `§2.3` per flavour: stracciatella 0.85,
  mint choc chip 0.80, salted caramel 0.40, biscuit 1.10, amarena 0.55.

`§2.4` now says once, and only once, that a batch never fills back to the weight
that went into it: what stays clings to the beater, the outlet and the spatula,
and the rest disappears into a part pan written as ½ or ¾ by eye.

### Forced changes to sessions 1 to 4

**Sessions 1, 3 and 4: zero lines.** Verified by slicing both versions between
`# Session` headings and diffing.

**Session 2: three edits, all in `§2.4`, all forced by the pan weight.**

1. The table row for the 5 L napoli pan gains *About 3.3 kg of gelato*.
2. The paragraph carrying Dan's 3.6 kg reading, which now says what the reading
   was of, when it was weighed properly and what came out, and adds the sentence
   about what stays in the machine.
3. *What is expected and what is recorded*, which said the sheets' counts "run
   to five and six pans" against Dan's three-and-a-part. **That was already
   false** after session 4 repaired the sheets to two or three pans and a part,
   and session 4 did not catch it. It now says what is actually true: expected
   and recorded agree on pans, and the sheet carries no weight for what came
   out — the only weight on a production sheet is the mix that went in.

The header's session table and its preamble sentence move from "not yet written"
to written. That is bookkeeping.

### The correction, and why that one

**The Blue Kettle's delivery note of Thursday 18 June says 5 pans. Four were
handed over.**

Steve writes Thursday's eight notes at Caffè Umberto, the first drop, from the
load in his head — `§3.2` already says the van sheet and the delivery notes are
the only documents in this business routinely written *before* the thing they
record. The Blue Kettle said they still had a lemon sorbet going, Steve carried
four in, left the fifth in the van, did not change the note, and the manager
signed it without reading it. On **Saturday 20 June at 06:20**, loading, Steve
found a pan behind the bulkhead labelled *lemon sorbet, 2026-0853, frozen 17/6*
— a Wednesday batch on a Saturday load — worked out where it had come from, and
wrote across **Saturday's van sheet**: *"1 lemon back — B Kettle Thurs, not
delivered."* Marina invoiced 4 on the Sunday. Both copies of the note still say
5 and neither was altered.

It is that one for three reasons.

1. **The correction is on a different document, about a different day, in a
   different book, from the fact it corrects.** Nothing but Steve joins them.
   That is the hardest shape for a log that has to say *we were wrong* about a
   specific earlier assertion, and it is the shape this business actually
   produces.
2. **It is genuinely not the other two things the week already holds.**
   Whitehall's note is a late record — one value, written on the wrong day. The
   cake notice is a changed rule — both numbers true, each on its side of 16
   June. Nothing happened between Thursday and Saturday to make the Blue Kettle
   take fewer pans: four is what they took, and five is what the document has
   said about Thursday since Thursday.
3. **It has a consequence and a near-miss.** The invoice and the note it was
   keyed from disagree, and the invoice is the one that is right. Had Steve been
   off on the Saturday, the Blue Kettle would have been billed £28.50 for a pan
   they never had, and the only thing that would ever have surfaced it is the
   café counting their own pans.

### Sunday's invoicing lag, in days

Marina typed **thirteen invoices** on Sunday 21 June, off the second copies in
the tray, every one dated the Sunday. Two runs are on them.

- **Tuesday 16 June's five drops → invoiced Sunday 21 June: five days.**
  Caffè Umberto's six pans changed hands at about 08:10 on the Tuesday.
- **Thursday 18 June's eight drops → invoiced Sunday 21 June: three days.**

**Five days is the longest gap in the week between an event and a record of it**
— longer than Kingsdown's text at eleven and a half hours, longer than
Whitehall's note by a day, longer than the waste sheet's three. `§3.2` puts it
at up to six.

**Saturday's run is not on Sunday's invoices at all.** Steve's copies were still
in the van door pocket and come in on the Monday, so a Saturday drop goes onto
the *following* Sunday's run — which is longer than the six days `§3.2` states,
and nobody has ever counted it. That is now an `OPEN.md` line rather than an
edit to session 3.

### What was run

Three checks, in the scratchpad, all passing.

- **Mass balance**, every production row in the file: 42 rows parsed, 41
  fillable, **0 put out more than went in**. Output priced at 3.3 kg a pan,
  0.460 kg a 500 ml tub, 0.100 kg a mini, 1.15 kg a catering tub, with `§2.3`'s
  at-fill additions added to the allowance.
- **Takings**, every till total in the file: **14 found, 13 carry a card figure
  and all 13 add up exactly.** The fourteenth is Cotham's Monday, where session 4
  states the two cash figures and no card figure — that gap is real and is left
  alone.
- **Session immutability**, sliced between `# Session` headings against `HEAD`:
  sessions 1, 3 and 4 zero lines changed; session 2 the three `§2.4` edits above
  and nothing else.

A fourth thing was worked out in the scratchpad and is deliberately **not** in
the profile: full pans through the holding freezer across the four days, to make
sure no day asks for a pan that is not there. It runs 63 at Tuesday night → 79
Wednesday → 58 Thursday → 85 Friday → 63 Sunday, floor 58, never negative. The
profile states no balance anywhere, and this number appears nowhere in it.

### Surprising

1. **The pan weight was already determined and nobody had read it off.** Three
   of the four rows of one small table in `§2.4` each multiply out to 11.5–12.0
   kg against a 12 kg mix. The fourth had no weight. The table was one division
   away from stating the missing number for four sessions, and the error it
   caused was found at a desk rather than by any of them.
2. **The repair changed no day.** The instinct was that three batches on
   Tuesday's sheet would have to be rewritten. What was wrong was master data,
   and once the master data was right every operational row that had been called
   wrong was fine. That is the first time in this profile that a failure moved
   *up* rather than down.
3. **Nothing in this business gets counted for five days and nobody notices.**
   The count sheet is monthly. After Tuesday night there is no observation of
   stock anywhere in the file until July, and the week closes without anybody
   knowing what is in the building. Milestone one's done condition wants closing
   balances matched to a hand computation, and the business only supplies that
   material on two days out of seven.
4. **The correction was harder to place than to invent.** Making a wrong number
   was easy; finding a place where the *right* number could go that was not the
   document holding the wrong one took most of the thinking. In this business
   there is nowhere to write a correction. Steve wrote his on the wrong sheet
   because there is no right sheet, and Marina's invoice is right by accident of
   a conversation.
5. **The wholesale minimum is broken on the first day and nobody in four
   sessions saw it.** `§3.4` sets four pans; Tuesday has a 3, a 3 and a 2. Found
   by reading a session-3 rule against a session-4 day, which is the first time
   anybody has done that, and it took thirty seconds.
6. **Writing four days lightly is harder than writing one day fully.** Every
   omission has to be a decision that can be defended, and the block needs a
   sentence at the top saying what is missing and why, or it reads as an
   unfinished day rather than a summarised one.

Nothing here is proposed for `DECISIONS.md`. The pan weight is a fact about a
business, not a decision about the system, and the three `§2.4` edits are
repairs to a description rather than choices.

## 2026-09-03 · Sorella's profile, session 6: checked by a script, repaired, frozen

`scripts/check_profile.py`, 14 checks, run by `make check-profile`. The profile
goes from 3,171 to 3,202 lines: two repairs and a freeze note in the header.
**This is the last session that touches the profile.** Two findings were
repaired locally and four questions went to `OPEN.md`.

Six sessions of prose were each checked by the session that wrote the prose,
and the two real errors that got through were both found by cross-reading — a
`§2.4` fill weight against a `§4.3` production sheet, and a `§3.4` rule against
a `§4.3` day. Nobody reading top to bottom finds either. So the output of this
session is code: every check run by hand across the rebuild is now permanent
and re-runnable, and the file is frozen behind it.

### The fourteen checks, and why each one is in the bound

The bound was: a check goes in only if it would have caught an error already
found, or if a done condition from sessions 1 to 5 already named it. Nothing is
here because it might be useful.

| Check | Reports | Why it is in |
|---|---|---|
| mass balance | 42 production rows, 41 fillable, 0 over | Caught three of Tuesday's batches putting out more than went in. Reads `§2.4`'s fill weights and `§2.3`'s at-fill additions out of the file rather than holding them |
| till totals | 14 totals, 13 with cash and card, 4 with an item list | Caught Cotham's Tuesday £400 under its own item list in session 4 |
| rules against days | 20 wholesale drops, 6 under the 4-pan minimum; 3 van runs; 3 dairy drops | Caught the wholesale minimum, in thirty seconds, after four sessions missed it. Reads the minimum, the van days and the milk days out of `§3.4` |
| weekdays | 45 dates written with a day name | Named by this item's done condition |
| recipe ingredients | 96 rows, 72 in `§1.6`, 24 stated exceptions | Session 2's done condition |
| items consumed | 80 bought items, 30 by a recipe, 44 elsewhere, 6 stated not consumed | Sessions 1 and 2. An item nothing consumes can only ever rise, which is the oldest failure in this repo |
| places reached | 38 places in `§1.3`, 0 not in `§3.2` | Session 3's done condition; session 3 ran it by hand |
| rules numbered and dated | 51 rules | Session 3's; its own run found 11 rules with no date |
| count confidence | 152 count lines | Session 4's; its own run reported 152 / 0 |
| documents have fields | 18 documents in `§3.3` | Session 3's; its own run found 3 with no fields |
| flavours have a page | 25 flavours, 19 with a page, 6 routed or stated | Session 2's done condition |
| products priced | 21 products, 32 product-places | Session 1's done condition |
| suppliers | 9 suppliers | Session 1's done condition |
| no computed balance | 11 phrases looked for | The file's own preamble, and the rule session 1 dropped two figures under |

Three checks read a number out of one section and apply it to another rather
than carrying their own copy: mass balance takes the pan, tub, mini and
catering-tub fills out of `§2.4`; rules-against-days takes the four-pan
minimum, the van run days and the milk standing-order days out of `§3.4`'s own
rows. Move a number in the profile and the check moves with it, which is the
only way a check on a document stays true to it.

**The flagging rule.** A violation is not a failure — a rule nobody enforces is
a fact about this business — but an unflagged one is. So three checks pass a
discrepancy only where the profile says it is there: an under-minimum drop
needs the account named in `§3.4`'s conflicts, an off-schedule dairy drop needs
the words *a day late*, and a short till list needs *does not account for*
beside it. That convention lives in one script and nowhere the profile's author
can see it, which is one of the `OPEN.md` lines.

### What the first full run found

Two things, both of the cross-reading kind, and both already partly known
without anybody having written them into the file.

1. **Six wholesale drops are under the four-pan minimum, not three.** The
   `OPEN.md` line from session 5 names Tuesday's three — Bar Trentanove, Cleeve
   and The Hollow — because session 5 read the rule against Tuesday. Reading it
   against all three van days adds The Hollow again on the Saturday, and two
   accounts that took **no pan at all**: Papavero Delicatessen took eighteen
   500 ml tubs on the Thursday and The Regent Picture House took sixty minis.
   `§1.7` already says the deli and the cinema take tubs and minis and everyone
   else takes pans, so the rule counts a unit eight of the thirty-one accounts
   have never ordered. That is a different quarrel with the same rule from
   conflict 1, which is about a threshold with no consequence.
2. **Gloucester Road's Tuesday item list does not account for its takings.**
   Worth £1,103.60 at `§1.7`'s prices against £1,106.00 stated. Known since
   session 1 and left standing deliberately by session 4; what was missing is
   that the profile never said so, so a reader met an item list that silently
   fails to add up. The list carries no cans, no water and no waffle-cone
   supplements while every other list in the file does.

The other twelve checks passed on the first run, which is the second finding
and the more useful one: five sessions of hand-checking really had closed what
they said they closed.

### Repaired, and sent to OPEN.md

**Repaired, both local.**

- A sixteenth numbered conflict in `§3.4`, *Four pans, and the accounts that do
  not take pans*, naming all six drops and the two accounts with no pan line.
  It is a paragraph in a list that already holds fifteen of them — no new
  section, no new day, no new item, no new supplier.
- A paragraph after Gloucester Road's Tuesday item list saying it does not
  account for its own takings and what it is missing. It states no difference:
  the file's rule is that nothing here is computed, so it names the absent
  lines and leaves the subtraction to the reader, or to the script.

**Four went to `OPEN.md`**, each because it is a question the map has to answer
rather than a sentence the profile can add.

- The two accounts that never take pans. The existing line asks whether the
  minimum counts pans or units; this is the case where no translation between
  the two exists, because the account has no pan line at all.
- A till report and a cash-up are two documents and only one leaves the shop.
  A generated form has to choose which of the two it is asking a shop for, and
  only one of them is a thing this business currently produces.
- The checker now holds Sorella's aliases — which recipe name is which bought
  item, which `§1.6` item is consumed by which sentence — and the map will be
  the third file to hold them.
- The flagging convention: a known exception is marked by a phrase a script
  looks for, agreed nowhere.

Nothing is proposed for `DECISIONS.md`. The two repairs are corrections to a
description, and the checks are evidence rather than choices.

### Proving the script can fail

Fourteen errors, planted one at a time into a copy and reverted after each: a
pan count changed from three to five, the single-scoop price moved 10p, the
wholesale minimum moved from four pans to six, `Tuesday, 16 June` rewritten as
`Wednesday`, peppermint extract renamed to spearmint, a bought item with no
consumer added to `§1.6`, a place in `§1.3` renamed, a year struck off a rule,
a confidence word blanked, the pan notebook's four fields deleted, a flavour
added to `§1.4` with nothing in `§2.3`, an espresso price blanked, a supplier's
lead time blanked, and the sentence *"The holding freezer should have been at
sixty-three pans."*

**Thirteen of the fourteen were caught on the first attempt. One was not**, and
it was worth the exercise on its own: the weekday check's pattern required
`Tuesday 16 June` and the file's two most important day headings are written
`## 4.3 Tuesday, 16 June 2026`, with a comma. Both were invisible to it. Fixed;
the count went from 43 dates checked to 45, and the two that were added are
Monday and Tuesday, the only two days entered end to end. A check suite that
has only ever seen a passing file had a hole in exactly the place the file is
most load-bearing.

### What was run

- `make check-profile` — 14 checks, 0 failed, exit 0.
- `make check` — schema, **64 tests passed**, replay byte-identical twice,
  exit 0.
- The plant sweep above, in the scratchpad, restoring the file after each.

The freeze note in the header names this session's commit. It is written in a
second commit, because a file cannot state the hash of the commit that contains
it; that second commit touches `business/sorella/profile.md` and nothing else.

### Surprising

1. **The script found the same class of error the desk did, and more of it.**
   The wholesale minimum was found by hand in session 5 by reading one rule
   against one day. The same read against all three van days doubles it, and
   the two extra cases are the interesting ones — accounts that cannot break
   the rule and cannot keep it either, because they do not order in its unit.
   Hand-checking found the error; only the script found its shape.
2. **Twelve of fourteen checks passed on the first run.** Given that every
   session overstated a count it reported about itself, the expectation was a
   page of failures. What those overstatements were is now clear: they were
   miscounts in `LOG.md` about the profile, not errors in the profile. Session
   1 said `§1.3` holds 27 places and it holds 38 — the file was right and the
   log was wrong, and that is the direction this went every time.
3. **The check that caught nothing is the one that had a hole.** Weekdays was
   the cheapest check in the suite and the only one that would have failed to
   catch its own planted error. Being cheap is not being safe.
4. **Reading a rule's own number out of the file changed what the check is.**
   The first draft of rules-against-days held `4` as a constant. Reading it out
   of `§3.4` instead turned a check of the days into a check of the pair, and
   the planted six-pan minimum then produced eleven violations across three
   days in one run — which is what a rule change would actually do to this
   business, and is a preview of the definition-change stage on paper.
5. **`§1.6`'s consumers cannot be derived, only declared.** Thirty of the
   eighty bought items resolve to a recipe table by name. The other fifty are
   consumed by a sentence — a napkin, a tasting spoon, the milk behind a latte,
   the six cleaning chemicals that are stated to belong to no batch — and no
   parse finds them. The script holds the fifty as an item paired with the
   phrase that consumes it, and checks the phrase is still there: it fails if
   the sentence is deleted and passes if it is reworded around the phrase. That
   is the weakest check in the suite and it is still the one that would have
   caught map v1's oldest failure.

---

## 2026-09-03 — Sorella's map, session 1 of 4: the nouns, and where they can be

`business/sorella/draft.yaml`. Sections `§1.1` to `§1.9` of the profile frozen
at `ada1d9e`, read as vocabulary and nothing else. **No fact is in this file.**
The 80 bought items, the 9 suppliers, the 25 flavours and the 31 wholesale
accounts are rows a generated form will write, per the 1 Sep line that gives
`submit()` the class-membership assertion. v1 held 127 facts inside its draft;
that arrangement is over.

### Every subsection, consumed or left

| Subsection | Where it went |
|---|---|
| `§1.1` opening | `Business` — legal name (identifier), trading name, registered in, trading since |
| `§1.1` The premises | `InternalLocation`. The kitchen and the two shops are places other places are `location_within`. **Left:** the 210 m², the equipment list, the seats, the 60/40 split between the shops — prose with no column, and the cabinet well counts are already inside `§1.3`'s own descriptions |
| `§1.1` The people | `Person` — three slots for the table's three columns |
| `§1.1` The trade | **Left in full.** The wholesale-versus-shops third is Marina's estimate and "twenty-two of the accounts order in any given summer week" is a rate over a period; both are `§3.5`-shaped contested numbers. What the book is made of falls out of `account_kind` without being stated |
| `§1.2` | `annotations.valid_from: '2026-06-15T00:00:00Z'`. **Left:** why Marina picked a Monday |
| `§1.3` kitchen, Cotham, Gloucester Road, Moving, Offsite | `InternalLocation` |
| `§1.3` Outside — where stock comes from | `Supplier is_a Location` |
| `§1.3` Outside — where stock goes | `WholesaleAccount is_a Location` for the account row; plain `Location` for the other nine — the walk-in customer, staff, comps, donations, tastings, Marina's house and the three bins |
| `§1.4` all three lists | `Flavour` — name, runs, listing, note |
| `§1.5` The units | `Unit` — name and meaning |
| `§1.5` Ordered / counted / worked | `item_ordered_in`, `item_counted_in`, `item_worked_in`, all ranging `Unit`, plus `item_note` for that table's Note column |
| `§1.5` The same thing counted two ways | **Mostly left.** The milk bullet is why two items are written apart; the tin bullet is why a count is in tins. The other seven — a pan, a batch, a tray, a case, a scoop, a 500 ml tub, and the two readings of a bag — are either session 2 and 3 material or the conversion gap below |
| `§1.6` table | `BoughtItem` — 8 slots for the table's 5 columns plus `§1.5`'s three |
| `§1.6` Prices that have moved | **Left.** Four dated prices and one price with no list at all. They are facts with a valid time, which is exactly what the two clocks are for, and this draft holds no facts |
| `§1.7` table | `SoldProduct` for the Product and Format columns, `ProductPrice` for the three price columns |
| `§1.7` How the prices work | **Left in full.** Eight bullets, and every one of them is a rule — a pan is one price whatever is in it, wholesale is one price for all 31 accounts, the catering tub goes to two restaurants and nowhere else. `§3.4` is session 3 and 4's, and modelling these here would be reaching forward |
| `§1.8` | `Supplier` — six slots for the table's six columns after the name |
| `§1.9` | `WholesaleAccount` — three slots for the table's three columns after the name |

Nothing was modelled that needed a later session to make sense of it. Two
things were reached for and put back: a direction on a movement, which needs
`§3.2`, and which format goes to which account, which needs `§1.7`'s prose read
as a rule.

### Counts

- **11 classes** — `Business`, `Location`, `InternalLocation`, `Supplier`,
  `WholesaleAccount`, `Person`, `Unit`, `Flavour`, `BoughtItem`, `SoldProduct`,
  `ProductPrice`. Three of them are `is_a Location`; that is the whole
  hierarchy, one level deep, per the 29 Aug flatness line.
- **38 slots**, every one carrying an explicit `slot_uri` under the `sorella:`
  prefix.
- **6 relationships** — `location_within` → `InternalLocation`
  (self-referential), `item_counted_in`, `item_ordered_in`, `item_worked_in` →
  `Unit`, `item_supplier` → `Supplier`, `price_product` → `SoldProduct`.
- **2 slots carry a fixed unit** — `item_pack_price` and `price_amount`, both
  `symbol: GBP`. Every other quantity's unit varies per item and is a
  `value_ref` to `Unit`, which is the 30 Aug split applied without a decision
  being needed.
- **Identifiers: 10 of 11 classes have one.** `business_legal_name`,
  `location_name` (inherited by all three subclasses), `person_name`,
  `unit_name`, `flavour_name`, `item_name`, `product_name`. `ProductPrice` has
  none — see the note on `unique_keys` below.
- `entity_class` with `designates_type: true` is induced on all 11.

### The mermaid render

`gen-mermaid-class-diagram` writes one Markdown file per class, not one
picture. All eleven, with the `click` lines and blank lines stripped:

```mermaid
 classDiagram
    class Business
      Business : business_legal_name
      Business : business_registered_in
      Business : business_trading_name
      Business : business_trading_since
      Business : entity_class
```
```mermaid
 classDiagram
    class Location
      Location <|-- InternalLocation
      Location <|-- Supplier
      Location <|-- WholesaleAccount
      Location : entity_class
      Location : location_description
      Location : location_name
```
```mermaid
 classDiagram
    class InternalLocation
      Location <|-- InternalLocation
      InternalLocation : entity_class
      InternalLocation : location_description
      InternalLocation : location_name
      InternalLocation : location_temperature
      InternalLocation : location_within
        InternalLocation --> "0..1" InternalLocation : location_within
```
```mermaid
 classDiagram
    class Supplier
      Location <|-- Supplier
      Supplier : credit_terms
      Supplier : entity_class
      Supplier : location_description
      Supplier : location_name
      Supplier : outside_where
      Supplier : supplier_brings
      Supplier : supplier_lead_time
      Supplier : supplier_minimum_order
      Supplier : supplier_rhythm
```
```mermaid
 classDiagram
    class WholesaleAccount
      Location <|-- WholesaleAccount
      WholesaleAccount : account_kind
      WholesaleAccount : credit_terms
      WholesaleAccount : entity_class
      WholesaleAccount : location_description
      WholesaleAccount : location_name
      WholesaleAccount : outside_where
```
```mermaid
 classDiagram
    class Person
      Person : entity_class
      Person : person_name
      Person : person_responsible_for
      Person : person_role
```
```mermaid
 classDiagram
    class Unit
      Unit : entity_class
      Unit : unit_meaning
      Unit : unit_name
```
```mermaid
 classDiagram
    class Flavour
      Flavour : entity_class
      Flavour : flavour_listing
      Flavour : flavour_name
      Flavour : flavour_note
      Flavour : flavour_runs
```
```mermaid
 classDiagram
    class BoughtItem
      BoughtItem : entity_class
      BoughtItem : item_arrives_as
      BoughtItem : item_counted_in
        BoughtItem --> "0..1" Unit : item_counted_in
      BoughtItem : item_name
      BoughtItem : item_note
      BoughtItem : item_ordered_in
        BoughtItem --> "0..1" Unit : item_ordered_in
      BoughtItem : item_pack_price
      BoughtItem : item_supplier
        BoughtItem --> "0..1" Supplier : item_supplier
      BoughtItem : item_worked_in
        BoughtItem --> "0..1" Unit : item_worked_in
```
```mermaid
 classDiagram
    class SoldProduct
      SoldProduct : entity_class
      SoldProduct : product_format
      SoldProduct : product_name
```
```mermaid
 classDiagram
    class ProductPrice
      ProductPrice : entity_class
      ProductPrice : price_amount
      ProductPrice : price_at
      ProductPrice : price_product
        ProductPrice --> "0..1" SoldProduct : price_product
```

### What was run

| Command | Exit |
|---|---|
| `PYTHONIOENCODING=utf-8 gen-owl --no-use-native-uris business/sorella/draft.yaml > build/sorella_draft.ttl` | 0 — 38,655 bytes |
| `PYTHONIOENCODING=utf-8 gen-mermaid-class-diagram -d build/sorella_mmd business/sorella/draft.yaml` | 0 — 11 files |
| `grep -n any_of business/sorella/draft.yaml` | 1 — no match |
| `grep -n facts business/sorella/draft.yaml` | 1 — no match |
| `make check` | 0 — **64 tests passed**, replay byte-identical twice |
| `git diff --stat ada1d9e -- business/sorella/profile.md` | 0 — empty, the profile is untouched |
| `git status --porcelain` | `?? business/sorella/draft.yaml` and the pre-existing ` M NEXT.md`. Nothing under `business/` outside `business/sorella/` added, moved or deleted |
| `SchemaView` introspection of the draft | 11 classes, 38 slots, 0 slots without a `slot_uri`, 0 `any_of` |
| enum probe (T1, below): `gen-owl` and `gen-mermaid-class-diagram` over a scratchpad copy | 0 and 0 |

`make check` collected 64 and passed 64. The 64 that existed still pass and no
test was added — this session writes no code.

### Surprising

1. **`§1.8` and `§1.9` stopped being tables the moment suppliers and accounts
   became `Location` subclasses.** They are not two more masters; they are more
   columns on rows `§1.3` had already listed. The nine suppliers appear twice in
   the profile and exactly once in the map, and there is no `supplier_name`
   slot at all — a `Supplier` is identified by `location_name`, because LinkML
   refuses a second identifier on a subclass. A modelling question turned into
   something the tool decides, and it decides it the right way.
2. **The `Unit` trap cannot arise from `§1.5`.** All 24 units in `§1.5` are
   things stock is counted, ordered or worked in. Not one is a day, a week or a
   percent. v1's defect — a dropdown offering "week" for litres — was not
   `§1.5` being too wide; it was `§10`'s thresholds being poured into the same
   class afterwards. So the split decided here is not a division of `§1.5`, it
   is a fence around it, and session 4 has to put a threshold's unit somewhere
   else or state why not.
3. **Two of the things `§1.1` calls premises are already `§1.3` rows.**
   The van and the container sit in `§1.3`'s Moving and Offsite tables, so a
   `Site` class would have made two of its instances two things at once. That,
   and the fact that a Site carrying only a name and a description renders the
   same form as a plain `Location`, is what killed it — the 1 Sep rule reached
   the same answer as the profile's own filing.
4. **`gen-mermaid-class-diagram` is eleven pictures, not one.** `-d` is
   required, there is no whole-schema render, and each file shows one class with
   its immediate neighbours. It is a findability view, which the 27 Aug
   readability line cares about — but nothing produced here shows the shape of
   the map as a whole. The 29 Aug line naming three viewers for three jobs is
   short one job.
5. **`gen-owl` writes zero `rdfs:domain` on this map too.** 0 occurrences in
   38,655 bytes. Second map, same result, which settles that the 30 Aug OPEN
   line is a property of the generator and not of v1.
6. **The `PYTHONIOENCODING` trap did not fire, and could not have.** `gen-owl`
   died on v1 because `§8`'s temperatures carry U+2212 and the *facts* copied
   them. This draft holds no facts and no temperature, so its only non-ASCII
   would have been in a description. The variable was set as instructed; the
   measured danger lives one session away, in whichever session writes the
   location facts.

### Two things left out of the draft on purpose

- **`unique_keys`.** The session brief lists the permitted vocabulary as
  "classes, slots, ranges, `is_a`, identifiers, units", and `unique_keys` is not
  in it, so none was written. `ProductPrice` is the one class that wants one —
  a price is identified by its product and its column and by no single slot,
  which is exactly the composite the 30 Aug line made `unique_keys` for. As it
  stands two prices for one product in one column do not compete. Reported
  rather than fixed: widening the session's vocabulary is a `NEXT.md` change.
- **`annotations.transcript`.** `seal` requires it and requires the file it
  names to exist, and the done condition says `draft.yaml` must be the only file
  added. So the draft carries `valid_from` and nothing else, and the seal after
  session 4 will refuse it until a provenance note is written beside it. Not a
  conflict inside this session's done condition — a dependency the sealing
  session inherits.

No two clauses of the done condition conflicted.

### T1, tried rather than argued: does an enum range survive?

Three slots carry a closed vocabulary the profile states in full —
`flavour_listing` (three lists), `account_kind` (seven kinds), `price_at` (three
columns) — and all three are `range: string`, because an enum is outside this
session's stated vocabulary. Whether that costs anything was worth ten minutes.

A scratchpad copy of the draft with `flavour_listing` ranged over a
`FlavourListing` enum: `gen-owl` exits 0 and writes 14 `FlavourListing` triples;
`gen-mermaid-class-diagram` exits 0; `induced_slot('flavour_listing').range` is
`'FlavourListing'`, which is **not** in `all_classes()` and **is** in
`all_enums()` — so `seal`'s class test sees a non-class and the value lands in
`value_literal`, which is correct and is what `seal`'s own docstring already
says. One defect found: mermaid draws the enum as an association to a
`FlavourListing` node and emits `click FlavourListing href "../FlavourListing"`,
and no `FlavourListing.md` is written, so the review render carries a dead link
per enum. Nothing else broke. Session 2 can use enums with that known.

### Proposed `DECISIONS.md` entries

1. `Unit` is the unit stock is counted, ordered or worked in, and nothing else.
   All 24 units in `§1.5` are quantity or packaging words and not one of them is
   a duration or a percentage; v1's dropdown offering "week" for litres came
   from `§10`'s thresholds being added to the same class after the fact, not
   from the units section being too wide. A threshold's own unit is either
   slot-level `unit` metadata under the 30 Aug line or a class session 4
   declares — and if it is a class, it is not this one.
2. `§1.7`'s three price columns become a `ProductPrice` class carrying the
   column as a value, not three slots named after the columns. A slot named
   `product_price_cotham_hill` puts an individual into the vocabulary, so
   opening a third shop would need a new map version for what is a new row —
   the writer joint the 1 Sep master-data line closed, reopened by a naming
   habit. The cost is named rather than absorbed: `price_at` is a string, so the
   three columns are labels rather than places, and nothing stops a fourth
   spelling.
3. A supplier and a wholesale account are `is_a Location`, not classes that
   reference one. They inherit `location_name` as their identifier, so the nine
   suppliers `§1.3` lists and the nine `§1.8` lists cannot become two sets of
   rows — and LinkML refuses a second identifier on a subclass, so the map is
   unable to drift into having one. This is the 1 Sep "the outside is
   locations" line carried into structure rather than only into movements.
4. `§1.1`'s premises are `InternalLocation` rows and `location_within` is
   self-referential, rather than a `Site` class. Two of the things `§1.1` calls
   premises — the van and the container — are already rows in `§1.3`, so a Site
   class would have made them two things at once; and a Site carrying a name and
   a description alone renders the same form as a plain `Location`, which the
   1 Sep rule says is one class with a field.
5. `entity_class`, `designates_type: true`, is on every class in the map from
   session one. The 2 Sep line admitted the feature and Claim C is the oldest
   failure in the list; declaring it now costs one slot and means no class in
   this map is ever born without a way for the log to say what its rows are.

### Proposed `OPEN.md` lines

- `[T3]` `price_at` is a string naming one of `§1.7`'s three price columns, and
  two of the three are shops that are also `InternalLocation` rows while the
  third, wholesale, is not a place at all and never can be — the price is one
  figure for all 31 accounts. So a price cannot be joined to where it was
  charged except by matching a label. Whether a price point is a location, a
  class of its own, or a label that stays a label is undecided, and it is the
  same shape as v1's folded pan-slot names one level out. Raised 3 Sep ·
  blocks: generation
- `[T3]` The map holds three units for a bought item and nothing that converts
  between them. `§1.5` gives ordered, counted and worked units for 22 items and
  `§1.6` gives the pack as one phrase, with the packs nesting two deep — a case
  of six tubs of one kilogram, a carton of ten bags of two. The only factor
  stated anywhere is Dan's 10.3 kg per bag, and `§1.5` says he weighs anyway. So
  a count in bags cannot reach a balance in grams by anything in the map.
  Whether the business is asked for factors, or the map decomposes a pack, or
  the conversion stays absent and a balance is only ever computable in the
  counted unit, is undecided. Raised 3 Sep · blocks: derive
- `[T3]` `location_within` is self-referential and nothing bounds it. LinkML
  states no acyclicity, the kernel states none, and a generated form's picker
  will offer every `InternalLocation` including the one being edited — so a
  shop can be put inside its own cabinet and every reader that walks the chain
  hangs. Whether a cycle is a violation the way negative stock is, a refusal the
  form makes, or a shape nobody will ever produce, is undecided. Raised 3 Sep ·
  blocks: generation
- `[T3]` A flavour's season is prose the business restates each year.
  `flavour_runs` holds "September to October", "June to July", "No season" and
  "On the cabinet plan all year, made perhaps monthly", which is what `§1.4`
  writes and what a cabinet plan is read off. Nothing turns it into dates, so
  "which flavours should be on in July" is not a query, and the three
  no-season flavours have a cabinet card and may not have been made for six
  weeks. Whether a season is a pair of dates, a recurring rule, or prose a
  person reads, is undecided. Raised 3 Sep · blocks: generation

## 2026-09-03 — Sorella's map, session 2 of 4: how a product gets made

`business/sorella/draft.yaml`, extended. Sections `§2.1` to `§2.7` of the
profile frozen at `ada1d9e`, read as vocabulary and nothing else. **Still no
fact in this file.** The twenty-one batch sheets, their ingredient lines, the
six runs, the fourteen packaging bills and the eight drinks are rows a
generated form will write.

### How a recipe's many ingredients are held, and what that costs

The 31 Aug line left three options and two were already shut, so this is
elimination and not preference: **a collection gets its own subject.** `Recipe`
is the page — a heading, a basis, and a note — and `RecipeLine` is one line
under it with its own identity, carrying `line_recipe`, `line_ingredient`,
`line_quantity`, `line_unit` and `line_stage`. Nothing is multivalued anywhere
in the map; every assertion stays one subject, one predicate, one value, and
supersession still works on that pair, because superseding pistachio's paste
weight touches one line and not the page. That is the same shape a bill of
materials has always had, and the price of it is paid in four places. **First,
a line has no name.** It is identified by nothing, like `ProductPrice`, so the
form that writes one has to mint a URI and a user cannot refer to a line except
through its page and its ingredient — and it cannot even have a `unique_keys`
of those two, because salted caramel puts the same variegate on the page twice
at two stages and the cake puts two lines on the page with no ingredient at all.
**Second, a page and its lines are two forms**, so entering the pistachio sheet
is one submission for the page and three more for the lines, where the profile
shows it as one table. **Third, nothing holds the page together**: a page whose
lines were half entered is a page, and no count anywhere says how many lines it
should have. **Fourth, walking a recipe is two hops rather than one** — from a
flavour to its page and from the page to its lines — and every reader that
totals a batch pays that twice over, because white base is itself a page.
Against those four: it holds, it needed nothing added to the kernel, and it is
the only one of the three options that was ever available.

### Every subsection, consumed or left

| Subsection | Where it went |
|---|---|
| `§2.1` The flow | **Left in full.** The six steps — weigh and pasteurise, age, flavour and churn, fill, blast, hold — are stock moving between `§1.3`'s places, and `§3.2` is called "every way stock moves". Modelling them here is reaching into session 3 |
| `§2.1` The two machines | **Left as a class, and it needs none.** Machine 1 and machine 2 are places a thing can be inside the kitchen and `InternalLocation` already holds them; that `§1.3` does not list them is a gap in the profile, not in the map. Their 12 kg reaches the map as `recipe_basis_quantity` on every batch sheet. What has nowhere to go is "machine 2 comes out drier", which is a rate over batches |
| `§2.1` The one thing a recipe calls for that nobody buys | `Ingredient`, the plain case. Water is a row: named on four pages, off the mains, not bought and not made |
| `§2.2` all six runs | `Ingredient` rows carrying `made_recipe`; the tables are `Recipe` + `RecipeLine`; the prose under each table is `recipe_note` |
| `§2.2` the stabiliser under two names | `line_named_as` — the words the page uses, kept beside the resolved ingredient rather than instead of it |
| `§2.3` made on white base / on water / on a run of its own / on syrup | `Recipe` + `RecipeLine`. The at-fill half is `line_stage: at_fill` |
| `§2.3` gianduja | A second `Recipe`, and `made_recipe` on the hazelnut `Flavour` moves between the two pages on the valid-time clock. This is the best thing in the session and it cost nothing |
| `§2.3` the three with no page | `RecipeLine` with an ingredient, no `line_quantity`, and a `line_note`. The map has the shape; whether Dan's book ever carries such a line is a fact |
| `§2.3` the cake | `Recipe` + `RecipeLine`, with two lines that carry an amount and **no ingredient** — 1.4 L of one flavour and 1.1 L of a second, read out on the phone per cake |
| `§2.3` What no page accounts for | **Left on purpose.** Sanitiser, CIP detergent, blue roll, gloves, bin liners, dry ice and the water are bought, used, and associated with a batch by nobody. Giving them a line would state a link the business does not make |
| `§2.4` the table | `SoldProduct` — `product_filled_to`, `product_fill_quantity`, `product_fill_unit`, `product_expected_per_batch` |
| `§2.4` Yield | **Left.** 15.5–17 L off a 12 kg mix depending on overrun that nobody logs. A range, and a comparison |
| `§2.4` The scoop | **Left, and the hole is visible.** `product_fill_quantity` exists on the scoop rows and is empty, because nobody has ever weighed one |
| `§2.4` What is expected and what is recorded | **Left.** A comparison, and the brief puts comparisons in session 4 |
| `§2.5` | `SoldProduct` — `product_which_flavours` and `product_flavour_decided_by`, both prose |
| `§2.6` the table | Fourteen `Recipe` rows with their lines. `product_recipe` joins the ones that match a price-list line |
| `§2.6` The pan | **Left.** Whether a pan at a café is stock, a loan or nobody's is `§3.2`'s, and it is already an OPEN line |
| `§2.6` The label, The tubs and the lids | `RecipeLine` — one blank label, one tub, one printed lid, one printed sleeve. The prose about roll counts and case sizes is `§1.5`'s and is already in the map |
| `§2.7` the table | Eight `Recipe` rows; `product_recipe` on `SoldProduct` joins them one for one |
| `§2.7` the pump, the jug, the 2 L bottle | **Left.** "A 2 L bottle does eight lattes" against Aoife saying she goes through more, and milk poured against milk steamed, are a loss rate over a period |

Two things were reached for and put back: a `Machine` class, and a join table
between `Flavour` and format for `§2.5` — `§2.5` never writes the pairs out,
only sentences, so enumerating them would have invented twenty-five by seven
facts nobody has stated.

### Counts

- **3 classes added** — `Ingredient`, `Recipe`, `RecipeLine`. **14 in total.**
- **20 slots added.** **58 in total**, every one carrying an explicit
  `slot_uri`. Session 1's 38 are all still present; none was renamed and none
  was re-ranged.
- **7 relationship slots added** — `made_recipe` → `Recipe` (on `Ingredient`
  and on `Flavour`), `recipe_basis_unit` → `Unit`, `line_recipe` → `Recipe`,
  `line_ingredient` → `Ingredient`, `line_unit` → `Unit`, `product_recipe` →
  `Recipe`, `product_fill_unit` → `Unit`. **13 in total.**
- **1 `is_a` edge added** — `BoughtItem is_a Ingredient`. The hierarchy is now
  four subclasses under two parents and is **still one level deep**.
- **1 enum added** — `RecipeStage`, two permissible values.
- **1 `unique_keys` added** — `ProductPrice`, on `price_product` + `price_at`.
- **0 identifiers added net**: `Recipe` has one (`recipe_name`), `RecipeLine`
  and `ProductPrice` have none, `Ingredient` uses `item_name`, and `BoughtItem`
  inherits it rather than declaring a second — the same LinkML refusal that
  made a `Supplier` be identified by `location_name` in session 1.

### What session 1 had to give up

Nothing was renamed and nothing was re-ranged. Four slots were **re-homed** —
moved from `BoughtItem` up to the new `Ingredient` — and three descriptions
were widened to match:

| Slot | What changed | Why |
|---|---|---|
| `item_name` | `BoughtItem` → `Ingredient`; description widened | A recipe line names bought things, made things and water with one slot, and the 30 Aug line says a shared range gets a common superclass. `item_name` is `Ingredient`'s identifier and `BoughtItem` inherits it |
| `item_counted_in` | `BoughtItem` → `Ingredient`; description widened | A made thing is counted too — aged base in 25 L buckets, and `§2.2` says nobody has ever counted it |
| `item_worked_in` | `BoughtItem` → `Ingredient` | Same reason; a page works in grams whatever the thing was bought in |
| `item_note` | `BoughtItem` → `Ingredient`; description widened | Water's note is that it comes off the mains and is not tracked against product, which is the same slot doing the same job |

`BoughtItem` still induces all nine of the slots it had in session 1 — checked
with `class_induced_slots`, not by reading. `Flavour` gained `made_recipe`,
`SoldProduct` gained seven, `ProductPrice` gained its `unique_keys`, and the
schema `description` was rewritten to name both sessions.

### The mermaid render, added and changed classes only

Six of the fourteen files differ from session 1's. `ProductPrice.md` is byte
for byte what session 1 pasted even though the class changed, because mermaid
does not draw a `unique_keys`; it is not repeated here.

```mermaid
 classDiagram
    class Ingredient
      Ingredient <|-- BoughtItem
      Ingredient : entity_class
      Ingredient : item_counted_in
        Ingredient --> "0..1" Unit : item_counted_in
      Ingredient : item_name
      Ingredient : item_note
      Ingredient : item_worked_in
        Ingredient --> "0..1" Unit : item_worked_in
      Ingredient : made_recipe
        Ingredient --> "0..1" Recipe : made_recipe
```
```mermaid
 classDiagram
    class BoughtItem
      Ingredient <|-- BoughtItem
      BoughtItem : entity_class
      BoughtItem : item_arrives_as
      BoughtItem : item_counted_in
        BoughtItem --> "0..1" Unit : item_counted_in
      BoughtItem : item_name
      BoughtItem : item_note
      BoughtItem : item_ordered_in
        BoughtItem --> "0..1" Unit : item_ordered_in
      BoughtItem : item_pack_price
      BoughtItem : item_supplier
        BoughtItem --> "0..1" Supplier : item_supplier
      BoughtItem : item_worked_in
        BoughtItem --> "0..1" Unit : item_worked_in
      BoughtItem : made_recipe
        BoughtItem --> "0..1" Recipe : made_recipe
```
```mermaid
 classDiagram
    class Recipe
      Recipe : entity_class
      Recipe : recipe_basis
      Recipe : recipe_basis_quantity
      Recipe : recipe_basis_unit
        Recipe --> "0..1" Unit : recipe_basis_unit
      Recipe : recipe_name
      Recipe : recipe_note
```
```mermaid
 classDiagram
    class RecipeLine
      RecipeLine : entity_class
      RecipeLine : line_ingredient
        RecipeLine --> "0..1" Ingredient : line_ingredient
      RecipeLine : line_named_as
      RecipeLine : line_note
      RecipeLine : line_quantity
      RecipeLine : line_recipe
        RecipeLine --> "0..1" Recipe : line_recipe
      RecipeLine : line_stage
        RecipeLine --> "0..1" RecipeStage : line_stage
      RecipeLine : line_unit
        RecipeLine --> "0..1" Unit : line_unit
```
```mermaid
 classDiagram
    class Flavour
      Flavour : entity_class
      Flavour : flavour_listing
      Flavour : flavour_name
      Flavour : flavour_note
      Flavour : flavour_runs
      Flavour : made_recipe
        Flavour --> "0..1" Recipe : made_recipe
```
```mermaid
 classDiagram
    class SoldProduct
      SoldProduct : entity_class
      SoldProduct : product_expected_per_batch
      SoldProduct : product_fill_quantity
      SoldProduct : product_fill_unit
        SoldProduct --> "0..1" Unit : product_fill_unit
      SoldProduct : product_filled_to
      SoldProduct : product_flavour_decided_by
      SoldProduct : product_format
      SoldProduct : product_name
      SoldProduct : product_recipe
        SoldProduct --> "0..1" Recipe : product_recipe
      SoldProduct : product_which_flavours
```

`RecipeLine.md` carries `click RecipeStage href "../RecipeStage"` and no
`RecipeStage.md` is written — fourteen files for fourteen classes. That is
session 1's measured enum cost arriving exactly as predicted, one dead link.

### The nine measured problems: where the map has somewhere to put each

| Problem | Somewhere to put it? |
|---|---|
| A batch's inputs exceed the batch | **Yes.** `recipe_basis` states the page is per mix in, and `line_stage: at_fill` marks the 0.85 chocolate, the 0.40 caramel, the 1.10 biscuit base and the 1.60 rhubarb as on top of the 12 kg. A place, not an answer: a page's lines deliberately do not sum to its basis, so whatever totals a batch has to know that, and nothing in the map tells it |
| Three flavours with a recipe and no quantities | **Yes.** A line with an ingredient, an empty `line_quantity` and a `line_note`. Whether the business would ever write such a line is a T2 |
| Water named in four recipes and not bought | **Yes, completely.** A plain `Ingredient` row. The bill of materials has no dangling line: it has a line pointing at a thing that is neither bought nor made, which is what water is |
| A pan holds about 3.3 kg and no document carries it | **Half.** `product_fill_quantity` holds the 3.3 and `product_filled_to` holds the sentence it came out of. Nothing converts "½ pan" or "¾ pan", which is what every count and every van sheet is written in, and nothing in `§2` states a factor for a fraction read by eye |
| No quantity says whether it is gross or net | **No, and deliberately not.** The business draws no such distinction anywhere, so a slot for it would be a distinction the map invented. `line_quantity`'s description records that the pan's 3.6 kg and 3.3 kg differ by the pan and that nothing recorded which was meant |
| A scoop has no weight | **The column, not the number.** `product_fill_quantity` sits on the scoop rows and is empty. This is the one place where the map being right makes the gap more visible rather than less |
| Passionfruit purée with no flavour made of it | **No.** It runs on the fruit sorbet page and only a `Flavour` or an `Ingredient` can point at a page, and passionfruit is neither. So the page exists, the purée exists, and nothing joins them. An unused material still looks exactly like a correct one |
| `§1.6`'s consumers must be declared, not derived | **Mostly yes, and further than expected.** The 30 that resolve to a recipe table are `RecipeLine`s, and `line_named_as` carries the alias so the page can go on saying "stabiliser base". `§2.6` and `§2.7` turn out to give lines to most of the other 50 as well — the napkin, the tasting spoon, the milk behind a latte are all rows in a table. What is left with no consumer is `§2.3`'s own list: sanitiser, CIP detergent, blue roll, gloves, bin liners and dry ice, which the profile says nobody associates with a batch |
| Three units for a bought item and nothing converts | **No, and this session sharpens it.** `line_unit` is grams on almost every page while `item_counted_in` is bags, sacks and tins, so a page and a count now name two different units for the same thing inside one map, and the only factor anywhere is Dan's 10.3 kg per bag. Unchanged from session 1's OPEN line except that it is now load-bearing rather than latent |

### Surprising

1. **Gianduja is the two clocks paying for themselves in a map with no facts
   in it.** `made_recipe` is single-valued, and from November to February the
   hazelnut cabinet card is made on a different page — chocolate in, no salt —
   while the production sheet says "hazelnut" either way. A system with one
   clock has to choose between a second flavour nobody sells and a page that
   lies for four months. Here it is one slot whose value changes on the
   valid-time axis, and the map needed nothing added for it. This was not
   designed; it fell out of pointing `made_recipe` from the made thing to the
   page instead of the other way round.
2. **Which way the recipe pointer faces was decided by the business, not by
   modelling taste.** The obvious shape is a page that names its output. It is
   wrong here, and the fruit sorbet page proves it: one page serves strawberry,
   raspberry, mango, the peach half of peach and basil, and a passionfruit that
   is not in the range at all, because Dan writes the fruit in the margin. A
   page does not know what it makes. Turning the arrow round made every pointer
   in `§2` single-valued at once — `made_recipe`, `product_recipe` — and that
   was the moment the multivalued question stopped being hard.
3. **The cake settled whether a `Flavour` is an `Ingredient`, and the answer is
   no.** Two hours could have gone into whether the cabinet-card entry and the
   substance in the pan are one class. The cake ends it in one sentence: its
   lines are "1.4 L of one flavour" and "1.1 L of a second", and which two is
   read out on the phone per cake. So even with `Flavour is_a Ingredient` the
   line could not have named one. A line with an amount and no ingredient is
   the only honest shape, and `Flavour` keeps `flavour_name`.
4. **`§2.6` is not a bill of materials for `§1.7`'s product list, and it cannot
   be made into one.** Five of its rows are formats and eight are drinks or
   cans that match a price line one for one. The rest are conditions across
   several lines — any scoop sale, tub or cake taken away, any drink taken
   away — and worse, a scoop's own bill depends on cone or cup, which `§1.7`
   prices as one product either way. So the till knows something the price list
   does not carry, and the map can hold both tables and not the join.
5. **`unique_keys` survives `gen-owl` as `owl:hasKey` and is invisible to
   mermaid.** One line, `owl:hasKey ( sorella:price_product sorella:price_at )`,
   in 63,986 bytes. `ProductPrice.md` renders identically to session 1's. So the
   review render cannot show a composite key at all, which matters because
   `ProductPrice` and `RecipeLine` are the two classes in this map with no
   identifier and a reviewer looking at pictures cannot tell them apart.
6. **The enum's OWL is a `owl:unionOf` of two `owl:Class` nodes, not a
   datatype.** Eleven `RecipeStage` triples, and `line_stage`'s range renders as
   a union of `RecipeStage#in_the_mix` and `RecipeStage#at_fill`. Session 1
   measured that `induced_slot` puts the enum outside `all_classes()` and
   confirmed it again here; what is new is that the OWL disagrees with that and
   calls both values classes. Nothing reads the OWL, so nothing breaks, but a
   reviewer in WebVOWL will see two nodes where the map has two words.
7. **The `PYTHONIOENCODING` trap did not fire again, and this is the last
   session where it could not have.** The draft still holds no facts and no
   temperatures. `§2` carries −35 °C and −18 °C in its prose and none of it
   reached a description; the exposure moves to whichever session writes
   location facts, unchanged.

### What was run

| Command | Exit |
|---|---|
| `PYTHONIOENCODING=utf-8 gen-owl --no-use-native-uris business/sorella/draft.yaml > build/sorella_draft.ttl` | 0 — 63,986 bytes, 0 `rdfs:domain`, 1 `owl:hasKey`, 11 `RecipeStage` triples |
| `PYTHONIOENCODING=utf-8 gen-mermaid-class-diagram -d "$TEMP/sorella_mmd2" business/sorella/draft.yaml` | 0 — 14 files, one per class, none for the enum |
| `grep -c any_of business/sorella/draft.yaml` | 1 on the first run — the word was in `Ingredient`'s own description explaining why it exists. Reworded to "a boolean range constraint"; **0, exit 1** after |
| `grep -c facts business/sorella/draft.yaml` | 1 — no match. No `annotations.facts` block |
| `make check` | 0 — **64 tests passed**, replay byte-identical twice, 5,334 bytes both times |
| `SchemaView` introspection | 14 classes, 58 slots, 1 enum, 13 relationship slots, 0 slots without a `slot_uri`, 0 `any_of` |
| `SchemaView` diff against `a06de07` | 0 of session 1's 38 slots missing, 0 of its 11 classes missing, 20 slots and 3 classes added |
| `class_induced_slots('BoughtItem')` | all 9 of session 1's `BoughtItem` slots still induced, plus `made_recipe` |
| `git diff --stat HEAD -- business/sorella/profile.md` | 0 — empty. The profile is untouched |
| `git status --porcelain` | ` M business/sorella/draft.yaml` and the pre-existing ` M DECISIONS.md`, ` M NEXT.md`. Nothing under `business/` outside `business/sorella/` added, moved or deleted |

`make check` collected 64 and passed 64. This session writes no code and adds
no test.

One clause needed reading twice rather than conflicting. The done condition
says `business/sorella/profile.md` is unchanged; it differs from `ada1d9e` by
one line, which `6ae7579` wrote to replace `PENDING` with the freeze commit's
own hash before this session began. Against `HEAD` the diff is empty, which is
what the clause means. No two clauses conflicted.

### Proposed `DECISIONS.md` entries

1. A recipe's many ingredients are held as a collection with its own subject:
   `Recipe` is the page and `RecipeLine` is one line carrying its ingredient,
   its quantity and its stage. The 31 Aug multivalued question is closed by
   elimination — the kernel is closed so the (subject, predicate) pair cannot
   stop being the unit of supersession, and refusing multivalued slots means
   refusing recipes. Nothing in the map is multivalued and nothing was added to
   the kernel. The four costs are named rather than absorbed: a line has no
   name and cannot have a `unique_keys` either, because salted caramel puts one
   variegate on one page twice; a page and its lines are two forms where the
   profile shows one table; nothing says how many lines a page should have; and
   walking a recipe is two hops, paid twice over because white base is itself a
   page.
2. A page is not an output, and what is made names its page rather than the
   reverse. The obvious shape — a recipe that names what it produces — is wrong
   for this business and `§2.3` says why: the fruit sorbet page serves
   strawberry, raspberry, mango, the peach half of peach and basil, and a
   passionfruit that is not in the range, because Dan writes the fruit in the
   margin and leaves the page alone. So `made_recipe` sits on `Ingredient` and
   on `Flavour` and `product_recipe` on `SoldProduct`, and every one of them is
   single-valued. The return was not foreseen: the hazelnut card is made on the
   gianduja page from November to February and on the hazelnut page the rest of
   the year, and that is one slot moving on the valid-time axis rather than a
   second flavour nobody sells.
3. `Ingredient` is the common superclass of everything a recipe line can name,
   and its plain case is water. `BoughtItem is_a Ingredient`, and `item_name`,
   `item_counted_in`, `item_worked_in` and `item_note` move up to the parent.
   This is the 30 Aug line applied — a slot whose range must cover two classes
   gets a common superclass rather than a boolean constraint — and it means the
   bill of materials has no dangling line: water is a row, not an absence.
   `Flavour` is deliberately **not** an `Ingredient`, and the cake settles it
   rather than an argument: its lines are 1.4 L of one flavour and 1.1 L of a
   second, chosen on the phone per cake, so no line could have named a flavour
   even if the class allowed it.
4. `line_stage` is an enum with two values, `in_the_mix` and `at_fill`, and it
   is where the at-fill half of a batch attaches. `§2.3` draws the line itself
   and states why — a page is per 12.00 kg into the batch freezer, and anything
   folded, drizzled or rippled in by hand goes in after the machine and is on
   top of it. The consequence has to be stated with the mechanism: **a page's
   lines do not sum to its basis, by design**, so anything that totals a batch
   must add the at-fill lines to the basis rather than expect them inside it,
   and nothing in the map enforces that. The map has a place for the problem;
   it does not make consumption balance.
5. The map carries no gross-or-net basis for a quantity, and that is a refusal
   rather than an omission. `§2.4` has a pan reading 3.6 kg on the scale as it
   stood and about 3.3 kg of gelato in it, and no document in the business
   records which was meant — the business draws no such distinction anywhere,
   so a slot for it would be one the map invented, which the 2 Sep profile rule
   forbids in the other direction and which is the same failure. The fact is
   recorded in `line_quantity`'s own description so that a reader of the map
   meets it.
6. `unique_keys` enters the map on `ProductPrice` and nowhere else, because it
   is the only class where a composite key is true. It renders as one
   `owl:hasKey` triple and mermaid does not draw it. `RecipeLine` was the other
   candidate and is refused a key: `(line_recipe, line_ingredient, line_stage)`
   looks right and is false, because the cake carries two lines with no
   ingredient at all.

### Proposed `OPEN.md` lines

- `[T3]` `§2.6`'s packaging bill cannot be joined to `§1.7`'s price list, and
  the map holds both. Five of `§2.6`'s fourteen rows are formats and eight are
  drinks or cans matching a price line one for one, so `product_recipe` reaches
  them; the rest are conditions across several lines — any scoop sale, tub or
  cake taken away, any drink taken away — and a scoop's own bill depends on
  cone or cup, which `§1.7` prices as one product either way. So the till knows
  a thing the price list does not carry, and those pages sit in the map with
  nothing pointing at them. Whether the join is a second class, a rule on the
  form, or a distinction the business has to be asked to make, is undecided.
  Raised 3 Sep · blocks: generation
- `[T3]` A page's lines do not sum to its basis and nothing says so. Every
  batch sheet is per 12.00 kg into the machine and `line_stage: at_fill` marks
  what goes in on top of it, so a reader that totals a page's lines and expects
  12.00 kg is wrong on eight of the twenty-two sheets. The stage is on the line
  and the basis is on the page, and joining them is arithmetic across rows,
  which is the aggregate shape the 1 Sep line puts outside this map. Whether a
  page should state its own output, whether the at-fill total is a derived
  slot, or whether nothing should ever total a page, is undecided. Raised 3 Sep
  · blocks: derive
- `[T3]` Scaling a page to a run is prose arithmetic. The white base page is
  per 10.00 kg of mix and `recipe_note` says it is made in 55 kg runs; the
  biscuit base page is per run and the run is ten packs of digestives while the
  line says 4.00 kg. So the factor between what a page states and what a
  session of work actually consumes lives in a sentence, and `§2.1` adds that a
  55 kg run does four batches and leaves about half a bucket that goes into the
  next morning topped up. Whether a run size is a slot, a fact per run, or
  prose, is undecided. Raised 3 Sep · blocks: derive
- `[T3]` Gelato in a pan is not a thing the map can name. A batch makes gelato
  of a flavour, the gelato fills pans, tubs and minis, and the pans sit in the
  holding freezer for up to 21 days — but the map has `Flavour` for the card
  and `SoldProduct` for the price line and nothing that is "pistachio in a 5 L
  napoli pan". `product_fill_quantity` says a pan holds about 3.3 kg and
  `made_recipe` says how the pistachio was made, and no slot joins them.
  Whether that is a class, a movement's two ends in `§3.2`, or something a
  count declares, is undecided, and milestone one's closing balance runs
  straight through it. Raised 3 Sep · blocks: generation
- `[T2]` Would Dan's book ever carry a line with no quantity? The map allows
  one — an ingredient, no number, a note — because `§2.3` says three flavours
  are made by feel and gives Dan's own answers: honey until it tastes right, a
  good glug of marsala, most of a 100 g pack of basil that he smells and
  decides about. He says he will not write a quantity for the basil. Whether he
  would write the line at all, or whether an unwritten page is simply absent,
  is a thing only he can say, and the two produce different consumption.
  Raised 3 Sep · blocks: interview
- `[T2]` What one filled 500 ml tub takes is two answers in the profile and the
  map holds them apart. `§2.4` says about 460 g of gelato and `§2.6` says one
  tub, one printed lid, one printed sleeve; the packaging is a `Recipe` and the
  gelato is `product_fill_quantity`, because which flavour goes in is decided
  at the bench and cannot be a line. Whether the business thinks of a filled
  tub as one bill or as two things that happen at the same moment decides
  whether a filling form asks one question or two. Raised 3 Sep ·
  blocks: interview

## 2026-09-03 — Sorella's map, session 3 of 4: every way stock moves, and the eighteen documents

`business/sorella/draft.yaml`, extended. Sections `§3.2` and `§3.3` of the
profile frozen at `ada1d9e`. **Still no fact in this file.** The fifty-three
ways stock moves, the batches, the counts and the movements themselves are rows
a generated form will write.

### What a movement's quantity is of, and whether the map can name gelato in a pan

It can name it, and it names it the way the business does, which is not as a
thing. Session 2 left three candidate shapes — a class of its own, a movement's
two ends, or something a count declares — and the documents decide between them
without an argument. The van sheet writes **flavour, format, quantity** as three
cells on a line; the wholesale delivery note writes the same three; the count
sheet writes `Fior di latte, 5 L pan | 6`, which is the first two cells with a
comma between them and a number beside it. No document in this business has ever
written "pistachio in a napoli pan" as one word, and `§2.5` refuses to write the
flavour-and-format pairs out at all, so a class whose rows are those pairs would
mint twenty-five by seven facts nobody has stated. So a movement's quantity is
of one of two things: an `Ingredient`, which covers everything bought and the
six things made in a run and water; or a `Flavour` **in** a `SoldProduct`, which
is the third candidate generalised from a count to every movement. Two slots,
declared per line, and the pair never becomes an entity. The return was not
designed: `movement_format` ranges over `SoldProduct`, which is the class
carrying `product_fill_quantity`, so the join from a count of pans to a recipe
in kilograms — about 3.3 for a pan, 0.460 for a tub, 0.100 for a mini — is a
slot that was already there. The cost is named rather than absorbed and it is
paid in the balance: a line the business writes without a flavour is in no
group. Its own count sheet has assorted catering tubs, assorted minis, part pans
on the top shelf and a finished cake, and not one of them says what is in it.

### The balance, and whether the aggregate annotation can carry a sign

**It cannot, and it does not need to.** Direction is carried by which slot the
`by` names, and the sign by a subtraction that is LinkML's own — which is the
1 Sep split between the two derivation problems arriving unchanged.

The map declares four aggregates and no net:

    ingredient_in    over StockMovement, sum movement_quantity,
                     by {ingredient_on_hand: movement_ingredient,
                         ingredient_where:   movement_into}
    ingredient_out   ... by {ingredient_on_hand: movement_ingredient,
                             ingredient_where:   movement_out_of}
    gelato_in        ... by {gelato_flavour: movement_flavour,
                             gelato_format:  movement_format,
                             gelato_where:   movement_into}
    gelato_out       ... by {gelato_flavour: movement_flavour,
                             gelato_format:  movement_format,
                             gelato_where:   movement_out_of}

One movement row is a departure from its origin and an arrival at its
destination at the same time, because the two aggregates are the same sum over
the same class grouped two different ways. Nothing anywhere says that goods
received add and waste subtracts.

What was run to find out: `trial_sign.py`, 167 lines, written **outside the
repo** in the scratchpad and expected to be deleted. It reads the four
declarations straight out of `business/sorella/draft.yaml` with `SchemaView` —
the map is never sealed, no database is touched, `read_map` refuses a draft and
was not used — and runs them over eight synthetic movements handed over the way
the generator hands a row over: every cell a `str`, because `value_literal` is
text, and `None` where the business writes nothing. The grouping rule is
`scripts/trial_derive.py`'s, unchanged in behaviour: a row silent under a
dimension is in no group, a row silent under the summed slot adds nothing.

    IngredientOnHand   over StockMovement, sum movement_quantity, cast to decimal
      ingredient_on_hand  ingredient_where  ingredient_in  ingredient_out  (net)
      caster_sugar        dry_store         0              5               -5   [silent: m3]
      caster_sugar        the_bench         5              0                5   [silent: m3]
      dextrose            dry_store         6              0                6
      dextrose            terra_nostra      0              6               -6

    GelatoOnHand   over StockMovement, sum movement_quantity, cast to decimal
      gelato_flavour  gelato_format  gelato_where     gelato_in  gelato_out  (net)
      pistachio       napoli_pan     bar_trentanove   2          0            2
      pistachio       napoli_pan     blast_freezer    3          3            0
      pistachio       napoli_pan     holding_freezer  3          2            1
      pistachio       napoli_pan     the_bench        0          3           -3
      pistachio       napoli_pan     the_van          2          2            0

    movements counted once as an arrival and once as a departure: m4 m5 m6 m7
    one class with four dimensions: 0 group(s) over 8 movements
    equals_expression '{a_in} - {a_out}' with 0 and 5 -> Decimal('-5')
    equals_expression '{a_in} - {a_out}' with 3 and 2 -> Decimal('1')
    equals_expression '{a_in} - {a_out}' with 2 and 2 -> Decimal('0')

Four of the eight movements are counted twice, once in each direction. Three of
the nine rows are negative and every one of them is right: the caster sugar
scooped out of the dry store never arrived there in this window, the pistachio
left the bench it was never delivered to, and Terra Nostra's own dextrose is
down six — the supplier's world drawn down without anyone declaring that it
should be, which is the 1 Sep line's double-entry argument turning up
uninvited.

**The smallest thing that could carry the sign is one `equals_expression` slot,
and this session's vocabulary forbids it.** It was measured on a throwaway
schema rather than assumed: `'{a_in} - {a_out}'` returns `Decimal('-5')`, not a
string and not an error. So the map ships with two of the balance's three
columns, and both derived classes say so in their own descriptions. Nothing was
invented to escape it and no second annotation shape was written.

### Why there are two balance classes and not one

Measured, not preferred. A single class dimensioned by ingredient, flavour,
format and place produced **0 groups over 8 movements**: every movement is
silent under two of the four dimensions, and a row silent under a dimension is
in no group. Two classes with disjoint dimension sets give the right rows, and
the null rule stops being a detail of a throwaway script and becomes the filter
— an ingredient movement is not in the gelato balance because it names no
flavour, and a pan movement is not in the ingredient balance because it names
no ingredient. Neither class carries `entity_class`: nobody ever asserts a row
of one.

### Every `§3.2` and `§3.3` subsection, consumed or left

| Subsection | Where it went |
|---|---|
| `§3.2` preamble | `movement_out_of`, `movement_into`, `kind_document`, `kind_lag`. The preamble is the mechanism: every movement names where the thing came from and where it went, both drawn from `§1.3` |
| `§3.2` Goods in (9) | `MovementKind` rows; the movements are `StockMovement` out of a `Supplier` into an internal place. **No `GoodsReceived` class** — see below |
| `§3.2` Inside the kitchen (15) | `StockMovement`. Churn and fill also mints a `Batch`; its pans-out and tubs-out are movements naming it |
| `§3.2` Out on the van (9) | `StockMovement`. Empty pans back is a movement of a `BoughtItem`, the napoli pan, not of gelato |
| `§3.2` Inside the shops (15) | `StockMovement`. A scoop sale is `movement_format` = single scoop with `movement_flavour` empty when the generic key was used |
| `§3.2` Out of the business without a sale (7) | `StockMovement` into `Comps`, `Donations`, `Tastings`, `Staff`, the owner's house and the three bins — all already `Location` rows from session 1 |
| `§3.2` What the movements leave out | **Left, deliberately.** All five are already OPEN lines: the container's missing thermometer, empty pans with nowhere to live, three places the file does not name, and the two Cotham back freezers nobody can tell apart. The map does not repair any of them |
| `§3.3` preamble | Nothing to model. "There is no stock system. There never has been" |
| `§3.3` the production sheet | `Batch` + its output movements. The margin is `batch_note` |
| `§3.3` the van sheet | `StockMovement` lines |
| `§3.3` the wholesale delivery note | `StockMovement` lines; the empty-pans box is a second movement |
| `§3.3` the pan notebook | `StockMovement` of a `BoughtItem` between the van and an account, out and back |
| `§3.3` the suppliers' delivery notes | `StockMovement`; the nine shapes are `kind_document` on nine `MovementKind` rows |
| `§3.3` the waste sheets | `StockMovement` into a bin. The sheet itself has no page class |
| `§3.3` the count sheet | `StockCount` + `StockCountLine` |
| `§3.3` the till | `StockMovement` for the stock lines only |
| `§3.3` the office tray and Xero, the cake order, the milk text, the orders out, the wholesale invoice, Marina's spreadsheet, the HACCP plan | **Left.** Money, intention and rules. The HACCP plan's rules are `§3.4` and belong to session 4 |
| `§3.3` the temperature log, the whiteboard, the cabinet plan | **Left, and they are the three stock documents with no home at all.** See the table below |
| `§3.1`, `§3.4` to `§3.7` | Outside this session. `§3.1` is context, `§3.4` and `§3.5` are session 4's, `§3.6` and `§3.7` belong to no session |

### The eighteen documents: can the map produce it

Three yes. Five that are a no by one or two fields, whose stock lines all have a
home. Three that are stock and genuinely absent. Seven that are not stock
documents at all.

| # | Document | Can the map produce it | What is missing |
|---|---|---|---|
| 1 | The production sheet | **No** | The pasteuriser run block at the head wants a **time of day**, and the only `time` in the map is `batch_frozen_at` on a `Batch`. The run itself is a movement of base and is producible; its clock is not. The batch rows, the freeze time, the initials, the margin and the cakes-built sentence all have a home, but the sheet is a header and its lines and so is at least two forms |
| 2 | The van sheet | **No** | The **signature** at the drop is a second person and `written_by` is one; the **time box** is a time of day; and the cake line's **customer name** has no home, because a retail customer is one `Location` and not a person. Every stock line is producible |
| 3 | The wholesale delivery note | **No** | The **customer's signature and printed name**. The price and line-total columns are never filled by anybody, so their absence costs nothing |
| 4 | The pan notebook | **Yes** | Two movements a line, out and back, of a napoli pan between the van and an account. It is never totalled anyway |
| 5 | The suppliers' delivery notes | **Yes** | One shape for nine. The **shape of the paper** is not recorded and the supplier's product codes are not either — but the business records neither, and the quantity is on a party's paper and nowhere else, which is already an OPEN line |
| 6 | The office tray and Xero | **No** | Invoice number, invoice date, net, VAT, gross, nominal code. `§3.3` says only the money is keyed and the quantities never enter any system, so it is not a stock document |
| 7 | The waste sheets | **No** | The **week-ending header**: the map gave the count sheet a page and the waste sheet none, so its lines are free-standing movements. And "mango, half" is a fraction written as a word, which `movement_quantity` cannot hold. The *why* column is covered — `movement_kind` is the reason, and the column is mostly blank |
| 8 | The count sheet | **Yes** | Nothing, and it is the one document where the map holds **more** than the paper: `count_line_where` is a place the sheet has no column for, and `count_line_written_as` keeps the cell as written beside what it resolves to |
| 9 | The temperature log | **No** | A twice-daily **reading** of a place. `location_temperature` is how cold a place is kept, a standing fact; there is no class for an observation of a place over time. It is the most consistently completed document in the business |
| 10 | The whiteboard | **No** | Nothing on it is a date — "roughly when, and never a date" — and nothing on it is a quantity. `happened_on` is a date and `movement_quantity` a decimal. The container runs are visible only as movements with both empty |
| 11 | The till | **No** | The money side entire: **price on the line**, **payment type**, **time of day**, and the whole **cash-up** with its unexplained variance box. The sale lines are producible, including the generic SCOOP key as a movement with no flavour and the comp key as a movement into `Comps` |
| 12 | The cabinet plan | **No** | A **well** is a `Unit` in `§1.5` and not a place in `§1.3`, so "wells 1 to 24, a flavour against each" has nowhere to land; and a plan for next week is an intention, which nothing in the map holds |
| 13 | The cake order | **No** | A named **customer with a phone number**, a **message for the box**, a **deposit**, and a **collection time**. And a cake takes two flavours where a movement carries one `movement_flavour`, so a movement of a cake cannot say what is in it |
| 14 | The milk text | **No** | An **order**. Nothing in the map states what was asked for, only what arrived |
| 15 | The orders out | **No** | The same, six more times. `§3.3` states the consequence itself: a short delivery is visible only if the supplier's own packer writes it on the note |
| 16 | The wholesale invoice | **No** | An invoice is a **second document about a movement**, and the map has movements rather than documents. The drop is Tuesday and the invoice is dated the Sunday, so one event has two dates up to six days apart; `happened_on` holds one of them and the kernel's `recorded_at` holds when the system learned it, and there is nowhere for the third |
| 17 | Marina's spreadsheet | **No** | Takings, payments and a costing tab last touched in 2023. The map holds two prices and no money |
| 18 | The HACCP plan | **No** | The shelf-life rules, the blast rule and the pasteurising rule are `§3.4` and are session 4's. Nobody fills any of it in |

### What `§3` threw, and where the map has somewhere to put each

| Problem | Somewhere to put it? |
|---|---|
| A scoop has no weight and two thirds of retail sales are counted in it | **No, and it is a limit on milestone one rather than a modelling gap.** `movement_format` reaches the scoop rows and `product_fill_quantity` on them is empty because nobody has ever weighed one. A closing balance at either shop cannot be computed from what the business records, and no input would change that, because no number exists to be found |
| Every count and van sheet is in whole pans and part pans, and a part pan is a half or three quarters by eye | **Half.** `movement_quantity` is a decimal and holds 0.5; nothing converts the *word*. The waste sheet writes "mango, half" in the *what* column and the how-much column beside it is blank |
| A page's lines do not sum to its basis, and nothing enforces it | **Unchanged from session 2 and now load-bearing.** `line_stage: at_fill` marks what goes in on top of the 12.00 kg, and a `Batch`'s `batch_mix_quantity` is the mix in. Anything that totals a batch must add the at-fill lines to the basis; nothing in the map tells it to |
| Whether a pan at a cafe is stock, a loan or nobody's | **A place for it, not an answer.** The pan is a `BoughtItem` and the account is a `Location`, so `IngredientOnHand` will show pans standing at Caffe Umberto. Whether that is stock is `§2.6`'s question and is already an OPEN line |
| `line_unit` is grams while `item_counted_in` is bags, sacks and tins, and movements name a third | **Confirmed, and the third unit is now real.** `movement_unit` exists precisely because `§3.2`'s ingredients to the machine is grams off a bench scale while the same item is counted in bags. One map now names three units for one thing and converts between none of them |
| `§2.6`'s packaging bill cannot be joined to `§1.7`'s price list | **Still not, and session 3 does not touch it.** Those pages sit in the map with nothing pointing at them |

### Counts

- **7 classes added** — `MovementKind`, `StockMovement`, `Batch`, `StockCount`,
  `StockCountLine`, `IngredientOnHand`, `GelatoOnHand`. **21 in total.**
- **41 slots added.** **99 in total**, every one carrying an explicit
  `slot_uri`. Sessions 1 and 2's 58 are all still present; **none was renamed,
  none re-ranged, none re-homed**, and no existing class's induced slot list
  changed — checked with `class_induced_slots` against `HEAD`, not by reading.
- **22 relationship slots added.** **35 in total.**
- **2 identifiers added** — `kind_name`, `batch_number`. **10 in total.**
  `StockMovement`, `StockCount`, `StockCountLine` and both balance classes have
  none, for the 30 Aug reason: the business identifies none of them.
- **4 aggregate annotations added**, the first in any Sorella map.
- **0 `is_a` edges added.** The hierarchy is unchanged and **still one level
  deep**.
- **0 enums added, 0 `unique_keys` added, 0 `equals_expression`.**

### The mermaid render, added and changed classes only

Seven files differ from session 2's and **no existing file changed** — checked
with `diff -rq` between a render of `HEAD`'s draft and a render of this one, 14
files against 21. Whitespace is collapsed and the `click` lines dropped, as
session 2 did.

```mermaid
 classDiagram
    class MovementKind
      MovementKind : entity_class
      MovementKind : kind_document
      MovementKind : kind_happens
      MovementKind : kind_lag
      MovementKind : kind_name
```
```mermaid
 classDiagram
    class StockMovement
      StockMovement : entity_class
      StockMovement : happened_on
      StockMovement : movement_batch
        StockMovement --> "0..1" Batch : movement_batch
      StockMovement : movement_flavour
        StockMovement --> "0..1" Flavour : movement_flavour
      StockMovement : movement_format
        StockMovement --> "0..1" SoldProduct : movement_format
      StockMovement : movement_ingredient
        StockMovement --> "0..1" Ingredient : movement_ingredient
      StockMovement : movement_into
        StockMovement --> "0..1" Location : movement_into
      StockMovement : movement_kind
        StockMovement --> "0..1" MovementKind : movement_kind
      StockMovement : movement_note
      StockMovement : movement_out_of
        StockMovement --> "0..1" Location : movement_out_of
      StockMovement : movement_quantity
      StockMovement : movement_unit
        StockMovement --> "0..1" Unit : movement_unit
      StockMovement : written_by
        StockMovement --> "0..1" Person : written_by
```
```mermaid
 classDiagram
    class Batch
      Batch : batch_flavour
        Batch --> "0..1" Flavour : batch_flavour
      Batch : batch_frozen_at
      Batch : batch_mix_quantity
      Batch : batch_mix_unit
        Batch --> "0..1" Unit : batch_mix_unit
      Batch : batch_note
      Batch : batch_number
      Batch : entity_class
      Batch : happened_on
      Batch : written_by
        Batch --> "0..1" Person : written_by
```
```mermaid
 classDiagram
    class StockCount
      StockCount : count_note
      StockCount : entity_class
      StockCount : happened_on
      StockCount : written_by
        StockCount --> "0..1" Person : written_by
```
```mermaid
 classDiagram
    class StockCountLine
      StockCountLine : count_line_flavour
        StockCountLine --> "0..1" Flavour : count_line_flavour
      StockCountLine : count_line_format
        StockCountLine --> "0..1" SoldProduct : count_line_format
      StockCountLine : count_line_ingredient
        StockCountLine --> "0..1" Ingredient : count_line_ingredient
      StockCountLine : count_line_note
      StockCountLine : count_line_quantity
      StockCountLine : count_line_unit
        StockCountLine --> "0..1" Unit : count_line_unit
      StockCountLine : count_line_where
        StockCountLine --> "0..1" Location : count_line_where
      StockCountLine : count_line_written_as
      StockCountLine : entity_class
      StockCountLine : line_count
        StockCountLine --> "0..1" StockCount : line_count
```
```mermaid
 classDiagram
    class IngredientOnHand
      IngredientOnHand : ingredient_in
      IngredientOnHand : ingredient_on_hand
        IngredientOnHand --> "0..1" Ingredient : ingredient_on_hand
      IngredientOnHand : ingredient_out
      IngredientOnHand : ingredient_where
        IngredientOnHand --> "0..1" Location : ingredient_where
```
```mermaid
 classDiagram
    class GelatoOnHand
      GelatoOnHand : gelato_flavour
        GelatoOnHand --> "0..1" Flavour : gelato_flavour
      GelatoOnHand : gelato_format
        GelatoOnHand --> "0..1" SoldProduct : gelato_format
      GelatoOnHand : gelato_in
      GelatoOnHand : gelato_out
      GelatoOnHand : gelato_where
        GelatoOnHand --> "0..1" Location : gelato_where
```

Mermaid draws no aggregate annotation. `IngredientOnHand` and `GelatoOnHand`
render as five plain slots each, so the review picture cannot show that two of
them are computed and three are dimensions of a group — the same blindness that
hides a `unique_keys`, one class further on.

### Surprising

1. **The four-dimension balance produced nothing at all.** One class dimensioned
   by ingredient, flavour, format and place gave **0 groups over 8 movements**.
   The rule that did it — a row silent under a dimension is in no group — looked
   like an implementation detail of a 292-line throwaway on 2 Sep. It is not: it
   decides how many balance classes a business needs, and it decided this one
   before any preference could.
2. **Fifty-five rows are fifty-three kinds, and the two duplicates are v1's
   failure for the third time.** *Refill a well* and *cabinet expiry* are each
   written twice, once per shop, differing only in which places they name — and
   the places are on the movement. Naming a kind per shop is exactly what
   folding location into a pan slot name was in v1, and what naming a slot after
   a price column would have been in session 1. The map has now refused the same
   shape three times in three sessions and it arrived looking different each
   time.
3. **`GoodsReceived` disappeared without an argument.** The 1 Sep line kept it
   separate from the merged movement class because it added a slot. In this map
   it does not: a delivery's origin is a supplier, a supplier is a place, and the
   form is the same form. The "outside is locations" decision was sold on
   direction becoming free; what it also bought was one class instead of two,
   and nobody predicted that.
4. **The supplier's own balance goes negative and nothing asked it to.**
   `IngredientOnHand` shows Terra Nostra at −6 dextrose. That is double-entry
   turning up uninvited: model the outside as places and the outside gets drawn
   down. It is correct, it is useless, and it will appear in every generated
   table until something filters it.
5. **Fifteen of the eighteen documents are a no, and eight of the fifteen are
   not stock documents at all.** The business's paper is mostly money,
   temperature and intention. That is not the map failing to reach; it is what
   walking a real business's whole record looks like, and it would not have been
   visible from the map's side.
6. **The map records something the paper cannot, twice.** `count_line_where` is
   a place the count sheet has no column for, and a generated count form has a
   list where the paper is blank ruled. Both change what a count means rather
   than digitising it, and only one of them was already an OPEN line.

### What was run

| Command | Exit |
|---|---|
| `PYTHONIOENCODING=utf-8 gen-owl --no-use-native-uris business/sorella/draft.yaml > build/sorella_draft.ttl` | 0 — 110,105 bytes, 0 `rdfs:domain`, 1 `owl:hasKey`. `range: time` survives |
| `PYTHONIOENCODING=utf-8 gen-mermaid-class-diagram -d "$TEMP/sorella_mmd3" business/sorella/draft.yaml` | 0 — 21 files, one per class, none for the enum |
| the same over `git show HEAD:business/sorella/draft.yaml`, then `diff -rq` | 0 — 14 files against 21; **7 added, 0 changed** |
| `grep -c any_of business/sorella/draft.yaml` | 1 — no match |
| `grep -c facts business/sorella/draft.yaml` | 1 — no match. No `annotations.facts` block |
| `grep -c equals_expression business/sorella/draft.yaml` | 1 — no match. The forbidden word is absent from the map and was measured outside it |
| `python -c "open(...,'rb').read().decode('ascii')"` | 0 — the draft is pure ASCII, so the U+2212 trap still cannot fire |
| `SchemaView` introspection | 21 classes, 99 slots, 1 enum, 35 relationship slots, 4 aggregates, 10 identifiers, 0 slots without a `slot_uri` |
| `SchemaView` diff against `HEAD` | 0 of 14 classes missing, 0 of 58 slots missing, 0 re-ranged, 0 classes whose induced slots changed; 7 classes and 41 slots added |
| `trial_sign.py` in the scratchpad, against the draft, no database | 0 — output above |
| `make check` | 0 — **64 tests passed**, replay byte-identical twice, 5,334 bytes both times |
| `git diff --stat HEAD -- business/sorella/profile.md` | 0 — empty. The profile is untouched |
| `git status --porcelain` | ` M business/sorella/draft.yaml` and nothing else. Nothing under `business/` outside `business/sorella/` added, moved or deleted |

`make check` collected 64 and passed 64. This session writes no code and adds no
test. `seal` was not run and the map was never sealed; the trial reads the draft
with `SchemaView`, which is what session 1 and session 2 also did.

**No two clauses of the done condition conflicted.** One reads oddly and did
not: the vocabulary forbids `equals_expression` while the item asks whether the
aggregate can carry a sign. It cannot, and the thing that can is the forbidden
one — so the answer to the question is the reason the map is one slot short, and
both halves are reported rather than one being satisfied quietly.

### Proposed `DECISIONS.md` entries

1. Gelato in a pan is two cells on a line and not a thing. A movement's quantity
   is of an `Ingredient`, or of a `Flavour` in a `SoldProduct` — two slots
   declared per line, and the pair never becomes an entity. The business decides
   this rather than modelling taste: the van sheet and the wholesale delivery
   note write flavour, format and quantity as three cells, the count sheet
   writes "Fior di latte, 5 L pan" as one cell with a comma in it, and `§2.5`
   refuses to write the flavour-and-format pairs out at all, so a class of those
   pairs would mint twenty-five by seven facts nobody has stated. The unforeseen
   return is that `movement_format`'s range is `SoldProduct`, which already
   carries `product_fill_quantity`, so the join from a count of pans to a recipe
   in kilograms was a slot that existed. The cost is named: a line written
   without a flavour — assorted minis, assorted catering tubs, part pans, a
   finished cake — is in no group of a balance grouped by flavour, and that is a
   thing the business does not record rather than one the map cannot express.
2. One movement class, and `GoodsReceived` does not survive into Sorella. The
   1 Sep line merged four byte-identical movement classes and kept
   `GoodsReceived` separate because it added a slot; in this map it adds none. A
   delivery's origin is a supplier, a supplier `is_a Location`, and the form is
   the same form. So "the outside of the business is locations" bought two
   things and only one was predicted: direction became free, and the movement
   classes became one.
3. `§3.2`'s fifty-five rows are fifty-three `MovementKind` rows, and the kind of
   a movement is a field on the movement rather than a class per kind. Two names
   are written twice — refill a well, cabinet expiry — once per shop, and the
   only difference between the two rows is which places they name, which the
   movement's own origin and destination already say. Folding the shop into the
   kind's name is v1's pan-slot failure and session 1's price-column refusal for
   the third time. The kind carries only what is constant per kind and never
   retyped per movement: what actually happens, the document and who fills it,
   and the lag — twenty-two of the fifty-five saying "Nothing" in that column,
   which is the value rather than an absence.
4. The aggregate annotation cannot carry a sign and does not need one. Measured
   over the four declarations read out of the unsealed draft: the same sum over
   the same class, grouped once by `movement_into` and once by
   `movement_out_of`, puts one movement row in the arrival group of its
   destination and the departure group of its origin — four of eight synthetic
   movements counted twice. Direction is which slot the `by` names; the sign is
   a subtraction, and `equals_expression '{a_in} - {a_out}'` returns
   `Decimal('-5')` for 0 minus 5. That is the 1 Sep two-problem split arriving
   unchanged. This session's vocabulary forbids `equals_expression`, so the map
   ships with `ingredient_in`, `ingredient_out`, `gelato_in`, `gelato_out` and
   no net, and both derived classes say so in their own descriptions.
5. Two balance classes and not one, decided by measurement. A single class
   dimensioned by ingredient, flavour, format and place produced **0 groups over
   8 movements**, because every movement is silent under two of the four
   dimensions and a row silent under a dimension is in no group. Two classes
   with disjoint dimension sets give the right rows and the null rule becomes
   the filter rather than something imposed on top of it. Neither carries
   `entity_class`: nobody ever asserts a row of one.
6. A count line is its own entity, and the 30 Aug rule that a quantity hangs on
   the thing rather than on the count is superseded for counts the way 1 Sep
   superseded it for movements. This is stated rather than done quietly, because
   30 Aug's decisive reason was Q6: two honest counts of one freezer must
   compete on one (subject, predicate) so the read rule breaks the tie and the
   overwrite is visible. With a count line as its own entity nothing competes
   and the two counts stand side by side — which is what the 2 Sep OPEN line
   asks for and is a change in what Q6 tests.

### Proposed `OPEN.md` lines

- `[T3]` The production sheet's pasteuriser run block wants a time of day on a
  movement and the map has one only on a `Batch`. `§3.3` gives the block three
  ruled lines — time, kilos, what it is — and the run itself is a
  `StockMovement` of base whose kilos and ingredient have homes. So one document
  is a no by one field, and the same field would answer the van sheet's time box
  and the till's time. Whether a movement carries a clock time, whether
  `happened_on` becomes a datetime, or whether a time of day is something the
  log holds only as `recorded_at`, is undecided. Raised 3 Sep · blocks: generation
- `[T3]` A document's signature is a second person and `written_by` is one. The
  van sheet is written by the driver and signed by the shop, the wholesale
  delivery note by the driver and signed by the customer, and Whitehall's note
  is signed by Dan on the mornings he is in. Two of `§3.3`'s eighteen documents
  are a no for this reason alone. Whether a second person slot, a `Person` on
  the movement's destination, or nothing, is undecided. Raised 3 Sep ·
  blocks: generation
- `[T3]` The map gave the count sheet a page and the waste sheet none. A waste
  sheet is a weekly page with a week-ending header written on the Monday and its
  lines are free-standing `StockMovement`s, so nothing joins the three lines
  written from memory on one Friday, and the header has nowhere to go. `§3.3`
  describes three such sheets. Whether every document with a header and lines
  needs a page class, or only the ones something totals, is undecided. Raised
  3 Sep · blocks: generation
- `[T3]` `happened_on` and the kernel's `valid_from` say the same thing twice.
  Every one of `§3.3`'s eighteen documents starts with a date a person fills in,
  so the map carries a slot for it; the kernel already carries `valid_from` for
  the same instant and `submit()` does not join them. The van sheet is the case
  that decides, because it is written at loading or at the first drop from
  memory and so its date can precede what it records. Whether a document's date
  slot is how a form sets `valid_from`, or a fact standing beside it, is
  undecided. Raised 3 Sep · blocks: recording
- `[T3]` A movement of a cake cannot say what is in it. `§2.3`'s cake takes
  1.4 L of one flavour and 1.1 L of a second, read out on the phone per cake,
  and `movement_flavour` is one slot. `§4`'s count sheet has two finished cakes
  standing in the holding freezer and the cake order carries two flavour fields.
  Whether a cake is a movement with two flavour slots, a thing minted at the
  bench, or a line the balance is allowed to lose, is undecided. Raised 3 Sep ·
  blocks: generation
- `[T3]` Three of `§3.3`'s documents are about stock and have no home at all:
  the temperature log, which is a twice-daily reading of a place where
  `location_temperature` is a standing fact; the whiteboard, where nothing is a
  date and nothing is a quantity; and the cabinet plan, where a well is a `Unit`
  and not a place and a plan is an intention. The first is the most consistently
  completed document in the business. Whether an observation of a place over
  time is a class, and whether an intention belongs in a log of what happened,
  are two different questions and neither is decided. Raised 3 Sep ·
  blocks: generation
- `[T3]` An invoice is a second document about a movement, and the map has
  movements rather than documents. A wholesale drop happens on the Tuesday and
  Marina types its invoice on the Sunday from the second copy in the tray, so
  one event carries two dates up to six days apart; `happened_on` holds one and
  `recorded_at` holds when the system learned it, and the third has nowhere to
  go. This is the same shape as the delivery note corrected across a later van
  sheet, which is already an OPEN line, seen from the money side. Raised 3 Sep ·
  blocks: report
- `[T2]` Would anybody pick a movement's kind off a list of fifty-three? The map
  makes `movement_kind` a picker over `§3.2`'s own rows, which is what lets the
  log say which of the ways stock moved rather than leaving it on
  `intent.action_name`. Whether Steve at a counter, or Dan at the machine, would
  choose from fifty-three rather than reach for the nearest, is a thing only
  they can say, and the alternative — a form per kind — is the failure the 1 Sep
  rule exists to prevent. Raised 3 Sep · blocks: interview

Two questions were triaged `[T1]` and tried rather than written down: whether
the aggregate annotation can carry a sign, and whether one balance class can
carry four dimensions. Both are answered above, in twenty minutes and one
throwaway script.

## 2026-09-04 — Sorella's map, session 4 of 4: the net, the seal, and v1's five gaps

The map is closed. `business/sorella/v1.yaml`, 56,613 bytes, sealed once with
`--into business/sorella/`, and the generator run against it. Not a fifth
modelling session: two slots were added and nothing else in the map moved.

`§3.4`'s fifty-one rules and `§3.5`'s nine contested measures are **not in this
map** and that is the point of sealing now. Nothing in either touches arrivals
minus departures, so milestone one does not need them, and adding them after
the seal is a definition change — stage 7, which has never had a real change to
replay.

### One — the net column

`ingredient_on_hand_net` and `gelato_on_hand_net`, each an `equals_expression`
over the two aggregates already beside it:

    ingredient_on_hand_net   '{ingredient_in} - {ingredient_out}'
    gelato_on_hand_net       '{gelato_in} - {gelato_out}'

Both classes' descriptions said the subtraction was absent. Those sentences are
gone, and the note beside them in `draft.txt` says why they were there: they
described a constraint on the author, not a property of the business. That is
the only sentence this map has ever carried for that reason.

Measured on the map's own two expressions before they were written into it, not
on a synthetic pair:

| expression | cells | result |
|---|---|---|
| `{ingredient_in} - {ingredient_out}` | `Decimal('0')`, `Decimal('5')` | `Decimal('-5')` |
| `{ingredient_in} - {ingredient_out}` | `Decimal('6')`, `Decimal('0')` | `Decimal('6')` |
| `{gelato_in} - {gelato_out}` | `Decimal('3')`, `Decimal('2')` | `Decimal('1')` |
| `{gelato_in} - {gelato_out}` | `Decimal('2')`, `Decimal('2')` | `Decimal('0')` |
| `{ingredient_in} - {ingredient_out}` | `'0'`, `'5'` — **uncast**, straight out of `value_literal` | `TypeError: unsupported operand type(s) for -: 'str' and 'str'` |

The last row is the one worth keeping. The 1 Sep trial found `{left} + {right}`
returning `'34'` for 3 + 4 — no exception, a valid `str`, a wrong number. **The
same evaluator, given two strings and a minus, raises.** Subtraction has no
string meaning, so the caster the 1 Sep line asks for is enforced by Python's
own type system on this expression and not on the addition beside it. The
missing cast is loud here and silent one operator away, which is worse than
either being uniformly true.

The three-column balance then runs end to end **off the sealed map**, in a
throwaway written in the scratchpad, no database, reading `over`, `sum`, `by`
and the expression with `SchemaView` and handing every cell over as a `str` the
way `generate.py` does:

    IngredientOnHand   over StockMovement, sum movement_quantity, read from v1.yaml
      ingredient_on_hand  ingredient_where  ingredient_in  ingredient_out  ingredient_on_hand_net
      caster_sugar        dry_store         25             8               17
      caster_sugar        terra_nostra      0              25              -25
      caster_sugar        the_bench         5              0               5
      dextrose            dry_store         6              0               6
      dextrose            terra_nostra      0              6               -6

    GelatoOnHand   over StockMovement, sum movement_quantity, read from v1.yaml
      gelato_flavour  gelato_format  gelato_where     gelato_in  gelato_out  gelato_on_hand_net
      pistachio       napoli_pan     bar_trentanove   2          0           2
      pistachio       napoli_pan     blast_freezer    3          3           0
      pistachio       napoli_pan     holding_freezer  3          2           1
      pistachio       napoli_pan     the_bench        0          3           -3
      pistachio       napoli_pan     the_van          2          2           0

Twenty-five kilograms of caster sugar arrived at the dry store and eight left
it, so seventeen stand. **That is stock falling**, which is gap 2 answered with
a number rather than with a slot list. One of the eight movements names an
origin and no destination — three out of the dry store, going nowhere the
business wrote down — and it is counted in `ingredient_out` and in no arrival
group anywhere, which is the null rule doing exactly what session 3 measured.

`gen-owl --no-use-native-uris` over the draft exits 0 and writes 112,541 bytes.

### Two — the provenance note

`business/sorella/draft.txt`, 23,086 bytes, and `annotations.transcript:
draft.txt`. The draft had carried only `valid_from` since session 1, and session
1's log said so at the time: not a conflict inside that session, a dependency
the sealing session inherits.

Shaped on Marlow's `v1.txt`, which was read before a line of it was written: the
same headings — what is in the file, what became what, who would have written
it, choices the profile does not make, what was deliberately not written, what
the renders showed. Two headings are new and both earn their place. **What a
later sitting took back** exists because this map was written over four sittings
and Marlow's over one, and the only re-homing that ever happened — four slots
from `BoughtItem` up to `Ingredient` — would otherwise be readable only in
`LOG.md`. The relationship list is written out slot by slot because Sorella's
profile has no section 6: Marlow's profile handed the author a relationship
table and this one did not, so the thirty-five had to be read off the sections
and there is nowhere else the coverage can be checked.

One note for four sittings, written at the seal, rather than four notes. A
sealed version is one artefact and `seal` copies one file beside it; four would
have needed a concatenation nobody would have re-read.

### Three — the seal, once

    sealed  business\sorella\v1.yaml  (v1)
    transcript business\sorella\v1.txt
    valid from 2026-06-15T00:00:00+00:00
    sealed at  2026-09-03T20:14:38.201488+00:00
    intent 8fc11510-d59f-4fd7-ab36-f41509fffbd0: 101 entities minted, 101 assertions

It did not refuse. Before running it, every check `seal` makes was run against
the draft **through `seal`'s own functions with no database connection** — 101
`slot_uri`s, 35 class-ranged, 0 facts, a `valid_from`, a flat annotations block,
a transcript that is a file, `v1` with nothing superseded, and the sealed text
re-validated through `SchemaView`. A refusal after the version file is written
is the one failure mode that cannot be retried, because `seal` refuses to
rewrite a version that exists, so the pure path was walked first.

**101 assertions and not one fact.** Every row is a URI registration: one per
declared `slot_uri`. `uniti:uri` itself was not minted, because Marlow's seal
already registered it and `seal` found it in the registry — the dedupe working
across two businesses eleven months apart.

Two stores now, each with a v1, neither superseding the other:

    business/          v1  valid_from 2025-09-01   Marlow, retired 2 Sep
    business/sorella/  v1  valid_from 2026-06-15   Sorella, supersedes: null

`resolve_version('business/sorella', valid_at=16 June 2026, as_of=today)` returns
`v1`. The default `--into` would have made Sorella a v2 superseding a business
retired on 2 Sep, which is the 28 Aug failure; it was not used.

**The seal round-trips the map with zero structural change.** Checked with
`SchemaView` rather than by reading: same 21 classes, same 101 slots, and for
every slot the same `slot_uri`, `range`, `required`, `identifier`,
`multivalued`, `equals_expression`, `designates_type`, `unit` and `description`;
same induced slot list on every class; same class descriptions; the `unique_keys`
on `ProductPrice`; the enum's two values; all four `aggregate` mappings and both
`equals_expression`. The schema description string is equal. What did change is
physical: `yaml.safe_dump` turns every block scalar into a quoted flow scalar and
reflows it, so the file is 1,308 bytes smaller and every long description is one
paragraph of wrapped text. The `str()` hazard did not fire because there is
nothing to stringify — no fact, no boolean, no trailing zero.

`gen-owl` over the sealed file exits 0, 112,699 bytes, 0 `rdfs:domain`, 1
`owl:hasKey`.

### Four — the generator

**No path was hard-coded and nothing under `components/` was changed.** Every
occurrence of `business/v1.yaml` in `generate.py` is in the module docstring's
usage block or in an `argparse` help string; the map is a positional argument.
That was checked before anything was run, because changing it would have been a
`components/` change and would have had to be said out loud.

**21 forms, one per class, all exit 0.** 137 fields, 41 pickers, 14 required
markers.

| class | fields | pickers | required | class | fields | pickers | required |
|---|---|---|---|---|---|---|---|
| `Batch` | 9 | 3 | 1 | `Recipe` | 6 | 1 | 1 |
| `BoughtItem` | 10 | 5 | 1 | `RecipeLine` | 8 | 3 | 0 |
| `Business` | 5 | 0 | 1 | `SoldProduct` | 10 | 2 | 1 |
| `Flavour` | 6 | 1 | 1 | `StockCount` | 4 | 1 | 0 |
| `GelatoOnHand` | 6 | 3 | 0 | `StockCountLine` | 10 | 6 | 0 |
| `Ingredient` | 6 | 3 | 1 | `StockMovement` | 13 | 9 | 0 |
| `IngredientOnHand` | 5 | 2 | 0 | `Supplier` | 9 | 0 | 1 |
| `InternalLocation` | 5 | 1 | 1 | `Unit` | 3 | 0 | 1 |
| `Location` | 3 | 0 | 1 | `WholesaleAccount` | 6 | 0 | 1 |
| `MovementKind` | 5 | 0 | 1 | `ProductPrice` | 4 | 1 | 0 |
| `Person` | 4 | 0 | 1 | | | | |

All 14 required markers sit on identifiers and nowhere else — there is no
required non-identifier slot anywhere in the map, and the ten identifiers are
required on each class that induces them, which is where the extra four come
from.

**21 tables, all exit 0, all 0 rows, all `--verify` clean.** That is correct and
uninteresting: the log holds 101 URI registrations and no fact, so no entity is
the subject of anything under any column. Marlow's 301 rows are in the same
database and **not one of them became a Sorella row** — `uniti:` and `sorella:`
predicates do not meet.

The form quoted in full is `StockMovement`, because it is the class that answers
three of the five gaps:

```
StockMovement form  (v1.yaml, v1)

field                type               from the map
-------------------  ---------------    --------------------------------------------------------
entity_class         string             Which class this entity is an instance of
movement_kind        -> MovementKind    Which of section 3.2's ways this movement was
movement_out_of      -> Location        Where it came from
movement_into        -> Location        Where it went
movement_ingredient  -> Ingredient      Which bought or made thing moved, where the movement is
movement_flavour     -> Flavour         Which flavour, where the movement is of gelato
movement_format      -> SoldProduct     What the gelato was in, which is a line of the price lis
movement_quantity    decimal            How many, or how much
movement_unit        -> Unit            What the number on this line is in
movement_batch       -> Batch           Which churn this came off, where it is one of a batch's
happened_on          date               The date written on the paper
written_by           -> Person          Who put their name on it
movement_note        string             Anything written in words rather than in a column

movement_kind offers nothing: the log holds no MovementKind

movement_out_of offers nothing: the log holds no Location

movement_into offers nothing: the log holds no Location

movement_ingredient offers nothing: the log holds no Ingredient

movement_flavour offers nothing: the log holds no Flavour

movement_format offers nothing: the log holds no SoldProduct

movement_unit offers nothing: the log holds no Unit

movement_batch offers nothing: the log holds no Batch

written_by offers nothing: the log holds no Person
```

All 41 pickers in all 21 forms offer nothing, over 12 distinct classes. Under
the 1 Sep line that is exactly where a freshly sealed map is supposed to be:
seal, then the master-data forms, then operate, and this session is the first of
the three.

### Can an empty picker be told from a missing class, from the rendered form alone?

**No, and it is measured rather than argued.** Marlow's `GoodsReceived` form was
re-rendered from `business/v1.yaml` — a read, nothing written — and its failing
line is put beside Sorella's healthy one:

    Marlow v1, the defect:  received_from offers nothing: the log holds no Supplier
    Sorella v1, expected:   movement_out_of offers nothing: the log holds no Location

Same sentence, same shape. One is a gap and one is a Tuesday morning before
anybody has typed anything, and nothing else on the page separates them. The
form names the range class and stops there; whether that class can ever be
filled depends on whether a form exists for it and whether `submit()` will mint
one, and both of those are facts about **a different artefact**. A reviewer
holding one rendered form cannot answer the question this session was set.

What settles it here is one command per class, not one form: `generate.py form`
succeeds for all 21 classes, so all 12 ranges are fillable. Under this generator
"the class is in the map" and "a form for it can be rendered" are the same
statement, so v1's first gap could not recur — but the artefact that shows it is
the directory listing, not the page.

### v1's five gaps

The list was written on 1 Sep, before Sorella's profile existed, so it cannot
have been tuned to the map that answers it.

**1 — no supplier was nameable. `received_from` was a field the form offered and
the log could never fill. → YES, answered.**
`Supplier` is a class in the sealed map, `is_a Location`, identified by
`location_name`, which is `required`. `generate.py form business/sorella/v1.yaml
Supplier` renders nine fields — `outside_where`, `supplier_brings`,
`supplier_rhythm`, `supplier_lead_time`, `supplier_minimum_order`,
`credit_terms`, plus the three inherited — and `submit()` mints under the 1 Sep
line. `BoughtItem.item_supplier -> Supplier` reaches it, and so does
`movement_out_of -> Location`, because a supplier is a place. The profile names
nine of them: Whitehall Dairy, Terra Nostra Ingredients, Marchetti Cones and six
more, where Marlow's `§4` counted four and named none. The picker is empty today
and that is not the gap — the gap was that no individual could ever exist.

**2 — nothing consumed anything, so material stock could only ever rise. → YES,
answered, with a number.**
Every `StockMovement` carries `movement_out_of` and `movement_into`, both
`-> Location`, so one row is a departure from its origin and an arrival at its
destination at once. `ingredient_out` is the same sum as `ingredient_in` grouped
by the other slot, and `ingredient_on_hand_net` subtracts. Run above: caster
sugar at the dry store is 25 in, 8 out, **17 standing**. Marlow's v1 hung
`stock_quantity` on `Material`, one subject with one winning row, and
`GoodsReceived` added while nothing anywhere took away. Consumption also has a
second home the map states independently: `RecipeLine` says what a page eats,
and `line_stage` says whether it went into the machine or on top of it.

**3 — no pan was minted, so `PanMoved` and `PanPulled` were forms about a thing
that did not exist. → YES, and half the answer is a refusal.**
There is no `Pan` class, no `PanMoved` and no `PanPulled`. The two things
Marlow's `Pan` was trying to be are separated. The **container** is a
`BoughtItem` — `§1.6` prices a steel napoli pan at £38.00 — with `item_name` as
a required identifier, a form of its own, and `movement_ingredient` to move it;
the pan notebook is two movements a line, out to an account and back. **Gelato
in a pan** is deliberately not a thing: it is `movement_flavour` plus
`movement_format` on one line, because no document in the business has ever
written "pistachio in a napoli pan" as one word. So the container is mintable
and the filled pan is a refusal with a reason, which is a different answer from
Marlow's, where neither existed. There is one movement form, and its
`movement_kind` says which of `§3.2`'s fifty-three ways it was.

**4 — no opening stock, no purchase or sell price, no adoption date. → YES, all
four.**
Adoption date: `annotations.valid_from: '2026-06-15T00:00:00+00:00'` in the
sealed file, from `§1.2` — the Monday Marina picked. Purchase price:
`item_pack_price` on `BoughtItem`, with slot-level `unit` metadata `symbol:
GBP`. Sell price: `price_amount` on `ProductPrice`, GBP, carrying the map's one
`unique_keys` on `price_product` + `price_at`, so a product cannot hold two
prices in one column. Opening stock: `StockCount` and `StockCountLine`, ten
fields on the line including `count_line_where`, `count_line_quantity`,
`count_line_unit` and `count_line_written_as` — the cell as it stands on the
paper, kept beside what it resolves to. The 3 Sep decision names Monday 15 June
as the opening position and Tuesday 16 June as milestone one's day.

**5 — four movement classes rendered byte-identical. → YES, and the contrast is
measured, not quoted.**
Marlow's four movement forms were re-rendered and hashed with the header line
stripped: `PanMoved`, `PanPulled`, `ThrownOut` and `TastingGiven` give **one
distinct body between them**. Sorella's 21 forms give **21 distinct bodies**. No
two forms in this map are identical even ignoring the header, and there is only
one movement class for another to be identical with.

Four yes and one yes-with-a-refusal. What none of the five can say is whether
the map is *right* — that is what competency questions are for, and the 3 Sep
line records that they are not written in this lap and are not faked in it.

### Surprising

1. **Subtraction raises where addition lies.** `'0' - '5'` is a `TypeError` and
   `'3' + '4'` is `'34'`. The missing cast the 1 Sep line found is loud on one
   operator and silent on the one beside it, so a map that only ever added would
   have shipped the defect and this one cannot. The instrument that catches it
   is Python's operator table, not anything in this repo.
2. **The generator renders a form for a balance.** `IngredientOnHand` and
   `GelatoOnHand` each get a form with fillable-looking fields, including the two
   aggregates and the net — five and six fields nobody may ever type into. The
   map says they are computed three times over: the class descriptions say so,
   four slots carry an `aggregate` annotation and two an `equals_expression`, and
   neither class carries `entity_class`. The generator reads none of it.
   `submit()` would accept a hand-typed `ingredient_on_hand_net` and the log
   would hold a judgement, which is the second closed finding broken by a form.
3. **Two seals, and the log cannot tell the businesses apart.** Marlow's intent
   and Sorella's differ in `id` and `occurred_at` and in nothing else: both
   `fareza`, both `seal`, both `seal_version`, both noted `sealed draft.yaml as
   v1`, and every assertion of both carries `ontology_version = 'v1'`. `select
   action_name, note, ontology_version, count(*)` returns **one row of 402**. The
   store separation this session was careful to get right in the filesystem does
   not exist in the log at all.
4. **The note answers a question a transcript would not have.** It is 23 KB,
   which is 40% of the map it describes, and almost all of it is choices and
   refusals. A transcript of a real interview would have been the conversation;
   this is an argument. It is better evidence for "why does the map say this"
   than a transcript would have been, and worse evidence for "what did the
   business say". The 29 Aug line called it real evidence, and it is — of the
   author.
5. **Docker Desktop was not running**, and nothing in `make` or in `seal` says
   what to do about that. `make check` starts the container and waits for the
   database; neither starts the engine. The first symptom was `failed to connect
   to the docker API at npipe:...`, which reads like a permissions problem.
6. **The seal costs 1,308 bytes and changes nothing.** Every block scalar becomes
   a quoted flow scalar on the way through `yaml.safe_dump`, so the sealed file
   reads worse than the draft while being structurally identical to it — checked
   field by field with `SchemaView`, not by eye. Anyone diffing a draft against
   the version it became sees the whole file move.

### Proposed `DECISIONS.md` entries

1. The net on a balance class is one `equals_expression` and the aggregate
   annotation stays arithmetic-free. `ingredient_on_hand_net` is
   `'{ingredient_in} - {ingredient_out}'` and `gelato_on_hand_net` is its twin,
   which is the 1 Sep two-problem split — within a row is LinkML's, across rows
   is ours — costing exactly two slots. Measured before being written: cast to
   `decimal` the expressions return `Decimal('-5')`, `Decimal('6')`,
   `Decimal('1')` and `Decimal('0')`; uncast, straight out of `value_literal`,
   the same expression raises `TypeError: unsupported operand type(s) for -:
   'str' and 'str'` where `{a} + {b}` returns `'34'`. So the missing cast is a
   loud failure on subtraction and a silent one on addition, and the caster the
   1 Sep line asks for cannot be justified by the sums alone.
2. A business gets its own version store, chosen by `seal --into`, and the log
   gets no such separation. `business/sorella/v1.yaml` and `business/v1.yaml`
   are two v1s superseding nothing, which is what the 2 Sep retirement of Marlow
   requires and what the default `--into` would have destroyed. What does not
   follow into the kernel is named rather than absorbed:
   `assertion.ontology_version` holds `'v1'` for both businesses, and `intent`
   holds the same actor, agent, `action_name` and note for both seals, so one log
   now carries two businesses and can tell them apart only by which URIs a row
   happens to name.
3. A hand-authored map's provenance note is written once, at the seal, covering
   every sitting, and not once per sitting. `seal` copies one file beside one
   version and a version is one artefact; four notes would need a concatenation
   nobody would re-read, and the thing a reader wants — what was chosen and what
   was refused — is only complete once the map is. The cost is that a choice made
   in the first sitting is recorded three sittings later, which is why the note
   carries a heading for what a later sitting took back.
4. The generator renders a form for a derived class, and that is a defect rather
   than a decision. `IngredientOnHand` and `GelatoOnHand` render fillable forms
   over slots carrying an `aggregate` annotation or an `equals_expression`, and
   `submit()` would write one to the log as a fact. The 21 Aug finding — the log
   holds raw facts and never judgements — is enforced today by nobody typing into
   that form. Whether the filter is the annotations, the absence of
   `entity_class`, or a key in the map is open; that there must be one is not.

### Proposed `OPEN.md` lines

- `[T3]` One log holds two businesses and cannot say which. Marlow's seal and
  Sorella's differ in `intent.id` and `occurred_at` and in nothing else — same
  actor, same agent, same `action_name`, same note `sealed draft.yaml as v1` —
  and every assertion of both carries `ontology_version = 'v1'`, so a group-by
  over those columns returns one row of 402. The version stores are separate
  directories and the kernel has no notion of a store, so `ontology_version` is a
  name unique only within a directory nothing in the log names. Whether a version
  identifier carries its store, whether the intent carries the business, or
  whether one log per business is the answer, is undecided — and multi-tenancy is
  on the stop-list, which is why this is a line and not a proposal. Found 4 Sep
  sealing the second business into the first one's log · blocks: report
- `[T3]` The generator renders a form for a class the map says is computed.
  `IngredientOnHand` and `GelatoOnHand` each render with their aggregates and
  their net as ordinary fields, and `submit()` would accept a typed value for any
  of them and write it as a `human_stated` fact — a judgement in a log that is
  supposed to hold none. The map states the class is derived three separate ways:
  in the class description, in the `aggregate` annotation on four slots and the
  `equals_expression` on two, and by neither class carrying `entity_class`.
  Whether the filter reads the annotations, reads the absence of a type slot, or
  is a key the map states, is undecided. Found 4 Sep rendering all 21 forms ·
  blocks: generation
- `[T3]` An empty picker and an unfillable class are the same sentence. Marlow's
  `received_from offers nothing: the log holds no Supplier` was the defect;
  Sorella's `movement_out_of offers nothing: the log holds no Location` is a
  Tuesday morning before anyone has typed anything, and the two rendered forms
  are indistinguishable. Telling them apart needs a second artefact — whether a
  form for the range class renders, and whether `submit()` will mint one.
  Whether the form should say so, whether a review needs a whole-map render of
  what is fillable, or whether the distinction only matters to a reviewer, is
  undecided. Found 4 Sep answering v1's first gap · blocks: generation
- `[T3]` Slot-level `unit` metadata reaches a second generator and dies there
  too. `item_pack_price` and `price_amount` both declare `symbol: GBP`, and both
  render as a bare `decimal` field with nothing about pounds anywhere on the
  page. The 30 Aug line found the same thing about `gen-owl`; the generator is
  now the second reader to drop it, and it is the one a person looks at. So that
  line is not about one tool. Found 4 Sep rendering `BoughtItem` and
  `ProductPrice` · blocks: generator
- `[T3]` The gap between a map's `valid_from` and its `sealed_at` is eighty days
  here, and the 31 Aug three-hour hole scales with it. Sorella's v1 takes effect
  on 15 June 2026 and was sealed on 3 September, so `resolve_version` returns
  `None` for every `as_of` before the seal — including the whole of milestone
  one's own week, read at the clocks it happened at. `submit()` is unaffected
  because it takes the version off the file it was handed, but any reader asking
  what the map said on 16 June as known on 16 June gets nothing. The 31 Aug line
  raised this as three hours and harmless; it is now a quarter of a year, and it
  covers the only operational day the PoC has. Found 4 Sep resolving the sealed
  store · blocks: report

Nothing was triaged `[T2]`. Two questions were `[T1]` and tried rather than
written down: whether the two named expressions evaluate over the map's own slot
names, and whether the three-column balance runs off the sealed file. Both are
answered above, in one throwaway script outside the repo.

### What was run

| Command | Exit |
|---|---|
| `SchemaView` over the edited draft | 0 — 21 classes, 101 slots, 1 enum, 35 relationships, 10 identifiers, 4 aggregates, 2 `equals_expression`, 1 `unique_keys`, 4 `is_a`, 0 slots without a `slot_uri` |
| `PYTHONIOENCODING=utf-8 gen-owl --no-use-native-uris business/sorella/draft.yaml > build/sorella_draft.ttl` | **0** — 112,541 bytes |
| `PYTHONIOENCODING=utf-8 gen-mermaid-class-diagram -d $TEMP/sorella_mmd4 business/sorella/draft.yaml` | 0 — 21 files, none for the enum |
| `eval_expr` over both `equals_expression`, cast and uncast | 0 — the table above; the uncast case raises, which is the result |
| `seal`'s pure path with no connection: `_validate`, `_slot_ranges`, `_facts`, `_valid_from`, `_flat`, `_transcript`, `_next_version`, `_sealed_document`, `_validate` again | 0 — 101 URIs, 0 facts, `v1`, supersedes `None`, 56,613 bytes of sealed text that re-validates |
| `python components/seal/seal.py business/sorella/draft.yaml --actor fareza --into business/sorella` | **0** — `v1`, 101 entities minted, 101 assertions, intent `8fc11510` |
| `md5sum business/sorella/draft.txt business/sorella/v1.txt` | 0 — identical, `bfc4b409...` |
| `load_versions` / `resolve_version` over both stores | 0 — two v1s, neither superseding; `None` before the seal instant and before `valid_from` |
| `SchemaView` draft-against-sealed, field by field | 0 — **no structural difference**, schema description equal |
| `PYTHONIOENCODING=utf-8 gen-owl --no-use-native-uris business/sorella/v1.yaml` | 0 — 112,699 bytes, 0 `rdfs:domain`, 1 `owl:hasKey` |
| `grep -n "business/" components/generator/generate.py` | 0 — 5 hits, all in the docstring's usage block or an `argparse` help string. **No live code path, nothing changed** |
| 21 × `generate.py form business/sorella/v1.yaml CLASS --out build/sorella_forms/CLASS.txt` | 0 each — 137 fields, 41 pickers, 14 required |
| 21 × `generate.py table business/sorella/v1.yaml CLASS --valid-at 2026-06-16T23:00:00Z --as-of 2026-09-03T23:00:00Z --verify` | 0 each — 0 rows every time, `--verify` clean |
| `md5sum` over the 21 form bodies, header stripped | 0 — **21 distinct** |
| 4 × `generate.py form business/v1.yaml` for `PanMoved`, `PanPulled`, `ThrownOut`, `TastingGiven`, into the scratchpad | 0 each — **1 distinct body between the four** |
| `generate.py form business/v1.yaml GoodsReceived` | 0 — `received_from offers nothing: the log holds no Supplier` |
| `trial_net.py` in the scratchpad, against the sealed map, no database | 0 — output above |
| `make check` | **0** — **64 tests passed**, replay byte-identical twice, 5,334 bytes both times |
| `git diff --stat HEAD -- business/sorella/profile.md` | 0 — **empty. The profile is untouched** |
| `git status --porcelain` | ` M business/sorella/draft.yaml`, `?? business/sorella/draft.txt`, `?? business/sorella/v1.txt`, `?? business/sorella/v1.yaml`. **Nothing under `business/` outside `business/sorella/` added, moved or deleted** |
| `psql -d uniti`, intents and assertion counts | 0 — 2 intents, 402 assertions: Marlow's 301 of 31 Aug 2025 and Sorella's 101 of 3 Sep 2026 |
| `docker compose up -d`, after starting Docker Desktop by hand | 0 |

`make check` collected 64 and passed 64. This session writes no code and adds no
test.

**No two clauses of the done condition conflicted.** One pair had to be ordered
rather than reconciled: `make check` reseeds `uniti_check` and the seal writes to
the working log `uniti`, which are different databases, so running the check
after the seal destroys nothing. That was verified afterwards rather than
assumed — 402 assertions still in `uniti` once `make check` had finished.

## 2026-09-04 — Sorella's master data, entered through the forms

The 1 Sep onboarding order's second step. The map was sealed yesterday and the
log held 101 URI registrations and no fact; it now holds **197 entities and
1,215 assertions** written by 197 `submit()` calls, all of them inside the
Monday-and-Tuesday boundary. Nothing under `business/` was touched, nothing was
sealed, and no value was submitted for a slot the map computes.

Two things were settled before the bulk of the entry, because both could have
made it worthless.

### 1 — `resolve_version` and a June date. The balance computes.

**The answer is yes for the read the balance actually needs, and no for the
read the item feared, and the second is correct rather than broken.**

`resolve_version` takes two clocks, not one. Sorella's v1 has
`valid_from 2026-06-15T00:00:00Z` and `sealed_at 2026-09-03T20:14:38Z` — eighty
days apart. Six pairs were resolved against `business/sorella`:

| `valid_at` | `as_of` | returns |
|---|---|---|
| 2026-06-15T00:00:00Z | 2026-06-15T00:00:00Z | `None` |
| 2026-06-16T23:00:00Z | 2026-06-16T23:00:00Z | `None` |
| 2026-06-16T23:00:00Z | 2026-09-03T23:00:00Z | **v1** |
| 2026-06-16T23:00:00Z | 2026-09-04T12:00:00Z | **v1** |
| 2026-06-14T23:59:59Z | 2026-09-04T12:00:00Z | `None` |
| 2026-09-04T12:00:00Z | 2026-09-04T12:00:00Z | **v1** |

The hole is only on the diagonal. A reader asking *what did the map say on
16 June, as known on 16 June* gets nothing, and that is the honest answer: on
16 June the business had not been described yet. A reader asking *what does the
map say today about how the world stood on 16 June* — which is what a balance,
a report and a shrinkage figure all ask — gets v1. The `None` is a fact about
the map, not a defect, and the 4 Sep `[T3]` line that raised it can be read
this way: the eighty days cost nothing that milestone one needs.

That was established by argument, so it was then run end to end. A throwaway
`june_balance.py` outside the repo resolves the version at a pair of clocks,
reads the two `aggregate` annotations and the `equals_expression` off whatever
file the resolver hands back, groups `StockMovement` out of the log through
`resolve_single` at the same clocks, and evaluates the net. Nothing in
`components/` does this yet; the script is the shape `report` will have.

At `valid_at 2026-06-16T23:00:00Z`, `as_of 2026-06-16T23:00:00Z` it exits 1 with

```
resolve_version -> None

No map applies at these clocks. Nothing downstream can run:
the balance has no column list, so it is not that it comes out
empty, it is that there is nothing to come out.
```

At `valid_at 2026-06-16T23:00:00Z`, `as_of 2026-09-04T12:00:00Z` it exits 0:

```
resolve_version -> v1
map      v1.yaml  sealed 2026-09-03T20:14:38.201488+00:00

IngredientOnHand   net = {ingredient_in} - {ingredient_out}
  grouped by ['ingredient_on_hand', 'ingredient_where'], over 0 StockMovement rows
  0 rows

GelatoOnHand   net = {gelato_in} - {gelato_out}
  grouped by ['gelato_flavour', 'gelato_format', 'gelato_where'], over 0 StockMovement rows
  0 rows
```

Zero rows because the log holds no movement — that is step three, not a
failure here. So that the run would prove the path and not the sum, a
`--selftest` pushes four movements **that are made up in the script and never
written** through the same grouping and the same expression:

```
--- selftest: four fabricated movements, nothing written ---

IngredientOnHand   net = {ingredient_in} - {ingredient_out}   by ['ingredient_on_hand', 'ingredient_where']
  Caster sugar | Dry store                         in     25  out    9.2  net   15.8

GelatoOnHand   net = {gelato_in} - {gelato_out}   by ['gelato_flavour', 'gelato_format', 'gelato_where']
  pistachio | 5 L napoli pan | Holding freezer     in      3  out      1  net      2
```

**So: the three-column balance can be computed for a June date, off the sealed
map, at the clocks milestone one happens at. What it lacks is movements.**
Nothing needs to change for that, and nothing under `components/` was changed.

One thing had to be got right inside the script and is worth writing down,
because it is a rule about the map rather than about the script. The two
aggregates are **two group-bys, not one**. `ingredient_in` keys
`ingredient_where` off `movement_into` and `ingredient_out` keys the same
column off `movement_out_of`; joining them on the balance's own key slots is
what makes a pallet an arrival at the dry store and a departure from the
supplier in one row. Read with a single mapping — the first mistake this
session made — the same four movements give six rows, three of them keyed
`None`, and two of the six carry a net with the wrong sign. The map is right;
a reader that ignores the per-aggregate `by` block is not.

### 2 — Tuesday's consumption is derived, not recorded.

**The profile settles it in one cell**, `§3.2`, *Inside the kitchen*, the first
row:

> | Ingredients to the machine | Dry store, Walk-in chiller, Ingredient freezer → the pasteuriser or the bench | Tins opened, sacks scooped, a bag of milk lifted out and weighed, a pail of glucose warmed. | **Nothing.** No document in this business records an ingredient leaving a shelf. | — |

`§4.3` bears it out. Tuesday states production twice and consumption never: the
pasteuriser block is *"07:10, 55 kg white base. 09:30, 55 kg white base. 11:00,
30 kg sorbet syrup"* and the batch table's only quantity column is *"Mix into
freezer — 12.0 kg"*. Not one line says how much sugar, milk or pistachio paste
left a shelf. The single exception proves the rule and is unweighed: *"Three
trays of Kingsdown strawberries were hulled for 0842. The hulls went in the
kitchen bin and were not weighed."*

So an ingredient consumption figure for Tuesday exists only as `batch_mix_quantity`
× a recipe, which means **recipes are master data the balance eventually needs**.
They are not entered this session, and the reason is the boundary rather than an
oversight: `§4.1` and `§4.3` name no recipe page. `§4.3` names batch *flavours*
and `Batch` has no slot for a recipe — `Flavour.made_recipe` is optional and
naming it would have minted twenty-two `Recipe` entities out of `§2.3`, which is
the eighty-bought-items failure wearing a different noun. It is written down
here as the next thing that will be needed rather than taken now.

This also means the derivation is a **second** thing the map states and no built
code reads, beside the aggregates: a consumption number for Tuesday is
`RecipeLine.line_quantity` scaled by `batch_mix_quantity ÷ recipe_basis_quantity`,
and nothing in `components/` walks that.

### The boundary, and how it was applied

The rule used, stated once and applied without exception:

> An entity is in scope when `§4.1` or `§4.3` names it **individually** — by the
> name that identifies it, or unambiguously by the words the day uses for it.

A group naming is not an individual naming. That is what keeps the thirty-one
wholesale accounts out: `§4.1`'s *"The 31 wholesale accounts | Every one of them
is a place a pan can be. Nobody drove round"* names the class and not one
member, and `§4.3`'s van run names five. The same rule keeps the nine suppliers
out and lets five in, and it is the reason sixteen bought items were entered
with no supplier — see below. Applied the other way it would have admitted all
thirty-one accounts and all nine suppliers off two table rows, which is the
outcome the item was written to prevent.

**The boundary bites very unevenly, and that is the session's most useful
number.** It cuts wholesale accounts from 31 to 6 and flavours from 25 to 18.
It cuts bought items from 80 to **77**. `§4.1`'s six count sheets walk the whole
building, so the opening count *is* most of `§1.6`: the three it leaves out are
exactly the three `§4.1` says it left out — *"No line was written for panettone,
figs or rhubarb. Three seasonals are out of season."* The premise that milestone
one touches a fraction of the eighty is true of the accounts and false of the
items.

### What was entered

197 entities, 1,215 assertions, one `submit()` call each, `valid_from
2026-06-15T00:00:00Z`, actor `fareza`, `recorded_at` left to default. 154 are
named by `§4.1` and 43 by `§4.3`.

| class | entities | assertions |
|---|---|---|
| `BoughtItem` | 77 | 593 |
| `Unit` | 26 | 104 |
| `InternalLocation` | 22 | 109 |
| `SoldProduct` | 21 | 118 |
| `Flavour` | 18 | 94 |
| `Location` | 9 | 36 |
| `Person` | 9 | 45 |
| `WholesaleAccount` | 6 | 42 |
| `Supplier` | 5 | 50 |
| `Ingredient` | 4 | 24 |

Ten classes of the map's twenty-one. The other eleven are dealt with under
*what had nowhere to go* below.

The full list, every entity against the `§4.1` or `§4.3` line that names it, is
in `build/sorella_master_entered.txt` and reproduced here.

**Unit — 26**

| uri | § | the line that names it |
|---|---|---|
| `sorella:unit_gram` | 4.1 | dry store: Digestive biscuits, 400 g pack \| 17 |
| `sorella:unit_kilogram` | 4.1 | dry store: Caster sugar, 25 kg sack \| 4, one of them open - 9.2 kg |
| `sorella:unit_litre` | 4.1 | walk-in chiller: Whole milk, 10 L bag-in-box \| 8 |
| `sorella:unit_millilitre` | 4.1 | packaging mezzanine: 125 ml mini tub with lid, sleeve of 100 \| 9 |
| `sorella:unit_each` | 4.1 | packaging mezzanine: 500 ml lid, printed, case of 1,000 \| 1, broken into - 20 lids, counted out on the bench |
| `sorella:unit_bag` | 4.1 | dry store: Skimmed milk powder, 25 kg bag \| 1, open - 12.4 kg |
| `sorella:unit_can` | 4.1 | walk-in chiller: Cream 38%, 5 L jerry can \| 3, one open |
| `sorella:unit_sack` | 4.1 | dry store: Dextrose, 25 kg sack \| 2, one open - 13.8 kg |
| `sorella:unit_pail` | 4.1 | dry store: Inverted sugar, 14 kg pail \| 2, one open |
| `sorella:unit_bucket` | 4.1 | walk-in chiller: Aged white base, 25 L bucket \| 1, part - about a third |
| `sorella:unit_carton` | 4.3 | deliveries received, Terra Nostra: 1 x carton Base 50 (10 x 2 kg) |
| `sorella:unit_tin` | 4.1 | dry store: Sicilian pistachio paste, 3.5 kg tin \| 1 sealed, 1 open |
| `sorella:unit_jar` | 4.1 | dry store: Amarena cherries in syrup, 2.6 kg jar \| 4 |
| `sorella:unit_box` | 4.1 | dry store: Dark chocolate 70% callets, 10 kg box \| 1 sealed, 1 open |
| `sorella:unit_case` | 4.1 | packaging mezzanine: 500 ml tub, case of 500 \| 2, one broken into |
| `sorella:unit_sleeve` | 4.1 | packaging mezzanine: Waffle cones, sleeve of 90 \| 21 |
| `sorella:unit_pack` | 4.1 | dry store: Digestive biscuits, 400 g pack \| 17 |
| `sorella:unit_tray` | 4.1 | walk-in chiller: Eggs, medium free range, tray of 30 \| 2 |
| `sorella:unit_punnet` | 4.1 | walk-in chiller: Strawberries, 2 kg punnet \| 2 |
| `sorella:unit_tub` | 4.1 | ingredient freezer: Fruit puree, mango, 1 kg tub \| 16 |
| `sorella:unit_pan` | 4.1 | holding freezer: Fior di latte, 5 L pan \| 6 |
| `sorella:unit_well` | 4.1 | Cotham cabinet: Twenty-four wells, written as fractions of a pan by eye |
| `sorella:unit_scoop` | 4.3 | sold, Cotham Hill: 268 single scoop, 141 double scoop, 22 triple scoop |
| `sorella:unit_drum` | 4.1 | dry store: Sanitiser, no-rinse, 5 L drum \| 2 |
| `sorella:unit_roll` | 4.1 | dry store: Blue roll, roll \| 9 |
| `sorella:unit_bottle` | 4.1 | dry store: Peppermint extract, 500 ml bottle \| 2, one part-used |

**Location — 9**

| uri | § | the line that names it |
|---|---|---|
| `sorella:loc_the_walk_in_customer` | 4.1 | places that were not counted: The walk-in customer, comps, donations, tastings, staff, Marina's house, and the three bins |
| `sorella:loc_comps` | 4.3 | given away: 4 comped cones at Gloucester Road. 2 were rung on the comp key |
| `sorella:loc_donations` | 4.3 | given away: 30 x 125 ml minis to the St Werburgh's primary school summer fair |
| `sorella:loc_tastings` | 4.3 | given away: 1 x 5 L pan of pistachio taken out at 15:00 by Marina in the cool box, to a tasting at a hotel on the Downs |
| `sorella:loc_staff` | 4.3 | given away: Staff scoops: seven people on shift across the two shops, plus four in the kitchen |
| `sorella:loc_marina_s_house` | 4.3 | given away: 1 x 5 L pan of vanilla taken home by Marina on her way to the wedding |
| `sorella:loc_the_kitchen_bin` | 4.3 | thrown out: Batch 2026-0844, salted caramel: 12.0 kg of churned mix, binned |
| `sorella:loc_the_cotham_bin` | 4.3 | thrown out: Cotham cabinet at close: 3 part pans past the 3-day rule. Scraped out and binned |
| `sorella:loc_the_gloucester_road_bin` | 4.3 | thrown out: Gloucester Road at close: 1 part pan of biscuit, about half, binned |

**InternalLocation — 22**

| uri | § | the line that names it |
|---|---|---|
| `sorella:loc_production_kitchen` | 4.3 | evening stock count - production unit, 21:10 |
| `sorella:loc_cotham_hill` | 4.1 | Aoife took Cotham Hill with Yusuf reading the cabinet out to her |
| `sorella:loc_gloucester_road` | 4.1 | Priya took Gloucester Road on her own |
| `sorella:loc_dry_store` | 4.1 | The production kitchen - the dry store. Dan, 05:55 to 07:10 |
| `sorella:loc_walk_in_chiller` | 4.1 | The production kitchen - walk-in chiller. Dan, 07:10 to 08:05 |
| `sorella:loc_ingredient_freezer` | 4.1 | The production kitchen - ingredient freezer. Tomas, 06:20 to 06:50 |
| `sorella:loc_blast_freezer` | 4.1 | The production kitchen - blast freezer. Tomas, 07:50 |
| `sorella:loc_holding_freezer` | 4.1 | The production kitchen - holding freezer. Tomas, 06:20 to 07:45 |
| `sorella:loc_packaging_mezzanine` | 4.1 | The production kitchen - packaging mezzanine. Jordan, 08:15 to 10:20 |
| `sorella:loc_office_cupboard` | 4.1 | The production kitchen - office cupboard. Jordan, 10:20 to 10:30 |
| `sorella:loc_cotham_cabinet` | 4.1 | Cotham cabinet. Aoife, 07:30 to 07:55, with Yusuf reading the wells out |
| `sorella:loc_cotham_back_freezer_1` | 4.1 | 5 L pan - Cotham back freezer 1 and Cotham back freezer 2 counted as one line \| 16 |
| `sorella:loc_cotham_back_freezer_2` | 4.1 | 5 L pan - Cotham back freezer 1 and Cotham back freezer 2 counted as one line \| 16 |
| `sorella:loc_cotham_under_counter_fridge` | 4.1 | Cotham under-counter fridge - whole milk, coffee bar, 2 L bottle \| 5, one open |
| `sorella:loc_cotham_shelf_unit` | 4.1 | Cotham shelf unit - waffle cones, sleeve of 90 \| 3, one part |
| `sorella:loc_gloucester_road_cabinet` | 4.1 | Gloucester Road cabinet, 16 wells \| 13 wells with something in them, 3 empty |
| `sorella:loc_gloucester_road_under_counter_freezer` | 4.1 | Gloucester Road under-counter freezer, 5 L pan \| 6 |
| `sorella:loc_gloucester_road_shelves` | 4.1 | Gloucester Road shelves - waffle cones, sleeve of 90 \| 2 |
| `sorella:loc_the_van` | 4.1 | The van. Jordan, 06:05, before anything else |
| `sorella:loc_the_cool_box` | 4.1 | places that were not counted: Marina's cool box \| At her house, in the boot |
| `sorella:loc_the_trailer` | 4.1 | The trailer. Jordan, 10:35. Parked at the kitchen and switched off since September |
| `sorella:loc_the_container` | 4.1 | places that were not counted: The container, Avonmouth |

**Supplier — 5**

| uri | § | the line that names it |
|---|---|---|
| `sorella:loc_whitehall_dairy` | 4.3 | deliveries received: 06:40 \| Whitehall Dairy \| 12 x 10 L bag-in-box whole milk; 8 x 5 L jerry can cream 38% |
| `sorella:loc_terra_nostra_ingredients` | 4.3 | deliveries received: 11:20 \| Terra Nostra Ingredients \| 4 x 3.5 kg tins pistachio paste; 2 x 5 kg tins hazelnut paste |
| `sorella:loc_severn_catering_supplies` | 4.3 | deliveries received: - \| Severn Catering Supplies \| Did not arrive. The Thursday drop was moved and nobody told the kitchen |
| `sorella:loc_avonside_packaging` | 4.3 | deliveries received: 14:05 \| Avonside Packaging \| 4 cases 500 ml tubs (500 per case); 2 cases 500 ml lids (1,000 per case) |
| `sorella:loc_kingsdown_fruit_farm` | 4.3 | deliveries received: 08:15 \| Kingsdown Fruit Farm \| 14 x 2 kg punnets of strawberries, left at the roller door before anybody was in |

**WholesaleAccount — 6**

| uri | § | the line that names it |
|---|---|---|
| `sorella:loc_caffe_umberto` | 4.3 | wholesale delivered: Caffe Umberto, Clifton \| 6 x 5 L pan \| 5 empty collected |
| `sorella:loc_bar_trentanove` | 4.3 | wholesale delivered: Bar Trentanove \| 3 x 5 L pan \| 0 empty collected |
| `sorella:loc_cleeve_coffee_house` | 4.3 | wholesale delivered: Cleeve Coffee House, Bishopston \| 3 x 5 L pan \| 4 empty collected |
| `sorella:loc_the_hollow` | 4.3 | wholesale delivered: The Hollow, Old City \| 4 x 1.5 L catering tub vanilla |
| `sorella:loc_wapping_wharf_kitchen` | 4.3 | wholesale delivered: Wapping Wharf Kitchen \| 4 x 5 L pan; 24 x 500 ml tub assorted |
| `sorella:loc_the_old_bakehouse` | 4.1 | The van: The Old Bakehouse was shut and Steve did not go back |

**Person — 9**

| uri | § | the line that names it |
|---|---|---|
| `sorella:person_marina_devlin` | 4.1 | Marina walked round, wrote the notes at the foot, and rang Whitehall at five past eight |
| `sorella:person_dan_farrugia` | 4.1 | Dan took the dry store and the walk-in chiller |
| `sorella:person_tomas_nowicki` | 4.1 | Tomas the three freezers |
| `sorella:person_rekha_pillai` | 4.3 | produced: Rekha drew down a pistachio pan and a dark chocolate pan and stood both back part-used |
| `sorella:person_jordan_hale` | 4.1 | Jordan the van, the packaging mezzanine and the office cupboard |
| `sorella:person_steve_corrigan` | 4.1 | The 31 wholesale accounts: Steve was asked and read his notebook back standing at the van |
| `sorella:person_aoife_brennan` | 4.1 | Aoife took Cotham Hill with Yusuf reading the cabinet out to her |
| `sorella:person_yusuf_adeyemi` | 4.1 | Aoife took Cotham Hill with Yusuf reading the cabinet out to her |
| `sorella:person_priya_shah` | 4.1 | Priya took Gloucester Road on her own |

**Flavour — 18**

| uri | § | the line that names it |
|---|---|---|
| `sorella:flavour_fior_di_latte` | 4.1 | holding freezer: Fior di latte, 5 L pan \| 6 |
| `sorella:flavour_stracciatella` | 4.1 | holding freezer: Stracciatella, 5 L pan \| 4 |
| `sorella:flavour_pistachio` | 4.1 | holding freezer: Pistachio, 5 L pan \| 6 |
| `sorella:flavour_hazelnut` | 4.1 | holding freezer: Hazelnut, 5 L pan \| 3 |
| `sorella:flavour_dark_chocolate` | 4.1 | holding freezer: Dark chocolate, 5 L pan \| 4 |
| `sorella:flavour_salted_caramel` | 4.1 | holding freezer: Salted caramel, 5 L pan \| 3 |
| `sorella:flavour_vanilla` | 4.1 | holding freezer: Vanilla, 5 L pan \| 5 |
| `sorella:flavour_coffee` | 4.1 | holding freezer: Coffee, 5 L pan \| 3 |
| `sorella:flavour_mint_choc_chip` | 4.1 | holding freezer: Mint choc chip, 5 L pan \| 2 |
| `sorella:flavour_biscuit` | 4.1 | holding freezer: Biscuit, 5 L pan \| 3 |
| `sorella:flavour_strawberry_sorbet` | 4.1 | holding freezer: Strawberry sorbet, 5 L pan \| 2 |
| `sorella:flavour_lemon_sorbet` | 4.1 | holding freezer: Lemon sorbet, 5 L pan \| 3 |
| `sorella:flavour_mango_sorbet` | 4.1 | holding freezer: Mango sorbet, 5 L pan \| 4 |
| `sorella:flavour_raspberry_sorbet` | 4.1 | holding freezer: Raspberry sorbet, 5 L pan \| 4 |
| `sorella:flavour_elderflower_sorbet` | 4.1 | holding freezer: Elderflower sorbet, 5 L pan \| 4 |
| `sorella:flavour_local_strawberry` | 4.1 | Cotham cabinet: Local strawberry \| 3/4 \| Eyeballed |
| `sorella:flavour_amarena_cherry` | 4.1 | Cotham cabinet: Amarena cherry \| 1/4 \| Eyeballed |
| `sorella:flavour_coconut` | 4.1 | Cotham cabinet: Coconut \| Well empty, cabinet card still in it |

**Ingredient — 4**

| uri | § | the line that names it |
|---|---|---|
| `sorella:item_white_base` | 4.3 | produced: Pasteuriser runs: 07:10, 55 kg white base. 09:30, 55 kg white base |
| `sorella:item_sorbet_syrup` | 4.3 | produced: Pasteuriser runs: 11:00, 30 kg sorbet syrup |
| `sorella:item_biscuit_base` | 4.1 | ingredient freezer: Biscuit base, lidded tub \| 1, about half |
| `sorella:item_coffee_brew` | 4.1 | walk-in chiller: Coffee brew, lidded bucket \| 1, about 2 L, steeped Friday night |

**BoughtItem — 77**

| uri | § | the line that names it |
|---|---|---|
| `sorella:item_caster_sugar_sucrose` | 4.1 | dry store: Caster sugar, 25 kg sack \| 4, one of them open - 9.2 kg |
| `sorella:item_dextrose` | 4.1 | dry store: Dextrose, 25 kg sack \| 2, one open - 13.8 kg |
| `sorella:item_skimmed_milk_powder` | 4.1 | dry store: Skimmed milk powder, 25 kg bag \| 1, open - 12.4 kg |
| `sorella:item_glucose_syrup_de38` | 4.1 | dry store: Glucose syrup DE38, 12.5 kg pail \| 1, open. Not lifted |
| `sorella:item_inverted_sugar` | 4.1 | dry store: Inverted sugar, 14 kg pail \| 2, one open |
| `sorella:item_base_50_stabiliser` | 4.1 | dry store: Base 50 stabiliser, 2 kg bag \| 4, one of them open with about a kilo in it |
| `sorella:item_sicilian_pistachio_paste` | 4.1 | dry store: Sicilian pistachio paste, 3.5 kg tin \| 1 sealed, 1 open |
| `sorella:item_hazelnut_paste` | 4.1 | dry store: Hazelnut paste, 5 kg tin \| 1 sealed, 1 open |
| `sorella:item_cocoa_22_24` | 4.1 | dry store: Cocoa 22/24, 5 kg bag \| 1 sealed, 1 open - about 2 kg in it |
| `sorella:item_dark_chocolate_70_callets` | 4.1 | dry store: Dark chocolate 70% callets, 10 kg box \| 1 sealed, 1 open - about 6 kg |
| `sorella:item_vanilla_bean_paste` | 4.1 | dry store: Vanilla bean paste, 1 kg tub \| 2, one open |
| `sorella:item_salted_caramel_variegate` | 4.1 | dry store: Salted caramel variegate, 3 kg pail \| 3, one open |
| `sorella:item_peppermint_extract` | 4.1 | dry store: Peppermint extract, 500 ml bottle \| 2, one part-used |
| `sorella:item_amarena_cherries_in_syrup` | 4.1 | dry store: Amarena cherries in syrup, 2.6 kg jar \| 4 |
| `sorella:item_amaretti_biscuits` | 4.1 | dry store: Amaretti biscuits, 1 kg box \| 2 |
| `sorella:item_pumpkin_puree` | 4.1 | dry store: Pumpkin puree, 3 kg tin \| 2, both dated last October |
| `sorella:item_marsala` | 4.1 | dry store: Marsala, 750 ml bottle \| 1, part-used, from December |
| `sorella:item_sea_salt_fine` | 4.1 | dry store: Sea salt, fine, 1 kg tub \| 3 |
| `sorella:item_digestive_biscuits` | 4.1 | dry store: Digestive biscuits, 400 g pack \| 17 |
| `sorella:item_honey_clear` | 4.1 | dry store: Honey, clear, 3 kg tub \| 2, one open |
| `sorella:item_ground_cinnamon` | 4.1 | dry store: Ground cinnamon, 500 g tub \| 1 |
| `sorella:item_lemons` | 4.1 | dry store: Lemons, 5 kg net bag \| 2 |
| `sorella:item_lemon_juice` | 4.1 | dry store: Lemon juice, bottled, 1 L bottle \| 6 |
| `sorella:item_elderflower_cordial` | 4.1 | dry store: Elderflower cordial, 1 L bottle \| 5 |
| `sorella:item_coffee_beans_espresso_blend` | 4.1 | dry store: Coffee beans, espresso blend, 1 kg bag \| 1, open - carried back from Cotham |
| `sorella:item_sanitiser_no_rinse` | 4.1 | dry store: Sanitiser, no-rinse, 5 L drum \| 2 |
| `sorella:item_cip_alkaline_detergent` | 4.1 | dry store: CIP alkaline detergent, 10 L drum \| 1, part-used |
| `sorella:item_blue_roll` | 4.1 | dry store: Blue roll, roll \| 9 |
| `sorella:item_nitrile_gloves` | 4.1 | dry store: Nitrile gloves, box of 100 \| 6 |
| `sorella:item_bin_liners_heavy_duty` | 4.1 | dry store: Bin liners, roll of 25 \| 4 |
| `sorella:item_freezer_label_blank` | 4.1 | dry store: Freezer label, roll of 500 \| 2, one part-used |
| `sorella:item_whole_milk_kitchen` | 4.1 | walk-in chiller: Whole milk, 10 L bag-in-box \| 8, one of them open with about 4 kg left |
| `sorella:item_whipping_cream_38` | 4.1 | walk-in chiller: Cream 38%, 5 L jerry can \| 3, one open - about 2.6 kg |
| `sorella:item_strawberries` | 4.1 | walk-in chiller: Strawberries, 2 kg punnet \| 2 |
| `sorella:item_ricotta` | 4.1 | walk-in chiller: Ricotta, 2 kg tub \| 1 |
| `sorella:item_cream_cheese` | 4.1 | walk-in chiller: Cream cheese, 2 kg tub \| 1 |
| `sorella:item_eggs_medium_free_range` | 4.1 | walk-in chiller: Eggs, medium free range, tray of 30 \| 2 |
| `sorella:item_basil_fresh` | 4.1 | walk-in chiller: Basil, fresh, 100 g pack \| A line was written and struck through. None found |
| `sorella:item_fruit_puree_strawberry` | 4.1 | ingredient freezer: Fruit puree, strawberry, 1 kg tub \| 9 |
| `sorella:item_fruit_puree_raspberry` | 4.1 | ingredient freezer: Fruit puree, raspberry, 1 kg tub \| 12 |
| `sorella:item_fruit_puree_mango` | 4.1 | ingredient freezer: Fruit puree, mango, 1 kg tub \| 16 |
| `sorella:item_fruit_puree_passionfruit` | 4.1 | ingredient freezer: Fruit puree, passionfruit, 1 kg tub \| 4 |
| `sorella:item_fruit_puree_peach` | 4.1 | ingredient freezer: Fruit puree, peach, 1 kg tub \| 6 |
| `sorella:item_fruit_puree_blood_orange` | 4.1 | ingredient freezer: Fruit puree, blood orange, 1 kg tub \| 2 |
| `sorella:item_fruit_puree_pink_grapefruit` | 4.1 | ingredient freezer: Fruit puree, pink grapefruit, 1 kg tub \| 3 |
| `sorella:item_coconut_puree` | 4.1 | ingredient freezer: Coconut puree, 1 kg tub \| 5 |
| `sorella:item_freeze_dried_raspberry_pieces` | 4.1 | ingredient freezer: Freeze-dried raspberry pieces, 400 g tub \| 2, one open |
| `sorella:item_500_ml_tub` | 4.1 | packaging mezzanine: 500 ml tub, case of 500 \| 2, one broken into - about 300 left in it |
| `sorella:item_500_ml_lid_printed` | 4.1 | packaging mezzanine: 500 ml lid, printed, case of 1,000 \| 1, broken into - 20 lids |
| `sorella:item_125_ml_mini_tub_with_lid` | 4.1 | packaging mezzanine: 125 ml mini tub with lid, sleeve of 100 \| 9, one open with about 40 in it |
| `sorella:item_1_5_l_catering_tub_with_lid` | 4.1 | packaging mezzanine: 1.5 L catering tub with lid, case of 50 \| 1, part - 22 |
| `sorella:item_waffle_cones` | 4.1 | packaging mezzanine: Waffle cones, sleeve of 90 \| 21 - five cases and a loose sleeve |
| `sorella:item_wafer_cones` | 4.1 | packaging mezzanine: Wafer cones, sleeve of 120 \| 14 |
| `sorella:item_gelato_cup_two_scoop` | 4.1 | packaging mezzanine: Gelato cup, two scoop, case of 1,000 \| 2 |
| `sorella:item_gelato_cup_three_scoop` | 4.1 | packaging mezzanine: Gelato cup, three scoop, case of 1,000 \| 1 |
| `sorella:item_gelato_spoon` | 4.1 | packaging mezzanine: Gelato spoon, box of 1,000 \| 4 |
| `sorella:item_tasting_spoon` | 4.1 | packaging mezzanine: Tasting spoon, case of 5,000 \| 1, open. Nobody has ever counted one out |
| `sorella:item_napkin_2_ply` | 4.1 | packaging mezzanine: Napkin, 2-ply, pack of 500 \| 19 |
| `sorella:item_takeaway_bag_paper_handled` | 4.1 | packaging mezzanine: Takeaway bag, case of 250 \| 2, one open |
| `sorella:item_cake_box_8` | 4.1 | packaging mezzanine: Cake box, 8", case of 50 \| 1, part - about 20 |
| `sorella:item_cake_board_8` | 4.1 | packaging mezzanine: Cake board, 8", case of 100 \| 1, part - about 55 |
| `sorella:item_napoli_pan_polycarbonate_5_l` | 4.1 | packaging mezzanine: Napoli pan, polycarbonate, new, case of 24 \| 1 |
| `sorella:item_printed_sleeve_500_ml` | 4.1 | office cupboard: Printed sleeve, 500 ml, case of 1,000 \| 1, open - about 400 |
| `sorella:item_napoli_pan_stainless_5_l` | 4.1 | empty pans, by the fill bench: Napoli pan, stainless 5 L, empty \| 34 |
| `sorella:item_whole_milk_coffee_bar` | 4.1 | Cotham under-counter fridge - whole milk, coffee bar, 2 L bottle \| 5, one open |
| `sorella:item_oat_milk_barista` | 4.1 | Cotham Hill: Oat milk, barista, 1 L carton \| 3 |
| `sorella:item_canned_soft_drink` | 4.1 | Cotham Hill: Canned soft drink \| 31 |
| `sorella:item_bottled_water_500_ml` | 4.1 | Cotham Hill: Bottled water, 500 ml \| 18 |
| `sorella:item_vanilla_syrup` | 4.1 | Cotham Hill: Vanilla syrup, 1 L bottle \| 1, part-used |
| `sorella:item_hazelnut_syrup` | 4.1 | Cotham Hill: Hazelnut syrup, 1 L bottle \| 1, part-used |
| `sorella:item_caramel_syrup` | 4.1 | Cotham Hill: Caramel syrup, 1 L bottle \| 2, one part-used |
| `sorella:item_hot_chocolate_powder` | 4.1 | Cotham Hill: Hot chocolate powder, 2 kg tub \| 1, part-used |
| `sorella:item_paper_cup_8_oz` | 4.1 | Cotham Hill: Paper cup, 8 oz \| About 700 |
| `sorella:item_paper_cup_12_oz` | 4.1 | Cotham Hill: Paper cup, 12 oz \| About 500 |
| `sorella:item_paper_cup_lid` | 4.1 | Cotham Hill: Paper cup lid \| About 900 |
| `sorella:item_wooden_stirrer` | 4.1 | Cotham Hill: Wooden stirrer \| 1 box, part-used |
| `sorella:item_dry_ice_pellets` | 4.1 | The van: Dry ice, 10 kg insulated tub \| 1, part-used, bought Saturday |

**SoldProduct — 21**

| uri | § | the line that names it |
|---|---|---|
| `sorella:product_single_scoop` | 4.3 | sold, Cotham Hill: 268 single scoop |
| `sorella:product_double_scoop` | 4.3 | sold, Cotham Hill: 141 double scoop |
| `sorella:product_triple_scoop` | 4.3 | sold, Cotham Hill: 22 triple scoop |
| `sorella:product_waffle_cone_instead_of_wafer` | 4.3 | sold, Cotham Hill: 118 waffle-cone supplements |
| `sorella:product_500_ml_retail_tub` | 4.3 | sold, Cotham Hill: 34 x 500 ml tub |
| `sorella:product_125_ml_mini_tub` | 4.3 | sold, Cotham Hill: 6 x 125 ml mini |
| `sorella:product_1_5_l_catering_tub` | 4.3 | wholesale delivered: The Hollow, Old City \| 4 x 1.5 L catering tub vanilla |
| `sorella:product_5_l_napoli_pan` | 4.1 | holding freezer: Fior di latte, 5 L pan \| 6 |
| `sorella:product_gelato_cake_8` | 4.1 | holding freezer: 8" cake, finished and boxed, awaiting collection \| 2 |
| `sorella:product_affogato` | 4.3 | sold, Cotham Hill: 12 affogato |
| `sorella:product_espresso` | 4.3 | sold, Cotham Hill: 96 coffees: 14 espresso |
| `sorella:product_americano` | 4.3 | sold, Cotham Hill: 96 coffees: 21 americano |
| `sorella:product_cappuccino` | 4.3 | sold, Cotham Hill: 96 coffees: 19 cappuccino |
| `sorella:product_flat_white` | 4.3 | sold, Cotham Hill: 96 coffees: 17 flat white |
| `sorella:product_latte` | 4.3 | sold, Cotham Hill: 96 coffees: 15 latte |
| `sorella:product_mocha` | 4.3 | sold, Cotham Hill: 96 coffees: 6 mocha |
| `sorella:product_hot_chocolate` | 4.3 | sold, Cotham Hill: 96 coffees: 4 hot chocolate |
| `sorella:product_oat_milk` | 4.3 | sold, Cotham Hill: 23 oat milk supplements |
| `sorella:product_syrup_shot` | 4.3 | sold, Cotham Hill: 19 syrup shots |
| `sorella:product_canned_soft_drink` | 4.3 | sold, Cotham Hill: 27 cans |
| `sorella:product_bottled_water` | 4.3 | sold, Cotham Hill: 14 bottles of water |

### `submit()` and the class-membership assertion

The 1 Sep line says master data enters through generated forms and `submit()`
writes the class membership. **The first half is done and the second half is
not built.** `submit()` mints a URI it has never seen and registers it under
`uniti:uri`, and it spends `class_name` on `action_name` alone; it writes no
class fact. Checked in the code before entering anything, not inferred:
`grep -n "designates_type\|entity_class\|rdf:type" components/generator/generate.py`
returns nothing.

What carries the class instead is the map. `sorella:entity_class` is a slot on
fifteen of the twenty-one classes, so **every submission set `entity_class`
explicitly as a form field** — `--set entity_class=BoughtItem` — and the fact
is in the log with both clocks, correctable like any other, which is what the
1 Sep line wanted. It went through `submit()`; nothing was hand-written. The
gap is that the value came off a hand-typed field rather than off the class the
form was generated from, and for an entity minted through a ref field there
would be no such field at all — which is the half of the 1 Sep line that is
still a proposal.

Nothing was minted through a ref field this session: the rows are ordered so
that every referenced entity already exists, and the guard that proves it is
the count — 197 planned, 197 minted, one per submission.

### The two live defects, and what the entry did to them

**The computed classes were not written to.** The plan refuses, before opening a
connection, any value for a slot carrying an `aggregate` annotation or an
`equals_expression`, and any submission at all to `IngredientOnHand` or
`GelatoOnHand`. The map's own reading of which slots those are:

```
slots that may not be submitted: ['gelato_in', 'gelato_on_hand_net',
 'gelato_out', 'ingredient_in', 'ingredient_on_hand_net', 'ingredient_out']
```

Checked afterwards against the log rather than trusted — every slot of both
balance classes, counted by predicate:

```
  sorella:gelato_flavour               0 assertions
  sorella:gelato_format                0 assertions
  sorella:gelato_in                    0 assertions
  sorella:gelato_on_hand_net           0 assertions
  sorella:gelato_out                   0 assertions
  sorella:gelato_where                 0 assertions
  sorella:ingredient_in                0 assertions
  sorella:ingredient_on_hand           0 assertions
  sorella:ingredient_on_hand_net       0 assertions
  sorella:ingredient_out               0 assertions
  sorella:ingredient_where             0 assertions
```

Eleven slots, nothing under any of them. The 21 Aug rule still holds and is
still held by nobody typing plus, now, one guard in a throwaway script.

**The log still cannot tell the two businesses apart by any column, and the
count is below.**

### Sorella's assertions, apart from Marlow's

| | assertions | entities | intents |
|---|---|---|---|
| Marlow | 301 | 107 | 1 |
| **Sorella** | **1,316** | **298** | **198** |
| total in the log | 1,617 | 405 | 199 |

Sorella's 1,316 are the seal's 101 slot-URI registrations plus this session's
1,215. The 1,215 are 197 entity mints and 1,018 field values.

**How they were told apart: the prefix on the URI a row's subject is registered
under, and nothing else.** Marlow's entities and slots are all `uniti:`,
Sorella's all `sorella:`, so the query joins every assertion to the `uniti:uri`
registry through its `subject_id` and buckets on the prefix:

```sql
WITH reg AS (
  SELECT a.subject_id AS eid, a.value_literal AS uri
  FROM assertion a
  WHERE a.predicate_id = (SELECT subject_id FROM assertion
                          WHERE subject_id = predicate_id
                            AND value_literal = 'uniti:uri'
                          ORDER BY seq LIMIT 1)
    AND a.value_literal IS NOT NULL)
SELECT CASE WHEN s.uri LIKE 'sorella:%' THEN 'sorella'
            WHEN s.uri LIKE 'uniti:%'   THEN 'marlow' END, count(*)
FROM assertion a LEFT JOIN reg s ON s.eid = a.subject_id
GROUP BY 1;
```

→ `[('sorella', 1316), ('marlow', 301)]`, no unregistered subject.

Every other column still says nothing. `ontology_version` is `'v1'` for both.
`source` splits `human_stated 1212` / `system_derived 405` across both
businesses. The 197 new intents are `fareza` / `generator` /
`submit_<Class>` — distinguishable from the two seals by `action_name`, but
that separates a *write path*, not a business, and Marlow's next form
submission would land in the same bucket. **The prefix is a convention this
session chose, not something the kernel knows**; had the URIs been minted
`uniti:caster_sugar`, nothing anywhere would have told the two apart. The 4 Sep
`[T3]` line stands, and is now load-bearing rather than theoretical.

### The tables, and the defect the entry created

`generate.py table` was run for each of the ten filled classes at
`valid_at 2026-06-16T23:00:00+00:00`, `as_of 2026-09-03T21:08:05+00:00`, each
with `--verify`. All ten exit 0 and every cell equals a direct read:

| class | rows | cells verified |
|---|---|---|
| `Unit` | 197 | 591 |
| `Location` | 197 | 591 |
| `InternalLocation` | 197 | 985 |
| `Supplier` | 197 | 1,773 |
| `WholesaleAccount` | 197 | 1,182 |
| `Person` | 197 | 788 |
| `Flavour` | 197 | 1,182 |
| `Ingredient` | 197 | 1,182 |
| `BoughtItem` | 197 | 1,970 |
| `SoldProduct` | 197 | 1,970 |

The done condition asks for non-zero rows per class and a clean `--verify`, and
both hold. **They hold in the worst possible way: every table has all 197
entities in it.** Every one. A unit is a row of the `BoughtItem` table, a
supplier is a row of the `Flavour` table, and a flavour is a row of the `Unit`
table.

The cause is the generator's row rule meeting the class fact:

> a row of this table is an entity that is the subject of at least one fact
> under one of this table's columns, and has at least one value standing at
> these clocks.

`entity_class` is a column of fifteen of the twenty-one classes, and now every
entity has one, so every entity qualifies as a row of every one of those
fifteen tables. **Filling the master data made every projection in the system
strictly worse than it was when the log was empty**, and it did so through the
one fact that exists to fix it.

The map already says which slot that is — `entity_class` carries
`designates_type: true` — and the log now carries the value. The generator
reads neither. This is the same shape as the `aggregate` defect found on
4 Sep: the map states something three ways and the generator reads none of
them. It is not worked around here; changing `components/` was outside this
item and would not have been said afterwards.

The same rule wrecks the pickers, and the before-and-after is exact. Yesterday
**all 41 pickers over 12 classes offered nothing.** Today **all 41 offer 197**,
which is every entity in the log whatever the field's range. `movement_flavour`,
whose range is `Flavour`:

```
movement_flavour offers 197:
    sorella:flavour_amarena_cherry  Amarena cherry
    sorella:flavour_biscuit  Biscuit
    sorella:flavour_coconut  Coconut
    ...
    sorella:unit_tray
    sorella:unit_tub
    sorella:unit_well
```

The eighteen real flavours carry a label and the other 179 do not, because a
label is the range class's identifier and a unit has no `flavour_name`. So the
rendered form does carry the information needed to separate them — the
generator computes the label and then does not use it to decide the row. An
empty picker and a picker holding the whole log are the same defect twice.

`Business`, `MovementKind`, `Recipe`, `RecipeLine`, `ProductPrice`,
`StockMovement`, `Batch`, `StockCount` and `StockCountLine` were not filled and
their tables also show 197 rows, for the same reason. Only `IngredientOnHand`
and `GelatoOnHand` show 0 — they are the two classes with no `entity_class`
slot, which is an accident of them being computed rather than a mechanism.

### What `§4.1` or `§4.3` named that had nowhere to go

1. **The place beside the fill bench.** `§4.1` counts 34 steel and 12
   polycarbonate empty pans and says of the heading itself: *"Jordan wrote these
   under a heading of his own — by the bench — which is not one of the places in
   `§1.3`."* `§3.2` agrees: *"Empty pans have nowhere to live. They come back on
   the van, get washed and stacked by the fill bench, and `§1.3` names no place
   for them."* No `InternalLocation` was entered, because the only name available
   is one the profile says the business does not have. The two count lines were
   entered as `BoughtItem` rows; where they were counted has no row.
2. **Aoife's car, the drinks fridge at Gloucester Road, and the sink at Cotham
   Hill.** `§4.1`'s own words: *"Neither was counted, because neither is a
   place."* Three things stock moves through with no `Location` row, and `§3.2`
   says the sink takes more milk than anything except the coffee machine.
3. **The pasteuriser and the bench.** `§4.1`: *"the pasteuriser went on at
   07:05."* `§3.2`: *"Between the chiller and the blast freezer everything in the
   building is inside a machine or on a bench, and `§1.3` names neither."* That
   is the destination of every ingredient-to-machine movement, so the
   consumption that `§3.2` says is unrecorded also has nowhere to be recorded
   *to*.
4. **The four confidence words.** `§4.1` has a section for them — *Weighed,
   Counted, Eyeballed, Not counted* — and says *"the difference between those
   two lines is the whole of what this count knows about itself."*
   `StockCountLine` has ten slots and not one is a confidence. The kernel has
   `assertion.confidence` and `submit()` has no way to set it, so the column
   exists and the map cannot reach it. This is the largest of the six for step
   three: without it `§4.1` can be entered as numbers and not as a count.
5. **Promo items.** `§4.1`, office cupboard: *"Promo items — a box of postcards
   from 2023, two roller banners | 1 box, 2 banners."* Not in `§1.6`'s eighty,
   not a flavour, a unit, a product or a place.
6. **A `twelve`.** `§1.5` orders steel napoli pans in *twelves* and `§1.6` says
   *"single pan, bought twelve at a time."* No `Unit` row was entered for it
   because no line of `§4.1` or `§4.3` names one, so
   `item_ordered_in` is blank on `sorella:item_napoli_pan_stainless_5_l`.
7. **Coffee beans, counted two ways.** `§1.5`: *"Coffee beans | kilos | bags at
   the shop | grams in the kitchen | Same bean, two places, two units."*
   `item_counted_in` is single-valued and holds `bag`; the kitchen's kilo has
   nowhere to go on the same row. The same shape as the two Cotham back
   freezers, one row short of what the business does.
8. **Sixteen bought items with no supplier.** `item_supplier` is blank on
   `bottled_water_500_ml`, `canned_soft_drink`, `caramel_syrup`,
   `coffee_beans_espresso_blend`, `dry_ice_pellets`, `hazelnut_syrup`,
   `hot_chocolate_powder`, `oat_milk_barista`, `paper_cup_8_oz`,
   `paper_cup_12_oz`, `paper_cup_lid`, `vanilla_syrup`, `wafer_cones`,
   `waffle_cones`, `whole_milk_coffee_bar` and `wooden_stirrer`. `§1.6` gives
   all sixteen a supplier and the four suppliers concerned — Bristol Cash &
   Carry, Marchetti Cones, Coldharbour Roastery, Bristol Ice & Dry Ice — are
   named by no line of `§4.1` or `§4.3`, so filling the field would have minted
   an out-of-scope entity through a ref field.

**The one borderline call, recorded so it can be overturned in a sentence.**
`§4.1` writes *"the cash and carry run was in the car by half past ten"*, which
does point at exactly one of the nine suppliers. It was read as **not** a
naming, because the sentence sits inside the table row headed *"Aoife's car,
the drinks fridge at Gloucester Road, and the sink at Cotham Hill — three
things `§3.7` says stock moves through that `§1.3` does not name"*, and what it
is there to say is that the car held stock. Reading a supplier out of it is
reading past what the line is about. Admitting it would add one `Supplier` row
and twelve `item_supplier` values.

### Classes deliberately not filled

| class | why |
|---|---|
| `Business` | `§4.1` and `§4.3` never write *Sorella Gelato Ltd*, which is the identifier. "Sorella" appears once, in *"the first count anybody at Sorella has taken"*. One row, wanted because it would be tidy, which is the boundary working |
| `MovementKind` | `§3.2`'s fifty-three rows are master data step three needs, and `§4.3` names events under `§3.2`'s five headings, never one of the fifty-three kinds |
| `Recipe`, `RecipeLine` | no page is named. See the consumption answer above — this is the one exclusion that has a cost |
| `ProductPrice` | `§4.3` gives two days' takings and not one product's price. `§1.7`'s grid is the source and neither day names a cell of it |
| `StockMovement`, `Batch`, `StockCount`, `StockCountLine` | documents and events, which is step three |
| `IngredientOnHand`, `GelatoOnHand` | computed. Not filled, by the 21 Aug rule and the 4 Sep defect |

### One table, in full

`Unit` — the smallest of the ten, and the clearest picture of what the row rule
now does. Twenty-six rows are units. The other 171 are there because they carry
an `entity_class`, and the class each of them carries is written in the first
column of the table it does not belong in.

```
Unit  (v1)
valid_at   2026-06-16T23:00:00+00:00
as_of      2026-09-03T21:08:05.022894+00:00

subject                                            entity_class      unit_name   unit_meaning
-------------------------------------------------  ----------------  ----------  ----------------------------------------------------------------------------------------------------------------------------------------
sorella:flavour_amarena_cherry                     Flavour
sorella:flavour_biscuit                            Flavour
sorella:flavour_coconut                            Flavour
sorella:flavour_coffee                             Flavour
sorella:flavour_dark_chocolate                     Flavour
sorella:flavour_elderflower_sorbet                 Flavour
sorella:flavour_fior_di_latte                      Flavour
sorella:flavour_hazelnut                           Flavour
sorella:flavour_lemon_sorbet                       Flavour
sorella:flavour_local_strawberry                   Flavour
sorella:flavour_mango_sorbet                       Flavour
sorella:flavour_mint_choc_chip                     Flavour
sorella:flavour_pistachio                          Flavour
sorella:flavour_raspberry_sorbet                   Flavour
sorella:flavour_salted_caramel                     Flavour
sorella:flavour_stracciatella                      Flavour
sorella:flavour_strawberry_sorbet                  Flavour
sorella:flavour_vanilla                            Flavour
sorella:item_125_ml_mini_tub_with_lid              BoughtItem
sorella:item_1_5_l_catering_tub_with_lid           BoughtItem
sorella:item_500_ml_lid_printed                    BoughtItem
sorella:item_500_ml_tub                            BoughtItem
sorella:item_amarena_cherries_in_syrup             BoughtItem
sorella:item_amaretti_biscuits                     BoughtItem
sorella:item_base_50_stabiliser                    BoughtItem
sorella:item_basil_fresh                           BoughtItem
sorella:item_bin_liners_heavy_duty                 BoughtItem
sorella:item_biscuit_base                          Ingredient
sorella:item_blue_roll                             BoughtItem
sorella:item_bottled_water_500_ml                  BoughtItem
sorella:item_cake_board_8                          BoughtItem
sorella:item_cake_box_8                            BoughtItem
sorella:item_canned_soft_drink                     BoughtItem
sorella:item_caramel_syrup                         BoughtItem
sorella:item_caster_sugar_sucrose                  BoughtItem
sorella:item_cip_alkaline_detergent                BoughtItem
sorella:item_cocoa_22_24                           BoughtItem
sorella:item_coconut_puree                         BoughtItem
sorella:item_coffee_beans_espresso_blend           BoughtItem
sorella:item_coffee_brew                           Ingredient
sorella:item_cream_cheese                          BoughtItem
sorella:item_dark_chocolate_70_callets             BoughtItem
sorella:item_dextrose                              BoughtItem
sorella:item_digestive_biscuits                    BoughtItem
sorella:item_dry_ice_pellets                       BoughtItem
sorella:item_eggs_medium_free_range                BoughtItem
sorella:item_elderflower_cordial                   BoughtItem
sorella:item_freeze_dried_raspberry_pieces         BoughtItem
sorella:item_freezer_label_blank                   BoughtItem
sorella:item_fruit_puree_blood_orange              BoughtItem
sorella:item_fruit_puree_mango                     BoughtItem
sorella:item_fruit_puree_passionfruit              BoughtItem
sorella:item_fruit_puree_peach                     BoughtItem
sorella:item_fruit_puree_pink_grapefruit           BoughtItem
sorella:item_fruit_puree_raspberry                 BoughtItem
sorella:item_fruit_puree_strawberry                BoughtItem
sorella:item_gelato_cup_three_scoop                BoughtItem
sorella:item_gelato_cup_two_scoop                  BoughtItem
sorella:item_gelato_spoon                          BoughtItem
sorella:item_glucose_syrup_de38                    BoughtItem
sorella:item_ground_cinnamon                       BoughtItem
sorella:item_hazelnut_paste                        BoughtItem
sorella:item_hazelnut_syrup                        BoughtItem
sorella:item_honey_clear                           BoughtItem
sorella:item_hot_chocolate_powder                  BoughtItem
sorella:item_inverted_sugar                        BoughtItem
sorella:item_lemon_juice                           BoughtItem
sorella:item_lemons                                BoughtItem
sorella:item_marsala                               BoughtItem
sorella:item_napkin_2_ply                          BoughtItem
sorella:item_napoli_pan_polycarbonate_5_l          BoughtItem
sorella:item_napoli_pan_stainless_5_l              BoughtItem
sorella:item_nitrile_gloves                        BoughtItem
sorella:item_oat_milk_barista                      BoughtItem
sorella:item_paper_cup_12_oz                       BoughtItem
sorella:item_paper_cup_8_oz                        BoughtItem
sorella:item_paper_cup_lid                         BoughtItem
sorella:item_peppermint_extract                    BoughtItem
sorella:item_printed_sleeve_500_ml                 BoughtItem
sorella:item_pumpkin_puree                         BoughtItem
sorella:item_ricotta                               BoughtItem
sorella:item_salted_caramel_variegate              BoughtItem
sorella:item_sanitiser_no_rinse                    BoughtItem
sorella:item_sea_salt_fine                         BoughtItem
sorella:item_sicilian_pistachio_paste              BoughtItem
sorella:item_skimmed_milk_powder                   BoughtItem
sorella:item_sorbet_syrup                          Ingredient
sorella:item_strawberries                          BoughtItem
sorella:item_takeaway_bag_paper_handled            BoughtItem
sorella:item_tasting_spoon                         BoughtItem
sorella:item_vanilla_bean_paste                    BoughtItem
sorella:item_vanilla_syrup                         BoughtItem
sorella:item_wafer_cones                           BoughtItem
sorella:item_waffle_cones                          BoughtItem
sorella:item_whipping_cream_38                     BoughtItem
sorella:item_white_base                            Ingredient
sorella:item_whole_milk_coffee_bar                 BoughtItem
sorella:item_whole_milk_kitchen                    BoughtItem
sorella:item_wooden_stirrer                        BoughtItem
sorella:loc_avonside_packaging                     Supplier
sorella:loc_bar_trentanove                         WholesaleAccount
sorella:loc_blast_freezer                          InternalLocation
sorella:loc_caffe_umberto                          WholesaleAccount
sorella:loc_cleeve_coffee_house                    WholesaleAccount
sorella:loc_comps                                  Location
sorella:loc_cotham_back_freezer_1                  InternalLocation
sorella:loc_cotham_back_freezer_2                  InternalLocation
sorella:loc_cotham_cabinet                         InternalLocation
sorella:loc_cotham_hill                            InternalLocation
sorella:loc_cotham_shelf_unit                      InternalLocation
sorella:loc_cotham_under_counter_fridge            InternalLocation
sorella:loc_donations                              Location
sorella:loc_dry_store                              InternalLocation
sorella:loc_gloucester_road                        InternalLocation
sorella:loc_gloucester_road_cabinet                InternalLocation
sorella:loc_gloucester_road_shelves                InternalLocation
sorella:loc_gloucester_road_under_counter_freezer  InternalLocation
sorella:loc_holding_freezer                        InternalLocation
sorella:loc_ingredient_freezer                     InternalLocation
sorella:loc_kingsdown_fruit_farm                   Supplier
sorella:loc_marina_s_house                         Location
sorella:loc_office_cupboard                        InternalLocation
sorella:loc_packaging_mezzanine                    InternalLocation
sorella:loc_production_kitchen                     InternalLocation
sorella:loc_severn_catering_supplies               Supplier
sorella:loc_staff                                  Location
sorella:loc_tastings                               Location
sorella:loc_terra_nostra_ingredients               Supplier
sorella:loc_the_container                          InternalLocation
sorella:loc_the_cool_box                           InternalLocation
sorella:loc_the_cotham_bin                         Location
sorella:loc_the_gloucester_road_bin                Location
sorella:loc_the_hollow                             WholesaleAccount
sorella:loc_the_kitchen_bin                        Location
sorella:loc_the_old_bakehouse                      WholesaleAccount
sorella:loc_the_trailer                            InternalLocation
sorella:loc_the_van                                InternalLocation
sorella:loc_the_walk_in_customer                   Location
sorella:loc_walk_in_chiller                        InternalLocation
sorella:loc_wapping_wharf_kitchen                  WholesaleAccount
sorella:loc_whitehall_dairy                        Supplier
sorella:person_aoife_brennan                       Person
sorella:person_dan_farrugia                        Person
sorella:person_jordan_hale                         Person
sorella:person_marina_devlin                       Person
sorella:person_priya_shah                          Person
sorella:person_rekha_pillai                        Person
sorella:person_steve_corrigan                      Person
sorella:person_tomas_nowicki                       Person
sorella:person_yusuf_adeyemi                       Person
sorella:product_125_ml_mini_tub                    SoldProduct
sorella:product_1_5_l_catering_tub                 SoldProduct
sorella:product_500_ml_retail_tub                  SoldProduct
sorella:product_5_l_napoli_pan                     SoldProduct
sorella:product_affogato                           SoldProduct
sorella:product_americano                          SoldProduct
sorella:product_bottled_water                      SoldProduct
sorella:product_canned_soft_drink                  SoldProduct
sorella:product_cappuccino                         SoldProduct
sorella:product_double_scoop                       SoldProduct
sorella:product_espresso                           SoldProduct
sorella:product_flat_white                         SoldProduct
sorella:product_gelato_cake_8                      SoldProduct
sorella:product_hot_chocolate                      SoldProduct
sorella:product_latte                              SoldProduct
sorella:product_mocha                              SoldProduct
sorella:product_oat_milk                           SoldProduct
sorella:product_single_scoop                       SoldProduct
sorella:product_syrup_shot                         SoldProduct
sorella:product_triple_scoop                       SoldProduct
sorella:product_waffle_cone_instead_of_wafer       SoldProduct
sorella:unit_bag                                   Unit              bag         Milk (10 L bag-in-box), skimmed milk powder (25 kg), cocoa (5 kg), Base 50 (2 kg), coffee beans (1 kg). Five unrelated things are a bag.
sorella:unit_bottle                                Unit              bottle      A 500 ml, 750 ml, 1 L or 2 L bottle. Section 1.5's unit list does not carry it and section 1.6 counts eight items in it.
sorella:unit_box                                   Unit              box         10 kg of chocolate, 1 kg of amaretti, 1,000 spoons, 5 kg of rhubarb.
sorella:unit_bucket                                Unit              bucket      Also the 25 L lidded bucket that aged base is drawn into. Two buckets in the chiller is base; two buckets in the dry store is glucose.
sorella:unit_can                                   Unit              can         The 5 L jerry can cream arrives in.
sorella:unit_carton                                Unit              carton      Ten 2 kg bags of Base 50. The only thing bought by the carton.
sorella:unit_case                                  Unit              case        The outer a supplier ships in. Never the same count twice: 500 tubs, 1,000 lids, 6 puree tubs, 4 cone sleeves, 24 cans.
sorella:unit_drum                                  Unit              drum        5 L or 10 L of cleaning chemical.
sorella:unit_each                                  Unit              each        One item. Cones, cups, spoons, napkins, tubs, lids, cake boards.
sorella:unit_gram                                  Unit              gram        Weight. Every recipe, the pasteuriser scale, the bench scale.
sorella:unit_jar                                   Unit              jar         2.6 kg of amarena cherries.
sorella:unit_kilogram                              Unit              kilogram    Weight. Every recipe, the pasteuriser scale, the bench scale.
sorella:unit_litre                                 Unit              litre       Volume. Pack sizes, pan and tub capacity, cordials and syrups.
sorella:unit_millilitre                            Unit              millilitre  Volume. Pack sizes, pan and tub capacity, cordials and syrups.
sorella:unit_pack                                  Unit              pack        400 g of digestives, 500 napkins, 100 g of basil.
sorella:unit_pail                                  Unit              pail        12.5 kg of glucose, 14 kg of inverted sugar, 3 kg of caramel variegate. Everyone says bucket.
sorella:unit_pan                                   Unit              pan         A 5 L napoli pan, steel or polycarbonate.
sorella:unit_punnet                                Unit              punnet      The kitchen's word for the same object.
sorella:unit_roll                                  Unit              roll        Blue roll, bin liners.
sorella:unit_sack                                  Unit              sack        25 kg of caster sugar or dextrose.
sorella:unit_scoop                                 Unit              scoop       One press of a till button.
sorella:unit_sleeve                                Unit              sleeve      90 waffle cones, 120 wafer cones, 100 mini tubs.
sorella:unit_tin                                   Unit              tin         3.5 kg pistachio paste, 5 kg hazelnut paste, 3 kg pumpkin puree.
sorella:unit_tray                                  Unit              tray        Kingsdown's word for a 2 kg punnet of strawberries or figs.
sorella:unit_tub                                   Unit              tub         A 500 ml retail tub, a 1 kg puree tub, a 1.5 L catering tub, a 2 kg ricotta tub, a 3 kg honey tub. The word alone never says which.
sorella:unit_well                                  Unit              well        One hole in a display cabinet. Twenty-four at Cotham, sixteen at Gloucester Road.

197 rows, 3 columns, 342 of 591 cells blank
```

### Surprising

1. **The class fact broke every table, and it is the fact that exists to fix
   them.** Yesterday every table had 0 rows and every picker offered nothing.
   Today every table has 197 rows and every picker offers 197. Neither number is
   right, and the thing that changed between them is the assertion the 1 Sep
   line asked for. The generator's row rule guesses class membership from which
   columns are filled; the log now *states* it, and the guess is worse than it
   was because the stated fact is one of the columns it guesses from. The map
   even says which slot to read — `designates_type: true` on `entity_class` —
   and the 1 Sep line refused `designates_type` on the ground that nothing reads
   it. It is still true that nothing reads it, and it is now the difference
   between a table and a dump.
2. **Two modules are named `resolve.py`.** `components/kernel/resolve.py` has
   `resolve_single` and `components/ontology/resolve.py` has `resolve_version`.
   Put both directories on `sys.path` and the second import silently gets the
   first module and dies on the name it wanted:
   `ImportError: cannot import name 'resolve_single' from 'resolve'
   (...\components\ontology\resolve.py)`. That was the first thing this session
   ran after writing the balance probe. `generate.py` never hits it because it
   only ever imports the kernel's. **Every reader of a balance needs both** —
   which map applies, then which fact wins — so `report` will hit it on its
   first line. The workaround here was `importlib.util.spec_from_file_location`.
3. **`§1.5` has no `bottle`.** The section the profile calls *"the single most
   persistent source of confusion in the business"* lists twenty-six units and
   omits the one `§1.6` counts eight rows in — peppermint extract, marsala,
   lemon juice, elderflower cordial, the coffee-bar milk and three syrups.
   `§4.1` writes *bottle* on eight of its lines. It was entered as a `Unit` under the
   item's own escape hatch, cited to *"Peppermint extract, 500 ml bottle | 2,
   one part-used"*. `flat`, which `§1.5` does list, was left out because no line
   of either day uses it. So the count of units the business works in is 26
   either way and the membership is not the same 26.
4. **The boundary barely touches the bought items.** It was written to keep the
   eighty out and it kept out three — panettone, figs and rhubarb — which are
   the exact three `§4.1` says nobody wrote a line for. Six sheets walking a
   building in five hands is not a sample of `§1.6`; it is very nearly `§1.6`.
   Where the boundary did its work is the accounts, 6 of 31, and the flavours,
   18 of 25.
5. **`submit()` does not write the class fact and the map does.** The 1 Sep line
   reads as a statement about the code and is satisfied by the map: fifteen
   classes carry an `entity_class` slot, so a form has a field for it and a
   submission fills it. From outside, the log looks exactly as the decision
   intended. From inside, the class came off a typed field rather than off the
   class the form was generated from, and an entity minted through a **ref**
   field — the supplier first named on a receipt, which is the case the 1 Sep
   line spells out — would still get no class at all. Nothing was minted that
   way this session, so the gap did not bite; step three is where it will.
6. **LinkML's annotations are not a mapping, and they fail three different
   ways.** `dict(slot.annotations)` raises `ValueError: dictionary update
   sequence element #0 has length 11; 2 is required` — on an annotations block
   that is *empty*. `spec.by.items()` raises `AttributeError: 'JsonObj' object
   has no attribute 'items'. Did you mean: '_items'?`. Reading the map's own
   `aggregate` spec took three attempts. Every one failed loudly, which is the
   opposite of 4 Sep's silent `'3' + '4' == '34'`, and is the reason this took
   ten minutes rather than shipping wrong.
7. **Sorella now outweighs Marlow four to one in one log and no column says
   so.** 1,316 against 301. The separation is a prefix this session chose when
   it minted the first URI; nothing enforced it and nothing would have noticed
   `uniti:caster_sugar`.
8. **One form submission is one intent, exactly.** 197 submissions, 197 new
   intents, 197 entities, 1,215 assertions, no partial write. The kernel's write
   gate held without anything being asked of it.

### Proposed `DECISIONS.md` entries

1. **A URI namespace per identifier slot.** The map identifies on ten slots and
   this session's ten classes use six of them — `location_name`, `unit_name`,
   `person_name`, `flavour_name`, `item_name`, `product_name` — so entity URIs
   are minted `sorella:loc_…`,
   `sorella:unit_…`, `sorella:person_…`, `sorella:flavour_…`, `sorella:item_…`
   and `sorella:product_…`. Forced by a case in the profile rather than chosen
   for tidiness: *Canned soft drink* is a `BoughtItem` in `§1.6` and a
   `SoldProduct` in `§1.7` — the same object bought and sold — and each class
   identifies on its own slot, so one URI cannot carry both. The alternatives
   were to rename one of them, which puts a word in the log the business does
   not use, or to give one entity two class facts, which loses the distinction
   the map draws. A supplier and a freezer share `location_name` and therefore
   share a namespace and may not share a name, which is the same thing the
   identifier already said. The cost is that a URI now names a class as well as
   an entity, and that duplicates a fact the log holds properly.
2. **Master data is valid from the adoption date and recorded today.** All 197
   entities carry `valid_from 2026-06-15T00:00:00Z` — `§1.2`'s Monday, and the
   map's own `valid_from` — with `recorded_at` left to `now()`. So the master
   data is true from the day the business started recording and known from the
   day it was typed, which is the two axes doing the only thing they can
   honestly do about eighty days of backfill. The alternative, back-dating
   `recorded_at`, would assert that the log knew in June.
3. **`resolve_version` returning `None` before `sealed_at` is correct, and the
   4 Sep line can be closed rather than fixed.** The gap is eighty days and it
   costs milestone one nothing, because the read a balance makes is `valid_at`
   in June and `as_of` today, which returns v1. The read that returns `None` is
   *what did the map say on 16 June as known on 16 June*, and the honest answer
   is that on 16 June the business had not been described. Anything that made
   that pair return v1 would be a lie about when the map was written. Measured
   before proposing: six clock pairs, and a three-column balance computed off
   the sealed file at a June `valid_at`.
4. **The generator's row rule reads the class fact.** Today it is *subject of at
   least one of this table's columns*, and now that `entity_class` is a column
   of fifteen classes and every entity has one, that rule puts all 197 entities
   in all fifteen tables and all 197 in every one of the 41 pickers. The rule
   the log can now support is *the entity whose `entity_class` says this class*,
   and the map names the slot with `designates_type: true`, so reading it stays
   domain-blind. This is a decision and not a repair because it changes what a
   projection **is** — from a guess the generator's own docstring admits to, to
   a read — and because it makes the 1 Sep class-membership line load-bearing
   rather than tidy.

### Proposed `OPEN.md` lines

- `[T3]` The generator's row rule is a guess and the log now contradicts it.
  Every one of the ten filled classes renders 197 rows and every one of the 41
  pickers offers 197, because `entity_class` is a column of fifteen classes and
  all 197 entities carry one, so the rule *subject of at least one of this
  table's columns* admits everything to everything. Before the master data went
  in the same tables had 0 rows and the same pickers offered nothing, so filling
  the log made every projection in the system worse. The map names the slot to
  read — `designates_type: true` on `entity_class` — and the 1 Sep line refused
  `designates_type` on the ground that nothing reads it. Whether the row rule
  reads that flag, reads a class-membership predicate the generator knows by
  name, or is a key the map states, is undecided. Found 4 Sep entering 197
  master-data rows · blocks: generation
- `[T3]` Two modules are named `resolve.py` and every reader of a balance needs
  both. `components/kernel/resolve.py` carries `resolve_single` and
  `components/ontology/resolve.py` carries `resolve_version`; with both
  directories on `sys.path` the second import gets the first module and raises
  `ImportError: cannot import name 'resolve_single' from 'resolve'`.
  `generate.py` is unaffected because it imports only the kernel's, which is
  also why nothing has caught this in three weeks. A balance needs the map
  resolver and the fact resolver in one process, so `report` hits it on its
  first line. Whether the files are renamed, whether the components become
  packages, or whether the 1 Sep line's unnamed joint inside `generate.py` is
  extracted and owns both, is undecided. Found 4 Sep writing a throwaway balance
  · blocks: report
- `[T3]` A count line has no confidence and the kernel has one.
  `assertion.confidence` is a column and `submit()` has no field for it;
  `StockCountLine` has ten slots and not one of them is *Weighed / Counted /
  Eyeballed / Not counted*. `§4.1` gives those four words a section of their own
  and says *"the difference between those two lines is the whole of what this
  count knows about itself"*, so entering Monday's count without them records
  the numbers and throws away what the count says about itself. Whether the four
  words are a slot on the line, an enum, or the `confidence` column the kernel
  already has reached through a form field, is undecided — and the second and
  third are different answers to whether a confidence is a fact about the world
  or about the claim. Found 4 Sep reading `§4.1` for master data · blocks:
  live use
- `[T2]` The business has no name for the place empty pans stand in. `§4.1`
  counts 34 steel and 12 polycarbonate pans under a heading Jordan invented —
  *by the bench* — and says it is not one of `§1.3`'s places; `§3.2` says the
  file has no name for it. It is reached by the wash-and-stack leg of every pan
  that comes back on the van, so it is not a place the map can leave out for
  long. Only Sorella can say what it is called. Found 4 Sep entering the two
  empty-pan lines · blocks: live use
- `[T2]` One bought item is counted in two units in two places and the map holds
  one. `§1.5` says of coffee beans *"kilos | bags at the shop | grams in the
  kitchen | Same bean, two places, two units"*; `item_counted_in` is
  single-valued and now holds `bag`. Whether the second reading is a second
  `BoughtItem`, a per-location unit, or something the business would say is one
  thing, is a question for Sorella and not for this desk. Found 4 Sep entering
  `sorella:item_coffee_beans_espresso_blend` · blocks: live use

Nothing was triaged `[T1]` and written down. Three questions were `[T1]` and
tried instead: whether `resolve_version` returns the map for a June `as_of`,
whether the three-column balance computes off the sealed file at a June
`valid_at`, and what filling `entity_class` does to the tables. All three are
answered above, in two throwaway scripts outside the repo.

### What was run

Working log is `uniti` (the default DSN); `make check` runs against
`uniti_check` and touches nothing here.

| Command | Exit |
|---|---|
| `resolve_version` over `business/sorella`, six clock pairs | 0 — the table above; `None` on the diagonal, **v1** for a June `valid_at` read today |
| `june_balance.py 2026-06-16T23:00:00+00:00 2026-06-16T23:00:00+00:00` | **1** — `resolve_version -> None`, and that is the result |
| `june_balance.py … --selftest`, first attempt | **1** — `ImportError: cannot import name 'resolve_single' from 'resolve'`. Two modules, one name |
| `june_balance.py … --selftest`, second attempt | **1** — `ValueError: dictionary update sequence element #0 has length 11` from `dict(slot.annotations)` |
| `june_balance.py … --selftest`, third attempt | **1** — `AttributeError: 'JsonObj' object has no attribute 'items'` |
| `june_balance.py 2026-06-16T23:00:00+00:00 2026-09-04T12:00:00+00:00 --selftest` | **0** — v1 resolved off the sealed file, 0 movements in the log, and the fabricated four give `15.8` and `2` through the map's own `equals_expression` |
| `sorella_master.py --dry-run` | 0 — 197 entities planned, no duplicate subject, no URI colliding with a slot URI, no computed slot in any submission |
| `sorella_master.py` | **0** — **197 submissions, 1,215 assertions, 197 entities minted** |
| assertion / entity / intent counts, bucketed on the URI prefix of each row's subject | 0 — `[('sorella', 1316), ('marlow', 301)]`, 405 entities, 199 intents, no unregistered subject |
| every slot of `IngredientOnHand` and `GelatoOnHand`, counted by predicate | 0 — **eleven slots, 0 assertions under each** |
| 10 × `generate.py table business/sorella/v1.yaml CLASS --valid-at 2026-06-16T23:00:00+00:00 --as-of 2026-09-03T21:08:05+00:00 --verify` | 0 each — **197 rows every time**, 12,214 cells verified against a direct read, no disagreement |
| 11 × `generate.py table` for the classes not filled | 0 each — 197 rows for the nine that carry `entity_class`, **0 rows** for `IngredientOnHand` and `GelatoOnHand` |
| 21 × `generate.py form business/sorella/v1.yaml CLASS` | 0 each — **41 pickers, every one offering 197**, none offering nothing |
| `grep -n "designates_type\|entity_class\|rdf:type" components/generator/generate.py` | **1** — no match. The generator reads none of the three |
| `make check` | **0** — **64 tests passed**, replay byte-identical twice, 5,334 bytes both times |
| `git status --porcelain` | 0 — **empty** |
| `git diff --stat HEAD -- business/` | 0 — **empty. Nothing under `business/` added, moved, changed or deleted** |
| assertion count in `uniti` after `make check` | 0 — 1,617, unchanged |

**No two clauses of the done condition conflicted, and one came close enough to
be worth naming.** *"`generate.py table` shows non-zero rows for each class
filled"* and *"`--verify` is clean"* both pass, and they pass on tables that
list every entity in the log under every class. Neither clause is wrong; they
were written before there was a way to know that a table could be simultaneously
non-empty, internally verified and useless. It is reported here rather than
satisfied quietly, because a reader who saw only the two green checks would
conclude the projections work.

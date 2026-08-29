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

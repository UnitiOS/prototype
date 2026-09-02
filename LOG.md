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

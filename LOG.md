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

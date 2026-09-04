# Execution Log

Written **only by Claude Code**, after something has actually been run.
Desktop reads this at the start of a session and never writes to it.

Format: date · what was run · the result · what was surprising.
Plans do not go here. Only what already happened.

---

## 2026-09-04 — Housekeeping run 2: LOG.md rotated whole, build/ triaged

Authorised by Fareza, not a `NEXT.md` item. `OPEN.md`, `DECISIONS.md` and
`NEXT.md` were not read or written this run — Desktop held them.

**LOG.md.** All 16 `## 2026-09-…` sections moved to `history/LOG-2026-09.md`,
in order. Before: 4,565 lines, 16 September sections, 0 August sections
(August left earlier the same day, in commit `93a3ee7`). After: LOG.md
holds its 10-line header and this entry; `history/LOG-2026-09.md` holds the
same 16 sections under a two-line header. The moved body is byte-identical to
`git show HEAD:LOG.md` lines 11–4565 (`cmp` clean, md5 `bb59e90a…`).

Surprising: the previous run's "Questions for Fareza" went to history with
their section, so LOG.md no longer surfaces them. They are unanswered in
`history/LOG-2026-09.md`, last section.

**build/ triage.** 259 files before, 2 after. Every `.py`, `.sh` and `.sql`
anywhere under `build/` was exactly the eight named — no ninth turned up, and
none of the eight is named by `components/`, `scripts/`, `tests/` or the
Makefile, so all eight are hand-written. Moved to `history/build-scripts/`
(plain `mv` then `git add`: `git mv` refuses an untracked path, and `build/`
has been in `.gitignore` since 2026-08-22, so nothing in it was ever tracked).
Deleted: `build/v1/` (139), `sorella_forms/` (21), `sorella_forms2/` (21),
`webvowl/` (23), `sorella_mmd/` (11), `sorella_tables/` (10), `probe/` (2),
`t/` (2), and 22 loose `.txt`/`.ttl`/`.err`/`.mmd` files at the root — 251 in
all. `build/` kept as an empty directory; `make replay` does not create it.
`make check` then exited 0, 65 tests passed, and `build/` holds only the
`projection_{a,b}.txt` that run just wrote.

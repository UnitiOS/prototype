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

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

# Uniti — PoC

An append-only claim log with per-field provenance and two time axes.

One fact is one row in `assertion`, and no row is ever updated or deleted.
Each row carries `valid_from` — when the world was that way — and
`recorded_at` — when we came to believe it. Two clocks, not one. That is why a
correction ("we were wrong about January") is a different event from a change
("the fee went up in March"), and why a read takes both `valid_at` and `as_of`.

Provenance sits on the claim, not on the record: `source`, `confidence`,
`authority` and the `intent` that produced it belong to each individual
statement, so a student's name can be human-confirmed while their phone number
is document-extracted.

**Schema generation is not the bet.** That is a commodity — ERPNext has shipped
it for a decade. The bet is the evidence substrate underneath it.

The findings this rests on are one line each in `DECISIONS.md`. Closed there
means not re-discussed; it does not mean proven.

**What the kernel must do:** one fact, corrected late, read at four
combinations of valid time and record time, gives four correct and distinct
answers. That is `test_four_reads` in `tests/test_bitemporal.py`. The
parametrised table is the specification — if you read one thing after this
file, read that.

That is the kernel's bar, not the PoC's. What the PoC as a whole has to show is
a stage 7 result, and it is stated in `CLAUDE.md`.

## The eight stages

The PoC runs in eight stages. Names only here; `CLAUDE.md` holds the list that
counts, and `DECISIONS.md` says why each is shaped the way it is.

1. **Interview** — the active stage
2. Ontology mapping
3. Graph review
4. Kernel recording — what this repo holds
5. Generation
6. Live use
7. Definition change
8. Agentic access

**The active stage is stage 1.** A kernel exists before its own stage is
reached because nothing said in stages 1-3 can be recorded until it does — so
this repo runs ahead of the stage marker, and the marker, not the repo, says
where the PoC is. Which stage decides whether any of it is worth doing is a
line in `DECISIONS.md`; it is not this one.

If this list and `CLAUDE.md` ever disagree, `CLAUDE.md` is right.

## Run it

Needs Docker and Python 3.12. Everything below runs from the repo root.

```
make check
```

One command from a clean clone: virtualenv, schema, tests, and a replay that
must come out byte-identical twice. It exits non-zero if either half fails, and
**it resets the database** — see `make replay` below. The rest of this section
is the same thing by hand, for when one step needs to be run alone.

```
docker compose up -d                    # postgres:17 on host port 5433
```

Apply the schema. `./kernel` is mounted read-only inside the container:

```
docker compose exec -T db psql -U uniti -d uniti -v ON_ERROR_STOP=1 \
    -f /kernel/001_schema.sql
```

On Git Bash prefix that with `MSYS_NO_PATHCONV=1`, or the container path is
rewritten into a Windows one. The script drops and recreates: it is re-runnable.

```
python -m venv .venv
.venv/Scripts/python.exe -m pip install "psycopg[binary]" pytest
.venv/Scripts/python.exe -m pytest tests -q          # expect 20 passed
```

Connection string comes from `UNITI_DSN`, defaulting to
`postgresql://uniti:uniti@localhost:5433/uniti` (`kernel/perform.py`).

```
make replay
```

Seeds 200 synthetic assertions, builds the same projection twice from the log
and checks the two files are byte-identical. **It resets the database first** —
harmless, the data is synthetic, but do not run it against anything you care
about. On a non-Windows machine change `PY` at the top of the `Makefile`.

## The three tables

Column list in `kernel/001_schema.sql`. It is closed: a new column on
`assertion` for a business reason is a question for Fareza, not a commit.

**`intent`** — one row per user action, not per field written. Who acted, when,
under what action name, optionally why. Everything an action wrote points back
at one intent row, so a whole edit can be traced to a single human decision.

**`assertion`** — the log. Subject, predicate, one value (literal xor entity
reference), the two timestamps, provenance, and `revokes`, which names an
earlier row this one withdraws. A retraction is itself an assertion, so a row
may carry no value at all — see the `value_exactly_one` constraint. Append-only
is enforced by the database, not by convention: `kernel_deny()` triggers plus a
`REVOKE` on UPDATE/DELETE/TRUNCATE. `tests/test_append_only.py` proves it.

**`entity`** — a registry of identity and nothing else: an id, when it was
minted, and the intent that minted it. There is **no class column**, because
class membership is a claim like any other and claims belong in the log. Saying
"this entity is a student" as a column would make it un-timed, un-sourced and
un-correctable; asserted as `member_of`, it gets the same two clocks, the same
provenance and the same right to be wrong as every other fact.

## Which file answers which question

Most of the value in this repo is knowing where a rule lives. Each rule lives
in exactly one place. This file points at them and deliberately does not repeat
them — a restated rule drifts from the one it restates.

| Question | Where the answer lives |
|---|---|
| Why does `as_of` exist? What is settled? | `DECISIONS.md` |
| How is a read resolved — which row wins, and why that one? | docstring of `kernel/resolve.py` |
| What may be written, and what is deliberately not validated? | docstring of `kernel/perform.py` |
| What are the columns, constraints and append-only guards? | `kernel/001_schema.sql` |
| What must be true, exactly? | `tests/` — the tests are the spec |
| What does a correction look like, versus a change? | `tests/test_bitemporal.py` fixtures |
| Can I really not UPDATE a row? | `tests/test_append_only.py`, `kernel/002_guard_test.sql` |
| What is undecided, or known-broken and left alone? | `OPEN.md` (typed `[T1]`/`[T2]`/`[T3]`) |
| What does a projection look like, and why is it never stored? | `scripts/project.py` |
| Where does the demo data come from? | `scripts/seed_200.py` (one RNG seed, deterministic) |
| What does the smallest possible write look like? | `scripts/write_three.py` |
| How is this repo worked on? What may not be built? | `CLAUDE.md` |
| What are the eight stages, and which one is active? | `CLAUDE.md`, then `DECISIONS.md` |
| What is being worked on right now? | `NEXT.md` |
| What was run, and what was surprising? | `LOG.md` |

`OPEN.md` is worth reading before trusting the kernel. It records things that
are known not to work — revocation does not cascade, `revokes` is not tied to
the same slot — written down rather than patched.

## Not built

Two different reasons, and they are not interchangeable. A DDL compiler, a UI
generator and an MCP endpoint are simply later stages — 5 and 8 — and arrive
when those stages do. Everything on the stop-list in `CLAUDE.md` is reasonable
and still not built, because nothing there is needed to find out whether this
works, and four previous projects died of building it first.

Either way the route in is the same: an item in `NEXT.md` names it. Nothing
enters by argument.

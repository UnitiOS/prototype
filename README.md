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
it for a decade. The bet is the evidence substrate underneath it, and the
business logic that runs from the graph rather than from code. `CLAUDE.md` says
what the system is; `ROADMAP.md` says how far it has got.

**What the kernel must do:** one fact, corrected late, read at four
combinations of valid time and record time, gives four correct and distinct
answers. That is `test_four_reads` in `tests/kernel/test_bitemporal.py`. The
parametrised table is the specification — if you read one thing after this
file, read that.

That is the kernel's bar, not the PoC's. What the PoC as a whole has to show is
a **definition change** result, and it is stated in `ROADMAP.md`.

## Run it

Needs Docker and Python 3.12. Everything below runs from the repo root.

```
make check
```

One command from a clean clone: virtualenv, schema, tests, and a replay that
must come out byte-identical twice. It exits non-zero if either half fails.
**69 tests today.**

`check`, `schema`, `test` and `replay` run against a throwaway database,
`uniti_check`, created on the first run and wiped on every one — `make` resets
what it owns and never touches the working log. `build` and `compile` point
back at the working log deliberately, because that is where the day being
entered lives.

```
make build      render the sealed map into build/sorella/v1/
make compile    run the map's own rules into the operational store
make serve      the loop in a browser, over business/sorella/v3.yaml
```

The demonstration business is a second one, `business/sorella_demo/`, with a
log and an operational store of its own — `uniti_demo` and `uniti_demo_ops` —
so seeding it touches nothing else. Both targets create their databases on the
first run.

```
make demo-seed    seven weeks of paper into uniti_demo, then compile it
make demo-serve   the same four routes over the demonstration map
```

`demo-seed` drops the three kernel tables and writes them again, every row
through `generate.submit`, so it is rerunnable and lands the same count twice.
It compiles afterwards because a form reads its choices out of the operational
store, and a store nothing has filled offers nothing.

The rest of this section is `check` by hand, against the working database, for
when one step needs to be run alone.

```
docker compose up -d                    # postgres:17 on host port 5433
```

Apply the schema. `./components/kernel` is mounted read-only inside the container:

```
docker compose exec -T db psql -U uniti -d uniti -v ON_ERROR_STOP=1 \
    -f /kernel/001_schema.sql
```

On Git Bash prefix that with `MSYS_NO_PATHCONV=1`, or the container path is
rewritten into a Windows one. The script drops and recreates: it is re-runnable.

```
python -m venv .venv
.venv/Scripts/python.exe -m pip install "psycopg[binary]" pytest linkml
.venv/Scripts/python.exe -m pytest tests -q          # expect 69 passed
```

Connection string comes from `UNITI_DSN`, defaulting to
`postgresql://uniti:uniti@localhost:5433/uniti` (`components/kernel/perform.py`).
That default is the working log — running `pytest tests` directly therefore
writes into it, which is why `make test` exists.

```
make replay
```

Seeds 200 synthetic assertions, builds the same projection twice from the log
and checks the two files are byte-identical. **It resets `uniti_check` first**;
run `scripts/seed_200.py` directly and it resets whatever `UNITI_DSN` names
instead. On a non-Windows machine change `PY` at the top of the `Makefile`.

## The three tables

Column list in `components/kernel/001_schema.sql`. It is closed: a new column on
`assertion` for a business reason is a question for Fareza, not a commit.

**`intent`** — one row per user action, not per field written. Who acted, when,
under what action name, optionally why. Everything an action wrote points back
at one intent row, so a whole edit can be traced to a single human decision.

**`assertion`** — the log. Subject, predicate, one value (literal xor entity
reference), the two timestamps, provenance, and `revokes`, which names an
earlier row this one withdraws. A retraction is itself an assertion, so a row
may carry no value at all — see the `value_exactly_one` constraint. Append-only
is enforced by the database, not by convention: `kernel_deny()` triggers plus a
`REVOKE` on UPDATE/DELETE/TRUNCATE. `tests/kernel/test_append_only.py` proves it.

**`entity`** — a registry of identity and nothing else: an id, when it was
minted, and the intent that minted it. There is **no class column**, because
class membership is a claim like any other and claims belong in the log. Saying
"this entity is a student" as a column would make it un-timed, un-sourced and
un-correctable; asserted as `member_of`, it gets the same two clocks, the same
provenance and the same right to be wrong as every other fact.

## business/

Not code: one directory per business, holding one flat file per sealed map
version with its transcript beside it. Written by `seal`, read by `ontology`
and by every generator. `business/sorella/` is the live one — `v1.yaml`, 21
classes and 101 slots, sealed at `b8de674`, with `profile.md` beside it as the
source the map was written from. `business/trial/` and `business/trial2/` are
fixtures that tests and scripts read.

## Which file answers which question

Most of the value in this repo is knowing where a rule lives. Each rule lives
in exactly one place. This file points at them and deliberately does not repeat
them — a restated rule drifts from the one it restates.

| Question | Where the answer lives |
|---|---|
| What is this system, and what must stay true of it? | `CLAUDE.md` |
| How far has it got — milestones, stages, components? | `ROADMAP.md` |
| What is being worked on right now? | `NEXT.md` |
| Why does `as_of` exist? What is settled? | `DECISIONS.md` |
| How is a read resolved — which row wins, and why that one? | docstring of `components/kernel/resolve.py` |
| Which map version applies at a `(valid_at, as_of)`? | docstring of `components/ontology/resolve.py` |
| What turns a draft into a sealed version, and what is refused? | docstring of `components/seal/seal.py` |
| What may be written, and what is deliberately not validated? | docstring of `components/kernel/perform.py` |
| How does a table or a form come out of the map? | docstring of `components/generator/generate.py` |
| How does a rule in the map become SQL that runs? | docstring of `components/compiler/compile.py` |
| What are the columns, constraints and append-only guards? | `components/kernel/001_schema.sql` |
| What must be true, exactly? | `tests/` — the tests are the spec |
| What does a correction look like, versus a change? | `tests/kernel/test_bitemporal.py` fixtures |
| Can I really not UPDATE a row? | `tests/kernel/test_append_only.py`, `components/kernel/002_guard_test.sql` |
| What is undecided, or known-broken and left alone? | `OPEN.md` (typed `[T1]`/`[T2]`/`[T3]`) |
| What does a projection look like, and why is it never stored? | `scripts/project.py` |
| Where does the replay data come from? | `scripts/seed_200.py` (one RNG seed, deterministic) |
| Where does the demonstration business come from? | `business/sorella_demo/draft.txt`, and `scripts/seed_demo.py` fills it |
| What does the smallest possible write look like? | `scripts/write_three.py` |
| What was run, and what was surprising? | `LOG.md` |

`OPEN.md` is worth reading before trusting the kernel. It records things that
are known not to work — revocation does not cascade, `revokes` is not tied to
the same slot — written down rather than patched.

## Working on it

Two skills under `.claude/skills/`, invoked by name:

- `/uniti-discuss` — design questions, reviewing a result, choosing what is next
- `/uniti-build` — one item from `NEXT.md`, run to its done condition

## history/

Material that has stopped being carried: earlier `LOG.md` and `DECISIONS.md`
eras, the retired T2 questions, Marlow (the business Sorella replaced), and the
eight hand-written scripts that once lived under `build/`. Read-only evidence —
quotable to answer a named question, never browsed. Same rule as `../archived/`.

## Not built

The `report` harness and the `agent` MCP are components this lap needs and does
not have yet; they arrive with the stages that need them. The `interview` skill
exists as prose at `components/interview/SKILL.md` but is not installed and is
not current — the stage is deferred, and the file predates the per-business
version store.

Everything listed as out of scope in `ROADMAP.md` is reasonable and still not
built, because nothing there is needed to find out whether this works.

Either way the route in is the same: an item in `NEXT.md` names it. Nothing
enters by argument.

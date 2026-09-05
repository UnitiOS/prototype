---
name: uniti-build
description: Implementation mode for Project Uniti — take one item from NEXT.md to its done condition, run it, and write LOG.md from what actually happened. Use when writing or changing code under components/, scripts/ or tests/, seeding the log, or running make check, make build or make compile. Do not use for design discussion; that is uniti-discuss.
---

# Uniti — build

One item from `NEXT.md`, taken to its done condition.

`CLAUDE.md` is what the system is, and the section **"What must stay true"** is
the part that governs code. Nothing here restates it; read it before writing
anything under `components/`.

## Start

Read the `NEXT.md` item in full, and its done condition especially — it is
written to be executed, and it is what "finished" means. `ROADMAP.md` says what
already exists so nothing gets built twice. `OPEN.md` carries what is
known-broken and deliberately left alone; the same defect discovered a second
time is not a discovery.

Where things live:

    components/kernel/      the log: 001_schema.sql, perform.py, resolve.py
    components/ontology/    which map version applies at a pair of clocks
    components/seal/        draft -> sealed version, and its facts to the log
    components/generator/   a table and a form for one class
    components/compiler/    the map's rules, as SQL, into the operational store
    business/<b>/           sealed map versions and their transcripts
    scripts/                one-off and trial scripts, not part of the system
    tests/                  the specification. Read the test before the code
    history/build-scripts/  scripts that stopped being run

Each component's docstring is its specification — `perform.py`, `resolve.py`,
`ontology/resolve.py`, `seal.py`, `generate.py`, `compile.py`. They are current
and they are the fastest way in.

## Running it

The interpreter is `.venv/Scripts/python.exe`. Postgres is Docker, host port
5433, brought up by `docker compose up -d`.

Three databases, and mixing them up is the one environment mistake worth
guarding against:

| Database | What it is | Reached by |
|---|---|---|
| `uniti` | the working log — Sorella's real map and data | the default `UNITI_DSN`, so any script run directly |
| `uniti_check` | throwaway. Wiped on every run | everything `make` runs |
| `uniti_ops` | the operational store. Dropped and rebuilt | `make compile` |

`make` overrides the DSN to `uniti_check` for `check`, `schema`, `test` and
`replay`, so a sealed version survives any number of checks. `make build` and
`make compile` deliberately point back at the working log, because that is
where the day being entered lives.

    make check          venv, schema, tests, and a replay that must come out
                        byte-identical twice. 65 tests today
    make test           pytest alone
    make replay         seed 200 synthetic assertions, project twice, compare
    make build          render the sealed map into build/sorella/v1/
    make compile        run the map's rules into the operational store
    make check-profile  cross-read business/sorella/profile.md. No database

Running `pytest tests` directly writes into the **working** log, because the
default DSN is `uniti` — `OPEN.md` carries this as a known trap. Use `make
test` unless there is a reason not to.

The components by hand:

    .venv/Scripts/python.exe components/seal/seal.py <draft>.yaml \
        --actor <name> [--into business/<b>] [--sealed-at <iso>]
    .venv/Scripts/python.exe components/generator/generate.py \
        table|form|submit <map>.yaml <CLASS> [--valid-at ...] [--as-of ...]
    .venv/Scripts/python.exe components/compiler/compile.py <map>.yaml \
        [CLASS ...] [--sql] [--into <dir>] [--valid-at ...] [--as-of ...]

On Git Bash, prefix a `docker compose exec` that passes a container path with
`MSYS_NO_PATHCONV=1`, or the path is rewritten into a Windows one.

`build/` is the inspection surface — where a person looks at what the system
produced, scoped `build/<business>/<version>/`. It is gitignored and rebuilt by
one command, so nothing hand-written belongs there. A script that turns up
under `build/` belongs in `scripts/`.

## While building

- **Stop when the done condition passes.** Adjacent code that already works is
  not part of the item.
- **No abstraction layer without a second caller.** One caller means write it
  inline. Interfaces, base classes and plugin points arrive with the second
  case.
- **A design question that blocks you**: pick the simplest thing that works,
  leave a `# TODO:` naming the question, append it to `OPEN.md` as a typed line
  with `blocks:`, and keep going. Do not open a discussion in the code, and do
  not sit idle — carry on with the part of the item that is not blocked.
- **Something that deserves a decision**: say so and propose the wording. Do not
  write `NEXT.md` or `DECISIONS.md` during an implementation run; those are
  written after Fareza has agreed to them in conversation.
- The kernel's column list is closed, and a business need is a reason to change
  the ontology, not the schema.

## Reading what came out

`CLAUDE.md`, "Reading a result": missing information, missing mechanism, or
passing by cheating. The third is the one to watch for in your own work — an
output that looks right because the code knew the domain is a failure, and the
check for it is a grep over `components/` for business terms.

## Finishing

Append to `LOG.md`: the date, what was run, the result, and what was
surprising. Facts only — what happened, with the numbers, not what it means for
the plan. If a hand computation is part of the done condition, the numbers go
in the entry, because that is where the evidence lives.

Then commit. Small and often; the message says what changed and why, in
English.

If the item is finished, say so and stop. Choosing the next one is Fareza's.

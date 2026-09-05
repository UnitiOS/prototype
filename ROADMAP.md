# Roadmap

Where the work stands. This is the only file that says so — `CLAUDE.md`
describes the system and does not track it, and `README.md` tells you how to
run it. When this file and any other disagree about what exists, this one is
the one being kept current.

What is being worked on right now is `NEXT.md`. This file is the horizon
behind it.

Last reviewed: 2026-09-05.

## Definition of done

**The same shrinkage report, computed as it was computed then and with today's
definition, side by side with why the numbers differ.**

Reached in three milestones, because a single distant target cannot be tracked
against — between here and there every week looks the same.

| Milestone | What it is | Done when | Status |
|---|---|---|---|
| One | Onboarding. A graph accurate to the business, generated forms, an operational database | One operational day — Tuesday 16 June 2026 — is entered entirely through generated forms and the closing balances match a hand computation | in progress |
| Two | Refinement, and the business changing | — | not started |
| Three | Analysis of what has accumulated | — | not started |

The shrinkage report is not milestone one.

## The stages

One lap the system runs for one business. `CLAUDE.md` says what each stage
means; this says how far each has been through a lap.

| Stage | Status |
|---|---|
| Interview and mapping | **Deferred for this PoC** (29 Aug). The map is authored by hand and sealed through the same gate an interview would use |
| Graph review | Exercised. `make build` renders the sealed map to OWL, tables and forms under `build/sorella/v1/` |
| Kernel recording | Exercised. Sorella's master data and three stock movements are in the working log |
| Generation | Partly. `generate.py` builds tables and forms from the map; nothing serves them over HTTP yet |
| Live use | Not started. This is milestone one's remaining half |
| Definition change | Not started. Needs the `report` harness |
| Agentic access | Not started. Needs the `agent` MCP |

**Definition change** is the stage that can kill the premise; the rest show the
system can be used, not that it is better.

## The components

| Component | Status | Note |
|---|---|---|
| `kernel` | built | Three tables, append-only enforced by the database |
| `ontology` | built | Version resolution at two clocks |
| `seal` | built | The gate a draft passes to become a version |
| `generator` | built | Tables and forms from a sealed map |
| `compiler` | built 5 Sep | Aggregates and expressions from the map, executed as SQL. It cannot read a parameter, and its `aggregate` cannot say which rows a balance counts — `p_gelato_on_hand` is three rows about nothing |
| `business/` | in use | Not code. Sorella's `v1.yaml` is sealed at `b8de674` — 21 classes, 101 slots |
| `interview` | prose only | `components/interview/SKILL.md`. Not installed as a skill; the stage is deferred and the file predates the per-business version store |
| `report` | not built | |
| `agent` | not built | |

## What has landed recently

- **5 Sep** — the compiler. `make compile` fills `p_ingredient_on_hand` from the
  map's own `aggregate` and `equals_expression`, and the net matches a hand
  computation: Dry store 27, Severn Catering Supplies −37, no location 10. The
  same rule at an earlier `--valid-at` gives 7 / −17 / 10, which is two runs of
  one rule at two clocks — the thing the substrate is for. `LOG.md`, same date.
- **6 Sep** — the first three stages of the trial ran, and one of their results
  was re-read. `p_ingredient_on_hand` reading 5.32 against a hand computation of
  6 was recorded as a missing mechanism and is not one: adding `movement_unit`
  to the aggregate's `by` gives 6 in tins and −0.68 in kilograms as two rows,
  with no code change. A missing **dimension** and a missing **scope** are
  different failures, and only the second is what the PoC is for.
  `DECISIONS.md`, same date.
- **5 Sep** — the rule corpus was measured against the two stores, and a trial
  was designed from what it found. The graph carries six rules, the kernel
  carries 93 parameter values, and none of the 93 is named by any rule in the
  graph, so every one is inert; the fifty-one rules of profile §3.4 are in
  neither store. `NEXT.md` carries the six-stage trial; `DECISIONS.md`, same
  date, carries the six entries behind it.
- **5 Sep** — the design was frozen: three layers, and where a rule lives.
- **4 Sep** — governance rotated. `OPEN.md` compacted from 150 items, `LOG.md`
  and `DECISIONS.md` rotated to `history/`, `build/` triaged from 259 files to 2.

## What is not in scope for the PoC

RLS · Neo4j · observation store · process primitives · emergent layer ·
impact routing · multi-tenancy · marketplace · export

Not forbidden — out of scope. Each is reasonable and none is needed to find out
whether this works. Something leaves this list by becoming an item in
`NEXT.md`, which is a decision taken in conversation.

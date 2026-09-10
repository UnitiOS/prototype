# Roadmap

Where the work stands. This is the only file that says so — `CLAUDE.md`
describes the system and does not track it, and `README.md` tells you how to
run it. When this file and any other disagree about what exists, this one is
the one being kept current.

What is being worked on right now is `NEXT.md`. This file is the horizon
behind it.

Last reviewed: 2026-09-07 (twice).

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
| Generation | Exercised. `generate.py` builds tables and forms from the map, and `components/web/` serves them over HTTP |
| Live use | Begun. The loop runs in a browser: a form writes to the kernel and the table rebuilds itself. Not yet a day entered end to end |
| Definition change | Not started. Needs the `report` harness |
| Agentic access | Not started. Needs the `agent` MCP |

**Definition change** is the stage that can kill the premise; the rest show the
system can be used, not that it is better.

## The demo lap

A second business, run end to end for one purpose: something a person who has
not read this repository can be shown. It is a **prefix of milestone one**, not
a detour — goods in, goods out, a count, and the difference between what was
expected and what was found is the shrinkage report in miniature.

Sorella's `v3` is untouched and stays as evidence. The demo is a business of its
own, so nothing is reversed and a later `v2` of the demo map is a real
definition change rather than a change of scope.

| Where | What |
|---|---|
| `business/sorella_demo/` | `draft.yaml`, `draft.txt`, then `v1.yaml`, `v1.txt` sealed through `seal` |
| `uniti_demo` | the kernel for it. A log of its own; the seed is written through `generate.submit`, never `INSERT` |
| `uniti_demo_ops` | the operational store. Derived, dropped and rebuilt |
| `scripts/seed_demo.py` | the seed: master data and 6-8 weeks of movements |
| `components/agent/` | the MCP surface. Item three |
| `make demo-serve` | as `make serve`, pointed at the two databases above |

Ten or eleven classes against Sorella's twenty-one: `Ingredient`, `Unit`,
`Location` with `InternalLocation` and `Supplier`, `MovementKind`, `Person`,
`StockMovement`, `StockCount`, `StockCountLine`, and the projections
`IngredientOnHand` and `CountedOnHand`. Three of them are documents a person
fills in; the rest are master data, seeded and grouped away from the path the
demonstration walks.

| Item | What it produces | Status |
|---|---|---|
| One — the business | the narrow map, both stores, and a seed large enough to look real | done 7 Sep, validated the same day |
| Two — the surface | navigation by stage, the transcript beside the map, the graph behind a column, and a cell that opens its own assertions | done 7 Sep, all seven conditions checked |
| Two and a half — the data | a seed with both clocks alive and corrections in it, names instead of URIs, and a table that can be sorted and filtered | done 7 Sep, landed at `481ddc5` |
| Three — the agent | an MCP over the graph, the operational database and provenance, and a correction that does not destroy what it corrects | done 10 Sep, validated live with Claude Desktop |

Item three carries claim F — *an agent answering better from the graph than from
tables* — and was validated live via Claude Desktop using 11 generic MCP tools.

## The components

| Component | Status | Note |
|---|---|---|
| `kernel` | built | Three tables, append-only enforced by the database |
| `ontology` | built | Version resolution at two clocks |
| `seal` | built | The gate a draft passes to become a version |
| `generator` | built | Tables and forms from a sealed map |
| `compiler` | built 5 Sep, extended 6 Sep & 9 Sep | Aggregates, expressions, parameters, scoped `where` filters and generic `convert:` unit conversions, executed as SQL |
| `web` | built 6 Sep, widened 7-10 Sep | Sticky 6-stage pipeline navigation, bitemporal `/correct` UI, and `/dashboard` Executive BI. |
| `business/` | in use | Not code. Sorella's `v1.yaml` sealed at `b8de674`; Sorella Demo sealed up to `v5.yaml` |
| `interview` | prose only | `components/interview/SKILL.md`. Not installed as a skill; the stage is deferred and the file predates the per-business version store |
| `report` | not built | |
| `provenance` | built 7 Sep, extended 10 Sep | Every assertion about one subject and predicate, recent activity ledger, and forensic timeline. Five tests |
| `agent` | built 10 Sep | A Universal Model Context Protocol (MCP) server over the graph, the operational store and `provenance`. 11 generic tools, 8 unit tests |

## What has landed recently

- **10 Sep** — universal MCP server built and validated live (`components/agent/`).
  11 domain-agnostic OS primitives over graph, operational projections, and kernel
  provenance. Tested against Claude Desktop: autonomous holistic model comprehension
  succeeded and surfaced pistachio shrinkage anomaly (Claim F validated).
- **10 Sep** — operational forms ergonomics, clock-synchronized ingestion, and
  first-class bitemporal correction & retraction UI (`/correct`) with authorized
  signatories and audit reason codes. Unified sticky 6-stage pipeline navigation.
- **9 Sep** — Executive BI & Decision Intelligence dashboard (`/dashboard`),
  realistic culinary dataset with pistachio loss and stockout risk, generic
  unit conversions (`kg`), scoped internal storage filters, and query planner
  1,000x speedup (`enable_nestloop = off`). Map sealed as `v5.yaml`.
- **7 Sep** — demo item two and a half landed at `481ddc5`: 26-week seed with both
  clocks alive, 32 assertions carrying revokes, sort/filter on URLs, and names
  rather than raw URIs.
- **7 Sep** — demo item two ran and was validated. All seven conditions hold:
  six stage cards, `/said` linking 12 of 12 classes to the sentence that asked
  for them, `/graph` drawing the map and the formula behind a column,
  `components/provenance/` behind `/why`, and 74 tests. Validation then found
  what the item did not ask about: the whole log was recorded in one second and
  holds no `revokes`, so `as_of` is a cliff rather than an axis and a correction
  cannot be shown at all. Missing information, not missing mechanism, and it
  puts an item between the surface and the agent. `LOG.md` and `OPEN.md`, same
  date.
- **7 Sep** — demo item two ran: the surface. `/` is six stage cards, `/said`
  puts the transcript beside the map with all twelve classes linked to the
  paragraph that asked for them, `/graph` draws the twelve classes and — from
  any column header — the rule that fills that column, and `/why` shows every
  assertion ever made about one pair. `components/provenance/` is the one
  kernel reader outside the compiler. `make demo-serve` binds 8100. 74 tests.
  `LOG.md`, same date.
- **7 Sep** — demo item one ran and was validated. `business/sorella_demo/v1`
  is 12 classes; `uniti_demo` holds 242 intents and 2,237 assertions from a seed
  written entirely through the write gate; `p_ingredient_on_hand` reads 59 rows
  at now, 54 at 9 August, 4 at 13 July, and the pistachio price multiplies by
  203.00 asked at 9 August and 214.00 at 10 August with neither row revoking the
  other. The loop closes through the form. Validation found four visible
  defects, none of them mechanism, and they are carried into item two.
  `LOG.md` and `OPEN.md`, same date.
- **7 Sep** — provenance became a surface rather than a privilege. A page that
  opens a cell reads the kernel, which the morning's amendment admitted only for
  the agent; naming the reader instead of the caller keeps the property holding
  something. `components/provenance/` serves both doors. `CLAUDE.md` and
  `DECISIONS.md`, same date.
- **7 Sep** — the demo lap was designed. A second business, `sorella_demo`,
  narrow enough to be shown and still a prefix of milestone one; the agent
  gains the right to read the kernel for provenance, which amends the first of
  the four properties in `CLAUDE.md`. Three items, of which one is in
  `NEXT.md`. `DECISIONS.md`, same date.
- **6 Sep** — the crossing ran. A `parameter` annotation names a key column and
  a slot, and the compiler reads that slot off the log for the entity the key
  resolves to; `ingredient_stock_value` is a balance summed out of the
  movements multiplied by a price stated in the kernel, joined by a name the
  graph gave it. Two of the three kinds of rule in `CLAUDE.md` now execute and
  constraint has no mechanism at all. It cost five lines of SQL and no clock
  machinery, because a parameter is one more read of `stated`. `LOG.md` and
  `DECISIONS.md`, same date.
- **6 Sep** — the PoC turns to an interface before finishing any more
  mechanism. Two weeks of widening produced nothing usable, and neither
  constraint nor definition change yields something a person can be shown.
  Nothing is reversed and nothing is dropped; the order changes. `DECISIONS.md`
  and `NEXT.md`, same date.
- **5 Sep** — the compiler. `make compile` fills `p_ingredient_on_hand` from the
  map's own `aggregate` and `equals_expression`, and the net matches a hand
  computation: Dry store 27, Severn Catering Supplies −37, no location 10. The
  same rule at an earlier `--valid-at` gives 7 / −17 / 10, which is two runs of
  one rule at two clocks — the thing the substrate is for. `LOG.md`, same date.
- **6 Sep** — the working log was rejected as the trial's substrate. About
  1,300 of its 1,742 assertions are master data stamped with one adoption date
  that is wrong wherever the profile gives a real one, and about 300 belong to
  Marlow. It is kept as evidence and stops being carried; the trial moves to a
  log seeded from everything 16 June touches — milestone one's own day, so the
  seed is milestone-one work rather than a detour. `NEXT.md` carries it.
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

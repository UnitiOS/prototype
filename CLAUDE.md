# Uniti — PoC

An evidence substrate: an append-only claim log with per-field provenance and
two time axes, and a business's own logic carried in a graph rather than in
code.

This file says what the system is. Three others say the rest:

| To know | Read |
|---|---|
| Where the work stands | `ROADMAP.md` |
| What is being worked on now | `NEXT.md` |
| How to run it, and where each answer lives | `README.md` |

## What is being proven

Not schema generation — that is a commodity, and ERPNext has shipped it for a
decade. Generation still happens and has a stage of its own; it is a means,
never the thing being proven.

The substrate is half of it. The other half is that the business's own logic —
how a balance is derived, what a threshold is, what is refused — lives in the
graph and in the log and never in code. An ERP carries those rules too: in a
config column that gets overwritten, and in a branch that gets recompiled. The
claim here is that they can be carried somewhere that keeps their history and
can still be executed. If they end up in code, the graph is decoration and this
is an ERP with fewer features.

The definition of done and the three milestones are in `ROADMAP.md`.

Domain: inventory for an ice cream business, Sorella Gelato.

## The three layers

The design of record is the 31 August diagram,
`../doc/Screenshot 2026-08-31 225845.png`. In words:

| Layer | Says | Read by |
|---|---|---|
| Graph | what things mean, how numbers are derived | the compiler, and nothing else |
| Kernel | what was stated, by whom, when, and what was later found wrong | the compiler, replay, provenance |
| Operational DB | what is true now, plain rows and plain indexes | forms, dashboards, agents |

Four properties hold the three apart, and each is a claim the PoC is testing.

- **Only the compiler and the provenance surface read the kernel.** Forms,
  lists and dashboards read the operational database, never the log. A read path
  that reaches `assertion` from a form defeats the separation. The provenance
  surface is the one exception and only for provenance — who said this, when, on
  what authority, and what was later withdrawn. It has two doors, a page and the
  agent's MCP, and one implementation behind them. It never reads the kernel to
  compute a number; a number comes from the operational database like everything
  else. Decided 7 Sep: provenance is the one thing the operational database
  cannot carry without becoming the log.
- **The operational database is derived.** Its schema comes from the graph, its
  rows from the kernel. It may be dropped whole and rebuilt, it is never a
  source of truth, and nothing writes to it directly. It is a database of its
  own rather than a schema inside the log, so a join between a projection and
  an `assertion` row is not merely discouraged — it is impossible.
- **One write gate.** Every door — a form, the chatbot, `seal` — produces one
  `intent` and N `assertion`, and nothing else writes anywhere.
- **The kernel is a ledger, not a balance sheet.** It holds what was said,
  including what was said wrongly. Nothing computed ever enters it.

## The stages

A **flow**, not a build list: one lap the system runs for one business, from
someone describing it to an agent acting on it. Nobody is "at" a stage.

Named, never numbered. Interview and mapping were two stages until they became
one, and every number after them moved. A name survives the next merge.

| Stage | What happens |
|---|---|
| Interview and mapping | the business is described to a chatbot, and the description becomes an ontology to an existing standard |
| Graph review | the ontology is visualised and judged |
| Kernel recording | everything stated is in the log |
| Generation | the operational database, its schema and its rules, and the UI, are all compiled from the ontology and filled from the kernel |
| Live use | the forms are used, the kernel is checked |
| Definition change | a definition moves, history is replayed |
| Agentic access | the data is navigated and acted on |

**Definition change** is the stage that can kill the premise; the rest show the
system can be used, not that it is better.

Which stages have been through a lap is in `ROADMAP.md`.

## The components

Stages and components are many-to-many: one component serves several stages,
one stage needs several components. Which of these exist today is in
`ROADMAP.md` — this table is what each one is.

| Component | What it is | Reads | Writes |
|---|---|---|---|
| `kernel` | the log, and the only write gate into it | — | `intent`, `entity`, `assertion` |
| `ontology` | which map version applies at a pair of clocks | sealed version files | nothing |
| `seal` | the gate a draft passes to become a version | a draft | `business/<b>/vN.yaml`, and the stated facts to the kernel |
| `generator` | a table and a form for one class | map, kernel | the kernel, through `submit` |
| `compiler` | the map's rules, executed as SQL | map, kernel | the operational database |
| `business/` | map versions and their transcripts. Files, no code | — | — |
| `interview` | a skill: a conversation that produces a draft | — | a draft |
| `report` | the same report under two definitions, and the difference | operational database | nothing |
| `provenance` | every assertion ever made about one subject and predicate, with its two clocks and its provenance. The one thing that reads the kernel outside the compiler, behind two doors | kernel | nothing |
| `agent` | an MCP surface over the graph and the operational database | graph, operational database, `provenance` | the kernel, through the write gate |

`business/` is one directory per business, holding one flat file per sealed
version with its transcript beside it. It is written by `seal` and read by
`ontology`.

## The kernel

Three tables. The column list is closed.

- **`intent`** — one row per user action, not per field written. Who acted,
  when, under what action name, optionally why. Everything an action wrote
  points back at one intent row, so a whole edit traces to a single human
  decision.
- **`assertion`** — the log. Fifteen columns: subject, predicate, one value
  (literal xor entity reference), `valid_from` and `recorded_at`, provenance
  (`source`, `confidence`, `authority`, `intent_id`, `ontology_version`), and
  `revokes`, which names an earlier row this one withdraws. A retraction is
  itself an assertion, so a row may carry no value at all. Append-only is
  enforced by the database — `kernel_deny()` triggers plus a `REVOKE` on
  UPDATE, DELETE and TRUNCATE — not by convention.
- **`entity`** — a registry of identity and nothing else: an id, when it was
  minted, and the intent that minted it. There is **no class column**, because
  class membership is a claim like any other. Asserted as a fact, it gets the
  same two clocks, the same provenance, and the same right to be wrong as
  everything else.

A new column on `assertion` for a business reason is a design change, not a
commit: business needs live in the ontology. The columns and their constraints
are `components/kernel/001_schema.sql`.

## Where a rule lives

Every rule a business states is one of three kinds, and each has one home.

| Kind | Lives in | Compiles to |
|---|---|---|
| Computation — how a number is derived | graph, as an expression | SQL filling a projection column |
| Parameter — a number with a history | kernel, as a dated assertion | a constant resolved at both clocks |
| Constraint — what is refused | graph for the shape, kernel for its numbers | form validation, write gate, violation table |

The graph is the only thing the compiler reads. **A parameter in the kernel is
inert until the graph names it.** That is what makes a rule execute, and it is
why a rule can never be recorded in the kernel alone.

## What must stay true

These are the properties that make a result mean anything. Each one, if it
breaks, makes a passing test prove nothing.

- **The generator and the compiler may not know what a business is.** No
  business term reaches a live code path under `components/` — not `stock`, not
  `material`, not `quantity`. Comments, docstrings and usage examples are
  documentation and are exempt; a branch on the word is not. The compiler reads
  `over`, an operator, `by` and `equals_expression`, and emits SQL. If the code
  carries the logic, the graph is decoration and milestone one's claim is false
  however perfectly the forms render.
- **A slot's identity is its `slot_uri`.** It survives renames. When the
  business changes what it calls something, the slot name changes and the
  `slot_uri` stays exactly where it was.
- **No rule construct enters a map before something can execute it.** Notation
  that moves nothing is worse than an absence, because it reads as capability.
- **The compiler does not decide which rows a balance counts.** A movement
  naming no place at one end produces its group rather than being filtered. A
  `WHERE` that tidies the output is the code taking a view the map never
  stated.
- **Nothing computed enters the kernel**, and no judgement either. The log
  stores raw facts — never a `no_show` status. Detection is computed; judgement
  is asserted.

Changing one of these is a conversation, not a commit.

## Settled findings

Settled means not re-discussed. It does not mean proven. The reasoning is in
`DECISIONS.md`, and behind it in `../archived/`.

1. Two time axes, and a correction ("we were wrong") is a different event from
   a change ("the world changed"). This is the product.
2. The log stores raw facts, never judgements.
3. Class is not a column on `entity`. Class membership is an assertion.
4. Detection is computed; judgement is asserted.
5. XTDB, Palantir Foundry and ERPNext already built adjacent things. What is
   left is narrow: open source, small organisations, LLM-assisted authoring.

A settled finding reopens on failing code or a real user, not on a more elegant
argument.

## Reading a result

A failure goes in one of three baskets, and one question decides which: **is
there an input that would make this pass?**

- **Missing information** — yes, there is. Repair the profile or the data.
  Nothing has been learned about the system.
- **Missing mechanism** — no input would make it pass. This is what the PoC is
  for. Either widen the mechanism, or accept the limit and write it down.
- **Passing by cheating** — it passed, but only because the generator knew the
  domain. Counts as a **failure**, however correct the output looked.

## The files

| File | Nature |
|---|---|
| `CLAUDE.md` | This file. What the system is |
| `ROADMAP.md` | Where the work stands: milestones, stages, components |
| `NEXT.md` | What is being worked on. Each item has a done condition that can be executed |
| `OPEN.md` | Open questions, one line each, typed `[T1]` / `[T2]` / `[T3]` |
| `DECISIONS.md` | Append-only. A decision and its reason, dated |
| `LOG.md` | What was run, what came out, and what was surprising |
| `README.md` | How to run it, and which file answers which question |

`DECISIONS.md` is append-only: a dated entry is never edited, and a reversal is
a new entry naming what it reverses. The standing-rules index above the line is
derived and may be rewritten.

Everything written to disk is in English, including commit messages.
Conversation is whatever Fareza is speaking.

## Working here

Two modes, one session. Each has a skill, invoked by name:

- **`/uniti-discuss`** — reading, thinking, deciding. Ends in a line in
  `DECISIONS.md`, `OPEN.md` or `NEXT.md`, or in nothing, which is also a
  result.
- **`/uniti-build`** — one item from `NEXT.md`, taken to its done condition,
  and `LOG.md` written from what actually ran.

One rule joins them: **a decision is not written in the same act as the code it
justifies.** `NEXT.md` and `DECISIONS.md` are written when Fareza has agreed to
the wording in conversation, never as a side effect of an implementation run.
Finishing an item and choosing the next one are two acts, and the second needs
him. Four previous projects died of rebuilding rather than shipping, and the
mechanism was always the same: widening the work and justifying the widening in
a single motion.

## The old corpus

`../archived/` holds the old design corpus. Its authority is revoked; it is
still evidence. `history/` holds this project's own rotated material — earlier
`LOG.md` and `DECISIONS.md` entries, retired business maps, scripts that
stopped being run. Nothing there is deleted; it stops being carried.

Both are **quoted to answer a named question**, with the file and section
cited, so the answer can be checked without anyone re-reading the corpus. The
previous cycle died from reading and amending that corpus, not from lacking it.

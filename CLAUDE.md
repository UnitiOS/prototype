# Uniti — Working Rules

## The bet

An evidence substrate: an append-only claim log with per-field provenance and
two time axes. Not schema generation — that is a commodity (ERPNext has shipped
it for a decade). Generation still happens, and has a stage of its own; it is a
means, never the thing being proven.

The substrate is half of it. The other half is that the business's own logic —
how a balance is derived, what a threshold is, what is refused — lives in the
graph and in the log and never in code. An ERP carries those rules too: in a
config column that gets overwritten, and in a branch that gets recompiled. The
claim here is that they can be carried somewhere that keeps their history and
can still be executed. If they end up in code, the graph is decoration and this
is an ERP with fewer features.

Definition of done for the PoC: **the same shrinkage report, computed as it was
computed then and with today's definition, side by side with why the numbers
differ.**

It is reached in three milestones, because a single distant target cannot be
tracked against — between here and there every week looks the same.

- **Milestone one** — onboarding. A graph accurate to the business, generated
  forms and an operational database. Done when one operational day is entered
  entirely through generated forms and the closing balances match a hand
  computation.
- **Milestone two** — refinement, and the business changing.
- **Milestone three** — analysis of what has accumulated.

The shrinkage report is not milestone one.

## The three layers

The design of record is the 31 August diagram, `../doc/design-2026-08-31.png`.
In words:

| Layer | Says | Read by |
|---|---|---|
| Graph | what things mean, how numbers are derived | the compiler, and nothing else |
| Kernel | what was stated, by whom, when, and what was later found wrong | the compiler, replay, provenance |
| Operational DB | what is true now, plain rows and plain indexes | forms, dashboards, agents |

- **Nothing but the compiler reads the kernel.** Forms, lists and dashboards
  read the operational database, never the log. A read path that reaches
  `assertion` from a form is a defect, not a shortcut.
- **The operational database is derived.** Its schema comes from the graph, its
  rows from the kernel. It may be dropped whole and rebuilt, it is never a
  source of truth, and nothing writes to it directly.
- **One write gate.** Every door — a form, the chatbot, `seal` — produces one
  `intent` and N `assertion`, and nothing else writes anywhere.
- The kernel is a ledger, not a balance sheet. It holds what was said, including
  what was said wrongly. Nothing computed ever enters it.

## The stages

A **flow**, not a build list: one lap the system runs for one business, from
someone describing it to an agent acting on it. Nobody is "at" a stage. What
gets built is the next section.

Named, never numbered. Interview and mapping were two stages until they became
one, and every number after them moved. A name survives the next merge.

- **Interview and mapping** — the business is described to a chatbot, and the
  description becomes an ontology to an existing standard
- **Graph review** — the ontology is visualised and judged
- **Kernel recording** — everything stated is in the log
- **Generation** — the operational database, its schema and its rules, and the
  UI, are all compiled from the ontology and filled from the kernel
- **Live use** — the forms are used, the kernel is checked
- **Definition change** — a definition moves, history is replayed
- **Agentic access** — the data is navigated and acted on

**Definition change** is the stage that can kill the premise; the rest show the
system can be used, not that it is better.

Domain: inventory for an ice cream business.

## The components

Stages and components are many-to-many: one component serves several stages,
one stage needs several components.

| Component | Kind | Serves |
|---|---|---|
| `kernel` | store | recording, replay, provenance |
| `compiler` | compiler | generation, live use, definition change |
| `business/` | store | map versions and transcripts — files, no code |
| `interview` | skill | interview and mapping |
| `seal` | tool | interview and mapping, recording |
| `ontology` | library | version resolution, read by generation, report, agent |
| `generator` | generator | generation, live use |
| `report` | harness | definition change |
| `agent` | MCP | agentic access |

**Built: `kernel`, `ontology`, `seal`, `generator`. Nothing else exists.**

**The interview is deferred for this PoC** (29 Aug). For the PoC the map is an
input to what is being proven, not part of it: the map is authored by hand and
sealed through the same gate that an interview would use. The stage is completed
after the consuming components have been through a lap.
What follows describes that stage as it will be built, not as it is being run.

The interview runs in Claude Desktop with a skill and the filesystem MCP
already in use. Most of that stage is not built: the conversation, the model and
the interface are the product, and the graph render is LinkML's own
`gen-erdiagram` — which is why no exporter appears above. What is built is prose
and one tool. A skill can ask for a valid draft; only `seal` can guarantee one.

## Six findings that are closed

Closed means not re-discussed, not proven. Reasoning lives in `../archived/`.

1. Two time axes, and a correction ("we were wrong") is distinct from a change
   ("the world changed"). This is the product.
2. The log stores raw facts, never judgements. Never `status='no_show'`.
3. Class is not a column on `entity`. Class membership is an assertion.
4. Detection is computed; judgement is asserted.
5. XTDB, Palantir Foundry and ERPNext already built adjacent things. What is
   left is narrow: open source, small organisations, LLM-assisted authoring.
6. The largest risk is the design spiral, not the technical problem. Four
   previous projects died from rebuilding rather than shipping. The stop-list
   and the `NEXT.md` ceiling exist because of it.

## Reading a result

A failure goes in one of three baskets, and one question decides which: **is
there an input that would make this pass?**

- **Missing information** — yes, there is. Repair the profile or the data.
  Nothing has been learned about the system. Most of what v1 exposed is here.
- **Missing mechanism** — no input would make it pass. This is what the PoC is
  for. Either widen the mechanism, or accept the limit and write it down.
- **Passing by cheating** — it passed, but only because the generator knew the
  domain. Counts as a **failure**, however correct the output looked.

**The generator may not know what a business is.** No business term reaches a
live code path under `components/` — not `stock`, not `material`, not
`quantity`. Comments, docstrings and usage examples are documentation and are
exempt; a branch on the word is not. If the code carries the logic then the
graph is decoration, and milestone one's claim is false even when every form
renders perfectly.

## The kernel

Three tables: `intent`, `assertion`, `entity`. The column list is closed.
If you need a new column on `assertion` for a business reason: **stop and ask.**
Business needs live in the ontology.

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

**No rule construct enters a map before something can execute it.** For weeks
`sorella/v1.yaml` carried four `aggregate` annotations and two
`equals_expression` that `generate.py` never read — measured, zero occurrences —
so every derived column was sought in the log as a stated fact and came back
empty. Notation that moves nothing is worse than an absence, because it reads as
capability. This replaces the older brake, which pointed the other way.

The compiler may not know what a business is, on the same terms as the
generator: it reads `over`, `sum`, `by` and `equals_expression`, and emits SQL.
A branch on a business word is the same failure there as anywhere else.

## Stop-list

RLS · Neo4j · observation store · process primitives · emergent layer ·
impact routing · multi-tenancy · marketplace · export

Not forbidden — routed. Nothing here is built unless an item in `NEXT.md` names
it. Components enter through `NEXT.md`, never by editing this file.

## Deciding alone, and stopping

Decide alone when all four hold:

- the change is inside the `NEXT.md` item you are on
- `git revert` undoes it — no data migration, nothing else depends on it yet
- it adds no dependency, service, or stored artefact
- it changes the meaning of nothing already in the log

Stop and ask when any one holds:

- the decision deserves a `DECISIONS.md` line — the sign is that someone will
  later ask why it is this way
- it touches the read rule, the schema, or the `assertion` column list
- it answers a T3 in `OPEN.md`, or uncovers a new one
- you must choose between two designs **no test can tell apart**
- the done condition in `NEXT.md` turns out to be wrong or unreachable

Stopping must be cheap: append a tagged line to `OPEN.md` with a `blocks:`
field, carry on with the part of the item that is not blocked, and report it in
`LOG.md`. Do not sit idle waiting.

## Process rules

- PoC data is synthetic. **No decision here is irreversible.** `DROP DATABASE`
  and reseed takes 30 seconds. Production discipline does not apply yet.
- No new `.md` files at the root. The six that exist are enough.
- Slides and diagrams live in `../doc/`, are always derived, and are never
  treated as a source of truth.
- `build/` is the inspection surface: where a person looks at what the system
  produced — the graph in a viewer, the generated forms, the projection tables.
  It is not a working directory and nothing is ever kept there.
  - Scoped by business and map version, `build/<business>/<version>/`, never by
    a filename prefix or a hand-typed counter.
  - Under each: `graph/`, `forms/`, `tables/`, and `log/` for the generators'
    stderr. `build/check/` holds what `make check` writes and nothing else.
  - Nothing hand-written ever lives under `build/`. A script found there belongs
    in `scripts/`.
  - Rebuilt by one command, and gitignored, so it may be deleted whole at any
    time — which holds only while the two rules above do.
- A new, more elegant architecture idea mid-stream: record it in `OPEN.md`, do
  not build it. That is the exact shape that killed the four previous projects.

## For Claude Code

You write code, `LOG.md`, and appended lines in `OPEN.md`. Nothing else.

- **Never write** `NEXT.md` or `DECISIONS.md`. If a task needs redefining, say
  so and stop — do not edit the file. When something deserves to be decided,
  propose the wording in `LOG.md`.
- **Never use the `uniti-pm` skill.** It is for discussion sessions.
- **Stop when the done condition in `NEXT.md` passes.** Do not improve adjacent
  code, do not refactor what already works, do not generalise a second case
  that has not appeared. Overshooting is this agent's version of the design
  spiral.
- **No abstraction layer without a second caller.** One caller means write it
  inline. Interfaces, base classes and plugin points arrive with the second
  case, never in anticipation of it.
- Work one `NEXT.md` item at a time. Do not continue into the next without
  being asked.
- A design question that blocks you: pick the dumbest thing that works, leave
  `# TODO:` with the question, keep going. Do not open a discussion in the code.
- After each run, append to `LOG.md`: date · what was run · the result · what
  was surprising. Facts only, no plans.
- Commit small and often. The gap since the last commit is a tracked metric.
- **Everything in English**, including commit messages.

## The files

| File | Written by | Nature |
|---|---|---|
| `CLAUDE.md` | Fareza | Constitution. Almost never changes |
| `DECISIONS.md` | Desktop | Append-only. A decision and its reason |
| `OPEN.md` | Desktop, appended by Claude Code | Open questions. One line, typed |
| `NEXT.md` | Desktop | Max 5 items. The only mutable file |
| `LOG.md` | Claude Code | What was run, and what happened |
| `README.md` | Claude Code | Orientation. Points, never restates |

Claude Code never writes `NEXT.md`. Desktop never writes `LOG.md`.

## The old corpus

The old design corpus lives in `../archived/`. Its authority is revoked, but it
is still evidence.

It may be **quoted to answer a named question**, with the file and section
cited so the answer can be checked without anyone re-reading the corpus. Never
browse it for context, never write to it. The previous cycle died from reading
and amending that corpus, not from lacking it.

`history/` holds this project's own rotated material: earlier `LOG.md` and
`DECISIONS.md` entries, retired business maps, scripts that stopped being run.
The same rule governs it — quoted by date to answer a named question, never
browsed for context. Nothing is deleted; it stops being carried.

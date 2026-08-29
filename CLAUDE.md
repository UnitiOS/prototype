# Uniti — Working Rules

## The bet

An evidence substrate: an append-only claim log with per-field provenance and
two time axes. Not schema generation — that is a commodity (ERPNext has shipped
it for a decade). Generation still happens, and has a stage of its own; it is a
means, never the thing being proven.

Definition of done for the PoC: **the same shrinkage report, computed as it was
computed then and with today's definition, side by side with why the numbers
differ.**

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
- **Generation** — UI and projection tables come from the ontology and the kernel
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
| `kernel` | store | recording, live use, every reader |
| `business/` | store | map versions and transcripts — files, no code |
| `interview` | skill | interview and mapping |
| `seal` | tool | interview and mapping, recording |
| `ontology` | library | version resolution, read by generation, report, agent |
| `generator` | generator | generation, live use |
| `report` | harness | definition change |
| `agent` | MCP | agentic access |

**Built: `kernel`, `ontology`, `seal`. Nothing else exists.**

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
6. The largest risk is process, not technical. Four previous projects died
   because nobody outside the team ever used them.

## The kernel

Three tables: `intent`, `assertion`, `entity`. The column list is closed.
If you need a new column on `assertion` for a business reason: **stop and ask.**
Business needs live in the ontology.

## Stop-list

RLS · Neo4j · observation store · constraint engine · process primitives ·
emergent layer · impact routing · multi-tenancy · marketplace · export

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

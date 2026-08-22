# Uniti — Working Rules

## The bet

An evidence substrate: an append-only claim log with per-field provenance and
two time axes. Not schema generation — that is a commodity (ERPNext has shipped
it for a decade).

Definition of done for the PoC: **one fact, corrected late, read at four
combinations of valid time and record time, gives four correct and distinct
answers.**

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

## Not built until a real user asks for it

DDL compiler · UI generator · RLS · Neo4j · observation store · MCP ·
constraint engine · process primitives · emergent layer · impact routing ·
multi-tenancy · marketplace · export

All of them are reasonable. None of them is needed to find out whether this works.

## Process rules

- PoC data is synthetic. **No decision here is irreversible.** `DROP DATABASE`
  and reseed takes 30 seconds. Production discipline does not apply yet.
- A design question open for more than 20 minutes: pick the dumbest thing that
  works, mark `# TODO`, move on.
- No new `.md` files at the root. The five that exist are enough.
- Slides and diagrams live in `../doc/`, are always derived, and are never
  treated as a source of truth.
- A new, more elegant architecture idea mid-stream: record it in OPEN.md, do not
  build it. That is the exact shape that killed the four previous projects.

## For Claude Code specifically

**Stop when the done condition in NEXT.md passes.** Do not improve adjacent
code, do not refactor what already works, do not generalise a second case that
has not appeared. Overshooting is this agent's version of the design spiral.

**No abstraction layer without a second caller.** One caller means write it
inline. Interfaces, base classes and plugin points are added when the second
case arrives, never in anticipation of it.

**Write `LOG.md` after every run**, and only after: date · what was run · the
result · what was surprising. Plans do not go there. Never touch NEXT.md.

**When blocked, stop and report — do not design around it.** A blocker belongs
in OPEN.md as a one-liner for the next Desktop session, not in a workaround that
becomes permanent.

**Everything in English**, including commit messages.

## The files

| File | Written by | Nature |
|---|---|---|
| `CLAUDE.md` | Fareza | Constitution. Almost never changes |
| `DECISIONS.md` | Desktop | Append-only. One line per decision |
| `OPEN.md` | Desktop | Open questions. One line, typed |
| `NEXT.md` | Desktop | Max 5 items. The only mutable file |
| `LOG.md` | Claude Code | What was run, and what happened |

Claude Code never writes NEXT.md. Desktop never writes LOG.md.

The old design corpus lives in `../archived/`. Its authority is revoked, but it
is still evidence.

**Read it only to answer a question that already exists** — one written in
OPEN.md, or one raised by failing code. Never read it to look for questions,
never read it for context at the start of a session, never write to it.
That directional rule is the whole point: the previous cycle died from reading
and amending the corpus, not from lacking it.

## For Claude Code specifically

You write code and `LOG.md`. Nothing else.

- **Never write** `NEXT.md`, `DECISIONS.md`, or `OPEN.md`. Those are Desktop's.
  If a task needs redefining, say so and stop — do not edit the file.
- **Never use the `uniti-pm` skill.** It is for discussion sessions.
- Work one `NEXT.md` item at a time, to its stated done condition. Do not
  continue into the next item without being asked.
- If a task turns out to need something on the "not built" list, **stop and
  ask.** Do not build it because it is blocking. That is how 29 components got
  designed last time.
- A design question that blocks you: pick the dumbest thing that works, leave
  `# TODO:` with the question, keep going. Do not open a discussion in the code.
- After each run, append to `LOG.md`: what was run, the result, what was
  surprising. Facts only, no plans.
- Commit small and often. The gap since the last commit is a tracked metric.

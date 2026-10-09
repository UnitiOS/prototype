# Uniti — proof of concept, prototype 2

Uniti keeps a business's facts and the business's own logic apart.

- **Facts** go into an append-only log. Nothing in it is ever changed or deleted.
  Every statement says when it became true in the world and when it was
  recorded, so any number can be read as it stood on any day, and as it was
  known on any day.
- **Logic** — what the business records and how its numbers are worked out —
  lives in a graph (LinkML plus a small rule vocabulary of Uniti's own), not in
  code. The graph is split into modules that are versioned, owned, and shared.
- **Numbers** are derived: a compiler turns the graph into SQL and builds tables
  from the log. The tables can be dropped and rebuilt at any time, and every
  cell can be traced back to the statements that hold it up.
- **The Studio** is where graphs are written. An AI agent builds them from what
  a person says about their business; the system checks every step; the person
  approves. Business examples with expected numbers are the contract: they run
  on every change, and a version cannot be sealed while one fails.

This README describes what exists in the code today. Two other documents sit
beside it:

| Document | What it holds |
|---|---|
| `P2.md` (Indonesian) | Prototype 2 from start to now: its goals, every stage, what each test found, the problems still open, and where it is going. |
| `DESIGN_NOTES.md` (Indonesian) | Why the system is shaped this way: roles and core, how the core may grow, the Studio, module kinds, ownership, one kernel per business. Reference, not rules. |
| `archived/` | The working documents of each stage, kept as they were written. |

Prototype 1 (a presentation of the idea, with hand-written graphs) is at tag
`p1-final`. Prototype 2 is built on branch `p2/refactor`.

---

## 1. How the pieces fit

### 1.1 The log (kernel)

Three tables in PostgreSQL (`components/kernel/001_schema.sql`):

- **`intent`** — one row per action: who acted (`actor_id`, and `agent_id` when an
  agent did), the action's name, a reason code, a note.
- **`entity`** — identity only. There is no class column; which class a thing
  belongs to is itself a statement.
- **`assertion`** — one fact per row, fifteen columns, a closed list: subject,
  predicate, a literal value or a reference, `valid_from` (true in the world
  from), `recorded_at` (known from), `revokes` (the earlier statement it
  withdraws or corrects), the intent that wrote it, `source`, `confidence`,
  `authority`, and `ontology_version` (the module version it was stated under).

Triggers and revoked privileges refuse `UPDATE`, `DELETE` and `TRUNCATE`.
`perform()` is the only write path; `resolve_single()` reads one fact at a pair
of clocks `(valid_at, as_of)`. A correction is a new statement that `revokes`
the old one, so what was believed before the correction can still be read.

### 1.2 Modules

A module is a directory in a **store** of files, holding sealed versions that
never change once written:

```
@scope/name/
  package.yaml        name, title, description, kind, (business)
  v1.yaml             the graph: classes, slots, rules (LinkML)
  v1.txt              transcript: every step that built it, and who took it
  v1.examples.yaml    the business examples it was sealed with
  v1.plan.yaml        the plan the person agreed to (when built with the agent)
  v1.chat.yaml        the conversation that built it (when built with the agent)
  draft.*             the version being written, if one is open
```

- A module **pins** the exact versions it uses (`@uniti/party@v1`). A new
  version of a pinned module changes nothing until the pinning module is
  sealed again with the new pin.
- Every slot carries its own `slot_uri`. In the log a predicate is the full URI
  expanded from the prefixes of the module that wrote it, so two modules that
  happen to share a prefix or a class name never share a predicate or a table.
- The store may have several roots (`UNITI_PACKAGES`, separated by `;`); the
  first root that holds a module wins. A business's private modules live in a
  root of their own, read before the shared one.

**Four kinds** of module (manifest field `kind`):

| Kind | Example | Owned by | What it is for |
|---|---|---|---|
| `core` | `@uniti/core` | the core keepers | roles and their bindings, read by mechanisms |
| `library` | `@uniti/party`, `@uniti/item`, `@uniti/transaction` | the core keepers | what nearly every business needs: one Party, one Item, the shape of a transaction with lines |
| `module` (default) | a rental module, a deposit module | its author | one business function, built on the library |
| `application` | `@kemahceria/sewa` | one business | that business's composition of pinned modules, its own additions, and its own examples; private |

**Roles** (`@uniti/core@v2`): `Thing`, `Resource`, `Event`, `Flow`, with the
bindings `amount`, `moment`, `affects`. `@uniti/transaction` adds the roles
`Transaction` and `TransactionLine` (bindings `transaction_counterparty`,
`line_transaction`). A class claims a role with `mixins:` and names which of
its own slots fills each binding. Roles are a shared vocabulary for finding and
connecting modules; a rule may total over a role, but an application normally
names which module's class it counts (explicit composition). No module may make
a class a kind of another module's class (`kind_of_foreign_class`): modules
connect only by pointing at each other.

**Ownership** (`components/owners`). Each owner of a name such as `@uniti` is a
dated statement in the kernel. The first person to seal under a name nobody
owns becomes its owner; after that only an owner seals under it, and owners add
or remove owners (never the last one). An application must be named after its
business. There is no sign-in: an owner is the name a person writes.

### 1.3 From draft to sealed version

1. **Draft.** `draft.yaml` is the only editable file in the store, and it
   changes only through steps from a closed list of 38 (`start`, `pin`,
   `add_class`, `add_slot`, `attach`, `bind`, `fill_role`, `aggregate`,
   `parameter`, `expression`, `add_example`, `record`, `expect`,
   `agree_example`, `agree_plan`, `label`, `revise`, `discard`, and their
   undoing). Nobody writes YAML. Every step is appended to `draft.txt` with the
   time and whether a person or the agent took it.
2. **Holes.** Reading a draft runs the seal's own checks, the compiler's, the
   recording standard's and the examples, and returns everything that is
   missing as questions, each with the finite set of answers that would fix it.
   A hole is a refusal that has not fired yet; there is no second judge.
3. **Examples.** A few records and the numbers they must add up to, with the
   story in the business's words. Each example runs in a scratch log of its own
   (temporary tables on one connection, always rolled back): the records go in
   through the same form gate as real data, the numbers come out of the same
   compiler. An example written by the agent is a proposal until a person
   agrees to it, and the agent cannot change one a person agreed to. Every
   column the draft computes must be checked by some example.
4. **Recording standard** (`components/standard`). English names and
   descriptions (labels in the person's language beside them), naming patterns,
   a description for every class and slot, a unit and a direction for every
   number (`increase`, `decrease`, `magnitude`, `level`), and a meaning for every
   date (`happened`, `recorded`, `takes_effect`, `expected`).
5. **Seal** (`components/seal`). The one gate from draft to version. It needs a
   `valid_from`, a `slot_uri` and a visible range on every slot, a transcript,
   one version per module in the closure, no name clashes, every example
   passing and agreed, every computed column checked, the standard met, and the
   sealer owning the name. It registers every predicate in the kernel.

Every refusal (`components/refusal`) is data: a `code` from a closed list of
121, where it happened, what was expected against what was there, and the
repairs with their valid options. The sentence a person reads is derived from
those parts.

### 1.4 A business, its applications, its records

- **One kernel per business** (`components/business`). A kernel says once which
  business it belongs to (`declare`); whoever declares it becomes the first
  owner of the business's name.
- **Install.** An application version is installed into its business's kernel
  from a day (`install`, `stop`). Installing is a statement in the kernel, so
  which version a business used on any day is read at two clocks like any
  number. Installing registers the vocabulary of everything the application
  pins. Nothing may pin an application, and another business's application is
  refused and hidden from the catalogue.
- **Forms** (`components/generator`). Columns and forms come from the sealed
  graph. A form writes only through the version installed for the day it
  records (`not_installed` otherwise). One submission is one intent and its
  statements; reference fields offer the records that exist; enum values and
  required fields are enforced.
- **Tables** (`components/compiler`). The compiler executes `aggregate` (sum or
  count over the rows of a class, grouped by a slot of those rows or by a slot
  of the record one of them points at, `slot.slot`), `parameter` (a value looked
  up from another record), `equals_expression` (arithmetic over columns, every
  divisor guarded), `where` (narrowing to a class) and `convert` (unit
  factors). It writes the results into an operational database that can be
  dropped and rebuilt.
- **Provenance** (`components/provenance`). Who stated what about a subject,
  when, and what was later withdrawn. In the application a cell opens onto the
  statements that make it up.
- **Catalogue and health** (`components/modules`). The catalogue is computed
  from what was sealed and is searchable; it says which class fills which role
  and who reads each predicate. Health reports six kinds of dead weight in one
  application: terms nothing reads, empty columns, empty classes, unfilled
  roles, lagging pins, and facts it cannot see. `roles.fit` reports what moving
  an application's pins onto another module would cost.

### 1.5 The agent

`components/agent` builds graphs through the same Studio steps a person uses.

- **Tools** (flat arguments, no unions, so any provider or a self-hosted model
  can call them): `look`, `options`, `do` (a batch of steps that stops at the
  first refusal), `catalogue`, `guide`. The actor is always `agent`. There is no
  tool to seal or to agree: those belong to the person.
- **Order kept by the system.** A turn ends as a `Reply`, a `Question`, a
  `Plan` or a `Proposal`. The work goes plan → examples → rules → seal, one
  request each. The agent takes no step before the person agrees to its plan,
  and writes no rule for a table before the person agrees to an example for
  it. A plan put forward before the agent searched the catalogue, and a
  proposal the draft does not bear out, are sent back before anybody sees them.
- **Accountant.** A separate model context that reads only the person's words
  and works out the numbers an example should expect, without seeing the graph.
- **Guide.** Generated from the steps, the refusal catalogue, the standard and
  the store's roles, and tested to name all of them (about 22,000 characters).
  The note that opens each request says which kind of module is open and so
  whom the agent is helping.
- **Models and limits** (`config/agent.yaml`, the only place a provider is
  named). Today: Gemini 3.8 Flash through Vertex AI for both parts. Per request:
  25 calls, 600,000 tokens, $0.20, 60 seconds per call. The last call that fits
  is kept so the agent can tell the person what it did and what is left.
- **Records.** The conversation, every call included, is kept beside the draft
  (`draft.chat.yaml`) and sent whole with each call (readings repeated unchanged
  are answered in one line, stale readings are shortened past 100,000 tokens).
  Every call to a model is written whole under `build/calls/`.
- **Rehearsal and eval.** `rehearse SCRIPT` plays a scripted builder with no
  model; `make app` plays one for `@rehearsal/levels`. `make eval` runs the
  tasks in `tests/agent/evals` (each three times, within its own budget).

### 1.6 The web application

React, TypeScript and Vite in `web/`, served by the API on one port. Five areas:

| Area | What it shows |
|---|---|
| Kernel | entities, actions and the log, read at two clocks that can be dragged on a clock plane |
| Modules | every module and version, a timeline, what each version pins, diffs between versions |
| Application | an application's tables at two clocks, how each column is worked out, a cell opened onto its statements, the forms that write to the kernel, which version is installed from when, and installing a version |
| Catalogue | search over everything sealed, by kind and by role, and one application's health |
| Studio | the whole screen: the conversation with the agent beside a map of the module (React Flow, laid out by dagre). The map has two views — what is in the module, and how its numbers are worked out — and can follow one example's numbers through the rules. What the agent changes is marked on the map as it works. Every gesture on the map is a Studio step, so a person can do by hand anything the agent does. Plan and proposal cards carry the buttons only a person may press: agree, and freeze (seal). Labels can be shown in the person's language ("Words in"). |

### 1.7 The API

`components/api` (Starlette) is the one JSON API that the web application and
scripts read. Every read takes `valid_at` and `as_of`.

- `/api/kernel/*` — summary, entities, intents, log, clock plane
- `/api/modules*` — modules, graph, version, diff, classes
- `/api/catalogue`
- `/api/app/*` — read, roles, health, check, fit, projection, cell, form;
  `state` (submit a form), `install`, `stop` (POST)
- `/api/business`, `/api/names` (and `/add`, `/remove`)
- `/api/studio/*` — drafts, draft, `step` (POST), chat, `ask` (POST, streamed one
  JSON object per line while the agent works), `seal` (POST)

### 1.8 Command line

```
python -m components.modules  list | find | health | examples | seal | register
python -m components.studio   drafts | show | steps | do   (do --by agent)
python -m components.agent    guide | look | catalogue | rehearse | ask | watch | eval
python components/compiler/compile.py APP.yaml --into DIR
python scripts/load_facts.py FACTS.yaml --actor NAME
python scripts/dev_modules.py STORE_ROOT [--extend]
```

---

## 2. Components

| Component | Responsibility |
|---|---|
| `components/kernel` | The three append-only tables, the triggers that guard them, `perform()` and `resolve_single()` |
| `components/ontology` | Which sealed graph version applies at `(valid_at, as_of)` |
| `components/modules` | The store, pins, kinds; `check` (every refusal at once), `roles` and `fit`, `catalogue`, `health`, `diff` |
| `components/seal` | The gate from draft to version; registering a version's vocabulary in a kernel |
| `components/standard` | The recording standard, one source for the seal, the Studio holes and the agent guide |
| `components/examples` | Business examples run in a scratch log; what the examples owe a draft |
| `components/studio` | Drafts, the closed list of steps, holes, transcript, changes between two readings |
| `components/generator` | Columns and forms from a graph; `submit`, the form's write gate |
| `components/compiler` | Rules executed as SQL into the operational database |
| `components/provenance` | Who stated what, when, and what was withdrawn |
| `components/refusal` | Refusals as data, their closed list of codes, and the sentence derived from them |
| `components/business` | One kernel per business; install and stop |
| `components/owners` | Who may seal under a name |
| `components/agent` | Builder, accountant, tools, guide, conversation, budget, call records, rehearsal, eval |
| `components/api` | The JSON API and the static web application |

Components contain no business words. Everything domain-specific lives in
test fixtures and in the stores under `build/`.

---

## 3. What is in the repository

```
components/        the mechanisms (above)
packages/@uniti/   core v1 and v2; party, item, transaction v1
config/agent.yaml  models, limits and prices for the agent
web/               the web application and its tests
tests/             Python tests, one folder per component; fixtures
scripts/           dev_modules.py, load_facts.py, seed_200.py, project.py
archived/          the working documents of each stage of prototype 2
build/             (ignored by git) development stores, test environments, call records
```

**Demonstration content.** Everything in `tests/modules/fixtures/` is made up.
`@demo/catalog`, `@demo/inventory`, `@demo/stock` (an application of the
business `demo`) and `@rival/stock-moves` give the mechanisms something to run
on. Each manifest declares `purpose: demonstration`, and that word is carried
onto every intent that writes one of them, so the log says of itself which rows
are made up. `@rival/stock-moves` shares no class name, slot name or prefix
with `@demo/inventory`; `@demo/stock@v3` is `v2` pinned to the rival instead,
and both produce the same numbers from different predicates.

**Test environments kept under `build/`** (not in git): `build/blank/` (the first
empty-store test), `build/dua/` (the two-round test: kernels `uniti_komunitas`
and `uniti_kemah`, the stores, and the scripts that entered the records),
`build/exp*/` (the composition experiment), `build/calls/` (every model call).

---

## 4. Running

Needs Docker, Python 3.12 and Node 22. PostgreSQL 17 runs in the container
`uniti-db` on port 5433.

```
make check        # database, kernel schema, tests, and a replay that must be byte-identical
make test         # Python tests only
make web-test     # web tests only

make dev-db       # an empty development log (uniti_dev), the demonstration modules
                  # sealed into build/dev/packages, then the demonstration facts
make dev-compile  # the demonstration application's tables into uniti_dev_ops
make web          # build the web application (runs its tests first)
make app          # API and web application on http://localhost:8200
make web-dev      # frontend with live reload on http://localhost:5173 (needs `make app`)
make eval         # the agent eval; calls the model and costs money
```

Tests run against throwaway databases (`uniti_check`, `uniti_check_ops`) and
refuse to run against any other. Today: 337 Python tests and 42 web tests.

**Environment variables**

| Variable | Meaning |
|---|---|
| `UNITI_DSN` | the kernel (log) database |
| `UNITI_OPS_DSN` | the operational database the compiler writes tables into |
| `UNITI_PACKAGES` | store roots, separated by `;`, first one wins |
| `UNITI_AGENT_CONFIG` | another agent config instead of `config/agent.yaml` |
| `UNITI_AGENT_REHEARSAL`, `UNITI_AGENT_REHEARSAL_PAUSE` | the rehearsal script `make app` plays, and its pace |

Model credentials are read from the environment, or from `.env` (ignored by
git) where the environment says nothing. The Vertex route uses
`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` and `GOOGLE_CLOUD_QUOTA_PROJECT`
with application-default login (`gcloud auth application-default login`),
in the `us` location.

---

## 5. What it does not do yet

Known limits of the code as it stands. `P2.md` §6 says where each was found.

- **No sign-in.** An owner or actor is a name typed by a person; ownership rules
  keep the record straight but secure nothing. Registering and installing are
  not checked against ownership.
- **Forms are not usable by a non-technical person.** They show English
  machine names even where a module carries labels, ask the person to invent an
  address for each record, ask for the date twice, and show rows by address
  rather than by name.
- **No correction screen.** The API accepts `revokes` (correct or withdraw a
  statement); the web application has no control for it.
- **The compiler cannot yet:** total only the rows whose value meets a
  condition (`where` compares nothing but class); group by a fact two records
  away; total over a computed table; read multi-valued slots; post one record
  into others. The agent is told to say so rather than build around it
  (`not_possible_yet`).
- **`moment` has no executor.** `Event` claims the compiler reads it; nothing
  does.
- **Roles are not filled where they should be.** In every agent-built module so
  far, quantities never filled `Flow`.
- **No alignment between modules.** Nothing can state that two modules' classes
  or predicates mean the same thing, so after a module swap the old records are
  read only by rules written against the old module.
- **Unpinning a module that is still used** is not refused at the step itself.
- **One shared registry does not exist yet.** The shared modules live in file
  stores; names are owned per kernel.
- **The agent runs on Gemini only.** Calls sometimes take far longer than the
  timeout says, and the per-request budget reserves a full-price call, which
  stops long conversations early.

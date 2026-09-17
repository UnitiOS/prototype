# Uniti — An Ontological Operating System over a Bitemporal Claim Log

Uniti is an append-only evidence substrate and a declarative operational platform. It replaces destructive database mutation and hardcoded business logic with an **immutable bitemporal claim log** paired with a **declarative ontology graph** expressed in LinkML.

From a domain model alone, Uniti compiles:

1. **Relational projections** — multi-CTE views carrying no hand-written business logic
2. **Write gates and input forms** for transaction ingestion
3. **Forensic provenance timelines** and time-travel querying
4. **Domain-agnostic agent tools** conforming to the Model Context Protocol (MCP)

---

## The Problem

Most operational software commits three design errors:

1. **Destructive mutation.** `UPDATE` and `DELETE` destroy evidence. A row's prior state is gone unless audit tables are retrofitted around it.
2. **A single clock.** One timestamp conflates *when something happened* with *when the system learned of it*. A backdated correction then becomes indistinguishable from a real-world change.
3. **Imperative logic lock-in.** Calculations scatter across application code, ORMs, and stored procedures. Changing a rule means refactoring code.

## The Response

- **Append-only kernel.** One fact is one row. No row is ever updated, deleted, or truncated; database triggers enforce this physically, and the privileges are revoked besides.
- **Two time axes.** Every assertion carries `valid_from` and `recorded_at`. Reads take both — `(valid_at, as_of)` — which makes time travel and non-destructive retrospective correction ordinary operations rather than special cases.
- **Per-field provenance.** Attribution (`intent_id`, `source`, `confidence`, `authority`) is recorded per statement, not per record.
- **The graph is the source of truth.** Rules, aggregations, unit conversions, and guards are declared in LinkML. A compiler turns the graph into SQL.
- **Agents are first-class.** Domain-agnostic OS primitives are exposed over standard JSON-RPC stdio.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          1. GRAPH LAYER (LinkML)                        │
│   Declarative ontologies: classes, slots, invariants, derivation rules  │
│   packages/  (composable modules)   ·   business/  (single-file maps)   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────┐
│     3. OPERATIONAL & QUERY LAYER      │   │          2. KERNEL LAYER          │
│  - Compiled multi-CTE SQL projections │   │  - PostgreSQL append-only ledger  │
│  - Single write gate (generate.py)    │◄──┤    (intent, entity, assertion)    │
│  - Web interface                      │   │  - Triggers deny UPDATE & DELETE  │
│  - MCP servers for agents             │   │  - Bitemporal indexing            │
└───────────────────────────────────────┘   └───────────────────────────────────┘
```

### 1. Graph layer

Two ways to express a domain, both LinkML, both sealed the same way:

- **`business/<name>/`** — a single-file map per version (`v1.yaml`, `v2.yaml`, …). The original form.
- **`packages/<scope>/<name>/`** — composable modules with a `uniti.package.yaml` manifest and a `schema/` directory, resolved through `components/linter/package_loader.py`. `@uniti/core` defines the root metamodel: five archetypes (**Agent, Resource, Commitment, Event, Projection**) that every domain class must descend from.

Derivation is declared through annotations, which is the entire vocabulary the compiler understands:

| Annotation | Meaning |
|---|---|
| `aggregate:` | Totals a numeric slot over a source class (`sum` is the only operator), grouped by `by`, with optional `where` / `is_a` filtering |
| `convert:` | Factor conversion between measurement units, resolved through a conversion class |
| `equals_expression:` | Closed arithmetic over other columns of the same projection |
| `parameter:` | A single fact read off the entity a key column names |

### 2. Kernel layer

Defined in `components/kernel/001_schema.sql`. Three tables, closed column lists:

- **`intent`** — who acted, when, under what action, and why. Every write links back to one.
- **`assertion`** — the claim log: `subject_id`, `predicate_id`, `value_literal` XOR `value_ref`, `valid_from`, `recorded_at`, `confidence`, `source`, `authority`, `revokes`.
- **`entity`** — the identity registry. There is no class column; class membership is itself an assertion.

A `kernel_deny()` trigger raises on `UPDATE`, `DELETE`, and `TRUNCATE`; those privileges are also revoked from `PUBLIC`.

### 3. Operational layer

The compiler reads the log through the map and fills a store in a **separate database**, so no page and no query can join a projection to an `assertion` row. Projections are derived caches: they are dropped and rebuilt, never treated as the source of truth.

---

## Components

| Path | Responsibility |
|---|---|
| `components/kernel/` | Schema, deny triggers, the write primitive (`perform`), single-fact resolution (`resolve`) |
| `components/compiler/` | LinkML → SQL compiler and aggregate planner |
| `components/generator/` | The single write gate (`submit`) and dynamic form generation |
| `components/seal/` | Draft validation and version sealing (draft → immutable `vN`) |
| `components/ontology/` | Version resolution across both time axes |
| `components/provenance/` | Forensic audit reader and claim history tracer |
| `components/linter/` | Package loader and the deterministic semantic linter |
| `components/studio/` | Ontology authoring: catalog, schema patcher, prompts, LLM agent |
| `components/agent/` | MCP servers — operational primitives and Studio authoring tools |
| `components/web/` | HTTP server, rendering, diagrams, Studio workbench handler |

### Authoring a projection

A class inheriting `Projection` is computed; nobody states a row of one. Each
of its value columns carries exactly one rule, and the authoring tools write
all three:

| Rule | Shape | Fills a column with |
|---|---|---|
| `equals_expression` | `"{column_a} * {column_b}"` | arithmetic over other columns of the same class |
| `aggregate` | `{over, sum, by, where?, convert?}` | a total over the rows of a source class, grouped by the key columns |
| `parameter` | `{of, slot}` | one fact the log holds about the entity a key column names |

A projection with no `aggregate` has no grouping, so it is not a table the
compiler can fill — it is a list somebody has to type in. `LINT-006` refuses it.

### Linter rules

| Rule | Severity | Checks |
|---|---|---|
| `LINT-000` | error | The schema and its imports resolve at all |
| `LINT-001` | error | Every class descends from one of the five archetypes |
| `LINT-002` | error | Every slot declares a `slot_uri` — its identity in the kernel, which `seal` also requires |
| `LINT-003` | error / warning | Commitment lifecycles are sound: declared initial state, known transitions, no deadlocked states |
| `LINT-004` | error | Invariant expressions parse and contain only safe AST nodes, rooted at `self` or `actor` |
| `LINT-005` | error | A projection's `equals_expression` references only slots that class actually has |
| `LINT-006` | error | A projection computes: at least one slot carries an `aggregate`, its `over` and `by` name real classes and slots, its measure can be totalled, and all its aggregates group by the same keys |
| `LINT-007` | error | A class is whole: one identifier slot, no two slots on one `slot_uri`, and no derivation rule on a class that is not a projection. Slots are shared by name, so a definition written for one class lands on every class that lists it |

---

## Two prototypes

The repository carries two running configurations of the same components.

| | **P1** | **P2** |
|---|---|---|
| Purpose | The operational walk: forms, projections, audit | Modular metamodel, its dashboard, and the authoring workbench |
| Graph source | `business/<name>/vN.yaml` | `packages/<scope>/<name>/` |
| Default port | 8000 | 8100 |
| Studio | off | on |
| `/studio`, `/dashboard` | 404 | served |
| Start | `make p1-serve` | `make p2-serve` |

Mode is explicit on the command line, and P1 refuses Studio routes outright:

```bash
serve.py <map> --port 8100 --mode p2 --studio
```

---

## Quick start

**Prerequisites:** Docker and Docker Compose, Python 3.12, Git.

```bash
make check
```

`make check` creates the virtual environment, starts PostgreSQL 17 on host port `5433`, applies the kernel schema to a throwaway database, runs the test suite, then seeds synthetic assertions and projects them twice — asserting the two projections come out byte-identical.

### Other targets

| Target | Does |
|---|---|
| `make schema` | Start the database, apply the kernel schema to the check database |
| `make test` | Run the test suite |
| `make replay` | Seed, project twice, assert determinism |
| `make compile` | Compile projections into the operational store |
| `make p1-serve` / `make p2-serve` | Run the web interface in either mode |
| `make mcp-serve` | Run the operational MCP server |
| `make mcp-studio-serve` | Run the Studio authoring MCP server |
| `make p2-bootstrap` | Register the core metamodel into a P2 kernel |
| `make p2-check` | Run the P2 test suite |

---

## The web interface

Every page carries two clock inputs in the header:

- **`valid_at`** (effective time) — how the world stood at a chosen moment
- **`as_of`** (record time) — what the system believed at a chosen moment

Both live on the URL, so any view is a link somebody can send, and moving a clock is a reload.

| Route | Shows |
|---|---|
| `/` | The stages, in the order they happen |
| `/said` | The narrative description beside the map it became |
| `/graph` | The map drawn; with `?class=&column=` it draws the rule deriving one column |
| `/why` | The raw claim ledger for one subject and predicate, with a bitemporal timeline |
| `/classes` | Every class the map gives a form, and every class it gives a table |
| `/form/<Class>` | A generated form; `POST` submits through the write gate |
| `/correct` | Retroactive correction and retraction, without mutating history |
| `/table/<Class>` | A projection compiled at the current clocks |
| `/dashboard` | What the modular layer holds: packages on the load path, archetypes, linter gates (P2 only) |
| `/studio` | The ontology workbench (P2 only) |

---

## Agent interface (MCP)

Two servers, both JSON-RPC 2.0 over stdio (`2024-11-05`). Neither contains a domain word: the same primitives operate any business.

**Operational server** — `components/agent/server.py`

| Graph | Digital twin | Provenance & write |
|---|---|---|
| `graph_get_schema` | `ops_list_projections` | `kernel_get_activity` |
| `graph_update_draft` | `ops_query_projection` | `kernel_trace_provenance` |
| `graph_validate_draft` | `ops_explain_projection` | `kernel_submit_transaction` |
| `graph_seal_version` | | `kernel_correct_assertion` |

**Studio server** — `components/agent/studio_server.py`

`studio_init_package` · `studio_inspect_package` · `studio_propose_patch` · `studio_search_catalog` · `studio_validate_linter` · `studio_render_graph` · `studio_seal_package`

### Connecting a client

The server names no default business. State it in the environment, or pass `business` on every call.

```json
{
  "mcpServers": {
    "uniti": {
      "command": "<repo>/.venv/Scripts/python.exe",
      "args": ["<repo>/components/agent/server.py"],
      "env": {
        "UNITI_DSN": "postgresql://uniti:uniti@localhost:5433/<log_db>",
        "UNITI_OPS_DSN": "postgresql://uniti:uniti@localhost:5433/<ops_db>",
        "UNITI_BUSINESS": "<name under business/>",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

---

## Architectural invariants

These hold across the codebase and must not be broken.

**1. Live code is domain-blind.**
No business term may appear in `components/`. Domain vocabulary belongs exclusively in `business/*.yaml` and `packages/**/schema/*.yaml`. A compiler that recognised a column name would be defective: point it at another map and another table must come out.

**2. One write gate.**
Never `INSERT INTO assertion` directly. Every write passes through `generate.submit()`, which mints an atomic `intent`, validates slot ranges and references, and assigns bitemporal stamps and attribution consistently.

**3. Immutability is enforced by the database.**
Never attempt `UPDATE`, `DELETE`, or `TRUNCATE` on `assertion`, `intent`, or `entity`. Retraction and correction are new assertions carrying `revokes`.

**4. A slot's identity is its URI.**
Every slot declares an explicit `slot_uri`, and `seal` refuses one that does not. Facts are recorded against the URI, never the slot's name — a URI derived from the name would change on every rename and orphan every fact already recorded under it. Where an authoring tool has no canonical URI to anchor to, it mints one and **writes it into the draft**, so the identity becomes a reviewable declaration rather than a value recomputed later.

**5. Projections are ephemeral.**
The operational store is a derived cache. It may be dropped and recompiled at any time and is never the source of truth.

**6. Tests touch throwaway databases only.**
Both `UNITI_DSN` and `UNITI_OPS_DSN` must point at throwaway databases. The operational one matters just as much as the log: compiling a projection *drops and rebuilds* its table, so a run that inherits a live operational store silently empties it. `tests/conftest.py` pins both and refuses to run otherwise.

---

## Repository layout

```
.
├── business/               # Single-file LinkML maps, one directory per domain
├── packages/               # Composable LinkML modules (@uniti/core = metamodel)
├── components/             # The system itself — see the Components table
├── scripts/                # Operational CLI utilities: seeding, projection, checks
├── tests/                  # Test suites, including tests/p2 for the modular layer
├── docker-compose.yml      # PostgreSQL 17
├── Makefile                # Automation targets
└── README.md
```

`business/` and `packages/` carry example domains used to exercise the system. They are fixtures, not part of it — everything under `components/` is written to work equally well against a map it has never seen.

---

## Manual execution

```bash
# 1. Start the database
docker compose up -d

# 2. Apply the kernel schema to a throwaway database
docker compose exec -T db psql -U uniti -d uniti_check -v ON_ERROR_STOP=1 -f /kernel/001_schema.sql

# 3. Run the tests (conftest pins both DSNs to throwaway stores)
.venv/Scripts/python.exe -m pytest tests -q

# 4. Verify replay determinism
.venv/Scripts/python.exe scripts/seed_200.py
.venv/Scripts/python.exe scripts/project.py build/check/projection_a.txt
.venv/Scripts/python.exe scripts/project.py build/check/projection_b.txt
.venv/Scripts/python.exe scripts/project.py --compare build/check/projection_a.txt build/check/projection_b.txt
```

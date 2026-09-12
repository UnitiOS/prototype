# Uniti — The Ontological Operating System & Bitemporal Claim Log

Uniti is an append-only evidence substrate and declarative operational platform. It replaces destructive database mutations and hardcoded business logic with an **immutable bitemporal claim log** paired with a **declarative ontology graph** (LinkML). 

From a high-level domain model, Uniti automatically compiles:
1. **Dynamic relational projections** (materialized multi-CTE views with zero hardcoded business logic)
2. **Transaction ingestion write-gates and user forms**
3. **Forensic provenance timelines and time-travel querying**
4. **Universal AI Agent tools** conforming to the Model Context Protocol (MCP)

---

## The Core Problem & Thesis

Most enterprise software (ERPs, CRMs, and operational databases) commits three fundamental design errors:
1. **Destructive Mutation:** `UPDATE` and `DELETE` destroy evidence. When a database row is updated, the previous state of the world is erased unless expensive audit tables are retrofitted.
2. **Single-Clock Confusion:** A database timestamp usually conflates *when an event happened in the real world* (`valid_from`) with *when the system learned about it* (`recorded_at`). This makes backdated corrections ("we made a mistake about January") indistinguishable from real-world changes ("the price changed in March").
3. **Imperative Business Logic Lock-in:** Calculations (e.g. stock reconciliation, taxes, commissions) are scattered across application code, ORMs, and stored procedures. Modifying a business rule requires refactoring application code.

### The Uniti Solution:
- **Append-Only Kernel:** One fact is one row in `assertion`. No row is ever updated, deleted, or truncated. Database triggers physically enforce immutability.
- **Two Time Axes (Bitemporality):** Every assertion carries `valid_from` and `recorded_at`. Reads take both `(valid_at, as_of)`, allowing true time travel and non-destructive retrospective corrections.
- **Per-Field Provenance:** Attribution (`intent_id`, `source`, `confidence`, `authority`) is recorded at the granularity of individual statements, not entire records.
- **Graph as the Single Source of Truth:** Business rules, aggregations, unit conversions, and validation guards are declared in standard LinkML YAML schemas. The compiler translates the graph into performant SQL queries.
- **First-Class AI Agent Protocol:** Exposes 11 domain-agnostic OS primitives via Model Context Protocol (MCP) over standard JSON-RPC stdio.

---

## 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          1. GRAPH LAYER (LinkML)                        │
│   Declarative Domain Ontologies: Classes, Slots, Invariants, & Rules    │
│   (business/sorella/, business/sorella_demo/)                           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────┐
│     3. OPERATIONAL & QUERY LAYER      │   │          2. KERNEL LAYER          │
│  - Dynamic Multi-CTE SQL Projections  │   │  - PostgreSQL Append-Only Ledger  │
│  - Single Write-Gate (generate.py)    │◄──┤    (intent, entity, assertion)    │
│  - Executive BI Dashboard (/dashboard)│   │  - Triggers deny UPDATE & DELETE  │
│  - Universal MCP Server (agent/)      │   │  - Bitemporal Indexing (5433)     │
└───────────────────────────────────────┘   └───────────────────────────────────┘
```

### 1. Graph Layer (LinkML Ontology)
- Located in `business/<business_name>/`.
- Expresses classes, relationships, and business logic using LinkML.
- Custom annotations define formulas:
  - `aggregate:` Scoped aggregation (`sum`, `count`) with `where: {is_a: ...}` filtering.
  - `convert:` Factor conversion across measurement units (e.g., cartons/tins to base kilograms).
  - `equals_expression:` Closed algebraic expressions across columns in a projection.
  - `parameters:` Attribute lookups linked to master data entities.

### 2. Kernel Layer (PostgreSQL Append-Only Claim Log)
- Defined in `components/kernel/001_schema.sql`.
- Strictly maintains three closed tables:
  - **`intent`**: Captures who acted, when, under what action name, and the human reason. Every write links back to an intent.
  - **`assertion`**: The claim log. Records `subject_id`, `predicate_id`, `value_literal` XOR `value_ref`, `valid_from`, `recorded_at`, `confidence`, `source`, `authority`, and `revokes`.
  - **`entity`**: Minted identity registry (`entity_id`, `uri`, `recorded_at`, `intent_id`). Class membership is an assertion (`member_of`), never a static column.
- **Append-only enforcement:** `kernel_deny()` triggers raise database exceptions on `UPDATE`, `DELETE`, or `TRUNCATE`.

### 3. Operational & Projection Layer
- Translates ontology rules into high-speed PostgreSQL Multi-CTE queries.
- Incorporates planner hints (`SET enable_nestloop = off; SET jit = off`) to bypass query optimizer pitfalls on unindexed dynamic CTEs, slashing execution times from 50s to 0.05s.
- Materializes projections into a derived operational database (`uniti_demo_ops`).

---

## Repository Structure

```
.
├── business/               # Declarative LinkML business ontologies
│   ├── sorella/            # Full reference model (gelato enterprise: v1–v3)
│   ├── sorella_demo/       # Live interactive demo model (sealed v1–v5)
│   └── trial/              # Minimal fixture ontology for LinkML tests
├── components/             # Core Uniti subsystem components (domain-agnostic)
│   ├── agent/              # Universal Model Context Protocol (MCP) server
│   ├── compiler/           # LinkML-to-SQL compiler & aggregate planner
│   ├── generator/          # Single write-gate (submit) & dynamic form generator
│   ├── kernel/             # PostgreSQL schema, deny-triggers, & connection helpers
│   ├── ontology/           # Bitemporal version resolution across time axes
│   ├── provenance/         # Forensic audit reader & historical claim tracer
│   ├── seal/               # Verification & version-sealing gate (draft -> version)
│   └── web/                # HTTP server, Executive BI dashboard, & SVG graph renderer
├── scripts/                # Operational CLI utilities
│   ├── check_profile.py    # Cross-validates business profiles against raw rules
│   ├── project.py          # Bitemporal projection builder & diff comparator
│   ├── seed_200.py         # Deterministic seed generator for regression testing
│   ├── seed_demo.py        # Realistic 6-month culinary enterprise seeder
│   ├── owl_domains.py      # OWL domain inference utility
│   └── render_map.py       # Map markdown and documentation renderer
├── tests/                  # 9 dedicated pytest suites (90 unit tests)
│   ├── agent/              # MCP protocol, tool dispatch, & schema inspection
│   ├── compiler/           # Scoped aggregates, unit conversions, & CTE validation
│   ├── generator/          # Dynamic form emission & transaction generation
│   ├── kernel/             # Bitemporal read matrix & append-only trigger enforcement
│   ├── ontology/           # Multi-version resolution at given (valid_at, as_of)
│   ├── provenance/         # Claim history, retraction tracking, & author tracing
│   ├── seal/               # Draft validation & sealing rules
│   └── trial/              # LinkML feature compatibility tests
├── docker-compose.yml      # PostgreSQL 17 multi-database container definition
├── Makefile                # Standard automation targets
└── README.md               # System overview and operational guide
```

---

## Quick Start & Verification

### Prerequisites
- **Docker** and Docker Compose
- **Python 3.12**
- Git

### 1. Verify Everything in One Command (`make check`)

From a clean clone, run:
```bash
make check
```
`make check` will:
1. Initialize the Python virtual environment (`.venv`) and install dependencies (`psycopg[binary]`, `pytest`, `linkml`).
2. Launch the PostgreSQL 17 Docker container on host port `5433`.
3. Wipe and re-apply the kernel schema to a throwaway database (`uniti_check`).
4. Execute the complete test suite (**90 passed in <2s**).
5. Seed 200 synthetic bitemporal assertions, project them twice, and assert that the output is **byte-identical twice in a row**.

---

## Running the Web Demonstration

Uniti includes an interactive web application running over `business/sorella_demo/v5.yaml` (a realistic artisanal gelato enterprise dataset with opening inventories, supplier deliveries, production batches, retail POS scans, and physical stocktake variance).

### Step 1: Seed the Demo Database
```bash
make demo-seed
```
This drops and recreates `uniti_demo` and `uniti_demo_ops`, loads 11,700+ assertions spanning 6 months, and compiles all digital twin projection tables.

### Step 2: Start the Web Server
```bash
make demo-serve
```
The server binds to **`http://localhost:8100`**.

### The 6-Stage Web Walk
Open your browser to `http://localhost:8100/` to explore the stages:

| Stage | Route | Description |
|---|---|---|
| **Overview** | `/` | Pipeline walk through the 6 stages of data life. |
| **Stage 1 · Narrative** | `/said` | Plain-English business transcript displayed side-by-side with the LinkML ontology it created. |
| **Stage 2 · Domain Graph** | `/graph` | Interactive Mermaid diagram with zoom/pan. Querying with `?class=...&column=...` highlights the exact derivation formula for any projected column. |
| **Stage 3 · Kernel Audit** | `/why` | Raw forensic audit ledger reading directly from `intent` and `assertion`. Includes a visual bitemporal timeline showing active vs revoked claims. |
| **Stage 4 · Forms Hub** | `/classes` | Auto-generated input forms for Events (e.g. `StockMovement`) and Master Data, reading select options dynamically from the operational store. |
| **Write Gate** | `/form/<Class>` | Submits new transactions through `generate.submit()`, minting entities and recording atomic intent. |
| **Bitemporal Correction** | `/correct` | Dedicated UI to retroactively correct or retract earlier assertions without mutating history. |
| **Stage 5 · Projections** | `/table/<Class>` | Dynamic digital twin projections. See `/table/StockReconciliation` for system vs. physical count variance and financial loss calculations. |
| **Stage 6 · Executive BI** | `/dashboard` | Executive Decision Dashboard with high-level KPI cards, safety stockout alerts, and anomaly detection (e.g., £2,000+ Sicilian Pistachio Paste shrinkage). |

### Global Bitemporal Time Travel
Every page features sticky header clock inputs:
- **`valid_at` (Effective Time):** View what the state of the world was at any date.
- **`as_of` (Record Time):** View what the system believed at any date (reconstructing historical knowledge before later corrections were submitted).
- **`[ ↻ Live Today ]`**: Instantly resets both clocks to current real time.

---

## Universal AI Agent Server (Model Context Protocol / MCP)

Uniti provides a built-in, domain-agnostic **MCP Server** (`components/agent/server.py`) conforming to the standard JSON-RPC 2.0 stdio protocol (`2024-11-05`). It allows external AI agents (Claude Desktop, Cursor, Antigravity, or custom autonomous loops) to explore the ontology, query the digital twin, audit provenance, and submit verified transactions.

### Running the MCP Server
```bash
make mcp-serve
```

### Connecting to Claude Desktop / Cursor
Add the following to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "uniti": {
      "command": "C:/Users/<username>/Desktop/Uniti/PoC/.venv/Scripts/python.exe",
      "args": [
        "C:/Users/<username>/Desktop/Uniti/PoC/components/agent/server.py"
      ],
      "env": {
        "UNITI_DSN": "postgresql://uniti:uniti@localhost:5433/uniti_demo",
        "UNITI_OPS_DSN": "postgresql://uniti:uniti@localhost:5433/uniti_demo_ops",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### The 11 Domain-Agnostic OS Primitives

The server contains **zero domain words**. An agent can operate any business (manufacturing, hospitality, logistics, healthcare) using the same 11 primitives:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        11 MCP TOOLS BY PILLAR                          │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ 1. GRAPH PILLAR   │ 2. TWIN PILLAR    │ 3. PROVENANCE & WRITE PILLAR   │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ graph_get_schema  │ ops_list_projections│ kernel_get_activity          │
│ graph_update_draft│ ops_query_projection│ kernel_trace_provenance      │
│ graph_validate_draft│ ops_explain_projection│ kernel_submit_transaction  │
│ graph_seal_version│                   │ kernel_correct_assertion       │
└───────────────────┴───────────────────┴────────────────────────────────┘
```

#### Graph Pillar
- `graph_get_schema`: Reads sealed LinkML ontologies, classes, slots, ranges, and formulas.
- `graph_update_draft`: Modifies draft ontology schemas during interactive business modeling.
- `graph_validate_draft`: Checks drafts against LinkML metamodel constraints and naming rules.
- `graph_seal_version`: Cryptographically seals an approved draft into an immutable version (`v1`, `v2`, ...).

#### Digital Twin & Operational Pillar
- `ops_list_projections`: Discovers available compiled operational tables and their column schemas.
- `ops_query_projection`: Executes filtered, parameterized queries against compiled operational views at `(valid_at, as_of)`.
- `ops_explain_projection`: Returns the formal mathematical formula and underlying LinkML rules behind any projected column.

#### Provenance & Forensic Pillar
- `kernel_get_activity`: Inspects the raw activity ledger (`intent` + `assertion`) across specific time windows.
- `kernel_trace_provenance`: Traces the complete lifecycle of a specific entity or property, showing every claim, author, confidence score, and revocation.

#### Write Gate Pillar
- `kernel_submit_transaction`: Validates and submits domain transactions through `generate.submit()`, minting entities and recording provenance.
- `kernel_correct_assertion`: Submits an append-only correction or retraction for an inaccurate historical assertion without mutating the log.

---

## Architectural Invariants (Guidelines for Agents & Developers)

When working on or extending this codebase, the following invariants **must remain unbroken**:

1. **Strict Domain-Blindness in Live Code:**
   No business terms (e.g. *gelato*, *ingredient*, *churn*, *sku*, *order*, *vendor*) may appear in `components/kernel/`, `components/compiler/`, `components/generator/`, or `components/agent/`. All domain logic belongs exclusively in `business/<business_name>/*.yaml`.

2. **The Single Write-Gate (`generate.submit`):**
   Never issue direct SQL `INSERT INTO assertion` in application code. All writes must pass through `generate.submit()`, which ensures:
   - An atomic `intent` row is minted.
   - Slot ranges and references are validated.
   - Bitemporal timestamps and attribution are assigned consistently.

3. **Database-Enforced Immutability:**
   Never attempt to run `UPDATE`, `DELETE`, or `TRUNCATE` on `assertion`, `intent`, or `entity`. Database triggers will abort the transaction. Retractions and corrections are modeled as new assertions where `revokes = <prior_assertion_id>`.

4. **Projections are Ephemeral Views:**
   Projections in `uniti_ops` / `uniti_demo_ops` are derived caches. They can be completely dropped and recompiled at any time using `components/compiler/compile.py`. Never treat operational tables as the source of truth.

5. **Test Isolation (`UNITI_DSN`):**
   Running tests against `uniti` or `uniti_demo` will cause assertion conflicts. Always point test runs to the throwaway database `uniti_check`:
   ```bash
   $env:UNITI_DSN="postgresql://uniti:uniti@localhost:5433/uniti_check"
   ```

---

## Manual Execution Reference

If running steps manually without `make`:

```bash
# 1. Start database
docker compose up -d

# 2. Reset throwaway schema
docker compose exec -T db psql -U uniti -d uniti_check -v ON_ERROR_STOP=1 -f /kernel/001_schema.sql

# 3. Run unit tests
$env:UNITI_DSN="postgresql://uniti:uniti@localhost:5433/uniti_check"
.venv/Scripts/python.exe -m pytest tests -q

# 4. Verify bitemporal replay determinism
.venv/Scripts/python.exe scripts/seed_200.py
.venv/Scripts/python.exe scripts/project.py build/check/projection_a.txt
.venv/Scripts/python.exe scripts/project.py build/check/projection_b.txt
.venv/Scripts/python.exe scripts/project.py --compare build/check/projection_a.txt build/check/projection_b.txt

# 5. Cross-check business profile
.venv/Scripts/python.exe scripts/check_profile.py
```

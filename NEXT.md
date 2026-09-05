# Now

What is being worked on. Every item needs a done condition that can be
**executed** — if it cannot be written as a command and a result, the item is
not ready to start.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. Where the work stands more
broadly is `ROADMAP.md`.

---

## The question this answers

**Is there anything a person can use?** Not "does a mechanism work" — that was
the last three items and the answer was yes. This one asks whether the system
has a surface, and it is measured by one thing: somebody who has not read this
repository opens a browser, types a movement, and watches a number change.

The PoC has widened for two weeks without producing anything that can be shown.
This item produces it, and it is the whole of the item.

### What is already there, and it is most of it

The interface is **three renderers and a server** away, not a component away.
The data structures already exist and are already right:

| Already returns a structure | What it holds |
|---|---|
| `generate.form(conn, map_, CLASS)` | fields, types, required, description, and **live dropdown options read from the log at two clocks** |
| `generate.submit(conn, map_, CLASS, …)` | one intent, N assertions, through the one write gate |
| `compile.compile_class(kernel, ops, map_, CLASS, valid_at, as_of)` | rebuilds one operational table at a pair of clocks and **returns the stored rows** |

Only the renderers are text. Nineteen classes of `v3.yaml` carry
`designates_type` and so have a form; `IngredientOnHand` and `GelatoOnHand`
have compiled tables. Nothing under `components/` renders HTML today, and there
is no HTML anywhere in the repository.

`compile_class` returning `stored` is what makes the clocks work in a browser:
a dashboard at a new pair of clocks is a rebuild of that one table, and
`CLAUDE.md` already says the operational database may be dropped whole and
rebuilt. The page reads the operational database, never the log.

---

## Open: the loop, in a browser

Four parts. Additive throughout — **nothing under `components/generator/` or
`components/compiler/` is edited**, because both already return what a web
component needs.

### 1 · Eight classifications, so the dropdowns are not empty

`uniti_trial` holds six items and thirteen movements, and every movement names
a place and a unit **as a reference** — but nothing in the log says what those
references are. `entity_class` is a fact like any other and it was never
stated, so `StockMovement`'s form today offers six ingredients and nothing
else:

    movement_out_of offers nothing: the log holds no Location
    movement_unit   offers nothing: the log holds no Unit

Eight entities, every one of them already a `value_ref` in the log, stated
through `generate.py submit` in a script beside `scripts/state_six_items.sh`.
This completes the six-item seed rather than widening it.

| URI | class | name |
|---|---|---|
| `sorella:loc_dry_store` | `InternalLocation` | `location_name` "Dry store" |
| `sorella:loc_terra_nostra_ingredients` | `Supplier` | `location_name` "Terra Nostra Ingredients" |
| `sorella:unit_tin` | `Unit` | `unit_name` "tin" |
| `sorella:unit_bag` | `Unit` | `unit_name` "bag" |
| `sorella:unit_carton` | `Unit` | `unit_name` "carton" |
| `sorella:unit_sack` | `Unit` | `unit_name` "sack" |
| `sorella:unit_box` | `Unit` | `unit_name` "box" |
| `sorella:unit_kilogram` | `Unit` | `unit_name` "kilogram" |

`Supplier is_a Location`, so a `Location`-ranged field offers both. Valid from
the adoption date `2026-06-15T00:00:00Z`, and no `--authority`: nobody "set"
what a place is.

### 2 · `components/web/render.py` — the same structures, as HTML

A new component. Two functions and one page shell, and **no logic**: it is
handed what `form()` and `compile_class()` already return.

- `form_html(built, *, valid_at, as_of, message=None)` — a `<form method=post>`
  over `built["fields"]`. A `ref` field is a `<select>` filled from
  `f["options"]`, labelled by `label or uri`; anything else is an `<input>`.
  Two inputs the map does not give: `subject`, a URI — `submit()` mints one it
  has not seen — and `actor`.
- `table_html(built, *, valid_at, as_of)` — a `<table>` over `built["rows"]`,
  with each column's `kind` shown under its name, so a reader sees which cells
  the graph computed, which it read out of the kernel as a parameter, and which
  are keys.
- `page(title, body, *, valid_at, as_of)` — one inline `<style>` block, and the
  **two clock inputs**, which appear on every page and are the point of the
  whole item.

No CSS framework, no JavaScript beyond the browser's own form submission, no
build step. One file.

### 3 · `components/web/serve.py` — four routes

`http.server.ThreadingHTTPServer` from the standard library. No dependency is
added; if it is ever too small it is swapped then, not now.

| Route | What it does |
|---|---|
| `GET /` | every class with a form, every class with a compiled table |
| `GET /form/<Class>` | `form()` at the clocks, rendered |
| `POST /form/<Class>` | `submit()`, then back to the form showing what was written |
| `GET /table/<Class>` | `compile_class()` at the clocks, rendered from the rows it returns |

`?valid_at=` and `?as_of=` on every GET, defaulting to now, and carried through
every link and through the POST redirect.

Two connections, and the separation is visible in which one each route holds:
`UNITI_DSN`, the kernel, for the form and the write; `UNITI_OPS_DSN` for the
table. They are different databases, so a page cannot join across them.

### 4 · `make serve`

    serve: export UNITI_DSN     := …/uniti_trial
    serve: export UNITI_OPS_DSN := …/uniti_trial_ops

A **separate** operational store from `uniti_ops`, which `make compile` builds
from the working log; the two must not collide. Created on first run the way
`make compile` creates `uniti_ops`. `MAP` is `business/sorella/v3.yaml`.

---

### Done when all five hold

1. `make serve`, then `http://localhost:8000/` lists **19 classes with a form**
   and **2 with a table**.
2. `/form/StockMovement` offers **2 places and 6 units by name** in dropdowns —
   not empty ones, and not raw URIs.
3. `/table/IngredientOnHand` at `valid_at=2026-06-16` shows **16 rows**;
   changing the clock box to `2026-06-15` and reloading shows **12 rows**, with
   pistachio at 2 tins rather than 6. Nothing else on the page is touched.
   *(Both numbers verified 6 Sep by running `compile.py` directly.)*
4. **The loop.** A new `StockMovement` is submitted through the browser form
   under a subject URI of its own; the kernel gains one `intent` and N
   `assertion`; reloading `/table/IngredientOnHand` at a clock that includes it
   shows the balance moved. No script is run between the two — the page
   rebuilds the table itself.
5. `make check` exits 0, and
   `grep -rn -i "pistachio\|movement\|stock\|ingredient\|location" components/web/`
   finds no business term in a live code path. The web component reads class
   and slot names from the map like every other component.

### Not in this item

No authentication, no styling beyond one inline `<style>`, no JavaScript
framework, no deployment. No entity-list page: a page listing every `Location`
would have to read the kernel, and only the two compiled tables are a
legitimate read path. No new projection classes. No constraint work and no
`report`. Anything found on the way is written into `LOG.md` as a finding and
left alone.

### One thing that is knowingly wrong, and is not fixed here

A form's dropdown options are read from the kernel by `generate._options`,
which is a read path from a form to `assertion` and is the thing `CLAUDE.md`
forbids. It is pre-existing, this item exposes it rather than creating it, and
closing it needs projections for classes that have none. `OPEN.md` carries it.
Build the form with its dropdowns and leave the defect where it is.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.

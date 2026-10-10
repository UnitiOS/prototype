# Ecosystem plan — finishing P2 on the graph

> Written 10 October 2026, after three rounds of discussion with the owner and a
> day of verification against the running system. It is the working plan for the
> rest of P2, meant to be executed in new sessions.
>
> - `README.md` describes the system as it is in the code. `P2.md` (Indonesian)
>   tells P2's story up to 9 October. `DESIGN_NOTES.md` explains why the system is
>   shaped the way it is. This document says **what P2 still has to do, why, in
>   which order, and how we know each step is done**.
> - **The code wins** where it disagrees with this document. Every claim marked
>   **[verified]** was checked against the running system on 10 October 2026 and
>   can be re-run from `build/probes/` (§4.6). Everything else is a proposal.
> - Working rules from `P2.md` §3 still apply: tests first, vertical slices
>   (mechanism *and* view), no business words in components, one commit per
>   complete step **only on the owner's command**, and every real model call is
>   announced first with its call, cost and time limits.

---

## Contents

1. Where P2 is going
2. Who the Studio is for
3. How one module connects to another
4. What was verified on 10 October 2026
5. Decisions
6. The work, step by step
7. The ecosystem test
8. Core v3 and the final re-run
9. Not in P2
10. Risks and how to keep scope
11. Appendices

---

## 1. Where P2 is going

### 1.1 The owner's direction (9–10 October 2026)

- The **Studio is where a user builds their system.** P2 is narrowed to the
  Studio and to the **graph**: making modules, composing applications, revising
  modules, and seeing how one module connects to another, harmoniously.
- P2 must **prove that the modular idea works and scales** — a new, more dynamic
  and more flexible way to share components than enterprise systems use — even
  where the full implementation is left for later.
- **The compiler follows the graph, not the other way round.** It must never stop
  a sound graph from being written. For every new graph construct we still check
  that the compiler *could* follow it in a way that stays reasonable.
- Function in the user's eyes comes first. Overall visual polish is **P3**.
- A test session with a real human (the earlier "stage C") is **not** part of P2
  unless the owner asks for it.

### 1.2 The finish line

P2 is finished when, in this order:

1. the mechanisms in §6 are built, each with its tests and its view;
2. the **ecosystem test** (§7) passes on every one of its seven stories;
3. **core v3** (§8) is sealed from what the ecosystem test showed;
4. the ecosystem test's examples are **re-run on core v3** and still pass, with
   the records entered before the change still read, untouched.

### 1.3 Why this is the right finish line

The two-round test (P2.md §4.10) already proved one module swap with correct
numbers. What it also showed, read again with the owner's direction in mind:

- The swap worked only because both modules pointed at the **same library
  `Item`**. Modules never connected to each other directly.
- The application had to **duplicate every stock column** (`_old` + `_new` +
  `_total`, 18 columns in `@kemahceria/sewa` v4). A third module would add a
  third copy of each.
- Old rentals **could not be returned through the new till**, because the till's
  return pointed at its own `Booking` class only.
- Two independent modules **cannot share a class name** (§4.3 shows it is worse
  than a refusal).
- The compiler is part of the seal: a graph shape the compiler cannot compute
  cannot be sealed (§4.2).

None of these are compiler or polish problems. They are the graph layer not yet
being modular enough. That is what the rest of P2 fixes and then proves.

---

## 2. Who the Studio is for

### 2.1 Two users with different jobs

| | **Business owner** (in the tests: Sari, Kemah Ceria) | **Module author** (in the tests: Rudi, Dewi, the till's author) |
|---|---|---|
| What they want | "A system for my business." | "A part that many businesses can use." |
| Modules, to them | Should be invisible. | Their daily work. |
| What modularity means to them | Not starting from nothing; upgrading or changing a supplier's module without losing old records. | Building on others' parts; knowing who builds on theirs; releasing a new version without breaking anybody. |
| The map they need | **Business lens**: things, events and numbers in their words, each with a small "from *module*" mark. | **Connection lens**: what my module points at, what I add to whose things, which roles I fill, who points at me. |

The strongest proof of modularity, for a business owner, is **what they never had
to do**. If Sari has to understand modules for her business to work, modularity
has failed in the user's eyes even when it works technically.

### 2.2 In P2: the function. In P3: the polish.

| In P2 (function) | In P3 (polish) |
|---|---|
| The lens that opens follows what is open: an application opens the business lens, a module opens the connection lens | Layout, colour, onboarding |
| What each lens contains (§6, step 7) | Separate screens or dashboards per user |
| The agent and the holes speak to the user they serve (already started: the guide by kind of module, P2.md §4.9 step 4) | The Studio's own buttons and headings in the user's language throughout |
| Flows that belong to one user: Sari's "new version available" card, Rudi's list of who builds on his module | Sign-in and permissions per user |

Two constraints:

- **One Studio, two lenses — not two Studios.** Sari sometimes needs the
  connection lens (changing tills); Rudi needs the business lens (checking his
  example's numbers). The lens opens by default from what is open, and either
  user can switch.
- **There is no sign-in.** In P2 the kind of user is read from what is open
  (`kind` in the manifest), not from who is signed in. That is enough for P2.

---

## 3. How one module connects to another

There are seven ways a module can connect to another. This table is the core of
the plan; every step in §6 moves one row.

| # | Way of connecting | Kemah Ceria example | Status on 10 Oct | After P2 |
|---|---|---|---|---|
| 1 | **Point at a shared thing** | Rental line → `Item` from `@uniti/item` | Works, proven (it is why the swap worked) | Unchanged |
| 2 | **Point at a role** | Guarantee → "any transaction", not Rudi's `Rental` | **Works end to end [verified]**, never used, never taught | Taught, labelled, with stand-in examples (step 4) |
| 3 | **Fill a role** | `Rental` claims `Transaction` | Works, used consistently, good for search | Unchanged |
| 4 | **Add facts to another module's thing** ("facet") | Rudi adds "rate per day" to `Item` | Not possible today: needs a side record. **Works with a small composition step [verified]** | Official (step 2) |
| 5 | **Total numbers from several modules** | Units out, from Rudi's lines and the till's lines | Works by duplicating every column | One rule, several sources (step 5) |
| 6 | **Say two things mean the same** (alignment) | Till's `Booking` means Rudi's `Rental` | No executor. LinkML already stores `exact_mappings` [verified] | **Not P2** (§9) |
| 7 | **Write under another module's predicate** | Two modules with the same `slot_uri` | Technically possible, unguarded (`components/seal/seal.py:326` says so) | Refused (step 3) |

### 3.1 Why facets are the step that matters most to users

In Odoo and ERPNext, sharing a component almost always means **extending shared
master data**: the accounting module adds columns to `res.partner`, the
warehouse module adds columns to `product`. That is row 4, and Uniti
deliberately refuses it (`kind_of_foreign_class`). The refusal is right: that kind
of extension is what makes upgrades painful in those systems. But it leaves Uniti:

- **ahead** on upgrading and swapping modules without migrating data (the log is
  never changed; a new version only changes how it is read);
- **behind** on one screen for a customer or an item that carries everything
  every module knows about it.

A facet closes that gap without giving up ownership. Rudi's module **owns a
predicate** whose subject is the **same entity** as the library's `Item`. The
library module is never touched; no second record exists; the kernel already
supports it (one entity, predicates from any module). Ownership stays per
predicate. This is the clearest "new way" P2 can show.

### 3.2 Where roles belong

Roles do not have to live in core. Evidence from every test so far:

| Core / library content | What it actually does |
|---|---|
| `Thing` (`entity_class`) | Essential: identity, read by forms and the compiler |
| `Resource` | Almost nothing |
| `Event.moment` | Read by nothing. Also duplicated: the recording standard already makes every date say what moment it is (`time_meaning: happened`, …) |
| `Flow` (`amount`, `affects`) | Never filled by any agent-built module. Partly duplicated: the standard already makes every number carry a unit and a direction |
| `Party`, `Item` (library) | **What actually connects modules** |
| `Transaction`, `TransactionLine` (library) | Used consistently, good for search; now also good as reference targets (row 2) |

So: **the library is the connecting layer**, as master data is in an ERP. Core is
in practice `Thing`. A role that is narrower than `Transaction` (for example
"rental agreement", so a return cannot point at a purchase) is **extracted into a
community interface module once a second module of the same kind exists** —
"discover the interface, don't design it" (DESIGN_NOTES.md §5).

### 3.3 LinkML and URIs: what fits and what does not

**[verified]** with `linkml_runtime` 1.11.1 (`build/probes/linkml/`):

| LinkML capability | Result |
|---|---|
| Two imported modules both declaring `Payment` | **One silently replaces the other**; the first module's slots vanish |
| A slot ranging over a mixin (a role) | Accepted |
| `any_of` ranges | Supported |
| `exact_mappings` on a class | Stored (an alignment place already exists) |
| Another module adding a slot to my class | Not in LinkML's model: a class owns its slot list |

The kernel thinks like RDF: an open world of entities and URI predicates, where a
class is just one more statement. LinkML thinks like a closed schema with global
names. **The flexibility the owner wants already exists in the kernel; LinkML is
what holds it back.** Therefore:

- Keep LinkML as the **format one module is written in** (tools, interop,
  labels, annotations for the rule vocabulary).
- Let **Uniti compose modules itself**, by URI, in the `Store`: qualify names,
  lock URIs, attach facets. Never rely on LinkML merging a closure into one name
  space.

What URIs already give (all **[verified]**):

- Data does not depend on names or versions: `rename_slot` keeps `slot_uri`
  (`components/studio/draft.py:1132`), so earlier records are never orphaned.
- Two modules that chose the same prefix still get different predicates
  (`components/seal/seal.py:174`).
- Classes are recorded in the kernel by full URI, so **the kernel is already
  namespaced per module**. Qualified names in the graph keep exactly the same
  URIs (§4.4), so no migration is needed.

What URIs do not give yet: the graph layer still works by name (§4.3); nothing
guards who writes under which predicate (row 7); `https://uniti.example/...` is
fine for a PoC but an open ecosystem will need a stable namespace per scope
(not P2).

---

## 4. What was verified on 10 October 2026

### 4.1 Environment and baseline

- Docker Desktop started; `uniti-db` (PostgreSQL 17) on port 5433 (`make db`).
- **337 Python tests and 42 web tests pass** (`make test`, `npm test` in `web/`).
- The web application was started on the two-round environment:

  ```
  UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_kemah \
  UNITI_OPS_DSN=postgresql://uniti:uniti@localhost:5433/uniti_kemah_ops \
  UNITI_PACKAGES="build/dua/kemahceria;build/dua/komunitas;packages" \
  .venv/Scripts/python.exe -m uvicorn components.api.app:app --port 8211
  ```

  It serves 7 modules, including `@kemahceria/sewa` v1–v4. The browser extension
  was not connected that day, so the screens were not inspected; every check went
  through the same API and components the screens use.
- All probes run in a kernel of their own, `uniti_probe` (+ `_ops`), recreated by
  each probe, with module stores under `build/probes/store-*`. The repository was
  not changed.

### 4.2 P2 — the compiler blocks a pure graph shape [verified]

A module with one recorded class and **no rule at all**: sealable. Make one of its
slots multivalued: **blocked** by `multivalued_not_read` — only because a table
cannot show a set yet (`components/compiler/compile.py:1012`). The seal requires
every table to compile (`components/seal/seal.py:491`, `_compiles`) and every
example to pass (which runs the compiler). Studio also refuses rule shapes the
compiler cannot run as `not_possible_yet` (`components/studio/draft.py:1559`).
The graph's language is currently exactly the compiler's capability.

### 4.3 P3a — a shared class name corrupts a pinned module [verified]

A third author seals `@lain/kasir` with a class `Rental`. An application pins it
next to `@komunitas/penyewaan@v3`, which also has `Rental`. Before the
`name_clash` refusal even appears, LinkML has replaced Rudi's `Rental` with the
till's, so **Rudi's own rule breaks inside the application**:

```
no_such_slot  CustomerDeposit.deposit_total_received  `sum` to name a slot of Rental
name_clash    draft.yaml: class Rental
```

Two independent modules with one common class name can never be used together
today.

### 4.4 P3b–P3d — qualified names solve it, with the same URIs [verified]

A probe-only patch (`build/probes/qualify.py`) qualifies every pinned module's
class, slot and enum names at load (`penyewaan__Rental`, `kasir__Rental`),
rewrites the references inside that module, and locks every `class_uri` and
`slot_uri` to its **full** URI. Results:

- Both `Rental` classes live side by side in the composed view.
- Every recorded class compiles, and **Rudi's own aggregates work again**.
- The application's own table totals deposits from both modules; its example
  passes; **the application seals**.
- The URIs under qualified names are **identical** to those the unqualified
  modules recorded under (`p3d_uris.py`: 4 of 4 identical). No migration.

Two design facts learned:

- **The qualifier must not contain `.`** — it collides with the one-hop path
  syntax in rules (`by: key=slot.slot`); every aggregate failed with `.`. `__`
  works. The name a user sees stays the plain one.
- **The composition gate is the `Store` class, not only `load_import`.** The
  composed view enters through `ModuleView.load_import`
  (`components/modules/store.py:392`), but **22 places in 9 files read raw module
  documents** through `store.document(...)` (list in §11.2): Studio steps,
  catalogue, health, roles, seal checks. In the probe, Studio steps refused
  qualified names (`not_in_draft`) because they read raw documents; the draft was
  therefore written directly to measure the rest of the pipeline.

### 4.5 P1 and P4 — role references and facets work end to end [verified]

**P1, a module pointing at a role** (`@dewi/jaminan`, written by a different
author than Rudi or SewaPro):

- Studio steps accept `range: Transaction` and an aggregate one hop through the
  role's binding: `by: customer_party=guarantee_for.transaction_counterparty`.
- An application pins `@komunitas/penyewaan@v3`, `@sewapro/kasir@v1` and
  `@dewi/jaminan@v1`. One rule totals guarantees on **Rudi's rentals and
  SewaPro's bookings**; the one-hop key reads `rental_customer` in one module and
  `booking_customer` in the other. Example passes; sealed; installed.
- The form for `Guarantee` offers **both** a rental and a booking as choices.
- Records entered through forms produce the expected real tables after compile.

New findings:

- **A module that only points at a role has no concrete record for its own
  example.** Recording an abstract `Transaction` is refused (`no_type_slot`). The
  probe used a guarantee as a stand-in transaction, which is a hack.
- **Choices for a role reference have no labels** (`('…/b1', '')`,
  `('…/r1', '')`): a person cannot tell a rental from a booking.

**P4, a facet** (`@rudi/tarif` adds `rental_rate` to `@uniti/item`'s `Item`,
probe-only patch `build/probes/facet.py` attaching any slot whose `domain` is a
class in the closure):

- The facet module seals; `@uniti/item` is untouched (`Item` still has only
  `item_name`).
- In the application, the `Item` form shows `rental_rate`; an example records an
  item with its rate; a rule computes income per item (2 days × 25,000 = 50,000)
  using a `parameter` on the facet. Example passes; sealed; installed.
- In the kernel, **one entity** "Tent" carries `entity_class` = library `Item`,
  `item_name` under the library's predicate and `rental_rate` under
  **`https://uniti.example/rudi/tarif/rental_rate`** — Rudi's predicate.

New findings:

- Studio misreads a facet module: holes say `nothing_declared` and
  `slot_is_loose`.
- There is no Studio step for `domain` (`SLOT_FIELDS` in
  `components/studio/draft.py` does not include it); the probe wrote it directly.

### 4.6 Re-running the probes

```
cd build/probes
../../.venv/Scripts/python.exe p1_role_reference.py      # module pointing at a role
../../.venv/Scripts/python.exe p1b_compose.py            # sealed, composed with two modules
../../.venv/Scripts/python.exe p1c_forms.py              # form choices, real tables
../../.venv/Scripts/python.exe p2_p3a.py                 # multivalued blocks; name clash corrupts
../../.venv/Scripts/python.exe p3b_qualified.py          # Studio steps refuse qualified names
../../.venv/Scripts/python.exe p3c_qualified_direct.py   # qualified names: example passes, seals
../../.venv/Scripts/python.exe p3d_uris.py               # same URIs (run after p3c)
../../.venv/Scripts/python.exe p4_facet.py               # facet on Item
../../.venv/Scripts/python.exe linkml/p.py               # (from build/probes/linkml) LinkML behaviour
```

Each probe drops and recreates `uniti_probe` and `uniti_probe_ops` only. They
depend on `build/dua/komunitas` (Rudi's and SewaPro's sealed modules). Probes are
evidence, not implementation: none of them is to be copied into `components/`.

### 4.7 Not verified

- **One rule over several sources** needs compiler work; judged by reasoning only
  (it is a `UNION ALL` before the grouping, and §6 step 5 gives its guard).
- **Studio screen bugs** reported in P2.md §6.1 (the seal button appearing only
  after a reload; the `@@` module name returning 500) were not reproduced, since
  the browser was not connected.
- **The agent's timeout**: read from the code only. `timeout` is passed to the
  model as a setting (`components/agent/config.py:76`) and `steady.py` retries on
  top, which explains calls of 102–207 s against a 60–90 s limit.

---

## 5. Decisions

### 5.1 Taken (9–10 October 2026)

| Topic | Decision |
|---|---|
| P2 scope | The Studio and the graph; function first; polish in P3 |
| Finish line | The ecosystem test passes, then core v3, then the re-run (§1.2) |
| Name | "Ecosystem test" (`uji ekosistem`) |
| Human test session | Not in P2 unless the owner asks |
| Compiler | Follows the graph; compiler gaps are recorded, not fixed in P2, and must not block the graph |
| Two users | In P2 for function; one Studio, two lenses chosen by what is open; polish in P3 |
| Core | Revised as the **last step of P2**, from the ecosystem test's evidence, then everything re-run |
| This document | English, `ECOSYSTEM_PLAN.md` at the repository root |

### 5.2 Agreed in principle, details confirmed at their step

| Topic | Direction | Confirmed in |
|---|---|---|
| Composition owned by Uniti | The `Store` qualifies names and locks URIs; LinkML never merges names | Step 1 (confirmed 10 Oct) |
| Reserved names | Core and library names (`Thing`, `Party`, `Item`, `Transaction`, …) stay unqualified and no other module may declare them | Step 1 (confirmed 10 Oct) |
| Facets | Official way to add facts to another module's thing | Step 2 (confirmed 10 Oct) |
| Own predicates | A `slot_uri` must be in the module's own namespace | Step 3 |
| Role references | Taught with three rules; narrower roles extracted into community interface modules | Step 4 |
| Several sources | One rule, explicit sources, guarded by unit and direction | Step 5 |
| Seal vs compiler | A sound graph seals even where the compiler cannot compute yet; vocabulary stays closed | Step 6 |
| Alignment | Not P2 | — |

Changing the seal/compiler relation **changes a principle carried from P1** ("no
construct without an executor"). The replacement principle is: *a construct
enters the graph with its written meaning and an example; its executor may come
later.* The owner confirms the exact wording at step 6.

---

## 6. The work, step by step

Each step is a vertical slice: mechanism, tests, and what a user sees. Each ends
with the full suite green (`make check`, `make web-test`) and an owner review
before any commit. Step 8 may be done at any time.

### Step 0 — Stop teaching `Flow` and `moment` (small, first)

- **Why:** the ecosystem test must not build modules on roles that core v3 may
  remove; it would blur the test.
- **What:** the guide (`components/agent/guide.py`) and the opening note stop
  asking agents to fill `Flow` and to bind `moment`; dates are described through
  the recording standard's time meaning. Core v2 itself is not changed.
- **Done when:** the guide test still names every step, refusal code and role it
  must; a scripted rehearsal shows no `Flow`/`moment` request.

### Step 1 — The `Store` composes modules: qualified names

- **User sees:** two modules with the same class name can be used together. In
  Studio and on the map the plain name shows, with its module as a small mark.
  When a short name is ambiguous, a hole asks "which one?" with the choices.
- **Design:**
  - Qualify every pinned module's class, slot and enum names as
    `<module-tag>__<Name>` when composing. Rewrite every reference inside that
    module: `is_a`, `mixins`, `slots`, `slot_usage`, `range`, `domain`, `any_of`,
    aggregate `over`/`sum`/`by` (keys and each part of a path)/`where`/`convert`,
    parameter `of`/`slot`, and `{names}` in `equals_expression`
    (`build/probes/qualify.py` is the measured starting point).
  - Lock every `class_uri` and `slot_uri` to the **full** URI, expanded with the
    declaring module's own prefixes.
  - The module tag must be unique in a closure (a scope and a name both count:
    `@komunitas/penyewaan` and `@rudi/penyewaan` cannot share `penyewaan`).
    Decide the tag form here.
  - **Reserved names:** core and library names stay unqualified; a module
    declaring one of them is refused.
  - **One place:** `Store` provides both the composed view and a composed
    document reader, and the 22 raw readers (§11.2) move onto it. A module's own
    draft keeps its own plain names.
  - Studio steps accept a plain name when it is unique in the closure and store
    the qualified one; an ambiguous name becomes a hole with its options.
  - `name_clash` between two pins disappears; a clash between the draft and a
    pin (`name_taken`) stays.
- **Watch:** `generate.table_name` turns class names into SQL table names
  (`components/generator/generate.py:272`); the qualifier must give valid,
  readable names. Examples files of applications use qualified names.
- **Compiler:** no new construct; it reads the composed view as today.
- **Existing stores:** sealed versions are immutable. For the PoC, re-seal the
  fixtures and the library (as was done for core in 1.5) rather than writing
  compatibility code; the two-round stores under `build/dua` stay as evidence of
  the old behaviour.
- **Done when:** the P3a scenario (§4.3) passes as a real test: both `Rental`s,
  Rudi's own rules intact, example passes, seal succeeds, and URIs are identical
  before and after.
- **Decided 10 October 2026 (owner):**
  - **Tag form:** the module's name alone, `-` read as `_`
    (`@komunitas/penyewaan` → `penyewaan__Rental`, table
    `p_penyewaan__rental`). Two modules with one tag in a closure are refused
    (`tag_taken`), at the `pin` step and at the seal.
  - **One resolution rule** instead of re-sealing: a plain name stands for the
    one qualified name in sight whose plain part it is; with several, the
    reader asks "which one?" (`name_ambiguous`). The same rule reads a pinned
    module, the draft, an example and a form, so versions sealed before step 1
    keep working unchanged. Studio and the seal keep the qualified name in
    what they write.
  - **Reserved names** are computed from the store: every class, slot and enum
    name any `kind: core` or `kind: library` version declares, plus any name
    with `__` in it (`name_reserved`). Core and the library may declare their
    own.
- **Built (`components/modules/compose.py`, `Store.composition`):** the 22 raw
  readers were each decided: the closure readers (`roles`, `catalogue`,
  `health` via `roles`, `read.version`, `read.class_graph`,
  `api/application._origins`, `seal.kind_refusals`, `studio.draft.seen`) read
  the composition; the readers of one version's own document (counts, its
  page's title, diffs between its own versions, `revise`, the imports a
  version pins, URI registries keyed by full URI) stay on `store.document`,
  because they never compare a name across modules.

### Step 2 — Facets

- **User sees:** Rudi says "items get a rate per day". The item screen in Sari's
  application gets a "Rental" section with that field. One record per item.
- **Design:**
  - A slot whose `domain` is a class this module does not own is a facet. A Studio
    step sets it (add `domain` to the slot fields, or a step of its own — decide
    here).
  - The `Store` attaches facet slots to their class **only in a composition that
    pins the facet's module** (`build/probes/facet.py` is the starting point).
  - Rules: a facet is **never required** (existing things have no value); it
    **cannot override or narrow** a slot of the owner; it **does not make the
    entity a new class**; its `slot_uri` is in its own module's namespace (step 3).
  - Studio understands a facet module: no `nothing_declared`, no `slot_is_loose`
    for a facet; the connection lens draws "adds *rate per day* to *Item*".
  - Forms group facet fields under their module's title.
- **Compiler:** none new; a facet is one more column of the class's table and can
  be read by `parameter` (verified).
- **Done when:** the P4 scenario is a real test, and a facet appears in the form
  and table of the application, with its own predicate in the kernel.
- **Decided 10 October 2026 (owner):** a facet is made with the existing
  `attach` step. A slot of the draft's own attached to a class another module
  owns is written as LinkML's `domain` on the slot; `detach` takes it off. No
  new step, and the `slot_is_loose` hole offers the things in sight beside the
  draft's own classes.
- **Built (`compose.facets`/`compose.attach`, `seal.facet_refusals`,
  `tests/modules/test_facets.py`):**
  - `Store.composition` hangs every facet on its class in the composition's
    copy of the owner's document, and `Store.view` does the same on the view,
    so forms, tables, the compiler, the examples and the map all read it. A
    composition that does not reach the facet's module never sees it.
  - One rule, at the step and at the seal: `facet_on_role`, `facet_obliges`
    (required, identifier, type) and `facet_elsewhere` (on a class of the
    module's own as well, or on a second thing); a `domain` naming nothing
    in sight is `not_in_draft`. Narrowing the owner's slots and making the
    entity a new class have no step, so need no refusal.
  - Studio: no `nothing_declared` for a module of facets, no `slot_is_loose`
    for a facet; each slot says `adds_to`, and the thing it adds to is drawn
    on the map with the field marked "added here". The class graph gives each
    class its `facets`. The application form groups facet fields under the
    adding module's title (`section`). Revision diffs include `domain`.
  - The guide teaches it in two lines; the instructions are now 22,498 of
    their 22,500-character budget (parking list).

### Step 3 — A module writes only under its own predicates

- **Design:** at seal, every non-abstract slot's full `slot_uri` must start with
  the module's own namespace. Facets satisfy this by construction. New refusal
  code, with the repair "use a facet, or point at the record".
- **Done when:** a module reusing another module's predicate is refused, with the
  repair offered as options.

### Step 4 — Pointing at roles, as the normal way to connect

- **User sees:** Dewi's guarantee module works with any rental module. In Sari's
  form, the choices read "Rental — Budi, 6 Oct" and "Booking — Ani, 7 Oct", not
  bare addresses.
- **Design:**
  - **The guide's three rules:**

    | Point at | When | Example |
    |---|---|---|
    | A library thing | Always, for parties and items | Rental line → Item |
    | A role | When the other side may belong to another module | Guarantee → transaction |
    | Your own class | For the structure inside your own module | Rental line → Rental |

  - **Choice labels** name the kind and the record (class label plus the record's
    identifying values or date).
  - **Stand-in records for examples:** a module whose reference ranges over a role
    may record a stand-in of that role in its own examples; the example runner
    gives it the role's URI as its class inside the scratch log only. Decide the
    exact form here.
  - **The "stands alone" hole** (an opening, not a refusal): a class in a module
    that pins the library but points at no shared thing; a class whose own
    identifying name slot duplicates `Party` or `Item`. Offered repair: "use Party
    from the library?" — so connecting is guaranteed by the system rather than
    hoped from the agent.
  - **Narrower roles:** when a second module of the same kind exists, the agent
    proposes an interface module (`@community/...`) holding the narrower role;
    both modules fill it. Not built into core.
- **Done when:** the P1 scenario is a real test (no hack for the module's own
  example), labels are readable, and the "stands alone" hole appears on a module
  built like the first empty-store test's guarantee module (P2.md §4.8).

### Step 5 — One rule, several sources

- **User sees:** "units out = rental lines (Rudi) + booking lines (till)" is one
  column, written once.
- **Design (proposal):** an aggregate may list `sources`, each with its own
  `over`, `sum`, `by` (and optional `where`, `convert`), instead of one. Guards:
  every source's summed slot has the **same unit and the same direction** (the
  recording standard already requires both on every number); the keys are of
  kinds that can meet (`key_kinds_differ` already exists). Studio: an
  `add_source` step, or `aggregate` taking several — decide here.
- **Compiler:** each source planned as today, `UNION ALL`, then grouped.
  Reasonable and analysable.
- **Rejected:** totalling automatically over a role. The composition experiment
  showed it double-counts and mixes units (P2.md §4.3).
- **Done when:** the Kemah Ceria v4 stock table is expressible with one column per
  number instead of three, and its numbers are unchanged.

### Step 6 — The seal stops depending on what the compiler can do

- **User sees:** a need the system cannot compute yet is still written and sealed;
  on the map it shows "not computed yet", and its example waits instead of
  failing.
- **Design:**
  - Split compiler refusals into **meaning** (the graph is wrong: stays blocking)
    and **capability** (the compiler cannot yet: becomes "awaiting executor").
    Proposed classification in §11.1; confirm here.
  - An example whose checked columns are all awaiting an executor is **pending**,
    not failed. A version may seal with pending columns; the catalogue and the map
    show them; installing such a version shows those columns empty and labelled.
  - Multivalued slots seal (`multivalued_not_read` becomes capability).
  - `not_possible_yet` steps (value filters, two hops) are accepted **in the
    vocabulary's fixed syntax** and marked awaiting.
  - **Vocabulary governance:** a construct enters the rule vocabulary only with
    (1) a written meaning, (2) an example, (3) a one-paragraph SQL sketch showing
    the compiler can follow it boundedly. The vocabulary stays closed and less
    powerful than SQL (DESIGN_NOTES.md §6). Posting (one record producing others)
    does not pass this test and stays out.
- **Done when:** the P2 scenario seals; a module with a value filter seals as
  awaiting; nothing that was a meaning refusal became sealable.

### Step 7 — Two lenses, and what a revision means for each user

- **Business lens** (opens for an application): things, events and numbers in the
  owner's words; small "from *module*" marks; facets shown inside their thing.
- **Connection lens** (opens for a module): what it points at, what it adds to
  whose things, which roles it fills, and which shared modules build on it.
  Start from the existing `ClassGraph` (Modules area) and the Studio map.
- **For Sari: "a new version is available"** card. The application's examples run
  against the candidate version **before** she re-pins (the health report already
  finds lagging pins); what changes is said in business words.
- **For Rudi: who builds on my module.** Only **shared** modules are listed:
  applications are private to their business, so Rudi does not see Sari's.
- **Unpinning a module that is still used** is refused at the step.
- **Stale tables after a swap** (P2.md §6.1): shown as a hole from the health
  report, not left to the agent to notice.
- **Done when:** both lenses are checked in a browser at 4K, 1280, 820 and 390
  pixels, as earlier slices were.

### Step 8 — Known Studio and agent defects (any time)

From P2.md §6.1, kept to what affects function:

- The seal button appears only after a reload.
- The module name field already holds `@`, so a typed name becomes `@@…` and the
  server answers 500.
- The agent's timeout is not enforced: enforce a wall-clock limit on our side
  around each call, retries included.
- The per-request budget reserves a full-price call and stops long conversations
  after two or three calls: reserve from the measured cost of the last call.
- An example sentence that is not English is caught only after the person agrees;
  catch it before the proposal.
- Technical names (module names, "module", "sealed") still leak to the business
  owner: check against a word list in the realistic sessions.

---

## 7. The ecosystem test

### 7.1 Shape

As in the two-round test (P2.md §4.10): separate kernels and servers for the
community and for each business; Claude plays every author and the business
owner; **truth numbers are written down before the test starts**; every model
call is announced with its limits. Suggested cap: **$6**, announced before the
first call (the two-round test spent $2.63).

### 7.2 The seven stories

| # | Who | What happens | Passes when | Proves |
|---|---|---|---|---|
| 1 | Rudi | Builds a rental module on the library: lines point at `Item`, rentals fill `Transaction`; adds "rate per day" to `Item` as a facet | Sealed; in an application the item screen carries the rate; one record per item | Rows 1, 3, 4 |
| 2 | Dewi | Builds a guarantee module pointing at "any transaction", independently of Rudi | Sealed with its own stand-in example; works with Rudi's rentals and another author's bookings | Row 2 |
| 3 | A third author | Builds a till that also declares `Rental`, independently | Can be pinned beside Rudi's module; both modules' own rules still hold | Namespaces |
| 4 | Sari | Composes her application through the agent | The agent finds and uses the existing modules; Sari sees her business, not modules; the numbers match the truth | Business lens |
| 5 | Rudi, then Sari | Rudi releases v2. Sari is told what changes for her | Rudi sees the shared modules building on his; Sari's examples run on v2 before she re-pins; old records are untouched | Revision and impact |
| 6 | Sari | Changes to the third author's till | Old rentals can be returned through the new till (its return points at a role); combined numbers are one rule each; numbers match the truth | Swap; rows 2 and 5 |
| 7 | Any author | Writes something the compiler cannot compute yet (a value filter, or a multivalued slot) | Sealed; shown as "not computed yet"; its example is pending, not failed | Compiler follows |

### 7.3 Criteria across all stories

- No developer intervention: no page reload to continue, no file written by hand,
  no workaround around the Studio.
- The approval points hold: plan → examples → rules → seal, each agreed by the
  person.
- No technical term reaches the business owner (checked against a word list).
- No conversation is cut short by the budget.
- Every number matches the truth fixed before the test.

---

## 8. Core v3 and the final re-run

**When:** after the ecosystem test passes, as the last step of P2 — not P3. P2's
third goal was to find the standard and the core seed through evidence; the
ecosystem test is that evidence.

**What (to be confirmed by the evidence):**

- Keep `Thing`.
- Remove `moment` and `Flow` (and probably `Resource`), or move them to the
  library, unless the ecosystem test showed a mechanism reading them.
- Add a role only if a mechanism built in §6 reads it (for example a "settles"
  role if returns or payments needed one).
- The library stays the connecting layer; its governance stays an open question
  (DESIGN_NOTES.md §15.7.4).

**The re-run:** re-seal the library and the ecosystem test's modules on core v3,
then run every ecosystem test example again. Slots that were `is_a: moment` keep
their `slot_uri`, so their records are unaffected. If every example passes and
every record entered before the change is still read without migration, P2 ends
with the strongest proof it can give: **even the foundation can be upgraded.**

---

## 9. Not in P2

| Item | Where it goes |
|---|---|
| Compiler growth: value filters, two hops, tables over tables, multivalued tables, posting, units as entities | After P2, driven by the "awaiting executor" list |
| Alignment between modules (`exact_mappings` with an executor) | After P2 |
| Sign-in, permissions, ownership checks on register and install | After P2 |
| One shared registry / Uniti kernel for names and versions | After P2 |
| Read access for outside agents (MCP) | After P2 |
| Group businesses (several companies) | Open question, DESIGN_NOTES.md §15.7.3 |
| Forms and application screens polished for non-technical staff | P3 |
| The Studio's own chrome in the user's language throughout | P3 |
| A test session with a real person | Only if the owner asks |
| Other model providers | Optional; `config/agent.yaml` already allows it |
| A stable public namespace for URIs | Before going open source, not P2 |

---

## 10. Risks and how to keep scope

- **Scope creep** is the documented failure of P2 (P2.md §6.3). Rule: a new idea
  found during a step goes into a parking list at the end of this document; it is
  not built in P2 unless the owner moves it into a step.
- **Step 1 has the widest blast radius** (the `Store`, 22 raw readers, Studio
  steps, the map, table names, examples files). Do it first, with the P3a
  scenario as its acceptance test, and keep URIs identical as a hard check.
- **Test design** went wrong twice before (P2.md §6.3): write each story's truth
  numbers and pass criteria before running it.
- **The scripted "person" approves everything:** judge the agent on realistic
  sessions, as decided on 3 October.
- **Probes are not implementation.** The patches in `build/probes` prove
  direction; the real code is written test-first in `components/`.
- **Environment:** Docker Desktop must be running (`make db`); model calls go
  through Vertex AI in `us` with application-default login.

---

## 11. Appendices

### 11.1 Proposed split of compiler refusals (confirm at step 6)

**Meaning — the graph is wrong; stays blocking:**
`no_such_class`, `no_such_slot`, `no_such_column`, `aggregate_keys`,
`parameter_keys`, `convert_keys`, `convert_on_empty`, `not_a_class`,
`not_summable`, `no_grouping`, `types_disagree`, `key_kinds_differ`,
`role_has_no_rows`, `two_rules_on_a_column`, `rule_on_a_recorded_class`,
`groupings_disagree`, `grouped_by_unknown`, `grouped_by_derived`,
`not_a_key_column`, `key_range_not_a_class`, `slot_not_below`,
`expression_cycle`, `expression_not_arithmetic` (keeps the vocabulary closed),
`expression_names_unknown`, `no_type_slot`.

**Capability — the compiler cannot yet; becomes "awaiting executor":**
`multivalued_not_read`, `not_possible_yet` (value comparison in `where`, keys more
than one record away), `where_not_is_a`.

**To decide:** `identity_column_taken` (an implementation naming detail — rename
in the compiler rather than refuse the graph?), `nothing_to_compile` and
`no_aggregate` (are they still meaningful for an application made only of pins?),
`computation_failed` (a data-time failure, not a graph one).

### 11.2 Raw module-document readers to move onto the `Store`'s composed reader

```
components/api/application.py:51
components/modules/catalogue.py:159, 192
components/modules/health.py:112, 253
components/modules/read.py:33, 107, 112, 137, 198, 295
components/modules/roles.py:65, 199, 200, 243
components/seal/seal.py:613, 664
components/studio/changes.py:57
components/studio/draft.py:536, 555, 865
components/studio/read.py:900
```

Some of these legitimately read the module's own document (a draft's own names,
a version's own contents for its page); each needs a decision, not a blind swap.

### 11.3 Key places in the code

| What | Where |
|---|---|
| Composed view and import loading | `components/modules/store.py:364` (`view`), `:392` (`load_import`) |
| Seal requires compilation | `components/seal/seal.py:491` (`_compiles`) |
| Seal requires examples | `components/seal/seal.py:507` (`_examples_hold`) |
| Name clash check | `components/seal/seal.py:583` |
| Predicate identity | `components/seal/seal.py:174` |
| Shared `slot_uri` unguarded | `components/seal/seal.py:326` |
| Rule shapes refused as not possible yet | `components/studio/draft.py:1559` |
| Rename keeps `slot_uri` | `components/studio/draft.py:1132` |
| Multivalued refused by the compiler | `components/compiler/compile.py:1012` |
| Form choices and their (missing) labels | `components/generator/generate.py:472` |
| Table names from class names | `components/generator/generate.py:272` |
| Agent timeout passed as a model setting | `components/agent/config.py:76` |
| Core roles | `packages/@uniti/core/v2.yaml` |
| Library | `packages/@uniti/{party,item,transaction}/v1.yaml` |

### 11.4 Parking list

Ideas found during the work that are not in a step. Empty on 10 October 2026.

- **The library still asks for `moment` and mentions `Flow`** (found at step 0).
  `@uniti/transaction@v1` declares `Transaction` with `is_a: Event`, so every class
  filling `Transaction` must bind core's `moment` (`binding_unfilled` blocks
  the seal), and `TransactionLine`'s description says "a line that moves an
  amount of an item fills core's `Flow` as well". Step 0 changed only what
  Uniti teaches and offers; the ecosystem test's rental modules will therefore
  still carry an `is_a: moment` slot. Options: leave it for core v3 (§8 already
  expects `is_a: moment` slots and keeps their `slot_uri`), or seal
  `@uniti/transaction@v2` with `Transaction` as a kind of `Thing` and the
  `Flow` sentence removed, before the ecosystem test. **Decided 10 October
  2026: left as it is until core v3.**
- **The library's `Item` still says facets are not the way** (found at step
  2). `@uniti/item@v1` describes itself: "What one kind of business says about
  an item, such as a rental rate or a reorder level, is a record of that
  business's own module pointing at the item, not part of the item." Step 2
  made exactly that a facet. The sentence is sealed and read by agents in the
  catalogue. Options: reword it in `@uniti/item@v2` before the ecosystem
  test, or with core v3.
- **The agent's instructions are at their budget** (found at step 2): 22,498
  of the 22,500 characters `test_agent` allows. Step 4's three rules will
  not fit without cutting something or raising the budget.

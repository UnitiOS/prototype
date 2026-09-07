# Execution Log

Written after something has actually been run, never before.

Format: date · what was run · the result · what was surprising.
Plans do not go here. Only what already happened.

---

## 2026-09-04 — Housekeeping run 2: LOG.md rotated whole, build/ triaged

Authorised by Fareza, not a `NEXT.md` item. `OPEN.md`, `DECISIONS.md` and
`NEXT.md` were not read or written this run — Desktop held them.

**LOG.md.** All 16 `## 2026-09-…` sections moved to `history/LOG-2026-09.md`,
in order. Before: 4,565 lines, 16 September sections, 0 August sections
(August left earlier the same day, in commit `93a3ee7`). After: LOG.md
holds its 10-line header and this entry; `history/LOG-2026-09.md` holds the
same 16 sections under a two-line header. The moved body is byte-identical to
`git show HEAD:LOG.md` lines 11–4565 (`cmp` clean, md5 `bb59e90a…`).

Surprising: the previous run's "Questions for Fareza" went to history with
their section, so LOG.md no longer surfaces them. They are unanswered in
`history/LOG-2026-09.md`, last section.

**build/ triage.** 259 files before, 2 after. Every `.py`, `.sh` and `.sql`
anywhere under `build/` was exactly the eight named — no ninth turned up, and
none of the eight is named by `components/`, `scripts/`, `tests/` or the
Makefile, so all eight are hand-written. Moved to `history/build-scripts/`
(plain `mv` then `git add`: `git mv` refuses an untracked path, and `build/`
has been in `.gitignore` since 2026-08-22, so nothing in it was ever tracked).
Deleted: `build/v1/` (139), `sorella_forms/` (21), `sorella_forms2/` (21),
`webvowl/` (23), `sorella_mmd/` (11), `sorella_tables/` (10), `probe/` (2),
`t/` (2), and 22 loose `.txt`/`.ttl`/`.err`/`.mmd` files at the root — 251 in
all. `build/` kept as an empty directory; `make replay` does not create it.
`make check` then exited 0, 65 tests passed, and `build/` holds only the
`projection_{a,b}.txt` that run just wrote.

**.gitignore.** `build/` moved out from under "# Local Claude Code settings",
which it had nothing to do with, into its own "# Build output" heading. It is
now line 23; `git check-ignore -v build/x` still resolves to it, and `git
status --short` shows nothing new.

## 2026-09-05 — The map becomes something a person can look at

**1 — `build/` takes its shape.** Created `build/sorella/v1/{graph,forms,
tables,log}` and `build/check/`; `OUT` moved from `build` to `build/check`, and
the two `projection_{a,b}.txt` left at the top level on 4 Sep were deleted, not
moved — they are derived and `replay` rewrites them. `make check` exits 0, 65
tests pass, the replay is identical twice (5,334 bytes), both projections land
in `build/check/`, and `build/`'s top level holds only the two directories.

**2 — explicit domains.** `scripts/owl_domains.py` reads a gen-owl TTL, walks
the `owl:Restriction`s a class carries and writes the missing end back onto the
property. `rdfs:domain` 0 -> 101: 95 slots are used by one class and get a
plain domain; 6 by more and get `owl:unionOf` — `entity_class` (15 classes),
`happened_on`, `written_by` (3), `credit_terms`, `made_recipe`, `outside_where`
(2). No repeated plain domain is emitted. `rdfs:range` was already complete at
101, so none was added; 2,170 -> 2,337 triples from 385 restrictions. Object
properties carrying both ends, what a viewer needs to draw an edge: 0 -> 36.
Surprising: `gen-owl` does not repeat an inherited slot on a subclass, so no
union holds a class and its parent. And the map has 36 object properties, not
the 16 relationships `NEXT.md` counts.

**3 — pyLODE 3.6.0, trialled.** `pip install pylode` into `.venv` only; the
Makefile and `make build` are untouched by it. Ran on both TTLs (input is
positional). Both render, 22 class blocks each — 21 classes and the
`RecipeStage` enum — with every description from the map and cardinalities as
`min 1` / `max 1` / `only xsd:string`. It draws no diagram: no SVG, no image;
relationships are text. What task 2 changes: all 101 properties gain a `Domain`
row (raw: none) and 21 classes gain an `In Domain Of` list (raw: 0); `In Range
Of` is 13 in both. A union renders `Supplier c or WholesaleAccount c`, but only
a plain domain is back-linked, so just the 95 single-class slots are listed.

**4 — Sorella rendered.** `scripts/render_map.py` asks the generator for every
class in the map; `make build` runs gen-owl, `owl_domains` and it twice, and is
no prerequisite of `check`. `rm -rf build/sorella && make build` reproduces 46
files: 21 tables, 19 forms (`GelatoOnHand` and `IngredientOnHand` refused, the
generator's reason on stderr), 2 TTLs, 4 stderr logs. `build` reads `uniti` and
not `uniti_check`, and the log is unchanged either side: 418 entities, 1,673
assertions, 208 intents. The 21 tables hold 197 distinct entities — Location 42
covers its 33 subclass rows, Ingredient 81 covers BoughtItem 77 — which is the
master data of 1 Sep.

## 2026-09-05 — gen-doc trialled against pyLODE

A comparison, authorised by Fareza. `make build`, `scripts/` and the pyLODE
output are untouched. `gen-doc business/sorella/v1.yaml -d build/sorella/v1/
graph/gen-doc` exits 0, writing **144** files: 21 classes, 101 slots, 1 enum,
19 types, `index.md`, the schema. pyLODE was re-measured, not quoted.

| | map | pyLODE 3.6.0 | gen-doc |
|---|---|---|---|
| classes / slots | 21 / 101 | 21 / 101 | 21 / 101 |
| class / slot descriptions | 21 / 101 | 21 / 101 | 21 / 101 |
| cardinality | 137 class-slot pairs | 244 axioms, 122 pairs | 137 pairs |
| domain / range per slot | 101 / 101 | 101 / 101 | 101 / 101 |
| `is_a` | 4 | 4 | 4, and 2 parent-side |

The baseline handed to this run was wrong on two rows. `gen-owl` writes no
`rdfs:comment` but does write `skos:definition`, whence pyLODE's descriptions;
its 244 is 122 `max 1` + 112 `min 0` + 10 `min 1`, and the 15 pairs short of 137
are inherited slots it never repeats. gen-doc gives all 137 a cell (`0..1` x123,
`1` x14) and `Required` on the 10 identifiers; the map bounds nothing else.

| the four | pyLODE | gen-doc |
|---|---|---|
| `aggregate` `over`/`sum`/`by`, 4 slots | 4 of 4 | 4 of 4 |
| `equals_expression`, 2 slots | 0 of 2 | 2 of 2 |
| `unique_keys` on `ProductPrice` | no | yes, both slots named |
| `designates_type` on `entity_class` | no | yes, its own row |

pyLODE showing the aggregates is the surprise: `gen-owl` emits each as a
`sorella:aggregate` string, the `JsonObj(...)` repr. The other three stay behind.

`mkdocs` 1.6.1 and `mkdocs-material` into `.venv` only, Makefile untouched;
`mkdocs.yml` was generated into `gen-doc/` by a scratchpad script, so nothing
under `build/` is hand-written. `mkdocs build --strict` is clean: 144 pages, 192
files, 142 links and every diagram click target resolving, 21 mermaid diagrams.

    .venv/Scripts/mkdocs.exe serve -f build/sorella/v1/graph/gen-doc/mkdocs.yml

Surprising: superfences' `format:` must be the bare `!!python/name:` — one level
deeper every fence is literal backticks, no diagram draws, `--strict` still ok.

## 2026-09-05 — two movements in the log, and a balance to compute

`NEXT.md` item one. Nothing under `components/` changed; two `generate.py
submit` calls and nothing else.

**The ingredient is digestive biscuits, and the unit is `pack`.** The aggregate
on `IngredientOnHand` does not group by unit, so the seed had to be one
ingredient in one unit. Two candidates were rejected first:

- **Canned soft drink** — the richest Monday story in §4.2 (4 cases into Cotham
  at 09:50, 2 cases into Gloucester Road at 10:35, 19 and 14 sold, one off the
  Gloucester Road shelf for a staff drink) and unusable. It arrives in cases of
  24 and leaves in cans, and §1.6 counts it in cases, so seeding it needs a
  case-to-can conversion the map holds nowhere. Bottled water fails identically.
- **Honey, clear** — one unit in the map (`tub`, no worked unit) but §2.2 draws
  0.75 kg of a 3 kg tub into the biscuit base run, so the only movement it has
  on Monday is in kilograms against a count in tubs.

Digestives are not innocent either: §1.5 gives them three units, ordered in
cases, counted in packs, worked in grams. What made them the pick is that
**every quantity the profile actually states for them is a pack** — 17 at the
count, ten a run — because §2.2 says the biscuit base page "is the only page in
the book that starts from a count of packs rather than a weight". So no seeded
movement needs a conversion, which is the condition that matters. No ingredient
with both an arrival and a departure on Monday is single-unit in §1.5; the
choice is between a mixed-unit seed and a seed with no departure at all.

**The two movements.**

| Subject | Out of | Into | Qty | From |
|---|---|---|---|---|
| `mov_2026_06_15_digestives_opening` | Severn Catering Supplies | Dry store | 17 pack | §4.1, Dan's dry store sheet, 05:55–07:10, *Counted* |
| `mov_2026_06_15_digestives_biscuit_base` | Dry store | — | 10 pack | §4.2 afternoon, Rekha's run; §2.2 puts a run at ten packs |

Both `valid_from 2026-06-15T00:00:00+00`, `recorded_at` today, `happened_on
2026-06-15`, source `human_stated`. `movement_kind` and `movement_batch` left
empty — the log holds no `MovementKind` and no `Batch`, neither slot is
required, and minting one to fill a picker would be inventing master data.
`written_by` left empty on both: §3.2 says nothing is written for the biscuit
base run, and the opening line is a count sheet, not a movement document.

Two seeding choices worth naming. **The opening position is given the supplier
as its origin** — §3.2 has the weekly drop as Severn Catering Supplies → Dry
store, and the map's own `ingredient_on_hand_net` description expects a supplier
to read negative. **The run has no destination.** §3.2's row for a digestive
leaving a shelf is *Ingredients to the machine — Dry store, Walk-in chiller,
Ingredient freezer → the pasteuriser or the bench*, and adds that §1.3 names
neither; the separate *Biscuit base made — Dry store → Ingredient freezer* row
is about where the made thing went, not where the packs went. Putting ten packs
of digestives into the ingredient freezer would have made the freezer hold packs
it does not hold.

**The hand computation.** Digestive biscuits, in packs, at `valid_at`
2026-06-15 or later, `as_of` now. `ingredient_in` sums `movement_quantity`
grouped by `movement_into`, `ingredient_out` by `movement_out_of`, and the net
is the first less the second.

| Location | in | out | net |
|---|---|---|---|
| Dry store | 17 | 10 | **7** |
| Severn Catering Supplies | 0 | 17 | **−17** |
| *no location* | 10 | 0 | **10** |

Seven packs on the dry store shelf at close on Monday, which is 17 counted at
05:55 less the ten Rekha took in the afternoon. Total across every location is
nought, as it must be when nothing is created.

**Run and result.**

    generate.py submit business/sorella/v1.yaml StockMovement \
      --subject sorella:mov_2026_06_15_digestives_opening \
      --set entity_class=StockMovement --set movement_quantity=17 ... \
      --actor fareza --valid-from 2026-06-15T00:00:00+00:00

Two intents, 2 entities minted, 17 assertions (9 and 8). Every predicate
already existed from the sealed map, so each call minted only its own subject.
`generate.py table business/sorella/v1.yaml StockMovement --verify` lists both
rows and reports *26 cells equal a direct read of the log*; 11 of 26 cells are
blank and five columns are empty — `movement_kind`, `movement_flavour`,
`movement_format`, `movement_batch`, `written_by`.

**What a quantity looks like in the log, for item two.** `value_literal` is
`text` and holds `'17'` and `'10'`, length 2, casting cleanly to `numeric`. The
compiler will have to cast. Unlike `seal`, `submit` does not round-trip through
a Python float: it takes the `--set` string and calls `str()` on it, so what was
typed is what is stored. The `4.20` → `"4.2"` T1 in `OPEN.md` is a `seal`
problem and not a `submit` one, and this seed happens not to exercise it because
packs are whole.

**Surprising.** The profile is built so that almost nothing survives the
single-unit test: of the items that move at all on Monday, the only ones counted
and worked in the same unit are wooden stirrers and paper cups, and neither has
a departure anybody records. The unit mismatch is not an edge case in this
business, it is the shape of it — §1.5 opens by calling it "the single most
persistent source of confusion" — and an aggregate that does not group by unit
can only ever be seeded around it.

Appended to `OPEN.md`: a T3 on what the compiler does with a movement that
names no place at one end, since the seed now contains one.

## 2026-09-05 — the compiler, and one rule executing

`NEXT.md` item two. New component `components/compiler/compile.py`, a `compile`
target in the `Makefile`, one more movement in the log. `generate.py` untouched,
`table()` and its defect left where they were.

**The seed first.** The 20 packs of digestives are §5.1's **Thursday 18 June**
09:15 Severn drop, not 17 June — line 2892 sits under the Thursday heading and
§5.1's own week says *Severn comes Thursday*; Wednesday's only delivery is
Whitehall Dairy's milk and cream. Same ingredient, same `pack`, so no conversion
is needed. `written_by` is Jordan Hale, who signed the driver's hand-held;
`movement_kind` and `movement_batch` are empty for the reasons item one gave.
One intent, 1 entity minted, 10 assertions. The log now holds 211 intents, 421
entities, 1700 assertions.

**The store.** The operational database is `uniti_ops`, a database of its own on
the same server, not a schema inside `uniti`. Two connections, no join between
them: a form that reached `assertion` would have to open a second connection to
another database to do it, so the read rule is enforced by the topology rather
than by discipline. The cost is that the projection is materialised through
Python — one `SELECT` against the log, one `executemany` into the store — rather
than as `INSERT ... SELECT`. **Proposed for `DECISIONS.md`:** *The operational
database is a database of its own, not a schema beside the kernel. A read path
from a form to `assertion` is then impossible rather than discouraged, at the
cost of the fill being two statements on two connections.*

**What the compiler reads.** Four words and nothing else: `over`, the operator
key, `by`, and `equals_expression`. The operator is read from the annotation
rather than assumed — `EMPTY = {"sum": "0"}` is both the list of operators it
knows and what each is over no rows. Column kinds fall out of that: a column an
aggregate groups `by` is a key, a column carrying the annotation is a total, a
column carrying `equals_expression` is arithmetic over the others, and a column
no rule reaches is nulls and is reported as such. Ranges become column types
through one table; a class or enum range is `text`, because the cell holds the
URI the log resolved to.

**The SQL it emitted**, verbatim from
`build/sorella/v1/tables/p_ingredient_on_hand.sql`, minus the three CTEs that
are the same for every map (`standing`, the DECISIONS.md 2026-08-22 rule
written once for all subjects and predicates; `registry`, uri to entity,
`DISTINCT ON` so a join cannot multiply a sum; `stated`, one standing fact as
subject/slot/value with a ref coming back as its URI):

    source_0 AS (
        SELECT s.subject_id FROM stated s
        WHERE s.slot = 'sorella:entity_class'
          AND s.value = ANY (ARRAY['StockMovement'])
    ),
    total_0 AS (
        SELECT t0_k0.value AS "ingredient_on_hand",
               t0_k1.value AS "ingredient_where",
               sum((t0_m.value)::numeric) AS "ingredient_in"
        FROM source_0 r
        LEFT JOIN stated t0_k0 ON t0_k0.subject_id = r.subject_id
                            AND t0_k0.slot = 'sorella:movement_ingredient'
        LEFT JOIN stated t0_k1 ON t0_k1.subject_id = r.subject_id
                            AND t0_k1.slot = 'sorella:movement_into'
        LEFT JOIN stated t0_m ON t0_m.subject_id = r.subject_id
                            AND t0_m.slot = 'sorella:movement_quantity'
        GROUP BY 1, 2
    ),
    total_1 AS (   -- the same, grouped by 'sorella:movement_out_of'
        ... AS "ingredient_out" ...
    ),
    grouping AS (
        SELECT "ingredient_on_hand", "ingredient_where" FROM total_0
        UNION
        SELECT "ingredient_on_hand", "ingredient_where" FROM total_1
    )
    SELECT g."ingredient_on_hand" AS "ingredient_on_hand",
           g."ingredient_where" AS "ingredient_where",
           coalesce(total_0."ingredient_in", 0) AS "ingredient_in",
           coalesce(total_1."ingredient_out", 0) AS "ingredient_out",
           (coalesce(total_0."ingredient_in", 0)
            - coalesce(total_1."ingredient_out", 0)) AS "ingredient_on_hand_net"
    FROM grouping g
    LEFT JOIN total_0 ON total_0."ingredient_on_hand"
                             IS NOT DISTINCT FROM g."ingredient_on_hand"
                     AND total_0."ingredient_where"
                             IS NOT DISTINCT FROM g."ingredient_where"
    LEFT JOIN total_1 ON ...
    ORDER BY 1, 2;

Every identifier and every literal in it came out of the map. `movement_into`
and `movement_out_of` appear once each, inside a string, because the `by` map
put them there; the subtraction is the map's `{ingredient_in} -
{ingredient_out}` with each name replaced by the SQL for that column.

Three pieces of it are worth naming. **`::numeric`** is the cast item one said
would be needed, and its type is the range of the slot the operator names, not a
guess. **`IS NOT DISTINCT FROM`** is what carries the group keyed on nothing
through the join; `=` would drop it. **`coalesce(..., 0)`** is the empty sum: a
group one total makes and the other does not is nought on the missing side, not
unknown. That is not the compiler taking a view — the map's own
`ingredient_on_hand_net` description says a place a thing left but never arrived
at "reads below nought", which is only true if the absent arrival is nought.

**`make compile`, and the hand computation.**

| Location | in | out | net |
|---|---|---|---|
| Dry store | 37 | 10 | **27** |
| Severn Catering Supplies | 0 | 37 | **−37** |
| *no location* | 10 | 0 | **10** |

37 is 17 + 20, two rows summed, which is what item one's Monday-only seed could
not exercise. 27 packs on the dry store shelf: 17 counted on Monday, less the
ten Rekha took, plus the twenty Severn dropped on Thursday. Severn is −37
because 37 packs left it and none arrived. The three nets total nought.
`p_ingredient_on_hand` holds exactly those three rows.

**The same table at an earlier clock.** `--valid-at 2026-06-16T00:00:00+00:00`
gives 17/10/**7**, 0/17/**−17**, 10/0/**10** — item one's hand computation,
reproduced without being told about it, because the 18 June movement's
`valid_from` is after that clock. Two runs of one rule at two clocks, which is
the thing the substrate is for.

**Surprising, and now a T3.** `p_gelato_on_hand` is not empty. Its three `by`
slots are `movement_flavour`, `movement_format` and `movement_into`, and the
three digestive movements state neither of the first two — so they group under
(null, null, place) and the gelato balance reads 37 / −37 / 10 in packs of
biscuits. The map's own `GelatoOnHand` description claims a line without a
flavour is "in no group at all"; it is in a group keyed on nothing, and that
group is indistinguishable from a real one. A `WHERE` would fix it and would be
the compiler deciding which rows a balance counts, which is the failure
`CLAUDE.md` calls passing by cheating, so it stands as written and `OPEN.md`
carries it as a T3 beside the no-place one. Emptiness on a *classifying*
dimension is a different problem from emptiness on a place: one makes a row
nobody asked for, the other makes a row about the wrong thing entirely.

Two `# TODO`s left, both appended to `OPEN.md` as T1: `equals_expression` is
read as arithmetic over `{slot}` names and anything else is refused, and two
aggregates on one class must group by the same set. No test today tells either
choice from its alternative.

`make test` 65 passed. `make check` not re-run: nothing this touched is in it,
and the compiler reads the working log, which `check` deliberately does not.
No test was written for the compiler — the done condition asks for a table, a
number and a grep, and all three are above.

## 2026-09-05 — The governing files restructured, and two skills installed

Authorised by Fareza in conversation, not a `NEXT.md` item. No code was
touched: `components/`, `scripts/` and `tests/` are unchanged, so `make check`
was not re-run.

**What was wrong.** `CLAUDE.md` named its design of record as
`../doc/design-2026-08-31.png`, which does not exist — the file is
`../doc/Screenshot 2026-08-31 225845.png`. `README.md` claimed three built
components (five exist), an empty `business/` (three directories), and
"expect 41 passed" (`pytest --collect-only` reports 65). `CLAUDE.md` still
carried the `generate.py` reads-no-annotations paragraph in the present tense,
which `486fe20` had made false the day before, and `NEXT.md` still carried the
compiler item unticked with the same run recorded as finished below it.

**What changed.** `ROADMAP.md` is new and is now the only file that states
status: milestones, per-stage progress, per-component status. `CLAUDE.md` was
rewritten to describe the system only — 244 lines against 319, with the stage
and component tables kept but their status columns removed. `README.md` was
corrected throughout and given a `business/` section and rows for the generator
and compiler docstrings. `NEXT.md` holds no open item.

`.claude/` was empty; nothing was installed anywhere, and no skill had ever
loaded. It now holds `skills/uniti-discuss/` and `skills/uniti-build/`.
`../uniti-pm-SKILL.md` was the ancestor of the first and is left where it is.

**Dropped rather than moved**: the ~150-line read budget, the twenty-minute
question time-box, the per-entry line ceilings, the per-file line ceilings, and
"no new `.md` files at the root". They constrained the session rather than
describing the system, and the last of them forbade `ROADMAP.md`.

Surprising: `components/interview/SKILL.md` writes `business/draft.yaml`, a
path the 4 Sep per-business version store retired. It is not installed as a
skill, so nothing was reading it — the same shape as the `equals_expression`
annotations no code read. Left alone; the stage is deferred and `OPEN.md`
already carries the `seal --into` half of it.

## 2026-09-05 — Stage 1: the write gate can carry provenance

`NEXT.md` stage 1 of the four-rules trial, taken to its done condition.

**What changed.** `submit()` in `components/generator/generate.py:337` now takes
`authority`, `confidence`, `reason_code` and `note`, and the CLI offers
`--authority`, `--confidence` (choices `high`/`medium`/`low`), `--reason-code`
and `--note`. `authority` and `confidence` land on every assertion the
submission states; `reason_code` and `note` land on the intent, `note`
replacing the default description of the submission. All four default to
`None`, and nothing fills them in. `perform()` was not touched — it already
took every one of these.

The `uniti:uri` rows minted alongside a submission deliberately carry neither
`authority` nor `confidence`: registering an identifier is bookkeeping, and
nobody set it.

**What was run.**

    make check          67 passed, replay identical twice (5334 bytes), exit 0
    grep -rn "authority" components/generator/generate.py
                        5 lines: signature, docstring, the assertion dict,
                        the CLI flag, the call. No default value anywhere

Two new tests in `tests/generator/test_generated.py` — 65 before, 67 now. The
first submits `g_tub_name` with `authority="Marina"`, `confidence="high"`,
`reason_code="correction"` and a note, then reads back the assertion's
`authority` and `confidence` and the intent's `reason_code` and `note`, and
asserts the minted `uniti:uri` row carries `(None, None)`. The second submits
the same field with no provenance and asserts NULL on the row and the default
note on the intent.

The CLI path was run end to end against `uniti_check`, with the generator's
fixture draft sealed into a scratch directory first:

     source         | authority | confidence | reason_code | note
    ----------------+-----------+------------+-------------+--------------------------
     system_derived |           |            | correction  | the CLI carries a reason
     human_stated   | Marina    | high       | correction  | the CLI carries a reason

**Surprising.** `make test` alone fails four tests — three in `tests/seal/` and
one in `tests/generator/` — on a `uniti_check` left dirty by a previous run;
`make check` reloads the schema first and all 67 pass. The same four fail on an
untouched tree, so it is not this change. It is a second face of the trap
`OPEN.md` already carries about running `pytest` directly: the suite is not
independent of the state of the database it finds.

`business/sorella/v1.yaml` has no `item_label` slot — the first smoke attempt
used it and the generator refused, listing the ten fields `BoughtItem` has. The
refusal came from the map, not from code that knew the domain.

## 2026-09-05 — Stage 2: the four slots enter the map, sealed as v2

`business/sorella/v2.yaml`, sealed from `draft.yaml` at 08:37:24 UTC. Four
slots added and nothing else: `free_delivery_above` on `Business` (decimal,
`unit: GBP`), `location_minimum_flavours` on `InternalLocation` (integer),
`item_reorder_level` and `item_order_quantity` on `BoughtItem` (decimal). 21
classes unchanged, 101 slots to 105, 0 facts. No number entered the kernel.

`valid_from` stayed at `2026-06-15T00:00:00+00:00`, byte-identical to v1's;
`supersedes: v1`; `transcript: v2.txt`, 7,717 bytes against v1.txt's 23,086 —
a new note, not a copy.

**What was run.**

    seal.py draft.yaml --actor fareza --into business/sorella
                        v2, 4 entities minted, 4 assertions.
                        The other 101 slot URIs were already registered;
                        425 uniti:uri rows in the working log after
    make build          gen-owl 105 properties, 105 domains, 36 drawable;
                        21 of 21 tables, 19 of 21 forms
    make compile        p_ingredient_on_hand 3 rows, unchanged
    make check          67 passed, replay identical twice (5334 bytes), exit 0

A rehearsal seal ran first, into a scratch directory against `uniti_check`, so
the draft was known to validate and to produce v2 before anything reached the
append-only working log. The v1-to-v2 diff is 76 added lines and 6 removed; all
six removals are the four stamped annotations and the two line boundaries the
description paragraph reflowed. No slot removed, renamed or re-ranged.

`p_ingredient_on_hand` under v2, movement data untouched:

    ingredient_on_hand               ingredient_where       in  out  net
    -------------------------------  ---------------------  --  ---  ---
    sorella:item_digestive_biscuits  sorella:loc_dry_store  37   10   27
    sorella:item_digestive_biscuits  ...severn_catering...   0   37  -37
    sorella:item_digestive_biscuits                         10    0   10

27 / −37 / 10, the same three numbers as under v1. Adding vocabulary moved no
number.

**`resolve_version` discriminated, on its first real choice.** v1 is sealed at
2026-09-03T20:14:38, v2 at 2026-09-05T08:37:24. Both hold `valid_from`
2026-06-15, so `valid_at` is the same for both and only `as_of` separates them:

    valid_at 2026-06-16  as_of 2026-09-04T00:00:00Z  ->  v1
    valid_at 2026-06-16  as_of 2026-09-05T23:00:00Z  ->  v2

Until today the component had only ever had one candidate.

The four slot URIs in the working log's registry, one query, four rows:

    sorella:free_delivery_above        386c8ad1-4236-4321-96e3-e37d23ee678e
    sorella:item_order_quantity        86323f42-3c71-447a-8e3a-3773f49788cc
    sorella:item_reorder_level         1518c851-5338-4733-a497-023d1b083f31
    sorella:location_minimum_flavours  a5003bcd-b691-4e26-95c1-bcb40d604a7a

**Surprising.** §3.4's ordering table does not carry the two numbers in one
unit, which the stage's brief assumed it did. Three of its four rows do —
"reorder at 2 tins, order 10", "reorder at 3 sacks, order 10" — and the fourth
does not: Base 50 stabiliser is "reorder at 4 bags, order 1 carton", which is
`item_counted_in` for the level and `item_ordered_in` for the quantity. The map
already draws that split, so no new slot was needed, but nothing in the map
says which of the two a given `item_order_quantity` is in. It is written into
the slot's own description and into `v2.txt`; pistachio, the only item stage 3
records, is unaffected because both of its numbers are tins.

`make build` was run before `make compile` and `mkdir -p` both times, so
`build/sorella/v1/` still stands beside `build/sorella/v2/`. Nothing removed it
and nothing points at it.

## 2026-09-05 — Stage 3: the numbers enter the kernel, with their history

Ten submissions through `generate.py submit`, all against `business/sorella/v2.yaml`,
scripted in `scripts/state_stage3.sh` — committed, because it is the record of
what was stated. Nothing was inserted directly, no `revokes` anywhere, and
nothing executes any of it. 1,704 assertions in the working log before, 1,742
after: 38 written under `ontology_version` v2, 4 entities minted.

**What was run.**

    scripts/state_stage3.sh   10 intents, 38 assertions, exit 0
    make compile              p_ingredient_on_hand, 6 rows, was 3
    make check                67 passed, replay identical twice, exit 0

The whole script was rehearsed against `uniti_check` first, so nothing
unsealable reached an append-only log.

**The six values, one query.** Every one carries `ontology_version` v2 and
`recorded_at` today; `valid_from` is the day the number took effect.

    subject                        slot                       value   valid_from  authority                 conf
    -----------------------------  -------------------------  ------  ----------  ------------------------  ----
    item_sicilian_pistachio_paste  item_pack_price            170.50  2024-09-01  Terra Nostra Ingredients
    item_sicilian_pistachio_paste  item_pack_price            203.00  2026-02-01  Terra Nostra Ingredients
    item_sicilian_pistachio_paste  item_reorder_level         2       2026-06-07  Dan Farrugia              low
    item_sicilian_pistachio_paste  item_order_quantity        10      2026-02-01  Dan Farrugia
    loc_cotham_cabinet             location_minimum_flavours  12      2025-11-01  Marina
    business_sorella_gelato        free_delivery_above        120     2026-04-01  Marina

A seventh row stands beside them and was not written today: `item_pack_price`
203.00, `valid_from` 2026-06-15, `ontology_version` v1, no authority — the
adoption-date row the log already held. It stays, as the item said.

`authority` went from 0 assertions to 6. Before this stage the column had never
been non-NULL in the working log; stage 1 gave `submit` the flag and this is the
first use of it.

The Business entity was minted first, six assertions, no authority — nobody
"set" the company's name. Rule C had no subject before it.

**Two clocks on one parameter.** `resolve_single()` on `item_pack_price` for
pistachio, `as_of` now:

    valid_at 2025-06-01  ->  170.50   (the row valid from 2024-09-01)
    valid_at 2026-06-16  ->  203.00   (the row valid from 2026-06-15)
    valid_at 2024-01-01  ->  None     (the 152.00 was never recorded)

One parameter, two clocks, two answers. The 203.00 answer is won by the
adoption-date row rather than by the 2026-02-01 one, because `valid_from DESC`
picks the later of two rows carrying the same value. Both say 203.00 so the
answer is right, but the row that wins is the one with no authority on it.

**The hand computation was 6 tins. `p_ingredient_on_hand` reads 5.32.**

    ingredient_on_hand                     ingredient_where                        in    out    net
    -------------------------------------  ------------------------------------  ----  -----  -----
    sorella:item_digestive_biscuits        sorella:loc_dry_store                   37     10     27
    sorella:item_digestive_biscuits        sorella:loc_severn_catering_supplies     0     37    -37
    sorella:item_digestive_biscuits                                                10      0     10
    sorella:item_sicilian_pistachio_paste  sorella:loc_dry_store                    6   0.68   5.32
    sorella:item_sicilian_pistachio_paste  sorella:loc_terra_nostra_ingredients     0      6     -6
    sorella:item_sicilian_pistachio_paste                                        0.68      0   0.68

The balance summed tins and kilograms into one number: 2 + 4 tins in, 0.68 kg
out, 6 − 0.68 = 5.32 of nothing. It is the second of the two outcomes the item
named in advance, and nothing was changed to repair it — no `WHERE`, no unit
filter, no conversion.

The business's own closing sheet, §5.1, counts "5 sealed, 1 open", which is 6,
because §1.5 counts a tin as one tin whether it is sealed or has 400 g left in
it. So the business and the compiler disagree by exactly one 0.68 kg draw that
the business's own counting method does not subtract.

Read under `CLAUDE.md`, "Reading a result": **missing mechanism.** No input
repairs it. Recording the draw in tins would make 6 come out, but §1.5 says the
count does not decrement on a draw, so that number would be invented. The
compiler has `movement_unit` in the map and no construct that lets an
`aggregate` say a balance is per unit or convert between two — and `OPEN.md`
already carries both halves, the G-conversion line and the line saying an
`aggregate` cannot say which rows a balance counts. This is the first time
either has been executable rather than argued.

The arithmetic is internally consistent even so: 5.32 − 6 + 0.68 = 0, so
nothing leaked. Only the units are mixed.

The digestive-biscuit rows are unchanged at 27 / −37 / 10. New facts about a
different item moved none of them.

**What was not written, and why.**

- **`item_pack_price` 152.00.** §1.6 says "it was £152.00 until September 2024"
  — an end and no start. `valid_from` is NOT NULL, so the earliest value of a
  chain cannot be recorded at all.
- **`item_order_quantity` 6**, **`location_minimum_flavours` 16**,
  **`free_delivery_above` 80.** Same shape. §3.4 dates *changes* and never
  *starts*, so for every one of the four rules the predecessor is undateable.
  Of the seven values the profile states across these four chains, three could
  be dated and four could not.

That is the result worth keeping from this stage: a business records a rule as
"12, changed from 16 in November 2025", which is one dated instant and two
values, while the two-axis model wants a `valid_from` on each. The half the
model cannot take is always the older half, so the log can never be asked what
the rule was before the first change anybody remembers.

`location_minimum_flavours` carries a second problem. "Was 16 at Cotham" is a
claim about one location; the current 12 is stated for cabinets generally. The
12 was recorded on `sorella:loc_cotham_cabinet`, which is the only cabinet the
change is evidenced at, but Gloucester Road's cabinet now carries nothing and
the map cannot say that a rule applies to a class rather than to a row.

**Surprising.**

`submit` cannot write into a log that has never been sealed into. The first
rehearsal, against a `uniti_check` freshly wiped by `make check`, died in
`perform._ref` with `ValueError: badly formed hexadecimal UUID string`:
`submit` mints the subject and every field URI but never `uniti:uri` itself, so
on a virgin log the predicate of its own registration rows resolves to the
literal string. Sealing the map into `uniti_check` first fixed it and the
script then ran clean. The working log has been sealed into since v1, so this
never touches it — but the error names a UUID, not a missing registry, and
gives a reader nothing to go on.

`--authority` was recorded verbatim from `NEXT.md`, which writes "Dan Farrugia"
in full and "Marina" without a surname, though the log holds
`sorella:person_marina_devlin`. Three spellings now stand in one text column —
two people and a company — and nothing joins any of them to a `Person` entity.

No `movement_kind` on any of the three movements: the log holds no
`MovementKind` entity and minting one would state a thing nobody has. The three
digestive movements set none either. `movement_batch` is empty for the same
reason — batch 2026-0838 is in `movement_note` as text.

## 2026-09-06 — Stage substrate: the door into an empty log, and the seed measured

`NEXT.md`, stage **substrate**. Two of its seven done conditions are met and
the third through sixth are held at the checkpoint condition 1 puts in front of
them.

**The blocker, cleared.** `seal.py` gained `register()` and a `--register`
flag. It takes a version that is already sealed, reads the `slot_uri` of every
slot it declares, and writes one `uniti:uri` row for each one the log does not
already hold — the same rows `seal` writes, under the same predicate, dated by
the version's own `valid_from`. No file is written and no version number is
assigned. A file still carrying `annotations.facts` is refused as a draft; a
file with no `version:` is refused for the same reason.

    createdb uniti_trial; psql -f /kernel/001_schema.sql
    UNITI_DSN=…/uniti_trial seal.py business/sorella/v2.yaml --register --actor fareza
    → registered business/sorella/v2.yaml (v2)
      valid from 2026-06-15T00:00:00+00:00
      intent d5925203: 106 entities minted, 106 assertions

106 = v2's 105 slots plus `uniti:uri`, which registers itself.
`business/sorella/` before and after holds `v1.yaml`, `v1.txt`, `v2.yaml`,
`v2.txt`, `draft.yaml`, `draft.txt`, `profile.md` — unchanged, so **done
condition 2 holds**.

**`state_stage3.sh` re-ran unchanged against `uniti_trial`**: 10 submissions,
6 minted subjects, all six parameter values landed. `resolve_single` on
`item_pack_price`:

| `valid_at` | value | `valid_from` of the winning row | `authority` |
|---|---|---|---|
| 2025-06-01 | 170.50 | 2024-09-01 | Terra Nostra Ingredients |
| 2026-06-16 | 203.00 | 2026-02-01 | Terra Nostra Ingredients |

That is **done condition 5**, including its second half. In the working log the
winner at the second clock was the adoption-dated row with `authority` NULL;
here nothing blanket-dated shadows the February row, so the answer carries who
said it. Trial log after both runs: 11 intents, 116 entities, 150 assertions,
`valid_from` spread over 2024-09-01, 2025-11-01, 2026-02-01, 2026-04-01,
2026-06-07, 2026-06-15 and 2026-06-16.

**The enumeration** is `scripts/seed_2026_06_16.md`, written before anything
was submitted — **done condition 1**. It applies the selection rule to §4.3 and
§4.1, numbers every row, and states the four conventions it had to commit to
before a row could be written: one movement per line of paper (so the van is
named only where the profile puts something in it), a quantity is the number on
the paper or nothing, a place is the finest one the paper distinguishes, and
master data is not in the seed.

**The size, measured rather than guessed:**

| Part | Rows | | Part | Rows |
|---|---|---|---|---|
| B1 deliveries received | 10 | | B9 evening stock count | 39 |
| B2 produced | 22 | | C1 opening — ingredients | 57 |
| B3 wholesale delivered | 23 | | C2 opening — gelato | 50 |
| B4 transferred to the shops | 22 | | D control carried over | 3 |
| B5 sold | 25 | | | |
| B6 the cake order | 0 | | **Total** | **265** |
| B7 given away | 6 | | | |
| B8 thrown out | 8 | | | |

265 `generate.py submit` calls, each with a note quoting its profile section.
Two more rows the rule selects are already in the log — pistachio's opening
position and its Terra Nostra pallet line — so the day is 267 rows. Dates:
2026-06-15 on 109, 2026-06-16 on 155, 2026-06-18 on 1. The seeded log would be
about 276 intents and roughly 2,600 assertions.

**28 findings** are written up rather than skipped. The sharpest is **F14**:
the cake notice period moved from three days to forty-eight hours on 16 June
2026 — the only rule §3.4 says changed while anybody was recording — and v2
names no slot for it, so the one rule that moved is the one the log cannot
hold. **F2**: the nine batches draw no recorded ingredient off any shelf, and
the only draw this trial has comes from a §2.3 recipe page rather than from the
day. **F19/F20**: twelve of the evening count's 38 lines are words rather than
a number, and none of the 38 carries a confidence.

**`make check`: ok, 69 tests.** Two new ones in `tests/seal/test_seal.py` —
`register` names every `slot_uri` and writes no file, and a second call mints
nothing and reuses what the first minted. The count is 69 and not the 67
`NEXT.md` predicts: the repo was already at 67 before this run, not the 65 the
prediction was made from. `grep` over `components/` for business terms finds
six hits, all of them usage examples in docstrings, which `CLAUDE.md` exempts.

**Surprising.**

Registering a sealed version costs one intent and 106 assertions, and every one
of them carries `valid_from 2026-06-15` — the version's own. So a freshly
registered log already has 106 rows sharing one date before a single fact is
stated. They are `uniti:uri` bookkeeping under `source = system_derived` and
not claims about the world, but a query grouping the log by `valid_from` sees
them, and done condition 4's "no blanket dates" has to be read as being about
stated facts rather than about the registry.

Applying the selection rule turns up **107 opening-position rows against the
day's own 116 movements** — the previous morning is nearly as large as the day
it opens. Most of the difference is §4.1's count of the two shops, the
packaging mezzanine and the coffee bar, which 16 June touches through sales and
transfers but which no single §4.3 line names.

The enumeration cannot be transcribed mechanically. Four questions had to be
decided before any row could be written, and each of them changes the row
count: whether the van is a leg or a place, whether "1 half pan" is 0.5 or no
number, whether a place with two names is one row or two, and whether the
12.0 kg mix line is a movement. Three of the four went the way that produces
*fewer* rows and *more* findings.

---

## 2026-09-06 — The crossing: a parameter named by the graph, executed

`NEXT.md`'s one item, all four parts. Everything below ran against
`uniti_trial`; the working log `uniti` was not touched.

**What was run, in order.**

    python <scratch>/mkscratch.py business/sorella/v2.yaml <scratch>/v2p.yaml
    UNITI_DSN=…/uniti_trial python components/compiler/compile.py <scratch>/v2p.yaml \
        IngredientOnHand --valid-at 2026-06-16 --as-of 2026-09-06
    UNITI_DSN=…/uniti_check bash scripts/state_six_items.sh          # smoke test
    bash scripts/state_six_items.sh                                  # into uniti_trial
    UNITI_DSN=…/uniti_check python components/seal/seal.py business/sorella/draft.yaml \
        --actor fareza --into business/sorella
    UNITI_DSN=…/uniti_trial python components/seal/seal.py business/sorella/v3.yaml \
        --actor fareza --register
    UNITI_DSN=…/uniti_trial python components/compiler/compile.py business/sorella/v3.yaml \
        IngredientOnHand --valid-at 2025-06-01 --as-of 2026-09-06 --into build/sorella/v3/tables/2025-06-01
    UNITI_DSN=…/uniti_trial python components/compiler/compile.py business/sorella/v3.yaml \
        IngredientOnHand --valid-at 2026-06-16 --as-of 2026-09-06 --into build/sorella/v3/tables/2026-06-16
    make check

**Part 2 first, against a scratch map.** The parameter column was written and
proved against a copy of `v2.yaml` in the scratchpad before anything was
sealed, which is how `CLAUDE.md`'s refusal of unexecutable notation was
honoured. The compiler's vocabulary went from four words to six: `parameter`,
`of`, `slot`. `plan()` gained a fifth column kind and `emit()` one CTE shape.
The emitted SQL for a parameter is five lines, and it reads the same `stated`
CTE every other cell reads, so both clocks come free:

    param_0 AS (
        SELECT e.uri AS key_value, s.value AS value
        FROM registry e
        JOIN stated s ON s.subject_id = e.entity_id
                     AND s.slot = 'sorella:item_reorder_level'
    ),
    …
    LEFT JOIN param_0 ON param_0.key_value IS NOT DISTINCT FROM g."ingredient_on_hand"

`'sorella:item_reorder_level'` is the only place the slot appears, and it came
out of the map.

**Part 1, `scripts/state_six_items.sh`.** 23 submissions through
`generate.py submit`: 6 master-data rows, 5 pack prices, 2 reorder levels and
10 movements. Pistachio's price chain, its level, its opening position and its
pallet line were already there and were not rewritten. The trial log went from
11 intents / 116 entities / 150 assertions to **35 / 139 / 274**, over eight
distinct `valid_from` dates: 2023-01-01, 2024-09-01, 2025-11-01, 2026-02-01,
2026-04-01, 2026-06-07, 2026-06-15, 2026-06-16.

**Part 3, v3.** Sealed from `business/sorella/draft.yaml` with a fresh
`draft.txt`; `valid_from` unchanged at `2026-06-15T00:00:00Z`, `sealed_at`
2026-09-05T23:19:25Z, `supersedes: v2`. 109 slots, was 105. `--register` into
`uniti_trial` minted **4 entities and 4 assertions** — exactly the four new
slot URIs. `VERSION` in the Makefile now reads `v3`.

**Part 4, the table at `valid_at 2026-06-16`, `as_of 2026-09-06`.** 16 rows,
9 columns.

| item | where | unit | in | out | net | level | price | value |
|---|---|---|---|---|---|---|---|---|
| base_50_stabiliser | dry_store | bag | 4 | 0 | 4 | 4 | 276.00 | 1104.00 |
| base_50_stabiliser | dry_store | carton | 1 | 0 | 1 | 4 | 276.00 | 276.00 |
| base_50_stabiliser | terra_nostra | bag | 0 | 4 | −4 | 4 | 276.00 | −1104.00 |
| base_50_stabiliser | terra_nostra | carton | 0 | 1 | −1 | 4 | 276.00 | −276.00 |
| cocoa_22_24 | dry_store | bag | 4 | 0 | 4 | | 41.00 | 164.00 |
| cocoa_22_24 | terra_nostra | bag | 0 | 4 | −4 | | 41.00 | −164.00 |
| dark_chocolate_70 | dry_store | box | 3 | 0 | 3 | | 96.00 | 288.00 |
| dark_chocolate_70 | terra_nostra | box | 0 | 3 | −3 | | 96.00 | −288.00 |
| dextrose | dry_store | sack | 4 | 0 | 4 | | 41.00 | 164.00 |
| dextrose | terra_nostra | sack | 0 | 4 | −4 | | 41.00 | −164.00 |
| hazelnut_paste | dry_store | tin | 4 | 0 | 4 | 2 | 142.50 | 570.00 |
| hazelnut_paste | terra_nostra | tin | 0 | 4 | −4 | 2 | 142.50 | −570.00 |
| pistachio_paste | dry_store | kilogram | 0 | 0.68 | −0.68 | 2 | 203.00 | −138.0400 |
| pistachio_paste | dry_store | tin | 6 | 0 | 6 | 2 | 203.00 | 1218.00 |
| pistachio_paste | terra_nostra | tin | 0 | 6 | −6 | 2 | 203.00 | −1218.00 |
| pistachio_paste | *(none)* | kilogram | 0.68 | 0 | 0.68 | 2 | 203.00 | 138.0400 |

The run at `valid_at 2025-06-01`, `as_of 2026-09-06`, same map and same log:
**0 rows**, 9 columns.

**The done conditions, one by one.**

1. **Holds.** Six items. Base 50 reads 4, hazelnut 2, pistachio 2 — exactly the
   three §3.4 names — and cocoa, dark chocolate and dextrose read empty. Not 0:
   the cell is NULL, and §3.4:1682 names those three among the things with no
   written level.
2. **Holds.** Pistachio is 6 tins and −0.68 kg as two rows. Six is 2 from
   §4.1's "1 sealed, 1 open" plus 4 from §4.3's pallet line. The 5.32 of 5 Sep
   is gone because `ingredient_unit` is a third grouping dimension, not because
   a `WHERE` removed anything: every movement that entered the 5.32 is still in
   the table, in one of the two rows.
3. **Holds.** Base 50 appears twice at the dry store, 4 bags and 1 carton,
   unconverted, and twice more at the supplier with the signs reversed.
4. **Holds.** `ingredient_stock_value` is 1218.00 for pistachio in tins: 6, a
   number summed out of the movements, times 203.00, a number Terra Nostra set
   in February 2026 and somebody wrote into §1.6. The graph named the price,
   through `parameter: {of: ingredient_on_hand, slot: item_pack_price}`, and
   the compiler read the log through that name. **A rule carried half in the
   graph and half in the kernel executed.** Ninety-three parameter values had
   been inert since 5 Sep; two of them are now read.
5. **Does not hold, and no pair of clocks on this log would make it hold.** The
   run at `valid_at 2025-06-01` returns 0 rows rather than the same movements
   at the older price. Every movement in the trial log has `valid_from`
   2026-06-15 or 2026-06-16, and pistachio's price rose from 170.50 to 203.00
   on 2026-02-01, four months earlier — so at every clock where a movement
   stands the price is already 203.00, and at every clock where 170.50 stands
   there are no movements. `as_of` does not rescue it: the 203.00 row was
   recorded at 22:39:20.919989 and the 170.50 row at 22:39:21.580324 on 5 Sep,
   both before any movement was recorded, so no `as_of` yields 170.50 with rows
   beside it. The two runs do differ, but they differ because the movements
   appeared and not because a rule moved. Missing information rather than a
   missing mechanism — the clocks reach the parameter, which `resolve_single`
   showed on 5 Sep and which the emitted SQL shows structurally, since the
   parameter is read out of the already-resolved `stated` — but the input that
   would make it pass is a movement dated before February 2026, and the profile
   has none.
6. **Holds.** `grep -rn -i "pistachio\|reorder\|tin\|cocoa\|stock\|ingredient"
   components/ --include=*.py` returns 7 lines, every one of them either a
   substring inside an ordinary word — `DISTINCT`, `minting`, `continuations`,
   `stated` — or prose in a docstring. No live code path branches on a business
   word. `parameter`, `of` and `slot` are the only names the change added, and
   none of them is a business term.
7. **Holds.** `make check`: ok, **69 tests**, replay byte-identical twice.
   `business/sorella/` holds v1, v2 and v3 and no v4.

**Surprising.**

The parameter column needed **no clock machinery at all**. The expectation was
that a fact with a history would want resolving separately from the rows; it
does not, because `stated` is already one resolution of the whole log at the
two clocks and a parameter is one more read of it. Five lines of SQL, and the
history came with them.

The unit dimension changed **which rows exist**, not only what they read.
Before it, pistachio at the dry store was one row reading 5.32; after it, two
rows reading 6 and −0.68 — and Base 50 went from one row to two at each of two
places. The table is 16 rows where the same movements without the dimension
would give 8, and not one movement was added to make that happen.

`ingredient_stock_value` is **wrong in a visible way** for Base 50, and that is
the honest output rather than a defect: 1 carton × £276.00 is right, and 4 bags
× £276.00 = £1104.00 is four times what is actually on the shelf, because §1.6
prices Base 50 by the carton, §1.5 counts it in bags, and nothing converts. The
map states no conversion, so the compiler states none, and the row says so on
its face rather than quietly averaging it away.

Sealing v3 minted **97 entities into `uniti_check`** and 4 into `uniti_trial`.
The 97 is the whole v2 vocabulary, because `uniti_check` had been wiped by the
previous `make check`; the 4 is the real number of new names in v3. Sealing
against a throwaway log and registering into the real one keeps those two
numbers apart, which is what `--register` was built for on 6 Sep.

---

## 2026-09-06 — The loop, in a browser

`NEXT.md`'s "Open: the loop, in a browser", all four parts, against the trial
log `uniti_trial` and a store of its own, `uniti_trial_ops`.

**What was run.**

    scripts/state_places_and_units.sh                 8 submissions
    make serve                                        v3, port 8000
    curl GET  /                                       19 forms, 2 tables
    curl GET  /form/StockMovement
    curl GET  /table/IngredientOnHand?valid_at=2026-06-16&as_of=2026-09-06
    curl GET  /table/IngredientOnHand?valid_at=2026-06-15&as_of=2026-09-06
    curl POST /form/StockMovement                     one movement
    curl GET  /table/IngredientOnHand                 at now
    grep -rn -i "pistachio|movement|stock|ingredient|location" components/web/
    make check

Three files added and one edited: `scripts/state_places_and_units.sh`,
`components/web/render.py`, `components/web/serve.py`, and a `serve` target in
the `Makefile`. Nothing under `components/generator/` or `components/compiler/`
was touched.

**The eight classifications.** Eight submissions through `generate.py submit`,
**0 entities minted** in all eight: every one of the eight URIs was already in
the registry, put there as a `value_ref` by the movements that name it. What
was missing was only what each one *is*. `uniti_trial` went 274 → 290
assertions, 35 → 43 intents, and stayed at 139 entities.

**Done condition 1. Holds.** `GET /` lists 19 classes with a form and 2 with a
table, both counted out of the map: 19 is every class carrying a
`designates_type` slot, 2 is every class carrying an `aggregate`.

**Done condition 2. Holds.** `/form/StockMovement` before the eight
submissions: `movement_out_of` and `movement_into` offered nothing,
`movement_unit` offered nothing. After: 2 places — "Dry store" and "Terra
Nostra Ingredients", the second reached because `Supplier is_a Location` — and
6 units, "bag box carton kilogram sack tin", each by its name and not its URI.
`movement_ingredient` still offers its 6 by URI alone: `Ingredient`'s
identifier slot holds no value for them, which is a fact about the seed and
not about the renderer.

**Done condition 3. Holds.** `/table/IngredientOnHand` at `valid_at=2026-06-16`
is **16 rows**, pistachio at the dry store 6 tins. The same URL at
`valid_at=2026-06-15` is **12 rows**, pistachio 2 tins. Nothing but the clock
box changed, and each load is a full drop and rebuild of `ingredient_on_hand`
in `uniti_trial_ops`.

**Done condition 4. Holds — the loop closed.** Before the write, dextrose at
the dry store in sacks read `in 4, out 0, net 4`. One POST to
`/form/StockMovement`, the request the rendered form makes, under a subject the
log had never seen, `sorella:mov_2026_09_06_web_dextrose`, 3 sacks from Terra
Nostra Ingredients into the dry store. The page came back saying **1 intent, 9
assertions, 1 entity minted**, and the log moved 43 → 44 intents, 290 → 299
assertions, 139 → 140 entities. Reloading `/table/IngredientOnHand` at the
default clocks: dextrose at the dry store reads `in 7, out 0, net 7`, and the
supplier side `out 7, net −7`. **No script was run between the two loads.** The
page rebuilt the table itself.

The write went through `generate.submit()` and nowhere else, and the reload
through `compile.compile_class()` and nowhere else — the interface added no
write path and no read path of its own.

**Done condition 5. Holds.** `grep -rn -i
"pistachio\|movement\|stock\|ingredient\|location" components/web/` returns
nothing, exit 1. `make check`: ok, **69 tests**, replay byte-identical twice.

**Surprising.**

`Location` is a **business word and an HTTP header**. The obvious shape for a
POST is a 303 back to the form, and `Location:` in the response would have
tripped the very grep the item is checked by. The route re-renders the form at
status 200 instead, which is a better page anyway — it can say what was
written. The constraint picked the design.

The two clocks needed **no code**. `page()` puts them in a `<form method=get
action="">`, which the browser submits back to the URL it is on, so one form
serves all four routes and every page is at a stated pair of clocks without a
single line deciding what to do with them.

`render.py` is **252 lines and holds no `if` over any name**. Everything it
prints — nineteen class names, thirteen slot names, five column kinds, which
field is a dropdown and which a box — arrived inside the structure it was
handed. The only table it carries is `INPUT_TYPE`, six LinkML primitive ranges
to six HTML input types, which is a fact about LinkML and the browser and about
no business.

`entity_class` had to be **prefilled**, and it is read from the map, not
guessed: `_type_slot(map_, CLASS)` names the slot and the class name fills it.
Without it a person filling the form by hand writes an entity nothing can ever
say the class of — a subject with facts on it and no table it belongs to. The
form's own defect and the map's own answer, in one line.

The web component has **no test**. `make check`'s 69 are the 69 that were there
before; the done condition asked for five checks against a running server and
those were run by hand. The interface is the least-covered component in the
repository.

---

## 2026-09-06 — Every link the app builds was broken, and nothing found it

A check of the previous entry's item, run by following the application's own
links rather than by typing URLs at it.

**What was wrong.** `render._carried()` built the query string that every link
and every page header carries:

    return f"valid_at={escape(str(valid_at))}&amp;as_of={escape(str(as_of))}"

`escape()` is HTML escaping. An offset-aware clock ends in `+00:00`, and a `+`
in a query string means a space to every reader of one, so `parse_qs` on the
next request produced `2026-09-06T10:48:52.177118 00:00` and Postgres refused
it. Eleven of the twenty-two links the index page renders returned **500**.

Which eleven is the shape that made it look intermittent: a form 500s if and
only if it has a `ref` field, because only a ref field calls `_options`, and
only `_options` puts a timestamp into a query. `Unit`, `Business`, `Flavour`,
`Person` and five others have none and rendered fine; `StockMovement`,
`Ingredient`, `Recipe` and five others 500'd, and so did both tables.

**Why the previous session's five done conditions all passed.** Every check in
that entry was a `curl` against a hand-written URL:

    curl GET /table/IngredientOnHand?valid_at=2026-06-16&as_of=2026-09-06

`2026-06-16` contains no `+`, so it round-trips. Not one check followed a link
the application generated, so the defect was invisible to a test suite that
covered every route. **The route was never the untested thing; the link was.**

**Two changes.** `_carried()` now percent-encodes before it HTML-escapes, via
`urlencode`, which writes the offset `%2B00%3A00`. And `_clocks()` in
`serve.py`, which had a docstring saying it validated nothing on purpose, now
parses each clock with `datetime.fromisoformat` and raises `ClockError`. A
clock that is not a time is a 400 naming the field, not a 500 quoting
Postgres. The parse is thrown away; what reaches the query is still the text as
written.

**After, by crawling.** A script that reads `GET /` and follows every `href` it
finds:

    22 links followed, 0 broken

with `/table/IngredientOnHand` at **16 rows** and `/table/GelatoOnHand` at 3.

**The clock box, submitted as a browser submits it.** `valid_at=2026-06-15` is
**12 rows**, `valid_at=2026-06-16` is **16 rows**, pistachio 2 tins against 6.

**The loop, closed again.** A `StockMovement` POSTed to `/form/StockMovement`
with quantity 5: one intent, 8 assertions, 1 entity minted. Dextrose at the dry
store then read `in 12, out 0, net 12` at the default clocks — 4 from the seed,
3 from the previous session's own test write, 5 from this one. No script ran
between the write and the read.

`make check` ok. `grep -rn -i "pistachio\|movement\|stock\|ingredient\|location"
components/web/` finds nothing in a live code path.

**Surprising.** The write does not appear at the clock its own `happened_on`
names. A movement submitted through the form with `happened_on 2026-06-16` is
absent from the table at `valid_at 2026-06-16` and present at now, because the
form has no `valid_from` field and every assertion it writes is valid from the
moment it is written. `happened_on` is a fact about the movement and
`valid_from` is a fact about the claim; the form shows the first and sets the
second silently. `OPEN.md` has carried that question since 4 Sep as a `[T3]`,
and the interface turns it from a question about recording into the reason the
demonstration cannot tell its own story.

## 2026-09-07 — the demonstration business: a narrow map, its own log, and the dropdown's read into the kernel closed

`NEXT.md` demo item one, all six done conditions. Nothing of the surface and
nothing of the agent: this is the business the next two items stand on.

**The map.** `business/sorella_demo/draft.yaml`, hand-authored, sealed as `v1`
with `--into business/sorella_demo`. 12 classes, 51 slots, 52 URIs registered,
52 assertions, one intent. Nine classes are what the business is, three are
what it writes, two are computed. Every slot that means what a slot of
`business/sorella/v3.yaml` means carries that slot's `slot_uri` unchanged under
the `sorella:` prefix; only `CountedOnHand`'s four declare `sorella_demo:` URIs,
because v3 has no class for them. `draft.txt` is the business in prose, 200
lines, and stands on its own — it names every class and every slot the map
declares without pointing at `profile.md` or at this repository.

`CountedOnHand` is the new one: an `aggregate` over `StockCountLine`, summing
`count_line_quantity` by ingredient, place and unit. It compiled first time.
Whether the two tables can be subtracted in one expression was not tried; they
stand side by side, as the item says.

**The seed.** `make demo-seed` into `uniti_demo`, from empty, every write
through `generate.submit`, no `INSERT` anywhere in `scripts/seed_demo.py`.

    31 master rows, 190 movements, 18 count lines on 2 sheets
    241 intents and 2,185 assertions from the seed
    242 intents, 2,237 assertions, 292 entities in the log with `register`

Run twice from empty: the same three numbers both times.

**The store.** `make demo-seed` compiles afterwards, and `compile.py` with no
class named now fills a table for every class the map can fill — 12 of them:
`p_ingredient_on_hand` (59 rows), `p_counted_on_hand` (10), and ten lists of
entities. That second shape is new: a class the map gives no aggregate but that
the log can say an entity is of compiles to one row per entity, one column per
slot, and a first column `entity_uri` carrying the URI the log registered it
under.

**Four routes, on port 8100.** The index lists **3 forms under "what gets
written down"** — `StockCount`, `StockCountLine`, `StockMovement` — **7 under
"what it refers to"**, and **2 tables**. The grouping is read off the map and
is not a list of business names: a class one of its slots *identifies* is a
thing somebody names; a class nothing identifies is an event. The three
documents are exactly the three classes this map gives no identifier.

**The clock, moved.** `/table/IngredientOnHand`:

    valid_at                    rows
    now (2026-09-06T22:2x)        59
    2026-08-10                    57
    2026-08-09                    54

    row                                            in    out   net    price    value
    dextrose, dry store, sacks   at now            20      8    12    41.00   492.00
    dextrose, dry store, sacks   at 2026-08-10      6      8    -2    41.00   -82.00
    pistachio, dry store, tins   at now            36      8    28   214.00  5992.00
    pistachio, dry store, tins   at 2026-08-10     19      7    12   214.00  2568.00
    pistachio, dry store, tins   at 2026-08-09     19      6    13   203.00  2639.00

The last two lines are the parameter's own history executing. The seed states
the pistachio price twice — 203.00 from 13 July, 214.00 from 10 August, neither
revoking the other — and the table asked at 9 August multiplies by 203.00 and
asked at 10 August by 214.00. Nothing in the map or the compiler knows a price
changed; both rows stand and the clock picks one.

**The dropdowns, out of the operational store.** Every select on the three
document forms is filled:

    StockMovement   movement_kind 5, movement_out_of 8, movement_into 8,
                    movement_ingredient 8, movement_unit 6, written_by 3
    StockCount      written_by 3
    StockCountLine  line_count 2, count_line_ingredient 8,
                    count_line_where 8, count_line_unit 6

Proved to come from the store rather than the log by inserting one row into
`p_unit` that no assertion says anything about — `probe:unit_only_in_the_store`
— and reloading the form: `movement_unit` offered 7, the seventh being the
probe. `p_unit` was recompiled afterwards and is 6 rows again.

**The loop.** `POST /form/StockMovement`, form-encoded, 5 sacks of dextrose out
of Terra Nostra into the dry store: one intent, 11 assertions, 1 entity minted.
Reloading `/table/IngredientOnHand` at the default clocks: dextrose at the dry
store in sacks went `20 / 8 / 12` to `25 / 8 / 17`, value 492.00 to 697.00, and
the log went 242 intents to 243, 2,237 assertions to 2,248. No script ran
between the write and the read. The log was reseeded afterwards, so the counts
above are the seeded ones.

**`make check` ok**, 69 tests. `grep -rn -i
"gelato\|pistachio\|movement\|stock\|ingredient\|location" components/` finds
nothing at all — not in a live path and not in a docstring either.

### Surprising

**The forbidden read closed further than the item asked.** The item names four
classes for a projection — `Ingredient`, `Unit`, `Location`, `MovementKind` —
and expects `_options` to fall back to the kernel for the rest. It does not:
`compile.py` with no class named fills a table for every class the log can
classify, so `Person` and `StockCount` have one too, and for this map
`_options` never reaches `assertion` at all. The fallback path is still there
and is still what Sorella's map uses, because `make compile` has not been run
against it since.

**A dropdown over a class nothing identifies shows URIs.** `line_count` offers
the two count sheets as `sorella:count_2026-08-02` and `sorella:count_2026-08-30`
with no name beside them, because `StockCount` declares no identifier — the map
says in its own description that nothing in the business identifies a count
sheet. There is no input that would repair it: a name would have to be invented
first. The store path and the kernel path behave identically here, so this is
not a regression from the change.

**Every internal place has one negative row, and it is the unit dimension
saying so.** Waste is weighed, so it leaves in kilos, and nothing ever arrives
in kilos — `dry store / kilos` reads −34.87 for dextrose while `dry store /
sacks` reads +12. That is the map refusing to convert, working exactly as
`ingredient_unit` was added to make it work, and it will read as broken data to
anyone shown the table without that sentence. Worth knowing before item two
puts it on a screen.

**A hand-authored draft is not a machine-dumped one.** `seal` refused the first
draft with a LinkML `ScannerError`: a plain-scalar `description:` whose
continuation line contains `": "` is not valid YAML. Every existing map was
written by `yaml.safe_dump`, which quotes for you, so nothing had ever hit it.
Fixed by making every description a `>-` block.

**Two notes on the environment, neither a defect of the system.** The Chrome
extension was not connected, so the loop was closed with a form-encoded POST to
`/form/StockMovement` — byte for byte what the browser sends — rather than
through a browser window. And a `serve.py` from an earlier session was still
holding port 8000 and answering with Sorella's v3 map; `make demo-serve
PORT=8100` was used throughout, and that process is still running.
## 2026-09-07 — demo item two: the surface, and the log behind a cell

`NEXT.md` item two, run to its seven done conditions. Four new things exist:
`components/provenance/`, `components/web/diagram.py`, four routes on
`serve.py`, and `tests/provenance/`. No mechanism was widened — every number on
every page still comes out of the operational store, and the one page that
reads the log reads it for provenance and computes nothing.

### The seven conditions

**1 · the port and the walk.** `make demo-serve` binds **8100**, from
`DEMO_PORT` in the Makefile rather than the shared `PORT`. `/` is six cards in
stage order — *What was said*, *What it became*, *What was recorded*, *What was
generated*, *Live use*, *Definition change* — and the sixth is drawn dead, with
"not built yet" where the link would be. The eleven forms and two tables moved
to `/classes`, which cards four and five enter at `#forms` and `#tables`.

**2 · `/said`.** 36 paragraphs of `v1.txt` on the left, `v1.yaml` on the right,
and **12 of 12 classes linked** to a paragraph. Spot-checked, every one of the
twelve lands on the sentence that asked for it: `InternalLocation` → "There are
two places inside the business in this corner of it", `Supplier` → "A supplier
is a place. That is the part of this description that surprises people",
`StockCountLine` → "Each line on the sheet is the third document".

**3 · `/graph`.** The class diagram is 12 classes, 2 inheritance edges and 19
relations, generated as Mermaid text from the map. Every column header of a
grouped table links to `/graph?class=…&column=…`;
`IngredientOnHand.ingredient_stock_value` draws six column nodes and nine
source nodes — the expression `{ingredient_on_hand_net} * {ingredient_pack_price}`,
below it `{ingredient_in} - {ingredient_out}`, below those **both aggregates**
(`sum of StockMovement.sorella:movement_quantity by ingredient_on_hand =
sorella:movement_ingredient, ingredient_unit = sorella:movement_unit,
ingredient_where = sorella:movement_into`, and the same into
`movement_out_of`), and beside them the **parameter**, `sorella:item_pack_price`
of the entity `ingredient_on_hand` names, reading "the log — stated, never
computed".

**4 · the window.** `/table/IngredientOnHand?valid_at=2026-06-16&as_of=2026-09-07`
still says "No rows at these clocks" and now says what it is outside of: *The
log holds 2,237 assertions under 242 intents. Nothing in it is valid before
2026-07-13 00:00:00+00:00, and the latest anything is valid from is
2026-08-30 00:00:00+00:00.* The window is one query in `provenance.window()`.

**5 · a blank subject.** `POST /form/StockMovement` with `subject=` empty, form
encoded, ten fields: **200, one intent, 10 assertions, 1 entity minted**, and
the page says *The subject was left blank, so one was minted for it:
`sorella_demo:stockmovement_af5d49f16eab`*. The URI is the map's own
`default_prefix`, the class name the form came from, and 12 hex digits. The log
was reseeded afterwards, so the counts elsewhere in this entry are the seeded
ones.

**6 · `/why` for the pack price.** `sorella:item_sicilian_pistachio_paste` /
`sorella:item_pack_price` returns **two** assertions, neither revoking the
other:

    203.00  valid_from 2026-07-13  human_stated  authority Marina Devlin
    214.00  valid_from 2026-08-10  human_stated  authority Terra Nostra
                                                 invoice, 10 August

Both carry actor `marina`, action `submit_Ingredient` and their intent id. Every
`parameter` cell in a grouped table and every `stated` cell in an entity table
links to its own pair — 79 such links on `/table/IngredientOnHand` alone.

**7 · the two checks.** `make check` ok, **74 tests** (69 before; the five new
ones are `tests/provenance/`). `grep -rn -i
"gelato\|pistachio\|movement\|stock\|ingredient\|location" components/` finds
exactly one line, `components/interview/SKILL.md:89`, which is prose in a skill
file and predates this item. No live code path names a business term, the new
files included.

### The fix to the form's own note

`render.form_html` told the reader the dropdown choices "were read out of the
log". `generate._options` now returns *(pairs, source)* and the page prints the
source it was handed: for this map it says **"read out of the operational
store"** for all six ref fields, with no "and the log", because every class the
demo map's ref fields range over is compiled.

### Surprising

**Blank lines inside a block scalar closed the section.** `/said` linked 6 of
12 classes on the first run, and the six missing were the last six in the file.
The scan for the `classes:` block treated any line not starting with a space as
a new top-level key, and `v1.yaml` has blank lines at 104, 147 and 167 — inside
`description:` blocks. A blank line is inside whatever contains it; the fix is
one condition.

**The bridge from the map to the transcript is the description, not the name.**
Matching paragraphs on the words of the class name alone linked 6 of 12 and put
`Ingredient` on a paragraph about something else. `Location` and
`InternalLocation` matched nothing at all, because the transcript never uses the
word "location" — it says "place". Scoring the class's *description* as well,
each word worth `1/(paragraphs containing it)` and a name word worth six times a
description word, links all twelve and lands every one correctly. The
description is where the business's own words survive into the map, so it is
what a transcript can be matched against. The weight was tried at 3 (Ingredient
wrong) and 10 (StockCount wrong) before 6.

**Two servers held port 8100 at once.** Windows accepted a second bind on a port
already listening, so the first probe run was answered by the process from the
previous session and every result looked unchanged. Both had to be stopped by
pid before the new code served anything. `netstat -ano | grep 8100` showing two
LISTENING lines is the tell.

**A `#` ends the URL.** The stage cards were built as `/classes#forms` plus the
carried clocks and came out `/classes#forms?valid_at=…`, which is a fragment
called `forms?valid_at=…` and a request with no clocks on it. The clocks go
before the fragment.

**The most persuasive page needed the least code.** `/graph`'s formula view is
about sixty lines over `compile.plan()`, because the plan already holds every
column's kind, its aggregate, its parameter and its expression — it is what the
compiler emits SQL from. Drawing it is a second rendering of a structure that
was already there, which is exactly the claim being made about it.

**Not verified: the drawing itself.** The Chrome extension is not connected, so
the Mermaid *text* was checked against the map — 12 classes, both aggregates,
the parameter — and the rendered picture was not. If the CDN is unreachable the
`<div class="mermaid">` shows that text instead of a diagram, which is legible
but is not the page as intended.

## 2026-09-07 — Demo item three: both clocks alive, corrections in the log, a table that can be read

`NEXT.md`'s six conditions, each run.

### What was changed

**The write gate takes a correction.** `generate.submit()` gains `revokes`
(field name -> the assertion id it withdraws), `source`, and a `stated` key in
its result giving field name -> the id that field wrote, which is how a caller
gets the id it later revokes. A field in `values` and `revokes` together is a
correction; a field in `revokes` alone writes an assertion with no value at
all, which the kernel's `value_exactly_one` constraint has always allowed and
nothing had ever written. No schema change: the column list is untouched.

**The map got titles and an earlier adoption date.** `business/sorella_demo/`
was resealed as **v2**: all 51 slots carry a `title`, and `valid_from` moved
from 13 July to 2 March. Not one `slot_uri` moved and not one slot name
changed, so every predicate is the predicate it was. `make demo-seed` and
`make demo-serve` point at v2; v1 stays where it is.

**The seed states both clocks.** `scripts/seed_demo.py` rewritten: 26 weeks,
20 ingredients, 5 suppliers, 3 internal places, and `recorded_at` passed on
every submission from §3.2's own *lag* column — a pallet note signed at the
door lands the same day, a dairy note left on the chiller shelf lands three
days later, Kingsdown's text that evening, a till receipt after a fortnight,
the waste sheet one to six days later from memory. `source` and `confidence`
come off the same table. A stated `LEARNED_BY = 2026-09-05` clamps the tail, so
nothing is recorded in the future and two runs still agree.

**The table renders names and can be used.** `render.table_html` prints a
column's `title` and, for a cell whose value names another entity, what the
operational store calls it — read through the same `_projected_options` a form
reads its dropdowns with, one query per class, keyed off the identifier the map
declares. Sorting is a link, filtering is a `<select>` per ref column, and both
live on the URL. The clock boxes became `type="date"`, and `serve._instant()`
reads a bare date as the whole of that day, so `as_of=today` includes what was
written this afternoon.

### 1 · The seed, twice from empty

`make demo-seed`, and the same numbers both runs (`diff` clean):

```
1074 intents, 9684 assertions
assertions              9736
carrying revokes        32
distinct recorded days  184
valid_from              2026-03-02 to 2026-08-30 (181 days)
recorded_at             2026-03-02 to 2026-09-07
  Ingredient 20   InternalLocation 3   Location 3   MovementKind 5
  Person 3   StockCount 6   StockCountLine 126   StockMovement 859
  Supplier 5   Unit 11
```

Against the targets: 20 ingredients (asked 20), 859 movements (asked 800),
181 days (asked ~180), 184 distinct recorded days (asked 20), 32 revoking
assertions (asked 30), 6 count sheets. Was 8 / 190 / 48 days / **1** / **0**.

### 2 · One `valid_at`, three `as_of`

`/table/IngredientOnHand?valid_at=2026-08-30`, three `as_of`:

| as_of | rows | Cocoa 22/24, Dry store, bags — Standing | Price a pack |
|---|---|---|---|
| 2026-04-15 | 119 | 15 | 41.00 |
| 2026-06-15 | 152 | 31 | 41.00 |
| 2026-09-05 | 164 | 32 | 41.00 |

Three different answers to one question about one day. The sharper pair is
either side of the price correction, same `valid_at`:

| as_of | Standing | Price a pack | What it is worth |
|---|---|---|---|
| 2026-03-10 | 7 | **4.10** | 28.70 |
| 2026-03-23 | 14 | **41.00** | 574.00 |

The world did not change between those two rows. What changed is what the log
knew about it.

### 3 · `/why` shows the withdrawal

`/why?subject=sorella:item_cocoa_22_24&predicate=sorella:item_pack_price`,
two rows, one `<tr class="gone">`:

```
4.10   valid_from 2026-03-02  recorded_at 2026-03-02  human_stated       high  Marina Devlin                        revoked by c6670548
41.00  valid_from 2026-03-02  recorded_at 2026-03-23  document_extracted high  Terra Nostra invoice, checked …      revokes 1b2669d0
```

Beside it, the other two shapes, on the same page under other subjects:

```
sea salt   11.50                          recorded 2026-03-02   revoked by 66f2169c
sea salt   retraction — carries no value  recorded 2026-04-14   revokes 4cd85d5b
pistachio  203.00  valid_from 2026-03-02  recorded 2026-03-02   (nothing)
pistachio  214.00  valid_from 2026-06-08  recorded 2026-06-08   (nothing)
```

A correction, a pure retraction, and a change. The log tells the three apart
without being asked to, which is `CLAUDE.md`'s first settled finding with data
under it for the first time.

### 4 · Names, not URIs

Scraping every `<td>` of `/table/IngredientOnHand`: **0 cells carry a URI**
(164 rows × 9 columns). Headers read
`Thing · Place · Unit · Arrived · Left · Standing · Reorder at · Price a pack ·
What it is worth`. Both came out of the map — the titles are the map's, the
names are the identifier slot of whatever class the column ranges over, read
out of the operational store.

### 5 · Sort, filter, clock

- unsorted: `Base 50 stabiliser … (blank)`; by Thing descending:
  `Whole milk, kitchen … (blank)` — reordered, blanks last either way.
- by What it is worth, descending: `13248.00, 10285.00, 9855.96`.
- 164 rows; one thing 7; one place 34; both together 2.
- the clock is two `<input type="date">`.

### 6 · `make check`, and the grep

`make check` exits 0 — **74 tests**, replay byte-identical twice
(5,334 bytes). The grep over `components/` for six business terms finds one
line: `components/interview/SKILL.md:89`, prose in a skill, in a sentence about
what an interviewer should listen for. No `.py` and no `.sql` matches.

### Surprising

**Two stale servers held port 8100 again.** Same failure as 6 Sep, same tell: a
freshly started server bound the port, curl was answered by a v1 process from
the previous session, and the first probe reported the old markup as though
nothing had changed. Windows accepts the second bind silently. It cost a whole
probe run and it is the second time; the check before believing any page is
`Get-CimInstance Win32_Process` for `serve.py`, not `curl`.

**A date is not a clock until it is the whole day.** Making the clock boxes
`type="date"` is one line, and on its own it breaks the loop: `as_of=today`
would parse as midnight, and a write made an hour ago would be invisible on the
page that had just written it. So a bare date is read as the *end* of that day,
which is what makes a date picker a usable control. Checked rather than
reasoned about: a POST to `/form/StockMovement` came back listed on the same
page at `as_of=2026-09-07`. It is a widening of what a clock means on a URL, and
in the web layer only — the compiler's CLI still reads `--as-of 2026-06-16` as
midnight.

**The whole seed runs in seven and a half seconds.** 1,074 `perform()` calls,
each its own transaction, each preceded by a full registry read — 9,736
assertions through the same write gate a form writes through. The cost that was
paid deliberately turns out not to be a cost.

**The net column sums to zero and always will.** Summing `Standing` over every
row of the balance gives exactly 0.00 at every clock, because every movement is
counted at both ends and the supplier's side is the negative of ours. It is
correct, and it makes the whole-table total useless as evidence — the row is
the unit, not the table. `OPEN.md` already carries the question of whether a
balance is scoped to internal places; this is what the absence of that scoping
looks like arithmetically.

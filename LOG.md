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

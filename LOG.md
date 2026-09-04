# Execution Log

Written **only by Claude Code**, after something has actually been run.
Desktop reads this at the start of a session and never writes to it.

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

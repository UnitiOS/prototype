# Open Questions

One line each. The discussion happens in chat and is **not stored here.**

- `[T1]` answerable by trying it, under 30 minutes. Do not debate — try.
- `[T2]` only a real user can answer. **Out of scope — it leaves, it does not
  park here.** Rotated 2026-09-05; see `DECISIONS.md`, same date.
- `[T3]` genuinely needs thought before data exists. These are few.

`blocks:` names a stage or component from `CLAUDE.md`, never a number. A line
whose `blocks:` names nothing that exists is not parked — it is dead, and it
leaves. Answered lines leave the same day they are answered; the answer's home
is `DECISIONS.md`.

Compacted 2026-09-04 from 150 items. The full text is
`history/OPEN-2026-09-04.md`.

---

## T3 — discuss to a conclusion

- The demo log was recorded in one second, so `as_of` is a cliff and not an
  axis, and it holds no `revokes` at all. Half of what `CLAUDE.md` calls the
  product — a correction as distinct from a change — has no data to be shown
  with. Missing information, not missing mechanism: `perform.py` already takes
  `recorded_at` and `resolve.py` already names the backfilled case
  · blocks: live use
- Graph traversal asymmetry: `kernel_trace_provenance` only queries `WHERE subject_id = %s`,
  missing inbound relations where an entity is `value_ref`, and `graph_get_schema` lacks
  reverse `referenced_by` slot mappings · blocks: agent traversal
- A projection renders a ref cell as its URI and a column as its slot name,
  while a form renders both by name. The map already declares five identifier
  slots and carries no `title` on any of its 51 · blocks: generation
- The demo seed spans 13 July to 30 August 2026, so a clock before it renders
  an empty table saying only "No rows at these clocks". 16 June, the date
  milestone one names and this repository types by habit, is one of them
  · blocks: live use
- A form's `subject` is required and is not minted when left blank, while the
  field's own help text says one is. An empty subject returns 200 and writes
  nothing · blocks: generation
- A form's dropdown options are read from the kernel by `generate._options`,
  which is a read path from a form to `assertion` — the one `CLAUDE.md`
  forbids. Closing it needs a projection for every class a ref field ranges
  over, and only two classes have one. Knowingly left open 6 Sep so the
  interface can be built. The demo map ranges its ref fields over four classes,
  so a projection for each is cheap — demo item one may close this rather than
  expose it · blocks: generation
- Constraint is the one kind of rule with no mechanism: computation and
  parameter both execute, and what a map writes to say what is refused has
  never been asked · blocks: generation
- Whether `required: true` is enforced by the write gate, refused by the
  generator, or a documentation-only marker · blocks: generation
- Whether a ref field may mint at all, and whether `submit()` writes the class
  its own form came from · blocks: generation
- What a movement with no stated quantity means when summed, and whether a
  derived total can say what it left out · blocks: report
- Whether a confidence is a slot on the count line, an enum, or the kernel's
  `confidence` column reached through a form field · blocks: live use
- Whether a multivalued slot is refused at the map, or (subject, predicate)
  stops being the unit of supersession, or a collection gets its own subject
  · blocks: recording
- Whether a document's date slot is how a form sets `valid_from`, or a fact
  standing beside it. Answered 10 Sep: `serve.py` synchronizes `valid_from` with the
  active `valid_at` browsing clock when submitting via forms or `/correct`, so
  backdated entries immediately appear in the temporal projection being inspected.
- Whether a correction carried on a different document is a retraction, an
  independent assertion, or a relation the map must state · blocks: kernel
- One log holds two businesses and cannot say which: `ontology_version` is
  unique only within a store nothing in the log names · blocks: report
- Whether a balance is scoped to internal places, or an outside place is marked
  as one, or a reader simply ignores those rows · blocks: report · answered 9 Sep:
  scoped to internal places via `where: {movement_into: {is_a: InternalLocation}}`
- Whether an empty picker and an unfillable class can be told apart in a
  rendered form · blocks: generation
- Whether a movement carries a clock time, or `happened_on` becomes a datetime
  · blocks: generation
- Where a pack-to-pack conversion factor lives — asked of the business,
  decomposed in the map, or a balance only ever in the counted unit. A fourth
  answer was probed 6 Sep and works with no code change: the balance is *per
  unit*, `movement_unit` in the aggregate's `by`. That leaves only the case
  where two units of one item must be added, which the business itself does not
  do · blocks: generation
- Revocation does not cascade, and nothing ties `revokes` to the same
  (subject, predicate) · blocks: kernel
- Two concurrent writers at the write gate: stock can go negative under READ
  COMMITTED, and a slow transaction leaks into the past · blocks: live use
- Whether the diff attributes a difference to the individual rule that moved,
  or data-vs-definition decomposition is enough · blocks: report
- A movement may name no place at one end, and the seed now holds one:
  whether a group under no location is a row of the balance, is dropped, or
  is named · blocks: generation · answered 9 Sep: dropped by the scope filter join
- An `aggregate` cannot say which rows a balance counts, so `p_gelato_on_hand`
  and `p_ingredient_on_hand` are numerically identical and one of them is about
  nothing. Diagnosed as a missing mechanism 5 Sep, `DECISIONS.md` same date;
  answered 9 Sep: the `where` block with `is_a` constraints provides this mechanism
- A rule the business states about a class is recorded on one row: "minimum
  flavours in a cabinet, 12" sits on `loc_cotham_cabinet` alone and Gloucester
  Road's carries nothing. Assert it per cabinet, give the map a class the rule
  can be scoped to, or a class-scoped parameter is new mechanism
  · blocks: generation
- `authority` is free text and joins to nothing. Three spellings stand in one
  column — "Dan Farrugia", "Marina", "Terra Nostra Ingredients" — while the log
  holds `sorella:person_marina_devlin`. It may be right: "the HACCP plan" is
  neither a Person nor a Supplier · blocks: kernel
- Master data carries `valid_from` of the adoption date, and for most facts
  that is not when they became true — 1,333 of 1,700 v1 assertions share
  2026-06-15. It shadows better-dated facts written later, and every question
  asked before that date returns almost nothing · blocks: report
- The other two constructs with no home — F refusal (no sorbet in a cake,
  minimum order 4 pans) and H schedule (van runs Tue/Thu/Sat May to September).
  Parked until something demands one; G conversion has its own line above
  · blocks: generation

## T1 — just try it

- The compiler reads `equals_expression` as arithmetic over `{slot}` names and
  refuses anything else, while LinkML's own is a fuller language. Write one the
  map needs and this refuses · blocks: generation
- Two aggregates on one class must group by the same set or the compiler
  refuses. Write a class where they should not and see what a row of it is
  · blocks: generation
- `gen-doc` renders from LinkML directly rather than through OWL, so the 122
  descriptions and the cardinalities should survive where they do not now.
  Render v1 and compare against `build/sorella/v1/graph/sorella-v1.html`
  · blocks: graph review
- `seal` stringifies values with `str()`: a boolean lands as `True` and a price
  of `4.20` as `4.2` · blocks: generation
- Two slots sharing one `slot_uri` with different ranges — the first declaration
  decides and nothing guards it · blocks: -
- `make schema` applies `001_schema.sql` to `uniti_check` only, so the working
  log is never migrated and the two match by history alone · blocks: -
- `pytest tests/generator` run directly writes into the working log: the default
  DSN is `uniti` and only `make check` points at `uniti_check` · blocks: -
- `seal --into` defaults to `business/`, now empty — a bare run mints a stray
  `business/v1.yaml` beside `sorella/`. Created 4 Sep retiring Marlow
  · blocks: generation
- `business/trial/` is a live fixture: `tests/trial/test_linkml_features.py` and
  three scripts read it. Move it into `tests/`, or leave it · blocks: -
- What serves the HTML — `http.server`, Flask, or FastAPI. Write the smallest
  thing that renders one form and takes one POST; the dependency itself is
  Fareza's under CLAUDE.md · blocks: generation
- The flat-annotations guard sits in `seal`, so a version file `seal` did not
  write still resolves to the wrong version silently · blocks: -
- A transcript is copied beside its version rather than moved, so one stale
  `draft.txt` can be sealed under two versions · blocks: -

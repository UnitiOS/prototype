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
  standing beside it · blocks: recording
- Whether a correction carried on a different document is a retraction, an
  independent assertion, or a relation the map must state · blocks: kernel
- One log holds two businesses and cannot say which: `ontology_version` is
  unique only within a store nothing in the log names · blocks: report
- Whether a balance is scoped to internal places, or an outside place is marked
  as one, or a reader simply ignores those rows · blocks: report
- Whether an empty picker and an unfillable class can be told apart in a
  rendered form · blocks: generation
- Gelato in a pan has no name in the map, and milestone one's closing balance
  runs through it · blocks: generation
- Whether a movement carries a clock time, or `happened_on` becomes a datetime
  · blocks: generation
- Where a pack-to-pack conversion factor lives — asked of the business,
  decomposed in the map, or a balance only ever in the counted unit
  · blocks: generation
- Revocation does not cascade, and nothing ties `revokes` to the same
  (subject, predicate) · blocks: kernel
- Two concurrent writers at the write gate: stock can go negative under READ
  COMMITTED, and a slow transaction leaks into the past · blocks: live use
- Whether the diff attributes a difference to the individual rule that moved,
  or data-vs-definition decomposition is enough · blocks: report
- A movement may name no place at one end, and the seed now holds one:
  whether a group under no location is a row of the balance, is dropped, or
  is named · blocks: generation
- The same emptiness on a classifying dimension is worse than on a place: a
  movement with no flavour and no format is a row of `p_gelato_on_hand` keyed
  on nothing, so every digestive movement is in the gelato balance
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

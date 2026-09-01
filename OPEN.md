# Open Questions

One line each. The discussion happens in chat and is **not stored here.**

- `[T1]` answerable by trying it, under 30 minutes. Do not debate — try.
- `[T2]` only a real user can answer. Written down, waited on, not argued about.
- `[T3]` genuinely needs thought before data exists. These are few.

The `blocks:` field names a stage or a component, never a number, and decides
whether the line may hold up this week's work. `blocks: -` means it may not.

---

## T3 — discuss to a conclusion

- Valid-time model for the ontology — closed 26 Aug. Left as a line only so the
  seal tool is written against the decisions, not re-derived · blocks: -
- Does the diff attribute a difference to the individual rule that moved, or is
  data-vs-definition decomposition enough for the PoC · blocks: report + diff
- The shape of a derived rule inside `annotations` — SQL, a narrow declarative
  aggregate, or both with a sentence. The 26 Aug deferral expired 29 Aug: the
  map is hand-authored, so a real stated rule now comes from there. This is the
  next thing to settle. No longer blocks the map: v1 carries no derived rule
  (29 Aug), and the first generator item reads a rule-free v1 · blocks: generator
- Does graph review need competency questions written by someone other than the
  ontology's author, plus one deliberately wrong concept — now that "every
  predicate in the log exists in the ontology" is a query · blocks: graph review
- Where the record-time spread the replay demo needs comes from, given that one
  interview commits at a single recorded_at — answered 27 Aug: dated role-play
  episodes, each sealed at its own instant. Left as a line only until an episode
  has actually been run that way · blocks: -
- What writes a fact correction — answered 29 Aug: the episode runner is a
  second writer into the kernel, so a correction is an ordinary episode and no
  longer bumps the ontology version. Left as a line only until one has actually
  been replayed that way · blocks: -
- Does `report` come before `generator`, now that the spread comes from episodes
  rather than live use — the generator shows the system can be used, the report
  shows it is better. Sharpened 29 Aug: with the interview deferred, this is the
  only remaining ordering question in the lap · blocks: report
- `seal` never writes a `value_ref`. `perform()` takes one, but `_facts()`
  str()s every value, so a stated relationship lands as a literal that merely
  looks like a URI — confirmed 28 Aug: every assertion from a seal has
  value_ref null, including ones whose value names an entity. The map declares
  `range: Freezer`; the log cannot honour it, so the graph has nodes and no
  edges. A draft could say which is which, or `seal` could read the slot's
  `range` from the map — a class means a ref, a type means a literal — which
  needs no new key and puts the logic where the logic lives. Decided 29 Aug:
  the range rule, shared by `seal` and the runner. The hand-authored draft
  states no facts, so the runner is where it must land first; `seal`'s own
  fact path is unused for this PoC · blocks: episodes
- Operational definition of "the kernel recorded it correctly" — every screen
  state reproducible from the log alone at some (valid_at, as_of)? · blocks:
  live use
- Isolation of two concurrent writers at the write gate; stock can go negative
  under READ COMMITTED · blocks: live use
- Commit order vs seq/recorded_at; audit mode leaks when a slow transaction
  inserts into the past · blocks: definition change
- Does revocation cascade? Revoking a retraction does not resurface its target
  — NOT EXISTS never asks whether the revoker is itself revoked · blocks: -
- Nothing ties `revokes` to the same (subject, predicate); a row about Bob can
  silently remove a standing fact about Alice · blocks: -
- Nothing says an entity is a Material. The map declares classes and slots, the
  log holds (subject, predicate, value), and CLAUDE.md's third closed finding
  says class membership is an assertion — but v1 states none, so a generator has
  to guess which entities are a class's rows. Its rule is the only one the two
  files support: a row is a subject of one of that table's own columns. An
  inherited slot breaks it in the open — `stock_location` is a column of both
  Material and Pan, so the generated Pan table holds nineteen materials with
  every pan column blank. Whether membership is a fact the interview must state,
  a rule read off the identifier slot, or a filter only the projection applies,
  is undecided. Found 31 Aug generating the first two tables · blocks: generation
- `required: true` reaches a generated form as a label and stops nothing. The
  map says `material_name` is required, the form prints "required", and the
  submit path writes whatever it is handed; the kernel has no opinion, because
  no constraint compares a fact against the map. Refusing the entry is a
  judgement made at write time, which is the one thing the log is not supposed
  to make, so it is not obvious the form should refuse either. Whether required
  lives in the form, in a generated table's constraints, or only in the report
  that says what is missing, is undecided · blocks: live use
- The generator's scope and capabilities are written down nowhere, and the graph
  structure cannot be judged until they are. The map exists to satisfy its
  readers and the generator is the first one, so "is this map good" has no
  referent while what the generator must produce is unstated — every argument
  about typing or enforcement is then an argument about a target nobody has
  named. Raised 1 Sep · blocks: generator
- Which milestone owns the shrinkage report. The 24 Aug definition of done is
  staged rather than dropped and is not milestone one; whether a definition
  change belongs to refinement or to analysis is undecided, and it decides
  whether the map must carry two versions before any analysis exists · blocks: -
- Nothing types a cell between the log and LinkML's evaluator, so a computed
  value can be silently wrong. `assertion.value_literal` is text, the generator
  hands the row over as text, and `eval_expr` dispatches on Python types: the
  trial map's `{left_amount} + {right_amount}` returns `'34'` for 3 + 4 and
  `'102'` for 10 + 2, with no exception and a perfectly good `str`. Casting each
  cell to the `range` the map already declares gives 7 and 12, so the
  information is there and nobody applies it. Whether the caster is the
  generator's `table()`, the kernel's read, or the expression evaluation itself
  is undecided — and the same question decides what a form's typed field writes
  back. Adjacent: `infer_all_slot_values`, the documented entry point, walks a
  row that is not a `YAMLRoot` and changes nothing without erroring. Found 1 Sep
  in the LinkML feature trial · blocks: generator
- The declared aggregate now has a shape that runs end to end, so the shape line
  above has evidence instead of options: `over`, `sum` and a named `by` mapping,
  read off the induced slot of a sealed map, summed over rows the generator
  assembled at both clocks. What is not settled is the spelling. LinkML refuses
  a mapping placed directly under an annotation tag — `TypeError:
  Annotation.__init__() got an unexpected keyword argument 'over'` — and accepts
  three alternatives that are not equivalent: under `value:` (structure intact,
  what trial2 used), under a nested `annotations:` (two levels deeper, one
  `Annotation` per key), or as flat tags (`aggregate_over:`, structure gone).
  Whether `derive` reads an annotation at all or reads SQL is still the
  question; the trial shows only that a narrow declarative aggregate is enough
  for one number. Found 2 Sep · blocks: derive
- A seal that changes no definition still mints a version. A fact recorded later
  than the rest can only be stated *through the map* by a second seal, because
  `seal` writes one `recorded_at` per intent — so trial2's v2 exists, supersedes
  v1, and is byte-identical to it apart from its own annotations.
  `resolve_version` hands every later reader v2, and nothing in the sealed store
  distinguishes a version that moved a definition from one that only added
  facts, which is the exact distinction the report exists to make. The 29 Aug
  answer — episodes are the second writer into the kernel — removes the need for
  most such seals but not for a fact that belongs to the map itself. Found 2 Sep
  · blocks: report

## T2 — wait for a user

- Are LLMs good interviewers and bad authors? The old corpus concluded this from
  a simulation, never from a real session with a real person. Now load-bearing:
  the chatbot is the only writer of the ontology and so the only path to a
  definition change. Sharpened 27 Aug — this PoC is also simulation, so the
  question stays open by construction. A role-player never rambles, never
  contradicts themselves unnoticed, and never has tacit knowledge they cannot
  articulate. Either the brief carries that mess or nothing does. Deferred
  29 Aug: there is no interview at all in this PoC, so this is not merely open
  by construction — it is untouched, and the interview stage is where it gets
  asked · blocks: -
- Can a person dictate a precise ontology change and have the chatbot execute it
  mechanically, keeping LLM authoring off the critical path · blocks: -
- What must already work before the first ontology is written · blocks: -
- Can business people author an ontology, or only its structure · blocks: -
- Do two people describing the same business produce similar ontologies · blocks: -

## T1 — just try it

- value_literal: jsonb or text · blocks: -
- subject_key_id: came in from the archived spec, used nowhere, meaning
  unknown · blocks: -
- carry intent.channel or not · blocks: -
- final `source` vocabulary · blocks: -
- Ontology storage stack: a graph database, or a versioned file plus a
  renderer — one writer and a read-only viewer remove most of what a graph
  database buys · blocks: ontology store
- Ontology serialisation: LinkML, OWL, or plain YAML — closed, LinkML. Left as
  a line only until the generator probe confirms the mechanics · blocks: -
- Inventory valuation in scope, or quantity movement only — no longer decided in
  advance: a plain interview is not steered, so whatever is said is what the map
  holds · blocks: generator
- Which stated rules become ontology structure and which become derived rules —
  a modelling choice the LLM makes and we measure, not one we settle first
  · blocks: -
- What enforces an identifier's presence — answered 27 Aug: not the SHACL.
  `gen-shacl` suppresses `minCount` on an `identifier` slot on purpose, and
  `required: true` is not an override; `key: true` emits it but no longer forms
  the instance URI. The generated DDL's `NOT NULL`/`PRIMARY KEY` enforces it,
  and the kernel's write gate enforces it for facts. A validator reading only
  the SHACL is incomplete — a trap for anyone who assumes otherwise · blocks: -
- Where the class/individual line falls in real speech — "12 flavours" splits
  cleanly into a class in the map and individuals in the log, but "Freezer A"
  and "wholesale customer" do not. Observed in the first interview, not settled
  before it · blocks: -
- Who authors an individual's URI — the chatbot inventing `uniti:freezer_a`, or
  the value of the class's identifier slot. `seal` takes whatever the draft
  says and registers it; nothing yet says where it should come from · blocks: -
- `business/` holds sealed versions naming entities the kernel no longer holds:
  `make replay` resets the log on every check, so the map store and the log
  fall out of step by design · blocks: interview
- `business/v1.yaml` and `v2.yaml` are fixture drafts sealed for real, so the
  first role-played interview lands as v3 superseding a business nobody
  described. Deeper than it looked: `test_business_holds_the_two_sealed_versions`
  reads `business/`, so the production map store is a test fixture. Queued in
  NEXT.md 28 Aug · blocks: interview
- Webapp framework for the generated forms · blocks: -
- Chatbot split into authoring and query, or merged behind one MCP · blocks: -
- Probed 27 Aug: `required: true` beside `identifier: true` emits no
  `sh:minCount` either, and `key: true` does — so what enforces an identifier's
  presence is the generated DDL's `NOT NULL`/`PRIMARY KEY`, not the SHACL,
  unless the map gives up the URI-forming slot · blocks: generator
- `make schema` applies `001_schema.sql` to `uniti_check` only, so the working
  log is never migrated and never tested. They match today by history alone;
  the next change to the schema diverges them silently, and the database that
  holds real interview evidence is the one that never sees it · blocks: -
- `make` now owns a throwaway database, `uniti_check`, and every target points
  at it - so nothing reseeds the working log except running `scripts/seed_200.py`
  by hand, which still drops and recreates whatever `UNITI_DSN` names. A sealed
  episode is one careless run of that script from gone · blocks: -
- The flat-annotations guard sits in `seal`, on what is carried into a sealed
  file, not in `components/ontology/resolve.py`. Any version file `seal` did not
  write — hand-edited, or made by another tool — still leaks a nested
  `valid_from` upward and resolves to the wrong version silently · blocks: -
- A nested annotation is refused in two voices: LinkML's own metamodel raises
  `TypeError: Annotation.__init__() got an unexpected keyword argument` for a
  mapping with arbitrary keys, so only the shape LinkML accepts (`value` plus a
  nested `annotations`) reaches the guard. Both exit non-zero having written
  nothing, but the two messages tell a different story about why · blocks: -
- The transcript is copied beside its version, not moved, so nothing stops one
  stale `draft.txt` being sealed under two versions — evidence for the wrong
  session, and no error. Moving it would refuse the second seal, at the cost of
  a fixture that deletes itself when a test runs · blocks: interview
- `business/v1.yaml` and `v2.yaml` name no transcript: they were sealed before
  the contract existed, so the map store holds two versions today's `seal` would
  refuse. The line above about clearing them covers it · blocks: -
- Migrating the working log and destroying it are the same command. Emptying it
  on 28 Aug was done by re-applying `001_schema.sql` to the default DSN, which
  is still the only thing that has ever migrated that database — and it opens
  with three `DROP TABLE`s. Softened 29 Aug rather than fixed: once the whole
  log replays from episode files, destruction is recoverable and a schema change
  · blocks: kernel recording — softened only while every fact there came from a file
- The two databases have not actually diverged: before the 28 Aug wipe, the
  working log's indexes, check constraints, foreign keys and deny triggers
  matched `uniti_check` exactly. They match by history alone, so the wipe
  proved nothing about the divergence the `make schema` line above warns of
  · blocks: -
- `business/` is now empty and held open by a `.gitkeep`: git does not track an
  empty directory, and both `seal`'s default `--into` and the interview skill
  write into it by path. First real seal makes the placeholder redundant
  · blocks: -
- Replaying an episode file twice appends it twice. `perform()` has no
  idempotency and the kernel forbids delete, so a deterministic re-run means
  dropping the tables first. Does the runner refuse a non-empty log, or is that
  the caller's problem · blocks: episodes
- Where episode files live, and their exact shape. Sketched 29 Aug: one act per
  entry with `recorded_at`, `action_name`, and facts carrying a local `key` for
  a later `revokes` to name · blocks: episodes
- How many acts per data set — guess is 1 for onboarding, 30-40 for three
  months, ~150 for a year. Enough spread to be real, few enough to read by hand
  when a number looks wrong · blocks: episodes
- What the runner does when `resolve_version` returns None for an act's clocks —
  an act dated before the map's first `sealed_at` has no version to name
  · blocks: episodes
- Where the frozen competency questions live. Not a design document and not a
  root `.md`: proposed `episodes/questions.md`, data beside the data it guards
  · blocks: episodes
- Whether a hand-authored map needs `gen-erdiagram` to be readable at all before
  it is sealed, or whether the graph render stays a graph-review concern
  · blocks: -
- Does the restatement report — every number that moved since the last close,
  split into data, correction and definition — belong in `report` or is it the
  same harness seen from a different angle · blocks: report + diff
- `confidence` has three levels and has never been used by any writer. Curated
  data needs at least one low-confidence fact for a number to carry what it is
  made of — answered 30 Aug: `seal` takes it as an optional fact key, and §13's
  six estimated quantities are the first use any writer has made of the column
  · blocks: -
- Two competing counts of the same thing at the same valid_at, neither revoking
  the other — the read rule breaks the tie on record time and returns one. Is
  that right for a disputed number, or does the reader need to see both
  · blocks: report + diff
- Two slots sharing one `slot_uri` but declaring different ranges — one class,
  one type. `seal` lets the first declaration decide and writes every fact under
  that predicate the same way; found 29 Aug writing `value_ref`, not guarded,
  because a rename keeping its `slot_uri` is the case that made sharing legal
  and no draft has yet disagreed about the range · blocks: -
- A slot whose ranges are all classes but stated as `any_of` reads as a literal.
  `induced_slot` leaves `range` at `default_range` and puts the classes under
  `any_of`, so `seal`'s class test sees `string` and the fact lands in the wrong
  column silently. Profile §6 has one such relationship — "Stock count counted
  Material or Pan" — so the map either gives those two a common superclass or
  `seal` learns to read `any_of` — answered 30 Aug: the map gives the two a
  common superclass and `seal` is not taught `any_of`, so a draft written that
  way is still silently wrong and nothing guards it · blocks: -
- Location is folded into the pan slot names in v1, so "how much vanilla is in
  the shop" is a sum the reader assembles rather than a slot it reads. Accepted
  30 Aug as the untidiness an interview would have produced, and named here
  because it is also the candidate definition change with a real blast radius
  for v2 · blocks: -
- `gen-owl` renders a draft's whole `annotations.facts` block as one string
  literal on the ontology node — 12,176 characters, a quarter of the TTL, for
  the 127-fact v1 draft. Found 30 Aug rendering the draft. It vanishes on seal,
  because `seal` strips `facts`, so it is a property of looking at a draft and
  not of looking at a version; anyone opening a draft in Protege or WebVOWL
  sees the log inside the map · blocks: -
- `gen-erdiagram` flattens `is_a`: each subclass repeats its parent's
  relationships rather than inheriting an edge. The v1 draft's five movement
  subclasses turn six parent relationships into thirty, so twenty of the
  thirty-two edges are repetition. The 29 Aug decision makes this render the
  diffable working view, so a v2 change to a parent shows up once per child
  · blocks: graph review
- Slot-level `unit` metadata does not reach `gen-owl` at all: no `ucum_code`,
  no symbol, no triple. The 30 Aug decision puts a fixed unit on the slot and a
  varying one in a `value_ref`, and only the second half of that survives a
  generator so far · blocks: generator
- WebVOWL cannot see the shape it is there to check. `gen-owl` writes no
  `rdfs:domain` at all — a slot's domain becomes an `owl:Restriction` inside
  each class, 135 of them in the v1 draft — and VOWL draws a property as an edge
  only when it carries both a domain and a range. So all 16 relationships render
  out of a generic node and the only class-to-class edges left are the 7
  `subClassOf` links. The 29 Aug line names WebVOWL the shape check and warns it
  validates nothing; the sharper problem is the inverse of the one that line
  feared, a picture that looks poorer than the map is. Found 30 Aug by counting
  the triples behind a picture that looked wrong. LinkML's own `gen-doc` and
  `gen-mermaid-class-diagram` draw both inheritance and associations
  · blocks: graph review
- `seal` stringifies a fact's value with `str()`, so the draft's first boolean
  reaches `value_literal` as `True` rather than `true`, and a scoop price
  written `4.20` reaches it as `4.2`. The map declares `range: boolean` and
  `range: decimal` and the draft states a boolean and a decimal, so what is
  Python's spelling here is the tool's, not the map's. Found 30 Aug adding the
  sixteen `flavour_in_rotation` facts, the first booleans and the first money in
  the PoC · blocks: generator
- `gen-owl` dies on the map's own data under Windows' default console codec.
  §8's temperatures use U+2212 MINUS SIGN, the draft copies them faithfully, and
  Python encodes stdout as cp1252 when it is redirected, so the render exits 1
  leaving a zero-byte file, with the `UnicodeEncodeError` buried under two
  screens of deprecation warnings. `PYTHONIOENCODING=utf-8` fixes it. Not fixed
  by normalising the character: §8 writes it that way and the map copies what
  the business said. The sharper half is that `make check` never runs `gen-owl`,
  so the repo's own check cannot see this, and it could not have appeared before
  30 Aug because `location_temperature` had no facts until then. Found by
  auditing a session whose own check passed · blocks: graph review
- The recipe is never stated, so material stock can only ever rise. §3 names six
  ingredients for a 25-litre base mix and gives no quantity for any of them, and
  §6 omits the Base-to-Material relationship altogether even though §3's prose
  states it. `GoodsReceived` adds and `StockCount` counts; nothing consumes. An
  inventory module for a business that manufactures needs a bill of materials,
  and this one has none — not because the map dropped it but because the shop
  never said it. Whether v2 states a recipe, or records consumption per batch,
  or leaves the dead end visible as the honest answer, is undecided
  · blocks: generator
- Eggs sit in §8's chiller and nowhere else. Not in §13's count, not in §3's
  base, not a material in the map. Either the profile slipped or Marta genuinely
  never counted them; the second reading is the more useful one and matches §12's
  temper, but nobody has said so · blocks: -
- Each of §10's six rules is now in the map twice: as a `Policy` fact carrying
  the sentence and its threshold, and as the `stated_rule` annotation on the slot
  the rule is about, which has been there since the first draft. The annotation
  says something the fact does not — which slot the rule is about — but it also
  carries the number, so it is stale the first time Marta moves a threshold, and
  a sealed version cannot be corrected without a v2. Either the annotation drops
  the sentence and keeps the pointer, or it goes. Found 31 Aug giving §10 a home
  in the log while leaving the map's copy where it was · blocks: -
- A multivalued slot has no story in the kernel. `base_ingredients` is the first
  one and it is empty, so nothing breaks yet. But an assertion is one subject,
  one predicate, one value, and supersession works on that pair — so six
  ingredients on one base would be six assertions competing for the same pair,
  and the sixth would most likely retire the other five rather than join them.
  Either multivalued slots are refused at the map, or the pair stops being the
  unit of supersession, or a collection gets its own subject. Found 31 Aug while
  checking the draft for duplicate pairs before sealing · blocks: episodes
- `Unit` now holds litre, kg, piece, day, week and percent. The last three came
  from §10's thresholds and the business does utter them, so nothing was
  invented, but `material_unit` and `policy_unit` now share one class across two
  uses that never overlap. A generated dropdown for a material's unit will offer
  "week". Whether that wants two classes, a subset, or nothing at all is
  undecided · blocks: generator
- Nothing answers for an instant before the map's own `valid_from`. v1 is sealed
  at 21:00 on 31 August and takes effect at midnight, so for three hours
  `resolve_version` returns None and `resolve_single` returns None for every one
  of the 194 facts — the shop has just counted its stock, `seal` has written all
  301 rows, and both readers say nothing about either the stock or the
  vocabulary that describes it. Harmless while nothing happened before 1
  September, but a report takes a period and a correction can be backdated below
  the first version. Whether a `valid_at` under the earliest `valid_from` returns
  nothing, falls back to the earliest version, or is refused is undecided — the
  27 Aug item settled the same question on the `as_of` axis only. Found 31 Aug
  reading v1 back after the seal · blocks: report
- Each of §10's six rules sits in v1 twice, and v1 is sealed. Once as a `Policy`
  fact in the log, once as a `stated_rule` annotation on a slot where it has sat
  since the first draft. The 31 Aug item added the second home without removing
  the first, because the clause written here never mentioned an annotation
  nobody had noticed. The wordings already differ — Marta's "Stock should never
  go below zero. If it does, something was recorded wrong" against the
  annotation's run-on paraphrase — while the numbers still agree, so nothing
  contradicts today. The first time Marta moves a threshold the log supersedes
  and the sealed annotation cannot, and the map will answer a question the log
  answers differently. Directly against the 30 Aug line on where a number lives.
  This is the first thing v2 carries · blocks: -
- One `valid_from` serves both the version and its facts, so the map is not
  valid until the balances are. `annotations.valid_from` is 1 September and the
  seal instant is 21:00 on 31 August, so in between `resolve_version` returns no
  version and `resolve_single` returns nothing: for three hours the shop has
  counted its stock, 301 rows are written, and the log answers nothing about
  either the stock or the map that describes it. The facts genuinely do not
  apply until the morning and that half is right. Whether a map's own
  `valid_from` should instead be its seal instant, so the words mean something
  from the moment they are sealed, is undecided · blocks: episodes
- How a movement class declares its direction — a slot on the class, an
  annotation on the class, or a sign read off which location slot is filled.
  Nothing in v1 says `GoodsReceived` adds and `ThrownOut` subtracts, and no
  balance can be computed without it. Raised 1 Sep · blocks: generator
- `received_from` is a field the form offers and the log can never fill. It is
  the only picker in the eight document forms with zero options: v1 states no
  supplier individual, §5's four suppliers never became facts, and none of the
  eight forms creates a Supplier, so nothing will ever mint one for the options
  rule to find. `submit()` would mint a supplier URI typed on the command line,
  which means the field is reachable from the CLI and unreachable from the form
  it belongs to. The same form's `movement_out_of` offers only the five internal
  locations, so a delivery's origin has no correct answer either: the outside of
  the business is unrepresentable twice in one document. Found 1 Sep rendering
  the eight forms · blocks: generator
- A pan movement cannot name a pan. `movement_of` ranges over `StockItem` and
  the picker offers nineteen materials in all five movement forms, because no
  Pan entity has ever been minted and the options rule can only offer entities
  the log already holds. `count_of` on StockCount is the same nineteen, so the
  stock count cannot count a pan. Whether pans are minted by a Pan form, by the
  seal, or by the first `MixBatch` that fills one, is undecided — and until one
  of those happens `PanMoved` and `PanPulled` are forms about a thing that does
  not exist. Found 1 Sep · blocks: generator
- `PanMoved`, `PanPulled`, `ThrownOut` and `TastingGiven` render byte-identical
  apart from the class name in the header: same six fields, same four pickers,
  same options. All four are `StockMovement` with nothing added, so filling one
  and filling another writes the same facts, and the only trace of which
  document was used is `intent.action_name`, which `submit()` writes as
  `submit_<Class>`. Whether that is enough — the class lives on the intent and
  never on the assertions — or whether a movement's kind has to be a fact,
  is undecided. Adjacent to the 1 Sep direction line but not the same question:
  that one asks which way the number moves, this one asks whether the log can
  say which of four documents was filled in. Found 1 Sep · blocks: generator
- `required` renders and enforces nothing. The form marks `count_location` and
  `count_taken_on` required from the map, and `submit()` rejects only an unknown
  field name and an empty submission, so a StockCount carrying `count_quantity`
  alone would be written. The 30 Aug T1 already found `gen-shacl` emits no
  `minCount` beside an identifier; this is the second place `required` means
  nothing, and the first where a user is being shown the word. Whether the write
  gate enforces it, the generator refuses the submission, or `required` is a
  documentation-only marker in this PoC, is undecided. Found 1 Sep reading
  `submit()` after rendering the forms · blocks: generator
- Whether a ref field may mint at all. `submit()` today mints any URI it has not
  seen, including one typed into a ref field, so a supplier misspelled once
  becomes a second supplier silently. An ERP refuses this — a receipt picks a
  supplier from a list and cannot invent one — and if master data enters through
  its own form there is no reason for a document form to create anything but its
  own subject. Recommended at this desk, not yet decided. Raised 1 Sep ·
  blocks: generator
- What a movement with no stated quantity means when it is summed. Zero, or
  unknown, or an error. Treating it as zero makes a total quietly wrong in the
  same way `'34'` was quietly wrong; treating it as an error makes a real
  business — where three of nine movements go unrecorded — unable to see any
  balance at all. This is not a mechanism question and cannot be settled at this
  desk: it is a statement the business profile has to make, so it joins what
  profile v2 must state. Raised 1 Sep · blocks: derive
- `designates_type` can carry class membership, and reading it repairs the
  generator's row rule. Measured in trial2: the generator offered 8 candidate
  rows for Movement and the log states that 4 of them are one — in a map with no
  inheritance at all, because `entity_class` is a column of Movement, Thing and
  Place alike, so every entity in the map is a candidate row of every table.
  Three lines in a throwaway script filtered it. That is one of the three
  options the 31 Aug row-rule line left undecided, tried rather than argued;
  where the filter belongs — `columns()`, `table()`, or a per-class rule in the
  map — is untried, and so is whether the interview can be relied on to state
  membership for every entity it names. Found 2 Sep · blocks: generation
- A derived total has nowhere to say what it left out. `out_total` printed 4 and
  then 7 for a pair whose group also held a movement stating no quantity, and
  `0` for a pair holding no movement at all; all four are the same kind of cell,
  and only the breakdown printed beside the table tells them apart. This is not
  the 1 Sep line about what a missing quantity *means* — even once that is
  settled, one decimal has no room to carry it, and a shrinkage number that
  quietly excludes three of nine movements is the exact failure the report
  exists to expose. Whether a derived slot needs a companion count, a
  confidence, or a refusal to compute, is undecided. Found 2 Sep · blocks: derive
- Claim F is stated twice in `DECISIONS.md`, at 1150 and 1179, written hours
  apart by two sessions that could not see each other. The two wordings agree.
  Neither is removed because the file is append-only; a reader should know one
  claim is meant, not two. Raised 2 Sep · blocks: -
- Sorella's Tuesday has 4.8 kg of strawberries unaccounted for: fourteen punnets
  in, one binned mouldy, 2.6 used by the sorbet batch, and eight counted where
  10.4 were expected. Nothing in the profile says whether that is deliberate
  shrinkage or an arithmetic slip, and an unmarked discrepancy cannot be told
  apart from a mistake. Raised 2 Sep · blocks: -

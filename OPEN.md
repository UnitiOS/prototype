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
- Twenty-two of the fifty-five movements in Sorella's `§3.2` produce no document
  of any kind, and two more produce only a text message or a card receipt. If the
  system holds only what a document witnessed it cannot hold two fifths of the
  ways stock moves; if it holds them anyway, somebody types an event no paper
  saw, and the two clocks have nothing to separate. Which of the two a generated
  form is for is untried, and it is not the same question as what a missing
  quantity means. Raised 2 Sep · blocks: generation
- The van sheet and the wholesale delivery notes are filled at loading or at the
  first drop from memory, so the paper predates the movement. Every other
  document in Sorella has a lag of nought to six days; these two have a negative
  one, and they are what the whole wholesale side rests on. Whether a document
  recording a movement that has not happened yet is a fact with `valid_from`
  after `recorded_at`, an intent, or a forecast the log should refuse, is
  undecided. Raised 2 Sep · blocks: live use
- The only goods-in document in Sorella is the supplier's own, in nine shapes, of
  which two are not documents — a text message and a till receipt. Whether the
  map carries one goods-in class the nine collapse into, or whether the shape of
  the paper is part of what the log records, is untried. It matters because the
  quantity received is on the supplier's paper and nowhere else, so the only
  witness to a receipt is a party outside the business. Raised 2 Sep · blocks: generation
- Three things in Sorella move through places `§1.3` does not name: Aoife's car,
  which carries the shop-to-shop transfer and the cash and carry run; Gloucester
  Road's drinks fridge; and the sink at Cotham Hill, which takes more milk than
  anything but the machine. The 1 Sep line models the outside of the business as
  locations so direction comes free — a destination nobody would call a place is
  the same problem one level in. Raised 2 Sep · blocks: interview
- The two Cotham back freezers are two places in `§1.3` and one place to the
  business: no document has ever named which of them a pan is in. A map that
  carries both will carry a location nothing can ever distinguish, and a map that
  merges them contradicts a profile written from the building. Raised 2 Sep · blocks: generation
- Sorella's free-delivery rule names a threshold of £120 and no consequence, and
  nobody in the business can say what is charged below it. The 21 Aug and 1 Sep
  lines make a constraint a derived boolean producing a violation list; this is a
  threshold whose violation has no action attached, which is a shape the four
  target rules do not cover. Raised 2 Sep · blocks: derive
- Nine numbers in Sorella's `§3.5` are each computed two ways by two people in
  the building, both in use, neither wrong — litres produced, a pan, waste,
  debtor days, the year-on-year comparison, labour percentage, the wholesale
  share, the cost of a pistachio pan, and how many specials ran. Whether a
  contested number is one derived slot whose definition moves, or two named slots
  that disagree, is the definition-change stage's material arriving early, and it
  is undecided. Raised 2 Sep · blocks: definition change
- A count line in Sorella's opening count carries a confidence — weighed,
  counted, eyeballed, or not counted — and the kernel has nowhere to put one.
  `assertion`'s column list is closed and a confidence is not a business need in
  the `ontology` sense either: it is a property of how a fact came to be known,
  not of what the fact says. Whether it is a second assertion about the first, a
  slot on the count class in the map, or something the log must refuse, is
  undecided, and 152 of the profile's own count lines carry one. Raised 3 Sep ·
  blocks: recording
- An absent count line is evidence and cannot be told from an unlooked-for one.
  Sorella's count sheet is blank ruled paper with no printed list of what should
  be there, so a flavour that has run out simply has no row: the frozen-purée
  strawberry sorbet is at nought on Tuesday night and Dan wrote nothing, while
  coconut and basil were written and struck through, which is a different fact
  arrived at by accident. A generated count form has a list and will therefore
  record an absence the paper one could not, which changes what the count means
  rather than digitising it. Raised 3 Sep · blocks: generation
- Two pans went to wholesale accounts on Tuesday having sat in the van since
  Saturday midday, and nothing on the delivery note, the label or the van sheet
  distinguishes them from a pan that left the holding freezer that morning. The
  14-day pan best-before reads the freeze date, which is unaffected. So a thing's
  location history is the evidence and the thing carries none of it; whether the
  log answers "where has this been" by walking movements or whether a movement
  must name the thing rather than the flavour is the row-identity question
  arriving from the business side. Raised 3 Sep · blocks: live use
- The one rule that moved after Sorella's adoption date was written in the corner
  of a cabinet-plan sheet at one shop and nowhere else. The definition-change
  stage assumes a definition change is authored into the map; here the business's
  own record of it is a scribble one person can read, and the person who executes
  the rule was never told either number. Whether the map is where a rule change
  becomes visible or only where it becomes computable is untried, and it decides
  what the replay is a replay of. Raised 3 Sep · blocks: definition change

- `price_at` is a string naming one of `§1.7`'s three price columns, and two of
  the three are shops that are also `InternalLocation` rows while the third,
  wholesale, is not a place at all and never can be — the price is one figure
  for all 31 accounts. So a price cannot be joined to where it was charged
  except by matching a label. Whether a price point is a location, a class of
  its own, or a label that stays a label is undecided, and it is the same shape
  as v1's folded pan-slot names one level out. Raised 3 Sep · blocks: generation
- The map holds three units for a bought item and nothing that converts between
  them. `§1.5` gives ordered, counted and worked units for 22 items and `§1.6`
  gives the pack as one phrase, with the packs nesting two deep — a case of six
  tubs of one kilogram, a carton of ten bags of two. The only factor stated
  anywhere is Dan's 10.3 kg per bag, and `§1.5` says he weighs anyway.
  Sharpened 3 Sep by session 2: `line_unit` is grams on almost every page while
  `item_counted_in` is bags, sacks and tins, so a page and a count now name two
  different units for one thing inside one map, and the question is load-bearing
  rather than latent. Whether the business is asked for factors, or the map
  decomposes a pack, or a balance is only ever computable in the counted unit,
  is undecided. Raised 3 Sep · blocks: derive
- `location_within` is self-referential and nothing bounds it. LinkML states no
  acyclicity, the kernel states none, and a generated form's picker will offer
  every `InternalLocation` including the one being edited — so a shop can be put
  inside its own cabinet and every reader that walks the chain hangs. Whether a
  cycle is a violation the way negative stock is, a refusal the form makes, or a
  shape nobody will ever produce, is undecided. Raised 3 Sep · blocks: generation
- A flavour's season is prose the business restates each year. `flavour_runs`
  holds "September to October", "June to July", "No season" and "On the cabinet
  plan all year, made perhaps monthly", which is what `§1.4` writes and what a
  cabinet plan is read off. Nothing turns it into dates, so "which flavours
  should be on in July" is not a query, and the three no-season flavours have a
  cabinet card and may not have been made for six weeks. Whether a season is a
  pair of dates, a recurring rule, or prose a person reads, is undecided.
  Raised 3 Sep · blocks: generation
- Gelato in a pan is not a thing the map can name, and milestone one's closing
  balance runs straight through it. A batch makes gelato of a flavour, the
  gelato fills pans, tubs and minis, and the pans sit in the holding freezer for
  up to 21 days — but the map has `Flavour` for the cabinet card and
  `SoldProduct` for the price line and nothing that is "pistachio in a 5 L
  napoli pan". `product_fill_quantity` says a pan holds about 3.3 kg and
  `made_recipe` says how the pistachio was made, and no slot joins them. Whether
  that is a class, a movement's two ends in `§3.2`, or something a count
  declares, is undecided. Raised 3 Sep · blocks: generation
- A page's lines do not sum to its basis and nothing says so. Every batch sheet
  is per 12.00 kg into the machine and `line_stage: at_fill` marks what goes in
  on top of it, so a reader that totals a page's lines and expects 12.00 kg is
  wrong on eight of the twenty-two sheets. The stage is on the line and the
  basis is on the page, and joining them is arithmetic across rows, which is the
  aggregate shape the 1 Sep line puts outside this map. Whether a page should
  state its own output, whether the at-fill total is a derived slot, or whether
  nothing should ever total a page, is undecided. Raised 3 Sep · blocks: derive
- Scaling a page to a run is prose arithmetic. The white base page is per
  10.00 kg of mix and `recipe_note` says it is made in 55 kg runs; the biscuit
  base page is per run and the run is ten packs of digestives while the line
  says 4.00 kg. So the factor between what a page states and what a session of
  work actually consumes lives in a sentence, and `§2.1` adds that a 55 kg run
  does four batches and leaves about half a bucket that goes into the next
  morning topped up. Whether a run size is a slot, a fact per run, or prose, is
  undecided. Raised 3 Sep · blocks: derive
- `§2.6`'s packaging bill cannot be joined to `§1.7`'s price list, and the map
  holds both. Five of `§2.6`'s fourteen rows are formats and eight are drinks or
  cans matching a price line one for one, so `product_recipe` reaches them; the
  rest are conditions across several lines — any scoop sale, tub or cake taken
  away, any drink taken away — and a scoop's own bill depends on cone or cup,
  which `§1.7` prices as one product either way. So the till knows a thing the
  price list does not carry, and those pages sit in the map with nothing
  pointing at them. Whether the join is a second class, a rule on the form, or a
  distinction the business has to be asked to make, is undecided. Raised 3 Sep ·
  blocks: generation

- The production sheet's pasteuriser run block wants a time of day on a movement
  and the map has one only on a `Batch`. `§3.3` gives the block three ruled lines
  — time, kilos, what it is — and the run itself is a `StockMovement` of base
  whose kilos and ingredient have homes. So one document is a no by one field,
  and the same field would answer the van sheet's time box and the till's time.
  Whether a movement carries a clock time, whether `happened_on` becomes a
  datetime, or whether a time of day is something the log holds only as
  `recorded_at`, is undecided. Raised 3 Sep · blocks: generation
- A document's signature is a second person and `written_by` is one. The van
  sheet is written by the driver and signed by the shop, the wholesale delivery
  note by the driver and signed by the customer, and Whitehall's note is signed
  by Dan on the mornings he is in. Two of `§3.3`'s eighteen documents are a no
  for this reason alone. Whether a second person slot, a `Person` on the
  movement's destination, or nothing, is undecided. Raised 3 Sep ·
  blocks: generation
- The map gave the count sheet a page and the waste sheet none. A waste sheet is
  a weekly page with a week-ending header written on the Monday and its lines are
  free-standing `StockMovement`s, so nothing joins the three lines written from
  memory on one Friday, and the header has nowhere to go. `§3.3` describes three
  such sheets. Whether every document with a header and lines needs a page class,
  or only the ones something totals, is undecided. Raised 3 Sep ·
  blocks: generation
- `happened_on` and the kernel's `valid_from` say the same thing twice. Every one
  of `§3.3`'s eighteen documents starts with a date a person fills in, so the map
  carries a slot for it; the kernel already carries `valid_from` for the same
  instant and `submit()` does not join them. The van sheet is the case that
  decides, because it is written at loading or at the first drop from memory and
  so its date can precede what it records. Whether a document's date slot is how
  a form sets `valid_from`, or a fact standing beside it, is undecided. Raised
  3 Sep · blocks: recording
- A movement of a cake cannot say what is in it. `§2.3`'s cake takes 1.4 L of one
  flavour and 1.1 L of a second, read out on the phone per cake, and
  `movement_flavour` is one slot. `§4`'s count sheet has two finished cakes
  standing in the holding freezer and the cake order carries two flavour fields.
  Whether a cake is a movement with two flavour slots, a thing minted at the
  bench, or a line the balance is allowed to lose, is undecided. Raised 3 Sep ·
  blocks: generation
- Three of `§3.3`'s documents are about stock and have no home at all: the
  temperature log, which is a twice-daily reading of a place where
  `location_temperature` is a standing fact; the whiteboard, where nothing is a
  date and nothing is a quantity; and the cabinet plan, where a well is a `Unit`
  and not a place and a plan is an intention. The first is the most consistently
  completed document in the business. Whether an observation of a place over time
  is a class, and whether an intention belongs in a log of what happened, are two
  different questions and neither is decided. Raised 3 Sep · blocks: generation
- An invoice is a second document about a movement, and the map has movements
  rather than documents. A wholesale drop happens on the Tuesday and Marina types
  its invoice on the Sunday from the second copy in the tray, so one event
  carries two dates up to six days apart; `happened_on` holds one and
  `recorded_at` holds when the system learned it, and the third has nowhere to
  go. This is the same shape as the delivery note corrected across a later van
  sheet, which is already an OPEN line, seen from the money side. Raised 3 Sep ·
  blocks: report
- The supplier's own balance goes negative and nothing asked it to.
  `IngredientOnHand` shows Terra Nostra at −6 dextrose over eight synthetic
  movements, because modelling the outside as places draws the outside down —
  double-entry arriving uninvited from the 1 Sep decision. It is correct, it is
  useless, and it will appear in every generated table until something filters
  it. Whether a balance is scoped to internal places, whether an outside place is
  marked as one, or whether the rows are simply ignored by a reader, is
  undecided. Raised 3 Sep · blocks: report

## T2 — wait for a user

- Would anybody pick a movement's kind off a list of fifty-three? The map makes
  `movement_kind` a picker over `§3.2`'s own rows, which is what lets the log say
  which of the ways stock moved rather than leaving it on `intent.action_name`.
  Whether Steve at a counter, or Dan at the machine, would choose from fifty-three
  rather than reach for the nearest, is a thing only they can say, and the
  alternative — a form per kind — is the failure the 1 Sep rule exists to
  prevent. Raised 3 Sep · blocks: interview

- Would Dan's book ever carry a line with no quantity? The map allows one — an
  ingredient, no number, a note — because `§2.3` says three flavours are made by
  feel and gives Dan's own answers: honey until it tastes right, a good glug of
  marsala, most of a 100 g pack of basil that he smells and decides about. He
  says he will not write a quantity for the basil. Whether he would write the
  line at all, or whether an unwritten page is simply absent, is a thing only he
  can say, and the two produce different consumption. Raised 3 Sep ·
  blocks: interview
- What one filled 500 ml tub takes is two answers in the profile and the map
  holds them apart. `§2.4` says about 460 g of gelato and `§2.6` says one tub,
  one printed lid, one printed sleeve; the packaging is a `Recipe` and the
  gelato is `product_fill_quantity`, because which flavour goes in is decided at
  the bench and cannot be a line. Whether the business thinks of a filled tub as
  one bill or as two things that happen at the same moment decides whether a
  filling form asks one question or two. Raised 3 Sep · blocks: interview

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
- A supplier that is collected rather than delivered has no lead time and no
  minimum order. Session 1 of Sorella's profile states both as "None" for Bristol
  Cash & Carry, which supplies the whole coffee bar. Whether "None" is a value
  the map carries or an absence it must allow is untried, and it is the only
  supplier of the nine shaped that way. Raised 2 Sep · blocks: interview
- Two bought items in Sorella's session 1 are both called "the milk": Whitehall's
  10 L bag-in-box in the kitchen and the cash and carry's 2 L bottles for the
  coffee machine. Two suppliers, two units, two places, one word. Whether that is
  one material in two packs or two materials is a modelling choice the profile
  deliberately does not make. Raised 2 Sep · blocks: interview
- The steel napoli pan is a bought item at £38, a reusable asset, and the
  container a wholesale sale travels in and comes back from. Session 1 names it
  once in the buying table and names each of the 31 accounts as a place stock can
  sit; nothing says whether a pan at a café is stock, a loan, or neither, and
  §11 (carried) says nobody has ever counted them. Raised 2 Sep · blocks: interview
- Session 1 states prices as at 15 June 2026 and puts superseded ones in prose —
  pistachio at £152.00 until September 2024 and £170.50 until February 2026.
  Whether an old price enters the log as a dated fact or stays prose is
  undecided, and master data is the cheapest place the two time axes could be
  exercised on something other than a movement. Raised 2 Sep · blocks: interview
- Water is named in four recipes and is deliberately not a bought item. `§1.6`
  excludes it in its own preamble — not tracked against product — and `§2.1`
  names it as the one thing a recipe calls for that the buying table does not
  hold. So a bill of materials has a line with no material behind it. Whether the
  map carries a material nobody buys, or a recipe line the map is allowed to
  leave dangling, is untried. Raised 2 Sep · blocks: interview
- A batch's inputs exceed the batch. Every page is written per 12.00 kg into the
  batch freezer, and the variegates — 0.85 kg of chocolate on stracciatella, 0.40
  kg of caramel, 1.10 kg of biscuit base, 1.60 kg of stewed rhubarb — go in by
  hand after the machine and are on top of it. Whether a recipe is per mix in or
  per output, and where the at-fill half attaches, decides whether consumption
  ever balances. Raised 2 Sep · blocks: interview
- Three flavours have a recipe with no quantities in it. Ricotta and fig,
  panettone and marsala, and peach and basil are made by feel and `§2.3` says so
  and says what Dan does instead. A bill of materials that must hold "honey until
  it tastes right" either carries a null quantity, or carries the ingredient with
  no number, or refuses the flavour. Every one of the three is a different answer
  for the generator. Raised 2 Sep · blocks: interview
- A scoop has no weight, and it is the unit two thirds of the retail sales are
  counted in. `§1.5` says it is a press of a button; `§2.4` adds that Aoife tells
  new staff a pan does forty-five and that Callum's do thirty, and that nobody
  has ever weighed one. Nothing converts a till line into grams out of a well, so
  a closing balance at either shop cannot be computed from what the business
  records. This is a missing-information failure in the 1 Sep sense only if a
  number exists to be found, and none does. Raised 2 Sep · blocks: live use
- Passionfruit purée is bought, priced and counted, and no flavour in `§1.4` is
  made of it. `§2.3` states that it runs on the fruit sorbet page when an account
  asks and has never had a cabinet card or a season. So the range and the buying
  table disagree by one item, in the direction the map will not notice: an unused
  material looks exactly like a correct one. Raised 2 Sep · blocks: -

- A pan has a weight now and still has no weight on any document. `§2.4` states
  about 3.3 kg of gelato, from three pans weighed on one morning because a hotel
  asked; every count, transfer, delivery note and van sheet in the business is in
  whole pans and part pans, and a part pan is ½ or ¾ by eye. Whether the map
  carries a pan as a container with a nominal fill, as a unit of measure, or as
  neither — and what a half pan converts to when a recipe is in kilograms — is
  untried, and milestone one joins a recipe to a count through exactly this.
  Raised 3 Sep · blocks: interview
- No quantity in the profile says whether it is gross or net. The pan's two
  readings differ by the pan itself: 3.6 kg was the pan on the scale as it stood
  and 3.3 kg is what is in it, and nothing on either occasion recorded which was
  meant. The tub and the mini are stated as fills only, with no gross anywhere.
  This is what made three of Tuesday's batches read as putting out more than went
  in. Whether a quantity in the log needs a basis beside its unit is untried, and
  it is cheap to try. Raised 3 Sep · blocks: interview
- Three of Tuesday's five wholesale drops are under the stated minimum. `§3.4`
  sets a minimum wholesale order of 4 pans; `§4.3` has Bar Trentanove on 3 pans,
  Cleeve on 3, and The Hollow on 2 pans plus 4 catering tubs. Written in session
  4, found in session 5 by reading the rule against the day. Whether the minimum
  counts pans or units, whether a rule nobody has ever enforced belongs in the
  map, and what a generated order form should do with it, are three different
  answers. Raised 3 Sep · blocks: interview
- A correction can live on a document that is not the one it corrects. The Blue
  Kettle's delivery note of 18 June says 5 pans and 4 were handed over; what puts
  it right is a sentence Steve wrote across **Saturday's van sheet** two days
  later, and an invoice Marina typed on the Sunday for 4. The note itself was
  never altered and both its copies still say 5. So the log would hold two
  assertions about one delivery, sourced from two documents about two different
  days, and the only thing joining them is that Steve remembered. Whether the
  second is a retraction of the first, an independent assertion that happens to
  win on recorded time, or something the map has to be told to relate, is
  undecided — and this is the first correction in the material, so it is the
  first test of the mechanism the whole PoC rests on. Raised 3 Sep · blocks: kernel
- The week has no closing count. The count sheet is monthly and the last one is
  the June one; nothing was counted anywhere in the business between Dan's
  evening count on Tuesday 16 June and the end of Sunday 21 June. So there is an
  opening position and one two-day stretch that can be checked, and five days
  after it that cannot be checked against anything. Whether milestone one's
  “closing balances match a hand computation” has anything to land on past
  Tuesday, or whether the business would have to be asked to count again, is not
  something the profile can answer. Raised 3 Sep · blocks: live use
- A pan's age is a date on a label and nothing tracks where the pan has been. The
  lemon sorbet pan the Blue Kettle did not take stood in the van from Thursday to
  Saturday and then went into the holding freezer with the rest, and its label
  still reads *frozen 17/6*. `§3.4` puts a wholesale pan's best-before at 14 days
  from the freeze date and the holding freezer's maximum age at 21 days, so both
  rules read off a label and neither reads off a location. Whether the log should
  hold the two days in the van at all, when no document in the business names
  them, is undecided. Raised 3 Sep · blocks: interview
- Two wholesale accounts never take the unit the minimum is written in. `§3.4`
  sets a minimum wholesale order of 4 pans; on Thursday 18 June, Papavero
  Delicatessen took eighteen 500 ml tubs and The Regent Picture House took sixty
  minis, and neither took a pan. `§1.7` says the deli and the cinema take tubs
  and minis and everyone else takes pans, so the rule counts a thing eight of
  the thirty-one accounts have never ordered. The earlier line on this rule asks
  whether the minimum counts pans or units; this is the case where no
  translation between the two exists, because the account has no pan line at
  all. Found 3 Sep by the check script reading `§3.4` against all three van
  days — the earlier line was written from Tuesday alone. Raised 3 Sep ·
  blocks: interview
- A day's till report and a day's takings are two different documents and only
  one of them leaves the shop. Gloucester Road's Tuesday item list carries no
  cans, no water and no waffle-cone supplements and does not account for its own
  takings, while every other item list in the profile does add up exactly
  against `§1.7`. The lines stay in the till; what reaches Marina is the
  cash-up, which is four numbers. So a generated form that asks a shop to enter
  its day has to choose which of the two it is asking for, and only one of them
  is a thing this business currently produces. Raised 3 Sep · blocks: generation
- The check script that guards the profile is a second reader of the same
  material the map will read, and it holds business knowledge the map does not:
  which recipe name is which bought item, which `§1.6` item is consumed by which
  sentence, and what a batch's at-fill additions are. That is legitimate in
  `scripts/`, but it means two files now encode Sorella's aliases and the map
  will be the third. Whether the map should be the one place those aliases live,
  and the checker read them from it once a map exists, is untried and cheap to
  try once generation has been through a lap. Raised 3 Sep · blocks: generation
- Every check in the suite that finds a violation needs the profile to say the
  violation is there, and the way it says so is a phrase the script looks for —
  an account named in `§3.4`'s conflicts, the words "a day late" on a delivery,
  "does not account for" beside a till total. That is a convention held in one
  script and stated nowhere the profile's author can see it. Whether a frozen
  document needs a machine-readable way to mark a known exception, or whether a
  phrase a person would write anyway is the right mechanism, is undecided, and
  the same question arrives again the first time a generated form has to record
  a rule being broken on purpose. Raised 3 Sep · blocks: -

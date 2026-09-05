# Decisions

## Standing rules

Everything below the line is append-only and is never edited. This index is the
opposite: it is **derived, mutable, and has no authority.** It says which entry
governs a topic today so that a reader does not have to walk 200 entries to find
out. Where the two disagree, the dated entry wins and this index is stale.

A rule that has been superseded is not listed. Its entry is still below, still
readable, still dated — but it no longer governs, and reading it as though it
did is the failure this index exists to prevent.

Built 2026-09-04 from 203 entries, of which 52 carried a reversal. Extended
2026-09-05 with the rule-corpus entries and 2026-09-06 with the dimension-and-
scope split, both of which the build predates.

### What is being proven

- Definition of done: one shrinkage report under two definitions, plus why the
  numbers differ · 24 Aug, staged into three milestones 1 Sep
- Milestone one is done when one operational day — Tuesday 16 June 2026 — is
  entered entirely through generated forms and the closing balances match a hand
  computation · 1 Sep, day fixed 3 Sep
- Five claims that can each fail: A form derivability, B number derivability,
  C row identity, D the full loop and two clocks, E benchmark coverage. Plus F,
  an agent answering better from the graph than from tables · 1 Sep
- A result lands in one of three baskets, fixed before any result exists:
  missing information, missing mechanism, or passing by cheating · 1 Sep
- An ERP is a benchmark, not a direction. Each mechanism is admitted or refused
  with a reason · 1 Sep
- Milestone one's forms are rendered HTML in a browser, local, no polish · 4 Sep

### The two stores

- The map holds the logic, the log holds the history. A rule is the frame for
  reading the world, not a fact about it · 26 Aug, superseding 24 Aug
- Judgement is allowed at the two edges — interview, agent — and forbidden
  between them. `seal` is that boundary · 1 Sep
- `seal` writes map versions, `submit` writes facts. Adding a supplier is no
  longer a reason to publish a map version · 1 Sep
- Where a number lives has four homes and one test: if this number changed,
  would a report about last month change with it · 30 Aug
- A business gets its own version store via `seal --into`. The log gets no such
  separation, so one log now carries two businesses · 4 Sep
- A rule that computes lives in the graph; a rule that is a number with a
  history lives in the kernel and is inert until the graph names it · 5 Sep
- Every rule splits into a sentence the graph carries and a number the kernel
  carries. A rule that cannot be split that way is not yet understood
  · 5 Sep, extending the line above
- The kernel's columns are sufficient for the rule corpus and the graph's are
  not. None has been exercised: `authority` is NULL on all 1,700 assertions and
  there are no revocations · 5 Sep
- Nine kinds of rule. A about one entity, B about one place, C about the
  business are one mechanism under three subjects and need nothing new; D is
  the aggregates; I is an observed rate that is explicitly not a rule. E scope,
  F refusal, G conversion and H schedule have no construct · 5 Sep
- The map was authored as a data model, never as a rule model, which is why the
  two stores do not meet: the rule crossing has run zero times · 5 Sep

### The map

- LinkML is the serialisation; a predicate's identity is its `slot_uri`, stable
  across renames, which is why `gen-owl` needs `--no-use-native-uris` · 26 Aug
- A sealed version is never edited or deleted; a correction is a new version
  that supersedes it · 26 Aug
- Time attaches to a whole version, not to individual rules: `valid_from` and
  `sealed_at`, chosen the same way the kernel chooses a fact · 26 Aug
- The map stays flat — `is_a` only, no mixins · 29 Aug
- `seal` refuses a draft with no `valid_from` and no `slot_uri`; it strips the
  `facts` block, so the map never holds a number about a thing · 27 Aug, 30 Aug
- A hand-authored map carries a provenance note as its transcript, written once
  at the seal covering every sitting · 29 Aug, 4 Sep
- A key enters `annotations` only when a rule already stated in the profile
  cannot be expressed without it, never in anticipation · 1 Sep
- Derivation is two problems: within a row is LinkML's `equals_expression`,
  across rows is ours — an `aggregate` annotation with `over`, `sum` and `by`,
  arithmetic-free · 1 Sep, spelling fixed 2 Sep, net is one expression 4 Sep
- No rule construct enters a map before something can execute it · 5 Sep
- An aggregate's `by` names every slot its measure is meaningless without. This
  is what a projection class is authored against · 6 Sep
- A missing **dimension** and a missing **scope** are different failures. The
  rows are the right rows but not comparable to each other, and the map repairs
  it by adding to `by`; or the rows are the wrong rows, and no dimension helps
  · 6 Sep, splitting a basket the 5 Sep entries had held as one
- An `aggregate` is `over`, an operator and `by`, and cannot say which rows a
  balance counts. `p_gelato_on_hand` is three rows about nothing because of it
  · 5 Sep. This is the scope half and it stands; the unit half was a dimension
  and was corrected 6 Sep
- LinkML's class `rules` are refused: `linkml_runtime` raises
  `NotImplementedError` for any rule, so a map could look enforcing and never
  execute · 1 Sep
- `designates_type` is admitted: it names which slot carries the type, and the
  value stays an assertion with both clocks · 2 Sep, reversing 1 Sep
- A class earns its existence by changing the shape of its form · 1 Sep
- The outside of the business is modelled as locations, so direction is free —
  a supplier and a wholesale account are `is_a Location` · 1 Sep, 3 Sep
- One movement class; `GoodsReceived` does not survive into Sorella, and the
  kind of a movement is a field over 53 `MovementKind` rows · 3 Sep
- A collection gets its own subject — `Recipe` is the page, `RecipeLine` is one
  line — which closes the multivalued question by elimination · 3 Sep
- A count line is its own entity · 3 Sep, superseding 30 Aug for counts as
  1 Sep superseded it for movements
- Gelato in a pan is two cells on a line, not a thing · 3 Sep
- `Unit` is what stock is counted, ordered or worked in, and nothing else
  · 3 Sep, correcting 30 Aug
- The map carries no gross-or-net basis, because the business draws none · 3 Sep
- Detailed validation is `gen-mermaid-class-diagram`; WebVOWL is a glance at the
  whole shape and validates nothing · 3 Sep, superseding 29 Aug and 30 Aug

### The kernel and the log

- Facts are written through `perform()`, never by direct INSERT · 29 Aug
- The log holds raw facts and never judgements; a constraint is a derived
  boolean producing a violation list, never a refusal · 21 Aug, 1 Sep
- A form refuses exactly one thing: a required field left empty · 1 Sep
- A value whose slot declares a class as its range is written as `value_ref`
  · 29 Aug
- Reading a value applies the range the map declares. The caster lives in the
  unnamed seam inside `generate.py`, not in `ontology` · 1 Sep, correcting an
  entry made the same day
- Master data is valid from the adoption date and recorded today · 4 Sep
- `resolve_version` returning `None` before a map's `sealed_at` is correct, not
  a defect: the hole is only on the diagonal · 4 Sep, closing 31 Aug

### The generator

- The generator may not know what a business is. The rule is stated against code
  with comments and docstrings stripped · 1 Sep
- A form is generated per class, and the document classes are already classes
  · 1 Sep
- The row rule reads the class fact — the entity whose `entity_class` names this
  class — and walks `is_a`, so an entity is a row of more than one table
  · 4 Sep, replacing the 31 Aug guess
- A class carrying no `designates_type` slot renders no form. A derived class
  keeps its projection table; only the form goes · 4 Sep
- Master data enters through generated forms, and `submit` writes the
  class-membership assertion · 1 Sep

### The business

- The business is Sorella Gelato. Marlow is retired and nothing is measured
  against it · 2 Sep
- Sorella's profile is frozen at `ada1d9e` and does not change without an item
  in `NEXT.md`. The gate is `scripts/check_profile.py` · 3 Sep
- A check enters that suite only when an error it would have caught has already
  been found · 3 Sep
- Whoever writes the profile may read this repo. The guard is on content: every
  number is one a person in the business would know or say, nothing is computed,
  and no distinction appears that the business does not itself make · 2 Sep,
  superseding 27 Aug and the blind-author line of 2 Sep
- v1 is evidence, not a reference: its gaps are missing information · 1 Sep

### Process

- Stages are named, never numbered, and are a flow one lap runs — not a build
  list. Nobody is "at" a stage · 26 Aug, superseding 24 Aug
- The stop-list is entered only through `NEXT.md`, never by editing CLAUDE.md
  · 24 Aug
- One session holds both modes. `NEXT.md` and `DECISIONS.md` are written
  once Fareza has agreed to the wording, never as a side effect of an
  implementation run · 5 Sep, superseding 24 Aug
- `CLAUDE.md` says what the system is and does not track it. Where the work
  stands is `ROADMAP.md`; how a session works is the two skills · 5 Sep
- The archived corpus may be quoted to answer a named question, with file and
  section cited, and never browsed · 24 Aug
- Decisions are written at the rate evidence arrives, not at the rate arguments
  do. If nothing is being built and nothing has failed, the honest entry is no
  entry · 2 Sep
- A done condition may not pin a total test count while also asking for new
  tests. The form that works is "the N that existed still pass" · 1 Sep
- The interview is deferred until the consuming components exist. There is no
  interview in this PoC and no date for one · 29 Aug, 27 Aug
- No component named `derive` is built. Where the code lives is a filing
  question, decided when `report` gives it a second caller · 2 Sep, withdrawing
  a 1 Sep entry that is left standing rather than corrected

---

Append-only. Each entry carries the decision **and the reason for it**.
If the reason cannot be stated, it is not yet a decision.
A path considered and rejected is a decision too — without it, the same
proposal comes back next session.

Reopening a line here requires a reason from **code or a user**, never from a
better argument.

Lines marked `(inherited)` were decided in the archived corpus, not here. Their
reasoning lives in `../archived/`. They are closed, which means not re-discussed
— it does not mean proven.

The 203 entries made between 2026-08-21 and 2026-09-04 are in
`history/DECISIONS-2026-08-21_2026-09-04.md`. What still governs from them is
the standing-rules list above; the rest is evidence, quoted by date, never
browsed.

---


2026-09-05 · `build/` is the inspection surface, scoped by business and version.
             It is deletable whole only while nothing hand-written lives there
             and one command rebuilds it; both were false on 4 Sep, and eight
             scripts had to be recovered from a directory git never held.
2026-09-05 · The graph render carries explicit `rdfs:domain`, derived by
             `scripts/owl_domains.py` and never read back by anything. A slot
             owned by several classes gets `owl:unionOf`, because two plain
             `rdfs:domain` triples mean intersection and would assert that a
             thing is two classes at once. Measured: 0 domains before, 101
             after, 6 of them unions, and all 101 match what the map declares.
2026-09-05 · The OWL render is for shape and never for reading. `gen-owl`
             carries no `rdfs:comment` at all, so all 122 descriptions the map
             holds — 21 classes and 101 slots — reach no OWL viewer, and pyLODE
             shows no cardinality either although the TTL carries 122 of each.
             This falsifies the 3 Sep line that put the gross-or-net refusal in
             `line_quantity`'s description so that a reader of the map would
             meet it. Through this path no reader ever does.
2026-09-05 · The 5 Sep line saying the OWL render carries no descriptions is
             wrong, and is corrected here rather than edited. `gen-owl` writes
             126 `skos:definition` rather than `rdfs:comment`, and pyLODE
             renders every one; cardinality is there too, as 122 `min` and 122
             `max` restriction axioms. Both errors were one mistake — measuring
             a single spelling, finding zero, and never grepping the rendered
             file that was already on disk. The 3 Sep line putting the
             gross-or-net refusal in `line_quantity`'s description stands.
2026-09-05 · The PoC's subject is the system. Whether anyone wants it is a
             business question, out of scope, and not raised in these sessions.
             The six T2 lines rotate to `history/OPEN-T2-2026-09-05.md`, and T2
             leaves the file rather than parking in it.

2026-09-05 · The 1 Sep line "a generated table is a projection by construction —
             a read of the log, never a store" is corrected here rather than
             edited. It answered a question about reporting priority with an
             architectural claim nobody asked for, and deleted the projector
             layer that both the 31 Aug diagram and `01-ARSITEKTUR.md` §5 carry.
             The operational database is a generated store filled from the
             kernel; forms and dashboards read it and never the log.
2026-09-05 · A rule that computes lives in the graph, because the graph is the
             only thing the compiler reads. A rule that is a number with a
             history lives in the kernel, and is inert until the graph names it.
             Neither home is sufficient alone.
2026-09-05 · No rule construct enters a map before something can execute it.
             `sorella/v1.yaml` carried four `aggregate` annotations and two
             `equals_expression` that `generate.py` never read — zero
             occurrences, measured — so `table()` sought every derived column in
             the log as a stated fact and `GelatoOnHand` returned no rows. This
             replaces the `constraint engine` brake, which pointed the other
             way; `constraint engine` leaves the stop-list.

2026-09-05 · The governing files are split by what they answer, because status
             written in three places disagreed in all three. `CLAUDE.md` says
             what the system is and tracks nothing; `ROADMAP.md` is the only
             file that says where the work stands; `README.md` says how to run
             it. It found `CLAUDE.md` naming a design diagram that does not
             exist and `README.md` claiming three built components, an empty
             `business/` and 41 tests, against five, three and 65.
2026-09-05 · Session procedure leaves `CLAUDE.md` for two skills,
             `.claude/skills/uniti-discuss` and `uniti-build`, invoked by name.
             The read budget, the per-entry line ceilings, the file-count
             ceilings and the ban on new root `.md` files are dropped rather
             than moved: they policed the session instead of describing the
             system, and `ROADMAP.md` is the seventh root file they forbade.
             What survives is the one rule with a failure behind it — a
             decision is not written in the same act as the code it justifies.

2026-09-05 · The business's rules are in no store. Measured against the working
             log and `sorella/v1.yaml`: the graph carries six rules — four
             `aggregate` annotations and two `equals_expression`, which is the
             whole of `annotations` across 1,190 lines of map. The kernel
             carries 93 parameter values — `item_pack_price` 77,
             `credit_terms` 11, `supplier_minimum_order` 5 — and not one of
             them is named by any rule in the graph, so by the 5 Sep line
             above every one is inert. `compile.py` carries zero business
             terms, which is correct and is the only one of the four homes
             that is as it should be. The fifty-one rules of profile §3.4,
             each with a number, a setter, a date it last changed and what it
             was before, are in none of the three.
2026-09-05 · Every rule splits into a sentence the graph carries and a number
             the kernel carries, and a rule that cannot be split that way is
             not yet understood. The graph carries the shape: which class the
             rule is about, the slot that names its number, and what the
             number does. The kernel carries the value: the number,
             `valid_from`, `recorded_at`, `authority`, and the reason on the
             intent. This extends the 5 Sep line from a division of rules into
             two kinds to a decomposition applied to each rule. The reason is
             that a number and a shape have different lifetimes: the cake
             order's notice rule has not changed shape since 2022 and its
             number moved on 16 June 2026, so holding both in one place makes
             every change of a number publish a map version and re-version
             every report ever run. It is also the whole of the difference
             from an ERP's config column, which holds the number with no
             history and the shape in a branch that gets recompiled.
2026-09-05 · The kernel's columns are sufficient for the rule corpus and the
             graph's are not. §3.4's four columns map onto the kernel with
             nothing left over: the number is the value, "Last changed" is
             `valid_from`, "written down 7 June 2026" is `recorded_at` and is
             a different date, "Set by" is `authority`, why it changed is
             `intent.note`, and what it was before is the superseded
             assertion. No column is missing. What has not been exercised is
             all of it: `authority` is NULL on all 1,700 assertions,
             `confidence` is set on 19, there are no revocations, and 1,700
             assertions cover 1,672 distinct (subject, predicate) pairs, so 28
             are a second or later value. The log is a snapshot, not a history.
2026-09-05 · The map was authored as a data model and never as a rule model,
             and that is why the graph and the kernel do not meet. The order
             was profile, then map from the nouns the business handles, then
             kernel loaded with master data whose shape the map had already
             fixed. So the kernel sits downstream of the graph's *data* shape
             and the rules were an input to neither. Only one kind of crossing
             has ever happened — the map declares a slot and the kernel holds
             values for it — and the crossing the design is about, where the
             graph names a parameter, the kernel supplies its value and its
             history, and the compiler executes it, has run zero times.
             `credit_terms` exists because it reads as an attribute of a
             supplier; "21 days maximum age in the holding freezer" does not,
             because it reads as a rule and there was no home for a rule.
2026-09-05 · The rule corpus classifies into nine kinds, and only four of them
             need mechanism that does not exist. A rules about one entity
             (a reorder level, a credit term, a price), B rules about one
             place (12 flavours minimum in a cabinet, 21 days in the holding
             freezer), C rules about the business (free delivery above £120)
             are one mechanism under three subjects — a slot and an assertion
             — and need nothing new. D derivations are the aggregates that
             exist. I is an observed rate that is explicitly not a rule
             ("a tin of pistachio does about five batches"; "Specials
             actually run — Practice, and not a rule") and is what
             `confidence` and `authority` are for. The four with no
             construct are E scope (which movements a balance counts, which
             flavours go in which format), F refusal (no sorbet in a cake,
             minimum order 4 pans), G conversion (case to pack to gram), and
             H schedule (van runs Tue/Thu/Sat May to September). Roughly two
             thirds of §3.4 is A, B or C. The map is not short of
             expressiveness; it was never asked what governs its classes.
2026-09-05 · The gelato balance's spurious rows are a scope hole in the
             `aggregate` construct, not a defect in the map. Measured:
             `p_gelato_on_hand` and `p_ingredient_on_hand` are numerically
             identical, 27 / −37 / 10, both produced by the same three
             digestive-biscuit movements, and one of the two tables is
             entirely about nothing. The profile is not at fault — §2.5 is
             wholly about flavour and format and even names the cases written
             without a flavour. The map is not at fault for what it models —
             the 3 Sep line that gelato in a pan is two cells on a line
             stands, and `GelatoOnHand`'s own description states that a line
             without a flavour should be in no group at all. The fault is
             that the description is the only place that rule exists: an
             `aggregate` is `over`, an operator and `by`, and there is no way
             for a map to say which rows a balance counts. The 5 Sep brake
             stopping the compiler from filtering is right and was read as
             though nothing needed to decide; what follows from it is that
             the graph must be able to say it, and it cannot. The `OPEN.md`
             line "Gelato in a pan has no name in the map" leaves, answered
             by the 3 Sep standing rule; the classifying-dimension line stays,
             now typed as a missing mechanism rather than a question.

2026-09-06 · `p_ingredient_on_hand` reading 5.32 is the map grouping by the
             wrong set, not a mechanism the compiler lacks, and the 5 Sep
             entry that put it in the missing-mechanism basket is corrected
             here rather than edited. Probed: a copy of `v2.yaml` with one
             slot `ingredient_unit` added to `IngredientOnHand` and
             `ingredient_unit: movement_unit` added to the `by` of both its
             aggregates, compiled against the same log with **no code change
             at all**, gives pistachio 6 in tins and −0.68 in kilograms as two
             rows. Six is the hand computation exactly. `movement_unit` has
             been in the map since v1 and was carried as a field to display,
             never as a dimension to group by — the same data-model thinking
             the 5 Sep entry names, this time inside an aggregate. Under
             `CLAUDE.md`'s own test there was an input that made it pass, so
             it was never a missing mechanism. The gelato finding is not
             corrected with it: no dimension repairs that one.
2026-09-06 · An aggregate's `by` names every slot its measure is meaningless
             without, and this is the ideal a projection class is authored
             against. The test for a missing one is whether the rows of a
             group are comparable to each other. It separates two failures
             that had been sitting in one basket, and the separation is the
             durable part:

             A **missing dimension** — every row belongs in the table, but
             they are not comparable, tins summed against kilograms. The map
             repairs it by adding the dimension to `by`, and nothing else is
             needed. Diagnosis: the number is nonsense but the rows are the
             right rows.

             A **missing scope** — rows are in the table that should not be
             there at all, every digestive movement standing in
             `p_gelato_on_hand`. No dimension helps: the offending rows are
             silent on the dimension that would exclude them, and silence
             produces a group keyed on nothing rather than no group. This is
             the mechanism `aggregate` does not have. Diagnosis: the rows are
             the wrong rows, whatever the number says.

             When a map names a measure, the question to ask of it is what
             this number would mean nothing without. Every answer is a `by`
             entry. Place, unit, flavour and format are all answers; the map
             had asked it only of place. Calling a dimension a mechanism does
             two harms — it inflates what the PoC thinks it has learned, and
             it hides work that could be done today.

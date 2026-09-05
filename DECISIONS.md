# Decisions

## Standing rules

Everything below the line is append-only and is never edited. This index is the
opposite: it is **derived, mutable, and has no authority.** It says which entry
governs a topic today so that a reader does not have to walk 200 entries to find
out. Where the two disagree, the dated entry wins and this index is stale.

A rule that has been superseded is not listed. Its entry is still below, still
readable, still dated — but it no longer governs, and reading it as though it
did is the failure this index exists to prevent.

Built 2026-09-04 from 203 entries, of which 52 carried a reversal.

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
- Claude Code never writes `DECISIONS.md`; it proposes wording in `LOG.md`
  · 24 Aug
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

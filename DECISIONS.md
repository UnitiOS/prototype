# Decisions

Append-only. Each entry carries the decision **and the reason for it**.
If the reason cannot be stated, it is not yet a decision.
A path considered and rejected is a decision too — without it, the same
proposal comes back next session.

Reopening a line here requires a reason from **code or a user**, never from a
better argument.

Lines marked `(inherited)` were decided in the archived corpus, not here. Their
reasoning lives in `../archived/`. They are closed, which means not re-discussed
— it does not mean proven.

---

2026-08-21 · Old design corpus archived to `../archived/`. No longer a reference.
2026-08-21 · (inherited) Kernel is three tables: intent, assertion, entity.
2026-08-21 · (inherited) Build the kernel, do not adopt XTDB — per-statement versioning.
2026-08-21 · (inherited) Point-based valid time. No valid_to column.
2026-08-21 · (inherited) confidence has three levels (high/medium/low), not a number.
2026-08-21 · (inherited) Constraint violations are projections, not assertions.
2026-08-21 · (inherited) Neo4j deferred with no date.
2026-08-21 · Work order: vertical slice -> time-travel demo -> real user.
             Compiler and UI generator come after.

2026-08-21 · A retraction is itself an assertion; the revokes filter is evaluated at the query's as_of, not globally.
2026-08-22 · resolve_single: candidates are valid_from <= :valid_at AND
             recorded_at <= :as_of, minus those revoked by a row whose
             recorded_at is also <= :as_of; winner is max valid_from, ties
             broken by max seq.
2026-08-22 · A pure retraction carries no value. value_exactly_one is relaxed
             to allow zero values when revokes IS NOT NULL, so "we were wrong"
             can be said without inventing a replacement.
2026-08-22 · A candidate must state something about the world: resolve_single
             filters on num_nonnulls(value_literal, value_ref) = 1, not on
             revokes IS NULL. A valued row that also revokes stays a candidate.

2026-08-24 · Uniti replaces an ERP, not Airtable or Notion, because an ERP is
             what a customer would actually retire — and the comparison decides
             what the PoC has to prove.
2026-08-24 · The PoC is eight stages: interview, ontology mapping, graph review,
             kernel recording, generated UI and projections, live use,
             definition change and replay, agentic access. The kernel is a base
             layer no user can feel on its own; only the stages above it can be
             judged from outside the team.
2026-08-24 · Stage 7 is the one that can kill the premise. Stages 1-6 and 8 show
             that Uniti can be used; only a definition changed after data exists
             shows that it is better.
2026-08-24 · The ontology lives outside the log and follows an existing
             standard, so the kernel stays the only home for facts and the
             result can still be exported to something else.
2026-08-24 · The graph is visualised with tools that already exist, never
             generated — a graph viewer is a commodity and generating one
             proves nothing.
2026-08-24 · ontology_version names a version of the ontology artefact, not a
             point in the log, because the ontology no longer lives in the log
             and there is no seq to point at.
2026-08-24 · The PoC domain is inventory for an ice cream business: stock on
             hand is a projection rather than a fact, so the kernel's claim is
             felt directly — and inventory's boundaries are not clean, which is
             the harder test.
2026-08-24 · Three interfaces — chatbot, generated forms, graph viewer — and the
             operators are the Uniti team, so none needs polish. The PoC has to
             show that generation works, not that a product is pleasant.
2026-08-24 · Everything stated in an interview, rules and aggregates included,
             is recorded in the log and the kernel must be ready for it:
             whatever is not in the log cannot be projected later.
2026-08-24 · Rule statements are assertions like any other; what a rule computes
             is a projection, never an assertion. What the user said is a raw
             fact — only its output is a judgement.
2026-08-24 · The ten entries above were rewritten once, on the day they were
             written, to carry their reasons — with Fareza's permission. Nothing
             dated before 2026-08-24 was touched.

2026-08-24 · PoC definition of done: the same shrinkage report, computed as it
             was computed then and with today's definition, plus why the numbers
             differ. Anything short of that shows Uniti can be used, not that it
             is better.
2026-08-24 · The generated webapp exists to show that a form can be generated,
             filled, and written back to the kernel. It is not meant to be a
             usable product.
2026-08-24 · No separate roadmap document. The eight stages are the roadmap; a
             document above them would only add dates that slip and detail
             decided before we are able to decide it.
2026-08-24 · No skills, subagents, or hooks for Claude Code's own workflow until
             a pattern has repeated three times. Machinery for a problem we do
             not have yet. This says nothing about the product's chatbot, which
             is stage 1.
2026-08-24 · CLAUDE.md is rigid about process and loose about content: it says
             how to decide, not what to build. Content rules go stale the moment
             a decision changes; process rules do not.
2026-08-24 · The "not built" list becomes a stop-list: nothing on it is built
             unless an item in NEXT.md names it. Components enter through
             NEXT.md, not by editing CLAUDE.md.
2026-08-24 · The eight stages appear in CLAUDE.md as the goal, names only, with
             a marker of the current stage. Without it, structure and design get
             built for one component instead of eight.
2026-08-24 · Claude Code's authority is bounded by a test, not a list of allowed
             actions: a list always misses the case that matters. The test lives
             in CLAUDE.md.
2026-08-24 · Claude Code may append to OPEN.md and LOG.md and never writes
             DECISIONS.md. When it thinks something should be decided, it
             proposes the wording in LOG.md.
2026-08-24 · The archived corpus stays a non-reference, but it may be quoted to
             answer a named question, with file and section cited. What killed
             the last cycle was browsing and editing it, not quoting it.

2026-08-26 · The stages are a **flow**, not a build list — one lap the system
             runs for one business, not eight things the team builds in order.
             Read as a build list they produced a repo holding the kernel while
             the plan said "currently stage 1". That contradiction was the
             symptom, not a bookkeeping slip.
2026-08-26 · Stages are named, never numbered. Interview and mapping merged and
             every number after them moved, which would have quietly falsified
             four lines in this file, a paragraph in CLAUDE.md and a section in
             README.md at once. A name survives the next merge; a number does
             not, and a number in one file drifts from the same number in
             another.
2026-08-26 · Interview and ontology mapping are one stage. Deciding whether a
             statement becomes ontology structure, a derived rule or code needs
             a follow-up question, and only the interviewer can ask one — a
             mapper reading a transcript cannot. Recording depends on the same
             act: perform() needs a minted predicate and an ontology_version,
             so nothing can be recorded before the mapping exists.
2026-08-26 · Stages and components are many-to-many. A component per stage
             would have built the chatbot twice — once for mapping, once for a
             definition change — and given graph review and live use components
             of their own when neither needs code.
2026-08-26 · The chatbot holds the session in a draft and writes nothing until
             the user asks to commit. The kernel records what the business is,
             not how the interview went: someone correcting their own sentence
             is looking for a word, not producing evidence about the world. The
             cost is accepted — a self-correction mid-interview never reaches
             the log, and a whole interview lands at one recorded_at, so the
             spread the replay demo needs can only come from live use.
2026-08-26 · The session draft is internal to the chatbot and is not a store.
             It holds no facts and may be lost; losing it means the interview is
             repeated. Making it durable would add a third store to hold
             something that is not evidence.
2026-08-26 · Only the chatbot writes the ontology. One writer means linear
             versions, no reconciliation between writers, and a graph viewer
             that stays strictly read-only. A human who wants a change says it
             to the chatbot.
2026-08-26 · A commit writes the ontology version first, then mints predicates,
             then calls perform(). There is no transaction across a file and
             Postgres, so a failed commit must leave an orphan ontology version
             — harmless — rather than assertions naming a version that was never
             written. The ontology store tolerates orphan versions.
2026-08-26 · The marker in CLAUDE.md names the component that is built, not the
             stage that is current. Under a flow reading nobody is "at" a stage,
             so a current-stage marker names something that does not exist. This
             supersedes the 2026-08-24 line that put a stage marker there.
2026-08-26 · The first interviews are Fareza and the Uniti team. What the first
             interview tests is the chatbot, not the subject, and a team member
             is available now. A shop owner is a different question and is not
             being answered yet; no date is set for an interview outside the
             team.
2026-08-26 · The map holds the logic; the log holds the history. What is stated
             about the world goes to the kernel; what is stated about how to
             read the world goes to the ontology. A rule is not a fact about the
             world — it is the frame for reading one — so putting it in the log
             is the mistake finding 2 forbids, in a subtler form. This changes
             how the 2026-08-24 line "rules and aggregates included, is recorded
             in the log" is read; that line stays as written and is superseded
             here. The cost is accepted: "what did shrinkage mean in March" moves
             out of the log, so the ontology needs a valid-time model of its own.
2026-08-26 · The directory tree names the components in CLAUDE.md. Components
             live under `components/`, tests mirror them under `tests/`. Someone
             reading the component table can find each one in the tree without
             being told the mapping, and six more arrive with a home already cut.
2026-08-26 · LinkML is the ontology serialisation. It carries both of what the
             map's readers need natively — range, cardinality and required for
             the generator; description and aliases for the agent — and every
             element gets a global URI for free.
2026-08-26 · A predicate's identity in the kernel is the `slot_uri` of its
             LinkML slot. The kernel has needed a rule for minting predicates
             since perform() was written; LinkML gives every slot a stable URI,
             so the join between map and log is not something we invent.
2026-08-26 · Derived rules do not live in LinkML itself. Its expression language
             has no control flow and so cannot aggregate; equals_expression is
             row-level and marked experimental; `rules` are validation, not
             computation. LinkML declines to be a rule language on purpose. The
             computation attaches to the slot through `annotations` and is
             compiled by the generator.
2026-08-26 · The shape of that computation is not decided yet, and deliberately
             so. Choosing it now means inventing a language before one real
             stated rule has been heard. The rules an interview produces will
             decide the shape better than a guess made today.
2026-08-26 · `slot_uri` is stable in the file but not automatically in the
             output. `gen-owl` defaults to `--use-native-uris`, which replaces
             an explicit URI with one built from the schema's own prefix, while
             `gen-shacl` honours the explicit URI with no flag at all. The two
             RDF generators disagree, and the one the map-to-log join depends on
             is the one that needs telling. The line written earlier today — a
             stable URI for free — is free in the file and costs one flag
             downstream. The ontology store carries that flag, not one command.
2026-08-26 · The interview runs in Claude Desktop with a skill and existing
             filesystem MCP access. Almost nothing is built: the conversation,
             the model and the interface are the product; the graph render is
             LinkML's own gen-erdiagram. What is built is a skill — prose, not
             code — and one seal tool.
2026-08-26 · The session draft is a file, not something internal to the chatbot.
             This supersedes the earlier line today that called it internal and
             losable: Claude Desktop has no durable memory of its own, so a
             draft can only live in the conversation or on disk, and a 90-minute
             interview will exhaust the context window before it ends. The draft
             is the working tree; sealing it is what makes a version.
2026-08-26 · The draft is the source of truth during an interview, never the
             conversation. Before adding to it the skill re-reads it, revises,
             and writes it back whole. That is also what lets a statement at
             minute 60 correct one from minute 10, and what lets an interview
             resume in a fresh chat window.
2026-08-26 · The act of turning a draft into a numbered version is called
             sealing, not committing. Git already owns the word commit in this
             repo and the two acts are unrelated.
2026-08-26 · The map lives in the PoC repo under `business/`, named as data
             rather than code, because the repo holds the system while the map
             holds one business's description of itself — separate things that
             production will have to keep apart. One file per version, flat,
             beside its transcript: `business/v1.yaml`, `business/draft.yaml`.
             ontology_version is written inside the file, never a git SHA — a
             SHA would tie kernel rows to the existence of a repository, and git
             has no valid-time axis anyway.
2026-08-26 · A version is one file rather than one overwritten file with history
             in git, because the definition-change stage needs two versions
             readable at the same moment. Reaching the old one through git would
             put a version-control system inside the report harness.
2026-08-26 · The transcript is saved at seal time, one text file beside its
             version. Under the map/log split the conversation lands nowhere,
             so "why does the map say this" would only be answerable from a chat
             window nobody can search. It is evidence, not a fact and not part
             of the map. An unsaved conversation cannot be recovered later.
2026-08-26 · Review is in business language, not a graph. Someone who has just
             described their shop cannot judge boxes and arrows. The graph is
             still rendered, but its audience is the team measuring blast
             radius, not the person being interviewed.
2026-08-26 · The seal tool validates the draft and fails loudly on invalid
             LinkML. A skill is instruction, not enforcement — it can ask for
             valid output but cannot guarantee it, so the guarantee sits in the
             one piece that is code.
2026-08-26 · The map carries two time axes of its own: `valid_from`, when a
             definition took effect in the business, and `sealed_at`, when it
             was written. The second is nearly free — a seal already happens at
             one instant — and without it a retroactive correction to a
             definition cannot be told from the definition it replaced.
2026-08-26 · Time attaches to a whole version, not to individual rules. A rule
             could carry its own period, but a structural change cannot: LinkML
             has no way to say a class existed from January to April, so
             structure needs whole versions regardless and two mechanisms are
             worse than one. Whole versions also make a chain of definitions
             coherent by construction — shrinkage over stock over movements can
             never mix a new rule with an old one it depends on — and they make
             blast radius visible as a diff of two files.
2026-08-26 · A version is chosen the way the kernel chooses a fact: among
             versions with `sealed_at <= as_of`, take those with
             `valid_from <= valid_at`, then the one sealed last. Map and log read
             time the same way rather than two ways.
2026-08-26 · A report takes two pairs, not one: facts=(valid_at, as_of) and
             definition=(valid_at, as_of), each resolved by the same rule, equal
             by default. Collapsing them into one pair supports an ordinary
             report and the definition-of-done demo as a special case; keeping
             them separate supports the whole class. `ontology_version`
             disappears as a parameter — it is derived from the definition pair.
2026-08-26 · Moving one pair while holding the other is what decomposes a
             difference: facts alone isolate data and corrections, definition
             alone isolates the definition change, both give the total. "Why the
             numbers differ" becomes three calls, not an interpretation.
2026-08-26 · Facts with no home in the definition being applied are reported
             beside the numbers, not raised as an error. A counterfactual report
             is the point, so failing loudly defeats it; passing silently hides
             a real cause. An orphaned predicate is one of the reasons a number
             moved.
2026-08-26 · `slot_uri` is stable across renames: a rename changes a label, not
             an identity. This is why `gen-owl` must be called with
             `--no-use-native-uris` — a URI derived from the schema's own naming
             would change with every rename and orphan every fact recorded
             before it. The flag is an invariant, not a detail of one command.
2026-08-26 · A sealed version is never edited or deleted; correcting one means
             sealing a version that supersedes it. One `as_of` reads both
             stores, so a store that can be edited in place makes `as_of` lie.
2026-08-26 · Version metadata lives in the schema's own `annotations`:
             valid_from, sealed_at, supersedes, transcript. The probe showed
             annotations survive every generator, so the map needs no sidecar
             file to carry its own history.
2026-08-26 · One seal is one intent, so perform() is called once with every fact
             from the session rather than once per fact. The two stores have no
             shared transaction, so a per-fact loop could leave half a session
             permanently in an append-only log — worse than the orphan version
             already accepted. One call makes a partial write impossible; the
             remaining failure modes are an orphan version file and orphan
             predicate entities, both harmless.
2026-08-26 · Facts stated in an interview inherit their `valid_from` from the
             map version being sealed, not from the moment of the interview.
             perform() defaults valid_from to the intent's occurred_at, which
             would date the whole business from the day it was described and
             leave every earlier period empty. The map claims to describe the
             business from a given date; its facts start at the same boundary.
2026-08-26 · Access is through the filesystem MCP already in use — no API and no
             new MCP server. The skill writes the draft as a file directly; seal
             is a script invoked the same way. Anything more is infrastructure
             built before a single interview has happened.
2026-08-27 · `valid_from` is required on a draft. `seal` refuses a draft without
             one, exits non-zero and writes nothing — the same rule, for the
             same reason, as its refusal of a slot with no `slot_uri`.
             Defaulting to the seal instant makes every business look born on
             the day it was described and leaves every earlier period empty;
             defaulting to an unbounded past claims more than anyone knows. The
             guess belongs in a conversation with a person present, not in a
             silent fallback in code. Recorded now because the earlier decision
             that facts inherit the version's valid_from never said what happens
             when the version itself has none — the gap was in the record, not
             in the implementation.
2026-08-27 · The conversation adapts to the person, not the other way round.
             Nobody being interviewed needs to know what an ontology is, and the
             skill never asks them to learn one. It asks about the business in
             the words the business uses; the mapping is the skill's problem.
             Stated by Fareza as a requirement on the interview and recorded
             here because it constrains the skill more than any mechanism does.
2026-08-27 · A later interview asks one question a first interview cannot: when
             a definition changes, "since when?" Without it `valid_from` has no
             answer and seal refuses the draft. That single question is the only
             behavioural difference between a first interview and every one
             after it.
2026-08-27 · Map quality is measured four ways, not judged: coverage — every
             predicate used in the log has a home in the map, which is a query;
             stability — the same person interviewed twice produces comparable
             maps; answering power — business questions written before the
             interview, answered after it; and change tolerance. Change
             tolerance is the sharpest: if moving one definition touches one
             derived rule the map is good, and if it touches a class hierarchy,
             three rules and a projection the map wrote the same fact in several
             places. One number, and the most honest test of LLM authoring we
             have.
2026-08-27 · Candidate definition changes are written after the interview and
             before the generator is touched, several of them, drawn from the
             business rather than from the map — and their costs are compared
             rather than one being picked. Designing the change in advance would
             steer the interview toward a change that is cheap, and what got
             measured would be the interviewer's staging, not the map. Comparing
             a spread removes the bias while leaving the interview plain.
2026-08-27 · Readability is measured, not assumed. Editing a map surgically
             requires a person to find the piece to change, so a 400-node map
             with no hierarchy cannot be edited surgically however good the
             viewer is. Visualisation does not rescue a bad map — it is a
             capability a bad map destroys. Blast radius and findability are the
             same property seen from two sides.
2026-08-27 · Why the map plus the log is worth its cost, recorded because the
             claim "an ontology makes an agent smarter" is usually empty and
             this one has to survive being asked. An LLM with a database schema
             already writes SQL; that is a commodity. What no ordinary system
             answers: what we believed on a past date with the knowledge of that
             date; the same report under an old definition and today's; whether
             a number moved because of data, a correction, or a definition; what
             is still unknown about a thing; and whether what was recorded is
             consistent with the rules that were stated. Five classes, four of
             which need both stores. The fourth needs the map to say what should
             be there, not only what may be — a SHACL-shaped demand, not an
             OWL-shaped one.
2026-08-27 · The PoC is run entirely as simulation: only Fareza and the team,
             role-playing a business as close to a real one as they can make it.
             No interview outside the team, and no date for one. Of the four
             quality measures, coverage, change tolerance and readability are
             properties of the artefact and survive this untouched; stability
             and answering power do not survive it unaided, because they assume
             a subject independent of the tester. The accepted cost is named
             rather than absorbed: whether an LLM can author a map from a real,
             half-articulate person stays unproven, and the T2 line in OPEN.md
             stays open by construction rather than being quietly closed by a
             simulation — which is exactly what the archived corpus did.
2026-08-27 · A one-page business brief is written before the first interview and
             frozen when it starts, and whoever plays the business does not
             write the interview skill. This is what returns stability and
             answering power to being measurable: two interviews from one brief
             can be diffed, and competency questions written against the brief
             ask about facts the map was never handed. The brief also carries
             the mess a cooperative role-player smooths away — a term used two
             ways, a rule nobody wrote down, a number two people compute
             differently. The 27 Aug line requiring candidate definition changes
             to be drawn from the business rather than the map already assumed
             something like this; under simulation the brief is the only place
             "the business" can live. Guard: one page, one hour, never revised
             after a session begins. A brief that grows between interviews has
             become a design document, which is the shape that killed four
             cycles.
2026-08-27 · The record-time spread comes from dated role-play episodes, each
             sealed at its own instant, not from live use. `perform()` already
             takes `recorded_at` and `seal()` already takes `sealed_at`; the
             25 Aug line calls replaying the acts the sanctioned way to write
             synthetic history, and an episode is an act. This supersedes the
             26 Aug line that said the spread could only come from live use —
             that was true when the only other writer was a generated form.
             It also dissolves the pressure to date facts individually:
             different dates now come from different episodes rather than from
             different facts inside one seal.
2026-08-27 · The interview skill lives in the repo at `components/interview/`
             and is uploaded to Claude Desktop by hand. It is a component like
             any other and the component table already names it; a skill living
             only in Desktop's own directory would be the one part of the system
             that is unversioned and unreviewable. The cost is accepted: the
             uploaded copy and the repo copy can drift, and nothing detects it.
2026-08-27 · The interview is deliberately not scripted. What is being tested is
             whether an ordinary conversation becomes a usable map, so a script
             would test the script. The skill carries only what the model cannot
             know: where the files go, what `seal` refuses, the traps that are
             not enforced, and that a stated rule is recorded verbatim rather
             than formalised. Everything about how to hold a conversation is
             left to the model.

2026-08-29 · The interview is deferred until the consuming components exist. For
             the PoC the map is an **input** to what is being proven, not part
             of it: what has to be shown sits at the reading end — projections,
             a generated UI, an agent finding something nobody pointed at.
             Requiring a working interview first puts the longest and least
             certain component on the critical path of every other one. The
             stage is not abandoned; it is completed after the rest of the lap
             runs. The cost is named rather than absorbed: the T2 on LLM
             authoring stays open, which under the 27 Aug simulation decision it
             already was.
2026-08-29 · A second author of the map, not a second writer. The 26 Aug line
             "only the chatbot writes the ontology" conflated composing a draft
             with writing the store. The writer is `seal` — it numbers the
             version, stamps `sealed_at`, refuses invalid LinkML, mints
             predicates from `slot_uri`. A hand-authored draft goes through the
             same gate, so versions stay linear, there is no reconciliation
             between writers, and the viewer stays read-only. That line's
             restriction on who may compose a draft is superseded; its rule
             about who writes is not.
2026-08-29 · The hand-authored draft states structure only, and no facts. Every
             fact enters through an episode instead. A seal's facts all land at
             one `recorded_at` carrying the version's `valid_from`, which is
             exactly the flat history the episodes exist to avoid, and one kind
             of thing should have one writer. `seal`'s fact path stays in the
             code for the interview later.
2026-08-29 · Facts are written through `perform()`, never by direct INSERT. The
             deny triggers refuse UPDATE, DELETE and TRUNCATE, so one wrong row
             can only be corrected by dropping the tables and rewriting the whole
             history; and the gate is also what mints entities and registers
             URIs, so a hand-written INSERT is the same work plus bookkeeping.
             Measured, not assumed: 200 assertions through the gate, one
             transaction each, cost 0.84 s.
2026-08-29 · Curated data lives in episode files outside the database, and a
             runner replays them. The whole log must be reproducible from a
             source outside Postgres, deterministically and repeatedly, because
             DROP-and-rewrite is the only correction the kernel allows. This is
             the discipline `make replay` already proves for the synthetic seed,
             applied to evidence rather than to a fixture.
2026-08-29 · A fact in an episode carries a local key, and the runner holds the
             key-to-uuid map across a whole replay. `revokes` names the id of
             another row, and an id exists only after that row is written — so a
             correction in month nine cannot reach a fact from month one by any
             other means.
2026-08-29 · One act is one `perform()` call at one `recorded_at`, following the
             25 Aug line. The record-time spread comes from the number of acts,
             not from varying the instant inside one.
2026-08-29 · The runner derives `ontology_version` by resolving the map at the
             act's clocks; it is never written in the episode file. Typed in, the
             map-to-log join is never exercised, and that join is part of what
             the PoC claims. Derived, the curated data proves the map is read on
             both time axes as a side effect of existing.
2026-08-29 · The three data sets are one log that grows, not three separate
             datasets. An `as_of` read that crosses all three is the axis being
             demonstrated; three logs would make that read meaningless.
2026-08-29 · A value whose slot declares a class as its `range` is written as
             `value_ref`; a type range stays a literal. This answers the open
             question on `seal` never writing a ref. Inventory is mostly
             relationships, so without refs the graph has nodes and no edges and
             the agent has nothing to navigate. The rule is read from the map and
             needs no new key, and both writers use the one rule — two writers
             disagreeing about which values are refs would be worse than no edges
             at all.
2026-08-29 · What writes a fact correction — answered. The runner is the second
             writer into the kernel, so a correction is an ordinary episode and
             no longer bumps the ontology version for data that moved. The
             definition-vs-data decomposition stops lying. This closes the T3
             that blocked report and diff, and it closes it because a component
             appeared, not because the argument improved.
2026-08-29 · Competency questions are written and frozen before any data is
             curated. This is the frozen-brief guard of 27 Aug moved to where
             authorship now sits: data curated first will be curated to answer
             the questions its author imagines, and the demo then validates
             itself. They are drawn from the five classes in the 27 Aug line,
             which forces the data to carry late recording, one real correction,
             one gap that is never filled, and one stated rule the recorded facts
             violate.
2026-08-29 · A hand-authored map carries a provenance note as its transcript.
             `seal` requires `annotations.transcript` to name a file that exists,
             and one page saying where the terms and the numbers came from is
             real evidence — in six weeks it is the only thing that answers why
             the map says what it says. Loosening `seal`'s contract would cost
             more and remove a guarantee.
2026-08-29 · Derived rules are in scope for the hand-authored map, so the shape
             of a rule inside `annotations` must be settled before the map is
             written. The 26 Aug line deferred that shape until a real stated
             rule had been heard; a hand-authored map is now where such a rule
             comes from, so the deferral expires rather than being overruled.
2026-08-29 · `business/` is emptied again and the hand-authored map is sealed as
             v1. The interview's v1 is three classes with no unit on either stock
             slot; keeping it as an onboarding version would force the proper map
             to build on a vocabulary nobody chose. It is committed to git before
             being removed — it is the only record of the first real session, and
             it is evidence, not a fixture.
2026-08-29 · The episode runner is a component of its own, and enters through
             `NEXT.md`. It is not part of `seal`: seal turns a description into a
             version, the runner turns curated acts into history, and the two
             fail in different ways.
2026-08-29 · The definition of done stays the shrinkage report while the design
             widens. Designing for one report makes the system narrow, but
             dropping the one concrete report leaves nothing that can falsify the
             premise — and a widening with no falsifier is the exact shape of the
             archived corpus: 2,800 lines of design and no code. Shrinkage is the
             instance, not the target. Any single concrete report would serve;
             this one is already named and already understood.
2026-08-29 · Additional target rules are chosen because their **shapes** differ,
             not because they complete the domain: stock on hand (aggregation
             over movements), shrinkage (a ratio of two derived quantities, and
             dependent on the first), a low-stock threshold (a threshold that
             produces violations, which is what exercises "is what was recorded
             consistent with the rules that were stated"), and usage rate per
             week (a windowed aggregation feeding the threshold). A rule shape
             that survives only one of the four is found out before the map is
             written rather than after.
2026-08-29 · The claim against BI is narrowed to **contested numbers**, and its
             limits are named. What warehouses already do: SCD2, daily
             snapshots, engine-level time travel, metrics as versioned code. What
             breaks: the knowledge axis dies at the ETL boundary — a correction
             is learned at the next load and SCD2 sits on dimensions, not facts,
             so the old value is overwritten; a metric version has no join to the
             numbers it produced, so "compute this on March's definition" is a
             code checkout, not a query; lineage names which table fed which,
             never whether a number moved because of data, a correction or a
             definition. Not helped, and said out loud: data quality, pipeline
             reliability, and metric sprawl. Ingestion gets more expensive, not
             less.
2026-08-29 · Month-end close is curated as a real moment: each month has a
             recorded (valid_at, as_of) pair at which its report was actually
             read. Otherwise "what did the March report say" has no referent and
             `as_of` is a number chosen at demo time, which is a performance
             rather than a demonstration. It also gives the restatement report
             its baseline — every number that moved since the last close.
2026-08-29 · One metric in one period must move for all three reasons — a
             late-recorded fact, a real correction, and a definition change.
             Spread across different metrics or different periods, the
             data-correction-definition decomposition is never exercised by the
             data that exists.
2026-08-29 · Claude Code curates the data; the competency questions are written
             here with Fareza and frozen before it starts. Curation is not done
             until it is replayed, counted and checked, and only Claude Code can
             run anything — Desktop could write 150 acts without ever knowing one
             of them landed. But an agent that invents the data must not also
             invent the questions, which is the 27 Aug guard in a new place. The
             separation is weaker than between two people — Claude Code reads the
             repo and knows what the PoC must prove — so what holds it is the
             questions being frozen first with git order as evidence, Fareza
             reading a sample, and the data being cheap to redo.
2026-08-29 · No runner for onboarding: `seal` is enough, and the draft carries
             its facts after all. The reason the earlier line today gave —
             a seal's facts all land at one `recorded_at` with one `valid_from`,
             which is a flat history — does not reach opening balances, which
             genuinely all take effect on one date and were genuinely all
             recorded in one moment. Flat is correct here. That line stands for
             a month of movements and is superseded for onboarding.
2026-08-29 · Whether a runner is needed at all is deferred until onboarding has
             been through the generator. It only becomes a question at the
             three-month stage, where one month holds many acts at different
             `valid_from` and `seal` would bump the map version for each. Deciding
             it now means deciding without the one thing that would inform it.
2026-08-29 · `episodes` leaves the component table. It was added this morning at
             Fareza's request and is removed the same day, before any code was
             written — nothing has needed it yet. If it returns it enters through
             `NEXT.md` like any other component.
2026-08-29 · Onboarding is not minimal. It must cover at least what an ERP
             inventory module holds for this business: items, units of measure,
             locations, opening balances. A thin onboarding would test the
             generator against an input no real business produces, and the
             earlier recommendation today to keep it minimal reasoned from what
             a four-turn interview happened to yield rather than from what the
             module has to hold.
2026-08-29 · Derived rules are not in v1. Stock on hand at onboarding **is** the
             opening balance; there is nothing to aggregate until movements
             exist. The shape of a derived rule inside `annotations` therefore
             stops blocking the map and moves to v2, where it will have real
             rules to be judged against. The scope decision earlier today was
             right; its timing was not.
2026-08-29 · `value_ref` is required before v1 is sealed, not after. An inventory
             module is mostly relationships — a flavour stored in a location, a
             material carrying a unit — so a map that declares them while the log
             cannot honour them is a map whose central claim is untested from the
             first day.
2026-08-29 · A one-page business profile is written and frozen before the map is:
             how many flavours, the production rhythm, who records and when,
             when stock is counted, when it is busy. It is the 27 Aug frozen
             brief moved to where authorship now sits — then it bounded what an
             interview could hear, now it bounds what curation may invent.
2026-08-29 · Three viewers for three jobs, and none of them is a component.
             `gen-erdiagram` is the working view: Mermaid, text, in the repo,
             diffable — so a v1-to-v2 map change shows up in `git diff` as a
             change in shape rather than as two pictures to compare by eye,
             which serves the definition-change demo directly. WebVOWL, via
             `gen-owl`, is the shape check: a force-directed graph makes it
             immediately visible when the map is nodes with no edges. Protégé
             with a reasoner is the only one of the three that can say the map is
             *wrong*, and it is used once at v1 and then left alone. All three
             are commands, so none enters the component table.
2026-08-29 · WebVOWL validates nothing. It renders. Saying so now because the
             temptation later will be to treat a clean picture as a passing test.
             Data validation stays `linkml-validate`; LinkML is closed-world and
             OWL is open-world, so a reasoner over `gen-owl` output will infer
             values for slots that are merely not required, without calling it an
             error.
2026-08-29 · The map stays flat: `is_a` only, no mixins, no elaborate derived
             types. A mixin-heavy schema produces a polyhierarchy that is hard to
             read, and WebVOWL supports most but not all OWL 2 constructs —
             complex datatypes among the gaps. Flatness here is not modesty about
             modelling; it is a requirement of being able to look at the result.
2026-08-29 · The business profile is set in London and written entirely in
             English, at Fareza's instruction. Nothing in the mechanics changed —
             the same nine movements with three of them never recorded, the same
             two readings of "the vanilla", the same two ways of computing
             shrinkage. One inconsistency was fixed on the way through: the first
             draft claimed eighteen recipes and described sixteen.

2026-08-30 · The competency questions are frozen in `business/questions.md`, six
             of them, written before the map exists and before any act. Q6 is
             expected to fail: two honest counts of the same freezer at the same
             `valid_at`, and the read rule breaks the tie on record time and
             returns one, which is the same overwrite an ERP performs. A set of
             questions that all pass was never a test. If Q6 turns out to have a
             good answer that is a finding; if it is quietly dropped, the
             exercise is a performance.
2026-08-30 · Every curated act must be able to name the component that would
             have written it. Onboarding is the interview and `seal`; a daily
             entry is the generated form; a correction is the form or the agent.
             An act with no writer is not a gap in the data — it is a missing
             component, and it is far cheaper to find that in a file than after
             the generator is built. `intent.source` already exists and already
             has a closed vocabulary, so this needs no new mechanism, only the
             discipline of not defaulting everything to `system_derived`.
2026-08-30 · The interview being deferred means the conversation is skipped, not
             the artefact. The hand-authored map must look like something that
             interview could have produced, imperfections included. A map that is
             tidier than any interview would yield tests the generator against an
             input it will never receive.
2026-08-30 · Curation is staged and stops to look. Onboarding, then the
             generator, then look; three months, then look; a year, then the
             agent. Curated top-down in one pass, the data would be shaped by
             what we imagine the components need, and what the first look teaches
             would cost a rewrite of a year of history rather than of one act.
2026-08-30 · At the year stage, the majority of acts must serve no question at
             all. Six questions touch perhaps ten acts out of a hundred and
             fifty; the rest is routine production and sales that illustrates
             nothing. That is not waste — a log in which every event happens to
             be interesting is not a business, and an agent set loose on one
             would find something remarkable in every direction. Not a condition
             at the onboarding stage, where there are too few acts to measure it.
2026-08-30 · `seal` takes an optional fourth fact key, `confidence`, and passes
             it to `perform()`. Profile §13 is the only place in the whole PoC
             where the business states confidence about a single fact — six of
             nineteen opening quantities were eyeballed rather than weighed —
             and Q4, frozen this morning, asks exactly that. The kernel column
             has existed since the first schema and no writer has ever set it.
             `counted` is `high`, `estimated` is `low`; `medium` is unused in v1
             because the business states two states, not three. No default: a
             fact silent about its own confidence records NULL, on the same
             reasoning as the 27 Aug refusal of a `valid_from` fallback — a
             default claims more than anyone knows. The invariant that kept
             `FACT_KEYS` closed is named rather than loosened: the ontology
             resolver's annotation reader is shallow and takes any `key: value`
             under `annotations:`, so a fact key may never collide with a
             version metadata key. `confidence` does not collide.
2026-08-30 · A quantity hangs on the thing it is a quantity of, never on the
             count that observed it, and no class receives individuals the
             profile does not name. `Pan` and `StockCount` are declared as
             classes because §4 and §6 require them, and neither gets an
             individual in v1: §13 records twenty-one pans weighed one by one
             but reports totals per flavour, so minting twenty-one pans means
             inventing twenty-one weights that happen to sum — inventing
             business — and §12 says pan numbers are reused, so a URI minted at
             onboarding is an identity the business itself cannot reproduce.
             The decisive reason for the subject rule is Q6: it can only fail
             the way it is predicted to fail if two counts compete on one
             (subject, predicate). Hung off the count, two counters produce two
             subjects, nothing competes, and the dispute dissolves instead of
             breaking. The same shape gives §11 a home — the counter staff's
             "the vanilla" is a pan slot at the display, Marta's is kilograms
             across the shop, two slots on one subject. Accepted consciously:
             location is folded into the pan slot names, which is untidy and
             stays untidy, because the 30 Aug line requires the map to look like
             something an interview produced and this is the candidate
             definition change with a real blast radius for v2. Dan's per-pan
             shrinkage cannot be computed until movements exist, which is
             correct: v1 carries no derived rule.
2026-08-30 · A unit belonging to an individual is a class and a `value_ref`; a
             unit belonging to an attribute is LinkML's own `unit` metadata on
             the slot. §6 states "Material is measured in Unit" as a
             relationship the business utters, and materials disagree — milk in
             litres, sugar in kilograms, cones in pieces — so a per-slot `unit`
             would be wrong for most of them. But §5 also states fixed units per
             attribute: a pan is weighed in kilograms, a mix is made in litres,
             a price is in pounds, and there the slot-level metadata is right.
             This is not a compromise between two mechanisms; it is a
             distinction the profile already draws. The `NEXT.md` clause "every
             quantity slot names its unit" is replaced accordingly, because one
             reading of it is unreachable.
2026-08-30 · Onboarding facts are not confined to §13. The clause "facts cover
             only §13" was written into `NEXT.md` here, and it is wrong: §13 is
             the count, but §1, §3, §4, §5 and §8 state standing master data the
             shop already holds — five locations with their temperatures, three
             named bases, two named people, a material's pack size and price and
             shelf life, which flavours are in rotation. An item master carrying
             only a name, a quantity, a unit and a location, beside a location
             master holding two of five locations, is below the floor the 29 Aug
             line set. Measured before deciding, not after: 35 of the draft's 45
             slots receive no fact and 2 of its 16 relationships are exercised.
             The ceiling stays the profile and is stated as loudly as the floor:
             no Supplier individual, because §4 says there are four and names
             none, and no counter staff, because §1 says three and names none.
             What is still empty afterwards is a gap the business has rather
             than one the map invented, and Q4 is the question that needs it.
2026-08-30 · Where a number lives, and the test that decides. Four homes, not
             two. An observation about one thing at one time is a row in
             `assertion` — 38 litres of milk on 1 September. A constraint on what
             kind of number may be said at all is the slot definition in the
             map. A policy is a row in `assertion` too, on a subject of its own.
             A definition is the map, and is the reason the map carries versions
             at all. The test between the last two: if this number changed,
             would a report about last month change with it? Marta moves the
             reorder threshold from five litres to four and last month's report
             stands, because five was the rule then — data, with its own
             `valid_from`. Marta changes what shrinkage means and the same
             events now yield a different number — map, new version, which is
             exactly Q2. The same five percent is therefore data in one place
             and map in another, and nothing about the number itself decides
             which. The map never holds a number about a thing; it holds the
             possibility of that number. `seal` enforces this literally, by
             deleting the `facts` block on the way through.
2026-08-30 · §10's six rules enter v1 as facts on a `Policy` subject, not as
             constraints inside the map. By the test above they are data: Marta
             can move a threshold without rewriting last month. §10 was the only
             section of the profile with no home anywhere in the draft, and the
             profile's own fourth line warns that §11 and §12 are the parts a
             cooperative author smooths away. The draft invented nothing, which
             was the thing being guarded against, but it smoothed §10 and §11 by
             omission instead, which was not. The rules are recorded as Marta
             states them: the sentence kept, a threshold attached only where she
             gives a number. "A flavour below five litres" carries a threshold
             and no unit, because §12 says nobody ever stated whether that means
             litres of mix or of finished gelato, and typing it as a slot would
             settle that silently. Nothing enforces any of them in v1 —
             enforcement needs a derived rule and derived rules are v2 — and
             §11's two shrinkage definitions stay out for that reason and only
             that one.
2026-08-30 · A class the business identifies gets a key; a class the business
             does not record gets nothing; the asymmetry is the finding rather
             than an omission. §4's "identified by" column is an instruction to
             the translator and it gives composites — a mix batch is a date and
             a base, a stock count a date and a location, a sale a date and a
             flavour. Those become `unique_keys` rather than `identifier`,
             because no single slot carries them, and the slots inside each key
             become required. `Pan` gets no key at all: §12 says the number on
             the tape is reused, so it does not identify, and minting a
             surrogate would bury the one fact that makes Q6 worth asking. The
             five movement classes stay keyless and entirely optional, because
             §7 records three of nine movements as "nobody" and "never", and a
             required recorder would assert that someone was there. Eleven event
             classes holding no key and no required slot was not a decision
             anyone took; this is the decision.
2026-08-31 · Coverage as the 27 Aug line defines it measures nothing, and is
             replaced by its converse. "Every predicate used in the log has a
             home in the map, which is a query" is true by construction: `seal`
             registers one entity per declared `slot_uri` whether or not
             anything ever says it, so the map's whole vocabulary enters the log
             at seal time and the query returns everything, always. Measured
             after the first real seal rather than argued: of 107 entities, 28
             are never the subject or the predicate of a stated fact — the 27
             declared slots carrying no fact, plus `uniti:uri` itself. The
             direction with content is the other one, how much of the map the
             log exercises, and it reads 22 of 49 slots ever used. That number
             can fall as well as rise, which is what a measure is for, and it is
             the one to carry into episodes. The other three measures are
             untouched; this corrects an implementation, not a judgement.
2026-08-31 · The re-evaluation has three joints, and the kernel is not one of
             them. Stepping back to think again is the shape that ended the
             previous four cycles, so this one is bounded before it starts, and
             the bound is drawn from what actually complained rather than from
             taste. Nothing has complained about the kernel: three tables,
             append-only, 57 tests, a replay identical twice in a row, 301 rows
             that survived a seal and two `make check` runs unchanged, and
             Unicode intact through Postgres. Nothing has complained about
             sealing or resolution either. What complained, and did so by being
             run rather than by being argued about, is one layer up, and it is
             three joints. First, typing: the log cannot say what a thing is,
             so the generated Pan table holds nineteen materials and every
             downstream reader must guess. Second, enforcement: `required: true`
             reaches a form as a label and stops nothing, §10's six rules are
             recorded and inert, and no constraint anywhere compares a fact
             against the map — the map describes and does not bind. Third, the
             writer: `seal` is the only one, and it writes a map version, so
             new facts cannot arrive without bumping the map, which fuses a
             schema change to a data arrival. Everything else found this week —
             rules in two homes, coverage measuring nothing, the three-hour
             hole, `Unit` widened to six — is a consequence of one of those
             three or a done condition written badly here. Widening this bound
             is Fareza's to do and takes one sentence; drifting past it is what
             this line exists to prevent.

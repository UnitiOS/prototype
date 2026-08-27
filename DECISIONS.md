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

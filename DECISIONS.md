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

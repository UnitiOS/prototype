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
  aggregate, or both with a sentence. Decided from real stated rules, not before
  · blocks: generator
- Does graph review need competency questions written by someone other than the
  ontology's author, plus one deliberately wrong concept — now that "every
  predicate in the log exists in the ontology" is a query · blocks: graph review
- Where the record-time spread the replay demo needs comes from, given that one
  interview commits at a single recorded_at · blocks: report + diff
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

## T2 — wait for a user

- Are LLMs good interviewers and bad authors? The old corpus concluded this from
  a simulation, never from a real session with a real person. Now load-bearing:
  the chatbot is the only writer of the ontology and so the only path to a
  definition change · blocks: definition change
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
  fall out of step by design · blocks: -
- Webapp framework for the generated forms · blocks: -
- Chatbot split into authoring and query, or merged behind one MCP · blocks: -
- Probed 27 Aug: `required: true` beside `identifier: true` emits no
  `sh:minCount` either, and `key: true` does — so what enforces an identifier's
  presence is the generated DDL's `NOT NULL`/`PRIMARY KEY`, not the SHACL,
  unless the map gives up the URI-forming slot · blocks: generator

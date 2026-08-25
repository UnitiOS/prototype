# Open Questions

One line each. The discussion happens in chat and is **not stored here.**

- `[T1]` answerable by trying it, under 30 minutes. Do not debate — try.
- `[T2]` only a real user can answer. Written down, waited on, not argued about.
- `[T3]` genuinely needs thought before data exists. These are few.

The `blocks:` field decides whether it may hold up this week's work.
`blocks: -` means it may not.

---

## T3 — discuss to a conclusion

- How a rule or an aggregate is recorded in the log without the log storing a
  judgement · blocks: stage 2
- Which stated rules become ontology structure, which become derived rules,
  and which need code · blocks: stage 2
- Inventory valuation in scope, or quantity movement only · blocks: stage 1
- Does stage 3 need competency questions written by someone other than the
  ontology's author, plus one deliberately wrong concept · blocks: stage 3
- Operational definition of "the kernel recorded it correctly" — every screen
  state reproducible from the log alone at some (valid_at, as_of)? · blocks: stage 6
- Isolation of two concurrent writers at the write gate; stock can go negative
  under READ COMMITTED · blocks: stage 6
- Commit order vs seq/recorded_at; audit mode leaks when a slow transaction
  inserts into the past · blocks: stage 7
- Does revocation cascade? Revoking a retraction does not resurface its target
  — NOT EXISTS never asks whether the revoker is itself revoked · blocks: -
- Nothing ties `revokes` to the same (subject, predicate); a row about Bob can
  silently remove a standing fact about Alice · blocks: -

## T2 — wait for a user

- What must already work before the first ontology is written · blocks: -
- Can business people author an ontology, or only its structure · blocks: -
- Are LLMs good interviewers and bad authors? The old corpus concluded this from
  a simulation, never from a real session with a real person · blocks: -
- Do two people describing the same business produce similar ontologies · blocks: -
- Interview subject: the Uniti team, or a real ice cream shop owner · blocks: -

## T1 — just try it

- value_literal: jsonb or text · blocks: -
- subject_key_id: came in from the archived spec, used nowhere, meaning
  unknown · blocks: -
- carry intent.channel or not · blocks: -
- final `source` vocabulary · blocks: -
- Ontology storage stack: a graph database, or a versioned file plus a
  renderer · blocks: -
- Ontology serialisation: LinkML, OWL, or plain YAML. LinkML can emit both OWL
  and SHACL · blocks: -
- Webapp framework for the generated forms · blocks: -
- Chatbot split into authoring and query, or merged behind one MCP · blocks: -

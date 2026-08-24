# Open Questions

One line each. The discussion happens in chat and is **not stored here.**

- `[T1]` answerable by trying it, under 30 minutes. Do not debate — try.
- `[T2]` only a real user can answer. Written down, waited on, not argued about.
- `[T3]` genuinely needs thought before data exists. These are few.

The `blocks:` field decides whether it may hold up this week's work.
`blocks: -` means it may not.

---

## T3 — discuss to a conclusion

- Isolation of two concurrent writers at the write gate; stock can go negative
  under READ COMMITTED · blocks: aggregate constraints
- Commit order vs seq/recorded_at; audit mode leaks when a slow transaction
  inserts into the past · blocks: audit mode
- ontology_version: content hash of a file, or "as of seq"? There is a gap
  between the assertion and the materialisation · blocks: audit replay

## T2 — wait for a user

- What must already work before the first ontology is written · blocks: -
- Can business people author an ontology, or only its structure · blocks: -
- Are LLMs good interviewers and bad authors? The old corpus concluded this from
  a simulation, never from a real session with a real person · blocks: -
- Do two people describing the same business produce similar ontologies · blocks: -

## T1 — just try it

- value_literal: jsonb or text · blocks: -
- subject_key_id: came in from the archived spec, used nowhere, meaning
  unknown · blocks: -
- carry intent.channel or not · blocks: -
- final `source` vocabulary · blocks: -

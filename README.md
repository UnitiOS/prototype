# Uniti — PoC

An append-only claim log with two time axes and per-field provenance, and a
business's own logic carried in a graph rather than in code.

> **P2 is being refactored** on branch `p2/refactor`. What is being built, in
> what order, and how to go back to an earlier state is in `REFACTOR_P2.md`.
> This README describes only what exists now.

## The mechanisms

| Component | What it is |
|---|---|
| `components/kernel` | Three append-only tables (`intent`, `entity`, `assertion`), enforced by triggers and revoked privileges. `perform()` is the only write gate; `resolve_single()` reads one fact at `(valid_at, as_of)`. |
| `components/ontology` | Which sealed map version applies at `(valid_at, as_of)`. |
| `components/seal` | The gate a draft passes to become an immutable version. Requires `valid_from`, a `slot_uri` on every slot, and a transcript. Registers every URI in the kernel. |
| `components/generator` | Columns and forms from a sealed map; `submit` writes one form into the kernel. |
| `components/compiler` | The map's `aggregate`, `parameter` and `equals_expression` rules, executed as SQL into an operational database that can be dropped and rebuilt. |
| `components/provenance` | Who stated what about a subject, when, and what was later withdrawn. |
| `packages/@uniti/core` | The seed of a shared core graph. A hypothesis, not yet a foundation. |

`components/agent` is kept for reference only while the agent layer is rebuilt.
It is not run or tested.

## Running

Needs Docker, Python 3.12 and Node 22.

```
make check    # database, kernel schema, tests, and a byte-identical replay
make test     # tests only
```

Tests run against throwaway databases (`uniti_check`, `uniti_check_ops`) and
refuse to run against any other.

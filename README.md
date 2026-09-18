# Uniti — PoC

An append-only claim log with two time axes and per-field provenance, and a
business's own logic carried in a graph rather than in code.

> **P2 is being refactored** on branch `p2/refactor`. What is being built, in
> what order, and how to go back to an earlier state is in `REFACTOR_P2.md`.
> Why it is shaped this way — what `@uniti/core` is for, how large it may grow,
> and how Studio and an agent read the graph — is in `DESIGN_NOTES.md`, which is
> reference rather than rules. This README describes only what exists now.

## The mechanisms

| Component | What it is |
|---|---|
| `components/kernel` | Three append-only tables (`intent`, `entity`, `assertion`), enforced by triggers and revoked privileges. `perform()` is the only write gate; `resolve_single()` reads one fact at `(valid_at, as_of)`. |
| `components/ontology` | Which sealed map version applies at `(valid_at, as_of)`. |
| `components/seal` | The gate a draft passes to become an immutable version. Requires `valid_from`, a `slot_uri` on every slot, and a transcript. Registers every URI in the kernel. |
| `components/generator` | Columns and forms from a sealed map; `submit` writes one form into the kernel. |
| `components/compiler` | The map's `aggregate`, `parameter` and `equals_expression` rules, executed as SQL into an operational database that can be dropped and rebuilt. |
| `components/refusal` | What every gate says when it says no: a `code` from a closed list, where, what was expected against what was there, and the repairs — each carrying the finite set of valid answers, computed from the graph. The sentence is derived from those parts, never written beside them. |
| `components/provenance` | Who stated what about a subject, when, and what was later withdrawn. |
| `components/api` | The JSON API every surface reads: the kernel's entities, actions and statements, each read at `(valid_at, as_of)`. It never decides which statement stands; that is `resolve_single`. |
| `components/modules` | Modules as directories of sealed versions. An import pins one version (`@scope/name@v1`), resolved through the store; `seal` refuses an unpinned import, one the store does not hold, or one sealed after the draft. `roles` says what core obliges and what a swap would cost; `check` runs the compiler's own readers and collects every refusal instead of stopping at the first. `python -m components.modules` lists, seals and registers. |
| `web/` | The application (React, TypeScript, Vite): the kernel explorer with its clock plane, and the module store with its timeline, versions and diffs. |
| `packages/@uniti/core` | The root module, sealed as `v1`. It holds only what a mechanism executes — today the predicate a class fact is stated under. What a core should standardise is a design still to be made. |

`components/agent` is kept for reference only while the agent layer is rebuilt.
It is not run or tested.

## Running

Needs Docker, Python 3.12 and Node 22.

```
make check    # database, kernel schema, tests, and a byte-identical replay
make test     # tests only

make dev-db      # an empty development log (uniti_dev), then the demonstration
                 # modules sealed into it and the facts stated under them
make dev-compile # every table the demonstration application can fill, into
                 # an operational store of its own (uniti_dev_ops)
make web         # build the application
make app         # API and application on http://localhost:8200
make web-dev     # frontend with live reload on http://localhost:5173 (needs `make app`)
```

Tests run against throwaway databases (`uniti_check`, `uniti_check_ops`) and
refuse to run against any other.

## The demonstration content

Everything in `tests/modules/fixtures/` is made up. Four modules — `@demo/catalog`,
`@demo/inventory`, `@demo/stock` and `@rival/stock-moves` — and the facts stated
under them exist so the mechanisms have something life-sized to run on. Each
manifest declares `purpose: demonstration`, and that word is carried onto every
intent that writes one of them, so the kernel says of itself which of its rows are
a demonstration. No component names any of it: the domain lives in the fixtures
alone.

`@rival/stock-moves` is there to make one test fair. It is a second inventory
module, written against `@uniti/core` alone, sharing not one class name, slot name
or prefix with `@demo/inventory`. `@demo/stock@v2` totals movements by naming
core's `Flow` role rather than anybody's class; `@demo/stock@v3` is the same file
below `imports`, byte for byte, pinned to the rival instead. Both produce the same
numbers from different predicates, which is the whole claim: an application written
against roles survives having a module replaced under it.

The same twenty-four movements are therefore stated twice, once in each
vocabulary — `demo_data.yaml` and `rival_data.yaml` — so the two can be compared
against one log.

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
| `components/seal` | The gate a draft passes to become an immutable version. Requires `valid_from`, a `slot_uri` on every slot, a range it can see for every slot, and a transcript, and refuses two modules in one closure declaring the same class, slot or enum name. Registers every predicate in the kernel by its full URI, expanded by the prefixes of the module that wrote it, and a class fact names the class's full URI — so two modules sharing a prefix or a class name never share a predicate or a table. Runs the draft's business examples and refuses the seal when a number comes out different, when an example is a proposal no person has agreed to, or when a column the draft computes has no number in any example; they land beside the version as `vN.examples.yaml`. |
| `components/examples` | Business examples: a few records and the numbers they must add up to, with the example itself in the business's words. Each one runs in a scratch log of its own (three temporary tables on one connection, rolled back), its records going in through the form's own door and its tables coming out through the compiler's own reader, so it sees nothing of the real log and leaves nothing in it. An example an agent writes carries `agreed: false` until a person agrees to it. `contract_refusals` is what the examples owe a draft before any runs: agreement, and a number for every computed column. `python -m components.modules examples @scope/name vN` reruns a sealed version's. |
| `components/generator` | Columns and forms from a sealed map; `submit` writes one form into the kernel. |
| `components/compiler` | The map's `aggregate`, `parameter` and `equals_expression` rules, executed as SQL into an operational database that can be dropped and rebuilt. An aggregate groups by a slot of the rows it totals, or by one of the record a row points at, written `slot.slot` — a line by the customer of the rental it is part of — and no further. |
| `components/refusal` | What every gate says when it says no: a `code` from a closed list, where, what was expected against what was there, and the repairs — each carrying the finite set of valid answers, computed from the graph. The sentence is derived from those parts, never written beside them. |
| `components/provenance` | Who stated what about a subject, when, and what was later withdrawn. |
| `components/api` | The JSON API every surface reads: the kernel's entities, actions and statements, each read at `(valid_at, as_of)`. It never decides which statement stands; that is `resolve_single`. |
| `components/modules` | Modules as directories of sealed versions. An import pins one version (`@scope/name@v1`), resolved through the store; `seal` refuses an unpinned import, one the store does not hold, or one sealed after the draft. `roles` says what core obliges and what a swap would cost; `check` runs the compiler's own readers and collects every refusal instead of stopping at the first. `catalogue` is what the store offers, computed from what was sealed and searchable; `health` is six things about one application that are doing nothing — dead terms, empty columns, empty classes, unfilled roles, lagging pins, facts it cannot see. `python -m components.modules` lists, finds, reports health, seals and registers. |
| `components/studio` | Where a version is made before it is one. A draft is `draft.yaml` in the module's own directory, and the only thing in the store that can be edited; every change to it is one step from a closed list, so nobody writes YAML. `read` says what is missing: it runs the seal's own readers and the compiler's over the draft and collects what they refuse, then hands each one back as a question with the finite set that answers it. Beside the draft, `draft.txt` records every step in order and becomes the transcript the seal copies out. The examples sit beside it as `draft.examples.yaml`, written by steps of their own (`add_example`, `record`, `expect` and their undoing); every read of the draft runs them, a failing one is a blocking hole, and a revision starts from the examples of the version it revises. Every step is taken by a person or an agent (`apply(..., actor=)`, `do ... --by agent`) and the transcript says which; only a person agrees to an example (`agree_example`), and an agent cannot change one a person agreed to. `python -m components.studio` lists drafts, shows one, enumerates the steps and performs them. `read.state` also names the classes a draft's own point at, and what those point at in turn, so the map beside them is the neighbourhood the module sits in rather than everything it pins. |
| `components/agent` | The agent that builds graphs, on whichever model it is given. Five tools over the studio — `look`, `options`, `do` (a batch of steps, stopping at the first refusal), `catalogue`, `guide` — with the actor fixed to `agent`, and none that seals or agrees: those are the person's. A turn ends as a `Reply`, a `Question`, a `Plan` or a `Proposal`, and the work goes in that order, a request each — the plan, then the examples, then the rules — which the studio keeps: no rule from an agent before the person agreed to its plan (`agree_plan`) and to an example for that table, and an example may be agreed to while its numbers still wait for their rules. A proposal the draft does not bear out is handed back to the agent before anybody sees it; what the person sees is `put_before`, the system's reading of the draft. The guide is generated from the steps, the refusal catalogue, the openings and the store's roles, and a test holds it to naming all of them. Tool arguments are flat — no unions, no maps with free keys — so any provider or a self-hosted model can write them. `python -m components.agent` prints the guide, a draft and the catalogue exactly as the agent reads them, and `rehearse SCRIPT` plays a scripted builder through the agent with no model behind it. Which model plays the builder and the accountant — a separate context that reads only the person's words and works out every number an example expects — is `config/agent.yaml`'s to say, with a budget per request; the conversation, every call included, is kept beside the draft; every call to a model is written down whole under `build/calls` (`watch FILE` reads one); `ask` makes one real request and `eval` (`make eval`) runs the tasks in `tests/agent/evals`, each three times, within a budget of its own. The web Studio talks to it through `components/api/agent.py`: a request streamed as the agent works, the conversation read back, and a seal only a person can make. |
| `web/` | The application (React, TypeScript, Vite): the kernel explorer with its clock plane, the module store with its timeline, versions and diffs, the application, the catalogue with one application's health, and the studio — the whole screen, with the conversation with the agent beside a map of the module (React Flow, laid out by dagre) where every gesture is one of the studio's steps, seen either as what is in the module or as how its numbers are worked out — with one business example's numbers followed through it, and what the agent changes marked on it as it works — and a panel for what is selected, the examples and what the machinery says. `make web-test` runs the page's own tests. |
| `packages/@uniti/core` | The root module, sealed as `v1`. It holds only what a mechanism executes — today the predicate a class fact is stated under. What a core should standardise is a design still to be made. |
| `packages/@uniti/party`, `item`, `transaction` | The library beside core (`DESIGN_NOTES.md` §15): one `Party` and one `Item` that every module points at rather than declaring its own, and the roles `Transaction` (a counterparty and a day) and `TransactionLine` (the transaction it is part of) that a module's own rental, purchase or deposit fills. No module may make a class a kind of another module's class (`kind_of_foreign_class`); it points at it with a slot. `scripts/dev_modules.py` registers every `@uniti` version into a log, in the order they were sealed. |


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
                 # (a request on @rehearsal/levels is played from a script: no model, no cost)
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

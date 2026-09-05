# Now

What is being worked on. Every item needs a done condition that can be
**executed** — if it cannot be written as a command and a result, the item is
not ready to start.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. Where the work stands more
broadly is `ROADMAP.md`.

The map is sealed — `business/sorella/v1.yaml`, `b8de674`, 21 classes and 101
slots. Sorella's master data and three digestive-biscuit movements are in the
working log, and `p_ingredient_on_hand` is computed from them by the compiler.

---

## The trial this belongs to

Agreed 5 Sep. The six 5 Sep entries in `DECISIONS.md` are the reasoning; this
is what is being built from them, and it is written out here because the
session that executes an item does not have the conversation that chose it.

**What is being tested.** That a business rule can be carried half in the graph
and half in the kernel and still execute. Measured on 5 Sep: the graph carries
six rules, the kernel carries 93 parameter values, **and not one of the 93 is
named by any rule in the graph**, so every one is inert. The crossing the
design is about has run zero times. This trial runs it once, end to end, as
small as it will go.

**The four rules**, taken from `business/sorella/profile.md` §3.4 and quoted
here so nobody has to choose again:

| | Profile | The rule, verbatim | Subject class | Slot |
|---|---|---|---|---|
| A1 | §3.4:1662 | Pistachio paste — reorder at 2 tins · Dan | `BoughtItem` | `item_reorder_level` |
| A2 | §3.4:1662 | …order 10 · Dan · **Feb 2026** — was order 6. Changed after the price rise, to buy ahead | `BoughtItem` | `item_order_quantity` |
| B | §3.4:1636 | Minimum flavours in a cabinet — 12 · Marina · **Nov 2025** — was 16 at Cotham. Cut to reduce end-of-day waste | `InternalLocation` | `location_minimum_flavours` |
| C | §3.4:1648 | Free delivery above — £120 · Marina · **Apr 2026** — was £80. Fuel and van servicing | `Business` | `free_delivery_above` |

A1 and A2 are meant to execute. **B and C are meant to stay inert** — recorded
in the kernel, named by a slot, consumed by nothing, visible in the `make
build` tables. That is not laziness: it is what makes "a parameter in the
kernel is inert until the graph names it" two columns a person can point at
instead of a sentence in `CLAUDE.md`.

**A2 carries the whole point.** Its number moved in Feb 2026 and the profile
says who moved it and why. Two compiler runs either side of that date, with
the movement data held constant, must differ — a report changing because a
rule changed and nothing else did. That is the *definition change* stage at
its smallest, and it is the stage that can kill the premise.

**The six stages**, in order. Only one is ever open.

1. The write gate can carry provenance. ← done 5 Sep
2. The four slots enter the map, sealed as `v2`. ← **open, below**
3. The numbers enter the kernel with their history, and pistachio gets enough
   movements to have a row in the balance.
4. The compiler gains one column kind, and a parameter executes.
5. Two clocks, on the rule rather than on the data.
6. What stayed inert, and `LOG.md`.

Opening more than one of these at a time is the failure `CLAUDE.md` names:
widening the work and justifying the widening in one motion. Finishing a stage
and opening the next are two acts and the second needs Fareza.

---

Stage 1 closed 5 Sep — `LOG.md`, same date. `submit()` and its CLI now carry
`authority`, `confidence`, `reason_code` and `note`, all defaulting to NULL;
67 tests pass.

## Open: stage 2 — the four slots enter the map, sealed as v2

**What this does and what it does not.** It gives the four rules a name the
graph can hold, and nothing else. No number is recorded — that is stage 3 —
and nothing executes — that is stage 4. At the end of this stage the map can
say "a bought item has a reorder level" and the log still holds none.

**Edit the draft, never a sealed version.** The source is
`business/sorella/draft.yaml`, 1,452 lines. `v1.yaml` is output: a sealed
version is never edited (`DECISIONS.md`, 26 Aug). The two differ in length only
because `seal` re-emits normalised YAML — the draft carries no `facts` block,
so this seal writes no facts to the log, only the slot URIs it registers.

**The four slots.**

| Slot | Class | Range | Note |
|---|---|---|---|
| `item_reorder_level` | `BoughtItem` | `decimal` | The unit is the item's `item_counted_in`, inherited from `Ingredient`. Do not add a unit slot beside it: §3.4 writes "reorder at 2 tins" and pistachio is counted in tins |
| `item_order_quantity` | `BoughtItem` | `decimal` | Same unit basis. "order 10" |
| `location_minimum_flavours` | `InternalLocation` | `integer` | A count of flavours in one cabinet |
| `free_delivery_above` | `Business` | `decimal` | Carries `unit: {symbol: GBP, descriptive_name: pounds}`, exactly as `item_pack_price` already does |

Each needs a `slot_uri` of `sorella:<name>` — `seal` refuses a draft with a
slot that declares none — and a description written from §3.4 rather than
invented. Most of the map's slots run to two or three sentences and say what
the business does with the thing; match that, and say in each what it is *not*:
none of these is a fact about a movement, and `item_reorder_level` is not a
minimum stock the system enforces, because §3.4 says "everything else has no
level" and 76 of the 80 bought items will carry none.

**`valid_from` stays at `2026-06-15T00:00:00Z`, unchanged from v1.** This is
the one judgement in this stage, so it is written out. v2 is not the world
changing and not a correction of an error: it is the same period described
further. Under the two-axis rule that is `valid_from` unchanged and a later
`sealed_at`, which is the same shape as a correction and is why it is safe.
`resolve_version` sorts candidates by `sealed_at` and uses `valid_from` only as
a filter (`components/ontology/resolve.py:110`), so two versions sharing a
`valid_from` are not ambiguous — the later seal wins. Leave the draft's
`annotations.valid_from` alone.

**Write a new transcript.** `seal` requires one and checks it is a file
(`seal.py:289`), and it *copies* rather than moves, so leaving `transcript:
draft.txt` pointing at v1's transcript seals a stale conversation under a
second version — `OPEN.md` already carries that as a T1. v1's own description
calls the rules with their numbers "session four"; this is that session. Write
`business/sorella/draft.txt` afresh as a provenance note for it, naming §3.4
and the four rules, and let `seal` copy it to `v2.txt`.

**Watch for this.** `seal` connects to the working log, not `uniti_check`, and
registering the four slot URIs there is the point — stage 3 cannot address a
slot the registry has never seen. The write is append-only and cannot be undone,
so read the draft diff before sealing.

**Done when all five hold:**

1. `business/sorella/v2.yaml` exists carrying `version: v2`, `supersedes: v1`,
   `valid_from` byte-identical to v1's, a later `sealed_at`, and
   `transcript: v2.txt`; `v2.txt` is the new note and not a copy of `v1.txt`.
2. `resolve_version("business/sorella", valid_at=<any instant from 2026-06-15>,
   as_of=<an instant between v1's and v2's sealed_at>)` returns **v1**, and the
   same `valid_at` with `as_of` now returns **v2**. This is the first time the
   component has had more than one version to choose between; if it cannot
   discriminate, that is a finding and belongs in `LOG.md` before anything is
   fixed.
3. The four slot URIs are in the working log's registry — one query naming all
   four and returning four rows.
4. `VERSION := v2` in the Makefile, and `make build` then `make compile` run
   clean against it. `p_ingredient_on_hand` must still read 27 / −37 / 10:
   adding vocabulary moves no number, and if it does, stop and write it down.
5. `make check` exits 0 with 67 tests.

**Not in this stage.** No number written to the kernel, no compiler change, no
new construct in the map beyond four ordinary slots. An `aggregate` or an
`equals_expression` naming any of the four belongs to stage 4, and adding one
here would put notation in a sealed map that nothing can execute — the thing
`CLAUDE.md` refuses.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.

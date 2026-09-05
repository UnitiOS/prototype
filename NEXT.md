# Now

What is being worked on. Every item needs a done condition that can be
**executed** — if it cannot be written as a command and a result, the item is
not ready to start.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. Where the work stands more
broadly is `ROADMAP.md`.

The map is sealed at `business/sorella/v2.yaml` — 21 classes, 105 slots,
superseding v1. Sorella's master data and three digestive-biscuit movements are
in the working log, and `p_ingredient_on_hand` is computed from them by the
compiler.

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

**One parameter has to carry the whole point.** Two compiler runs either side
of the date its number moved, with the movement data held constant, must differ
— a report changing because a rule changed and nothing else did. That is the
*definition change* stage at its smallest, and it is the stage that can kill
the premise. The plan named A2 for it.

Stage 3 settled that by running it. A2 cannot carry the demonstration: its
predecessor, the order quantity of 6, has no start date anywhere in the profile
and so was never recorded, leaving A2 with one value and one answer at every
clock. `item_pack_price` has two dated values and returns 170.50 at
`valid_at 2025-06-01` and 203.00 at 2026-06-16. It carries stage 5 instead. A2
stays recorded and inert, which is now a demonstration of its own — a rule
whose history the business did not keep.

**The six stages**, in order. Only one is ever open.

1. The write gate can carry provenance. ← done 5 Sep
2. The four slots enter the map, sealed as `v2`. ← done 5 Sep
3. The numbers enter the kernel with their history, and pistachio gets enough
   movements to have a row in the balance. ← done 5 Sep
4. `IngredientOnHand` gains its missing dimension, the compiler gains one
   column kind, and a parameter executes. Two changes, and they are kept
   separate in the result: the dimension is a map change that repairs a number
   already known to be wrong, the column kind is the new mechanism.
5. Two clocks, on the rule rather than on the data.
6. What stayed inert, and `LOG.md`.

Opening more than one of these at a time is the failure `CLAUDE.md` names:
widening the work and justifying the widening in one motion. Finishing a stage
and opening the next are two acts and the second needs Fareza.

---

Stage 3 closed 5 Sep — `LOG.md`, same date. Ten submissions through the write
gate, scripted in `scripts/state_stage3.sh`. `authority` goes from 0 assertions
to 6, `revokes` stays at 0, and every parameter is still inert.

It produced four results, and 6 Sep re-read one of them. `DECISIONS.md`, both
dates, carries them; the two that change what stage 4 does are:

- **`p_ingredient_on_hand` read 5.32 against a hand computation of 6**, and the
  entry calling that a missing mechanism was wrong. It is the map grouping by
  the wrong set: adding `ingredient_unit` to `IngredientOnHand` and
  `ingredient_unit: movement_unit` to the `by` of both its aggregates gives 6
  in tins and −0.68 in kilograms as two rows, with no code change at all. That
  map change is folded into stage 4.
- **Provenance is shadowed at the operational clock.** Three rows now stand for
  pistachio's pack price, and the one that wins at any clock from 15 June 2026
  is the v1 master-data row — value 203.00, correct, `authority` NULL — because
  it carries a later `valid_from` than the properly-provenanced row. Its
  `valid_from` of 2026-06-15 is simply wrong; the price took effect in
  February. This is the trial's first genuine case for a revocation, and
  `submit` has no `--revokes`. **Decide it before stage 4 opens:** revoke, or
  accept and write the limit down. 1,333 of the 1,700 v1 assertions carry that
  same adoption date, so this is one instance of a convention, not one bad row.

*No item open.* Stage 4 is next and opening it is Fareza's act.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.

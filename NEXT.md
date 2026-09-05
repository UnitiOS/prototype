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

**A2 carries the whole point.** Its number moved in Feb 2026 and the profile
says who moved it and why. Two compiler runs either side of that date, with
the movement data held constant, must differ — a report changing because a
rule changed and nothing else did. That is the *definition change* stage at
its smallest, and it is the stage that can kill the premise.

Stage 3 found a better candidate for that one job — `item_pack_price`, whose
history the profile dates in full where A2's predecessor has no date at all.
The choice is open and is Fareza's; the last paragraph of stage 3 states it.

**The six stages**, in order. Only one is ever open.

1. The write gate can carry provenance. ← done 5 Sep
2. The four slots enter the map, sealed as `v2`. ← done 5 Sep
3. The numbers enter the kernel with their history, and pistachio gets enough
   movements to have a row in the balance. ← **open, below**
4. The compiler gains one column kind, and a parameter executes.
5. Two clocks, on the rule rather than on the data.
6. What stayed inert, and `LOG.md`.

Opening more than one of these at a time is the failure `CLAUDE.md` names:
widening the work and justifying the widening in one motion. Finishing a stage
and opening the next are two acts and the second needs Fareza.

---

Stage 2 closed 5 Sep — `LOG.md`, same date. `business/sorella/v2.yaml` is
sealed, 105 slots, `supersedes: v1`, and `resolve_version` discriminated
between two versions on `as_of` for the first time.

## Open: stage 3 — the numbers enter the kernel, with their history

**What this does and what it does not.** It writes numbers, and only numbers.
Nothing is executed and no rule is read by anything — that is stage 4. At the
end of this stage the log holds parameters with two clocks and a named
authority, and every one of them is still inert.

Everything here is written through the write gate — `generate.py submit`, the
CLI stage 1 taught to carry provenance. Nothing is inserted directly. The map
is `business/sorella/v2.yaml`.

**One value is one `submit`.** `submit` takes a single `--valid-from` and a
single `--recorded-at` for the whole call, and `recorded_at` belongs to the
intent. Two values of one rule with different `valid_from` are therefore two
calls, never one. Expect roughly a dozen calls; a small shell script under
`scripts/` is fine, and it should be committed, because it is the record of
what was stated.

**No `revokes` anywhere in this stage, and `submit` deliberately has no flag
for it.** Every change below is the world changing, not us being wrong: §3.4
says a price rose and a level moved, not that anybody mis-recorded them. A
change is a new assertion with a later `valid_from`, which
`resolve_single()` already picks by `valid_from DESC`. Revocation is for a
correction, and there is none here. If a run seems to need one, stop — that is
a finding about the two axes, not a missing flag.

### The dates, and what may not be invented

`recorded_at` is **today** for everything below. The log is learning these now,
from the profile; the day the business wrote a rule on paper is a fact about
the business's paper, and belongs in `--note`. This follows the master-data
rule already in force (`DECISIONS.md`, 4 Sep: valid from the adoption date and
recorded today), and every existing Sorella assertion in the log matches it.

`valid_from` is the day the number took effect. Two rules bind:

- **A month with no day becomes the first of that month**, and `--note` must
  say the profile gave the month only. "February 2026" is
  `2026-02-01T00:00:00Z`. This is a bounded, stated approximation.
- **A start date the profile does not give is not invented.** Do not reach for
  a plausible year. Record the value the profile dates and leave the earlier
  one out, then write the gap into `LOG.md`. §3.4 dates *changes*, never
  *starts*, so the earliest value of any chain can never be dated — and the
  kernel's `valid_from` is NOT NULL. That mismatch between how a business
  records its rules and what the two-axis model demands is a result of this
  stage, and possibly its most interesting one.

### What to record

**1 — The one chain with real dates: pistachio's pack price.** §1.6:423 gives
it in full: £203.00 a tin since February 2026, up from £170.50, and £152.00
until September 2024. Subject `sorella:item_sicilian_pistachio_paste`, slot
`item_pack_price`, which already exists and already holds `203.00` valid from
2026-06-15 (the adoption date) — that row stays, it is append-only and it is
not wrong.

| Value | `valid_from` | Note |
|---|---|---|
| `203.00` | `2026-02-01` | the same value the log already holds, now dated from when it took effect |
| `170.50` | `2024-09-01` | |
| `152.00` | — | **do not write.** "until September 2024" bounds its end and gives no start |

`--authority "Terra Nostra Ingredients"` — it is the supplier's price, not
Marina's or Dan's. This is the chain stage 5's demonstration will rest on if
Fareza chooses it; see the note at the end of this item.

**2 — The four rules of the trial.** All four slots exist in v2.

| Rule | Subject | Slot | Value | `valid_from` | `--authority` |
|---|---|---|---|---|---|
| A1 | `sorella:item_sicilian_pistachio_paste` | `item_reorder_level` | `2` | see below | `Dan Farrugia` |
| A2 | same | `item_order_quantity` | `10` | `2026-02-01` | `Dan Farrugia` |
| B | `sorella:loc_cotham_cabinet` | `location_minimum_flavours` | `12` | `2025-11-01` | `Marina` |
| C | the Business entity — see 3 below | `free_delivery_above` | `120` | `2026-04-01` | `Marina` |

A1's level has never moved — §3.4:1662 says "was reorder at 2" — and the
profile gives no date for when Dan set it. §3.4's ordering preamble says he
was first asked how he picks a level on 7 June 2026. Record `2` with
`valid_from 2026-06-07`, `--confidence low`, and a note saying that is the day
it was first written down and not the day it began; that is the honest floor
the profile supports.

The predecessors of A2 (`6`), B (`16`) and C (`80`) have **no start date in
the profile** and are not written. Say so in `LOG.md`. B's predecessor carries
a second problem worth a sentence: "was 16 at Cotham" is per-location while
the current 12 is stated for cabinets generally, so the two are not the same
claim about the same subject.

**3 — Mint the Business entity.** There is none in the log: a query for
`entity_class = Business` returns nothing, so rule C has no subject to hang
on. Mint it through the same gate, `--subject sorella:business_sorella_gelato`,
with `entity_class`, `business_legal_name`, `business_trading_name`,
`business_registered_in` and `business_trading_since` taken from §1.1:37
("Sorella Gelato Ltd, trading as Sorella. Registered in England"). Ordinary
master data through a form, which `DECISIONS.md` 1 Sep already blesses. Do
this before C, and give it no `--authority`: nobody "set" the company's name.

**4 — Pistachio's movements, so the item has a row in the balance.** All from
the profile, none invented, all as `StockMovement` through `submit`:

| Profile | What happened | Movement |
|---|---|---|
| §4.1:2066 | opening count, Monday 15 June: "1 sealed, 1 open" | **2 tins** into `sorella:loc_dry_store`, out of `sorella:loc_terra_nostra_ingredients`, `happened_on 2026-06-15` — the same shape the three digestive movements already use for an opening position |
| §4.3:2537 | Tuesday 16 June, 11:20, Terra Nostra pallet | **4 tins** in, same pair of places, `happened_on 2026-06-16`. One tin was dented on the rim and accepted; that goes in `movement_note`, not in the quantity |
| §4.3:2555 | batch 2026-0838, Pistachio, 12.0 kg | the draw against it, in the unit the profile states it in — §2.3:744 gives **0.68 kg** of paste per 12.00 kg batch |

`movement_unit` is `sorella:unit_tin` for the first two. **The third is not in
tins**, and that is deliberate. §1.5:317 says a tin is counted as one tin
whether sealed or with 400 g left, so the business's own count does not
decrement on a draw — §5.1:2744 counts "5 sealed, 1 open" afterwards, which is
6, and 2 + 4 = 6 exactly. Record all three anyway and then look:

> **The hand computation is 6 tins.** If `p_ingredient_on_hand` reads 6, the
> balance ignored the kg draw and the reason must be found. If it reads 5.32,
> the balance summed tins and kilograms into one number. **Either way, change
> nothing** — no `WHERE`, no unit filter, no conversion. Write down what it
> read and why. This is the G-conversion line in `OPEN.md` made executable, and
> a repaired result would destroy the evidence.

### Done when all six hold

1. Every value above is in the working log, written through `generate.py
   submit`, each with `--authority` where the table gives one and `--note`
   naming its profile section. One query returns them with `valid_from`,
   `recorded_at`, `authority` and `ontology_version`, and every
   `ontology_version` reads `v2`.
2. `authority` is no longer NULL everywhere: the count of assertions carrying
   one goes from 0 to the number written.
3. `resolve_single()` on `item_pack_price` for pistachio returns **170.50** at
   `valid_at 2025-06-01` and **203.00** at `valid_at 2026-06-16`, both at
   `as_of` now. One parameter, two clocks, two answers.
4. `make compile` gives `p_ingredient_on_hand` a pistachio row, and what it
   reads is compared against the hand computation of 6 tins in `LOG.md`,
   whichever way it comes out.
5. The digestive-biscuit rows still read 27 / −37 / 10. New facts about a
   different item must not move them.
6. `make check` exits 0, 67 tests.

**Not in this stage.** No map change and no seal — v2 already has every slot
this needs. No compiler change. No `aggregate` or `equals_expression` naming
any of these numbers. Nothing is executed, and at the end of this stage all
five parameters are still inert, which is the correct state to be in.

**One thing for Fareza before stage 4 opens.** The plan of 5 Sep named
`item_order_quantity` as the parameter whose history would carry the two-clock
demonstration. Reading §1.6:423 for this item found something better:
`item_pack_price` has a three-step chain with real dates, needs no new slot,
and multiplied by a balance gives the value of stock on hand — one expression,
pure arithmetic, meaningful. `item_order_quantity`'s predecessor has no date at
all, so it cannot show two answers. Both are recorded here and nothing is
foreclosed; which one stage 4 executes is a decision, not a build step.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.

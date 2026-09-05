# Now

What is being worked on. Every item needs a done condition that can be
**executed** — if it cannot be written as a command and a result, the item is
not ready to start.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. Where the work stands more
broadly is `ROADMAP.md`.

---

## The question this answers

**Can one business rule be carried half in the graph and half in the kernel and
still execute?** That is the whole of it. Measured 5 Sep: the graph carried six
rules, the kernel carried 93 parameter values, and not one of the 93 was named
by any rule in the graph, so every one was inert. The crossing the design is
about had run zero times.

Everything below runs it once, end to end, **as small as it will go.** It is
not milestone one, it does not seed an operational day, and it does not repair
anything else the trial has turned up.

### What is already done

| | |
|---|---|
| **provenance** | `submit` and its CLI carry `--authority`, `--confidence`, `--reason-code`, `--note`, all defaulting to NULL · 5 Sep |
| **naming** | `v2.yaml` sealed: `item_reorder_level`, `item_order_quantity` on `BoughtItem`, `location_minimum_flavours`, `free_delivery_above` · 5 Sep |
| **numbers** | six parameter values in the kernel with two clocks and a named authority · 5 Sep |
| **substrate** | `seal --register` opens an empty log without publishing a version; `uniti_trial` holds 150 assertions, 116 entities, 11 intents, `valid_from` over seven real dates · 6 Sep |

`item_pack_price` for pistachio already returns **170.50** at
`valid_at 2025-06-01` and **203.00** at 2026-06-16, both carrying
`authority = Terra Nostra Ingredients`. The kernel half works. Nothing in the
graph reads it.

### What is left, and it is one item

The trial log holds **one** item, which is too thin to prove anything: a
parameter column with a single row cannot show that it says nothing where
nothing is stated. Widening it, giving the graph the two things it lacks, and
running the clocks is one session's work.

---

## Open: the crossing — a parameter named by the graph, executed

Four parts, in this order. They are one item because none of them is worth
running without the others.

### 1 · Six items, three with a rule and three without

The selection rule is one line of the profile, **§4.3:2537** — the Terra Nostra
pallet of 16 June, 11:20:

> 4 × 3.5 kg tins pistachio paste; 2 × 5 kg tins hazelnut paste; 2 × 5 kg bags
> cocoa 22/24; 1 × carton Base 50 (10 × 2 kg); 2 × 25 kg sacks dextrose;
> 1 × 10 kg box dark chocolate 70%.

Six items on one piece of paper. **Three carry a reorder level in §3.4 and
three are named in §3.4:1682 as having none** — "Everything else has no level.
Cocoa, chocolate, dextrose …". That contrast is the test, and it comes from the
profile rather than from a choice: a parameter column has to be right about
absence as well as presence.

Written to **`uniti_trial`** through `generate.py submit`, in a committed
script beside `scripts/state_stage3.sh`. Pistachio's rows are already there and
are not rewritten.

**Master data**, one `entity_class` and one `item_counted_in` each:

| Item | URI | counted in | `item_pack_price` §1.6 |
|---|---|---|---|
| Sicilian pistachio paste | `sorella:item_sicilian_pistachio_paste` | tin | already recorded, dated chain |
| Hazelnut paste | `sorella:item_hazelnut_paste` | tin | 142.50 |
| Cocoa 22/24 | `sorella:item_cocoa_22_24` | bag | 41.00 |
| Base 50 stabiliser | `sorella:item_base_50_stabiliser` | bag | 276.00 |
| Dextrose | `sorella:item_dextrose` | sack | 41.00 |
| Dark chocolate 70% callets | `sorella:item_dark_chocolate_70_callets` | box | 96.00 |

§1.6's buying table gives those five prices no date, so they take the adoption
date `2026-06-15` and the note says so — that is the 4 Sep rule as narrowed on
6 Sep, and this is it working rather than failing.

**The three reorder levels**, §3.4, with `--authority "Dan Farrugia"`:

| Item | Level | Order quantity | `valid_from` |
|---|---|---|---|
| Pistachio paste | 2 tins | 10 | already recorded |
| Hazelnut paste | 2 tins | 6 | `2023-01-01`, and the note says §3.4 gives the year only |
| Base 50 stabiliser | 4 bags | 1 **carton** | `2023-01-01`, same note |

The other three get **nothing**. Not a zero — nothing. §3.4 says they have no
level, and a row that reads 0 would state a rule the business does not have.

**Twelve movements**, all `sorella:loc_terra_nostra_ingredients` →
`sorella:loc_dry_store`:

- six opening positions, §4.1:2061–2069, `happened_on 2026-06-15`: dextrose 2
  sacks, Base 50 4 bags, pistachio 2 tins *(already recorded)*, hazelnut 2
  tins, cocoa 2 bags, dark chocolate 2 boxes
- six delivery lines, §4.3:2537, `happened_on 2026-06-16`: 4 tins, 2 tins, 2
  bags, **1 carton**, 2 sacks, 1 box

**Two things the script must not do.** Base 50 arrives as **1 carton** and is
counted in **bags** — §1.5 gives it two units and the map converts between them
nowhere, so the delivery is recorded as `1` with `movement_unit` carton and the
opening as `4` with unit bag. Do not multiply by ten. And §4.1 writes "1 sealed,
1 open — about 2 kg in it" and "2, one open — 13.8 kg": the number is the count
on the paper, per §1.5:317, and the words go in `movement_note`. No second
quantity is invented from them.

### 2 · The compiler learns to read a parameter

One new column kind, and it is the only new mechanism in this item. A column
whose value is a stated fact about the entity one of the key columns names:

```yaml
    annotations:
      parameter:
        value:
          of: ingredient_on_hand      # which key column names the entity
          slot: item_reorder_level    # which slot of it to read from the log
```

The compiler joins `stated` on the entity that key resolves to. **It inherits
both clocks for free** — `stated` is already resolved at `valid_at` and `as_of`
by `_STANDING` — so a parameter's history needs no machinery of its own.

Its vocabulary goes from four words to six: `parameter`, `of`, `slot`. **No
business term may enter `components/`**; the grep in done condition 6 is the
check. Where no fact is stated the column is NULL, never a zero.

Write and prove this **before** anything is sealed, against a scratch copy of
`v2.yaml` in the scratchpad. `CLAUDE.md` refuses notation a map carries that
nothing can execute, and that ordering is how the refusal is honoured.

### 3 · v3, carrying four things and nothing else

Seal the draft once, adding to `IngredientOnHand`:

| Slot | What it is |
|---|---|
| `ingredient_unit` | range `Unit`, and **added to the `by` of both `ingredient_in` and `ingredient_out`** as `ingredient_unit: movement_unit` |
| `ingredient_reorder_level` | `parameter`, `of: ingredient_on_hand`, `slot: item_reorder_level` |
| `ingredient_pack_price` | `parameter`, `of: ingredient_on_hand`, `slot: item_pack_price` |
| `ingredient_stock_value` | `equals_expression: '{ingredient_on_hand_net} * {ingredient_pack_price}'` |

`valid_from` stays `2026-06-15T00:00:00Z`, unchanged from v1 and v2 — the same
period described further is a later `sealed_at`, not a new validity (6 Sep).
Write a fresh `draft.txt` first; `seal` copies it and a stale one would seal
v2's transcript under v3. Then `seal --register business/sorella/v3.yaml` into
`uniti_trial`, and point `VERSION` in the Makefile at v3.

`ingredient_unit` and the parameter columns are **two different kinds of
change** and the `LOG.md` entry keeps them apart: the dimension repairs a number
already known to be wrong, the parameter column is the mechanism being tested.

### 4 · Two clocks, on the rule

Two `make compile` runs against `uniti_trial`, movement data identical, only
`--valid-at` differing: **2025-06-01** and **2026-06-16**.

---

### Done when all seven hold

1. `p_ingredient_on_hand` has six items. **Three carry a reorder level and
   three carry NULL** — not 0 — and the three that carry one are exactly the
   three §3.4 names.
2. Pistachio reads **6 tins** and **−0.68 kg** as two rows. Six is the hand
   computation of §4.1's "1 sealed, 1 open" plus §4.3's four delivered, and the
   5.32 of 5 Sep is gone because the dimension is there, not because anything
   filtered.
3. Base 50 appears **twice**, 4 bags and 1 carton, unconverted. That is the
   honest shape of an item the business counts in two units.
4. `ingredient_stock_value` is filled from a number that came out of the kernel
   through a name the graph gave it. **This is the sentence the whole trial
   exists to make true**, and `LOG.md` says it plainly or says why not.
5. The two runs differ, and **the only reason they differ is that a rule
   moved**: pistachio's pack price is 170.50 at the first clock and 203.00 at
   the second, so its stock value moves with it. `LOG.md` shows both tables.
6. `grep -rn -i "pistachio\|reorder\|tin\|cocoa\|stock\|ingredient" components/
   --include=*.py` finds nothing outside docstrings and comments.
7. `make check` exits 0 and `business/sorella/` holds v1, v2 and v3 and no v4.

### Not in this item

No gelato and no scope work — `p_gelato_on_hand` stays as it is and stays
wrong. No revocation, and `submit` gains no `--revokes`. No seeding of the rest
of 16 June: `scripts/seed_2026_06_16.md` enumerates it and stays a
specification for milestone one, not for this. No touching the old working log.
No HTTP and no form. Anything found on the way is written into `LOG.md` as a
finding and left alone.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.

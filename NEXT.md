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

1. The write gate can carry provenance. ← **open, below**
2. The four slots enter the map, sealed as `v2`.
3. The numbers enter the kernel with their history, and pistachio gets enough
   movements to have a row in the balance.
4. The compiler gains one column kind, and a parameter executes.
5. Two clocks, on the rule rather than on the data.
6. What stayed inert, and `LOG.md`.

Opening more than one of these at a time is the failure `CLAUDE.md` names:
widening the work and justifying the widening in one motion. Finishing a stage
and opening the next are two acts and the second needs Fareza.

---

## Open: stage 1 — the write gate can carry provenance

**Why this first.** §3.4 gives every rule a setter ("Set by: Marina", "Dan",
"The HACCP plan", "Terra Nostra Ingredients") and a reason for each change
("Cut after a wholesale complaint about the texture of a 26-day pan"). Those
are `assertion.authority` and `intent.note`. Both columns exist and neither is
reachable: `authority` is NULL on all 1,700 assertions in the working log, and
`submit()` does not accept it. Recording the four rules without this would
keep the numbers and lose the provenance, which is the half being tested.

**What is already there, so nothing needs designing.** `perform()` in
`components/kernel/perform.py:55` already takes `reason_code` and `note` on the
intent, and each assertion dict already accepts `confidence`, `authority` and
`revokes` — see its docstring at `perform.py:80`. The gap is only that
`submit()` in `components/generator/generate.py:336` does not pass them and the
CLI at `generate.py:492` does not offer them.

**Watch for this.** `recorded_at` belongs to the intent and not the assertion —
one act of recording lands at one instant. So two values of a rule that were
learned on different days are two `submit` calls, not one. Stage 3 depends on
that being true, so do not move `recorded_at` onto the assertion to make stage
3 tidier.

**Done when all four hold:**

1. `submit()` accepts `authority`, `confidence`, `reason_code` and `note` and
   passes them through to `perform()`, and the CLI offers `--authority`,
   `--confidence`, `--reason-code` and `--note`.
2. A new test under `tests/generator/` submits one value carrying
   `--authority "Marina"` and `--note`, then reads back the assertion's
   `authority` and the intent's `note` and asserts both. It runs against
   `uniti_check` like the rest of the suite, never the working log.
3. `make check` exits 0 and the test count is above 65.
4. `grep -rn "authority" components/generator/generate.py` shows the parameter
   reaching `perform()`, and no default value: a submission that names no
   authority writes NULL, because "nobody said who set this" is a fact about
   the log and must not be papered over.

**Not in this stage.** No map change, no new slot, no seal, no compiler change,
no rule recorded. Those are stages 2 to 4 and they are not open.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.

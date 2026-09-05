# Now

What is being worked on. Every item needs a done condition that can be
**executed** — if it cannot be written as a command and a result, the item is
not ready to start.

A finished item is removed once `LOG.md` carries what was run. The record of
what was done is `LOG.md` and git, never this file. Where the work stands more
broadly is `ROADMAP.md`.

The map is sealed at `business/sorella/v2.yaml` — 21 classes, 105 slots,
superseding v1. The working log holds 1,742 assertions and is **no longer the
substrate this trial runs on**: about 1,300 of them are master data stamped
with one adoption date and about 300 belong to a different business. Building
the log the trial does run on is the open item.

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
`valid_at 2025-06-01` and 203.00 at 2026-06-16. It carries the **two clocks** stage instead. A2
stays recorded and inert, which is now a demonstration of its own — a rule
whose history the business did not keep.

**The stages**, in order. Only one is ever open. They are **named**, because
one was inserted on 6 Sep and every number after it moved — `CLAUDE.md` says
why.

| Stage | What it is | |
|---|---|---|
| **provenance** | the write gate can carry who said it and why | done 5 Sep |
| **naming** | the four slots enter the map, sealed as `v2` | done 5 Sep |
| **numbers** | the values enter the kernel with their history | done 5 Sep, on a substrate since rejected |
| **substrate** | a log we built, small enough to read whole | ← **open, below** |
| **execution** | `IngredientOnHand` gains its missing dimension, the compiler gains one column kind, and a parameter executes. Two changes, kept apart in the result: the dimension repairs a number already known to be wrong, the column kind is the new mechanism | |
| **two clocks** | on the rule rather than on the data | |
| **inert** | what stayed inert, and `LOG.md` | |

Opening more than one of these at a time is the failure `CLAUDE.md` names:
widening the work and justifying the widening in one motion. Finishing a stage
and opening the next are two acts and the second needs Fareza.

---

Stage **numbers** closed 5 Sep — `LOG.md`, same date. Ten submissions through
the write gate, scripted in `scripts/state_stage3.sh`; `authority` went from 0
assertions to 6. Its script and its discipline stand. What it wrote into does
not: see below.

## Open: substrate — a log we built

**Why this exists.** The working log cannot carry this trial. Measured 5 and 6
Sep: of its 1,742 assertions, about 1,300 are master data stamped
`valid_from 2026-06-15` — the adoption date — which for most of them is not
when the fact became true, and about 300 belong to Marlow, a different business
in the same log. There is no `authority` on any of them and no revocation
anywhere. The trial is about a rule's history; running it on a store with no
history is testing on sand, and it already produced one false result — the
pack price resolving at the operational clock to a row whose `valid_from` is
simply wrong.

What is wrong is the master data, not the way anything is written. All six
movements in the log are dated by the day they happened and cite the profile
section they came from. That convention is right and carries over unchanged.

**The point is not cleanliness. It is that a log of roughly this size can be
read from end to end by a person.** 1,742 assertions of unknown provenance can
only be hoped about.

### The selection rule, stated before the data

The seed is **everything Tuesday 16 June 2026 touches** — §4.3, 62 rows across
nine sections — **plus the opening position of each thing it touches**, from
§4.1's count of the previous morning.

That rule is not chosen to make the trial pass. It is chosen because 16 June is
milestone one's own day (`ROADMAP.md`), so this seed is milestone-one work and
not a detour. Anyone can apply it to the profile and arrive at the same set.

**Nothing is dropped for being awkward.** The rule drags in, on purpose, the
cases that are expected to fail: gelato movements carrying a flavour and a
format, which is where the scope hole lives; movements in units that do not
add; §4.3's own note that *"Gloucester Road's list does not account for its own
takings"*; *"Nobody wrote a confidence against anything"*; and the cake order
whose notice rule moved that day, which is the only rule §3.4 says changed
while anybody was recording. A row that cannot be recorded is **written up as
a finding, never skipped silently.**

### The scripts must be stupid

This is the third of `CLAUDE.md`'s three baskets — passing by cheating — and it
arrives somewhere the "no business term under `components/`" rule does not
look. `scripts/` is allowed to know the business. So the bias comes in through
which rows get chosen, not through a branch, and a seed picked because it works
produces a beautiful table that proves nothing.

Four rules, all checkable:

1. **Every literal in the seed is quotable from the profile**, and its `--note`
   names the section it came from. No number is computed, derived, converted or
   rounded on the way in. If a value is not in the profile it does not go in.
2. **No branch on business identity.** A flat sequence of `submit` calls, the
   shape `scripts/state_stage3.sh` already has. No `if item == …`.
3. **The script does not know what the trial is testing.** It transcribes a
   day. It must be correct whether or not the **execution** stage ever happens,
   and it must not be adjusted later to make a downstream number come out.
4. **The `seal` change below is a general capability**, not a path that exists
   for this trial.

### The blocker to clear first

`seal()` is the only door into an empty log — it registers `uniti:uri` and
every slot URI — and it always writes a new version file, refusing to touch one
that exists. So registering `v2`'s URIs into a fresh log today means minting a
`v3` that describes nothing new.

`seal` needs a way to register a **sealed** version's URIs into a log without
writing a version file. It is a small change and it exposes something real: a
log cannot be rebuilt from a map plus a set of facts. For a ledger that may be
correct; for a trial it blocks the door.

### Where it goes

A new database, `uniti_trial`, created and schema-applied like `uniti_check`
is. Once it is seeded, `make build` and `make compile` read it instead of
`uniti`.

**The old working log is not touched.** It is append-only and it is evidence.
It stops being carried, which is what `CLAUDE.md` says about `history/` — it is
not deleted, and no assertion in it is revoked.

### Done when all seven hold

1. **The enumeration is written before anything is submitted.** Applying the
   selection rule to §4.3 and §4.1 yields a list — every entity and every
   movement, with its profile line — committed as a file. Its size is then a
   measured fact rather than a guess, and if it is too large for one sitting
   that is Fareza's call to make on a number, not a feeling.
2. `seal` can register a sealed version's URIs into a log without writing a
   version file, and `business/sorella/` still holds exactly `v1.yaml` and
   `v2.yaml` afterwards.
3. `uniti_trial` holds the seed, every fact written through `generate.py
   submit`, every `valid_from` the one the profile supports, and `authority`
   wherever the profile names who says so.
4. **No blanket dates.** A query grouping the seed by `valid_from` shows dates
   the profile gives, not one date repeated across the master data. Where the
   profile gives none, the adoption date is used and the note says so.
5. `scripts/state_stage3.sh` re-runs against `uniti_trial` unchanged and its
   six parameter values land, with `resolve_single` on `item_pack_price` still
   giving 170.50 at `valid_at 2025-06-01` and 203.00 at 2026-06-16 — and now
   with `authority` on the winning row at the second clock, because no
   blanket-dated row shadows it.
6. `make compile` runs against `uniti_trial`. The two hand computations hold:
   digestive biscuits **27 / −37 / 10** and pistachio **6 tins** against
   **0.68 kg**, still summed into 5.32 because the dimension fix belongs to the
   next stage. Every other row is reported, not tidied.
7. `make check` exits 0 at 67 tests, and `grep` finds no business term under
   `components/`.

**Not in this stage.** No map change and no seal of a new version. No compiler
change — `ingredient_unit` belongs to **execution** and adding it here would
mix a substrate result with a mechanism result. No revocation of anything in
the old log. Nothing executes any parameter, and at the end of this stage every
one of them is still inert.

---

The interview is deferred, not abandoned — see `DECISIONS.md`, 29 Aug.

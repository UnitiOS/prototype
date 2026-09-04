# Marlow Gelato — business profile

Frozen before the map is written. This file bounds what curation may invent:
nothing enters the log that this profile does not account for. It describes the
business, not the ontology — no class names, no slot names, no ranges. The
translation into LinkML is the thing being tested, so it is not done here.

Read order for a translator: things (§4) become classes, attributes (§5) become
slots with units, relationships (§6) become slots whose range is another class,
movements (§7) become classes of their own. §11 and §12 are the parts a
cooperative author would smooth away and must not.

## 1. The business

A single-branch artisan gelato shop on a high street in north London. Opened
March 2023. One production room behind the counter, one display cabinet, a small
dry store, and three freezers. The owner, Marta, does the buying and the books.
One production hand, Dan, runs the batch freezer three mornings a week. Three
part-time counter staff scoop, take payment, and write nothing down.

Sixteen flavours exist in the recipe book. The cabinet holds twelve pans, which
in practice is ten flavours, because the two best sellers take two pans each.
Two flavours are seasonal: peach runs roughly June to August, and a gingerbread
flavour runs in December only.

The shop adopts this system on **1 September 2025**. Everything before that date
exists only in a spreadsheet and in Marta's memory, and most of it is not
recoverable.

## 2. Dates that matter

| Date | What happens |
|---|---|
| 2023-03-14 | Shop opens. No records survive from before 2025. |
| 2025-08-31 | Stock counted in the evening after close, for onboarding. |
| 2025-09-01 | Opening balances take effect. The system starts here. |
| last Sunday of each month | Full stock count after close. This is month end. |
| Mon, Wed, Fri mornings | Production. |
| Friday | Supplier invoices paid, and purchases recorded. |
| Sunday evening | Dan's paper production log entered into the system. |

## 3. How gelato gets made here

Raw materials arrive from suppliers into the dry store or the chiller. Two or
three times a week Dan makes a **base mix** — a 25-litre batch of milk, cream,
sugar, milk powder, dextrose and stabiliser, pasteurised and left to age in the
chiller for at least four hours. There are two dairy bases, a white base and a
chocolate base, and a fruit sorbet base with no dairy in it.

An aged base is flavoured and run through the batch freezer. Air is whipped in,
so four litres of mix comes out as roughly five litres of gelato. That is the
**overrun**. The output is scraped into a **pan** — a steel tray holding about
five litres — which goes into the blast freezer for two hours to harden, then to
the storage freezer. Pans move to the display cabinet as the ones on display run
out. Counter staff scoop from the display.

A pan is pulled from display when it is roughly a fifth full, because it looks
poor and the scoop drags. What happens to what is left is section 11.

## 4. Things the business tracks

| Thing | One of them is | Identified by | Notes |
|---|---|---|---|
| Material | one purchasable input | name | milk, cream, sugar, cocoa, cones, cups |
| Supplier | one company sold to by | name | four of them, one for dairy |
| Flavour | one entry in the recipe book | name | 16 exist, 10 on display |
| Base | one of three mix formulas | name | white, chocolate, sorbet |
| Mix batch | one 25-litre pasteurised batch | date and base | aged in the chiller |
| Pan | one steel tray of finished gelato | a number written on tape | reused, so numbers repeat |
| Location | one place stock sits | name | see §8 |
| Stock count | one physical count | date and location | monthly, sometimes weekly |
| Sale | one day's till total per flavour | date and flavour | not per transaction |

## 5. What is known about each thing

Units are given because the business states them. Where the business does not
state a unit, that is recorded as a gap in §12 rather than filled in.

| Thing | What is known | Unit | Typical | Who knows it |
|---|---|---|---|---|
| Material | quantity on hand | litre, kg, or piece | milk 38 L, cones 900 pcs | the count |
| Material | purchase pack size | litre/kg/piece per pack | cream 1 L per carton | Marta |
| Material | price paid per pack | pounds | cream £2.80 | the invoice |
| Material | shelf life once opened | days | fresh milk 3 | Dan |
| Flavour | which base it uses | — | pistachio uses white | recipe book |
| Flavour | scoop price | pounds | £4.20, seasonal £5.50 | the menu |
| Flavour | in rotation or not | yes/no | 10 of 16 | Marta |
| Mix batch | volume made | litre | 25 | Dan's log |
| Mix batch | date pasteurised | date | — | Dan's log |
| Pan | weight when filled | kg | 2.9 | Dan's log |
| Pan | weight when pulled | kg | 0.6 | Dan's log |
| Pan | date filled | date | — | Dan's log |
| Sale | scoops sold | count | 100/day midweek | the till |
| Stock count | quantity found | same as the material | — | whoever counted |

A scoop is meant to be 80 grams. Nobody weighs one. Counter staff serve between
70 and 105 grams depending on who is holding the scoop and how hard the gelato
is. The till records a count of scoops, never a weight.

## 6. What refers to what

These are the relationships the business states out loud. A translator should
expect these to become properties pointing at another thing, not text.

| From | Relation | To |
|---|---|---|
| Flavour | is made from | Base |
| Mix batch | is a batch of | Base |
| Mix batch | was made by | a person |
| Pan | holds | Flavour |
| Pan | was filled from | Mix batch |
| Pan | sits in | Location |
| Material | is bought from | Supplier |
| Material | is measured in | Unit |
| Stock count | counted | Material or Pan |
| Stock count | happened at | Location |
| Sale | was of | Flavour |

## 7. How stock moves

| Movement | Out of | Into | Recorded by | Recorded when |
|---|---|---|---|---|
| Goods received | supplier | dry store or chiller | Marta | Friday, from the invoice |
| Base made | chiller (materials) | chiller (mix batch) | Dan, on paper | Sunday |
| Pan filled | chiller (mix batch) | blast freezer | Dan, on paper | Sunday |
| Pan moved | blast or storage | storage or display | nobody | never |
| Scoop sold | display | — | the till | next morning |
| Pan pulled | display | see §11 | nobody | never |
| Thrown out | anywhere | — | Marta, sometimes | when she remembers |
| Tasting given | display | — | nobody | never |
| Stock counted | — | — | Marta | the same evening |

Three of these nine are never recorded at all. That is not an oversight in this
profile; it is how the shop runs, and it is the reason the numbers argue.

## 8. Where stock sits

| Location | Temperature | Holds |
|---|---|---|
| Dry store | ambient | sugar, powders, cones, cups, packaging |
| Chiller | 2–4 °C | milk, cream, eggs, mix batches ageing |
| Blast freezer | −35 °C | pans hardening, two hours each |
| Storage freezer | −22 °C | pans waiting for display |
| Display cabinet | −14 °C | twelve pans, the ones being sold |

The display cabinet runs warmer on purpose so the gelato scoops properly. It is
also where gelato ages fastest. Marta knows this and has never written it down.

## 9. When things are recorded

The gap between when something happened and when the system learns it is not
noise here — it is the shape of the business.

| What | Happens | Learned |
|---|---|---|
| Sales | all day | next morning, from the till export |
| Purchases | delivery days, milk daily | Friday, when the invoice is paid |
| Production | Mon/Wed/Fri morning | Sunday evening, from paper |
| Stock counts | last Sunday of the month | the same evening |
| Waste | whenever | days later, or never |

So a delivery on Monday 3 November is learned on Friday 7 November. A pan filled
on Wednesday is learned on Sunday. And the month-end count on the last Sunday is
the only moment the shop looks at its numbers and calls them settled.

## 10. Rules the business states

Stated the way Marta says them, not as formulas. A translator should not tidy
the vagueness out — the vagueness is the finding.

- Stock should never go below zero. If it does, something was recorded wrong.
- A flavour below five litres across the whole shop should be made again.
- Fresh milk older than three days does not go into a base.
- A pan older than three weeks comes out of display, whatever is left in it.
- Never fewer than eight flavours in the cabinet, or the display looks poor.
- Shrinkage above five percent in a month means something is wrong.

The last one is the number the whole shop argues about, and §11 says why.

## 11. Words used two ways, and numbers computed two ways

**"The vanilla."** Counter staff mean what is in the display cabinet, because
that is what they can see. Marta means everything in the shop — display, storage
freezer, and any pan still in the blast freezer. When a counter staff member says
the vanilla has run out, Marta often finds two pans in the storage freezer.

**"Batch."** Dan means one 25-litre pasteurised mix. Marta means one delivery
from a supplier — a batch of cream, arriving Tuesday. Both say batch.

**Litres or kilograms.** Mix is made in litres. Pans are weighed in kilograms.
Sales are counted in scoops. Converting between them needs a density, the
density differs by flavour — chocolate is heavier than a fruit sorbet — and
nobody has ever measured it. Marta uses one number for everything.

**Overrun.** Assumed to be thirty percent. Actually runs between twenty-two and
thirty-eight, depending on the flavour and how full the batch freezer is. Nobody
measures it, and it is the single largest reason litres made and scoops sold do
not reconcile.

**Shrinkage, computed two ways.** Marta computes it for the whole shop, per
month: litres made minus litres sold, over litres made, converting scoops to
litres at 80 grams and one density. Dan computes it per pan: the weight he wrote
when he filled it, minus the weight when it was pulled, against what the till
says was sold of that flavour that week. Their numbers differ by two to four
percentage points every month. Both are honest. Neither is written down anywhere,
except that Marta's number goes into the monthly summary.

**The unwritten rule.** A pan pulled at roughly a fifth full goes one of three
ways: given away as tastings over the next two days, taken home by staff, or
thrown out. Which one happens is decided in the moment and never recorded. In
Marta's arithmetic all three are shrinkage. In Dan's, tastings are not.

## 12. What is not known, and stays not known

These are gaps to preserve, not gaps to fill. A map that answers them has
invented business.

- No history before 2025-09-01. The shop ran for two and a half years and none
  of it is recoverable.
- Density per flavour has never been measured. One number is used for all.
- Actual overrun per batch is not measured.
- Actual scoop weight is not measured.
- Supplier lot numbers are not recorded, so a bad batch of cream cannot be
  traced to the pans made from it.
- Sugar and cones in the dry store were eyeballed at the onboarding count, not
  weighed. Marta knows the numbers are approximate and used them anyway.
- Nobody has ever stated the unit for "a flavour below five litres" — litres of
  mix, or litres of finished gelato. The rule has been applied both ways.
- Pan numbers are written on tape and reused, so the same number refers to
  different pans over time.

## 13. Opening balances, counted 2025-08-31 after close

Effective 2025-09-01. Counted by Marta and Dan together over about two hours.
The freezers were counted pan by pan. The dry store was not.

| Material | Quantity | Unit | Location | Confidence |
|---|---|---|---|---|
| Fresh milk | 38 | litre | chiller | counted |
| Double cream | 24 | litre | chiller | counted |
| Skimmed milk powder | 12 | kg | dry store | counted |
| Sugar | 45 | kg | dry store | estimated |
| Dextrose | 6 | kg | dry store | counted |
| Stabiliser | 1.5 | kg | dry store | counted |
| Cocoa powder | 4 | kg | dry store | counted |
| Dark chocolate | 8 | kg | dry store | counted |
| Pistachio paste | 3 | kg | chiller | counted |
| Vanilla paste | 1.2 | kg | chiller | counted |
| Matcha powder | 0.8 | kg | dry store | counted |
| Strawberry puree | 5 | kg | chiller | counted |
| Lemons | 60 | piece | chiller | estimated |
| Hazelnut paste | 2.5 | kg | chiller | counted |
| Cones | 900 | piece | dry store | estimated |
| Cups 3 oz | 1,400 | piece | dry store | estimated |
| Cups 5 oz | 600 | piece | dry store | estimated |
| Spoons | 2,000 | piece | dry store | estimated |
| Tubs, 500 ml | 180 | piece | dry store | counted |

Twelve pans in the display cabinet and nine in the storage freezer, twenty-one
in all, weighed pan by pan:

| Flavour | Pans on display | Pans in storage | Total kg |
|---|---|---|---|
| Vanilla | 2 | 2 | 11.4 |
| Dark chocolate | 2 | 1 | 8.6 |
| Pistachio | 1 | 1 | 5.8 |
| Matcha | 1 | 0 | 2.4 |
| Strawberry sorbet | 1 | 1 | 5.2 |
| Stracciatella | 1 | 1 | 5.6 |
| Lemon sorbet | 1 | 0 | 1.9 |
| Cookies and cream | 1 | 1 | 5.9 |
| Salted caramel | 1 | 1 | 5.7 |
| Mango sorbet | 1 | 1 | 5.1 |

Six flavours in the recipe book had no stock on 31 August: peach (season ended),
tiramisu, hazelnut, raspberry sorbet, black sesame, and gingerbread. They are on
the menu board with a sticker over them.

No mix batches were in the chiller — the count was done on a Sunday and the last
production run was Friday.

---

Written 2026-08-29 for curation. Frozen when `business/draft.yaml` is created.
If something in here turns out to be wrong, it is corrected the way the business
would correct it — as a later fact, not by editing this file.

#!/usr/bin/env bash
#
# Stage 3 — the numbers enter the kernel, with their history.
#
# Ten submissions through the write gate. Nothing is inserted directly, and
# nothing here is executed by anything: at the end of this script all five
# parameters are named by a slot in v2 and read by nothing, which is the state
# stage 3 is meant to leave the log in.
#
# It is committed because it is the record of what was stated. Every value has
# a profile section in its --note, and every value the profile does not date is
# absent rather than guessed.
#
# `recorded_at` is left to default to now: the log is learning these today,
# from the profile, whatever day the business wrote them on paper. That day is
# in the note where it is known.
#
# No --revokes anywhere, and submit has no flag for one. Every change below is
# the world changing — a price rose, a level moved — not us being wrong.
#
# Run against the WORKING log:
#     scripts/state_stage3.sh
#
# Run against the throwaway one first, which is what was done:
#     UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check \
#         scripts/state_stage3.sh

set -eu

cd "$(dirname "$0")/.."
PY=.venv/Scripts/python.exe
MAP=business/sorella/v2.yaml
ACTOR=fareza

submit() {
    echo
    echo "--- $1"
    shift
    "$PY" components/generator/generate.py submit "$MAP" "$@" --actor "$ACTOR"
}


# ---------------------------------------------------------------------------
# 3. The Business entity. There is none in the log, so rule C has no subject.
#    Ordinary master data through a form: valid from the adoption date,
#    recorded today (DECISIONS.md, 4 Sep). No --authority — nobody "set" the
#    company's name.
# ---------------------------------------------------------------------------

submit "Business — master data, section 1.1" Business \
    --subject sorella:business_sorella_gelato \
    --set entity_class=Business \
    --set 'business_legal_name=Sorella Gelato Ltd' \
    --set 'business_trading_name=Sorella' \
    --set 'business_registered_in=England' \
    --set 'business_trading_since=May 2021' \
    --valid-from 2026-06-15T00:00:00Z \
    --note 'Section 1.1: Sorella Gelato Ltd, trading as Sorella, registered in England, first batch sold May 2021. Valid from the adoption date and recorded today, as all Sorella master data is. The trading-since value is a month and a year because that is how the business states it.'


# ---------------------------------------------------------------------------
# 1. The one chain with real dates: pistachio's pack price, section 1.6.
#    203.00 a tin since February 2026, up from 170.50, and 152.00 until
#    September 2024. The 152.00 is NOT written: "until September 2024" bounds
#    its end and gives no start, and valid_from is NOT NULL.
#
#    The log already holds 203.00 valid from 2026-06-15, the adoption date.
#    That row stays. It is append-only and it is not wrong.
#
#    --authority is the supplier: it is Terra Nostra's price, not Marina's.
# ---------------------------------------------------------------------------

submit "pistachio pack price — 203.00 from February 2026" BoughtItem \
    --subject sorella:item_sicilian_pistachio_paste \
    --set item_pack_price=203.00 \
    --valid-from 2026-02-01T00:00:00Z \
    --authority 'Terra Nostra Ingredients' \
    --note 'Section 1.6, prices that have moved: 203.00 a tin since February 2026, up from 170.50. The same value the log already holds from the adoption date, now dated from when it took effect. The profile gives the month and not the day, so this is the first of that month.'

submit "pistachio pack price — 170.50 from September 2024" BoughtItem \
    --subject sorella:item_sicilian_pistachio_paste \
    --set item_pack_price=170.50 \
    --valid-from 2024-09-01T00:00:00Z \
    --authority 'Terra Nostra Ingredients' \
    --note 'Section 1.6: it was 152.00 until September 2024, so 170.50 ran from then until February 2026. The profile gives the month and not the day, so this is the first of that month. The 152.00 that preceded it is not recorded: the profile bounds its end and gives it no start.'


# ---------------------------------------------------------------------------
# 2. The four rules of the trial. All four slots exist in v2 and none of them
#    is read by anything.
#
#    The predecessors of A2 (6), B (16) and C (80) have no start date in the
#    profile and are not written.
# ---------------------------------------------------------------------------

submit "A1 — pistachio reorder level, 2 tins" BoughtItem \
    --subject sorella:item_sicilian_pistachio_paste \
    --set item_reorder_level=2 \
    --valid-from 2026-06-07T00:00:00Z \
    --authority 'Dan Farrugia' \
    --confidence low \
    --note 'Section 3.4, ordering: pistachio paste, reorder at 2 tins. The level has never moved - the row reads "was reorder at 2" - and the profile gives no date for when Dan set it. 7 June 2026 is the day the ordering preamble says he was first asked how he picks a level, so it is the day it was written down and not the day it began. Confidence low for that reason. The unit is tins, which item_counted_in already says.'

submit "A2 — pistachio order quantity, 10 from February 2026" BoughtItem \
    --subject sorella:item_sicilian_pistachio_paste \
    --set item_order_quantity=10 \
    --valid-from 2026-02-01T00:00:00Z \
    --authority 'Dan Farrugia' \
    --note 'Section 3.4, ordering: pistachio paste, order 10, changed February 2026 after the price rise, to buy ahead. It was 6. The profile gives the month and not the day, so this is the first of that month. The 6 that preceded it has no start date in the profile and is not recorded.'

submit "B — Cotham cabinet minimum flavours, 12 from November 2025" InternalLocation \
    --subject sorella:loc_cotham_cabinet \
    --set location_minimum_flavours=12 \
    --valid-from 2025-11-01T00:00:00Z \
    --authority 'Marina' \
    --note 'Section 3.4, the cabinet and the counter: minimum flavours in a cabinet, 12, set by Marina November 2025, cut to reduce end-of-day waste; Aoife still disputes it. The profile gives the month and not the day, so this is the first of that month. The 16 that preceded it is not recorded: it has no start date, and "was 16 at Cotham" is a claim about one location while the 12 is stated for cabinets generally, so the two are not the same claim about the same subject.'

submit "C — free delivery above 120 from April 2026" Business \
    --subject sorella:business_sorella_gelato \
    --set free_delivery_above=120 \
    --valid-from 2026-04-01T00:00:00Z \
    --authority 'Marina' \
    --note 'Section 3.4, wholesale: free delivery above 120 pounds, set by Marina April 2026, moved on fuel and van servicing. It was 80. The profile gives the month and not the day, so this is the first of that month. The 80 that preceded it has no start date in the profile and is not recorded.'


# ---------------------------------------------------------------------------
# 4. Pistachio's movements, so the item has a row in the balance. All from the
#    profile, none invented. The same shape the three digestive movements
#    already use: valid_from is the day it happened, and no movement_kind,
#    because the log holds no MovementKind entity and minting one would state
#    a thing nobody has.
#
#    The hand computation is 6 tins: 2 + 4, and the business's own count of
#    "5 sealed, 1 open" on the closing sheet is 6. The third movement is 0.68
#    kg and not tins, deliberately.
# ---------------------------------------------------------------------------

submit "opening position, 15 June — 2 tins" StockMovement \
    --subject sorella:mov_2026_06_15_pistachio_opening \
    --set entity_class=StockMovement \
    --set movement_out_of=sorella:loc_terra_nostra_ingredients \
    --set movement_into=sorella:loc_dry_store \
    --set movement_ingredient=sorella:item_sicilian_pistachio_paste \
    --set movement_quantity=2 \
    --set movement_unit=sorella:unit_tin \
    --set happened_on=2026-06-15 \
    --set 'movement_note=Opening position. Section 4.1, dry store, Dan 05:55-07:10, counted: 1 sealed, 1 open, which is 2 tins because section 1.5 counts a tin as one tin whether it is sealed or has 400 g left in it. Origin is the supplier because section 3.2 has the pallet as Terra Nostra Ingredients to Dry store; no delivery note for it survives.' \
    --valid-from 2026-06-15T00:00:00Z \
    --note 'Section 4.1 opening count, pistachio paste, entered as a movement in the same shape as the digestive opening position.'

submit "Terra Nostra pallet, 16 June 11:20 — 4 tins" StockMovement \
    --subject sorella:mov_2026_06_16_pistachio_terra_nostra \
    --set entity_class=StockMovement \
    --set movement_out_of=sorella:loc_terra_nostra_ingredients \
    --set movement_into=sorella:loc_dry_store \
    --set movement_ingredient=sorella:item_sicilian_pistachio_paste \
    --set movement_quantity=4 \
    --set movement_unit=sorella:unit_tin \
    --set happened_on=2026-06-16 \
    --set 'movement_note=Section 4.3, Tuesday 16 June, 11:20, Terra Nostra Ingredients: 4 x 3.5 kg tins pistachio paste, on a pallet that also carried hazelnut paste, cocoa, a carton of Base 50, dextrose and dark chocolate. One tin was dented on the rim and accepted, so the quantity is four and not three; the damage is written here and not in the number.' \
    --valid-from 2026-06-16T00:00:00Z \
    --note 'Section 4.3 delivery, pistachio paste only. The other five lines of the same pallet are not entered: this stage records what pistachio needs to have a row.'

submit "batch 2026-0838, 16 June — 0.68 kg drawn" StockMovement \
    --subject sorella:mov_2026_06_16_pistachio_batch_0838 \
    --set entity_class=StockMovement \
    --set movement_out_of=sorella:loc_dry_store \
    --set movement_ingredient=sorella:item_sicilian_pistachio_paste \
    --set movement_quantity=0.68 \
    --set movement_unit=sorella:unit_kilogram \
    --set happened_on=2026-06-16 \
    --set 'movement_note=Batch 2026-0838, Pistachio, 12.0 kg into the batch freezer, section 4.3. Section 2.3 puts 0.68 kg of Sicilian pistachio paste in a 12.00 kg batch, and this is that draw, in kilograms because kilograms is the unit the page is written in. No destination: section 3.2 sends ingredients to the pasteuriser or the bench and section 1.3 names neither, which is the same silence the biscuit base run carries. Not recorded against a Batch entity: the log holds none, and minting one would state a thing nobody has.' \
    --valid-from 2026-06-16T00:00:00Z \
    --note 'Section 4.3 production, the pistachio line of batch 2026-0838. Deliberately in kilograms and not converted to tins: section 1.5 says the business counts a tin as one tin whatever is left in it, so its own count does not decrement on a draw.'

echo
echo "stage 3: 10 submissions"

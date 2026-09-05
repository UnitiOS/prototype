#!/usr/bin/env bash
#
# Six items on one piece of paper, into the trial log.
#
# The selection rule is one line of the profile, section 4.3:2537 — the Terra
# Nostra pallet of Tuesday 16 June, 11:20. Everything here is one of the six
# items on that pallet, and nothing else is. Three of the six carry a reorder
# level in section 3.4 and three are named in 3.4:1682 as having none, which is
# the contrast the trial needs: a column that reads a stated rule has to be
# right about absence as well as presence, and an absent rule is empty here
# rather than nought.
#
# Twenty-three submissions through the write gate. Nothing is inserted
# directly. Pistachio's own rows — its price chain, its level, its opening
# position and its pallet line — were written by scripts/state_stage3.sh and
# are not rewritten; what pistachio gets here is the master data that script
# did not state.
#
# Two things this deliberately does not do. Base 50 arrives as one carton and
# is counted in bags, and section 1.5 gives the map no conversion between them,
# so the delivery is 1 with unit carton and the opening is 4 with unit bag and
# neither is multiplied by ten. And where section 4.1 writes "1 sealed, 1 open
# — about 2 kg in it", the number is the count on the paper, per 1.5:317; the
# words go in movement_note and no second quantity is invented from them.
#
# `recorded_at` defaults to now: the log is learning these today, from the
# profile, whatever day the business wrote them on paper.
#
# Run against the TRIAL log, which is what it defaults to:
#     scripts/state_six_items.sh

set -eu

cd "$(dirname "$0")/.."
PY=.venv/Scripts/python.exe
MAP=business/sorella/v2.yaml
ACTOR=fareza

: "${UNITI_DSN:=postgresql://uniti:uniti@localhost:5433/uniti_trial}"
export UNITI_DSN

submit() {
    echo
    echo "--- $1"
    shift
    "$PY" components/generator/generate.py submit "$MAP" "$@" --actor "$ACTOR"
}

ADOPTED=2026-06-15T00:00:00Z
FROM=sorella:loc_terra_nostra_ingredients
INTO=sorella:loc_dry_store


# ---------------------------------------------------------------------------
# 1. Master data. One entity_class and one item_counted_in each, from section
#    1.6's Counted in column. Valid from the adoption date and recorded today,
#    as all Sorella master data is (DECISIONS.md, 4 Sep). No --authority:
#    nobody "set" what a thing is counted in.
# ---------------------------------------------------------------------------

master() {
    submit "$2 — master data, section 1.6" BoughtItem \
        --subject "$1" \
        --set entity_class=BoughtItem \
        --set "item_counted_in=$3" \
        --valid-from $ADOPTED \
        --note "Section 1.6, the buying table: $2, counted in $4. Valid from the adoption date and recorded today."
}

master sorella:item_sicilian_pistachio_paste 'Sicilian pistachio paste' sorella:unit_tin tins
master sorella:item_hazelnut_paste 'Hazelnut paste' sorella:unit_tin tins
master sorella:item_cocoa_22_24 'Cocoa 22/24' sorella:unit_bag bags
master sorella:item_base_50_stabiliser 'Base 50 stabiliser' sorella:unit_bag bags
master sorella:item_dextrose 'Dextrose' sorella:unit_sack sacks
master sorella:item_dark_chocolate_70_callets 'Dark chocolate 70% callets' sorella:unit_box boxes


# ---------------------------------------------------------------------------
# 2. The five pack prices section 1.6 gives no date for. Pistachio's is not
#    here: it has a dated chain of its own from section 1.6's "prices that have
#    moved", written by state_stage3.sh, and a blanket-dated row would shadow
#    it. The other five take the adoption date and the note says so — the 4 Sep
#    rule as narrowed on 6 Sep. --authority is the supplier, because the price
#    is theirs.
# ---------------------------------------------------------------------------

price() {
    submit "$2 pack price — $3" BoughtItem \
        --subject "$1" \
        --set "item_pack_price=$3" \
        --valid-from $ADOPTED \
        --authority 'Terra Nostra Ingredients' \
        --note "Section 1.6, the buying table: $2, £$3 per $4, prices as at 15 June 2026. The table dates nothing, so this takes the adoption date rather than a guessed one, and it is the price of the pack as it arrives and not of what is in it."
}

price sorella:item_hazelnut_paste 'Hazelnut paste' 142.50 '5 kg tin'
price sorella:item_cocoa_22_24 'Cocoa 22/24' 41.00 '5 kg bag'
price sorella:item_base_50_stabiliser 'Base 50 stabiliser' 276.00 'carton of 10 x 2 kg'
price sorella:item_dextrose 'Dextrose' 41.00 '25 kg sack'
price sorella:item_dark_chocolate_70_callets 'Dark chocolate 70% callets' 96.00 '10 kg box'


# ---------------------------------------------------------------------------
# 3. Two of the three levels section 3.4 states. The third, pistachio's, is
#    already in the log. Section 3.4 gives these two a year and no month, so
#    valid_from is the first of that year and the note says that is what it is.
#    --authority is Dan Farrugia, who set them.
#
#    The other three items of the pallet get nothing at all. Section 3.4:1682
#    names cocoa, chocolate and dextrose among the things with no written
#    level, and a row reading 0 would state a rule the business does not have.
# ---------------------------------------------------------------------------

submit "hazelnut paste — reorder at 2 tins, order 6" BoughtItem \
    --subject sorella:item_hazelnut_paste \
    --set item_reorder_level=2 \
    --set item_order_quantity=6 \
    --valid-from 2023-01-01T00:00:00Z \
    --authority 'Dan Farrugia' \
    --confidence low \
    --note 'Section 3.4, ordering: hazelnut paste, reorder at 2 tins, order 6, set by Dan, last changed 2023. The profile gives the year and nothing finer, so this is the first of that year; confidence is low for that reason and not because the number is doubted. The unit is tins, which item_counted_in already says.'

submit "Base 50 stabiliser — reorder at 4 bags, order 1 carton" BoughtItem \
    --subject sorella:item_base_50_stabiliser \
    --set item_reorder_level=4 \
    --set item_order_quantity=1 \
    --valid-from 2023-01-01T00:00:00Z \
    --authority 'Dan Farrugia' \
    --confidence low \
    --note 'Section 3.4, ordering: Base 50 stabiliser, reorder at 4 bags, order 1 carton, set by Dan, last changed 2023. The profile gives the year and nothing finer, so this is the first of that year, and confidence is low for that reason. The level is in bags and the order quantity is in cartons: item_counted_in says bags and the map has no slot for the unit an order quantity is in, so the carton is written here and nowhere else, and the 1 is not multiplied by ten.'


# ---------------------------------------------------------------------------
# 4. Five opening positions, section 4.1:2058-2069, Dan in the dry store
#    05:55 to 07:10 on 15 June. Pistachio's is already in the log. Same shape
#    as it: origin is the supplier, because section 3.2 has the pallet as Terra
#    Nostra Ingredients to Dry store and no delivery note survives for what was
#    already on the shelf. No movement_kind — the log holds no MovementKind
#    entity, and minting one would state a thing nobody has.
# ---------------------------------------------------------------------------

opening() {
    submit "opening position, 15 June — $2" StockMovement \
        --subject "sorella:mov_2026_06_15_$1" \
        --set entity_class=StockMovement \
        --set movement_out_of=$FROM \
        --set movement_into=$INTO \
        --set "movement_ingredient=$3" \
        --set "movement_quantity=$4" \
        --set "movement_unit=$5" \
        --set happened_on=2026-06-15 \
        --set "movement_note=Opening position. Section 4.1, dry store, Dan 05:55-07:10, counted: $6. The number is the count on the paper and what is written beside it stays here in the words." \
        --valid-from 2026-06-15T00:00:00Z \
        --note "Section 4.1 opening count, $2, entered as a movement in the same shape as pistachio's."
}

opening dextrose_opening 'dextrose, 2 sacks' \
    sorella:item_dextrose 2 sorella:unit_sack \
    '2, one open - 13.8 kg, weighed'
opening base_50_opening 'Base 50, 4 bags' \
    sorella:item_base_50_stabiliser 4 sorella:unit_bag \
    '4, one of them open with about a kilo in it, counted. Section 1.5 gives Base 50 two units, a bag and the carton of ten it comes in; the shelf is counted in bags'
opening hazelnut_opening 'hazelnut paste, 2 tins' \
    sorella:item_hazelnut_paste 2 sorella:unit_tin \
    '1 sealed, 1 open, counted, which is 2 tins because section 1.5 counts a tin as one tin whatever is left in it'
opening cocoa_opening 'cocoa 22/24, 2 bags' \
    sorella:item_cocoa_22_24 2 sorella:unit_bag \
    '1 sealed, 1 open - about 2 kg in it, eyeballed'
opening dark_chocolate_opening 'dark chocolate 70%, 2 boxes' \
    sorella:item_dark_chocolate_70_callets 2 sorella:unit_box \
    '1 sealed, 1 open - about 6 kg, eyeballed'


# ---------------------------------------------------------------------------
# 5. Five delivery lines, section 4.3:2537, the Terra Nostra pallet of 16 June
#    at 11:20. Pistachio's is already in the log. One line of paper is one
#    movement, and the unit is the one the line is written in: the Base 50 line
#    says one carton and is recorded as 1 carton.
# ---------------------------------------------------------------------------

delivery() {
    submit "Terra Nostra pallet, 16 June 11:20 — $2" StockMovement \
        --subject "sorella:mov_2026_06_16_$1" \
        --set entity_class=StockMovement \
        --set movement_out_of=$FROM \
        --set movement_into=$INTO \
        --set "movement_ingredient=$3" \
        --set "movement_quantity=$4" \
        --set "movement_unit=$5" \
        --set happened_on=2026-06-16 \
        --set "movement_note=Section 4.3, Tuesday 16 June, 11:20, Terra Nostra Ingredients: $6. One line of the six on the pallet." \
        --valid-from 2026-06-16T00:00:00Z \
        --note "Section 4.3 delivery, $2. The quantity and the unit are the ones the line is written in."
}

delivery hazelnut_terra_nostra 'hazelnut paste, 2 tins' \
    sorella:item_hazelnut_paste 2 sorella:unit_tin \
    '2 x 5 kg tins hazelnut paste'
delivery cocoa_terra_nostra 'cocoa 22/24, 2 bags' \
    sorella:item_cocoa_22_24 2 sorella:unit_bag \
    '2 x 5 kg bags cocoa 22/24'
delivery base_50_terra_nostra 'Base 50, 1 carton' \
    sorella:item_base_50_stabiliser 1 sorella:unit_carton \
    '1 x carton Base 50 (10 x 2 kg). It is recorded as one carton because that is what the line says. Section 1.5 has the shelf counted in bags and nothing in the map converts a carton into ten of them, so this is not multiplied and the two units stand as two rows'
delivery dextrose_terra_nostra 'dextrose, 2 sacks' \
    sorella:item_dextrose 2 sorella:unit_sack \
    '2 x 25 kg sacks dextrose'
delivery dark_chocolate_terra_nostra 'dark chocolate 70%, 1 box' \
    sorella:item_dark_chocolate_70_callets 1 sorella:unit_box \
    '1 x 10 kg box dark chocolate 70%'

echo
echo "six items: 23 submissions"

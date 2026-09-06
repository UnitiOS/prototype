#!/usr/bin/env bash
#
# The eight places and units the six-item seed already names, said out loud.
#
# Every movement scripts/state_six_items.sh and scripts/state_stage3.sh wrote
# names a place at each end and a unit for its number, and every one of those
# names is already a `value_ref` in the log. What the log does not hold is what
# any of them *is*: `entity_class` is a fact like any other and it was never
# stated for them, so a Location-ranged or Unit-ranged field offers nothing.
#
# Eight submissions, one per entity, each stating its class and its name. This
# completes the six-item seed rather than widening it: nothing here is an
# entity the seed did not already reference.
#
# `Supplier is_a Location`, so Terra Nostra is a Supplier and a Location-ranged
# field offers it alongside the dry store.
#
# Valid from the adoption date, recorded today, and no --authority: nobody
# "set" what a place is.
#
# Run against the TRIAL log, which is what it defaults to:
#     scripts/state_places_and_units.sh

set -eu

cd "$(dirname "$0")/.."
PY=.venv/Scripts/python.exe
MAP=business/sorella/v3.yaml
ACTOR=fareza

: "${UNITI_DSN:=postgresql://uniti:uniti@localhost:5433/uniti_trial}"
export UNITI_DSN

ADOPTED=2026-06-15T00:00:00Z

submit() {
    echo
    echo "--- $1"
    shift
    "$PY" components/generator/generate.py submit "$MAP" "$@" --actor "$ACTOR"
}


# ---------------------------------------------------------------------------
# 1. The two ends of every movement in the seed. Section 1.3 has the dry store
#    as a room of the business; section 3.2 has the pallet arriving from Terra
#    Nostra Ingredients, who are a supplier and so are outside.
# ---------------------------------------------------------------------------

place() {
    submit "$3 — $2" "$2" \
        --subject "$1" \
        --set "entity_class=$2" \
        --set "location_name=$3" \
        --valid-from $ADOPTED \
        --note "$4"
}

place sorella:loc_dry_store InternalLocation 'Dry store' \
    'Section 1.3: the dry store is one of the rooms. Named as a place so that a Location-ranged field can offer it; the seed has already put it at one end of eleven movements.'
place sorella:loc_terra_nostra_ingredients Supplier 'Terra Nostra Ingredients' \
    'Section 3.2: the pallet comes from Terra Nostra Ingredients. A Supplier is_a Location in the map, so this one entity is both the origin of a movement and a supplier.'


# ---------------------------------------------------------------------------
# 2. The six units the seed's numbers are written in. Section 1.5 is the list;
#    what each one means in kilograms is not stated here, because section 1.5
#    gives no conversion for most of them and inventing one is not this seed's
#    business.
# ---------------------------------------------------------------------------

unit() {
    submit "$2 — Unit" Unit \
        --subject "$1" \
        --set entity_class=Unit \
        --set "unit_name=$2" \
        --valid-from $ADOPTED \
        --note "Section 1.5, the units things are counted in: $2. Stated as a Unit so that a Unit-ranged field can offer it; the seed already writes numbers in it. No meaning in kilograms is stated: section 1.5 gives none."
}

unit sorella:unit_tin tin
unit sorella:unit_bag bag
unit sorella:unit_carton carton
unit sorella:unit_sack sack
unit sorella:unit_box box
unit sorella:unit_kilogram kilogram

echo
echo "places and units: 8 submissions"

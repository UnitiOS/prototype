"""Fill the demonstration log: one business, six months of paper, and the
corrections a business makes to what it wrote down.

The map is `business/sorella_demo/v2.yaml` and the log is whatever `UNITI_DSN`
names — `make demo-seed` points it at `uniti_demo`, which is nothing else's.

**Every write goes through `generate.submit`.** One entity is one submission,
one submission is one intent and N assertions, and there is not one `INSERT`
here: a demonstration whose own data went in through a side door would be
demonstrating a write gate that is a fiction. The cost of that is one
`perform()` per row and it is paid deliberately.

Deterministic. One RNG seed and fixed dates, so a second run into an empty log
writes the same number of assertions as the first.

**Both clocks are stated.** `recorded_at` is passed on every submission rather
than left to default, because a log recorded in one second has a second clock
that is a cliff and not an axis. What is passed comes off §3.2 of the profile,
which carries a *lag* column for every way stock moves: a pallet note is signed
at the door and reaches the tray the same day, a dairy note is left on the
chiller shelf and reaches it three days later, a fruit delivery is a text
message that evening, a till receipt sits in an envelope behind the counter for
a fortnight, and the waste sheet is weekly and filled in from memory. So a
question asked at one `valid_at` and three different `as_of` gets three
different answers, which is the entire point of there being two clocks.

**Corrections are here too, and are not changes.** A count line written wrong
and put right, a price mistyped, a delivery recorded that never arrived: each
is an assertion carrying `revokes`, and where there is nothing to put in its
place it carries no value at all. Beside them stands one price rise, which is a
new `valid_from` and revokes nothing — the world moved, and nobody was wrong.
Telling those two apart is what the log is for, so both are in it.

The facts are Sorella's own, drawn from `business/sorella/profile.md` §1.6 for
the things and their prices, §1.8 for the suppliers, and §3.2 for the ways
stock moves, its documents and its lags. The movements themselves are invented:
no such log exists, and six months of deliveries and waste is what a
demonstration needs and what nobody wrote down.

Run: .venv/Scripts/python.exe scripts/seed_demo.py
"""

import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

from generate import read_map, submit  # noqa: E402
from perform import DSN, connect  # noqa: E402
from seal import register  # noqa: E402

MAP = ROOT / "business" / "sorella_demo" / "v5.yaml"
SCHEMA = ROOT / "components" / "kernel" / "001_schema.sql"

RNG_SEED = 20260907

# When the description was adopted, which is the version's own valid_from and
# the day every standing fact about a thing, a place or a person starts from.
ADOPTED = datetime(2026, 3, 2, tzinfo=timezone.utc)

# Twenty-six weeks of paper, ending a week before today so that today's clocks
# see all of it and a write through the form lands after all of it.
FIRST_WEEK = date(2026, 3, 2)
WEEKS = 26

# The day the office had caught up to. Nothing was learned after it, because a
# log cannot have recorded tomorrow what happened today: a till receipt that
# sat in an envelope for a fortnight, and a correction found nine days after
# that, would otherwise land past the end of the window. It is a stated day
# rather than `now` so that two runs of this script agree.
LEARNED_BY = date(2026, 9, 5)

UNITS = [
    ("bags", "A bag as it arrives. Ten litres of milk, twenty-five kilograms "
             "of powder, five of cocoa — the word says nothing about how much."),
    ("cans", "A five-litre jerry can, which is how the cream comes."),
    ("sacks", "A twenty-five kilogram paper sack."),
    ("tins", "A sealed tin: three and a half kilograms of pistachio paste."),
    ("cartons", "A carton of ten two-kilogram bags of stabiliser."),
    ("pails", "A seven-kilogram pail, warmed before it pours."),
    ("trays", "A tray as the farm stacks it. Nobody weighs one."),
    ("boxes", "A box as it comes off the van, which is not a standard size."),
    ("tubs", "A sealed tub, frozen or chilled depending on what is in it."),
    ("cases", "A case as the wholesaler sells it."),
    ("kilos", "A kilogram on the scale. What goes in the bin is weighed, "
              "whatever it arrived as."),
]

PEOPLE = [
    ("Dan Farrugia", "Head gelatiere, four days"),
    ("Marina Devlin", "Owner; the ordering and the monthly count"),
    ("Aoife Byrne", "Shop manager, Cotham"),
]

INTERNAL = [
    ("Dry store", "Ambient racking off the kitchen: sugar, dextrose, powder, "
                  "cartons of stabiliser, cocoa and pistachio", "Ambient"),
    ("Walk-in chiller", "The cold room off the kitchen: milk, cream, fruit "
                        "and the eggs", "2 to 4 degrees"),
    ("Ingredient freezer", "The upright off the kitchen: purées and anything "
                           "that arrives frozen", "-18 degrees"),
]

OUTSIDE = [
    ("Kitchen bin", "Where waste goes. Three bags a week, weighed"),
    ("Staff", "Where a thing goes when somebody takes it home, with permission"),
    ("Tastings", "Where a thing goes when it is opened for a trade customer or "
                 "a school visit and does not come back"),
    ("Production", "The kitchen production area: pasteuriser, batch freezers and churn bench"),
]

# name, brings, where, rhythm, lead time — and then the paper: what the
# document is, how many days after the delivery it reaches whoever records it,
# the kernel's word for where the statement came from, how sure it is, and who
# is standing behind it. All five come out of §3.2's own document and lag
# columns; not one of them is invented here.
SUPPLIERS = [
    ("Terra Nostra Ingredients", "Dry goods, pastes and the stabiliser",
     "Watford", "A pallet every second Tuesday", "Two working days from the order",
     "The printed note, two copies, signed at the door", (0,),
     "document_extracted", "high"),
    ("Whitehall Dairy", "Milk and cream", "Somerset",
     "Three mornings a week", "Next day",
     "Whitehall's own note, left on the chiller shelf. Nothing is ever checked "
     "against it", (0, 3, 3),
     "document_extracted", "medium"),
    ("Severn Catering Supplies", "Sugar, powder, biscuits and the chilled goods",
     "Avonmouth", "Thursdays", "Three days",
     "The driver's hand-held, signed with a finger, and a docket left behind",
     (0, 1), "document_extracted", "high"),
    ("Kingsdown Fruit Farm", "Fruit, in season", "Chew Valley",
     "Twice a week from May to September", "None; it is left at the door",
     "Nothing. Kingsdown text Marina a number of trays and a price, and the "
     "text is the only record that anything arrived", (0, 1),
     "human_stated", "low"),
    ("Bristol Cash & Carry", "Whatever the kitchen has run out of",
     "Bedminster", "When somebody drives over", "None",
     "The till receipt, in the envelope behind the Cotham till", (7, 10, 14),
     "human_confirmed", "low"),
]

KINDS = [
    ("Delivery in",
     "A driver arrives, someone counts the packs against the note and signs it",
     "The duplicate delivery note, signed by whoever took it"),
    ("Transfer between stores",
     "A thing moves from the dry store to the chiller or back, because it was "
     "opened or because it was put in the wrong one",
     "Nothing"),
    ("Used in production",
     "Ingredients taken from storage into production to make gelato batches",
     "The daily production sheet, signed by Dan Farrugia"),
    ("Thrown away",
     "A bag, a pail or an opened tin goes in the bin: out of date, split, or "
     "left out overnight",
     "The waste sheet. It is weighed, not counted"),
    ("Taken by staff",
     "Somebody takes a pack home, with permission",
     "The waste sheet"),
    ("Used for tastings",
     "A tin is opened for a trade customer or a school visit and does not come "
     "back",
     "The waste sheet, if whoever opened it remembers"),
]

# The kitchen production sheet is filled in daily by Dan Farrugia as batches are churned.
PRODUCTION_PAPER = ("The daily production sheet, signed by Dan Farrugia",
                    (0, 1), "document_extracted", "high")

# The waste sheet is weekly and filled in from memory, so everything on it is
# written down between a day and six days after it happened, by whoever was
# closing, and nobody would call it certain.
WASTE_PAPER = ("The kitchen waste sheet, filled in at the end of the week from "
               "memory", (1, 2, 3, 4, 5, 6), "human_stated", "low")

# A transfer between two of our own places is on no document at all. It is
# entered the same day by whoever moved the thing, and there is no authority
# to name, because nobody signed anything.
TRANSFER_PAPER = (None, (0,), "human_stated", "low")

# name, counted in, supplier, price per pack, reorder level, note, where it lives
ITEMS = [
    ("Whole milk, kitchen", "bags", "Whitehall Dairy", "8.90", "4",
     "A bag is ten litres, bag-in-box", "Walk-in chiller"),
    ("Whipping cream 38%", "cans", "Whitehall Dairy", "14.60", "3",
     None, "Walk-in chiller"),
    ("Caster sugar (sucrose)", "sacks", "Severn Catering Supplies", "24.50", "4",
     None, "Dry store"),
    ("Dextrose", "sacks", "Terra Nostra Ingredients", "41.00", "2",
     None, "Dry store"),
    ("Skimmed milk powder", "bags", "Severn Catering Supplies", "62.00", "2",
     "A bag here is twenty-five kilograms, not ten litres", "Dry store"),
    ("Base 50 stabiliser", "cartons", "Terra Nostra Ingredients", "276.00", "2",
     "A carton is ten two-kilogram bags; the dry store counts cartons "
     "and the bench counts bags", "Dry store"),
    ("Sicilian pistachio paste", "tins", "Terra Nostra Ingredients", "203.00", "2",
     None, "Dry store"),
    ("Cocoa 22/24", "bags", "Terra Nostra Ingredients", "4.10", "2",
     "A bag is five kilograms", "Dry store"),
    ("Glucose syrup", "pails", "Terra Nostra Ingredients", "58.00", "2",
     "A pail is seven kilograms and is warmed before it pours", "Dry store"),
    ("Inulin", "bags", "Terra Nostra Ingredients", "46.00", "2",
     None, "Dry store"),
    ("Piedmont hazelnut paste", "tins", "Terra Nostra Ingredients", "187.00", "2",
     None, "Dry store"),
    ("Vanilla paste", "tins", "Terra Nostra Ingredients", "96.00", "1",
     None, "Dry store"),
    ("Lemons", "trays", "Kingsdown Fruit Farm", "18.00", "2",
     "A tray is about five kilograms and nobody weighs it", "Walk-in chiller"),
    ("Strawberries", "trays", "Kingsdown Fruit Farm", "22.50", "2",
     None, "Walk-in chiller"),
    ("Rhubarb", "boxes", "Kingsdown Fruit Farm", "16.00", "2",
     None, "Walk-in chiller"),
    ("Raspberry purée", "tubs", "Terra Nostra Ingredients", "34.00", "2",
     "Frozen. It goes straight into the ingredient freezer", "Ingredient freezer"),
    ("Free-range eggs", "trays", "Severn Catering Supplies", "9.80", "3",
     "A tray is thirty", "Walk-in chiller"),
    ("Ricotta", "tubs", "Severn Catering Supplies", "12.40", "2",
     None, "Walk-in chiller"),
    ("Digestive biscuits", "cases", "Severn Catering Supplies", "21.00", "2",
     "Crushed for the biscuit base", "Dry store"),
    ("Sea salt", "sacks", "Bristol Cash & Carry", "11.50", "1",
     None, "Dry store"),
]

# Which weekdays each supplier comes on, and — for the fortnightly pallet and
# the seasonal fruit — when they come at all.
DELIVERY_DAYS = {
    "Terra Nostra Ingredients": (1,),
    "Whitehall Dairy": (0, 2, 4),
    "Severn Catering Supplies": (3,),
    "Kingsdown Fruit Farm": (1, 4),
    "Bristol Cash & Carry": (5,),
}
FORTNIGHTLY = ("Terra Nostra Ingredients",)
IN_SEASON = {"Kingsdown Fruit Farm": (5, 6, 7, 8)}
CHANCE = {"Whitehall Dairy": 0.85, "Bristol Cash & Carry": 0.30}
DEFAULT_CHANCE = 0.75

# The one thing whose price moves inside the window, and it is a change and not
# a correction: nothing was wrong, the price then was the price then. §1.6 has
# it at three prices in two years.
PRICE_RISE = ("Sicilian pistachio paste", date(2026, 6, 8), "214.00",
              "Terra Nostra invoice, 8 June")

# The price that was typed wrong on the day the description was adopted, and
# put right three weeks later. A bag of cocoa is forty-one pounds and was
# always forty-one pounds; the four-pounds-ten in the log is the log being
# wrong, so the row that replaces it revokes it and is valid from the same day.
PRICE_TYPO = ("Cocoa 22/24", date(2026, 3, 23), "41.00",
              "Terra Nostra invoice, checked against the statement")

# The price nobody could find a document for, so it was withdrawn with nothing
# to put in its place. The cell it fills goes empty rather than to nought.
PRICE_WITHDRAWN = ("Sea salt", date(2026, 4, 14))

# Conversion factors to standard base unit (kilograms).
# Every ingredient has a conversion from its primary packaging unit to kg,
# and Base 50 also has a conversion from loose bags (2 kg) to kg.
# For items already measured in kg or where 1 kg = 1 kg, factor is 1.0.
CONVERSIONS = [
    ("Whole milk, kitchen", "bags", "10.3"),       # 10 L bag-in-box * 1.03 density = 10.3 kg
    ("Whole milk, kitchen", "kilos", "1.0"),
    ("Whipping cream 38%", "cans", "5.0"),        # 5 L can * 1.00 density = 5.0 kg
    ("Whipping cream 38%", "kilos", "1.0"),
    ("Caster sugar (sucrose)", "sacks", "25.0"),  # 25 kg sack
    ("Caster sugar (sucrose)", "kilos", "1.0"),
    ("Dextrose", "sacks", "25.0"),                # 25 kg sack
    ("Dextrose", "kilos", "1.0"),
    ("Skimmed milk powder", "bags", "25.0"),      # 25 kg bag
    ("Skimmed milk powder", "kilos", "1.0"),
    ("Base 50 stabiliser", "cartons", "20.0"),    # carton of 10 x 2kg bags = 20 kg
    ("Base 50 stabiliser", "bags", "2.0"),        # bench bag = 2 kg
    ("Base 50 stabiliser", "kilos", "1.0"),
    ("Sicilian pistachio paste", "tins", "3.5"),   # 3.5 kg tin
    ("Sicilian pistachio paste", "kilos", "1.0"),
    ("Cocoa 22/24", "bags", "5.0"),               # 5 kg bag
    ("Cocoa 22/24", "kilos", "1.0"),
    ("Glucose syrup", "pails", "7.0"),            # 7 kg pail
    ("Glucose syrup", "kilos", "1.0"),
    ("Inulin", "bags", "5.0"),                    # 5 kg bag
    ("Inulin", "kilos", "1.0"),
    ("Piedmont hazelnut paste", "tins", "5.0"),   # 5 kg tin
    ("Piedmont hazelnut paste", "kilos", "1.0"),
    ("Vanilla paste", "tins", "1.0"),             # 1 kg tin
    ("Vanilla paste", "kilos", "1.0"),
    ("Lemons", "trays", "5.0"),                   # 5 kg tray
    ("Lemons", "kilos", "1.0"),
    ("Strawberries", "trays", "2.0"),             # 2 kg tray
    ("Strawberries", "kilos", "1.0"),
    ("Rhubarb", "boxes", "5.0"),                  # 5 kg box
    ("Rhubarb", "kilos", "1.0"),
    ("Raspberry purée", "tubs", "1.0"),           # 1 kg tub
    ("Raspberry purée", "kilos", "1.0"),
    ("Free-range eggs", "trays", "1.8"),          # 30 eggs tray = ~1.8 kg
    ("Free-range eggs", "kilos", "1.0"),
    ("Ricotta", "tubs", "2.0"),                   # 2 kg tub
    ("Ricotta", "kilos", "1.0"),
    ("Digestive biscuits", "cases", "4.8"),       # 4.8 kg case
    ("Digestive biscuits", "kilos", "1.0"),
    ("Sea salt", "sacks", "25.0"),                # 25 kg sack
    ("Sea salt", "kilos", "1.0"),
]

# Standard price per kilogram for each item (pack price / kg per pack)
ITEM_KG_PRICES = {
    "Whole milk, kitchen": "0.86",       # 8.90 / 10.3
    "Whipping cream 38%": "2.92",        # 14.60 / 5.0
    "Caster sugar (sucrose)": "0.98",    # 24.50 / 25.0
    "Dextrose": "1.64",                  # 41.00 / 25.0
    "Skimmed milk powder": "2.48",       # 62.00 / 25.0
    "Base 50 stabiliser": "13.80",       # 276.00 / 20.0
    "Sicilian pistachio paste": "58.00", # 203.00 / 3.5
    "Cocoa 22/24": "0.82",               # 4.10 / 5.0 (initial typo price)
    "Glucose syrup": "8.29",             # 58.00 / 7.0
    "Inulin": "9.20",                    # 46.00 / 5.0
    "Piedmont hazelnut paste": "37.40",  # 187.00 / 5.0
    "Vanilla paste": "96.00",            # 96.00 / 1.0
    "Lemons": "3.60",                    # 18.00 / 5.0
    "Strawberries": "11.25",             # 22.50 / 2.0
    "Rhubarb": "3.20",                   # 16.00 / 5.0
    "Raspberry purée": "34.00",          # 34.00 / 1.0
    "Free-range eggs": "5.44",           # 9.80 / 1.8
    "Ricotta": "6.20",                   # 12.40 / 2.0
    "Digestive biscuits": "4.38",        # 21.00 / 4.8
    "Sea salt": "0.46",                  # 11.50 / 25.0
}

WASTE_NOTES = [
    "Split bag", "Out of date", "Left out overnight", "Bin weighed at close",
    None, None,
]

# How many of each kind of correction the six months hold. They are counts and
# not a rate: what matters is that all three kinds are in the log and that
# there are enough of them to find.
TRANSPOSED = 15          # a number written down wrong, and put right
NEVER_ARRIVED = 8        # a delivery recorded that never came
MISCOUNTED = 6           # lines put right across count sheets


def uri(prefix, name):
    """A URI out of a name. Two things with one name are one thing."""
    slug = "".join(c if c.isalnum() else "_" for c in name.lower())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return f"sorella:{prefix}_{slug.strip('_')}"


def _moment(day, hour=9):
    return datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)


def _learned(day, hour=16):
    """When the log learned it: the day the paper arrived, or the day the
    office had caught up to, whichever came first."""
    return _moment(min(day, LEARNED_BY), hour)


def _weekday(week, weekday):
    """A date inside week `week` of the window, on the given weekday."""
    return FIRST_WEEK + timedelta(days=7 * week + weekday)


def reset(conn):
    """Drop and recreate the three tables. The demonstration log is synthetic."""
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.autocommit = False


class Tally:
    def __init__(self):
        self.intents = 0
        self.assertions = 0

    def add(self, result):
        self.intents += 1
        self.assertions += len(result["assertions"])
        return result


def state(conn, map_, class_name, subject, values, *, actor, counts,
          when=ADOPTED, recorded=None, source=None, confidence=None,
          authority=None, note=None):
    """One row, through the write gate. Empty fields are not written at all.

    `recorded` is when the log learned it and defaults to when it became true,
    which is right only for a thing stated on the day it was decided. Anything
    written on paper passes the day the paper reached whoever typed it.
    """
    entered = {name: str(value) for name, value in values.items()
               if value is not None and str(value) != ""}
    entered["entity_class"] = class_name
    return counts.add(submit(
        conn, map_, class_name, subject=subject, values=entered,
        actor_id=actor, valid_from=when, recorded_at=recorded or when,
        source=source, confidence=confidence, authority=authority, note=note))


def correct(conn, map_, class_name, subject, field, revoked, *, actor, counts,
            value=None, when, recorded, source, confidence=None,
            authority=None, note=None):
    """Withdraw one earlier assertion, with or without a replacement.

    `value` None is a pure retraction: the row carries no value at all, which
    is how a business says a thing it wrote down never happened. A `value`
    given is a correction, and it is valid from the same day the row it
    replaces was — because what was wrong was the writing down, not the world.
    """
    return counts.add(submit(
        conn, map_, class_name, subject=subject,
        values={field: value} if value is not None else {},
        revokes={field: revoked}, actor_id=actor, valid_from=when,
        recorded_at=recorded, source=source, confidence=confidence,
        authority=authority, note=note))


def master(conn, map_, counts):
    """The classes that are what the business is, before anything moves."""
    for name, meaning in UNITS:
        state(conn, map_, "Unit", uri("unit", name),
              {"unit_name": name, "unit_meaning": meaning},
              actor="marina", counts=counts, source="human_stated",
              confidence="high", authority="Marina Devlin")

    for name, role in PEOPLE:
        state(conn, map_, "Person", uri("person", name),
              {"person_name": name, "person_role": role},
              actor="marina", counts=counts, source="human_stated",
              confidence="high", authority="Marina Devlin")

    for name, what, temperature in INTERNAL:
        state(conn, map_, "InternalLocation", uri("loc", name),
              {"location_name": name, "location_description": what,
               "location_temperature": temperature},
              actor="marina", counts=counts, source="human_stated",
              confidence="high", authority="Marina Devlin")

    for name, what in OUTSIDE:
        state(conn, map_, "Location", uri("loc", name),
              {"location_name": name, "location_description": what},
              actor="marina", counts=counts, source="human_stated",
              confidence="high", authority="Marina Devlin")

    for name, brings, where, rhythm, lead, document, _, _, _ in SUPPLIERS:
        state(conn, map_, "Supplier", uri("loc", name),
              {"location_name": name,
               "location_description": "A supplier, and a place: what they "
               "bring is theirs until it is put away here",
               "outside_where": where, "supplier_brings": brings,
               "supplier_rhythm": rhythm, "supplier_lead_time": lead},
              actor="marina", counts=counts, source="human_stated",
              confidence="high", authority="Marina Devlin",
              note=f"Supplier, {name}. On paper: {document}")

    for name, happens, document in KINDS:
        state(conn, map_, "MovementKind", uri("kind", name),
              {"kind_name": name, "kind_happens": happens,
               "kind_document": document},
              actor="marina", counts=counts, source="human_stated",
              confidence="high", authority="Marina Devlin")

    for item_name, unit_name, factor in CONVERSIONS:
        conv_key = f"{item_name}_{unit_name}"
        state(
            conn, map_, "UnitConversion", uri("conv", conv_key),
            {
                "conversion_ingredient": uri("item", item_name),
                "conversion_unit": uri("unit", unit_name),
                "conversion_factor": factor,
            },
            actor="marina", counts=counts, source="human_stated",
            confidence="high", authority="Marina Devlin",
            note=f"Conversion factor: 1 {unit_name} of {item_name} = {factor} kg",
        )

    prices = {}
    for name, unit, supplier, price, reorder, note, _ in ITEMS:
        kg_price = ITEM_KG_PRICES[name]
        result = state(
            conn, map_, "Ingredient", uri("item", name),
            {"item_name": name, "item_base_unit": uri("unit", "kilos"),
             "item_counted_in": uri("unit", unit),
             "item_supplier": uri("loc", supplier), "item_pack_price": price,
             "item_price_per_kg": kg_price,
             "item_reorder_level": reorder, "item_note": note},
            actor="marina", counts=counts, source="human_stated",
            confidence="high", authority="Marina Devlin")
        prices[name] = {
            "pack_price": result["stated"]["item_pack_price"],
            "price_per_kg": result["stated"]["item_price_per_kg"],
        }
    return prices


def price_history(conn, map_, counts, prices):
    """One rise, one typo put right, and one price withdrawn for want of paper.

    Three assertions under one predicate, and the log tells them apart without
    being asked to. The rise carries a later `valid_from` and revokes nothing.
    The typo revokes the row it replaces and is valid from the same day as it.
    The withdrawal revokes and carries no value, so the cell it filled goes
    empty and not to nought.
    """
    name, when, price, why = PRICE_RISE
    state(conn, map_, "Ingredient", uri("item", name),
          {"item_pack_price": price, "item_price_per_kg": "61.14"},
          actor="marina", counts=counts, when=_moment(when),
          recorded=_moment(when, 17), source="document_extracted",
          confidence="high", authority=why,
          note="The price on the invoice, from this delivery on. Nothing here "
               "was wrong before: this is the price now")

    name, when, price, why = PRICE_TYPO
    correct(conn, map_, "Ingredient", uri("item", name), "item_pack_price",
            prices[name]["pack_price"], value=price, actor="marina", counts=counts,
            when=ADOPTED, recorded=_moment(when, 11),
            source="document_extracted", confidence="high", authority=why,
            note="Typed as four pounds ten when the description was taken "
                 "down. It was forty-one then and it is forty-one now, so this "
                 "withdraws the row rather than standing beside it")
    correct(conn, map_, "Ingredient", uri("item", name), "item_price_per_kg",
            prices[name]["price_per_kg"], value="8.20", actor="marina", counts=counts,
            when=ADOPTED, recorded=_moment(when, 11),
            source="document_extracted", confidence="high", authority=why,
            note="Price per kg updated to match the corrected pack price")

    name, when = PRICE_WITHDRAWN
    correct(conn, map_, "Ingredient", uri("item", name), "item_pack_price",
            prices[name]["pack_price"], actor="marina", counts=counts,
            when=ADOPTED, recorded=_moment(when, 16), source="human_stated",
            authority="Marina Devlin",
            note="Nobody can find a receipt for it and nobody remembers what "
                 "it cost. Withdrawn with nothing to put in its place")
    correct(conn, map_, "Ingredient", uri("item", name), "item_price_per_kg",
            prices[name]["price_per_kg"], actor="marina", counts=counts,
            when=ADOPTED, recorded=_moment(when, 16), source="human_stated",
            authority="Marina Devlin",
            note="Price per kg withdrawn with nothing to put in its place")


def _delivers(supplier, week, day):
    """Whether this supplier comes at all on this day of this week."""
    if day.weekday() not in DELIVERY_DAYS[supplier]:
        return False
    if supplier in FORTNIGHTLY and week % 2:
        return False
    months = IN_SEASON.get(supplier)
    return months is None or day.month in months


def movements(conn, map_, rng, counts):
    """Six months of movements: deliveries, daily gelato production, waste, tastings, and transfers."""
    by_supplier = {supplier[0]: supplier[5:] for supplier in SUPPLIERS}
    written = []

    def movement(n, when, kind, values, *, actor, paper, note=None):
        lags, source, confidence = paper[1], paper[2], paper[3]
        recorded = when + timedelta(days=rng.choice(lags))
        result = state(conn, map_, "StockMovement", f"sorella:movement_{n:04d}",
                       {"movement_kind": uri("kind", kind), **values,
                        "happened_on": when.isoformat()},
                       actor=actor, counts=counts, when=_moment(when),
                       recorded=_learned(recorded), source=source,
                       confidence=confidence, authority=paper[0],
                       note=note)
        if "movement_quantity" in result["stated"]:
            written.append({
                "subject": f"sorella:movement_{n:04d}",
                "assertion": result["stated"]["movement_quantity"],
                "quantity": values["movement_quantity"],
                "kind": kind, "happened": when, "recorded": recorded,
                "actor": actor,
                "ingredient": values.get("movement_ingredient"),
                "where": values.get("movement_into"),
            })
        return result

    n = 0
    for week in range(WEEKS):
        # 1. Deliveries from suppliers into internal stores
        for weekday in range(6):
            day = _weekday(week, weekday)
            for item in ITEMS:
                name, unit, supplier, price, reorder, note, store = item
                if not _delivers(supplier, week, day):
                    continue

                # Calibrated deliveries to maintain realistic gelato inventory:
                if name == "Base 50 stabiliser":
                    # Fortnightly until week 20 (11 cartons = 220 kg). August factory shut -> triggers critical reorder!
                    if week > 20:
                        continue
                    qty = 1
                elif name == "Sicilian pistachio paste":
                    # Delivered in weeks 2, 10, 16, 22: 2 tins each = total 8 tins (28 kg)
                    if week not in (2, 10, 16, 22):
                        continue
                    qty = 2
                elif name == "Whole milk, kitchen":
                    # Whitehall delivers Mon, Wed, Fri.
                    # Storyline 3: In week 19 (15 July), note typed as 10 bags, later corrected to 15 bags.
                    if week == 19 and weekday == 2:
                        qty = 10
                    elif weekday == 0 and week % 2 == 1:
                        qty = 1
                    else:
                        qty = 2
                elif name == "Whipping cream 38%":
                    qty = 2 if (weekday == 4 and week in (4, 10, 16, 22)) else 1
                elif name == "Caster sugar (sucrose)":
                    qty = 2
                    if week in (6, 14, 22):
                        qty = 3
                elif name == "Dextrose":
                    qty = 1
                    if week == 24:
                        qty = 2
                elif name == "Skimmed milk powder":
                    if week % 2 != 0:
                        continue
                    qty = 1
                    if week == 24:
                        qty = 2
                elif name == "Cocoa 22/24":
                    if week % 4 != 0:
                        continue
                    qty = 2
                elif name == "Glucose syrup":
                    qty = 1
                elif name == "Inulin":
                    if week % 4 != 0:
                        continue
                    qty = 1
                elif name == "Piedmont hazelnut paste":
                    if week % 4 != 0:
                        continue
                    qty = 1
                elif name == "Vanilla paste":
                    if week not in (0, 14):
                        continue
                    qty = 1
                elif name == "Lemons":
                    if weekday != 1:
                        continue
                    qty = 2
                elif name == "Strawberries":
                    if weekday != 4:
                        continue
                    qty = 2
                elif name == "Rhubarb":
                    if weekday != 1:
                        continue
                    qty = 1
                elif name == "Free-range eggs":
                    if weekday != 3:
                        continue
                    qty = 1
                elif name == "Ricotta":
                    if week % 2 != 0:
                        continue
                    qty = 1
                elif name == "Digestive biscuits":
                    if week % 6 != 0:
                        continue
                    qty = 1
                elif name == "Raspberry purée":
                    if week % 4 != 0:
                        continue
                    qty = 2
                elif name == "Sea salt":
                    if week != 0:
                        continue
                    qty = 1
                else:
                    qty = 1

                n += 1
                movement(n, day, "Delivery in",
                         {"movement_out_of": uri("loc", supplier),
                          "movement_into": uri("loc", store),
                          "movement_ingredient": uri("item", name),
                          "movement_quantity": qty,
                          "movement_unit": uri("unit", unit),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=by_supplier[supplier])

        # 2. Gelato Production Runs (Monday to Friday)
        for weekday in range(5):
            day = _weekday(week, weekday)
            # Gelato base: milk & cream
            m_qty = 2 if (weekday == 4 and week >= 14) else 1
            n += 1
            movement(n, day, "Used in production",
                     {"movement_out_of": uri("loc", "Walk-in chiller"),
                      "movement_into": uri("loc", "Production"),
                      "movement_ingredient": uri("item", "Whole milk, kitchen"),
                      "movement_quantity": m_qty,
                      "movement_unit": uri("unit", "bags"),
                      "written_by": uri("person", "Dan Farrugia")},
                     actor="dan", paper=PRODUCTION_PAPER,
                     note="Daily gelato base: whole milk pasteuriser run")

            if weekday in (0, 2, 4):
                n += 1
                movement(n, day, "Used in production",
                     {"movement_out_of": uri("loc", "Walk-in chiller"),
                      "movement_into": uri("loc", "Production"),
                      "movement_ingredient": uri("item", "Whipping cream 38%"),
                      "movement_quantity": 1,
                      "movement_unit": uri("unit", "cans"),
                      "written_by": uri("person", "Dan Farrugia")},
                     actor="dan", paper=PRODUCTION_PAPER)

            # Dry store sugars and powders into pasteuriser
            if weekday in (1, 3):
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Dry store"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Caster sugar (sucrose)"),
                          "movement_quantity": 1,
                          "movement_unit": uri("unit", "sacks"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)

            if weekday == 2 and week % 2 == 0:
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Dry store"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Dextrose"),
                          "movement_quantity": 1,
                          "movement_unit": uri("unit", "sacks"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)

            if weekday == 4 and week % 2 == 0:
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Dry store"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Skimmed milk powder"),
                          "movement_quantity": 1,
                          "movement_unit": uri("unit", "bags"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)

            # Base 50 stabiliser: loose 2 kg bags into pasteuriser
            if weekday < 4:
                if not (week in (24, 25) and weekday == 3):
                    n += 1
                    movement(n, day, "Used in production",
                             {"movement_out_of": uri("loc", "Dry store"),
                              "movement_into": uri("loc", "Production"),
                              "movement_ingredient": uri("item", "Base 50 stabiliser"),
                              "movement_quantity": 1,
                              "movement_unit": uri("unit", "bags"),
                              "written_by": uri("person", "Dan Farrugia")},
                             actor="dan", paper=PRODUCTION_PAPER,
                             note="Base 50 loose bag added to pasteuriser mix")

            if weekday in (1, 4):
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Dry store"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Glucose syrup"),
                          "movement_quantity": "1.50",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)

            if weekday == 3:
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Dry store"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Inulin"),
                          "movement_quantity": "0.50",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)

            # Flavour churn batches:
            if weekday == 0 and week % 2 == 0:
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Dry store"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Cocoa 22/24"),
                          "movement_quantity": "2.50",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Dry store"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Vanilla paste"),
                          "movement_quantity": "0.05",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)
            elif weekday == 1:
                if week % 3 == 0:
                    n += 1
                    movement(n, day, "Used in production",
                             {"movement_out_of": uri("loc", "Dry store"),
                              "movement_into": uri("loc", "Production"),
                              "movement_ingredient": uri("item", "Piedmont hazelnut paste"),
                              "movement_quantity": "1.00",
                              "movement_unit": uri("unit", "kilos"),
                              "written_by": uri("person", "Dan Farrugia")},
                             actor="dan", paper=PRODUCTION_PAPER)
                # Sicilian pistachio paste used in weeks 4, 12, 18, 24 (4 tins total = 14 kg used)
                if week in (4, 12, 18, 24):
                    n += 1
                    movement(n, day, "Used in production",
                             {"movement_out_of": uri("loc", "Dry store"),
                              "movement_into": uri("loc", "Production"),
                              "movement_ingredient": uri("item", "Sicilian pistachio paste"),
                              "movement_quantity": 1,
                              "movement_unit": uri("unit", "tins"),
                              "written_by": uri("person", "Dan Farrugia")},
                             actor="dan", paper=PRODUCTION_PAPER,
                             note="Sicilian pistachio batch churned")
            elif weekday == 2 and week >= 8:
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Walk-in chiller"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Strawberries"),
                          "movement_quantity": "1.50",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Walk-in chiller"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Lemons"),
                          "movement_quantity": "4.00",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Walk-in chiller"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Rhubarb"),
                          "movement_quantity": "2.00",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)
            elif weekday == 3:
                if week % 2 == 0:
                    n += 1
                    movement(n, day, "Used in production",
                             {"movement_out_of": uri("loc", "Walk-in chiller"),
                              "movement_into": uri("loc", "Production"),
                              "movement_ingredient": uri("item", "Ricotta"),
                              "movement_quantity": "1.00",
                              "movement_unit": uri("unit", "kilos"),
                              "written_by": uri("person", "Dan Farrugia")},
                             actor="dan", paper=PRODUCTION_PAPER)
                    n += 1
                    movement(n, day, "Used in production",
                             {"movement_out_of": uri("loc", "Dry store"),
                              "movement_into": uri("loc", "Production"),
                              "movement_ingredient": uri("item", "Digestive biscuits"),
                              "movement_quantity": "0.80",
                              "movement_unit": uri("unit", "kilos"),
                              "written_by": uri("person", "Dan Farrugia")},
                             actor="dan", paper=PRODUCTION_PAPER)
            elif weekday == 4:
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Walk-in chiller"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Free-range eggs"),
                          "movement_quantity": "0.90",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)
                if week % 4 == 0:
                    n += 1
                    movement(n, day, "Used in production",
                             {"movement_out_of": uri("loc", "Walk-in chiller"),
                              "movement_into": uri("loc", "Production"),
                              "movement_ingredient": uri("item", "Raspberry purée"),
                              "movement_quantity": 1,
                              "movement_unit": uri("unit", "tubs"),
                              "written_by": uri("person", "Dan Farrugia")},
                             actor="dan", paper=PRODUCTION_PAPER,
                             note="Raspberry sorbet churned with thawed purée")

            if weekday == 0:
                n += 1
                movement(n, day, "Used in production",
                         {"movement_out_of": uri("loc", "Dry store"),
                          "movement_into": uri("loc", "Production"),
                          "movement_ingredient": uri("item", "Sea salt"),
                          "movement_quantity": "0.10",
                          "movement_unit": uri("unit", "kilos"),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=PRODUCTION_PAPER)

        # 3. Waste, Tastings, Staff, and Store Transfers
        for _ in range(2):
            w_item = rng.choice(["Lemons", "Strawberries", "Whole milk, kitchen", "Free-range eggs"])
            n += 1
            movement(n, _weekday(week, rng.randrange(6)), "Thrown away",
                     {"movement_out_of": uri("loc", "Walk-in chiller"),
                      "movement_into": uri("loc", "Kitchen bin"),
                      "movement_ingredient": uri("item", w_item),
                      "movement_quantity": "0.50",
                      "movement_unit": uri("unit", "kilos"),
                      "written_by": uri("person", rng.choice(["Aoife Byrne", "Dan Farrugia"]))},
                     actor="aoife", paper=WASTE_PAPER,
                     note=rng.choice(WASTE_NOTES))

        if week % 2 == 0:
            t_item = rng.choice(["Sicilian pistachio paste", "Piedmont hazelnut paste", "Strawberries"])
            t_store = "Dry store" if "paste" in t_item else "Walk-in chiller"
            n += 1
            movement(n, _weekday(week, rng.randrange(6)), "Used for tastings",
                     {"movement_out_of": uri("loc", t_store),
                      "movement_into": uri("loc", "Tastings"),
                      "movement_ingredient": uri("item", t_item),
                      "movement_quantity": "0.10",
                      "movement_unit": uri("unit", "kilos")},
                     actor="dan", paper=WASTE_PAPER)

        if week % 3 == 0:
            s_item = rng.choice(["Free-range eggs", "Strawberries", "Digestive biscuits", "Whole milk, kitchen"])
            s_store = "Dry store" if s_item == "Digestive biscuits" else "Walk-in chiller"
            n += 1
            movement(n, _weekday(week, rng.randrange(6)), "Taken by staff",
                     {"movement_out_of": uri("loc", s_store),
                      "movement_into": uri("loc", "Staff"),
                      "movement_ingredient": uri("item", s_item),
                      "movement_quantity": 1,
                      "movement_unit": uri("unit", "kilos" if s_item != "Free-range eggs" else "trays"),
                      "written_by": uri("person", "Marina Devlin")},
                     actor="marina", paper=WASTE_PAPER)

        # Internal transfer: Dan moves 1 tub of raspberry purée from freezer to chiller on Thursday to thaw
        if week % 4 == 0:
            n += 1
            movement(n, _weekday(week, 3), "Transfer between stores",
                     {"movement_out_of": uri("loc", "Ingredient freezer"),
                      "movement_into": uri("loc", "Walk-in chiller"),
                      "movement_ingredient": uri("item", "Raspberry purée"),
                      "movement_quantity": 1,
                      "movement_unit": uri("unit", "tubs")},
                     actor="dan", paper=TRANSFER_PAPER,
                     note="Transferred 1 tub raspberry purée to chiller to thaw for Friday sorbet production")

    return written


def movement_corrections(conn, map_, rng, counts, written):
    """What the office found when supplier statements and delivery dockets were reconciled."""
    # Storyline 3: Whitehall Dairy Whole Milk delivery on 15 July 2026 (week 19).
    # Delivery docket noted 10 bags. Whitehall invoice #WH-4491 confirmed 15 bags.
    # Marina corrects the quantity to 15 with revokes!
    milk_row = next((row for row in written
                     if row["kind"] == "Delivery in"
                     and row.get("ingredient") == uri("item", "Whole milk, kitchen")
                     and row["happened"] == date(2026, 7, 15)), None)
    if milk_row:
        correct(conn, map_, "StockMovement", milk_row["subject"],
                "movement_quantity", milk_row["assertion"], value=15,
                actor="marina", counts=counts, when=_moment(milk_row["happened"]),
                recorded=_learned(date(2026, 7, 20), 11),
                source="document_extracted", confidence="high",
                authority="Whitehall Dairy invoice #WH-4491",
                note="Driver docket recorded 10 bags. Whitehall invoice #WH-4491 "
                     "and crate count verify 15 bags delivered")

    # Transposed typos (15) and never arrived (8)
    adjust_candidates = [
        row for row in written
        if row["kind"] == "Delivery in"
        and row["subject"] != (milk_row["subject"] if milk_row else None)
        and row.get("ingredient") in (
            uri("item", "Whole milk, kitchen"),
            uri("item", "Whipping cream 38%"),
            uri("item", "Lemons"),
            uri("item", "Strawberries"),
            uri("item", "Rhubarb"),
            uri("item", "Free-range eggs"),
            uri("item", "Digestive biscuits"),
            uri("item", "Caster sugar (sucrose)"),
        )
    ]
    chosen = rng.sample(adjust_candidates, TRANSPOSED + NEVER_ARRIVED)

    for row in chosen[:TRANSPOSED]:
        right = int(float(row["quantity"])) + rng.choice([-1, 1])
        correct(conn, map_, "StockMovement", row["subject"],
                "movement_quantity", row["assertion"], value=max(right, 1),
                actor="marina", counts=counts, when=_moment(row["happened"]),
                recorded=_learned(row["recorded"] + timedelta(days=5), 14),
                source="document_extracted", confidence="high",
                authority="The supplier's monthly statement, against the note",
                note="The figure on the note was not the figure on the "
                     "statement. This is the statement's")

    for row in chosen[TRANSPOSED:]:
        correct(conn, map_, "StockMovement", row["subject"],
                "movement_quantity", row["assertion"],
                actor="marina", counts=counts, when=_moment(row["happened"]),
                recorded=_learned(row["recorded"] + timedelta(days=9), 15),
                source="human_stated", authority="Marina Devlin",
                note="It was on the note and it was never delivered. Withdrawn "
                     "with no quantity in its place, because there is no true "
                     "number for a thing that did not happen")


COUNT_SHEETS = [
    ("dry_store", "Dry store ambient count", "Dan Farrugia",
     date(2026, 8, 30), "Full annual audit: ambient ingredients and pastes on racking"),
    ("chiller", "Walk-in chiller dairy and fruit count", "Aoife Byrne",
     date(2026, 8, 30), "Full annual audit: dairy, cream, fresh fruits and eggs"),
    ("freezer", "Ingredient freezer count", "Dan Farrugia",
     date(2026, 8, 30), "Full annual audit: purées and frozen ingredients"),
    ("prep_bench", "Kitchen prep bench open containers", "Marina Devlin",
     date(2026, 8, 30), "Full annual audit: opened bags and bench containers"),
    ("audit_pastes", "Manager verification of high-value pastes", "Marina Devlin",
     date(2026, 8, 30), "Audit verification: pistachio, hazelnut and vanilla shelves"),
    ("closing_review", "Annual stocktake master verification", "Marina Devlin",
     date(2026, 8, 30), "Signed off closing stock sheet for financial year end"),
]


def count_sheets(conn, map_, rng, counts):
    """Six count sheets representing physical audit zones, with recount corrections."""
    sheet_ids = {}
    for code, title, author, when, note in COUNT_SHEETS:
        sheet = f"sorella:count_{code}"
        sheet_ids[code] = sheet
        state(conn, map_, "StockCount", sheet,
              {"happened_on": when.isoformat(),
               "written_by": uri("person", author),
               "count_note": f"{title}. {note}"},
              actor="marina", counts=counts, when=_moment(when),
              recorded=_moment(when, 17), source="human_confirmed",
              confidence="high", authority="Marina Devlin")

    # Query active expected inventory balance per ingredient and internal location
    with conn.cursor() as cur:
        cur.execute("""
            WITH active_a AS (
                SELECT * FROM assertion
                WHERE id NOT IN (SELECT revokes FROM assertion WHERE revokes IS NOT NULL)
            ),
            uri_pred AS (
                SELECT subject_id FROM active_a WHERE value_literal = 'uniti:uri' LIMIT 1
            ),
            conversions AS (
                SELECT 
                    a.subject_id,
                    max(CASE WHEN p.value_literal = 'sorella:conversion_ingredient' THEN r.value_literal END) AS ingredient,
                    max(CASE WHEN p.value_literal = 'sorella:conversion_unit' THEN r.value_literal END) AS unit,
                    max(CASE WHEN p.value_literal = 'sorella:conversion_factor' THEN a.value_literal END)::numeric AS factor
                FROM active_a a
                JOIN active_a p ON p.subject_id = a.predicate_id AND p.predicate_id = (SELECT subject_id FROM uri_pred)
                LEFT JOIN active_a r ON r.subject_id = a.value_ref AND r.predicate_id = (SELECT subject_id FROM uri_pred)
                GROUP BY a.subject_id
            ),
            movements AS (
                SELECT 
                    a.subject_id,
                    max(CASE WHEN p.value_literal = 'sorella:movement_ingredient' THEN r.value_literal END) AS ingredient,
                    max(CASE WHEN p.value_literal = 'sorella:movement_quantity' THEN a.value_literal END)::numeric AS quantity,
                    max(CASE WHEN p.value_literal = 'sorella:movement_unit' THEN r.value_literal END) AS unit,
                    max(CASE WHEN p.value_literal = 'sorella:movement_into' THEN r.value_literal END) AS loc_into,
                    max(CASE WHEN p.value_literal = 'sorella:movement_out_of' THEN r.value_literal END) AS loc_out
                FROM active_a a
                JOIN active_a p ON p.subject_id = a.predicate_id AND p.predicate_id = (SELECT subject_id FROM uri_pred)
                LEFT JOIN active_a r ON r.subject_id = a.value_ref AND r.predicate_id = (SELECT subject_id FROM uri_pred)
                GROUP BY a.subject_id
            ),
            ins AS (
                SELECT m.ingredient, m.loc_into AS loc, sum(m.quantity * coalesce(c.factor, 1.0)) AS in_kg
                FROM movements m
                LEFT JOIN conversions c ON c.ingredient = m.ingredient AND c.unit = m.unit
                WHERE m.loc_into IN ('sorella:loc_dry_store', 'sorella:loc_walk_in_chiller', 'sorella:loc_ingredient_freezer')
                GROUP BY 1, 2
            ),
            outs AS (
                SELECT m.ingredient, m.loc_out AS loc, sum(m.quantity * coalesce(c.factor, 1.0)) AS out_kg
                FROM movements m
                LEFT JOIN conversions c ON c.ingredient = m.ingredient AND c.unit = m.unit
                WHERE m.loc_out IN ('sorella:loc_dry_store', 'sorella:loc_walk_in_chiller', 'sorella:loc_ingredient_freezer')
                GROUP BY 1, 2
            )
            SELECT 
                coalesce(i.ingredient, o.ingredient) AS ingredient,
                coalesce(i.loc, o.loc) AS loc,
                coalesce(i.in_kg, 0) - coalesce(o.out_kg, 0) AS expected_kg
            FROM ins i
            FULL OUTER JOIN outs o ON o.ingredient = i.ingredient AND o.loc = i.loc
            WHERE coalesce(i.in_kg, 0) - coalesce(o.out_kg, 0) > 0
            ORDER BY 1, 2;
        """)
        expected_rows = cur.fetchall()

    lines = 0
    written_lines = {}
    recounts = []

    store_to_sheet = {
        uri("loc", "Dry store"): "dry_store",
        uri("loc", "Walk-in chiller"): "chiller",
        uri("loc", "Ingredient freezer"): "freezer",
    }
    item_lookup = {uri("item", item[0]): item for item in ITEMS}

    for item_no, (ing_uri, loc_uri, exp_num) in enumerate(expected_rows, start=1):
        if ing_uri not in item_lookup:
            continue
        item = item_lookup[ing_uri]
        name = item[0]
        exp_kg = float(exp_num)
        sheet_code = store_to_sheet.get(loc_uri, "dry_store")
        sheet = sheet_ids[sheet_code]
        line_subj = f"sorella:count_line_{sheet_code}_{item_no:02d}"

        # Storylines and calibrated physical count:
        if name == "Sicilian pistachio paste":
            # Storyline 2: 2 tins missing (-7.0 kg, -£428.00)
            final_qty = round(exp_kg - 7.0, 2)
            # Initial misread: Dan thought 1 opened tin had 2kg (total 9.0kg)
            initial_qty = round(final_qty + 2.0, 2)
            recount_note = "Dan estimated 9.0kg with open tin. Verified shelf count: exactly 2 tins (7.0kg). Deficit: 2 tins (-£428.00) missing from July delivery."
            recounts.append((name, line_subj, str(final_qty), recount_note))
        elif name == "Base 50 stabiliser":
            # Storyline 4: 16.0 kg on shelf (< 40 kg reorder level), zero variance
            final_qty = round(exp_kg, 2)
            # Initial misread: Dan counted 1 full carton (20kg)
            initial_qty = round(final_qty + 4.0, 2)
            recount_note = "Dan counted 20kg carton. Marina noted 4kg emptied into daily bench hopper. Actual warehouse stock is 16.0kg. Below reorder threshold (40kg)."
            recounts.append((name, line_subj, str(final_qty), recount_note))
        elif name == "Whole milk, kitchen":
            final_qty = round(exp_kg - 0.25, 2)
            initial_qty = round(final_qty + 15.0, 2)
            recount_note = "Aoife included empty crates. Re-audited full bag count: verified."
            recounts.append((name, line_subj, str(final_qty), recount_note))
        elif name == "Caster sugar (sucrose)":
            final_qty = round(exp_kg - 0.25, 2)
            initial_qty = round(final_qty - 10.0, 2)
            recount_note = "Dan missed 1 sack behind dextrose pallet. Verified recount."
            recounts.append((name, line_subj, str(final_qty), recount_note))
        elif name == "Cocoa 22/24":
            final_qty = round(exp_kg - 0.25, 2)
            initial_qty = round(final_qty + 5.0, 2)
            recount_note = "Rough box estimate corrected to weighed scale count."
            recounts.append((name, line_subj, str(final_qty), recount_note))
        elif name == "Lemons":
            final_qty = round(exp_kg - 0.25, 2)
            initial_qty = round(final_qty - 5.0, 2)
            recount_note = "Aoife recounted bottom chiller shelf crates: verified."
            recounts.append((name, line_subj, str(final_qty), recount_note))
        elif name == "Vanilla paste":
            final_qty = round(exp_kg - 0.05, 2)
            initial_qty = final_qty
        else:
            loss = round(rng.uniform(0.15, 0.35), 2)
            final_qty = round(exp_kg - loss, 2)
            initial_qty = final_qty

        lines += 1
        result = state(
            conn, map_, "StockCountLine", line_subj,
            {"line_count": sheet,
             "count_line_written_as": name,
             "count_line_ingredient": ing_uri,
             "count_line_where": loc_uri,
             "count_line_quantity": str(initial_qty),
             "count_line_unit": uri("unit", "kilos"),
             "count_line_note": f"Audited on {sheet_code}"},
            actor="marina", counts=counts, when=_moment(date(2026, 8, 30), 10),
            recorded=_moment(date(2026, 8, 30), 17), source="human_confirmed",
            confidence="medium", authority=uri("person", "Dan Farrugia"))

        if "count_line_quantity" in result["stated"]:
            written_lines[name] = (line_subj, result["stated"]["count_line_quantity"])

    # Now apply the 6 recount corrections on 1 September
    for name, line_subj, correct_qty, recount_note in recounts:
        if name in written_lines:
            _, assertion_id = written_lines[name]
            correct(conn, map_, "StockCountLine", line_subj,
                    "count_line_quantity", assertion_id, value=correct_qty,
                    actor="marina", counts=counts,
                    when=_moment(date(2026, 8, 30), 16),
                    recorded=_moment(date(2026, 9, 1), 10),
                    source="human_confirmed", confidence="high",
                    authority="Marina Devlin",
                    note=recount_note)

    return lines


_SHAPE_SQL = """
SELECT count(*)                                   AS assertions,
       count(*) FILTER (WHERE revokes IS NOT NULL) AS revoking,
       count(DISTINCT recorded_at::date)           AS recorded_days,
       min(valid_from)::date                       AS first_valid,
       max(valid_from)::date                       AS last_valid,
       min(recorded_at)::date                      AS first_recorded,
       max(recorded_at)::date                      AS last_recorded
FROM assertion
"""

# The two clocks of the log, and what stands under each of the three classes a
# count of this seed is stated in. Read straight out of the log because this is
# a seed script and not a page: what a reader sees is the operational store.
_OF_CLASS_SQL = """
SELECT a.value_literal, count(DISTINCT a.subject_id)
FROM assertion a
WHERE a.predicate_id = (
        SELECT subject_id FROM assertion
        WHERE value_literal = %s
          AND predicate_id = (
              SELECT subject_id FROM assertion
              WHERE subject_id = predicate_id AND value_literal = 'uniti:uri'
              ORDER BY seq LIMIT 1)
        ORDER BY seq LIMIT 1)
GROUP BY 1 ORDER BY 1
"""


def shape(conn):
    """What the seed actually put in the log, printed as the numbers."""
    with conn.cursor() as cur:
        cur.execute(_SHAPE_SQL)
        (assertions, revoking, recorded_days, first_valid, last_valid,
         first_recorded, last_recorded) = cur.fetchone()
        cur.execute(_OF_CLASS_SQL, ("sorella:entity_class",))
        per_class = cur.fetchall()

    span = (last_valid - first_valid).days
    print(f"assertions              {assertions}")
    print(f"carrying revokes        {revoking}")
    print(f"distinct recorded days  {recorded_days}")
    print(f"valid_from              {first_valid} to {last_valid} "
          f"({span} days)")
    print(f"recorded_at             {first_recorded} to {last_recorded}")
    for name, held in per_class:
        print(f"  {name:22} {held}")


def main():
    rng = random.Random(RNG_SEED)
    map_ = read_map(MAP)
    counts = Tally()

    print(f"log  {DSN}")
    with connect() as conn:
        reset(conn)
        registered = register(conn, MAP, actor_id="fareza")
        print(f"registered {len(registered['minted'])} URIs from "
              f"{MAP.name} ({registered['version']})")

        prices = master(conn, map_, counts)
        price_history(conn, map_, counts, prices)
        print(f"master data: {counts.intents} rows")

        written = movements(conn, map_, rng, counts)
        print(f"movements:   {len(written)} with a quantity")

        movement_corrections(conn, map_, rng, counts, written)
        lines = count_sheets(conn, map_, rng, counts)
        print(f"count lines: {lines} on {len(COUNT_SHEETS)} sheets")
        print(f"{counts.intents} intents, {counts.assertions} assertions")
        print()
        shape(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())

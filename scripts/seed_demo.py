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

MAP = ROOT / "business" / "sorella_demo" / "v2.yaml"
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
    ("Whipping cream 38%", "cans", "Whitehall Dairy", "14.60", "2",
     None, "Walk-in chiller"),
    ("Caster sugar (sucrose)", "sacks", "Severn Catering Supplies", "24.50",
     None, None, "Dry store"),
    ("Dextrose", "sacks", "Terra Nostra Ingredients", "41.00", "1",
     None, "Dry store"),
    ("Skimmed milk powder", "bags", "Severn Catering Supplies", "62.00", None,
     "A bag here is twenty-five kilograms, not ten litres", "Dry store"),
    ("Base 50 stabiliser", "cartons", "Terra Nostra Ingredients", "276.00",
     None, "A carton is ten two-kilogram bags; the dry store counts cartons "
     "and the bench counts bags", "Dry store"),
    ("Sicilian pistachio paste", "tins", "Terra Nostra Ingredients", "203.00",
     "2", None, "Dry store"),
    ("Cocoa 22/24", "bags", "Terra Nostra Ingredients", "4.10", None,
     "A bag is five kilograms", "Dry store"),
    ("Glucose syrup", "pails", "Terra Nostra Ingredients", "58.00", "1",
     "A pail is seven kilograms and is warmed before it pours", "Dry store"),
    ("Inulin", "bags", "Terra Nostra Ingredients", "46.00", None,
     None, "Dry store"),
    ("Piedmont hazelnut paste", "tins", "Terra Nostra Ingredients", "187.00",
     "2", None, "Dry store"),
    ("Vanilla paste", "tins", "Terra Nostra Ingredients", "96.00", "1",
     None, "Dry store"),
    ("Lemons", "trays", "Kingsdown Fruit Farm", "18.00", None,
     "A tray is about five kilograms and nobody weighs it", "Walk-in chiller"),
    ("Strawberries", "trays", "Kingsdown Fruit Farm", "22.50", None,
     None, "Walk-in chiller"),
    ("Rhubarb", "boxes", "Kingsdown Fruit Farm", "16.00", None,
     None, "Walk-in chiller"),
    ("Raspberry purée", "tubs", "Terra Nostra Ingredients", "34.00", None,
     "Frozen. It goes straight into the ingredient freezer", "Ingredient freezer"),
    ("Free-range eggs", "trays", "Severn Catering Supplies", "9.80", "3",
     "A tray is thirty", "Walk-in chiller"),
    ("Ricotta", "tubs", "Severn Catering Supplies", "12.40", None,
     None, "Walk-in chiller"),
    ("Digestive biscuits", "cases", "Severn Catering Supplies", "21.00", None,
     "Crushed for the biscuit base", "Dry store"),
    ("Sea salt", "sacks", "Bristol Cash & Carry", "11.50", None,
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

WASTE_NOTES = [
    "Split bag", "Out of date", "Left out overnight", "Bin weighed at close",
    None, None,
]

# How many of each kind of correction the six months hold. They are counts and
# not a rate: what matters is that all three kinds are in the log and that
# there are enough of them to find.
TRANSPOSED = 12          # a number written down wrong, and put right
NEVER_ARRIVED = 6        # a delivery recorded that never came
MISCOUNTED = 2           # lines put right per count sheet


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

    prices = {}
    for name, unit, supplier, price, reorder, note, _ in ITEMS:
        result = state(
            conn, map_, "Ingredient", uri("item", name),
            {"item_name": name, "item_counted_in": uri("unit", unit),
             "item_supplier": uri("loc", supplier), "item_pack_price": price,
             "item_reorder_level": reorder, "item_note": note},
            actor="marina", counts=counts, source="human_stated",
            confidence="high", authority="Marina Devlin")
        prices[name] = result["stated"]["item_pack_price"]
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
          {"item_pack_price": price},
          actor="marina", counts=counts, when=_moment(when),
          recorded=_moment(when, 17), source="document_extracted",
          confidence="high", authority=why,
          note="The price on the invoice, from this delivery on. Nothing here "
               "was wrong before: this is the price now")

    name, when, price, why = PRICE_TYPO
    correct(conn, map_, "Ingredient", uri("item", name), "item_pack_price",
            prices[name], value=price, actor="marina", counts=counts,
            when=ADOPTED, recorded=_moment(when, 11),
            source="document_extracted", confidence="high", authority=why,
            note="Typed as four pounds ten when the description was taken "
                 "down. It was forty-one then and it is forty-one now, so this "
                 "withdraws the row rather than standing beside it")

    name, when = PRICE_WITHDRAWN
    correct(conn, map_, "Ingredient", uri("item", name), "item_pack_price",
            prices[name], actor="marina", counts=counts,
            when=ADOPTED, recorded=_moment(when, 16), source="human_stated",
            authority="Marina Devlin",
            note="Nobody can find a receipt for it and nobody remembers what "
                 "it cost. Withdrawn with nothing to put in its place")


def _delivers(supplier, week, day):
    """Whether this supplier comes at all on this day of this week."""
    if day.weekday() not in DELIVERY_DAYS[supplier]:
        return False
    if supplier in FORTNIGHTLY and week % 2:
        return False
    months = IN_SEASON.get(supplier)
    return months is None or day.month in months


def movements(conn, map_, rng, counts):
    """Six months of the three documents, as one class of movement."""
    # (the document, the lags, the source, the confidence) — the four the
    # table above states about the paper each supplier leaves behind.
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
            })
        return result

    n = 0
    for week in range(WEEKS):
        for weekday in range(6):
            day = _weekday(week, weekday)
            for item in ITEMS:
                supplier = item[2]
                if not _delivers(supplier, week, day):
                    continue
                if rng.random() >= CHANCE.get(supplier, DEFAULT_CHANCE):
                    continue
                n += 1
                movement(n, day, "Delivery in",
                         {"movement_out_of": uri("loc", supplier),
                          "movement_into": uri("loc", item[6]),
                          "movement_ingredient": uri("item", item[0]),
                          "movement_quantity": rng.randint(3, 10),
                          "movement_unit": uri("unit", item[1]),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan", paper=by_supplier[supplier])

        # Waste. Weighed, so it is in kilos whatever the thing arrived in.
        for _ in range(7):
            item = rng.choice(ITEMS)
            n += 1
            movement(n, _weekday(week, rng.randrange(6)), "Thrown away",
                     {"movement_out_of": uri("loc", item[6]),
                      "movement_into": uri("loc", "Kitchen bin"),
                      "movement_ingredient": uri("item", item[0]),
                      "movement_quantity": f"{rng.uniform(0.4, 6.0):.2f}",
                      "movement_unit": uri("unit", "kilos"),
                      "written_by": uri("person", rng.choice(
                          ["Aoife Byrne", "Dan Farrugia"]))},
                     actor="aoife", paper=WASTE_PAPER,
                     note=rng.choice(WASTE_NOTES))

        # A tasting or two. Weighed as well.
        for _ in range(4):
            item = rng.choice(ITEMS)
            n += 1
            movement(n, _weekday(week, rng.randrange(6)), "Used for tastings",
                     {"movement_out_of": uri("loc", item[6]),
                      "movement_into": uri("loc", "Tastings"),
                      "movement_ingredient": uri("item", item[0]),
                      "movement_quantity": f"{rng.uniform(0.2, 3.0):.2f}",
                      "movement_unit": uri("unit", "kilos")},
                     actor="dan", paper=WASTE_PAPER)

        # Somebody takes a pack home. In the pack it was in — and a carton of
        # stabiliser is never taken home, a bag out of one is.
        for _ in range(2):
            item = rng.choice(ITEMS)
            unit = "bags" if item[0] == "Base 50 stabiliser" else item[1]
            n += 1
            movement(n, _weekday(week, rng.randrange(6)), "Taken by staff",
                     {"movement_out_of": uri("loc", item[6]),
                      "movement_into": uri("loc", "Staff"),
                      "movement_ingredient": uri("item", item[0]),
                      "movement_quantity": 1,
                      "movement_unit": uri("unit", unit),
                      "written_by": uri("person", rng.choice(
                          [p[0] for p in PEOPLE]))},
                     actor="marina", paper=WASTE_PAPER)

        # Between our own stores, usually because something was opened.
        for _ in range(4):
            item = rng.choice(ITEMS)
            other = rng.choice([place for place, *_ in INTERNAL
                                if place != item[6]])
            n += 1
            movement(n, _weekday(week, rng.randrange(6)),
                     "Transfer between stores",
                     {"movement_out_of": uri("loc", item[6]),
                      "movement_into": uri("loc", other),
                      "movement_ingredient": uri("item", item[0]),
                      "movement_quantity": rng.randint(1, 3),
                      "movement_unit": uri("unit", item[1])},
                     actor="dan", paper=TRANSFER_PAPER)

        # Once a week the bin is weighed and nobody wrote down what was in it.
        n += 1
        movement(n, _weekday(week, 5), "Thrown away",
                 {"movement_out_of": uri("loc", "Dry store"),
                  "movement_into": uri("loc", "Kitchen bin"),
                  "movement_quantity": f"{rng.uniform(1.0, 9.0):.2f}",
                  "movement_unit": uri("unit", "kilos")},
                 actor="aoife", paper=WASTE_PAPER,
                 note="Bin weighed at close. Nobody wrote down what was in it")

    # Lines with no origin at all: a pack found on the floor and put away, and
    # nobody knows which delivery it came off.
    for week in (3, 9, 15, 21):
        item = ITEMS[week % len(ITEMS)]
        n += 1
        movement(n, _weekday(week, 4), "Delivery in",
                 {"movement_into": uri("loc", item[6]),
                  "movement_ingredient": uri("item", item[0]),
                  "movement_quantity": 1,
                  "movement_unit": uri("unit", item[1])},
                 actor="dan", paper=TRANSFER_PAPER,
                 note="Found on the floor. No note with it")

    return written


def movement_corrections(conn, map_, rng, counts, written):
    """What the office found when the statement came in.

    Two kinds, and the log tells them apart by whether the row that revokes
    carries a value. A number transposed on the note is put right; a delivery
    that never arrived is withdrawn and nothing replaces it, because there is
    no true number to write — the line should not be there at all.
    """
    delivered = [row for row in written if row["kind"] == "Delivery in"]
    chosen = rng.sample(delivered, TRANSPOSED + NEVER_ARRIVED)

    for row in chosen[:TRANSPOSED]:
        right = int(float(row["quantity"])) + rng.choice([-2, -1, 1, 2, 3])
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


# The count sheet is filled in as the counter walks the building, and typed up
# a day or two later. Six of them, one at the end of each month.
COUNT_DAYS = [date(2026, 3, 29), date(2026, 4, 26), date(2026, 5, 31),
              date(2026, 6, 28), date(2026, 7, 26), date(2026, 8, 30)]

COUNT_NOTES = [
    "First count under the new sheets. The chiller was still being loaded, so "
    "the milk is what was on the shelf at six.",
    "Counted alone. The ingredient freezer was iced up and the bottom basket "
    "was not emptied.",
    "Dan counted the dry store with me. Two bags of Base 50 out of an opened "
    "carton are written as bags.",
    "Quick count before the bank holiday. The fruit had just come in and is "
    "counted with it.",
    "Aoife counted the chiller. Everything in the freezer was written from the "
    "labels rather than lifted out.",
    "Full count. Everything opened was written as what it was opened into.",
]


def count_sheets(conn, map_, rng, counts):
    """Six count sheets and their lines, and two lines a sheet put right."""
    lines = 0
    for sheet_no, when in enumerate(COUNT_DAYS, start=1):
        sheet = f"sorella:count_{when.isoformat()}"
        typed = when + timedelta(days=sheet_no % 3)
        state(conn, map_, "StockCount", sheet,
              {"happened_on": when.isoformat(),
               "written_by": uri("person", "Marina Devlin"),
               "count_note": COUNT_NOTES[sheet_no - 1]},
              actor="marina", counts=counts, when=_moment(when),
              recorded=_moment(typed, 20), source="human_confirmed",
              confidence="high", authority="Marina Devlin")

        written = []
        for item_no, item in enumerate(ITEMS, start=1):
            lines += 1
            struck = (sheet_no == 1 and item[0] == "Cocoa 22/24")
            result = state(
                conn, map_, "StockCountLine",
                f"sorella:count_line_{sheet_no}_{item_no:02d}",
                {"line_count": sheet,
                 "count_line_written_as": item[0],
                 "count_line_ingredient": uri("item", item[0]),
                 "count_line_where": uri("loc", item[6]),
                 "count_line_quantity": None if struck else rng.randint(1, 12),
                 "count_line_unit": None if struck else uri("unit", item[1]),
                 "count_line_note": "Struck through — could not find it"
                                    if struck else None},
                actor="marina", counts=counts, when=_moment(when),
                recorded=_moment(typed, 20), source="human_confirmed",
                confidence="medium", authority="Marina Devlin")
            if "count_line_quantity" in result["stated"]:
                written.append((f"sorella:count_line_{sheet_no}_{item_no:02d}",
                                result["stated"]["count_line_quantity"]))

        # The opened carton, counted in the other unit. The same thing, twice
        # on one sheet, and nothing converts between them.
        lines += 1
        state(conn, map_, "StockCountLine",
              f"sorella:count_line_{sheet_no}_99",
              {"line_count": sheet,
               "count_line_written_as": "Base 50, loose bags",
               "count_line_ingredient": uri("item", "Base 50 stabiliser"),
               "count_line_where": uri("loc", "Dry store"),
               "count_line_quantity": rng.randint(2, 9),
               "count_line_unit": uri("unit", "bags"),
               "count_line_note": "Out of an opened carton"},
              actor="marina", counts=counts, when=_moment(when),
              recorded=_moment(typed, 20), source="human_confirmed",
              confidence="medium", authority="Marina Devlin")

        # Two lines a sheet were read off the shelf wrong and found when the
        # sheet was checked against the one before it.
        for subject, assertion in rng.sample(written, MISCOUNTED):
            correct(conn, map_, "StockCountLine", subject,
                    "count_line_quantity", assertion, value=rng.randint(1, 12),
                    actor="marina", counts=counts, when=_moment(when),
                    recorded=_moment(typed + timedelta(days=3), 19),
                    source="human_confirmed", confidence="high",
                    authority="Marina Devlin",
                    note="Recounted against last month's sheet. The first "
                         "figure was read off the wrong shelf")
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
        print(f"count lines: {lines} on {len(COUNT_DAYS)} sheets")
        print(f"{counts.intents} intents, {counts.assertions} assertions")
        print()
        shape(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Fill the demonstration log: one business, seven weeks of paper.

The map is `business/sorella_demo/v1.yaml` and the log is whatever `UNITI_DSN`
names — `make demo-seed` points it at `uniti_demo`, which is nothing else's.

**Every write goes through `generate.submit`.** One entity is one submission,
one submission is one intent and N assertions, and there is not one `INSERT`
here: a demonstration whose own data went in through a side door would be
demonstrating a write gate that is a fiction. The cost of that is one
`perform()` per row and it is paid deliberately.

Deterministic. One RNG seed and fixed dates, so a second run into an empty log
writes the same number of assertions as the first.

Everything is dated in the past, ending before today, for two reasons. Moving
`valid_at` backwards then changes both which rows exist and what the numbers
are, which is the whole point of the first clock; and a write through the form
lands at now, later than every row here, so the loop moves a balance that is
already standing. What cannot be shown that way is a backdated entry, which is
`OPEN.md`'s question about `happened_on` and is not this script's to answer.

The facts are Sorella's own, drawn from `business/sorella/profile.md` §1.6 for
the eight things and their prices, §1.8 for the three suppliers, and §3.2 for
the ways stock moves. The movements themselves are invented: no such log
exists, and a seven-week run of deliveries and waste is what a demonstration
needs and what nobody wrote down.

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

MAP = ROOT / "business" / "sorella_demo" / "v1.yaml"
SCHEMA = ROOT / "components" / "kernel" / "001_schema.sql"

RNG_SEED = 20260907

# When the description was adopted, which is the version's own valid_from and
# the day every standing fact about a thing, a place or a person starts from.
ADOPTED = datetime(2026, 7, 13, tzinfo=timezone.utc)

# Seven weeks of paper, ending a week before today so that today's clocks see
# all of it and a write through the form lands after all of it.
FIRST_WEEK = date(2026, 7, 13)
WEEKS = 7

UNITS = [
    ("bags", "A bag as it arrives. Ten litres of milk, twenty-five kilograms "
             "of powder, five of cocoa — the word says nothing about how much."),
    ("cans", "A five-litre jerry can, which is how the cream comes."),
    ("sacks", "A twenty-five kilogram paper sack."),
    ("tins", "A sealed tin: three and a half kilograms of pistachio paste."),
    ("cartons", "A carton of ten two-kilogram bags of stabiliser."),
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
    ("Walk-in chiller", "The cold room off the kitchen: milk and cream",
     "2 to 4 degrees"),
]

OUTSIDE = [
    ("Kitchen bin", "Where waste goes. Three bags a week, weighed"),
    ("Staff", "Where a thing goes when somebody takes it home, with permission"),
    ("Tastings", "Where a thing goes when it is opened for a trade customer or "
                 "a school visit and does not come back"),
]

SUPPLIERS = [
    ("Terra Nostra Ingredients", "Dry goods, pastes and the stabiliser",
     "Watford", "Tuesdays", "Two working days from the order"),
    ("Whitehall Dairy", "Milk and cream", "Somerset",
     "Three mornings a week", "Next day"),
    ("Severn Catering Supplies", "Sugar, powder and general kitchen goods",
     "Avonmouth", "Thursdays", "Three days"),
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

# name, counted in, supplier, price per pack, reorder level, note, where it lives
ITEMS = [
    ("Whole milk, kitchen", "bags", "Whitehall Dairy", "8.90", "4",
     "A bag is ten litres, bag-in-box", "Walk-in chiller"),
    ("Whipping cream 38%", "cans", "Whitehall Dairy", "14.60", None,
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
    ("Cocoa 22/24", "bags", "Terra Nostra Ingredients", "41.00", None,
     "A bag is five kilograms", "Dry store"),
]

# The one thing whose price moves inside the window, so that the same question
# asked at two clocks gets two answers. §1.6 has it at three prices in two years.
PRICE_RISE = ("Sicilian pistachio paste", date(2026, 8, 10), "214.00",
              "Terra Nostra invoice, 10 August")

WASTE_NOTES = [
    "Split bag", "Out of date", "Left out overnight", "Bin weighed at close",
    None, None,
]


def uri(prefix, name):
    """A URI out of a name. Two things with one name are one thing."""
    slug = "".join(c if c.isalnum() else "_" for c in name.lower())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return f"sorella:{prefix}_{slug.strip('_')}"


def reset(conn):
    """Drop and recreate the three tables. The demonstration log is synthetic."""
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.autocommit = False


def state(conn, map_, class_name, subject, values, *, actor, when=ADOPTED,
          authority=None, note=None):
    """One row, through the write gate. Empty fields are not written at all."""
    entered = {name: str(value) for name, value in values.items()
               if value is not None and str(value) != ""}
    entered["entity_class"] = class_name
    result = submit(conn, map_, class_name, subject=subject, values=entered,
                    actor_id=actor, valid_from=when, authority=authority,
                    note=note)
    return len(result["assertions"])


def master(conn, map_, counts):
    """The nine classes that are what the business is, before anything moves."""
    for name, meaning in UNITS:
        counts.add(state(conn, map_, "Unit", uri("unit", name),
                         {"unit_name": name, "unit_meaning": meaning},
                         actor="marina", authority="Marina Devlin"))

    for name, role in PEOPLE:
        counts.add(state(conn, map_, "Person", uri("person", name),
                         {"person_name": name, "person_role": role},
                         actor="marina", authority="Marina Devlin"))

    for name, what, temperature in INTERNAL:
        counts.add(state(conn, map_, "InternalLocation", uri("loc", name),
                         {"location_name": name, "location_description": what,
                          "location_temperature": temperature},
                         actor="marina", authority="Marina Devlin"))

    for name, what in OUTSIDE:
        counts.add(state(conn, map_, "Location", uri("loc", name),
                         {"location_name": name, "location_description": what},
                         actor="marina", authority="Marina Devlin"))

    for name, brings, where, rhythm, lead in SUPPLIERS:
        counts.add(state(conn, map_, "Supplier", uri("loc", name),
                         {"location_name": name,
                          "location_description": "A supplier, and a place: "
                          "what they bring is theirs until it is put away here",
                          "outside_where": where, "supplier_brings": brings,
                          "supplier_rhythm": rhythm,
                          "supplier_lead_time": lead},
                         actor="marina", authority="Marina Devlin"))

    for name, happens, document in KINDS:
        counts.add(state(conn, map_, "MovementKind", uri("kind", name),
                         {"kind_name": name, "kind_happens": happens,
                          "kind_document": document},
                         actor="marina", authority="Marina Devlin"))

    for name, unit, supplier, price, reorder, note, _ in ITEMS:
        counts.add(state(conn, map_, "Ingredient", uri("item", name),
                         {"item_name": name,
                          "item_counted_in": uri("unit", unit),
                          "item_supplier": uri("loc", supplier),
                          "item_pack_price": price,
                          "item_reorder_level": reorder,
                          "item_note": note},
                         actor="marina", authority="Marina Devlin"))

    # The price that moves. A second assertion under the same predicate, valid
    # from the day of the invoice: nothing is edited and nothing is revoked,
    # because the old price was not wrong, it was the price then.
    name, when, price, why = PRICE_RISE
    counts.add(state(conn, map_, "Ingredient", uri("item", name),
                     {"item_pack_price": price},
                     actor="marina", when=_moment(when), authority=why,
                     note="The price on the invoice, from this delivery on"))


def _moment(day):
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def _weekday(week, weekday):
    """A date inside week `week` of the window, on the given weekday."""
    return FIRST_WEEK + timedelta(days=7 * week + weekday)


def movements(conn, map_, rng, counts):
    """Seven weeks of the three documents, as one class of movement."""
    by_name = {name: item for item in ITEMS for name in (item[0],)}
    dairy = [item for item in ITEMS if item[2] == "Whitehall Dairy"]
    dry = [item for item in ITEMS if item[2] != "Whitehall Dairy"]
    written = 0

    def movement(n, when, kind, values, *, actor, note=None):
        nonlocal written
        written += 1
        counts.add(state(conn, map_, "StockMovement",
                         f"sorella:movement_{n:04d}",
                         {"movement_kind": uri("kind", kind), **values,
                          "happened_on": when.isoformat(),
                          "movement_note": note},
                         actor=actor, when=_moment(when)))

    n = 0
    for week in range(WEEKS):
        # The dairy comes three mornings a week; everything else comes on the
        # day its supplier comes.
        for weekday in (0, 2, 4):
            for item in dairy:
                if rng.random() < 0.85:
                    n += 1
                    movement(n, _weekday(week, weekday), "Delivery in",
                             {"movement_out_of": uri("loc", item[2]),
                              "movement_into": uri("loc", item[6]),
                              "movement_ingredient": uri("item", item[0]),
                              "movement_quantity": rng.randint(4, 10),
                              "movement_unit": uri("unit", item[1]),
                              "written_by": uri("person", "Dan Farrugia")},
                             actor="dan")

        for item in dry:
            weekday = 1 if item[2] == "Terra Nostra Ingredients" else 3
            if rng.random() < 0.75:
                n += 1
                movement(n, _weekday(week, weekday), "Delivery in",
                         {"movement_out_of": uri("loc", item[2]),
                          "movement_into": uri("loc", item[6]),
                          "movement_ingredient": uri("item", item[0]),
                          "movement_quantity": rng.randint(3, 9),
                          "movement_unit": uri("unit", item[1]),
                          "written_by": uri("person", "Dan Farrugia")},
                         actor="dan")

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
                     actor="aoife", note=rng.choice(WASTE_NOTES))

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
                     actor="dan")

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
                     actor="marina")

        # Between the two stores, usually because something was opened.
        for _ in range(4):
            item = rng.choice(ITEMS)
            other = ("Dry store" if item[6] == "Walk-in chiller"
                     else "Walk-in chiller")
            n += 1
            movement(n, _weekday(week, rng.randrange(6)),
                     "Transfer between stores",
                     {"movement_out_of": uri("loc", item[6]),
                      "movement_into": uri("loc", other),
                      "movement_ingredient": uri("item", item[0]),
                      "movement_quantity": rng.randint(1, 3),
                      "movement_unit": uri("unit", item[1])},
                     actor="dan")

        # Once a week the bin is weighed and nobody wrote down what was in it.
        n += 1
        movement(n, _weekday(week, 5), "Thrown away",
                 {"movement_out_of": uri("loc", "Dry store"),
                  "movement_into": uri("loc", "Kitchen bin"),
                  "movement_quantity": f"{rng.uniform(1.0, 9.0):.2f}",
                  "movement_unit": uri("unit", "kilos")},
                 actor="aoife", note="Bin weighed at close. Nobody wrote down "
                                     "what was in it")

    # Three lines with no origin at all: a pack found on the floor and put
    # away, and nobody knows which delivery it came off.
    for week in (1, 3, 5):
        item = by_name["Caster sugar (sucrose)"] if week == 3 else by_name["Cocoa 22/24"]
        n += 1
        movement(n, _weekday(week, 4), "Delivery in",
                 {"movement_into": uri("loc", item[6]),
                  "movement_ingredient": uri("item", item[0]),
                  "movement_quantity": 1,
                  "movement_unit": uri("unit", item[1])},
                 actor="dan", note="Found on the floor. No note with it")

    return written


COUNT_SHEETS = [
    (date(2026, 8, 2), "Marina Devlin",
     "Counted after close. The chiller was still being loaded, so the milk is "
     "what was on the shelf at six."),
    (date(2026, 8, 30), "Marina Devlin",
     "Dan counted the dry store with me. Two bags of Base 50 out of an opened "
     "carton are written as bags."),
]


def counts_sheets(conn, map_, rng, counts):
    """Two count sheets and their lines. A sheet has no key, so it gets a URI."""
    lines = 0
    for sheet_no, (when, who, note) in enumerate(COUNT_SHEETS, start=1):
        sheet = f"sorella:count_{when.isoformat()}"
        counts.add(state(conn, map_, "StockCount", sheet,
                         {"happened_on": when.isoformat(),
                          "written_by": uri("person", who),
                          "count_note": note},
                         actor="marina", when=_moment(when)))

        for item_no, item in enumerate(ITEMS, start=1):
            lines += 1
            struck = (sheet_no == 1 and item[0] == "Cocoa 22/24")
            counts.add(state(
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
                actor="marina", when=_moment(when)))

        # The opened carton, counted in the other unit. The same thing, twice
        # on one sheet, and nothing converts between them.
        lines += 1
        counts.add(state(
            conn, map_, "StockCountLine",
            f"sorella:count_line_{sheet_no}_99",
            {"line_count": sheet,
             "count_line_written_as": "Base 50, loose bags",
             "count_line_ingredient": uri("item", "Base 50 stabiliser"),
             "count_line_where": uri("loc", "Dry store"),
             "count_line_quantity": rng.randint(2, 9),
             "count_line_unit": uri("unit", "bags"),
             "count_line_note": "Out of an opened carton"},
            actor="marina", when=_moment(when)))
    return lines


class Tally:
    def __init__(self):
        self.intents = 0
        self.assertions = 0

    def add(self, assertions):
        self.intents += 1
        self.assertions += assertions


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

        master(conn, map_, counts)
        print(f"master data: {counts.intents} rows")

        before = counts.intents
        moved = movements(conn, map_, rng, counts)
        print(f"movements:   {moved}")

        lines = counts_sheets(conn, map_, rng, counts)
        print(f"count lines: {lines} on {len(COUNT_SHEETS)} sheets")

        assert counts.intents - before == moved + lines + len(COUNT_SHEETS)

    print(f"{counts.intents} intents, {counts.assertions} assertions, "
          f"{FIRST_WEEK} to {_weekday(WEEKS - 1, 6)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""Cross-read Sorella's business profile.

`business/sorella/profile.md` is prose. Six sessions wrote it and each session
checked its own prose, and the two real errors that got through were both found
by holding two sections against each other -- a session-2 fill weight against a
session-4 production sheet, and a session-3 rule against a session-4 day. That
class of error is not visible to anybody reading the file top to bottom, and
the number of section pairs is now past what a person will do by hand.

So every check run by hand across the rebuild lives here. Each one either
caught an error that has already been found, or was named by the done
condition of a session that has already run. Nothing is here because it might
be useful one day.

This script is allowed to know what a business is. It lives in `scripts/`, not
in `components/`: it checks a *description* of a business, so it is supposed to
be full of pans and flavours and accounts. Nothing under `components/` may
import it.

Stdlib only. Prints one line per check with a count, and exits non-zero if any
check fails. Every failure names a line number.
"""

import datetime
import re
import sys
from pathlib import Path

PROFILE = Path(__file__).resolve().parent.parent / "business" / "sorella" / "profile.md"


# --------------------------------------------------------------------------
# reading the file
# --------------------------------------------------------------------------

class Line:
    """A line of the profile, keeping the 1-based number it can be found at."""

    __slots__ = ("n", "text")

    def __init__(self, n, text):
        self.n = n
        self.text = text


class Table:
    """One markdown table: its header cells, its rows, and where each row is."""

    __slots__ = ("header", "rows")

    def __init__(self, header, rows):
        self.header = header
        self.rows = rows          # list of (line_number, [cells])

    def key(self):
        return " | ".join(self.header)


def cells(text):
    inner = text.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        return [Line(i + 1, t.rstrip("\n")) for i, t in enumerate(fh)]


def sections(lines):
    """Map "1.6" -> the lines of `## 1.6 ...` up to the next `## ` heading."""
    out = {}
    key, start = None, None
    for i, line in enumerate(lines):
        m = re.match(r"^## (\d+\.\d+)\s", line.text)
        if m:
            if key:
                out[key] = lines[start:i]
            key, start = m.group(1), i
        elif re.match(r"^#{1,2} ", line.text) and key:
            out[key] = lines[start:i]
            key, start = None, None
    if key:
        out[key] = lines[start:]
    return out


def tables(block):
    """Every markdown table in a block of lines."""
    found, i = [], 0
    while i < len(block):
        if block[i].text.startswith("|"):
            header = cells(block[i].text)
            if i + 1 < len(block) and set(block[i + 1].text) <= set("|-: "):
                rows, j = [], i + 2
                while j < len(block) and block[j].text.startswith("|"):
                    rows.append((block[j].n, cells(block[j].text)))
                    j += 1
                found.append(Table(header, rows))
                i = j
                continue
        i += 1
    return found


def table_named(block, *header_words):
    """The tables in `block` whose header starts with the given cells."""
    out = []
    for t in tables(block):
        if len(t.header) >= len(header_words) and all(
            t.header[k] == w for k, w in enumerate(header_words)
        ):
            out.append(t)
    return out


def text_of(block):
    return "\n".join(l.text for l in block)


def flowed(block):
    """A block with its line breaks taken out, so a phrase that wraps is one."""
    return re.sub(r"\s+", " ", text_of(block))


# --------------------------------------------------------------------------
# the results of a check
# --------------------------------------------------------------------------

class Check:
    def __init__(self, name):
        self.name = name
        self.count = ""
        self.failures = []       # list of (line_number, message)

    def fail(self, line_number, message):
        self.failures.append((line_number, message))

    @property
    def ok(self):
        return not self.failures


# --------------------------------------------------------------------------
# things read out of the profile that several checks need
# --------------------------------------------------------------------------

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
    "December": 12,
}

DAY_NAMES = {
    "Mon": 0, "Monday": 0, "Tue": 1, "Tuesday": 1, "Wed": 2, "Wednesday": 2,
    "Thu": 3, "Thurs": 3, "Thursday": 3, "Fri": 4, "Friday": 4,
    "Sat": 5, "Saturday": 5, "Sun": 6, "Sunday": 6,
}


def fill_weights(sec):
    """Section 2.4's `Filled to` column, in kilograms, per format.

    The pan is the weight that three sessions of production sheets are priced
    at, and it is the number whose absence made three of Tuesday's batches read
    as putting out more mass than went into them. It is read here rather than
    written here, so that moving it in the profile moves it in this check.
    """
    weights = {}
    for t in table_named(sec["2.4"], "Format", "Filled to"):
        for n, row in t.rows:
            fmt, filled = row[0], row[1]
            kg = re.search(r"([\d.]+)\s*kg", filled)
            g = re.search(r"([\d.]+)\s*g\b", filled)
            if kg:
                weights[fmt] = float(kg.group(1))
            elif g:
                weights[fmt] = float(g.group(1)) / 1000.0
    return weights


def sell_prices(sec):
    """Section 1.7, product -> {place: price}. `-` means not sold there."""
    prices = {}
    for t in table_named(sec["1.7"], "Product", "Format"):
        places = t.header[2:]
        for n, row in t.rows:
            at = {}
            for place, cell in zip(places, row[2:]):
                m = re.match(r"^£([\d,]+\.\d\d)$", cell)
                at[place] = float(m.group(1).replace(",", "")) if m else None
            prices[row[0]] = at
    return prices


def rule_rows(sec):
    """Section 3.4's rules: (line, rule, number, set_by, last_changed)."""
    out = []
    for t in table_named(sec["3.4"], "Rule", "The number"):
        for n, row in t.rows:
            out.append((n, row[0], row[1], row[2], row[3]))
    return out


def rule_number(rules, name):
    for n, rule, number, _, _ in rules:
        if rule == name:
            return number
    return None


def bold_pages(block):
    """Section 2.2 / 2.3 recipe pages: name -> the lines of that page."""
    marks = []
    for i, line in enumerate(block):
        m = re.match(r"^\*\*(.+?) — per ", line.text)
        if m:
            marks.append((i, m.group(1)))
        elif re.match(r"^#{3,4} ", line.text):
            marks.append((i, None))
    pages = {}
    for k, (i, name) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(block)
        if name:
            pages[name] = block[i:end]
    return pages


def at_fill_additions(sec):
    """Per flavour, the mass added by hand after the machine.

    Section 2.3 writes a page per 12.00 kg *into the batch freezer* and puts
    anything folded, drizzled or rippled in at fill underneath the table
    instead of in it, because it goes in after the machine and is on top of the
    12 kg. Mass balance has to allow for it or five flavours read as gaining
    mass.
    """
    out = {}
    for name, page in bold_pages(sec["2.3"]).items():
        added = 0.0
        for t in tables(page):
            for n, row in t.rows:
                if "at fill" in row[0].lower():
                    m = re.search(r"([\d.]+)\s*kg", row[1])
                    if m:
                        added += float(m.group(1))
        for line in page:
            if line.text.startswith("Plus ") and "at fill" in line.text.lower():
                m = re.match(r"^Plus ([\d.]+) kg", line.text)
                if m:
                    added += float(m.group(1))
        if added:
            out[name] = added
    return out


def flavours(sec):
    """Section 1.4's twenty-five names."""
    out = []
    for t in table_named(sec["1.4"], "Flavour", "Runs"):
        for n, row in t.rows:
            out.append(row[0])
    return out


def day_blocks(lines):
    """Every operational day in the file: name -> (date, its lines).

    Monday and Tuesday are sections of their own; Wednesday to Saturday are
    `###` headings inside 5.1; Sunday is a section again. A day runs to the
    next heading at its own level or above, so the `###` headings inside a day
    — deliveries, production, the van, the till — stay inside it.
    """
    heads = []
    for i, line in enumerate(lines):
        h = re.match(r"^(#{1,4}) ", line.text)
        if not h:
            continue
        m = re.match(
            r"^#{1,4} (?:\d+\.\d+ )?"
            r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
            r",? (\d{1,2}) (\w+) (\d{4})",
            line.text,
        )
        if m:
            heads.append((i, len(h.group(1)), m.group(1),
                          datetime.date(int(m.group(4)), MONTHS[m.group(3)],
                                        int(m.group(2)))))
        else:
            heads.append((i, len(h.group(1)), None, None))
    out = {}
    for k, (i, level, name, date) in enumerate(heads):
        if not name:
            continue
        end = len(lines)
        for j, other, _, _ in heads[k + 1:]:
            if other <= level:
                end = j
                break
        out[name] = (date, lines[i:end])
    return out


def bullet_list(block, start):
    """The run of bullets at `start`, each joined back up, and what follows.

    A till report's coffee line wraps onto a second line and half the drinks
    are on it, so a bullet has to be read whole or the day comes out short.
    """
    bullets, i = [], start
    while i < len(block) and not block[i].text.strip():
        i += 1                       # the blank line before the list
    while i < len(block):
        text = block[i].text
        if not text.strip():
            k = i + 1
            while k < len(block) and not block[k].text.strip():
                k += 1
            if k < len(block) and block[k].text.startswith("- ") and bullets:
                i = k
                continue
            break
        if text.startswith("- "):
            bullets.append(text[2:])
        elif text.startswith("  ") and bullets:
            bullets[-1] += " " + text.strip()
        else:
            break
        i += 1
    tail = " ".join(l.text.strip() for l in block[i:i + 12])
    return bullets, tail


def production_rows(lines):
    """Every production sheet row in the file, wherever a day states one."""
    out = []
    for t in table_named(lines, "Batch", "Flavour", "Mix into freezer"):
        for n, row in t.rows:
            out.append((n, row[0], row[1], row[2], row[3]))
    return out


# --------------------------------------------------------------------------
# consistency checks: each of these has already caught something
# --------------------------------------------------------------------------

def check_mass_balance(lines, sec):
    """No batch puts out more mass than went into it.

    Found three of Tuesday's batches over the line, by multiplying section
    2.4's fill weights against section 4.3's production sheet. The failure was
    in the master data -- the pan had no weight and the only reading anybody
    had was of a pan with the pan still on the scale.
    """
    check = Check("mass balance")
    weights = fill_weights(sec)
    additions = at_fill_additions(sec)
    known = {f.lower() for f in flavours(sec)}

    units = [
        (re.compile(r"(\d+)\s*×\s*5 L pan"), "5 L napoli pan", 1.0),
        (re.compile(r"(\d+)\s*×\s*500 ml tub"), "500 ml retail tub", 1.0),
        (re.compile(r"(\d+)\s*×\s*125 ml mini"), "125 ml mini tub", 1.0),
        (re.compile(r"(\d+)\s*×\s*1\.5 L catering tub"),
         "1.5 L catering tub", 1.0),
        (re.compile(r"(\d+) half pan"), "5 L napoli pan", 0.5),
        (re.compile(r"(\d+) quarter pan"), "5 L napoli pan", 0.25),
        (re.compile(r"(\d+) three.quarter pan"), "5 L napoli pan", 0.75),
    ]
    missing = [f for _, f, _ in units if f not in weights]
    if missing:
        check.fail(0, "no fill weight in 2.4 for: " + ", ".join(sorted(set(missing))))
        return check

    rows, fillable = 0, 0
    for n, batch, flavour, mix_in, output in production_rows(lines):
        rows += 1
        m = re.match(r"^([\d.]+)\s*kg", mix_in)
        if not m:
            check.fail(n, "%s: no mix weight in %r" % (batch, mix_in))
            continue
        mix = float(m.group(1))
        bare = re.sub(r"\s*\(.*?\)\s*", "", flavour).strip()
        if bare.lower() not in known:
            check.fail(n, "%s: %r is not a flavour in 1.4" % (batch, bare))
        out_kg = 0.0
        for pattern, fmt, share in units:
            for hit in pattern.finditer(output):
                out_kg += int(hit.group(1)) * weights[fmt] * share
        if out_kg == 0.0:
            continue                       # a binned batch fills nothing
        fillable += 1
        allowance = mix + additions.get(bare, 0.0)
        if out_kg - allowance > 0.005:
            check.fail(n, "%s %s: %.2f kg out against %.2f kg allowed"
                          % (batch, bare, out_kg, allowance))
    check.count = "%d production rows, %d fillable, %d over" % (
        rows, fillable, len(check.failures))
    return check


def check_till_totals(lines, sec):
    """Every day's takings against 1.7's prices and that day's own item list.

    Found Tuesday's Cotham takings 400 pounds under their own item list in
    session 4. Two things are checked: cash plus card against the stated
    takings, and, where a day writes out what it sold, that list priced at 1.7.
    """
    check = Check("till totals")
    prices = sell_prices(sec)

    def price(product, place):
        at = prices.get(product)
        return at.get(place) if at else None

    # what a line of a till report is worth, as the counter rings it
    items = [
        (r"(\d+) single scoop", "Single scoop", 1),
        (r"(\d+) double scoop", "Double scoop", 1),
        (r"(\d+) triple scoop", "Triple scoop", 1),
        (r"(\d+) waffle-cone supplements", "Waffle cone instead of wafer", 1),
        (r"(\d+) × 500 ml tub", "500 ml retail tub", 1),
        (r"(\d+) × 125 ml mini", "125 ml mini tub", 1),
        (r"(\d+) × 8\" cake", "Gelato cake, 8\"", 1),
        (r"(\d+) affogato", "Affogato", 1),
        (r"(\d+) espresso", "Espresso", 1),
        (r"(\d+) americano", "Americano", 1),
        (r"(\d+) cappuccino", "Cappuccino", 1),
        (r"(\d+) flat white", "Flat white", 1),
        (r"(\d+) latte", "Latte", 1),
        (r"(\d+) mocha", "Mocha", 1),
        (r"(\d+) hot chocolate", "Hot chocolate", 1),
        (r"(\d+) oat milk supplements", "Oat milk", 1),
        (r"(\d+) syrup shots", "Syrup shot", 1),
        (r"(\d+) cans", "Canned soft drink", 1),
        (r"(\d+) bottles of water", "Bottled water", 1),
    ]

    shops = ("Cotham Hill", "Gloucester Road")
    takings_line = re.compile(
        r"^(?:- )?\*\*(%s)\*\*,.*?takings \*\*£([\d,]+\.\d\d)\*\*"
        % "|".join(re.escape(s) for s in shops))

    totals, cashcard, listed, flagged = 0, 0, 0, 0

    for name, (date, block) in sorted(day_blocks(lines).items()):
        for i, line in enumerate(block):
            m = takings_line.match(line.text)
            if not m:
                continue
            totals += 1
            shop = m.group(1)
            stated = float(m.group(2).replace(",", ""))
            here = line.n

            # the takings paragraph: this line and the lines it wraps onto
            j, paragraph = i + 1, line.text
            while j < len(block) and block[j].text.strip() \
                    and not block[j].text.lstrip().startswith("- "):
                paragraph += " " + block[j].text.strip()
                j += 1

            cash = re.search(r"[Cc]ash £([\d,]+\.\d\d)", paragraph)
            card = re.search(r"card £([\d,]+\.\d\d)", paragraph)
            if cash and card:
                cashcard += 1
                s = (float(cash.group(1).replace(",", ""))
                     + float(card.group(1).replace(",", "")))
                if abs(s - stated) > 0.005:
                    check.fail(here, "%s %s: cash + card %.2f against takings %.2f"
                                     % (name, shop, s, stated))

            bullets, tail = bullet_list(block, j)
            if not any(re.search(r"\d+ single scoop", b) for b in bullets):
                continue
            listed += 1
            worked = 0.0
            for bullet in bullets:
                if bullet.startswith("**") or "comped" in bullet:
                    continue
                for pattern, product, mult in items:
                    for hit in re.finditer(pattern, bullet):
                        p = price(product, shop)
                        if p is None:
                            check.fail(here, "%s %s: %s has no price at %s"
                                             % (name, shop, product, shop))
                            continue
                        worked += int(hit.group(1)) * p * mult
            if abs(worked - stated) > 0.005:
                # A shortfall is a fact about the day, not a failure, so long
                # as the day says its list does not account for its takings.
                if "does not account for" in tail and shop in tail:
                    flagged += 1
                else:
                    check.fail(here, "%s %s: list worth %.2f against takings "
                                     "%.2f, and the day does not say so"
                                     % (name, shop, worked, stated))
    check.count = ("%d till totals, %d with cash and card, %d with an item list, "
                   "%d short and stated" % (totals, cashcard, listed, flagged))
    return check


def check_rules_against_days(lines, sec):
    """Three rules from 3.4 read against every day that could break them.

    The wholesale minimum is the one that found something: four pans is the
    rule and Tuesday has a three, a three and a two. A violation is not itself
    a failure -- a rule nobody enforces is a fact about this business -- but an
    *unflagged* violation is, so a violation passes only where the profile says
    it is there.
    """
    check = Check("rules against days")
    rules = rule_rows(sec)
    days = day_blocks(lines)

    conflicts = flowed(sec["3.4"]).split("### Where two rules disagree")[-1]

    # -- the minimum wholesale order, counted in the unit the rule names
    minimum = rule_number(rules, "Minimum wholesale order")
    m = re.match(r"^(\d+) pans$", minimum or "")
    if not m:
        check.fail(0, "3.4's minimum wholesale order is not a number of pans: %r"
                      % minimum)
        return check
    floor = int(m.group(1))
    drops, under, unflagged = 0, 0, 0
    for name, (date, block) in days.items():
        for t in table_named(block, "Customer", "Delivered"):
            for n, row in t.rows:
                drops += 1
                account = row[0].split(",")[0].strip()
                pans = sum(int(h) for h in
                           re.findall(r"(\d+)\s*×\s*5 L pan", row[1]))
                if pans < floor:
                    under += 1
                    if account not in conflicts:
                        unflagged += 1
                        check.fail(n, "%s: %s took %d pans against a minimum of "
                                      "%d, and 3.4 does not say so"
                                      % (name, account, pans, floor))

    # -- the van run days
    van = rule_number(rules, "Van run days")
    summer = (van or "").split(";")[0]
    van_days = {d for d in DAY_NAMES if re.search(r"\b%s\b" % d, summer)}
    if not van_days:
        check.fail(0, "3.4's van run days could not be read from %r" % van)
    runs = 0
    for name, (date, block) in days.items():
        ran = bool(table_named(block, "Customer", "Delivered"))
        if ran:
            runs += 1
            if not any(DAY_NAMES[d] == date.weekday() for d in van_days):
                check.fail(block[0].n, "%s: a wholesale run on a day 3.4 does "
                                       "not put the van out" % name)

    # -- the milk standing order days
    milk = rule_number(rules, "Milk standing order days")
    milk_days = {d for d in DAY_NAMES if re.search(r"\b%s\b" % d, milk or "")}
    if not milk_days:
        check.fail(0, "3.4's milk standing order days could not be read from %r"
                      % milk)
    drops_in, off_schedule = 0, 0
    for name, (date, block) in days.items():
        for t in table_named(block, "Time", "Supplier"):
            for n, row in t.rows:
                if "Whitehall" not in row[1] or "Did not arrive" in row[2]:
                    continue
                drops_in += 1
                if not any(DAY_NAMES[d] == date.weekday() for d in milk_days):
                    off_schedule += 1
                    if "a day late" not in row[2]:
                        check.fail(n, "%s: a dairy drop on a day 3.4's standing "
                                      "order does not name, and nothing says so"
                                      % name)

    check.count = ("%d wholesale drops, %d under the %d-pan minimum, %d unflagged; "
                   "%d van runs on run days; %d dairy drops, %d off schedule and "
                   "stated" % (drops, under, floor, unflagged, runs, drops_in,
                               off_schedule))
    return check


def check_weekdays(lines):
    """Every date written with a day name is that day.

    16 June 2026 is a Tuesday. Nothing has caught a wrong one yet; the done
    condition names it, and it is the cheapest cross-read in the file.
    """
    check = Check("weekdays")
    pattern = re.compile(
        r"\b(Mon|Monday|Tue|Tuesday|Wed|Wednesday|Thu|Thurs|Thursday|Fri|Friday"
        r"|Sat|Saturday|Sun|Sunday),?\s+(\d{1,2})\s+"
        r"(January|February|March|April|May|June|July|August|September|October"
        r"|November|December)(?:\s+(\d{4}))?")
    seen = 0
    for line in lines:
        for m in pattern.finditer(line.text):
            seen += 1
            year = int(m.group(4)) if m.group(4) else 2026
            try:
                d = datetime.date(year, MONTHS[m.group(3)], int(m.group(2)))
            except ValueError:
                check.fail(line.n, "%s is not a date" % m.group(0))
                continue
            if d.weekday() != DAY_NAMES[m.group(1)]:
                check.fail(line.n, "%s is a %s" % (m.group(0), d.strftime("%A")))
    check.count = "%d dates written with a day name, %d wrong" % (
        seen, len(check.failures))
    return check


# --------------------------------------------------------------------------
# completeness checks: each of these was asked for by a done condition
# --------------------------------------------------------------------------

# Recipe names that are not 1.6 items, and what each of them is instead.
INTERMEDIATE = {
    "White base", "Sorbet syrup", "Biscuit base", "Coffee brew", "Custard base",
    "Stewed rhubarb", "Purée",
}
NOT_BOUGHT = {"Water"}

# Recipe names that are a 1.6 item under another name. The business writes the
# same object two ways on two pages and 1.5 already says so.
INGREDIENT_ALIAS = {
    "Whole milk": "Whole milk, kitchen",
    "Cream 38%": "Whipping cream 38%",
    "Sucrose": "Caster sugar (sucrose)",
    "Base 50 stabiliser/emulsifier": "Base 50 stabiliser",
    "Stabiliser base": "Base 50 stabiliser",
    "Sea salt": "Sea salt, fine",
    "Egg yolk": "Eggs, medium free range",
    "Dark chocolate 70%, melted, drizzled at fill": "Dark chocolate 70% callets",
    "Amarena cherries in syrup, blended": "Amarena cherries in syrup",
    "Glucose syrup DE38, warmed": "Glucose syrup DE38",
    "Lemon juice, fresh, from about a 5 kg bag of lemons": "Lemons",
    "Lemon juice, bottled": "Lemon juice",
    "Coffee beans, espresso blend": "Coffee beans, espresso blend",
}

# Every 1.6 item that no recipe table names, and the sentence that consumes it.
# The phrase must still be in the section it is claimed to be in, so deleting
# the sentence fails the check rather than silently passing it.
OTHER_CONSUMERS = {
    "Amaretti biscuits": ("2.3", "Plus 0.55 kg amaretti"),
    "Panettone": ("2.3", "A 1 kg panettone torn up by hand"),
    "Marsala": ("2.3", "soaked in marsala"),
    "Freeze-dried raspberry pieces": ("2.3", "The decoration is freeze-dried raspberry pieces"),
    "Fruit purée, strawberry": ("2.3", "off frozen purée, which runs on this page"),
    "Fruit purée, raspberry": ("2.3", "**raspberry sorbet**"),
    "Fruit purée, mango": ("2.3", "**mango sorbet**"),
    "Fruit purée, passionfruit": ("2.3", "buys passionfruit purée"),
    "Fruit purée, peach": ("2.3", "the peach in peach and basil"),
    "Strawberries": ("2.3", "5.20 kg hulled strawberries"),
    "Figs": ("2.3", "The figs are quartered and go in at fill"),
    "Basil, fresh": ("2.3", "most of a 100 g pack"),
    "Ricotta": ("2.3", "works in a 2 kg tub of ricotta"),
    "Cream cheese": ("2.3", "a 2 kg tub of cream cheese"),
    "Waffle cones": ("2.6", "or one waffle cone where the 50p supplement is rung"),
    "Wafer cones": ("2.6", "One wafer cone"),
    "500 ml tub": ("2.6", "One 500 ml tub"),
    "500 ml lid, printed": ("2.6", "one printed lid"),
    "Printed sleeve, 500 ml": ("2.6", "one printed sleeve"),
    "125 ml mini tub with lid": ("2.6", "One 125 ml mini tub with lid"),
    "1.5 L catering tub with lid": ("2.6", "One 1.5 L catering tub with lid"),
    "Gelato cup, two scoop": ("2.6", "One two-scoop gelato cup"),
    "Gelato cup, three scoop": ("2.6", "One three-scoop gelato cup"),
    "Gelato spoon": ("2.6", "one gelato spoon"),
    "Tasting spoon": ("2.6", "Tasting spoons before the choice"),
    "Napkin, 2-ply": ("2.6", "One napkin"),
    "Takeaway bag, paper handled": ("2.6", "One paper handled bag"),
    "Cake box, 8\"": ("2.6", "one 8\" cake box"),
    "Cake board, 8\"": ("2.6", "One 8\" cake board"),
    "Napoli pan, stainless 5 L": ("2.6", "One napoli pan, steel or polycarbonate"),
    "Napoli pan, polycarbonate 5 L": ("2.6", "One napoli pan, steel or polycarbonate"),
    "Freezer label, blank": ("2.6", "One blank label"),
    "Paper cup, 8 oz": ("2.6", "One 8 oz paper cup"),
    "Paper cup, 12 oz": ("2.6", "One paper cup, 8 oz or 12 oz by the drink"),
    "Paper cup lid": ("2.6", "one lid, and one wooden stirrer"),
    "Wooden stirrer": ("2.6", "one wooden stirrer"),
    "Canned soft drink": ("2.6", "Bought and sold as the same object"),
    "Bottled water, 500 ml": ("2.6", "Bought and sold as the same object"),
    "Whole milk, coffee bar": ("2.7", "the cash and carry's 2 L bottle"),
    "Oat milk, barista": ("2.7", "the same volume out of a 1 L carton"),
    "Vanilla syrup": ("2.7", "free-pours the vanilla, the hazelnut and the caramel"),
    "Hazelnut syrup": ("2.7", "free-pours the vanilla, the hazelnut and the caramel"),
    "Caramel syrup": ("2.7", "free-pours the vanilla, the hazelnut and the caramel"),
    "Hot chocolate powder": ("2.7", "hot chocolate powder"),
    # Bought, used, and stated to be associated with no batch by anybody.
    "Sanitiser, no-rinse": ("2.3", "never associated with a batch by anybody"),
    "CIP alkaline detergent": ("2.3", "never associated with a batch by anybody"),
    "Blue roll": ("2.3", "never associated with a batch by anybody"),
    "Nitrile gloves": ("2.3", "never associated with a batch by anybody"),
    "Bin liners, heavy duty": ("2.3", "never associated with a batch by anybody"),
    "Dry ice pellets": ("2.3", "never associated with a batch by anybody"),
}


def bought_items(sec):
    out = []
    for t in table_named(sec["1.6"], "Item", "Counted in"):
        for n, row in t.rows:
            out.append((n, row[0]))
    return out


def recipe_ingredients(sec):
    """Every ingredient cell in 2.2 and 2.3, with the line it sits on."""
    out = []
    for key in ("2.2", "2.3"):
        for t in table_named(sec[key], "Ingredient", "Quantity"):
            for n, row in t.rows:
                out.append((n, row[0]))
    return out


def check_recipe_ingredients(sec):
    """Every ingredient on a recipe page is a 1.6 item, or a stated exception.

    Session 2's done condition asked for it. Water is the exception, stated in
    2.1 under a heading of its own; the intermediates are made in 2.2 and
    bought by nobody.
    """
    check = Check("recipe ingredients")
    items = {name for _, name in bought_items(sec)}
    rows, resolved, exceptions = 0, 0, 0
    for n, name in recipe_ingredients(sec):
        rows += 1
        if name in INTERMEDIATE or name in NOT_BOUGHT:
            exceptions += 1
            continue
        target = INGREDIENT_ALIAS.get(name, name)
        if target in items:
            resolved += 1
        else:
            check.fail(n, "%r is not a 1.6 item and is not a stated exception"
                          % name)
    check.count = "%d ingredient rows, %d in 1.6, %d stated exceptions, %d loose" % (
        rows, resolved, exceptions, len(check.failures))
    return check


def check_items_consumed(sec):
    """Every 1.6 item is consumed by something, or is stated not to be.

    An item nothing consumes can only ever rise, and that is the oldest failure
    in this repo -- map v1 stated no recipe, so material stock had no way down.
    Eighty items went in; ingredients are consumed by recipes and packaging by
    fills, and the cleaning chemicals, the dry ice, the napkins and the coffee
    side each need saying one at a time.
    """
    check = Check("items consumed")
    items = bought_items(sec)
    names = {name for _, name in items}

    by_recipe = set()
    for _, name in recipe_ingredients(sec):
        target = INGREDIENT_ALIAS.get(name, name)
        if target in names:
            by_recipe.add(target)

    for extra in sorted(set(OTHER_CONSUMERS) - names):
        check.fail(0, "%r is claimed consumed and is not a 1.6 item" % extra)

    elsewhere, stated = 0, 0
    for n, name in items:
        if name in by_recipe:
            continue
        if name not in OTHER_CONSUMERS:
            check.fail(n, "%r is bought and nothing consumes it" % name)
            continue
        where, phrase = OTHER_CONSUMERS[name]
        if re.sub(r"\s+", " ", phrase) not in flowed(sec[where]):
            check.fail(n, "%r claims §%s says %r, and it does not"
                          % (name, where, phrase))
            continue
        if "never associated with a batch" in phrase:
            stated += 1
        else:
            elsewhere += 1
    check.count = ("%d bought items, %d consumed by a recipe, %d elsewhere, "
                   "%d stated not consumed, %d loose"
                   % (len(items), len(by_recipe), elsewhere, stated,
                      len(check.failures)))
    return check


def check_places_move(sec):
    """Every place in 1.3 is named by a movement in 3.2.

    Session 3's done condition asked for it. A place nothing reaches is a place
    the graph will carry and nothing will ever put stock into.
    """
    check = Check("places reached")
    places = []
    for t in table_named(sec["1.3"], "Name", "What it is"):
        for n, row in t.rows:
            places.append((n, row[0]))
    body = text_of(sec["3.2"]).lower()
    for n, place in places:
        if place.lower() not in body:
            check.fail(n, "%r is a place in 1.3 and no movement in 3.2 names it"
                          % place)
    check.count = "%d places in 1.3, %d not named in 3.2" % (
        len(places), len(check.failures))
    return check


def check_rules_dated(sec):
    """Every rule in 3.4 carries a number and a date.

    Session 3's own run of this found eleven rules with no date and one row
    that was not a rule at all. The number cell must say something; the
    last-changed cell must carry a year, because a rule with no date has no
    before and the whole point of the file is that a rule has one.
    """
    check = Check("rules numbered and dated")
    rules = rule_rows(sec)
    for n, rule, number, set_by, changed in rules:
        if not number or number in ("-", "—"):
            check.fail(n, "%r carries no number" % rule)
        if not re.search(r"\b(19|20)\d\d\b", changed):
            check.fail(n, "%r carries no year in %r" % (rule, changed))
        if not set_by:
            check.fail(n, "%r says nobody set it" % rule)
    check.count = "%d rules, %d without a number or a year" % (
        len(rules), len(check.failures))
    return check


CONFIDENCES = {"Weighed", "Counted", "Eyeballed", "Not counted"}


def check_count_confidence(sec):
    """Every line of the opening count carries one of the four words.

    Session 4's done condition asked for it. The difference between a
    part-used sack that was weighed and one that was eyeballed is the whole of
    what that count knows about itself.
    """
    check = Check("count confidence")
    rows = 0
    for t in table_named(sec["4.1"], "Item", "Counted") + \
             table_named(sec["4.1"], "Well", "Counted"):
        if len(t.header) < 3 or t.header[2] != "Confidence":
            continue
        for n, row in t.rows:
            rows += 1
            if len(row) < 3 or row[2] not in CONFIDENCES:
                check.fail(n, "%r carries %r, which is not one of the four words"
                              % (row[0], row[2] if len(row) > 2 else ""))
    check.count = "%d count lines, %d without one of the four words" % (
        rows, len(check.failures))
    return check


def check_documents_have_fields(sec):
    """Every document in 3.3 carries its fields.

    Session 3's own run of this found three documents with no fields -- the
    whiteboard, the milk text and the HACCP file -- all of which do have fields
    once anybody asks.
    """
    check = Check("documents have fields")
    block = sec["3.3"]
    marks = [i for i, l in enumerate(block) if l.text.startswith("### ")]
    for k, i in enumerate(marks):
        end = marks[k + 1] if k + 1 < len(marks) else len(block)
        body = block[i:end]
        fields = [l for l in body
                  if re.match(r"^(\d+\.|-) ", l.text.strip()) or
                     re.match(r"^\d+\. ", l.text)]
        if not fields:
            check.fail(block[i].n, "%r lists no fields"
                                   % block[i].text[4:])
    check.count = "%d documents in 3.3, %d with no fields" % (
        len(marks), len(check.failures))
    return check


def check_flavours_have_a_page(sec):
    """Every flavour in 1.4 has a page in 2.3, or a stated reason for none.

    Session 2's done condition asked for it. Three of the eight seasonals have
    never been written down and 2.3 says what Dan does instead; four more run
    on somebody else's page and 2.3 says which.
    """
    check = Check("flavours have a page")
    pages = set(bold_pages(sec["2.3"]))
    body = text_of(sec["2.3"]).lower()
    named = []
    for t in table_named(sec["1.4"], "Flavour", "Runs"):
        for n, row in t.rows:
            named.append((n, row[0]))
    own, stated = 0, 0
    for n, flavour in named:
        if any(p.lower().startswith(flavour.lower()) for p in pages):
            own += 1
        elif flavour.lower() in body:
            stated += 1
        else:
            check.fail(n, "%r has no page in 2.3 and 2.3 does not name it"
                          % flavour)
    check.count = "%d flavours, %d with a page, %d routed or stated, %d silent" % (
        len(named), own, stated, len(check.failures))
    return check


def check_products_priced(sec):
    """Every product in 1.7 carries a price at each place it is sold.

    Session 1's done condition asked for it. A cell is a price or an em dash;
    a blank is a product somebody could ring up for nothing.
    """
    check = Check("products priced")
    rows, sold = 0, 0
    for t in table_named(sec["1.7"], "Product", "Format"):
        places = t.header[2:]
        for n, row in t.rows:
            rows += 1
            for place, cell in zip(places, row[2:]):
                if re.match(r"^£[\d,]+\.\d\d$", cell):
                    sold += 1
                elif cell != "—":
                    check.fail(n, "%r at %s reads %r, which is neither a price "
                                  "nor a dash" % (row[0], place, cell))
            if not any(re.match(r"^£", c) for c in row[2:]):
                check.fail(n, "%r is sold nowhere" % row[0])
    check.count = "%d products, %d product-places priced, %d wrong" % (
        rows, sold, len(check.failures))
    return check


def check_suppliers(sec):
    """Every supplier in 1.8 carries a lead time and a minimum order.

    Session 1's done condition asked for it. Bristol Cash & Carry states None
    for both, which is an answer -- it is collected, not delivered -- and a
    blank is not.
    """
    check = Check("suppliers")
    rows = 0
    for t in table_named(sec["1.8"], "Supplier", "Where"):
        try:
            lead = t.header.index("Lead time")
            minimum = t.header.index("Minimum order")
        except ValueError:
            check.fail(t.rows[0][0] if t.rows else 0,
                       "1.8 has no lead time or minimum order column")
            break
        for n, row in t.rows:
            rows += 1
            for label, k in (("lead time", lead), ("minimum order", minimum)):
                if k >= len(row) or not row[k] or row[k] == "—":
                    check.fail(n, "%s carries no %s" % (row[0], label))
    check.count = "%d suppliers, %d missing a lead time or a minimum" % (
        rows, len(check.failures))
    return check


# Phrases that would introduce a figure derived from other figures in the file.
# The profile states observations; working a balance out is the system's job.
# `variance box`, `line total`, `card total` and `never totalled` all name a
# box on a document rather than a computed number, so none of them is here.
COMPUTED = [
    r"should have been",
    r"expected on hand",
    r"(opening|closing) balance",
    r"stock on hand",
    r"works out (to|at)\b",
    r"a total of £",
    r"adds up to",
    r"in total,",
    r"variance of £",
    r"we calculate",
    r"computed as",
]


def check_no_computed_balance(lines):
    """No computed balance anywhere.

    The file's own preamble says nothing here is computed. Session 1 dropped
    two figures under this rule -- a headcount of sixteen and a turnover -- and
    both were sums of things the file already lists.
    """
    check = Check("no computed balance")
    patterns = [re.compile(p, re.I) for p in COMPUTED]
    for line in lines:
        if line.n <= 10:
            continue                # the preamble states the rule it names
        for p in patterns:
            m = p.search(line.text)
            if m:
                check.fail(line.n, "%r reads as a computed figure" % m.group(0))
    check.count = "%d phrases looked for, %d found" % (
        len(COMPUTED), len(check.failures))
    return check


# --------------------------------------------------------------------------

def main():
    # The profile is full of £, é, § and ×, and a failure message quotes it.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    if not PROFILE.exists():
        print("no profile at %s" % PROFILE)
        return 2
    lines = read_lines(PROFILE)
    sec = sections(lines)

    missing = [k for k in ("1.3", "1.4", "1.6", "1.7", "1.8", "2.2", "2.3",
                           "2.4", "2.6", "2.7", "3.2", "3.3", "3.4", "4.1")
               if k not in sec]
    if missing:
        print("profile is missing sections: %s" % ", ".join(missing))
        return 2

    checks = [
        check_mass_balance(lines, sec),
        check_till_totals(lines, sec),
        check_rules_against_days(lines, sec),
        check_weekdays(lines),
        check_recipe_ingredients(sec),
        check_items_consumed(sec),
        check_places_move(sec),
        check_rules_dated(sec),
        check_count_confidence(sec),
        check_documents_have_fields(sec),
        check_flavours_have_a_page(sec),
        check_products_priced(sec),
        check_suppliers(sec),
        check_no_computed_balance(lines),
    ]

    width = max(len(c.name) for c in checks)
    for c in checks:
        print("%-4s %-*s  %s" % ("ok" if c.ok else "FAIL", width, c.name, c.count))
        for n, message in c.failures:
            where = "profile.md:%d" % n if n else "profile.md"
            print("       %s  %s" % (where, message))

    bad = [c for c in checks if not c.ok]
    print("\n%d checks, %d failed" % (len(checks), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

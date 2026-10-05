"""standard — how every module is recorded, whoever records it.

A module is read by people and agents who did not write it: somebody choosing
between two modules in the catalogue, a rule in a third module totalling what
this one records, an agent on another model a year from now. That only works
if every module is written down the same way. So the way is written here, once,
and three readers take it from here and nowhere else:

    the seal     refuses a draft that breaks it (`refusals`)
    the studio   shows each break as a blocking hole with the step that mends
                 it, and each doubt as an open question (`doubts`)
    the guide    teaches it to an agent (`teach`), so what an agent is taught
                 cannot differ from what the seal enforces

What it holds a module to:

    one language   English, for every name, title and description and for
                   what an example says. The person's own words are kept
                   beside it as labels, one per language, in LinkML's own
                   place for them: `structured_aliases` with `in_language`.
    one shape      a class is `PascalCase`; a slot is `snake_case`, and every
                   slot of one class starts with the same word; a value of an
                   enum is `snake_case`; a module is `@scope/words-with-hyphens`.
    meaning        every class and slot is described; every number says its
                   unit (LinkML's `unit`) and which way it runs; every date
                   says what moment it is. The last two are chosen from closed
                   lists, because the 2.8 failures — a total counting twice, a
                   sign running backwards — came from exactly the meaning
                   nobody wrote down.

Only the draft's own declarations are held to it. A pinned module was sealed
under whatever held when it was sealed, and a sealed version is never changed:
it is brought to the standard by sealing a new version.

Whether a text is English is answered by a deliberately small reader — common
words of English and of a handful of other languages, and the script a text
is written in. Text it is sure is not English is refused; text it cannot place
is asked about and blocks nothing. It reads words, not meaning, so a name made
of words it has never seen passes, and the description beside it is what
carries the check.
"""

import re
import textwrap

from components.refusal import CODES, Refusal, Repair

# The language every module is recorded in.
LANGUAGE = "en"

# How wide the guide's lines are, as the rest of the guide is written.
WIDTH = 78

# Which way a number runs: what a positive value means. Closed, so that a rule
# totalling two modules' numbers can be checked against them, and so that the
# question is asked once, of whoever knows, rather than guessed by each reader.
DIRECTIONS = {
    "increase": "a change, and positive means there is more of it afterwards: "
                "received, added, earned",
    "decrease": "a change, and positive means there is less of it afterwards: "
                "issued, used, spent",
    "magnitude": "a change that is never negative; another fact of the same "
                 "record says which way it went",
    "level": "not a change: how much there is, or how much something is, at "
             "one moment: a balance, a price, a count, a threshold",
}

# What moment a date or a time is. Closed, for the reason DIRECTIONS is: a
# business reads "the date" four ways, and the log keeps two clocks of its own.
TIME_MEANINGS = {
    "happened": "when it happened in the world",
    "recorded": "when somebody wrote it down, which may be later",
    "takes_effect": "from when it holds, which may differ from when it was "
                    "agreed or written",
    "expected": "when it is due or planned to happen",
}

NUMBERS = ("integer", "decimal", "float", "double")
MOMENTS = ("date", "datetime")

# The order every agent records in, whichever model it runs on. Taught by the
# guide from here; the seal holds the result, not the order.
PROCEDURE = (
    "Search the catalogue for what the person described, in their words and in "
    "English: a module's labels are the words its people used.",
    "Reuse what is there: pin the sealed module that already records it and "
    "point at its classes with slots ranging over them; never declare one "
    "again under another name, nor make a class a kind of one.",
    "Fill the shared roles: a class that is a kind of thing a role names "
    "fills that role and binds its slots, so other modules can read it.",
    "Declare only what is missing, to this standard.",
    "Record the examples the person agreed to.",
    "Write the rules that compute, last, and hold them to the examples.",
)

# The shapes. Each is what the standard asks of a name; `_word` in the studio
# asks less, only what SQL and expressions need.
CLASS_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")
SLOT_NAME = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
VALUE_NAME = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
MODULE_NAME = re.compile(r"^@[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*$")

# The fields of a slot the standard adds to what LinkML already has: one
# native (`unit`), two kept as annotations because LinkML has no place for them.
DIRECTION = "direction"
TIME_MEANING = "time_meaning"

# What a refusal of the standard is about, in the order a reader mends them.
# The meanings are the refusal catalogue's, where every code is written once.
CHECKS = {code: CODES[code] for code in (
    "name_not_standard", "prefix_not_shared", "description_missing",
    "not_in_english", "unit_missing", "direction_missing", "time_meaning_missing",
)}

# What is asked and blocks nothing.
DOUBTS = {
    "maybe_not_english": "a text the standard cannot tell is English",
}


class StandardError(Refusal):
    """The draft is not recorded the way every module is. Nothing was written."""

    gate = "the recording standard"


# ---- reading words --------------------------------------------------------

# Common English words: the function words and the plain nouns a business
# description is made of. A text is placed by the share of its words found
# here and in OTHER, not by a model.
ENGLISH = set("""
a about above after again against all also always among amount an and another
any anything are as at back based be because been before being below between
both but by can cannot could count counted date day days did do does done down
during each either else end ever every everything few first for from full get
given goes going had has have having he her here his how however i if in into
is it its itself just kept kind known last later least less like made make many
may me might more most much must my name named names never new next no none nor
not nothing now number of off often old on once one only or other others our
out over own part per place same say says said see seen set several shall she
should since so some something somebody someone still such than that the their
them then there these they thing things this those through to too two under
until up upon us used very was way we well were what whatever when where whether
which while who whom whose why will with within without would yet you your
account accounts address added amount amounts balance bought buy buyer category
change changes code cost costs customer customers delivered delivery due each
entry entries fact facts goods group held hold holds hour hours identifier
ingredient ingredients item items kept label level line lines list location
money month months movement movements moved moves note order orders paid
payment payments period person people place price prices product products
quantity quantities rate reason received record recorded records row rows
sale sales sold staff stock stocks store stored supplier suppliers table total
totals type unit units value values week weeks what year years
""".split())

# Common words of other languages written in the Latin script — the function
# words first, which say the most about a language and the least about a
# business, then the few nouns a business description is made of. A word that
# is also English is not here: it would say nothing.
OTHER = set("""
yang dan di ke dari untuk dengan adalah ini itu tidak atau pada oleh dalam akan
sudah belum juga karena sebagai setiap bila jika apabila saat ketika tiap berapa
apa siapa kapan mana bahwa agar supaya hanya masih lebih kurang sama satu dua
kami kita saya anda mereka ada bisa dapat harus boleh telah sedang sebuah
seorang para tersebut antara hingga sampai sejak bagi tentang secara serta
maupun namun tetapi tapi jumlah tanggal nama barang bahan harga stok sisa masuk
keluar catatan dicatat pembelian penjualan pemasok pelanggan gudang toko satuan
banyaknya bulan tahun minggu hari biaya uang bayar dibayar
el la los las del que y en por para con una es son como pero sus muy fecha
nombre precio cantidad proveedor cliente
o os um uma do da dos das em com por não para preço quantidade fornecedor
le les des du et est sont pour avec dans sur pas nom prix quantité
fournisseur
der den dem des und ist sind nicht mit von für auf ein eine einen menge preis
lieferant kunde datum
het een van en is zijn niet met voor op prijs hoeveelheid leverancier
il lo gli della delle che non per con sono prezzo quantità fornitore
""".split()) - ENGLISH

_WORD = re.compile(r"[^\W\d_]+")
_LATIN = re.compile(r"^[a-z]+$")


def words_of(text):
    """The words of a text or of a name, lower case: `StockMovement` and
    `stock_movement` are both `stock`, `movement`."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|[_\-]", " ", str(text))
    return [w.lower() for w in _WORD.findall(spaced)]


def english(text):
    """`yes`, `no`, or `unsure`: whether a text is English, as far as words show.

    `no` only where it is plain: mostly a script that is not Latin, or more
    words of another language than of English. A text of words it has never
    seen is `unsure`, never `no`.
    """
    found = words_of(text)
    if not found:
        return "unsure"
    letters = "".join(found)
    foreign_script = sum(1 for ch in letters if not ("a" <= ch <= "z"))
    if foreign_script / len(letters) > 0.3:
        return "no"
    ours = sum(1 for w in found if w in ENGLISH)
    theirs = sum(1 for w in found if w in OTHER or not _LATIN.match(w))
    if theirs and theirs > ours:
        return "no"
    if not ours:
        return "unsure"
    return "yes"


def pascal(name):
    return "".join(w[:1].upper() + w[1:] for w in words_of(name)) or str(name)


def snake(name):
    return "_".join(words_of(name)) or str(name)


# ---- labels ---------------------------------------------------------------

def labels(body):
    """A term's labels, by language: what its people call it."""
    out = {}
    for alias in (body or {}).get("structured_aliases") or []:
        alias = alias or {}
        if alias.get("in_language") and alias.get("literal_form"):
            out[str(alias["in_language"])] = str(alias["literal_form"])
    return out


def with_label(body, language, text):
    """The body with one label set, replacing any other in the same language."""
    body = dict(body or {})
    kept = [dict(a or {}) for a in (body.get("structured_aliases") or [])
            if (a or {}).get("in_language") != language]
    kept.append({"literal_form": str(text), "in_language": language,
                 "predicate": "EXACT_SYNONYM"})
    body["structured_aliases"] = kept
    return body


# ---- what a slot says -----------------------------------------------------

def unit_of(body):
    unit = (body or {}).get("unit")
    if isinstance(unit, dict):
        return next((str(unit[k]) for k in ("symbol", "ucum_code", "abbreviation",
                                             "descriptive_name") if unit.get(k)), None)
    return str(unit) if unit else None


def unit(text):
    """A unit as LinkML holds it: a symbol, or — said in words — a name."""
    text = str(text).strip()
    if " " in text or len(text) > 16:
        return {"descriptive_name": text}
    return {"symbol": text}


def annotation(body, key):
    held = ((body or {}).get("annotations") or {}).get(key)
    if isinstance(held, dict) and set(held) == {"value"}:
        held = held["value"]
    return str(held) if held not in (None, "") else None


def _computed(body):
    annotations = (body or {}).get("annotations") or {}
    return bool((body or {}).get("equals_expression")
                or "aggregate" in annotations or "parameter" in annotations)


# ---- the checks -----------------------------------------------------------

def _said(where, expected, got, do, options=()):
    """A refusal's parts, its one repair carrying the answers that fit."""
    return {"where": where, "expected": expected, "got": got,
            "repairs": [Repair(do, options=options)]}


def _prefixes(document):
    """Per class, the word its own slots share, and the slots that do not.

    The shared word is the one most of its slots already start with — the
    least renaming — and the slots counted are the draft's own that are on
    this class alone: a slot on two classes cannot start with both words.
    """
    classes = document.get("classes") or {}
    own = document.get("slots") or {}
    on = {}
    for class_name, body in classes.items():
        for slot in (body or {}).get("slots") or []:
            if slot in own:
                on.setdefault(slot, []).append(class_name)
    out = {}
    for class_name, body in classes.items():
        mine = [s for s in (body or {}).get("slots") or []
                if s in own and on.get(s) == [class_name]
                and not (own[s] or {}).get("abstract")]
        firsts = [s.split("_")[0] for s in mine if SLOT_NAME.match(s)]
        if not firsts:
            continue
        shared = max(firsts, key=lambda w: (firsts.count(w), -firsts.index(w)))
        out[class_name] = (shared, [s for s in mine if s.split("_")[0] != shared
                                    or not SLOT_NAME.match(s)])
    return out


def refusals(document, examples=None, range_of=None):
    """Every way this draft breaks the standard, as the refusal each one is.

    A generator, like the seal's own readers: the seal raises the first, the
    studio shows them all. `examples` is the draft's examples by name, and
    `range_of(slot)` the range a slot has in the map — inherited from the
    binding it fills when it states none — which the document alone cannot say.
    """
    classes = document.get("classes") or {}
    slots = document.get("slots") or {}
    enums = document.get("enums") or {}
    range_of = range_of or (lambda s: (slots.get(s) or {}).get("range"))

    for class_name, body in classes.items():
        where = f"class {class_name}"
        if not CLASS_NAME.match(class_name):
            yield StandardError("name_not_standard", **_said(
                where, "a class named in PascalCase: English words, each starting "
                "with a capital, nothing between them",
                class_name, "rename it", [pascal(class_name)]))
        elif english(class_name) == "no":
            yield StandardError("not_in_english", **_said(
                where, "a class named in English", class_name,
                "rename it in English, and keep this name as its label in the "
                "person's language", ["rename_class", "label"]))
        yield from _described(where, body)

    shared = _prefixes(document)
    for slot_name, body in slots.items():
        where = f"slot {slot_name}"
        if not SLOT_NAME.match(slot_name):
            yield StandardError("name_not_standard", **_said(
                where, "a slot named in snake_case: two or more English words "
                "in lower case, joined by _, the first being the word every "
                "slot of its class starts with",
                slot_name, "rename it", [_suggested(slot_name, shared, document)]))
        elif english(slot_name) == "no":
            yield StandardError("not_in_english", **_said(
                where, "a slot named in English", slot_name,
                "rename it in English, and keep this name as its label in the "
                "person's language", ["rename_slot", "label"]))
        else:
            owner = next((c for c, (_, off) in shared.items() if slot_name in off),
                         None)
            if owner:
                yield StandardError("prefix_not_shared", **_said(
                    where, f"a slot of {owner} starting with `{shared[owner][0]}_`, "
                    f"the word its other slots start with",
                    slot_name, "rename it", [_suggested(slot_name, shared, document)]))
        if (body or {}).get("title") and english(body["title"]) == "no":
            yield StandardError("not_in_english", **_said(
                f"{where} title", "a title in English", body["title"],
                "write the title in English, and keep this one as its label in "
                "the person's language", ["set_slot", "label"]))
        yield from _described(where, body)
        yield from _meant(slot_name, body or {}, range_of(slot_name))

    for enum_name, body in enums.items():
        where = f"enum {enum_name}"
        if not CLASS_NAME.match(enum_name):
            yield StandardError("name_not_standard", **_said(
                where, "an enum named in PascalCase, as a class is", enum_name,
                "declare it again under this name", [pascal(enum_name)]))
        for value in ((body or {}).get("permissible_values") or {}):
            if not VALUE_NAME.match(str(value)) or english(value) == "no":
                yield StandardError("name_not_standard", **_said(
                    f"{where} value {value}", "a value named in English snake_case",
                    str(value), "write its values again in this shape, and keep "
                    "the person's words as labels", [snake(value)]))

    for field in ("title", "description"):
        if document.get(field) and english(document[field]) == "no":
            yield StandardError("not_in_english", **_said(
                f"module {field}", f"the module's {field} in English",
                _short(document[field]),
                f"write the {field} in English, and keep this as the module's "
                f"label in the person's language", ["set", "label"]))

    for example, body in (examples or {}).items():
        said = str((body or {}).get("says") or "")
        if said and english(said) == "no":
            yield StandardError("not_in_english", **_said(
                f"example {example}", "what the example says, in English",
                _short(said), "say it again in English, and keep the person's own "
                "words as the example's label", ["set_example", "label"]))


def _described(where, body):
    text = str((body or {}).get("description") or "").strip()
    if not text:
        yield StandardError("description_missing", **_said(
            where, "a description: what it is, in a sentence somebody choosing "
            "between two modules can read", "none", "describe it"))
    elif english(text) == "no":
        yield StandardError("not_in_english", **_said(
            f"{where} description", "a description in English", _short(text),
            "describe it in English, and keep the person's words as its label",
            ["label"]))


def _meant(slot_name, body, range_):
    """What a number or a date has to say for a reader to use it rightly."""
    if body.get("abstract") or body.get("identifier") or body.get("designates_type"):
        return
    where = f"slot {slot_name}"
    if str(range_ or "") in NUMBERS:
        if not unit_of(body):
            yield StandardError("unit_missing", **_said(
                where, "the unit it is counted in: kg, IDR, piece, hour, or in "
                "words, such as `the unit of the item moved`",
                "none", "say its unit"))
        if annotation(body, DIRECTION) not in DIRECTIONS:
            yield StandardError("direction_missing", **_said(
                where, "which way it runs" + (", computed or stated"
                                              if _computed(body) else ""),
                annotation(body, DIRECTION) or "none",
                "choose what a positive value means", list(DIRECTIONS)))
    if str(range_ or "") in MOMENTS:
        if annotation(body, TIME_MEANING) not in TIME_MEANINGS:
            yield StandardError("time_meaning_missing", **_said(
                where, "what moment it is", annotation(body, TIME_MEANING) or "none",
                "choose one", list(TIME_MEANINGS)))


def _suggested(slot_name, shared, document):
    """A name in the standard's shape, starting with its class's word."""
    owner = next((c for c, body in (document.get("classes") or {}).items()
                  if slot_name in ((body or {}).get("slots") or [])), None)
    words = words_of(slot_name)
    if owner in shared:
        word = shared[owner][0]
        rest = words[1:] if words and words[0] == word else words
        return "_".join([word] + (rest or ["value"]))
    if owner and len(words) < 2:
        return "_".join([words_of(owner)[-1]] + words)
    return snake(slot_name)


def _short(text):
    text = " ".join(str(text).split())
    return text if len(text) <= 80 else text[:77] + "..."


def doubts(document, examples=None):
    """What the standard cannot tell, asked rather than refused: `(where, text)`."""
    out = []

    def ask(where, text):
        if text and english(text) == "unsure" and len(words_of(text)) >= 3:
            out.append((where, _short(text)))

    for class_name, body in (document.get("classes") or {}).items():
        ask(f"class {class_name}", (body or {}).get("description"))
    for slot_name, body in (document.get("slots") or {}).items():
        ask(f"slot {slot_name}", (body or {}).get("description"))
    ask("module description", document.get("description"))
    for example, body in (examples or {}).items():
        ask(f"example {example}", (body or {}).get("says"))
    return out


def module_name(name):
    """A module's name in the standard's shape, or the refusal saying why not.

    Asked when a module is started: a module cannot be renamed, so this is
    the one moment its name can still be put right.
    """
    if MODULE_NAME.match(str(name)):
        return None
    scope, _, local = str(name).partition("/")
    fixed = "@" + "-".join(words_of(scope)) + "/" + "-".join(words_of(local))
    return StandardError("name_not_standard", **_said(
        f"module {name}", "a module named @scope/words-with-hyphens, in lower case",
        str(name), "start it under this name", [fixed]))


# ---- what an agent is taught ----------------------------------------------

def teach():
    """The standard as the guide states it: generated from the lists above."""
    def para(text, indent=""):
        return textwrap.fill(text, WIDTH, initial_indent=indent,
                             subsequent_indent=indent)

    def item(key, text, indent, width):
        return textwrap.fill(text, WIDTH, initial_indent=f"{indent}{key:<{width}}",
                             subsequent_indent=" " * (len(indent) + width))

    out = [
        para("Every module is recorded the same way, by every agent, so that "
             "modules find and read each other. The seal refuses a draft that "
             "breaks this; each break is a blocking hole with the step that "
             "mends it."),
        "",
        para("Language. Record in English: every name, title and description, "
             "and what an example says. Talk to the person in their own "
             "language, and keep their words for each class, slot, enum value "
             "and example as a label in their language (`label`): the studio "
             "shows them those."),
        "",
        "Names.",
        item("class, enum", "PascalCase English, a singular noun: StockMovement",
             "    ", 14),
        item("slot", "snake_case English, starting with one word shared by every "
             "slot of its class: movement_quantity, movement_happened_on",
             "    ", 14),
        item("enum value", "snake_case English", "    ", 14),
        item("module", "@scope/words-with-hyphens", "    ", 14),
        "",
        para("Meaning. Describe every class and slot in a sentence. Every number ("
             + ", ".join(NUMBERS) + ") that is not an identifier says its `unit` "
             "and its `direction`, and every date (" + ", ".join(MOMENTS) + ") "
             "its `time_meaning`; give them with `add_slot` or `set_slot`. "
             "Computed columns too."),
        "",
        "    direction, what a positive value means:",
    ]
    out += [item(k, v, "        ", 14) for k, v in DIRECTIONS.items()]
    out += ["", "    time_meaning, which moment a date is:"]
    out += [item(k, v, "        ", 14) for k, v in TIME_MEANINGS.items()]
    out += ["", "The procedure, in this order:"]
    out += [item(f"{i}.", step, "    ", 3) for i, step in enumerate(PROCEDURE, start=1)]
    return "\n".join(out)


__all__ = ["CHECKS", "DIRECTION", "DIRECTIONS", "DOUBTS", "LANGUAGE", "MOMENTS",
           "NUMBERS", "PROCEDURE", "StandardError", "TIME_MEANING",
           "TIME_MEANINGS", "annotation", "doubts", "english", "labels",
           "module_name", "refusals", "teach", "unit", "unit_of", "with_label",
           "words_of"]

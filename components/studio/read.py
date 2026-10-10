"""read — what a draft is, what is missing from it, and what may be done next.

> Never show the whole graph. Show the hole the person is standing in, what it
> obliges, and the finite set that can fill it.

That is the whole of this file. A draft is read here exactly as the gates read
it — the seal's own checks and the compiler's planner, nothing invented — and
what they refuse becomes a question with its answers attached.

Two kinds of question, and the difference is whether anything is blocked:

    a refusal      the seal or the compiler would say no. It carries `where`,
                   `expected`, `got` and repairs whose `options` are computed
                   from the graph, and the step that answers it is named.
    an opening     nothing is refused, and something is still unfinished: a
                   class nothing can ever be, a slot no class carries, a
                   description nobody wrote. Listed in `OPEN` below.

The gates stop at the first problem, which is right for a gate and useless for
somebody editing. So the two readers that can refuse more than once —
`seal.uri_refusals` and `seal.role_refusals` — are generators, and `check`
already collects the compiler's. No rule is re-implemented here; if it were,
the studio would say a draft is fine and `seal` would refuse it, which is the
failure the first attempt at this was built out of.

Nothing here writes.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from compile import _covered, plan, tables  # noqa: E402
from components.modules import diff as diff_read  # noqa: E402
from components.modules.check import check  # noqa: E402
from components.modules.compose import matches  # noqa: E402
from components.modules.store import APPLICATION  # noqa: E402
from components.modules.roles import (  # noqa: E402
    NOT_TAUGHT, _above, _bindings, _fills, taught,
)
from components.refusal import Refusal  # noqa: E402
from components import standard  # noqa: E402
from components.examples import examples as business  # noqa: E402
from components.studio import changes as changed  # noqa: E402
from components.studio.draft import (  # noqa: E402
    CLASS_FIELDS, DRAFT, ENUM_FIELDS, EXAMPLE_FIELDS, FIELDS, OPERATIONS,
    SLOT_FIELDS, USAGE_FIELDS, enums_seen, examples_of, facets_of, open_draft, path,
    ranges, seen, terms, text_of, transcript,
)
from seal import (  # noqa: E402
    _facts, _one_version_per_module, _pins_already_sealed, _slot_ranges,
    _transcript, _valid_from, _validate, composed, facet_refusals, kind_refusals,
    name_refusals, range_refusals,
    role_refusals, uri_refusals,
)

# What is unfinished without anything refusing it. A closed list, like the
# refusal codes are, and for the same reason: "what else is there to do here"
# is answerable without reading the code. None of these stops a seal — a
# module may perfectly well declare a class nobody ever states — and every one
# of them is something the author probably did not mean.
OPEN = {
    "nothing_declared": "a draft with no class in it yet",
    "class_is_empty": "a class carrying no slot",
    "class_has_no_rows": "a class nothing can be stated to be and no rule derives",
    "slot_is_loose": "a slot no class carries, so nothing is ever stated under it",
    **standard.DOUBTS,
    "no_examples": "a draft no business example holds to anything, so nothing "
                   "says what its numbers must be",
    "example_expects_nothing": "an example that records things and expects no "
                               "number of them, so it can never fail",
}

# Which step answers which refusal. Small and closed on purpose: a refusal the
# studio cannot name a step for is still a hole, and its repairs still carry
# the options — it just has no button. Inventing a step for every code would
# be guessing on behalf of the author.
#
# `where` is read for the names, because that is where the gate put them. The
# two shapes are the gates' own and a test holds them to it.
ANSWERS = ("binding_unfilled", "binding_ambiguous", "slot_without_uri",
           "no_valid_from", "name_clash", "range_unknown", "column_unchecked",
           "example_not_agreed") + tuple(standard.CHECKS)


def _map(store, name, document):
    """The draft read as a map: everything but the version it does not have.

    Every reader that only reads takes one. Nothing that writes to the kernel
    is ever given one, because an assertion has to name the version it was
    stated under, and a draft is not a version.
    """
    view = _validate(text_of(document), DRAFT, store)
    return {"path": path(store, name), "view": view, "version": None,
            "label": f"{name}@draft"}


def inspect(store, name, document, conn=None):
    """Every refusal this draft would meet, collected instead of thrown.

    The seal's readers first, then the compiler's, then the business examples.
    A draft that cannot be parsed or whose pins do not resolve stops here with
    one refusal: there is nothing below it to read, and a page full of
    consequences of one missing import helps nobody.

    The examples need a database to run in — each in a scratch log of its own
    on `conn`, rolled back, so nothing reaches the log. Without one they are
    listed and not run, and `examples_run` says so.
    """
    out = {"refusals": [], "tables": [], "map": None, "examples": [],
           "examples_run": False, "doubts": []}
    try:
        held = examples_of(store, name)
    except Refusal as exc:
        out["refusals"].append(exc.as_dict())
        held = {}
    out["examples"] = [_unrun(example, body) for example, body in held.items()]
    try:
        map_ = _map(store, name, document)
    except Refusal as exc:
        out["refusals"].append(exc.as_dict())
        return out
    out["map"] = map_
    view = map_["view"]
    # Read as it would be sealed: under the names the store composes it with.
    try:
        document = composed(store, document, name)
    except Refusal as exc:
        out["refusals"].append(exc.as_dict())
        return out
    annotations = document.get("annotations") or {}

    missing_uris = [r for r in uri_refusals(view, DRAFT)]
    out["refusals"] += [r.as_dict() for r in missing_uris]
    out["refusals"] += [r.as_dict() for r in role_refusals(view, document, DRAFT)]
    out["refusals"] += [r.as_dict() for r in range_refusals(view, document, DRAFT)]

    def collect(reader, *args):
        try:
            reader(*args)
        except Refusal as exc:
            out["refusals"].append(exc.as_dict())

    # As it would be sealed now: a pin to a version sealed after this moment
    # is the one thing about a draft that can go wrong by the clock alone.
    collect(_pins_already_sealed, store, document,
            datetime.now(timezone.utc), DRAFT)
    collect(_one_version_per_module, store, document, DRAFT)
    for reader, args in ((name_refusals, (name,)), (kind_refusals, ()),
                         (facet_refusals, ())):
        try:
            out["refusals"] += [r.as_dict() for r in reader(store, document, DRAFT, *args)]
        except Refusal as exc:
            out["refusals"].append(exc.as_dict())
    collect(_valid_from, annotations, DRAFT)
    collect(_transcript, annotations, path(store, name), DRAFT)
    if not missing_uris:
        # Facts are checked against the predicates the draft declares, so a
        # draft still missing one of those is asked about that first.
        collect(_facts, annotations, _slot_ranges(view, DRAFT), DRAFT, view)

    report = check(store, name, "draft", map_=map_)
    out["refusals"] += report["refusals"]
    out["tables"] = report["tables"]
    # What the examples owe the draft needs no log: whether each is agreed,
    # and whether every column the draft computes has a number in one.
    out["refusals"] += [r.as_dict() for r in
                        business.contract_refusals(map_, document, held)]
    # How it is written down, whoever wrote it: the seal's last reading.
    out["refusals"] += [r.as_dict() for r in
                        standard.refusals(document, held, _range_in(view))]
    out["doubts"] = standard.doubts(document, held)

    if conn is not None and held:
        results = business.run(conn, map_, held)
        out["examples"] = business.report(results)
        out["examples_run"] = True
        # A table the compiler refuses stops every example that reads it, with
        # the compiler's own refusal. That one is already listed above.
        said = {(r["code"], r["where"]) for r in out["refusals"]}
        out["refusals"] += [r.as_dict() for r in business.refusals(results)
                            if (r.code, r.where) not in said]
    return out


def _range_in(view):
    """A slot's range as the map reads it: inherited from the binding it
    fills where it states none."""
    def range_of(slot_name):
        try:
            return view.induced_slot(slot_name).range
        except Exception:  # noqa: BLE001 - a slot LinkML cannot induce has none
            return None
    return range_of


def _unrun(example, body):
    """An example as the file holds it, before anything has run it."""
    return {"name": example, "says": str(body.get("says") or ""),
            "agreed": business.agreed(body),
            "records": len(body.get("records") or []),
            "expected": len(body.get("expect") or []),
            "checks": [], "tables": [], "refusals": [], "passed": None, "waits": False}


def _about(refusal):
    """The names a gate put in `where`, for the step that answers it.

    `binding_unfilled` and `binding_ambiguous` write `Class.binding`;
    `slot_without_uri` writes `file: slot`. Read here rather than carried as
    extra fields, because a refusal's shape is the same for every reader and a
    field only the studio used would be a field only the studio maintained.
    """
    where = refusal["where"]
    if refusal["code"] in ("binding_unfilled", "binding_ambiguous"):
        class_name, _, binding = where.partition(".")
        return {"class": class_name, "binding": binding}
    if refusal["code"] == "column_unchecked":
        class_name, _, column = where.partition(".")
        return {"class": class_name, "column": column}
    if refusal["code"] == "example_not_agreed":
        return {"example": where.removeprefix("example ")}
    if refusal["code"] in ("slot_without_uri", "range_unknown"):
        _, _, slot = where.partition(": ")
        return {"slot": slot}
    if refusal["code"] in standard.CHECKS:
        # `class Name`, `slot name title`, `enum Name value v`, `module title`.
        kind, _, rest = where.partition(" ")
        term, _, part = rest.partition(" ")
        return {"kind": kind, kind: term, "part": part}
    if refusal["code"] == "name_clash":
        _, _, said = where.partition(": ")
        kind, _, term = said.partition(" ")
        return {"kind": kind, kind: term}
    return {}


def _step_for(refusal):
    """The one step that answers this refusal, where the studio has one."""
    code, about = refusal["code"], _about(refusal)
    options = [o for repair in refusal["repairs"] for o in repair["options"]]
    if code == "binding_unfilled":
        return {"op": "bind", "args": {"binding": about["binding"]},
                "choose": "slot", "options": options}
    if code == "binding_ambiguous":
        return {"op": "unbind", "args": {}, "choose": "slot", "options": options}
    if code == "slot_without_uri":
        return {"op": "set_slot",
                "args": {"slot": about["slot"], "field": "slot_uri"},
                "choose": "value", "options": []}
    if code == "no_valid_from":
        return {"op": "set", "args": {"field": "valid_from"},
                "choose": "value", "options": []}
    if code == "range_unknown":
        return {"op": "set_slot", "args": {"slot": about["slot"], "field": "range"},
                "choose": "value", "options": options}
    if code == "name_clash" and "this draft" in refusal["got"]:
        kind = about["kind"]
        return {"op": f"rename_{kind}", "args": {kind: about[kind]},
                "choose": "to", "options": []}
    if code == "column_unchecked":
        # The first repair's options are the examples there are to add the
        # number to; with none, the step is to write one.
        held = refusal["repairs"][0]["options"]
        if not held:
            return {"op": "add_example", "args": {}, "choose": "example",
                    "options": []}
        return {"op": "expect", "args": {"table": about["class"]},
                "choose": "example", "options": held}
    if code == "example_not_agreed":
        return {"op": "agree_example", "args": {"example": about["example"]},
                "choose": "example", "options": [about["example"]]}
    if code in standard.CHECKS:
        return _mend(code, about, options)
    return None


# Where each kind of term has its fields set.
_SET = {"class": ("set_class", "class"), "slot": ("set_slot", "slot"),
        "example": ("set_example", "example")}

# The field each break of the standard is mended in.
_MENDED_IN = {"description_missing": "description", "unit_missing": "unit",
              "direction_missing": standard.DIRECTION,
              "time_meaning_missing": standard.TIME_MEANING}


def _mend(code, about, options):
    """The step that mends one break of the standard, where the studio has one.

    A name is mended by renaming; a text by setting it again; a meaning by
    setting the field that says it. An enum has no rename, so a name of one
    is left to the refusal's own words.
    """
    kind, part = about["kind"], about["part"]
    term = about.get(kind)
    steps = ("rename_class", "rename_slot", "set", "set_slot", "set_example", "label")
    answers = [o for o in options if o not in steps]
    if kind == "module":
        return {"op": "set", "args": {"field": term}, "choose": "value",
                "options": []}
    if kind in ("class", "slot") and not part and (
            code in ("name_not_standard", "prefix_not_shared")
            or (code == "not_in_english" and f"rename_{kind}" in options)):
        return {"op": f"rename_{kind}", "args": {kind: term}, "choose": "to",
                "options": answers}
    field = _MENDED_IN.get(code)
    if code == "not_in_english":
        field = part or ("says" if kind == "example" else "description")
    if field and kind in _SET:
        op, key = _SET[kind]
        return {"op": op, "args": {key: term, "field": field}, "choose": "value",
                "options": answers}
    return None


def _question(kind, where, detail):
    """One hole in a question, assembled from its parts and never stored apart."""
    if kind == "binding_unfilled":
        return (f"which slot of {detail.get('class')} is its "
                f"{detail.get('binding')}?")
    if kind == "binding_ambiguous":
        return (f"two slots say they are {detail.get('class')}'s "
                f"{detail.get('binding')} — which one is not?")
    if kind == "slot_without_uri":
        return f"what predicate is {detail.get('slot')} recorded under?"
    if kind == "no_valid_from":
        return "when did these definitions take effect?"
    if kind == "range_unknown":
        return f"what does {detail.get('slot')} hold? What it names is not in sight"
    if kind == "name_clash":
        what = detail.get("kind")
        return (f"a module this draft pins declares the {what} "
                f"{detail.get(what)} too — what should this draft's be called?")
    if kind == "column_unchecked":
        return (f"what number should {detail.get('class')}'s "
                f"{detail.get('column')} come to, in an example the business "
                f"agrees with?")
    if kind == "example_not_agreed":
        return (f"is the example {detail.get('example')} what the business "
                f"does, and are its numbers right?")
    if kind == "name_not_standard":
        return f"what should {where} be called, in the shape every module uses?"
    if kind == "prefix_not_shared":
        return (f"{where} does not start with the word the other slots of its "
                f"class start with: what should it be called?")
    if kind == "description_missing":
        return f"what is {where}? Say it in a sentence, in English"
    if kind == "not_in_english":
        return f"how is the {where} said in English? Keep the person's words as a label"
    if kind == "unit_missing":
        return f"what unit is {where} counted in?"
    if kind == "direction_missing":
        return f"which way does {where} run: what does a positive value mean?"
    if kind == "time_meaning_missing":
        return (f"what moment is {where}: when it happened, when it was "
                f"recorded, when it takes effect, or when it is due?")
    if kind == "maybe_not_english":
        return f"is what the {where} says written in English?"
    if kind == "nothing_declared":
        return "what kinds of thing does this module know about?"
    if kind == "class_is_empty":
        return f"what is said about a {where}?"
    if kind == "class_has_no_rows":
        return f"how would anything ever become a {where}?"
    if kind == "slot_is_loose":
        return f"which class is {where} said about?"
    if kind == "no_examples":
        return ("what would the business expect this to add up to? Give one "
                "example, with its numbers")
    if kind == "example_expects_nothing":
        return f"what numbers should the example {where} come to?"
    return f"what about {where}?"


def _hole(kind, where, *, blocking, because, detail=None, step=None, refusal=None):
    return {"kind": kind, "where": where, "blocking": blocking,
            "question": _question(kind, where, detail or {}),
            "because": because, "step": step, "refusal": refusal}


def _carriers(store, document):
    """Every role in sight that brings a slot saying which class an entity is.

    The answer to "how would anything become one of these": claim a role that
    carries the predicate, and the log can say it. Computed rather than named,
    so a second module declaring such a role is offered too.
    """
    classes, slots = seen(store, document)
    out = []
    for role, body in classes.items():
        if not body.get("abstract"):
            continue
        reach = [role] + sorted(_above(classes, role))
        carried = [s for c in reach for s in (classes[c].get("slots") or [])]
        if any((slots.get(s) or {}).get("designates_type") for s in carried):
            out.append(role)
    return taught(sorted(out))


def _things_in_sight(store, document):
    """Every class of a pinned module a facet could add to: the things some
    module records, not the roles."""
    classes, _ = seen(store, document)
    return sorted(c for c, body in classes.items()
                  if body["module"] is not None and not body.get("abstract"))


def with_rows_of(map_):
    """Every class this draft would build a table for, by the compiler's rule.

    A class outside it is not refused: it compiles, and it is empty forever.
    That is the difference between `class_has_no_rows` and a refusal.
    """
    if map_ is None:
        return set()
    try:
        return set(tables(map_))
    except Refusal:
        # Nothing to compile is itself an answer, and it is already among the
        # refusals if it mattered. The openings below do not need it.
        return set()


# The one module every draft pins whatever it is about (`studio.draft`).
CORE = "@uniti/core"


def composes(store, name, document):
    """Whether the draft is an application made of the modules it pins.

    An application is a business's composition: the modules it pins, and its
    own examples of what their numbers must come to for that business
    (DESIGN_NOTES.md §15.2). It may declare nothing of its own, and is a
    version all the same: what it holds is the choice of modules, and the
    examples that check them.
    """
    try:
        kind = store.kind(name)
    except Refusal:
        return False
    return kind == APPLICATION and any(pinned != CORE for pinned, _ in store.imports(document))


def holes(store, name, document, found):
    """Every question this draft is standing in, the blocking ones first.

    `found` is what `inspect` collected. A refusal becomes a hole with the step
    that answers it; the rest are the openings in `OPEN`, which nothing refuses
    and which are the difference between a module that compiles and a module
    somebody else can use.
    """
    out = []
    for refusal in found["refusals"]:
        hole = _hole(refusal["code"], refusal["where"], blocking=True,
                     because=refusal["expected"], detail=_about(refusal),
                     step=_step_for(refusal), refusal=refusal)
        if refusal["code"] not in ANSWERS:
            # No step to name, so no question of the studio's own either: the
            # refusal already says it, in the words of whichever gate refused.
            hole["question"] = refusal["sentence"]
        out.append(hole)

    own_classes = document.get("classes") or {}
    own_slots = document.get("slots") or {}
    # A facet is a slot on a class another module owns: a module of facets
    # alone has declared something, and its slots are not loose.
    adds_to = facets_of(document)
    if not own_classes and not adds_to and not composes(store, name, document):
        out.append(_hole("nothing_declared", name, blocking=False,
                         because=OPEN["nothing_declared"],
                         step={"op": "add_class", "args": {}, "choose": "class",
                               "options": []}))

    with_rows = with_rows_of(found["map"])
    # A draft that computes something is already asked for its numbers, one
    # column at a time and blocking; the opening is for one that computes
    # nothing and may still be worth an example.
    computes = any(r["code"] == "column_unchecked" for r in found["refusals"])
    if own_classes and not found["examples"] and not computes:
        out.append(_hole("no_examples", name, blocking=False,
                         because=OPEN["no_examples"],
                         step={"op": "add_example", "args": {},
                               "choose": "example", "options": []}))
    for example in found["examples"]:
        if not example["expected"]:
            out.append(_hole("example_expects_nothing", example["name"],
                             blocking=False,
                             because=OPEN["example_expects_nothing"],
                             step={"op": "expect",
                                   "args": {"example": example["name"]},
                                   "choose": "table",
                                   "options": sorted(with_rows)}))
    carried = _carriers(store, document)
    attached = {s for body in own_classes.values()
                for s in ((body or {}).get("slots") or [])} | set(adds_to)
    for class_name, body in sorted(own_classes.items()):
        body = body or {}
        if body.get("abstract"):
            continue
        if not body.get("slots"):
            out.append(_hole("class_is_empty", class_name, blocking=False,
                             because=OPEN["class_is_empty"],
                             step={"op": "attach", "args": {"class": class_name},
                                   "choose": "slot", "options": sorted(own_slots)}))
        elif class_name not in with_rows:
            out.append(_hole("class_has_no_rows", class_name, blocking=False,
                             because=OPEN["class_has_no_rows"],
                             step={"op": "fill_role", "args": {"class": class_name},
                                   "choose": "role", "options": carried}))

    for slot_name, body in sorted(own_slots.items()):
        body = body or {}
        if slot_name not in attached and not body.get("abstract"):
            out.append(_hole("slot_is_loose", slot_name, blocking=False,
                             because=OPEN["slot_is_loose"],
                             step={"op": "attach", "args": {"slot": slot_name},
                                   "choose": "class",
                                   "options": sorted(own_classes)
                                   + _things_in_sight(store, document)}))
    # What the standard cannot tell is English: asked, never refused.
    for where, _said in found.get("doubts") or []:
        kind, _, term = where.partition(" ")
        step = None
        if kind in _SET:
            op, key = _SET[kind]
            step = {"op": op, "args": {key: term, "field": "says" if kind == "example"
                                       else "description"},
                    "choose": "value", "options": []}
        out.append(_hole("maybe_not_english", where, blocking=False,
                         because=OPEN["maybe_not_english"], step=step))
    return sorted(out, key=lambda h: (not h["blocking"], h["where"]))


_FIELDS_OF = {"set": FIELDS, "set_class": CLASS_FIELDS, "set_slot": SLOT_FIELDS,
              "set_enum": ENUM_FIELDS, "set_usage": USAGE_FIELDS,
              "set_example": EXAMPLE_FIELDS}


def steps(store, name, document):
    """Every operation, with the answers that fit this draft as it stands.

    This is the list the form draws and the list the agent chooses from, and
    it is one list. An argument whose answers are a finite set carries them;
    one that depends on another argument says which — `column` is a slot of
    whichever class was named, and that class is not known until it is.
    """
    classes, slots = seen(store, document)
    own_classes = sorted(document.get("classes") or {})
    own_slots = sorted(document.get("slots") or {})
    pinned = [str(i) for i in (document.get("imports") or [])
              if not str(i).startswith("linkml:")]
    try:
        held = examples_of(store, name)
    except Refusal:
        # A file the studio cannot read is a hole of its own; it offers no
        # answers here.
        held = {}
    options = {
        "own_example": list(held),
        "record": sorted({str(r.get("record")) for body in held.values()
                          for r in (body.get("records") or [])}),
        "own_class": own_classes,
        "own_slot": own_slots,
        "own_enum": sorted(document.get("enums") or {}),
        "class": sorted(classes),
        "slot": sorted(slots),
        "role": taught(sorted(c for c, b in classes.items() if b.get("abstract"))),
        "binding": sorted(s for s, b in slots.items() if b.get("abstract")),
        "range": ranges(store, document),
        "pin": sorted(f"{n}@{v['version']}" for n in store.names()
                      if n != name for v in store.versions(n)),
        "held_pin": pinned,
        "direction": list(standard.DIRECTIONS),
        "time_meaning": list(standard.TIME_MEANINGS),
        "term": terms(document, held),
    }

    def argument(op, key, kind, required):
        out = {"name": key, "kind": kind, "required": required,
               "options": list(options.get(kind, ()))}
        if kind == "field":
            out["options"] = list(_FIELDS_OF[op])
        if kind == "column":
            out["depends"] = "class"
        if kind == "record":
            out["depends"] = "example"
        return out

    return [{
        "op": op,
        "does": spec["does"],
        "takes": [argument(op, k, v, True) for k, v in spec["takes"].items()]
                 + [argument(op, k, v, False) for k, v in spec["may"].items()],
    } for op, spec in OPERATIONS.items()]


def _roles_of(store, document):
    """Every role in sight, and how far this draft's own classes have filled it.

    The picture §7.2 asks for: the role, what it obliges, and a tick or a hole
    per binding. Read off the documents, the same way the store's own role
    panel reads them, so a draft and a sealed version look alike on the page.
    """
    classes, slots = seen(store, document)
    out = []
    for role in sorted(c for c, b in classes.items() if b.get("abstract")):
        bindings = _bindings(classes, slots, role)
        filled = []
        for class_name in sorted(document.get("classes") or {}):
            if (classes[class_name].get("abstract")
                    or role not in _above(classes, class_name)):
                continue
            filled.append({
                "class": class_name,
                "bindings": {b["name"]: (_fills(classes, slots, class_name,
                                                b["name"]) or [None])[0]
                             for b in bindings},
            })
        # Not offered to a new class, so in sight only where one fills it.
        if role in NOT_TAUGHT and not filled:
            continue
        out.append({"name": role, "module": classes[role]["module"],
                    "description": classes[role].get("description") or "",
                    "bindings": bindings, "filled_by": filled})
    return out


def _borrowed(store, document):
    """The classes from pinned modules this draft actually sits among.

    A map is not a catalogue. What belongs on it is what this module points at
    — the range of one of its slots, or what one of its classes specialises —
    and then whatever those point at in turn. Reachability, not everything
    pinned: a module pins a whole vocabulary and uses a corner of it, and
    drawing the whole vocabulary is how a map stops being readable.

    Roles are not here. A role is a shape a class claims, and it belongs drawn
    on the class that claimed it, not standing beside it as another thing.
    """
    classes, slots = seen(store, document)
    own = document.get("classes") or {}

    def points_at(body):
        out = [(body or {}).get("is_a")]
        for slot_name in ((body or {}).get("slots") or []):
            out.append((slots.get(slot_name) or {}).get("range"))
        return [str(n) for n in out if n]

    wanted = [str((b or {}).get("range")) for b in (document.get("slots") or {}).values()
              if (b or {}).get("range")]
    # What a facet adds to is drawn, with the facet on it.
    wanted += list(facets_of(document).values())
    for body in own.values():
        wanted += points_at(body)

    found = {}
    while wanted:
        class_name = wanted.pop()
        body = classes.get(class_name)
        if class_name in found or class_name in own or body is None:
            continue
        if body.get("abstract"):
            continue
        found[class_name] = body
        wanted += points_at(body)

    return _described(classes, slots, found)


def _workings(map_, own, shapes):
    """Where every number this draft works out comes from, as the compiler reads it.

    The rule on a slot says `over: Flow`; what it actually adds up is the
    `qty_delta` of every Movement, because Movement is what fills Flow. That
    is the compiler's reading, not the document's, so it is asked for here
    rather than worked out again: per table this draft computes, its keys,
    and per worked-out column the classes it reads, the fields of each it
    reads and, for a sum, the field of each that says which row it lands on.

    A table the compiler refuses has no workings to show; its refusal is
    already on the page.
    """
    if map_ is None:
        return []
    view = map_["view"]

    def fields_of(class_name):
        return {str(s.name) for s in view.class_induced_slots(class_name)
                if not s.abstract}

    out = []
    for class_name in sorted(own):
        if shapes.get(class_name) != "grouped":
            continue
        try:
            planned = plan(map_, class_name)
        except Refusal:
            continue
        columns = []
        for col in planned["columns"]:
            name, kind = col["name"], col["kind"]
            if kind == "aggregate":
                spec = planned["aggregates"][name]
                reads = []
                for source in spec["covers"]:
                    held = fields_of(source)
                    reads.append({
                        "class": source,
                        "fields": [s for s in spec["measure_slots"] if s in held],
                        # The field of the source each key is read off: for a
                        # key one record away, the field naming that record,
                        # and under `via` the fields of that record it is.
                        "by": {key: next((s for s, _ in pairs if s in held), None)
                               for key, pairs in {**spec["by_slots"],
                                                  **spec.get("through_slots", {})}.items()},
                        **({"via": {key: [s for s, _ in spec["by_slots"][key]]
                                    for key in spec["through_slots"]}}
                           if spec.get("through_slots") else {}),
                    })
                columns.append({"name": name, "kind": kind,
                                "operator": spec["operator"], "reads": reads})
            elif kind == "parameter":
                spec = planned["parameters"][name]
                key_range = next((str(c["range"]) for c in planned["columns"]
                                  if c["name"] == spec["of"]), None)
                below = _covered(view, key_range) if key_range else []
                columns.append({"name": name, "kind": kind, "of": spec["of"], "reads": [
                    {"class": source, "fields": [spec["slot"]], "by": {}}
                    for source in below if spec["slot"] in fields_of(source)]})
            elif kind == "expression":
                columns.append({"name": name, "kind": kind, "reads": []})
        out.append({"class": class_name, "keys": planned["keys"], "columns": columns})
    return out


def _described(classes, slots, names):
    """Classes of pinned modules, as the map draws one it cannot change."""
    return [{
        "name": class_name,
        "description": classes[class_name].get("description") or "",
        "labels": standard.labels(classes[class_name]),
        "module": classes[class_name]["module"],
        "fills": [str(m) for m in (classes[class_name].get("mixins") or [])],
        "slots": [{"name": s,
                   "range": (slots.get(s) or {}).get("range"),
                   "identifier": bool((slots.get(s) or {}).get("identifier")),
                   "labels": standard.labels(slots.get(s))}
                  for s in (classes[class_name].get("slots") or [])],
    } for class_name in sorted(names)]


def _read_from(store, document, workings, borrowed):
    """The classes a rule reads that the map would not otherwise draw.

    A sum over a role reaches whichever classes fill it, and nothing in this
    module points at those — so the place the numbers come from was missing
    from the map. Drawn beside the borrowed classes, and only these.
    """
    classes, slots = seen(store, document)
    drawn = set(document.get("classes") or {}) | {b["name"] for b in borrowed}
    wanted = {read["class"] for table in workings for column in table["columns"]
              for read in column["reads"]}
    return _described(classes, slots, [n for n in wanted
                                       if n not in drawn and n in classes])


def _recorded(store, name, examples, view=None):
    """Each example with the records it states, in the order it states them.

    What a number on the map was worked out from: the page shows the records
    that went into it beside it. A record names its class once, where it is
    first stated, and is carried on by name after that, as the file reads.
    And what the example says in the words of its people (`labels`), which
    the page shows them in place of the English it is recorded in.

    Names as the map names them, by the composition's one rule, so a record
    of `Movement` is drawn on the map's `stock_moves__Movement`.
    """
    known = set(view.all_classes()) if view is not None else set()

    def called_as(wanted, among):
        found = matches(wanted, among)
        return found[0] if len(found) == 1 else str(wanted)

    def slots_of(class_name):
        if view is None or class_name not in known:
            return set()
        return {str(s.name) for s in view.class_induced_slots(class_name)}

    try:
        held = examples_of(store, name)
    except Refusal:
        return examples

    def plain(value):
        return value if value is None or isinstance(value, (bool, int, float, str)) \
            else str(value)

    out = []
    for example in examples:
        class_of = {}
        records = []
        for record in (held.get(example["name"]) or {}).get("records") or []:
            record = record or {}
            called = str(record.get("record") or "")
            if record.get("class"):
                class_of[called] = called_as(record["class"], known)
            carried = slots_of(class_of.get(called))
            records.append({
                "record": called,
                "class": class_of.get(called),
                "when": plain(record.get("when")),
                "facts": {called_as(k, carried): plain(v)
                          for k, v in (record.get("facts") or {}).items()},
            })
        labels = (held.get(example["name"]) or {}).get("labels") or {}
        out.append({**example, "recorded": records,
                    "labels": {str(k): str(v) for k, v in labels.items()}})
    return out


def _rule_of(body):
    if (body or {}).get("equals_expression"):
        return {"kind": "expression", "spec": str(body["equals_expression"])}
    for kind in ("aggregate", "parameter"):
        held = ((body or {}).get("annotations") or {}).get(kind)
        if held is not None:
            if isinstance(held, dict) and set(held) == {"value"}:
                held = held["value"]
            return {"kind": kind, "spec": held}
    return None


def state(store, name, conn=None):
    """One draft, everything about it, in one read.

    The three columns of the studio in one object: what is being built, the
    holes to stand in, and what it would do — the checks, the business
    examples and the numbers they come to, the diff against the version this
    would supersede, and the steps taken so far. The examples run on `conn`,
    and are only listed without one.
    """
    # The store first: a name it does not hold is its refusal to make, not a
    # missing draft, and the two are answered by different people.
    manifest = store.manifest(name)
    document = open_draft(store, name)
    found = inspect(store, name, document, conn)
    held = [v["version"] for v in store.versions(name)]
    revises = held[-1] if held else None
    own_classes = document.get("classes") or {}
    own_slots = document.get("slots") or {}
    attached = {}
    for class_name, body in own_classes.items():
        for slot_name in ((body or {}).get("slots") or []):
            attached.setdefault(slot_name, []).append(class_name)

    classes, slots = seen(store, document)
    annotations = document.get("annotations") or {}
    found_holes = holes(store, name, document, found)
    with_rows = with_rows_of(found["map"])
    borrowed = _borrowed(store, document)
    workings = _workings(found["map"], own_classes,
                         {t["class"]: t["shape"] for t in found["tables"]})
    since = changed.between(
        changed.look_at_version(store, name, revises),
        {"document": document, "examples": examples_of(store, name)}, name)
    # Nothing to freeze: a new module that declares nothing of its own, or a
    # revision that changes nothing. Not a refusal — nothing is wrong with it —
    # but not a version either. An application made of the modules it pins is
    # not empty: the composition is what it holds.
    empty = not (own_classes or own_slots or document.get("enums")
                 or composes(store, name, document)) \
        and (revises is None or not since)
    return {
        "name": name,
        "title": document.get("title"),
        "description": document.get("description"),
        "labels": standard.labels(document),
        "purpose": manifest.get("purpose"),
        "valid_from": annotations.get("valid_from"),
        "versions": held,
        "revises": revises,
        "becomes": f"v{len(held) + 1}",
        "pins": [{"name": p[0], "version": p[1]} for p in store.imports(document)],
        "sees": {"classes": len(classes), "slots": len(slots)},
        "classes": [{
            "name": class_name,
            "description": (body or {}).get("description") or "",
            "labels": standard.labels(body),
            "fills": [str(m) for m in ((body or {}).get("mixins") or [])],
            "is_a": (body or {}).get("is_a"),
            "slots": list((body or {}).get("slots") or []),
            # What a slot obliges on this class alone, where it says so.
            "usage": {s: dict(u or {}) for s, u in
                      ((body or {}).get("slot_usage") or {}).items()},
            "has_rows": class_name in with_rows,
        } for class_name, body in sorted(own_classes.items())],
        "slots": [{
            "name": slot_name,
            "title": str((body or {}).get("title") or slot_name),
            "description": (body or {}).get("description") or "",
            "labels": standard.labels(body),
            "slot_uri": (body or {}).get("slot_uri"),
            "range": (body or {}).get("range"),
            "unit": standard.unit_of(body),
            "direction": standard.annotation(body, standard.DIRECTION),
            "time_meaning": standard.annotation(body, standard.TIME_MEANING),
            "identifier": bool((body or {}).get("identifier")),
            "designates_type": bool((body or {}).get("designates_type")),
            "required": bool((body or {}).get("required")),
            "multivalued": bool((body or {}).get("multivalued")),
            "binds": (body or {}).get("is_a"),
            "rule": _rule_of(body),
            "on": attached.get(slot_name, []),
            # The class another module owns that this slot adds to: a facet.
            "adds_to": facets_of(document).get(slot_name),
        } for slot_name, body in sorted(own_slots.items())],
        "enums": [{
            "name": enum_name,
            "description": (body or {}).get("description") or "",
            "values": list(((body or {}).get("permissible_values") or {})),
            "labels": standard.labels(body),
            "value_labels": {str(v): standard.labels(b) for v, b in
                             ((body or {}).get("permissible_values") or {}).items()
                             if standard.labels(b)},
            "module": body["module"],
        } for enum_name, body in sorted(enums_seen(store, document).items())],
        "roles": _roles_of(store, document),
        "borrowed": borrowed,
        "workings": workings,
        "read_from": _read_from(store, document, workings, borrowed),
        "tables": found["tables"],
        "examples": _recorded(store, name, found["examples"],
                              found["map"]["view"] if found["map"] else None),
        "examples_run": found["examples_run"],
        "refusals": found["refusals"],
        "holes": found_holes,
        "blocking": sum(1 for h in found_holes if h["blocking"]),
        "steps": steps(store, name, document),
        "taken": transcript(store, name),
        "diff": diff_read.compare(store.document(name, revises) if revises else {},
                                  document),
        # What sealing it would change, as the map draws it: everything, for a
        # module with no version yet.
        "changes": since,
        "empty": empty,
        # Examples nobody ran are examples nobody knows the answer to.
        "sealable": not empty and not found["refusals"]
                    and (found["examples_run"] or not found["examples"]),
        "document": text_of(document),
    }


__all__ = ["OPEN", "holes", "inspect", "state", "steps", "with_rows_of"]

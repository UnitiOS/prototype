"""draft — the version that does not exist yet, and the steps that made it.

A draft is a file, `draft.yaml`, in the module's own directory, beside the
versions already sealed there. It is the only thing in the store that can be
edited: a sealed version never is. Nothing reads a draft except this, the
checks, and — once somebody seals it — `seal` itself.

Every change to it is an **operation** from the list below, and the list is
closed. That is the whole design:

> Nobody writes YAML. A step is chosen from an enumerated set, and the system
> writes the file.

A closed list is what makes the form and the agent one mechanism rather than
two. `steps()` enumerates the operations with the answers that fit right now;
a form draws them as controls and an agent chooses from them, and neither can
name a class or a slot that is not there. When an argument is wrong anyway,
the refusal carries the finite set it should have come from — the same
machinery every other gate uses, so there is nothing here to learn twice.

Beside the draft sits `draft.txt`, one line per operation, in order. It is
evidence: it says how this version came to look the way it does, and it is
what `seal` copies out as the transcript. Nobody writes that either.

Two things this deliberately does not do.

    It does not judge.  Whether the draft holds is answered by running the
                        seal's own readers and the compiler's over it —
                        `holes.inspect`. An operation refuses only what it
                        cannot perform at all: a class that is not there, a
                        field that does not exist. A second judge is how the
                        first attempt at this went wrong.
    It does not write to the kernel.  A draft is a file. Nothing about it
                        reaches the log until it is sealed, and a draft that
                        is discarded never happened.
"""

import re
import shutil
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from components.examples import examples as business  # noqa: E402
from components.modules.roles import _above  # noqa: E402
from components.refusal import Refusal, Repair  # noqa: E402
from compile import SQL_TYPE, SYNTAX  # noqa: E402

DRAFT = "draft.yaml"
TRANSCRIPT = "draft.txt"
MANIFEST = "package.yaml"
# The business examples the draft is held to, beside it under its own name.
EXAMPLES = business.path_for(Path(DRAFT)).name

# The keys a module document holds, in the order they are written. A file
# whose keys move about on every save is a file whose diff is unreadable.
ORDER = ("id", "name", "title", "description", "prefixes", "default_prefix",
         "default_range", "imports", "classes", "slots", "enums", "annotations")

# Where a module started here declares its own terms, when nobody says
# otherwise. `.example` is reserved for exactly this (RFC 2606): a namespace
# that is well-formed, unique per module, and claims no domain on the internet.
BASE = "https://uniti.example"

# What a draft may say about itself, about one of its classes, and about one of
# its slots. Closed lists, because "which fields does this have" is a question
# a form and an agent both have to be able to ask, and a field that only some
# code knows about cannot be offered by either.
FIELDS = ("title", "description", "valid_from")
CLASS_FIELDS = ("description", "is_a")
SLOT_FIELDS = ("title", "description", "range", "slot_uri",
               "identifier", "required", "multivalued", "designates_type")
BOOLEAN_FIELDS = ("identifier", "required", "multivalued", "designates_type")
# An enum is a closed list of values; `values` is written `a, b, c`.
ENUM_FIELDS = ("description", "values")
# What a slot means on one class rather than everywhere it is used. LinkML's
# `slot_usage`, of which only `required` is offered: the same slot may be
# obligatory on an order line and optional on a note.
USAGE_FIELDS = ("required",)
# What may be said about a business example as a whole. Its records and its
# numbers are steps of their own.
EXAMPLE_FIELDS = ("says",)

# Who performs a step. A person, or an agent working on a person's behalf; the
# transcript says which, line by line, and the two are held to different
# rules about the examples. An agent proposes an example and a person agrees
# to it; once agreed, it is the business's word, and only a person changes it.
ACTORS = ("person", "agent")
_ACTOR = ContextVar("actor", default="person")

# The operations, what each one does, and what it takes. The kinds are what
# `steps()` turns into option lists, so they are the vocabulary a form renders
# and an agent chooses from:
#
#   text  word  uri  moment        typed in
#   pin   held_pin                 a sealed version, from the store
#   own_class  own_slot  own_enum  something this draft declares
#   own_example  record            an example beside it, and one of its records
#   class  slot  role  binding     something this draft can see
#   range  field  column  mapping  computed from what is around it
OPERATIONS = {
    "start": {
        "does": "create a module and open its first draft",
        "takes": {"title": "text", "description": "text"},
        "may": {"purpose": "text", "prefix": "word", "base": "uri"},
    },
    "revise": {
        "does": "open a draft from the latest sealed version of a module",
        "takes": {},
        "may": {},
    },
    "discard": {
        "does": "throw the draft away, sealing nothing",
        "takes": {},
        "may": {},
    },
    "set": {
        "does": "what this module is called, what it is for, and when its "
                "definitions took effect",
        "takes": {"field": "field", "value": "text"},
        "may": {},
    },
    "pin": {
        "does": "import one sealed version of another module",
        "takes": {"module": "pin"},
        "may": {},
    },
    "unpin": {
        "does": "drop an import",
        "takes": {"module": "held_pin"},
        "may": {},
    },
    "add_class": {
        "does": "declare a class: a kind of thing this module knows about",
        "takes": {"class": "word"},
        "may": {"description": "text"},
    },
    "remove_class": {
        "does": "take a class out of the draft",
        "takes": {"class": "own_class"},
        "may": {},
    },
    "rename_class": {
        "does": "rename a class, and everything in this draft that names it",
        "takes": {"class": "own_class", "to": "word"},
        "may": {},
    },
    "set_class": {
        "does": "a class's description, or what it is a kind of",
        "takes": {"class": "own_class", "field": "field", "value": "text"},
        "may": {},
    },
    "fill_role": {
        "does": "claim a role for a class, which obliges every binding it carries",
        "takes": {"class": "own_class", "role": "role"},
        "may": {},
    },
    "unfill_role": {
        "does": "drop a claim, and the obligations that came with it",
        "takes": {"class": "own_class", "role": "role"},
        "may": {},
    },
    "add_slot": {
        "does": "declare a slot, and the predicate the log records it under",
        "takes": {"slot": "word"},
        "may": {"slot_uri": "uri", "range": "range", "title": "text",
                "description": "text"},
    },
    "remove_slot": {
        "does": "take a slot out of the draft",
        "takes": {"slot": "own_slot"},
        "may": {},
    },
    "rename_slot": {
        "does": "rename a slot, keeping the predicate — so every fact already "
                "stated under it still belongs to it",
        "takes": {"slot": "own_slot", "to": "word"},
        "may": {},
    },
    "set_slot": {
        "does": "a slot's title, description, range, predicate, or what kind "
                "of slot it is",
        "takes": {"slot": "own_slot", "field": "field", "value": "text"},
        "may": {},
    },
    "add_enum": {
        "does": "declare a closed list of values, for a slot that may hold "
                "only one of them",
        "takes": {"enum": "word", "values": "text"},
        "may": {"description": "text"},
    },
    "set_enum": {
        "does": "an enum's description, or its values, written `a, b, c`",
        "takes": {"enum": "own_enum", "field": "field", "value": "text"},
        "may": {},
    },
    "remove_enum": {
        "does": "take an enum out of the draft",
        "takes": {"enum": "own_enum"},
        "may": {},
    },
    "set_usage": {
        "does": "what one slot obliges on one class only: whether this class "
                "requires it",
        "takes": {"class": "own_class", "slot": "slot", "field": "field",
                  "value": "text"},
        "may": {},
    },
    "attach": {
        "does": "put a slot on a class",
        "takes": {"class": "own_class", "slot": "slot"},
        "may": {},
    },
    "detach": {
        "does": "take a slot off a class",
        "takes": {"class": "own_class", "slot": "slot"},
        "may": {},
    },
    "bind": {
        "does": "name the slot that fills one binding of a role",
        "takes": {"slot": "own_slot", "binding": "binding"},
        "may": {},
    },
    "unbind": {
        "does": "take a slot off the binding it was filling",
        "takes": {"slot": "own_slot"},
        "may": {},
    },
    "aggregate": {
        "does": "derive a column by totalling something over every entity of "
                "a class or of a role",
        "takes": {"class": "own_class", "column": "column", "over": "class",
                  "sum": "slot", "by": "mapping"},
        # `where` narrows the rows to those whose slot is one class (slot=Class);
        # the three `convert_` answers are one conversion — the class holding
        # the factor, how its slots match the source's, and which slot the
        # factor is — written as the compiler's `convert: {using, on, factor}`.
        "may": {"where": "mapping", "convert_using": "class",
                "convert_on": "mapping", "convert_factor": "slot"},
    },
    "parameter": {
        "does": "derive a column by reading one fact off what a key names",
        "takes": {"class": "own_class", "column": "column", "of": "column",
                  "slot": "slot"},
        "may": {},
    },
    "expression": {
        "does": "derive a column by arithmetic on other columns of the same "
                "table: " + SYNTAX,
        "takes": {"class": "own_class", "column": "column", "expression": "text"},
        "may": {},
    },
    "unrule": {
        "does": "take the rule off a column, leaving the slot stated",
        "takes": {"slot": "own_slot"},
        "may": {},
    },
    "add_example": {
        "does": "write down a business example: a few records and the numbers "
                "they must add up to. Every change to the draft is held to it, "
                "and it cannot be sealed while one fails. `says` is the example "
                "in the business's own words",
        "takes": {"example": "word", "says": "text"},
        "may": {},
    },
    "set_example": {
        "does": "reword what an example says",
        "takes": {"example": "own_example", "field": "field", "value": "text"},
        "may": {},
    },
    "remove_example": {
        "does": "take an example out, with everything it records and expects",
        "takes": {"example": "own_example"},
        "may": {},
    },
    "record": {
        "does": "state one record in an example, as a form would: what it is "
                "(`class`, the first time), its facts written `slot=value, ...`, "
                "and the day it became true (`when`). A value naming another "
                "record is that record's name. The same record stated again "
                "with a later `when` is that record changing",
        "takes": {"example": "own_example", "record": "word"},
        "may": {"class": "class", "facts": "mapping", "when": "moment"},
    },
    "unrecord": {
        "does": "take a record out of an example, every statement of it",
        "takes": {"example": "own_example", "record": "record"},
        "may": {},
    },
    "expect": {
        "does": "say what the numbers must be: the table, the row (the value "
                "of its first column, or `column=value, ...`), and the columns "
                "with their numbers, `column=number, ...` — nothing after `=` "
                "means the cell must be empty. `at` is the day the table is "
                "read on, the whole of it; without it, after everything. The "
                "same row on the same day again adds to or changes its numbers",
        "takes": {"example": "own_example", "table": "class", "row": "text",
                  "values": "mapping"},
        "may": {"at": "moment"},
    },
    "unexpect": {
        "does": "take back what an example expects of one row on one day",
        "takes": {"example": "own_example", "table": "class", "row": "text"},
        "may": {"at": "moment"},
    },
    "agree_example": {
        "does": "agree that an example is what the business does and what its "
                "numbers must be. Only a person agrees: an example an agent "
                "wrote is a proposal until then, and cannot be sealed",
        "takes": {"example": "own_example"},
        "may": {},
    },
}

# A LinkML name: what a class or a slot may be called. Not a style rule — these
# names are written into SQL identifiers and into expressions read by `{name}`.
WORD = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
CURIE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*:[A-Za-z0-9_][A-Za-z0-9_.-]*$")
TRUE = ("true", "yes", "1", "on")
FALSE = ("false", "no", "0", "off", "")


class StudioError(Refusal):
    """The studio cannot perform this step. The draft is unchanged."""

    gate = "the studio"


# ---- the files ------------------------------------------------------------

def directory(store, name):
    return store.place(name)


def path(store, name):
    return directory(store, name) / DRAFT


def open_draft(store, name):
    """The draft document, or a refusal saying there is none."""
    where = path(store, name)
    if not where.is_file():
        raise StudioError(
            "no_draft",
            where=name,
            expected="a draft open on this module",
            got="none",
            repairs=[
                Repair("start a module of your own", options=["start"]),
                Repair("or open a draft from its latest sealed version",
                       options=["revise"]),
            ],
        )
    return yaml.safe_load(where.read_text(encoding="utf-8")) or {}


def drafts(store):
    """Every module with a draft open, and what it was built from."""
    out = []
    for name in store.names():
        where = path(store, name)
        if not where.is_file():
            continue
        held = [v["version"] for v in store.versions(name)]
        out.append({"name": name, "title": store.manifest(name).get("title"),
                    "purpose": store.manifest(name).get("purpose"),
                    "versions": held, "revises": held[-1] if held else None,
                    "steps": _steps_taken(store, name)})
    return out


def _steps_taken(store, name):
    where = directory(store, name) / TRANSCRIPT
    if not where.is_file():
        return 0
    return sum(1 for line in where.read_text(encoding="utf-8").splitlines()
               if line and not line.startswith((" ", "#")))


def transcript(store, name):
    where = directory(store, name) / TRANSCRIPT
    return where.read_text(encoding="utf-8") if where.is_file() else ""


def examples_of(store, name):
    """The draft's business examples, by name. None written is none."""
    return business.load(directory(store, name) / EXAMPLES)


def _save_examples(store, name, held, op, args, *, record=True):
    """Write the examples beside the draft; the step goes in the transcript,
    because an example is as much a part of the version as a rule is."""
    where = directory(store, name)
    if held:
        (where / EXAMPLES).write_text(business.dump(held), encoding="utf-8",
                                      newline="\n")
    else:
        (where / EXAMPLES).unlink(missing_ok=True)
    if record:
        _record(where / TRANSCRIPT, name, op, args)


def _ordered(document):
    known = {k: document[k] for k in ORDER if k in document}
    return {**known, **{k: v for k, v in document.items() if k not in known}}


def _save(store, name, document, op, args):
    where = directory(store, name)
    where.mkdir(parents=True, exist_ok=True)
    (where / DRAFT).write_text(
        yaml.safe_dump(_ordered(document), sort_keys=False,
                       default_flow_style=False, allow_unicode=True),
        encoding="utf-8", newline="\n")
    _record(where / TRANSCRIPT, name, op, args)
    return document


def _record(where, name, op, args):
    """One line per step, in order. This file becomes the seal's transcript."""
    if not where.is_file():
        where.write_text(
            f"# {name} — how this version was built\n"
            f"#\n"
            f"# One line per step the studio performed, in order. Nobody wrote\n"
            f"# this file and nobody edits it; `seal` copies it out beside the\n"
            f"# version it becomes.\n",
            encoding="utf-8", newline="\n")
    moment = datetime.now(timezone.utc).isoformat(timespec="seconds")
    short = {k: v for k, v in args.items()
             if isinstance(v, str) and len(v) <= 60 and "\n" not in v}
    long = {k: v for k, v in args.items() if k not in short}
    line = f"\n{moment}  {_ACTOR.get()}  {op}"
    if short:
        line += "  " + " ".join(f"{k}={v}" for k, v in short.items())
    for key, value in long.items():
        body = "\n".join(f"    {row}" for row in str(value).splitlines())
        line += f"\n  {key}:\n{body}"
    with where.open("a", encoding="utf-8", newline="\n") as out:
        out.write(line + "\n")


# ---- what the draft can see -----------------------------------------------

def seen(store, document):
    """Every class and slot this draft can see, its own overriding what it pins.

    Each carries the module version it came from, and `None` for the draft's
    own — which is the whole of the difference between what can be changed
    here and what has to be changed by sealing a new version of somebody
    else's module.
    """
    classes, slots = {}, {}
    for pin in store.imports(document):
        for dep in store.closure(*pin):
            held = store.document(*dep)
            origin = {"name": dep[0], "version": dep[1]}
            for class_name, c in (held.get("classes") or {}).items():
                classes[class_name] = {**(c or {}), "module": origin}
            for slot_name, s in (held.get("slots") or {}).items():
                slots[slot_name] = {**(s or {}), "module": origin}
    for class_name, c in (document.get("classes") or {}).items():
        classes[class_name] = {**(c or {}), "module": None}
    for slot_name, s in (document.get("slots") or {}).items():
        slots[slot_name] = {**(s or {}), "module": None}
    return classes, slots


def enums_seen(store, document):
    """Every enum this draft can see, its own overriding what it pins."""
    enums = {}
    for pin in store.imports(document):
        for dep in store.closure(*pin):
            origin = {"name": dep[0], "version": dep[1]}
            for enum_name, e in (store.document(*dep).get("enums") or {}).items():
                enums[enum_name] = {**(e or {}), "module": origin}
    for enum_name, e in (document.get("enums") or {}).items():
        enums[enum_name] = {**(e or {}), "module": None}
    return enums


def ranges(store, document):
    """Everything a slot may range over: the types, the classes, the enums in sight."""
    classes, _ = seen(store, document)
    return sorted(SQL_TYPE) + sorted(classes) + sorted(enums_seen(store, document))


def text_of(document):
    """The draft as the file says it — what a reader is handed to parse."""
    return yaml.safe_dump(_ordered(document), sort_keys=False,
                          default_flow_style=False, allow_unicode=True)


# ---- performing one step --------------------------------------------------

def apply(store, name, op, args=None, *, actor="person"):
    """Perform one operation on one draft, and return the document it wrote.

    `actor` is who performs it: a person, or an agent. The transcript records
    it, and an agent may not change an example a person agreed to.
    """
    if actor not in ACTORS:
        raise ValueError(f"actor must be one of {ACTORS}, not {actor!r}")
    held = _ACTOR.set(actor)
    try:
        return _perform(store, name, op, args)
    finally:
        _ACTOR.reset(held)


def _perform(store, name, op, args):
    args = dict(args or {})
    if op not in OPERATIONS:
        raise StudioError(
            "not_an_operation",
            where="the studio",
            expected="one of the steps the studio performs",
            got=f"{op!r}",
            repairs=[Repair("choose a step", options=sorted(OPERATIONS))],
        )
    args = _arguments(op, args)
    document = None if op in ("start", "revise") else open_draft(store, name)
    return _PERFORM[op](store, name, document, args)


def _arguments(op, args):
    """Exactly the arguments this operation takes, and nothing else."""
    spec = OPERATIONS[op]
    missing = [k for k in spec["takes"] if args.get(k) in (None, "")]
    unknown = sorted(set(args) - set(spec["takes"]) - set(spec["may"]))
    if missing or unknown:
        raise StudioError(
            "operation_arguments",
            where=op,
            expected=", ".join(spec["takes"]) or "nothing",
            got=(f"{', '.join(missing)} missing" if missing else "")
                + ("; " if missing and unknown else "")
                + (f"{', '.join(unknown)} not taken here" if unknown else ""),
            repairs=[Repair(spec["does"],
                            options=sorted(set(spec["takes"]) | set(spec["may"])))],
        )
    return {k: v for k, v in args.items() if v not in (None, "")}


def _word(value, what):
    if WORD.match(str(value)):
        return str(value)
    raise StudioError(
        "operation_arguments",
        where=what,
        expected="a name starting with a letter, then letters, digits or _",
        got=f"{value!r}",
        repairs=[Repair("names are written into SQL and into expressions, so "
                        "they are held to this shape")],
    )


def _free(store, document, kind, proposed, what):
    """A name nothing in sight already uses.

    A class and an enum are both things a slot ranges over, so they share one
    space of names; a slot has its own.
    """
    classes, slots = seen(store, document)
    taken = slots if kind == "slot" else {**enums_seen(store, document), **classes}
    if proposed in taken:
        held = taken[proposed]["module"]
        raise StudioError(
            "name_taken",
            where=what,
            expected=f"a {kind} name nothing in this draft uses",
            got=f"{proposed!r}, which "
                + (f"{held['name']}@{held['version']} declares" if held
                   else "this draft already declares"),
            repairs=[Repair(f"choose another name for the {kind}")],
        )
    return proposed


def _own(document, kind, wanted, what):
    """One of the draft's own classes, slots or enums: the ones it can change."""
    held = document.get({"class": "classes", "slot": "slots",
                         "enum": "enums"}[kind]) or {}
    if wanted in held:
        return wanted
    raise StudioError(
        "not_yours",
        where=what,
        expected=f"a {kind} this draft declares",
        got=f"{wanted!r}",
        repairs=[Repair(f"name a {kind} of your own", options=sorted(held)),
                 Repair("a class or slot of a module you pin is changed by "
                        "sealing a new version of that module, not here")],
    )


def _visible(store, document, kind, wanted, what):
    classes, slots = seen(store, document)
    held = classes if kind == "class" else slots
    if wanted in held:
        return wanted
    raise StudioError(
        "not_in_draft",
        where=what,
        expected=f"a {kind} this draft declares or pins",
        got=f"{wanted!r}",
        repairs=[Repair(f"name a {kind} in sight", options=sorted(held)),
                 Repair("or pin the module that declares it", options=["pin"])],
    )


def _field(op, fields, wanted):
    if wanted in fields:
        return wanted
    raise StudioError(
        "not_a_field",
        where=op,
        expected="a field this has",
        got=f"{wanted!r}",
        repairs=[Repair("set one of these", options=list(fields))],
    )


def _value(field, value):
    """A field's value, as the document holds it."""
    if field in BOOLEAN_FIELDS:
        return str(value).strip().lower() in TRUE
    return str(value)


def _classes(document):
    return document.setdefault("classes", {})


def _slots(document):
    return document.setdefault("slots", {})


def _tidy(document):
    """Drop a container when the last thing in it goes."""
    for key in ("classes", "slots", "enums"):
        if key in document and not document[key]:
            del document[key]
    return document


# ---- starting and ending --------------------------------------------------

def _start(store, name, _document, args):
    where = directory(store, name)
    if (where / DRAFT).is_file():
        raise StudioError(
            "draft_open",
            where=name,
            expected="a module with no draft open",
            got=f"a draft with {_steps_taken(store, name)} steps in it",
            repairs=[Repair("carry on with the draft that is open"),
                     Repair("or throw it away first", options=["discard"])],
        )
    if (where / MANIFEST).is_file() and store.versions(name):
        raise StudioError(
            "module_exists",
            where=name,
            expected="a module the store does not hold yet",
            got=f"{len(store.versions(name))} versions already sealed",
            repairs=[Repair("open a draft from its latest version instead",
                            options=["revise"])],
        )

    scope, local = name.split("/")
    prefix = args.get("prefix") or re.sub(r"[^a-z0-9_]", "_", local.lower())
    base = args.get("base") or f"{BASE}/{scope.lstrip('@')}/{local}"
    document = {
        "id": base,
        "name": re.sub(r"[^a-z0-9_]", "_", f"{scope.lstrip('@')}_{local}".lower()),
        "title": args["title"],
        "description": args["description"],
        "prefixes": {"linkml": "https://w3id.org/linkml/", prefix: base + "/"},
        "default_prefix": prefix,
        "default_range": "string",
        "imports": ["linkml:types"],
        # A draft says when its definitions took effect. Today, until somebody
        # says otherwise — a module written now and true from now is the
        # ordinary case, and `set valid_from` is one step away when it is not.
        "annotations": {
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "transcript": TRANSCRIPT,
        },
    }
    # Core is the one import that is not a choice about this module's subject:
    # it is where the roles live, and a module that pins nothing can fill none
    # of them. It is pinned at its latest, and said out loud in the steps.
    core = next((n for n in store.names() if n == "@uniti/core"), None)
    if core and store.versions(core):
        document["imports"].append(f"{core}@{store.versions(core)[-1]['version']}")

    where.mkdir(parents=True, exist_ok=True)
    manifest = {"name": name, "title": args["title"],
                "description": args["description"]}
    if args.get("purpose"):
        manifest["purpose"] = args["purpose"]
    (where / MANIFEST).write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8", newline="\n")
    return _save(store, name, document, "start",
                 {**args, "module": name, "imports": ", ".join(document["imports"])})


def _revise(store, name, _document, args):
    if (path(store, name)).is_file():
        raise StudioError(
            "draft_open",
            where=name,
            expected="a module with no draft open",
            got=f"a draft with {_steps_taken(store, name)} steps in it",
            repairs=[Repair("carry on with the draft that is open"),
                     Repair("or throw it away first", options=["discard"])],
        )
    held = store.versions(name)
    if not held:
        raise StudioError(
            "nothing_sealed",
            where=name,
            expected="a sealed version to revise",
            got="nothing sealed here yet",
            repairs=[Repair("start a module instead", options=["start"])],
        )
    latest = held[-1]["version"]
    document = dict(store.document(name, latest))
    # What `seal` stamps, it stamps again. A draft carrying the version it came
    # from would seal as a copy of it, and `supersedes` is the seal's to write.
    annotations = dict(document.get("annotations") or {})
    for key in ("sealed_at", "supersedes"):
        annotations.pop(key, None)
    annotations["transcript"] = TRANSCRIPT
    document.pop("version", None)
    document["annotations"] = annotations
    # The examples the latest version was held to hold this draft too, until
    # somebody says otherwise: a revision is judged by the same contract.
    examples = business.path_for(store.path(name, latest))
    if examples.is_file():
        shutil.copyfile(examples, directory(store, name) / EXAMPLES)
    return _save(store, name, document, "revise", {"module": name, "from": latest})


def _discard(store, name, _document, _args):
    """Throw the draft away. Nothing was sealed, so nothing is lost but this."""
    where = directory(store, name)
    for leaf in (DRAFT, TRANSCRIPT, EXAMPLES):
        (where / leaf).unlink(missing_ok=True)
    # A module that never sealed anything and has no draft any more is not a
    # module; leaving the shell behind would put a name in the store that
    # answers nothing.
    if not store.versions(name) and not any(
            p.name not in (MANIFEST,) for p in where.glob("*")):
        shutil.rmtree(where)
    return None


# ---- the module itself ----------------------------------------------------

def _set(store, name, document, args):
    field = _field("set", FIELDS, args["field"])
    if field == "valid_from":
        document.setdefault("annotations", {})["valid_from"] = str(args["value"])
    else:
        document[field] = str(args["value"])
    return _save(store, name, document, "set", args)


def _pin(store, name, document, args):
    pinned = str(args["module"])
    # The store is the judge of whether a pin resolves, and it refuses by name
    # with the versions it does hold.
    held = store.pinned(pinned)
    store.path(*held)
    # One version of a module, never two: pinning again moves the pin.
    kept = []
    for imp in (str(i) for i in document.get("imports") or []):
        other = None if imp.startswith("linkml:") else store.pinned(imp)
        if other and other[0] == held[0]:
            continue
        kept.append(imp)
    document["imports"] = kept + [pinned]
    return _save(store, name, document, "pin", args)


def _unpin(store, name, document, args):
    wanted = str(args["module"])
    imports = [str(i) for i in document.get("imports") or []]
    pins = [i for i in imports if not i.startswith("linkml:")]
    if wanted not in pins:
        raise StudioError(
            "not_a_pin",
            where=name,
            expected="an import this draft holds",
            got=f"{wanted!r}",
            repairs=[Repair("drop one it holds", options=pins)],
        )
    document["imports"] = [i for i in imports if i != wanted]
    return _save(store, name, document, "unpin", args)


# ---- classes --------------------------------------------------------------

def _add_class(store, name, document, args):
    class_name = _free(store, document, "class",
                       _word(args["class"], "add_class"), "add_class")
    body = {}
    if args.get("description"):
        body["description"] = str(args["description"])
    _classes(document)[class_name] = body
    return _save(store, name, document, "add_class", args)


def _remove_class(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "remove_class")
    del _classes(document)[class_name]
    return _save(store, name, _tidy(document), "remove_class", args)


def _rename_class(store, name, document, args):
    old = _own(document, "class", str(args["class"]), "rename_class")
    new = _free(store, document, "class",
                _word(args["to"], "rename_class"), "rename_class")
    classes = _classes(document)
    classes[new] = classes.pop(old)
    for body in classes.values():
        body = body or {}
        if str(body.get("is_a") or "") == old:
            body["is_a"] = new
        if body.get("mixins"):
            body["mixins"] = [new if str(m) == old else m for m in body["mixins"]]
    for body in (document.get("slots") or {}).values():
        body = body or {}
        if str(body.get("range") or "") == old:
            body["range"] = new
        spec = _rule_spec(body, "aggregate")
        if spec and str(spec.get("over") or "") == old:
            spec["over"] = new
    _examples_renamed(store, name, "class", old, new)
    return _save(store, name, document, "rename_class", args)


def _set_class(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "set_class")
    field = _field("set_class", CLASS_FIELDS, args["field"])
    if field == "is_a":
        _visible(store, document, "class", str(args["value"]), "set_class")
    _classes(document)[class_name] = {**(_classes(document)[class_name] or {}),
                                      field: _value(field, args["value"])}
    return _save(store, name, document, "set_class", args)


def _roles_in_sight(store, document):
    classes, _ = seen(store, document)
    return sorted(c for c, body in classes.items() if body.get("abstract"))


def _fill_role(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "fill_role")
    role = str(args["role"])
    if role not in _roles_in_sight(store, document):
        raise StudioError(
            "not_a_role",
            where=f"{class_name}.{role}",
            expected="a role — a class declared abstract, carrying bindings",
            got=f"{role!r}",
            repairs=[Repair("claim a role in sight",
                            options=_roles_in_sight(store, document)),
                     Repair("an ordinary class is not claimed but inherited",
                            options=["set_class"])],
        )
    body = _classes(document)[class_name] or {}
    mixins = [str(m) for m in (body.get("mixins") or [])]
    if role not in mixins:
        mixins.append(role)
    body["mixins"] = mixins
    _classes(document)[class_name] = body
    return _save(store, name, document, "fill_role", args)


def _unfill_role(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "unfill_role")
    role = str(args["role"])
    body = _classes(document)[class_name] or {}
    mixins = [str(m) for m in (body.get("mixins") or []) if str(m) != role]
    if mixins:
        body["mixins"] = mixins
    else:
        body.pop("mixins", None)
    _classes(document)[class_name] = body
    return _save(store, name, document, "unfill_role", args)


# ---- slots ----------------------------------------------------------------

def _add_slot(store, name, document, args):
    slot_name = _free(store, document, "slot",
                      _word(args["slot"], "add_slot"), "add_slot")
    # A predicate's identity is written down, never derived at read time: a
    # rename would otherwise orphan every fact recorded before it. The studio
    # offers one made from the module's own prefix; it lands in the file as a
    # literal, and `rename_slot` keeps it.
    uri = str(args.get("slot_uri")
              or f"{document.get('default_prefix') or 'x'}:{slot_name}")
    if not CURIE.match(uri):
        raise StudioError(
            "operation_arguments",
            where=f"add_slot {slot_name}",
            expected="a `slot_uri` of the form prefix:name",
            got=f"{uri!r}",
            repairs=[Repair("name it under a prefix this module declares",
                            options=sorted(document.get("prefixes") or {}))],
        )
    body = {"slot_uri": uri}
    for field in ("title", "description"):
        if args.get(field):
            body[field] = str(args[field])
    if args.get("range"):
        body["range"] = _range(store, document, str(args["range"]), "add_slot")
    _slots(document)[slot_name] = body
    return _save(store, name, document, "add_slot", {**args, "slot_uri": uri})


def _range(store, document, wanted, what):
    if wanted in SQL_TYPE:
        return wanted
    classes, _ = seen(store, document)
    enums = enums_seen(store, document)
    if wanted in classes or wanted in enums:
        return wanted
    raise StudioError(
        "not_in_draft",
        where=what,
        expected="a type, a class or an enum this draft can see",
        got=f"{wanted!r}",
        repairs=[Repair("a value is one of these", options=sorted(SQL_TYPE)),
                 Repair("or it names an entity of one of these",
                        options=sorted(classes)),
                 Repair("or it is one value of a closed list",
                        options=sorted(enums) + ["add_enum"])],
    )


def _remove_slot(store, name, document, args):
    slot_name = _own(document, "slot", str(args["slot"]), "remove_slot")
    del _slots(document)[slot_name]
    for body in (document.get("classes") or {}).values():
        body = body or {}
        if slot_name in (body.get("slots") or []):
            body["slots"] = [s for s in body["slots"] if s != slot_name]
            if not body["slots"]:
                body.pop("slots")
        if slot_name in (body.get("slot_usage") or {}):
            del body["slot_usage"][slot_name]
            if not body["slot_usage"]:
                body.pop("slot_usage")
    return _save(store, name, _tidy(document), "remove_slot", args)


def _rename_slot(store, name, document, args):
    old = _own(document, "slot", str(args["slot"]), "rename_slot")
    new = _free(store, document, "slot",
                _word(args["to"], "rename_slot"), "rename_slot")
    slots = _slots(document)
    slots[new] = slots.pop(old)
    for body in slots.values():
        body = body or {}
        if str(body.get("is_a") or "") == old:
            body["is_a"] = new
        aggregate = _rule_spec(body, "aggregate")
        if aggregate:
            if str(aggregate.get("sum") or "") == old:
                aggregate["sum"] = new
            if aggregate.get("by"):
                aggregate["by"] = {(new if k == old else k):
                                   (new if str(v) == old else v)
                                   for k, v in aggregate["by"].items()}
        parameter = _rule_spec(body, "parameter")
        if parameter:
            for key in ("of", "slot"):
                if str(parameter.get(key) or "") == old:
                    parameter[key] = new
        if body.get("equals_expression"):
            body["equals_expression"] = str(body["equals_expression"]).replace(
                "{" + old + "}", "{" + new + "}")
    for body in (document.get("classes") or {}).values():
        body = body or {}
        if old in (body.get("slots") or []):
            body["slots"] = [new if s == old else s for s in body["slots"]]
        if old in (body.get("slot_usage") or {}):
            body["slot_usage"] = {(new if k == old else k): v
                                  for k, v in body["slot_usage"].items()}
    _examples_renamed(store, name, "slot", old, new)
    return _save(store, name, document, "rename_slot", args)


def _set_slot(store, name, document, args):
    slot_name = _own(document, "slot", str(args["slot"]), "set_slot")
    field = _field("set_slot", SLOT_FIELDS, args["field"])
    value = _value(field, args["value"])
    if field == "range":
        value = _range(store, document, str(args["value"]), "set_slot")
    if field == "slot_uri" and not CURIE.match(str(value)):
        raise StudioError(
            "operation_arguments",
            where=f"set_slot {slot_name}",
            expected="a `slot_uri` of the form prefix:name",
            got=f"{value!r}",
            repairs=[Repair("name it under a prefix this module declares",
                            options=sorted(document.get("prefixes") or {}))],
        )
    body = {**(_slots(document)[slot_name] or {}), field: value}
    if field in BOOLEAN_FIELDS and not value:
        body.pop(field, None)
    _slots(document)[slot_name] = body
    return _save(store, name, document, "set_slot", args)


def _attach(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "attach")
    slot_name = _visible(store, document, "slot", str(args["slot"]), "attach")
    body = _classes(document)[class_name] or {}
    slots = list(body.get("slots") or [])
    if slot_name not in slots:
        slots.append(slot_name)
    body["slots"] = slots
    _classes(document)[class_name] = body
    return _save(store, name, document, "attach", args)


def _detach(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "detach")
    slot_name = str(args["slot"])
    body = _classes(document)[class_name] or {}
    if slot_name not in (body.get("slots") or []):
        raise StudioError(
            "not_attached",
            where=f"{class_name}.{slot_name}",
            expected="a slot this class carries",
            got=f"{slot_name!r}",
            repairs=[Repair("take one off that is on it",
                            options=list(body.get("slots") or []))],
        )
    body["slots"] = [s for s in body["slots"] if s != slot_name]
    if not body["slots"]:
        body.pop("slots")
    _classes(document)[class_name] = body
    return _save(store, name, document, "detach", args)


def _carried(store, document, class_name):
    """Every slot a class carries: its own, and what it inherits or mixes in."""
    classes, _ = seen(store, document)
    out = list((classes.get(class_name) or {}).get("slots") or [])
    for parent in _above(classes, class_name):
        out += [s for s in (classes[parent].get("slots") or []) if s not in out]
    return out


def _set_usage(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "set_usage")
    slot_name = str(args["slot"])
    field = _field("set_usage", USAGE_FIELDS, args["field"])
    carried = _carried(store, document, class_name)
    if slot_name not in carried:
        raise StudioError(
            "not_attached",
            where=f"{class_name}.{slot_name}",
            expected="a slot this class carries, its own or inherited",
            got=f"{slot_name!r}",
            repairs=[Repair("say how one of these is used here", options=carried),
                     Repair("or put the slot on the class first",
                            options=["attach"])],
        )
    body = _classes(document)[class_name] or {}
    usage = dict(body.get("slot_usage") or {})
    held = {**(usage.get(slot_name) or {}), field: _value(field, args["value"])}
    # Saying `false` is not a statement worth keeping: it is the default.
    held = {k: v for k, v in held.items() if v is not False}
    if held:
        usage[slot_name] = held
    else:
        usage.pop(slot_name, None)
    if usage:
        body["slot_usage"] = usage
    else:
        body.pop("slot_usage", None)
    _classes(document)[class_name] = body
    return _save(store, name, document, "set_usage", args)


# ---- enums ----------------------------------------------------------------

def _values(value, what):
    """A closed list written `a, b, c`: each value once, none of them empty."""
    out = []
    for held in str(value).split(","):
        held = held.strip()
        if held and held not in out:
            out.append(held)
    if out:
        return out
    raise StudioError(
        "operation_arguments",
        where=what,
        expected="at least one value, written `a, b, c`",
        got=f"{value!r}",
        repairs=[Repair("name every value the slot may hold, separated by commas")],
    )


def _add_enum(store, name, document, args):
    enum_name = _free(store, document, "enum",
                      _word(args["enum"], "add_enum"), "add_enum")
    body = {}
    if args.get("description"):
        body["description"] = str(args["description"])
    body["permissible_values"] = {v: {} for v in _values(args["values"], "add_enum")}
    document.setdefault("enums", {})[enum_name] = body
    return _save(store, name, document, "add_enum", args)


def _set_enum(store, name, document, args):
    enum_name = _own(document, "enum", str(args["enum"]), "set_enum")
    field = _field("set_enum", ENUM_FIELDS, args["field"])
    body = dict(document["enums"][enum_name] or {})
    if field == "values":
        # A value kept keeps whatever was said about it.
        before = body.get("permissible_values") or {}
        body["permissible_values"] = {v: before.get(v) or {}
                                      for v in _values(args["value"], "set_enum")}
    else:
        body[field] = str(args["value"])
    document["enums"][enum_name] = body
    return _save(store, name, document, "set_enum", args)


def _remove_enum(store, name, document, args):
    enum_name = _own(document, "enum", str(args["enum"]), "remove_enum")
    del document["enums"][enum_name]
    return _save(store, name, _tidy(document), "remove_enum", args)


def _bindings_in_sight(store, document):
    _, slots = seen(store, document)
    return sorted(s for s, body in slots.items() if body.get("abstract"))


def _bind(store, name, document, args):
    slot_name = _own(document, "slot", str(args["slot"]), "bind")
    binding = str(args["binding"])
    if binding not in _bindings_in_sight(store, document):
        raise StudioError(
            "not_a_binding",
            where=f"{slot_name} is_a {binding}",
            expected="a binding — an abstract slot a role carries",
            got=f"{binding!r}",
            repairs=[Repair("fill a binding in sight",
                            options=_bindings_in_sight(store, document)),
                     Repair("a role is claimed by the class, and its bindings "
                            "are filled by the class's slots",
                            options=["fill_role"])],
        )
    _slots(document)[slot_name] = {**(_slots(document)[slot_name] or {}),
                                   "is_a": binding}
    return _save(store, name, document, "bind", args)


def _unbind(store, name, document, args):
    slot_name = _own(document, "slot", str(args["slot"]), "unbind")
    body = dict(_slots(document)[slot_name] or {})
    body.pop("is_a", None)
    _slots(document)[slot_name] = body
    return _save(store, name, document, "unbind", args)


# ---- rules ----------------------------------------------------------------

def _rule_spec(body, kind):
    """The body of one rule annotation, unwrapped from LinkML's envelope."""
    annotation = ((body or {}).get("annotations") or {}).get(kind)
    if isinstance(annotation, dict) and set(annotation) == {"value"}:
        annotation = annotation["value"]
    return annotation if isinstance(annotation, dict) else None


def _column(store, document, class_name, wanted, what):
    """A slot of this class, and the draft's own, because a rule is written on it."""
    body = (document.get("classes") or {}).get(class_name) or {}
    if wanted not in (body.get("slots") or []):
        raise StudioError(
            "not_attached",
            where=f"{class_name}.{wanted}",
            expected="a slot this class carries, to carry the rule",
            got=f"{wanted!r}",
            repairs=[Repair("write the rule on a column of this class",
                            options=list(body.get("slots") or [])),
                     Repair("or declare the slot and put it on the class first",
                            options=["add_slot", "attach"])],
        )
    return _own(document, "slot", wanted, what)


def _rule(document, slot_name, kind, spec):
    """Put one rule on a slot, and take off whatever rule it had."""
    body = dict(document["slots"][slot_name] or {})
    annotations = {k: v for k, v in (body.get("annotations") or {}).items()
                   if k not in ("aggregate", "parameter")}
    body.pop("equals_expression", None)
    if kind == "expression":
        body["equals_expression"] = spec
    else:
        annotations[kind] = {"value": spec}
    if annotations:
        body["annotations"] = annotations
    else:
        body.pop("annotations", None)
    document["slots"][slot_name] = body
    return document


def _mapping(value, what):
    """Pairs written `key=value, ...`: `by` (column=slot), `where` (slot=Class)
    and `convert_on` (slot of the conversion=slot of the source)."""
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    out = {}
    for pair in str(value).split(","):
        if pair.strip() and "=" in pair:
            key, _, held = pair.partition("=")
            out[key.strip()] = held.strip()
    if out:
        return out
    raise StudioError(
        "operation_arguments",
        where=what,
        expected="pairs written key=value, separated by commas",
        got=f"{value!r}",
        repairs=[Repair("write at least one pair, the name on this side "
                        "first and what it matches on the other side after `=`")],
    )


def _aggregate(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "aggregate")
    column = _column(store, document, class_name, str(args["column"]), "aggregate")
    # `over`, `sum` and `by` are read by the compiler, which is the judge of
    # whether they resolve. Writing them here and letting the check answer is
    # what keeps one judge — and the check runs on the next read.
    spec = {"over": str(args["over"]), "sum": str(args["sum"]),
            "by": _mapping(args["by"], "aggregate")}
    if "where" in args:
        spec["where"] = {slot: {"is_a": held} for slot, held in
                         _mapping(args["where"], "aggregate: where").items()}
    # Whichever of the three were given, as given: half a conversion is the
    # compiler's to refuse, and it names the keys that are missing.
    convert = {}
    if "convert_using" in args:
        convert["using"] = str(args["convert_using"])
    if "convert_on" in args:
        convert["on"] = _mapping(args["convert_on"], "aggregate: convert_on")
    if "convert_factor" in args:
        convert["factor"] = str(args["convert_factor"])
    if convert:
        spec["convert"] = convert
    said = {**args, "by": _pairs(spec["by"])}
    for key in ("where", "convert_on"):
        if key in args:
            said[key] = _pairs(_mapping(args[key], "aggregate"))
    return _save(store, name, _rule(document, column, "aggregate", spec),
                 "aggregate", said)


def _pairs(mapping):
    return ", ".join(f"{k}={v}" for k, v in mapping.items())


def _parameter(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "parameter")
    column = _column(store, document, class_name, str(args["column"]), "parameter")
    spec = {"of": str(args["of"]), "slot": str(args["slot"])}
    return _save(store, name, _rule(document, column, "parameter", spec),
                 "parameter", args)


def _expression(store, name, document, args):
    class_name = _own(document, "class", str(args["class"]), "expression")
    column = _column(store, document, class_name, str(args["column"]), "expression")
    return _save(store, name,
                 _rule(document, column, "expression", str(args["expression"])),
                 "expression", args)


def _unrule(store, name, document, args):
    slot_name = _own(document, "slot", str(args["slot"]), "unrule")
    body = dict(_slots(document)[slot_name] or {})
    body.pop("equals_expression", None)
    annotations = {k: v for k, v in (body.get("annotations") or {}).items()
                   if k not in ("aggregate", "parameter")}
    if annotations:
        body["annotations"] = annotations
    else:
        body.pop("annotations", None)
    _slots(document)[slot_name] = body
    return _save(store, name, document, "unrule", args)


# ---- business examples ----------------------------------------------------
#
# The file beside the draft, never the draft itself: an example is about the
# map and is not part of it, and LinkML has no place for one. Every step here
# refuses only what it cannot perform — an example that is not there, a record
# it does not hold. Whether an example holds is answered by running it, which
# the next read does.

def _example(held, wanted, what):
    if wanted in held:
        return wanted
    raise StudioError(
        "no_such_example",
        where=what,
        expected="an example this draft holds",
        got=f"{wanted!r}",
        repairs=[Repair("name one of its examples", options=list(held)),
                 Repair("or write one first", options=["add_example"])],
    )


def _changeable(held, wanted, what):
    """An example this actor may change: any, for a person; for an agent, only
    one that is still its own proposal.

    An agreed example is the business's word on what the numbers must be. An
    agent that could rewrite it could make any failing map pass by changing
    the answer instead of the rule — so it cannot, and it says so to the
    person instead. Not a matter of the agent's judgement: of who it is.
    """
    example = _example(held, wanted, what)
    if _ACTOR.get() == "agent" and business.agreed(held[example]):
        raise StudioError(
            "example_agreed",
            where=f"{what}: {example}",
            expected="an example still proposed, or a person making the change",
            got=f"{example!r}, which a person agreed to",
            repairs=[Repair("tell the person what should change and why; they "
                            "change it, or agree to a new example you propose "
                            "in its place",
                            options=["add_example"])],
        )
    return example


def _add_example(store, name, document, args):
    held = examples_of(store, name)
    example = _word(args["example"], "add_example")
    if example in held:
        raise StudioError(
            "name_taken",
            where="add_example",
            expected="an example name this draft does not use",
            got=f"{example!r}, which is already one",
            repairs=[Repair("choose another name, or add to that example",
                            options=["record", "expect"])],
        )
    held[example] = {"says": str(args["says"])}
    if _ACTOR.get() == "agent":
        # Written by an agent, it is a proposal: the business has not said so.
        held[example]["agreed"] = False
    held[example].update({"records": [], "expect": []})
    _save_examples(store, name, held, "add_example", args)
    return document


def _set_example(store, name, document, args):
    held = examples_of(store, name)
    example = _changeable(held, str(args["example"]), "set_example")
    field = _field("set_example", EXAMPLE_FIELDS, args["field"])
    held[example][field] = str(args["value"])
    _save_examples(store, name, held, "set_example", args)
    return document


def _remove_example(store, name, document, args):
    held = examples_of(store, name)
    del held[_changeable(held, str(args["example"]), "remove_example")]
    _save_examples(store, name, held, "remove_example", args)
    return document


def _agree_example(store, name, document, args):
    held = examples_of(store, name)
    example = _example(held, str(args["example"]), "agree_example")
    if _ACTOR.get() != "person":
        raise StudioError(
            "person_only",
            where=f"agree_example: {example}",
            expected="a person, agreeing that this is what the business does",
            got="an agent",
            repairs=[Repair("show the person what the example says, what it "
                            "records and the numbers it expects, and ask them "
                            "to agree to it")],
        )
    held[example].pop("agreed", None)
    _save_examples(store, name, held, "agree_example", args)
    return document


def _record_step(store, name, document, args):
    held = examples_of(store, name)
    example = _changeable(held, str(args["example"]), "record")
    record = {"record": _word(args["record"], "record")}
    if "class" in args:
        record["class"] = _visible(store, document, "class", str(args["class"]),
                                   "record")
    if "when" in args:
        business.instant(args["when"], "record: when")
        record["when"] = str(args["when"])
    if "facts" in args:
        record["facts"] = _mapping(args["facts"], "record: facts")
    if "class" not in record and "facts" not in record:
        raise StudioError(
            "nothing_entered",
            where="record",
            expected="what the record is, or at least one fact about it",
            got="neither",
            repairs=[Repair("give it a class, facts, or both",
                            options=["class", "facts"])],
        )
    held[example].setdefault("records", []).append(record)
    said = dict(args)
    if "facts" in args:
        said["facts"] = _pairs(record["facts"])
    _save_examples(store, name, held, "record", said)
    return document


def _unrecord(store, name, document, args):
    held = examples_of(store, name)
    example = _changeable(held, str(args["example"]), "unrecord")
    records = held[example].get("records") or []
    kept = [r for r in records if str(r.get("record")) != str(args["record"])]
    if len(kept) == len(records):
        raise StudioError(
            "not_in_example",
            where=f"unrecord: {example}",
            expected="a record this example holds",
            got=f"{args['record']!r}",
            repairs=[Repair("name one of its records",
                            options=sorted({str(r.get("record")) for r in records}))],
        )
    held[example]["records"] = kept
    _save_examples(store, name, held, "unrecord", args)
    return document


def _row_of(value):
    """A row as written: one value of its first column, or column=value pairs."""
    if isinstance(value, dict) or "=" in str(value):
        return _mapping(value, "expect: row")
    return str(value)


def _same_row(expectation, table, row, at):
    return (str(expectation.get("table")) == table
            and expectation.get("row") == row
            and (None if expectation.get("at") is None
                 else str(expectation["at"])) == at)


def _expect(store, name, document, args):
    held = examples_of(store, name)
    example = _changeable(held, str(args["example"]), "expect")
    table = str(args["table"])
    row = _row_of(args["row"])
    at = None
    if "at" in args:
        business.instant(args["at"], "expect: at", end_of_day=True)
        at = str(args["at"])
    values = _mapping(args["values"], "expect: values")
    values = {column: (None if value == "" else value)
              for column, value in values.items()}
    expected = held[example].setdefault("expect", [])
    for expectation in expected:
        if _same_row(expectation, table, row, at):
            expectation["values"] = {**(expectation.get("values") or {}), **values}
            break
    else:
        expectation = {"table": table, "row": row}
        if at is not None:
            expectation["at"] = at
        expectation["values"] = values
        expected.append(expectation)
    said = {**args, "values": _pairs({k: "" if v is None else v
                                      for k, v in values.items()})}
    if isinstance(row, dict):
        said["row"] = _pairs(row)
    _save_examples(store, name, held, "expect", said)
    return document


def _unexpect(store, name, document, args):
    held = examples_of(store, name)
    example = _changeable(held, str(args["example"]), "unexpect")
    table, row = str(args["table"]), _row_of(args["row"])
    at = str(args["at"]) if "at" in args else None
    expected = held[example].get("expect") or []
    kept = [e for e in expected if not _same_row(e, table, row, at)]
    if len(kept) == len(expected):
        raise StudioError(
            "not_in_example",
            where=f"unexpect: {example}",
            expected="a row this example expects numbers of",
            got=f"{table} {row if not isinstance(row, dict) else _pairs(row)}"
                + (f" at {at}" if at else ""),
            repairs=[Repair("name one it expects", options=[
                f"{e.get('table')} {_pairs(e['row']) if isinstance(e.get('row'), dict) else e.get('row')}"
                + (f" at {e['at']}" if e.get("at") is not None else "")
                for e in expected])],
        )
    held[example]["expect"] = kept
    said = dict(args)
    if isinstance(row, dict):
        said["row"] = _pairs(row)
    _save_examples(store, name, held, "unexpect", said)
    return document


def _examples_renamed(store, name, kind, old, new):
    """A rename reaches the examples too, as it reaches every rule that names
    the thing: an example is written in the draft's own words, and a rename
    that left it behind would make it fail for no reason about the business."""
    held = examples_of(store, name)
    if not held:
        return

    def keys(mapping):
        return {(new if str(k) == old else k): v for k, v in mapping.items()}

    for body in held.values():
        for record in body.get("records") or []:
            if kind == "class" and str(record.get("class") or "") == old:
                record["class"] = new
            if kind == "slot" and record.get("facts"):
                record["facts"] = keys(record["facts"])
        for expectation in body.get("expect") or []:
            if kind == "class" and str(expectation.get("table")) == old:
                expectation["table"] = new
            if kind == "slot":
                if isinstance(expectation.get("row"), dict):
                    expectation["row"] = keys(expectation["row"])
                expectation["values"] = keys(expectation.get("values") or {})
    _save_examples(store, name, held, None, None, record=False)


_PERFORM = {
    "start": _start, "revise": _revise, "discard": _discard,
    "set": _set, "pin": _pin, "unpin": _unpin,
    "add_class": _add_class, "remove_class": _remove_class,
    "rename_class": _rename_class, "set_class": _set_class,
    "fill_role": _fill_role, "unfill_role": _unfill_role,
    "add_slot": _add_slot, "remove_slot": _remove_slot,
    "rename_slot": _rename_slot, "set_slot": _set_slot,
    "add_enum": _add_enum, "set_enum": _set_enum, "remove_enum": _remove_enum,
    "set_usage": _set_usage,
    "attach": _attach, "detach": _detach,
    "bind": _bind, "unbind": _unbind,
    "aggregate": _aggregate, "parameter": _parameter,
    "expression": _expression, "unrule": _unrule,
    "add_example": _add_example, "set_example": _set_example,
    "remove_example": _remove_example,
    "record": _record_step, "unrecord": _unrecord,
    "expect": _expect, "unexpect": _unexpect,
    "agree_example": _agree_example,
}

__all__ = ["ACTORS", "EXAMPLES", "OPERATIONS", "StudioError", "apply", "drafts",
           "enums_seen", "examples_of", "open_draft", "path", "ranges", "seen",
           "text_of", "transcript"]

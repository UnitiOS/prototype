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
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from components.refusal import Refusal, Repair  # noqa: E402
from compile import SQL_TYPE  # noqa: E402

DRAFT = "draft.yaml"
TRANSCRIPT = "draft.txt"
MANIFEST = "package.yaml"

# The keys a module document holds, in the order they are written. A file
# whose keys move about on every save is a file whose diff is unreadable.
ORDER = ("id", "name", "title", "description", "prefixes", "default_prefix",
         "default_range", "imports", "classes", "slots", "annotations")

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
               "identifier", "required", "designates_type")
BOOLEAN_FIELDS = ("identifier", "required", "designates_type")

# The operations, what each one does, and what it takes. The kinds are what
# `steps()` turns into option lists, so they are the vocabulary a form renders
# and an agent chooses from:
#
#   text  word  uri  moment        typed in
#   pin   held_pin                 a sealed version, from the store
#   own_class  own_slot            something this draft declares
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
        "does": "derive a column by arithmetic on other columns of the same table",
        "takes": {"class": "own_class", "column": "column", "expression": "text"},
        "may": {},
    },
    "unrule": {
        "does": "take the rule off a column, leaving the slot stated",
        "takes": {"slot": "own_slot"},
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
    line = f"\n{moment}  {op}"
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


def ranges(store, document):
    """Everything a slot may range over: the types, then the classes in sight."""
    classes, _ = seen(store, document)
    return sorted(SQL_TYPE) + sorted(classes)


def text_of(document):
    """The draft as the file says it — what a reader is handed to parse."""
    return yaml.safe_dump(_ordered(document), sort_keys=False,
                          default_flow_style=False, allow_unicode=True)


# ---- performing one step --------------------------------------------------

def apply(store, name, op, args=None):
    """Perform one operation on one draft, and return the document it wrote."""
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
    """A name nothing in sight already uses."""
    classes, slots = seen(store, document)
    taken = classes if kind == "class" else slots
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
    """One of the draft's own classes or slots, which are the ones it can change."""
    held = document.get("classes" if kind == "class" else "slots") or {}
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
    """Drop the two containers when the last thing in them goes."""
    for key in ("classes", "slots"):
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
    return _save(store, name, document, "revise", {"module": name, "from": latest})


def _discard(store, name, _document, _args):
    """Throw the draft away. Nothing was sealed, so nothing is lost but this."""
    where = directory(store, name)
    for leaf in (DRAFT, TRANSCRIPT):
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
    if wanted in classes:
        return wanted
    raise StudioError(
        "not_in_draft",
        where=what,
        expected="a type, or a class this draft can see",
        got=f"{wanted!r}",
        repairs=[Repair("a value is one of these", options=sorted(SQL_TYPE)),
                 Repair("or it names an entity of one of these",
                        options=sorted(classes))],
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


_PERFORM = {
    "start": _start, "revise": _revise, "discard": _discard,
    "set": _set, "pin": _pin, "unpin": _unpin,
    "add_class": _add_class, "remove_class": _remove_class,
    "rename_class": _rename_class, "set_class": _set_class,
    "fill_role": _fill_role, "unfill_role": _unfill_role,
    "add_slot": _add_slot, "remove_slot": _remove_slot,
    "rename_slot": _rename_slot, "set_slot": _set_slot,
    "attach": _attach, "detach": _detach,
    "bind": _bind, "unbind": _unbind,
    "aggregate": _aggregate, "parameter": _parameter,
    "expression": _expression, "unrule": _unrule,
}

__all__ = ["OPERATIONS", "StudioError", "apply", "drafts", "open_draft",
           "path", "ranges", "seen", "text_of", "transcript"]

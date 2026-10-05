"""changes — what became different in a draft, said as a person reads a map.

A draft is looked at twice and the two looks compared: before and after one
request to the agent, before and after one call of that request, or the
version a draft revises against the draft itself. What comes back is a list,
one line per thing that is new, different or gone:

    {"what": "kind",    "name": "Level",                 "how": "added"}
    {"what": "field",   "name": "Level.level_on_hand",   "how": "changed"}
    {"what": "example", "name": "flour",                 "how": "added"}
    {"what": "pin",     "name": "@demo/catalog@v3",      "how": "removed"}
    {"what": "module",  "name": "@scope/name",           "how": "changed"}

A field is a slot on a kind, because that is what a map draws: a slot two
kinds carry is two fields, and a rule on it changing changes both. A kind is
"changed" when anything said about it is — its words, its shapes, or any of
its fields — so a map can light the box as well as the line inside it.

A look reads the files and nothing else: no compiler, no log. It is cheap
enough to take after every call the agent makes.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.examples import examples as business  # noqa: E402
from components.studio import draft as studio  # noqa: E402

# What is said about a module as a whole. A seal writes annotations of its
# own (when, what it supersedes); only the one an author writes is compared.
MODULE_FIELDS = ("title", "description")
# What is said about a kind itself, apart from its fields.
KIND_FIELDS = ("description", "is_a", "mixins", "abstract")

# A kind's fields follow it, in the order the kind lists them.
ORDER = {"module": 0, "pin": 1, "kind": 2, "field": 2, "example": 3}


def look(store, name):
    """The draft as it stands: its document and its examples. A module with
    no draft open looks empty."""
    where = studio.path(store, name)
    if not where.is_file():
        return {"document": {}, "examples": {}}
    return {"document": studio.open_draft(store, name),
            "examples": studio.examples_of(store, name)}


def look_at_version(store, name, version):
    """A sealed version, looked at the same way. None is a module that has
    no version yet: everything in its draft is new."""
    if version is None:
        return {"document": {}, "examples": {}}
    return {"document": store.document(name, version),
            "examples": business.load(business.path_for(store.path(name, version)))}


def between(before, after, name=None):
    """Everything different from `before` to `after`, in a steady order."""
    old, new = before.get("document") or {}, after.get("document") or {}
    out = []

    if name and old and new and _said(old) != _said(new):
        out.append(_line("module", name, "changed"))

    old_pins = _pins(old)
    new_pins = _pins(new)
    out += [_line("pin", p, "added") for p in new_pins if p not in old_pins]
    out += [_line("pin", p, "removed") for p in old_pins if p not in new_pins]

    old_classes, new_classes = _own(old, "classes"), _own(new, "classes")
    old_slots, new_slots = _own(old, "slots"), _own(new, "slots")
    for kind in sorted(set(old_classes) | set(new_classes)):
        if kind not in new_classes:
            out.append(_line("kind", kind, "removed"))
            continue
        fields = _fields(kind, old_classes.get(kind), new_classes[kind],
                         old_slots, new_slots)
        if kind not in old_classes:
            how = "added"
        elif fields or any(old_classes[kind].get(f) != new_classes[kind].get(f)
                           for f in KIND_FIELDS):
            how = "changed"
        else:
            continue
        out.append(_line("kind", kind, how))
        out += fields

    old_examples = before.get("examples") or {}
    new_examples = after.get("examples") or {}
    for example in sorted(set(old_examples) | set(new_examples)):
        if example not in new_examples:
            out.append(_line("example", example, "removed"))
        elif example not in old_examples:
            out.append(_line("example", example, "added"))
        elif old_examples[example] != new_examples[example]:
            out.append(_line("example", example, "changed"))

    return sorted(out, key=lambda line: ORDER[line["what"]])


def _fields(kind, old_kind, new_kind, old_slots, new_slots):
    """The fields of one kind that are new, different or gone."""
    old_kind = old_kind or {}
    had = list(old_kind.get("slots") or [])
    has = list(new_kind.get("slots") or [])
    old_usage = old_kind.get("slot_usage") or {}
    new_usage = new_kind.get("slot_usage") or {}
    out = []
    for slot in has:
        if slot not in had:
            out.append(_line("field", f"{kind}.{slot}", "added"))
        elif (old_slots.get(slot) != new_slots.get(slot)
              or old_usage.get(slot) != new_usage.get(slot)):
            out.append(_line("field", f"{kind}.{slot}", "changed"))
    out += [_line("field", f"{kind}.{slot}", "removed") for slot in had if slot not in has]
    return out


def _pins(document):
    """The modules a document pins; `linkml:types` and the like are not one."""
    return [str(i) for i in document.get("imports") or [] if str(i).startswith("@")]


def _said(document):
    return ([document.get(f) for f in MODULE_FIELDS],
            (document.get("annotations") or {}).get("valid_from"))


def _own(document, part):
    return {k: (v or {}) for k, v in (document.get(part) or {}).items()}


def _line(what, name, how):
    return {"what": what, "name": name, "how": how}


__all__ = ["between", "look", "look_at_version"]

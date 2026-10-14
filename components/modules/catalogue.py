"""catalogue — what the store holds, computed from what was sealed, and searchable.

Nobody writes this. Every entry is read off a sealed version, so it cannot
fall behind the store it describes: seal a new version and the catalogue has
already changed.

Four kinds of entry, one list:

    module   a module at its latest sealed version: what it is, what it pins
    role     an abstract class: the bindings it obliges, and who has filled it
    class    a class a module declares: which roles it fills, whether the log
             can say an entity is one, and which rules anywhere read it
    slot     a slot a module declares: its predicate, which binding it fills,
             and which rules anywhere read that predicate

"What the store holds" is the latest sealed version of every module — what
somebody installing from the store today would get. "Which rules read it" is
wider on purpose: every sealed version of every module, because an application
still pinned to an old version is still an application, and a predicate it
reads is not unread just because a newer version stopped reading it.

An application is one business's own (DESIGN_NOTES.md §15.2). It is in the
catalogue only for that business: `business` names whose catalogue this is,
and every other business's application is left out, its rules included — a
rule says what a business counts, which is its own affair.

It is a list to be asked, not a document to be loaded. `find()` narrows it by
text, by kind, by the role an entry fills, by the module that declares it, and
by the module an entry pins — which is what somebody (or an agent) needs when
the store holds more than fits on a page or in a prompt.

Nothing here writes, and nothing here touches the log.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from compile import plan_for, tables, type_slot  # noqa: E402
from components.modules.roles import _above, _bindings, _closure_documents  # noqa: E402
from components.modules.store import APPLICATION  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.standard import (  # noqa: E402
    DIRECTION, TIME_MEANING, annotation, labels, unit_of,
)
from generate import _identifier, columns, read_map  # noqa: E402
from seal import predicate, written_uri  # noqa: E402

KINDS = ("module", "role", "class", "slot")


def _pin(name, version):
    return {"name": name, "version": version}


def _uris(values):
    return [str(v) for v in values or [] if v]


def readers(map_):
    """Every rule in one map, and every predicate each of them reads.

    Two sorts of reader. The compiler's rules — an `aggregate` or a `parameter`
    on some column — are what a module author wrote. The mechanisms' own reads
    are what nobody wrote and everything relies on: the generator names a
    subject by its identifier slot, and both the generator and the compiler
    find the rows of a table through the slot that says which class an entity
    is. A predicate read only by a mechanism is still read.

    An expression is not here: it reads other columns, never a predicate.

    Returns (readers, refusals). A table whose plan is refused has no readers
    to report; the refusal says why, and it is the same one `check` collects.
    """
    view = map_["view"]
    out, refused = [], []
    for class_name in tables(map_):
        try:
            plan_ = plan_for(map_, class_name)
        except Refusal as exc:
            refused.append({**exc.as_dict(), "class": class_name})
            continue

        for column, whole in plan_["aggregates"].items():
            reads, covers = [], []
            # A column totalling several sources reads what each of them reads.
            for spec in whole["sources"]:
                reads += spec["measure_uris"]
                for uris in [*spec["by"].values(), *(spec.get("through") or {}).values()]:
                    reads += uris
                for narrowing in spec.get("where") or []:
                    reads += _uris(narrowing["slot_uris"]) + _uris([narrowing["type_slot_uri"]])
                convert = spec.get("convert")
                if convert:
                    reads += _uris([convert["type_slot_uri"], convert["factor_slot_uri"]])
                    for pair in convert.get("on") or []:
                        reads += _uris([pair.get("conv_slot_uri")]) + _uris(pair.get("source_slot_uris"))
                source = type_slot(map_, spec["over"])
                if source is not None and source.slot_uri:
                    reads.append(predicate(view, source))
                covers += spec["covers"]
            out.append({"rule": f"{class_name}.{column}", "kind": "aggregate",
                        "reader": "the compiler",
                        "over": " + ".join(s["over"] for s in whole["sources"]),
                        "overs": [s["over"] for s in whole["sources"]],
                        "covers": covers, "reads": sorted(set(reads))})

        for column, spec in plan_["parameters"].items():
            key = next((c for c in plan_["columns"] if c["name"] == spec["of"]), None)
            out.append({"rule": f"{class_name}.{column}", "kind": "parameter",
                        "reader": "the compiler",
                        "over": str(key["range"]) if key else None,
                        "covers": [], "reads": sorted(set(spec["slot_uris"]))})

        if plan_["shape"] == "entities":
            carrier = type_slot(map_, class_name)
            if carrier is not None and carrier.slot_uri:
                out.append({"rule": f"{class_name}", "kind": "type",
                            "reader": "the compiler", "over": class_name,
                            "covers": [class_name], "reads": [predicate(view, carrier)]})
            identifier = _identifier(map_, class_name)
            if identifier is not None and identifier.slot_uri:
                out.append({"rule": f"{class_name}", "kind": "identifier",
                            "reader": "the generator", "over": class_name,
                            "covers": [class_name], "reads": [predicate(view, identifier)]})
    return out, refused


def _binding_of(slots, slot):
    """The abstract slot this one fills, found by walking `is_a` upward."""
    parent, hops = (slot or {}).get("is_a"), 0
    while parent and hops < 8:
        above = slots.get(str(parent)) or {}
        if above.get("abstract"):
            return str(parent)
        parent, hops = above.get("is_a"), hops + 1
    return None


def visible(store, business=None):
    """The modules this business may see: everything shared, and its own
    applications."""
    return [name for name in store.names()
            if store.kind(name) != APPLICATION or store.business(name) == business]


def _rules_everywhere(store, business=None):
    """Every rule in every sealed version, and which module owns each class it
    covers; and each version read as a map, keyed by (name, version)."""
    rules, maps = [], {}
    for name in visible(store, business):
        for held in store.versions(name):
            version = held["version"]
            try:
                map_ = read_map(store.path(name, version), store)
            except Refusal:
                continue
            maps[(name, version)] = map_
            origin = {}
            for dep, document in store.version_composition(name, version):
                for class_name in (document.get("classes") or {}):
                    origin[class_name] = dep[0]
            found, _ = readers(map_)
            for rule in found:
                if rule["kind"] not in ("aggregate", "parameter"):
                    continue
                rules.append({**rule, "module": _pin(name, version),
                              "covers": [(c, origin.get(c)) for c in rule["covers"]]})
    return rules, maps


def _required(map_, class_name):
    """What a new entity of this class must be given, as the form asks it."""
    if map_ is None:
        return []
    try:
        fields = columns(map_, class_name)
    except Refusal:
        return []
    return [f["name"] for f in fields if f["required"] and not f["designates_type"]]


def catalogue(store, business=None):
    """Every module, role, class and slot the store offers now, as one list."""
    rules, maps = _rules_everywhere(store, business)
    entries = []

    for name in visible(store, business):
        held = store.versions(name)
        if not held:
            continue
        version = held[-1]["version"]
        manifest = store.manifest(name)
        document = store.document(name, version)
        classes, slots = _closure_documents(store, name, version)
        pins = [_pin(*p) for p in store.imports(document)]
        own_classes = document.get("classes") or {}
        own_slots = document.get("slots") or {}

        entries.append({
            "kind": "module", "name": name, "module": _pin(name, version),
            "title": manifest.get("title") or document.get("title"),
            "description": manifest.get("description") or document.get("description") or "",
            "purpose": manifest.get("purpose"),
            "of_kind": store.kind(name),
            "labels": labels(document),
            "versions": [v["version"] for v in held],
            "pins": pins,
            "declares": {"classes": sorted(own_classes), "slots": sorted(own_slots)},
            "fills": [], "reads": [],
        })

        for class_name in sorted(own_classes):
            c = own_classes[class_name] or {}
            above = _above(classes, class_name)
            fills = sorted(r for r in above if classes[r].get("abstract"))
            if c.get("abstract"):
                bindings = _bindings(classes, slots, class_name)
                entries.append({
                    "kind": "role", "name": class_name, "module": _pin(name, version),
                    "title": class_name,
                    "description": c.get("description") or "",
                    "labels": labels(c),
                    "bindings": bindings,
                    "fills": fills,
                    "filled_by": [],  # completed below, once every class is known
                    "read_by": _read_by_class(rules, class_name, name),
                })
                continue
            induced = [s for s in (c.get("slots") or [])]
            for parent in above:
                induced += [s for s in (classes[parent].get("slots") or [])
                            if s not in induced]
            entries.append({
                "kind": "class", "name": class_name, "module": _pin(name, version),
                "title": class_name,
                "description": c.get("description") or "",
                "labels": labels(c),
                "fills": fills,
                "statable": any((slots.get(s) or {}).get("designates_type") for s in induced),
                "slots": list(c.get("slots") or []),
                "required": _required(maps.get((name, version)), class_name),
                "read_by": _read_by_class(rules, class_name, name),
            })

        for slot_name in sorted(own_slots):
            s = own_slots[slot_name] or {}
            uri = written_uri(document, s["slot_uri"]) if s.get("slot_uri") else None
            binding = _binding_of(slots, s)
            entries.append({
                "kind": "slot", "name": slot_name, "module": _pin(name, version),
                "title": str(s.get("title") or slot_name),
                "description": s.get("description") or "",
                "labels": labels(s),
                "uri": uri,
                "range": s.get("range"),
                "unit": unit_of(s),
                "direction": annotation(s, DIRECTION),
                "time_meaning": annotation(s, TIME_MEANING),
                "abstract": bool(s.get("abstract")),
                "fills": [binding] if binding else [],
                "on": sorted(k for k, c in own_classes.items()
                             if slot_name in ((c or {}).get("slots") or [])),
                "read_by": [_rule_ref(r) for r in rules if uri and uri in r["reads"]],
            })

    # Who fills each role, across the whole store: a class names the roles it
    # reaches, and a role lists every class that named it.
    for role in (e for e in entries if e["kind"] == "role"):
        role["filled_by"] = [
            {"class": e["name"], "module": e["module"]}
            for e in entries if e["kind"] == "class" and role["name"] in e["fills"]
        ]
    return entries


def _rule_ref(rule):
    return {"module": rule["module"], "rule": rule["rule"], "kind": rule["kind"]}


def _read_by_class(rules, class_name, module_name):
    """The rules whose rows come from this class, in any version of anything.

    A rule written against a role names the role in `over` and covers the
    classes filling it, so it is listed under both: under the role because
    that is what it was written against, and under each class because that is
    where its rows actually come from.
    """
    return [_rule_ref(r) for r in rules
            if (class_name, module_name) in r["covers"]
            or class_name in r.get("overs", [r["over"]])]


def find(entries, *, text=None, kind=None, fills=None, module=None, pins=None):
    """The entries matching every filter given; an absent filter matches all.

    text     a case-insensitive fragment of the name, title, description,
             predicate, module, or a label in any language: somebody looks a
             thing up in their own words
    kind     module, role, class or slot
    fills    a role or a binding: the classes that fill that role and the
             slots that fill that binding
    module   the module that declares the entry
    pins     a module name: the modules whose latest version pins it — that
             is, who would be affected by it changing
    """
    needle = (text or "").strip().lower()

    def matches(entry):
        if kind and entry["kind"] != kind:
            return False
        if fills and fills not in entry.get("fills", []):
            return False
        if module and entry["module"]["name"] != module:
            return False
        if pins and not any(p["name"] == pins for p in entry.get("pins", [])):
            return False
        if needle:
            hay = " ".join(str(entry.get(k) or "") for k in
                           ("name", "title", "description", "uri"))
            hay += " " + entry["module"]["name"]
            hay += " " + " ".join((entry.get("labels") or {}).values())
            if needle not in hay.lower():
                return False
        return True

    found = [e for e in entries if matches(e)]
    return {
        "entries": found,
        "counts": {k: sum(1 for e in found if e["kind"] == k) for k in KINDS},
        "held": {k: sum(1 for e in entries if e["kind"] == k) for k in KINDS},
        "roles": sorted({e["name"] for e in entries if e["kind"] == "role"}),
        "bindings": sorted({b["name"] for e in entries if e["kind"] == "role"
                            for b in e["bindings"]}),
        "modules": sorted({e["module"]["name"] for e in entries}),
    }


__all__ = ["catalogue", "find", "readers", "KINDS"]

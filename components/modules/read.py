"""read — the module store, read for a person looking at it.

Nothing here writes. Each version is read as it was sealed: its own classes and
slots, the versions it pins, and — through those pins — everything it can see,
each item marked with the module version it came from.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "provenance"))

from components.modules import diff as _diff  # noqa: E402
from components.modules.store import ModuleError  # noqa: E402

RULES = ("aggregate", "parameter")


def _pin(name, version):
    return {"name": name, "version": version}


def modules(store):
    """Every module, with its versions in order and what each one pins."""
    out = []
    for name in store.names():
        manifest = store.manifest(name)
        versions = []
        for held in store.versions(name):
            document = store.document(name, held["version"])
            versions.append({
                "version": held["version"],
                "valid_from": held["valid_from"],
                "sealed_at": held["sealed_at"],
                "supersedes": held["supersedes"],
                "imports": [_pin(*p) for p in store.imports(document)],
                "classes": len(document.get("classes") or {}),
                "slots": len(document.get("slots") or {}),
            })
        out.append({
            "name": name,
            "title": manifest.get("title"),
            "purpose": manifest.get("purpose"),
            "description": manifest.get("description"),
            "versions": versions,
            "latest": versions[-1]["version"] if versions else None,
            "draft": (store.directory(name) / "draft.yaml").is_file(),
        })
    return out


def graph(store):
    """Every sealed version as a node; an edge for each pin and each supersession."""
    nodes, edges = [], []
    for module in modules(store):
        for v in module["versions"]:
            nodes.append({**_pin(module["name"], v["version"]),
                          "latest": v["version"] == module["latest"],
                          "purpose": module["purpose"],
                          "sealed_at": v["sealed_at"]})
            for pin in v["imports"]:
                edges.append({"from": _pin(module["name"], v["version"]), "to": pin, "kind": "imports"})
            if v["supersedes"]:
                edges.append({"from": _pin(module["name"], v["version"]),
                              "to": _pin(module["name"], v["supersedes"]), "kind": "supersedes"})
    return {"nodes": nodes, "edges": edges}


def _rule(slot):
    """What kind of rule a slot declares, or None where it is simply stated."""
    spec = rule_of(slot)
    return spec["kind"] if spec else None


def rule_of(slot):
    """The rule a slot declares, unwrapped from LinkML's annotation envelope.

    An annotation body arrives as `{"value": {...}}` because that is how the
    metamodel carries a structured annotation. A reader wants what is inside,
    and so does anything explaining a column to a person.
    """
    if slot.get("equals_expression"):
        return {"kind": "expression", "expression": str(slot["equals_expression"])}
    annotations = slot.get("annotations") or {}
    for kind in RULES:
        if kind in annotations:
            body = annotations[kind]
            if isinstance(body, dict) and set(body) == {"value"}:
                body = body["value"]
            return {"kind": kind, "spec": body if isinstance(body, dict) else {}}
    return None


def version(store, name, version, registered=None):
    """One sealed version: what it declares, what it pins, and what it can see.

    `registered` is the set of URIs the kernel holds, when a kernel is at hand;
    each slot then says whether its `slot_uri` is known to the log.
    """
    document = store.document(name, version)
    latest = {n: store.versions(n)[-1]["version"] for n in store.names() if store.versions(n)}

    classes, slots = {}, {}
    for dep_name, dep_version in store.closure(name, version):
        dep = store.document(dep_name, dep_version)
        origin = _pin(dep_name, dep_version)
        for class_name, c in (dep.get("classes") or {}).items():
            c = c or {}
            classes[class_name] = {
                "name": class_name, "is_a": c.get("is_a"), "description": c.get("description"),
                "slots": list(c.get("slots") or []), "from": origin,
            }
        for slot_name, s in (dep.get("slots") or {}).items():
            s = s or {}
            slots[slot_name] = {
                "name": slot_name, "slot_uri": s.get("slot_uri"), "range": s.get("range"),
                "identifier": bool(s.get("identifier")), "required": bool(s.get("required")),
                "designates_type": bool(s.get("designates_type")),
                "rule": _rule(s), "rule_spec": rule_of(s),
                "title": str(s["title"]) if s.get("title") else slot_name,
                "description": s.get("description"), "from": origin,
                "registered": (s.get("slot_uri") in registered) if registered is not None else None,
            }

    imported_by = []
    for other in store.names():
        for held in store.versions(other):
            pins = store.imports(store.document(other, held["version"]))
            if (name, version) in pins:
                imported_by.append(_pin(other, held["version"]))

    held = next(v for v in store.versions(name) if v["version"] == version)
    transcript = held["path"].with_name(f"{version}.txt")
    own = lambda item: item["from"] == _pin(name, version)

    return {
        "name": name,
        "version": version,
        "title": document.get("title"),
        "purpose": store.manifest(name).get("purpose"),
        "description": document.get("description"),
        "valid_from": held["valid_from"],
        "sealed_at": held["sealed_at"],
        "supersedes": held["supersedes"],
        "latest": latest.get(name),
        "imports": [{**_pin(*p), "latest": latest.get(p[0])} for p in store.imports(document)],
        "imported_by": imported_by,
        "closure": [_pin(*p) for p in store.closure(name, version)],
        "classes": sorted(classes.values(), key=lambda c: (not own(c), c["name"])),
        "slots": sorted(slots.values(), key=lambda s: (not own(s), s["name"])),
        "transcript": transcript.read_text(encoding="utf-8") if transcript.is_file() else None,
    }


def class_graph(store, name, version):
    """Every class one version can see, and what joins them, across its modules.

    The timeline answers *when* — which version was sealed before which, and
    what each one pins. This answers *what is connected to what*, which is the
    question a pin is actually about: a module pins another one so that its own
    classes can point at that one's classes.

    Five kinds of join, and they are not the same kind of thing:

        is_a        a class is a kind of another class.
        fills       a class promises a role: it mixes one in and names a slot
                    of its own for each binding the role carries. This is the
                    only edge a module can be swapped at, because it is the
                    only one whose target belongs to nobody.
        reference   a slot's value names an entity of another class. This is
                    the ordinary edge, and it crosses a module boundary
                    wherever a pinned module's class is the range.
        aggregate   a derived column reads every entity of another class and
                    totals one of its slots. The arrow runs to where the rows
                    come from — which, for a rule written against a role, is
                    the role, and reaching a real class is one more hop along
                    a `fills` edge. The picture shows that hop rather than
                    collapsing it: the hop is the seam.
        parameter   a derived column reads one fact off the entity a key names.

    Nothing here is computed from the log. It is what the sealed versions say,
    read in the same closure order the compiler reads them in.
    """
    store.path(name, version)
    closure = store.closure(name, version)

    classes, slots = {}, {}
    for dep in closure:
        document = store.document(*dep)
        origin = _pin(*dep)
        for class_name, c in (document.get("classes") or {}).items():
            classes[class_name] = {**(c or {}), "module": origin}
        for slot_name, s in (document.get("slots") or {}).items():
            slots[slot_name] = {**(s or {}), "module": origin}

    def parents(class_name):
        """Everything above this class: its `is_a` chain and its mixins' too.

        Both relations, because a role reaches a class through `mixins` and a
        module's own hierarchy through `is_a`, and a slot inherited either way
        is a slot the class has.
        """
        seen, stack = [], [class_name]
        while stack:
            current = stack.pop()
            for above in ([classes[current].get("is_a")]
                          + list(classes[current].get("mixins") or [])):
                above = str(above) if above else None
                if above in classes and above not in seen:
                    seen.append(above)
                    stack.append(above)
        return seen

    def inherited(class_name):
        """Its own slots and every slot it gets from above, in that order."""
        out = list(classes[class_name].get("slots") or [])
        for above in parents(class_name):
            out += [s for s in (classes[above].get("slots") or []) if s not in out]
        return out

    def shape(class_name):
        """What kind of table this class would be, by the compiler's own rule."""
        if classes[class_name].get("abstract"):
            return "role"
        own = inherited(class_name)
        if any((slots.get(s) or {}) and _rule(slots[s]) == "aggregate" for s in own):
            return "derived"
        if any(bool((slots.get(s) or {}).get("designates_type")) for s in own):
            return "stated"
        return "unstatable"

    nodes = [{
        "name": class_name,
        "module": classes[class_name]["module"],
        "is_a": classes[class_name].get("is_a"),
        "fills": [str(m) for m in (classes[class_name].get("mixins") or [])
                  if str(m) in classes],
        "abstract": bool(classes[class_name].get("abstract")),
        "description": classes[class_name].get("description"),
        "shape": shape(class_name),
        "slots": inherited(class_name),
    } for class_name in sorted(classes)]

    edges = []

    def edge(source, target, kind, label):
        if target in classes:
            edges.append({"from": source, "to": target, "kind": kind, "label": label})

    for class_name in sorted(classes):
        parent = classes[class_name].get("is_a")
        if parent:
            edge(class_name, str(parent), "is_a", "is a")
        for mixed in classes[class_name].get("mixins") or []:
            # No label: the box the arrow lands in is the role's own name, and
            # writing "fills" four times over would only crowd the picture.
            edge(class_name, str(mixed), "fills", "")
        for slot_name in inherited(class_name):
            slot = slots.get(slot_name)
            if slot is None:
                continue
            rule = rule_of(slot)
            kind = rule["kind"] if rule else None
            if kind == "aggregate":
                edge(class_name, str(rule["spec"].get("over") or ""), "aggregate", slot_name)
            elif kind == "parameter":
                key = slots.get(str(rule["spec"].get("of") or ""))
                edge(class_name, str((key or {}).get("range") or ""), "parameter", slot_name)
            elif slot.get("range"):
                edge(class_name, str(slot["range"]), "reference", slot_name)

    return {
        "name": name,
        "version": version,
        "modules": [{**_pin(*pin), "purpose": store.manifest(pin[0]).get("purpose"),
                     "title": store.manifest(pin[0]).get("title")} for pin in closure],
        "nodes": nodes,
        "edges": edges,
    }


def compare(store, name, older, newer):
    for v in (older, newer):
        store.path(name, v)
    return {"name": name, "from": older, "to": newer,
            "diff": _diff.compare(store.document(name, older), store.document(name, newer))}


__all__ = ["modules", "graph", "version", "class_graph", "compare", "ModuleError"]

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
                          "sealed_at": v["sealed_at"]})
            for pin in v["imports"]:
                edges.append({"from": _pin(module["name"], v["version"]), "to": pin, "kind": "imports"})
            if v["supersedes"]:
                edges.append({"from": _pin(module["name"], v["version"]),
                              "to": _pin(module["name"], v["supersedes"]), "kind": "supersedes"})
    return {"nodes": nodes, "edges": edges}


def _rule(slot):
    if slot.get("equals_expression"):
        return "expression"
    annotations = slot.get("annotations") or {}
    return next((r for r in RULES if r in annotations), None)


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
                "rule": _rule(s), "description": s.get("description"), "from": origin,
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


def compare(store, name, older, newer):
    for v in (older, newer):
        store.path(name, v)
    return {"name": name, "from": older, "to": newer,
            "diff": _diff.compare(store.document(name, older), store.document(name, newer))}


__all__ = ["modules", "graph", "version", "compare", "ModuleError"]

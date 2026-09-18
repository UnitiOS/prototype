"""application — a set of pinned modules, read as one map.

An application is not a new kind of thing in the store. It is one sealed
version that pins others and declares the tables somebody wants; the compiler
reads its closure as a single map, and the modules under it never know they
were composed. So everything here is a read of what is already sealed, plus
one run of the compiler's own SQL against the log.

Nothing here writes. The compiler's operational store is filled by the
compiler; a person looking at a number should not cause a table somewhere to
be dropped and rebuilt, so this takes the emitted SELECT, runs it on the
kernel, and stops there.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from compile import MapError, plan_for, preview, sql_text, tables  # noqa: E402
from components.modules import read as modules_read  # noqa: E402
from generate import read_map, table_name  # noqa: E402


def _map(store, name, version):
    """The application's own version, read with its pins resolved through the store."""
    return read_map(store.path(name, version), store)


def _origins(store, name, version):
    """Which module version declares each class and each slot, across the closure."""
    classes, slots = {}, {}
    for pin in store.closure(name, version):
        document = store.document(*pin)
        origin = {"name": pin[0], "version": pin[1]}
        for class_name in (document.get("classes") or {}):
            classes[class_name] = origin
        for slot_name in (document.get("slots") or {}):
            slots[slot_name] = origin
    return classes, slots


def application(store, name, version):
    """What this application is: the versions it pins and the tables it can fill."""
    map_ = _map(store, name, version)
    classes, _ = _origins(store, name, version)
    detail = modules_read.version(store, name, version)

    out = []
    for class_name in tables(map_):
        plan_ = plan_for(map_, class_name)
        out.append({
            "class": class_name,
            "table": table_name(class_name),
            "shape": plan_["shape"],
            "module": classes.get(class_name),
            "columns": len(plan_["columns"]),
        })
    return {
        "name": name,
        "version": version,
        "title": detail["title"],
        "purpose": detail["purpose"],
        "description": detail["description"],
        "modules": [{**pin, "purpose": store.manifest(pin["name"]).get("purpose")}
                    for pin in detail["closure"]],
        "tables": out,
    }


def projection(conn, store, name, version, class_name, *, valid_at, as_of):
    """One table of the application, derived from the log at the two clocks.

    Every column says which rule produced it and which module the slot belongs
    to, so a number on the screen can be read back to the module that defined
    what it means. The emitted SQL comes with it: it is the evidence, and none
    of it was written by hand.
    """
    map_ = _map(store, name, version)
    _, slot_origin = _origins(store, name, version)
    built = preview(conn, map_, class_name, valid_at=valid_at, as_of=as_of)
    plan_ = built["plan"]

    columns = []
    for col in plan_["columns"]:
        rule = None
        if col["kind"] == "aggregate":
            spec = plan_["aggregates"][col["name"]]
            rule = {"kind": "aggregate", "operator": spec["operator"],
                    "over": spec["over"], "measure": spec["measure_uri"],
                    "by": spec["by"]}
        elif col["kind"] == "parameter":
            rule = {"kind": "parameter", **plan_["parameters"][col["name"]]}
        elif col["kind"] == "expression":
            rule = {"kind": "expression",
                    "expression": plan_["expressions"][col["name"]]}
        columns.append({
            "name": col["name"],
            "title": col.get("title") or col["name"],
            "type": col["type"],
            "kind": col["kind"],
            "description": col.get("description") or "",
            "module": slot_origin.get(col["name"]),
            "rule": rule,
        })

    return {
        "name": name,
        "version": version,
        "class": class_name,
        "table": plan_["table"],
        "shape": plan_["shape"],
        "keys": plan_["keys"],
        "columns": columns,
        "rows": [list(row) for row in built["rows"]],
        "sql": sql_text(built),
        "valid_at": valid_at,
        "as_of": as_of,
    }


__all__ = ["application", "projection", "MapError"]

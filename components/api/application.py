"""application — a set of pinned modules, read as one map.

An application is one business's composition (DESIGN_NOTES.md §15.2): a
sealed version that pins modules and declares the tables somebody wants, whose
manifest says `kind: application` and which business it belongs to. The
compiler reads its closure as a single map, and the modules under it never
know they were composed.

Reading works through any version, so a version not yet installed can be
looked at against real records. The one write here, a form submission, goes
only through the version the business has installed for that day.

The compiler's operational store is filled by the compiler; a person looking
at a number should not cause a table somewhere to be dropped and rebuilt, so
this takes the emitted SELECT, runs it on the kernel, and stops there.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

sys.path.insert(0, str(ROOT / "components" / "kernel"))

from components import business  # noqa: E402
from compile import MapError, plan_for, preview, sql_text, tables  # noqa: E402
from compile import _REF as EXPRESSION_REFS  # noqa: E402
from components.modules import read as modules_read  # noqa: E402
from components.modules.compose import facets, matches  # noqa: E402
from components.refusal import Repair  # noqa: E402
from generate import IDENTITY_COLUMN, form, named, read_map, submit, table_name  # noqa: E402
from generate import _registry, _row_subjects, _type_slot  # noqa: E402
from resolve import resolve_single  # noqa: E402

# A cell of a grouping can stand on a great many statements. A page showing
# them is a page somebody reads, so the list is cut off and says that it was.
MOST = 200


def _map(store, name, version):
    """The application's own version, read with its pins resolved through the store."""
    return read_map(store.path(name, version), store)


def _origins(store, name, version):
    """Which module version declares each class and each slot, across the
    closure, under the names the application reads them by."""
    classes, slots = {}, {}
    for pin, document in store.version_composition(name, version):
        origin = {"name": pin[0], "version": pin[1]}
        for class_name in (document.get("classes") or {}):
            classes[class_name] = origin
        for slot_name in (document.get("slots") or {}):
            slots[slot_name] = origin
    return classes, slots


def _title(store, module):
    """What a module is called for a reader: its manifest's title."""
    return store.manifest(module).get("title") or module


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
        "kind": store.kind(name),
        "business": store.business(name),
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
    class_name = named(map_, class_name)
    _, slot_origin = _origins(store, name, version)
    built = preview(conn, map_, class_name, valid_at=valid_at, as_of=as_of)
    plan_ = built["plan"]

    columns = []
    for col in plan_["columns"]:
        rule = None
        if col["kind"] == "aggregate":
            spec = plan_["aggregates"][col["name"]]
            sources = [{"over": s["over"], "covers": s["covers"],
                        "measure": s["measure"], "measure_uris": s["measure_uris"],
                        "by": s["by_names"], "by_uris": s["by"]}
                       for s in spec["sources"]]
            rule = {"kind": "aggregate", "operator": spec["operator"],
                    **sources[0], "sources": sources}
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
            # Sound and sealed, and not computed yet: the column is empty, and
            # this says why, so the screen labels it rather than showing blanks.
            "awaiting": col.get("awaiting"),
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


def _key_value(conn, subject_id, spec, key_column, by_uri, by_id, *, valid_at, as_of):
    """The value one row groups under for one key, read as the compiler reads
    it: off the row itself, or one record further — the record the row names
    under `through`, and the key's slot of that record."""
    subject = subject_id
    through = (spec.get("through") or {}).get(key_column)
    if through:
        named = _standing(conn, subject_id, through, by_uri, by_id,
                          valid_at=valid_at, as_of=as_of)
        subject = by_uri.get((named or {}).get("value"))
        if subject is None:
            return None
    return (_standing(conn, subject, spec["by"][key_column], by_uri, by_id,
                      valid_at=valid_at, as_of=as_of) or {}).get("value")


def _standing(conn, subject_id, predicate_uris, by_uri, by_id, *, valid_at, as_of):
    """One statement, resolved by the same rule everything else is resolved by.

    `predicate_uris` is a list because a rule written against a role stands for
    one predicate per class filling it. A subject is of one class and states
    only its own, so at most one of them answers; the first that does is it.
    """
    if isinstance(predicate_uris, str):
        predicate_uris = [predicate_uris]
    for predicate_uri in predicate_uris:
        predicate_id = by_uri.get(predicate_uri)
        if predicate_id is None:
            continue
        row = resolve_single(conn, subject_id=subject_id, predicate_id=predicate_id,
                             valid_at=valid_at, as_of=as_of)
        if row is not None:
            break
    else:
        return None
    if row is None:
        return None
    return {
        "assertion_id": row["id"],
        "intent_id": row["intent_id"],
        "subject_id": subject_id,
        "subject_uri": by_id.get(subject_id),
        "predicate": predicate_uri,
        "value": (by_id.get(row["value_ref"]) if row["value_ref"] is not None
                  else row["value_literal"]),
        "names_entity": row["value_ref"] is not None,
        "valid_from": row["valid_from"],
        "recorded_at": row["recorded_at"],
        "source": row["source"],
        "ontology_version": row["ontology_version"],
    }


def _column_named(column, names):
    found = matches(column, names)
    return found[0] if len(found) == 1 else str(column)


def cell(conn, store, name, version, class_name, column, keys, *, valid_at, as_of):
    """What one cell of a table stands on: the statements underneath it.

    A projection is a claim, and a claim nobody can take apart is a claim
    nobody should act on. This takes the same map and the same two clocks the
    table was derived at and answers the only question worth asking about a
    number on a screen: which statements, by whom, made it this.

    Nothing is recomputed differently here. The contributing rows are found by
    the same downward walk of `designates_type` the compiler's source CTE
    makes, and each value is one `resolve_single()`. So if this disagrees with
    the table, one of the two is wrong and the disagreement is on the screen
    rather than hidden.
    """
    map_ = _map(store, name, version)
    class_name = named(map_, class_name)
    plan_ = plan_for(map_, class_name)
    # A column and a key, too, by the plain name a person reads them by.
    names = [c["name"] for c in plan_["columns"]]
    column = _column_named(column, names)
    keys = {_column_named(k, names): v for k, v in (keys or {}).items()}
    col = next((c for c in plan_["columns"] if c["name"] == column), None)
    if col is None:
        raise MapError(
            "no_such_column",
            where=class_name,
            expected="a column of this table",
            got=f"{column!r}",
            repairs=[Repair("open a column the table has",
                            options=[c["name"] for c in plan_["columns"]])],
        )
    by_uri, by_id = _registry(conn)
    out = {"name": name, "version": version, "class": class_name,
           "column": column, "kind": col["kind"], "keys": keys,
           "statements": [], "reads": [], "cut_off": False,
           "entity": None, "valid_at": valid_at, "as_of": as_of,
           "awaiting": col.get("awaiting")}
    if col.get("awaiting"):
        # Not computed yet, so it stands on nothing: listing the rows its rule
        # would read would show statements for a number nobody computed.
        return out

    if col["kind"] == "aggregate":
        spec = plan_["aggregates"][column]
        out["over"] = spec["over"]
        out["covers"] = spec["covers"]
        out["operator"] = spec["operator"]
        # A column totalling several sources stands on the rows of each.
        out["sources"] = [source["over"] for source in spec["sources"]]
        for source in spec["sources"]:
            for subject_id in _row_subjects(conn, map_, source["over"], by_uri,
                                            valid_at=valid_at, as_of=as_of):
                grouped = all(
                    _key_value(conn, subject_id, source, key_column, by_uri, by_id,
                               valid_at=valid_at, as_of=as_of)
                    == keys.get(key_column)
                    for key_column in source["by"]
                )
                if not grouped:
                    continue
                measure = _standing(conn, subject_id, source["measure_uris"], by_uri,
                                    by_id, valid_at=valid_at, as_of=as_of)
                if measure is not None:
                    out["statements"].append(measure)
                if len(out["statements"]) >= MOST:
                    out["cut_off"] = True
                    return out
        return out

    if col["kind"] == "parameter":
        spec = plan_["parameters"][column]
        out["of"] = spec["of"]
        subject_uri = keys.get(spec["of"])
        subject_id = by_uri.get(subject_uri)
        out["entity"] = ({"uri": subject_uri, "id": subject_id}
                         if subject_id is not None else None)
        if subject_id is not None:
            held = _standing(conn, subject_id, spec["slot_uris"], by_uri, by_id,
                             valid_at=valid_at, as_of=as_of)
            if held is not None:
                out["statements"].append(held)
        return out

    if col["kind"] == "expression":
        out["expression"] = plan_["expressions"][column]
        known = {c["name"] for c in plan_["columns"]}
        out["reads"] = [found.strip()
                        for found in EXPRESSION_REFS.findall(out["expression"])
                        if found.strip() in known]
        return out

    # A key, an identity column, or a slot the log simply states. All three are
    # about one entity: whichever this row is, or whichever the key names.
    subject_uri = keys.get(IDENTITY_COLUMN) or keys.get(column)
    subject_id = by_uri.get(subject_uri)
    out["entity"] = ({"uri": subject_uri, "id": subject_id}
                     if subject_id is not None else None)
    if subject_id is not None and col.get("uri"):
        held = _standing(conn, subject_id, col["uri"], by_uri, by_id,
                         valid_at=valid_at, as_of=as_of)
        if held is not None:
            out["statements"].append(held)
    return out


def form_of(conn, store, name, version, class_name, *, valid_at, as_of):
    """The fields a person fills in to state something, read out of the map.

    Nothing here is written per class. The map says which slots the class has
    and what each one ranges over; a field over a class range offers the
    entities of that class, so choosing one writes an edge rather than a
    string. `options_from` says where those choices were read — the log, at
    this form's clocks — so the page can say it rather than leave it implied.
    """
    map_ = _map(store, name, version)
    class_name = named(map_, class_name)
    built = form(conn, map_, class_name, valid_at=valid_at, as_of=as_of)
    slot_origin = _origins(store, name, version)[1]
    type_slot = _type_slot(map_, class_name)
    # A field another module adds to this class is grouped under that
    # module's title: the item form in Sari's application has a section
    # for Rudi's rates, apart from what the item itself is.
    added = {slot: dep for owner, slot, dep in
             facets(store.version_composition(name, version))
             if owner == class_name}
    stated_by_the_form = str(type_slot.name) if type_slot else None
    return {
        "name": name,
        "version": version,
        "class": class_name,
        "label": map_["label"],
        # The class fact is not a field: the map says which slot carries it and
        # submitting the form states it, so nobody has to type the class in.
        "type_slot": stated_by_the_form,
        "fields": [{
            "name": f["name"], "title": f["title"], "range": f["range"],
            "required": f["required"], "ref": f["ref"],
            "description": f["description"],
            "module": slot_origin.get(f["name"]),
            "section": (_title(store, added[f["name"]][0])
                        if f["name"] in added else None),
            "options": [{"uri": uri, "label": label} for uri, label in f["options"]],
            "options_from": f["options_from"],
        } for f in built["fields"] if f["name"] != stated_by_the_form],
    }


def state(conn, store, name, version, class_name, *, subject, values, actor_id,
          valid_from=None, note=None, revokes=None):
    """One form submission: one intent, N assertions, through the same gate.

    The purpose the application's manifest declares rides along on the intent,
    so a fact typed into a demonstration is marked as one exactly like a fact
    that was sealed or loaded into it.

    `revokes` is field name -> the id of an earlier assertion this submission
    withdraws, exactly as `submit` takes it: with a value beside it, a
    correction; alone, a withdrawal. `stated` in the answer is where those ids
    come from.

    It writes only through the version the business has installed for the day
    the record is about (components/business). Any version can be read; what
    staff record goes through the one the owner chose.
    """
    business.require_installed(conn, name, version,
                               valid_at=valid_from or datetime.now(timezone.utc))
    map_ = _map(store, name, version)
    purpose = store.manifest(name).get("purpose")
    given = values
    class_name, values = named(map_, class_name, values)
    # The answer speaks the caller's names back: `stated` is keyed by what
    # was sent, whether that was `movement_quantity` or its full name.
    sent = dict(zip(values, given))
    if revokes:
        revokes = named(map_, class_name, revokes)[1]
    type_slot = _type_slot(map_, class_name)
    entered = {name: value for name, value in values.items()
               if value not in (None, "")}
    # Nothing in the log is a member of a class until something says so, and a
    # form that left it out would write an entity no table has a row for. The
    # map names the slot that carries it; this does not.
    # A withdrawal alone states nothing, the class included: it says "we were
    # wrong" and only that.
    if type_slot is not None and entered:
        entered[str(type_slot.name)] = class_name
    written = submit(conn, map_, class_name, subject=subject, values=entered,
                     actor_id=actor_id, valid_from=valid_from,
                     reason_code=purpose, note=note, revokes=revokes)
    return {"intent_id": written["intent_id"], "subject_id": written["subject_id"],
            "assertions": len(written["assertions"]),
            "minted": len(written["minted"]),
            "stated": {sent.get(k, k): str(v) for k, v in written["stated"].items()},
            "class": class_name, "subject": subject,
            "ontology_version": map_["label"]}


__all__ = ["application", "projection", "cell", "form_of", "state", "MapError"]

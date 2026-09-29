"""health — six things worth knowing about an application's graph, none of them refusals.

A refusal says this cannot go on. These say it can, and that something in it
is doing nothing: a predicate stated and never read, a column no rule reaches,
a class nothing has ever been, a role nobody fills, a pin the store has moved
past, statements the application cannot see. Each one is a fact computed from
the sealed closure and, where it needs one, a count against the log. None is a
guess and none is a warning about what might happen.

    dead_term      stated in the log, and read by no rule and no mechanism
    empty_column   a column no rule reaches, so it is always empty
    empty_class    a class the log could say an entity is, and never has
    unfilled_role  a role nothing in this application fills
    lagging_pin    a pinned version the store has sealed a newer one of
    orphaned_fact  statements under a predicate no module here declares

They are read against one application — one sealed version and its closure —
because "read by nothing" only means something against a particular set of
rules. A predicate this application never reads may be exactly what another
one totals; the catalogue says who, across the whole store.

The log is counted whole: every statement ever recorded, withdrawn or not,
because a statement withdrawn is still a statement somebody made under that
predicate. No clock is applied. A reader who wants "as of" wants a projection,
not a health report.

Nothing here writes.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from compile import _covered, type_slot  # noqa: E402
from components.modules.catalogue import _binding_of, readers  # noqa: E402
from components.modules.check import check  # noqa: E402
from components.modules.roles import _closure_documents, roles  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from generate import read_map  # noqa: E402
from seal import URI_PREDICATE, class_uri, predicate, written_uri  # noqa: E402

DIAGNOSES = {
    "dead_term": "stated in the log, and read by no rule and no mechanism",
    "empty_column": "a column no rule reaches, so it is always empty",
    "empty_class": "a class the log could say an entity is, and never has",
    "unfilled_role": "a role nothing in this application fills, so a rule "
                     "written against it has no rows",
    "lagging_pin": "a pinned version the store has sealed a newer one of",
    "orphaned_fact": "statements under a predicate no module in this "
                     "application declares",
}

# Every predicate the log holds a statement under, and how many. A predicate
# is an entity like any other and is named through the registry, which is why
# this joins the log to itself. The registry's own predicate is left out by
# the caller: it names things, it is not a fact about any of them.
_PREDICATES_SQL = """
SELECT u.value_literal AS uri, count(DISTINCT a.id) AS held
FROM assertion a
JOIN assertion u ON u.subject_id = a.predicate_id
WHERE u.predicate_id = (
        SELECT subject_id FROM assertion
        WHERE subject_id = predicate_id AND value_literal = %(uri)s
        ORDER BY seq LIMIT 1)
GROUP BY 1
"""

# How many subjects have ever been stated to be each class, under whichever
# predicates carry a class. Distinct subjects, because one entity restated is
# still one entity.
_MEMBERS_SQL = """
SELECT a.value_literal AS class, count(DISTINCT a.subject_id) AS members
FROM assertion a
JOIN assertion u ON u.subject_id = a.predicate_id
WHERE u.predicate_id = (
        SELECT subject_id FROM assertion
        WHERE subject_id = predicate_id AND value_literal = %(uri)s
        ORDER BY seq LIMIT 1)
  AND u.value_literal = ANY(%(carriers)s)
  AND a.value_literal IS NOT NULL
GROUP BY 1
"""


def _pin(name, version):
    return {"name": name, "version": version}


def _counts(conn):
    with conn.cursor() as cur:
        cur.execute(_PREDICATES_SQL, {"uri": URI_PREDICATE})
        return {uri: held for uri, held in cur.fetchall() if uri != URI_PREDICATE}


def _members(conn, carriers):
    if not carriers:
        return {}
    with conn.cursor() as cur:
        cur.execute(_MEMBERS_SQL, {"uri": URI_PREDICATE, "carriers": sorted(carriers)})
        return dict(cur.fetchall())


def _declared_anywhere(store):
    """Every predicate any sealed version declares, and which modules declare it."""
    out = {}
    for name in store.names():
        for held in store.versions(name):
            document = store.document(name, held["version"])
            for slot in (document.get("slots") or {}).values():
                uri = (slot or {}).get("slot_uri")
                if not uri:
                    continue
                uri = written_uri(document, uri)
                versions = out.setdefault(uri, {}).setdefault(name, [])
                versions.append(held["version"])
    return {uri: [{"name": n, "versions": v} for n, v in sorted(by.items())]
            for uri, by in out.items()}


def _sentence(code, f):
    """One finding in a sentence, assembled from its parts and never stored apart."""
    if code == "dead_term":
        out = f"{f['uri']} is stated {f['held']} times and read by nothing"
        if f["fills"]:
            out += f"; it fills `{f['fills']}`, which no rule here reads"
        return out
    if code == "empty_column":
        return f"{f['class']}.{f['column']} is reached by no rule"
    if code == "empty_class":
        return f"nothing in the log has ever been stated to be a {f['class']}"
    if code == "unfilled_role":
        return f"nothing in this application fills {f['role']}"
    if code == "lagging_pin":
        return (f"{f['module']} is pinned at {f['pinned']}; the store has sealed "
                f"up to {f['latest']}")
    if code == "orphaned_fact":
        out = f"{f['uri']} holds {f['held']} statements no module here declares"
        if f["declared_by"]:
            names = ", ".join(d["name"] for d in f["declared_by"])
            return out + f"; {names} does, and this application does not pin it"
        return out + "; nothing in the store declares it"
    raise KeyError(code)


def _diagnosis(code, findings):
    if findings is not None:
        for f in findings:
            f["sentence"] = _sentence(code, f)
    return {"code": code, "means": DIAGNOSES[code], "findings": findings}


def health(store, name, version, *, conn=None):
    """The six diagnoses for one application, and the terms they were read from.

    Without a log (`conn=None`) the three that need a count — dead terms, empty
    classes, orphaned facts — are reported as not counted rather than as
    empty: nothing found and nothing looked at are different answers.
    """
    out = {"name": name, "version": version, "counted": conn is not None,
           "modules": [], "terms": [], "diagnoses": [], "refusals": []}
    # Asking about a version the store does not hold is a refusal for the
    # caller; a version that is held but cannot be read is the report's answer.
    path = store.path(name, version)
    try:
        map_ = read_map(path, store)
    except Refusal as exc:
        return {**out, "refusals": [exc.as_dict()]}

    closure = store.closure(name, version)
    out["modules"] = [_pin(*p) for p in closure]
    classes, slots = _closure_documents(store, name, version)
    view = map_["view"]

    found, refused = readers(map_)
    out["refusals"] = refused
    read_by = {}
    for rule in found:
        for uri in rule["reads"]:
            read_by.setdefault(uri, []).append(
                {"rule": rule["rule"], "kind": rule["kind"], "reader": rule["reader"]})

    held = _counts(conn) if conn is not None else {}

    # Every predicate this application declares, with who reads it and how
    # often the log states it. The dead terms are a slice of this table; the
    # table itself is how somebody sees what the rules are actually built on.
    declared = {}
    for slot_name, s in slots.items():
        if not s.get("slot_uri") or slot_name not in view.all_slots():
            continue
        # The log holds the full URI; the document writes a CURIE.
        uri = predicate(view, view.induced_slot(slot_name))
        declared[uri] = {
            "uri": uri, "slot": slot_name, "module": s["module"],
            "on": sorted(c for c, spec in classes.items()
                         if slot_name in (spec.get("slots") or [])),
            "fills": _binding_of(slots, s),
            "held": held.get(uri, 0) if conn is not None else None,
            "read_by": read_by.get(uri, []),
        }
    out["terms"] = sorted(declared.values(), key=lambda t: (t["module"]["name"], t["uri"]))

    # 1. Dead terms: stated, and nothing reads them. The ones filling a
    # binding come first — a slot that fills a role's binding was put there to
    # be computed on, and nobody has collected on the promise yet.
    dead = None
    if conn is not None:
        dead = sorted(
            ({k: t[k] for k in ("uri", "slot", "module", "on", "fills", "held")}
             for t in declared.values() if t["held"] and not t["read_by"]),
            key=lambda t: (t["fills"] is None, -t["held"], t["uri"]))

    # 2. Empty columns: the compiler's own word for them, `unfilled`.
    report = check(store, name, version, map_=map_)
    empty_columns = [{"class": t["class"], "column": column}
                     for t in report["tables"] for column in t["unfilled"]]

    # 3. Empty classes: something the log could say an entity is, and never
    # has — counted over the class and everything concrete below it, because
    # an entity of a subclass is one of these too.
    empty_classes = None
    statable = sorted(str(c) for c in view.all_classes()
                      if not view.get_class(c).abstract and type_slot(map_, c) is not None)
    if conn is not None:
        carriers = {predicate(view, type_slot(map_, c)) for c in statable
                    if type_slot(map_, c).slot_uri}
        members = _members(conn, carriers)
        empty_classes = []
        for class_name in statable:
            below = _covered(view, class_name)
            if not any(members.get(class_uri(view, c)) for c in below):
                empty_classes.append({
                    "class": class_name,
                    "module": classes.get(class_name, {}).get("module"),
                    "read_by": sorted({r["rule"] for r in found
                                       if class_name in r["covers"]
                                       and r["kind"] in ("aggregate", "parameter")}),
                })

    # 4. Unfilled roles.
    unfilled = [{"role": r["name"], "module": r["module"],
                 "bindings": [b["name"] for b in r["bindings"]],
                 "candidates": statable}
                for r in roles(store, name, version)["roles"] if not r["filled_by"]]

    # 5. Lagging pins: anything in the closure the store has moved past.
    pinned_by = {}
    for dep in closure:
        for pin in store.imports(store.document(*dep)):
            pinned_by.setdefault(pin, []).append(_pin(*dep))
    lagging = []
    for dep_name, dep_version in closure:
        if dep_name == name:
            continue
        held_versions = [v["version"] for v in store.versions(dep_name)]
        newer = held_versions[held_versions.index(dep_version) + 1:]
        if newer:
            lagging.append({"module": dep_name, "pinned": dep_version,
                            "latest": held_versions[-1], "newer": newer,
                            "pinned_by": pinned_by.get((dep_name, dep_version), [])})

    # 6. Orphaned facts: the log holds them, and nothing this application can
    # see declares their predicate. Not lost: another module may declare it,
    # and pinning that module would make them readable again.
    orphaned = None
    if conn is not None:
        anywhere = _declared_anywhere(store)
        orphaned = sorted(
            ({"uri": uri, "held": count, "declared_by": anywhere.get(uri, [])}
             for uri, count in held.items() if uri not in declared and count),
            key=lambda f: (-f["held"], f["uri"]))

    out["diagnoses"] = [
        _diagnosis("dead_term", dead),
        _diagnosis("empty_column", empty_columns),
        _diagnosis("empty_class", empty_classes),
        _diagnosis("unfilled_role", unfilled),
        _diagnosis("lagging_pin", lagging),
        _diagnosis("orphaned_fact", orphaned),
    ]
    return out


__all__ = ["health", "DIAGNOSES"]

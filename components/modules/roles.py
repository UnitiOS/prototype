"""roles — what core obliges, who has honoured it, and what a swap would cost.

Two reads, and the second is the one worth having.

`roles()` answers what exists: every role in a closure, every binding it
carries, and every class that has filled it. It is the registry a rule is
written against, and it is derived entirely from sealed content — nobody
maintains it.

`fit()` answers what changes. Given two versions of one application, it says
which pins moved, which roles are now filled by somebody else, which rules
still resolve and which would go dark, and which predicates the log still holds
that no module in the new closure declares any more.

That last one is the answer to the question an app store has to be able to
face: what happens to the facts. In an ordinary system, uninstalling a module
drops its tables or strands them. Here the facts live below the schema, so a
swap changes only which predicates a rule can reach — the statements are
untouched, and the report says how many of them there are rather than leaving
somebody to wonder.

Nothing here writes, and nothing here decides. A swap is refused by nobody: the
report is for the person making the decision.
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from compile import plan_for, tables  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from generate import read_map  # noqa: E402
from seal import URI_PREDICATE, written_uri  # noqa: E402

# Every statement in the log, counted per predicate, for the predicates asked
# about. The predicate is an entity like any other and is named through the
# registry, which is why this joins the log to itself.
_HELD_SQL = """
SELECT u.value_literal AS uri, count(*) AS held
FROM assertion a
JOIN assertion u ON u.subject_id = a.predicate_id
WHERE u.predicate_id = (
        SELECT subject_id FROM assertion
        WHERE subject_id = predicate_id AND value_literal = %(uri)s
        ORDER BY seq LIMIT 1)
  AND u.value_literal = ANY(%(uris)s)
GROUP BY 1
"""

# Core's roles no new module is asked to fill (ECOSYSTEM_PLAN.md, step 0).
# Nothing reads `Event`'s `moment`, which the recording standard's time
# meaning already says of every date, and no module an agent built has ever
# filled `Flow`. Both stay in core, and every module sealed under them is read
# and totalled as before; they are only no longer offered or taught, so that
# new modules are not built on what core v3 may remove.
NOT_TAUGHT = ("Event", "Flow")


def taught(roles):
    """The roles of `roles` a new module is offered, in their order."""
    return [r for r in roles if r not in NOT_TAUGHT]


def _pin(name, version):
    return {"name": name, "version": version}


def _closure_documents(store, name, version):
    """Every sealed document this version can see, with where each came from."""
    classes, slots = {}, {}
    for dep in store.closure(name, version):
        document = store.document(*dep)
        for class_name, c in (document.get("classes") or {}).items():
            classes[class_name] = {**(c or {}), "module": _pin(*dep)}
        for slot_name, s in (document.get("slots") or {}).items():
            slots[slot_name] = {**(s or {}), "module": _pin(*dep)}
    return classes, slots


def _bindings(classes, slots, role):
    """The binding slots a role carries, its own and its ancestors'.

    Walked here rather than through SchemaView because this reads what the
    documents say, which is what a person looking at the store is reading.
    """
    out, stack, seen = [], [role], set()
    while stack:
        current = stack.pop()
        if current in seen or current not in classes:
            continue
        seen.add(current)
        for slot_name in classes[current].get("slots") or []:
            slot = slots.get(slot_name) or {}
            if slot.get("abstract") and slot_name not in [b["name"] for b in out]:
                out.append({
                    "name": slot_name,
                    # What the module that declared it calls it in prose. A
                    # reader is shown this and not the slot name, which is the
                    # name an expression is written with.
                    "title": str(slot.get("title") or slot_name),
                    "required": bool(slot.get("required")),
                    "range": slot.get("range"),
                    "description": slot.get("description") or "",
                })
        above = classes[current].get("is_a")
        stack += ([str(above)] if above else []) + \
                 [str(m) for m in (classes[current].get("mixins") or [])]
    return out


def _fills(classes, slots, class_name, binding):
    """The class's own slots that fill one binding: those descending from it."""
    found = []
    stack, seen = list(classes[class_name].get("slots") or []), set()
    while stack:
        slot_name = stack.pop(0)
        if slot_name in seen:
            continue
        seen.add(slot_name)
        slot = slots.get(slot_name) or {}
        if slot.get("abstract"):
            continue
        parent, hops = slot.get("is_a"), 0
        while parent and hops < 8:
            if str(parent) == binding:
                found.append(slot_name)
                break
            parent = (slots.get(str(parent)) or {}).get("is_a")
            hops += 1
    return sorted(found)


def _above(classes, class_name):
    """Every class this one inherits from, by `is_a` or by `mixins`, transitively.

    Both relations, and transitively, because a class mixing in Flow is an
    Event too — Flow is one. A reader asking who fills Event wants that class
    in the answer, not just whoever happened to write the word.
    """
    seen, stack = set(), [class_name]
    while stack:
        current = stack.pop()
        if current not in classes:
            continue
        above = classes[current].get("is_a")
        for parent in ([str(above)] if above else []) + \
                      [str(m) for m in (classes[current].get("mixins") or [])]:
            if parent in classes and parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return seen


def roles(store, name, version):
    """Every role this version can see, its bindings, and who has filled them.

    This is the catalogue a rule is written against. A role with nobody filling
    it is still listed: that is the shape of a question the store cannot answer
    yet, and it is more useful on the page than absent.
    """
    classes, slots = _closure_documents(store, name, version)

    out = []
    for role in sorted(classes):
        if not classes[role].get("abstract"):
            continue
        bindings = _bindings(classes, slots, role)
        filled = []
        for class_name in sorted(classes):
            if classes[class_name].get("abstract"):
                continue
            # Reached, not just named. A class mixing in Flow also fills Event,
            # because Flow is one — and the class's `moment` answers Event's
            # binding whether or not anybody wrote the word.
            if role not in _above(classes, class_name):
                continue
            filled.append({
                "class": class_name,
                "module": classes[class_name]["module"],
                "bindings": {
                    b["name"]: (_fills(classes, slots, class_name, b["name"]) or [None])[0]
                    for b in bindings
                },
            })
        out.append({
            "name": role,
            "module": classes[role]["module"],
            "description": classes[role].get("description") or "",
            "bindings": bindings,
            "filled_by": filled,
        })
    return {"name": name, "version": version,
            "modules": [_pin(*p) for p in store.closure(name, version)],
            "roles": out}


def _map_with_the_pins_of(store, name, version, other):
    """This version's own rules, read as though it pinned what `other` pins.

    The question a fit report answers is "my rules, their module", and there is
    no way to ask it without building the map that does not exist yet. So it is
    built here, in memory, and only ever planned — never sealed, never written,
    never registered. A hypothetical that is refused is the answer, not a
    failure.
    """
    document = dict(store.document(name, version))
    document["imports"] = list(store.document(name, other).get("imports") or [])
    view = store.view(yaml.safe_dump(document, sort_keys=False, allow_unicode=True))
    return {"path": store.path(name, version), "view": view, "version": version,
            "label": f"{name}@{version}"}


def _rules(store, name, version, map_=None):
    """Every derived column of every table, with what its rule resolved to."""
    map_ = map_ if map_ is not None else read_map(store.path(name, version), store)
    out = {}
    for class_name in tables(map_):
        try:
            plan_ = plan_for(map_, class_name)
        except Refusal as exc:
            # The refusal travels whole. A swap report that said only "this
            # breaks" would leave the reader to work out what to add, which is
            # the one question they came here with.
            out[(class_name, None)] = {"class": class_name, "column": None,
                                       "kind": "refused", "refusal": exc.as_dict()}
            continue
        for column in plan_["columns"]:
            key = (class_name, column["name"])
            if column["kind"] == "aggregate":
                spec = plan_["aggregates"][column["name"]]
                out[key] = {"class": class_name, "column": column["name"],
                            "kind": "aggregate", "over": spec["over"],
                            "covers": spec["covers"],
                            "reads": sorted(set(spec["measure_uris"])
                                            | {u for uris in [*spec["by"].values(),
                                                              *(spec.get("through") or {}).values()]
                                               for u in uris})}
            elif column["kind"] == "parameter":
                spec = plan_["parameters"][column["name"]]
                out[key] = {"class": class_name, "column": column["name"],
                            "kind": "parameter", "over": spec["of"],
                            "covers": [], "reads": sorted(spec["slot_uris"])}
    return out


def _declared(store, name, version):
    """Every predicate the closure declares, and which module version owns it."""
    owners = {}
    for dep in store.closure(name, version):
        document = store.document(*dep)
        for slot in (document.get("slots") or {}).values():
            if (slot or {}).get("slot_uri"):
                owners.setdefault(written_uri(document, slot["slot_uri"]), _pin(*dep))
    return owners


def _held(conn, uris):
    """How many statements the log holds under each of these predicates."""
    if not uris or conn is None:
        return {}
    with conn.cursor() as cur:
        cur.execute(_HELD_SQL, {"uri": URI_PREDICATE, "uris": list(uris)})
        return {uri: held for uri, held in cur.fetchall()}


def fit(store, name, version, against, *, conn=None):
    """What moving this application from one version to another would cost.

    Everything it reports is computed from two sealed closures and, for the
    last section, one count against the log. Nothing is estimated and nothing
    is a warning about something that might happen: a rule either resolves
    against the new closure or it does not, and the report says which.
    """
    before, after = (name, version), (name, against)
    pins_before = {n: v for n, v in store.closure(*before) if n != name}
    pins_after = {n: v for n, v in store.closure(*after) if n != name}

    removed = sorted(n for n in pins_before
                     if n not in pins_after or pins_after[n] != pins_before[n])
    added = sorted(n for n in pins_after
                   if n not in pins_before or pins_before[n] != pins_after[n])

    roles_before = {r["name"]: r for r in roles(store, *before)["roles"]}
    roles_after = {r["name"]: r for r in roles(store, *after)["roles"]}
    role_rows = []
    for role in sorted(set(roles_before) | set(roles_after)):
        was = [f["class"] for f in roles_before.get(role, {}).get("filled_by", [])]
        now = [f["class"] for f in roles_after.get(role, {}).get("filled_by", [])]
        role_rows.append({
            "name": role,
            "before": was, "after": now,
            "status": "unchanged" if was == now else
                      ("gained" if not was else "lost" if not now else "replaced"),
        })

    # The rules are this version's own, both times. What changes between the
    # two readings is only which modules they are resolved against — which is
    # exactly the move being considered.
    rules_before = _rules(store, *before)
    rules_after = _rules(store, name, version,
                         _map_with_the_pins_of(store, name, version, against))
    # A table the new closure refuses outright explains its own columns, so
    # they are not listed again underneath it.
    refused = {key[0] for key, rule in rules_after.items() if rule["kind"] == "refused"}
    rule_rows, dark = [], []
    for key in sorted(set(rules_before) | set(rules_after), key=lambda k: (k[0], k[1] or "")):
        was, now = rules_before.get(key), rules_after.get(key)
        if now and now["kind"] == "refused":
            dark.append({**now, "why": now["refusal"]["sentence"]})
            continue
        if key[0] in refused:
            continue
        if was and not now:
            # Not a refusal: the new closure simply has nothing to say here,
            # and there is no gate to ask for a repair.
            dark.append({**was, "refusal": None,
                         "why": "nothing in the new closure answers this rule"})
            continue
        if not was or not now:
            continue
        rule_rows.append({
            "class": key[0], "column": key[1], "kind": now["kind"],
            "over": now["over"],
            "covered_before": was.get("covers", []),
            "covered_after": now.get("covers", []),
            "reads_before": was.get("reads", []),
            "reads_after": now.get("reads", []),
            "status": "unchanged" if was.get("reads") == now.get("reads")
                      else "rebound",
        })

    # The facts. A predicate the new closure no longer declares is not deleted
    # and not migrated — it stops being read, and that is the whole of it.
    declared_before = _declared(store, *before)
    declared_after = _declared(store, *after)
    orphan_uris = [uri for uri, owner in declared_before.items()
                   if uri not in declared_after]
    held = _held(conn, orphan_uris)
    orphaned = sorted(
        ({"uri": uri, "module": declared_before[uri], "held": held.get(uri, 0)}
         for uri in orphan_uris),
        key=lambda row: (-row["held"], row["uri"]),
    )

    return {
        "name": name, "from": version, "to": against,
        "pins": {
            "removed": [_pin(n, pins_before[n]) for n in removed],
            "added": [_pin(n, pins_after[n]) for n in added],
            "kept": [_pin(n, v) for n, v in sorted(pins_after.items())
                     if pins_before.get(n) == v],
        },
        "roles": role_rows,
        "rules": rule_rows,
        "dark": dark,
        "orphaned": orphaned,
        "orphaned_statements": sum(row["held"] for row in orphaned),
        "clean": not dark,
    }


__all__ = ["NOT_TAUGHT", "roles", "fit", "taught"]

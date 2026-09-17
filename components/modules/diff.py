"""diff — what changed between two versions of a schema, in the terms that matter.

Compared on what each version declares itself, not on what it imports: a
module's own version history is about its own classes and slots. Imports are
compared as a list of pins, so moving from `@x/y@v1` to `@x/y@v2` shows as
exactly that.

A slot that disappears under one name and appears under another with the same
`slot_uri` is a rename. It is reported as one, because the kernel sees one
predicate: every fact recorded under the old name still belongs to the new one.
"""

SLOT_FIELDS = ("slot_uri", "range", "identifier", "required", "multivalued",
               "designates_type", "equals_expression", "title", "description")
CLASS_FIELDS = ("is_a", "description")


def _changes(old, new, fields):
    changed = {}
    for field in fields:
        if old.get(field) != new.get(field):
            changed[field] = {"from": old.get(field), "to": new.get(field)}
    if (old.get("annotations") or {}) != (new.get("annotations") or {}):
        changed["annotations"] = {"from": old.get("annotations"), "to": new.get("annotations")}
    return changed


def compare(old, new):
    old_imports = [str(i) for i in old.get("imports") or []]
    new_imports = [str(i) for i in new.get("imports") or []]

    old_slots = old.get("slots") or {}
    new_slots = new.get("slots") or {}
    removed = [s for s in old_slots if s not in new_slots]
    added = [s for s in new_slots if s not in old_slots]

    renamed = []
    for gone in list(removed):
        uri = (old_slots[gone] or {}).get("slot_uri")
        match = next((s for s in added if uri and (new_slots[s] or {}).get("slot_uri") == uri), None)
        if match:
            renamed.append({"from": gone, "to": match, "slot_uri": uri,
                            "changes": _changes(old_slots[gone] or {}, new_slots[match] or {},
                                                tuple(f for f in SLOT_FIELDS if f != "slot_uri"))})
            removed.remove(gone)
            added.remove(match)

    old_classes = old.get("classes") or {}
    new_classes = new.get("classes") or {}
    classes_changed = []
    for name in old_classes:
        if name not in new_classes:
            continue
        before, after = old_classes[name] or {}, new_classes[name] or {}
        fields = _changes(before, after, CLASS_FIELDS)
        slots_before, slots_after = before.get("slots") or [], after.get("slots") or []
        if fields or slots_before != slots_after:
            classes_changed.append({
                "name": name,
                "changes": fields,
                "slots_added": [s for s in slots_after if s not in slots_before],
                "slots_removed": [s for s in slots_before if s not in slots_after],
            })

    slots_changed = []
    for name in old_slots:
        if name in new_slots:
            fields = _changes(old_slots[name] or {}, new_slots[name] or {}, SLOT_FIELDS)
            if fields:
                slots_changed.append({"name": name, "changes": fields})

    return {
        "imports": {
            "added": [i for i in new_imports if i not in old_imports],
            "removed": [i for i in old_imports if i not in new_imports],
        },
        "classes": {
            "added": [c for c in new_classes if c not in old_classes],
            "removed": [c for c in old_classes if c not in new_classes],
            "changed": classes_changed,
        },
        "slots": {
            "added": added,
            "removed": removed,
            "renamed": renamed,
            "changed": slots_changed,
        },
    }

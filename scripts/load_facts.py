"""Load stated facts into a log, through the one write gate, from a data file.

`seal` puts a *map* into the log — the vocabulary, the predicates, the shape.
Nothing yet puts *instances* there except a form, one field at a time. This is
the bulk door for the same thing, and it is the same door underneath: one
`perform()` per action, one intent per action, every value resolved through the
map rather than named in code.

It knows nothing about what it is loading. A data file names one sealed map
version, and under it a list of actions; the slot names inside are looked up in
that map, which decides each one's predicate URI and whether the value names
another entity or is a literal. Point it at another map and another world goes
in.

    map: "@scope/name@v1"     the version these facts are stated under. It is
                              what every assertion records as its
                              `ontology_version`: a fact is stated under the
                              map the person was looking at, and which module
                              owns each predicate is recoverable from the
                              store.
    purpose: demonstration    optional; becomes every intent's `reason_code`,
                              so a log holding made-up content says so.
    actions:                  one intent each, in order.
      - action: <name>        the intent's `action_name`.
        actor: <id>           who; falls back to --actor.
        valid_from: <instant> from when what this action says is true of the
                              world. Defaults to the action's `occurred_at`.
        occurred_at: <instant>  when the action was taken.
        recorded_at: <instant>  when this log learned of it. Defaults to now.
        source: <word>        the kernel's own vocabulary; default human_stated.
        note: <text>
        entities:
          - uri: <prefix:local>   what the log calls this entity.
            class: <ClassName>    stated under whichever slot the map flags
                                  `designates_type`, so this file names no
                                  predicate of its own.
            valid_from: <instant> overrides the action's.
            facts:
              <slot name>: <value>

A URI the log already holds is reused, never minted twice — the same rule
`seal` follows. Nothing here revokes or edits: stating something again at a
later `valid_from` is how the world changes, and both rows stay.

Run: UNITI_DSN=... .venv/Scripts/python.exe scripts/load_facts.py <data.yaml> --actor <id>
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from components.modules.store import PIN, ModuleError, Store  # noqa: E402
from perform import connect, perform  # noqa: E402
from seal import _REGISTRY_SQL, URI_PREDICATE  # noqa: E402

DEFAULT_SOURCE = "human_stated"


class DataError(ValueError):
    """The data file cannot be loaded. Nothing has been written."""


def _utc(value, fallback=None):
    if value is None:
        return fallback
    moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def pinned_map(store, pin):
    """The map a data file names, as the two lookups loading it needs.

    `slots` is slot name -> (predicate URI, whether the value names an entity),
    read through SchemaView so a slot inherited or defaulted is there too.
    `type_slot` is the predicate a class fact is stated under, per class, which
    the map flags and a data file never names.
    """
    match = PIN.match(str(pin or ""))
    if not match:
        raise DataError(f"map {pin!r} is not a pinned version, such as @scope/name@v1")
    view = store.view(store.path(match["name"], match["version"]))
    classes = set(str(name) for name in view.all_classes())

    slots, type_slot = {}, {}
    for class_name in classes:
        for slot in view.class_induced_slots(class_name):
            if not slot.slot_uri:
                raise DataError(f"{class_name}.{slot.name} declares no slot_uri")
            slots[str(slot.name)] = (str(slot.slot_uri), str(slot.range) in classes)
            if slot.designates_type:
                type_slot[class_name] = str(slot.slot_uri)
    return {"label": str(pin), "classes": classes, "slots": slots, "type_slot": type_slot}


def _statements(map_, action, where):
    """One action's facts as (subject uri, predicate uri, value, is_ref, valid_from)."""
    default_valid = _utc(action.get("valid_from"), _utc(action.get("occurred_at")))
    out = []
    for i, item in enumerate(action.get("entities") or []):
        at = f"{where}.entities[{i}]"
        uri = item.get("uri")
        if not uri:
            raise DataError(f"{at} states no uri, so nothing in the log can be it")
        valid_from = _utc(item.get("valid_from"), default_valid)
        if valid_from is None:
            raise DataError(f"{at} has no valid_from, and its action states none")

        class_name = item.get("class")
        if class_name is not None:
            if str(class_name) not in map_["classes"]:
                raise DataError(
                    f"{at} is a {class_name!r}, which {map_['label']} has no class for")
            predicate = map_["type_slot"].get(str(class_name))
            if predicate is None:
                raise DataError(
                    f"{at}: {class_name} has no slot carrying designates_type, so "
                    f"nothing in the log can say an entity is one"
                )
            out.append((uri, predicate, str(class_name), False, valid_from))

        for slot_name, value in (item.get("facts") or {}).items():
            known = map_["slots"].get(str(slot_name))
            if known is None:
                raise DataError(
                    f"{at} states {slot_name!r}, which {map_['label']} has no slot for")
            predicate, ref = known
            out.append((uri, predicate, str(value), ref, valid_from))
    return out


def load(conn, data, store, *, actor_id, recorded_at=None):
    """Write every action in `data`, one intent each. Returns a summary per action."""
    map_ = pinned_map(store, data.get("map"))
    purpose = data.get("purpose")
    actions = data.get("actions") or []
    if not actions:
        raise DataError("the data file states no actions")

    with conn.cursor() as cur:
        cur.execute(_REGISTRY_SQL, (URI_PREDICATE,))
        known = {uri: entity_id for uri, entity_id in cur.fetchall()}

    written = []
    for i, action in enumerate(actions):
        where = f"actions[{i}]"
        name = action.get("action")
        if not name:
            raise DataError(f"{where} states no action name")
        statements = _statements(map_, action, where)
        if not statements:
            raise DataError(f"{where} states nothing")

        source = str(action.get("source") or DEFAULT_SOURCE)
        occurred_at = _utc(action.get("occurred_at"))
        recorded = _utc(action.get("recorded_at"), recorded_at)

        wanted = [URI_PREDICATE]
        wanted += [s[0] for s in statements]
        wanted += [s[1] for s in statements]
        wanted += [s[2] for s in statements if s[3]]
        minting = []
        for uri in wanted:
            if uri not in known and uri not in minting:
                minting.append(uri)

        def ref(uri, _known=known):
            return _known.get(uri, uri)

        earliest = min(s[4] for s in statements)
        assertions = [
            {"subject": ref(uri), "predicate": ref(URI_PREDICATE), "value": uri,
             "valid_from": earliest, "source": "system_derived"}
            for uri in minting
        ] + [
            {"subject": ref(subject), "predicate": ref(predicate),
             **({"ref": ref(value)} if is_ref else {"value": value}),
             "valid_from": valid_from, "source": source}
            for subject, predicate, value, is_ref, valid_from in statements
        ]

        intent_id, names, assertion_ids = perform(
            conn,
            actor_id=str(action.get("actor") or actor_id),
            agent_id="load_facts",
            action_name=str(name),
            ontology_version=map_["label"],
            reason_code=purpose,
            note=action.get("note"),
            mint=minting,
            assertions=assertions,
            occurred_at=occurred_at,
            recorded_at=recorded,
        )
        known.update(names)
        written.append({"action": str(name), "intent_id": intent_id,
                        "minted": len(minting), "assertions": len(assertion_ids)})
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data", help="a data file")
    parser.add_argument("--actor", default="dev", help="who, where an action names nobody")
    args = parser.parse_args(argv)

    data = yaml.safe_load(Path(args.data).read_text(encoding="utf-8")) or {}
    try:
        with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
            written = load(conn, data, Store.from_env(), actor_id=args.actor)
    except (DataError, ModuleError) as exc:
        print(f"not loaded: {exc}", file=sys.stderr)
        return 2
    minted = sum(w["minted"] for w in written)
    stated = sum(w["assertions"] for w in written) - minted
    print(f"{len(written)} actions, {minted} entities minted, {stated} statements")
    return 0


if __name__ == "__main__":
    sys.exit(main())

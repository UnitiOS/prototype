"""generator — a projection table and a form, from a sealed map and the log.

Nothing here is hand-written per class. The map says what a class is made of;
the log says what has been said about the world; the generator puts the two
together and renders the result. Point it at another class and another table
comes out.

    the map    which slots a class has, what each one ranges over, which are
               required. Read with SchemaView so `is_a` and `default_range`
               are applied — a class's columns are its *induced* slots.
    the log    the values. Every cell is one `resolve_single()` call at the
               same (valid_at, as_of), so the table is a read of the kernel and
               never a store of its own.

**Which entities are rows is not in the map.** A class is a set of slots; the
log is (subject, predicate, value); and nothing anywhere asserts that an entity
is a Material. So the rule here is the only one the two files can support:

    a row of this table is an entity that is the subject of at least one fact
    under one of this table's columns, and has at least one value standing at
    these clocks.

That is self-consistent — the table shows exactly what it has something to say
about — and it is a guess, not a reading. An inherited slot makes it visibly
wrong: `stock_location` is a column of Material *and* of Pan, so a pan sitting
in a freezer is a row of the material table with every other cell blank. See
OPEN.md. It is not worked around here, because working around it would mean
inventing a class assertion the business never made.

A form is the same slots, asked for rather than reported. `submit()` turns the
entered values into one `perform()` call — one form submission is one intent —
and the value comes straight back out of `resolve_single()`.

Run:
    generate.py table  business/v1.yaml Material --out build/material.txt
    generate.py table  business/v1.yaml Material --verify
    generate.py form   business/v1.yaml Material
    generate.py submit business/v1.yaml Material --subject uniti:milk_powder \
                       --set material_supplier=uniti:dairy_supplier --actor fareza
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from linkml_runtime import SchemaView
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components"))

from perform import connect, perform  # noqa: E402
from resolve import resolve_single  # noqa: E402
from seal import URI_PREDICATE  # noqa: E402

# Someone typing into a form is stating something. The kernel's vocabulary.
FORM_SOURCE = "human_stated"
MINT_SOURCE = "system_derived"

# Every URI the log has ever registered, both ways round.
_REGISTRY_SQL = """
SELECT a.subject_id, a.value_literal
FROM assertion a
WHERE a.predicate_id = (
        SELECT subject_id FROM assertion
        WHERE subject_id = predicate_id AND value_literal = %s
        ORDER BY seq LIMIT 1)
  AND a.value_literal IS NOT NULL
"""

# Anything ever said under one of these predicates. Record time is not filtered
# here: a subject whose only facts were recorded after `as_of` survives this
# query and is dropped later, when every one of its cells resolves to nothing.
_SUBJECTS_SQL = """
SELECT DISTINCT subject_id FROM assertion WHERE predicate_id = ANY(%s)
"""

# The independent read. Deliberately not resolve_single: one statement with
# DISTINCT ON instead of one query per pair, so `--verify` compares two paths
# through the same rule rather than a function against itself.
_DIRECT_SQL = """
SELECT DISTINCT ON (a.subject_id, a.predicate_id)
       a.subject_id, a.predicate_id, a.value_literal, a.value_ref
FROM assertion a
WHERE a.subject_id   = ANY(%(subjects)s)
  AND a.predicate_id = ANY(%(predicates)s)
  AND a.valid_from  <= %(valid_at)s
  AND a.recorded_at <= %(as_of)s
  AND num_nonnulls(a.value_literal, a.value_ref) = 1
  AND NOT EXISTS (
      SELECT 1 FROM assertion r
      WHERE r.revokes = a.id
        AND r.recorded_at <= %(as_of)s
  )
ORDER BY a.subject_id, a.predicate_id,
         a.valid_from DESC, a.recorded_at DESC, a.seq DESC
"""


class MapError(Exception):
    """The map cannot be generated from. Nothing has been written."""


def _utc(value):
    moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def read_map(path):
    """One sealed version file, as far as a generator needs it.

    A draft is refused: it carries no `version`, and every assertion this
    writes has to name the version it was stated under.
    """
    path = Path(path)
    if not path.is_file():
        raise MapError(f"no map at {path}")
    view = SchemaView(path.read_text(encoding="utf-8"))
    version = view.schema.version
    if not version:
        raise MapError(f"{path.name} carries no version, so it is not a sealed map")
    return {"path": path, "view": view, "version": version}


def columns(map_, class_name):
    """The class's induced slots: its own, its parents', with ranges applied.

    Each column carries what the map says about it and nothing more. `ref` is
    the same test `seal` makes when it decides which column a value lands in:
    a class range means the value names another entity.
    """
    view = map_["view"]
    if class_name not in view.all_classes():
        raise MapError(
            f"{map_['path'].name} declares no class {class_name!r} — it has "
            f"{sorted(view.all_classes())}"
        )
    classes = set(view.all_classes())
    out = []
    for slot in view.class_induced_slots(class_name):
        if not slot.slot_uri:
            raise MapError(f"slot {slot.name!r} declares no slot_uri")
        out.append(
            {
                "name": slot.name,
                "uri": slot.slot_uri,
                "range": slot.range,
                "required": bool(slot.required),
                "multivalued": bool(slot.multivalued),
                "ref": slot.range in classes,
                "description": slot.description or "",
            }
        )
    return out


def _identifier(map_, class_name):
    """The slot the map says identifies this class, or None."""
    if class_name not in map_["view"].all_classes():
        return None
    for slot in map_["view"].class_induced_slots(class_name):
        if slot.identifier:
            return slot
    return None


def _registry(conn):
    """uri -> entity id, and entity id -> uri."""
    with conn.cursor() as cur:
        cur.execute(_REGISTRY_SQL, (URI_PREDICATE,))
        rows = cur.fetchall()
    return {uri: eid for eid, uri in rows}, {eid: uri for eid, uri in rows}


def _subjects(conn, predicate_ids):
    if not predicate_ids:
        return []
    with conn.cursor() as cur:
        cur.execute(_SUBJECTS_SQL, (list(predicate_ids),))
        return [row[0] for row in cur.fetchall()]


def table(conn, map_, class_name, *, valid_at, as_of):
    """The projection: columns from the map, rows and cells from the log."""
    cols = columns(map_, class_name)
    by_uri, by_id = _registry(conn)
    predicate_ids = [by_uri[c["uri"]] for c in cols if c["uri"] in by_uri]

    rows = []
    for subject_id in _subjects(conn, predicate_ids):
        cells = []
        for col in cols:
            predicate_id = by_uri.get(col["uri"])
            row = (
                resolve_single(conn, subject_id=subject_id,
                               predicate_id=predicate_id,
                               valid_at=valid_at, as_of=as_of)
                if predicate_id is not None
                else None
            )
            if row is None:
                cells.append(None)
            elif row["value_ref"] is not None:
                cells.append(by_id.get(row["value_ref"], f"<{row['value_ref']}>"))
            else:
                cells.append(row["value_literal"])
        # An entity with nothing standing at these clocks is not a row: the
        # log has no answer about it, and an all-blank line would claim it did.
        if any(cell is not None for cell in cells):
            rows.append({"subject": subject_id,
                         "uri": by_id.get(subject_id, f"<{subject_id}>"),
                         "cells": cells})

    rows.sort(key=lambda r: r["uri"])
    return {"class": class_name, "columns": cols, "rows": rows,
            "valid_at": valid_at, "as_of": as_of, "version": map_["version"]}


def direct_read(conn, subject_ids, predicate_ids, *, valid_at, as_of):
    """(subject, predicate) -> (value_literal, value_ref), in one statement."""
    if not subject_ids or not predicate_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            _DIRECT_SQL,
            {"subjects": list(subject_ids), "predicates": list(predicate_ids),
             "valid_at": valid_at, "as_of": as_of},
        )
        return {(s, p): (literal, ref) for s, p, literal, ref in cur.fetchall()}


def verify(conn, built):
    """Every cell of a built table, against a direct read of the log.

    Returns the list of disagreements, which is empty when the generated table
    is what the log says at those clocks.
    """
    by_uri, by_id = _registry(conn)
    predicate_ids = [by_uri[c["uri"]] for c in built["columns"] if c["uri"] in by_uri]
    subject_ids = [r["subject"] for r in built["rows"]]
    direct = direct_read(conn, subject_ids, predicate_ids,
                         valid_at=built["valid_at"], as_of=built["as_of"])

    wrong = []
    for row in built["rows"]:
        for col, cell in zip(built["columns"], row["cells"]):
            predicate_id = by_uri.get(col["uri"])
            literal, ref = direct.get((row["subject"], predicate_id), (None, None))
            expected = by_id.get(ref, f"<{ref}>") if ref is not None else literal
            if cell != expected:
                wrong.append((row["uri"], col["name"], cell, expected))
    return wrong


def form(conn, map_, class_name, *, valid_at=None, as_of=None):
    """The same slots, asked for instead of reported.

    A field over a class range offers what the log already holds for that
    class, labelled by whatever the map says identifies it. That is the whole
    of the dropdown: the options are entities, not strings, so choosing one
    writes an edge. The options are read at clocks like everything else — a
    form filled in today offers what today's log holds, which is the default.
    """
    valid_at = valid_at or _NOW()
    as_of = as_of or _NOW()
    fields = []
    for col in columns(map_, class_name):
        field = dict(col)
        field["options"] = (
            _options(conn, map_, col["range"], valid_at=valid_at, as_of=as_of)
            if col["ref"] else []
        )
        fields.append(field)
    return {"class": class_name, "fields": fields, "version": map_["version"],
            "source": map_["path"].name}


def _options(conn, map_, class_name, *, valid_at, as_of):
    """Every entity the log holds for a class, as (uri, label) pairs."""
    cols = columns(map_, class_name)
    by_uri, by_id = _registry(conn)
    predicate_ids = [by_uri[c["uri"]] for c in cols if c["uri"] in by_uri]
    identifier = _identifier(map_, class_name)
    label_id = by_uri.get(identifier.slot_uri) if identifier else None

    out = []
    for subject_id in _subjects(conn, predicate_ids):
        label = ""
        if label_id is not None:
            row = resolve_single(conn, subject_id=subject_id, predicate_id=label_id,
                                 valid_at=valid_at, as_of=as_of)
            label = (row or {}).get("value_literal") or ""
        out.append((by_id.get(subject_id, f"<{subject_id}>"), label))
    out.sort()
    return out


def _NOW():
    return datetime.now(timezone.utc)


def submit(conn, map_, class_name, *, subject, values, actor_id,
           valid_from=None, recorded_at=None):
    """One form submission: one intent, N assertions.

    `values` is keyed by field name, which is the slot's name in the map. A
    URI never seen before — the subject, or the entity a ref field names — is
    registered under `uniti:uri` exactly as `seal` registers one, so the form
    and the seal put the same entity in the log rather than two.
    """
    fields = {c["name"]: c for c in columns(map_, class_name)}
    unknown = sorted(set(values) - set(fields))
    if unknown:
        raise MapError(
            f"{class_name} has no field {unknown} — it has {sorted(fields)}"
        )
    if not values:
        raise MapError(f"nothing entered for {subject}")

    by_uri, _ = _registry(conn)
    named = [subject] + [f["uri"] for f in fields.values() if f["name"] in values]
    named += [str(v) for name, v in values.items() if fields[name]["ref"]]

    minting = []
    for uri in named:
        if uri not in by_uri and uri not in minting:
            minting.append(uri)

    def ref(uri):
        return by_uri.get(uri, uri)

    assertions = [
        {"subject": ref(uri), "predicate": ref(URI_PREDICATE), "value": uri,
         "valid_from": valid_from, "source": MINT_SOURCE}
        for uri in minting
    ] + [
        {
            "subject": ref(subject),
            "predicate": ref(fields[name]["uri"]),
            **({"ref": ref(str(value))} if fields[name]["ref"]
               else {"value": str(value)}),
            "valid_from": valid_from,
            "source": FORM_SOURCE,
        }
        for name, value in values.items()
    ]

    intent_id, names, assertion_ids = perform(
        conn,
        actor_id=actor_id,
        agent_id="generator",
        action_name=f"submit_{class_name}",
        ontology_version=map_["version"],
        note=f"{class_name} form, {len(values)} field(s), {subject}",
        mint=minting,
        assertions=assertions,
        recorded_at=recorded_at,
    )
    entities = {**by_uri, **names}
    return {"intent_id": intent_id, "subject_id": entities[subject],
            "predicates": {name: entities[fields[name]["uri"]] for name in values},
            "assertions": assertion_ids, "minted": names}


# ---- rendering ------------------------------------------------------------

def _grid(headers, rows):
    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) if rows
              else len(headers[i]) for i in range(len(headers))]

    def line(cells):
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()

    return [line(headers), line(["-" * w for w in widths])] + [line(r) for r in rows]


def render_table(built):
    cols = built["columns"]
    headers = ["subject"] + [c["name"] for c in cols]
    body = [[r["uri"]] + ["" if c is None else c for c in r["cells"]]
            for r in built["rows"]]
    blank = sum(1 for r in built["rows"] for c in r["cells"] if c is None)
    empty = [c["name"] for i, c in enumerate(cols)
             if all(r["cells"][i] is None for r in built["rows"])]

    out = [
        f"{built['class']}  ({built['version']})",
        f"valid_at   {built['valid_at']}",
        f"as_of      {built['as_of']}",
        "",
    ]
    out += _grid(headers, body)
    out += [
        "",
        f"{len(built['rows'])} rows, {len(cols)} columns, "
        f"{blank} of {len(built['rows']) * len(cols)} cells blank",
    ]
    if empty:
        out.append(f"columns the log says nothing under: {', '.join(empty)}")
    return "\n".join(out) + "\n"


def render_form(built):
    rows = []
    for f in built["fields"]:
        kind = f["range"] or "string"
        if f["ref"]:
            kind = f"-> {kind}"
        if f["multivalued"]:
            kind += " (many)"
        rows.append([f["name"], kind, "required" if f["required"] else "",
                     f["description"].split(". ")[0][:56]])

    out = [f"{built['class']} form  ({built['source']}, {built['version']})", ""]
    out += _grid(["field", "type", "", "from the map"], rows)

    for f in built["fields"]:
        if not f["ref"]:
            continue
        out.append("")
        if f["options"]:
            out.append(f"{f['name']} offers {len(f['options'])}:")
            out += [f"    {uri}{'  ' + label if label else ''}"
                    for uri, label in f["options"]]
        else:
            out.append(f"{f['name']} offers nothing: the log holds no {f['range']}")
    return "\n".join(out) + "\n"


# ---- CLI ------------------------------------------------------------------

def _write(text, out):
    if out is None:
        sys.stdout.write(text)
        return
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out} ({len(text.encode('utf-8'))} bytes)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate from a sealed map.")
    sub = parser.add_subparsers(dest="what", required=True)

    for name in ("table", "form", "submit"):
        p = sub.add_parser(name)
        p.add_argument("map", help="a sealed version, e.g. business/v1.yaml")
        p.add_argument("klass", metavar="CLASS")
        if name != "submit":
            p.add_argument("--out", default=None)
        if name == "table":
            p.add_argument("--valid-at", default=None)
            p.add_argument("--as-of", default=None)
            p.add_argument("--verify", action="store_true",
                           help="compare every cell with a direct read")
        if name == "submit":
            p.add_argument("--subject", required=True, metavar="URI")
            p.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE")
            p.add_argument("--actor", required=True)
            p.add_argument("--valid-from", default=None)
            p.add_argument("--recorded-at", default=None)

    args = parser.parse_args(argv)

    try:
        map_ = read_map(args.map)
        with connect() as conn:
            if args.what == "form":
                _write(render_form(form(conn, map_, args.klass)), args.out)
                return 0

            if args.what == "table":
                now = _NOW().isoformat()
                built = table(conn, map_, args.klass,
                              valid_at=args.valid_at or now,
                              as_of=args.as_of or now)
                _write(render_table(built), args.out)
                if args.verify:
                    wrong = verify(conn, built)
                    cells = len(built["rows"]) * len(built["columns"])
                    if wrong:
                        for uri, name, got, expected in wrong:
                            print(f"  {uri}.{name}: table {got!r}, log {expected!r}")
                        print(f"{len(wrong)} of {cells} cells differ")
                        return 1
                    print(f"verified: {cells} cells equal a direct read of the log")
                return 0

            values = {}
            for pair in args.set:
                if "=" not in pair:
                    raise MapError(f"--set {pair} is not FIELD=VALUE")
                field, value = pair.split("=", 1)
                values[field] = value
            result = submit(conn, map_, args.klass, subject=args.subject,
                            values=values, actor_id=args.actor,
                            valid_from=_utc(args.valid_from) if args.valid_from else None,
                            recorded_at=_utc(args.recorded_at) if args.recorded_at else None)
            print(f"intent {result['intent_id']}: {len(result['minted'])} minted, "
                  f"{len(result['assertions'])} assertions")
            for name in values:
                print(f"  {args.subject}  {name}  {values[name]}")
            return 0
    except MapError as exc:
        print(f"not generated: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

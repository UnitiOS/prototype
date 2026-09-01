"""Prove or break `derive`: a computation declared in a sealed map, run against
the log at a stated pair of clocks.

Throwaway. Nothing under `components/` is created or changed, and this file is
expected to be deleted once the finding is written down.

The claim under test is milestone three in miniature. A map declares, on a slot
nobody ever states a value for, *what* to sum, over *which* class, grouped by
*which* dimensions:

    in_total:
      annotations:
        aggregate:
          value:
            over: Movement
            sum: movement_quantity
            by:
              holding_thing: movement_thing
              holding_place: movement_into

Nothing here knows what a Movement is. `over`, `sum` and both `by` dimensions
are read out of the sealed file; the rows come from `components/generator` at a
stated `(valid_at, as_of)`; the last column is LinkML's own `equals_expression`
subtracting one sum from the other. Ask the same question at a later `as_of`
and a different number comes out, because one movement was recorded five weeks
late. That difference is the whole point, and the script asserts it rather than
leaving it to the eye.

Two things are already known and are used rather than re-derived (LOG.md,
1 Sep): `eval_expr` has six functions and `sum` is not among them, so the
summing is done here in Python; and `assertion.value_literal` is text, so every
cell is cast to the range the map declares before any arithmetic.

Against the throwaway database, never the working log:

    UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check \
        .venv/Scripts/python.exe scripts/trial_derive.py
"""

import os
import sys
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path

import jsonasobj2
from jsonasobj2 import JsonObj
from linkml_runtime.utils.inference_utils import Config, generate_slot_value

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components"))

from generate import connect, read_map, table  # noqa: E402
from ontology.resolve import resolve_version  # noqa: E402

MAPS = ROOT / "business" / "trial2"
DERIVED = "Holding"

# One question about one day, asked twice. Between the two answers the log
# learned about a movement that had been valid on that day all along.
VALID_AT = "2026-03-01T00:00:00Z"
AS_OF = ("2026-03-06T00:00:00Z", "2026-04-11T00:00:00Z")

CAST = {"integer": int, "decimal": Decimal, "float": float, "boolean": bool}


def cast(value, declared):
    """A cell, as the type its own slot declares. Text otherwise."""
    if value is None or declared not in CAST:
        return value
    try:
        return CAST[declared](value)
    except (ValueError, ArithmeticError):
        return value


def aggregates(view, class_name):
    """(slot, spec) for every slot of the class carrying `annotations.aggregate`."""
    out = []
    for slot in view.class_induced_slots(class_name):
        if "aggregate" not in slot.annotations:
            continue
        out.append((slot, jsonasobj2.as_dict(slot.annotations["aggregate"].value)))
    return out


def computed(view, class_name):
    """The class's slots LinkML itself can compute, once the aggregates stand."""
    return [
        slot
        for slot in view.class_induced_slots(class_name)
        if slot.equals_expression and "aggregate" not in slot.annotations
    ]


def type_slot(view):
    """The slot the map says carries class membership, or None."""
    for slot in view.all_slots().values():
        if slot.designates_type:
            return slot
    return None


def source_rows(conn, map_, class_name, *, valid_at, as_of):
    """The generator's table for the class, and the subset the log calls one.

    The generator's row rule is a guess — an entity with a value under any of
    the class's columns. `designates_type` turns the guess into a reading: a
    row is kept only if the log states, at these clocks, that it belongs here.
    """
    built = table(conn, map_, class_name, valid_at=valid_at, as_of=as_of)
    names = [c["name"] for c in built["columns"]]
    declared = {c["name"]: c["range"] for c in built["columns"]}
    stated = type_slot(map_["view"])
    offered = [dict(zip(names, r["cells"]), uri=r["uri"]) for r in built["rows"]]
    kept = [r for r in offered if stated and r.get(stated.name) == class_name]
    return offered, kept, declared


def group(rows, spec, declared):
    """One aggregate: rows grouped by its `by` dimensions, its `sum` summed.

    A row saying nothing under a dimension is in no group — a movement that
    left nowhere is not a departure from anywhere. A row that is in a group and
    states no value under the summed slot is counted as `silent` and adds
    nothing. That is what this script does with it, not what anyone decided it
    means.
    """
    groups = OrderedDict()
    for row in rows:
        key = tuple(row.get(source) for source in spec["by"].values())
        if any(k is None for k in key):
            continue
        g = groups.setdefault(key, {"total": Decimal(0), "from": [], "silent": []})
        value = row.get(spec["sum"])
        if value is None:
            g["silent"].append(row["uri"])
            continue
        g["from"].append(row["uri"])
        g["total"] += cast(value, declared[spec["sum"]])
    return groups


def derive(conn, path, *, valid_at, as_of):
    """The derived table, from the map alone plus the log at these clocks."""
    map_ = read_map(path)
    view = map_["view"]
    specs = aggregates(view, DERIVED)
    over = sorted({spec["over"] for _, spec in specs})
    dimensions = list(specs[0][1]["by"])

    offered, kept, declared = {}, {}, {}
    for class_name in over:
        offered[class_name], kept[class_name], declared[class_name] = source_rows(
            conn, map_, class_name, valid_at=valid_at, as_of=as_of
        )

    cells = OrderedDict()
    for slot, spec in specs:
        for key, g in group(kept[spec["over"]], spec, declared[spec["over"]]).items():
            cells.setdefault(key, {})[slot.name] = g

    empty = {"total": Decimal(0), "from": [], "silent": []}
    rows = []
    for key in sorted(cells):
        row = dict(zip(dimensions, key))
        for slot, _ in specs:
            row[slot.name] = cells[key].get(slot.name, dict(empty))
        obj = JsonObj(**dict(zip(dimensions, key)),
                      **{s.name: row[s.name]["total"] for s, _ in specs})
        for slot in computed(view, DERIVED):
            try:
                row[slot.name] = generate_slot_value(
                    obj, slot.name, view, class_name=DERIVED,
                    config=Config(use_expressions=True,
                                  use_string_serialization=False),
                )
            except Exception as exc:
                row[slot.name] = f"{type(exc).__name__}: {exc}"
        rows.append(row)

    return {"map": map_, "specs": specs, "dimensions": dimensions,
            "computed": [s.name for s in computed(view, DERIVED)],
            "over": over, "offered": offered, "kept": kept,
            "rows": rows, "valid_at": valid_at, "as_of": as_of}


def render(built):
    headers = (built["dimensions"] + [s.name for s, _ in built["specs"]]
               + built["computed"])
    body = []
    for row in built["rows"]:
        line = [str(row[d]) for d in built["dimensions"]]
        line += [str(row[s.name]["total"]) for s, _ in built["specs"]]
        line += [str(row[c]) for c in built["computed"]]
        body.append(line)

    widths = [max(len(headers[i]), *(len(r[i]) for r in body)) if body
              else len(headers[i]) for i in range(len(headers))]

    def line(cells):
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()

    out = [
        f"{DERIVED}  ({built['map']['version']}, {built['map']['path'].name})",
        f"valid_at   {built['valid_at']}",
        f"as_of      {built['as_of']}",
        "",
        line(headers),
        line(["-" * w for w in widths]),
    ]
    out += [line(r) for r in body]
    out.append("")
    for class_name in built["over"]:
        out.append(
            f"{class_name}: the generator offered "
            f"{len(built['offered'][class_name])} rows, the log states "
            f"{len(built['kept'][class_name])} of them are one"
        )
    for row in built["rows"]:
        key = ", ".join(str(row[d]) for d in built["dimensions"])
        for slot, _ in built["specs"]:
            g = row[slot.name]
            note = f"{len(g['from'])} movement(s)"
            if g["silent"]:
                note += (f", and {len(g['silent'])} that matched but stated no "
                         f"quantity and added nothing: {', '.join(g['silent'])}")
            out.append(f"  ({key}).{slot.name} = {g['total']} from {note}")
    return "\n".join(out) + "\n"


def main():
    dsn = os.environ.get("UNITI_DSN")
    if not dsn or dsn.rsplit("/", 1)[-1] == "uniti":
        print("refusing: set UNITI_DSN to the throwaway database, not the "
              "working log", file=sys.stderr)
        return 2

    print(f"dsn        {dsn}")
    print(f"maps       {MAPS}")
    for slot, spec in aggregates(read_map(MAPS / "v1.yaml")["view"], DERIVED):
        print(f"declared   {slot.name} = {spec}")

    tables = []
    with connect() as conn:
        for as_of in AS_OF:
            version = resolve_version(MAPS, valid_at=VALID_AT, as_of=as_of)
            print(f"\nthe map itself resolves to {version['version']} "
                  f"at as_of {as_of}\n")
            tables.append(derive(conn, version["path"],
                                 valid_at=VALID_AT, as_of=as_of))
            print(render(tables[-1]))

    before, after = tables
    dims, net = before["dimensions"], before["computed"][0]
    over = before["over"][0]

    nets = [{tuple(r[d] for d in dims): r[net] for r in t["rows"]} for t in tables]
    changed = {k: (nets[0][k], nets[1][k]) for k in nets[0]
               if k in nets[1] and nets[0][k] != nets[1][k]}
    appeared = ({r["uri"] for r in after["kept"][over]}
                - {r["uri"] for r in before["kept"][over]})
    quantity = sum(
        (Decimal(r["movement_quantity"]) for r in after["kept"][over]
         if r["uri"] in appeared and r.get("movement_quantity") is not None),
        Decimal(0),
    )

    print("what the two tables say to each other")
    print(f"  {over}s visible at the later as_of and not the earlier: "
          f"{sorted(appeared) or 'none'}")
    print(f"  their quantity, resolved at the later as_of: {quantity}")
    print(f"  pairs in both tables whose {net} differs: "
          f"{ {'/'.join(k): v for k, v in changed.items()} }")
    print(f"  pairs in one table and not the other: "
          f"{sorted(set(nets[0]) ^ set(nets[1])) or 'none'}")

    assert len(appeared) == 1, appeared
    assert len(changed) == 1, changed
    (pair, (was, now)), = changed.items()
    assert abs(was - now) == quantity, (was, now, quantity)
    print(f"  asserted: exactly one movement arrived late, exactly one pair "
          f"moved ({'/'.join(pair)} {net} {was} -> {now}), and "
          f"|{was} - {now}| == {quantity}, that movement's own quantity")
    return 0


if __name__ == "__main__":
    sys.exit(main())

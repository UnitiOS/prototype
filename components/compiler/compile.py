"""compiler — an operational table, from a sealed map and the log.

The map declares rules. This turns one kind of rule into SQL and runs it.

    the map    which class the table is, which columns it has, and for each
               column what derives it: an `aggregate` annotation naming an
               operator, a source class and a grouping, or an
               `equals_expression` over the columns beside it.
    the log    the values, resolved at one pair of clocks by the same rule
               `resolve_single()` uses, written once as a CTE rather than once
               per cell.
    the store  a database of its own. The log is read here and written
               nowhere; the operational store is dropped and rebuilt whole.

Two connections and no join between them: nothing that reads the operational
store can reach an `assertion` row, because it is not in the same database.

**Nothing here knows what the map is about.** It reads four words — `over`,
the operator, `by`, and `equals_expression` — and emits SQL. A column whose
name it recognised would be a defect: point it at another map and another
table comes out.

    a row of the table is one distinct combination of the grouping values,
    from every aggregate on the class taken together. A combination one
    aggregate produces and another does not still stands: the missing side is
    the operator's empty value, which for a sum is nought.

The emitted SQL is the evidence. `--sql` prints it, `--into` writes it beside
the rows, and nothing in it was written by hand: every identifier and every
literal in it came out of the map.

Run:
    compile.py <map>                     every class the map gives an aggregate
    compile.py <map> <CLASS> --sql
    compile.py <map> --valid-at 2026-06-16 --as-of 2026-06-16 --into build/x
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from jsonasobj2 import as_dict, items

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

# The map is read exactly as the generator reads it — same induced slots, same
# rule for which entities are of a class — so the two cannot drift apart.
from generate import MapError, columns, read_map  # noqa: E402
from generate import _grid as grid  # noqa: E402
from generate import _type_slot as type_slot  # noqa: E402
from perform import connect as connect_kernel  # noqa: E402
from seal import URI_PREDICATE  # noqa: E402

OPS_DSN = os.environ.get(
    "UNITI_OPS_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_ops"
)

# A range becomes a column type. A range that is a class or an enum holds a
# name, so it is text: the operational store keeps the URI the log resolved to.
SQL_TYPE = {
    "string": "text",
    "uri": "text",
    "uriorcurie": "text",
    "curie": "text",
    "ncname": "text",
    "date": "date",
    "datetime": "timestamptz",
    "time": "time",
    "integer": "bigint",
    "decimal": "numeric",
    "double": "double precision",
    "float": "double precision",
    "boolean": "boolean",
}

# Which operators an aggregate may name, and what each one is over no rows.
# A group one aggregate makes and another does not is not an absence of an
# answer, it is the operator's empty value, and for a sum that is nought.
EMPTY = {"sum": "0"}

SUMMABLE = {"numeric", "bigint", "double precision"}

# A reference to another column of the same class, inside an equals_expression.
_REF = re.compile(r"\{([^{}]+)\}")

# What is allowed to stand between those references. Arithmetic and nothing
# else: an expression the map can write is an expression this can read whole.
# TODO: LinkML's own equals_expression is a fuller language than this. Widen it
# when a map writes something this refuses, and not before.
_ARITHMETIC = re.compile(r"^[-+*/(). 0-9]*$")


# ---- reading the map ------------------------------------------------------

def _lit(text):
    """A SQL string literal. Everything the map contributes goes through here."""
    return "'" + str(text).replace("'", "''") + "'"


def _ident(name):
    return '"' + str(name).replace('"', '""') + '"'


def _table_name(class_name):
    return "p_" + re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()


def _annotation(slot, name):
    for key, annotation in items(slot.annotations or {}):
        if str(key) == name:
            return as_dict(annotation.value)
    return None


def _sql_type(map_, range_):
    if range_ in map_["view"].all_classes() or range_ in map_["view"].all_enums():
        return "text"
    return SQL_TYPE.get(str(range_), "text")


def _read_aggregate(map_, where, spec):
    """One `aggregate` annotation, checked against the map it names."""
    view = map_["view"]
    named = [key for key in spec if key in EMPTY]
    unknown = set(spec) - set(named) - {"over", "by"}
    if len(named) != 1 or unknown:
        raise MapError(
            f"{where}: an aggregate is `over`, `by` and one operator of "
            f"{sorted(EMPTY)} — this one has {sorted(spec)}"
        )
    operator = named[0]
    over = str(spec.get("over") or "")
    if over not in view.all_classes():
        raise MapError(f"{where}: `over` names {over!r}, which is not a class")

    source = {slot.name: slot for slot in view.class_induced_slots(over)}

    def named_slot(slot_name, role):
        slot = source.get(str(slot_name))
        if slot is None:
            raise MapError(
                f"{where}: `{role}` names {slot_name!r}, which {over} has no slot for"
            )
        if not slot.slot_uri:
            raise MapError(f"{where}: {over}.{slot.name} declares no slot_uri")
        return slot

    measure = named_slot(spec[operator], operator)
    measure_type = _sql_type(map_, measure.range)
    if measure_type not in SUMMABLE:
        raise MapError(
            f"{where}: {operator} is over {measure.name}, whose range "
            f"{measure.range} is {measure_type} and cannot be totalled"
        )

    by = as_dict(spec.get("by") or {})
    if not by:
        raise MapError(f"{where}: an aggregate with no `by` groups nothing")

    return {
        "operator": operator,
        "over": over,
        "measure_uri": measure.slot_uri,
        "measure_type": measure_type,
        "by": {str(key): named_slot(value, "by").slot_uri for key, value in by.items()},
    }


def plan(map_, class_name):
    """What the map says this class's table is: its columns, and each one's rule.

    Every column falls in one of four kinds. `key` is a column an aggregate
    groups by; `aggregate` is one the map annotates; `expression` is one the
    map writes in terms of the others; `unfilled` is a column no rule reaches,
    which is a column of nulls and is reported as one.
    """
    view = map_["view"]
    cols = columns(map_, class_name)
    slots = {slot.name: slot for slot in view.class_induced_slots(class_name)}

    aggregates, expressions = {}, {}
    for col in cols:
        slot = slots[col["name"]]
        annotation = _annotation(slot, "aggregate")
        expression = slot.equals_expression
        where = f"{class_name}.{col['name']}"
        if annotation and expression:
            raise MapError(f"{where} declares an aggregate and an expression both")
        if annotation:
            aggregates[col["name"]] = _read_aggregate(map_, where, annotation)
        elif expression:
            expressions[col["name"]] = str(expression)

    if not aggregates:
        raise MapError(
            f"{class_name} carries no aggregate, so no rule here fills a table for it"
        )

    # TODO: must every aggregate on one class group by the same set? Refusing
    # is the narrow reading and no map has asked for the wide one yet.
    groupings = {tuple(sorted(spec["by"])) for spec in aggregates.values()}
    if len(groupings) > 1:
        raise MapError(
            f"the aggregates on {class_name} group by different sets "
            f"{sorted(groupings)} — a row of one table has one grouping"
        )
    grouped_by = set(next(iter(groupings)))

    names = {col["name"] for col in cols}
    stray = sorted(grouped_by - names)
    if stray:
        raise MapError(f"{class_name} is grouped by {stray}, which it has no slot for")
    derived = sorted(grouped_by & (set(aggregates) | set(expressions)))
    if derived:
        raise MapError(f"{class_name} is grouped by {derived}, which it derives")

    # The grouping in the class's own column order, so the table reads the way
    # the map wrote it rather than the way an annotation happened to be keyed.
    keys = [col["name"] for col in cols if col["name"] in grouped_by]

    planned = []
    for col in cols:
        kind = (
            "key" if col["name"] in keys
            else "aggregate" if col["name"] in aggregates
            else "expression" if col["name"] in expressions
            else "unfilled"
        )
        planned.append({**col, "kind": kind, "type": _sql_type(map_, col["range"])})

    return {
        "class": class_name,
        "table": _table_name(class_name),
        "columns": planned,
        "keys": keys,
        "aggregates": aggregates,
        "expressions": expressions,
        "version": map_["version"],
    }


# ---- emitting the SQL -----------------------------------------------------

_STANDING = """standing AS (
    -- What stands at the two clocks, for every subject and every predicate.
    -- DECISIONS.md, 2026-08-22, written once instead of once per cell.
    SELECT DISTINCT ON (a.subject_id, a.predicate_id)
           a.subject_id, a.predicate_id, a.value_literal, a.value_ref
    FROM assertion a
    WHERE a.valid_from  <= %(valid_at)s
      AND a.recorded_at <= %(as_of)s
      AND num_nonnulls(a.value_literal, a.value_ref) = 1
      AND NOT EXISTS (
          SELECT 1 FROM assertion r
          WHERE r.revokes = a.id AND r.recorded_at <= %(as_of)s)
    ORDER BY a.subject_id, a.predicate_id,
             a.valid_from DESC, a.recorded_at DESC, a.seq DESC
)"""

_REGISTRY = """registry AS (
    -- Every URI the log has registered. Identity does not vary with a clock,
    -- so this one is not resolved at them; DISTINCT ON keeps it one per entity.
    SELECT DISTINCT ON (a.subject_id) a.subject_id AS entity_id,
           a.value_literal AS uri
    FROM assertion a
    WHERE a.predicate_id = (
              SELECT subject_id FROM assertion
              WHERE subject_id = predicate_id AND value_literal = %(uri_predicate)s
              ORDER BY seq LIMIT 1)
      AND a.value_literal IS NOT NULL
    ORDER BY a.subject_id, a.seq
)"""

_STATED = """stated AS (
    -- One standing fact as (subject, slot, value). A value that names another
    -- entity comes back as that entity's URI, so a cell is text either way.
    SELECT s.subject_id,
           p.uri AS slot,
           coalesce(o.uri, s.value_literal) AS value
    FROM standing s
    JOIN registry p ON p.entity_id = s.predicate_id
    LEFT JOIN registry o ON o.entity_id = s.value_ref
)"""


def _source_cte(map_, over, alias):
    """The subjects the log says are of a class, or of one below it."""
    slot = type_slot(map_, over)
    if slot is None or not slot.slot_uri:
        raise MapError(
            f"{over} has no slot carrying designates_type, so nothing in the "
            f"log can say a subject is one and no aggregate can run over it"
        )
    names = ", ".join(_lit(name) for name in map_["view"].class_descendants(over))
    return (
        f"{alias} AS (\n"
        f"    SELECT s.subject_id FROM stated s\n"
        f"    WHERE s.slot = {_lit(slot.slot_uri)}\n"
        f"      AND s.value = ANY (ARRAY[{names}])\n"
        f")"
    )


def _aggregate_cte(spec, column, alias, source_alias, keys, prefix):
    """One aggregate: the source class, grouped the way the map groups it."""
    selects, joins = [], [f"    FROM {source_alias} r"]
    for i, key in enumerate(keys):
        k = f"{prefix}k{i}"
        selects.append(f"           {k}.value AS {_ident(key)}")
        joins.append(
            f"    LEFT JOIN stated {k} ON {k}.subject_id = r.subject_id\n"
            f"                        AND {k}.slot = {_lit(spec['by'][key])}"
        )
    m = f"{prefix}m"
    selects.append(
        f"           {spec['operator']}(({m}.value)::{spec['measure_type']}) "
        f"AS {_ident(column)}"
    )
    joins.append(
        f"    LEFT JOIN stated {m} ON {m}.subject_id = r.subject_id\n"
        f"                        AND {m}.slot = {_lit(spec['measure_uri'])}"
    )
    body = "    SELECT " + ",\n".join(selects).lstrip() + "\n" + "\n".join(joins)
    group = ", ".join(str(i + 1) for i in range(len(keys)))
    return f"{alias} AS (\n{body}\n    GROUP BY {group}\n)"


def _column_sql(plan_, name, aliases, stack=()):
    """The SQL that produces one column, wherever the map puts its rule."""
    col = next(c for c in plan_["columns"] if c["name"] == name)
    if col["kind"] == "key":
        return f"g.{_ident(name)}"
    if col["kind"] == "aggregate":
        empty = EMPTY[plan_["aggregates"][name]["operator"]]
        return f"coalesce({aliases[name]}.{_ident(name)}, {empty})"
    if col["kind"] == "unfilled":
        return "NULL"

    if name in stack:
        raise MapError(
            f"{plan_['class']}.{name} is written in terms of itself, "
            f"through {' -> '.join(stack + (name,))}"
        )
    text = plan_["expressions"][name]
    if not _ARITHMETIC.match(_REF.sub(" ", text)):
        raise MapError(
            f"{plan_['class']}.{name}: {text!r} is more than arithmetic over "
            f"the columns beside it, and that is all an expression may be here"
        )
    known = {c["name"] for c in plan_["columns"]}
    for referenced in _REF.findall(text):
        if referenced.strip() not in known:
            raise MapError(
                f"{plan_['class']}.{name} names {{{referenced}}}, "
                f"which {plan_['class']} has no slot for"
            )
    return "(" + _REF.sub(
        lambda m: _column_sql(plan_, m.group(1).strip(), aliases, stack + (name,)), text
    ) + ")"


def emit(map_, plan_):
    """The DDL that makes the table, and the one SELECT that fills it."""
    table, keys = plan_["table"], plan_["keys"]

    ddl = [
        f"DROP TABLE IF EXISTS {_ident(table)}",
        "CREATE TABLE {} (\n{}\n)".format(
            _ident(table),
            ",\n".join(
                f"    {_ident(c['name'])} {c['type']}" for c in plan_["columns"]
            ),
        ),
    ]

    sources, source_ctes = {}, []
    for spec in plan_["aggregates"].values():
        if spec["over"] not in sources:
            alias = f"source_{len(sources)}"
            sources[spec["over"]] = alias
            source_ctes.append(_source_cte(map_, spec["over"], alias))

    aliases, aggregate_ctes = {}, []
    for i, (column, spec) in enumerate(plan_["aggregates"].items()):
        alias = f"total_{i}"
        aliases[column] = alias
        aggregate_ctes.append(
            _aggregate_cte(spec, column, alias, sources[spec["over"]], keys, f"t{i}_")
        )

    key_list = ", ".join(_ident(k) for k in keys)
    grouping = "grouping AS (\n" + "\n    UNION\n".join(
        f"    SELECT {key_list} FROM {aliases[column]}" for column in plan_["aggregates"]
    ) + "\n)"

    joins = []
    for column, alias in aliases.items():
        on = "\n                       AND ".join(
            f"{alias}.{_ident(k)} IS NOT DISTINCT FROM g.{_ident(k)}" for k in keys
        )
        joins.append(f"LEFT JOIN {alias} ON {on}")

    select = (
        "WITH "
        + ",\n".join([_STANDING, _REGISTRY, _STATED] + source_ctes
                     + aggregate_ctes + [grouping])
        + "\nSELECT "
        + ",\n       ".join(
            f"{_column_sql(plan_, c['name'], aliases)} AS {_ident(c['name'])}"
            for c in plan_["columns"]
        )
        + "\nFROM grouping g\n"
        + "\n".join(joins)
        + "\nORDER BY "
        + ", ".join(str(i + 1) for i in range(len(keys)))
    )
    return ddl, select


# ---- running it -----------------------------------------------------------

def compile_class(kernel, ops, map_, class_name, *, valid_at, as_of):
    """Read the log through the map's rules; drop and rebuild one table."""
    plan_ = plan(map_, class_name)
    ddl, select = emit(map_, plan_)

    with kernel.cursor() as cur:
        cur.execute(select, {"valid_at": valid_at, "as_of": as_of,
                             "uri_predicate": URI_PREDICATE})
        rows = cur.fetchall()

    names = [c["name"] for c in plan_["columns"]]
    insert = "INSERT INTO {} ({}) VALUES ({})".format(
        _ident(plan_["table"]),
        ", ".join(_ident(n) for n in names),
        ", ".join(["%s"] * len(names)),
    )
    with ops.transaction():
        with ops.cursor() as cur:
            for statement in ddl:
                cur.execute(statement)
            if rows:
                cur.executemany(insert, rows)

    with ops.cursor() as cur:
        cur.execute(f"SELECT * FROM {_ident(plan_['table'])}")
        stored = cur.fetchall()

    return {"plan": plan_, "ddl": ddl, "select": select, "rows": stored,
            "valid_at": valid_at, "as_of": as_of}


def render(built):
    plan_ = built["plan"]
    headers = [c["name"] for c in plan_["columns"]]
    body = [["" if cell is None else str(cell) for cell in row]
            for row in built["rows"]]
    out = [
        f"{plan_['table']}  ({plan_['class']}, {plan_['version']})",
        f"valid_at   {built['valid_at']}",
        f"as_of      {built['as_of']}",
        "",
    ]
    out += grid(headers, body)
    kinds = {}
    for col in plan_["columns"]:
        kinds.setdefault(col["kind"], []).append(col["name"])
    out += ["", f"{len(built['rows'])} rows, {len(headers)} columns"]
    for kind in ("key", "aggregate", "expression", "unfilled"):
        if kind in kinds:
            out.append(f"{kind}: {', '.join(kinds[kind])}")
    return "\n".join(out) + "\n"


def sql_text(built):
    plan_ = built["plan"]
    return "\n".join(
        [
            f"-- {plan_['table']}, compiled from {plan_['class']} "
            f"({plan_['version']})",
            f"-- valid_at {built['valid_at']}   as_of {built['as_of']}",
            "-- Emitted, not written: every name and every literal below came "
            "out of the map.",
            "",
        ]
        + [statement + ";" for statement in built["ddl"]]
        + ["", built["select"] + ";", ""]
    )


def _aggregate_classes(map_):
    """Every class the map gives at least one aggregate column."""
    view = map_["view"]
    out = []
    for class_name in view.all_classes():
        for slot in view.class_induced_slots(class_name):
            if _annotation(slot, "aggregate"):
                out.append(str(class_name))
                break
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile a sealed map's rules into the operational store.")
    parser.add_argument("map", help="a sealed version file")
    parser.add_argument("klass", nargs="*", metavar="CLASS",
                        help="default: every class the map gives an aggregate")
    parser.add_argument("--valid-at", default=None)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--sql", action="store_true", help="print the emitted SQL")
    parser.add_argument("--into", default=None, metavar="DIR",
                        help="write the SQL and the rows here, one pair per table")

    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc).isoformat()
    valid_at, as_of = args.valid_at or now, args.as_of or now

    try:
        map_ = read_map(args.map)
        classes = args.klass or _aggregate_classes(map_)
        if not classes:
            raise MapError(f"{args.map} declares no aggregate anywhere")

        with connect_kernel() as kernel, psycopg.connect(OPS_DSN) as ops:
            for class_name in classes:
                built = compile_class(kernel, ops, map_, class_name,
                                      valid_at=valid_at, as_of=as_of)
                if args.sql:
                    sys.stdout.write(sql_text(built))
                sys.stdout.write(render(built))
                sys.stdout.write("\n")
                if args.into:
                    into = Path(args.into)
                    into.mkdir(parents=True, exist_ok=True)
                    table = built["plan"]["table"]
                    (into / f"{table}.sql").write_text(
                        sql_text(built), encoding="utf-8", newline="\n")
                    (into / f"{table}.txt").write_text(
                        render(built), encoding="utf-8", newline="\n")
                    print(f"wrote {into / table}.sql and .txt")
        return 0
    except MapError as exc:
        print(f"not compiled: {exc}", file=sys.stderr)
        return 2
    except psycopg.OperationalError as exc:
        print(f"not compiled: no store at {OPS_DSN} — {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())

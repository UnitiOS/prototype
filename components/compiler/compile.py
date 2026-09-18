"""compiler — an operational table, from a sealed map and the log.

The map declares rules. This turns one kind of rule into SQL and runs it.

    the map    which class the table is, which columns it has, and for each
               column what derives it: an `aggregate` annotation naming an
               operator, a source class and a grouping, an `equals_expression`
               over the columns beside it, or a `parameter` annotation naming a
               key column and one slot to read off the entity that key names.
    the log    the values, resolved at one pair of clocks by the same rule
               `resolve_single()` uses, written once as a CTE rather than once
               per cell.
    the store  a database of its own. The log is read here and written
               nowhere; the operational store is dropped and rebuilt whole.

Two connections and no join between them: nothing that reads the operational
store can reach an `assertion` row, because it is not in the same database.

**Nothing here knows what the map is about.** It reads eight words — `over`,
the operator, `by`, `where` and its `is_a`, `convert`, `equals_expression`,
`parameter` and its `of` and `slot` — and emits SQL. A column whose name it
recognised would be a defect: point it at another map and another table comes out.

A `parameter` column is the fourth kind: not computed from the rows at all, but
one fact the log holds about the entity a key column names — a threshold
somebody set, a rate somebody agreed. It carries no clock machinery of its own,
because the fact is read out of the same `stated` CTE every other cell is read
from, already resolved at both clocks. Where nothing is stated the cell is
NULL, never a nought: an absent rule is not a rule that says zero.

    a row of the table is one distinct combination of the grouping values,
    from every aggregate on the class taken together. A combination one
    aggregate produces and another does not still stands: the missing side is
    the operator's empty value, which for a sum is nought.

A table has one of two shapes and the map decides which. A class the map gives
an aggregate is the grouping above. A class it gives none, but that the log can
say an entity is one of, is a **list of its entities**: one row per entity, one
column per slot, each cell the value standing at the two clocks, and a first
column carrying the URI the log registered it under. That second shape is what
puts master data in the operational store, and it is why a form can offer the
entities of a class without reading the log.

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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

# The map is read exactly as the generator reads it — same induced slots, same
# rule for which entities are of a class — so the two cannot drift apart.
from components.modules.store import Store  # noqa: E402
from components.refusal import Refusal, Repair  # noqa: E402
from generate import IDENTITY_COLUMN, MapError, columns, read_map, table_name  # noqa: E402
from generate import _carriers as carriers  # noqa: E402
from generate import _grid as grid  # noqa: E402
from generate import _type_slot as type_slot  # noqa: E402
from perform import connect as connect_kernel  # noqa: E402
from seal import URI_PREDICATE  # noqa: E402

OPS_DSN = os.environ.get(
    "UNITI_OPS_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_ops"
)


class CompileError(MapError):
    """A rule this cannot execute. Nothing has been written.

    The same refusal as the generator's, saying who is speaking. Which gate
    refused decides who can answer it: a map the generator cannot read is a
    file problem, and a rule the compiler cannot execute is a modelling one.
    """

    gate = "the compiler"


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


def _annotation(slot, name):
    for key, annotation in items(slot.annotations or {}):
        if str(key) == name:
            return as_dict(annotation.value)
    return None


def _sql_type(map_, range_):
    if range_ in map_["view"].all_classes() or range_ in map_["view"].all_enums():
        return "text"
    return SQL_TYPE.get(str(range_), "text")


def _any_of(uris):
    """SQL for "this slot is one of these predicates"."""
    if len(uris) == 1:
        return f"= {_lit(uris[0])}"
    return "= ANY (ARRAY[" + ", ".join(_lit(uri) for uri in uris) + "])"


def _covered(view, class_name):
    """The classes an aggregate over `class_name` actually reads.

    Its descendants, minus the abstract ones: a role is never something an
    entity *is*, only something a class promises. Nothing in the log ever
    states `entity_class: Flow`, so listing it would widen the scan for no row.
    """
    return [str(name) for name in view.class_descendants(class_name)
            if not view.get_class(name).abstract]


def _fillers(view, class_name, binding):
    """The class's own slots that fill one binding: those descending from it.

    The same walk `seal` makes when it checks the promise was kept. It is
    repeated here rather than imported because the compiler must work on a map
    whoever sealed it is not present for, and because reading the map is the
    only thing that may decide what a rule means.
    """
    below = set(view.slot_descendants(binding)) - {binding}
    return [slot for slot in view.class_induced_slots(class_name)
            if str(slot.name) in below and not slot.abstract]


def _sources(map_):
    """What an aggregate could run over, as (classes, roles).

    Both halves are answers, and they are not the same answer. A class is what
    an entity is; a role is what a class promised, and a rule written against
    one reaches whoever kept the promise — which is the difference between a
    rule that survives a module being replaced and one that does not.

    Only classes carrying `designates_type` are here: without it nothing in the
    log can say a subject is one, so there would be no rows. And only roles
    something concrete descends from, because a role nothing fills has no rows
    either.
    """
    view = map_["view"]
    classes, roles = [], []
    for name in sorted(str(n) for n in view.all_classes()):
        if type_slot(map_, name) is None:
            continue
        if not view.get_class(name).abstract:
            classes.append(name)
        elif _covered(view, name):
            roles.append(name)
    return classes, roles


def _bound(map_, where, over, slot_name, role):
    """Every predicate `slot_name` stands for, across the classes `over` covers.

    A concrete slot names one predicate and this is the whole of it. A binding
    names a hole, and each class filling the role fills it with a predicate of
    its own — so a rule written against the binding reads all of them at once.
    That is safe because a subject is of exactly one class and states only its
    own class's predicates: the union never double-counts a row.

    This is the one function that makes an application substitutable. Without
    it a rule can only name a slot some particular module owns, and moving a
    pin breaks every rule that crossed the boundary.
    """
    view = map_["view"]
    slot_name = str(slot_name)
    declared = {str(slot.name): slot for slot in view.class_induced_slots(over)}
    slot = declared.get(slot_name)
    if slot is None:
        raise CompileError(
            "no_such_slot",
            where=where,
            expected=f"`{role}` to name a slot of {over}",
            got=f"{slot_name!r}",
            repairs=[Repair(f"name a slot {over} has", options=sorted(declared))],
        )
    if not slot.abstract:
        if not slot.slot_uri:
            raise CompileError(
                "slot_without_uri",
                where=f"{where}: {over}.{slot_name}",
                expected="a `slot_uri`, which is the predicate this reads",
                got="none",
                repairs=[Repair(f"declare a slot_uri on {slot_name} and seal again")],
            )
        return [slot]

    found = []
    for class_name in _covered(view, over):
        filled = _fillers(view, class_name, slot_name)
        if len(filled) > 1:
            raise CompileError(
                "binding_ambiguous",
                where=f"{where}: {class_name}.{slot_name}",
                expected=f"one slot filling '{slot_name}'",
                got=f"{len(filled)} — {', '.join(str(s.name) for s in filled)}",
                repairs=[Repair(
                    f"keep `is_a: {slot_name}` on one of them and take it off "
                    f"the rest, in whichever module declares {class_name}",
                    options=[str(s.name) for s in filled],
                )],
            )
        found += filled
    if not found:
        covered = _covered(view, over)
        raise CompileError(
            "binding_unfilled",
            where=where,
            expected=f"some class below {over} to fill the binding {slot_name!r}",
            got=f"none: {', '.join(covered) or 'nothing'} below it",
            repairs=[
                Repair(f"declare a slot with `is_a: {slot_name}` on one of these",
                       options=covered),
                Repair(f"or write the rule against a slot they do have",
                       options=sorted(declared)),
            ],
        )
    for slot in found:
        if not slot.slot_uri:
            raise CompileError(
                "slot_without_uri",
                where=f"{where}: {slot.name}",
                expected="a `slot_uri`, which is the predicate this reads",
                got="none",
                repairs=[Repair(f"declare a slot_uri on {slot.name} and seal again")],
            )
    return found


def _one_type(map_, where, slots, role):
    """The SQL type these slots share, or a refusal naming the disagreement."""
    types = {_sql_type(map_, slot.range) for slot in slots}
    if len(types) > 1:
        detail = ", ".join(f"{s.name} is {_sql_type(map_, s.range)}" for s in slots)
        raise CompileError(
            "types_disagree",
            where=where,
            expected=f"one type across the slots filling `{role}`, because one "
                     f"column has one type",
            got=detail,
            repairs=[Repair(
                "make the ranges agree in the modules that declare them, or "
                "give each its own column",
                options=[f"{s.name}: {s.range}" for s in slots],
            )],
        )
    return types.pop()


def _read_aggregate(map_, where, spec):
    """One `aggregate` annotation, checked against the map it names."""
    view = map_["view"]
    named = [key for key in spec if key in EMPTY]
    unknown = set(spec) - set(named) - {"over", "by", "where", "convert"}
    if len(named) != 1 or unknown:
        raise CompileError(
            "aggregate_keys",
            where=where,
            expected=f"`over`, `by`, one operator of {sorted(EMPTY)}, and "
                     f"optionally `where` and `convert`",
            got=", ".join(sorted(str(k) for k in spec)) or "nothing",
            repairs=[Repair("use these keys and no others",
                            options=["over", "by", "where", "convert"] + sorted(EMPTY))],
        )
    operator = named[0]
    over = str(spec.get("over") or "")
    if over not in view.all_classes():
        raise CompileError(
            "not_a_class",
            where=where,
            expected="`over` to name a class this application can see",
            got=f"{over!r}",
            repairs=[
                Repair("name a class the log can say an entity is",
                       options=_sources(map_)[0]),
                Repair("or name a role, and the rule reaches whichever class "
                       "fills it — which is what survives the module under it "
                       "being replaced",
                       options=_sources(map_)[1]),
            ],
        )

    def named_slot(slot_name, role):
        """One slot of the source class — the first of whatever fills the name."""
        return _bound(map_, where, over, slot_name, role)[0]

    def uris(slot_name, role):
        """Every predicate the name stands for, across the classes `over` covers."""
        return [str(slot.slot_uri)
                for slot in _bound(map_, where, over, slot_name, role)]

    measures = _bound(map_, where, over, spec[operator], operator)
    measure_type = _one_type(map_, where, measures, operator)
    if measure_type not in SUMMABLE:
        raise CompileError(
            "not_summable",
            where=where,
            expected=f"`{operator}` over something numeric",
            got=f"{', '.join(str(m.name) for m in measures)}, which is {measure_type}",
            repairs=[Repair(
                f"total a slot whose range is one of these",
                options=sorted(name for name, sql in SQL_TYPE.items() if sql in SUMMABLE),
            )],
        )

    by = as_dict(spec.get("by") or {})
    if not by:
        raise CompileError(
            "no_grouping",
            where=where,
            expected="`by`, naming what each row of the table stands for",
            got="none, which groups nothing",
            repairs=[Repair(
                "name one column of this class and the slot of the source that "
                "fills it, as `by: {<column>: <slot>}`",
                options=[str(slot.name) for slot in view.class_induced_slots(over)
                         if not slot.abstract],
            )],
        )

    where_block = as_dict(spec.get("where") or {})
    parsed_where = []
    for slot_name, cond in where_block.items():
        cond_dict = as_dict(cond) if cond else {}
        if set(cond_dict) != {"is_a"}:
            raise CompileError(
                "where_not_is_a",
                where=f"{where}: where.{slot_name}",
                expected="`is_a`, naming the class the value must be",
                got=", ".join(sorted(str(k) for k in cond_dict)) or "nothing",
                repairs=[Repair(
                    "a `where` narrows by what something is, and that is all it "
                    "does here. Anything else is arithmetic in a column of its own",
                    options=["is_a"],
                )],
            )
        target_class = str(cond_dict["is_a"])
        if target_class not in view.all_classes():
            raise CompileError(
                "not_a_class",
                where=f"{where}: where.{slot_name}",
                expected="`is_a` to name a class this application can see",
                got=f"{target_class!r}",
                repairs=[Repair("name a class",
                                options=sorted(str(n) for n in view.all_classes()))],
            )
        t_slot = type_slot(map_, target_class)
        if t_slot is None or not t_slot.slot_uri:
            raise CompileError(
                "no_type_slot",
                where=f"{where}: where.{slot_name}",
                expected=f"{target_class} to carry a `designates_type` slot, so "
                         f"the log can say a subject is one",
                got="none",
                repairs=[Repair("narrow by a class that carries one",
                                options=carriers(map_))],
            )
        parsed_where.append({
            "slot_name": str(slot_name),
            "slot_uris": uris(slot_name, "where"),
            "type_slot_uri": t_slot.slot_uri,
            "descendants": _covered(view, target_class),
        })

    convert_block = dict(as_dict(spec.get("convert") or {}))
    parsed_convert = None
    if convert_block:
        # In YAML 1.1, unquoted `on:` parses as boolean True.
        if True in convert_block:
            convert_block["on"] = convert_block.pop(True)
        elif "True" in convert_block:
            convert_block["on"] = convert_block.pop("True")
        expected = {"using", "on", "factor"}
        if set(convert_block) != expected:
            raise CompileError(
                "convert_keys",
                where=f"{where}: convert",
                expected="`using`, `on` and `factor`",
                got=", ".join(sorted(str(k) for k in convert_block)) or "nothing",
                repairs=[Repair(
                    "use these three keys. An unquoted `on:` is boolean True in "
                    "YAML 1.1 and is read here as if it were the word",
                    options=sorted(expected),
                )],
            )
        using_class = str(convert_block["using"])
        if using_class not in view.all_classes():
            raise CompileError(
                "not_a_class",
                where=f"{where}: convert.using",
                expected="a class this application can see",
                got=f"{using_class!r}",
                repairs=[Repair("name the class that holds the conversion",
                                options=sorted(str(n) for n in view.all_classes()))],
            )
        using_slots = {slot.name: slot for slot in view.class_induced_slots(using_class)}

        factor_name = str(convert_block["factor"])
        factor_slot = using_slots.get(factor_name)
        if factor_slot is None:
            raise CompileError(
                "no_such_slot",
                where=f"{where}: convert.factor",
                expected=f"a slot of {using_class}",
                got=f"{factor_name!r}",
                repairs=[Repair(f"name a slot {using_class} has",
                                options=sorted(str(n) for n in using_slots))],
            )
        factor_type = _sql_type(map_, factor_slot.range)
        if factor_type not in SUMMABLE:
            raise CompileError(
                "not_summable",
                where=f"{where}: convert.factor",
                expected="a factor something numeric can be multiplied by",
                got=f"{factor_name}, whose range {factor_slot.range} is {factor_type}",
                repairs=[Repair(
                    f"name a slot of {using_class} with a numeric range",
                    options=sorted(str(s.name) for s in using_slots.values()
                                   if _sql_type(map_, s.range) in SUMMABLE),
                )],
            )

        t_slot = type_slot(map_, using_class)
        if t_slot is None or not t_slot.slot_uri:
            raise CompileError(
                "no_type_slot",
                where=f"{where}: convert.using",
                expected=f"{using_class} to carry a `designates_type` slot, so "
                         f"the log can say a subject is one",
                got="none",
                repairs=[Repair("convert using a class that carries one",
                                options=carriers(map_))],
            )

        on_block = as_dict(convert_block["on"])
        if not on_block:
            raise CompileError(
                "convert_on_empty",
                where=f"{where}: convert.on",
                expected=f"at least one pair matching a slot of {using_class} to "
                         f"a slot of the source",
                got="nothing",
                repairs=[Repair(f"map one slot of {using_class} onto the source "
                                f"slot it must equal",
                                options=sorted(str(n) for n in using_slots))],
            )

        parsed_on = []
        for conv_slot_name, src_slot_name in on_block.items():
            c_slot = using_slots.get(str(conv_slot_name))
            if c_slot is None:
                raise CompileError(
                    "no_such_slot",
                    where=f"{where}: convert.on",
                    expected=f"a slot of {using_class}",
                    got=f"{conv_slot_name!r}",
                    repairs=[Repair(f"name a slot {using_class} has",
                                    options=sorted(str(n) for n in using_slots))],
                )
            if not c_slot.slot_uri:
                raise CompileError(
                    "slot_without_uri",
                    where=f"{where}: {using_class}.{conv_slot_name}",
                    expected="a `slot_uri`, which is the predicate this reads",
                    got="none",
                    repairs=[Repair(f"declare a slot_uri on {conv_slot_name} and "
                                    f"seal again")],
                )
            parsed_on.append({
                "conv_slot_uri": c_slot.slot_uri,
                "source_slot_uris": uris(src_slot_name, "convert.on"),
            })

        parsed_convert = {
            "using": using_class,
            "type_slot_uri": t_slot.slot_uri,
            "descendants": _covered(view, using_class),
            "factor_slot_uri": factor_slot.slot_uri,
            "on": parsed_on,
        }

    return {
        "operator": operator,
        "over": over,
        # What the rule was written against, and what it actually reads. When
        # `over` is a role the two differ, and the difference is the whole
        # point: one rule, every class that kept the promise.
        "covers": _covered(view, over),
        # What the map wrote, and what it resolved to. When the map names a
        # binding the two differ, and a reader wants to see both: the rule as
        # written, and the predicates it actually reached.
        "measure": str(spec[operator]),
        "measure_slots": [str(m.name) for m in measures],
        "measure_uris": [str(m.slot_uri) for m in measures],
        "measure_type": measure_type,
        "by": {str(key): uris(value, "by") for key, value in by.items()},
        "by_names": {str(key): str(value) for key, value in by.items()},
        "where": parsed_where,
        "convert": parsed_convert,
    }


def _read_parameter(map_, where, spec, keys, cols):
    """One `parameter` annotation: a fact the log holds about a key's entity.

    `of` names one of this table's key columns and `slot` names a slot of
    whatever that column ranges over, or of a class below it — the same
    downward walk `_source_cte` does, because the log classifies an entity as
    the narrowest thing it is and a key may name any of them.
    """
    view = map_["view"]
    if set(spec) != {"of", "slot"}:
        raise CompileError(
            "parameter_keys",
            where=where,
            expected="`of` and `slot`",
            got=", ".join(sorted(str(k) for k in spec)) or "nothing",
            repairs=[Repair("name the key column to read off, and the slot to "
                            "read", options=["of", "slot"])],
        )
    of = str(spec["of"])
    if of not in keys:
        raise CompileError(
            "not_a_key_column",
            where=where,
            expected="`of` to name one of this table's key columns",
            got=f"{of!r}",
            repairs=[Repair("a parameter is read off a key, because a key is "
                            "what a row stands for", options=keys)],
        )
    range_ = next(col["range"] for col in cols if col["name"] == of)
    if range_ not in view.all_classes():
        raise CompileError(
            "key_range_not_a_class",
            where=where,
            expected=f"a key whose value names an entity to read a fact off",
            got=f"{of!r}, whose range {range_} is not a class",
            repairs=[Repair("read off a key that ranges over a class",
                            options=[col["name"] for col in cols
                                     if col["name"] in keys
                                     and col["range"] in view.all_classes()])],
        )
    wanted = str(spec["slot"])
    found = []
    for class_name in _covered(view, range_):
        declared = {str(slot.name): slot
                    for slot in view.class_induced_slots(class_name)}
        slot = declared.get(wanted)
        if slot is None:
            continue
        if slot.abstract:
            # The key's class fills the binding with a slot of its own, and
            # which one that is may differ from class to class below the range.
            filled = _fillers(view, class_name, wanted)
            if len(filled) > 1:
                raise CompileError(
                    "binding_ambiguous",
                    where=f"{where}: {class_name}.{wanted}",
                    expected=f"one slot filling '{wanted}'",
                    got=f"{len(filled)} — {', '.join(str(s.name) for s in filled)}",
                    repairs=[Repair(
                        f"keep `is_a: {wanted}` on one of them and take it off "
                        f"the rest, in whichever module declares {class_name}",
                        options=[str(s.name) for s in filled],
                    )],
                )
            slot = filled[0] if filled else None
        if slot is None:
            continue
        if not slot.slot_uri:
            raise CompileError(
                "slot_without_uri",
                where=f"{where}: {class_name}.{slot.name}",
                expected="a `slot_uri`, which is the predicate this reads",
                got="none",
                repairs=[Repair(f"declare a slot_uri on {slot.name} and seal again")],
            )
        if str(slot.slot_uri) not in found:
            found.append(str(slot.slot_uri))
    if not found:
        below = _covered(view, range_)
        raise CompileError(
            "slot_not_below",
            where=where,
            expected=f"`slot` to name something {range_}, or a class below it, has",
            got=f"{wanted!r}",
            repairs=[Repair(
                f"name a slot one of {', '.join(below) or range_} declares",
                options=sorted({str(slot.name) for class_name in below
                                for slot in view.class_induced_slots(class_name)
                                if not slot.abstract}),
            )],
        )
    return {"of": of, "slot": wanted, "slot_uris": found}


def plan(map_, class_name):
    """What the map says this class's table is: its columns, and each one's rule.

    Every column falls in one of five kinds. `key` is a column an aggregate
    groups by; `aggregate` is one the map annotates; `parameter` is one the map
    reads off the entity a key names; `expression` is one the map writes in
    terms of the others; `unfilled` is a column no rule reaches, which is a
    column of nulls and is reported as one.
    """
    view = map_["view"]
    cols = columns(map_, class_name)
    slots = {slot.name: slot for slot in view.class_induced_slots(class_name)}

    aggregates, expressions, stated = {}, {}, {}
    for col in cols:
        slot = slots[col["name"]]
        annotation = _annotation(slot, "aggregate")
        parameter = _annotation(slot, "parameter")
        expression = slot.equals_expression
        where = f"{class_name}.{col['name']}"
        declared = sum(1 for rule in (annotation, parameter, expression) if rule)
        if declared > 1:
            raise CompileError(
                "two_rules_on_a_column",
                where=where,
                expected="one rule, because a column is filled once",
                got=", ".join(kind for kind, rule in
                              (("aggregate", annotation), ("parameter", parameter),
                               ("equals_expression", expression)) if rule),
                repairs=[Repair("keep one and move the other to a column of its own",
                                options=["aggregate", "parameter", "equals_expression"])],
            )
        if annotation:
            aggregates[col["name"]] = _read_aggregate(map_, where, annotation)
        elif parameter:
            stated[col["name"]] = parameter
        elif expression:
            expressions[col["name"]] = str(expression)

    if not aggregates:
        raise CompileError(
            "no_aggregate",
            where=class_name,
            expected="at least one column carrying an `aggregate`",
            got="none, so no rule fills a table for this class",
            repairs=[Repair(
                f"annotate one slot of {class_name} with an aggregate, or read "
                f"it as a list of its own entities instead",
                options=[col["name"] for col in cols],
            )],
        )

    # TODO: must every aggregate on one class group by the same set? Refusing
    # is the narrow reading and no map has asked for the wide one yet.
    groupings = {tuple(sorted(spec["by"])) for spec in aggregates.values()}
    if len(groupings) > 1:
        raise CompileError(
            "groupings_disagree",
            where=class_name,
            expected="one grouping, because a row of one table stands for one thing",
            got=" and ".join("(" + ", ".join(g) + ")" for g in sorted(groupings)),
            repairs=[Repair(
                "group every aggregate on this class the same way, or split the "
                "odd one into a table of its own",
                options=sorted(aggregates),
            )],
        )
    grouped_by = set(next(iter(groupings)))

    names = {col["name"] for col in cols}
    stray = sorted(grouped_by - names)
    if stray:
        raise CompileError(
            "grouped_by_unknown",
            where=class_name,
            expected=f"`by` to name columns {class_name} has",
            got=", ".join(stray),
            repairs=[Repair("group by a column of this class", options=sorted(names))],
        )
    derived = sorted(
        grouped_by & (set(aggregates) | set(expressions) | set(stated)))
    if derived:
        raise CompileError(
            "grouped_by_derived",
            where=class_name,
            expected="a grouping of columns nothing derives",
            got=", ".join(derived) + ", which this class derives",
            repairs=[Repair(
                "group by a column the source states, not one computed from it",
                options=sorted(names - set(aggregates) - set(expressions) - set(stated)),
            )],
        )

    # The grouping in the class's own column order, so the table reads the way
    # the map wrote it rather than the way an annotation happened to be keyed.
    keys = [col["name"] for col in cols if col["name"] in grouped_by]

    parameters = {
        name: _read_parameter(map_, f"{class_name}.{name}", spec, keys, cols)
        for name, spec in stated.items()
    }

    planned = []
    for col in cols:
        kind = (
            "key" if col["name"] in keys
            else "aggregate" if col["name"] in aggregates
            else "parameter" if col["name"] in parameters
            else "expression" if col["name"] in expressions
            else "unfilled"
        )
        planned.append({**col, "kind": kind, "type": _sql_type(map_, col["range"])})

    return {
        "shape": "grouped",
        "class": class_name,
        "table": table_name(class_name),
        "columns": planned,
        "keys": keys,
        "aggregates": aggregates,
        "parameters": parameters,
        "expressions": expressions,
        "version": map_["version"],
    }


def plan_entities(map_, class_name):
    """What a table of one class's entities is, for a class no rule derives.

    The other plan is a grouping: rows are combinations of values, and which
    combinations exist is decided by the rows underneath them. This one is a
    list — one row per entity the log says is of this class or of one below it,
    one column per slot the class induces, and each cell the value standing at
    the two clocks.

    It exists so that a class a rule *reads* has a table too. A field over a
    class range has to offer the entities of that class, and until every such
    class was in the store the only place to read them was the log, which is
    the one read path a form may not have.

    The first column is the entity's URI, under a name the map does not supply
    and cannot: a value naming an entity is written as its URI everywhere else
    in the store, and a row nothing could name could not be pointed at. A class
    that declares a slot of that name is refused rather than shadowed.
    """
    if type_slot(map_, class_name) is None:
        raise CompileError(
            "no_type_slot",
            where=class_name,
            expected="one slot carrying `designates_type: true`",
            got="none, so nothing in the log can say an entity is one",
            repairs=[Repair(
                f"put {class_name} below a class that carries one, or give this "
                f"class an aggregate so its table is a grouping instead",
                options=carriers(map_),
            )],
        )
    cols = columns(map_, class_name)
    if any(col["name"] == IDENTITY_COLUMN for col in cols):
        raise CompileError(
            "identity_column_taken",
            where=f"{class_name}.{IDENTITY_COLUMN}",
            expected=f"no slot named {IDENTITY_COLUMN!r}",
            got="one, and that is the column a projection carries its subject's URI in",
            repairs=[Repair(f"rename the slot; {IDENTITY_COLUMN} is the "
                            f"compiler's, and a row nothing could name could "
                            f"not be pointed at")],
        )

    planned = [{
        "name": IDENTITY_COLUMN, "uri": None, "range": "string",
        "required": True, "multivalued": False, "ref": False,
        "description": "The URI the log registered this entity under.",
        "kind": "identity", "type": "text",
    }]
    planned += [
        {**col, "kind": "stated", "type": _sql_type(map_, col["range"])}
        for col in cols
    ]

    return {
        "shape": "entities",
        "class": class_name,
        "table": table_name(class_name),
        "columns": planned,
        "keys": [],
        "aggregates": {},
        "parameters": {},
        "expressions": {},
        "version": map_["version"],
    }


def plan_for(map_, class_name):
    """Which of the two shapes this class's table is, read off the map.

    A class the map gives an aggregate is a grouping; anything else the log can
    say an entity is, is a list of them. Nothing else decides it.
    """
    if class_name not in map_["view"].all_classes():
        raise CompileError(
            "no_such_class",
            where=map_["path"].name,
            expected="a class this map declares",
            got=f"{class_name!r}",
            repairs=[Repair("name a class the map can see",
                            options=sorted(str(name) for name
                                           in map_["view"].all_classes()))],
        )
    for slot in map_["view"].class_induced_slots(class_name):
        if _annotation(slot, "aggregate"):
            return plan(map_, class_name)
    return plan_entities(map_, class_name)


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
        raise CompileError(
            "no_type_slot",
            where=over,
            expected="one slot carrying `designates_type: true`",
            got="none, so nothing in the log can say a subject is one",
            repairs=[Repair(f"run the aggregate over a class that carries one",
                            options=carriers(map_))],
        )
    covered = _covered(map_["view"], over)
    if not covered:
        raise CompileError(
            "role_has_no_rows",
            where=over,
            expected=f"at least one class below {over} that an entity can be",
            got="none: everything below it is abstract",
            repairs=[Repair(
                f"pin a module whose class mixes in {over}. A role is what "
                f"somebody promises, never what something is",
                options=[str(name) for name in map_["view"].all_classes()
                         if not map_["view"].get_class(name).abstract],
            )],
        )
    names = ", ".join(_lit(name) for name in covered)
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
            f"                        AND {k}.slot {_any_of(spec['by'][key])}"
        )
    for j, w in enumerate(spec.get("where") or []):
        w_val = f"{prefix}w{j}_v"
        w_reg = f"{prefix}w{j}_r"
        w_cls = f"{prefix}w{j}_c"
        descendants = ", ".join(_lit(name) for name in w["descendants"])
        joins.append(
            f"    JOIN stated {w_val} ON {w_val}.subject_id = r.subject_id\n"
            f"                       AND {w_val}.slot {_any_of(w['slot_uris'])}\n"
            f"    JOIN registry {w_reg} ON {w_reg}.uri = {w_val}.value\n"
            f"    JOIN stated {w_cls} ON {w_cls}.subject_id = {w_reg}.entity_id\n"
            f"                       AND {w_cls}.slot = {_lit(w['type_slot_uri'])}\n"
            f"                       AND {w_cls}.value = ANY (ARRAY[{descendants}])"
        )
    if spec.get("convert"):
        cv = spec["convert"]
        c_descendants = ", ".join(_lit(name) for name in cv["descendants"])
        sub_selects = ["cv_c.subject_id"]
        sub_joins = []
        on_clauses = []
        for c_idx, on_item in enumerate(cv["on"]):
            c_alias = f"cv_{c_idx}"
            s_alias = f"{prefix}cv_s{c_idx}"
            joins.append(
                f"    LEFT JOIN stated {s_alias} ON {s_alias}.subject_id = r.subject_id\n"
                f"                                AND {s_alias}.slot {_any_of(on_item['source_slot_uris'])}"
            )
            sub_selects.append(f"{c_alias}.value AS match_{c_idx}")
            sub_joins.append(
                f"        JOIN stated {c_alias} ON {c_alias}.subject_id = cv_c.subject_id\n"
                f"                             AND {c_alias}.slot = {_lit(on_item['conv_slot_uri'])}"
            )
            on_clauses.append(f"{prefix}cv.match_{c_idx} = {s_alias}.value")

        f_alias = f"{prefix}cv_f"
        sub_selects.append(f"({f_alias}.value)::numeric AS factor")
        sub_joins.append(
            f"        JOIN stated {f_alias} ON {f_alias}.subject_id = cv_c.subject_id\n"
            f"                               AND {f_alias}.slot = {_lit(cv['factor_slot_uri'])}"
        )

        sub_query = (
            f"    LEFT JOIN (\n"
            f"        SELECT " + ", ".join(sub_selects) + "\n"
            f"        FROM stated cv_c\n"
            + "\n".join(sub_joins) + "\n"
            f"        WHERE cv_c.slot = {_lit(cv['type_slot_uri'])}\n"
            f"          AND cv_c.value = ANY (ARRAY[{c_descendants}])\n"
            f"    ) {prefix}cv ON " + "\n                AND ".join(on_clauses)
        )
        joins.append(sub_query)
        measure_expr = f"(({prefix}m.value)::{spec['measure_type']} * coalesce({prefix}cv.factor, 1))"
    else:
        measure_expr = f"(({prefix}m.value)::{spec['measure_type']})"

    m = f"{prefix}m"
    selects.append(
        f"           {spec['operator']}({measure_expr}) "
        f"AS {_ident(column)}"
    )
    joins.append(
        f"    LEFT JOIN stated {m} ON {m}.subject_id = r.subject_id\n"
        f"                        AND {m}.slot {_any_of(spec['measure_uris'])}"
    )
    body = "    SELECT " + ",\n".join(selects).lstrip() + "\n" + "\n".join(joins)
    group = ", ".join(str(i + 1) for i in range(len(keys)))
    return f"{alias} AS (\n{body}\n    GROUP BY {group}\n)"


def _parameter_cte(spec, alias):
    """One parameter: what the log says under one slot, per entity, by URI.

    It reads `stated`, so it is resolved at both clocks already and the value
    that comes back is the one standing then. An entity the log says nothing
    about under this slot is absent here, and the LEFT JOIN then leaves the
    cell NULL — which is the whole difference between a rule nobody wrote and
    a rule that says nought.
    """
    return (
        f"{alias} AS (\n"
        f"    SELECT e.uri AS key_value, s.value AS value\n"
        f"    FROM registry e\n"
        f"    JOIN stated s ON s.subject_id = e.entity_id\n"
        f"                 AND s.slot {_any_of(spec['slot_uris'])}\n"
        f")"
    )


def _column_sql(plan_, name, aliases, stack=()):
    """The SQL that produces one column, wherever the map puts its rule."""
    col = next(c for c in plan_["columns"] if c["name"] == name)
    if col["kind"] == "key":
        return f"g.{_ident(name)}"
    if col["kind"] == "aggregate":
        empty = EMPTY[plan_["aggregates"][name]["operator"]]
        return f"coalesce({aliases[name]}.{_ident(name)}, {empty})"
    if col["kind"] == "parameter":
        return f"({aliases[name]}.value)::{col['type']}"
    if col["kind"] == "unfilled":
        return "NULL"

    if name in stack:
        raise CompileError(
            "expression_cycle",
            where=f"{plan_['class']}.{name}",
            expected="an expression over the columns beside it",
            got="one written in terms of itself, through "
                + " -> ".join(stack + (name,)),
            repairs=[Repair("break the ring: one of these must be stated or "
                            "aggregated rather than computed",
                            options=list(stack + (name,)))],
        )
    text = plan_["expressions"][name]
    if not _ARITHMETIC.match(_REF.sub(" ", text)):
        raise CompileError(
            "expression_not_arithmetic",
            where=f"{plan_['class']}.{name}",
            expected="arithmetic over {columns}, and nothing else",
            got=f"{text!r}",
            repairs=[Repair(
                "keep to + - * / ( ) and the columns beside it. The language "
                "stays smaller than SQL on purpose: a swap report can only be "
                "exact while every rule can be read whole"
            )],
        )
    known = {c["name"] for c in plan_["columns"]}
    for referenced in _REF.findall(text):
        if referenced.strip() not in known:
            raise CompileError(
                "expression_names_unknown",
                where=f"{plan_['class']}.{name}",
                expected=f"columns {plan_['class']} has",
                got="{" + referenced + "}",
                repairs=[Repair("name a column beside it", options=sorted(known))],
            )
    return "(" + _REF.sub(
        lambda m: _column_sql(plan_, m.group(1).strip(), aliases, stack + (name,)), text
    ) + ")"


def emit_entities(map_, plan_):
    """The DDL, and the one SELECT that lists the class's entities.

    One LEFT JOIN per column into the same `stated` CTE every other cell is
    read from, so a slot the log says nothing under is NULL and a slot naming
    another entity is that entity's URI.
    """
    ddl = [
        f"DROP TABLE IF EXISTS {_ident(plan_['table'])}",
        "CREATE TABLE {} (\n{}\n)".format(
            _ident(plan_["table"]),
            ",\n".join(
                f"    {_ident(c['name'])} {c['type']}" for c in plan_["columns"]
            ),
        ),
    ]

    selects = [f"e.uri AS {_ident(IDENTITY_COLUMN)}"]
    joins = ["FROM source_0 r", "JOIN registry e ON e.entity_id = r.subject_id"]
    for i, col in enumerate(plan_["columns"]):
        if col["kind"] != "stated":
            continue
        alias = f"c{i}"
        selects.append(f"({alias}.value)::{col['type']} AS {_ident(col['name'])}")
        joins.append(
            f"LEFT JOIN stated {alias} ON {alias}.subject_id = r.subject_id\n"
            f"                        AND {alias}.slot = {_lit(col['uri'])}"
        )

    select = (
        "WITH "
        + ",\n".join([_STANDING, _REGISTRY, _STATED,
                       _source_cte(map_, plan_["class"], "source_0")])
        + "\nSELECT "
        + ",\n       ".join(selects)
        + "\n"
        + "\n".join(joins)
        + "\nORDER BY 1"
    )
    return ddl, select


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

    aliases, aggregate_ctes, parameter_ctes = {}, [], []
    for i, (column, spec) in enumerate(plan_["aggregates"].items()):
        alias = f"total_{i}"
        aliases[column] = alias
        aggregate_ctes.append(
            _aggregate_cte(spec, column, alias, sources[spec["over"]], keys, f"t{i}_")
        )

    for i, (column, spec) in enumerate(plan_["parameters"].items()):
        alias = f"param_{i}"
        aliases[column] = alias
        parameter_ctes.append(_parameter_cte(spec, alias))

    key_list = ", ".join(_ident(k) for k in keys)
    grouping = "grouping AS (\n" + "\n    UNION\n".join(
        f"    SELECT {key_list} FROM {aliases[column]}" for column in plan_["aggregates"]
    ) + "\n)"

    joins = []
    for column in plan_["aggregates"]:
        alias = aliases[column]
        on = "\n                       AND ".join(
            f"{alias}.{_ident(k)} IS NOT DISTINCT FROM g.{_ident(k)}" for k in keys
        )
        joins.append(f"LEFT JOIN {alias} ON {on}")
    for column, spec in plan_["parameters"].items():
        alias = aliases[column]
        joins.append(
            f"LEFT JOIN {alias} ON {alias}.key_value "
            f"IS NOT DISTINCT FROM g.{_ident(spec['of'])}"
        )

    select = (
        "WITH "
        + ",\n".join([_STANDING, _REGISTRY, _STATED] + source_ctes
                     + aggregate_ctes + parameter_ctes + [grouping])
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

def preview(kernel, map_, class_name, *, valid_at, as_of):
    """Plan one table, emit its SQL, and run it against the log. Writes nothing.

    This is the whole of the derivation except the last step. It exists because
    a reader wants the numbers and the rules that produced them without a
    projection being dropped and rebuilt under somebody else's feet — the
    operational store is per application, and reading is not a reason to touch
    it.
    """
    plan_ = plan_for(map_, class_name)
    ddl, select = (emit(map_, plan_) if plan_["shape"] == "grouped"
                   else emit_entities(map_, plan_))

    with kernel.cursor() as cur:
        # Prevent catastrophic nested loop plans on unindexed CTEs and bypass LLVM JIT overhead
        cur.execute("SET enable_nestloop = off; SET jit = off")
        cur.execute(select, {"valid_at": valid_at, "as_of": as_of,
                             "uri_predicate": URI_PREDICATE})
        rows = cur.fetchall()
    return {"plan": plan_, "ddl": ddl, "select": select, "rows": rows,
            "valid_at": valid_at, "as_of": as_of}


def compile_class(kernel, ops, map_, class_name, *, valid_at, as_of):
    """Read the log through the map's rules; drop and rebuild one table."""
    built = preview(kernel, map_, class_name, valid_at=valid_at, as_of=as_of)
    plan_, ddl, select, rows = (built["plan"], built["ddl"],
                                built["select"], built["rows"])

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
    for kind in ("identity", "key", "stated", "aggregate", "parameter",
                 "expression", "unfilled"):
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


def _entity_classes(map_):
    """Every other class the log can say an entity is one of.

    A class with an aggregate is not here: its table is that grouping, and a
    list of its entities would be a second table under one name.

    Nor is a role. A role is something a class promises, never something an
    entity is, so nothing in the log is ever one and its table would have no
    rows. It does mean a field ranging over a role has no projection to read
    its choices from and falls back to the log — which the form says on the
    page rather than rounding off, and which closes when a role carries a
    binding the generator reads for a label.
    """
    view = map_["view"]
    grouped = set(_aggregate_classes(map_))
    return [str(name) for name in view.all_classes()
            if str(name) not in grouped
            and not view.get_class(name).abstract
            and type_slot(map_, name) is not None]


def tables(map_):
    """Every class this map can fill a table for, groupings first.

    One list, in the order the CLI compiles them and a reader should meet
    them: what the map derives, then what the log can say an entity is.
    """
    return _aggregate_classes(map_) + _entity_classes(map_)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile a sealed map's rules into the operational store.")
    parser.add_argument("map", help="a sealed version file")
    parser.add_argument("klass", nargs="*", metavar="CLASS",
                        help="default: every class the map can fill a table for")
    parser.add_argument("--valid-at", default=None)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--sql", action="store_true", help="print the emitted SQL")
    parser.add_argument("--into", default=None, metavar="DIR",
                        help="write the SQL and the rows here, one pair per table")

    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc).isoformat()
    valid_at, as_of = args.valid_at or now, args.as_of or now

    try:
        map_ = read_map(args.map, Store.from_env())
        classes = args.klass or (_aggregate_classes(map_) + _entity_classes(map_))
        if not classes:
            raise CompileError(
                "nothing_to_compile",
                where=args.map,
                expected="a class carrying an aggregate, or one the log can say "
                         "an entity is",
                got="neither",
                repairs=[Repair("annotate a slot with an aggregate, or pin a "
                                "module whose classes carry designates_type")],
            )

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
    except Refusal as exc:
        print(f"not compiled: {exc.explain()}", file=sys.stderr)
        return 2
    except psycopg.OperationalError as exc:
        print(f"not compiled: no store at {OPS_DSN} — {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())

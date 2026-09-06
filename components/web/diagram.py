"""web/diagram — the map, and one column's rule, as Mermaid text.

Two drawings, both generated from the sealed map and from nothing else.

    classes(map_)          every class the map declares, what is below what,
                           and every slot whose range is another class
    formula(map_, plan_, column)
                           one column of one table and what fills it: the
                           expression it is written as, the columns that
                           expression names, the aggregate under each of those
                           and the fact the log is read for

The second is the answer to "how do you know the logic is not in the code",
drawn rather than argued. Every label on it is a name the map wrote — a class,
a slot, an operator, an expression — and this file supplies none of them. Point
it at another map and another diagram comes out, which is the whole claim.

Mermaid because it is text: the diagram is generated the way the SQL is
generated, and the browser turns it into a picture with one script and no build
step.
"""

from html import escape

# Mermaid reads its own punctuation inside a label even when the label is
# quoted, so a label is escaped to HTML entities on the way in. `#` first: it
# is the escape character, and doing it second would eat the others.
_ESCAPES = [("#", "#35;"), ("\"", "#quot;"), ("{", "#123;"), ("}", "#125;"),
            ("(", "#40;"), (")", "#41;"), ("[", "#91;"), ("]", "#93;")]


def _label(text):
    out = str(text)
    for char, entity in _ESCAPES:
        out = out.replace(char, entity)
    return out


def classes(map_):
    """Every class, what it is below, and what it points at.

    A slot whose range is another class is an edge labelled with the slot's own
    name — which is how the map says one thing refers to another, and the only
    thing here that decides an arrow exists.
    """
    view = map_["view"]
    names = sorted(str(name) for name in view.all_classes())
    known = set(names)
    lines = ["classDiagram"]
    for name in names:
        lines.append(f"  class {name}")
    for name in names:
        parent = view.get_class(name).is_a
        if parent and str(parent) in known:
            lines.append(f"  {parent} <|-- {name}")
    for name in names:
        for slot in view.class_induced_slots(name):
            range_ = str(slot.range or "")
            if range_ in known and range_ != name:
                lines.append(f"  {name} --> {range_} : {slot.name}")
    return "\n".join(lines)


def _references(expression):
    """The column names an expression names, in the order it names them."""
    out, rest = [], str(expression)
    while "{" in rest and "}" in rest:
        _, _, rest = rest.partition("{")
        name, _, rest = rest.partition("}")
        if name not in out:
            out.append(name)
    return out


def formula(map_, plan_, column):
    """One column, and everything the map reads to fill it.

    Walked backwards from the column asked for: an expression reaches the
    columns it names, an aggregate reaches the class it is over and the slot it
    totals, a parameter reaches the key it is of and the slot it reads off that
    key's entity. A key column reaches nothing — it is what a row is.
    """
    by_name = {col["name"]: col for col in plan_["columns"]}
    if column not in by_name:
        raise KeyError(column)

    lines = ["flowchart TD"]
    ids, sources = {}, []
    seen = []

    def node(name):
        if name not in ids:
            ids[name] = f"c{len(ids)}"
            col = by_name[name]
            lines.append(f'  {ids[name]}["{_label(name)}<br><i>{col["kind"]}</i>"]')
        return ids[name]

    def source(text, shape="([{}])"):
        sources.append(text)
        ident = f"s{len(sources)}"
        lines.append(f"  {ident}" + shape.format(f'"{_label(text)}"'))
        return ident

    def walk(name):
        if name in seen:
            return
        seen.append(name)
        here = node(name)
        col = by_name[name]
        if col["kind"] == "expression":
            written = plan_["expressions"][name]
            wrote = source(written, "[/{}/]")
            lines.append(f"  {wrote} --> {here}")
            for other in _references(written):
                if other in by_name:
                    lines.append(f"  {node(other)} --> {wrote}")
                    walk(other)
        elif col["kind"] == "aggregate":
            spec = plan_["aggregates"][name]
            grouped = ", ".join(f"{key} = {slot}"
                                for key, slot in sorted(spec["by"].items()))
            what = source(
                f"{spec['operator']} of {spec['over']}.{spec['measure_uri']}"
                f"<br>by {grouped}", "[({})]")
            lines.append(f"  {what} --> {here}")
            lines.append(f"  {source(spec['over'] + ' — rows of the store')}"
                         f" --> {what}")
        elif col["kind"] == "parameter":
            spec = plan_["parameters"][name]
            what = source(f"{spec['slot_uri']}<br>of the entity {spec['of']} "
                          f"names, at both clocks", "[({})]")
            lines.append(f"  {what} --> {here}")
            lines.append(f"  {source('the log — stated, never computed')}"
                         f" --> {what}")
            lines.append(f"  {node(spec['of'])} --> {what}")
            walk(spec["of"])
        elif col["kind"] == "key":
            lines.append(f"  {source('what a row is')} --> {here}")

    walk(column)
    return "\n".join(lines)


def script(text, *, height="34rem"):
    """One diagram, and the one script that draws it."""
    return (
        f'<div class="mermaid" style="min-height:{height}">{escape(text)}</div>'
        '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/'
        'mermaid.min.js"></script>'
        "<script>mermaid.initialize({startOnLoad:true,theme:'neutral'});</script>"
    )

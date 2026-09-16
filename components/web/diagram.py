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
import uuid

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

def _node(view, name, style):
    """One box: the class's name, and the first sentence the map wrote for it."""
    cls = view.get_class(name)
    desc = (cls.description or "").split(".")[0].strip()
    if len(desc) > 34:
        desc = desc[:31] + "..."
    desc_str = f"<br><small>{_label(desc)}</small>" if desc else ""
    return f'    {name}["<b>{_label(name)}</b>{desc_str}"]:::{style}'


def _tiers(map_):
    """The three tiers, read off the map and out of nothing else.

    A class the map gives an aggregate is **computed**: nobody states a row of
    it. Of the rest, the ones the log can say an entity is — those carrying
    `designates_type` — divide by the map's own distinction, the same one the
    forms page uses: a class one of its slots identifies is a thing somebody
    names and refers to afterwards, and a class nothing identifies is written
    down as it happens and identified by nothing but having happened.

    Whatever is left is a class the log cannot instantiate — an abstract parent
    — and it is drawn beside the things it is a parent of.
    """
    from compile import _aggregate_classes
    from generate import _identifier, _type_slot

    all_classes = sorted(str(name) for name in map_["view"].all_classes())
    computed = sorted(str(name) for name in _aggregate_classes(map_))
    rest = [c for c in all_classes if c not in set(computed)]

    named, unnamed, abstract = [], [], []
    for name in rest:
        if _type_slot(map_, name) is None:
            abstract.append(name)
        elif _identifier(map_, name) is not None:
            named.append(name)
        else:
            unnamed.append(name)
    return sorted(named + abstract), unnamed, computed


def _edges(map_, drawn):
    """Every line on the drawing, and what the map says each one is.

    Four kinds, and each is a thing the map declares rather than a thing this
    file knows: inheritance, a slot whose range is another class, the source an
    aggregate runs over, and the class a parameter reads its fact off.

    Slots between one pair of classes are gathered onto a single line: two
    classes joined by three slots are one relationship read three ways, and
    three arrows say less than one.
    """
    from compile import _annotation

    view = map_["view"]
    index, out = {}, []

    def add(source, target, label, arrow):
        if source not in drawn or target not in drawn or source == target:
            return
        key = (source, target, arrow)
        edge = index.get(key)
        if edge is None:
            edge = {"source": source, "target": target,
                    "arrow": arrow, "labels": []}
            index[key] = edge
            out.append(edge)
        if label and label not in edge["labels"]:
            edge["labels"].append(label)

    def spec_get(spec, key):
        try:
            return spec.get(key)
        except AttributeError:
            return None

    for name in drawn:
        cls = view.get_class(name)

        if cls.is_a and str(cls.is_a) in drawn:
            add(name, str(cls.is_a), "is a", "-->")

        for slot in view.class_induced_slots(name):
            slot_name = str(slot.name)

            # A slot whose range is another class is an edge from it.
            if slot.range and str(slot.range) in drawn:
                add(str(slot.range), name, str(slot.title or slot_name), "-->")

            # An aggregate names the class it runs over.
            aggregate = _annotation(slot, "aggregate")
            over = spec_get(aggregate, "over") if aggregate else None
            if over:
                add(str(over), name, "aggregates", "==>")

            # A parameter reads one fact off whatever its key column names.
            parameter = _annotation(slot, "parameter")
            of = spec_get(parameter, "of") if parameter else None
            if of:
                try:
                    key_slot = view.induced_slot(str(of), name)
                except Exception:
                    key_slot = None
                if key_slot is not None and key_slot.range and str(key_slot.range) in drawn:
                    add(str(key_slot.range), name, "reads", "-.->")

    return out


def classes(map_):
    """Every class the map declares, tiered and joined by what the map says.

    There is no list of names here: the tiers come from `_tiers` and the lines
    from `_edges`, and both of them read the map. Point it at another map and
    another drawing comes out, which is the whole claim.
    """
    view = map_["view"]
    named, unnamed, computed = _tiers(map_)
    drawn = set(named) | set(unnamed) | set(computed)

    lines = ["flowchart TD"]

    for tier_id, heading, members, style in (
        ("L1", "LAYER 1 &middot; WHAT THE BUSINESS REFERS TO", named, "master"),
        ("L2", "LAYER 2 &middot; WHAT THE BUSINESS WRITES DOWN", unnamed, "event"),
        ("L3", "LAYER 3 &middot; WHAT IS COMPUTED, AND STATED BY NOBODY", computed, "proj"),
    ):
        if not members:
            continue
        lines.append(f'  subgraph {tier_id} ["{heading}"]')
        lines.append("    direction TB")
        lines += [_node(view, name, style) for name in members]
        lines.append("  end")
        lines.append("")

    lines.append("  %% Every line below is a rule the map declares.")
    for edge in _edges(map_, drawn):
        label = " / ".join(edge["labels"])
        joint = f"|{_label(label)}|" if label else ""
        lines.append(f'  {edge["source"]} {edge["arrow"]}{joint} {edge["target"]}')

    lines.append("")
    lines.append("  %% Themes")
    lines.append("  classDef master fill:#f0fdf4,stroke:#16a34a,stroke-width:1.5px,color:#14532d,rx:6px,ry:6px;")
    lines.append("  classDef event fill:#fffbeb,stroke:#d97706,stroke-width:1.5px,color:#78350f,rx:6px,ry:6px;")
    lines.append("  classDef proj fill:#eef2ff,stroke:#4f46e5,stroke-width:2px,color:#312e81,rx:5px,ry:5px;")
    lines.append("  style L1 fill:#fafaf9,stroke:#86efac,stroke-dasharray: 4 4,color:#166534")
    lines.append("  style L2 fill:#fafaf9,stroke:#fcd34d,stroke-dasharray: 4 4,color:#92400e")
    lines.append("  style L3 fill:#fafaf9,stroke:#a5b4fc,stroke-dasharray: 4 4,color:#3730a3")
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


def script(text, *, height="36rem", title="Stage 2 · Enterprise Domain Architecture"):
    """One diagram, and the one script that draws it, with interactive zoom and pan controls."""
    chart_id = f"mermaid_{uuid.uuid4().hex[:8]}"
    return (
        f'<div class="diagram-toolbar">'
        f'  <div class="diagram-toolbar-title">{escape(title or "Enterprise Domain Graph")}</div>'
        f'  <div class="diagram-btn-group">'
        f'    <button type="button" onclick="diagramZoom(\'{chart_id}\', 0.2)">➕ Zoom In</button>'
        f'    <button type="button" onclick="diagramZoom(\'{chart_id}\', -0.2)">➖ Zoom Out</button>'
        f'    <button type="button" onclick="diagramReset(\'{chart_id}\')">↺ Reset (100%)</button>'
        f'    <button type="button" onclick="diagramFit(\'{chart_id}\')">↔ Fit View</button>'
        f'  </div>'
        f'</div>'
        f'<div class="mermaid-viewport" id="{chart_id}_wrapper" style="min-height:{height}">'
        f'  <div class="mermaid" id="{chart_id}">{escape(text)}</div>'
        f'</div>'
        '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>'
        '<script>'
        'if (!window._mermaid_init) {'
        '  window._mermaid_init = true;'
        '  mermaid.initialize({'
        '    startOnLoad: true,'
        '    theme: "neutral",'
        '    flowchart: {'
        '      useMaxWidth: false,'
        '      htmlLabels: true,'
        '      curve: "basis"'
        '    }'
        '  });'
        '}'
        'window._zoom_levels = window._zoom_levels || {};'
        'function diagramZoom(id, delta) {'
        '  let z = (window._zoom_levels[id] || 1.0) + delta;'
        '  z = Math.max(0.4, Math.min(2.5, z));'
        '  window._zoom_levels[id] = z;'
        '  applyDiagramZoom(id);'
        '}'
        'function diagramReset(id) {'
        '  window._zoom_levels[id] = 1.0;'
        '  applyDiagramZoom(id);'
        '}'
        'function diagramFit(id) {'
        '  const wrapper = document.getElementById(id + "_wrapper");'
        '  const svg = document.querySelector("#" + id + " svg");'
        '  if (wrapper && svg) {'
        '    const currentZ = window._zoom_levels[id] || 1.0;'
        '    const svgW = svg.getBoundingClientRect().width / currentZ;'
        '    const wrapW = wrapper.clientWidth - 40;'
        '    if (svgW > 0) {'
        '      window._zoom_levels[id] = Math.min(1.2, Math.max(0.4, wrapW / svgW));'
        '      applyDiagramZoom(id);'
        '    }'
        '  }'
        '}'
        'function applyDiagramZoom(id) {'
        '  const z = window._zoom_levels[id] || 1.0;'
        '  const svg = document.querySelector("#" + id + " svg");'
        '  if (svg) {'
        '    svg.style.transform = "scale(" + z + ")";'
        '    svg.style.transformOrigin = "top center";'
        '    svg.style.transition = "transform 0.18s ease";'
        '  }'
        '}'
        '</script>'
    )


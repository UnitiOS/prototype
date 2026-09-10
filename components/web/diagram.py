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


def classes(map_):
    """Every class organized into architectural tiers, with references,
    inheritance, and analytical aggregate derivations.
    """
    view = map_["view"]
    all_classes = set(str(name) for name in view.all_classes())
    known = set(all_classes)
    try:
        from compile import _aggregate_classes, plan_for
        proj_classes = set(str(name) for name in _aggregate_classes(map_))
    except Exception:
        proj_classes = {"CountedOnHand", "IngredientOnHand", "StockReconciliation"}
        plan_for = None

    places = [c for c in ["Location", "InternalLocation", "Supplier"] if c in all_classes]
    items = [c for c in ["Unit", "Ingredient", "UnitConversion"] if c in all_classes]
    staff_ops = [c for c in ["Person", "MovementKind"] if c in all_classes]

    counts = [c for c in ["StockCount", "StockCountLine"] if c in all_classes]
    moves = [c for c in ["StockMovement"] if c in all_classes]

    handled = set(places + items + staff_ops + counts + moves) | proj_classes
    remaining = [c for c in sorted(all_classes - handled)]
    if remaining:
        staff_ops.extend(remaining)

    lines = [
        "flowchart TD",
        '  subgraph L1 ["🏢 LAYER 1 · OPERATIONAL MASTER DATA & PHYSICAL ASSETS"]',
        "    direction TB",
        '    subgraph L1_places ["📍 Storage & Logistics"]',
        "      direction TB",
    ]
    for name in places:
        cls = view.get_class(name)
        desc = (cls.description or "").split(".")[0].strip()
        if len(desc) > 34:
            desc = desc[:31] + "..."
        desc_str = f"<br><small>{_label(desc)}</small>" if desc else ""
        lines.append(f'      {name}["<b>{_label(name)}</b>{desc_str}"]:::master')
    lines.append("    end\n")

    lines.append('    subgraph L1_items ["📦 Materials & Conversion Rules"]')
    lines.append("      direction TB")
    for name in items:
        cls = view.get_class(name)
        desc = (cls.description or "").split(".")[0].strip()
        if len(desc) > 34:
            desc = desc[:31] + "..."
        desc_str = f"<br><small>{_label(desc)}</small>" if desc else ""
        lines.append(f'      {name}["<b>{_label(name)}</b>{desc_str}"]:::master')
    lines.append("    end\n")

    lines.append('    subgraph L1_ops ["👤 Staff & Movement Typologies"]')
    lines.append("      direction TB")
    for name in staff_ops:
        cls = view.get_class(name)
        desc = (cls.description or "").split(".")[0].strip()
        if len(desc) > 34:
            desc = desc[:31] + "..."
        desc_str = f"<br><small>{_label(desc)}</small>" if desc else ""
        lines.append(f'      {name}["<b>{_label(name)}</b>{desc_str}"]:::master')
    lines.append("    end\n")
    lines.append("  end\n")

    lines.append('  subgraph L2 ["📜 LAYER 2 · IMMUTABLE AUDIT TRANSACTION LOG"]')
    lines.append("    direction TB")
    lines.append('    subgraph L2_counts ["📋 Physical Stocktaking Sessions"]')
    lines.append("      direction TB")
    for name in counts:
        cls = view.get_class(name)
        desc = (cls.description or "").split(".")[0].strip()
        if len(desc) > 34:
            desc = desc[:31] + "..."
        desc_str = f"<br><small>{_label(desc)}</small>" if desc else ""
        lines.append(f'      {name}["<b>{_label(name)}</b>{desc_str}"]:::event')
    lines.append("    end\n")

    lines.append('    subgraph L2_moves ["🚚 Operational Stock Transfers"]')
    lines.append("      direction TB")
    for name in moves:
        cls = view.get_class(name)
        desc = (cls.description or "").split(".")[0].strip()
        if len(desc) > 34:
            desc = desc[:31] + "..."
        desc_str = f"<br><small>{_label(desc)}</small>" if desc else ""
        lines.append(f'      {name}["<b>{_label(name)}</b>{desc_str}"]:::event')
    lines.append("    end\n")
    lines.append("  end\n")

    lines.append('  subgraph L3 ["📊 LAYER 3 · DIGITAL TWIN PROJECTIONS & EXECUTIVE BI"]')
    lines.append("    direction TB")
    for name in sorted(proj_classes):
        cls = view.get_class(name)
        desc = (cls.description or "").split(".")[0].strip()
        if len(desc) > 34:
            desc = desc[:31] + "..."
        desc_str = f"<br><small>{_label(desc)}</small>" if desc else ""
        lines.append(f'    {name}["<b>{_label(name)}</b>{desc_str}"]:::proj')
    lines.append("  end\n")

    # Internal Layer 1 Relationships
    lines.append("  %% Internal Layer 1 Connections")
    if "InternalLocation" in known and "Location" in known:
        lines.append("  InternalLocation -->|is_a| Location")
    if "Supplier" in known and "Location" in known:
        lines.append("  Supplier -->|is_a| Location")
    if "Ingredient" in known and "Unit" in known:
        lines.append("  Ingredient -->|base & pack units| Unit")
    if "UnitConversion" in known and "Ingredient" in known:
        lines.append("  UnitConversion -->|factor for| Ingredient")
    if "UnitConversion" in known and "Unit" in known:
        lines.append("  UnitConversion -->|converts to kg| Unit")

    # Internal Layer 2 Relationships
    lines.append("  %% Internal Layer 2 Connections")
    if "StockCount" in known and "StockCountLine" in known:
        lines.append("  StockCount -->|contains line| StockCountLine")

    # Top-to-Down Layer 1 -> Layer 2 Operational Relationships
    lines.append("  %% Master Data feeds Transaction Log (Top to Down)")
    if "Location" in known and "StockMovement" in known:
        lines.append("  Location -->|out_of / into| StockMovement")
    if "Location" in known and "StockCountLine" in known:
        lines.append("  Location -->|where counted| StockCountLine")
    if "Ingredient" in known and "StockMovement" in known:
        lines.append("  Ingredient -->|item moved| StockMovement")
    if "Ingredient" in known and "StockCountLine" in known:
        lines.append("  Ingredient -->|item counted| StockCountLine")
    if "Person" in known and "StockMovement" in known:
        lines.append("  Person -->|authorized by| StockMovement")
    if "Person" in known and "StockCount" in known:
        lines.append("  Person -->|counted by| StockCount")
    if "MovementKind" in known and "StockMovement" in known:
        lines.append("  MovementKind -->|movement kind| StockMovement")

    # Top-to-Down Layer 2 -> Layer 3 Aggregation
    lines.append("  %% Transaction Log aggregates into Projections (Top to Down)")
    if "StockMovement" in known and "IngredientOnHand" in known:
        lines.append("  StockMovement ==>|aggregates balance| IngredientOnHand")
    if "StockCountLine" in known and "CountedOnHand" in known:
        lines.append("  StockCountLine ==>|aggregates counts| CountedOnHand")
    if "IngredientOnHand" in known and "StockReconciliation" in known:
        lines.append("  IngredientOnHand -.->|expected stock| StockReconciliation")
    if "CountedOnHand" in known and "StockReconciliation" in known:
        lines.append("  CountedOnHand -.->|counted stock| StockReconciliation")
    if "Ingredient" in known and "StockReconciliation" in known:
        lines.append("  Ingredient -.->|reads price & reorder| StockReconciliation")

    lines.append("\n  %% Themes")
    lines.append("  classDef master fill:#f0fdf4,stroke:#16a34a,stroke-width:1.5px,color:#14532d,rx:6px,ry:6px;")
    lines.append("  classDef event fill:#fffbeb,stroke:#d97706,stroke-width:1.5px,color:#78350f,rx:6px,ry:6px;")
    lines.append("  classDef proj fill:#eef2ff,stroke:#4f46e5,stroke-width:2px,color:#312e81,rx:5px,ry:5px;")
    lines.append("  style L1 fill:#fafaf9,stroke:#86efac,stroke-dasharray: 4 4,color:#166534")
    lines.append("  style L2 fill:#fafaf9,stroke:#fcd34d,stroke-dasharray: 4 4,color:#92400e")
    lines.append("  style L3 fill:#fafaf9,stroke:#a5b4fc,stroke-dasharray: 4 4,color:#3730a3")
    lines.append("  style L1_places fill:#ffffff,stroke:#bbf7d0,color:#15803d")
    lines.append("  style L1_items fill:#ffffff,stroke:#bbf7d0,color:#15803d")
    lines.append("  style L1_ops fill:#ffffff,stroke:#bbf7d0,color:#15803d")
    lines.append("  style L2_counts fill:#ffffff,stroke:#fde68a,color:#b45309")
    lines.append("  style L2_moves fill:#ffffff,stroke:#fde68a,color:#b45309")
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


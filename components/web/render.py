"""web/render — the structures the generator and the compiler already return,
as HTML.

There is no logic here and there is deliberately no room for any. Every
function is handed a built structure and turns it into markup:

    form_html    what `generate.form()` returns: fields, ranges, and the
                 options it read at the clocks, as a `<form method=post>`
    table_html   what `compile.compile_class()` returns: the rows it stored,
                 with each column's kind under its name, so a reader can see
                 which cells the graph computed and which it read as a
                 parameter
    page         the shell both sit in: one inline style block and the two
                 clock boxes, which appear on every page

Nothing here reads a database, and nothing here knows what any class or slot
is called: the names it prints came out of the built structure, which came out
of the map.

The two clocks are the point. They are on every page as a plain GET form
submitting to the page it is on, so changing one and pressing the button is a
reload of the same page at a different pair of clocks — and for a table that
is a rebuild of the table.
"""

from html import escape

# One block, no framework, no build step. Enough to read a table and fill in a
# form and no more.
STYLE = """
:root { color-scheme: light; }
body { font: 15px/1.5 -apple-system, Segoe UI, system-ui, sans-serif;
       margin: 0; color: #1a1a1a; background: #fbfaf8; }
main { max-width: 78rem; margin: 0 auto; padding: 1.5rem 2rem 4rem; }
h1 { font-size: 1.35rem; margin: 0 0 .25rem; font-weight: 600; }
h2 { font-size: 1rem; margin: 2rem 0 .5rem; font-weight: 600; }
a { color: #1c4f8b; }
header.bar { border-bottom: 1px solid #e2ded7; background: #fff;
             padding: .75rem 2rem; display: flex; gap: 1.5rem;
             align-items: baseline; flex-wrap: wrap; }
header.bar .home { font-weight: 600; text-decoration: none; color: #1a1a1a; }
form.clocks { display: flex; gap: .75rem; align-items: baseline;
              flex-wrap: wrap; margin-left: auto; }
form.clocks label { font-size: .8rem; color: #6b6259; }
input, select, button { font: inherit; padding: .3rem .4rem;
                        border: 1px solid #cfc9c0; border-radius: 3px;
                        background: #fff; }
input[type=submit], button { background: #1c4f8b; color: #fff;
                             border-color: #1c4f8b; cursor: pointer; }
.note { color: #6b6259; font-size: .85rem; margin: 0 0 1rem; }
.msg { border-left: 3px solid #1c4f8b; background: #eef3f9;
       padding: .6rem .8rem; margin: 0 0 1.25rem; font-size: .9rem;
       white-space: pre-wrap; }
.msg.bad { border-color: #a33; background: #faeceb; }
table { border-collapse: collapse; font-size: .88rem; width: 100%; }
th, td { border: 1px solid #e2ded7; padding: .3rem .5rem; text-align: left;
         vertical-align: top; white-space: nowrap; }
th { background: #f3efe9; }
th .kind { display: block; font-weight: 400; font-size: .72rem;
           color: #6b6259; text-transform: uppercase; letter-spacing: .04em; }
td.empty { background: #faf8f5; }
.scroll { overflow-x: auto; }
.field { margin: 0 0 .9rem; max-width: 34rem; }
.field label { display: block; font-weight: 600; font-size: .85rem; }
.field .hint { display: block; color: #6b6259; font-size: .8rem;
               margin: 0 0 .25rem; }
.field input, .field select { width: 100%; box-sizing: border-box; }
.req { color: #a33; }
ul.classes { columns: 3; list-style: none; padding: 0; margin: 0; }
ul.classes li { margin: 0 0 .2rem; break-inside: avoid; }
"""

# A range the map declares becomes an input the browser knows how to check.
# Anything else is a text box — and a class range never reaches here, because
# a field over one is a select.
INPUT_TYPE = {
    "integer": "number",
    "decimal": "number",
    "float": "number",
    "double": "number",
    "date": "date",
}

STEP = {"decimal": "any", "float": "any", "double": "any"}


def _clocks(valid_at, as_of):
    """The two boxes, submitting to the page they are on."""
    return (
        '<form class="clocks" method="get" action="">'
        '<label>valid_at<br><input name="valid_at" value="{}"></label>'
        '<label>as_of<br><input name="as_of" value="{}"></label>'
        '<label><br><input type="submit" value="at these clocks"></label>'
        "</form>"
    ).format(escape(str(valid_at)), escape(str(as_of)))


def page(title, body, *, valid_at, as_of):
    """One page: the shell, the clock boxes, and a body already rendered."""
    home = f"/?{_carried(valid_at, as_of)}"
    return (
        "<!doctype html>\n<html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{STYLE}</style></head><body>"
        f'<header class="bar"><a class="home" href="{home}">uniti</a>'
        f"{_clocks(valid_at, as_of)}</header>"
        f"<main>{body}</main></body></html>\n"
    )


def _carried(valid_at, as_of):
    """The clocks, as a query string to hang on a link."""
    return f"valid_at={escape(str(valid_at))}&amp;as_of={escape(str(as_of))}"


def index_html(forms, tables, *, valid_at, as_of):
    """Every class with a form and every class with a compiled table.

    Both lists are read from the map by the caller. This prints what it is
    handed, in the order it is handed it.
    """
    carried = _carried(valid_at, as_of)
    out = ["<h1>What the map declares</h1>"]
    out.append(
        '<p class="note">Every class below came out of the sealed map. A class '
        "with a form is one the log can say an entity is; a class with a table "
        "is one the map gives a rule that fills it.</p>"
    )
    out.append(f"<h2>{len(forms)} with a form</h2>")
    out.append('<ul class="classes">')
    for name in forms:
        out.append(
            f'<li><a href="/form/{escape(name)}?{carried}">{escape(name)}</a></li>')
    out.append("</ul>")
    out.append(f"<h2>{len(tables)} with a table</h2>")
    out.append('<ul class="classes">')
    for name in tables:
        out.append(
            f'<li><a href="/table/{escape(name)}?{carried}">{escape(name)}</a></li>')
    out.append("</ul>")
    return "\n".join(out)


def _field_html(field, value=""):
    """One slot, asked for. A class range is a select, everything else a box."""
    name = escape(str(field["name"]))
    required = " required" if field["required"] else ""
    star = ' <span class="req" title="required">*</span>' if field["required"] else ""
    hint = field["description"] or ""
    if field["ref"]:
        options = ['<option value="">—</option>']
        for uri, label in field["options"]:
            selected = " selected" if uri == value else ""
            shown = f"{label} — {uri}" if label else uri
            options.append(
                f'<option value="{escape(uri)}"{selected}>{escape(shown)}</option>')
        if len(options) == 1:
            hint = (hint + " (the log holds none)").strip()
        control = (f'<select name="{name}" id="f_{name}"{required}>'
                   + "".join(options) + "</select>")
    else:
        range_ = str(field["range"] or "string").lower()
        kind = INPUT_TYPE.get(range_, "text")
        step = f' step="{STEP[range_]}"' if range_ in STEP else ""
        control = (f'<input type="{kind}"{step} name="{name}" id="f_{name}" '
                   f'value="{escape(str(value))}"{required}>')
    return (f'<div class="field"><label for="f_{name}">{name}{star}</label>'
            f'<span class="hint">{escape(hint)}</span>{control}</div>')


# The two boxes the map does not give and the kernel cannot do without.
EXTRA_FIELDS = [
    {"name": "subject", "required": True, "ref": False, "range": "string",
     "description": "The URI of the thing being written about. One the log has "
                    "not seen before is minted."},
    {"name": "actor", "required": True, "ref": False, "range": "string",
     "description": "Who is acting. It goes on the intent, once, for the whole "
                    "submission."},
]


def form_html(built, *, valid_at, as_of, values=None, message=None, bad=False):
    """What `generate.form()` returns, as a form that posts to itself.

    `values` prefills fields the caller already knows the answer to. The only
    caller passes the class name for the slot the map flags as carrying it,
    and passes back what was entered when a submission was refused.
    """
    values = values or {}
    out = [f"<h1>{escape(str(built['class']))}</h1>"]
    out.append(
        f'<p class="note">{escape(str(built["source"]))}, '
        f'{escape(str(built["version"]))} — {len(built["fields"])} slots. '
        f"The choices in a list below were read out of the log at valid_at "
        f"{escape(str(valid_at))}, as_of {escape(str(as_of))}.</p>"
    )
    if message:
        out.append(f'<p class="msg{" bad" if bad else ""}">{escape(message)}</p>')
    out.append('<form method="post" action="">')
    for field in EXTRA_FIELDS:
        out.append(_field_html(field, values.get(field["name"], "")))
    for field in built["fields"]:
        out.append(_field_html(field, values.get(field["name"], "")))
    out.append('<button type="submit">write it</button>')
    out.append("</form>")
    return "\n".join(out)


def table_html(built, *, valid_at, as_of):
    """What `compile_class()` returns, as a table.

    The rows are the ones it read back out of the operational store after
    filling it, so what is printed is what is stored. Each column's kind sits
    under its name: a reader can see which cells the map computed, which it
    read out of the log as a stated number, and which are the grouping.
    """
    plan_ = built["plan"]
    cols = plan_["columns"]
    out = [f"<h1>{escape(str(plan_['class']))}</h1>"]
    out.append(
        f'<p class="note">{escape(str(plan_["table"]))}, '
        f'{escape(str(plan_["version"]))} — {len(built["rows"])} rows, '
        f"{len(cols)} columns, rebuilt at valid_at {escape(str(valid_at))}, "
        f"as_of {escape(str(as_of))}. Read back out of the operational store "
        "this page just filled; the log itself is not on this page.</p>"
    )
    head = "".join(
        f'<th>{escape(str(col["name"]))}'
        f'<span class="kind">{escape(str(col["kind"]))}</span></th>'
        for col in cols
    )
    body = []
    for row in built["rows"]:
        cells = [
            '<td class="empty"></td>' if cell is None
            else f"<td>{escape(str(cell))}</td>"
            for cell in row
        ]
        body.append("<tr>" + "".join(cells) + "</tr>")
    out.append('<div class="scroll"><table><thead><tr>' + head
               + "</tr></thead><tbody>" + "".join(body)
               + "</tbody></table></div>")
    if not built["rows"]:
        out.append('<p class="note">No rows at these clocks.</p>')
    return "\n".join(out)


def message_page(title, text, *, valid_at, as_of, bad=True):
    """Nothing to render, or a refusal. Still a page, still with its clocks."""
    body = (f"<h1>{escape(title)}</h1>"
            f'<p class="msg{" bad" if bad else ""}">{escape(text)}</p>')
    return page(title, body, valid_at=valid_at, as_of=as_of)

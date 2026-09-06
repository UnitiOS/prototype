"""web/render — the structures the generator and the compiler already return,
as HTML.

There is no logic here and there is deliberately no room for any. Every
function is handed a built structure and turns it into markup:

    home_html    the stages, as cards in the order they happen — a walk
                 forward rather than a list of links
    said_html    a transcript and the map it became, side by side, with a
                 class on one side linked to the sentence on the other
    graph_html   one diagram, already generated as Mermaid text
    why_html     every assertion ever made about one subject and predicate
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
from urllib.parse import quote, urlencode

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

/* the walk: one card per stage, in the order the stages happen */
ol.stages { list-style: none; padding: 0; margin: 1.5rem 0 0;
            display: grid; gap: .9rem;
            grid-template-columns: repeat(auto-fill, minmax(19rem, 1fr)); }
ol.stages li { border: 1px solid #e2ded7; background: #fff; border-radius: 4px;
               padding: .9rem 1rem 1rem; }
ol.stages .step { font-size: .72rem; color: #8a8078; letter-spacing: .08em;
                  text-transform: uppercase; }
ol.stages h3 { margin: .15rem 0 .35rem; font-size: 1.05rem; font-weight: 600; }
ol.stages p { margin: 0 0 .6rem; font-size: .88rem; color: #4a443e; }
ol.stages li.dead { background: #f6f4f1; color: #8a8078; }
ol.stages li.dead h3, ol.stages li.dead p { color: #8a8078; }

/* the transcript beside the map */
.said { display: grid; gap: 1.5rem; grid-template-columns: 1fr 1fr;
        align-items: start; }
.said > section { min-width: 0; }
.said .prose { max-height: 78vh; overflow-y: auto; padding-right: .5rem; }
.said .prose p { white-space: pre-wrap; margin: 0 0 .9rem;
                 font-size: .86rem; padding: .2rem .4rem; }
.said .prose p:target { background: #fdf3d0; outline: 2px solid #e6c65c; }
.said pre { max-height: 78vh; overflow: auto; background: #fff;
            border: 1px solid #e2ded7; padding: .75rem; font-size: .8rem;
            margin: 0; }
.said pre a { text-decoration: none; background: #eef3f9; }

/* the assertions behind one cell */
table.why td.value { white-space: normal; font-weight: 600; }
table.why tr.gone td { color: #8a8078; text-decoration: line-through; }
.timeline { list-style: none; padding: 0; margin: 0; }
.timeline li { border-left: 3px solid #1c4f8b; padding: .1rem 0 .6rem .8rem;
               margin: 0 0 .8rem; }
.mermaid { background: #fff; border: 1px solid #e2ded7; padding: 1rem;
           overflow: auto; }
a.why { text-decoration: none; border-bottom: 1px dotted #1c4f8b; }
th a { color: #1c4f8b; }
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
    """The clocks, as a query string to hang on a link.

    Percent-encoded before it is HTML-escaped, and the order matters. An
    offset-aware clock ends in `+00:00`, and a `+` in a query string means a
    space to every reader of one — so a link built by escaping alone hands the
    next request a clock it cannot parse. `urlencode` writes it `%2B`.
    """
    return escape(urlencode({"valid_at": str(valid_at), "as_of": str(as_of)}))


def _q(value):
    """One value, safe in a query string and then safe in an attribute."""
    return escape(quote(str(value), safe=""))


def home_html(stages, *, valid_at, as_of):
    """The stages, in order, one card each.

    `stages` is a list of (name, sentence, path) and the path may be None,
    which is a stage nothing here reaches yet and is drawn as one rather than
    left off. The names are the system's own stages and came from the caller;
    this prints what it is handed, in the order it is handed it.
    """
    carried = _carried(valid_at, as_of)
    out = ["<h1>One lap, from what somebody said to what an agent acts on</h1>"]
    out.append(
        '<p class="note">Each card is a stage. They happen in this order, and '
        "everything on the pages behind them was derived from the one before "
        "it: a description became a map, the map became a log, and the log "
        "became tables and forms that nobody wrote.</p>"
    )
    out.append('<ol class="stages">')
    for number, (name, sentence, path) in enumerate(stages, start=1):
        dead = ' class="dead"' if not path else ""
        # The clocks go before the fragment, never after it: a `#` ends the
        # URL for the browser, and a query string written past one is part of
        # the anchor's name rather than a question asked of the server.
        where, _, fragment = (path or "").partition("#")
        joined = f'{where}{"&amp;" if "?" in where else "?"}{carried}'
        link = (f'<a href="{joined}{"#" + fragment if fragment else ""}">'
                "open</a>" if path else "<em>not built yet</em>")
        out.append(
            f'<li{dead}><span class="step">stage {number}</span>'
            f"<h3>{escape(name)}</h3><p>{escape(sentence)}</p>{link}</li>"
        )
    out.append("</ol>")
    return "\n".join(out)


def said_html(paragraphs, lines, *, source, transcript):
    """A transcript on the left and the map it became on the right.

    `paragraphs` is the prose, one string each, and its index is its anchor.
    `lines` is the map's own file, one (text, anchor) pair per line: an anchor
    is the paragraph a class on that line was matched to, or None. Both were
    computed by the caller — this places them in two columns and links one to
    the other.
    """
    left = "".join(
        f'<p id="p{number}">{escape(text)}</p>'
        for number, text in enumerate(paragraphs)
    )
    right = []
    for text, anchor in lines:
        if anchor is None:
            right.append(escape(text))
        else:
            right.append(f'<a href="#p{anchor}">{escape(text)}</a>')
    return (
        "<h1>What was said, and what it became</h1>"
        '<p class="note">On the left, the description of the business as it '
        "was given. On the right, the sealed map that came out of it. A class "
        "on the right is a link: it moves to the sentence on the left that "
        "asked for it. Nothing on this page was authored twice — one file is "
        f"{escape(str(transcript))} and the other is {escape(str(source))}.</p>"
        f'<div class="said"><section class="prose">{left}</section>'
        f"<section><pre>{''.join(right)}</pre></section></div>"
    )


def graph_html(title, note, diagram, *, back=None):
    """One diagram, already Mermaid text wrapped by `diagram.script`."""
    out = [f"<h1>{escape(title)}</h1>", f'<p class="note">{note}</p>']
    if back:
        out.append(f'<p class="note">{back}</p>')
    out.append(diagram)
    return "\n".join(out)


def why_html(built, *, valid_at, as_of):
    """Every assertion ever made about one subject and one predicate.

    Ordered as the log holds them and not resolved to a winner: which one
    stands at a pair of clocks is a question the table answered, and this page
    is the other question — what has ever been said, by whom, on what
    authority, and what was later withdrawn.
    """
    rows = built["rows"]
    out = ["<h1>Everything ever said about this</h1>"]
    out.append(
        f'<p class="note"><code>{escape(str(built["subject"]))}</code> — '
        f'<code>{escape(str(built["predicate"]))}</code>. {len(rows)} '
        "assertion(s), oldest first. This is the one page that reads the log "
        "itself; every number anywhere else came out of the operational store. "
        "Two rows under one pair with different <code>valid_from</code> and no "
        "<code>revokes</code> between them are not a conflict — both are true, "
        "each of its own time, and the clocks above decide which one a table "
        "shows.</p>"
    )
    if not rows:
        out.append('<p class="msg">Nothing has ever been said under this '
                   "pair.</p>")
        return "\n".join(out)
    head = ("<tr><th>value</th><th>valid_from</th><th>recorded_at</th>"
            "<th>source</th><th>confidence</th><th>authority</th>"
            "<th>actor</th><th>action</th><th>intent</th>"
            "<th>revokes</th></tr>")
    body = []
    for row in rows:
        gone = ' class="gone"' if row["revoked_by"] else ""
        value = ("<em>retraction — carries no value</em>"
                 if row["value"] is None else escape(str(row["value"])))
        withdrawn = []
        if row["revokes"]:
            withdrawn.append(f"revokes {str(row['revokes'])[:8]}")
        if row["revoked_by"]:
            withdrawn.append(f"revoked by {str(row['revoked_by'])[:8]}")
        body.append(
            f'<tr{gone}><td class="value">{value}</td>'
            f'<td>{escape(str(row["valid_from"]))}</td>'
            f'<td>{escape(str(row["recorded_at"]))}</td>'
            f'<td>{escape(str(row["source"]))}</td>'
            f'<td>{escape(str(row["confidence"] or ""))}</td>'
            f'<td>{escape(str(row["authority"] or ""))}</td>'
            f'<td>{escape(str(row["actor_id"]))}</td>'
            f'<td>{escape(str(row["action_name"]))}</td>'
            f'<td>{escape(str(row["intent_id"])[:8])}</td>'
            f"<td>{escape(', '.join(withdrawn))}</td></tr>"
        )
    out.append('<div class="scroll"><table class="why"><thead>' + head
               + "</thead><tbody>" + "".join(body) + "</tbody></table></div>")
    return "\n".join(out)


def ask_html(window, *, valid_at, as_of):
    """No pair asked for: what the log holds, and a box to name one."""
    out = ["<h1>What was recorded</h1>"]
    out.append(
        '<p class="note">The log is append-only and nothing in it is ever '
        "edited. A page here shows every assertion ever made about one "
        "subject and one predicate — including the ones later withdrawn, and "
        "the ones superseded by something valid from a later day. Reach it by "
        "following a value in a table, or name a pair.</p>"
    )
    out.append(_window_html(window))
    out.append(
        '<form method="get" action="/why">'
        f'<input type="hidden" name="valid_at" value="{escape(str(valid_at))}">'
        f'<input type="hidden" name="as_of" value="{escape(str(as_of))}">'
        '<div class="field"><label for="f_subject">subject</label>'
        '<span class="hint">The URI of the thing said to be.</span>'
        '<input name="subject" id="f_subject"></div>'
        '<div class="field"><label for="f_predicate">predicate</label>'
        '<span class="hint">The URI of what was said about it — a slot_uri '
        "from the map.</span>"
        '<input name="predicate" id="f_predicate"></div>'
        '<button type="submit">show every assertion</button></form>'
    )
    return "\n".join(out)


def index_html(forms, tables, *, valid_at, as_of):
    """Every class with a form and every class with a compiled table.

    `forms` is a list of (heading, classes) pairs and the headings came out of
    the caller, which read the grouping off the map. This prints what it is
    handed, in the order it is handed it, and decides nothing about which class
    belongs where.
    """
    carried = _carried(valid_at, as_of)
    out = ['<h1 id="forms">What the map declares</h1>']
    out.append(
        '<p class="note">Every class below came out of the sealed map. A class '
        "with a form is one the log can say an entity is; a class with a table "
        "is one the map gives a rule that fills it.</p>"
    )
    for heading, group in forms:
        if not group:
            continue
        out.append(f"<h2>{escape(heading)} — {len(group)} with a form</h2>")
        out.append('<ul class="classes">')
        for name in group:
            out.append(
                f'<li><a href="/form/{escape(name)}?{carried}">'
                f"{escape(name)}</a></li>")
        out.append("</ul>")
    out.append(f'<h2 id="tables">{len(tables)} with a table</h2>')
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
    note = (f'{escape(str(built["source"]))}, '
            f'{escape(str(built["version"]))} — {len(built["fields"])} slots.')
    sources = sorted({f["options_from"] for f in built["fields"]
                      if f.get("options_from")})
    if sources:
        note += (f" The choices in a list below were read out of "
                 f"{escape(' and '.join(sources))}, at valid_at "
                 f"{escape(str(valid_at))}, as_of {escape(str(as_of))}.")
    out.append(f'<p class="note">{note}</p>')
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


def table_html(built, *, valid_at, as_of, window=None):
    """What `compile_class()` returns, as a table.

    The rows are the ones it read back out of the operational store after
    filling it, so what is printed is what is stored. Each column's kind sits
    under its name: a reader can see which cells the map computed, which it
    read out of the log as a stated number, and which are the grouping.

    Two things on this page point elsewhere, and both are read off the plan
    rather than decided here. A column the map gives a rule links to the
    drawing of that rule, so a header answers where its own numbers came from.
    A cell the map fills by reading a fact off an entity links to every
    assertion ever made under that pair — the value in the cell is the one
    standing at these clocks, and the others are on the other page.

    `window` is what the log holds, and it is passed only when there are no
    rows: "nothing here" and "nothing was ever written down this early" are
    different answers and a reader cannot tell them apart from an empty table.
    """
    plan_ = built["plan"]
    cols = plan_["columns"]
    carried = _carried(valid_at, as_of)
    class_name = str(plan_["class"])
    out = [f"<h1>{escape(class_name)}</h1>"]
    out.append(
        f'<p class="note">{escape(str(plan_["table"]))}, '
        f'{escape(str(plan_["version"]))} — {len(built["rows"])} rows, '
        f"{len(cols)} columns, rebuilt at valid_at {escape(str(valid_at))}, "
        f"as_of {escape(str(as_of))}. Read back out of the operational store "
        "this page just filled; the log itself is not on this page.</p>"
    )

    index = {str(col["name"]): i for i, col in enumerate(cols)}
    identity = next((i for i, col in enumerate(cols)
                     if col["kind"] == "identity"), None)

    head = []
    for col in cols:
        name = escape(str(col["name"]))
        shown = name
        if plan_["shape"] == "grouped":
            shown = (f'<a href="/graph?class={escape(class_name)}'
                     f'&amp;column={name}&amp;{carried}" '
                     f'title="what the map says fills this column">{name}</a>')
        head.append(f'<th>{shown}'
                    f'<span class="kind">{escape(str(col["kind"]))}</span></th>')

    def opens(col, row):
        """The pair of URIs behind one cell, where the map reads a fact."""
        name = str(col["name"])
        if col["kind"] == "parameter":
            spec = plan_["parameters"][name]
            subject = row[index[spec["of"]]]
            return (subject, spec["slot_uri"]) if subject else None
        if col["kind"] == "stated" and identity is not None and col["uri"]:
            subject = row[identity]
            return (subject, str(col["uri"])) if subject else None
        return None

    body = []
    for row in built["rows"]:
        cells = []
        for col, cell in zip(cols, row):
            if cell is None:
                cells.append('<td class="empty"></td>')
                continue
            shown = escape(str(cell))
            pair = opens(col, row)
            if pair:
                shown = (f'<a class="why" href="/why?subject={_q(pair[0])}'
                         f'&amp;predicate={_q(pair[1])}&amp;{carried}" '
                         f'title="every assertion ever made about this">'
                         f'{shown}</a>')
            cells.append(f"<td>{shown}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    out.append('<div class="scroll"><table><thead><tr>' + "".join(head)
               + "</tr></thead><tbody>" + "".join(body)
               + "</tbody></table></div>")
    if not built["rows"]:
        out.append('<p class="note">No rows at these clocks.</p>')
        out.append(_window_html(window))
    return "\n".join(out)


def _window_html(window):
    """What the log holds at all, said when a page comes back with nothing."""
    if not window:
        return ""
    if not window.get("assertions"):
        return ('<p class="msg">The log is empty: nothing has been written '
                "down under it at any clock.</p>")
    return (
        '<p class="msg">The log holds {a:,} assertions under {i:,} intents. '
        "Nothing in it is valid before {vf}, and the latest anything is valid "
        "from is {vl}; the first was recorded at {rf} and the last at {rl}. A "
        "clock outside that is not an empty table — it is a question asked "
        "before there was anything to answer it.</p>"
    ).format(a=window["assertions"], i=window["intents"],
             vf=escape(str(window["first_valid_from"])),
             vl=escape(str(window["last_valid_from"])),
             rf=escape(str(window["first_recorded_at"])),
             rl=escape(str(window["last_recorded_at"])))


def message_page(title, text, *, valid_at, as_of, bad=True):
    """Nothing to render, or a refusal. Still a page, still with its clocks."""
    body = (f"<h1>{escape(title)}</h1>"
            f'<p class="msg{" bad" if bad else ""}">{escape(text)}</p>')
    return page(title, body, valid_at=valid_at, as_of=as_of)

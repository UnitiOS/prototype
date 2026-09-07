"""web/serve — four routes over the map, the log and the operational store.

The whole of the interface. It builds nothing and derives nothing: each route
calls a function that already exists, hands what comes back to `render`, and
writes the result out.

    GET  /                the stages, in the order they happen, one card each
    GET  /classes         every class the map gives a form, every class it
                          gives a table
    GET  /said            the description of the business beside the map it
                          became, one linked to the other
    GET  /graph           the map drawn, or — with `class` and `column` — the
                          rule that fills one column, drawn
    GET  /why             every assertion ever made about one subject and one
                          predicate. The one page that reads the log
    GET  /form/<Class>    `generate.form()` at the clocks
    POST /form/<Class>    `generate.submit()` — one intent, N assertions —
                          then the same form again, saying what was written
    GET  /table/<Class>   `compile.compile_class()` at the clocks, rendered
                          from the rows it read back out of the store

Three databases would be one too many, so there are two, and `/why` reads the
log through `provenance` — the one reader outside the compiler, named in
`CLAUDE.md`. It computes nothing: every number on every other page came out of
the operational store.

`?valid_at=` and `?as_of=` sit on every URL and default to today. They are
carried through every link and through the POST, so a page is always at a
stated pair of clocks and moving one is a reload. A clock written as a bare
date means the whole of that day, which is what makes a date picker a usable
control: `as_of=2026-09-07` includes what was recorded this afternoon, where
midnight would have excluded it.

A table also carries `sort`, `dir` and one `only.<column>` per filter. All of
them live on the URL and nowhere else, so a table somebody sorted and filtered
is a link they can send.

Two databases, and which one a route holds is the separation made visible.
`UNITI_DSN` is the log: the form reads it and the write gate writes it.
`UNITI_OPS_DSN` is the operational store: the table is read out of it. They
are separate databases, so no page can join one to the other. The table route
holds both, because rebuilding a table is exactly the act of reading the log
through the map and filling the store — which is what the compiler is, and the
compiler is the only thing allowed to do it.

Nothing here knows what a class or a slot is called. The lists on the front
page are read out of the map: a class has a form when the map flags one of its
slots `designates_type`, and a table when the map gives one of them an
aggregate. The forms are grouped in two by whether the map gives the class an
identifier — a thing somebody names, or an event nothing does — which is the
map's own distinction and not a business's.

Run:
    make serve
    make demo-serve
    UNITI_DSN=... UNITI_OPS_DSN=... serve.py business/sorella/v3.yaml --port 8000
"""

import argparse
import re
import sys
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import psycopg

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "web"))
sys.path.insert(0, str(ROOT / "components" / "provenance"))

import diagram  # noqa: E402
import provenance  # noqa: E402
import render  # noqa: E402
from compile import OPS_DSN, _aggregate_classes, compile_class  # noqa: E402
from compile import plan_for  # noqa: E402
from generate import MapError, _identifier, _projected_options  # noqa: E402
from generate import _type_slot, form, read_map, submit  # noqa: E402
from perform import DSN as KERNEL_DSN  # noqa: E402
from perform import connect as connect_kernel  # noqa: E402

# A form submission is a person stating something. There is no other actor.
MAX_BODY = 1 << 20


def _today():
    """The default for both clocks, and a value a date box can hold."""
    return datetime.now(timezone.utc).date().isoformat()


def _instant(clock):
    """One clock as the moment a query is asked at.

    A bare date is the whole of that day, not the midnight at the start of it.
    That is what lets the clocks be date boxes: a reader who sets `as_of` to
    today means everything the log knows today, and midnight would answer with
    everything it knew last night. A clock that carries a time is passed
    through untouched — somebody who wrote one meant it.
    """
    written = str(clock)
    if len(written) != 10:
        return written
    try:
        day = datetime.fromisoformat(written)
    except ValueError:
        return written
    return day.replace(hour=23, minute=59, second=59, microsecond=999999,
                       tzinfo=timezone.utc).isoformat()


class ClockError(ValueError):
    """A clock on the URL that is not a time."""


def _clock(fields, name):
    """One clock off the query string, checked here rather than in Postgres.

    A value that is not a time is the reader's mistake and belongs in a 400
    naming the field, not in a 500 quoting the database. Checking it costs one
    parse and it is thrown away: what goes to the query is the text as written,
    so nothing about how a clock is spelled is decided here.
    """
    written = (fields.get(name, [""])[0] or "").strip()
    if not written:
        return _today()
    try:
        datetime.fromisoformat(written)
    except ValueError:
        raise ClockError(
            f"{name} is {written!r}, which is not a time. Write it as "
            f"2026-06-16, or as 2026-06-16T00:00:00+00:00."
        ) from None
    return written


def _clocks(query):
    """The pair on the URL, or now."""
    fields = parse_qs(query)
    return _clock(fields, "valid_at"), _clock(fields, "as_of")


# The stages of `CLAUDE.md`, in the order they happen, and where each one is
# on this server. A stage with no page is drawn as one rather than left off:
# an absence a viewer can see is worth more than a menu that hides it.
STAGES = [
    ("What was said", "The business described in the words somebody used, "
     "beside the sealed map that description became. Neither file was "
     "written twice.", "/said"),
    ("What it became", "Every class the map declares and what refers to what "
     "— and, from any column of any table, the rule that fills it.", "/graph"),
    ("What was recorded", "The log: what was stated, by whom, when, on what "
     "authority, and what was later withdrawn. Nothing in it is ever edited.",
     "/why"),
    ("What was generated", "A form for every class the log can say an entity "
     "is, and a table for every class the map gives a rule. No screen here "
     "was written by hand.", "/classes#forms"),
    ("Live use", "Fill one in. The write becomes one intent and N assertions "
     "through the one gate, and the table rebuilds itself from the log the "
     "next time it is asked for.", "/classes#tables"),
    ("Definition change", "A definition moves, and the same question is asked "
     "again under both. Nothing here reaches it yet.", None),
]


def _mint_uri(map_, class_name):
    """A URI for a subject nobody named, from the map's own prefix.

    A form asks for the thing being written about, and for an event nobody
    names there is nothing to type: the delivery note has no number on it. The
    field says a URI it has not seen is minted, and this is what is minted —
    the map's default prefix, the class the form came from, and enough
    randomness that two of them never collide.
    """
    prefix = str(map_["view"].schema.default_prefix or "uniti")
    return f"{prefix}:{str(class_name).lower()}_{uuid.uuid4().hex[:12]}"


def _transcript_path(map_):
    """The file the map's own annotations name, beside the map."""
    for key, annotation in (map_["view"].schema.annotations or {}).items():
        if str(key) == "transcript" and annotation.value:
            return map_["path"].parent / str(annotation.value)
    return map_["path"].with_suffix(".txt")


# What a word of the class's own name is worth against a word of its
# description. Six, because the name is the strongest signal there is and the
# description is a paragraph of ordinary English around it. Tried at 3, which
# sends a class the transcript names only in passing to a paragraph its
# description happens to rhyme with, and at 10, which lets a two-word name
# outvote everything the description says.
NAME_WEIGHT = 6


def _words(text):
    """A name or a sentence, as the words it is made of."""
    return [word.lower() for word
            in re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+", str(text))
            if len(word) > 3]


def _matched(paragraphs, name, described):
    """Which paragraph of the prose asked for this class, or None.

    Scored, not looked up. The words are the class's own name and the map's
    own description of it, and a word is worth what it is rare: one appearing
    in half the transcript separates nothing, and one appearing in a single
    paragraph very nearly names it. A class the business calls something else
    entirely still lands, because the description the map carries uses the
    words the business used.

    Nothing here is told what any class is called or what a business is. The
    words come off the map, the counts come off the transcript, and this
    weighs one against the other.
    """
    wanted = [(word, NAME_WEIGHT) for word in _words(name)]
    wanted += [(word, 1) for word in dict.fromkeys(_words(described))]
    if not wanted:
        return None
    lowered = [text.lower() for text in paragraphs]
    best, score = None, 0.0
    for number, text in enumerate(lowered):
        here = 0.0
        for word, weight in wanted:
            pattern = rf"\b{re.escape(word)}"
            if not re.search(pattern, text):
                continue
            common = sum(1 for other in lowered if re.search(pattern, other))
            here += weight / common
        if here > score:
            best, score = number, here
    return best


def _said(map_):
    """The transcript in paragraphs, and the map's own file with its anchors."""
    prose = _transcript_path(map_).read_text(encoding="utf-8")
    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", prose)
                  if block.strip()]
    view = map_["view"]
    anchors = {
        str(name): _matched(paragraphs, name,
                            view.get_class(name).description or "")
        for name in view.all_classes()
    }

    lines, inside = [], False
    for line in map_["path"].read_text(encoding="utf-8").splitlines(keepends=True):
        # A blank line inside a block scalar is still inside it. Only a line
        # that starts a key of its own ends the section.
        if line.strip() and not line.startswith((" ", "\t")):
            inside = line.startswith("classes:")
        declared = re.match(r"^  ([A-Za-z_][A-Za-z0-9_]*):\s*$", line)
        anchor = None
        if inside and declared and declared.group(1) in anchors:
            anchor = anchors[declared.group(1)]
        lines.append((line, anchor))
    return paragraphs, lines


def _form_classes(map_):
    """Every class the log can say an entity is one of, in two groups.

    The split is the map's own and carries no knowledge of any business: a
    class one of its slots identifies is a thing somebody names — a place, a
    unit, a person — and its rows are written once and referred to afterwards.
    A class nothing identifies is an event, written down as it happens and
    identified by nothing but the fact that it happened — the paper it was
    written on carries no number, and the map says so by giving it no
    identifier.

    Returned as (heading, classes) pairs so that the page prints what it is
    handed. Nineteen links in one list is a menu; these are two lists.
    """
    named, unnamed = [], []
    for name in sorted(str(name) for name in map_["view"].all_classes()):
        if _type_slot(map_, name) is None:
            continue
        (named if _identifier(map_, name) else unnamed).append(name)
    return [
        ("what gets written down", unnamed),
        ("what it refers to", named),
    ]


def _table_classes(map_):
    """Every class the map gives a rule that fills a table."""
    return sorted(_aggregate_classes(map_))


def _labels(map_, cols):
    """URI -> what the business calls it, for every class a column ranges over.

    Read out of the operational store, one query per class, through the same
    function a form reads its choices with: the identifier the map declares for
    that class, off the projection of it. A class with no identifier, or none
    compiled, contributes nothing and its cells stay the URIs they were.

    Nothing here knows what any class is called. The ranges came off the map,
    the identifier came off the map, and the values came out of the store.
    """
    out = {}
    for range_ in sorted({str(col["range"]) for col in cols if col["ref"]}):
        for uri, label in _projected_options(map_, range_) or []:
            if label:
                out[uri] = label
    return out


def _choices(rows, cols):
    """The values each filterable column actually holds, in order.

    A column is filterable when its value names another entity — the map's own
    test, the same one that decides a form field is a `<select>`. The values
    are read off the rows rather than out of the store, so a choice always
    returns something.
    """
    out = {}
    for i, col in enumerate(cols):
        if not col["ref"]:
            continue
        held = sorted({str(row[i]) for row in rows if row[i] is not None})
        if held:
            out[str(col["name"])] = held
    return out


def _only(rows, cols, chosen):
    """The rows a reader asked to keep. An empty choice keeps everything."""
    index = {str(col["name"]): i for i, col in enumerate(cols)}
    for name, value in chosen.items():
        if value:
            rows = [row for row in rows if str(row[index[name]]) == value]
    return rows


def _in_order(rows, cols, name, descending):
    """The rows by one column, numbers as numbers and blanks always last."""
    index = [str(col["name"]) for col in cols].index(name)

    def key(row):
        cell = row[index]
        if cell is None:
            return (-1 if descending else 1, 0.0, "")
        try:
            return (0, float(cell), "")
        except (TypeError, ValueError):
            return (0, 0.0, str(cell).lower())

    return sorted(rows, key=key, reverse=descending)


class Handler(BaseHTTPRequestHandler):
    server_version = "uniti"
    map_ = None

    # ---- plumbing ---------------------------------------------------------

    def log_message(self, fmt, *args):
        sys.stderr.write("%s  %s\n" % (self.log_date_time_string(), fmt % args))

    def _send(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _refuse(self, title, text, valid_at, as_of, status=400):
        self._send(render.message_page(title, text, valid_at=valid_at,
                                       as_of=as_of), status)

    def _route(self):
        parsed = urlparse(self.path)
        parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
        return parts, parsed.query

    # ---- the routes -------------------------------------------------------

    def do_GET(self):
        parts, query = self._route()
        try:
            valid_at, as_of = _clocks(query)
        except ClockError as exc:
            today = _today()
            return self._refuse("Not a clock", str(exc), today, today, 400)
        try:
            if not parts:
                return self._home(valid_at, as_of)
            if parts == ["classes"]:
                return self._index(valid_at, as_of)
            if parts == ["said"]:
                return self._said(valid_at, as_of)
            if parts == ["graph"]:
                return self._graph(query, valid_at, as_of)
            if parts == ["why"]:
                return self._why(query, valid_at, as_of)
            if len(parts) == 2 and parts[0] == "form":
                return self._form(parts[1], valid_at, as_of)
            if len(parts) == 2 and parts[0] == "table":
                return self._table(parts[1], query, valid_at, as_of)
            return self._refuse("Not a page", f"There is no {self.path} here.",
                                valid_at, as_of, 404)
        except MapError as exc:
            return self._refuse("The map refuses", str(exc), valid_at, as_of, 404)
        except psycopg.Error as exc:
            traceback.print_exc()
            return self._refuse("The database refuses", str(exc),
                                valid_at, as_of, 500)

    def do_POST(self):
        parts, query = self._route()
        try:
            valid_at, as_of = _clocks(query)
        except ClockError as exc:
            today = _today()
            return self._refuse("Not a clock", str(exc), today, today, 400)
        if len(parts) != 2 or parts[0] != "form":
            return self._refuse("Not a page", f"Nothing accepts a write at "
                                f"{self.path}.", valid_at, as_of, 404)
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._refuse("Too much", "The submission is too large.",
                                valid_at, as_of, 413)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        entered = {name: values[0] for name, values in parse_qs(raw).items()}
        try:
            return self._write(parts[1], entered, valid_at, as_of)
        except MapError as exc:
            return self._refuse("The map refuses", str(exc), valid_at, as_of, 400)
        except psycopg.Error as exc:
            traceback.print_exc()
            return self._refuse("The write was refused", str(exc),
                                valid_at, as_of, 400)

    # ---- what each one does -----------------------------------------------

    def _home(self, valid_at, as_of):
        body = render.home_html(STAGES, valid_at=valid_at, as_of=as_of)
        self._send(render.page("uniti", body, valid_at=valid_at, as_of=as_of))

    def _said(self, valid_at, as_of):
        paragraphs, lines = _said(self.map_)
        body = render.said_html(paragraphs, lines,
                                source=self.map_["path"].name,
                                transcript=_transcript_path(self.map_).name)
        self._send(render.page("what was said", body,
                               valid_at=valid_at, as_of=as_of))

    def _graph(self, query, valid_at, as_of):
        """The whole map, or the rule behind one column of one table."""
        fields = parse_qs(query)
        class_name = (fields.get("class", [""])[0] or "").strip()
        column = (fields.get("column", [""])[0] or "").strip()
        carried = render._carried(valid_at, as_of)
        if not class_name:
            classes = sorted(str(name) for name in self.map_["view"].all_classes())
            body = render.graph_html(
                "The map",
                f"{len(classes)} classes, drawn from "
                f"{self.map_['path'].name}. An arrow is a slot whose range is "
                "another class, labelled with the slot's own name; a hollow "
                "arrow is one class standing below another. Nothing here was "
                "drawn by hand.",
                diagram.script(diagram.classes(self.map_), height="46rem"))
            return self._send(render.page("the map", body,
                                          valid_at=valid_at, as_of=as_of))
        plan_ = plan_for(self.map_, class_name)
        try:
            drawing = diagram.formula(self.map_, plan_, column)
        except KeyError:
            return self._refuse(
                "No such column",
                f"{class_name} has no column {column!r} — it has "
                f"{[col['name'] for col in plan_['columns']]}.",
                valid_at, as_of, 404)
        body = render.graph_html(
            f"{class_name}.{column}",
            f"What the map says fills this column, and what that reads in "
            f"turn. Every box is something {self.map_['path'].name} states: an "
            "expression, an aggregate, or a fact the log is read for. The "
            "compiler turns exactly this into SQL, and nothing about it is "
            "written in the code.",
            diagram.script(drawing),
            back=f'<a href="/table/{class_name}?{carried}">'
                 f"back to {class_name}</a>")
        self._send(render.page(f"{class_name}.{column}", body,
                               valid_at=valid_at, as_of=as_of))

    def _why(self, query, valid_at, as_of):
        """Every assertion ever made about one pair. The one kernel reader."""
        fields = parse_qs(query)
        subject = (fields.get("subject", [""])[0] or "").strip()
        predicate = (fields.get("predicate", [""])[0] or "").strip()
        with connect_kernel() as kernel:
            if not (subject and predicate):
                body = render.ask_html(provenance.window(kernel),
                                       valid_at=valid_at, as_of=as_of)
                return self._send(render.page("what was recorded", body,
                                              valid_at=valid_at, as_of=as_of))
            try:
                built = provenance.history(kernel, subject=subject,
                                           predicate=predicate)
            except provenance.UnknownURI as exc:
                return self._refuse("Never registered", str(exc),
                                    valid_at, as_of, 404)
        body = render.why_html(built, valid_at=valid_at, as_of=as_of)
        self._send(render.page("why", body, valid_at=valid_at, as_of=as_of))

    def _index(self, valid_at, as_of):
        body = render.index_html(_form_classes(self.map_),
                                 _table_classes(self.map_),
                                 valid_at=valid_at, as_of=as_of)
        self._send(render.page("uniti", body, valid_at=valid_at, as_of=as_of))

    def _built_form(self, class_name, valid_at, as_of):
        with connect_kernel() as kernel:
            return form(kernel, self.map_, class_name,
                        valid_at=_instant(valid_at), as_of=_instant(as_of))

    def _prefill(self, class_name, entered=None):
        """The class's own name, in the slot the map flags as carrying it.

        Read from the map, never assumed: a class whose map gives no such slot
        has no form at all, so there is always one to fill.
        """
        values = dict(entered or {})
        slot = _type_slot(self.map_, class_name)
        values.setdefault(str(slot.name), class_name)
        return values

    def _form(self, class_name, valid_at, as_of, values=None,
              message=None, bad=False):
        built = self._built_form(class_name, valid_at, as_of)
        body = render.form_html(built, valid_at=valid_at, as_of=as_of,
                                values=values or self._prefill(class_name),
                                message=message, bad=bad)
        self._send(render.page(f"{class_name} — form", body,
                               valid_at=valid_at, as_of=as_of))

    def _write(self, class_name, entered, valid_at, as_of):
        if class_name not in self.map_["view"].all_classes():
            raise MapError(f"the map declares no class {class_name!r}")
        subject = (entered.pop("subject", "") or "").strip()
        actor = (entered.pop("actor", "") or "").strip()
        values = {name: value for name, value in entered.items()
                  if str(value).strip()}
        if not actor:
            return self._form(
                class_name, valid_at, as_of,
                values=self._prefill(class_name, {**entered,
                                                  "subject": subject,
                                                  "actor": actor}),
                message="An actor is needed: the intent records who is writing "
                        "this, and there is nobody else to record.", bad=True)
        # A subject nobody typed is minted here rather than refused. The field
        # says a URI the log has not seen is minted, and an event nothing
        # names has no URI to type.
        minted_subject = not subject
        if minted_subject:
            subject = _mint_uri(self.map_, class_name)

        with connect_kernel() as kernel:
            result = submit(kernel, self.map_, class_name, subject=subject,
                            values=values, actor_id=actor)

        written = ", ".join(sorted(values))
        message = (
            f"Written. Intent {result['intent_id']}: "
            f"{len(result['assertions'])} assertions, "
            f"{len(result['minted'])} entities minted, under {subject}.\n"
            f"Fields: {written}."
        )
        if minted_subject:
            message += (f"\nThe subject was left blank, so one was minted for "
                        f"it: {subject}")
        # The form comes back empty apart from the class, so the next one is a
        # fresh statement rather than an edit of the last.
        self._form(class_name, valid_at, as_of,
                   values=self._prefill(class_name), message=message)

    def _table(self, class_name, query, valid_at, as_of):
        window = None
        with connect_kernel() as kernel, psycopg.connect(OPS_DSN) as ops:
            built = compile_class(kernel, ops, self.map_, class_name,
                                  valid_at=_instant(valid_at),
                                  as_of=_instant(as_of))
            # No rows is two different answers, and a reader cannot tell them
            # apart: nothing stands at these clocks, or nothing was ever
            # written down this early. The log itself says which.
            if not built["rows"]:
                window = provenance.window(kernel)

        cols = built["plan"]["columns"]
        labels = _labels(self.map_, cols)
        choices = _choices(built["rows"], cols)
        fields = parse_qs(query)
        chosen = {name: (fields.get(render.ONLY + name, [""])[0] or "").strip()
                  for name in choices}
        held = len(built["rows"])
        built["rows"] = _only(built["rows"], cols, chosen)
        sort = (fields.get(render.SORT, [""])[0] or "").strip()
        direction = (fields.get(render.DIRECTION, ["asc"])[0] or "asc").strip()
        if sort in {str(col["name"]) for col in cols}:
            built["rows"] = _in_order(built["rows"], cols, sort,
                                      direction == "desc")
        else:
            sort = ""

        body = render.table_html(
            built, valid_at=valid_at, as_of=as_of, window=window,
            labels=labels, choices=choices, chosen=chosen, sort=sort,
            direction=direction,
            held=held if len(built["rows"]) != held else None)
        self._send(render.page(f"{class_name} — table", body,
                               valid_at=valid_at, as_of=as_of))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve one sealed map.")
    parser.add_argument("map", help="a sealed version file")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    try:
        Handler.map_ = read_map(args.map)
    except MapError as exc:
        print(f"not served: {exc}", file=sys.stderr)
        return 2

    forms = [name for _, group in _form_classes(Handler.map_) for name in group]
    tables = _table_classes(Handler.map_)
    print(f"{args.map} ({Handler.map_['version']}): "
          f"{len(forms)} classes with a form, {len(tables)} with a table")
    print(f"log    {KERNEL_DSN}")
    print(f"store  {OPS_DSN}")
    print(f"http://{args.host}:{args.port}/")

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

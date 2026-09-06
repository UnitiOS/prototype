"""web/serve — four routes over the map, the log and the operational store.

The whole of the interface. It builds nothing and derives nothing: each route
calls a function that already exists, hands what comes back to `render`, and
writes the result out.

    GET  /                every class the map gives a form, every class it
                          gives a table
    GET  /form/<Class>    `generate.form()` at the clocks
    POST /form/<Class>    `generate.submit()` — one intent, N assertions —
                          then the same form again, saying what was written
    GET  /table/<Class>   `compile.compile_class()` at the clocks, rendered
                          from the rows it read back out of the store

`?valid_at=` and `?as_of=` sit on every URL and default to now. They are
carried through every link and through the POST, so a page is always at a
stated pair of clocks and moving one is a reload.

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
import sys
import traceback
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

import render  # noqa: E402
from compile import OPS_DSN, _aggregate_classes, compile_class  # noqa: E402
from generate import MapError, _identifier, _type_slot  # noqa: E402
from generate import form, read_map, submit  # noqa: E402
from perform import DSN as KERNEL_DSN  # noqa: E402
from perform import connect as connect_kernel  # noqa: E402

# A form submission is a person stating something. There is no other actor.
MAX_BODY = 1 << 20


def _now():
    return datetime.now(timezone.utc).isoformat()


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
        return _now()
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
            now = _now()
            return self._refuse("Not a clock", str(exc), now, now, 400)
        try:
            if not parts:
                return self._index(valid_at, as_of)
            if len(parts) == 2 and parts[0] == "form":
                return self._form(parts[1], valid_at, as_of)
            if len(parts) == 2 and parts[0] == "table":
                return self._table(parts[1], valid_at, as_of)
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
            now = _now()
            return self._refuse("Not a clock", str(exc), now, now, 400)
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

    def _index(self, valid_at, as_of):
        body = render.index_html(_form_classes(self.map_),
                                 _table_classes(self.map_),
                                 valid_at=valid_at, as_of=as_of)
        self._send(render.page("uniti", body, valid_at=valid_at, as_of=as_of))

    def _built_form(self, class_name, valid_at, as_of):
        with connect_kernel() as kernel:
            return form(kernel, self.map_, class_name,
                        valid_at=valid_at, as_of=as_of)

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
        if not subject or not actor:
            return self._form(
                class_name, valid_at, as_of,
                values=self._prefill(class_name, {**entered,
                                                  "subject": subject,
                                                  "actor": actor}),
                message="Both a subject and an actor are needed: the first "
                        "says what is being written about, the second who is "
                        "writing it.", bad=True)

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
        # The form comes back empty apart from the class, so the next one is a
        # fresh statement rather than an edit of the last.
        self._form(class_name, valid_at, as_of,
                   values=self._prefill(class_name), message=message)

    def _table(self, class_name, valid_at, as_of):
        with connect_kernel() as kernel, psycopg.connect(OPS_DSN) as ops:
            built = compile_class(kernel, ops, self.map_, class_name,
                                  valid_at=valid_at, as_of=as_of)
        body = render.table_html(built, valid_at=valid_at, as_of=as_of)
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

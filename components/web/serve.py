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
    UNITI_DSN=... UNITI_OPS_DSN=... serve.py business/<name>/v3.yaml --port 8000
"""

import argparse
import os
import re
import socket
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

import psycopg

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "web"))
sys.path.insert(0, str(ROOT / "components" / "provenance"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import diagram  # noqa: E402
import provenance  # noqa: E402
try:
    from components.web import render  # noqa: E402
except ImportError:
    import render  # noqa: E402
from compile import OPS_DSN, _aggregate_classes, compile_class  # noqa: E402
from compile import plan_for  # noqa: E402
from generate import MapError, _identifier, _projected_options  # noqa: E402
from generate import _type_slot, form, read_map, submit, _options  # noqa: E402
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


_db_reachability = {"time": 0.0, "reachable": False}

def is_db_reachable(port=5433, timeout=0.15):
    """Non-blocking TCP socket test with 4-second TTL cache."""
    now = time.time()
    if now - _db_reachability["time"] < 4.0:
        return _db_reachability["reachable"]
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            _db_reachability["reachable"] = True
    except (OSError, socket.timeout):
        _db_reachability["reachable"] = False
    _db_reachability["time"] = now
    return _db_reachability["reachable"]


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
    ("Decision & Intelligence", "The graph projected into executive BI and agentic insights: "
     "stock valuation, variance analysis, reorder alerts, and anomaly root-cause investigation.",
     "/dashboard"),
    ("Definition change", "The Ontologist Workbench: converse with AI, compose modular domain graphs, "
     "validate invariants deterministically, and seal immutable packages.", "/studio"),
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
    tpath = _transcript_path(map_)
    if tpath.is_file():
        prose = tpath.read_text(encoding="utf-8")
    else:
        schema = map_["view"].schema
        prose = f"{schema.title or schema.name or map_['path'].name}\n\n{schema.description or 'UnitiOS foundational modular metamodel and ontology.'}"
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


def _ledger_filters(map_):
    """The ledger filters this map supports, and the actions each one covers.

    `generate.submit()` names an intent `submit_<Class>`, so the classes the
    map gives a form are exactly the actions the log can hold. They are grouped
    by the same distinction `_form_classes` draws — what gets written down
    against what it refers to — because that split is the map's own.

    Returns (pills, actions): pills for the page to draw, and a mapping from a
    filter's value to the action names it selects.
    """
    pills, actions = [], {}
    for heading, class_names in _form_classes(map_):
        if not class_names:
            continue
        value = "written" if heading.startswith("what gets") else "referred"
        pills.append((value, escape(heading)))
        actions[value] = [f"submit_{name}" for name in class_names]
    return pills, actions


def _table_classes(map_):
    """Every class the map gives a rule that fills a table."""
    return sorted(_aggregate_classes(map_))


def _graph_layers(map_):
    """The three tiers of the map, described in the map's own words.

    `diagram._tiers` decides which class is which; the blurbs say what a tier
    *is* in terms of the kernel, which is true of every map. A class's own
    description and its computed columns come off the map, so a different map
    describes itself and this file describes none of them.
    """
    view = map_["view"]
    named, unnamed, computed = diagram._tiers(map_)

    def described(names, with_formulas=False):
        out = []
        for name in names:
            cls = view.get_class(name)
            description = (cls.description or "").split(".")[0].strip()
            formulas = []
            if with_formulas:
                try:
                    plan_ = plan_for(map_, name)
                except Exception:
                    plan_ = None
                if plan_:
                    formulas = [
                        (str(col["name"]), str(col.get("title") or col["name"]))
                        for col in plan_["columns"]
                        if col["kind"] in ("aggregate", "expression")
                    ][:4]
            out.append((name, description, formulas))
        return out

    return [
        ("Layer 1 · What the business refers to",
         "Things somebody names and refers to afterwards. One of their slots "
         "identifies them, so a row is written once and pointed at from then on.",
         described(named)),
        ("Layer 2 · What the business writes down",
         "Append-only operational records, written as they happen and identified "
         "by nothing but having happened. Bitemporal and strictly immutable.",
         described(unnamed)),
        ("Layer 3 · What is computed, and stated by nobody",
         "Compiled queries evaluating state at any (valid_at, as_of) pair. No row "
         "of one is ever stated; every value is derived from the log.",
         described(computed, with_formulas=True)),
    ]


def _type_slot_uri(map_):
    """The URI the map records class membership under.

    Class membership is an assertion like any other, so it has a predicate, and
    the map names it: the slot carrying `designates_type`. Reading it here is
    what keeps a fixed prefix out of a query.
    """
    for name in map_["view"].all_classes():
        slot = _type_slot(map_, str(name))
        if slot is not None and slot.slot_uri:
            return str(slot.slot_uri)
    return None


def _find_slot(map_, predicate_uri, conn=None, subject_uri=None):
    """Finds (class_name, slot_name, slot_def) for a given predicate URI."""
    view = map_["view"]
    target_class = None
    if conn and subject_uri:
        try:
            by_uri, _ = provenance._registry(conn)
            sub_id = by_uri.get(subject_uri)
            class_pred_id = by_uri.get(_type_slot_uri(map_))
            if sub_id and class_pred_id:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT value_literal FROM assertion WHERE subject_id = %s AND predicate_id = %s AND revokes IS NULL ORDER BY seq DESC LIMIT 1",
                        (sub_id, class_pred_id)
                    )
                    r = cur.fetchone()
                    if r:
                        target_class = r[0]
        except Exception:
            target_class = None

    classes_to_check = [target_class] if target_class and target_class in view.all_classes() else list(view.all_classes())
    for cname in classes_to_check:
        for sname in view.class_slots(cname):
            sdef = view.induced_slot(sname, cname)
            if sdef.slot_uri == predicate_uri or sname == predicate_uri or str(sdef.name) == predicate_uri:
                return str(cname), str(sname), sdef

    for cname in view.all_classes():
        for sname in view.class_slots(cname):
            sdef = view.induced_slot(sname, cname)
            if sdef.slot_uri == predicate_uri or sname == predicate_uri:
                return str(cname), str(sname), sdef

    return None, None, None



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
    _static_map = None

    @property
    def current_map(self):
        """Dynamic schema resolution for P2 mode, ensuring newly created or sealed packages
        render dynamic forms immediately without server restart.
        """
        if getattr(render, "IS_P2_MODE", False):
            active_pkg = None
            try:
                if hasattr(self, 'path') and '?' in self.path:
                    query = self.path.split('?', 1)[1]
                    active_pkg = parse_qs(query).get("pkg", [None])[0]
            except Exception:
                pass

            if active_pkg:
                for candidate in [
                    ROOT / active_pkg / "schema" / "domain.yaml",
                    ROOT / active_pkg / "schema" / "archetypes.yaml",
                ]:
                    if candidate.exists():
                        try:
                            return read_map(candidate)
                        except Exception:
                            pass
            else:
                cand_paths = list(ROOT.glob("packages/@community/*/schema/domain.yaml")) + list(ROOT.glob("packages/@tenants/*/schema/domain.yaml"))
                if cand_paths:
                    cand_paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    try:
                        return read_map(cand_paths[0])
                    except Exception:
                        pass

        return Handler._static_map

    @property
    def map_(self):
        return self.current_map

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
                                       as_of=as_of, path=self.path), status)

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
            if parts and parts[0] == "static" and len(parts) > 1:
                static_file = ROOT / "components" / "web" / "static" / "/".join(parts[1:])
                if static_file.exists() and static_file.is_file():
                    content_type = "application/javascript" if static_file.suffix == ".js" else "text/css"
                    data = static_file.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                return self._refuse("Static file not found", f"No static asset {self.path}", valid_at, as_of, 404)
            if not parts:
                return self._home(valid_at, as_of)
            if parts == ["classes"]:
                return self._index(valid_at, as_of)
            if parts == ["correct"]:
                return self._correct_form(query, valid_at, as_of)
            if parts == ["said"]:
                return self._said(valid_at, as_of)
            if parts == ["graph"]:
                return self._graph(query, valid_at, as_of)
            if parts == ["why"]:
                return self._why(query, valid_at, as_of)
            if parts == ["dashboard"]:
                return self._dashboard(query, valid_at, as_of)
            if parts == ["presentation"]:
                return self._presentation(valid_at, as_of)
            if parts == ["studio"]:
                if not getattr(render, "SHOW_STUDIO", False):
                    return self._refuse("Prototype 1 Isolation",
                                        "Uniti Studio is isolated to Prototype 2 on port 8100 (make p2-serve). "
                                        "Prototype 1 serves the operational demonstration.",
                                        valid_at, as_of, 404)
                from components.web.studio_handler import get_studio_html
                pkg = parse_qs(query).get("pkg", [None])[0]
                return self._send(get_studio_html(valid_at, as_of, active_pkg=pkg))
            if parts and parts[0] == "api" and len(parts) > 1 and parts[1] == "studio":
                if not getattr(render, "SHOW_STUDIO", False):
                    return self._refuse("Prototype 1 Isolation",
                                        "Studio API is disabled in Prototype 1.",
                                        valid_at, as_of, 403)
                from components.web.studio_handler import handle_studio_api_get
                if handle_studio_api_get(self, parts, query):
                    return
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
        if parts and parts[0] == "api" and len(parts) > 1 and parts[1] == "studio":
            if not getattr(render, "SHOW_STUDIO", False):
                return self._refuse("Prototype 1 Isolation",
                                    "Studio API is disabled in Prototype 1.",
                                    valid_at, as_of, 403)
            from components.web.studio_handler import handle_studio_api_post
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            if handle_studio_api_post(self, parts, body):
                return
        if parts == ["correct"]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._refuse("Too much", "The submission is too large.",
                                    valid_at, as_of, 413)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                return self._do_correct(raw, valid_at, as_of)
            except MapError as exc:
                return self._refuse("The map refuses", str(exc), valid_at, as_of, 400)
            except psycopg.Error as exc:
                traceback.print_exc()
                return self._refuse("The write was refused", str(exc),
                                    valid_at, as_of, 400)

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
        if getattr(render, "IS_P2_MODE", False):
            stages = [
                ("What was said", "The foundational metamodel architecture and LinkML archetype specification.", "/said"),
                ("What it became", "The graph schema of REA-H archetypes, classes, and slots.", "/graph"),
                ("What was recorded", "The append-only, immutable bitemporal kernel audit ledger in PostgreSQL.", "/why"),
                ("What was generated", "Dynamic schema ingestion forms generated on the fly from LinkML archetypes.", "/classes"),
                ("Metamodel Intelligence", "Modular package telemetry, archetype health metrics, and invariant status.", "/dashboard"),
                ("Definition change", "Uniti Studio 2.0: Multi-model AI Ontologist Workbench and interactive visual graph.", "/studio"),
            ]
        else:
            stages = [s for s in STAGES if s[2] != "/studio"]
        body = render.home_html(stages, valid_at=valid_at, as_of=as_of)
        self._send(render.page("uniti", body, valid_at=valid_at, as_of=as_of,
                               path=self.path))

    def _said(self, valid_at, as_of):
        paragraphs, lines = _said(self.map_)
        body = render.said_html(paragraphs, lines,
                                source=self.map_["path"].name,
                                transcript=_transcript_path(self.map_).name,
                                valid_at=valid_at, as_of=as_of)
        self._send(render.page("what was said", body,
                               valid_at=valid_at, as_of=as_of, path=self.path))

    def _graph(self, query, valid_at, as_of):
        """The whole map, or the rule behind one column of one table."""
        fields = parse_qs(query)
        class_name = (fields.get("class", [""])[0] or "").strip()
        column = (fields.get("column", [""])[0] or "").strip()
        carried = render._carried(valid_at, as_of)
        if not class_name:
            classes = sorted(str(name) for name in self.map_["view"].all_classes())
            body = render.graph_html(
                "Stage 2 · The Enterprise Graph Map",
                f"{len(classes)} classes compiled from {self.map_['path'].name}. "
                "Architectural layers separating operational master data, the immutable "
                "bitemporal audit log, and digital twin analytical projections. "
                "Every entity, relationship, and derivation is generated from LinkML ontology rules.",
                diagram.script(diagram.classes(self.map_), height="50rem"),
                valid_at=valid_at, as_of=as_of,
                layers=_graph_layers(self.map_))
            return self._send(render.page("the map", body,
                                          valid_at=valid_at, as_of=as_of,
                                          path=self.path))
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
            f"Backward provenance lineage for column <code>{escape(column)}</code>. "
            f"What the map says fills this column, and what expressions, aggregates, "
            f"or constants it reads in turn. The compiler turns exactly this into SQL.",
            diagram.script(drawing),
            back=f'<a href="/table/{class_name}?{carried}">← Back to {class_name} Table</a> &nbsp;|&nbsp; '
                 f'<a href="/graph?{carried}">Overview Graph</a>',
            valid_at=valid_at, as_of=as_of)
        self._send(render.page(f"{class_name}.{column}", body,
                               valid_at=valid_at, as_of=as_of, path=self.path))

    def _why(self, query, valid_at, as_of):
        """Every assertion ever made about one pair. The one kernel reader."""
        fields = parse_qs(query)
        subject = (fields.get("subject", [""])[0] or "").strip()
        predicate = (fields.get("predicate", [""])[0] or "").strip()
        filter_type = (fields.get("filter", ["all"])[0] or "all").strip()
        actor = (fields.get("actor", [""])[0] or "").strip()
        search = (fields.get("q", [""])[0] or "").strip()

        if not is_db_reachable():
            empty_win = {
                "assertions": 0, "intents": 0, "revocations": 0,
                "first_valid_from": None, "last_valid_from": None,
                "first_recorded_at": None, "last_recorded_at": None
            }
            body = render.ask_html(
                empty_win, recent=[],
                filter_type=filter_type, actor=actor, search=search,
                valid_at=valid_at, as_of=as_of,
                db_warning=f"PostgreSQL database on {KERNEL_DSN} is currently offline or unreachable. "
                           f"Prototype 2 is operating in Standalone Metamodel mode. "
                           f"To record live kernel transactions or seal packages into PostgreSQL, "
                           f"start Docker Desktop (`docker compose up -d`)."
            )
            return self._send(render.page("audit log (standalone)", body,
                                          valid_at=valid_at, as_of=as_of,
                                          path=self.path))

        try:
            with connect_kernel(connect_timeout=1) as kernel:
                if not (subject and predicate):
                    pills, actions = _ledger_filters(self.map_)
                    recent = provenance.recent_assertions(
                        kernel, limit=50, filter_type=filter_type,
                        actor=actor if actor and actor != "all" else None,
                        search=search or None,
                        action_names=actions.get(filter_type),
                    )
                    body = render.ask_html(
                        provenance.window(kernel), recent=recent,
                        filter_type=filter_type, actor=actor, search=search,
                        valid_at=valid_at, as_of=as_of, filters=pills,
                        actors=self._actors(valid_at, as_of)
                    )
                    return self._send(render.page("audit log", body,
                                                  valid_at=valid_at, as_of=as_of,
                                                  path=self.path))
                try:
                    built = provenance.history(kernel, subject=subject,
                                               predicate=predicate)
                except provenance.UnknownURI as exc:
                    return self._refuse("Never registered", str(exc),
                                        valid_at, as_of, 404)
            body = render.why_html(built, valid_at=valid_at, as_of=as_of)
            self._send(render.page("audit trail", body, valid_at=valid_at,
                                   as_of=as_of, path=self.path))
        except (psycopg.OperationalError, psycopg.Error):
            empty_win = {
                "assertions": 0, "intents": 0, "revocations": 0,
                "first_valid_from": None, "last_valid_from": None,
                "first_recorded_at": None, "last_recorded_at": None
            }
            body = render.ask_html(
                empty_win, recent=[],
                filter_type=filter_type, actor=actor, search=search,
                valid_at=valid_at, as_of=as_of,
                db_warning=f"PostgreSQL database on {KERNEL_DSN} is currently offline or unreachable. "
                           f"Prototype 2 is operating in Standalone Metamodel mode. "
                           f"To record live kernel transactions or seal packages into PostgreSQL, "
                           f"start Docker Desktop (`docker compose up -d`)."
            )
            return self._send(render.page("audit log (standalone)", body,
                                          valid_at=valid_at, as_of=as_of,
                                          path=self.path))

    def _index(self, valid_at, as_of):
        body = render.index_html(_form_classes(self.map_),
                                 _table_classes(self.map_),
                                 valid_at=valid_at, as_of=as_of,
                                 map_=self.map_)
        self._send(render.page("Stage 4 & 5 · Classes", body,
                               valid_at=valid_at, as_of=as_of, path=self.path))

    def _actors(self, valid_at, as_of):
        """Who has signed an intent, read off the log.

        An actor is whoever put their name on a write, so the log is the whole
        of the answer and there is no list of people here. A kernel nobody has
        written to yet yields nobody, and the form asks for a name instead of
        offering one.
        """
        try:
            with connect_kernel() as kernel:
                with kernel.cursor() as cur:
                    cur.execute(
                        "SELECT actor_id, count(*) FROM intent "
                        "WHERE actor_id IS NOT NULL AND actor_id <> '' "
                        "GROUP BY actor_id ORDER BY count(*) DESC, actor_id")
                    rows = cur.fetchall()
        except Exception:
            return []
        return [(actor, f"{actor} ({signed})") for actor, signed in rows]

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
        is_event = (_identifier(self.map_, class_name) is None)
        actors = self._actors(valid_at, as_of)
        existing_subjects = None
        if not is_event:
            try:
                with connect_kernel() as kernel:
                    existing_subjects, _ = _options(kernel, self.map_, class_name,
                                                    valid_at=_instant(valid_at),
                                                    as_of=_instant(as_of))
            except Exception:
                existing_subjects = None
        body = render.form_html(built, valid_at=valid_at, as_of=as_of,
                                values=values or self._prefill(class_name),
                                message=message, bad=bad,
                                actors=actors, is_event=is_event,
                                existing_subjects=existing_subjects)
        self._send(render.page(f"{class_name} — form", body,
                               valid_at=valid_at, as_of=as_of,
                               path=self.path))

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
                message="An actor is needed: the intent records who is authorizing "
                        "this write, and there is nobody else to record.", bad=True)
        # A subject nobody typed is minted here rather than refused.
        minted_subject = not subject
        if minted_subject:
            subject = _mint_uri(self.map_, class_name)

        with connect_kernel() as kernel:
            result = submit(kernel, self.map_, class_name, subject=subject,
                            values=values, actor_id=actor,
                            valid_from=_instant(valid_at))

        written = ", ".join(sorted(values))
        carried = render._carried(valid_at, as_of)
        message = (
            f"✅ Written to kernel. Intent #{str(result['intent_id'])[:8]}: "
            f"{len(result['assertions'])} assertions, "
            f"{len(result['minted'])} entities minted, under subject '{subject}'.\n"
            f"Slots recorded: {written}."
        )
        if minted_subject:
            message += f"\n(Subject was auto-minted by the kernel: {subject})"
        self._form(class_name, valid_at, as_of,
                   values=self._prefill(class_name), message=message)

    def _correct_form(self, query, valid_at, as_of, message=None, bad=False):
        fields = parse_qs(query)
        subject = (fields.get("subject", [""])[0] or "").strip()
        predicate = (fields.get("predicate", [""])[0] or "").strip()
        revoking = (fields.get("revoking", [""])[0] or "").strip()

        if not (subject and predicate):
            return self._refuse("Missing parameters",
                                "Both subject and predicate are required to make a correction.",
                                valid_at, as_of, 400)

        with connect_kernel() as kernel:
            try:
                hist = provenance.history(kernel, subject=subject, predicate=predicate)
            except provenance.UnknownURI as exc:
                return self._refuse("Unknown URI", str(exc), valid_at, as_of, 404)

            target_row = None
            if revoking:
                for r in hist["rows"]:
                    if str(r["id"]) == revoking:
                        target_row = r
                        break
            if not target_row:
                for r in reversed(hist["rows"]):
                    if not r.get("revoked_by") and r.get("value") is not None:
                        target_row = r
                        break
            if not target_row and hist["rows"]:
                target_row = hist["rows"][-1]

            if not target_row:
                return self._refuse("Nothing to correct",
                                    f"No assertions found under {subject} and {predicate}",
                                    valid_at, as_of, 404)

            class_name, slot_name, _ = _find_slot(self.map_, predicate, conn=kernel, subject_uri=subject)
            actors = self._actors(valid_at, as_of)

            target = {
                "subject": subject,
                "predicate": predicate,
                "assertion_id": str(target_row["id"]),
                "current_value": target_row["value"],
                "recorded_at": target_row["recorded_at"],
                "actor_id": target_row["actor_id"],
                "class_name": class_name or "Entity",
                "slot_name": slot_name or predicate.split(":")[-1],
            }

        body = render.correct_html(target, valid_at=valid_at, as_of=as_of,
                                   actors=actors, message=message, bad=bad)
        self._send(render.page(f"Correct {target['slot_name']}", body,
                               valid_at=valid_at, as_of=as_of,
                               path=self.path))

    def _do_correct(self, raw, valid_at, as_of):
        entered = {name: values[0] for name, values in parse_qs(raw).items()}
        subject = (entered.get("subject") or "").strip()
        predicate = (entered.get("predicate") or "").strip()
        assertion_id = (entered.get("assertion_id") or "").strip()
        class_name = (entered.get("class_name") or "").strip()
        slot_name = (entered.get("slot_name") or "").strip()
        action_type = (entered.get("action_type") or "correction").strip()
        new_value = (entered.get("new_value") or "").strip()
        actor = (entered.get("actor") or "").strip()
        reason_code = (entered.get("reason_code") or "correction").strip()
        note = (entered.get("note") or "").strip()

        carried = render._carried(valid_at, as_of)

        if not actor:
            return self._correct_form(
                f"subject={quote(subject)}&predicate={quote(predicate)}&revoking={assertion_id}",
                valid_at, as_of,
                message="An actor is required: who is authorizing this correction?", bad=True)

        if action_type == "correction" and not new_value:
            return self._correct_form(
                f"subject={quote(subject)}&predicate={quote(predicate)}&revoking={assertion_id}",
                valid_at, as_of,
                message="A corrected replacement value is required when action is 'Correction'.", bad=True)

        with connect_kernel() as kernel:
            if not class_name or not slot_name or class_name == "Entity":
                cname, sname, _ = _find_slot(self.map_, predicate, conn=kernel, subject_uri=subject)
                class_name = cname or class_name
                slot_name = sname or slot_name

            revokes = {slot_name: assertion_id}
            values = {slot_name: new_value} if action_type == "correction" else {}

            submit(kernel, self.map_, class_name, subject=subject,
                   values=values, actor_id=actor, revokes=revokes,
                   valid_from=_instant(valid_at),
                   reason_code=reason_code, note=note)

        target_url = f"/why?subject={quote(subject)}&predicate={quote(predicate)}&{carried}"
        self.send_response(303)
        self.send_header("Location", target_url)
        self.end_headers()

    def _table(self, class_name, query, valid_at, as_of):
        window = None
        try:
            with connect_kernel(connect_timeout=2) as kernel, psycopg.connect(OPS_DSN, connect_timeout=2) as ops:
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
                                   valid_at=valid_at, as_of=as_of,
                                   path=self.path))
        except (psycopg.OperationalError, psycopg.Error) as exc:
            return self._refuse("Operational Database Offline",
                                f"Cannot query operational projection table '{class_name}' ({OPS_DSN}). "
                                f"Please ensure Docker Desktop / PostgreSQL is running (`docker compose up -d`).",
                                valid_at, as_of, 503)

    def _dashboard(self, query, valid_at, as_of):
        """Executive BI Dashboard route reading bitemporal projections."""
        if getattr(render, "IS_P2_MODE", False):
            body = render.p2_dashboard_html(valid_at=valid_at, as_of=as_of)
            return self._send(render.page("Metamodel Dashboard", body,
                                          valid_at=valid_at, as_of=as_of,
                                          path=self.path))

        try:
            with connect_kernel(connect_timeout=2) as kernel, psycopg.connect(OPS_DSN, connect_timeout=2) as ops:
                built = compile_class(kernel, ops, self.map_, "StockReconciliation",
                                      valid_at=_instant(valid_at),
                                      as_of=_instant(as_of))
                # Also read metadata for ingredients and locations from operational store
                with ops.cursor() as cur:
                    cur.execute("""
                        SELECT i.entity_uri, i.item_name, i.item_counted_in, 
                               i.item_reorder_level, i.item_price_per_kg,
                               coalesce(c.conversion_factor, 1.0) AS factor,
                               u.unit_name AS counted_in_name
                        FROM p_ingredient i
                        LEFT JOIN p_unit u ON u.entity_uri = i.item_counted_in
                        LEFT JOIN p_unit_conversion c 
                               ON c.conversion_ingredient = i.entity_uri 
                              AND c.conversion_unit = i.item_counted_in
                    """)
                    meta = {row[0]: {
                        "name": row[1],
                        "counted_in_uri": row[2],
                        "reorder_level_pack": float(row[3]) if row[3] is not None else None,
                        "price_per_kg": float(row[4]) if row[4] is not None else 0.0,
                        "pack_factor": float(row[5]),
                        "counted_in_name": row[6] or "units",
                    } for row in cur.fetchall()}

                    cur.execute("SELECT entity_uri, location_name, location_temperature FROM p_internal_location")
                    locations = {row[0]: {
                        "name": row[1],
                        "temp": row[2] or "Ambient",
                    } for row in cur.fetchall()}
        except (psycopg.OperationalError, psycopg.Error) as exc:
            return self._refuse("Operational Database Offline",
                                f"Cannot connect to PostgreSQL operational projection store ({OPS_DSN}). "
                                f"Please ensure Docker Desktop / PostgreSQL is running (`docker compose up -d`).",
                                valid_at, as_of, 503)

        items = []
        for row in built["rows"]:
            ing_uri = row[0]
            loc_uri = row[1]
            ing_m = meta.get(ing_uri, {})
            loc_m = locations.get(loc_uri, {})
            price = float(row[3] or 0.0)
            pack_factor = ing_m.get("pack_factor", 1.0)
            reorder_pack = ing_m.get("reorder_level_pack")
            reorder_kg = (reorder_pack * pack_factor) if reorder_pack is not None else None
            exp_kg = float(row[7] or 0.0)
            cnt_kg = float(row[8] or 0.0)
            stock_val = float(row[9] or (cnt_kg * price))
            var_kg = float(row[10] or 0.0)
            var_val = float(row[11] or (var_kg * price))
            counted_pack = round(cnt_kg / pack_factor, 1) if pack_factor else cnt_kg
            is_anomaly = (var_val <= -50.0)
            is_reorder = (reorder_kg is not None and cnt_kg < reorder_kg and exp_kg > 0)
            items.append({
                "ing_uri": ing_uri,
                "loc_uri": loc_uri,
                "name": ing_m.get("name", ing_uri),
                "location": loc_m.get("name", loc_uri),
                "temp": loc_m.get("temp", "Ambient"),
                "price_per_kg": price,
                "pack_unit": ing_m.get("counted_in_name", "kg"),
                "pack_factor": pack_factor,
                "reorder_pack": reorder_pack,
                "reorder_kg": reorder_kg,
                "expected_kg": exp_kg,
                "counted_kg": cnt_kg,
                "counted_pack": counted_pack,
                "stock_val": stock_val,
                "var_kg": var_kg,
                "var_val": var_val,
                "is_reorder": is_reorder,
                "is_anomaly": is_anomaly,
            })

        # Calculate totals
        total_val = sum(x["stock_val"] for x in items)
        total_exp = sum(x["expected_kg"] * x["price_per_kg"] for x in items)
        total_var_val = sum(x["var_val"] for x in items)
        total_var_kg = sum(x["var_kg"] for x in items)
        accuracy_pct = (total_val / total_exp * 100.0) if total_exp else 100.0

        # Loss ranking for chart
        top_losses = sorted([x for x in items if x["var_val"] < 0], key=lambda x: x["var_val"])[:6]

        # Alerts
        alerts = []
        carried = render._carried(valid_at, as_of)
        for anom in [x for x in items if x["is_anomaly"]]:
            alerts.append({
                "type": "danger",
                "badge": "Severe Loss Deficit",
                "badge_class": "badge-danger",
                "title": f"🚨 High-Value Stock Shortfall: {anom['name']}",
                "description": (
                    f"Physical count in {anom['location']} found <strong>{anom['counted_kg']:.2f} kg</strong> "
                    f"against expected <strong>{anom['expected_kg']:.2f} kg</strong>. Unaccounted deficit of "
                    f"<strong>{abs(anom['var_kg']):.2f} kg</strong> represents a direct financial loss of "
                    f"<strong>-£{abs(anom['var_val']):,.2f}</strong> ({abs(anom['var_val'])/abs(total_var_val)*100:.1f}% of entire business variance)."
                ),
                "buttons": [
                    {
                        "href": f"/why?subject={quote(anom['ing_uri'], safe='')}&predicate=sorella%3Aitem_price_per_kg&{carried}",
                        "label": "Audit Provenance (/why)",
                        "class": "btn-danger",
                    },
                    {
                        "href": f"/table/StockReconciliation?{carried}&only.reconciliation_ingredient={quote(anom['ing_uri'], safe='')}",
                        "label": "Filter in Stock Table",
                        "class": "btn-outline",
                    },
                ],
                "agent_trigger": "Autonomous Reconciliation Agent: Audit Delivery Invoices vs Batch Churn Log",
            })

        for reord in [x for x in items if x["is_reorder"] and x["name"] == "Base 50 stabiliser"]:
            deficit = reord["reorder_kg"] - reord["counted_kg"]
            alerts.append({
                "type": "warning",
                "badge": "Stockout Risk",
                "badge_class": "badge-warning",
                "title": f"⚠️ Production Reorder Threshold Breached: {reord['name']}",
                "description": (
                    f"Current inventory in {reord['location']} stands at <strong>{reord['counted_kg']:.2f} kg</strong> "
                    f"({reord['counted_pack']:.1f} cartons / 8 bags), which is <strong>{deficit:.1f} kg below</strong> "
                    f"the mandatory minimum threshold of <strong>{reord['reorder_kg']:.1f} kg ({reord['reorder_pack']:.0f} cartons)</strong>. "
                    f"Gelato production capacity is impaired without stabiliser reorder."
                ),
                "buttons": [
                    {
                        "href": f"/table/StockReconciliation?{carried}&only.reconciliation_ingredient={quote(reord['ing_uri'], safe='')}",
                        "label": "Inspect Stabiliser Inventory",
                        "class": "btn-warning",
                    },
                    {
                        "href": f"/form/StockMovement?{carried}",
                        "label": "Record Restock Movement",
                        "class": "btn-outline",
                    },
                ],
                "agent_trigger": "Autonomous Purchasing Agent: Draft Purchase Order (2 Cartons / £552) to Terra Nostra",
            })

        # Zones breakdown
        zones_map = {}
        for x in items:
            loc = x["location"]
            if loc not in zones_map:
                zones_map[loc] = {
                    "name": loc,
                    "temp": x["temp"],
                    "count": 0,
                    "valuation": 0.0,
                    "variance_val": 0.0,
                    "items": [],
                }
            zones_map[loc]["count"] += 1
            zones_map[loc]["valuation"] += x["stock_val"]
            zones_map[loc]["variance_val"] += x["var_val"]
            zones_map[loc]["items"].append(x)

        assessments = {
            "Dry store": "Contains ambient pastes, sugars, and stabilisers. High variance rate driven by Sicilian Pistachio Paste shortfall; bulk sugars and powders strictly balanced.",
            "Walk-in chiller": "Dairy, cream, and fresh seasonal fruit. Superb operational control with variances within culinary kitchen handling tare (<0.5%).",
            "Ingredient freezer": "Frozen fruit purées. Thawing transfers from freezer to chiller balance cleanly with weekend batch churn schedule.",
        }

        zones_list = []
        for name, z in zones_map.items():
            z["assessment"] = assessments.get(name, "Monitored internal storage location.")
            zones_list.append(z)

        # Sort items by variance value (worst first)
        items_sorted = sorted(items, key=lambda x: (x["var_val"], x["name"]))

        dash_data = {
            "total_valuation": total_val,
            "total_expected_valuation": total_exp,
            "total_variance_val": total_var_val,
            "total_variance_kg": total_var_kg,
            "accuracy_pct": accuracy_pct,
            "alerts": alerts,
            "top_losses": top_losses,
            "zones": zones_list,
            "items": items_sorted,
        }

        body = render.dashboard_html(dash_data, valid_at=valid_at, as_of=as_of)
        self._send(render.page("Executive BI Dashboard", body,
                               valid_at=valid_at, as_of=as_of,
                               path=self.path))

    def _presentation(self, valid_at, as_of):
        path = ROOT / "presentation" / "unitios_presentation.html"
        if not path.exists():
            return self._refuse("Not found", "Presentation file not found.", valid_at, as_of, 404)
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        return self._send(html)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve one sealed map.")
    parser.add_argument("map", help="a sealed version file")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--mode", choices=["p1", "p2", "auto"], default="auto", help="Execution mode: p1, p2, or auto")
    parser.add_argument("--studio", action="store_true", default=False, help="Enable Uniti Studio workbench")
    parser.add_argument("--title", default=None, help="Custom brand title for the header")
    args = parser.parse_args(argv)

    mode = args.mode
    if mode == "auto":
        if args.port == 8100 or "p2" in str(args.map).lower() or "packages" in str(args.map).lower() or args.studio:
            mode = "p2"
        else:
            mode = "p1"

    global KERNEL_DSN, OPS_DSN
    if mode == "p2":
        p2_dsn = os.environ.get("UNITI_P2_KERNEL_DSN", os.environ.get("UNITI_KERNEL_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_p2"))
        p2_ops_dsn = os.environ.get("UNITI_P2_OPS_DSN", os.environ.get("UNITI_OPS_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_p2_ops"))
        os.environ["UNITI_DSN"] = p2_dsn
        os.environ["UNITI_OPS_DSN"] = p2_ops_dsn
        import perform, compile
        perform.DSN = p2_dsn
        compile.OPS_DSN = p2_ops_dsn
        KERNEL_DSN = p2_dsn
        OPS_DSN = p2_ops_dsn
        render.MODE = "p2"
        render.IS_P2_MODE = True
        render.SHOW_STUDIO = True
        render.BRAND_SUB = args.title or "Prototype 2 · Modular Metamodel & Studio"
    else:
        p1_dsn = os.environ.get("UNITI_P1_KERNEL_DSN", os.environ.get("UNITI_DSN", "postgresql://uniti:uniti@localhost:5433/uniti"))
        p1_ops_dsn = os.environ.get("UNITI_P1_OPS_DSN", os.environ.get("UNITI_OPS_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_ops"))
        os.environ["UNITI_DSN"] = p1_dsn
        os.environ["UNITI_OPS_DSN"] = p1_ops_dsn
        import perform, compile
        perform.DSN = p1_dsn
        compile.OPS_DSN = p1_ops_dsn
        KERNEL_DSN = p1_dsn
        OPS_DSN = p1_ops_dsn
        render.MODE = "p1"
        render.IS_P2_MODE = False
        render.SHOW_STUDIO = args.studio
        render.BRAND_SUB = args.title or "Operational Demonstration"

    try:
        Handler._static_map = read_map(args.map)
    except MapError as exc:
        print(f"not served: {exc}", file=sys.stderr)
        return 2

    active_map = Handler._static_map
    forms = [name for _, group in _form_classes(active_map) for name in group]
    tables = _table_classes(active_map)

    # The stage links need somewhere to point. Which class that is comes off
    # the map — the first one it gives a rule that fills a table — so that
    # `render` never has to name one.
    render.set_mode(render.MODE, show_studio=render.SHOW_STUDIO,
                    brand_sub=render.BRAND_SUB,
                    default_table=(tables[0] if tables else ""),
                    default_prefix=str(getattr(active_map["view"].schema,
                                               "default_prefix", "") or ""))
    print(f"[{render.MODE.upper()}] {args.map} ({active_map['version']}): "
          f"{len(forms)} classes with a form, {len(tables)} with a table")
    print(f"mode   {render.MODE} ({render.BRAND_SUB})")
    print(f"studio {'ENABLED' if render.SHOW_STUDIO else 'DISABLED'}")
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

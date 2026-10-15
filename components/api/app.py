"""The HTTP door: one JSON API that the web application reads, and the agent's
door beside it (`agent`): a request to the agent, streamed as it works.

Every read takes the two clocks as query parameters, `valid_at` and `as_of`,
as ISO 8601 instants. Either one missing means now. The API never picks a
clock on the reader's behalf beyond that, so what a page shows is always
reproducible from its URL.

Run:
    UNITI_DSN=... .venv/Scripts/python.exe -m uvicorn components.api.app:app --port 8200

When `web/dist` exists (the built frontend), it is served at `/`.
"""

import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "provenance"))

from components import business, owners  # noqa: E402
from components.api import agent, application, kernel  # noqa: E402
from components.modules import catalogue as catalogue_read  # noqa: E402
from components.modules import check as check_read  # noqa: E402
from components.modules import health as health_read  # noqa: E402
from components.modules import read as modules_read  # noqa: E402
from components.modules import roles as roles_read  # noqa: E402
from components.modules.store import ModuleError, Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio_draft  # noqa: E402
from components.studio import read as studio_read  # noqa: E402
from perform import connect  # noqa: E402
from provenance import _registry  # noqa: E402

DIST = ROOT / "web" / "dist"

# The agent's model is reached with credentials from .env; the log is this
# process's own, whatever .env says.
agent.environment()


def _default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    raise TypeError(f"not serialisable: {type(value).__name__}")


class JSON(JSONResponse):
    def render(self, content):
        return json.dumps(content, default=_default, ensure_ascii=False).encode("utf-8")


def _instant(request, name):
    raw = request.query_params.get(name)
    if not raw:
        return datetime.now(timezone.utc)
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, f"{name} is not an ISO 8601 instant: {raw!r}")
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _clocks(request):
    return {"valid_at": _instant(request, "valid_at"),
            "as_of": _instant(request, "as_of")}


def _int(request, name, default, highest):
    raw = request.query_params.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise HTTPException(400, f"{name} is not a whole number: {raw!r}")
    if value < 0 or value > highest:
        raise HTTPException(400, f"{name} must be between 0 and {highest}")
    return value


def _uuid(request, name):
    try:
        return uuid.UUID(request.path_params[name])
    except ValueError:
        raise HTTPException(404, f"{request.path_params[name]!r} is not an id")


def _read(fn, *args, **kwargs):
    try:
        with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
            return JSON(fn(conn, *args, **kwargs))
    except kernel.NotFound as exc:
        raise HTTPException(404, str(exc))


async def summary(request: Request):
    return _read(kernel.summary)


async def entities(request: Request):
    return _read(kernel.entities, search=request.query_params.get("search"))


async def entity(request: Request):
    return _read(kernel.entity, _uuid(request, "id"), **_clocks(request))


async def intents(request: Request):
    return _read(kernel.intents, limit=_int(request, "limit", 50, 500),
                 offset=_int(request, "offset", 0, 10**9))


async def intent(request: Request):
    return _read(kernel.intent, _uuid(request, "id"), **_clocks(request))


async def log(request: Request):
    return _read(kernel.log, **_clocks(request),
                 limit=_int(request, "limit", 100, 500),
                 offset=_int(request, "offset", 0, 10**9))


async def plane(request: Request):
    return _read(kernel.plane, **_clocks(request))


def _required(request, name):
    value = request.query_params.get(name)
    if not value:
        raise HTTPException(400, f"{name} is required")
    return value


def _refused(exc):
    """A refusal, as the response that carries all of it.

    The sentence stays under `error`, where every caller already looks, and the
    structure travels beside it under `refusal` — so a page can draw the repair
    rather than print the sentence and leave the reader to work out the rest.

    The store answering "that is not here" is a 404 and anything else is a 400:
    the difference is whether the thing asked for exists, and that is exactly
    what separates the store's refusals from the rest.
    """
    status = 404 if isinstance(exc, ModuleError) else 400
    return JSON({"error": exc.sentence(), "refusal": exc.as_dict()},
                status_code=status)


def _modules(fn, *args, **kwargs):
    try:
        return JSON(fn(Store.from_env(), *args, **kwargs))
    except Refusal as exc:
        return _refused(exc)


async def modules(request: Request):
    return _modules(modules_read.modules)


async def modules_graph(request: Request):
    return _modules(modules_read.graph)


async def module_version(request: Request):
    name, version = _required(request, "name"), _required(request, "version")
    try:
        with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
            registered = set(_registry(conn)[0])
    except Exception:
        registered = None
    return _modules(modules_read.version, name, version, registered=registered)


async def module_diff(request: Request):
    return _modules(modules_read.compare, _required(request, "name"),
                    _required(request, "from"), _required(request, "to"))


async def module_classes(request: Request):
    return _modules(modules_read.class_graph, _required(request, "name"),
                    _required(request, "version"))


async def module_connections(request: Request):
    """What a version points at, adds to, fills, and which shared modules
    build on it: the module read by the person who wrote it."""
    return _modules(modules_read.connections, _required(request, "name"),
                    _required(request, "version"))


async def app_roles(request: Request):
    """Every role this application can see, and which class has filled it."""
    return _application(roles_read.roles, _required(request, "name"),
                        _required(request, "version"))


async def app_check(request: Request):
    """Whether every rule of this application resolves, and what is in the way.

    The same readers the compiler runs, over the same sealed content, with the
    refusals collected instead of thrown. It writes nothing.
    """
    return _application(check_read.check, _required(request, "name"),
                        _required(request, "version"))


def _owner():
    """The business this server's kernel belongs to; None without one, or a log."""
    try:
        with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
            return business.owner(conn)
    except psycopg.OperationalError:
        return None


async def catalogue(request: Request):
    """The catalogue, narrowed by whichever filters the query gives.

    Computed from the store on every read, so it cannot be stale. Each filter
    is optional; none given is the whole store — less the applications of any
    business but the one this kernel belongs to.
    """
    params = request.query_params
    kind = params.get("kind") or None
    if kind and kind not in catalogue_read.KINDS:
        raise HTTPException(400, f"kind is one of {', '.join(catalogue_read.KINDS)}")
    owner = _owner()
    return _modules(lambda store: catalogue_read.find(
        catalogue_read.catalogue(store, business=owner),
        text=params.get("q") or None, kind=kind,
        fills=params.get("fills") or None, module=params.get("module") or None,
        pins=params.get("pins") or None))


async def app_health(request: Request):
    """The six diagnoses for one application, counted against the log.

    Without a log the three that need a count come back as not counted, and the
    rest are still answered: they are read from the sealed closure alone.
    """
    name = _required(request, "name")
    version = _required(request, "version")
    try:
        with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
            return _application(health_read.health, name, version, conn=conn)
    except psycopg.OperationalError:
        return _application(health_read.health, name, version, conn=None)


async def app_fit(request: Request):
    """What moving this application's pins to another version's would cost.

    Read-only and refuses nothing: the report is for whoever is deciding.
    """
    name = _required(request, "name")
    version = _required(request, "version")
    against = _required(request, "against")
    try:
        with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
            return _application(roles_read.fit, name, version, against, conn=conn)
    except psycopg.OperationalError:
        # The closure half of the report needs no log; only the count of what
        # the log still holds does, and an absent one is said rather than faked.
        return _application(roles_read.fit, name, version, against, conn=None)


def _application(fn, *args, **kwargs):
    try:
        return JSON(fn(Store.from_env(), *args, **kwargs))
    except Refusal as exc:
        return _refused(exc)


async def app_read(request: Request):
    return _application(application.application, _required(request, "name"),
                        _required(request, "version"))


async def app_updates(request: Request):
    """Newer versions of what this application pins, and what moving means.

    Its own examples run against each candidate, each in a scratch log that
    is rolled back, so asking writes nothing.
    """
    name = _required(request, "name")
    version = _required(request, "version")
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        try:
            return _application(lambda store: application.updates(
                conn, store, name, version))
        finally:
            conn.rollback()


async def app_projection(request: Request):
    """One table of the application, derived now, at the clocks in the URL."""
    name = _required(request, "name")
    version = _required(request, "version")
    class_name = _required(request, "class")
    clocks = _clocks(request)
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        return _application(lambda store: application.projection(
            conn, store, name, version, class_name, **clocks))


async def app_cell(request: Request):
    """What one cell of a table stands on, at the clocks it was derived at."""
    name = _required(request, "name")
    version = _required(request, "version")
    class_name = _required(request, "class")
    column = _required(request, "column")
    # The grouping values, one query parameter per key column: `key.<column>`.
    keys = {k[len("key."):]: v for k, v in request.query_params.items()
            if k.startswith("key.")}
    clocks = _clocks(request)
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        return _application(lambda store: application.cell(
            conn, store, name, version, class_name, column, keys, **clocks))


async def app_form(request: Request):
    name = _required(request, "name")
    version = _required(request, "version")
    class_name = _required(request, "class")
    clocks = _clocks(request)
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        return _application(lambda store: application.form_of(
            conn, store, name, version, class_name, **clocks))


async def app_state(request: Request):
    """One form submission. The only write this API makes.

    `revokes`, when given, is field name -> the id of an assertion this
    submission withdraws: beside a value for the same field, a correction;
    alone, a withdrawal. The answer's `stated` gives the ids a later
    correction names.

    It is one `perform()` underneath, exactly as a seal is: one intent, N
    assertions, nothing edited. The response names the intent, so whatever was
    written can be opened in the kernel explorer straight away.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "the body is not JSON")
    if not isinstance(body, dict):
        raise HTTPException(400, "the body is not an object")
    for field in ("name", "version", "class", "subject", "actor"):
        if not body.get(field):
            raise HTTPException(400, f"{field} is required")
    values = body.get("values") or {}
    if not isinstance(values, dict):
        raise HTTPException(400, "values is not an object")
    revokes = body.get("revokes") or {}
    if not isinstance(revokes, dict):
        raise HTTPException(400, "revokes is not an object of field -> assertion id")

    valid_from = body.get("valid_from")
    if valid_from:
        try:
            valid_from = datetime.fromisoformat(str(valid_from).replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, f"valid_from is not an ISO 8601 instant: {valid_from!r}")
        if valid_from.tzinfo is None:
            valid_from = valid_from.replace(tzinfo=timezone.utc)
    else:
        valid_from = datetime.now(timezone.utc)

    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        return _application(lambda store: application.state(
            conn, store, body["name"], body["version"], body["class"],
            subject=str(body["subject"]), values=values,
            actor_id=str(body["actor"]), valid_from=valid_from,
            note=body.get("note") or None, revokes=revokes))


async def business_read(request: Request):
    """Whose kernel this is, and which applications it uses at the clocks."""
    clocks = _clocks(request)
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        return JSON(business.summary(conn, **clocks))


async def _body(request, *fields):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "the body is not JSON")
    if not isinstance(body, dict):
        raise HTTPException(400, "the body is not an object")
    for field in fields:
        if not str(body.get(field) or "").strip():
            raise HTTPException(400, f"{field} is required")
    since = body.get("valid_from")
    if since:
        try:
            since = datetime.fromisoformat(str(since).replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, f"valid_from is not an ISO 8601 instant: {since!r}")
        body["valid_from"] = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
    else:
        body["valid_from"] = datetime.now(timezone.utc)
    return body


async def app_install(request: Request):
    """Use one version of an application from a day on. A person's step: the
    process owner decides when the business starts recording through it."""
    body = await _body(request, "name", "version", "actor")
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        return _application(lambda store: business.install(
            conn, store, str(body["name"]), str(body["version"]),
            actor_id=str(body["actor"]), valid_from=body["valid_from"]))


async def app_stop(request: Request):
    """Stop using an application from a day on. What was recorded stays."""
    body = await _body(request, "name", "actor")
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        return _application(lambda store: business.stop(
            conn, store, str(body["name"]), actor_id=str(body["actor"]),
            valid_from=body["valid_from"]))


async def names_read(request: Request):
    """Who owns each name the kernel knows an owner of, at the clocks; or one
    name's owners, with `name`, which may be one nobody owns yet."""
    clocks = _clocks(request)
    scope = request.query_params.get("name")
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        if scope:
            scope = owners.scope_of(scope)
            return JSON({"name": scope, "owned": owners.owned(conn, scope),
                         "owners": owners.owners(conn, scope, **clocks)})
        return JSON({"names": owners.names(conn, **clocks)})


def _names(change):
    async def route(request: Request):
        """An owner of a name adds or removes one, from a day on."""
        body = await _body(request, "name", "person", "actor")
        try:
            with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
                return JSON(change(conn, owners.scope_of(str(body["name"]).strip()),
                                   str(body["person"]), actor_id=str(body["actor"]),
                                   valid_from=body["valid_from"]))
        except Refusal as exc:
            return _refused(exc)
    return route


async def studio_drafts(request: Request):
    """Every draft open in the store, and what each one would supersede."""
    return _modules(studio_draft.drafts)


def _studio_state(store, name):
    """One draft, with its business examples run.

    They run on a connection to the log, each in a scratch log of its own that
    is rolled back, so reading a draft writes nothing. Without a log to connect
    to, the draft is still read and the examples are listed, not run — the
    state says so, and does not call the draft sealable. With one, the state
    also says who owns the draft's name.
    """
    try:
        conn = connect(os.environ.get("UNITI_DSN"), connect_timeout=3)
    except psycopg.OperationalError:
        return studio_read.state(store, name)
    with conn:
        try:
            state = studio_read.state(store, name, conn)
            # Who may seal it, said while it is still a draft rather than
            # at the end, when the seal refuses.
            scope = owners.scope_of(name)
            state["owners"] = {"name": scope, "owned": owners.owned(conn, scope),
                               "owners": owners.owners(conn, scope)}
            return state
        finally:
            conn.rollback()


async def studio_state(request: Request):
    """One draft: what is being built, the holes in it, and what it would do."""
    return _modules(_studio_state, _required(request, "name"))


async def studio_step(request: Request):
    """Perform one operation on one draft, and answer with the draft after it.

    A write, and the only one the API makes that does not reach the kernel: a
    draft is a file until somebody seals it. The step is named from the closed
    list, so a body naming anything else is refused before a file is touched.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "the body is not JSON")
    if not isinstance(body, dict):
        raise HTTPException(400, "the body is not an object")
    for field in ("name", "step"):
        if not body.get(field):
            raise HTTPException(400, f"{field} is required")
    args = body.get("args") or {}
    if not isinstance(args, dict):
        raise HTTPException(400, "args is not an object")

    name, step = str(body["name"]), str(body["step"])
    try:
        store = Store.from_env()
        studio_draft.apply(store, name, step, args)
        if step == "discard":
            return JSON({"name": name, "discarded": True})
        if not studio_draft.path(store, name).is_file():
            # A plan agreed to before the module is started: there is no
            # draft to answer with yet, only the plan.
            return JSON({"name": name, "plan": studio_draft.plan_of(store, name)})
        return JSON(_studio_state(store, name))
    except Refusal as exc:
        return _refused(exc)


async def studio_chat(request: Request):
    """What was said with the agent about one draft, kept beside it."""
    return _modules(agent.chat, _required(request, "name"))


async def studio_seal(request: Request):
    """Seal one draft, by the person named in the body. The agent cannot."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "the body is not JSON")
    if not isinstance(body, dict):
        raise HTTPException(400, "the body is not an object")
    for field in ("name", "actor"):
        if not str(body.get(field) or "").strip():
            raise HTTPException(400, f"{field} is required")
    return _modules(agent.sealed, str(body["name"]).strip(), str(body["actor"]).strip())


async def _error(request: Request, exc: HTTPException):
    return JSON({"error": exc.detail}, status_code=exc.status_code)


routes = [
    Route("/api/kernel/summary", summary),
    Route("/api/kernel/entities", entities),
    Route("/api/kernel/entities/{id}", entity),
    Route("/api/kernel/intents", intents),
    Route("/api/kernel/intents/{id}", intent),
    Route("/api/kernel/log", log),
    Route("/api/kernel/plane", plane),
    Route("/api/modules", modules),
    Route("/api/modules/graph", modules_graph),
    Route("/api/modules/version", module_version),
    Route("/api/modules/diff", module_diff),
    Route("/api/modules/classes", module_classes),
    Route("/api/modules/connections", module_connections),
    Route("/api/app", app_read),
    Route("/api/catalogue", catalogue),
    Route("/api/app/roles", app_roles),
    Route("/api/app/health", app_health),
    Route("/api/app/check", app_check),
    Route("/api/app/fit", app_fit),
    Route("/api/app/updates", app_updates),
    Route("/api/app/projection", app_projection),
    Route("/api/app/cell", app_cell),
    Route("/api/app/form", app_form),
    Route("/api/app/state", app_state, methods=["POST"]),
    Route("/api/app/install", app_install, methods=["POST"]),
    Route("/api/app/stop", app_stop, methods=["POST"]),
    Route("/api/business", business_read),
    Route("/api/names", names_read),
    Route("/api/names/add", _names(owners.add), methods=["POST"]),
    Route("/api/names/remove", _names(owners.remove), methods=["POST"]),
    Route("/api/studio/drafts", studio_drafts),
    Route("/api/studio/draft", studio_state),
    Route("/api/studio/step", studio_step, methods=["POST"]),
    Route("/api/studio/chat", studio_chat),
    Route("/api/studio/ask", agent.ask, methods=["POST"]),
    Route("/api/studio/seal", studio_seal, methods=["POST"]),
]
if DIST.is_dir():
    routes.append(Mount("/", StaticFiles(directory=DIST, html=True)))

app = Starlette(routes=routes, exception_handlers={HTTPException: _error})

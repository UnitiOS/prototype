"""The HTTP door: one JSON API that the web application and, later, the agent read.

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

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "provenance"))

from components.api import application, kernel  # noqa: E402
from components.modules import read as modules_read  # noqa: E402
from components.modules.store import ModuleError, Store  # noqa: E402
from perform import connect  # noqa: E402
from provenance import _registry  # noqa: E402

DIST = ROOT / "web" / "dist"


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


def _modules(fn, *args, **kwargs):
    try:
        return JSON(fn(Store.from_env(), *args, **kwargs))
    except ModuleError as exc:
        raise HTTPException(404, str(exc))


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


def _application(fn, *args, **kwargs):
    try:
        return JSON(fn(Store.from_env(), *args, **kwargs))
    except ModuleError as exc:
        raise HTTPException(404, str(exc))
    except application.MapError as exc:
        raise HTTPException(400, str(exc))


async def app_read(request: Request):
    return _application(application.application, _required(request, "name"),
                        _required(request, "version"))


async def app_projection(request: Request):
    """One table of the application, derived now, at the clocks in the URL."""
    name = _required(request, "name")
    version = _required(request, "version")
    class_name = _required(request, "class")
    clocks = _clocks(request)
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        return _application(lambda store: application.projection(
            conn, store, name, version, class_name, **clocks))


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
    Route("/api/app", app_read),
    Route("/api/app/projection", app_projection),
]
if DIST.is_dir():
    routes.append(Mount("/", StaticFiles(directory=DIST, html=True)))

app = Starlette(routes=routes, exception_handlers={HTTPException: _error})

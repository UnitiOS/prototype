"""The agent's door: a person asks, the agent works, the page watches it work.

    POST /api/studio/ask    {name, text}   one request to the agent about one
                                           module's draft. The answer is a
                                           stream, one JSON object per line,
                                           as the work happens:
            {"event": "call", ...}      a call the agent (or its accountant)
                                        made to the model: what it did — the
                                        tools it called, what it said — how
                                        long it took and what it used, and
                                        whether the draft changed; when it
                                        did, what changed since the last call
                                        (`now`) and since the request began
                                        (`touched`), as the map draws it
            {"event": "note", ...}      something the session said (a stop)
            {"event": "error", ...}     a call that failed
            {"event": "turn", ...}      how the request ended: the ending the
                                        page draws (Reply, Question, Plan,
                                        Proposal, Stopped), what the person is
                                        put before, what the request spent,
                                        and what it changed in the draft
    GET  /api/studio/chat   ?name=         the conversation kept beside the
                                           draft, the plan and whether the
                                           person agreed to it, whether a
                                           request on it is running now, and
                                           the conversations that built each
                                           sealed version, to read
    POST /api/studio/seal   {name, actor}  seal the draft, by a person; then
                                           the draft is closed and its
                                           conversation kept beside the version

Every call to a model is also written down whole in a watch file under
build/calls, exactly as `python -m components.agent ask` writes it: the page
is shown the gist, the file keeps everything.

One request per module at a time: a second is refused while the first runs,
because both would be changing the same draft. A request that the person
stops watching (the page closed) runs to its end all the same — it is held by
its budget, and what it did is in the draft either way.

The agent has no seal and cannot agree to a plan or an example: agreeing is
a studio step the page sends as the person (`/api/studio/step`), and sealing
is here.

A rehearsal can be watched from the page too. With UNITI_AGENT_REHEARSAL
naming a script (`components.agent.rehearsal`), a request on the script's own
module is played from the script instead of by a model — the same tools on the
same draft, nothing spent — one move every UNITI_AGENT_REHEARSAL_PAUSE seconds
so a person can follow it. Every other module still goes to the model.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from components.agent import conversation as kept  # noqa: E402
from components.agent import rehearsal  # noqa: E402
from components.agent.config import unlimited  # noqa: E402
from components.agent.session import Session  # noqa: E402
from components.agent.tools import Bench  # noqa: E402
from components.agent.watch import Watch  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.studio import changes  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from perform import connect  # noqa: E402
from seal import seal  # noqa: E402

CALLS = ROOT / "build" / "calls"

# The modules a request is running on now.
RUNNING = set()

# Which models play the parts: config/agent.yaml's when None. A test puts a
# configuration of scripted models here.
configured = None


def environment():
    """The model's credentials, from .env where the environment says nothing.
    Whatever the process was started with wins: the log it reads is its own."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env", override=False)


class Relay(Watch):
    """A watch that also hands the gist of each event to a page, as it happens:
    and, after a call that changed the draft, what changed — `look` is how the
    draft is looked at."""

    def __init__(self, path, loop, queue, look=None):
        super().__init__(path)
        self._loop = loop
        self._queue = queue
        self._look = look
        self._first = self._last = look() if look else None

    def write(self, event, **fields):
        super().write(event, **fields)
        shown = gist(event, fields)
        if shown is None:
            return
        if shown.get("changed") and self._look:
            now = self._look()
            shown["now"] = changes.between(self._last, now)
            shown["touched"] = changes.between(self._first, now)
            self._last = now
        self._loop.call_soon_threadsafe(self._queue.put_nowait, shown)


def gist(event, fields):
    """What a page shows of one watch event; None for what it does not."""
    if event == "note":
        return {"event": "note", "text": fields.get("text", "")}
    if event == "error":
        return {"event": "error", "part": fields.get("part"),
                "error": str(fields.get("error", ""))[:400]}
    if event != "call":
        return None
    did = []
    for part in fields.get("received") or []:
        if "call" in part:
            did.append({"tool": part["call"], "args": part.get("args") or {}})
        elif "text" in part and part["text"].strip():
            did.append({"text": part["text"][:600]})
        elif "thought" in part and part["thought"].strip():
            did.append({"thought": part["thought"][:600]})
    answered = [p for p in fields.get("sent") or [] if "answer" in p]
    tokens = fields.get("tokens") or {}
    return {"event": "call", "part": fields.get("part"), "step": fields.get("step"),
            "seconds": fields.get("seconds"), "did": did,
            "answered": [{"tool": p["answer"],
                          "first": str(p.get("content", "")).strip().splitlines()[0][:200]
                          if str(p.get("content", "")).strip() else ""}
                         for p in answered],
            # A `do` answered means the draft changed since the last look.
            "changed": any(p["answer"] == "do" for p in answered),
            "tokens": {"input": tokens.get("input", 0), "output": tokens.get("output", 0),
                       "thinking": tokens.get("thoughts_tokens", 0),
                       "cached": tokens.get("cached_content_tokens", 0)}}


def ended(turn):
    """How a request ended, as the page draws it."""
    return {"event": "turn", "ended": turn.ended, "said": turn.output.model_dump(),
            "shown": turn.shown, "spent": turn.spent, "touched": turn.touched or []}


def parts_for(name):
    """Which models play a request on `name`: a test's, a rehearsal's when the
    server rehearses this module, else the configuration file's (None)."""
    if configured is not None:
        return configured
    script_path = os.environ.get("UNITI_AGENT_REHEARSAL")
    if not script_path:
        return None
    script = rehearsal.load(ROOT / script_path)
    if script["module"] != name:
        return None
    pause = float(os.environ.get("UNITI_AGENT_REHEARSAL_PAUSE") or 0)
    return unlimited(builder=rehearsal.model(script, pause=pause),
                     accountant=rehearsal.accountant(script, pause=pause))


async def _body(request, *required):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "the body is not JSON")
    if not isinstance(body, dict):
        raise HTTPException(400, "the body is not an object")
    for field in required:
        if not str(body.get(field) or "").strip():
            raise HTTPException(400, f"{field} is required")
    return body


async def ask(request: Request):
    body = await _body(request, "name", "text")
    name, text = str(body["name"]).strip(), str(body["text"]).strip()
    if name in RUNNING:
        raise HTTPException(409, f"the agent is already working on {name}; "
                                 f"wait for it to finish")
    store = Store.from_env()
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    watch = Relay(CALLS / f"{stamp}-{name.replace('@', '').replace('/', '-')}.jsonl",
                  loop, queue, look=lambda: changes.look(store, name)).http()
    session = Session(Bench.from_env(store), name, parts_for(name), watch=watch)
    RUNNING.add(name)

    async def work():
        try:
            await queue.put(ended(await session.ask_async(text)))
        except Exception as exc:  # the page is told, and the file keeps it
            watch.write("error", part="session", error=f"{type(exc).__name__}: {exc}")
            await queue.put({"event": "failed", "error": f"{type(exc).__name__}: {exc}"})
        finally:
            watch.stop()
            RUNNING.discard(name)
            await queue.put(None)

    task = asyncio.create_task(work())

    async def lines():
        where = watch.path.relative_to(ROOT) if watch.path.is_relative_to(ROOT) else watch.path
        yield json.dumps({"event": "started", "watch": where.as_posix()}) + "\n"
        while (item := await queue.get()) is not None:
            yield json.dumps(item, ensure_ascii=False, default=str) + "\n"
        await task

    return StreamingResponse(lines(), media_type="application/x-ndjson")


def chat(store, name):
    """The conversation as a page reads it: the turns without their calls, and
    above them the conversations that built each sealed version (`earlier`),
    so a module opened again shows how it came to be."""
    held = kept.load(store, name)
    return {"name": name, "running": name in RUNNING,
            "turns": [{k: v for k, v in turn.items() if k != "messages"}
                      for turn in held.turns],
            "reckonings": held.reckonings,
            "plan": studio.plan_of(store, name),
            "earlier": kept.beside(store, name)}


def sealed(store, name, actor):
    """Seal a draft as a person, then close it. The seal's own gates judge; a
    refusal comes back before anything is written."""
    if name in RUNNING:
        raise HTTPException(409, f"the agent is still working on {name}")
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        out = seal(conn, studio.path(store, name), actor_id=actor,
                   into=studio.directory(store, name), store=store)
    studio.closed(store, name, out["version"])
    return {"name": name, "version": out["version"], "minted": len(out["minted"])}


__all__ = ["RUNNING", "ask", "chat", "environment", "gist", "sealed"]

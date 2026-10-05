"""watch — every call to a model, written down whole, as it happens.

The output of a turn says what the agent concluded. It does not say what each
call cost, how long it took, what the model was sent, what it thought, or
whether the connection had to try twice. A `Watch` records all of that, one
JSON line per event, into a file, while the request runs:

    call      one call to a model, by one part (builder, accountant):
              when it started and how long it took; the model and the
              provider's own id for the response; why it stopped; the tokens
              in, out, thought and cached; what was new in what it was sent
              (the person's words, tool answers, what was sent back); and all
              it answered — its thoughts where the provider returns them, its
              text, and every tool call with its arguments
    error     a call that failed, and after how long
    http      what the libraries underneath log as they go — every HTTP
              request with its status, and any retry a provider's library
              makes — so a retry or a slow provider shows as what it is
    note      anything the caller adds (a budget stop, a run's start)

Nothing here names a provider or a library. It hangs on the framework's
hooks, which every model has, and on Python's own log, which every library
writes to.

`python -m components.agent watch FILE` prints a file for a person.
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.capabilities import Hooks
from pydantic_ai.messages import (
    ModelRequest, RetryPromptPart, SystemPromptPart, TextPart, ThinkingPart,
    ToolCallPart, ToolReturnPart, UserPromptPart,
)


# Libraries this system uses for its own work, whose chatter is not about the
# model: left out of the watch.
QUIET = ("linkml", "linkml_runtime")


class Watch:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._http = None

    def write(self, event, **fields):
        line = {"at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "event": event, **fields}
        with self._lock, self.path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")

    def note(self, text, **fields):
        self.write("note", text=text, **fields)

    def hooks(self, part):
        """The hooks that write down every call one part makes."""
        hooks = Hooks()
        started = {}

        @hooks.on.before_model_request
        async def _before(ctx, request_context):
            started[ctx.run_id] = (time.monotonic(), len(request_context.messages))
            return request_context

        @hooks.on.after_model_request
        async def _after(ctx, *, request_context, response):
            t0, _ = started.pop(ctx.run_id, (time.monotonic(), 0))
            usage = response.usage
            self.write(
                "call", part=part, step=ctx.run_step,
                seconds=round(time.monotonic() - t0, 2),
                model=response.model_name, response_id=response.provider_response_id,
                finish=response.finish_reason,
                tokens={"input": usage.input_tokens, "output": usage.output_tokens,
                        **dict(usage.details or {})},
                sent=_new(request_context.messages),
                received=[_part(p) for p in response.parts],
                provider=response.provider_details)
            return response

        @hooks.on.model_request_error
        async def _failed(ctx, *, request_context, error):
            t0, _ = started.pop(ctx.run_id, (time.monotonic(), 0))
            self.write("error", part=part, step=ctx.run_step,
                       seconds=round(time.monotonic() - t0, 2),
                       error=f"{type(error).__name__}: {error}")
            raise error

        return hooks

    def http(self):
        """Write down what every library logs, from INFO up, until `stop`."""
        watch = self

        class _Line(logging.Handler):
            def emit(self, record):
                if not record.name.startswith(QUIET):
                    watch.write("http", source=record.name, text=record.getMessage())

        root = logging.getLogger()
        self._http = (_Line(logging.INFO), root.level)
        root.setLevel(logging.INFO)
        root.addHandler(self._http[0])
        return self

    def stop(self):
        if self._http is not None:
            root = logging.getLogger()
            root.removeHandler(self._http[0])
            root.setLevel(self._http[1])
            self._http = None


def _new(messages):
    """What the last request added: everything after the model last spoke."""
    last = messages[-1] if messages else None
    if not isinstance(last, ModelRequest):
        return []
    return [_part(p) for p in last.parts]


def _part(part):
    if isinstance(part, ThinkingPart):
        return {"thought": part.content}
    if isinstance(part, TextPart):
        return {"text": part.content}
    if isinstance(part, ToolCallPart):
        return {"call": part.tool_name, "args": part.args_as_dict()}
    if isinstance(part, ToolReturnPart):
        return {"answer": part.tool_name, "content": str(part.content)}
    if isinstance(part, RetryPromptPart):
        content = part.content if isinstance(part.content, str) else str(part.content)
        return {"sent_back": part.tool_name, "content": content}
    if isinstance(part, UserPromptPart):
        return {"person": str(part.content)}
    if isinstance(part, SystemPromptPart):
        return {"system": len(part.content)}
    return {type(part).__name__: str(part)[:2000]}


def render(path):
    """A watch file as a person reads it: one block per call."""
    lines = []
    totals = {"calls": 0, "input": 0, "output": 0, "thoughts": 0, "seconds": 0.0}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        e = json.loads(raw)
        clock = e["at"][11:19]
        if e["event"] == "note":
            lines.append(f"{clock} -- {e['text']}")
        elif e["event"] == "http":
            lines.append(f"{clock}    http: {e['text']}")
        elif e["event"] == "error":
            lines.append(f"{clock} !! {e['part']} call {e['step']} failed after "
                         f"{e['seconds']} s: {e['error']}")
        else:
            t = e["tokens"]
            thoughts = t.get("thoughts_tokens", 0)
            totals["calls"] += 1
            totals["input"] += t["input"]
            totals["output"] += t["output"]
            totals["thoughts"] += thoughts
            totals["seconds"] += e["seconds"]
            lines.append(f"{clock} {e['part']} call {e['step']}: {e['seconds']} s, "
                         f"{t['input']} in ({t.get('cached_content_tokens', 0)} cached), "
                         f"{t['output']} out ({thoughts} thinking), stop: {e['finish']}")
            for part in e["sent"]:
                lines.append("    sent " + _short(part))
            for part in e["received"]:
                lines.append("    got  " + _short(part))
    lines.append(f"{totals['calls']} calls, {totals['input']} tokens in, "
                 f"{totals['output']} out of which {totals['thoughts']} thinking, "
                 f"{totals['seconds']:.1f} s waiting on the model")
    return lines


def _short(part, width=400):
    key, value = next(iter(part.items()))
    if key in ("call", "answer", "sent_back"):
        rest = part.get("args") if key == "call" else part.get("content")
        text = f"{key} {value}: {json.dumps(rest, ensure_ascii=False) if key == 'call' else rest}"
    else:
        text = f"{key}: {value}"
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[:width] + f" … ({len(text)} chars)"


__all__ = ["Watch", "render"]

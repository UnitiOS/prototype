"""rehearsal — the builder played from a script, with no model behind it.

Before a model is trusted with the tools, the tools are shown to work without
one. A rehearsal is a script of moves — which tool with which arguments, and
how the turn ends — played through the same agent a model would drive: the
same framework, the same tool schemas, the same checks on a proposal. Only the
choosing is scripted. Whatever the system answers is real: the steps are
taken on a real draft, the examples run in real scratch logs, and a proposal
the draft does not bear out is handed back exactly as it would be to a model.

A script is data, and lives with the test data, because it names a business.
The work goes in requests, as it does with a person — a plan, the examples,
the rules — and a script says what each request does:

    module: "@scope/name"
    requests:
      - says: what the person asked for
        moves:
          - tool: catalogue
            args: {kind: role}
          - end: Plan
            args: {message: ..., builds: ..., records: [...], numbers: [...]}
      - says: Agreed, go on.
        moves:
          - tool: do
            args:
              module: "@scope/name"
              steps:
                - {op: add_class, args: {class: Thing, description: ...}}
          - tool: reckon
            args: {example: ..., happened: [...], wanted: [...]}
          - end: Proposal
            args: {module: "@scope/name", message: ..., agree: [...]}
    accountant:
      - figures: [{figure: ..., value: "20", working: ...}]

Which request is being played is read off the conversation — how many
requests it has had — so a page can ask as it likes and each request plays its
own moves; what the person says is not read. A script may also be one request
written flat, `says` and `moves`, its moves played in order across however
many requests one session makes.

The accountant is scripted too, apart from the builder: each `reckon` the
builder makes is answered by the entry of `accountant` whose figures it asks
for, or else the next one, through the same accountant agent a model would
play, so what it answers is checked, kept and shown exactly as a model's would
be.

`do` steps are written with their arguments as a mapping, which is how a
person reads them; they are handed to the tool as name/value pairs, which is
how a model writes them.

A `pause` holds each move back that many seconds, for a person watching a
rehearsal from the page; tests play it without one.
"""

import asyncio
import sys
from pathlib import Path

import yaml
from pydantic_ai import ModelResponse, ToolCallPart
from pydantic_ai.messages import (
    ModelRequest, RetryPromptPart, TextPart, ToolReturnPart, UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.agent.config import unlimited  # noqa: E402
from components.agent.guide import OPENS  # noqa: E402
from components.agent.session import Session, Stopped, person_agrees  # noqa: E402


FAREWELL = "I stopped here, at this request's budget; ask me to go on."


def load(path):
    """A script, read and shaped for the tools."""
    script = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for move in _moves(script):
        if move.get("tool") == "do":
            move["args"]["steps"] = load_steps(move["args"]["steps"])
    return script


def _moves(script):
    """Every move of a script, whichever way it is written."""
    if "requests" in script:
        return [move for request in script["requests"] for move in request["moves"]]
    return script["moves"]


def _where(messages):
    """Which request a conversation is in, counted from 0, and how many calls
    that request has made: every request opens with the system's note."""
    request, made = -1, 0
    for message in messages:
        if isinstance(message, ModelRequest) and any(
                isinstance(p, UserPromptPart) and str(p.content).startswith(OPENS)
                for p in message.parts):
            request, made = request + 1, 0
        elif isinstance(message, ModelResponse):
            made += 1
    return request, made


def load_steps(steps):
    """Steps written with their arguments as a mapping, as name/value pairs."""
    return [{"op": s["op"], "args": [{"name": str(k), "value": str(v)}
                                     for k, v in (s.get("args") or {}).items()]}
            for s in steps]


def _paced(answer, pause):
    """The same answers, each one `pause` seconds later."""
    if not pause:
        return answer

    async def later(messages, info: AgentInfo):
        await asyncio.sleep(pause)
        return answer(messages, info)

    return later


def model(script, pause=0):
    """A model that makes the script's moves, one per call, in order."""
    moves = iter(script.get("moves") or [])

    def play(messages, info: AgentInfo):
        # The budget's last call allows only some endings: a script that did not
        # fit in it says goodbye in the first of them, as a model must.
        allowed = (info.model_settings or {}).get("tool_choice")
        if isinstance(allowed, list):
            name = next(t.name for t in info.output_tools if t.name in allowed)
            return ModelResponse(parts=[ToolCallPart(name, {
                "message": script.get("farewell") or FAREWELL})])
        if "requests" in script:
            request, made = _where(messages)
            if not 0 <= request < len(script["requests"]):
                raise RuntimeError("the script has no request left")
            planned = script["requests"][request]["moves"]
            move = planned[made] if made < len(planned) else None
        else:
            move = next(moves, None)
        if move is None:
            raise RuntimeError("the script ran out of moves before the turn ended")
        if "tool" in move:
            name = move["tool"]
        else:
            name = next(t.name for t in info.output_tools
                        if t.name.endswith(f"_{move['end']}"))
        return ModelResponse(parts=[ToolCallPart(name, move.get("args") or {})])

    return FunctionModel(_paced(play, pause), model_name="rehearsal")


def accountant(script, pause=0):
    """A model that gives the script's accountant answers: the one whose
    figures it is asked for, or else the next."""
    held = list(script.get("accountant") or [])
    answers = iter(held)

    def answer(messages, info: AgentInfo):
        asked = "\n".join(str(p.content) for m in messages for p in m.parts
                          if hasattr(p, "content"))
        given = next((a for a in held if a.get("figures")
                      and all(f"- {f['figure']}" in asked for f in a["figures"])), None) \
            or next(answers, None)
        if given is None:
            raise RuntimeError("the script has no accountant answer left")
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, given)])

    return FunctionModel(_paced(answer, pause), model_name="rehearsal-accountant")


def rehearse(bench, script, request=0):
    """Play one request of the script through a session on the builder — the
    first, unless another is named. Returns the turn."""
    parts = unlimited(builder=model(script), accountant=accountant(script))
    says = script["requests"][request]["says"] if "requests" in script else script["says"]
    return Session(bench, script["module"], parts).ask(says)


def play_through(bench, script):
    """Every request of the script in turn, the person agreeing to whatever
    each one puts before them (`person_agrees`). The turns."""
    turns = []
    for request in range(len(script.get("requests") or [None])):
        turn = rehearse(bench, script, request)
        turns.append(turn)
        if isinstance(turn.output, Stopped):
            break
        person_agrees(bench.store, script["module"], turn.output)
    return turns


def trace(messages):
    """The run as a person would read it: each call, and what came back."""
    lines = []
    for message in messages:
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                lines.append(f"person: {part.content}")
            elif isinstance(part, ToolCallPart):
                args = part.args_as_dict()
                if part.tool_name == "do":
                    said = "; ".join(
                        s["op"] + " " + " ".join(f"{a['name']}={a['value']}"
                                                 for a in s.get("args") or [])
                        for s in args.get("steps") or [])
                    lines.append(f"agent calls do on {args.get('module')}: {said}")
                else:
                    shown = ", ".join(f"{k}={v}" for k, v in args.items())
                    lines.append(f"agent calls {part.tool_name}({shown})")
            elif isinstance(part, ToolReturnPart):
                lines.append(_indented(str(part.content)))
            elif isinstance(part, RetryPromptPart):
                content = part.content if isinstance(part.content, str) \
                    else str(part.content)
                lines.append(_indented(f"sent back: {content}"))
            elif isinstance(part, TextPart) and not isinstance(message, ModelRequest):
                lines.append(f"agent says: {part.content}")
    return lines


def _indented(text):
    return "\n".join(f"    | {line}" for line in text.splitlines())


__all__ = ["accountant", "load", "load_steps", "model", "play_through", "rehearse",
           "trace"]

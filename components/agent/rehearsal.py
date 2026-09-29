"""rehearsal — the builder played from a script, with no model behind it.

Before a model is trusted with the tools, the tools are shown to work without
one. A rehearsal is a script of moves — which tool with which arguments, and
how the turn ends — played through the same agent a model would drive: the
same framework, the same tool schemas, the same checks on a proposal. Only the
choosing is scripted. Whatever the system answers is real: the steps are
taken on a real draft, the examples run in real scratch logs, and a proposal
the draft does not bear out is handed back exactly as it would be to a model.

A script is data, and lives with the test data, because it names a business:

    module: "@scope/name"
    says: what the person asked for
    moves:
      - tool: catalogue
        args: {kind: role}
      - tool: do
        args:
          module: "@scope/name"
          steps:
            - {op: add_class, args: {class: Thing, description: ...}}
      - end: Proposal
        args: {module: "@scope/name", message: ..., agree: [...], seal: true}

`do` steps are written with their arguments as a mapping, which is how a
person reads them; they are handed to the tool as name/value pairs, which is
how a model writes them.
"""

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

from components.agent.builder import builder  # noqa: E402


def load(path):
    """A script, read and shaped for the tools."""
    script = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for move in script["moves"]:
        if move.get("tool") == "do":
            move["args"]["steps"] = [
                {"op": s["op"], "args": [{"name": str(k), "value": str(v)}
                                          for k, v in (s.get("args") or {}).items()]}
                for s in move["args"]["steps"]]
    return script


def model(script):
    """A model that makes the script's moves, one per request, in order."""
    moves = iter(script["moves"])

    def play(messages, info: AgentInfo):
        move = next(moves, None)
        if move is None:
            raise RuntimeError("the script ran out of moves before the turn ended")
        if "tool" in move:
            name = move["tool"]
        else:
            name = next(t.name for t in info.output_tools
                        if t.name.endswith(f"_{move['end']}"))
        return ModelResponse(parts=[ToolCallPart(name, move.get("args") or {})])

    return FunctionModel(play, model_name="rehearsal")


def rehearse(bench, script):
    """Play the script through the builder. Returns the framework's result."""
    return builder(model(script)).run_sync(script["says"], deps=bench)


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


__all__ = ["load", "model", "rehearse", "trace"]

"""conversation — what was said about a draft, kept beside it.

The agent's memory is the system: the draft, its transcript, its examples. A
model that forgot everything and read those again would know where the work
stands. What the draft cannot say is what the person asked for and answered,
and what the accountant worked out. That is kept here, beside the draft, as
`draft.chat.yaml`:

    turns:
      - at: 2026-09-30T10:00:00+00:00
        person: what they asked, in their words
        ended: Reply | Question | Proposal | Stopped
        said: {...}        how the turn ended, as the page draws it
        spent: {requests, input, output, dollars, seconds}
        shown: ...         for a proposal, what the person was put before,
                           read off the draft by the system (`put_before`)
        touched: [...]     what the turn changed in the draft, a line per
                           kind, field, example or pin (`studio.changes`)
        messages: [...]    every call of the turn and its answer, as the
                           framework writes them
    reckonings:
      example_name:
        happened: [...]    the situation the builder put to the accountant
        wanted: [...]      the figures asked for
        figures: [{figure, value, working}]
        question: ...      what the person's words left open
        by: provider:model

The model is handed every earlier turn whole: what the person said, each
call it made and what the system answered, and how the turn ended. What it
read in one turn it does not read again in the next — reading is most of what
a turn costs, and every call sends the whole conversation again. What it read
can have changed since; where the module stands is said again at the start of
every request (`guide.opened`), and every step is checked against the draft as
it is then, not as the model remembers it. A turn that stopped part way is
handed back ending on what the person was told, never on a call nobody
answered.

Two things keep the whole conversation cheap without taking anything out of
it that still holds:

    unchanged   a reading — `look`, `options`, `catalogue`, `guide` — that
                comes out the same as the last time the same thing was read in
                this conversation is answered with one line saying so, and the
                model works from the reading it already has (`unchanged`)
    cleared     once a conversation is long (`clear_above` tokens, as the
                provider counted the last call), a reading that was read again
                later is replaced by one line saying so (`cleared`). The call
                stays; only its superseded answer goes. What the person said,
                what the agent answered them, and every step it took with what
                the system answered are never cleared.

Both keep the start of what is sent the same from one call to the next, which
is what a provider's cache serves cheaply: nothing is cleared until the
conversation is long, and then everything stale at once.

The conversation is kept from the first request, before the module has a
draft — the questions asked before anything was built are part of it. A
discarded draft takes its conversation with it (`studio.draft`).
"""

import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter, ModelRequest, ModelResponse, TextPart, ToolCallPart,
    ToolReturnPart, UserPromptPart,
)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.modules.store import ModuleError  # noqa: E402
from components.studio import draft as studio  # noqa: E402

FILE = studio.CONVERSATION

# The tools that only read, each with what a call means when an argument is left
# out: two calls that read the same thing are the same reading.
READINGS = {
    "look": {"module": "", "part": "draft"},
    "options": {"module": "", "op": ""},
    "catalogue": {"text": "", "kind": "", "fills": "", "module": ""},
    "guide": {"topic": "workflow"},
}

# How a reading answered in one line begins, so that it is never taken for a
# reading in full.
UNCHANGED = "[unchanged]"
CLEARED = "[cleared]"


@dataclass
class Conversation:
    turns: list = field(default_factory=list)
    reckonings: dict = field(default_factory=dict)

    def said(self, now=None):
        """The conversation as the person had it: their words and the
        questions put to them, oldest first, and `now` last. This, and
        nothing the builder did, is what the accountant reads."""
        lines = []
        for turn in self.turns:
            lines.append(f"The person said: {turn['person']}")
            if turn["ended"] == "Question":
                lines.append(f"They were asked: {turn['said']['question']}")
        if now:
            lines.append(f"The person said: {now}")
        return lines

    def history(self):
        """The earlier turns for the model, each whole. A turn written before
        turns kept their calls is handed as it was said: request and answer."""
        messages = []
        for turn in self.turns:
            if turn.get("messages"):
                messages += ModelMessagesTypeAdapter.validate_python(turn["messages"])
                continue
            messages.append(ModelRequest(parts=[UserPromptPart(turn["person"])]))
            messages.append(ModelResponse(parts=[TextPart(spoken(turn))]))
        return messages

    def as_dict(self):
        return {"turns": self.turns, "reckonings": self.reckonings}


def spoken(turn):
    """How a turn ended, as one piece of text."""
    said = turn["said"]
    kind = turn["ended"]
    if kind == "Question":
        choices = f" (choices: {', '.join(said['choices'])})" if said.get("choices") else ""
        return f"[asked] {said['question']}{choices}"
    if kind == "Proposal":
        agree = ", ".join(said.get("agree") or []) or "nothing"
        ready = " and said it is ready to be sealed" if said.get("seal") else ""
        return (f"[proposed {said['module']}: asked to agree to {agree}{ready}] "
                f"{said['message']}")
    if kind == "Stopped":
        agree = ", ".join(said.get("agree") or [])
        ready = " and that it is ready to be sealed" if said.get("seal") else ""
        put = (f"; the system put {agree} before them to agree to{ready}" if agree
               else f"; the system told them{ready}" if ready else "")
        return f"[stopped{put}] {said['message']}"
    return said["message"]


def closed(messages, turn):
    """A turn's calls as the next turn is handed them, ready to be written:
    ending on what the person was told, never on a call nobody answered."""
    messages = list(messages)
    while messages and isinstance(messages[-1], ModelResponse) \
            and any(isinstance(p, ToolCallPart) for p in messages[-1].parts):
        messages.pop()
    if not messages or not isinstance(messages[-1], ModelResponse):
        messages.append(ModelResponse(parts=[TextPart(spoken(turn))]))
    return ModelMessagesTypeAdapter.dump_python(messages, mode="json")


# ---- readings: what was read, and what still holds --------------------------

def reading(tool, args):
    """What a call reads, as a key: the tool and its arguments, defaults filled
    in, so that two calls reading the same thing are the same reading. None for
    a tool that does more than read."""
    if tool not in READINGS:
        return None
    given = {**READINGS[tool], **{k: v for k, v in (args or {}).items() if v is not None}}
    if tool == "options":
        # Which steps, not in what order; and without one, the list of steps,
        # which is the same whatever the module.
        ops = sorted({o.strip() for o in str(given["op"]).split(",") if o.strip()})
        return (tool, str(given["module"]).strip() if ops else "", ",".join(ops))
    return (tool,) + tuple(" ".join(str(given[k]).split()) for k in READINGS[tool])


def _in_full(part):
    return isinstance(part, ToolReturnPart) and part.tool_name in READINGS \
        and not str(part.content).startswith((UNCHANGED, CLEARED))


def _readings(messages):
    """Every reading answered in full, in order: (message, part, key)."""
    asked, found = {}, []
    for i, message in enumerate(messages):
        for j, part in enumerate(message.parts):
            if isinstance(part, ToolCallPart):
                asked[part.tool_call_id] = reading(part.tool_name, part.args_as_dict())
            elif _in_full(part) and asked.get(part.tool_call_id) is not None:
                found.append((i, j, asked[part.tool_call_id]))
    return found


def unchanged(messages, tool, args, answer):
    """The answer to a reading, or one line saying it is the same as the last
    time this was read in full in `messages` — which the model still has."""
    key = reading(tool, args)
    last = None
    for i, j, found in _readings(messages):
        if found == key:
            last = messages[i].parts[j].content
    if last is None or str(last) != answer:
        return answer
    shown = ", ".join(f"{k}={v}" for k, v in (args or {}).items() if v not in (None, ""))
    return (f"{UNCHANGED} {tool}({shown}) reads exactly as it did the last time you "
            f"read it in this conversation: nothing has changed since. Work from that "
            f"reading.")


def cleared(messages, above):
    """The messages with every superseded reading cleared, when the last call
    sent was `above` tokens or more; otherwise the same messages.

    A reading is superseded when the same thing was read again later, in full.
    The latest reading of everything stays, and so does every call: only the
    old answer goes, replaced by a line saying where the current one is.
    """
    if above is None or sent(messages) < above:
        return messages
    found = _readings(messages)
    latest = {key: (i, j) for i, j, key in found}
    stale = {(i, j) for i, j, key in found if latest[key] != (i, j)}
    if not stale:
        return messages
    out = []
    for i, message in enumerate(messages):
        if not any(i == s[0] for s in stale):
            out.append(message)
            continue
        out.append(replace(message, parts=[
            replace(part, content=(f"{CLEARED} This was read again later in the "
                                   f"conversation; that later reading is the one "
                                   f"that holds."))
            if (i, j) in stale else part
            for j, part in enumerate(message.parts)]))
    return out


def sent(messages):
    """How many tokens the provider counted in the last call it answered, or 0."""
    for message in reversed(messages):
        if isinstance(message, ModelResponse) and message.usage.input_tokens:
            return message.usage.input_tokens
    return 0


def path(store, module):
    return studio.directory(store, module) / FILE


def load(store, module):
    """The conversation about a draft; an empty one when there is none."""
    where = path(store, module)
    if not where.is_file():
        return Conversation()
    raw = yaml.safe_load(where.read_text(encoding="utf-8")) or {}
    return Conversation(turns=list(raw.get("turns") or []),
                        reckonings=dict(raw.get("reckonings") or {}))


def beside(store, module):
    """The conversations that built each sealed version of a module, oldest
    first, for a person to read: `vN.chat.yaml`, kept beside the version when
    its draft was sealed, with the plan agreed to then. The turns come without
    their calls, as a page draws them.

    Only people read these. The agent is handed the draft's own conversation
    (`load`), which a new version starts empty: what built a version is in the
    version itself, and sending it to a model again would be paid for on
    every call."""
    try:
        versions = store.versions(module)
    except ModuleError as exc:
        # Nothing started under this name yet: a conversation can come first.
        if exc.code != "no_such_module":
            raise
        return []
    out = []
    for held in versions:
        version = held["version"]
        chat = held["path"].with_name(f"{version}.chat.yaml")
        if not chat.is_file():
            continue
        raw = yaml.safe_load(chat.read_text(encoding="utf-8")) or {}
        plan = held["path"].with_name(f"{version}.plan.yaml")
        out.append({
            "version": version,
            "sealed_at": held["sealed_at"].isoformat(),
            "turns": [{k: v for k, v in turn.items() if k != "messages"}
                      for turn in raw.get("turns") or []],
            "reckonings": dict(raw.get("reckonings") or {}),
            "plan": (yaml.safe_load(plan.read_text(encoding="utf-8")) or None)
            if plan.is_file() else None,
        })
    return out


def save(store, module, conversation):
    """Write it where the module's draft is or will be. A module nobody has
    started yet is no module (it has no manifest), so the conversation about
    it waits there without the store holding a name it cannot answer for."""
    where = path(store, module)
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(yaml.safe_dump(conversation.as_dict(), sort_keys=False,
                                    allow_unicode=True, width=88),
                     encoding="utf-8", newline="\n")


__all__ = ["CLEARED", "Conversation", "FILE", "READINGS", "UNCHANGED", "beside", "cleared",
           "closed", "load", "path", "reading", "save", "sent", "spoken", "unchanged"]

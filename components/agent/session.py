"""session — one person, one draft, one request at a time.

A session is what a page or a terminal talks to. It holds the conversation
about one module's draft, and `ask` takes what the person says, runs the
builder on it within the budget, keeps the turn beside the draft, and returns
how the turn ended:

    Reply, Question, Plan,      the builder's own endings (`builder`)
    Proposal
    Stopped                     the request ran out of budget, the model could
                                not produce an answer the system accepts, or the
                                provider kept failing (`cause` says which)

A plan is kept beside the draft as the person is shown it, not agreed to
(`studio.draft.propose_plan`); a person agrees to it with a studio step, as
they agree to an example. `person_agrees` is that part played by code — what a
person who agrees to everything put before them would do — for the harnesses
that play the person: an eval, a rehearsal, a test.

At the budget, the agent says itself where it stopped: its last call is kept
for that (`builder`), and its reply is the turn's Stopped message. Only when
that call fails too does the session say it, in a fixed sentence. Either way,
what was left waiting for the person is not left to the agent's words: the
examples it wrote that the person can agree to now, and whether the draft is
then ready, are read off the draft by the system and put before them with the
stop (`agree`, `seal`, and `shown` as a proposal's are) — so a request that
ran out on the last step still ends where the person can take the next one.

What the model is sent with the person's words is a note on which module is
open, which kind it is and so whom the agent helps, where it stands and where
its plan stands (`guide.opened`), read off the store as the request starts; the conversation keeps the person's words as they
said them.

Whatever happens, what the builder did before it stopped is in the draft, and
the next request starts from there. What the request changed in the draft —
kinds, fields, examples, pins — is kept with the turn (`touched`), read off the
draft before and after, so a page can show it on the map long afterwards.

Which models play the builder and the accountant is `config`'s to say. A test
passes a configuration whose parts are test models.

`ask_async` is the request itself; `ask` runs it to its end from code that is
not async, on the thread's own event loop — the one the framework keeps its
connections on — so that many requests at once (an eval) share one loop and
one connection pool rather than each opening their own.
"""

import asyncio
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel
from pydantic_ai import capture_run_messages
from pydantic_ai.exceptions import (
    ModelAPIError, UnexpectedModelBehavior, UsageLimitExceeded,
)
from pydantic_ai.usage import RunUsage, UsageLimits

from components.agent import config as configuration
from components.agent import conversation as kept
from components.agent import guide
from components.agent.builder import (
    Plan, Proposal, Reply, Work, builder, put_before, unsupported,
)
from components.refusal import Refusal
from components.studio import changes
from components.studio import draft as studio


class Stopped(BaseModel):
    """The request ended without the builder finishing it."""

    message: str
    cause: str = "budget"  # budget | model | provider
    # What the system found waiting for the person when it stopped: the
    # examples they can agree to now, and whether the draft is ready once
    # they do. Not the agent's say.
    agree: list[str] = []
    seal: bool = False


@dataclass
class Turn:
    person: str
    output: BaseModel
    messages: list
    spent: dict
    shown: str | None = None
    touched: list = None

    @property
    def ended(self):
        return type(self.output).__name__


class Session:
    def __init__(self, bench, module, config=None, *, watch=None):
        self.bench = bench
        self.module = module
        self.config = config or configuration.load()
        self.watch = watch
        self.conversation = kept.load(bench.store, module)
        self.agent = builder(self.config.part("builder").model, watch=watch)

    def ask(self, text):
        """One request, start to end. What the person is shown comes back."""
        return settle(self.ask_async(text))

    async def ask_async(self, text):
        """One request, start to end, from async code."""
        work = Work(bench=self.bench, conversation=self.conversation,
                    config=self.config, now=text, watch=self.watch,
                    module=self.module)
        if self.watch:
            self.watch.note(f"request on {self.module}: {text}")
        usage = RunUsage()
        started = time.monotonic()
        before = changes.look(self.bench.store, self.module)
        earlier = self.conversation.history()
        opening = await asyncio.to_thread(guide.opened, self.bench.store, self.module,
                                          self.bench.business())
        said = f"{opening}\n\n{text}"
        # Kept as they happen, so a request that stops part way can still be
        # read call by call.
        with capture_run_messages() as happened:
            try:
                result = await self.agent.run(
                    said, deps=work, usage=usage, message_history=earlier,
                    model_settings=self.config.settings("builder"),
                    usage_limits=UsageLimits(request_limit=None))
                output = result.output
                if work.ending and isinstance(output, Reply):
                    output = Stopped(message=output.message)
            except UsageLimitExceeded as exc:
                output = Stopped(message=f"I stopped because {_said(exc)}. What I did "
                                         f"is in the draft; ask me to go on and I start "
                                         f"from there.")
            except UnexpectedModelBehavior as exc:
                output = Stopped(message=f"I could not finish: {_said(exc)}. What I did "
                                         f"is in the draft; ask me to go on and I start "
                                         f"from there.", cause="model")
            except ModelAPIError as exc:
                output = Stopped(message=f"The model's service kept failing "
                                         f"({_said(exc)[:200]}). What I did is in the "
                                         f"draft; ask me to go on and I start from there.",
                                 cause="provider")
        messages = list(happened[len(earlier):])
        if self.watch and isinstance(output, Stopped):
            self.watch.note(output.message)
        spent = _spent(work, usage, time.monotonic() - started)
        touched = changes.between(before, changes.look(self.bench.store, self.module),
                                  self.module)
        turn = Turn(person=text, output=output, messages=messages, spent=spent,
                    touched=touched)
        if isinstance(output, Stopped):
            waiting = await asyncio.to_thread(left_waiting, work, self.module)
            if waiting:
                output.agree, output.seal = waiting.agree, waiting.seal
                turn.shown = await asyncio.to_thread(put_before, work, waiting)
        if isinstance(output, Proposal):
            turn.shown = await asyncio.to_thread(put_before, work, output)
        if isinstance(output, Plan):
            studio.propose_plan(self.bench.store, self.module,
                                output.model_dump(exclude={"message"}))
        kept_turn = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "person": text, "ended": turn.ended, "said": output.model_dump(),
            "spent": spent}
        if turn.shown:
            kept_turn["shown"] = turn.shown
        if touched:
            kept_turn["touched"] = touched
        kept_turn["messages"] = kept.closed(messages, kept_turn)
        self.conversation.turns.append(kept_turn)
        kept.save(self.bench.store, self.module, self.conversation)
        return turn


def left_waiting(work, module):
    """What a stopped request leaves for the person, as the proposal the agent
    did not get to make, or None: every example still a proposal that could
    be put to them now, and whether the draft is ready once they agree. The
    same checks as a proposal the agent makes (`unsupported`)."""
    try:
        report = work.bench.state(module)
    except Refusal:
        return None
    asked = Proposal(module=module, message="", agree=[])
    agree = [e["name"] for e in report["examples"] if not e["agreed"]
             and unsupported(work, asked.model_copy(update={"agree": [e["name"]]})) is None]
    seal = unsupported(work, asked.model_copy(update={"agree": agree, "seal": True})) is None
    if not agree and not seal:
        return None
    return asked.model_copy(update={"agree": agree, "seal": seal})


def person_agrees(store, module, output):
    """What a person who agrees to everything put before them does about how a
    turn ended: agree to a plan, or to the examples a proposal names or a
    stop leaves waiting. What
    they agreed to comes back; nothing, for any other ending."""
    if isinstance(output, Plan):
        studio.apply(store, module, "agree_plan", {})
        return ["plan"]
    if isinstance(output, (Proposal, Stopped)):
        for name in output.agree:
            studio.apply(store, module, "agree_example", {"example": name})
        return list(output.agree)
    return []


def _said(exc):
    """What an exception says, without the framework's advice to programmers."""
    said = str(exc.args[0]) if exc.args else str(exc)
    return said.split(". Consider raising the limit")[0].rstrip(".")


def settle(awaitable):
    """Run a coroutine to its end on this thread's event loop, making one
    when the thread has none. Not from inside a running loop."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(awaitable)


def _spent(work, usage, seconds):
    """What one request used, every part together."""
    dollars = work.dollars(usage)
    return {"requests": usage.requests + work.spent["requests"],
            "input": usage.input_tokens + work.spent["input"],
            "output": usage.output_tokens + work.spent["output"],
            "dollars": None if dollars is None else round(dollars, 4),
            "seconds": round(seconds, 1)}


__all__ = ["Session", "Stopped", "Turn", "left_waiting", "person_agrees", "settle"]

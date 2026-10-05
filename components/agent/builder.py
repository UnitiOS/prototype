"""builder — the agent that builds graphs, assembled from the tools and the guide.

Which model it runs on is not decided here. `builder(model)` takes whatever
the agent framework accepts — a `provider:name` string, a model object, a
test model — so the choice of provider is configuration (`config`), and
nothing in this file names one.

It works on a `Work`: the bench the tools act on, the conversation about the
draft, the accountant, and what this request has spent. One `Work` is one
request from the person.

A turn ends one of four ways, each a structured answer the page can draw:

    Reply      something said to the person, who answers when they like
    Question   something only the person can answer, with choices where there are
    Plan       what it is going to build, from which records, which numbers
               come out, and what of the request the system cannot do yet —
               for the person to agree to or change
    Proposal   the draft put before the person: the examples to agree to, and
               whether it is ready to be sealed

The work goes in that order, and the system keeps it (`studio.draft.RULED`):
no rule computing a number is written until the person has agreed to the plan
and to an example giving that table's numbers. Each is one request: the plan,
then the examples, then the rules until the examples hold, then the seal.

A proposal is checked before it reaches anybody. The agent may only propose
examples that are still proposals, that have run, that pass or wait only for
their rules, and whose every expected number the accountant worked out; and
may only say a draft is ready when the one thing it is waiting for is the
person's agreement to those examples. A
proposal that says more than the draft bears out is handed back to the agent
with what is actually the case, and it tries again. What the person then sees
is `put_before()`: the examples, their numbers and the accountant's working,
read off the draft by the system — not the agent's summary of them.

Before every call to a model the budget is checked. The last call that fits
in it is kept for the agent to say goodbye (`Work.last_call`): it is told the
budget is reached, may call no tool, and can only reply — what it did, what is
left, in the person's language. Past that, or past the budget itself, the
request stops with `UsageLimitExceeded`, and the session says so in a fixed
sentence of its own.

The instructions are the same on every call of every request, which is what
lets a provider serve them, and the conversation after them, from its cache.
Whatever changes — which module is open and where it stands — is said in the
person's message and in the tools' answers (`opened`), never in the
instructions. A reading that comes out as it did before is answered in one
line, and once a conversation is long its superseded readings are cleared
(`conversation`).
"""

import math
import os
import sys
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic import BaseModel, Field  # noqa: E402
from pydantic_ai import Agent, ModelRetry, RunContext  # noqa: E402
from pydantic_ai.capabilities import Hooks  # noqa: E402
from pydantic_ai.exceptions import UsageLimitExceeded  # noqa: E402
from pydantic_ai.messages import ModelResponse, UserPromptPart  # noqa: E402
from pydantic_ai.usage import RequestUsage  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.agent import accountant as accounting  # noqa: E402
from components.agent import conversation as kept  # noqa: E402
from components.agent import guide as guide_read  # noqa: E402
from components.agent import tools  # noqa: E402
from components.agent.config import unlimited  # noqa: E402
from components.agent.conversation import Conversation  # noqa: E402
from components.agent.steady import steady  # noqa: E402
from components.agent.tools import Bench  # noqa: E402
from components.examples.examples import render as render_examples  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio.draft import OPERATIONS  # noqa: E402

Op = Literal[tuple(OPERATIONS)]


# ---- what one request works with ------------------------------------------

@dataclass
class Work:
    """One request from the person, and everything the builder reaches in it.

    `now` is what the person just said. `spent` is what the accountant has
    used so far in this request; the builder's own use is the framework's to
    count, and `overspent` adds the two.
    """

    bench: Bench
    conversation: Conversation = field(default_factory=Conversation)
    config: object = field(default_factory=unlimited)
    now: str = ""
    watch: object = None
    module: str | None = None
    spent: dict = field(default_factory=lambda: {
        "requests": 0, "input": 0, "output": 0, "dollars": 0.0})
    # Why the request is on its last call, once it is: the agent was told to
    # end the turn, and any call after that one is refused.
    ending: str | None = None

    def overspent(self, usage):
        """What of the budget the request has gone past, or None. `usage` is
        the builder's so far."""
        budget = self.config.budget
        requests = usage.requests + self.spent["requests"]
        tokens = (usage.input_tokens + usage.output_tokens
                  + self.spent["input"] + self.spent["output"])
        if budget.requests is not None and requests >= budget.requests:
            return f"{requests} model calls, the budget is {budget.requests}"
        if budget.tokens is not None and tokens >= budget.tokens:
            return f"{tokens} tokens, the budget is {budget.tokens}"
        dollars = self.dollars(usage)
        if budget.dollars is not None and dollars is not None \
                and dollars >= budget.dollars:
            return f"${dollars:.2f}, the budget is ${budget.dollars:.2f}"
        return None

    def last_call(self, usage, last):
        """Why the next call is the last one the budget has room for, or None.

        `last` is the size of the builder's last call (a provider's usage), the
        best guess at the next one's. A call is the last when after it there
        would be no room for another: one is always kept back for the agent to
        tell the person where it stopped.
        """
        budget = self.config.budget
        requests = usage.requests + self.spent["requests"]
        if budget.requests is not None and budget.requests - requests <= 1:
            return f"{requests} of its {budget.requests} model calls are used"
        if last is None:
            return None
        size = last.input_tokens + last.output_tokens
        tokens = (usage.input_tokens + usage.output_tokens
                  + self.spent["input"] + self.spent["output"])
        if budget.tokens is not None and size \
                and (budget.tokens - tokens) / size < 2:
            return f"{tokens} of its {budget.tokens} tokens are used"
        dollars = self.dollars(usage)
        # At the full price: the provider's cache may not serve the next call,
        # and the goodbye, which may call nothing but a reply, it seldom does.
        each = self.config.cost("builder", RequestUsage(
            input_tokens=last.input_tokens, output_tokens=last.output_tokens))
        if budget.dollars is not None and dollars is not None and each \
                and math.floor((budget.dollars - dollars) / each) < 2:
            return f"${dollars:.2f} of its ${budget.dollars:.2f} is spent"
        return None

    def dollars(self, usage):
        """The request's cost so far, or None when a part has no price."""
        builder = self.config.cost("builder", usage)
        if builder is None or self.spent["dollars"] is None:
            return None
        return builder + self.spent["dollars"]

    async def reckon(self, example, happened, wanted):
        """Put one situation to the accountant, keep its answer, say it back."""
        part = self.config.part("accountant")
        result = await accounting.accountant(part.model, watch=self.watch).run(
            accounting.prompt(self.conversation.said(self.now), happened, wanted),
            model_settings=self.config.settings("accountant"))
        usage = result.usage
        self.spent["requests"] += usage.requests
        self.spent["input"] += usage.input_tokens
        self.spent["output"] += usage.output_tokens
        cost = self.config.cost("accountant", usage)
        self.spent["dollars"] = None if cost is None or self.spent["dollars"] is None \
            else self.spent["dollars"] + cost
        answer = result.output
        self.conversation.reckonings[example] = {
            "happened": list(happened), "wanted": list(wanted),
            "figures": [f.model_dump() for f in answer.figures],
            "question": answer.question, "by": part.label}
        return reckoned(example, self.conversation.reckonings[example])


def reckoned(example, reckoning):
    """What the accountant answered, as the builder reads it."""
    lines = [f"The accountant worked out, for {example}:"]
    for figure in reckoning["figures"]:
        value = figure["value"] if figure["value"] != "" else "(empty)"
        lines.append(f"    {figure['figure']} = {value} — {figure['working']}")
    if not reckoning["figures"]:
        lines.append("    nothing yet")
    if reckoning["question"]:
        lines.append(f"It asks: {reckoning['question']}")
        lines.append("Put that to the person before writing the example; then "
                     "reckon again with their answer.")
    else:
        lines.append("Write the example's expected numbers from these values.")
    return "\n".join(lines)


# ---- what a step is, as a model writes one --------------------------------
#
# Flat on purpose: a list of objects with string fields, and nothing a small
# model or a strict provider could stumble on — no maps with free keys, no
# unions. The studio checks every value; the schema only has to carry them.

class Arg(BaseModel):
    """One argument of a step."""

    name: str = Field(description="the argument's name, as `options` lists it")
    value: str = Field(description="its value, as text")


class Step(BaseModel):
    """One studio step."""

    op: Op = Field(description="which step")
    args: list[Arg] = Field(default_factory=list, description="its arguments")


# ---- how a turn ends ------------------------------------------------------

class Reply(BaseModel):
    """Say something to the person and wait for them: what you did, what you
    found, or what you are going to do next. In their language, in business
    words."""

    message: str


class Question(BaseModel):
    """Ask the person something only they can answer, and wait. Offer choices
    whenever the answers can be listed."""

    question: str
    choices: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """Put your plan before the person and wait for them to agree, before you
    write any rule that computes a number: what you will build, from which
    records, which numbers come out, and what of their request the system
    cannot do yet. In their language and their words. They agree or tell you
    what to change; you cannot agree for them."""

    message: str = Field(description="what you ask of them, briefly")
    builds: str = Field(description="what you will build, in a sentence or two")
    records: list[str] = Field(
        default_factory=list,
        description="the records the numbers come from, one each, in the "
                    "person's words: what they record already and what they "
                    "will record — never a module's name or an English name "
                    "it is recorded under")
    numbers: list[str] = Field(
        default_factory=list,
        description="each number that comes out: what, for whom, as of when")
    cannot: list[str] = Field(
        default_factory=list,
        description="what of their request the system cannot do yet; empty "
                    "when it can do all of it")


class Proposal(BaseModel):
    """Put a draft before the person: ask them to agree to the examples you
    proposed, and — when nothing else is missing — say it is ready to be
    sealed. They agree and seal; you cannot."""

    module: str = Field(description="the module whose draft this is, @scope/name")
    message: str = Field(description="what you are asking of them, in business words")
    agree: list[str] = Field(default_factory=list,
                             description="the examples you ask them to agree to")
    seal: bool = Field(default=False,
                       description="whether it is ready to be sealed once they agree")


# ---- the tools, as the framework calls them --------------------------------

# A reading that comes out as it did the last time it was read is answered in
# one line: the model still has the reading, and need not be sent it twice.

def look(ctx: RunContext[Work], module: str, part: str = "draft") -> str:
    return kept.unchanged(ctx.messages, "look", {"module": module, "part": part},
                          tools.look(ctx.deps.bench, module, part))


def options(ctx: RunContext[Work], module: str, op: str = "") -> str:
    return kept.unchanged(ctx.messages, "options", {"module": module, "op": op},
                          tools.options(ctx.deps.bench, module, op))


def do(ctx: RunContext[Work], module: str, steps: list[Step]) -> str:
    return tools.do(ctx.deps.bench, module, [s.model_dump() for s in steps])


def catalogue(ctx: RunContext[Work], text: str = "", kind: str = "",
              fills: str = "", module: str = "") -> str:
    return kept.unchanged(
        ctx.messages, "catalogue",
        {"text": text, "kind": kind, "fills": fills, "module": module},
        tools.catalogue(ctx.deps.bench, text, kind, fills, module))


def guide(ctx: RunContext[Work], topic: str = "workflow") -> str:
    if topic in guide_read.GIVEN:
        return (f"The topic {topic} is in your instructions already; read it there. "
                f"Other topics: {', '.join(t for t in guide_read.TOPICS if t not in guide_read.GIVEN)}.")
    return kept.unchanged(ctx.messages, "guide", {"topic": topic},
                          tools.guide(ctx.deps.bench, topic))


async def reckon(ctx: RunContext[Work], example: str, happened: list[str],
                 wanted: list[str]) -> str:
    """Ask the accountant for an example's numbers, before you write them.

    The accountant reads what the person said and the situation you give it,
    never the graph, and works out each figure with how it got there — or asks
    the question the person's words leave open. An example goes to the person
    only when every number it expects is one the accountant gave for it.

    example   the example's name, as it is or will be in the draft
    happened  what exists and what happened in it, one line each, in business
              words, with every quantity, unit and day
    wanted    the figures, one per number the example will expect, in
              business words (what, for whom, as of when)
    """
    return await ctx.deps.reckon(example, happened, wanted)


for wrapper, tool in ((look, tools.look), (options, tools.options), (do, tools.do),
                      (catalogue, tools.catalogue), (guide, tools.guide)):
    wrapper.__doc__ = tool.__doc__

TOOLS = (look, options, do, catalogue, guide, reckon)


# ---- the proposal, checked -----------------------------------------------

def unsupported(work, proposal):
    """What a proposal claims that the draft does not bear out, or None."""
    try:
        report = work.bench.state(proposal.module)
    except Refusal as exc:
        return exc.sentence()
    held = {e["name"]: e for e in report["examples"]}
    unknown = [n for n in proposal.agree if n not in held]
    if unknown:
        return (f"{', '.join(unknown)} is not an example of {proposal.module}; "
                f"its examples are {', '.join(held) or 'none'}")
    agreed = [n for n in proposal.agree if held[n]["agreed"]]
    if agreed:
        return f"{', '.join(agreed)} is agreed already; propose only proposals"
    unrun = [n for n in proposal.agree if held[n]["passed"] is None]
    if unrun:
        return (f"{', '.join(unrun)} has not run, so nobody knows what it does; "
                f"an example is put to the person once it has run")
    failing = [n for n in proposal.agree
               if held[n]["passed"] is False and not held[n].get("waits")]
    if failing:
        return (f"{', '.join(failing)} fails; an example is put to the person "
                f"when the graph bears it out, or waits only for its rules, or "
                f"with the question of which is wrong")
    for name in proposal.agree:
        problem = unreckoned(name, held[name], work.conversation.reckonings.get(name))
        if problem:
            return problem
    if not proposal.seal:
        return None
    if report.get("empty"):
        return "it is not ready: the draft declares nothing yet"
    if report["examples"] and not report["examples_run"]:
        return "the examples could not be run, so nothing can be called ready"
    waiting = {h["refusal"]["where"].removeprefix("example ")
               for h in report["holes"]
               if h["blocking"] and h["kind"] == "example_not_agreed"}
    others = [h for h in report["holes"]
              if h["blocking"] and h["kind"] != "example_not_agreed"]
    if others or waiting - set(proposal.agree):
        return ("it is not ready: once the person agrees to what you propose, "
                "this is what the draft would still be standing in —\n"
                + tools.standing(report))
    return None


def unreckoned(name, example, reckoning):
    """Why an example's numbers are not the accountant's, or None when they are.

    Each number the example expects must be a value the accountant gave for
    that example: the builder writes where a number goes, never what it is.
    """
    if reckoning is None:
        return (f"nobody but you worked out the numbers of {name}. Call `reckon` "
                f"with its situation and the figures it expects, and write its "
                f"numbers from the answer")
    if reckoning["question"]:
        return (f"the accountant left a question open about {name}: "
                f"{reckoning['question']} Ask the person, then `reckon` again")
    given = {_number(f["value"]) for f in reckoning["figures"]}
    strays = [f"{c['table']} {c['row']} {c['column']} = {c['expected']}"
              for c in example["checks"]
              if c["column"] and _number(c["expected"]) not in given]
    if strays:
        values = ", ".join(f["value"] or "(empty)" for f in reckoning["figures"])
        return (f"{name} expects {'; '.join(strays)}, which the accountant did not "
                f"work out for it (it gave {values or 'nothing'}). Write the numbers "
                f"from its answer, or `reckon` again if the situation you gave it is "
                f"not the example's")
    return None


def _number(value):
    """A value as a number to compare, or None for an empty one. Text that is
    not a number is kept as it is, so it matches only itself."""
    if value is None or str(value).strip() in ("", "~", "None"):
        return None
    try:
        return Decimal(str(value).strip()).normalize()
    except InvalidOperation:
        return str(value).strip()


def put_before(work, proposal):
    """What the person is shown: the system's reading of the draft, not the
    agent's. Each example proposed with what it says, every number, and how
    the accountant worked the numbers out."""
    report = work.bench.state(proposal.module)
    lines = [f"{report['name']} — {report['title'] or 'untitled'}"]
    shown = [e for e in report["examples"] if e["name"] in proposal.agree]
    if shown:
        lines.append("Examples to agree to:")
    for example in shown:
        lines += [f"  {line}" for line in render_examples([example])]
        reckoning = work.conversation.reckonings.get(example["name"])
        if reckoning:
            lines.append("    worked out by the accountant, from your words:")
            lines += [f"      {f['figure']} = {f['value'] or '(empty)'}: {f['working']}"
                      for f in reckoning["figures"]]
    if proposal.seal:
        lines.append(f"Ready to be sealed as {report['becomes']}"
                     + (" once they are agreed." if shown else "."))
    return "\n".join(lines)


# ---- the last call ---------------------------------------------------------

# What the agent is told on the call the budget keeps for it, as a note from
# the system at the end of what it is sent.
ENDING = ("(From the system, not the person: this request has reached its budget — "
          "{why}. Take no more steps and call no tool. End the turn now with a "
          "Reply to the person, in their language and in business words: what you "
          "did in this request, what is still left to do, and that they can ask you "
          "to carry on from the draft as it is. Any example of yours they can agree "
          "to now is put before them beside your reply by the system, with its "
          "numbers: say what it shows in their words, never by its name.)")


def ending(request_context, why):
    """The request as it goes out on its last call: the note at its end, and
    only a reply allowed. What is sent before the note is unchanged, so the
    provider's cache still serves it."""
    messages = list(request_context.messages)
    last = messages[-1]
    messages[-1] = replace(last, parts=[*last.parts, UserPromptPart(ENDING.format(why=why))])
    reply = next(t.name for t in request_context.model_request_parameters.output_tools
                 if t.name.endswith("_Reply"))
    settings = {**(request_context.model_settings or {}), "tool_choice": [reply]}
    return replace(request_context, messages=messages, model_settings=settings)


def _last_size(messages):
    """The usage of the builder's last call in `messages`, or None."""
    for message in reversed(messages):
        if isinstance(message, ModelResponse) and message.usage.input_tokens:
            return message.usage
    return None


# ---- the agent -------------------------------------------------------------

def builder(model=None, *, retries=3, watch=None):
    """The agent that builds, on `model`. Nothing about it depends on which.
    With a `watch`, every call it makes is written down."""
    hooks = Hooks()

    @hooks.on.before_model_request
    async def _within_budget(ctx: RunContext[Work], request_context):
        work = ctx.deps
        problem = work.overspent(ctx.usage) or work.ending
        if problem:
            raise UsageLimitExceeded(f"this request has spent its budget: {problem}")
        messages = kept.cleared(request_context.messages, work.config.clear_above)
        if messages is not request_context.messages:
            request_context = replace(request_context, messages=messages)
        why = work.last_call(ctx.usage, _last_size(messages))
        if why:
            work.ending = why
            return ending(request_context, why)
        return request_context

    agent = Agent(
        model,
        name="builder",
        deps_type=Work,
        output_type=[Reply, Question, Plan, Proposal],
        instructions=guide_read.instructions(),
        tools=list(TOOLS),
        retries=retries,
        capabilities=[hooks, steady("builder", watch)]
        + ([watch.hooks("builder")] if watch else []),
        defer_model_check=True,
    )

    @agent.output_validator
    def _honest(ctx: RunContext[Work], output):
        if isinstance(output, Proposal):
            problem = unsupported(ctx.deps, output)
            if problem:
                raise ModelRetry(f"That proposal cannot go to the person: {problem}")
        return output

    return agent


__all__ = ["ENDING", "Arg", "Plan", "Proposal", "Question", "Reply", "Step", "TOOLS", "Work",
           "builder", "ending", "put_before", "reckoned", "unreckoned", "unsupported"]

"""builder — the agent that builds graphs, assembled from the tools and the guide.

Which model it runs on is not decided here. `builder(model)` takes whatever
the agent framework accepts — a `provider:name` string, a model object, a
test model — so the choice of provider is configuration, and nothing in this
file names one.

A turn ends one of three ways, each a structured answer the page can draw:

    Reply      something said to the person, who answers when they like
    Question   something only the person can answer, with choices where there are
    Proposal   the draft put before the person: the examples to agree to, and
               whether it is ready to be sealed

A proposal is checked before it reaches anybody. The agent may only propose
examples that are still proposals, and may only say a draft is ready when the
one thing it is waiting for is the person's agreement to those examples. A
proposal that says more than the draft bears out is handed back to the agent
with what the draft is actually standing in, and it tries again. What the
person then sees is `put_before()`: the examples and their numbers, read off
the draft by the system — not the agent's summary of them.
"""

import os
import sys
from pathlib import Path
from typing import Literal

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic import BaseModel, Field  # noqa: E402
from pydantic_ai import Agent, ModelRetry, RunContext  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from components.agent import guide as guide_read  # noqa: E402
from components.agent import tools  # noqa: E402
from components.agent.tools import Bench  # noqa: E402
from components.examples.examples import render as render_examples  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio.draft import OPERATIONS  # noqa: E402

Op = Literal[tuple(OPERATIONS)]


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

def look(ctx: RunContext[Bench], module: str, part: str = "draft") -> str:
    return tools.look(ctx.deps, module, part)


def options(ctx: RunContext[Bench], module: str, op: str = "") -> str:
    return tools.options(ctx.deps, module, op)


def do(ctx: RunContext[Bench], module: str, steps: list[Step]) -> str:
    return tools.do(ctx.deps, module, [s.model_dump() for s in steps])


def catalogue(ctx: RunContext[Bench], text: str = "", kind: str = "",
              fills: str = "", module: str = "") -> str:
    return tools.catalogue(ctx.deps, text, kind, fills, module)


def guide(ctx: RunContext[Bench], topic: str = "workflow") -> str:
    return tools.guide(ctx.deps, topic)


for wrapper, tool in ((look, tools.look), (options, tools.options), (do, tools.do),
                      (catalogue, tools.catalogue), (guide, tools.guide)):
    wrapper.__doc__ = tool.__doc__


# ---- the proposal, checked -----------------------------------------------

def unsupported(bench, proposal):
    """What a proposal claims that the draft does not bear out, or None."""
    try:
        report = bench.state(proposal.module)
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
    failing = [n for n in proposal.agree if held[n]["passed"] is False]
    if failing:
        return (f"{', '.join(failing)} fails; an example is put to the person "
                f"when the graph bears it out, or with the question of which is wrong")
    if not proposal.seal:
        return None
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


def put_before(bench, proposal):
    """What the person is shown: the system's reading of the draft, not the
    agent's. Each example proposed, with what it says and every number."""
    report = bench.state(proposal.module)
    shown = [e for e in report["examples"] if e["name"] in proposal.agree]
    lines = [f"{report['name']} — {report['title'] or 'untitled'}"]
    if shown:
        lines.append("Examples to agree to:")
        lines += [f"  {line}" for line in render_examples(shown)]
    if proposal.seal:
        lines.append(f"Ready to be sealed as {report['becomes']} once they are agreed.")
    return "\n".join(lines)


# ---- the agent -------------------------------------------------------------

def builder(model=None, *, retries=3):
    """The agent that builds, on `model`. Nothing about it depends on which."""
    agent = Agent(
        model,
        name="builder",
        deps_type=Bench,
        output_type=[Reply, Question, Proposal],
        instructions=guide_read.instructions(),
        tools=[look, options, do, catalogue, guide],
        retries=retries,
        defer_model_check=True,
    )

    @agent.output_validator
    def _honest(ctx: RunContext[Bench], output):
        if isinstance(output, Proposal):
            problem = unsupported(ctx.deps, output)
            if problem:
                raise ModelRetry(f"That proposal cannot go to the person: {problem}")
        return output

    return agent


__all__ = ["Arg", "Proposal", "Question", "Reply", "Step", "builder", "put_before",
           "unsupported"]

"""accountant — works out an example's numbers from the business's words alone.

The builder writes the map and the examples the map is held to. If it also
chose the numbers, a misunderstanding would sit on both sides of the check and
the check would pass: the map would count a return twice and the example would
expect it counted twice. So the numbers come from somewhere else. The
accountant is a second model call with a context of its own. It is given what
the person said, the questions the person was asked, and one situation in the
business's words — and never the map, the draft, the tools, or anything the
builder concluded. It answers each figure asked with a number and how it came
to it, or with the question the person's words leave open.

It has no tools and changes nothing. What it answers is kept beside the draft
(`conversation`), the builder writes the example from it, and a proposal whose
numbers the accountant did not work out does not reach the person.
"""

import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic import BaseModel, Field  # noqa: E402
from pydantic_ai import Agent  # noqa: E402

from components.agent.steady import steady  # noqa: E402

INSTRUCTIONS = """\
You are the accountant of a business. You are told what the business said, in
its own words, and one small situation: some things that exist and some things
that happened. You work out the figures you are asked for.

You never see how the business's software is built, and you do not need to:
count what the business's words say.

For each figure:
- give the number, and how you came to it, in the business's words, short
  enough to check by hand;
- count each event once. If the same event is told twice (two records of one
  delivery, say), count it once and say which one you counted;
- mind the direction: what goes out lowers what is held, what comes in raises
  it. Say which way you counted when the words could be read both ways;
- mind the unit and the period: convert only as the business says, and count
  only what falls in the period the figure asks about;
- when a figure has nothing to count (nobody set the value it needs), say so:
  its value is empty, which is not nought.

When the business's words leave open something that changes a number, do not
guess. Ask it in `question`, in the business's words, and give figures only for
what is settled.

Write each value as a plain number: digits, a minus sign when it is below
nought, a decimal point when it has a fraction. No thousands separators, no
units, no currency. An empty value is written as an empty string.
"""


class Figure(BaseModel):
    """One figure worked out."""

    figure: str = Field(description="the figure, as it was asked for")
    value: str = Field(description="the number: digits, '-' and '.' only; "
                                   "empty when there is nothing to count")
    working: str = Field(description="how it comes to that, in the business's words")


class Reckoning(BaseModel):
    """The figures asked for, and what the business's words leave open."""

    figures: list[Figure] = Field(default_factory=list)
    question: str = Field(default="", description="what must be asked of the person "
                                                  "before a figure can be given; "
                                                  "empty when nothing is open")


def accountant(model=None, *, watch=None):
    """The accountant, on `model`. Nothing about it depends on which.
    With a `watch`, every call it makes is written down."""
    return Agent(model, name="accountant", output_type=Reckoning,
                 instructions=INSTRUCTIONS, defer_model_check=True,
                 capabilities=[steady("accountant", watch)]
                 + ([watch.hooks("accountant")] if watch else []))


def prompt(said, happened, wanted):
    """What the accountant reads: the person's words, one situation, the figures.

    `said` is the conversation as the person had it — what they said and what
    they were asked — and nothing the builder did in between.
    """
    lines = ["What the business said:"]
    lines += [f"- {line}" for line in said] or ["- nothing yet"]
    lines += ["", "The situation:"]
    lines += [f"- {line}" for line in happened]
    lines += ["", "Work out:"]
    lines += [f"- {figure}" for figure in wanted]
    return "\n".join(lines)


__all__ = ["Figure", "INSTRUCTIONS", "Reckoning", "accountant", "prompt"]

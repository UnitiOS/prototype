"""guide — what an agent needs to know to build a graph here, read off the system.

An agent building modules has to know the steps, the rules a column can carry,
how a business example is written, and every way the system says no. All of
that already exists — in the studio's closed list of operations, the refusal
catalogue, the examples' closed shapes, the store's roles — so the guide is
**generated** from those, on every read, and cannot fall behind them. A test
holds it to naming every operation, every refusal and every opening.

What is written by hand here is only what no list in the code can say: the
order to work in and why, and what a rule means. It is kept short, it names no
business, and wherever it states a name the code also has, the name is taken
from the code.

One section per topic, asked for when needed. The instructions an agent starts
with are `instructions()`: how to work, the rules and how examples are written
— which every build needs, and which a model otherwise spends a call on each
— and the list of the other topics, read when the work calls for one.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "compiler"))

from compile import SYNTAX  # noqa: E402
from components.examples.examples import (  # noqa: E402
    COMPUTED, EXAMPLE_KEYS, EXPECT_KEYS, RECORD_KEYS,
)
from components.modules import catalogue as catalogue_read  # noqa: E402
from components.refusal import CODES, Refusal  # noqa: E402
from components import standard  # noqa: E402
from components.studio.draft import OPERATIONS, plan_of  # noqa: E402
from components.studio.read import ANSWERS, OPEN  # noqa: E402

REFUSAL_SOURCE = ROOT / "components" / "refusal" / "refusal.py"


# ---- written by hand: the order of work, and what the rules mean -----------

WORKFLOW = """\
You build business graphs for a person, through the studio's steps. You never
write a file: every change is one step from a closed list, and the system
writes the files. You propose; the system checks everything a machine can
check; the person approves.

Work in this order; the system holds you to it. Stages 2, 3 and 5 end your
turn; the next starts when the person has answered.

1. Understand. Learn what the business does and what it wants to know, in its
   own words, and search the catalogue for what is recorded already. Ask about
   anything whose meaning is not certain — which way an amount runs, its unit,
   whether the same event is recorded elsewhere too, when something counts as
   happened — that neither their words nor the module recording it says.
   Offer choices where you can.
2. Plan. End the turn with a Plan: what you will build, from which records
   (a sealed module's, where one records them), which numbers come out, and
   what the system cannot do yet. Wait for the person to agree; a changed
   plan is agreed again. Until then nothing is built, not even the draft.
3. Examples. Start the draft; declare, without rules, every class and slot
   the tables will show, looked-up columns too. Write examples giving each
   column its value, numbers from the accountant (below); propose them. An
   example waiting only for its rules is agreed to as it is. Only the person
   agrees.
4. Rules. Write the rules until every example holds; a rule needs an agreed
   example giving its table's numbers. A column no agreed example checks
   needs a new one (agreed ones cannot change): end the turn proposing it.
   Never change an expected number to make the graph pass: if you think an
   agreed number is wrong, say which and why, and let the person decide. A
   blocking hole must be answered before a seal; its fix names the step.
5. Seal. When the only thing left is the person's agreement, propose it as
   ready to be sealed. You cannot seal and you cannot agree.

Read in as few rounds as you can: several `catalogue`, `look` or `options`
calls side by side cost one round, and every round resends the conversation;
`catalogue` with `module` and `options` with `op` take comma-separated names.
Never read again what you read earlier in this conversation, nor the steps
described below. Take steps in batches; give a slot its description, unit,
direction or time meaning in the `add_slot` that declares it.

How you speak to the person:
- follow their language and their way of writing;
- read from how they write how much they know, and say as much as they need;
- use a technical word only when they used it first — never a step name, a
  refusal code, YAML or the English a module is recorded in otherwise — and
  call things by their own words for them;
- when you are not sure how much detail they want, ask.
"Agreed, go on." from a button on their page does not change their language."""

RULES = f"""\
A module declares classes (kinds of thing) and slots (what is said about
them). A slot goes on a class with `attach`. Two kinds of table come out:

    an entity table   one row per thing somebody states: a class whose rows
                      are recorded. Its columns are what was stated. A rule on
                      one of its columns is refused — nothing would run it.
    a grouped table   one row per combination of key values, computed from
                      rows underneath: a class with at least one `aggregate`.
                      Its columns without a rule are the keys it groups by.

A column of a grouped table is computed by one of three rules — the column
kinds {", ".join(f"`{kind}`" for kind in COMPUTED)}:

    aggregate    total a slot over every entity of a class or of a role:
                 `over` the class, `sum` the slot, `by` key=slot pairs saying
                 which slot of the source matches each key. `where` narrows
                 the source to rows whose slot is one class (slot=Class).
                 `convert_using`, `convert_on` and `convert_factor` multiply
                 each row by a factor read off another class, matched on
                 slots, before totalling.
    parameter    read one fact off the thing a key names: `of` the key
                 column, `slot` the slot of the thing it names. Where nobody
                 stated the fact, the cell is empty — not nought.
    expression   arithmetic on other columns of the same table: {SYNTAX}.
                 A value from another table is brought in first by an
                 aggregate or a parameter.

Roles are shared words across modules, found in the catalogue: a role names
bindings, and a class that fills a role (`fill_role`) names which of its slots
fills each binding (`bind`). An aggregate may be written `over` a role, and
then every class filling it counts — only when that is truly meant. When two
modules record the same event, totalling the role counts it twice; name the
class instead. An application says explicitly what it counts from which
module.

What the system cannot do yet: total only the rows whose value meets a
condition (`where` narrows by the class a slot points at, never by a value),
and group by a fact reached through another record (each key of `by` is a
slot of the rows totalled themselves). When a request needs one of these, say
so to the person plainly, in a reply, and build nothing else in its place.

For something to be stated, its class must carry the slot that says which
class an entity is — usually by filling a role that brings it. One slot per
class is its `identifier`, the name somebody states it under."""

EXAMPLES = f"""\
A business example is the person's word on what the numbers must be. It has
`says` (the example in the business's own words), `records` and `expect`; an
example has only these keys: {", ".join(EXAMPLE_KEYS)}.

    records   stated as a form states them, one at a time: {", ".join(RECORD_KEYS)}.
              `record` is a word naming it; another record points at it by
              that word. `class` says what it is, the first time. `facts` are
              slot=value pairs. `when` is the day it became true. The same
              record stated again with a later `when` is that thing changing.
    expect    the numbers: {", ".join(EXPECT_KEYS)}. `table` is a class,
              `row` is the value of its first column (a record's word, when
              that column names a record) or column=value pairs, `values` are
              column=number pairs. Nothing after `=` means the cell must be
              empty, which is not nought. `at` is the day the table is read;
              without it, after everything.

Each example runs in a log of its own, through the same form and the same
compiler as real data, so a value the form refuses is refused in the example
too. Every column a draft computes needs a number in some example before the
draft can be sealed.

Write examples that would catch the mistakes that matter: an amount running
the wrong way, a unit mixed up, one event counted twice, something recorded
late or corrected, a value nobody stated (empty, not nought). A number you
cannot work out from what the person said is a question to ask them, not a
number to guess.

The numbers come from the accountant. Decide the whole example first, then
call `reckon` once for it, and record exactly the situation you described.
Call `reckon` with the example's name,
what exists and what happened in it (one line each, in business words, with
every quantity and day), and the figures wanted (one per number the example
will expect, such as "on hand for X at the end of June"). Write `expect` from
the values it gives. An example is only put to the person when every number it
expects is one the accountant worked out for that example."""

TOPICS = {
    "workflow": "the order to work in, and what you may and may not do",
    "steps": "every studio step, what it does and what it takes",
    "rules": "classes, slots, the two kinds of table, and the three rules",
    "examples": "how a business example is written and run",
    "holes": "the questions a draft is standing in, and which block a seal",
    "standard": "how every module is recorded: language, names, meaning, procedure",
    "refusals": "every way the system says no, by who says it",
    "roles": "the shared roles in the store, their bindings and who fills them",
}


# ---- generated: read off the system on every call --------------------------

# What each kind of argument means, in the words of OPERATIONS' own comment.
KINDS = {
    "text": "free text", "word": "a new name: a letter, then letters, digits or _",
    "uri": "a URI or prefix:name", "moment": "a day such as 2026-06-30, or a moment",
    "pin": "a sealed version, @scope/name@vN", "held_pin": "a version this draft pins",
    "own_class": "a class this draft declares", "own_slot": "a slot this draft declares",
    "own_enum": "an enum this draft declares", "own_example": "an example of this draft",
    "record": "a record of that example", "class": "a class in sight",
    "slot": "a slot in sight", "role": "a role in sight", "binding": "a binding in sight",
    "range": "a type, class or enum in sight", "field": "one of the fields listed",
    "column": "a slot of the class named", "mapping": "pairs written key=value, key=value",
    "direction": "what a positive number means: " + ", ".join(standard.DIRECTIONS),
    "time_meaning": "what moment a date is: " + ", ".join(standard.TIME_MEANINGS),
    "term": "a class, slot, enum, Enum.value or example of this draft, or `module`",
    "language": "a language tag: id, en, ms, es, pt-BR",
}


def _steps():
    lines = ["Every step, what it does, and what it takes. Call `options` only for",
             "the answers that fit a draft right now — the pins, classes or slots",
             "a step may name — never to read a step described here. Argument kinds:"]
    lines += [f"    {kind:<12} {meaning}" for kind, meaning in KINDS.items()]
    for op, spec in OPERATIONS.items():
        lines.append("")
        lines.append(f"{op}: {spec['does']}")
        takes = [f"{k} ({v})" for k, v in spec["takes"].items()]
        may = [f"{k} ({v})" for k, v in spec["may"].items()]
        lines.append(f"    takes: {', '.join(takes) or 'nothing'}")
        if may:
            lines.append(f"    may:   {', '.join(may)}")
    return "\n".join(lines)


def _sections():
    """Each refusal code under the gate the refusal catalogue files it under."""
    section, out = None, {}
    for line in REFUSAL_SOURCE.read_text(encoding="utf-8").splitlines():
        header = re.match(r"\s*# ---- (.+?) -*$", line)
        if header:
            section = header.group(1)
            continue
        code = re.match(r'\s*"([a-z_]+)":', line)
        if code and code.group(1) in CODES:
            out.setdefault(section, []).append(code.group(1))
    return out


def _refusals():
    lines = ["Every refusal names where, what was expected, what it got, and how",
             "to fix it — with the finite set of answers wherever there is one.",
             "Read the fix; it is usually the next step."]
    for section, codes in _sections().items():
        lines.append("")
        lines.append(section)
        lines += [f"    {code}: {CODES[code]}" for code in codes]
    return "\n".join(lines)


def _holes():
    lines = ["A draft read by the studio is a list of holes. A blocking hole is",
             "something the seal would refuse; it carries the refusal and, where",
             "the studio has one, the step that answers it. These refusals come",
             "with a step: " + ", ".join(ANSWERS) + ".",
             "",
             "An open question blocks nothing and is still worth answering:"]
    lines += [f"    {kind}: {meaning}" for kind, meaning in OPEN.items()]
    return "\n".join(lines)


def _roles(store):
    if store is None:
        return "No store to read the roles from."
    found = catalogue_read.find(catalogue_read.catalogue(store), kind="role")["entries"]
    lines = ["The roles the store offers. A class fills a role with `fill_role`,",
             "then names the slot filling each binding with `bind`."]
    for role in found:
        lines.append("")
        pin = f"{role['module']['name']}@{role['module']['version']}"
        above = f", a kind of {', '.join(role['fills'])}" if role["fills"] else ""
        lines.append(f"{role['name']} ({pin}{above})")
        if role["description"]:
            lines.append(f"    {' '.join(role['description'].split())}")
        for binding in role["bindings"]:
            lines.append(f"    binding {binding['name']}"
                         + (f": {binding.get('range')}" if binding.get("range") else ""))
        filled = [f"{f['class']} ({f['module']['name']}@{f['module']['version']})"
                  for f in role["filled_by"]]
        lines.append(f"    filled by: {', '.join(filled) or 'nothing yet'}")
    return "\n".join(lines)


def section(topic, store=None):
    """One topic of the guide, or the list of topics when there is no such one."""
    if topic == "workflow":
        return WORKFLOW
    if topic == "steps":
        return _steps()
    if topic == "rules":
        return RULES
    if topic == "examples":
        return EXAMPLES
    if topic == "holes":
        return _holes()
    if topic == "standard":
        return standard.teach()
    if topic == "refusals":
        return _refusals()
    if topic == "roles":
        return _roles(store)
    return (f"There is no topic {topic!r}. The topics are:\n"
            + "\n".join(f"    {name}: {what}" for name, what in TOPICS.items()))


# The topics an agent starts with, in `instructions()`: every build reads
# them, and a topic read with `guide` costs a round and is sent again with
# every round after it, while the instructions are the same at the top of
# every call, which a provider can serve from its cache.
GIVEN = ("workflow", "standard", "rules", "examples", "steps", "holes")


# Said once in the instructions, so that the instructions never change: which
# module is open, and where it stands, comes with each message (`opened`).
OPENED = """\
Each message from the person starts with a note from the system, in
parentheses: which module they have open and where it stands. Everything you
build for them goes in that module, and a proposal is about it. Other modules
are read with `catalogue` and pinned; they are not changed from here. A tool
answer that starts with [unchanged] or [cleared] points you to a reading you
already have in this conversation."""


def instructions():
    """What an agent starts with: how to work, and where to read the rest. The
    same text on every call of every request."""
    given = GIVEN
    return (WORKFLOW
            + "\n\n" + OPENED
            + "\n\n# Recording standard\n\n" + standard.teach()
            + "\n\n# Rules\n\n" + RULES
            + "\n\n# Examples\n\n" + EXAMPLES
            + "\n\n# Steps\n\n" + _steps()
            + "\n\n# Holes\n\n" + _holes()
            + "\n\nThose are the guide's topics " + ", ".join(given) + ": you have "
            "them, so do not read them again. The rest of the guide is one topic at "
            "a time; read one only when the work needs it, and once:\n"
            + "\n".join(f"    {name}: {what}" for name, what in TOPICS.items()
                        if name not in given))


# How the note opening every request begins; a rehearsal counts requests by it.
OPENS = "(From the system, not the person: they have "


def opened(store, module):
    """Which module the person has open, where it stands and where its plan
    stands — said to the agent with the person's message at the start of
    every request, read off the store each time."""
    try:
        sealed = store.versions(module)
    except Refusal:
        sealed = []
    draft = (store.place(module) / "draft.yaml").is_file()
    if draft:
        state = "Its draft is open: `look` at it before anything else."
    elif sealed:
        state = (f"It is sealed up to {sealed[-1]['version']} and has no draft: `revise` "
                 f"opens one from the latest version.")
    else:
        state = "It does not exist yet: `start` creates it and opens its draft."
    plan = plan_of(store, module)
    if plan is None:
        planned = "No plan is put forward yet: nothing is built before one is agreed."
    elif plan.get("agreed"):
        planned = "The person agreed to your plan."
    else:
        planned = "Your plan waits for the person's agreement: nothing is built until then."
    return f"{OPENS}{module} open. {state} {planned})"


__all__ = ["GIVEN", "OPENED", "OPENS", "TOPICS", "instructions", "opened", "section"]

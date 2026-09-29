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
with are `instructions()`: who it works for, what it may and may not do, and
the list of topics — not the whole guide, which would be read once and then
drowned by everything after it.
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
from components.refusal import CODES  # noqa: E402
from components.studio.draft import OPERATIONS  # noqa: E402
from components.studio.read import ANSWERS, OPEN  # noqa: E402

REFUSAL_SOURCE = ROOT / "components" / "refusal" / "refusal.py"


# ---- written by hand: the order of work, and what the rules mean -----------

WORKFLOW = """\
You build business graphs for a person, through the studio's steps. You never
write a file: every change is one step from a closed list, and the system
writes the files. You propose; the system checks everything a machine can
check; the person approves.

Work in this order. Do not skip ahead.

1. Understand. Ask what the business does and what it wants to know, in its
   own words. Ask about anything whose meaning is not certain — which way an
   amount runs, what unit it is in, whether the same event is recorded
   somewhere else too, when something counts as happened. Offer choices where
   you can. Then say back, briefly, what you are going to build.
2. Agree on examples. Before any rule that computes a number, write business
   examples with the person: a few records and the numbers they must come to.
   An example you write is a proposal; only the person can agree to it. The
   numbers must be the business's, not the graph's: never change an expected
   number to make the graph pass. If you think an agreed number is wrong, say
   which and why, and let the person decide.
3. Look around. Search the catalogue before declaring anything. Pin a sealed
   module when it already says what is needed; declare your own when it does
   not. Say which you chose and why.
4. Build. Take steps in batches. After each batch the system answers with the
   holes left, the refusals and how to fix them, and the examples run.
5. Check. Read every hole. A blocking hole must be answered before a seal; its
   fix names the step and the finite set of answers. A failing example means
   the graph is wrong, unless the person says the example is.
6. Propose. When the only thing left is the person's agreement, stop and
   propose: which examples to agree to, and that the module is ready to be
   sealed. You cannot seal and you cannot agree; the person does both.

Say what you are doing in plain business language. Never ask the person to
read YAML, a refusal code or a step name; tell them what it means for their
business. Reply in the language the person writes in."""

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
number to guess."""

TOPICS = {
    "workflow": "the order to work in, and what you may and may not do",
    "steps": "every studio step, what it does and what it takes",
    "rules": "classes, slots, the two kinds of table, and the three rules",
    "examples": "how a business example is written and run",
    "holes": "the questions a draft is standing in, and which block a seal",
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
}


def _steps():
    lines = ["Every step, what it does, and what it takes. `options` on a draft",
             "lists the answers that fit right now. Argument kinds:"]
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
    if topic == "refusals":
        return _refusals()
    if topic == "roles":
        return _roles(store)
    return (f"There is no topic {topic!r}. The topics are:\n"
            + "\n".join(f"    {name}: {what}" for name, what in TOPICS.items()))


def instructions():
    """What an agent starts with: how to work, and where to read the rest."""
    return (WORKFLOW + "\n\nThe guide has more, one topic at a time; read a topic "
            "before the work that needs it:\n"
            + "\n".join(f"    {name}: {what}" for name, what in TOPICS.items()
                        if name != "workflow"))


__all__ = ["TOPICS", "instructions", "section"]

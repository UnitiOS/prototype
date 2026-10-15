"""tools — what an agent can do, and nothing else.

Five tools, each a plain function over a `Bench`, each answering in text a
model reads cheaply. They are the studio's own readers and its one door, with
the actor fixed to `agent`:

    look       a draft as it stands: what it declares, the holes it is in, the
               examples and their numbers, whether it could be sealed
    options    the steps, or one step with the answers that fit right now
    do         a batch of steps, stopping at the first refusal, answered with
               what the draft is standing in afterwards
    catalogue  what the store holds: modules, roles, classes, slots
    guide      one topic of the guide

There is no tool that seals and none that agrees to an example. Those are the
person's, and the absence is the guarantee: an agent cannot do what it has no
tool for, however it is instructed.

Nothing here is tied to a model or a provider. `builder` hands these to an
agent framework; the same functions could be served over MCP.

The text is written for a reader who pays per word. It says what the draft is
and what to do next, and leaves out whatever the reader could ask for again.
"""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

from components.agent import guide as guide_read  # noqa: E402
from components.examples.examples import render as render_examples  # noqa: E402
from components.modules import catalogue as catalogue_read  # noqa: E402
from components.modules.roles import NOT_TAUGHT, taught  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from components.business import owner  # noqa: E402
from perform import connect  # noqa: E402

# Every step an agent takes is an agent's. Nothing the agent says can change it.
ACTOR = "agent"

# How many answers a list shows before it says how many more there are. Large
# enough that the right answer is almost always there; a longer list is a
# reason to narrow with `catalogue`, and the text says so.
SHOWN = 40

PARTS = ("draft", "around", "examples", "history")


@dataclass
class Bench:
    """Where an agent works: a module store, and a log to run examples in.

    `dsn` is the log the business examples run in, each in a scratch log of
    its own that is rolled back. Without one the examples are listed and not
    run, and nothing can be called sealable.
    """

    store: object
    dsn: str | None = None

    @classmethod
    def from_env(cls, store):
        return cls(store=store, dsn=os.environ.get("UNITI_DSN"))

    def business(self):
        """The business the log belongs to, whose applications the agent may
        see; None without a log or before the log says."""
        if self.dsn is None:
            return None
        try:
            with connect(self.dsn, connect_timeout=3) as conn:
                return owner(conn)
        except psycopg.OperationalError:
            return None

    def state(self, name):
        """The studio's one read of a draft, examples run when there is a log."""
        if self.dsn is None:
            return reading.state(self.store, name)
        try:
            conn = connect(self.dsn, connect_timeout=3)
        except psycopg.OperationalError:
            return reading.state(self.store, name)
        with conn:
            try:
                return reading.state(self.store, name, conn)
            finally:
                conn.rollback()


# ---- the tools ------------------------------------------------------------

def look(bench, module, part="draft"):
    """Read one module's draft. A sealed module has none: read it with
    `catalogue` and `module`.

    part: `draft` (default) — what it declares, every hole, the examples in
    brief, and whether it could be sealed; `around` — the classes of pinned
    modules it points at, the roles in sight and the enums; `examples` — every
    example with every number and the tables they produce; `history` — the
    steps taken so far, who took them.
    """
    if part not in PARTS:
        return f"There is no part {part!r}. Parts: {', '.join(PARTS)}."
    try:
        report = bench.state(module)
    except Refusal as exc:
        if _unheard_of(exc, module):
            return _NOT_YET.format(module=module)
        said = _refusal(exc.as_dict())
        if exc.code == "no_draft" and _sealed(bench.store, module):
            said += (f"\n{module} is sealed and has no draft: `catalogue` with "
                     f"module={module} reads what it declares.")
        return said
    if part == "around":
        return _around(report)
    if part == "examples":
        return _examples(report, tables=True)
    if part == "history":
        return report["taken"].strip() or "No step taken yet."
    return _draft(report)


# A module the store has never held is the usual start of a request, not a
# fault: the store's own refusal speaks to whoever configures it, of roots
# and environment variables, which the agent can do nothing about.
_NOT_YET = ("There is no module {module} yet. The step `start` (title, "
            "description) creates it and opens its first draft, once the person "
            "agreed to your plan; take it in the same `do` as the steps that follow.")


def _unheard_of(exc, module):
    return exc.code == "no_such_module" and module in exc.sentence()


def _sealed(store, module):
    try:
        return bool(store.versions(module))
    except Refusal:
        return False


def options(bench, module, op=""):
    """The steps there are, or — naming one, or several separated by commas —
    what each takes and the answers that fit this draft right now."""
    if not op:
        return "\n".join(f"{name}: {_first(spec['does'])}"
                         for name, spec in studio.OPERATIONS.items())
    wanted = [o.strip() for o in op.split(",") if o.strip()]
    unknown = [o for o in wanted if o not in studio.OPERATIONS]
    if unknown:
        return (f"There is no step {unknown[0]!r}. Steps: "
                + ", ".join(studio.OPERATIONS) + ".")
    try:
        offered = {s["op"]: s for s in reading.steps(
            bench.store, module, studio.open_draft(bench.store, module))}
    except Refusal:
        # No draft yet: the steps are still described, without answers to offer.
        offered = {}
    return "\n".join(_offered(o, offered.get(o)) for o in wanted)


def _offered(op, offered):
    spec = studio.OPERATIONS[op]
    if offered is None:
        offered = {"takes": [{"name": k, "kind": v, "required": True, "options": []}
                             for k, v in spec["takes"].items()]
                   + [{"name": k, "kind": v, "required": False, "options": []}
                      for k, v in spec["may"].items()]}
    lines = [f"{op}: {spec['does']}"]
    for takes in offered["takes"]:
        mark = "" if takes["required"] else ", optional"
        line = f"    {takes['name']} ({guide_read.KINDS.get(takes['kind'], takes['kind'])}{mark})"
        if takes.get("depends"):
            line += f", depends on {takes['depends']}"
        lines.append(line)
        if takes["options"]:
            lines.append(f"        one of: {_listed(takes['options'])}")
    return "\n".join(lines)


def do(bench, module, steps):
    """Take steps on one module's draft, in order, as the agent.

    Each step is `{"op": ..., "args": [{"name": ..., "value": ...}, ...]}`.
    The first refusal stops the batch: the steps before it are taken, the rest
    are not, and the refusal says how to fix it. Afterwards the draft is read
    again and what it is standing in comes back — the holes, the examples, and
    whether it could be sealed.
    """
    lines = []
    for i, step in enumerate(steps, start=1):
        op = str(step.get("op") or "")
        args = {str(a.get("name")): str(a.get("value") if a.get("value") is not None else "")
                for a in (step.get("args") or [])}
        said = " ".join(f"{k}={v}" for k, v in args.items())
        try:
            studio.apply(bench.store, module, op, args, actor=ACTOR)
        except Refusal as exc:
            lines.append(f"{i}. refused: {op} {said}".rstrip())
            lines.append(_indent(_refusal(exc.as_dict()), 3))
            if i + 1 == len(steps):
                lines.append(f"Step {i + 1} was not taken.")
            elif i < len(steps):
                lines.append(f"Steps {i + 1} to {len(steps)} were not taken.")
            break
        lines.append(f"{i}. done: {op} {said}".rstrip())
    if not steps:
        lines.append("No step given.")
    if not studio.path(bench.store, module).is_file():
        # Discarded, or never started: there is nothing to read back.
        return "\n".join(lines)
    try:
        report = bench.state(module)
    except Refusal as exc:
        return "\n".join(lines + ["", _refusal(exc.as_dict())])
    return "\n".join(lines + ["", standing(report)])


def catalogue(bench, text="", kind="", fills="", module=""):
    """Search what the store holds: modules, roles, classes and slots, at
    their latest sealed versions. Every filter is optional. `text` matches a
    name, title, description or predicate; `kind` is module, role, class or
    slot; `fills` is a role or binding; `module` is the module declaring it,
    or several separated by commas, read in one call."""
    if kind and kind not in catalogue_read.KINDS:
        return f"kind is one of {', '.join(catalogue_read.KINDS)}."
    everything = catalogue_read.catalogue(bench.store, business=bench.business())
    # A pin names a version; the catalogue holds the latest, the one meant.
    names = [re.sub(r"@v\d+$", "", m.strip()) for m in module.split(",") if m.strip()]
    entries = []
    for name in names or [None]:
        found = catalogue_read.find(everything, text=text or None, kind=kind or None,
                                    fills=fills or None, module=name)
        entries += found["entries"]
    if not entries:
        return ("Nothing matches. The store holds modules "
                + ", ".join(found["modules"]) + "; roles "
                + ", ".join(taught(found["roles"])) + ".")
    shown = SHOWN * max(1, len(names))
    lines = [f"{len(entries)} found."]
    for entry in entries[:shown]:
        lines.append(_entry(entry))
    if len(entries) > shown:
        lines.append(f"And {len(entries) - shown} more: narrow the search.")
    return "\n".join(lines)


def guide(bench, topic="workflow"):
    """Read one topic of the guide: workflow, steps, rules, examples, holes,
    refusals or roles."""
    return guide_read.section(topic, bench.store)


# ---- how things read ------------------------------------------------------

def _first(text):
    return text.split(". ")[0].split(": ")[0]


def _listed(items):
    items = [str(i) for i in items]
    shown = ", ".join(items[:SHOWN])
    if len(items) > SHOWN:
        shown += f", and {len(items) - SHOWN} more (narrow with catalogue)"
    return shown


def _indent(text, by):
    return "\n".join(" " * by + line for line in text.splitlines())


def _refusal(refusal):
    lines = [f"[{refusal['code']}] {refusal['sentence']}"]
    for repair in refusal["repairs"]:
        lines.append(f"  fix: {repair['do']}")
        if repair.get("where"):
            lines.append(f"       in {repair['where']}")
        if repair["options"]:
            lines.append(f"       one of: {_listed(repair['options'])}")
    return "\n".join(lines)


def _rule(rule):
    spec = rule["spec"]
    if rule["kind"] == "expression":
        return f"expression {spec}"
    if rule["kind"] == "parameter":
        return f"parameter of {spec.get('of')}, slot {spec.get('slot')}"
    if isinstance(spec.get("sources"), list):
        return " + ".join(_rule({"kind": "aggregate", "spec": source})
                          for source in spec["sources"])
    by = ", ".join(f"{k}={v}" for k, v in (spec.get("by") or {}).items())
    out = f"aggregate over {spec.get('over')}, sum {spec.get('sum')}, by {by}"
    if spec.get("where"):
        out += ", where " + ", ".join(
            f"{k}={(v or {}).get('is_a')}" if "is_a" in (v or {})
            else f"{k} " + " ".join(f"{w} {x}" for w, x in (v or {}).items())
            for k, v in spec["where"].items())
    if spec.get("convert"):
        convert = spec["convert"]
        on = ", ".join(f"{k}={v}" for k, v in (convert.get("on") or {}).items())
        out += (f", convert using {convert.get('using')} on {on} "
                f"factor {convert.get('factor')}")
    return out


def _labelled(name, labels):
    """A name with the person's words for it: `IngredientStock ("Stok bahan" id)`."""
    said = ", ".join(f'"{text}" {language}' for language, text in (labels or {}).items())
    return f"{name} ({said})" if said else name


def _slot_line(slot):
    marks = [slot["range"] or "string"]
    if slot.get("unit"):
        marks.append(f"unit {slot['unit']}")
    if slot.get("direction"):
        marks.append(slot["direction"])
    if slot.get("time_meaning"):
        marks.append(slot["time_meaning"])
    if slot["identifier"]:
        marks.append("identifier")
    if slot["designates_type"]:
        marks.append("says which class")
    if slot["required"]:
        marks.append("required")
    if slot["multivalued"]:
        marks.append("many values")
    if slot["binds"]:
        marks.append(f"fills binding {slot['binds']}")
    line = f"{_labelled(slot['name'], slot.get('labels'))}: {', '.join(marks)}"
    if slot["rule"]:
        line += f" = {_rule(slot['rule'])}"
    return line


def _header(report):
    pins = ", ".join(f"{p['name']}@{p['version']}" for p in report["pins"]) or "nothing"
    made = f"revising {report['revises']}" if report["revises"] else "a new module"
    return (f"{report['name']} — {report['title'] or 'untitled'}: draft of "
            f"{report['becomes']}, {made}; pins {pins}")


def _draft(report):
    lines = [_header(report)]
    if report["description"]:
        lines.append(f"  {' '.join(str(report['description']).split())}")
    shapes = {t["class"]: t for t in report["tables"]}
    slots = {s["name"]: s for s in report["slots"]}
    lines.append("")
    lines.append("Its classes:" if report["classes"] else "It declares no class yet.")
    for c in report["classes"]:
        table = shapes.get(c["name"])
        kind = (f"{table['shape']} table" if table
                else "no table: nothing can be stated to be one")
        fills = f", fills {', '.join(c['fills'])}" if c["fills"] else ""
        above = f", a kind of {c['is_a']}" if c["is_a"] else ""
        lines.append(f"  {_labelled(c['name'], c.get('labels'))} ({kind}{fills}{above})")
        for slot_name in c["slots"]:
            slot = slots.get(slot_name)
            lines.append(f"    {_slot_line(slot)}" if slot
                         else f"    {slot_name}: a slot of a pinned module")
        for slot_name, usage in c["usage"].items():
            lines.append(f"    on this class only: {slot_name} "
                         + ", ".join(f"{k}={v}" for k, v in usage.items()))
    loose = [s for s in report["slots"] if not s["on"]]
    for slot in loose:
        lines.append(f"  on no class: {_slot_line(slot)}")
    own_enums = [e for e in report["enums"] if e["module"] is None]
    for enum in own_enums:
        values = [_labelled(v, enum.get("value_labels", {}).get(v)) for v in enum["values"]]
        lines.append(f"  enum {_labelled(enum['name'], enum.get('labels'))}: "
                     f"{', '.join(values)}")
    lines.append("")
    lines.append(standing(report))
    return "\n".join(lines)


def standing(report):
    """What a draft is standing in: the holes, the examples, and the verdict."""
    blocking = [h for h in report["holes"] if h["blocking"]]
    open_ = [h for h in report["holes"] if not h["blocking"]]
    lines = [f"Holes: {len(blocking)} blocking, {len(open_)} open."]
    for hole in blocking:
        lines.append(f"  ! {hole['question']}")
        lines += _answer(hole)
    for hole in open_:
        lines.append(f"  ? {hole['question']}")
        lines += _answer(hole)
    lines.append("")
    lines.append(_examples(report, tables=False))
    lines.append("")
    if report.get("empty"):
        # True of any new draft, and no reason to stop: nothing asked is built.
        lines.append("It declares nothing yet; build what the person asked for.")
    elif report["sealable"]:
        lines.append("Nothing blocks a seal. Propose it once it does what the person "
                     "asked; you cannot seal.")
    elif not blocking and report["examples"] and not report["examples_run"]:
        lines.append("Not sealable: the examples could not be run, there is no log.")
    else:
        agreeing = all(h["kind"] == "example_not_agreed" for h in blocking)
        lines.append("Not sealable yet: only the person's agreement to the examples "
                     "is missing. Propose them." if blocking and agreeing
                     else "Not sealable yet.")
    waiting = [e for e in report["examples"] if e.get("waits")]
    if any(not e["agreed"] for e in waiting):
        lines.append("An example waiting for its rules is put to the person as it is; "
                     "the rules come once they agree.")
    if any(e["agreed"] for e in waiting):
        lines.append("Agreed, and waiting for their rules: "
                     + ", ".join(e["name"] for e in waiting if e["agreed"]) + ".")
    return "\n".join(lines)


def _answer(hole):
    """The step that answers a hole, or the refusal's own fixes when there is none."""
    step = hole["step"]
    if step:
        given = " ".join(f"{k}={v}" for k, v in step["args"].items())
        line = f"      step: {step['op']} {given}".rstrip()
        if step["choose"]:
            line += f", choosing {step['choose']}"
        out = [line]
        if step["options"]:
            out.append(f"        one of: {_listed(step['options'])}")
        return out
    if hole["refusal"]:
        return [_indent("\n".join(_refusal(hole["refusal"]).splitlines()[1:]), 4)]
    return []


def _examples(report, *, tables):
    if not report["examples"]:
        return "Examples: none yet."
    lines = ["Examples:"]
    if not report["examples_run"]:
        lines.append("  (not run: there is no log to run them in)")
    lines += [f"  {line}" for line in render_examples(report["examples"], tables=tables)]
    return "\n".join(lines)


def _around(report):
    lines = [_header(report), "", "Classes of pinned modules this draft points at:"]
    for c in report["borrowed"]:
        pin = f"{c['module']['name']}@{c['module']['version']}" if c["module"] else ""
        fills = f", fills {', '.join(c['fills'])}" if c["fills"] else ""
        lines.append(f"  {c['name']} ({pin}{fills})")
        for slot in c["slots"]:
            mark = ", identifier" if slot["identifier"] else ""
            lines.append(f"    {slot['name']}: {slot['range'] or 'string'}{mark}")
    if not report["borrowed"]:
        lines.append("  none yet")
    lines += ["", "Roles in sight:"]
    for role in report["roles"]:
        bindings = ", ".join(b["name"] for b in role["bindings"]) or "no binding"
        filled = ", ".join(f["class"] for f in role["filled_by"])
        lines.append(f"  {role['name']}: binds {bindings}"
                     + (f"; filled here by {filled}" if filled else ""))
    enums = [e for e in report["enums"]]
    if enums:
        lines += ["", "Enums in sight:"]
        lines += [f"  {e['name']}: {', '.join(e['values'])}" for e in enums]
    lines.append("")
    lines.append(f"It sees {report['sees']['classes']} classes and "
                 f"{report['sees']['slots']} slots in all; `options` lists them "
                 f"per step, `catalogue` describes them.")
    return "\n".join(lines)


# How the catalogue names each kind of module to the agent (guide: kinds).
OF_KIND = {"core": "core", "library": "standard library", "module": "community module",
           "application": "this business's application"}


def _entry(entry):
    pin = f"{entry['module']['name']}@{entry['module']['version']}"
    about = " ".join(str(entry.get("description") or "").split())
    if len(about) > 160:
        about = about[:157] + "..."
    if entry["kind"] == "module":
        pins = ", ".join(f"{p['name']}@{p['version']}" for p in entry["pins"]) or "nothing"
        head = (f"module {_labelled(pin, entry.get('labels'))} "
                f"({OF_KIND.get(entry.get('of_kind'), entry.get('of_kind'))}) — "
                f"{entry['title']}; pins {pins}; declares "
                f"{', '.join(entry['declares']['classes']) or 'no class'}")
    elif entry["kind"] == "role":
        bindings = ", ".join(b["name"] for b in entry["bindings"]) or "nothing"
        filled = ", ".join(f"{f['class']} ({f['module']['name']})"
                           for f in entry["filled_by"]) or "nothing"
        head = f"role {entry['name']} ({pin}): binds {bindings}; filled by {filled}"
        if entry["name"] in NOT_TAUGHT:
            # Found, so what was sealed under it still reads; not taught.
            head = (f"role {entry['name']} ({pin}), kept for the modules sealed under "
                    f"it: fill no new class with it; binds {bindings}; filled by {filled}")
            about = ""
    elif entry["kind"] == "class":
        fills = f", fills {', '.join(entry['fills'])}" if entry["fills"] else ""
        statable = "" if entry["statable"] else ", cannot be stated"
        head = (f"class {_labelled(entry['name'], entry.get('labels'))} "
                f"({pin}{fills}{statable}): slots "
                f"{', '.join(entry['slots']) or 'none'}")
        if entry["statable"] and entry.get("required"):
            head += f"; a new one must be given {', '.join(entry['required'])}"
    else:
        fills = f", fills {', '.join(entry['fills'])}" if entry["fills"] else ""
        meant = "".join(f", {entry[k]}" if k != "unit" else f", unit {entry[k]}"
                        for k in ("unit", "direction", "time_meaning") if entry.get(k))
        head = (f"slot {_labelled(entry['name'], entry.get('labels'))} ({pin}): "
                f"{entry['range'] or 'string'}{meant}{fills}; on "
                f"{', '.join(entry['on']) or 'no class'}")
    return f"  {head}" + (f"\n      {about}" if about else "")


TOOLS = (look, options, do, catalogue, guide)

__all__ = ["ACTOR", "Bench", "PARTS", "TOOLS", "catalogue", "do", "guide", "look",
           "options", "standing"]

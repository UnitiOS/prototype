"""seal — a draft becomes a version.

One seal is one intent. The draft is validated as LinkML, the next version
number is assigned, `valid_from` and `sealed_at` are stamped into the schema's
own annotations, and everything the session stated reaches the kernel in a
single `perform()` call. There is no transaction across a file and Postgres, so
the order is fixed by the 2026-08-26 decision: the version file first, then one
write. A failed write leaves an orphan version file, which is harmless; a loop
would leave half a session permanently in an append-only log, which is not.

What is where:

    the map    classes, slots and their `slot_uri` — the frame for reading the
               world. Written to `business/vN.yaml`.
    the log    what was said about the world. Written to the kernel and
               **stripped** from the sealed version: a fact kept in the map is
               a fact living outside the log.

A fact is stated in the draft's `annotations.facts`, three keys and an
optional fourth:

    annotations:
      valid_from: '2026-01-01T00:00:00Z'
      facts:
        - subject: uniti:thing_a
          predicate: uniti:thing_label
          value: Thing A
          confidence: low

`confidence` is how sure the business is of this one fact, and it is the
kernel's own vocabulary — `high`, `medium`, `low`. It has no default: a fact
that says nothing about its own confidence records NULL, because a business
that measured some things and estimated others said two things, not one.

`predicate` is a `slot_uri` the draft declares — that is the whole of the join
between map and log. `subject` is a URI too, because the kernel's `entity` has
no name column: identity is an assertion like everything else. Every URI is
registered by one assertion under the well-known predicate `uniti:uri`, which
registers itself — one row whose subject, predicate and value all name the same
thing — so a single query finds every entity the map has ever named, and a
second seal reuses them instead of minting twins.

Which column a `value` lands in is read from the map, not stated in the fact:
if the predicate's slot declares a **class** as its range the value names
another entity and is written as `value_ref`, and a URI first seen there is
registered exactly as a subject is. A type range, an enum, or no range at all
stays a `value_literal`. An inventory is mostly relationships, so this is what
puts edges in the graph rather than strings that only look like URIs.

The draft also names its transcript, relative to its own directory:

    annotations:
      transcript: draft.txt

That file is evidence and is required. It lands beside the version as `vN.txt`
and the sealed annotation is rewritten to match, so a sealed version and the
conversation that produced it are found together.

A draft may carry business examples beside it, `<draft>.examples.yaml`: a few
records and the numbers they must add up to (components/examples). Every one
is run before anything is written, and a number that comes out different
refuses the seal. They land beside the version as `vN.examples.yaml`. A draft
that computes a column must carry them: every computed column of its own
classes needs a number in some example, and every example needs a person to
have agreed to it.

One sealed version can be put into a second log without being sealed again.
`register()` reads a version that already exists, writes its `slot_uri` rows
under `uniti:uri`, and writes no file — the door into an empty log for a map
that has one. It states no facts: a sealed version carries none.

Run: .venv/Scripts/python.exe components/seal/seal.py business/draft.yaml --actor fareza
     .venv/Scripts/python.exe components/seal/seal.py business/<name>/v2.yaml           --register --actor <actor>
"""

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from linkml_runtime import SchemaView

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components"))

from components.refusal import Refusal, Repair  # noqa: E402
from ontology.resolve import load_versions  # noqa: E402
from perform import connect, perform  # noqa: E402

# The predicate every entity's URI is recorded under. It registers itself.
URI_PREDICATE = "uniti:uri"

# A fact says who, what, and what it is. Anything else is a typo — and an
# unknown key here would also be read as version metadata by the ontology
# resolver, which scans the annotations block shallowly. That invariant is why
# the set stays closed: a fact key may never collide with a version metadata
# key, and `confidence` does not.
FACT_KEYS = ("subject", "predicate", "value")

# How sure the business is of this one fact. Optional, and never defaulted —
# absent records NULL, because a default claims more than anyone said.
FACT_OPTIONAL = ("confidence",)

# The kernel's confidence_levels constraint, checked here so a typo is refused
# with the fact's number rather than as an integrity error mid-transaction.
CONFIDENCE_LEVELS = ("high", "medium", "low")

# The four keys seal stamps itself. Whatever a draft says under them is
# replaced, so `_sealed_document` carries neither them nor `facts` across.
STAMPED = ("valid_from", "sealed_at", "supersedes", "transcript")

# Minting is the tool's act; the facts are the interviewee's.
MINT_SOURCE = "system_derived"
FACT_SOURCE = "human_stated"

_VERSION_NAME = re.compile(r"^v(\d+)$")

_REGISTRY_SQL = """
SELECT value_literal, subject_id
FROM assertion
WHERE predicate_id = (
        SELECT subject_id FROM assertion
        WHERE subject_id = predicate_id AND value_literal = %s
        ORDER BY seq LIMIT 1)
  AND value_literal IS NOT NULL
"""


class DraftError(Refusal):
    """The draft cannot be sealed. Nothing has been written."""

    gate = "seal"


def _utc(value):
    """An ISO 8601 string or a datetime, as one aware datetime."""
    moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _declared_in(view, element):
    """The schema of the closure that declares this class or slot.

    LinkML merges every module's prefixes into one table, and when two modules
    map one prefix to two namespaces the last one read wins, silently. So a
    CURIE is only ever expanded against the prefixes of the module that wrote
    it, which is the one `from_schema` names.
    """
    origin = getattr(element, "from_schema", None)
    if origin:
        for schema in view.schema_map.values():
            if schema.id == origin:
                return schema
    return view.schema


def _expand(view, schema, curie):
    """A CURIE as the full URI its own module means by it."""
    text = str(curie)
    if "://" in text:
        return text
    prefix, sep, local = text.partition(":")
    held = (schema.prefixes or {}).get(prefix) if sep else None
    if held is not None:
        return str(held.prefix_reference) + local
    return str(view.expand_curie(text))


def predicate(view, slot):
    """The full URI a slot's facts are recorded under, or None without one.

    This, and never the `slot_uri` as written, is a predicate's identity in the
    log. A CURIE is shorthand for one module: two authors who both chose the
    prefix `stock:` meant two namespaces, and registering `stock:qty` as
    written made their two predicates one.
    """
    if not slot.slot_uri:
        return None
    return _expand(view, _declared_in(view, slot), slot.slot_uri)


def written_uri(document, curie):
    """A CURIE in a module document, expanded by that document's own prefixes.

    For readers holding a module's YAML rather than a view of its closure. The
    same answer `predicate` gives, because the prefixes are the same module's.
    """
    text = str(curie)
    if "://" in text:
        return text
    prefix, sep, local = text.partition(":")
    held = (document.get("prefixes") or {}).get(prefix) if sep else None
    if isinstance(held, dict):
        held = held.get("prefix_reference")
    return f"{held}{local}" if held else text


def class_uri(view, class_name):
    """The full URI an entity's class fact names, for one class.

    A bare class name says nothing about whose class it is: two modules may
    each declare an `Item`, and a class fact reading `Item` could be either.
    The class's own `class_uri` when it declares one, otherwise its name in
    the namespace of the module that declares it.
    """
    cls = view.get_class(class_name)
    schema = _declared_in(view, cls)
    if cls.class_uri:
        return _expand(view, schema, cls.class_uri)
    prefix = schema.default_prefix
    if prefix and prefix in (schema.prefixes or {}):
        return _expand(view, schema, f"{prefix}:{class_name}")
    return f"{str(schema.id).rstrip('/#')}/{class_name}"


def _validate(text, name, store=None):
    """Load through SchemaView, which is what "valid LinkML" means here.

    SchemaView raises on malformed YAML, on a missing `id` or `name`, and on
    any key the metamodel does not know. It does not resolve ranges or class
    slot references — that is not parsing, and the generator will meet those.

    With a module `store`, imports are resolved through it and checked now:
    every module import must pin a version the store holds sealed.
    """
    try:
        return store.view(text) if store is not None else SchemaView(text)
    except Refusal:
        # The store refusing an import is already a refusal with its own
        # repairs. Wrapping it would bury them under a parse error.
        raise
    except Exception as exc:
        raise DraftError(
            "not_linkml",
            where=name,
            expected="a schema LinkML can load",
            got=f"{type(exc).__name__}: {exc}",
            repairs=[Repair("fix what LinkML names above; it reads the file "
                            "before anything here does", where=name)],
        ) from exc


def uri_refusals(view, name):
    """Every slot with no `slot_uri`, as the refusal each one would raise.

    A generator, because a gate and a page want different things from the same
    rule: `seal` raises the first and stops, and a draft being edited wants all
    of them at once. The rule is read here once, so the two cannot drift.
    """
    for slot_name in view.schema.slots:
        slot = view.induced_slot(slot_name)
        if slot.abstract or slot.slot_uri:
            # An abstract slot is a binding, not a predicate. It names a hole
            # that whichever class fills the role fills with a slot of its
            # own, so nothing is ever stated under it and it needs no identity
            # in the kernel. This is what keeps roles out of the log entirely:
            # `slot_uri` is not inherited, so a fact is always recorded under
            # the concrete predicate, and changing a role invalidates nothing.
            continue
        yield DraftError(
            "slot_without_uri",
            where=f"{name}: {slot_name}",
            expected="a `slot_uri`, which is a predicate's identity in the kernel",
            got="none",
            repairs=[Repair(
                f"declare `slot_uri: <prefix>:{slot_name}`. It is not derived "
                f"from the name: a rename would then orphan every fact "
                f"recorded before it",
                where=name,
            )],
        )


def range_refusals(view, draft, name):
    """Every slot the draft declares whose range names nothing in sight.

    LinkML loads a schema without resolving ranges, so a slot left ranging
    over a class that was removed or renamed, or never pinned, reads as text
    everywhere downstream: its values land as strings nothing can follow.
    A generator, for the reason `uri_refusals` is one.
    """
    known = ({str(n) for n in view.all_types()} | {str(n) for n in view.all_classes()}
             | {str(n) for n in view.all_enums()})
    for slot_name, body in (draft.get("slots") or {}).items():
        wanted = (body or {}).get("range")
        if wanted is None or str(wanted) in known:
            continue
        yield DraftError(
            "range_unknown",
            where=f"{name}: {slot_name}",
            expected="a range that is a type, a class or an enum in sight",
            got=f"{wanted!r}",
            repairs=[Repair(
                f"range {slot_name} over one of these, or pin the module that "
                f"declares {wanted}",
                where=name,
                options=sorted(known)),
            ],
        )


def _slot_ranges(view, name):
    """Every `slot_uri` the draft declares, and whether its range is a class.

    In declaration order, and `True` where the value is another entity.

    An explicit `slot_uri` is not optional. A slot without one has no identity
    a fact can point at, and a URI derived from the schema's own naming would
    change with every rename and orphan every fact recorded before it.

    The range decides which column a fact lands in: a class range means the
    value names an entity, so it is a `value_ref`; a type range, an enum, or no
    range at all is a `value_literal`. Nothing new is written into the draft to
    say so — the map already declares it, and a second key would be a second
    place for the two writers to disagree.

    Slots are read through `induced_slot`, which applies `default_range` and
    inheritance: a schema whose `default_range` is a class would otherwise have
    every unranged slot read as a literal.

    Two slots sharing one `slot_uri` is how a rename keeps its identity, and
    the first of them decides the range. Two that shared a URI and disagreed
    about it would be one predicate meaning two things — unguarded, and a line
    in OPEN.md rather than a refusal invented here.
    """
    for refusal in uri_refusals(view, name):
        raise refusal
    classes = set(view.all_classes())
    ranges = {}
    for slot_name in view.schema.slots:
        slot = view.induced_slot(slot_name)
        if not slot.abstract:
            ranges.setdefault(predicate(view, slot), slot.range in classes)
    return ranges


def _written(view):
    """Each predicate as the draft writes it, and the full URI it stands for.

    A fact in a draft names its predicate the way the draft's own slots do, as
    a CURIE; the log holds the full URI. Either spelling is accepted.
    """
    out = {}
    for slot_name in view.schema.slots:
        slot = view.induced_slot(slot_name)
        if not slot.abstract and slot.slot_uri:
            full = predicate(view, slot)
            out[str(slot.slot_uri)] = full
            out[full] = full
    return out


def _class_facts(view):
    """Full predicate -> {class name: class URI}, for every slot naming a class.

    A fact under a `designates_type` slot says which class a subject is, and
    the draft writes the class by name. The log records the class's full URI,
    so the same name in two modules is two classes there too.
    """
    names = {str(c): class_uri(view, c) for c in view.all_classes()}
    return {predicate(view, view.induced_slot(s)): names
            for s in view.all_slots()
            if view.induced_slot(s).designates_type
            and view.induced_slot(s).slot_uri}


def fillers(view, class_name, binding):
    """The class's own slots that fill one binding: those descending from it.

    One place, because three components need the same answer. `seal` checks
    that there is exactly one, the compiler resolves a rule written against the
    binding to whichever slot that is, and a reader is shown what filled what.
    """
    below = set(view.slot_descendants(binding)) - {binding}
    return sorted(
        str(slot.name)
        for slot in view.class_induced_slots(class_name)
        if str(slot.name) in below and not slot.abstract
    )


def candidates(view, class_name, binding):
    """The class's own slots that could fill one binding, judged by range.

    The hole, and the shapes that fit it. A binding ranging over a type is
    filled by a slot of that type; one ranging over a class by a slot ranging
    over that class or anything below it.

    This does not guess which slot is right — that is the one thing only the
    author knows. It is the finite set they are choosing from, which is what
    turns "name a slot" into a list rather than a blank page.
    """
    wanted = str(binding.range) if binding.range else None
    below = ({str(n) for n in view.class_descendants(wanted)}
             if wanted in view.all_classes() else set())
    out = []
    for slot in view.class_induced_slots(class_name):
        if slot.abstract:
            continue
        found = str(slot.range) if slot.range else None
        if wanted is None or found == wanted or found in below:
            out.append(str(slot.name))
    return sorted(out)


def _roles(view, draft, name):
    """Raise the first unmet claim. The rule itself is in `role_refusals`."""
    for refusal in role_refusals(view, draft, name):
        raise refusal


def role_refusals(view, draft, name):
    """Every class this draft declares fills the roles it claims, exactly once.

    A role is a class core declares `abstract`, carrying `abstract` slots that
    are bindings rather than predicates. Mixing one in is a claim, and this is
    where the claim is checked, because `seal` is the only gate: a module whose
    class says it is a Flow but names no quantity would compile to a column of
    nulls somewhere else, far from the mistake.

    Two refusals, and they are not symmetrical:

        nothing fills a required binding   refused. The role was claimed and
                                           not honoured.
        two slots fill one binding         refused. Which of `qty_gross` and
                                           `qty_net` is *the* amount is a
                                           question only the author can answer,
                                           and guessing it would be a wrong
                                           number that looks right.

    A binding that is not required may go unfilled: that is what an optional
    part of a role means.

    Only the draft's own classes are checked. An imported class was checked
    when it was sealed, and an error about somebody else's module here would
    name a file the reader cannot change.

    A generator, for the same reason `uri_refusals` is one: the gate raises the
    first of these and a draft being edited shows all of them, off one rule.
    """
    for class_name in (draft.get("classes") or {}):
        if class_name not in view.all_classes():
            continue
        if view.get_class(class_name).abstract:
            continue
        for slot in view.class_induced_slots(class_name):
            if not slot.abstract:
                continue
            binding = str(slot.name)
            filled = fillers(view, class_name, binding)
            if len(filled) > 1:
                yield DraftError(
                    "binding_ambiguous",
                    where=f"{class_name}.{binding}",
                    expected=f"one slot filling '{binding}'",
                    got=f"{len(filled)} — {', '.join(filled)}",
                    repairs=[Repair(
                        f"keep `is_a: {binding}` on the one that is the "
                        f"{binding}, and take it off the rest. Which one that "
                        f"is cannot be guessed, and guessing it would be a "
                        f"wrong number that looks right",
                        where=name,
                        options=filled,
                    )],
                )
            if not filled and slot.required:
                roles = ", ".join(str(r) for r in (view.get_class(class_name).mixins or [])) \
                    or "a role"
                yield DraftError(
                    "binding_unfilled",
                    where=f"{class_name}.{binding}",
                    expected=f"one slot with `is_a: {binding}`, which mixing in "
                             f"{roles} obliges",
                    got="none",
                    repairs=[Repair(
                        f"put `is_a: {binding}` on the slot of {class_name} that "
                        f"is its {binding}"
                        + (f" — the ones ranging over {slot.range}"
                           if slot.range else ""),
                        where=name,
                        options=candidates(view, class_name, slot),
                    )],
                )


def _compiles(view, draft_path):
    """Every table the draft can fill compiles, or the compiler's refusal.

    The same reading `check` makes and Studio shows as a blocking hole, stopping
    at the first as a gate does. Without it a module whose rule the compiler
    refuses was sealed, listed in the catalogue, and could never be computed.
    """
    # Imported here: the compiler reads this module's URI_PREDICATE.
    from components.modules.check import compiled
    map_ = {"path": draft_path, "view": view, "version": None,
            "label": draft_path.name}
    for _, _, refusal in compiled(map_):
        if refusal is not None:
            raise refusal


def _examples_hold(conn, view, draft, draft_path):
    """Every business example beside the draft is agreed, every column the
    draft computes is checked by one, and each comes out as it says.

    The contract the person agreed to, run the way the studio runs it on every
    change: each example in a scratch log of its own, rolled back, so nothing
    it states reaches this log. The first refusal stops the seal, as every
    gate here does. Returns the examples file, or None when there is none.
    """
    # Imported here: the examples read the compiler, which reads this module.
    from components.examples.examples import (
        contract_refusals, load, path_for, refusals, run,
    )
    held = path_for(draft_path)
    examples = load(held)
    map_ = {"path": draft_path, "view": view, "version": None,
            "label": draft_path.name}
    for refusal in contract_refusals(map_, draft, examples):
        raise refusal
    if not examples:
        return None
    for refusal in refusals(run(conn, map_, examples)):
        raise refusal
    return held


def _standard_held(view, draft, draft_path):
    """The draft is written down the way every module is: the first break of
    the recording standard, as the studio shows them all."""
    from components.examples.examples import load, path_for
    from components.standard import refusals

    def range_of(slot_name):
        try:
            return view.induced_slot(slot_name).range
        except Exception:  # noqa: BLE001 - a slot LinkML cannot induce has none
            return None

    for refusal in refusals(draft, load(path_for(draft_path)), range_of):
        raise refusal


def _one_version_per_module(store, draft, name):
    """No module reachable from this draft appears at two versions.

    Pins are exact, so two of them can disagree: an application pinning
    `@uniti/core@v2` while a module under it pins `@v1` would put two `Flow`
    classes in one closure, of the same name and different identity, and
    whichever LinkML merged last would win silently.

    Refusing is the narrow reading and it is the right one for a foundation: it
    means the ecosystem moves together on core, which is exactly the property
    core is for — and one more reason for core to stay small.
    """
    seen = {}
    for pin in store.imports(draft):
        for pinned_name, pinned_version in store.closure(*pin):
            held = seen.setdefault(pinned_name, (pinned_version, pin))
            if held[0] != pinned_version:
                raise DraftError(
                    "two_versions_of_a_module",
                    where=name,
                    expected=f"one version of {pinned_name} in the whole closure",
                    got=f"{held[0]} through {held[1][0]}@{held[1][1]}, and "
                        f"{pinned_version} through {pin[0]}@{pin[1]}",
                    repairs=[Repair(
                        f"move one of the two onto the other's version of "
                        f"{pinned_name} and seal it, then pin that",
                        options=[f"{held[1][0]}@{held[1][1]}", f"{pin[0]}@{pin[1]}"],
                    )],
                )


_KINDS = (("classes", "class"), ("slots", "slot"), ("enums", "enum"))


def name_clashes(store, draft, name):
    """Every class, slot or enum name two modules in one closure both declare.

    LinkML puts a closure's names in one space and merges a second declaration
    over the first without a word: the `Warehouse` one module declared and the
    `Warehouse` another declared become whichever was read last, and every rule
    naming it reads the wrong one. Nothing downstream can tell. So it is
    refused here, where both declarations are in sight.

    The draft's own names are in the closure too. A clash between the draft
    and a pin is answered by renaming in the draft; one between two pins by
    not pinning both as they are.

    A generator, for the reason `uri_refusals` is one.
    """
    owners = {}

    def declare(owner, document):
        for key, kind in _KINDS:
            for term in (document.get(key) or {}):
                held = owners.setdefault((kind, str(term)), [])
                # One module at two versions is `two_versions_of_a_module`'s
                # to refuse; counting it here would say it once per name.
                if not any(o == owner or (o and owner and o[0] == owner[0])
                           for o in held):
                    held.append(owner)

    declare(None, draft)
    for pin in store.imports(draft):
        for dep in store.closure(*pin):
            declare(dep, store.document(*dep))

    pins = [f"{n}@{v}" for n, v in store.imports(draft)]
    for (kind, term), held in owners.items():
        if len(held) < 2:
            continue
        said = ["this draft" if o is None else f"{o[0]}@{o[1]}" for o in held]
        if None in held:
            repairs = [Repair(f"rename the {kind} this draft declares; the "
                              f"module you pin keeps its name",
                              where=name,
                              options=[f"rename_{kind}"] if kind != "enum" else [])]
        else:
            repairs = [Repair(f"two modules you pin both declare the {kind} "
                              f"{term}, so they cannot be read together as they "
                              f"are. Drop one pin, or seal a version of one that "
                              f"renames it and pin that",
                              where=name, options=pins)]
        yield DraftError(
            "name_clash",
            where=f"{name}: {kind} {term}",
            expected=f"one module in the closure declaring the {kind} {term}",
            got=f"{len(held)}: {', '.join(said)}",
            repairs=repairs,
        )


def _no_clash(store, draft, name):
    """Raise the first clash. The rule itself is in `name_clashes`."""
    for refusal in name_clashes(store, draft, name):
        raise refusal


def kind_refusals(store, draft, name):
    """Every class this draft makes a kind of a class another module owns.

    A class may be a kind of a role — an abstract class, which nobody records
    into and which exists to be filled — or of a class of its own module.
    Never of another module's class: that is its owner's to grow. A rental
    module whose `RentalItem` is a kind of the library's `Item` splits one
    tent into as many kinds as there are modules that deal with tents, and a
    tent that is both rented and sold can only be one of them. So a module
    points at another module's class with a slot instead, and the thing stays
    one thing (DESIGN_NOTES.md §15.4).

    A generator, for the reason `name_clashes` is one.
    """
    own = draft.get("classes") or {}
    theirs = {}
    for pin in store.imports(draft):
        for dep in store.closure(*pin):
            for term, body in (store.document(*dep).get("classes") or {}).items():
                theirs.setdefault(str(term), (dep, body or {}))
    for term, body in own.items():
        body = body or {}
        for above in [body.get("is_a"), *(body.get("mixins") or [])]:
            if not above or str(above) in own or str(above) not in theirs:
                continue
            (module, version), held = theirs[str(above)]
            if held.get("abstract"):
                continue
            yield DraftError(
                "kind_of_foreign_class",
                where=f"{name}: class {term}",
                expected="a kind of a role, or of a class this module declares",
                got=f"a kind of {above}, which {module}@{version} owns",
                repairs=[Repair(f"point at {above} instead: give {term} a slot "
                                f"whose range is {above}",
                                where=name, options=["add_slot"]),
                         Repair("or, where a role says what is meant, fill it",
                                where=name, options=["fill_role"])],
            )


def _own_business(conn, store, directory):
    """An application is sealed only into the kernel of the business it is for.

    Its sealing intent and the URIs it mints are that business's records; in
    another business's kernel they would be somebody else's private
    composition sitting in a log it has no part in.
    """
    module = store.module_of(directory) if store is not None else None
    if module is None:
        return
    from components.business import require_own
    require_own(conn, store, module)


def _no_foreign_kind(store, draft, name):
    """Raise the first. The rule itself is in `kind_refusals`."""
    for refusal in kind_refusals(store, draft, name):
        raise refusal


def _facts(annotations, ranges, name, view=None):
    """The stated facts, checked against the vocabulary the draft declares.

    Each carries `ref`, taken from its predicate's range: `True` where the
    value names an entity rather than saying something about one, and
    `confidence`, which is `None` unless the fact stated one.
    """
    stated = annotations.get("facts") or []
    if not isinstance(stated, list):
        raise DraftError(
            "facts_not_a_list",
            where=f"{name}: annotations.facts",
            expected="a list of facts",
            got=type(stated).__name__,
            repairs=[Repair("write each fact as one `- subject:` item", where=name)],
        )

    written = _written(view) if view is not None else {p: p for p in ranges}
    class_names = _class_facts(view) if view is not None else {}
    facts = []
    for i, fact in enumerate(stated, start=1):
        at = f"{name}: fact {i}"
        if not isinstance(fact, dict):
            raise DraftError(
                "fact_not_a_mapping",
                where=at,
                expected="subject, predicate and value",
                got=type(fact).__name__,
                repairs=[Repair("write the three keys under one `-` item", where=name)],
            )
        keys = set(fact)
        if not keys >= set(FACT_KEYS) or not keys <= set(FACT_KEYS + FACT_OPTIONAL):
            raise DraftError(
                "fact_keys",
                where=at,
                expected=f"{', '.join(FACT_KEYS)}, and optionally "
                         f"{', '.join(FACT_OPTIONAL)}",
                got=", ".join(sorted(str(k) for k in fact)) or "nothing",
                repairs=[Repair("use only these keys",
                                where=name,
                                options=FACT_KEYS + FACT_OPTIONAL)],
            )
        confidence = fact.get("confidence")
        if confidence is not None and confidence not in CONFIDENCE_LEVELS:
            raise DraftError(
                "fact_confidence",
                where=at,
                expected="a confidence the kernel knows",
                got=f"{confidence!r}",
                repairs=[Repair("state one of these, or leave it out — absent "
                                "records NULL, which claims nothing",
                                where=name, options=CONFIDENCE_LEVELS)],
            )
        full = written.get(str(fact["predicate"]))
        if full not in ranges:
            raise DraftError(
                "fact_predicate_unknown",
                where=at,
                expected="a predicate this draft declares a slot for",
                got=f"{fact['predicate']!r}",
                repairs=[Repair("state it under a slot_uri this draft declares",
                                where=name,
                                options=sorted(k for k in written if "://" not in k)
                                or sorted(ranges))],
            )
        if fact["value"] is None or isinstance(fact["value"], (dict, list)):
            raise DraftError(
                "fact_value_not_scalar",
                where=at,
                expected="one scalar value",
                got="nothing" if fact["value"] is None else type(fact["value"]).__name__,
                repairs=[Repair("state one value; a fact with several is several "
                                "facts", where=name)],
            )
        value = str(fact["value"])
        named = class_names.get(full)
        if named is not None:
            value = named.get(value, value)
        facts.append(
            {
                "subject": str(fact["subject"]),
                "predicate": full,
                "value": value,
                "ref": ranges[full],
                "confidence": confidence,
            }
        )
    return facts


def _valid_from(annotations, name):
    """When this definition took effect. Not optional, and never guessed.

    A default makes the guess silently: the seal instant dates the business
    from the day it was described and leaves every earlier period empty, and an
    unbounded past claims more than anyone knows. Whoever is describing the
    business is the one who can say, so the refusal sends the question back to
    the conversation instead of answering it here.
    """
    stated = annotations.get("valid_from")
    if not stated:
        raise DraftError(
            "no_valid_from",
            where=f"{name}: annotations",
            expected="`valid_from`, the instant these definitions took effect",
            got="none",
            repairs=[Repair(
                "state the date the business started doing it this way. It is "
                "not defaulted: the seal instant would date the business from "
                "the day somebody described it and leave every earlier period "
                "empty",
                where=name,
            )],
        )
    return _utc(stated)


def _flat(annotations, name):
    """Every annotation that travels into the sealed file is a scalar.

    `components/ontology/resolve.py` reads the annotations block with a scanner
    that tracks no depth: it enters the block at an indent-zero `annotations:`
    and leaves it at the next indent-zero key, so every `key: value` line
    between them is read as version metadata whatever it is nested under. A
    mapping under `annotations` therefore leaks its own keys upward, and a
    nested `valid_from`, `sealed_at`, `supersedes` or `transcript` silently
    replaces the real one — the wrong version resolves and nothing complains.

    The guard sits here rather than in the scanner because this is where the
    sealed file is decided, and a sealed version is never edited afterwards.
    `facts` is exempt by construction: it is stripped before the file is
    written, so its nested keys never reach a reader. Slot-level annotations
    are untouched — the scanner never enters them.
    """
    for key, value in annotations.items():
        if key == "facts":
            continue
        if isinstance(value, (dict, list)):
            raise DraftError(
                "annotation_not_scalar",
                where=f"{name}: annotations.{key}",
                expected="a scalar",
                got=type(value).__name__,
                repairs=[Repair(
                    f"flatten it, or move it onto the slot it is about. The "
                    f"version resolver reads this block without tracking depth, "
                    f"so a nested {key} leaks its own keys into the version "
                    f"metadata and can silently replace valid_from",
                    where=name,
                )],
            )


def _transcript(annotations, draft_path, name):
    """The transcript file this draft was produced by. Evidence, and required.

    Named relative to the draft's own directory. A conversation that was not
    saved cannot be recovered later, so a missing one is refused rather than
    warned about: under the map/log split the conversation lands nowhere else,
    and "why does the map say this" would be answerable only from a chat window
    nobody can search.
    """
    stated = annotations.get("transcript")
    if not stated:
        raise DraftError(
            "no_transcript",
            where=f"{name}: annotations",
            expected="`transcript`, naming the record of the conversation this came from",
            got="none",
            repairs=[Repair(
                "write down why the map says what it says, and name the file. "
                "It lands beside the version as vN.txt, which is the only place "
                "the reasoning survives",
                where=name,
                options=sorted(p.name for p in draft_path.parent.glob("*.txt")),
            )],
        )
    path = draft_path.parent / str(stated)
    if not path.is_file():
        raise DraftError(
            "transcript_missing",
            where=f"{name}: annotations.transcript",
            expected=f"a file beside the draft, named relative to {draft_path.parent.name}/",
            got=f"{stated!r}, which is not a file",
            repairs=[Repair("name a file that is there",
                            where=str(draft_path.parent),
                            options=sorted(p.name for p in draft_path.parent.glob("*.txt")))],
        )
    return path


def _next_version(into):
    """The next version number, and the version it supersedes.

    Read from inside the files, never from their names: `load_versions` takes
    each version's own `version:` key, and this only asks that it be `vN`.
    """
    versions = load_versions(into) if Path(into).exists() else []
    numbered = []
    for version in versions:
        match = _VERSION_NAME.match(version["version"])
        if match is None:
            raise DraftError(
                "version_not_numbered",
                where=version["path"].name,
                expected="a version named vN, so the next number can be assigned",
                got=f"{version['version']!r}",
                repairs=[Repair("the version key is read from inside the file, "
                                "never from its name", where=str(version["path"]))],
            )
        numbered.append((int(match.group(1)), version["version"]))
    if not numbered:
        return 1, None
    highest = max(numbered)
    return highest[0] + 1, highest[1]


def _sealed_document(draft, version, valid_from, sealed_at, supersedes):
    """The draft, stamped. `facts` does not travel: the log has them now."""
    annotations = dict(draft.get("annotations") or {})
    carried = {
        key: value
        for key, value in annotations.items()
        if key not in ("facts",) + STAMPED
    }
    # `version` sits next to `name`, where a reader looks for it, rather than
    # wherever appending a key happens to put it.
    document = {}
    for key, value in draft.items():
        document[key] = value
        if key == "name":
            document["version"] = version
    document["version"] = version
    document["annotations"] = {
        "valid_from": valid_from.isoformat(),
        "sealed_at": sealed_at.isoformat(),
        "supersedes": supersedes,
        # Rewritten, not carried: the transcript is about to sit beside this
        # file under the version's own name.
        "transcript": f"{version}.txt",
        **carried,
    }
    return document


def seal(conn, draft_path, *, actor_id, into=None, sealed_at=None, store=None,
         standard=True):
    """Seal one draft. Returns a dict describing what was written.

    Raises DraftError, before anything is written anywhere, if the draft is not
    sealable.

    With a module `store`, the draft's imports resolve through it, and when
    `into` is one of the store's modules the kernel records the version as
    `@scope/name@vN`: a bare `v1` names nothing once there is more than one
    module.

    A draft sealed into a module of the store is held to the recording standard
    (components/standard), last, once everything else holds: the store is
    where modules find and read each other, and the standard is what one owes
    the rest. A draft outside a store is read by nobody else. `standard=False`
    is for one caller only: replaying versions that were sealed before the
    standard existed, whose bytes are history and are not changed to fit a
    rule written after them.
    """
    draft_path = Path(draft_path)
    into = Path(into) if into is not None else ROOT / "business"
    sealed_at = _utc(sealed_at) if sealed_at else datetime.now(timezone.utc)

    if not draft_path.is_file():
        raise DraftError(
            "no_draft",
            where=str(draft_path),
            expected="a draft to seal",
            got="nothing at that path",
            repairs=[Repair("name a file that is there",
                            options=sorted(p.name for p in draft_path.parent.glob("*.yaml"))
                            if draft_path.parent.is_dir() else ())],
        )
    text = draft_path.read_text(encoding="utf-8")
    view = _validate(text, draft_path.name, store)
    draft = yaml.safe_load(text) or {}

    if store is not None:
        _pins_already_sealed(store, draft, sealed_at, draft_path.name)
        _one_version_per_module(store, draft, draft_path.name)
        _no_clash(store, draft, draft_path.name)
        _no_foreign_kind(store, draft, draft_path.name)
    ranges = _slot_ranges(view, draft_path.name)
    for refusal in range_refusals(view, draft, draft_path.name):
        raise refusal
    _roles(view, draft, draft_path.name)
    annotations = draft.get("annotations") or {}
    facts = _facts(annotations, ranges, draft_path.name, view)
    _compiles(view, draft_path)
    examples = _examples_hold(conn, view, draft, draft_path)
    if standard and store is not None and store.module_of(into):
        _standard_held(view, draft, draft_path)
    _own_business(conn, store, into)

    valid_from = _valid_from(annotations, draft_path.name)
    _flat(annotations, draft_path.name)
    transcript = _transcript(annotations, draft_path, draft_path.name)

    number, supersedes = _next_version(into)
    version = f"v{number}"
    document = _sealed_document(draft, version, valid_from, sealed_at, supersedes)
    sealed_text = yaml.safe_dump(
        document, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    _validate(sealed_text, f"{version}.yaml", store)

    path = into / f"{version}.yaml"
    transcript_path = into / f"{version}.txt"
    examples_path = into / f"{version}.examples.yaml"
    for existing in (path, transcript_path, examples_path):
        if existing.exists():
            raise DraftError(
                "version_exists",
                where=str(existing),
                expected=f"nothing at {version}, the next free number",
                got="a file already there",
                repairs=[Repair(
                    "a sealed version is never rewritten. Move the file aside "
                    "if it is a leftover, and otherwise seal a new version",
                    where=str(into),
                )],
            )

    # The version file first: a write that fails after this leaves an orphan
    # version, which is harmless, rather than assertions naming a version that
    # was never written. The transcript goes ahead of it, so no version file
    # ever names evidence that is not beside it. It is copied, not moved: the
    # draft it belongs to is left exactly as it was found.
    into.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(transcript, transcript_path)
    # The examples travel with the version they held for, and are never
    # rewritten either: a revision starts from them, and has to pass them.
    if examples is not None:
        shutil.copyfile(examples, examples_path)
    path.write_text(sealed_text, encoding="utf-8", newline="\n")

    with conn.cursor() as cur:
        cur.execute(_REGISTRY_SQL, (URI_PREDICATE,))
        known = {uri: entity_id for uri, entity_id in cur.fetchall()}

    # A class-ranged value names an entity, and an entity has to exist before a
    # row can point at it — so a URI first seen on the value side is registered
    # exactly as a subject is. Deduping against `known` and against this list is
    # what makes two facts about `uniti:thing_a` one entity rather than two,
    # whether they name it as a subject, as a value, or one of each.
    named = [fact["subject"] for fact in facts]
    named += [fact["value"] for fact in facts if fact["ref"]]

    minting = []
    for uri in [URI_PREDICATE] + list(ranges) + named:
        if uri not in known and uri not in minting:
            minting.append(uri)

    def ref(uri):
        """An existing entity's uuid, or the label this call mints it under."""
        return known.get(uri, uri)

    assertions = [
        {
            "subject": ref(uri),
            "predicate": ref(URI_PREDICATE),
            "value": uri,
            "valid_from": valid_from,
            "source": MINT_SOURCE,
        }
        for uri in minting
    ] + [
        {
            "subject": ref(fact["subject"]),
            "predicate": ref(fact["predicate"]),
            # One or the other, never both: the kernel's value_exactly_one
            # constraint counts the two columns together.
            **(
                {"ref": ref(fact["value"])}
                if fact["ref"]
                else {"value": fact["value"]}
            ),
            "valid_from": valid_from,
            "source": FACT_SOURCE,
            "confidence": fact["confidence"],
        }
        for fact in facts
    ]

    intent_id, names, assertion_ids = perform(
        conn,
        actor_id=actor_id,
        agent_id="seal",
        action_name="seal_version",
        ontology_version=_label(store, into, version),
        reason_code=_purpose(store, into),
        note=f"sealed {draft_path.name} as {version}",
        mint=minting,
        assertions=assertions,
        occurred_at=sealed_at,
        recorded_at=sealed_at,
    )

    return {
        "version": version,
        "path": path,
        "transcript": transcript_path,
        "examples": examples_path if examples is not None else None,
        "valid_from": valid_from,
        "sealed_at": sealed_at,
        "supersedes": supersedes,
        "intent_id": intent_id,
        "entities": {**known, **names},
        "minted": names,
        "assertions": assertion_ids,
    }


def _pins_already_sealed(store, draft, sealed_at, name):
    """Every pinned import was sealed before this seal.

    A version records what existed when it was sealed. Pinning a version
    sealed later would make the history say a module imported something that
    was not there yet.
    """
    for pinned_name, pinned_version in store.imports(draft):
        versions = store.versions(pinned_name)
        held = next(v for v in versions if v["version"] == pinned_version)
        if held["sealed_at"] > sealed_at:
            raise DraftError(
                "pin_sealed_later",
                where=f"{name}: {pinned_name}@{pinned_version}",
                expected=f"a version sealed before this seal at {sealed_at.isoformat()}",
                got=f"one sealed at {held['sealed_at'].isoformat()}",
                repairs=[Repair(
                    f"pin a version of {pinned_name} that existed by then; a "
                    f"version records what was there when it was sealed",
                    options=[f"{pinned_name}@{v['version']}" for v in versions
                             if v["sealed_at"] <= sealed_at],
                )],
            )


def _label(store, directory, version):
    """How the kernel names a version: `@scope/name@vN` for a module, else `vN`."""
    module = store.module_of(directory) if store is not None else None
    return f"{module}@{version}" if module else version


def _purpose(store, directory):
    """What the module's manifest says its content is for, or None.

    It becomes the intent's `reason_code`, so that a log holding made-up
    content says so on every row it was written by, and nobody has to know
    which module names are fixtures to find out.
    """
    module = store.module_of(directory) if store is not None else None
    return store.purpose(module) if module else None


def register(conn, version_path, *, actor_id, recorded_at=None, store=None):
    """Put a sealed version's vocabulary into a log, writing no file.

    `seal` does two things at once: it decides a version and it registers the
    URIs that version names. In one directory with one log that is right —
    every version file has its facts in the log beside it. Point the same map
    at a second log and the two come apart: the version already exists, the log
    knows none of its URIs, and there is no door in. Sealing again would mint a
    `vN+1` that describes nothing new, so the map store would grow a version
    for every store it was ever loaded into.

    So this registers and does not decide: it takes a version that is already
    sealed, reads the `slot_uri` of every slot it declares, and writes one
    `uniti:uri` row for each one the log does not already hold — the same rows
    `seal` writes, under the same predicate, dated by the version's own
    `valid_from`. Nothing is written to disk and no version number is assigned.

    It is not a way to load facts. A sealed version carries none: `seal` strips
    them on the way out, because a fact kept in the map is a fact living
    outside the log. A file that still carries `annotations.facts` is a draft
    however it is named, and is refused.

    Registering twice is not an error and writes nothing the second time: a URI
    the log already holds is left alone, exactly as a second `seal` reuses the
    predicates the first one minted.

    `recorded_at` is when this log learned the vocabulary, which is now, and is
    not the version's `sealed_at` — the version was sealed once, and a log
    seeded from it today is learning it today.
    """
    version_path = Path(version_path)
    if not version_path.is_file():
        raise DraftError(
            "no_version_file",
            where=str(version_path),
            expected="a sealed version to register",
            got="nothing at that path",
            repairs=[Repair("name a file that is there",
                            options=sorted(p.name for p in version_path.parent.glob("v*.yaml"))
                            if version_path.parent.is_dir() else ())],
        )
    text = version_path.read_text(encoding="utf-8")
    view = _validate(text, version_path.name, store)
    document = yaml.safe_load(text) or {}

    version = view.schema.version
    if not version:
        raise DraftError(
            "not_sealed",
            where=version_path.name,
            expected="a `version:` key, which seal stamps",
            got="none, so this is still a draft",
            repairs=[Repair("seal it, then register the version that comes out",
                            where=str(version_path))],
        )

    annotations = document.get("annotations") or {}
    if annotations.get("facts"):
        raise DraftError(
            "still_a_draft",
            where=f"{version_path.name}: annotations.facts",
            expected="none: seal strips them, because a fact kept in the map is "
                     "a fact living outside the log",
            got=f"{len(annotations['facts'])} still here",
            repairs=[Repair(
                "register states no facts, only the URIs a map names. Seal this "
                "as a version and register that instead",
                where=str(version_path),
            )],
        )

    ranges = _slot_ranges(view, version_path.name)
    valid_from = _valid_from(annotations, version_path.name)
    _own_business(conn, store, version_path.parent)

    with conn.cursor() as cur:
        cur.execute(_REGISTRY_SQL, (URI_PREDICATE,))
        known = {uri: entity_id for uri, entity_id in cur.fetchall()}

    minting = []
    for uri in [URI_PREDICATE] + list(ranges):
        if uri not in known and uri not in minting:
            minting.append(uri)

    # Nothing new is nothing written: not even an intent saying so.
    if not minting:
        return {"version": version, "path": version_path, "valid_from": valid_from,
                "intent_id": None, "entities": known, "minted": {}, "assertions": []}

    def ref(uri):
        return known.get(uri, uri)

    assertions = [
        {
            "subject": ref(uri),
            "predicate": ref(URI_PREDICATE),
            "value": uri,
            "valid_from": valid_from,
            "source": MINT_SOURCE,
        }
        for uri in minting
    ]

    intent_id, names, assertion_ids = perform(
        conn,
        actor_id=actor_id,
        agent_id="seal",
        action_name="register_version",
        ontology_version=_label(store, version_path.parent, version),
        reason_code=_purpose(store, version_path.parent),
        note=f"registered the URIs {version_path.name} names",
        mint=minting,
        assertions=assertions,
        recorded_at=recorded_at,
    )

    return {
        "version": version,
        "path": version_path,
        "valid_from": valid_from,
        "intent_id": intent_id,
        "entities": {**known, **names},
        "minted": names,
        "assertions": assertion_ids,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Seal a draft as the next version.")
    parser.add_argument(
        "draft",
        help="path to the draft, or to a sealed version with --register",
    )
    parser.add_argument("--actor", required=True, help="who is sealing")
    parser.add_argument("--into", default=None, help="version directory, default business/")
    parser.add_argument(
        "--register",
        action="store_true",
        help="the file is already sealed: put the URIs it names into this log "
             "and write nothing to disk",
    )
    # A dated episode is sealed at the instant it belongs to, not at the
    # instant it is replayed: seal() has taken sealed_at since it was written,
    # and without this the only caller that can pass one is a test.
    parser.add_argument(
        "--sealed-at",
        default=None,
        metavar="INSTANT",
        help="ISO 8601 instant this seal is recorded at, default now",
    )
    args = parser.parse_args(argv)

    try:
        sealed_at = _utc(args.sealed_at) if args.sealed_at else None
    except ValueError as exc:
        print(f"not sealed: --sealed-at is not an instant — {exc}", file=sys.stderr)
        return 2

    # The store the draft's pins resolve through. Without one a module import
    # is read as a path and fails far from the cause, as a traceback rather
    # than as a refusal saying which versions there are.
    from components.modules.store import Store
    store = Store.from_env()

    if args.register:
        try:
            with connect() as conn:
                result = register(conn, args.draft, actor_id=args.actor, store=store)
        except Refusal as exc:
            print(f"not registered: {exc.explain()}", file=sys.stderr)
            return 2
        print(f"registered {result['path']}  ({result['version']})")
        print(f"valid from {result['valid_from'].isoformat()}")
        print(
            f"intent {result['intent_id']}: {len(result['minted'])} entities minted, "
            f"{len(result['assertions'])} assertions"
        )
        return 0

    try:
        with connect() as conn:
            result = seal(
                conn,
                args.draft,
                actor_id=args.actor,
                into=args.into,
                sealed_at=sealed_at,
                store=store,
            )
    except Refusal as exc:
        print(f"not sealed: {exc.explain()}", file=sys.stderr)
        return 2

    print(f"sealed  {result['path']}  ({result['version']})")
    print(f"transcript {result['transcript']}")
    print(f"valid from {result['valid_from'].isoformat()}")
    print(f"sealed at  {result['sealed_at'].isoformat()}")
    print(
        f"intent {result['intent_id']}: {len(result['minted'])} entities minted, "
        f"{len(result['assertions'])} assertions"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""refusal — why not, and what would fix it.

A refusal is the most-read thing this system produces. Somebody describing a
business meets far more refusals than successes, and each one is a question
asked back at them. So a refusal here is **data before it is a sentence**:

    code      what kind of refusal it is, from a closed list. Stable across
              rewording, which is what makes it a thing to match on.
    where     the one place to look: a class, a column, a file.
    expected  what would have been accepted, as a noun phrase.
    got       what was there instead.
    repairs   what to do about it — each with the finite set of valid answers,
              wherever one can be computed.

One source, three readers:

    a person   `str(refusal)` is one sentence, assembled from the parts. The
               CLIs print it and the API sends it as `error`.
    a page     `as_dict()` is what the API sends beside it and what Studio
               draws: a repair is a control, not a paragraph.
    an agent   the same dict. `options` is the point — an agent choosing from
               an enumerated set cannot invent a slot that does not exist.

The sentence is **derived**, never written beside the structure. A refusal
carrying both would have two places to disagree, and the prose is the one
nobody updates.

Four gates raise these, and each says which it is, because the answer to
"who can fix this" differs: `DraftError` is the seal refusing to make a
version, `MapError` is the generator or the compiler refusing to read one,
`ModuleError` is the store refusing to find one, and `StudioError` is the
studio refusing to perform a step on a draft.

`repairs` is not decoration and is not optional in spirit. A refusal with no
repair is a dead end, and the only honest ones are the few where the answer is
genuinely outside the system — a file that is not there, a name only the author
knows.
"""

from dataclasses import dataclass, field

# Every way this system says no, and what each one means. A closed list, so
# that "what can go wrong here" is answerable without reading the code — it is
# the other half of the catalogue, and the constructor refuses a code that is
# not in it.
#
# Kept in one place on purpose: a code is a promise to whoever matched on it,
# and a promise made in forty scattered string literals is not one.
CODES = {
    # ---- the store: a module, a version, an import ------------------------
    "not_a_module_name": "a name that is not `@scope/name`",
    "no_such_module": "a module no root of the store holds",
    "manifest_disagrees": "a manifest that names a different module than its directory",
    "no_such_version": "a version of a module the store has not sealed",
    "import_not_pinned": "an import that names a module but no version of it",
    "import_not_understood": "an import that is neither `@scope/name@vN` nor `linkml:...`",
    "import_cycle": "modules that import each other in a ring",

    # ---- the seal: a draft becoming a version -----------------------------
    "no_draft": "no file where a draft was named",
    "not_linkml": "a draft LinkML itself cannot load",
    "slot_without_uri": "a slot with no `slot_uri`, so no identity in the kernel",
    "binding_ambiguous": "two or more slots filling one binding of a role",
    "binding_unfilled": "a role claimed and a required binding left unnamed",
    "two_versions_of_a_module": "one closure reaching one module at two versions",
    "pin_sealed_later": "a pin to a version sealed after the draft itself",
    "facts_not_a_list": "`annotations.facts` that is not a list",
    "fact_not_a_mapping": "a stated fact that is not a mapping",
    "fact_keys": "a stated fact with keys other than subject, predicate, value",
    "fact_confidence": "a confidence that is not one the kernel knows",
    "fact_predicate_unknown": "a fact under a predicate the draft does not declare",
    "fact_value_not_scalar": "a fact whose value is not one scalar",
    "no_valid_from": "a draft that does not say when its definitions took effect",
    "annotation_not_scalar": "a nested annotation, which would leak into version metadata",
    "no_transcript": "a draft naming no transcript of the conversation behind it",
    "transcript_missing": "a named transcript that is not a file",
    "version_not_numbered": "a held version whose name is not `vN`",
    "version_exists": "a version file already on disk, which is never rewritten",
    "no_version_file": "no file where a sealed version was named",
    "not_sealed": "a file carrying no version, so it is still a draft",
    "still_a_draft": "a version file that still carries stated facts",

    # ---- reading a map ----------------------------------------------------
    "no_map": "no file where a map was named",
    "pins_need_a_store": "a map that pins modules, read without a store to resolve them",
    "not_a_sealed_map": "a map with no version, read where a sealed one is needed",
    "no_such_class": "a class the map does not declare",
    "no_such_slot": "a slot the named class does not have",
    "no_such_column": "a column the planned table does not have",
    "no_such_field": "a form field the class does not have",
    "nothing_entered": "a submission with no value and no retraction in it",
    "no_type_slot": "a class with no slot carrying `designates_type`",
    "identity_column_taken": "a class whose own slot is named like the identity column",
    "nothing_to_compile": "a map declaring neither an aggregate nor a class with entities",

    # ---- reading a rule ---------------------------------------------------
    "aggregate_keys": "an aggregate whose keys are not the ones an aggregate has",
    "parameter_keys": "a parameter whose keys are not `of` and `slot`",
    "convert_keys": "a convert block whose keys are not `using`, `on` and `factor`",
    "convert_on_empty": "a convert block that maps nothing",
    "where_not_is_a": "a `where` condition that is not `is_a`",
    "not_a_class": "a rule naming something that is not a class",
    "not_summable": "a rule totalling something whose range cannot be totalled",
    "no_grouping": "an aggregate with no `by`, which groups nothing",
    "types_disagree": "slots filling one binding whose ranges do not agree",
    "role_has_no_rows": "a rule over a role nothing concrete descends from",
    "two_rules_on_a_column": "a column carrying more than one rule",
    "no_aggregate": "a class no rule derives a table for",
    "groupings_disagree": "aggregates on one class grouping by different sets",
    "grouped_by_unknown": "a grouping naming a column the class does not have",
    "grouped_by_derived": "a grouping naming a column the class derives",
    "not_a_key_column": "a parameter reading off a column that is not a key",
    "key_range_not_a_class": "a parameter reading off a key whose value names no entity",
    "slot_not_below": "a slot no class below the named range declares",
    "expression_cycle": "an expression written in terms of itself",
    "expression_not_arithmetic": "an expression that is more than arithmetic",
    "expression_names_unknown": "an expression naming a column that does not exist",

    # ---- the studio: a draft being built ----------------------------------
    "not_an_operation": "a step the studio does not perform",
    "operation_arguments": "a step given arguments it does not take",
    "module_exists": "a module the store already holds",
    "draft_open": "a module whose draft is already open",
    "nothing_sealed": "a module with no sealed version to revise",
    "name_taken": "a name something in this draft already uses",
    "not_in_draft": "a class or slot nothing this draft can see declares",
    "not_yours": "a class or slot of a pinned module, which a draft cannot change",
    "not_a_field": "a field that is not one this thing has",
    "not_a_role": "a class that is not a role, so nothing can claim it",
    "not_a_binding": "a slot that is not a binding any role obliges",
    "not_attached": "a slot that is not on the class",
    "not_a_pin": "an import this draft does not hold",

    # ---- the command line -------------------------------------------------
    "not_field_value": "a `--set` argument that is not FIELD=VALUE",
}

# How many options a terminal prints before it stops. The dict keeps them all:
# this is a courtesy to a person reading, never a limit on what a caller gets.
SHOWN = 12


@dataclass
class Repair:
    """One way out, and — where it can be computed — the answers that fit.

    `do` is an imperative addressed to whoever can act. `where` names the file
    or class to change it in, and is worth stating whenever it is not the place
    the refusal points at: a repair inside somebody else's sealed module is a
    different kind of problem from one in your own draft, and a reader should
    not have to work that out.

    `options` is the finite set of valid answers. It is what makes a refusal
    something a form can render as a list and an agent can choose from rather
    than guess at, and it is why nothing here is phrased as advice.
    """

    do: str
    where: str = None
    options: tuple = field(default_factory=tuple)

    def __post_init__(self):
        self.options = tuple(str(option) for option in self.options)
        self.where = str(self.where) if self.where is not None else None

    def as_dict(self):
        return {"do": self.do, "where": self.where, "options": list(self.options)}


class Refusal(Exception):
    """Nothing was written. Here is where, what was expected, and what to do."""

    # Which gate is speaking. Subclasses name themselves, because a refusal
    # from the store and a refusal from the seal are answered by different
    # people.
    gate = "the system"

    def __init__(self, code, *, where, expected, got, repairs=()):
        if code not in CODES:
            raise KeyError(
                f"{code!r} is not a refusal code — add it to refusal.CODES, "
                f"where every way this system says no is written down once"
            )
        self.code = code
        self.where = str(where)
        self.expected = str(expected)
        self.got = str(got)
        self.repairs = list(repairs)
        super().__init__(self.sentence())

    def sentence(self):
        """The whole refusal as one line, assembled from the parts."""
        return f"{self.where}: expected {self.expected}, got {self.got}"

    def as_dict(self):
        """What the API sends and what Studio draws."""
        return {
            "code": self.code,
            "means": CODES[self.code],
            "gate": self.gate,
            "where": self.where,
            "expected": self.expected,
            "got": self.got,
            "sentence": self.sentence(),
            "repairs": [repair.as_dict() for repair in self.repairs],
        }

    def explain(self):
        """The same thing for a terminal: the sentence, then what to do."""
        lines = [self.sentence()]
        for repair in self.repairs:
            lines.append(f"    fix  {repair.do}")
            if repair.where:
                lines.append(f"         in {repair.where}")
            if repair.options:
                shown = ", ".join(repair.options[:SHOWN])
                if len(repair.options) > SHOWN:
                    shown += f", and {len(repair.options) - SHOWN} more"
                lines.append(f"         one of: {shown}")
        return "\n".join(lines)


__all__ = ["CODES", "Refusal", "Repair"]

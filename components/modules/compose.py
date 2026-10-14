"""compose — modules read together, each under its own names.

LinkML puts every name of a closure into one space, and a second declaration
of a name silently replaces the first: two authors who both called a class
`Rental` cannot be pinned side by side, and whichever was read last breaks the
other's rules (ECOSYSTEM_PLAN.md §4.3). So Uniti composes modules itself, and
LinkML is never asked to merge a name.

A pinned module is read with its own names qualified by its tag, its scope and
name together:

    @komunitas/penyewaan   Rental, rental_customer
        read by whoever pins it as
                           komunitas_penyewaan__Rental,
                           komunitas_penyewaan__rental_customer

The scope is part of the tag because a name alone is not unique: `kasir` and
`penyewaan` will be chosen by more than one author, and two modules with one
tag can never meet (ECOSYSTEM_PLAN.md §0.3, G1). `@scope/name` is unique in a
store, so the tag is too, but for a `-` read like the `_` that joins scope and
name: `@a-b/c` and `@a/b-c`.

The `__` is not `.`, which a rule already uses for one hop
(`by: key=slot.slot`). The names a module wrote for itself never change: its
own draft and its own version keep them plain, and only those who pin it see
the tag.

Three things hold the composition steady:

  - Every `class_uri` and `slot_uri` is locked to the full URI the module
    itself meant, so a qualified name records under exactly the predicate the
    plain one did. Nothing in the log moves.
  - Core's and the library's names are reserved: they stay plain everywhere,
    because they are what modules share, and no other module may declare one.
  - Two modules with the same tag cannot be read together (`tag_taken`): the
    tag is the whole of what tells their names apart. Only the
    transliteration lets it happen: `@a-b/c` and `@a/b-c`.

A reference is resolved by one rule, wherever it is written — a pinned
module, the draft being built, an example: a name the module declares itself
is its own; a name in sight as it is written is that one; otherwise a plain
name stands for the one qualified name whose plain part it is, when there is
exactly one. With none or several it is left as written, for a reader to ask
"which one?".

A module may add facts to a thing another module owns — a facet: Rudi's
`rental_rate` on the library's `Item`. It declares the slot as its own, with
`domain: Item`, and the composition hangs the slot on `Item` (`attach`). Only
a composition that pins Rudi's module does: the library's version is never
touched, no second record exists, and the slot keeps Rudi's predicate.
"""

import copy
import re

SEP = "__"

KINDS = ("classes", "slots", "enums")

# `{name}` in an expression.
_REF = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def tag_of(module):
    """The tag a module's names are qualified with: `@scope/name` -> `scope_name`."""
    scope, name = str(module).lstrip("@").split("/", 1)
    return f"{scope}_{name}".replace("-", "_")


def qualified(tag, name):
    return f"{tag}{SEP}{name}"


def plain(name):
    """The name as its module wrote it."""
    return str(name).rsplit(SEP, 1)[-1]


def tag_in(name):
    """The tag a composed name carries, or None for a plain one."""
    text = str(name)
    return text.rsplit(SEP, 1)[0] if SEP in text else None


def matches(name, known):
    """Every name of `known` that `name` may stand for, by the one rule.

    The name itself when it is known as written; otherwise each qualified name
    whose plain part it is. One match is the answer; several is the question.
    """
    name = str(name)
    if name in known:
        return [name]
    if SEP in name:
        return []
    return sorted(k for k in known if SEP in str(k) and plain(k) == name)


def declared(document):
    """Every class, slot and enum name a document declares, by kind."""
    return {kind: [str(n) for n in (document.get(kind) or {})] for kind in KINDS}


def expand(document, curie):
    """A CURIE as the full URI its own document means by it."""
    text = str(curie)
    if "://" in text:
        return text
    prefix, sep, local = text.partition(":")
    held = (document.get("prefixes") or {}).get(prefix) if sep else None
    if isinstance(held, dict):
        held = held.get("prefix_reference")
    return f"{held}{local}" if held else text


def rewrite(document, rename, refer, *, lock=False):
    """A copy of `document` with its names renamed and its references resolved.

    `rename(name)` is what a name the document declares is called in the
    composition; `refer(name)` what a name it mentions stands for. With
    `lock`, every class and slot keeps the full URI its plain name meant.
    Everything the vocabulary names is reached: `is_a`, `mixins`, `slots`,
    `slot_usage`, `range`, `domain`, rule annotations and expressions.
    """
    out = {k: copy.deepcopy(v) for k, v in document.items() if k not in KINDS}
    default = document.get("default_prefix")

    def path(value):
        return ".".join(refer(part) for part in str(value).split("."))

    classes = {}
    for name, body in (document.get("classes") or {}).items():
        body = copy.deepcopy(body or {})
        if lock:
            body["class_uri"] = expand(document, body.get("class_uri")
                                       or f"{default}:{name}")
        if body.get("is_a"):
            body["is_a"] = refer(body["is_a"])
        if body.get("mixins"):
            body["mixins"] = [refer(m) for m in body["mixins"]]
        if body.get("slots"):
            body["slots"] = [refer(s) for s in body["slots"]]
        if body.get("slot_usage"):
            body["slot_usage"] = {refer(k): _slot_refs(v or {}, refer, path)
                                  for k, v in body["slot_usage"].items()}
        classes[rename(name)] = body

    slots = {}
    for name, body in (document.get("slots") or {}).items():
        body = _slot_refs(copy.deepcopy(body or {}), refer, path)
        if lock:
            body["slot_uri"] = expand(document, body.get("slot_uri")
                                      or f"{default}:{name}")
        slots[rename(name)] = body

    enums = {rename(n): copy.deepcopy(e) for n, e in (document.get("enums") or {}).items()}
    for key, held in (("classes", classes), ("slots", slots), ("enums", enums)):
        if key in document:
            out[key] = held
    return out


def _slot_refs(body, refer, path):
    """One slot's body, or one slot usage, with every name in it resolved."""
    for key in ("range", "is_a", "domain"):
        if body.get(key):
            body[key] = refer(body[key])
    if body.get("equals_expression"):
        body["equals_expression"] = _REF.sub(
            lambda m: "{" + refer(m.group(1)) + "}", str(body["equals_expression"]))
    annotations = body.get("annotations") or {}
    for kind in ("aggregate", "parameter"):
        held = annotations.get(kind)
        if not isinstance(held, dict):
            continue
        wrapped = set(held) == {"value"}
        spec = dict(held["value"] if wrapped else held)
        if isinstance(spec.get("sources"), list):
            spec["sources"] = [_rule_refs(dict(source), refer, path)
                               for source in spec["sources"]]
        spec = _rule_refs(spec, refer, path)
        annotations[kind] = {"value": spec} if wrapped else spec
    return body


def _rule_refs(spec, refer, path):
    """One rule, or one source of an aggregate, with every name in it resolved."""
    for key in ("over", "sum", "of", "slot"):
        if spec.get(key):
            spec[key] = refer(spec[key])
    if isinstance(spec.get("by"), dict):
        spec["by"] = {refer(k): path(v) for k, v in spec["by"].items()}
    if isinstance(spec.get("where"), dict):
        spec["where"] = {refer(k): ({**w, "is_a": refer(w["is_a"])}
                                    if isinstance(w, dict) and w.get("is_a") else w)
                         for k, w in spec["where"].items()}
    if isinstance(spec.get("convert"), dict):
        convert = dict(spec["convert"])
        for key in ("using", "factor"):
            if convert.get(key):
                convert[key] = refer(convert[key])
        for key in ("on", True):
            if isinstance(convert.get(key), dict):
                convert[key] = {refer(k): path(v) for k, v in convert[key].items()}
            elif convert.get(key):
                convert[key] = path(convert[key])
        spec["convert"] = convert
    return spec


def facets(entries):
    """Every facet in a composition: a slot one document declares with a
    `domain` that another document of the composition declares as a class.

    `entries` are a composition's `(pin, document)` pairs. Returned as
    `(class, slot, pin)`, in the composition's order: the class it adds to,
    the slot as the composition calls it, and the pin of the module that
    declares the slot (`None` for the document being read itself). A
    `domain` naming a class of the slot's own document is LinkML's own
    business and no facet.
    """
    owner = {}
    for index, (_pin, document) in enumerate(entries):
        for name in (document.get("classes") or {}):
            owner.setdefault(str(name), index)
    out = []
    for index, (pin, document) in enumerate(entries):
        for name, body in (document.get("slots") or {}).items():
            domain = str((body or {}).get("domain") or "")
            if domain and owner.get(domain, index) != index:
                out.append((domain, str(name), pin))
    return out


def attach(entries):
    """A composition with every facet carried by the class it adds to.

    The slot is appended to that class's own list, in the copy of its
    owner's document this composition holds: the owner's sealed version is
    never touched, and a composition that does not pin the facet's module
    never sees it.
    """
    owner = {}
    for _pin, document in entries:
        for name, body in (document.get("classes") or {}).items():
            owner.setdefault(str(name), document)
    for class_name, slot, _pin in facets(entries):
        classes = owner[class_name]["classes"]
        body = classes[class_name] or {}
        slots = [str(s) for s in (body.get("slots") or [])]
        if slot not in slots:
            body["slots"] = slots + [slot]
        classes[class_name] = body
    return entries


def resolver(own, known, rename=lambda n: n):
    """The one rule, for a document declaring `own` among `known` names.

    `own` are the names the document declares, as it wrote them; `rename` is
    what each is called in the composition. `known` is every composed name
    the document can see beside its own.
    """
    own = set(own)

    def refer(name):
        name = str(name)
        if name in own:
            return rename(name)
        found = matches(name, known)
        return found[0] if len(found) == 1 else name
    return refer


def ambiguous(document, known):
    """Every name a document mentions that stands for more than one in sight.

    Read off the same rewrite that resolves them, so what is asked about is
    exactly what the rule could not settle: (name, the names it could be).
    """
    own = {n for names in declared(document).values() for n in names}
    out = {}

    def refer(name):
        name = str(name)
        if name not in own:
            found = matches(name, known)
            if len(found) > 1:
                out[name] = found
        return name
    rewrite(document, lambda n: n, refer)
    return sorted(out.items())


__all__ = ["SEP", "tag_of", "qualified", "plain", "tag_in", "matches",
           "declared", "rewrite", "resolver", "ambiguous", "expand",
           "facets", "attach"]

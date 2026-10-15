"""jargon — the system's own words, which a business owner is never told.

The agent speaks to two kinds of people. A module's author builds for many
businesses and works with modules, versions and seals; to them those are the
words of the job. A business owner composing their own application is told
about their business: what is kept, what happened, what is worked out. The
guide asks the agent to use a technical word only when the person used it
first; this is that rule, written down so a machine can hold it.

    found(text, said)   the system's words in `text` the person never used
    spoken(output)      every sentence of a turn's ending the person reads
    leaks(turns)        each turn of a kept conversation that told the person
                        a word of the system's, and which

What counts is the machinery: a module's tag (`@scope/name`), a name as the
system writes it (`rental_note`, `tag__Name`), anything in backticks, and the
words for the system's own parts in English and in Indonesian, the two
languages the people of the tests write in. Everyday words that a business
also uses ("draft", "version", "table") are not on it.

`builder` hands back an ending that uses one while an application is open
(`audience`), and the ecosystem test reads the kept conversations with
`leaks`. The same list, for the application screen, is `MACHINERY` in
web/src/lens.ts.
"""

import re

WORDS = (
    # English
    "module", "modules", "seal", "seals", "sealed", "sealing", "unseal",
    "pin", "pins", "pinned", "pinning", "unpin", "slot", "slots", "class",
    "classes", "predicate", "predicates", "aggregate", "aggregates", "schema",
    "projection", "projections", "kernel", "refusal", "refusals", "uri",
    "sql", "yaml", "closure", "intent", "intents", "manifest", "facet",
    "facets", "namespace", "catalogue", "catalog",
    # Indonesian
    "modul", "segel", "disegel", "menyegel", "tersegel", "penyegelan",
    "disematkan", "menyematkan", "sematkan", "kelas", "predikat", "skema",
    "proyeksi", "katalog",
)

# A word of the list, with the endings Indonesian adds to a word ("modulnya").
_WORD = re.compile(r"\b(" + "|".join(WORDS) + r")(?:nya|lah|ku|mu)?\b", re.IGNORECASE)
# A tag, a name with an underscore, or anything quoted as code.
_NAME = re.compile(r"@[\w.-]+/[\w.-]+|\b[A-Za-z][A-Za-z0-9]*(?:_+[A-Za-z0-9]+)+\b|`[^`]+`")


def found(text, said=()):
    """The system's words in `text`, in the order they come, each once;
    leaving out any word the person used first (`said`: what they said)."""
    text = text or ""
    theirs = " ".join(said).lower()
    names = list(_NAME.finditer(text))
    words = [m for m in _WORD.finditer(text)
             if not any(n.start() <= m.start() < n.end() for n in names)]
    out = []
    for match in sorted(names + words, key=lambda m: m.start()):
        word = match.group(0)
        root = (match.group(1) if match.re is _WORD else word).lower()
        if root in theirs or word.lower() in (w.lower() for w in out):
            continue
        out.append(word)
    return out


def spoken(said):
    """Every sentence a turn's ending puts before the person, from the ending
    as it is kept (`said`, a dict) or as the builder made it (a model)."""
    if hasattr(said, "model_dump"):
        said = said.model_dump()
    texts = []
    for key in ("message", "question", "builds"):
        if said.get(key):
            texts.append(said[key])
    for key in ("choices", "records", "reuses", "elsewhere", "numbers", "cannot"):
        texts += [line for line in said.get(key) or [] if line]
    return texts


def leaks(turns):
    """Each turn of a kept conversation whose ending told the person a word of
    the system's they had not used: (turn number, the words)."""
    out = []
    said = []
    for n, turn in enumerate(turns, 1):
        said.append(turn.get("person") or "")
        words = found("\n".join(spoken(turn.get("said") or {})), said)
        if words:
            out.append((n, words))
    return out


__all__ = ["WORDS", "found", "leaks", "spoken"]

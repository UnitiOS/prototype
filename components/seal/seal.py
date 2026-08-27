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

A fact is stated in the draft's `annotations.facts`, three keys and no more:

    annotations:
      valid_from: '2026-01-01T00:00:00Z'
      facts:
        - subject: uniti:freezer_a
          predicate: uniti:freezer_label
          value: Freezer A

`predicate` is a `slot_uri` the draft declares — that is the whole of the join
between map and log. `subject` is a URI too, because the kernel's `entity` has
no name column: identity is an assertion like everything else. Every URI is
registered by one assertion under the well-known predicate `uniti:uri`, which
registers itself — one row whose subject, predicate and value all name the same
thing — so a single query finds every entity the map has ever named, and a
second seal reuses them instead of minting twins.

The draft also names its transcript, relative to its own directory:

    annotations:
      transcript: draft.txt

That file is evidence and is required. It lands beside the version as `vN.txt`
and the sealed annotation is rewritten to match, so a sealed version and the
conversation that produced it are found together.

Run: .venv/Scripts/python.exe components/seal/seal.py business/draft.yaml --actor fareza
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
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components"))

from ontology.resolve import load_versions  # noqa: E402
from perform import connect, perform  # noqa: E402

# The predicate every entity's URI is recorded under. It registers itself.
URI_PREDICATE = "uniti:uri"

# A fact says who, what, and what it is. Anything else is a typo — and an
# unknown key here would also be read as version metadata by the ontology
# resolver, which scans the annotations block shallowly.
FACT_KEYS = ("subject", "predicate", "value")

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


class DraftError(Exception):
    """The draft cannot be sealed. Nothing has been written."""


def _utc(value):
    """An ISO 8601 string or a datetime, as one aware datetime."""
    moment = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _validate(text, name):
    """Load through SchemaView, which is what "valid LinkML" means here.

    SchemaView raises on malformed YAML, on a missing `id` or `name`, and on
    any key the metamodel does not know. It does not resolve ranges or class
    slot references — that is not parsing, and the generator will meet those.
    """
    try:
        return SchemaView(text)
    except Exception as exc:
        raise DraftError(
            f"{name} is not valid LinkML — {type(exc).__name__}: {exc}"
        ) from exc


def _slot_uris(view, name):
    """Every `slot_uri` the draft declares, in the order it declares them.

    An explicit `slot_uri` is not optional. A slot without one has no identity
    a fact can point at, and a URI derived from the schema's own naming would
    change with every rename and orphan every fact recorded before it.
    """
    uris = []
    for slot_name, slot in view.schema.slots.items():
        if not slot.slot_uri:
            raise DraftError(
                f"{name}: slot '{slot_name}' declares no slot_uri, so it has no "
                f"identity in the kernel"
            )
        if slot.slot_uri not in uris:
            uris.append(slot.slot_uri)
    return uris


def _facts(annotations, slot_uris, name):
    """The stated facts, checked against the vocabulary the draft declares."""
    stated = annotations.get("facts") or []
    if not isinstance(stated, list):
        raise DraftError(f"{name}: annotations.facts must be a list")

    facts = []
    for i, fact in enumerate(stated, start=1):
        if not isinstance(fact, dict):
            raise DraftError(f"{name}: fact {i} is not a mapping")
        if set(fact) != set(FACT_KEYS):
            raise DraftError(
                f"{name}: fact {i} has keys {sorted(fact)}, expected "
                f"{sorted(FACT_KEYS)}"
            )
        if fact["predicate"] not in slot_uris:
            raise DraftError(
                f"{name}: fact {i} names predicate {fact['predicate']!r}, which "
                f"no slot in this draft declares"
            )
        if fact["value"] is None or isinstance(fact["value"], (dict, list)):
            raise DraftError(f"{name}: fact {i} must state one scalar value")
        facts.append(
            {
                "subject": str(fact["subject"]),
                "predicate": str(fact["predicate"]),
                "value": str(fact["value"]),
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
            f"{name}: annotations declare no valid_from, so nothing says when "
            f"this definition took effect"
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
                f"{name}: annotations.{key} is a {type(value).__name__}, and every "
                f"annotation carried into a sealed version must be a scalar — a "
                f"nested block leaks its keys into the version metadata"
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
            f"{name}: annotations declare no transcript, so nothing records the "
            f"conversation this map came from"
        )
    path = draft_path.parent / str(stated)
    if not path.is_file():
        raise DraftError(f"{name}: names transcript {stated!r}, which is not a file")
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
                f"{version['path'].name} carries version {version['version']!r}, "
                f"which is not vN — the next number cannot be assigned"
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


def seal(conn, draft_path, *, actor_id, into=None, sealed_at=None):
    """Seal one draft. Returns a dict describing what was written.

    Raises DraftError, before anything is written anywhere, if the draft is not
    sealable.
    """
    draft_path = Path(draft_path)
    into = Path(into) if into is not None else ROOT / "business"
    sealed_at = _utc(sealed_at) if sealed_at else datetime.now(timezone.utc)

    if not draft_path.is_file():
        raise DraftError(f"no draft at {draft_path}")
    text = draft_path.read_text(encoding="utf-8")
    view = _validate(text, draft_path.name)
    draft = yaml.safe_load(text) or {}

    slot_uris = _slot_uris(view, draft_path.name)
    annotations = draft.get("annotations") or {}
    facts = _facts(annotations, slot_uris, draft_path.name)

    valid_from = _valid_from(annotations, draft_path.name)
    _flat(annotations, draft_path.name)
    transcript = _transcript(annotations, draft_path, draft_path.name)

    number, supersedes = _next_version(into)
    version = f"v{number}"
    document = _sealed_document(draft, version, valid_from, sealed_at, supersedes)
    sealed_text = yaml.safe_dump(
        document, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    _validate(sealed_text, f"{version}.yaml")

    path = into / f"{version}.yaml"
    transcript_path = into / f"{version}.txt"
    for existing in (path, transcript_path):
        if existing.exists():
            raise DraftError(
                f"{existing} already exists — a sealed version is never rewritten"
            )

    # The version file first: a write that fails after this leaves an orphan
    # version, which is harmless, rather than assertions naming a version that
    # was never written. The transcript goes ahead of it, so no version file
    # ever names evidence that is not beside it. It is copied, not moved: the
    # draft it belongs to is left exactly as it was found.
    into.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(transcript, transcript_path)
    path.write_text(sealed_text, encoding="utf-8", newline="\n")

    with conn.cursor() as cur:
        cur.execute(_REGISTRY_SQL, (URI_PREDICATE,))
        known = {uri: entity_id for uri, entity_id in cur.fetchall()}

    minting = []
    for uri in [URI_PREDICATE] + slot_uris + [fact["subject"] for fact in facts]:
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
            "value": fact["value"],
            "valid_from": valid_from,
            "source": FACT_SOURCE,
        }
        for fact in facts
    ]

    intent_id, names, assertion_ids = perform(
        conn,
        actor_id=actor_id,
        agent_id="seal",
        action_name="seal_version",
        ontology_version=version,
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
        "valid_from": valid_from,
        "sealed_at": sealed_at,
        "supersedes": supersedes,
        "intent_id": intent_id,
        "entities": {**known, **names},
        "minted": names,
        "assertions": assertion_ids,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Seal a draft as the next version.")
    parser.add_argument("draft", help="path to the draft, e.g. business/draft.yaml")
    parser.add_argument("--actor", required=True, help="who is sealing")
    parser.add_argument("--into", default=None, help="version directory, default business/")
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

    try:
        with connect() as conn:
            result = seal(
                conn,
                args.draft,
                actor_id=args.actor,
                into=args.into,
                sealed_at=sealed_at,
            )
    except DraftError as exc:
        print(f"not sealed: {exc}", file=sys.stderr)
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

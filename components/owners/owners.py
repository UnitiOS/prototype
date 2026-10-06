"""owners — who may seal under a name, kept as statements in the kernel.

A module's name begins with the name it is published under, its scope:
`@uniti` in `@uniti/party`, `@kemahceria` in `@kemahceria/rental`. Only an
owner of that name seals a new version under it (DESIGN_NOTES.md §15.4).
Anybody else asks an owner, copies the module to a name of their own, or
links to it from a module or an application of their own.

Each owner of a name is one statement in the kernel the versions are sealed
into, valid from a day:

    subject     uniti:owner/@kemahceria/budi
    predicate   uniti:name_owner
    value       owner, or `removed` from the day they stop being one

so who owned `@uniti` in August is read at two clocks, like every other
number, and a removed owner stays in the history.

A name nobody has owned yet becomes the property of whoever seals under it
first, in the same intent as the seal, so the log says so where it happened.
From then on an owner adds and removes owners. The last owner cannot remove
themselves: a name with no owner would be taken by the next person to seal.
A business's kernel gives its own name to the person who declares it
(components/business).

Registering another owner's version into a kernel is not checked: that is
reading their work, not making it. Drafts are not checked either: anyone may
try anything in the studio, and the rule speaks when a version is sealed.

There is no sign-in yet, so an owner is the name a person writes. The rule
keeps the record honest and stops a mistaken seal; it does not stop somebody
writing another person's name.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from components.refusal import Refusal, Repair  # noqa: E402
from perform import perform  # noqa: E402
from resolve import resolve_single  # noqa: E402
from seal import _REGISTRY_SQL, MINT_SOURCE, URI_PREDICATE, _utc  # noqa: E402

PREFIX = "uniti:owner/"
OWNS = "uniti:name_owner"
OWNER = "owner"
REMOVED = "removed"

# What naming owners is stated under: it belongs to no map.
LABEL = "kernel"

# An owner adding or removing one is a person saying so; the first owner of a
# name is the rule's doing, read off the seal that claimed it.
SOURCE = "human_stated"
CLAIMED = "system_derived"


class OwnerError(Refusal):
    """Only a name's owners seal under it and change who owns it. Nothing was
    written."""

    gate = "the owners of names"


def scope_of(name):
    """The name a module is published under: `@uniti` for `@uniti/party`."""
    return str(name).split("/", 1)[0]


def subject(scope, person):
    return f"{PREFIX}{scope}/{quote(person, safe='')}"


# ---------------------------------------------------------------- statements

def known(conn):
    """Every URI the log has registered, and the entity it names."""
    with conn.cursor() as cur:
        cur.execute(_REGISTRY_SQL, (URI_PREDICATE,))
        return {uri: entity_id for uri, entity_id in cur.fetchall()}


def state(conn, statements, *, actor_id, action_name, ontology_version, note,
          reason_code=None, recorded_at=None):
    """One intent stating each (subject, predicate, value, valid_from, source),
    registering whichever URIs are new. Returns the intent and the id of each
    statement, in order."""
    held = known(conn)
    uris = [URI_PREDICATE] + [uri for s in statements for uri in s[:2]]
    minting = [uri for uri in dict.fromkeys(uris) if uri not in held]

    def ref(uri):
        return held.get(uri, uri)

    first = statements[0][3] if statements else None
    registered = [{"subject": ref(uri), "predicate": ref(URI_PREDICATE), "value": uri,
                   "valid_from": first, "source": MINT_SOURCE}
                  for uri in minting]
    stated = [{"subject": ref(s), "predicate": ref(p), "value": v,
               "valid_from": valid_from, "source": source}
              for s, p, v, valid_from, source in statements]
    intent_id, _, assertion_ids = perform(
        conn, actor_id=actor_id, action_name=action_name,
        ontology_version=ontology_version, reason_code=reason_code, note=note,
        mint=minting, assertions=registered + stated, recorded_at=recorded_at)
    return intent_id, assertion_ids[len(registered):]


def claim(scope, person, valid_from):
    """The statement that makes `person` the first owner of `scope`."""
    return (subject(scope, person), OWNS, OWNER, _utc(valid_from), CLAIMED)


# ---------------------------------------------------------------- reading

def _subjects(held, scope):
    head = f"{PREFIX}{scope}/"
    return {unquote(uri[len(head):]): entity_id for uri, entity_id in held.items()
            if uri.startswith(head)}


def owners(conn, scope, *, valid_at=None, as_of=None):
    """Who owns `scope` on `valid_at`, as the log stood at `as_of`, each with
    the day they became an owner."""
    now = datetime.now(timezone.utc)
    held = known(conn)
    if OWNS not in held:
        return []
    out = []
    for person, entity_id in _subjects(held, scope).items():
        row = resolve_single(conn, subject_id=entity_id, predicate_id=held[OWNS],
                             valid_at=_utc(valid_at or now), as_of=_utc(as_of or now))
        if row is not None and row["value_literal"] == OWNER:
            out.append({"owner": person, "since": row["valid_from"],
                        "assertion": row["id"]})
    return sorted(out, key=lambda o: o["owner"])


def owned(conn, scope):
    """Whether the log has ever named an owner of `scope`."""
    return bool(_subjects(known(conn), scope))


def names(conn, *, valid_at=None, as_of=None):
    """Every name the log knows an owner of, with its owners."""
    scopes = {uri[len(PREFIX):].split("/", 1)[0] for uri in known(conn)
              if uri.startswith(PREFIX)}
    return [{"name": scope, "owners": owners(conn, scope, valid_at=valid_at, as_of=as_of)}
            for scope in sorted(scopes)]


# ---------------------------------------------------------------- the rule

def _person(person):
    person = str(person or "").strip()
    if not person:
        raise OwnerError(
            "no_person",
            where="the owner",
            expected="the name of the person",
            got="nothing",
            repairs=[Repair("say who it is")],
        )
    return person


def _not_an_owner(conn, scope, person, *, valid_at, doing, where, dated=True):
    current = owners(conn, scope, valid_at=valid_at)
    return OwnerError(
        "not_an_owner",
        where=where,
        expected=f"{doing} by an owner of {scope}",
        got=f"{person}, who is not one" + (f" on {_utc(valid_at).date()}" if dated else ""),
        repairs=[Repair(f"ask an owner of {scope} to do it, or to add you as an owner",
                        options=[o["owner"] for o in current]),
                 Repair("or copy the module to a name of your own"),
                 Repair("or link to it from a module or an application of your own")],
    )


def at_seal(conn, name, person, *, sealed_at):
    """What sealing a version of `name` by `person` says about its owners.

    Nothing when they are an owner; the claim that makes them the first one
    when nobody has owned the name; a refusal otherwise.
    """
    person = _person(person)
    scope = scope_of(name)
    if not owned(conn, scope):
        return [claim(scope, person, sealed_at)]
    if any(o["owner"] == person for o in owners(conn, scope, valid_at=sealed_at)):
        return []
    raise _not_an_owner(conn, scope, person, valid_at=sealed_at,
                        doing="a version sealed", where=name, dated=False)


def first(conn, scope, *, actor_id, valid_from=None, recorded_at=None):
    """Make `actor_id` the first owner of a name nobody owns, without sealing.

    For setting a kernel up, where a name's versions arrive registered rather
    than sealed (`@uniti` in a business's kernel): otherwise the next person
    to seal under it would take it. Saying it again writes nothing.
    """
    actor_id = _person(actor_id)
    valid_from = _utc(valid_from or datetime.now(timezone.utc))
    if owned(conn, scope):
        if any(o["owner"] == actor_id for o in owners(conn, scope, valid_at=valid_from)):
            return {"name": scope, "owner": actor_id, "intent_id": None}
        raise _not_an_owner(conn, scope, actor_id, valid_at=valid_from,
                            doing="a first owner named", where=scope)
    intent_id, (assertion,) = state(
        conn, [claim(scope, actor_id, valid_from)], actor_id=actor_id,
        action_name="claim_name", ontology_version=LABEL,
        note=f"{actor_id} owns {scope}", recorded_at=recorded_at)
    return {"name": scope, "owner": actor_id, "since": valid_from,
            "intent_id": intent_id, "assertion": assertion}


def add(conn, scope, person, *, actor_id, valid_from=None, recorded_at=None):
    """Make `person` an owner of `scope` from `valid_from`. Adding somebody
    who already is one writes nothing."""
    person, actor_id = _person(person), _person(actor_id)
    valid_from = _utc(valid_from or datetime.now(timezone.utc))
    current = owners(conn, scope, valid_at=valid_from)
    if not any(o["owner"] == actor_id for o in current):
        raise _not_an_owner(conn, scope, actor_id, valid_at=valid_from,
                            doing="an owner added", where=scope)
    if any(o["owner"] == person for o in current):
        return {"name": scope, "owner": person, "intent_id": None}
    intent_id, (assertion,) = state(
        conn, [(subject(scope, person), OWNS, OWNER, valid_from, SOURCE)],
        actor_id=actor_id, action_name="add_owner", ontology_version=LABEL,
        note=f"{person} owns {scope}", recorded_at=recorded_at)
    return {"name": scope, "owner": person, "since": valid_from,
            "intent_id": intent_id, "assertion": assertion}


def remove(conn, scope, person, *, actor_id, valid_from=None, recorded_at=None):
    """`person` stops owning `scope` from `valid_from`. The versions they
    sealed are unchanged."""
    person, actor_id = _person(person), _person(actor_id)
    valid_from = _utc(valid_from or datetime.now(timezone.utc))
    current = owners(conn, scope, valid_at=valid_from)
    if not any(o["owner"] == actor_id for o in current):
        raise _not_an_owner(conn, scope, actor_id, valid_at=valid_from,
                            doing="an owner removed", where=scope)
    if not any(o["owner"] == person for o in current):
        raise OwnerError(
            "not_an_owner",
            where=scope,
            expected=f"an owner of {scope} to remove",
            got=f"{person}, who is not one on {valid_from.date()}",
            repairs=[Repair("name an owner", options=[o["owner"] for o in current])],
        )
    if len(current) == 1:
        raise OwnerError(
            "last_owner",
            where=scope,
            expected=f"another owner of {scope} left behind",
            got=f"{person}, its only owner",
            repairs=[Repair("add the person who takes it over first, then remove "
                            "yourself")],
        )
    intent_id, (assertion,) = state(
        conn, [(subject(scope, person), OWNS, REMOVED, valid_from, SOURCE)],
        actor_id=actor_id, action_name="remove_owner", ontology_version=LABEL,
        note=f"{person} no longer owns {scope}", recorded_at=recorded_at)
    return {"name": scope, "owner": person, "since": valid_from,
            "intent_id": intent_id, "assertion": assertion}

"""business — whose kernel this is, and which applications it has installed.

One business, one kernel (DESIGN_NOTES.md §15.5). The kernel says which
business it belongs to once, when it is set up, and from then on an
application of another business is refused at its door: it cannot be sealed,
registered or installed here.

The person who declares it becomes the first owner of the business's name,
`@kemahceria`, in this kernel (components/owners): an application is sealed
under its business's name, by that name's owners.

Sealing and installing are two decisions made by two people (§15.3). Sealing
says a composition is right; that is the composer's, with the owner's
agreement. Installing says the business's staff record through it from a given
day; that is the process owner's alone. So installing is a statement in the
kernel like any other:

    subject     uniti:application/@kemahceria/rental
    predicate   uniti:application_version
    value       v1, valid from the day it is in use

Moving to v2 is a later statement with a later day, and v1 stays in the log as
what was used before. Stopping is a statement too, valid from the day it
stops, saying `stopped`. A wrong installation is withdrawn like any wrong
statement. Which application was in use in August is then read the way every
other number is, at two clocks.

Installing also brings the vocabulary of every version the application pins
into the kernel (`seal.register`), so a log never holds statements under words
it has no record of learning.

A form writes only through an application installed for the day it records
(`require_installed`). Reading through any other version stays open: that is
how an owner looks at v2 against real records before moving to it.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from components import owners  # noqa: E402
from components.modules.store import APPLICATION, BUSINESS  # noqa: E402
from components.refusal import Refusal, Repair  # noqa: E402
from resolve import resolve_single  # noqa: E402
from seal import _utc, register  # noqa: E402

# The kernel itself, as the subject of the one statement of whose it is.
KERNEL = "uniti:kernel"
BELONGS_TO = "uniti:kernel_business"

# An installed application, and the version of it in use.
APPLICATION_PREFIX = "uniti:application/"
IN_USE = "uniti:application_version"
STOPPED = "stopped"

# What the kernel's bookkeeping is stated under: it belongs to no map.
LABEL = "kernel"

# A person said so: the owner who set the kernel up, or who installed.
SOURCE = "human_stated"


class BusinessError(Refusal):
    """The business's kernel refuses what is not its own. Nothing was written."""

    gate = "the business kernel"


def _known(conn):
    return owners.known(conn)


def _state(conn, *, actor_id, action_name, ontology_version, note, subject, predicate,
           value, valid_from=None, reason_code=None, recorded_at=None, also=()):
    """One intent stating one value, and any statements `also` carries."""
    intent_id, assertion_ids = owners.state(
        conn, [(subject, predicate, value, valid_from, SOURCE), *also],
        actor_id=actor_id, action_name=action_name, ontology_version=ontology_version,
        note=note, reason_code=reason_code, recorded_at=recorded_at)
    return intent_id, assertion_ids[0]


# ---------------------------------------------------------------- the kernel

def owner(conn):
    """The business this kernel belongs to, or None when it has not said."""
    known = _known(conn)
    if KERNEL not in known or BELONGS_TO not in known:
        return None
    with conn.cursor() as cur:
        cur.execute(
            "SELECT value_literal FROM assertion WHERE subject_id = %s "
            "AND predicate_id = %s AND value_literal IS NOT NULL ORDER BY seq LIMIT 1",
            (known[KERNEL], known[BELONGS_TO]))
        row = cur.fetchone()
    return row[0] if row else None


def declare(conn, business, *, actor_id, recorded_at=None):
    """Say once which business this kernel belongs to.

    Saying it again for the same business writes nothing. Saying it for
    another is refused: a kernel's records are one business's, and a second
    owner would make them two businesses' without moving one of them.
    """
    if not BUSINESS.match(str(business or "")):
        raise BusinessError(
            "not_a_business_name",
            where="the kernel",
            expected="a business named by a lower-case word, as an application's "
                     "manifest names it",
            got=f"{business!r}",
            repairs=[Repair("name the business in lower case, with - or _ between words")],
        )
    current = owner(conn)
    if current == business:
        return {"business": business, "intent_id": None}
    if current is not None:
        raise BusinessError(
            "kernel_owned",
            where="the kernel",
            expected=f"a kernel that belongs to no business yet, or to {business}",
            got=f"one that belongs to {current}",
            repairs=[Repair(f"give {business} a kernel of its own"),
                     Repair("or work in this kernel as the business it belongs to",
                            options=[current])],
        )
    # Whoever sets the kernel up owns the business's name in it, unless
    # somebody already does: its applications are sealed under that name.
    scope = "@" + business
    also = [] if owners.owned(conn, scope) else [
        owners.claim(scope, actor_id, recorded_at or datetime.now(timezone.utc))]
    intent_id, _ = _state(
        conn, actor_id=actor_id, action_name="declare_business", ontology_version=LABEL,
        note=f"this kernel belongs to {business}", subject=KERNEL, predicate=BELONGS_TO,
        value=business, recorded_at=recorded_at, also=also)
    return {"business": business, "intent_id": intent_id,
            "owner": actor_id if also else None}


def require_own(conn, store, name):
    """Refuse an application that is not this kernel's business's.

    Anything other than an application passes: modules, the library and core
    are shared, and any business may hold their vocabulary.
    """
    if store.kind(name) != APPLICATION:
        return
    belongs = store.business(name)
    current = owner(conn)
    if current is None:
        raise BusinessError(
            "kernel_not_declared",
            where="the kernel",
            expected=f"a kernel that says it belongs to {belongs}, as {name} does",
            got="one that has not said whose it is",
            repairs=[Repair("declare which business this kernel belongs to",
                            options=[belongs])],
        )
    if current != belongs:
        raise BusinessError(
            "wrong_business",
            where=name,
            expected=f"an application of {current}, whose kernel this is",
            got=f"an application of {belongs}",
            repairs=[Repair(f"use {belongs}'s own kernel for it"),
                     Repair(f"or compose an application of {current}'s own from the "
                            "same modules")],
        )


# ---------------------------------------------------------------- installing

def _application(store, name):
    if store.kind(name) != APPLICATION:
        raise BusinessError(
            "not_an_application",
            where=name,
            expected="an application: a manifest saying `kind: application`",
            got=f"a {store.kind(name)}, which is shared and installed by nobody",
            repairs=[Repair("install an application that pins it",
                            options=[n for n in store.names()
                                     if store.kind(n) == APPLICATION])],
        )


def install(conn, store, name, version, *, actor_id, valid_from, recorded_at=None):
    """Use this version of the application from `valid_from` on.

    Every version it pins is registered into the kernel first, in the order
    they depend on each other, so the words it records under are words the log
    has learned.
    """
    _application(store, name)
    require_own(conn, store, name)
    valid_from = _utc(valid_from)
    registered = []
    for pin in store.closure(name, version):
        out = register(conn, store.path(*pin), actor_id=actor_id, store=store,
                       recorded_at=recorded_at)
        if out["minted"]:
            registered.append(f"{pin[0]}@{pin[1]}")
    intent_id, assertion_id = _state(
        conn, actor_id=actor_id, action_name="install_application",
        ontology_version=f"{name}@{version}",
        reason_code=store.purpose(name),
        note=f"installed {name}@{version}", subject=APPLICATION_PREFIX + name,
        predicate=IN_USE, value=version, valid_from=valid_from, recorded_at=recorded_at)
    return {"name": name, "version": version, "since": valid_from,
            "intent_id": intent_id, "assertion": assertion_id, "registered": registered}


def stop(conn, store, name, *, actor_id, valid_from, recorded_at=None):
    """Stop using the application from `valid_from` on. Its records stay."""
    _application(store, name)
    require_own(conn, store, name)
    valid_from = _utc(valid_from)
    now = datetime.now(timezone.utc)
    if name not in {i["name"] for i in installed(conn, valid_at=valid_from, as_of=now)}:
        raise BusinessError(
            "not_installed",
            where=name,
            expected=f"an application in use on {valid_from.date()}",
            got="one that is not",
            repairs=[Repair("name an application in use that day",
                            options=[i["name"] for i in
                                     installed(conn, valid_at=valid_from, as_of=now)])],
        )
    intent_id, assertion_id = _state(
        conn, actor_id=actor_id, action_name="stop_application",
        ontology_version=LABEL, reason_code=store.purpose(name),
        note=f"stopped using {name}", subject=APPLICATION_PREFIX + name,
        predicate=IN_USE, value=STOPPED, valid_from=valid_from, recorded_at=recorded_at)
    return {"name": name, "since": valid_from, "intent_id": intent_id,
            "assertion": assertion_id}


def installed(conn, *, valid_at, as_of):
    """Every application in use on `valid_at`, as the log stood at `as_of`.

    Each with the version in use and the day that version came into use.
    """
    known = _known(conn)
    if IN_USE not in known:
        return []
    uri_of = {entity_id: uri for uri, entity_id in known.items()}
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT subject_id FROM assertion WHERE predicate_id = %s",
                    (known[IN_USE],))
        subjects = [row[0] for row in cur.fetchall()]
    out = []
    for subject_id in subjects:
        row = resolve_single(conn, subject_id=subject_id, predicate_id=known[IN_USE],
                             valid_at=_utc(valid_at), as_of=_utc(as_of))
        if row is None or row["value_literal"] == STOPPED:
            continue
        out.append({"name": uri_of[subject_id][len(APPLICATION_PREFIX):],
                    "version": row["value_literal"], "since": row["valid_from"],
                    "assertion": row["id"]})
    return sorted(out, key=lambda i: i["name"])


def require_installed(conn, name, version, *, valid_at, as_of=None):
    """Refuse a write through a version the business does not use that day."""
    as_of = as_of or datetime.now(timezone.utc)
    in_use = installed(conn, valid_at=valid_at, as_of=as_of)
    if any(i["name"] == name and i["version"] == version for i in in_use):
        return
    day = _utc(valid_at).date()
    same = next((i for i in in_use if i["name"] == name), None)
    got = (f"{name}@{version}, while {same['version']} is the version in use that day"
           if same else f"{name}@{version}, which is not installed for that day")
    raise BusinessError(
        "not_installed",
        where=f"{name}@{version}",
        expected=f"an application the business uses on {day}",
        got=got,
        repairs=[Repair("record through the application in use that day",
                        options=[f"{i['name']}@{i['version']}" for i in in_use]),
                 Repair("or ask the business's owner to install this version from "
                        "that day", options=[f"{name}@{version}"])],
    )


def summary(conn, *, valid_at=None, as_of=None):
    """Whose kernel this is and what it uses, for a page to say at the top."""
    now = datetime.now(timezone.utc)
    return {"business": owner(conn),
            "installed": installed(conn, valid_at=valid_at or now, as_of=as_of or now)}

"""check — every refusal an application raises as it stands.

The gates refuse one thing at a time, because each of them is in the middle of
doing something: `seal` stops at the first problem, and so does the compiler.
That is right for a gate and wrong for a page. Somebody looking at a map wants
to know whether it holds, and if not, everything that is in the way — not the
first thing, then the second thing after they fix the first.

So this runs the same readers over the same sealed content and collects what
they say. It decides nothing of its own: every refusal here came out of
`plan_for` and the emitter after it — the compiler's own reading, stopping short
of the database. A map this calls clean is a map that compiles. It once stopped
at the plan, and called maps clean whose expressions the emitter then refused.

Nothing is written, nothing is sealed, and the operational store is not
touched. It is a read, and it is the read Studio makes while somebody types.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from compile import emit, emit_entities, plan_for, tables  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from generate import read_map  # noqa: E402


def compiled(map_):
    """Each table the map can fill, as (class, plan, refusal): one of the two
    is None. Everything the compiler does before it opens a connection."""
    for class_name in tables(map_):
        try:
            plan_ = plan_for(map_, class_name)
            (emit if plan_["shape"] == "grouped" else emit_entities)(map_, plan_)
        except Refusal as exc:
            yield class_name, None, exc
            continue
        yield class_name, plan_, None


def check(store, name, version, *, map_=None):
    """Whether this application holds, and every refusal in the way if not.

    `map_` is for a map that is not in the store: the hypothetical a fit report
    builds, or later a draft somebody is still editing. Without one the version
    is read from the store as usual.
    """
    out = {"name": name, "version": version, "tables": [], "refusals": [],
           "clean": True}

    if map_ is None:
        try:
            map_ = read_map(store.path(name, version), store)
        except Refusal as exc:
            # The map itself cannot be read, so there is nothing below this to
            # check. One refusal, and it is the only true one.
            return {**out, "clean": False, "refusals": [exc.as_dict()]}

    for class_name, plan_, exc in compiled(map_):
        if exc is not None:
            out["clean"] = False
            out["refusals"].append({**exc.as_dict(), "class": class_name})
            out["tables"].append({"class": class_name, "holds": False,
                                  "shape": None, "columns": 0, "unfilled": [],
                                  "awaiting": {}})
            continue
        # A column no rule reaches is not a refusal — it compiles, as nulls.
        # It is said here anyway, because it is the same question asked one
        # step later: the table holds, and this part of it says nothing.
        out["tables"].append({
            "class": class_name,
            "holds": True,
            "shape": plan_["shape"],
            "columns": len(plan_["columns"]),
            "unfilled": [col["name"] for col in plan_["columns"]
                         if col["kind"] == "unfilled"],
            # Nor is a column the compiler cannot compute yet: the graph is
            # sound, the table holds, and this part of it waits — with why.
            "awaiting": {col["name"]: col["awaiting"] for col in plan_["columns"]
                         if col.get("awaiting")},
        })
    return out


__all__ = ["check", "compiled"]

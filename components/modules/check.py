"""check — every refusal an application raises as it stands.

The gates refuse one thing at a time, because each of them is in the middle of
doing something: `seal` stops at the first problem, and so does the compiler.
That is right for a gate and wrong for a page. Somebody looking at a map wants
to know whether it holds, and if not, everything that is in the way — not the
first thing, then the second thing after they fix the first.

So this runs the same readers over the same sealed content and collects what
they say. It decides nothing of its own: every refusal here came out of
`plan_for`, which is the function the compiler calls before it emits a line of
SQL. A map this calls clean is a map that compiles.

Nothing is written, nothing is sealed, and the operational store is not
touched. It is a read, and it is the read Studio makes while somebody types.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from compile import plan_for, tables  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from generate import read_map  # noqa: E402


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

    for class_name in tables(map_):
        try:
            plan_ = plan_for(map_, class_name)
        except Refusal as exc:
            out["clean"] = False
            out["refusals"].append({**exc.as_dict(), "class": class_name})
            out["tables"].append({"class": class_name, "holds": False,
                                  "shape": None, "columns": 0, "unfilled": []})
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
        })
    return out


__all__ = ["check"]

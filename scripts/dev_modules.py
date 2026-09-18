"""Seal the demonstration modules, in order, into a store root of their own.

Four modules, sealed as they would have been over time:

    @demo/catalog@v1        what a small bakery buys and keeps
    @demo/inventory@v1      movements of it, pinning the catalog's v1
    @demo/catalog@v2        one slot renamed, a reorder level added
    @demo/inventory@v2      moves its pin to the catalog's v2
    @demo/stock@v1          the application, written against @demo/inventory's
                            own names — and so unable to survive replacing it
    @demo/catalog@v3        moves to core v2; an Ingredient is a Resource
    @demo/inventory@v3      moves to core v2; a StockMovement is a Flow
    @rival/stock-moves@v1   somebody else's inventory module, pinning core and
                            nothing else, sharing not one word with @demo's
    @demo/stock@v2          the application again, naming roles instead of names
    @demo/stock@v3          the same rules, byte for byte, pinned to @rival

The order is the point: when `@demo/catalog@v2` is sealed, `@demo/inventory@v1`
already exists and pins `@demo/catalog@v1`, and nothing about it changes. And
v1 of the application is kept rather than rewritten, so both ways of writing a
rule are in the store side by side and the difference can be read.

Every one of these modules declares `purpose: demonstration` in its manifest.
The content is made up, and `seal` carries that word onto the intent, so the
log says so on every row it wrote.

The root is emptied first. `@uniti/core` is not copied: it is real content in
`packages/`, found through the store's second root.

Run: UNITI_DSN=... .venv/Scripts/python.exe scripts/dev_modules.py build/dev/packages
"""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from components.modules.store import MANIFEST, Store  # noqa: E402
from perform import connect  # noqa: E402
from seal import register, seal  # noqa: E402

FIXTURES = ROOT / "tests" / "modules" / "fixtures"

CATALOG = "@demo/catalog"
INVENTORY = "@demo/inventory"
RIVAL = "@rival/stock-moves"
STOCK = "@demo/stock"
CORE = "@uniti/core"

# Sealed now, one after another: a seal records when it happened, and each of
# these pins versions sealed before it. What each version says about the world
# is dated by its own `valid_from`.
SEQUENCE = [
    (CATALOG, "v1"),
    (INVENTORY, "v1"),
    (CATALOG, "v2"),
    (INVENTORY, "v2"),
    (STOCK, "v1"),
    (CATALOG, "v3"),
    (INVENTORY, "v3"),
    (RIVAL, "v1"),
    (STOCK, "v2"),
    (STOCK, "v3"),
]

# The application: the version the compiler and the generator read as one map.
APPLICATION = (STOCK, "v2")

# The same application, pinned to the rival's module. Everything below
# `imports` is identical to APPLICATION's, which is what makes comparing the
# two worth anything.
SWAPPED = (STOCK, "v3")

# Both core versions go into the log: the first five modules pin v1 and the
# rest pin v2, and a log that held only one of them would be missing the
# vocabulary half the store was sealed against.
CORE_VERSIONS = ("v1", "v2")


def build(conn, root, *, until=None, register_core=True):
    """Seal the sequence into `root`, stopping after `until` (a name@version) if given."""
    root = Path(root)
    if root.exists():
        shutil.rmtree(root)
    for name in {name for name, _ in SEQUENCE}:
        target = root / name
        target.mkdir(parents=True)
        shutil.copyfile(FIXTURES / name / MANIFEST, target / MANIFEST)

    store = Store([root, ROOT / "packages"])
    if register_core:
        for version in CORE_VERSIONS:
            register(conn, store.path(CORE, version), actor_id="dev", store=store)

    sealed = []
    for name, version in SEQUENCE:
        out = seal(conn, FIXTURES / name / f"{version}.draft.yaml", actor_id="dev",
                   into=store.directory(name), store=store)
        assert out["version"] == version, (name, out["version"], version)
        sealed.append(f"{name}@{version}")
        if until == sealed[-1]:
            break
    return store, sealed


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    with connect(os.environ.get("UNITI_DSN"), connect_timeout=3) as conn:
        _, sealed = build(conn, argv[0])
    print("sealed " + ", ".join(sealed))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

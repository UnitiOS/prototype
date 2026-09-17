"""Seal the fixture modules, in order, into a store root of their own.

Two modules, two versions each, sealed as they would be over time:

    @example/things@v1      a thing has a code and a label
    @example/movements@v1   pins things@v1
    @example/things@v2      the label is renamed, a size and a group are added
    @example/movements@v2   moves its pin to things@v2

The order is the point: when things@v2 is sealed, movements@v1 already exists
and pins things@v1, and nothing about it changes.

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
# Sealed now, one after another: a seal records when it happened, and each of
# these pins versions sealed before it. What each version says about the world
# is dated by its own `valid_from`.
SEQUENCE = [
    ("@example/things", "v1"),
    ("@example/movements", "v1"),
    ("@example/things", "v2"),
    ("@example/movements", "v2"),
]


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
        register(conn, store.path("@uniti/core", "v1"), actor_id="dev", store=store)

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

"""store — modules as directories of sealed versions, and imports pinned to one.

A module is a directory named for it, `@scope/name`, under one of the store's
roots:

    @scope/name/
        package.yaml      name, title, description — nothing that changes meaning
        v1.yaml  v1.txt   sealed versions and their transcripts, written by `seal`
        v2.yaml  v2.txt
        draft.yaml        optional: the next version, not yet sealed

It is the version store `seal` already writes, with a manifest beside it, so
`resolve_version` reads a module's history exactly as it reads any other.

An import names one sealed version, never a module in general:

    imports:
      - linkml:types
      - "@uniti/core@v1"

A version is never rewritten, so what `@uniti/core@v1` means today is what it
meant when it was imported. A module that wants `v2` says so in a version of
its own. An import without a version, of a module the store does not hold, or
of a version not yet sealed, is refused by name.

The roots come from `UNITI_PACKAGES`, a path list in the platform's separator,
or default to `packages/` at the repository root. The first root holding a
module wins, so a development root can sit beside the real one.
"""

import os
import re
import sys
from pathlib import Path

import yaml
from linkml_runtime.utils.schemaview import SchemaView, load_schema_wrap

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components"))

from components.refusal import Refusal, Repair  # noqa: E402
from ontology.resolve import load_versions  # noqa: E402

MANIFEST = "package.yaml"
NAME = re.compile(r"^@[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*$")
TAIL = re.compile(r"@[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*@v[1-9][0-9]*$")
PIN = re.compile(r"^(?P<name>@[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*)@(?P<version>v[1-9][0-9]*)$")


class ModuleError(Refusal, ValueError):
    """A module, a version, or an import that the store cannot stand behind."""

    gate = "the module store"


class Store:
    def __init__(self, roots):
        self.roots = [Path(r).resolve() for r in roots]

    @classmethod
    def from_env(cls):
        raw = os.environ.get("UNITI_PACKAGES")
        roots = [p for p in raw.split(os.pathsep) if p] if raw else [ROOT / "packages"]
        return cls(roots)

    # ------------------------------------------------------------ modules

    def names(self):
        """Every module the store holds, each once, in name order."""
        found = set()
        for root in self.roots:
            for manifest in root.glob(f"@*/*/{MANIFEST}"):
                name = f"{manifest.parent.parent.name}/{manifest.parent.name}"
                if NAME.match(name):
                    found.add(name)
        return sorted(found)

    def directory(self, name):
        if not NAME.match(name or ""):
            raise ModuleError(
                "not_a_module_name",
                where="the store",
                expected="a module name of the form @scope/name",
                got=f"{name!r}",
                repairs=[Repair("name a module the store holds", options=self.names())],
            )
        scope, local = name.split("/")
        for root in self.roots:
            candidate = root / scope / local
            if (candidate / MANIFEST).is_file():
                return candidate
        raise ModuleError(
            "no_such_module",
            where="the store",
            expected=f"a directory {name} holding a {MANIFEST}",
            got="no such directory under any root",
            repairs=[
                Repair("name a module the store holds", options=self.names()),
                Repair(
                    "point UNITI_PACKAGES at the root that holds it",
                    where=os.pathsep.join(str(root) for root in self.roots),
                ),
            ],
        )

    def place(self, name):
        """Where a module of this name lives, or would live if it existed.

        The first root, because that is the one the store reads first: a module
        started there is the one found afterwards, and a development root put
        ahead of the real one is how a draft stays out of it.
        """
        try:
            return self.directory(name)
        except ModuleError as exc:
            if exc.code != "no_such_module":
                raise
            scope, local = name.split("/")
            return self.roots[0] / scope / local

    def manifest(self, name):
        data = yaml.safe_load((self.directory(name) / MANIFEST).read_text(encoding="utf-8")) or {}
        if data.get("name") != name:
            raise ModuleError(
                "manifest_disagrees",
                where=f"{name}/{MANIFEST}",
                expected=f"name: {name}, matching the directory it sits in",
                got=f"{data.get('name')!r}",
                repairs=[Repair(f"set `name: {name}`", where=f"{name}/{MANIFEST}")],
            )
        return data

    def purpose(self, name):
        """What the content of this module is for, when its manifest says.

        A manifest that declares one is saying it about every version under it:
        `demonstration` means the content is made up and is here so that the
        mechanisms have something to run on. It is carried into the kernel on
        the intent that seals or registers a version, so a reader of the log
        knows without holding the store.
        """
        return self.manifest(name).get("purpose")

    def versions(self, name):
        return load_versions(self.directory(name))

    def path(self, name, version):
        held = self.versions(name)
        for version_held in held:
            if version_held["version"] == version:
                return version_held["path"]
        raise ModuleError(
            "no_such_version",
            where=name,
            expected=f"a sealed version {version}",
            got=f"{len(held)} sealed here" if held else "nothing sealed here yet",
            repairs=[
                Repair(
                    f"pin a version {name} has sealed",
                    options=[v["version"] for v in held],
                )
            ],
        )

    def module_of(self, directory):
        """The module a directory is, or None when it is not one of the store's."""
        directory = Path(directory).resolve()
        name = f"{directory.parent.name}/{directory.name}"
        try:
            return name if self.directory(name) == directory else None
        except ModuleError:
            return None

    # ------------------------------------------------------------ imports

    def pinned(self, imp):
        """(name, version) for a module import, None for a LinkML one.

        Anything else is refused: a module import without a version, and an
        import that is neither a module nor LinkML's own.
        """
        if imp.startswith("linkml:"):
            return None
        match = PIN.match(imp)
        if match:
            return match["name"], match["version"]
        if NAME.match(imp):
            raise ModuleError(
                "import_not_pinned",
                where="imports",
                expected=f"one sealed version of {imp}, such as {imp}@v1",
                got=f"{imp!r}, which names the module and no version",
                repairs=[
                    Repair(
                        f"pin one version of {imp}",
                        options=[f"{imp}@{v}" for v in self._held(imp)],
                    )
                ],
            )
        raise ModuleError(
            "import_not_understood",
            where="imports",
            expected="`@scope/name@vN` or a `linkml:` import",
            got=f"{imp!r}",
            repairs=[
                Repair("import a sealed version this store holds",
                       options=[f"{n}@{v}" for n in self.names() for v in self._held(n)]),
                Repair("import one of LinkML's own schemas, which need no pin",
                       options=["linkml:types"]),
            ],
        )

    def _held(self, name):
        """The versions of a module, or nothing when the store has no such module.

        Only ever asked while assembling a repair, and a repair that cannot be
        computed is an empty list rather than a second refusal thrown from
        inside the first one.
        """
        try:
            return [v["version"] for v in self.versions(name)]
        except ModuleError:
            return []

    def imports(self, document):
        """The pinned imports a schema document declares, each checked to exist."""
        pins = []
        for imp in document.get("imports") or []:
            pin = self.pinned(str(imp))
            if pin is not None:
                self.path(*pin)
                pins.append(pin)
        return pins

    def document(self, name, version):
        return yaml.safe_load(self.path(name, version).read_text(encoding="utf-8")) or {}

    def closure(self, name, version):
        """This version and everything it imports, dependencies first, each once."""
        order, seen = [], set()

        def visit(pin, trail):
            if pin in trail:
                ring = [f"{n}@{v}" for n, v in trail + [pin]]
                raise ModuleError(
                    "import_cycle",
                    where=f"{pin[0]}@{pin[1]}",
                    expected="imports that reach an end",
                    got=" -> ".join(ring),
                    repairs=[
                        Repair(
                            "drop one import in the ring, or move what both sides "
                            "need into a module below them",
                            options=ring,
                        )
                    ],
                )
            if pin in seen:
                return
            for dependency in self.imports(self.document(*pin)):
                visit(dependency, trail + [pin])
            seen.add(pin)
            order.append(pin)

        visit((name, version), [])
        return order

    def view(self, source):
        """A SchemaView whose module imports resolve through this store.

        `source` is a path or the text of a schema. The imports are resolved
        here, eagerly, so a schema that names something the store does not
        hold fails now rather than at whichever later read first needs it.
        """
        text = Path(source).read_text(encoding="utf-8") if _is_file(source) else str(source)
        # The schema's own imports are held to the exact form; only the ones
        # SchemaView rewrites on its way down the closure are read by their tail.
        self.imports(yaml.safe_load(text) or {})
        view = ModuleView(text, store=self)
        view.imports_closure()
        return view


def _is_file(source):
    try:
        return len(str(source)) < 1024 and "\n" not in str(source) and Path(source).is_file()
    except OSError:
        return False


class ModuleView(SchemaView):
    def __init__(self, schema, store, **kwargs):
        self.store = store
        super().__init__(schema, **kwargs)

    def load_import(self, imp, from_schema=None):
        # SchemaView treats an import it cannot read as a CURIE as a path, and
        # joins it to the directory of the schema that imported it — so a pin
        # made inside an imported module arrives as `@scope/@other/name@v1`.
        # The pin is the tail; what was prepended is not part of it.
        tail = TAIL.search(imp.replace("\\", "/"))
        if tail and not imp.startswith("linkml:"):
            imp = tail.group(0)
        pin = self.store.pinned(imp)
        if pin is None:
            return super().load_import(imp, from_schema)
        return load_schema_wrap(str(self.store.path(*pin)))

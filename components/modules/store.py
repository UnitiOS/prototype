"""store — modules as directories of sealed versions, and imports pinned to one.

A module is a directory named for it, `@scope/name`, under one of the store's
roots:

    @scope/name/
        package.yaml      name, title, description, kind — nothing that changes
                          meaning
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

A manifest may say which of four kinds the module is (DESIGN_NOTES.md §15.2):

    kind: core          the roles, kept by Uniti's own keepers
    kind: library       what almost every domain uses, kept by the same people
    kind: module        one business function, by whoever wrote it — the
                        default, so a manifest that says nothing is one
    kind: application   one business's composition, private to it:
                        business: <the business it belongs to>, and named
                        under it: @<business>/...

The kind changes no meaning. It says who owns a module and who may use it: an
application belongs to one business, is pinned by nothing, and is installed
only into that business's kernel (components/business).

Modules are read together by the store, never by LinkML merging their names
(components/modules/compose.py): a pinned module's names are qualified by its
tag, `penyewaan__Rental`, with the URIs its plain names meant, and core's and
the library's names stay plain for everybody. `composition` is the one reader
of a closure as composed, and `view` reads through it.

The roots come from `UNITI_PACKAGES`, a path list in the platform's separator,
or default to `packages/` at the repository root. The first root holding a
module wins, so a development root can sit beside the real one.
"""

import copy
import os
import re
import sys
from pathlib import Path

import yaml
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components"))

from components.modules import compose  # noqa: E402
from components.refusal import Refusal, Repair  # noqa: E402
from ontology.resolve import load_versions  # noqa: E402

MANIFEST = "package.yaml"
NAME = re.compile(r"^@[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*$")
TAIL = re.compile(r"@[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*@v[1-9][0-9]*$")
PIN = re.compile(r"^(?P<name>@[a-z0-9][a-z0-9_-]*/[a-z0-9][a-z0-9_-]*)@(?P<version>v[1-9][0-9]*)$")
BUSINESS = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

KINDS = ("core", "library", "module", "application")
APPLICATION = "application"
# What every module shares, kept by Uniti's own keepers: its names are the
# reserved ones, plain in every composition and declared by nothing else.
SHARED = ("core", "library")


class ModuleError(Refusal, ValueError):
    """A module, a version, or an import that the store cannot stand behind."""

    gate = "the module store"


def kind_of(name, manifest):
    """Which of the four kinds a manifest says its module is; `module` when it
    does not say.

    An application names the business it belongs to and nothing else may:
    a business on a module would read as a claim of ownership the module
    does not make. It is named under that business, `@kemahceria/rental`, so
    the owners of the business's name are the people who seal it.
    """
    kind = manifest.get("kind") or "module"
    where = f"{name}/{MANIFEST}"
    if kind not in KINDS:
        raise ModuleError(
            "kind_not_understood",
            where=where,
            expected=f"kind: one of {', '.join(KINDS)}",
            got=f"{kind!r}",
            repairs=[Repair("say which kind this module is", options=list(KINDS))],
        )
    business = manifest.get("business")
    if kind == APPLICATION and not BUSINESS.match(str(business or "")):
        raise ModuleError(
            "application_without_business",
            where=where,
            expected="business: the one business this application belongs to, "
                     "a lower-case word",
            got=f"{business!r}" if business else "none",
            repairs=[Repair("name the business", where=where)],
        )
    if kind == APPLICATION and name.split("/")[0] != "@" + business:
        raise ModuleError(
            "name_not_the_business",
            where=where,
            expected=f"an application named under its business, @{business}/...",
            got=name,
            repairs=[Repair("name the application under its business",
                            options=[f"@{business}/{name.split('/')[-1]}"])],
        )
    if kind != APPLICATION and business is not None:
        raise ModuleError(
            "business_on_a_module",
            where=where,
            expected=f"no business: a {kind} belongs to no one business",
            got=f"business: {business!r}",
            repairs=[Repair("drop the business", where=where),
                     Repair("or make it the application it is", options=[APPLICATION])],
        )
    return kind


class Store:
    def __init__(self, roots):
        self.roots = [Path(r).resolve() for r in roots]
        # A sealed version never changes, so neither does how it composes.
        self._composed, self._declared = {}, {}

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

    def kind(self, name):
        """Which of the four kinds this module is; `module` when it does not say."""
        return kind_of(name, self.manifest(name))

    def business(self, name):
        """The business an application belongs to, None for any other kind."""
        return self.manifest(name).get("business") if self.kind(name) == APPLICATION else None

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
        """The pinned imports a schema document declares, each checked to exist.

        An application is never one of them: it is one business's own, and a
        module pinning it would carry that business into everyone who pins the
        module in turn.
        """
        pins = []
        for imp in document.get("imports") or []:
            pin = self.pinned(str(imp))
            if pin is not None:
                self.path(*pin)
                if self.kind(pin[0]) == APPLICATION:
                    raise ModuleError(
                        "pins_an_application",
                        where="imports",
                        expected="modules, the library or core: what is shared",
                        got=f"{imp}, the application of {self.business(pin[0])}",
                        repairs=[Repair(
                            "pin the modules that application pins, and declare "
                            "here what it adds",
                            options=[f"{n}@{v}" for n, v in
                                     self.imports(self.document(*pin))])],
                    )
                pins.append(pin)
        return pins

    def document(self, name, version):
        return copy.deepcopy(_parsed(self.path(name, version)))

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

    # ------------------------------------------------------------ composing

    def tag(self, name):
        """The tag this module's names are qualified with when it is pinned,
        or None for core and the library, whose names stay plain."""
        return None if self.kind(name) in SHARED else compose.tag_of(name)

    def reserved(self):
        """Every name core and the library declare, in any version.

        They are what modules share, so they are never qualified, and a module
        declaring one of them would be declaring somebody else's word.
        """
        out = set()
        for name in self.names():
            if self.kind(name) not in SHARED:
                continue
            for held in self.versions(name):
                document = self.document(name, held["version"])
                out |= {n for names in compose.declared(document).values() for n in names}
        return frozenset(out)

    def _rename(self, name):
        tag = self.tag(name)
        return (lambda n: str(n)) if tag is None else (lambda n: compose.qualified(tag, n))

    def _names(self, pin):
        """Every name a sealed version declares, as a composition calls it."""
        if pin not in self._declared:
            rename = self._rename(pin[0])
            self._declared[pin] = frozenset(
                rename(n) for names in compose.declared(self.document(*pin)).values()
                for n in names)
        return set(self._declared[pin])

    def composed(self, name, version):
        """This version as the modules that pin it read it: its own names
        qualified, every reference resolved through its own closure, every URI
        locked to the one its plain name meant."""
        key = (name, version)
        if key not in self._composed:
            document = self.document(name, version)
            if self.tag(name) is None:
                self._composed[key] = document
            else:
                known = set()
                for dep in self.closure(name, version)[:-1]:
                    known |= self._names(dep)
                rename = self._rename(name)
                own = [n for names in compose.declared(document).values() for n in names]
                self._composed[key] = compose.rewrite(
                    document, rename, compose.resolver(own, known, rename), lock=True)
        return copy.deepcopy(self._composed[key])

    def reached(self, document):
        """Every version a document's pins reach, dependencies first, each once."""
        order = []
        for pin in self.imports(document):
            for dep in self.closure(*pin):
                if dep not in order:
                    order.append(dep)
        return order

    def known(self, document):
        """Every name a document can see in what it pins, as composed."""
        out = set()
        for dep in self.reached(document):
            out |= self._names(dep)
        return out

    def composition(self, document, name=None, *, tags=True):
        """A document and everything it pins, read together: the one reader
        for every place that reads a closure.

        `[(pin, document)]`, dependencies first, each as `composed` gives it;
        then `(None, document)` — the document itself, its own names plain
        and each reference to a pinned name resolved by the one rule. `name`
        is the module the document belongs to, when there is one: its tag
        counts among the closure's, because whoever pins it reads them all.
        `tags=False` reads a closure whose tags collide anyway, for a reader
        that has to show what is there while `tag_taken` is asked about.
        """
        order = self.reached(document)
        if tags:
            self._tags_apart(order, name)
        known = set()
        for dep in order:
            known |= self._names(dep)
        own = [n for names in compose.declared(document).values() for n in names]
        root = compose.rewrite(document, lambda n: str(n), compose.resolver(own, known))
        # Facets last: each slot a module adds to another's class is carried
        # by that class, here and only in compositions that reach the module.
        return compose.attach([(dep, self.composed(*dep)) for dep in order]
                              + [(None, root)])

    def version_composition(self, name, version):
        """`composition` of a sealed version, its own entry carrying its pin."""
        out = self.composition(self.document(name, version), name)
        return out[:-1] + [((name, version), out[-1][1])]

    def _tags_apart(self, order, name=None):
        """No two modules in one closure share a tag: it is the whole of what
        tells their names apart."""
        held = {}
        for module in dict.fromkeys([n for n, _ in order] + ([name] if name else [])):
            try:
                tag = self.tag(module)
            except ModuleError:
                # The draft's own module, not started yet: it has no manifest
                # to say its kind, and is a module until it says otherwise.
                tag = compose.tag_of(module)
            if tag is None:
                continue
            if tag in held and held[tag] != module:
                raise ModuleError(
                    "tag_taken",
                    where=name or "imports",
                    expected=f"one module tagged `{tag}` in one closure, because "
                             f"the tag is what tells their names apart",
                    got=f"{held[tag]} and {module}",
                    repairs=[Repair("pin one of the two, not both",
                                    options=[held[tag], module])],
                )
            held[tag] = module

    def view(self, source):
        """A SchemaView whose module imports resolve through this store.

        `source` is a path or the text of a schema. The imports are resolved
        here, eagerly, so a schema that names something the store does not
        hold fails now rather than at whichever later read first needs it.
        The schema is read as composed: every pinned module under its
        qualified names, and the schema's own references to them resolved.
        """
        text = Path(source).read_text(encoding="utf-8") if _is_file(source) else str(source)
        document = yaml.safe_load(text) or {}
        # The schema's own imports are held to the exact form; only the ones
        # SchemaView rewrites on its way down the closure are read by their tail.
        self.imports(document)
        composition = self.composition(document)
        resolved = composition[-1][1]
        if resolved != document:
            text = yaml.safe_dump(resolved, sort_keys=False, allow_unicode=True)
        view = ModuleView(text, store=self)
        view.imports_closure()
        # A pinned module arrives through `load_import` as it reads alone; the
        # facets this closure adds to its classes are hung on them here, the
        # same ones the composition carries. A facet is always on a class of
        # something pinned: nothing pinned can see the schema's own.
        facets = compose.facets(composition)
        for class_name, slot, _pin in facets:
            held = view.get_class(class_name)
            if slot not in held.slots:
                held.slots.append(slot)
        if facets:
            view.set_modified()
        return view


# A sealed version's file, parsed once: reading a closure parses every
# document in it, and a composition reads closures often. Keyed by the file's
# size and time as well, so a file that does change is read again.
_PARSED = {}


def _parsed(path):
    stat = Path(path).stat()
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if key not in _PARSED:
        _PARSED[key] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return _PARSED[key]


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
        return yaml_loader.load(self.store.composed(*pin), SchemaDefinition)

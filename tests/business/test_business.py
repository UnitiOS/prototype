"""One business, one kernel: whose a kernel is, and what it has installed.

What has to hold (DESIGN_NOTES.md §15, archived/APLIKASI_USAHA.md):

    a kernel says once     it belongs to one business; saying so again for
    whose it is            the same one writes nothing, for another is refused
    an application is      its manifest says whose it is; nothing may pin it;
    one business's own     it is sealed, registered and installed only into
                           that business's kernel
    sealing is not         installing is a statement in the kernel, valid from
    installing             a day: the version in use is read at two clocks,
                           a later version replaces it from its own day, and
                           stopping leaves the history where it was
    staff record through   a form goes only through the version installed for
    what is installed      the day it records; reading any version stays open

Every test here starts from a kernel of its own, emptied, because what is
tested is a kernel that has not yet said whose it is. The module files are
built once: they are the same whichever kernel reads them, which is the point
of keeping them apart.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

import dev_modules  # noqa: E402
from components.api import application  # noqa: E402
from components.business import (  # noqa: E402
    BusinessError, declare, install, installed, owner, stop,
)
from components.modules.store import MANIFEST, ModuleError, Store  # noqa: E402
from seal import register, seal  # noqa: E402

DEMO = dev_modules.BUSINESS
STOCK, CATALOG = dev_modules.STOCK, dev_modules.CATALOG

# A kernel of its own, beside the one the rest of the run shares: these tests
# need one that has not been declared, and empty it again and again.
DSN = os.environ["UNITI_DSN"].rsplit("/", 1)[0] + "/uniti_check_business"
SCHEMA = (ROOT / "components" / "kernel" / "001_schema.sql").read_text(encoding="utf-8")


def _empty():
    parts = urlsplit(DSN)
    admin = urlunsplit((parts.scheme, parts.netloc, "/postgres", "", ""))
    with psycopg.connect(admin, autocommit=True, connect_timeout=2) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s",
                            ("uniti_check_business",)).fetchone():
            conn.execute('CREATE DATABASE "uniti_check_business"')
    with psycopg.connect(DSN, autocommit=True, connect_timeout=2) as conn:
        conn.execute(SCHEMA)


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    """The demonstration modules, sealed once. The kernel they were sealed into
    is emptied straight after; the files stay."""
    _empty()
    with psycopg.connect(DSN) as conn:
        built, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
        conn.commit()
    return built


@pytest.fixture
def kernel(store):
    """An empty kernel, belonging to nobody yet."""
    _empty()
    with psycopg.connect(DSN) as conn:
        yield conn
        conn.rollback()


def test_a_kernel_says_once_whose_it_is(kernel):
    assert owner(kernel) is None
    first = declare(kernel, DEMO, actor_id="owner")
    assert first["intent_id"] is not None and owner(kernel) == DEMO
    assert declare(kernel, DEMO, actor_id="owner")["intent_id"] is None

    with pytest.raises(BusinessError) as refused:
        declare(kernel, "another", actor_id="owner")
    assert refused.value.code == "kernel_owned"
    assert refused.value.as_dict()["repairs"][1]["options"] == [DEMO]
    assert owner(kernel) == DEMO

    with pytest.raises(BusinessError) as refused:
        declare(kernel, "Kemah Ceria", actor_id="owner")
    assert refused.value.code == "not_a_business_name"


def test_a_manifest_says_which_kind_and_only_an_application_whose(store, tmp_path):
    assert store.kind("@uniti/core") == "core"
    assert store.kind("@uniti/party") == "library"
    assert store.kind(CATALOG) == "module"
    assert store.kind(STOCK) == "application" and store.business(STOCK) == DEMO
    assert store.business(CATALOG) is None

    odd = Store([tmp_path])
    for local, manifest, code in (
            ("strange", {"kind": "plugin"}, "kind_not_understood"),
            ("nobody", {"kind": "application"}, "application_without_business"),
            ("claimed", {"business": DEMO}, "business_on_a_module")):
        where = tmp_path / "@odd" / local
        where.mkdir(parents=True)
        (where / MANIFEST).write_text(
            yaml.safe_dump({"name": f"@odd/{local}", **manifest}), encoding="utf-8")
        with pytest.raises(ModuleError) as refused:
            odd.kind(f"@odd/{local}")
        assert refused.value.code == code, local


def test_nothing_pins_an_application(store):
    with pytest.raises(ModuleError) as refused:
        store.imports({"imports": ["linkml:types", f"{STOCK}@v2"]})
    assert refused.value.code == "pins_an_application"
    # What to pin instead is what the application pins.
    assert f"{CATALOG}@v3" in refused.value.as_dict()["repairs"][0]["options"]


def test_an_application_goes_only_into_its_own_business_s_kernel(store, kernel):
    # A shared module goes into any kernel, declared or not.
    assert register(kernel, store.path(CATALOG, "v1"), actor_id="owner",
                    store=store)["minted"]

    with pytest.raises(BusinessError) as refused:
        register(kernel, store.path(STOCK, "v2"), actor_id="owner", store=store)
    assert refused.value.code == "kernel_not_declared"
    assert refused.value.as_dict()["repairs"][0]["options"] == [DEMO]

    declare(kernel, "another", actor_id="owner")
    for attempt in (
            lambda: register(kernel, store.path(STOCK, "v2"), actor_id="owner", store=store),
            lambda: install(kernel, store, STOCK, "v2", actor_id="owner",
                            valid_from="2026-01-01T00:00:00Z"),
            lambda: seal(kernel, dev_modules.FIXTURES / STOCK / "v4.draft.yaml",
                         actor_id="owner", into=store.directory(STOCK), store=store)):
        with pytest.raises(BusinessError) as refused:
            attempt()
        assert refused.value.code == "wrong_business"
        assert "application of demo" in str(refused.value)
    # Refused before anything was written: no fifth version beside the four.
    assert [v["version"] for v in store.versions(STOCK)] == ["v1", "v2", "v3", "v4"]


def test_installing_is_a_statement_read_at_two_clocks(store, kernel):
    declare(kernel, DEMO, actor_id="owner")
    first = install(kernel, store, STOCK, "v1", actor_id="owner",
                    valid_from="2026-03-01T00:00:00Z", recorded_at="2026-03-01T09:00:00Z")
    # Every version it pins is learned by the kernel on the way in.
    assert set(first["registered"]) == {
        "@uniti/core@v1", f"{CATALOG}@v2", "@demo/inventory@v2", f"{STOCK}@v1"}
    install(kernel, store, STOCK, "v2", actor_id="owner",
            valid_from="2026-09-01T00:00:00Z", recorded_at="2026-09-02T09:00:00Z")

    def in_use(valid_at, as_of="2026-12-31T00:00:00Z"):
        return [(i["name"], i["version"]) for i in
                installed(kernel, valid_at=valid_at, as_of=as_of)]

    assert in_use("2026-02-01T00:00:00Z") == []
    assert in_use("2026-05-01T00:00:00Z") == [(STOCK, "v1")]
    assert in_use("2026-10-01T00:00:00Z") == [(STOCK, "v2")]
    # On 1 September it was already v2's day, but the business had not yet
    # said so: as the log stood then, v1 was still in use.
    assert in_use("2026-10-01T00:00:00Z", as_of="2026-09-01T12:00:00Z") == [(STOCK, "v1")]

    stop(kernel, store, STOCK, actor_id="owner", valid_from="2026-11-01T00:00:00Z")
    assert in_use("2026-12-01T00:00:00Z") == []
    assert in_use("2026-10-01T00:00:00Z") == [(STOCK, "v2")]
    with pytest.raises(BusinessError) as refused:
        stop(kernel, store, STOCK, actor_id="owner", valid_from="2026-12-01T00:00:00Z")
    assert refused.value.code == "not_installed"

    with pytest.raises(BusinessError) as refused:
        install(kernel, store, CATALOG, "v1", actor_id="owner",
                valid_from="2026-01-01T00:00:00Z")
    assert refused.value.code == "not_an_application"
    assert refused.value.as_dict()["repairs"][0]["options"] == [STOCK]


def test_a_form_writes_only_through_the_version_in_use_that_day(store, kernel):
    declare(kernel, DEMO, actor_id="owner")
    install(kernel, store, STOCK, "v1", actor_id="owner", valid_from="2026-03-01T00:00:00Z")
    install(kernel, store, STOCK, "v2", actor_id="owner", valid_from="2026-09-01T00:00:00Z")
    cocoa = {"ingredient_code": "ING-COCOA", "ingredient_name": "Cocoa"}

    with pytest.raises(BusinessError) as refused:
        application.state(kernel, store, STOCK, "v2", "Ingredient", subject="cat:ing_cocoa",
                          values=cocoa, actor_id="sari",
                          valid_from="2026-05-01T00:00:00+00:00")
    assert refused.value.code == "not_installed"
    assert "v1 is the version in use" in str(refused.value)
    assert refused.value.as_dict()["repairs"][0]["options"] == [f"{STOCK}@v1"]

    written = application.state(kernel, store, STOCK, "v2", "Ingredient",
                                subject="cat:ing_cocoa", values=cocoa, actor_id="sari",
                                valid_from="2026-09-10T00:00:00+00:00")
    assert written["ontology_version"] == f"{STOCK}@v2"

    # Reading through a version nobody installed stays open.
    read = application.projection(kernel, store, STOCK, "v4", "IngredientStock",
                                  valid_at="2026-09-30", as_of="2026-12-31")
    assert read["class"] == "IngredientStock"


def test_the_api_says_whose_kernel_and_installs_for_a_person(store, monkeypatch):
    from starlette.testclient import TestClient
    from components.api.app import app

    _empty()
    monkeypatch.setenv("UNITI_DSN", DSN)
    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in store.roots))
    client = TestClient(app)

    assert client.get("/api/business").json() == {"business": None, "installed": []}
    refused = client.post("/api/app/install", json={
        "name": STOCK, "version": "v2", "actor": "owner"})
    assert refused.status_code == 400
    assert refused.json()["refusal"]["code"] == "kernel_not_declared"

    with psycopg.connect(DSN) as conn:
        declare(conn, DEMO, actor_id="owner")
        conn.commit()
    done = client.post("/api/app/install", json={
        "name": STOCK, "version": "v2", "actor": "owner",
        "valid_from": "2026-09-01T00:00:00Z"})
    assert done.status_code == 200, done.json()
    said = client.get("/api/business", params={"valid_at": "2026-10-01T00:00:00Z"}).json()
    assert said["business"] == DEMO
    assert [(i["name"], i["version"]) for i in said["installed"]] == [(STOCK, "v2")]
    # This kernel's own application is in its catalogue.
    modules = client.get("/api/catalogue", params={"kind": "module"}).json()["entries"]
    assert STOCK in {e["name"] for e in modules}

    assert client.post("/api/app/install", json={"name": STOCK}).status_code == 400
    stopped = client.post("/api/app/stop", json={
        "name": STOCK, "actor": "owner", "valid_from": "2026-11-01T00:00:00Z"})
    assert stopped.status_code == 200
    assert client.get("/api/business", params={
        "valid_at": "2026-12-01T00:00:00Z"}).json()["installed"] == []


def test_the_studio_starts_an_application_that_says_whose_it_is(tmp_path):
    from components.studio import draft as studio
    from components.studio.draft import StudioError

    held = Store([tmp_path, ROOT / "packages"])
    said = {"title": "Rental", "description": "One business's rental application."}
    with pytest.raises(ModuleError) as refused:
        studio.apply(held, "@kemahceria/rental", "start", {**said, "kind": "application"})
    assert refused.value.code == "application_without_business"
    with pytest.raises(StudioError) as refused:
        studio.apply(held, "@kemahceria/rental", "start", {**said, "kind": "core"})
    assert refused.value.code == "not_possible_yet"
    # Refused before a file was written.
    assert not (tmp_path / "@kemahceria").exists()

    studio.apply(held, "@kemahceria/rental", "start",
                 {**said, "kind": "application", "business": "kemahceria"})
    assert held.kind("@kemahceria/rental") == "application"
    assert held.business("@kemahceria/rental") == "kemahceria"

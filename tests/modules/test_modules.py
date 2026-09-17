"""Modules as sealed versions, and imports pinned to one of them.

The claim this slice has to hold: a module that pins `@x/y@v1` means exactly
what it meant when it was sealed, whatever versions of `@x/y` come after.
"""

import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

import dev_modules  # noqa: E402
from components.modules import read  # noqa: E402
from components.modules.store import ModuleError, Store  # noqa: E402
from perform import connect  # noqa: E402
from seal import DraftError, seal  # noqa: E402

THINGS, MOVEMENTS, CORE = "@example/things", "@example/movements", "@uniti/core"


@pytest.fixture
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn


@pytest.fixture
def built(conn, tmp_path):
    store, sealed = dev_modules.build(conn, tmp_path / "packages")
    return store


def _draft(tmp_path, imports):
    draft = yaml.safe_load((dev_modules.FIXTURES / THINGS / "v1.draft.yaml").read_text(encoding="utf-8"))
    draft["imports"] = imports
    draft["annotations"]["transcript"] = "t.txt"
    path = tmp_path / "draft.yaml"
    path.write_text(yaml.safe_dump(draft), encoding="utf-8")
    (tmp_path / "t.txt").write_text("fixture", encoding="utf-8")
    return path


def test_the_store_holds_every_version_in_order(built):
    assert built.names() == [MOVEMENTS, THINGS, CORE]
    assert [v["version"] for v in built.versions(THINGS)] == ["v1", "v2"]
    listing = {m["name"]: m for m in read.modules(built)}
    assert listing[MOVEMENTS]["latest"] == "v2"
    assert listing[MOVEMENTS]["versions"][0]["imports"] == [
        {"name": CORE, "version": "v1"}, {"name": THINGS, "version": "v1"}]


@pytest.mark.parametrize("imports, refusal", [
    (["linkml:types", "@uniti/core"], "names no version"),
    (["linkml:types", "@uniti/core@v9"], "has no sealed version v9"),
    (["linkml:types", "@nobody/nothing@v1"], "holds no module @nobody/nothing"),
    (["linkml:types", "some/local/file"], "neither a module@version"),
    (["linkml:types", "some/local/@uniti/core@v1"], "neither a module@version"),
])
def test_an_import_must_pin_a_sealed_version(conn, built, tmp_path, imports, refusal):
    target = built.directory(THINGS)
    before = sorted(p.name for p in target.iterdir())
    with pytest.raises(DraftError, match=refusal):
        seal(conn, _draft(tmp_path, imports), actor_id="test", into=target, store=built)
    assert sorted(p.name for p in target.iterdir()) == before


def test_a_version_cannot_pin_one_sealed_after_it(conn, built, tmp_path):
    with pytest.raises(DraftError, match="after this seal"):
        seal(conn, _draft(tmp_path, ["linkml:types", "@uniti/core@v1"]), actor_id="test",
             into=built.directory(THINGS), sealed_at="2020-01-01T00:00:00+00:00", store=built)


def test_a_pinned_import_keeps_its_meaning_when_the_module_moves_on(conn, tmp_path):
    store, sealed = dev_modules.build(conn, tmp_path / "packages", until=f"{MOVEMENTS}@v1")
    assert sealed[-1] == f"{MOVEMENTS}@v1"
    before = read.version(store, MOVEMENTS, "v1")

    seal(conn, dev_modules.FIXTURES / THINGS / "v2.draft.yaml", actor_id="test",
         into=store.directory(THINGS), store=store)
    after = read.version(store, MOVEMENTS, "v1")

    assert after["classes"] == before["classes"]
    assert after["slots"] == before["slots"]
    assert after["closure"] == before["closure"]
    # What changed is only that a newer version exists beside the pin.
    pin = next(i for i in after["imports"] if i["name"] == THINGS)
    assert pin["version"] == "v1" and pin["latest"] == "v2"
    seen = {s["name"] for s in after["slots"]}
    assert "thing_label" in seen and "thing_name" not in seen


def test_a_version_sees_what_it_imports_and_says_where_it_came_from(built):
    detail = read.version(built, MOVEMENTS, "v2")
    assert detail["closure"] == [
        {"name": CORE, "version": "v1"}, {"name": THINGS, "version": "v2"},
        {"name": MOVEMENTS, "version": "v2"}]
    by_name = {c["name"]: c for c in detail["classes"]}
    assert by_name["Movement"]["from"] == {"name": MOVEMENTS, "version": "v2"}
    assert by_name["ThingGroup"]["from"] == {"name": THINGS, "version": "v2"}
    assert by_name["Resource"]["from"] == {"name": CORE, "version": "v1"}
    assert detail["classes"][0]["from"]["name"] == MOVEMENTS

    used = read.version(built, THINGS, "v1")["imported_by"]
    assert used == [{"name": MOVEMENTS, "version": "v1"}]


def test_a_rename_keeps_its_predicate(built):
    diff = read.compare(built, THINGS, "v1", "v2")["diff"]
    assert diff["slots"]["renamed"][0]["from"] == "thing_label"
    assert diff["slots"]["renamed"][0]["to"] == "thing_name"
    assert diff["slots"]["renamed"][0]["slot_uri"] == "th:thing_label"
    assert sorted(diff["slots"]["added"]) == ["group_code", "thing_size"]
    assert diff["slots"]["removed"] == []
    assert diff["classes"]["added"] == ["ThingGroup"]
    thing = diff["classes"]["changed"][0]
    assert thing["name"] == "Thing" and thing["slots_added"] == ["thing_name", "thing_size"]

    moved = read.compare(built, MOVEMENTS, "v1", "v2")["diff"]["imports"]
    assert moved == {"added": ["@example/things@v2"], "removed": ["@example/things@v1"]}


def test_the_kernel_names_a_module_version_in_full(conn, built):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT ontology_version FROM assertion "
                    "WHERE ontology_version LIKE '@example/%' ORDER BY 1")
        labels = [r[0] for r in cur.fetchall()]
    assert labels == ["@example/movements@v1", "@example/movements@v2",
                      "@example/things@v1", "@example/things@v2"]


def test_the_graph_draws_pins_and_supersessions(built):
    graph = read.graph(built)
    edges = {(e["from"]["name"], e["from"]["version"], e["to"]["name"], e["to"]["version"], e["kind"])
             for e in graph["edges"]}
    assert (MOVEMENTS, "v1", THINGS, "v1", "imports") in edges
    assert (MOVEMENTS, "v2", THINGS, "v2", "imports") in edges
    assert (THINGS, "v2", THINGS, "v1", "supersedes") in edges
    assert len(graph["nodes"]) == 5


def test_a_module_name_is_checked(built):
    with pytest.raises(ModuleError, match="not a module name"):
        built.directory("things")


def test_the_api_reads_the_store_in_the_environment(conn, built, monkeypatch):
    from starlette.testclient import TestClient
    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in built.roots))
    client = TestClient(app)

    names = [m["name"] for m in client.get("/api/modules").json()]
    assert names == [MOVEMENTS, THINGS, CORE]
    assert len(client.get("/api/modules/graph").json()["nodes"]) == 5

    detail = client.get("/api/modules/version", params={"name": THINGS, "version": "v2"}).json()
    own = {s["name"]: s for s in detail["slots"] if s["from"]["name"] == THINGS}
    assert all(s["registered"] for s in own.values())

    diff = client.get("/api/modules/diff", params={"name": THINGS, "from": "v1", "to": "v2"}).json()
    assert diff["diff"]["slots"]["renamed"][0]["to"] == "thing_name"

    missing = client.get("/api/modules/version", params={"name": THINGS, "version": "v7"})
    assert missing.status_code == 404 and "v7" in missing.json()["error"]
    assert client.get("/api/modules/diff", params={"name": THINGS}).status_code == 400

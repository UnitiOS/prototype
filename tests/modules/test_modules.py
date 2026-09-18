"""Modules as sealed versions, and imports pinned to one of them.

The claim this slice has to hold: a module that pins `@x/y@v1` means exactly
what it meant when it was sealed, whatever versions of `@x/y` come after.

The fixtures are three modules of demonstration content — a small bakery's
catalog, its stock movements, and an application over both. Every one of them
declares `purpose: demonstration` in its manifest, and the last test here is
that the word reaches the log, so nobody reading the kernel has to be told
which rows are made up.
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

CATALOG, INVENTORY, STOCK = dev_modules.CATALOG, dev_modules.INVENTORY, dev_modules.STOCK
RIVAL, CORE = dev_modules.RIVAL, dev_modules.CORE


@pytest.fixture
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn


@pytest.fixture
def built(conn, tmp_path):
    store, sealed = dev_modules.build(conn, tmp_path / "packages")
    return store


def _draft(tmp_path, imports):
    draft = yaml.safe_load(
        (dev_modules.FIXTURES / CATALOG / "v1.draft.yaml").read_text(encoding="utf-8"))
    draft["imports"] = imports
    draft["annotations"]["transcript"] = "t.txt"
    path = tmp_path / "draft.yaml"
    path.write_text(yaml.safe_dump(draft), encoding="utf-8")
    (tmp_path / "t.txt").write_text("fixture", encoding="utf-8")
    return path


def test_the_store_holds_every_version_in_order(built):
    assert built.names() == [CATALOG, INVENTORY, STOCK, RIVAL, CORE]
    assert [v["version"] for v in built.versions(CATALOG)] == ["v1", "v2", "v3"]
    listing = {m["name"]: m for m in read.modules(built)}
    assert listing[INVENTORY]["latest"] == "v3"
    assert listing[INVENTORY]["versions"][0]["imports"] == [
        {"name": CORE, "version": "v1"}, {"name": CATALOG, "version": "v1"}]


@pytest.mark.parametrize("imports, refusal", [
    (["linkml:types", "@uniti/core"], "names no version"),
    (["linkml:types", "@uniti/core@v9"], "has no sealed version v9"),
    (["linkml:types", "@nobody/nothing@v1"], "holds no module @nobody/nothing"),
    (["linkml:types", "some/local/file"], "neither a module@version"),
    (["linkml:types", "some/local/@uniti/core@v1"], "neither a module@version"),
])
def test_an_import_must_pin_a_sealed_version(conn, built, tmp_path, imports, refusal):
    target = built.directory(CATALOG)
    before = sorted(p.name for p in target.iterdir())
    with pytest.raises(DraftError, match=refusal):
        seal(conn, _draft(tmp_path, imports), actor_id="test", into=target, store=built)
    assert sorted(p.name for p in target.iterdir()) == before


def test_a_version_cannot_pin_one_sealed_after_it(conn, built, tmp_path):
    with pytest.raises(DraftError, match="after this seal"):
        seal(conn, _draft(tmp_path, ["linkml:types", "@uniti/core@v1"]), actor_id="test",
             into=built.directory(CATALOG), sealed_at="2020-01-01T00:00:00+00:00",
             store=built)


def test_a_pinned_import_keeps_its_meaning_when_the_module_moves_on(conn, tmp_path):
    store, sealed = dev_modules.build(conn, tmp_path / "packages",
                                      until=f"{INVENTORY}@v1")
    assert sealed[-1] == f"{INVENTORY}@v1"
    before = read.version(store, INVENTORY, "v1")

    seal(conn, dev_modules.FIXTURES / CATALOG / "v2.draft.yaml", actor_id="test",
         into=store.directory(CATALOG), store=store)
    after = read.version(store, INVENTORY, "v1")

    assert after["classes"] == before["classes"]
    assert after["slots"] == before["slots"]
    assert after["closure"] == before["closure"]
    # What changed is only that a newer version exists beside the pin.
    pin = next(i for i in after["imports"] if i["name"] == CATALOG)
    assert pin["version"] == "v1" and pin["latest"] == "v2"
    seen = {s["name"] for s in after["slots"]}
    assert "ingredient_label" in seen and "ingredient_name" not in seen


def test_a_version_sees_what_it_imports_and_says_where_it_came_from(built):
    detail = read.version(built, INVENTORY, "v2")
    assert detail["closure"] == [
        {"name": CORE, "version": "v1"}, {"name": CATALOG, "version": "v2"},
        {"name": INVENTORY, "version": "v2"}]
    by_name = {c["name"]: c for c in detail["classes"]}
    assert by_name["StockMovement"]["from"] == {"name": INVENTORY, "version": "v2"}
    assert by_name["Ingredient"]["from"] == {"name": CATALOG, "version": "v2"}
    assert detail["classes"][0]["from"]["name"] == INVENTORY

    # The one thing core holds is the predicate a class fact is stated under,
    # and every module sees the same one.
    by_slot = {s["name"]: s for s in detail["slots"]}
    assert by_slot["entity_class"]["from"] == {"name": CORE, "version": "v1"}
    assert by_slot["entity_class"]["designates_type"] is True
    assert by_name["StockMovement"]["slots"][0] == "entity_class"

    used = read.version(built, CATALOG, "v1")["imported_by"]
    assert used == [{"name": INVENTORY, "version": "v1"}]


def test_a_rename_keeps_its_predicate(built):
    diff = read.compare(built, CATALOG, "v1", "v2")["diff"]
    renamed = diff["slots"]["renamed"][0]
    assert renamed["from"] == "ingredient_label"
    assert renamed["to"] == "ingredient_name"
    assert renamed["slot_uri"] == "cat:ingredient_label"
    assert diff["slots"]["added"] == ["ingredient_reorder_level"]
    assert diff["slots"]["removed"] == []
    assert diff["classes"]["added"] == []
    ingredient = next(c for c in diff["classes"]["changed"] if c["name"] == "Ingredient")
    assert ingredient["slots_added"] == ["ingredient_name", "ingredient_reorder_level"]

    moved = read.compare(built, INVENTORY, "v1", "v2")["diff"]["imports"]
    assert moved == {"added": ["@demo/catalog@v2"], "removed": ["@demo/catalog@v1"]}


def test_the_kernel_names_a_module_version_in_full(conn, built):
    with conn.cursor() as cur:
        # Only what sealing wrote. Forms and loads write under a version label
        # too, and this is about how a *seal* names itself.
        cur.execute("SELECT DISTINCT a.ontology_version FROM assertion a "
                    "JOIN intent i ON i.id = a.intent_id "
                    "WHERE i.action_name IN ('seal_version', 'register_version') "
                    "AND a.ontology_version LIKE '@%' ORDER BY 1")
        labels = [r[0] for r in cur.fetchall()]

    # Only the versions that brought a predicate nobody had registered yet. A
    # seal writes what is new, and `@demo/catalog@v2` was new because it added
    # a reorder level.
    assert labels == ["@demo/catalog@v1", "@demo/catalog@v2",
                      "@demo/inventory@v1", "@demo/inventory@v2",
                      "@demo/stock@v1", "@rival/stock-moves@v1",
                      "@uniti/core@v1"]


def test_moving_a_module_onto_roles_writes_nothing_to_the_log(conn, built):
    """The v3 versions declare roles and mint not one assertion between them.

    Worth asserting rather than assuming, because it is the property the whole
    design rests on: a role lives in the map and never in the log. @demo/catalog
    and @demo/inventory each moved onto core v2 and said what their classes
    are, and the kernel did not need to hear about it — the predicates were
    already registered and not one of them changed.

    Which is also why re-binding an orphaned fact later can work at all.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT i.note, count(a.id)
            FROM intent i LEFT JOIN assertion a ON a.intent_id = i.id
            WHERE i.action_name = 'seal_version' AND i.reason_code = 'demonstration'
            GROUP BY i.id, i.note
        """)
        wrote = [(note, n) for note, n in cur.fetchall()]

    onto_roles = [n for note, n in wrote if "v3.draft" in note]
    assert onto_roles and set(onto_roles) == {0}

    # And no binding was ever registered as a predicate.
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM assertion WHERE value_literal = ANY(%s)",
                    (["uniti:amount", "uniti:affects", "uniti:moment"],))
        assert cur.fetchone()[0] == 0


def test_a_module_that_says_it_is_made_up_says_so_in_the_log(conn, built):
    """`purpose: demonstration` is a manifest word that reaches the kernel.

    A log is read by people who do not hold the store. If the content in it is
    made up, the rows have to say so themselves — so the word on the manifest
    becomes the `reason_code` of every intent that seals or registers one of
    its versions.
    """
    assert built.purpose(CATALOG) == "demonstration"
    assert built.purpose(CORE) is None

    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT i.reason_code FROM intent i "
                    "JOIN assertion a ON a.intent_id = i.id "
                    "WHERE a.ontology_version LIKE '@demo/%'")
        assert [r[0] for r in cur.fetchall()] == ["demonstration"]

        cur.execute("SELECT DISTINCT i.reason_code FROM intent i "
                    "JOIN assertion a ON a.intent_id = i.id "
                    "WHERE a.ontology_version LIKE '@uniti/core@%'")
        assert [r[0] for r in cur.fetchall()] == [None]

    assert read.version(built, CATALOG, "v1")["purpose"] == "demonstration"
    assert read.version(built, CORE, "v1")["purpose"] is None


def test_the_graph_draws_pins_and_supersessions(built):
    graph = read.graph(built)
    edges = {(e["from"]["name"], e["from"]["version"], e["to"]["name"], e["to"]["version"], e["kind"])
             for e in graph["edges"]}
    assert (INVENTORY, "v1", CATALOG, "v1", "imports") in edges
    assert (INVENTORY, "v2", CATALOG, "v2", "imports") in edges
    assert (STOCK, "v1", INVENTORY, "v2", "imports") in edges
    assert (CATALOG, "v2", CATALOG, "v1", "supersedes") in edges
    # The swap, drawn: one application version pins @demo's inventory and the
    # next pins somebody else's, and nothing else about them differs.
    assert (STOCK, "v2", INVENTORY, "v3", "imports") in edges
    assert (STOCK, "v3", RIVAL, "v1", "imports") in edges
    assert len(graph["nodes"]) == 12


def test_a_module_name_is_checked(built):
    with pytest.raises(ModuleError, match="not a module name"):
        built.directory("catalog")


def test_the_api_reads_the_store_in_the_environment(conn, built, monkeypatch):
    from starlette.testclient import TestClient
    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in built.roots))
    client = TestClient(app)

    names = [m["name"] for m in client.get("/api/modules").json()]
    assert names == [CATALOG, INVENTORY, STOCK, RIVAL, CORE]
    assert len(client.get("/api/modules/graph").json()["nodes"]) == 12

    detail = client.get("/api/modules/version",
                        params={"name": CATALOG, "version": "v2"}).json()
    own = {s["name"]: s for s in detail["slots"] if s["from"]["name"] == CATALOG}
    assert all(s["registered"] for s in own.values())

    diff = client.get("/api/modules/diff",
                      params={"name": CATALOG, "from": "v1", "to": "v2"}).json()
    assert diff["diff"]["slots"]["renamed"][0]["to"] == "ingredient_name"

    missing = client.get("/api/modules/version", params={"name": CATALOG, "version": "v7"})
    assert missing.status_code == 404 and "v7" in missing.json()["error"]
    assert client.get("/api/modules/diff", params={"name": CATALOG}).status_code == 400

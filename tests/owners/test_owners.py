"""Who may seal under a name: the owners of it, kept in the kernel.

What has to hold (DESIGN_NOTES.md §15.4, archived/PEMILIK_NAMA.md):

    the first to seal        under a name nobody owns becomes its owner, in
    owns the name            the seal's own intent
    only an owner seals      anybody else is refused before a file is written,
                             and told who the owners are
    owners change            an owner adds and removes owners from a day on,
    from a day               read at two clocks; the last owner stays
    a business's name        is its kernel's: whoever declares the kernel owns
                             it, and an application is named under it
    reading is not sealing   registering another owner's version is not
                             checked

Every test starts from a kernel of its own, emptied, and a store of its own:
what is tested is who owns a name, and that has to start from nobody.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from components import owners  # noqa: E402
from components.business import declare  # noqa: E402
from components.modules.store import MANIFEST, ModuleError, Store  # noqa: E402
from components.owners import OwnerError  # noqa: E402
from seal import register, seal  # noqa: E402

NAME = "@budi/notes"

DSN = os.environ["UNITI_DSN"].rsplit("/", 1)[0] + "/uniti_check_owners"
SCHEMA = (ROOT / "components" / "kernel" / "001_schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def kernel():
    """An empty kernel, in which nobody owns any name."""
    parts = urlsplit(DSN)
    admin = urlunsplit((parts.scheme, parts.netloc, "/postgres", "", ""))
    with psycopg.connect(admin, autocommit=True, connect_timeout=2) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s",
                            ("uniti_check_owners",)).fetchone():
            conn.execute('CREATE DATABASE "uniti_check_owners"')
    with psycopg.connect(DSN, autocommit=True, connect_timeout=2) as conn:
        conn.execute(SCHEMA)
    with psycopg.connect(DSN) as conn:
        yield conn
        conn.rollback()


@pytest.fixture
def store(tmp_path):
    """One module, started and not yet sealed, beside core and the library."""
    root = tmp_path / "packages"
    (root / NAME).mkdir(parents=True)
    (root / NAME / MANIFEST).write_text(
        yaml.safe_dump({"name": NAME, "title": "Notes", "purpose": "demonstration"}),
        encoding="utf-8")
    return Store([root, ROOT / "packages"])


def _draft(tmp_path):
    """The smallest draft the seal and the standard take: one kind of thing."""
    where = tmp_path / "drafts"
    where.mkdir(exist_ok=True)
    draft = {
        "id": "https://notes.example/notes",
        "name": "budi_notes",
        "title": "Notes",
        "description": "A module written for one test.",
        "prefixes": {"linkml": "https://w3id.org/linkml/", "nt": "https://notes.example/notes/"},
        "default_prefix": "nt",
        "default_range": "string",
        "imports": ["linkml:types", "@uniti/core@v2"],
        "classes": {"Note": {"mixins": ["Thing"], "slots": ["note_ref"],
                             "description": "Something somebody wrote down."}},
        "slots": {"note_ref": {"slot_uri": "nt:note_ref", "identifier": True,
                               "description": "The code a note is known by."}},
        "annotations": {"valid_from": "2026-09-01T00:00:00+00:00",
                        "transcript": "notes.txt"},
    }
    (where / "draft.yaml").write_text(yaml.safe_dump(draft, sort_keys=False),
                                      encoding="utf-8")
    (where / "notes.txt").write_text("notes", encoding="utf-8")
    return where / "draft.yaml"


def _seal(kernel, store, tmp_path, person):
    return seal(kernel, _draft(tmp_path), actor_id=person, into=store.directory(NAME),
                store=store)


def _owners(kernel, scope="@budi", **clocks):
    return [o["owner"] for o in owners.owners(kernel, scope, **clocks)]


def test_the_first_to_seal_under_a_name_owns_it_and_nobody_else_seals(
        kernel, store, tmp_path):
    assert not owners.owned(kernel, "@budi")
    first = _seal(kernel, store, tmp_path, "budi")
    assert first["version"] == "v1" and first["claimed"] is True
    assert _owners(kernel) == ["budi"]
    # Claimed where it happened: the claim is a statement of the seal's intent.
    [held] = owners.owners(kernel, "@budi")
    with kernel.cursor() as cur:
        cur.execute("SELECT intent_id FROM assertion WHERE id = %s", (held["assertion"],))
        assert cur.fetchone()[0] == first["intent_id"]

    with pytest.raises(OwnerError) as refused:
        _seal(kernel, store, tmp_path, "sari")
    assert refused.value.code == "not_an_owner"
    assert refused.value.gate == "the owners of names"
    assert refused.value.as_dict()["repairs"][0]["options"] == ["budi"]
    assert "copy the module to a name of your own" in str(refused.value.explain())
    # Refused before a file was written.
    assert [v["version"] for v in store.versions(NAME)] == ["v1"]

    again = _seal(kernel, store, tmp_path, "budi")
    assert again["version"] == "v2" and again["claimed"] is False


def test_owners_are_added_and_removed_from_a_day_and_the_last_one_stays(
        kernel, store, tmp_path):
    _seal(kernel, store, tmp_path, "budi")
    with pytest.raises(OwnerError) as refused:
        owners.add(kernel, "@budi", "tono", actor_id="tono")
    assert refused.value.code == "not_an_owner"

    owners.add(kernel, "@budi", "sari", actor_id="budi", valid_from="2027-01-01T00:00:00Z")
    assert owners.add(kernel, "@budi", "sari", actor_id="budi",
                      valid_from="2027-01-01T00:00:00Z")["intent_id"] is None
    owners.remove(kernel, "@budi", "budi", actor_id="sari",
                  valid_from="2027-03-01T00:00:00Z")

    assert _owners(kernel) == ["budi"]
    assert _owners(kernel, valid_at="2027-02-01T00:00:00Z") == ["budi", "sari"]
    assert _owners(kernel, valid_at="2027-04-01T00:00:00Z") == ["sari"]

    with pytest.raises(OwnerError) as refused:
        owners.remove(kernel, "@budi", "sari", actor_id="sari",
                      valid_from="2027-04-01T00:00:00Z")
    assert refused.value.code == "last_owner"
    with pytest.raises(OwnerError) as refused:
        owners.remove(kernel, "@budi", "tono", actor_id="sari",
                      valid_from="2027-04-01T00:00:00Z")
    assert refused.value.code == "not_an_owner"
    assert refused.value.as_dict()["repairs"][0]["options"] == ["sari"]
    with pytest.raises(OwnerError) as refused:
        owners.add(kernel, "@budi", "", actor_id="sari")
    assert refused.value.code == "no_person"
    assert [n["name"] for n in owners.names(kernel)] == ["@budi"]


def test_a_business_s_kernel_gives_its_name_to_whoever_declares_it(kernel, tmp_path):
    out = declare(kernel, "kemahceria", actor_id="ani")
    assert out["owner"] == "ani"
    assert _owners(kernel, "@kemahceria") == ["ani"]

    # An application is named under its business, so its owners seal it.
    odd = Store([tmp_path])
    where = tmp_path / "@probe" / "shop"
    where.mkdir(parents=True)
    (where / MANIFEST).write_text(yaml.safe_dump(
        {"name": "@probe/shop", "kind": "application", "business": "kemahceria"}),
        encoding="utf-8")
    with pytest.raises(ModuleError) as refused:
        odd.kind("@probe/shop")
    assert refused.value.code == "name_not_the_business"
    assert refused.value.as_dict()["repairs"][0]["options"] == ["@kemahceria/shop"]


def test_a_kernel_set_up_names_a_first_owner_and_registering_is_not_sealing(
        kernel, store):
    assert owners.first(kernel, "@uniti", actor_id="keeper")["intent_id"] is not None
    assert owners.first(kernel, "@uniti", actor_id="keeper")["intent_id"] is None
    with pytest.raises(OwnerError) as refused:
        owners.first(kernel, "@uniti", actor_id="budi")
    assert refused.value.code == "not_an_owner"

    # Reading another owner's version into a kernel is not making it.
    assert register(kernel, store.path("@uniti/party", "v1"), actor_id="budi",
                    store=store)["minted"]
    assert _owners(kernel, "@uniti") == ["keeper"]


def test_the_api_says_who_owns_a_name_and_an_owner_adds_one(
        kernel, store, tmp_path, monkeypatch):
    from starlette.testclient import TestClient
    from components.api.app import app
    from components.studio import draft as studio

    _seal(kernel, store, tmp_path, "budi")
    kernel.commit()
    monkeypatch.setenv("UNITI_DSN", DSN)
    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in store.roots))
    client = TestClient(app)

    said = client.get("/api/names", params={"name": NAME}).json()
    assert said["name"] == "@budi" and said["owned"] is True
    assert [o["owner"] for o in said["owners"]] == ["budi"]
    assert client.get("/api/names", params={"name": "@nobody"}).json()["owned"] is False

    refused = client.post("/api/names/add", json={
        "name": "@budi", "person": "sari", "actor": "tono"})
    assert refused.status_code == 400
    assert refused.json()["refusal"]["code"] == "not_an_owner"
    added = client.post("/api/names/add", json={
        "name": "@budi", "person": "sari", "actor": "budi"})
    assert added.status_code == 200, added.json()
    every = client.get("/api/names").json()["names"]
    assert [(n["name"], [o["owner"] for o in n["owners"]]) for n in every] == [
        ("@budi", ["budi", "sari"])]
    assert client.post("/api/names/remove", json={"name": "@budi"}).status_code == 400

    # A draft says who may seal it while it is still a draft.
    studio.apply(store, "@budi/more", "start",
                 {"title": "More", "description": "Another of Budi's modules."})
    draft = client.get("/api/studio/draft", params={"name": "@budi/more"}).json()
    assert [o["owner"] for o in draft["owners"]["owners"]] == ["budi", "sari"]

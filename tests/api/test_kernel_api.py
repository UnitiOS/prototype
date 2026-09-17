"""The kernel read API against a synthetic log with both clocks alive.

The one property that matters most: the API never judges which fact stands.
For every (subject, predicate) pair and every pair of clocks sampled, the row
it marks `winner` is exactly the row `resolve_single` returns, and a row is
marked `outranked` only when some other row won.
"""

import itertools
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

import seed_200  # noqa: E402
from perform import connect  # noqa: E402
from resolve import resolve_single  # noqa: E402
from components.api import kernel  # noqa: E402
from components.api.app import app  # noqa: E402

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
CLOCKS = [EPOCH + timedelta(days=d) for d in (0, 30, 90, 180, 365, 540)]


@pytest.fixture(scope="module")
def conn():
    seed_200.main()
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn


@pytest.fixture(scope="module")
def client(conn):
    return TestClient(app)


def _entity_ids(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT subject_id FROM assertion")
        return [r[0] for r in cur.fetchall()]


def test_winner_is_exactly_what_resolve_single_returns(conn):
    checked = 0
    for entity_id in _entity_ids(conn):
        for valid_at, as_of in itertools.product(CLOCKS, CLOCKS):
            view = kernel.entity(conn, entity_id, valid_at=valid_at, as_of=as_of)
            for fact in view["facts"]:
                expected = resolve_single(
                    conn, subject_id=entity_id, predicate_id=fact["predicate"]["id"],
                    valid_at=valid_at, as_of=as_of)
                winners = [r["id"] for r in fact["rows"] if r["status"] == "winner"]
                assert winners == ([expected["id"]] if expected else [])
                assert fact["standing"] == (expected["id"] if expected else None)
                if expected is None:
                    assert not [r for r in fact["rows"] if r["status"] == "outranked"]
                checked += 1
    assert checked > 1000


def test_every_status_occurs_somewhere(conn):
    seen = set()
    for entity_id in _entity_ids(conn):
        for valid_at, as_of in itertools.product(CLOCKS, CLOCKS):
            view = kernel.entity(conn, entity_id, valid_at=valid_at, as_of=as_of)
            seen |= {r["status"] for f in view["facts"] for r in f["rows"]}
    assert seen == {"not_recorded", "retraction", "revoked", "not_yet_valid",
                    "winner", "outranked"}


def test_a_revocation_counts_only_once_the_log_knew_of_it(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT t.subject_id, t.id, t.recorded_at, r.recorded_at
            FROM assertion r JOIN assertion t ON t.id = r.revokes
            WHERE r.recorded_at > t.recorded_at
            ORDER BY r.seq LIMIT 1""")
        subject_id, target, target_recorded, revoked_recorded = cur.fetchone()

    def status_at(as_of):
        view = kernel.entity(conn, subject_id, valid_at=CLOCKS[-1], as_of=as_of)
        return next(r["status"] for f in view["facts"] for r in f["rows"]
                    if r["id"] == target)

    assert status_at(target_recorded) != "revoked"
    assert status_at(revoked_recorded) == "revoked"


def test_summary_counts_the_log(client):
    body = client.get("/api/kernel/summary").json()
    assert body["assertions"] == 200
    assert body["intents"] == 201
    assert body["entities"] == 19
    assert body["registered"] == 19


def test_entities_are_named_through_the_registry(client):
    rows = client.get("/api/kernel/entities").json()
    assert len(rows) == 19
    assert all(r["uri"] for r in rows)
    found = client.get("/api/kernel/entities", params={"search": "group"}).json()
    assert sorted(r["uri"] for r in found) == ["ex:group_a", "ex:group_b", "ex:group_c"]


def test_entity_page_reads_at_the_clocks_in_its_url(client):
    subject = next(r for r in client.get("/api/kernel/entities").json()
                   if r["uri"] == "ex:subject_01")
    early = client.get(f"/api/kernel/entities/{subject['id']}",
                       params={"valid_at": "2026-01-01T00:00:00Z",
                               "as_of": "2026-01-01T00:00:00Z"}).json()
    late = client.get(f"/api/kernel/entities/{subject['id']}",
                      params={"valid_at": "2026-12-31T00:00:00Z",
                              "as_of": "2027-06-30T00:00:00Z"}).json()
    assert early["uri"] == "ex:subject_01"
    standing = lambda body: sum(1 for f in body["facts"] if f["standing"])
    assert standing(late) > standing(early)
    groups = client.get("/api/kernel/entities", params={"search": "group_"}).json()
    referenced = [client.get(f"/api/kernel/entities/{g['id']}").json()["referenced_by"]
                  for g in groups]
    assert any(referenced)


def test_intent_shows_what_it_wrote(client):
    listing = client.get("/api/kernel/intents", params={"limit": 5}).json()
    assert listing["total"] == 201 and len(listing["intents"]) == 5
    minting = client.get("/api/kernel/intents", params={"limit": 500}).json()["intents"]
    first = next(i for i in minting if i["minted"])
    body = client.get(f"/api/kernel/intents/{first['id']}").json()
    assert len(body["minted"]) == 19
    one = next(i for i in minting if i["assertions"] == 1)
    body = client.get(f"/api/kernel/intents/{one['id']}").json()
    assert len(body["assertions"]) == 1
    assert body["assertions"][0]["intent_id"] == one["id"]


def test_log_pages_newest_first(client):
    page = client.get("/api/kernel/log", params={"limit": 10, "offset": 5}).json()
    seqs = [a["seq"] for a in page["assertions"]]
    assert page["total"] == 200 and len(seqs) == 10
    assert seqs == sorted(seqs, reverse=True)


def test_plane_draws_the_whole_log_at_the_clocks(client):
    body = client.get("/api/kernel/plane", params={
        "valid_at": "2026-03-01T00:00:00Z", "as_of": "2026-03-01T00:00:00Z"}).json()
    assert body["total"] == 200 and len(body["points"]) == 200
    statuses = {p["status"] for p in body["points"]}
    assert {"not_recorded", "candidate"} <= statuses
    assert "winner" not in statuses


@pytest.mark.parametrize("url, status", [
    ("/api/kernel/entities/not-a-uuid", 404),
    ("/api/kernel/entities/00000000-0000-0000-0000-000000000000", 404),
    ("/api/kernel/intents/00000000-0000-0000-0000-000000000000", 404),
    ("/api/kernel/log?as_of=yesterday", 400),
    ("/api/kernel/log?limit=-1", 400),
])
def test_bad_requests_are_refused_in_words(client, url, status):
    response = client.get(url)
    assert response.status_code == status
    assert response.json()["error"]

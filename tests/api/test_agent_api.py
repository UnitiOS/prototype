"""The agent's door: a request streamed as the agent works, the conversation
read back, and a seal only a person can make.

Nothing here calls a model: the builder and the accountant are the scripted
ones from tests/agent/fixtures/rehearsal.yaml, played through the same session
the page talks to, request by request: a plan, the examples, the rules.
"""

import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

import dev_modules  # noqa: E402
from components.agent import rehearsal  # noqa: E402
from components.agent.config import unlimited  # noqa: E402
from components.api import agent as door  # noqa: E402
from components.api.app import app  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from perform import connect  # noqa: E402

SCRIPT = ROOT / "tests" / "agent" / "fixtures" / "rehearsal.yaml"


@pytest.fixture(scope="module")
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def world(conn, tmp_path_factory):
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    return store


@pytest.fixture
def client(world, conn, tmp_path, monkeypatch):
    script = rehearsal.load(SCRIPT)
    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in world.roots))
    monkeypatch.setattr(door, "configured", unlimited(
        builder=rehearsal.model(script), accountant=rehearsal.accountant(script)))
    monkeypatch.setattr(door, "CALLS", tmp_path)
    # The seal writes to the log the modules it pins were sealed into, which
    # is this test's own transaction.
    monkeypatch.setattr(door, "connect", lambda *a, **k: nullcontext(conn))
    return TestClient(app), script


def _lines(response):
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def _asked(client, name, text):
    response = client.post("/api/studio/ask", json={"name": name, "text": text})
    assert response.status_code == 200
    return _lines(response)


def test_a_request_is_streamed_as_it_works_and_a_person_agrees_and_seals(client, world):
    client, script = client
    name = script["module"]
    first, second, third = script["requests"]

    # A plan first, kept beside the draft, which the person agrees to before
    # there is a draft at all.
    events = _asked(client, name, first["says"])
    turn = events[-1]
    assert turn["event"] == "turn" and turn["ended"] == "Plan"
    assert turn["said"]["builds"].startswith("A table with one row per ingredient")
    chat = client.get("/api/studio/chat", params={"name": name}).json()
    assert chat["plan"]["agreed"] is False
    agreed = client.post("/api/studio/step", json={"name": name, "step": "agree_plan"})
    assert agreed.status_code == 200 and agreed.json()["plan"]["agreed"] is True

    events = _asked(client, name, second["says"])
    # First where every call is written down whole, then each call as it
    # happened, and last how the request ended.
    assert events[0]["event"] == "started" and events[0]["watch"].endswith(".jsonl")
    calls = [e for e in events if e["event"] == "call"]
    assert {e["part"] for e in calls} == {"builder", "accountant"}
    assert any(d.get("tool") == "reckon" for e in calls for d in e["did"])
    assert any(e["changed"] for e in calls)
    # A call that changed the draft says what changed, as the map draws it:
    # in that call, and since the request began. The first `do` starts the
    # module and builds Level.
    changed = next(e for e in calls if e["changed"])
    assert {"what": "kind", "name": "Level", "how": "added"} in changed["now"]
    assert {"what": "field", "name": "Level.level_on_hand", "how": "added"} in changed["now"]
    assert changed["touched"] == changed["now"]
    later = [e for e in calls if e["changed"]][-1]
    assert later["now"] != later["touched"]
    assert {"what": "example", "name": "flour", "how": "added"} in later["touched"]
    turn = events[-1]
    assert turn["touched"] == later["touched"]
    assert turn["event"] == "turn" and turn["ended"] == "Proposal"
    assert turn["said"]["agree"] == ["flour"] and turn["said"]["seal"] is False
    assert "[waits for its rules] flour" in turn["shown"]
    # The file has every call; the page was shown the gist of each.
    written = Path(events[0]["watch"])
    assert sum(1 for line in written.read_text(encoding="utf-8").splitlines()
               if '"event": "call"' in line) == len(calls)

    # The conversation reads back as the page draws it: without the calls.
    chat = client.get("/api/studio/chat", params={"name": name}).json()
    assert chat["running"] is False
    assert [t["ended"] for t in chat["turns"]] == ["Plan", "Proposal"]
    assert "messages" not in chat["turns"][1]
    assert chat["turns"][1]["shown"] == turn["shown"]
    assert chat["turns"][1]["touched"] == turn["touched"]
    assert chat["reckonings"]["flour"]["figures"][0]["value"] == "20"
    assert chat["plan"]["agreed"] is True

    # Sealing is refused while the example is only proposed. The person
    # agrees to it, and it waits for its rules.
    refused = client.post("/api/studio/seal", json={"name": name, "actor": "probe"})
    assert refused.status_code == 400
    agreed = client.post("/api/studio/step", json={
        "name": name, "step": "agree_example", "args": {"example": "flour"}})
    assert agreed.status_code == 200
    (flour,) = agreed.json()["examples"]
    assert flour["agreed"] and flour["waits"] and not agreed.json()["sealable"]

    events = _asked(client, name, third["says"])
    turn = events[-1]
    assert turn["ended"] == "Proposal" and turn["said"]["seal"] is True
    assert turn["shown"].endswith("Ready to be sealed as v1.")

    # The person seals. The draft is closed; the conversation and the plan
    # that built the version stay beside it, and are not taken for versions.
    sealed = client.post("/api/studio/seal", json={"name": name, "actor": "probe"})
    assert sealed.status_code == 200, sealed.json()
    assert sealed.json()["version"] == "v1"
    where = studio.directory(world, name)
    assert not (where / studio.DRAFT).exists() and not (where / studio.CONVERSATION).exists()
    assert (where / "v1.chat.yaml").is_file() and (where / "v1.examples.yaml").is_file()
    assert (where / "v1.plan.yaml").is_file() and not (where / studio.PLAN).exists()
    assert [v["version"] for v in world.versions(name)] == ["v1"]
    drafts = client.get("/api/studio/drafts").json()
    assert name not in [d["name"] for d in drafts]


def test_one_request_per_module_and_a_seal_needs_a_person(client, monkeypatch):
    client, script = client
    name = "@probe/busy"
    monkeypatch.setattr(door, "RUNNING", {name})
    busy = client.post("/api/studio/ask", json={"name": name, "text": "Hello."})
    assert busy.status_code == 409 and "already working" in busy.json()["error"]
    assert client.post("/api/studio/seal", json={"name": name}).status_code == 400
    assert client.post("/api/studio/ask", json={"name": name}).status_code == 400

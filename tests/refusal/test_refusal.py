"""Refusals: data before prose, and the repair beside every one.

A gate that says no is the surface this system is mostly met through. Someone
describing a business hits far more refusals than successes, so a refusal that
is only a sentence leaves them to work out the next move from prose — and
leaves an agent to guess at it, which is worse.

What is asserted here:

    the structure is the source     the sentence is assembled from `where`,
                                    `expected` and `got`, never written beside
                                    them, so the two cannot drift apart.
    the code is the promise         every way this system says no is written
                                    down in one closed list, and a raise site
                                    that invents one is refused.
    the repair is computed          `options` comes out of the graph — the
                                    slots that exist, the classes that exist —
                                    so choosing from it cannot be wrong in the
                                    way that inventing a name can.

And one read over the top: `check` runs the compiler's own readers and
collects what they refuse, because a gate stops at the first problem and a
person wants all of them. The seal does the same through generators, which is
why the scan below counts a `yield` as a refusal too.
"""

import os
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

import dev_modules  # noqa: E402
from components.modules import roles as roles_read  # noqa: E402
from components.modules.check import check  # noqa: E402
from components.modules.store import ModuleError  # noqa: E402
from components.refusal import CODES, Refusal, Repair  # noqa: E402
from perform import connect  # noqa: E402
from seal import DraftError, seal  # noqa: E402

CORE, STOCK = dev_modules.CORE, dev_modules.STOCK
APP_NAME, APP_VERSION = dev_modules.APPLICATION
SWAP_VERSION = dev_modules.SWAPPED[1]

# Every gate, and the module its refusals are raised in. The scan below reads
# these files, so a new gate is added here rather than discovered by accident.
GATES = {
    "components/seal/seal.py": "DraftError",
    "components/generator/generate.py": "MapError",
    "components/compiler/compile.py": "CompileError",
    "components/api/application.py": "MapError",
    "components/modules/store.py": "ModuleError",
    "components/studio/draft.py": "StudioError",
    "components/examples/examples.py": "ExampleError",
    "components/standard/standard.py": "StandardError",
    "components/business/business.py": "BusinessError",
    "components/owners/owners.py": "OwnerError",
}


@pytest.fixture(scope="module")
def conn():
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn


@pytest.fixture(scope="module")
def built(conn, tmp_path_factory):
    store, _ = dev_modules.build(conn, tmp_path_factory.mktemp("packages"))
    return store


# ---- the shape ------------------------------------------------------------

def test_a_refusal_is_data_and_the_sentence_is_derived():
    """One source. The prose is a reader of it, not a second copy of it."""
    refusal = ModuleError(
        "no_such_version",
        where="@a/b",
        expected="a sealed version v9",
        got="2 sealed here",
        repairs=[Repair("pin a version @a/b has", options=["v1", "v2"])],
    )
    assert refusal.code == "no_such_version"
    assert refusal.gate == "the module store"
    assert str(refusal) == "@a/b: expected a sealed version v9, got 2 sealed here"

    sent = refusal.as_dict()
    assert sent["sentence"] == str(refusal)
    assert sent["means"] == CODES["no_such_version"]
    assert sent["repairs"] == [
        {"do": "pin a version @a/b has", "where": None, "options": ["v1", "v2"]}]
    # The third reader is the terminal, and it is the same parts again.
    assert str(refusal) in refusal.explain()
    assert "one of: v1, v2" in refusal.explain()


def test_a_code_nobody_wrote_down_is_refused_where_it_is_raised():
    """A code is a promise to whoever matched on it, so it is not free."""
    with pytest.raises(KeyError, match="refusal.CODES"):
        ModuleError("improvised_on_the_spot", where="x", expected="y", got="z")


def test_every_code_the_gates_raise_is_written_down():
    """The closed list is closed, and the scan is what keeps it that way.

    It also catches the other direction: a raise site still passing prose as
    its first argument would not match, and the counts would disagree.
    """
    # `raise` or `yield`: a reader that can refuse more than once hands its
    # refusals back one at a time, so that a gate can stop at the first and a
    # page can collect them all. Both are the gate saying no — and so is
    # `return`, from a helper that builds the refusal its caller raises.
    gate = (r"(?:raise|yield|return) "
            r"(?:DraftError|MapError|ModuleError|CompileError|StudioError|ExampleError"
            r"|StandardError|BusinessError|OwnerError)")
    literal = re.compile(gate + r'\(\s*"([a-z_]+)"')
    any_raise = re.compile(gate + r"\(")

    raised, sites = set(), 0
    for path, gate in GATES.items():
        source = (ROOT / path).read_text(encoding="utf-8")
        assert f"{gate}(" in source, path
        raised |= set(literal.findall(source))
        sites += len(any_raise.findall(source))

    # Both directions. Nothing raised is missing from the list, and nothing on
    # the list is dead — a code nobody raises is a promise to a caller who will
    # wait for it forever.
    assert raised == set(CODES), {
        "raised but not listed": sorted(raised - set(CODES)),
        "listed but never raised": sorted(set(CODES) - raised),
    }
    # And every raise site passes one: a site still handing over prose would not
    # have matched `literal`, and the two counts would disagree.
    assert len(literal.findall(
        "\n".join((ROOT / p).read_text(encoding="utf-8") for p in GATES))) == sites


# ---- the repair is computed, not described --------------------------------

def _draft(tmp_path, classes, slots, imports=None, name="probe"):
    document = {
        "id": f"https://probe.example/{name}",
        "name": f"probe_{name}",
        "prefixes": {"linkml": "https://w3id.org/linkml/",
                     "pb": f"https://probe.example/{name}/"},
        "default_prefix": "pb",
        "default_range": "string",
        "imports": imports or ["linkml:types", f"{CORE}@v2"],
        "classes": classes,
        "slots": slots,
        "annotations": {"valid_from": "2026-09-01T00:00:00+00:00",
                        "transcript": "t.txt"},
    }
    path = tmp_path / f"{name}.draft.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    (tmp_path / "t.txt").write_text("probe", encoding="utf-8")
    return path


def test_an_unfilled_binding_hands_back_the_slots_that_would_fit(conn, built, tmp_path):
    """The hole, and the finite set that fits it — read off the ranges.

    This is the difference between a blank page and a question. `amount` ranges
    over a decimal, so the answer is among this class's decimal slots and
    nowhere else; `affects` ranges over Resource, so the answer is among the
    slots pointing at one. Neither list was written down anywhere.
    """
    draft = _draft(
        tmp_path,
        classes={"Delivery": {"mixins": ["Flow"],
                              "slots": ["crates", "weight", "item", "day"]}},
        slots={
            "crates": {"slot_uri": "pb:crates", "range": "decimal"},
            "weight": {"slot_uri": "pb:weight", "range": "decimal"},
            "item": {"is_a": "affects", "slot_uri": "pb:item"},
            "day": {"is_a": "moment", "slot_uri": "pb:day", "range": "date"},
        },
    )
    with pytest.raises(DraftError) as caught:
        seal(conn, draft, actor_id="test", into=tmp_path / "out", store=built)

    refusal = caught.value
    assert refusal.code == "binding_unfilled"
    assert refusal.where == "Delivery.amount"
    # Both decimal slots, and neither the date nor the reference: the range is
    # doing the work, and nothing here guesses which of the two is the amount.
    assert refusal.repairs[0].options == ("crates", "weight")
    assert "is_a: amount" in refusal.repairs[0].do


def test_a_rule_naming_a_class_that_is_not_there_hands_back_the_ones_that_are(built):
    """The compiler's refusals enumerate too, and from the same closure."""
    from compile import _read_aggregate
    from generate import read_map

    map_ = read_map(built.path(APP_NAME, APP_VERSION), built)
    with pytest.raises(Refusal) as caught:
        _read_aggregate(map_, "probe.column", {
            "over": "NoSuchThing", "sum": "x", "by": {"a": "b"}})

    assert caught.value.code == "not_a_class"
    # Two answers, and they are different answers. The classes an entity can
    # be, and — separately — the roles a rule could be written against instead.
    classes, roles = caught.value.repairs
    assert "inventory__StockMovement" in classes.options and "Flow" not in classes.options
    assert roles.options == ("Event", "Flow", "Resource", "Thing")


# ---- check: every refusal at once, instead of the first one ---------------

def test_an_application_that_holds_says_so_and_names_its_tables(built):
    from compile import tables
    from generate import read_map

    report = check(built, APP_NAME, APP_VERSION)
    assert report["clean"] is True
    assert report["refusals"] == []
    assert [t["class"] for t in report["tables"]] == \
        tables(read_map(built.path(APP_NAME, APP_VERSION), built))
    assert all(t["holds"] for t in report["tables"])


def test_check_collects_every_refusal_rather_than_stopping_at_the_first(built):
    """A gate stops; a page cannot afford to.

    Two tables, each broken in its own way. The compiler would raise the first
    and say nothing about the second, which is right for a gate in the middle
    of emitting SQL and useless to somebody deciding what to fix.
    """
    document = {
        "id": "https://probe.example/two",
        "name": "probe_two",
        "prefixes": {"linkml": "https://w3id.org/linkml/",
                     "pb": "https://probe.example/two/"},
        "default_prefix": "pb",
        "default_range": "string",
        "imports": ["linkml:types", f"{CORE}@v2"],
        "classes": {
            "First": {"slots": ["a_total"]},
            "Second": {"slots": ["b_total"]},
        },
        "slots": {
            "a_total": {"slot_uri": "pb:a_total", "range": "decimal",
                        "annotations": {"aggregate": {"value": {
                            "over": "Nowhere", "sum": "x", "by": {"k": "y"}}}}},
            "b_total": {"slot_uri": "pb:b_total", "range": "decimal",
                        "annotations": {"aggregate": {"value": {
                            "over": "Flow", "sum": "amount"}}}},
        },
        "version": "v1",
        "annotations": {"valid_from": "2026-09-01T00:00:00+00:00"},
    }
    view = built.view(yaml.safe_dump(document, sort_keys=False))
    map_ = {"path": Path("probe_two.yaml"), "view": view, "version": "v1",
            "label": "probe_two@v1"}

    report = check(built, "probe_two", "v1", map_=map_)
    assert report["clean"] is False
    by_class = {r["class"]: r for r in report["refusals"]}
    # Two tables, two different problems. The first names a class nothing
    # declares; the second names a role, which is fine in itself, but this
    # closure holds core alone and nothing in it has promised to be a Flow.
    assert by_class["First"]["code"] == "not_a_class"
    assert by_class["Second"]["code"] == "binding_unfilled"
    # Both, in one read, each with somewhere to go next.
    assert all(r["repairs"] for r in report["refusals"])
    assert [t["holds"] for t in report["tables"]] == [False, False]


# ---- the swap report carries the refusal whole ----------------------------

def test_a_rule_that_cannot_survive_a_swap_says_what_to_do_about_it(conn, built):
    """The question somebody actually arrives with: what must I add?

    @demo/stock@v1 writes its rules against @demo/inventory's own class. Asked
    to move onto the rival's module, it goes dark — and the report carries the
    refusal that made it go dark, repairs and all, so the answer (write the
    rule against a role that both modules fill) is on the page rather than left
    to the reader.
    """
    report = roles_read.fit(built, STOCK, "v1", SWAP_VERSION, conn=conn)
    assert not report["clean"]

    dark = report["dark"][0]
    refusal = dark["refusal"]
    assert refusal["code"] == "not_a_class"
    assert refusal["gate"] == "the compiler"
    assert dark["why"] == refusal["sentence"]
    # And the way out is on the page: write it against a role the new module
    # fills. That is the whole argument of the slice before this one, arriving
    # as an instruction rather than as a lesson.
    assert "Flow" in refusal["repairs"][1]["options"]

    # And the one that can move carries no refusal at all, because there is
    # nothing to repair.
    assert roles_read.fit(built, STOCK, APP_VERSION, SWAP_VERSION,
                          conn=conn)["dark"] == []


# ---- what the API sends ---------------------------------------------------

def test_the_api_sends_the_structure_beside_the_sentence(built, monkeypatch):
    from starlette.testclient import TestClient

    from components.api.app import app

    monkeypatch.setenv("UNITI_PACKAGES", os.pathsep.join(str(r) for r in built.roots))
    client = TestClient(app)

    answer = client.get("/api/app/projection", params={
        "name": APP_NAME, "version": APP_VERSION, "class": "Nothing"})
    assert answer.status_code == 400
    body = answer.json()
    # The sentence stays where every caller already looks for it.
    assert body["error"] == body["refusal"]["sentence"]
    assert body["refusal"]["code"] == "no_such_class"
    assert "IngredientStock" in body["refusal"]["repairs"][0]["options"]

    # The store not holding something is still a 404, because the question
    # there is whether the thing exists at all.
    missing = client.get("/api/app", params={"name": "@nobody/nothing",
                                             "version": "v1"})
    assert missing.status_code == 404
    assert missing.json()["refusal"]["code"] == "no_such_module"

    held = client.get("/api/app/check", params={"name": APP_NAME,
                                                "version": APP_VERSION})
    assert held.status_code == 200
    assert held.json()["clean"] is True

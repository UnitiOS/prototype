"""The authoring loop, end to end: Studio writes a projection that computes.

This is the thing Prototype 2 exists to show. A module is composed through the
write gate — classes, slots, and the rules that derive a column — and what
comes out the other end is a *grouped* table the compiler fills from the log,
not a list of rows somebody has to type in.

Before the gate could write `aggregate`, `parameter` and `equals_expression`,
a class could inherit Projection and carry no rule at all: it compiled to a
list of entities under a name that promised the opposite, and nothing said so.
"""

import json
from pathlib import Path

import pytest

from components.agent.studio_server import StudioTools
from components.generator.generate import read_map
from components.compiler.compile import plan_for
from tests.p2.conftest import package_sandbox

PKG = "@community/authoring_loop"


def _rule(spec, as_text):
    """A rule as an object, or as the JSON text a model often sends instead."""
    return json.dumps(spec) if as_text else spec


def _compose(tools, as_text=False):
    """One module: a thing, a place, a movement between them, and a balance."""
    assert tools.init_package(
        package_path=PKG, title="Authoring Loop", domain="inventory",
        author="test_runner",
    )["status"] == "INITIALIZED"

    # What the business refers to.
    tools.propose_patch(
        package_path=PKG, class_name="TrackedItem", archetype="Resource",
        description="A thing that is counted and has a price.",
        slots=["item_code", "unit_price"],
        slot_definitions={
            "item_code": {"range": "string", "identifier": True,
                          "slot_uri": "inv:batch_id"},
            "unit_price": {"range": "decimal", "slot_uri": "proc:unit_price"},
        },
    )
    tools.propose_patch(
        package_path=PKG, class_name="HoldingSite", archetype="Resource",
        description="A place a thing can be held.",
        slots=["site_code"],
        slot_definitions={"site_code": {"range": "string", "identifier": True}},
    )

    # What the business writes down.
    tools.propose_patch(
        package_path=PKG, class_name="Transfer", archetype="Event",
        description="A quantity of one thing arriving at one place.",
        slots=["transfer_item", "transfer_site", "transfer_quantity"],
        slot_definitions={
            "transfer_item": {"range": "TrackedItem"},
            "transfer_site": {"range": "HoldingSite", "slot_uri": "inv:target_location"},
            "transfer_quantity": {"range": "decimal", "slot_uri": "inv:quantity"},
        },
    )

    # What is computed, and stated by nobody.
    return tools.propose_patch(
        package_path=PKG, class_name="HeldBalance", archetype="Projection",
        description="How much of each thing stands at each place, and its value.",
        slots=["held_item", "held_site", "held_quantity", "held_price", "held_value"],
        slot_definitions={
            "held_item": {"range": "TrackedItem"},
            "held_site": {"range": "HoldingSite"},
            "held_quantity": {
                "range": "decimal",
                "aggregate": _rule({
                    "over": "Transfer",
                    "sum": "transfer_quantity",
                    "by": {"held_item": "transfer_item",
                           "held_site": "transfer_site"},
                }, as_text),
            },
            "held_price": {
                "range": "decimal",
                "parameter": _rule({"of": "held_item", "slot": "unit_price"}, as_text),
            },
            "held_value": {
                "range": "decimal",
                "equals_expression": "{held_quantity} * {held_price}",
            },
        },
    )


@pytest.mark.parametrize("as_text", [False, True], ids=["object", "json-text"])
def test_studio_authors_a_projection_that_computes(as_text):
    with package_sandbox() as sandbox:
        tools = StudioTools()
        out = _compose(tools, as_text)
        assert out.get("status") != "REJECTED", out

        # The linter passes it, which is what lets it be sealed at all.
        audit = tools.validate_linter(PKG)
        assert audit["error_count"] == 0, audit["diagnostics"]
        assert audit["can_seal"] is True

        # Sealing stamps the version a map needs before anything reads it.
        tools.seal_package(PKG, version="v1", author="test_runner")

        schema = Path(sandbox) / "@community" / "authoring_loop" / "schema" / "domain.yaml"
        plan = plan_for(read_map(schema), "HeldBalance")

    # A grouping, not a list: the compiler fills it from the log.
    assert plan["shape"] == "grouped"
    assert sorted(plan["keys"]) == ["held_item", "held_site"]

    kinds = {col["name"]: col["kind"] for col in plan["columns"]}
    assert kinds["held_item"] == "key"
    assert kinds["held_site"] == "key"
    assert kinds["held_quantity"] == "aggregate"
    assert kinds["held_price"] == "parameter"
    assert kinds["held_value"] == "expression"


def test_a_projection_that_computes_nothing_is_refused():
    """LINT-006: a Projection with no rule is a table to be filled in by hand."""
    with package_sandbox():
        tools = StudioTools()
        tools.init_package(package_path=PKG, title="Empty Twin",
                           domain="inventory", author="test_runner")
        tools.propose_patch(
            package_path=PKG, class_name="HollowBalance", archetype="Projection",
            description="Claims to be computed; computes nothing.",
            slots=["hollow_quantity"],
            slot_definitions={"hollow_quantity": {"range": "decimal"}},
        )
        audit = tools.validate_linter(PKG)

    refusals = [d for d in audit["diagnostics"] if d["rule_id"] == "LINT-006"]
    assert refusals, audit["diagnostics"]
    assert "HollowBalance" in refusals[0]["target"]
    assert audit["can_seal"] is False


def test_a_column_may_carry_only_one_rule():
    """The compiler refuses a column with two rules; the gate refuses it first."""
    with package_sandbox():
        tools = StudioTools()
        tools.init_package(package_path=PKG, title="Two Rules",
                           domain="inventory", author="test_runner")
        out = tools.propose_patch(
            package_path=PKG, class_name="Confused", archetype="Projection",
            description="One column, two rules.",
            slots=["muddled"],
            slot_definitions={
                "muddled": {
                    "range": "decimal",
                    "equals_expression": "{muddled}",
                    "parameter": {"of": "muddled", "slot": "whatever"},
                },
            },
        )

    assert out["status"] == "REJECTED"
    assert "one rule" in out["error"]


def test_the_gate_refuses_a_key_it_does_not_write():
    """A dropped key is a rule the author believes they wrote."""
    with package_sandbox():
        tools = StudioTools()
        tools.init_package(package_path=PKG, title="Typo",
                           domain="inventory", author="test_runner")
        out = tools.propose_patch(
            package_path=PKG, class_name="Mistyped", archetype="Projection",
            description="A rule spelled wrong.",
            slots=["total"],
            slot_definitions={"total": {"range": "decimal", "aggregat": {"over": "X"}}},
        )

    assert out["status"] == "REJECTED"
    assert "aggregat" in out["error"]


def _two_things(tools):
    tools.init_package(package_path=PKG, title="Whole Classes",
                       domain="inventory", author="test_runner")
    tools.propose_patch(
        package_path=PKG, class_name="TrackedItem", archetype="Resource",
        description="A thing with a price.",
        slots=["item_code", "unit_price"],
        slot_definitions={"item_code": {"range": "string", "identifier": True},
                          "unit_price": {"range": "decimal"}},
    )
    tools.propose_patch(
        package_path=PKG, class_name="Transfer", archetype="Event",
        description="A thing moving.",
        slots=["transfer_code", "transfer_item"],
        slot_definitions={"transfer_code": {"range": "string", "identifier": True},
                          "transfer_item": {"range": "TrackedItem"}},
    )


def _schema_text(sandbox):
    return (Path(sandbox) / "@community" / "authoring_loop" / "schema" / "domain.yaml").read_text(encoding="utf-8")


def test_a_rule_that_is_neither_object_nor_json_is_refused():
    with package_sandbox():
        tools = StudioTools()
        _two_things(tools)
        out = tools.propose_patch(
            package_path=PKG, class_name="Tally", archetype="Projection",
            description="A rule that is a number.",
            slots=["tally"],
            slot_definitions={"tally": {"range": "decimal", "aggregate": 123}},
        )
    assert out["status"] == "REJECTED"
    assert "must be an object" in out["error"]


def test_identifier_on_a_shared_slot_is_refused_and_nothing_is_written():
    """Slots are shared by name: a key made an identifier lands on the Event too."""
    with package_sandbox() as sandbox:
        tools = StudioTools()
        _two_things(tools)
        before = _schema_text(sandbox)
        out = tools.propose_patch(
            package_path=PKG, class_name="Balance", archetype="Projection",
            description="Keyed by the thing.",
            slots=["transfer_item"],
            slot_definitions={"transfer_item": {"range": "TrackedItem", "identifier": True}},
        )
        after = _schema_text(sandbox)
    assert out["status"] == "REJECTED"
    assert "identifier" in out["error"] and "Transfer" in out["error"]
    assert before == after


def test_a_rule_on_a_stated_field_is_refused():
    """A price recorded on a Resource cannot become a computed column."""
    with package_sandbox():
        tools = StudioTools()
        _two_things(tools)
        out = tools.propose_patch(
            package_path=PKG, class_name="Balance", archetype="Projection",
            description="Reuses the price slot as a parameter.",
            slots=["transfer_item", "unit_price"],
            slot_definitions={"unit_price": {
                "range": "decimal",
                "parameter": {"of": "transfer_item", "slot": "unit_price"}}},
        )
    assert out["status"] == "REJECTED"
    assert "TrackedItem" in out["error"] and "not a Projection" in out["error"]


def test_two_columns_on_one_predicate_are_refused():
    with package_sandbox():
        tools = StudioTools()
        _two_things(tools)
        out = tools.propose_patch(
            package_path=PKG, class_name="Transfer", archetype="Event",
            description="Two quantities on one predicate.",
            slots=["sent_quantity", "received_quantity"],
            slot_definitions={
                "sent_quantity": {"range": "decimal", "slot_uri": "inv:quantity"},
                "received_quantity": {"range": "decimal", "slot_uri": "inv:quantity"},
            },
        )
    assert out["status"] == "REJECTED"
    assert "inv:quantity" in out["error"]


def test_minted_uris_belong_to_the_package_not_to_core():
    with package_sandbox() as sandbox:
        tools = StudioTools()
        _two_things(tools)
        text = _schema_text(sandbox)
    assert "slot_uri: inventory:transfer_code" in text
    assert "uniti:transfer_code" not in text

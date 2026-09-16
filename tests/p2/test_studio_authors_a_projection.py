"""The authoring loop, end to end: Studio writes a projection that computes.

This is the thing Prototype 2 exists to show. A module is composed through the
write gate — classes, slots, and the rules that derive a column — and what
comes out the other end is a *grouped* table the compiler fills from the log,
not a list of rows somebody has to type in.

Before the gate could write `aggregate`, `parameter` and `equals_expression`,
a class could inherit Projection and carry no rule at all: it compiled to a
list of entities under a name that promised the opposite, and nothing said so.
"""

from pathlib import Path

import pytest

from components.agent.studio_server import StudioTools
from components.generator.generate import read_map
from components.compiler.compile import plan_for
from tests.p2.conftest import package_sandbox

PKG = "@community/authoring_loop"


def _compose(tools):
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
            "transfer_item": {"range": "TrackedItem", "slot_uri": "inv:quantity"},
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
                "aggregate": {
                    "over": "Transfer",
                    "sum": "transfer_quantity",
                    "by": {"held_item": "transfer_item",
                           "held_site": "transfer_site"},
                },
            },
            "held_price": {
                "range": "decimal",
                "parameter": {"of": "held_item", "slot": "unit_price"},
            },
            "held_value": {
                "range": "decimal",
                "equals_expression": "{held_quantity} * {held_price}",
            },
        },
    )


def test_studio_authors_a_projection_that_computes():
    with package_sandbox() as sandbox:
        tools = StudioTools()
        assert _compose(tools).get("status") != "REJECTED"

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

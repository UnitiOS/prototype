"""Which of five LinkML metamodel features survive `seal`.

`business/trial/draft.yaml` declares them, `seal` was run against a throwaway
database with `--into business/trial`, and `business/trial/v1.yaml` is what
came out. These tests read that sealed file — not a draft, not a fixture — and
say for each feature whether it is still there and still visible through
`SchemaView`, including through `induced_slot`, which is the door the
generator uses.

Present here means present in the file. It says nothing about whether anything
can act on it: `rules` survives the seal intact and `linkml_runtime` raises
`NotImplementedError` the moment it is asked to apply one. See LOG.md.

No database. The sealed file is the fixture.

Run: .venv/Scripts/python.exe -m pytest tests/trial -q
"""

from pathlib import Path

import pytest
from linkml_runtime import SchemaView

SEALED = Path(__file__).resolve().parent.parent.parent / "business" / "trial" / "v1.yaml"


@pytest.fixture(scope="module")
def view():
    return SchemaView(SEALED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def induced(view):
    """Reading's induced slots by name — what a generator actually reads."""
    return {slot.name: slot for slot in view.class_induced_slots("Reading")}


def test_the_sealed_file_is_a_version(view):
    """Everything below is about a sealed map, not a draft."""
    assert view.schema.version == "v1"


def test_equals_expression_survives(view, induced):
    """Present, verbatim, and unchanged by induction."""
    assert view.get_slot("total_amount").equals_expression == "{left_amount} + {right_amount}"
    assert induced["total_amount"].equals_expression == "{left_amount} + {right_amount}"


def test_rules_survive(view):
    """The whole block: the rule, its precondition and its postcondition."""
    rules = view.get_class("Reading").rules
    assert len(rules) == 1
    assert rules[0].preconditions.slot_conditions["left_amount"].minimum_value == 1
    assert rules[0].postconditions.slot_conditions["right_amount"].required is True


def test_unit_survives_with_its_ucum_code(view, induced):
    assert view.get_slot("held_amount").unit.ucum_code == "L"
    assert induced["held_amount"].unit.ucum_code == "L"


def test_unique_keys_survive(view):
    key = view.get_class("Reading").unique_keys["by_id"]
    assert list(key.unique_key_slots) == ["thing_id"]


def test_designates_type_survives(view, induced):
    assert view.get_slot("thing_kind").designates_type is True
    assert induced["thing_kind"].designates_type is True


def test_no_feature_reaches_the_log(view):
    """The seal writes facts, and none of the five is one.

    Every one of the five is map metadata: it says how to read a value or what
    a value must satisfy, never what anyone said. `seal` writes only
    `annotations.facts`, so all five stay in the file and nothing about them is
    in the kernel — which is why a test can check them without a database.
    """
    assert (view.schema.annotations or {}).keys() >= {"valid_from", "sealed_at"}
    assert "facts" not in (view.schema.annotations or {})

"""Unit tests for the compiler's scoped aggregate functionality.

Tests that `aggregate` annotations can declare a `where` block with `is_a`
constraints on source slots, that invalid constraints are refused with
MapError, that non-existent classes are refused, or missing designates_type,
and that emit produces the expected SQL with class-hierarchy joins.
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components"))

from compile import MapError, _read_aggregate
from generate import read_map

DEMO_MAP = ROOT / "business" / "sorella_demo" / "v5.yaml"


@pytest.fixture(scope="module")
def map_():
    return read_map(DEMO_MAP)


def test_read_aggregate_parses_valid_where(map_):
    spec = {
        "over": "StockMovement",
        "sum": "movement_quantity",
        "by": {
            "ingredient_on_hand": "movement_ingredient",
            "ingredient_where": "movement_into",
            "ingredient_unit": "movement_unit",
        },
        "where": {
            "movement_into": {
                "is_a": "InternalLocation",
            },
        },
    }
    parsed = _read_aggregate(map_, "test.slot", spec)
    assert parsed["where"] == [
        {
            "slot_name": "movement_into",
            "slot_uri": "sorella:movement_into",
            "type_slot_uri": "sorella:entity_class",
            "descendants": ["InternalLocation"],
        }
    ]


def test_read_aggregate_refuses_unknown_where_condition(map_):
    spec = {
        "over": "StockMovement",
        "sum": "movement_quantity",
        "by": {"ingredient_on_hand": "movement_ingredient"},
        "where": {"movement_into": {"equals": "Kitchen bin"}},
    }
    with pytest.raises(MapError, match="a `where` condition must be `is_a`"):
        _read_aggregate(map_, "test.slot", spec)


def test_read_aggregate_refuses_nonexistent_class(map_):
    spec = {
        "over": "StockMovement",
        "sum": "movement_quantity",
        "by": {"ingredient_on_hand": "movement_ingredient"},
        "where": {"movement_into": {"is_a": "NonExistentPlace"}},
    }
    with pytest.raises(MapError, match="is not a class"):
        _read_aggregate(map_, "test.slot", spec)


def test_read_aggregate_refuses_unknown_slot_in_where(map_):
    spec = {
        "over": "StockMovement",
        "sum": "movement_quantity",
        "by": {"ingredient_on_hand": "movement_ingredient"},
        "where": {"non_existent_slot": {"is_a": "InternalLocation"}},
    }
    with pytest.raises(MapError, match="has no slot for"):
        _read_aggregate(map_, "test.slot", spec)


def test_aggregate_cte_includes_where_filter():
    from compile import _aggregate_cte
    spec = {
        "operator": "sum",
        "over": "StockMovement",
        "measure_uri": "sorella:movement_quantity",
        "measure_type": "numeric",
        "by": {
            "ingredient_on_hand": "sorella:movement_ingredient",
            "ingredient_where": "sorella:movement_into",
        },
        "where": [
            {
                "slot_name": "movement_into",
                "slot_uri": "sorella:movement_into",
                "type_slot_uri": "sorella:entity_class",
                "descendants": ["InternalLocation"],
            }
        ],
    }
    cte = _aggregate_cte(
        spec, "ingredient_in", "total_0", "source_0",
        ["ingredient_on_hand", "ingredient_where"], "t0_"
    )
    assert "JOIN stated t0_w0_v ON t0_w0_v.subject_id = r.subject_id" in cte
    assert "t0_w0_v.slot = 'sorella:movement_into'" in cte
    assert "JOIN registry t0_w0_r ON t0_w0_r.uri = t0_w0_v.value" in cte
    assert "JOIN stated t0_w0_c ON t0_w0_c.subject_id = t0_w0_r.entity_id" in cte
    assert "t0_w0_c.slot = 'sorella:entity_class'" in cte
    assert "t0_w0_c.value = ANY (ARRAY['InternalLocation'])" in cte


def test_read_aggregate_rejects_malformed_convert(map_):
    # Missing required keys in convert block
    spec = {
        "over": "StockMovement",
        "sum": "movement_quantity",
        "by": {"ingredient_on_hand": "movement_ingredient"},
        "convert": {"using": "UnitConversion", "on": {"conversion_unit": "movement_unit"}},
    }
    with pytest.raises(MapError, match="must have `using`, `on`, and `factor`"):
        _read_aggregate(map_, "test.slot", spec)

    # Non-existent class in convert.using
    spec = {
        "over": "StockMovement",
        "sum": "movement_quantity",
        "by": {"ingredient_on_hand": "movement_ingredient"},
        "convert": {"using": "NoSuchConversionClass", "on": {"x": "movement_unit"}, "factor": "y"},
    }
    with pytest.raises(MapError, match="is not a class"):
        _read_aggregate(map_, "test.slot", spec)


def test_aggregate_cte_includes_convert():
    from compile import _aggregate_cte
    spec = {
        "operator": "sum",
        "over": "StockMovement",
        "measure_uri": "sorella:movement_quantity",
        "measure_type": "numeric",
        "by": {
            "ingredient_on_hand": "sorella:movement_ingredient",
            "ingredient_where": "sorella:movement_into",
        },
        "convert": {
            "using": "UnitConversion",
            "type_slot_uri": "sorella:entity_class",
            "descendants": ["UnitConversion"],
            "factor_slot_uri": "sorella:conversion_factor",
            "on": [
                {
                    "conv_slot_uri": "sorella:conversion_ingredient",
                    "source_slot_uri": "sorella:movement_ingredient",
                },
                {
                    "conv_slot_uri": "sorella:conversion_unit",
                    "source_slot_uri": "sorella:movement_unit",
                },
            ],
        },
    }
    cte = _aggregate_cte(
        spec, "ingredient_in", "total_0", "source_0",
        ["ingredient_on_hand", "ingredient_where"], "t0_"
    )
    assert "t0_cv ON t0_cv.match_0 = t0_cv_s0.value" in cte
    assert "t0_cv.match_1 = t0_cv_s1.value" in cte
    assert "sum(((t0_m.value)::numeric * coalesce(t0_cv.factor, 1))) AS \"ingredient_in\"" in cte


def test_plan_and_emit_stock_reconciliation(map_):
    from compile import plan, emit
    p = plan(map_, "StockReconciliation")
    assert p["table"] == "p_stock_reconciliation"
    assert len(p["keys"]) == 2
    assert "reconciliation_in" in p["aggregates"]
    assert "reconciliation_out" in p["aggregates"]
    assert "reconciliation_counted" in p["aggregates"]
    assert "reconciliation_expected" in p["expressions"]
    assert "reconciliation_variance" in p["expressions"]
    assert "reconciliation_variance_value" in p["expressions"]
    ddl, select = emit(map_, p)
    assert "CREATE TABLE \"p_stock_reconciliation\"" in ddl[1]
    assert "GROUP BY 1, 2" in select


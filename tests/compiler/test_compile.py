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

MAP = Path(__file__).resolve().parent / "fixtures" / "v1.yaml"


@pytest.fixture(scope="module")
def map_():
    return read_map(MAP)


def test_read_aggregate_parses_valid_where(map_):
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {
            "rec_thing": "transfer_thing",
            "rec_place": "transfer_to",
            "rec_measure": "transfer_measure",
        },
        "where": {
            "transfer_to": {
                "is_a": "InnerPlace",
            },
        },
    }
    parsed = _read_aggregate(map_, "test.slot", spec)
    assert parsed["where"] == [
        {
            "slot_name": "transfer_to",
            "slot_uri": "fx:transfer_to",
            "type_slot_uri": "fx:entity_class",
            "descendants": ["InnerPlace"],
        }
    ]


def test_read_aggregate_refuses_unknown_where_condition(map_):
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "where": {"transfer_to": {"equals": "some place"}},
    }
    with pytest.raises(MapError, match="a `where` condition must be `is_a`"):
        _read_aggregate(map_, "test.slot", spec)


def test_read_aggregate_refuses_nonexistent_class(map_):
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "where": {"transfer_to": {"is_a": "NoSuchPlace"}},
    }
    with pytest.raises(MapError, match="is not a class"):
        _read_aggregate(map_, "test.slot", spec)


def test_read_aggregate_refuses_unknown_slot_in_where(map_):
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "where": {"non_existent_slot": {"is_a": "InnerPlace"}},
    }
    with pytest.raises(MapError, match="has no slot for"):
        _read_aggregate(map_, "test.slot", spec)


def test_aggregate_cte_includes_where_filter():
    from compile import _aggregate_cte
    spec = {
        "operator": "sum",
        "over": "Transfer",
        "measure_uri": "fx:transfer_quantity",
        "measure_type": "numeric",
        "by": {
            "rec_thing": "fx:transfer_thing",
            "rec_place": "fx:transfer_to",
        },
        "where": [
            {
                "slot_name": "transfer_to",
                "slot_uri": "fx:transfer_to",
                "type_slot_uri": "fx:entity_class",
                "descendants": ["InnerPlace"],
            }
        ],
    }
    cte = _aggregate_cte(
        spec, "rec_in", "total_0", "source_0",
        ["rec_thing", "rec_place"], "t0_"
    )
    assert "JOIN stated t0_w0_v ON t0_w0_v.subject_id = r.subject_id" in cte
    assert "t0_w0_v.slot = 'fx:transfer_to'" in cte
    assert "JOIN registry t0_w0_r ON t0_w0_r.uri = t0_w0_v.value" in cte
    assert "JOIN stated t0_w0_c ON t0_w0_c.subject_id = t0_w0_r.entity_id" in cte
    assert "t0_w0_c.slot = 'fx:entity_class'" in cte
    assert "t0_w0_c.value = ANY (ARRAY['InnerPlace'])" in cte


def test_read_aggregate_rejects_malformed_convert(map_):
    # Missing required keys in convert block
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "convert": {"using": "MeasureConversion", "on": {"conversion_measure": "transfer_measure"}},
    }
    with pytest.raises(MapError, match="must have `using`, `on`, and `factor`"):
        _read_aggregate(map_, "test.slot", spec)

    # Non-existent class in convert.using
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "convert": {"using": "NoSuchConversionClass", "on": {"x": "transfer_measure"}, "factor": "y"},
    }
    with pytest.raises(MapError, match="is not a class"):
        _read_aggregate(map_, "test.slot", spec)


def test_aggregate_cte_includes_convert():
    from compile import _aggregate_cte
    spec = {
        "operator": "sum",
        "over": "Transfer",
        "measure_uri": "fx:transfer_quantity",
        "measure_type": "numeric",
        "by": {
            "rec_thing": "fx:transfer_thing",
            "rec_place": "fx:transfer_to",
        },
        "convert": {
            "using": "MeasureConversion",
            "type_slot_uri": "fx:entity_class",
            "descendants": ["MeasureConversion"],
            "factor_slot_uri": "fx:conversion_factor",
            "on": [
                {
                    "conv_slot_uri": "fx:conversion_thing",
                    "source_slot_uri": "fx:transfer_thing",
                },
                {
                    "conv_slot_uri": "fx:conversion_measure",
                    "source_slot_uri": "fx:transfer_measure",
                },
            ],
        },
    }
    cte = _aggregate_cte(
        spec, "rec_in", "total_0", "source_0",
        ["rec_thing", "rec_place"], "t0_"
    )
    assert "t0_cv ON t0_cv.match_0 = t0_cv_s0.value" in cte
    assert "t0_cv.match_1 = t0_cv_s1.value" in cte
    assert "sum(((t0_m.value)::numeric * coalesce(t0_cv.factor, 1))) AS \"rec_in\"" in cte


def test_plan_and_emit_reconciliation(map_):
    from compile import plan, emit
    p = plan(map_, "Reconciliation")
    assert p["table"] == "p_reconciliation"
    assert len(p["keys"]) == 2
    assert "rec_in" in p["aggregates"]
    assert "rec_out" in p["aggregates"]
    assert "rec_counted" in p["aggregates"]
    assert "rec_expected" in p["expressions"]
    assert "rec_variance" in p["expressions"]
    assert "rec_variance_value" in p["expressions"]
    ddl, select = emit(map_, p)
    assert "CREATE TABLE \"p_reconciliation\"" in ddl[1]
    assert "GROUP BY 1, 2" in select


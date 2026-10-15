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
            "slot_uris": ["https://uniti.example/fixture/transfer_to"],
            "type_slot_uri": "https://uniti.example/fixture/entity_class",
            "descendants": ["https://uniti.example/fixture/InnerPlace"],
        }
    ]


def test_read_aggregate_refuses_unknown_where_condition(map_):
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "where": {"transfer_to": {"like": "some place"}},
    }
    with pytest.raises(MapError) as caught:
        _read_aggregate(map_, "test.slot", spec)
    assert caught.value.code == "where_not_is_a"


def test_read_aggregate_refuses_nonexistent_class(map_):
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "where": {"transfer_to": {"is_a": "NoSuchPlace"}},
    }
    with pytest.raises(MapError) as caught:
        _read_aggregate(map_, "test.slot", spec)
    assert caught.value.code == "not_a_class"
    assert "Transfer" in caught.value.repairs[0].options


def test_read_aggregate_refuses_unknown_slot_in_where(map_):
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "where": {"non_existent_slot": {"is_a": "InnerPlace"}},
    }
    with pytest.raises(MapError) as caught:
        _read_aggregate(map_, "test.slot", spec)
    assert caught.value.code == "no_such_slot"
    assert "transfer_to" in caught.value.repairs[0].options


def test_aggregate_cte_includes_where_filter():
    from compile import _aggregate_cte
    spec = {
        "operator": "sum",
        "over": "Transfer",
        "measure_uris": ["https://uniti.example/fixture/transfer_quantity"],
        "measure_type": "numeric",
        "by": {
            "rec_thing": ["https://uniti.example/fixture/transfer_thing"],
            "rec_place": ["https://uniti.example/fixture/transfer_to"],
        },
        "where": [
            {
                "slot_name": "transfer_to",
                "slot_uris": ["https://uniti.example/fixture/transfer_to"],
                "type_slot_uri": "https://uniti.example/fixture/entity_class",
                "descendants": ["InnerPlace"],
            }
        ],
    }
    cte = _aggregate_cte(
        spec, "rec_in", "total_0", "source_0",
        ["rec_thing", "rec_place"], "t0_"
    )
    assert "JOIN stated t0_w0_v ON t0_w0_v.subject_id = r.subject_id" in cte
    assert "t0_w0_v.slot = 'https://uniti.example/fixture/transfer_to'" in cte
    assert "JOIN registry t0_w0_r ON t0_w0_r.uri = t0_w0_v.value" in cte
    assert "JOIN stated t0_w0_c ON t0_w0_c.subject_id = t0_w0_r.entity_id" in cte
    assert "t0_w0_c.slot = 'https://uniti.example/fixture/entity_class'" in cte
    assert "t0_w0_c.value = ANY (ARRAY['InnerPlace'])" in cte


def test_read_aggregate_rejects_malformed_convert(map_):
    # Missing required keys in convert block
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "convert": {"using": "MeasureConversion", "on": {"conversion_measure": "transfer_measure"}},
    }
    with pytest.raises(MapError) as caught:
        _read_aggregate(map_, "test.slot", spec)
    assert caught.value.code == "convert_keys"

    # Non-existent class in convert.using
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "convert": {"using": "NoSuchConversionClass", "on": {"x": "transfer_measure"}, "factor": "y"},
    }
    with pytest.raises(MapError) as caught:
        _read_aggregate(map_, "test.slot", spec)
    assert caught.value.code == "not_a_class"


def test_aggregate_cte_includes_convert():
    from compile import _aggregate_cte
    spec = {
        "operator": "sum",
        "over": "Transfer",
        "measure_uris": ["https://uniti.example/fixture/transfer_quantity"],
        "measure_type": "numeric",
        "by": {
            "rec_thing": ["https://uniti.example/fixture/transfer_thing"],
            "rec_place": ["https://uniti.example/fixture/transfer_to"],
        },
        "convert": {
            "using": "MeasureConversion",
            "type_slot_uri": "https://uniti.example/fixture/entity_class",
            "descendants": ["MeasureConversion"],
            "factor_slot_uri": "https://uniti.example/fixture/conversion_factor",
            "on": [
                {
                    "conv_slot_uri": "https://uniti.example/fixture/conversion_thing",
                    "source_slot_uris": ["https://uniti.example/fixture/transfer_thing"],
                },
                {
                    "conv_slot_uri": "https://uniti.example/fixture/conversion_measure",
                    "source_slot_uris": ["https://uniti.example/fixture/transfer_measure"],
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
    # No factor is assumed: a row that found none is flagged, not counted x1.
    assert "sum(((t0_m.value)::numeric * t0_cv.factor)) AS \"rec_in\"" in cte
    assert ("bool_or(t0_m.value IS NOT NULL AND t0_cv.factor IS NULL) "
            "AS \"unconverted rec_in\"") in cte


def _variant(tmp_path, change):
    """The fixture with one change, read back as a map."""
    import yaml
    document = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    change(document)
    path = tmp_path / "v1.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return read_map(path)


@pytest.mark.parametrize("rule", [
    {"equals_expression": "{thing_price} * 2"},
    {"annotations": {"parameter": {"value": {"of": "thing_base_measure",
                                             "slot": "measure_name"}}}},
])
def test_a_rule_on_a_class_whose_rows_are_recorded_is_refused(tmp_path, rule):
    """A class with no aggregate is a list of what people stated. Its columns
    are read out of the log and nothing computes them, so a rule there would
    be a column that is always empty — and a form field somebody types into.
    Refused, rather than left silent."""
    from compile import CompileError, plan_for

    def change(document):
        document["classes"]["Thing"]["slots"].append("thing_doubled")
        document["slots"]["thing_doubled"] = {
            "slot_uri": "fx:thing_doubled", "range": "decimal", **rule}

    variant = _variant(tmp_path, change)
    with pytest.raises(CompileError) as caught:
        plan_for(variant, "Thing")
    assert caught.value.code == "rule_on_a_recorded_class"
    assert "thing_doubled" in caught.value.got
    # The one class that computes is untouched by it.
    assert plan_for(variant, "Reconciliation")["shape"] == "grouped"


def test_check_says_a_rule_on_a_recorded_class_does_not_hold(tmp_path):
    """`check` is what Studio shows as a blocking hole, so this is the refusal
    a module author meets while typing, before anything is sealed."""
    from components.modules.check import check

    def change(document):
        document["classes"]["Thing"]["slots"].append("thing_doubled")
        document["slots"]["thing_doubled"] = {
            "slot_uri": "fx:thing_doubled", "range": "decimal",
            "equals_expression": "{thing_price} * 2"}

    report = check(None, "fixture", "v1", map_=_variant(tmp_path, change))
    assert not report["clean"]
    assert [(r["class"], r["code"]) for r in report["refusals"]] == [
        ("Thing", "rule_on_a_recorded_class")]


def _with_text_slot(document, class_name, slot_name):
    document["classes"][class_name]["slots"].append(slot_name)
    document["slots"][slot_name] = {"slot_uri": f"fx:{slot_name}", "range": "string"}


def test_a_conversion_matching_a_reference_to_text_is_refused(tmp_path):
    """`conversion_measure` names a Measure; `transfer_measure_code` is text.
    In the log one is a URI and the other is what somebody typed, so they
    never meet — and a conversion that never matches used to count as x1."""
    from compile import CompileError

    def change(document):
        _with_text_slot(document, "Transfer", "transfer_measure_code")

    variant = _variant(tmp_path, change)
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "convert": {"using": "MeasureConversion",
                    "on": {"conversion_measure": "transfer_measure_code"},
                    "factor": "conversion_factor"},
    }
    with pytest.raises(CompileError) as caught:
        _read_aggregate(variant, "test.slot", spec)
    assert caught.value.code == "key_kinds_differ"
    assert "transfer_measure_code" in caught.value.got


def test_a_conversion_between_unrelated_classes_is_refused(map_):
    """Two references can still never meet: a Thing is never a Measure."""
    from compile import CompileError
    spec = {
        "over": "Transfer",
        "sum": "transfer_quantity",
        "by": {"rec_thing": "transfer_thing"},
        "convert": {"using": "MeasureConversion",
                    "on": {"conversion_measure": "transfer_thing"},
                    "factor": "conversion_factor"},
    }
    with pytest.raises(CompileError) as caught:
        _read_aggregate(map_, "test.slot", spec)
    assert caught.value.code == "key_kinds_differ"


def test_a_grouping_that_meets_a_reference_with_text_is_refused(tmp_path):
    """A key column holds one kind of value. `rec_thing` names a Thing, and a
    source grouped into it by a text code would make rows of its own that no
    other aggregate ever lands in."""
    from compile import CompileError, plan

    def change(document):
        _with_text_slot(document, "CountLine", "count_thing_code")
        document["slots"]["rec_counted"]["annotations"]["aggregate"]["value"]["by"] = {
            "rec_thing": "count_thing_code", "rec_place": "count_place"}

    with pytest.raises(CompileError) as caught:
        plan(_variant(tmp_path, change), "Reconciliation")
    assert caught.value.code == "key_kinds_differ"
    assert "count_thing_code" in caught.value.got


class _OneMap:
    """Enough of a store for the loader to state facts under the fixture."""

    def path(self, name, version):
        return MAP

    def view(self, path):
        return read_map(MAP)["view"]


@pytest.fixture(scope="module")
def kernel():
    import os
    sys.path.insert(0, str(ROOT / "components" / "kernel"))
    from perform import connect
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn


# The log these tests read: stated once, at 2 January. One more fact is stated
# a year later, and only the test about it reads that far.
NOW = "2026-12-31T00:00:00+00:00"
A_YEAR_ON = "2027-06-30T00:00:00+00:00"


def _entity(uri, cls, **facts):
    return {"uri": uri, "class": cls, "facts": facts}


@pytest.fixture(scope="module")
def logged(kernel):
    sys.path.insert(0, str(ROOT / "scripts"))
    import load_facts
    load_facts.load(kernel, {"map": "@fx/fixture@v1", "actions": [{
        "action": "set_up", "valid_from": "2026-01-02T00:00:00+00:00",
        "entities": [
            _entity("fx:kg", "Measure", measure_name="kg"),
            _entity("fx:sack", "Measure", measure_name="sack"),
            _entity("fx:box", "Measure", measure_name="box"),
            _entity("fx:flour", "Thing", thing_name="flour", thing_base_measure="fx:kg"),
            _entity("fx:sugar", "Thing", thing_name="sugar", thing_base_measure="fx:kg"),
            _entity("fx:store", "InnerPlace", place_name="store"),
            _entity("fx:vendor", "OuterPlace", place_name="vendor"),
            _entity("fx:flour_sack", "MeasureConversion", conversion_thing="fx:flour",
                    conversion_measure="fx:sack", conversion_factor="25"),
            _entity("fx:sugar_kg", "MeasureConversion", conversion_thing="fx:sugar",
                    conversion_measure="fx:kg", conversion_factor="1"),
            _entity("fx:t1", "Transfer", transfer_thing="fx:flour", transfer_from="fx:vendor",
                    transfer_to="fx:store", transfer_quantity="2", transfer_measure="fx:sack"),
            _entity("fx:t2", "Transfer", transfer_thing="fx:flour", transfer_from="fx:vendor",
                    transfer_to="fx:store", transfer_quantity="5", transfer_measure="fx:box"),
            _entity("fx:t3", "Transfer", transfer_thing="fx:sugar", transfer_from="fx:vendor",
                    transfer_to="fx:store", transfer_quantity="3", transfer_measure="fx:kg"),
        ]}, {
        # A value no door would take any more; the loader is not a door.
        "action": "mistyped", "valid_from": "2027-01-01T00:00:00+00:00",
        "entities": [
            _entity("fx:t4", "Transfer", transfer_thing="fx:sugar", transfer_from="fx:vendor",
                    transfer_to="fx:store", transfer_quantity="lots", transfer_measure="fx:kg"),
        ]}]}, _OneMap(), actor_id="test")
    kernel.commit()
    return kernel


def _reconciled(kernel, map_, at=NOW):
    from compile import preview
    built = preview(kernel, map_, "Reconciliation", valid_at=at, as_of=A_YEAR_ON)
    names = [c["name"] for c in built["plan"]["columns"]]
    return {row[0]: dict(zip(names, row)) for row in built["rows"]}


def test_a_row_with_no_conversion_leaves_its_cell_empty(logged, map_):
    """Five boxes of flour have no conversion to anything. Counting them as
    five kilograms is a number that looks right and is not; leaving them out
    is a total that is short without saying so. The cell is empty instead,
    and a group whose rows all convert is untouched."""
    rows = _reconciled(logged, map_)
    assert rows["fx:flour"]["rec_in"] is None
    assert rows["fx:flour"]["rec_expected"] is None
    assert float(rows["fx:sugar"]["rec_in"]) == 3
    # Nothing converted out of the store, which is a nought and not a gap.
    assert float(rows["fx:flour"]["rec_out"]) == 0


def test_a_division_by_nought_leaves_its_cell_empty(logged, tmp_path):
    """Nothing went out of the store, so in/out has no answer. That is one
    empty cell, not a table that fails whole for everybody reading it."""
    def change(document):
        document["classes"]["Reconciliation"]["slots"].append("rec_turns")
        document["slots"]["rec_turns"] = {
            "slot_uri": "fx:rec_turns", "range": "decimal",
            "equals_expression": "({rec_in} + 1) / ({rec_out} * 2)"}

    rows = _reconciled(logged, _variant(tmp_path, change))
    assert float(rows["fx:sugar"]["rec_in"]) == 3
    assert rows["fx:sugar"]["rec_turns"] is None


def test_a_value_the_computation_cannot_read_is_a_refusal(logged, map_):
    """A computation the database refuses comes back as a refusal naming the
    table, not as an error the API turns into a 500. The connection is still
    usable afterwards."""
    from compile import CompileError
    with pytest.raises(CompileError) as caught:
        _reconciled(logged, map_, at=A_YEAR_ON)
    assert caught.value.code == "computation_failed"
    assert caught.value.where == "Reconciliation"
    assert "lots" in caught.value.got
    assert float(_reconciled(logged, map_)["fx:sugar"]["rec_in"]) == 3


@pytest.mark.parametrize("text", ["{rec_in} {rec_out}", "({rec_in} - {rec_out}",
                                  "{rec_in} -", "* {rec_in}"])
def test_an_expression_that_does_not_parse_is_refused(tmp_path, text):
    """The characters were checked and the grammar was not, so these reached
    the database and failed there."""
    from components.modules.check import check

    def change(document):
        document["slots"]["rec_expected"]["equals_expression"] = text

    report = check(None, "fixture", "v1", map_=_variant(tmp_path, change))
    assert [(r["class"], r["code"]) for r in report["refusals"]] == [
        ("Reconciliation", "expression_not_arithmetic")]


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



def test_check_reads_an_expression_the_way_the_compiler_does(tmp_path):
    """`check` said "holds" for an expression the compiler then refused: it
    planned the table and never emitted it. A map it calls clean compiles."""
    from components.modules.check import check

    def change(document):
        document["slots"]["rec_expected"]["equals_expression"] = "{rec_in} - rec_out"

    report = check(None, "fixture", "v1", map_=_variant(tmp_path, change))
    assert not report["clean"]
    assert [(r["class"], r["code"]) for r in report["refusals"]] == [
        ("Reconciliation", "expression_not_arithmetic")]


def test_check_refuses_a_total_over_a_table_the_map_computes(tmp_path):
    """A computed table has no rows in the log to total. The compiler says so
    when it emits the source; `check` has to say it too."""
    from components.modules.check import check

    def change(document):
        document["classes"]["Summary"] = {"slots": ["sum_thing", "sum_in"]}
        document["slots"]["sum_thing"] = {"slot_uri": "fx:sum_thing", "range": "Thing"}
        document["slots"]["sum_in"] = {
            "slot_uri": "fx:sum_in", "range": "decimal",
            "annotations": {"aggregate": {"value": {
                "over": "Reconciliation", "sum": "rec_in",
                "by": {"sum_thing": "rec_thing"}}}}}

    report = check(None, "fixture", "v1", map_=_variant(tmp_path, change))
    assert ("Summary", "no_type_slot") in [
        (r["class"], r["code"]) for r in report["refusals"]]

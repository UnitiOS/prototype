"""Try to say "the sum of these" in LinkML alone, and record what happens.

The 1 Sep split says derivation within a row is LinkML's and derivation across
rows is ours. This script is the second half of the evidence for that line: it
asks LinkML's own evaluator for a total across many instances, six ways, and
prints whatever comes back — a value, or the exception verbatim. Nothing is
worked around. An attempt that fails is the result.

Two of the six are run over rows the generator assembled from the kernel at a
stated pair of clocks, so the question is asked of real rows and not only of
literals.

    UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check \
        .venv/Scripts/python.exe scripts/trial_sum_across_rows.py
"""

import sys
from decimal import Decimal
from pathlib import Path

from jsonasobj2 import JsonObj
from linkml_runtime import SchemaView
from linkml_runtime.utils.eval_utils import eval_expr
from linkml_runtime.utils.inference_utils import Config, generate_slot_value

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components"))

from generate import connect, read_map, table  # noqa: E402

MAP = ROOT / "business" / "trial" / "v1.yaml"
VALID_AT = "2026-03-01T00:00:00Z"
AS_OF = "2026-03-01T00:00:00Z"

# A collection class, written the way anyone would write it: the parts are a
# multivalued slot, and the total is an equals_expression over them. Never
# sealed — if it cannot be evaluated there is nothing to seal it for.
COLLECTION = """
id: https://uniti.example/trial_sum
name: linkml_sum_trial
prefixes:
  linkml: https://w3id.org/linkml/
  trial: https://uniti.example/trial/
default_prefix: trial
imports:
  - linkml:types
default_range: string
classes:
  Batch:
    slots:
      - parts
      - batch_total
      - batch_count
slots:
  parts:
    slot_uri: trial:parts
    range: decimal
    multivalued: true
  batch_total:
    slot_uri: trial:batch_total
    range: decimal
    equals_expression: "sum({parts})"
  batch_count:
    slot_uri: trial:batch_count
    range: integer
    equals_expression: "len({parts})"
"""


def attempt(label, fn):
    """Run one attempt. Print the value, or the exception exactly as raised."""
    print(f"  {label}")
    try:
        print(f"      -> {fn()!r}")
    except Exception as exc:
        print(f"      !! {type(exc).__name__}: {exc}")
    print()


def main():
    map_ = read_map(MAP)
    with connect() as conn:
        built = table(conn, map_, "Reading", valid_at=VALID_AT, as_of=AS_OF)

    names = [col["name"] for col in built["columns"]]
    rows = [dict(zip(names, row["cells"])) for row in built["rows"]]
    amounts = [Decimal(row["held_amount"]) for row in rows]

    print(f"map        {MAP}  ({map_['version']})")
    print(f"clocks     valid_at {VALID_AT}   as_of {AS_OF}")
    print(f"rows       {len(rows)} assembled by the generator")
    print(f"held_amount across those rows: {amounts}, whose sum is {sum(amounts)}\n")

    view = SchemaView(COLLECTION)
    batch = JsonObj(parts=amounts, batch_total=None, batch_count=None)
    trial = map_["view"]

    attempt(
        "1. eval_expr on a literal list: sum([1, 2, 3])",
        lambda: eval_expr("sum([1, 2, 3])"),
    )
    attempt(
        f"2. eval_expr over the rows' own values: sum({{amounts}}) with amounts={amounts}",
        lambda: eval_expr("sum({amounts})", amounts=amounts),
    )
    attempt(
        "3. the same total, arity fixed at authoring time: {a} + {b}",
        lambda: eval_expr("{a} + {b}", a=amounts[0], b=amounts[1]),
    )
    attempt(
        "4. an aggregate LinkML does carry: max({amounts})",
        lambda: eval_expr("max({amounts})", amounts=amounts),
    )
    attempt(
        "5. a schema slot over a multivalued slot: batch_total = sum({parts})",
        lambda: generate_slot_value(
            batch, "batch_total", view, class_name="Batch",
            config=Config(use_expressions=True, use_string_serialization=False),
        ),
    )
    attempt(
        "6. the same shape, counting instead of summing: batch_count = len({parts})",
        lambda: generate_slot_value(
            batch, "batch_count", view, class_name="Batch",
            config=Config(use_expressions=True, use_string_serialization=False),
        ),
    )
    attempt(
        "7. and the rules block the sealed map carries, asked to apply itself",
        lambda: generate_slot_value(
            JsonObj(**rows[0]), "total_amount", trial, class_name="Reading",
            config=Config(use_rules=True, use_string_serialization=False),
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

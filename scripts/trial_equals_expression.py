"""Evaluate a map's `equals_expression` over a row this system assembles.

Not over an ordinary object. The row comes out of `components/generator`,
which builds it by resolving every column of a class at one stated
`(valid_at, as_of)` — so what is fed to LinkML is a bitemporal read of the
kernel, and the question is whether LinkML's own evaluator can be pointed at
one at all.

Three things are printed for each row, in order: the row exactly as the
generator hands it over, what LinkML computes from it, and what LinkML
computes once each cell is cast to the type its own slot declares. The middle
one is the honest answer and the last one is what a caller would have to do.

The trial map is sealed into a throwaway database, never the working log:

    UNITI_DSN=postgresql://uniti:uniti@localhost:5433/uniti_check \
        .venv/Scripts/python.exe scripts/trial_equals_expression.py
"""

import sys
from decimal import Decimal
from pathlib import Path

from jsonasobj2 import JsonObj
from linkml_runtime.utils.inference_utils import Config, generate_slot_value

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components"))

from generate import connect, read_map, table  # noqa: E402

MAP = ROOT / "business" / "trial" / "v1.yaml"
CLASS = "Reading"
COMPUTED = "total_amount"

# Both clocks stated, and both after the trial seal. A row is only a row at a
# pair of instants; there is no such thing as "the current row" here.
VALID_AT = "2026-03-01T00:00:00Z"
AS_OF = "2026-03-01T00:00:00Z"

# Every cell arrives as text, because `assertion.value_literal` is text. The
# map declares what each one is; this is the map being believed.
CAST = {"integer": int, "decimal": Decimal, "float": float, "boolean": bool}


def cast(value, declared):
    if value is None or declared not in CAST:
        return value
    try:
        return CAST[declared](value)
    except (ValueError, ArithmeticError):
        return value


def evaluate(view, obj, label):
    """One `generate_slot_value` call, or the exception it raised."""
    try:
        value = generate_slot_value(
            obj, COMPUTED, view, class_name=CLASS,
            config=Config(use_expressions=True, use_string_serialization=False),
        )
        print(f"    {label:<22} {value!r}   ({type(value).__name__})")
    except Exception as exc:
        print(f"    {label:<22} {type(exc).__name__}: {exc}")


def main():
    map_ = read_map(MAP)
    view = map_["view"]
    expression = view.induced_slot(COMPUTED, CLASS).equals_expression
    print(f"map        {MAP}  ({map_['version']})")
    print(f"class      {CLASS}")
    print(f"computed   {COMPUTED} = {expression}")
    print(f"valid_at   {VALID_AT}")
    print(f"as_of      {AS_OF}")

    with connect() as conn:
        built = table(conn, map_, CLASS, valid_at=VALID_AT, as_of=AS_OF)

    names = [col["name"] for col in built["columns"]]
    declared = {col["name"]: col["range"] for col in built["columns"]}
    print(f"\n{len(built['rows'])} rows assembled from the log\n")

    for row in built["rows"]:
        raw = dict(zip(names, row["cells"]))
        typed = {name: cast(value, declared[name]) for name, value in raw.items()}
        print(f"  {row['uri']}")
        print(f"    row as assembled     {raw}")
        evaluate(view, JsonObj(**raw), "computed from it")
        print(f"    row cast to the map  {typed}")
        evaluate(view, JsonObj(**typed), "computed from that")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

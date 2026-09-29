"""examples — what the numbers must be, said by the business, run on every change.

Nobody trusts a map by reading it. They trust it because, told "we took in ten
sacks of flour and used three", it answers "seven on hand" — and because it
still answers that after the next change, and the one after. So a map carries
its examples, and an example is a contract rather than a demonstration:

    says      the example in the business's own words. It is what the person
              agreed to, and what a failure is reported against.
    records   a few things that exist or happened, stated the way a form
              states them: one record at a time, each under the class it is.
    expect    the numbers those records must add up to: which table, which
              row, which columns, and what each one holds.

The file sits beside the map it is about, under the same name:

    @scope/name/
        draft.yaml   draft.examples.yaml     edited by the studio
        v1.yaml      v1.examples.yaml        copied out by `seal`, never again

and looks like this:

    examples:
      flour_in_and_out:
        says: Ten kg of flour came in and three went into bread, so 7 kg are on hand.
        records:
          - record: flour
            class: Ingredient
            facts: {ingredient_code: FLR, ingredient_name: Flour, ingredient_unit: kg}
          - record: flour_in
            class: StockMovement
            when: '2026-06-01'
            facts: {movement_ingredient: flour, movement_quantity: 10}
          - record: flour_used
            class: StockMovement
            when: '2026-06-03'
            facts: {movement_ingredient: flour, movement_quantity: -3}
        expect:
          - table: IngredientStock
            row: flour
            values: {quantity_on_hand: 7}

A record is named by a word of its own, and that word is what another record
writes to point at it and what a row of a table shows. The same word stated a
second time, later, is the same thing changing: that is how an example says
"the reorder level was raised on 1 July". `when` is the day a record became
true, from its first moment; `at` is the day an expectation reads the tables
on, to its last. Without them everything is stated at the beginning and read
at the end. (`when` rather than `on`: YAML 1.1 reads a bare `on:` key as
`true`.)

`row` names one row: by the value of its first column, or by `column: value`
pairs. An expected value that is empty (`~`) says the cell must be empty, which
is not the same as nought — an absent rule is not a rule that says zero.

**How one example runs.** In a log of its own, which exists for exactly as long
as the example does. Three temporary tables shadow the kernel's for this one
connection, inside a transaction that is always rolled back: the records go in
through the form's own door (`generate.submit`, so a value the form would refuse
is refused here too, in the form's words), the tables come out through the
compiler's own reader (`compile.preview`), and then all of it is gone. Nothing
reaches the real log, and nothing in the real log reaches an example — its
numbers are the example's and nobody else's.

Nothing here judges a map by a rule of its own. The door and the compiler do;
this only states, reads, and compares.
"""

import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "kernel"))

from compile import preview, tables  # noqa: E402
from components.refusal import Refusal, Repair  # noqa: E402
from generate import _type_slot, submit  # noqa: E402
from perform import perform  # noqa: E402
from seal import URI_PREDICATE, class_uri  # noqa: E402

SUFFIX = ".examples.yaml"

# The two ends of an example's time. A record nobody dated is true from the
# beginning, and an expectation nobody dated reads the tables at the end, after
# everything has happened and everything is known.
BEGINNING = datetime(2000, 1, 1, tzinfo=timezone.utc)
END = datetime(9999, 12, 31, tzinfo=timezone.utc)

# Who states an example's records, and why. They land only in the scratch log,
# which is rolled back, so nobody ever reads them — but the door asks.
ACTOR = "example"
REASON = "example"

# The closed shapes. An unknown key is a typo, and a typo in a contract is
# the one kind that must not pass silently.
EXAMPLE_KEYS = ("says", "records", "expect")
RECORD_KEYS = ("record", "class", "when", "facts")
EXPECT_KEYS = ("table", "row", "at", "values")

WORD = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

_TABLES = ("intent", "entity", "assertion")

# A scratch log: the kernel's three tables, empty, visible to this connection
# only and shadowing the real ones for as long as the transaction lasts. LIKE
# reads the real table's columns, so a column added to the kernel is one here
# too. `seq` is an identity column and has to be copied as one.
_SCRATCH = (
    "CREATE TEMP TABLE intent (LIKE intent INCLUDING DEFAULTS "
    "INCLUDING CONSTRAINTS) ON COMMIT DROP",
    "CREATE TEMP TABLE entity (LIKE entity INCLUDING DEFAULTS) ON COMMIT DROP",
    "CREATE TEMP TABLE assertion (LIKE assertion INCLUDING DEFAULTS "
    "INCLUDING CONSTRAINTS INCLUDING IDENTITY) ON COMMIT DROP",
)

_IS_SCRATCH = """
SELECT c.relnamespace = pg_my_temp_schema()
FROM pg_class c WHERE c.oid = to_regclass(%s)
"""


class ExampleError(Refusal):
    """A business example the map does not bear out, or cannot be read."""

    gate = "the business examples"


# ---- the file -------------------------------------------------------------

def path_for(map_path):
    """Where the examples of a map live: beside it, under its own name."""
    map_path = Path(map_path)
    stem = map_path.name[:-len(".yaml")] if map_path.name.endswith(".yaml") \
        else map_path.name
    return map_path.with_name(stem + SUFFIX)


def load(path):
    """The examples in a file, by name, in the order written. None is no file.

    The shape is checked here and nothing else: whether a class or a column
    exists is the map's to answer, and it answers when the example runs.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        held = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise _shape(path.name, "a YAML file", str(exc).splitlines()[0]) from None
    if not isinstance(held, dict) or set(held) - {"examples"}:
        raise _shape(path.name, "one key, `examples`",
                     sorted(held) if isinstance(held, dict) else type(held).__name__)
    examples = held.get("examples") or {}
    if not isinstance(examples, dict):
        raise _shape(f"{path.name}: examples", "examples by name",
                     type(examples).__name__)
    for name, body in examples.items():
        _example(path.name, name, body)
    return {str(name): body for name, body in examples.items()}


def dump(examples):
    """The file's text, as the studio writes it."""
    return yaml.safe_dump({"examples": examples}, sort_keys=False,
                          default_flow_style=False, allow_unicode=True)


def _shape(where, expected, got):
    return ExampleError(
        "examples_not_understood", where=where, expected=expected, got=f"{got}",
        repairs=[Repair("an examples file is written by the studio's steps; "
                        "use them rather than editing it",
                        options=["add_example", "record", "expect"])])


def _example(file, name, body):
    where = f"{file}: {name}"
    if not WORD.match(str(name)):
        raise _shape(where, "a name starting with a letter, then letters, "
                            "digits or _", repr(name))
    if not isinstance(body, dict):
        raise _shape(where, "an example", type(body).__name__)
    unknown = sorted(set(body) - set(EXAMPLE_KEYS))
    if unknown:
        raise _shape(where, f"only {', '.join(EXAMPLE_KEYS)}", ", ".join(str(u) for u in unknown))
    if not str(body.get("says") or "").strip():
        raise _shape(f"{where}.says", "the example in the business's own words",
                     "nothing")
    for i, record in enumerate(body.get("records") or []):
        at = f"{where}.records[{i}]"
        if not isinstance(record, dict):
            raise _shape(at, "a record", type(record).__name__)
        unknown = sorted(set(record) - set(RECORD_KEYS))
        if unknown:
            raise _shape(at, f"only {', '.join(RECORD_KEYS)}", ", ".join(str(u) for u in unknown))
        if not WORD.match(str(record.get("record") or "")):
            raise _shape(f"{at}.record", "a word naming the record",
                         repr(record.get("record")))
        _scalars(f"{at}.facts", record.get("facts"))
        if record.get("when") is not None:
            instant(record["when"], f"{at}.when")
    for i, expectation in enumerate(body.get("expect") or []):
        at = f"{where}.expect[{i}]"
        if not isinstance(expectation, dict):
            raise _shape(at, "an expectation", type(expectation).__name__)
        unknown = sorted(set(expectation) - set(EXPECT_KEYS))
        if unknown:
            raise _shape(at, f"only {', '.join(EXPECT_KEYS)}", ", ".join(str(u) for u in unknown))
        if not expectation.get("table"):
            raise _shape(f"{at}.table", "the table the numbers are read from",
                         "nothing")
        row = expectation.get("row")
        if row is None or row == "" or row == {}:
            raise _shape(f"{at}.row", "which row: a value of its first column, "
                                      "or column: value pairs", "nothing")
        if isinstance(row, dict):
            _scalars(f"{at}.row", row)
        if not expectation.get("values"):
            raise _shape(f"{at}.values", "at least one column and its number",
                         "nothing")
        _scalars(f"{at}.values", expectation["values"])
        if expectation.get("at") is not None:
            instant(expectation["at"], f"{at}.at", end_of_day=True)


def _scalars(where, held):
    if held is None:
        return
    if not isinstance(held, dict):
        raise _shape(where, "column: value pairs", type(held).__name__)
    for key, value in held.items():
        if isinstance(value, (dict, list)):
            raise _shape(f"{where}.{key}", "one value", type(value).__name__)


def instant(value, where="", *, end_of_day=False):
    """A moment an example names. A bare day is the whole of that day: from its
    first moment when something happens on it, to its last when it is read."""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, date):
        moment = datetime.combine(value, time())
        if end_of_day:
            moment += timedelta(days=1, microseconds=-1)
    else:
        text = str(value).strip()
        try:
            moment = datetime.fromisoformat(text)
        except ValueError:
            raise _shape(where, "a day such as 2026-06-30, or a moment",
                         repr(value)) from None
        if end_of_day and len(text) == 10:
            moment += timedelta(days=1, microseconds=-1)
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


# ---- running --------------------------------------------------------------

def run(conn, map_, examples):
    """Every example, each in a log of its own. One result per example."""
    return [run_one(conn, map_, name, body) for name, body in examples.items()]


def run_one(conn, map_, name, body):
    """One example: state its records, read its tables, compare, forget.

    The result keeps every check, passing or not, and the tables as they came
    out — the numbers are worth seeing when they are right too. `refusals` is
    what a gate says about it: the one refusal that stopped it, or one
    `example_failed` per number that came out different.
    """
    out = {"name": name, "says": str(body.get("says") or ""),
           "records": len(body.get("records") or []),
           "expected": len(body.get("expect") or []),
           "checks": [], "tables": [], "refusals": [], "passed": False}
    try:
        with conn.transaction():
            _scratch(conn)
            _state(conn, map_, name, body.get("records") or [])
            out["checks"] = _checks(conn, map_, name, body)
            out["tables"] = _tables(conn, map_)
            raise psycopg.Rollback()
    except Refusal as exc:
        out["refusals"] = [exc]
    finally:
        _gone(conn)
    if not out["refusals"]:
        out["refusals"] = [_failed(map_, name, out["says"], check)
                           for check in out["checks"] if not check["holds"]]
    out["passed"] = not out["refusals"]
    return out


def refusals(results):
    """Everything the examples refuse, in order: what `seal` and the studio read."""
    return [refusal for result in results for refusal in result["refusals"]]


def report(results):
    """The results as the API sends them and a page draws them."""
    return [{**result, "refusals": [r.as_dict() for r in result["refusals"]]}
            for result in results]


def render(reported, *, tables=False):
    """The results for a terminal, from `report()` or unrun. One line per
    example, one per number it expects, and the tables when asked."""
    lines = []
    for result in reported:
        mark = {True: "holds", False: "FAILS", None: "not run"}[result["passed"]]
        lines.append(f"[{mark}] {result['name']}: {result['says']}")
        for check in result["checks"]:
            at = f" on {check['at']}" if check["at"] else ""
            what = check["column"] or "the row"
            sign = "ok " if check["holds"] else "!! "
            lines.append(f"    {sign}{check['table']} {check['row']}{at}, {what}: "
                         f"expected {check['expected']}, got {check['got']}")
        if not result["checks"]:
            for refusal in result["refusals"]:
                lines.append(f"    !! {refusal['sentence']}")
        for table in result["tables"] if tables else ():
            lines.append(f"    table {table['table']}")
            for line in _grid(table["columns"], table["rows"]):
                lines.append(f"      {line}")
    return lines


def _grid(headers, rows):
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows))
              for i, h in enumerate(headers)]
    out = ["  ".join(str(h).ljust(w) for h, w in zip(headers, widths))]
    out += ["  ".join(str(c).ljust(w) for c, w in zip(row, widths)) for row in rows]
    return [line.rstrip() for line in out]


def _scratch(conn):
    """Open the example's own log, and make sure it is the one being written."""
    with conn.cursor() as cur:
        for table in _TABLES:
            cur.execute(_IS_SCRATCH, (table,))
            held = cur.fetchone()
            if held is not None and held[0]:
                raise RuntimeError(f"a scratch {table} is still open on this "
                                   f"connection; refusing to open another")
        for statement in _SCRATCH:
            cur.execute(statement)
        for table in _TABLES:
            cur.execute(_IS_SCRATCH, (table,))
            if not cur.fetchone()[0]:
                raise RuntimeError(f"{table} does not resolve to the scratch "
                                   f"log; nothing was stated")
    # Every log begins the same way, with the predicate that names things
    # registering itself. A seal writes it into a real one; the form's door
    # expects it to be there already.
    perform(conn, actor_id=ACTOR, agent_id="examples", action_name="begin",
            ontology_version=REASON, reason_code=REASON, mint=[URI_PREDICATE],
            assertions=[{"subject": URI_PREDICATE, "predicate": URI_PREDICATE,
                         "value": URI_PREDICATE, "valid_from": BEGINNING,
                         "source": "system_derived"}])


def _gone(conn):
    """After an example, every name resolves to the real log again.

    If one did not, the next write on this connection — a seal, say — would
    land in a table about to vanish. That is worth a crash rather than a
    refusal: it would be a defect here, not a problem with anybody's map.
    """
    if conn.closed or conn.info.transaction_status == psycopg.pq.TransactionStatus.INERROR:
        return
    with conn.cursor() as cur:
        for table in _TABLES:
            cur.execute(_IS_SCRATCH, (table,))
            held = cur.fetchone()
            if held is not None and held[0]:
                raise RuntimeError(f"the scratch {table} outlived its example")


def _stateable(map_):
    """Every class a record can be: concrete, and something the log can say."""
    view = map_["view"]
    return sorted(str(n) for n in view.all_classes()
                  if not view.get_class(n).abstract
                  and _type_slot(map_, n) is not None)


def _text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _state(conn, map_, name, records):
    """Every record, through the form's own door, in the order written."""
    view = map_["view"]
    classes = {}
    for record in records:
        rid = str(record["record"])
        where = f"example {name}: record {rid}"
        class_name = record.get("class") or classes.get(rid)
        if class_name is None:
            raise ExampleError(
                "record_without_class", where=where,
                expected="what it is, the first time it is stated",
                got="no class",
                repairs=[Repair("say which class it is", options=_stateable(map_))])
        class_name = str(class_name)
        if class_name not in view.all_classes():
            raise ExampleError(
                "no_such_class", where=where,
                expected="a class this map declares", got=repr(class_name),
                repairs=[Repair("name a class a record can be",
                                options=_stateable(map_))])
        slot = _type_slot(map_, class_name)
        if slot is None or view.get_class(class_name).abstract:
            raise ExampleError(
                "no_type_slot", where=where,
                expected="a class the log can say an entity is",
                got=f"{class_name}, which "
                    + ("is a role" if view.get_class(class_name).abstract
                       else "carries no slot saying which class an entity is"),
                repairs=[Repair("name a class a record can be",
                                options=_stateable(map_))])
        values = {str(k): _text(v) for k, v in (record.get("facts") or {}).items()
                  if v is not None}
        if record.get("class") or rid not in classes:
            values[str(slot.name)] = class_name
        classes[rid] = class_name
        on = (instant(record["when"]) if record.get("when") is not None
              else BEGINNING)
        try:
            submit(conn, map_, class_name, subject=rid, values=values,
                   actor_id=ACTOR, valid_from=on, reason_code=REASON,
                   note=where)
        except Refusal as exc:
            # The form's refusal, from the form's gate, said of this record:
            # the rule that refused it is the door's, and so is the answer.
            exc.where = f"{where}, {exc.where}"
            exc.args = (exc.sentence(),)
            raise


def _row(expectation, names):
    """The row an expectation names, as column: value pairs."""
    row = expectation["row"]
    return ({str(k): v for k, v in row.items()} if isinstance(row, dict)
            else {names[0]: row})


def _checks(conn, map_, name, body):
    known = tables(map_)
    read = {}
    out = []
    for expectation in body.get("expect") or []:
        table = str(expectation["table"])
        where = f"example {name}: {table}"
        if table not in known:
            raise ExampleError(
                "no_such_class", where=where,
                expected="a table this map computes", got=repr(table),
                repairs=[Repair("read the numbers from one of these",
                                options=known)])
        at = (instant(expectation["at"], end_of_day=True)
              if expectation.get("at") is not None else END)
        if (table, at) not in read:
            built = preview(conn, map_, table, valid_at=at, as_of=END)
            read[(table, at)] = ([c["name"] for c in built["plan"]["columns"]],
                                 built["rows"])
        names, rows = read[(table, at)]
        row = _row(expectation, names)
        values = {str(k): v for k, v in expectation["values"].items()}
        unknown = sorted((set(row) | set(values)) - set(names))
        if unknown:
            raise ExampleError(
                "no_such_column", where=where,
                expected=f"columns {table} has", got=", ".join(unknown),
                repairs=[Repair(f"name a column of {table}", options=names)])

        said = {"table": table, "row": _pairs(expectation["row"]),
                "at": None if expectation.get("at") is None else str(expectation["at"])}
        matches = [r for r in rows
                   if all(_same(map_, v, r[names.index(c)]) for c, v in row.items())]
        if len(matches) != 1:
            out.append({**said, "column": None, "expected": "one row",
                        "got": f"{len(matches)} rows", "holds": False,
                        "rows": [_shown(map_, r[0]) for r in rows]})
            continue
        for column, expected in values.items():
            got = matches[0][names.index(column)]
            out.append({**said, "column": column, "expected": _shown(map_, expected),
                        "got": _shown(map_, got),
                        "holds": _same(map_, expected, got)})
    return out


def _tables(conn, map_):
    """Every table the map computes from this example's records, with rows."""
    out = []
    for table in tables(map_):
        try:
            built = preview(conn, map_, table, valid_at=END, as_of=END)
        except Refusal:
            # A table the compiler refuses is a hole of its own, and already
            # said where the draft is read; it has no numbers to show here.
            continue
        if built["rows"]:
            out.append({"table": table,
                        "columns": [c["name"] for c in built["plan"]["columns"]],
                        "rows": [[_shown(map_, cell) for cell in row]
                                 for row in built["rows"]]})
    return out


def _failed(map_, name, says, check):
    where = f"example {name}: {check['table']} {check['row']}"
    if check["column"]:
        where += f", {check['column']}"
    if check["at"]:
        where += f" on {check['at']}"
    repairs = []
    if check["column"] is None:
        repairs.append(Repair(f"name a row {check['table']} has",
                              options=check["rows"]))
    repairs += [
        Repair("if the example is what the business does, the map is what is "
               "wrong: change the rule or the records that feed this number",
               where=f"{check['table']}.{check['column']}" if check["column"]
               else check["table"]),
        Repair("if the example itself is wrong, correct it with whoever gave "
               "it. It is their word on what the numbers must be, and changing "
               "it to match the map proves nothing",
               options=["expect"]),
    ]
    return ExampleError("example_failed", where=where,
                        expected=f"{check['expected']}, because: {says}",
                        got=check["got"], repairs=repairs)


# ---- comparing ------------------------------------------------------------

def _class_names(map_):
    view = map_["view"]
    return {class_uri(view, n): str(n) for n in view.all_classes()}


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _same(map_, expected, got):
    """Whether a cell holds what the example says it does.

    Numbers as numbers, so 17 and 17.000 are one answer. An empty expectation
    asks for an empty cell. A class is named as the example names it, and a
    cell holds its full URI, so either is accepted.
    """
    if expected is None or expected == "":
        return got is None
    if got is None:
        return False
    one, other = _number(expected), _number(got)
    if one is not None and other is not None:
        return one == other
    if _text(expected) == _text(got):
        return True
    return _class_names(map_).get(str(got)) == str(expected)


def _shown(map_, value):
    """A value as a person reads it: a number without trailing noughts, a class
    by its name, and an empty cell as `empty`."""
    if value is None or value == "":
        return "empty"
    number = _number(value)
    if number is not None and not isinstance(value, str):
        return format(number.normalize(), "f")
    if isinstance(value, str) and value in _class_names(map_):
        return _class_names(map_)[value]
    return _text(value)


def _pairs(row):
    if isinstance(row, dict):
        return ", ".join(f"{k}={v}" for k, v in row.items())
    return str(row)


__all__ = ["BEGINNING", "END", "ExampleError", "SUFFIX", "dump", "instant",
           "load", "path_for", "refusals", "render", "report", "run", "run_one"]

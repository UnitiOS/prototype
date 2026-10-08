"""The library: the first `@uniti/*` modules beside core (DESIGN_NOTES.md §15).

What has to hold, and what is asserted here:

    the library is   party, item and transaction are sealed in `packages/`,
    in the store     meet the recording standard, and the catalogue finds
                     their classes and their roles
    one thing stays  a module built on it points at the library's party and
    one thing        item, so one customer is stated once and read by every
                     record that names them; a deposit points at the rental it
                     secures, not at one of its lines
    a kind is a      a class made a kind of another module's class is refused,
    role or one's    at the step and at the seal; a kind of a role, or of the
    own              module's own class, is not
    one record       a line is grouped by the customer of the rental it is part
    further          of — a key read one record away, `line_rental.<slot>` —
                     in the example, in the table, and when a cell is taken
                     apart; two records away is refused as not possible yet

The module built here is a rental with a deposit: the shape the empty-store
test (UJI_LINGKUNGAN_KOSONG.md) could not build, because nothing said who a
customer was or what one rental is.
"""

import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from components.api import application  # noqa: E402
from components.modules import catalogue as catalogue_read  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from components.studio.draft import StudioError  # noqa: E402
from perform import connect  # noqa: E402
from compile import CompileError, _read_aggregate  # noqa: E402
from generate import read_map  # noqa: E402
from seal import DraftError, register, seal  # noqa: E402
from components.business import BusinessError, declare, install  # noqa: E402

LIBRARY = ("@uniti/party", "@uniti/item", "@uniti/transaction")
# The business the test log belongs to, as scripts/dev_modules.py declares it.
BUSINESS = "demo"
REGISTERED = [("@uniti/core", "v1"), ("@uniti/core", "v2"),
              ("@uniti/party", "v1"), ("@uniti/item", "v1"),
              ("@uniti/transaction", "v1")]


@pytest.fixture(scope="module")
def conn():
    """One connection, never committed: the seals here are rolled back."""
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def store(conn, tmp_path_factory):
    """A root of its own for what the tests build, the real store behind it.

    A log learns the library's words the way any second log does: by
    registering the sealed versions, not by sealing them again.
    """
    held = Store([tmp_path_factory.mktemp("packages"), ROOT / "packages"])
    for name, version in REGISTERED:
        register(conn, held.path(name, version), actor_id="dev", store=held)
    return held


def step(store, name, op, **args):
    return studio.apply(store, name, op, args)


def test_the_library_is_sealed_in_the_store_and_found_in_the_catalogue(store):
    for name in LIBRARY:
        assert [v["version"] for v in store.versions(name)] == ["v1"], name
        document = store.document(name, "v1")
        assert document["imports"][:2] == ["linkml:types", "@uniti/core@v2"]
        assert store.kind(name) == "library"

    found = catalogue_read.catalogue(store)
    classes = catalogue_read.find(found, kind="class")["entries"]
    by_name = {c["name"]: c for c in classes}
    assert by_name["Party"]["module"]["name"] == "@uniti/party"
    assert by_name["Item"]["module"]["name"] == "@uniti/item"
    roles = {r["name"]: r for r in catalogue_read.find(found, kind="role")["entries"]}
    assert {"Transaction", "TransactionLine"} <= set(roles)
    assert [b["name"] for b in roles["TransactionLine"]["bindings"]] == ["line_transaction"]
    # A transaction is an event: it binds the day as well as the party.
    assert {b["name"] for b in roles["Transaction"]["bindings"]} == {
        "moment", "transaction_counterparty"}
    # Found in the person's words too.
    assert any(e["name"] == "Party"
               for e in catalogue_read.find(found, text="Pihak")["entries"])


def test_the_library_holds_no_class_that_is_a_kind_of_another_modules(store):
    for name in LIBRARY:
        for body in (store.document(name, "v1").get("classes") or {}).values():
            assert not body.get("is_a") or body.get("abstract"), name


def _rental(store, name="@probe/rental"):
    """A rental and the deposit against it, on the library, by steps alone."""
    step(store, name, "start", title="Rental",
         description="Equipment rented to customers and the deposits they leave.")
    for pin in ("@uniti/party@v1", "@uniti/item@v1", "@uniti/transaction@v1"):
        step(store, name, "pin", module=pin)
    for class_name, said, roles in (
        ("Rental", "One customer renting equipment on one day.", ["Transaction"]),
        ("RentalLine", "One item of a rental and how many were taken.",
         ["TransactionLine", "Flow"]),
        ("Deposit", "Money a customer leaves against a rental.", ["Transaction"]),
        ("ItemOut", "How many of each item are out on rental.", []),
        ("CustomerOut", "How many items each customer has out on rental.", []),
        ("DepositHeld", "Deposit money held per customer.", []),
    ):
        step(store, name, "add_class", **{"class": class_name, "description": said})
        for role in roles:
            step(store, name, "fill_role", **{"class": class_name, "role": role})
    day = {"time_meaning": "happened"}
    for class_name, slot, kind, said, meant, binds in (
        ("Rental", "rental_number", "string", "The number on the rental note.", {}, None),
        ("Rental", "rental_customer", "Party", "Who rented.", {}, "transaction_counterparty"),
        ("Rental", "rental_date", "date", "The day of the rental.", day, "moment"),
        ("RentalLine", "line_rental", "Rental", "The rental this line is part of.", {},
         "line_transaction"),
        ("RentalLine", "line_item", "Item", "The item rented.", {}, "affects"),
        ("RentalLine", "line_quantity", "integer", "How many were taken out.",
         {"unit": "piece", "direction": "increase"}, "amount"),
        ("RentalLine", "line_date", "date", "The day of the rental, again.", day, "moment"),
        ("Deposit", "deposit_number", "string", "The number on the receipt.", {}, None),
        ("Deposit", "deposit_customer", "Party", "Who left it.", {}, "transaction_counterparty"),
        ("Deposit", "deposit_rental", "Rental", "The rental it secures.", {}, None),
        ("Deposit", "deposit_amount", "decimal", "Money received.",
         {"unit": "IDR", "direction": "increase"}, None),
        ("Deposit", "deposit_date", "date", "The day it was received.", day, "moment"),
        ("ItemOut", "out_item", "Item", "The item.", {}, None),
        ("ItemOut", "out_quantity", "integer", "How many are out.",
         {"unit": "piece", "direction": "level"}, None),
        ("CustomerOut", "customer_party", "Party", "The customer.", {}, None),
        ("CustomerOut", "customer_out", "integer", "How many items they have out.",
         {"unit": "piece", "direction": "level"}, None),
        ("DepositHeld", "held_customer", "Party", "The customer.", {}, None),
        ("DepositHeld", "held_amount", "decimal", "Deposit money held.",
         {"unit": "IDR", "direction": "level"}, None),
    ):
        step(store, name, "add_slot", slot=slot, range=kind, description=said, **meant)
        step(store, name, "attach", **{"class": class_name, "slot": slot})
        if binds:
            step(store, name, "bind", slot=slot, binding=binds)
    for slot in ("rental_number", "deposit_number"):
        step(store, name, "set_slot", slot=slot, field="identifier", value="true")
    step(store, name, "aggregate", **{
        "class": "ItemOut", "column": "out_quantity", "over": "RentalLine",
        "sum": "line_quantity", "by": "out_item=line_item"})
    # One record further, and through the role's binding: a line names its
    # rental, and the rental's counterparty is whichever slot fills it.
    step(store, name, "aggregate", **{
        "class": "CustomerOut", "column": "customer_out", "over": "RentalLine",
        "sum": "line_quantity",
        "by": "customer_party=line_rental.transaction_counterparty"})
    step(store, name, "aggregate", **{
        "class": "DepositHeld", "column": "held_amount", "over": "Deposit",
        "sum": "deposit_amount", "by": "held_customer=deposit_customer"})

    step(store, name, "add_example", example="budi",
         says="Budi rents two tents and a stove and leaves 150000 against the rental.")
    step(store, name, "record", example="budi", record="budi", **{"class": "Party"},
         facts="party_name=Budi, party_kind=person")
    for record, item in (("tent", "Tent"), ("stove", "Stove")):
        step(store, name, "record", example="budi", record=record,
             **{"class": "Item"}, facts=f"item_name={item}")
    step(store, name, "record", example="budi", record="r1", **{"class": "Rental"},
         when="2026-10-06",
         facts="rental_number=R1, rental_customer=budi, rental_date=2026-10-06")
    for record, item, quantity in (("l1", "tent", 2), ("l2", "stove", 1)):
        step(store, name, "record", example="budi", record=record,
             **{"class": "RentalLine"}, when="2026-10-06",
             facts=f"line_rental=r1, line_item={item}, line_quantity={quantity}, "
                   f"line_date=2026-10-06")
    step(store, name, "record", example="budi", record="d1", **{"class": "Deposit"},
         when="2026-10-06",
         facts="deposit_number=D1, deposit_customer=budi, deposit_rental=r1, "
               "deposit_amount=150000, deposit_date=2026-10-06")
    step(store, name, "expect", example="budi", table="ItemOut", row="tent",
         values="out_quantity=2")
    step(store, name, "expect", example="budi", table="ItemOut", row="stove",
         values="out_quantity=1")
    step(store, name, "expect", example="budi", table="DepositHeld", row="budi",
         values="held_amount=150000")
    step(store, name, "expect", example="budi", table="CustomerOut", row="budi",
         values="customer_out=3")
    return name


@pytest.fixture(scope="module")
def rental(store, conn):
    """The module, built by steps, and its first version sealed."""
    name = _rental(store)
    report = reading.state(store, name, conn)
    out = seal(conn, studio.path(store, name), actor_id="probe",
               into=store.directory(name), store=store)
    return name, report, out


@pytest.fixture(scope="module")
def shop(store, conn, rental):
    """The business's application: the rental module and nothing of its own,
    installed in the business's kernel. Staff record through this, never
    through the module, which is shared and installed by nobody."""
    name = "@demo/shop"
    step(store, name, "start", title="Shop", kind="application", business=BUSINESS,
         description="The rental business's application.")
    step(store, name, "pin", module=f"{rental[0]}@v1")
    declare(conn, BUSINESS, actor_id="dev")
    seal(conn, studio.path(store, name), actor_id="dev", into=store.directory(name),
         store=store)
    install(conn, store, name, "v1", actor_id="dev", valid_from="2026-01-01T00:00:00Z")
    return name


def test_an_application_made_of_the_modules_it_pins_is_a_version(store, conn, rental):
    # Nothing of its own: the modules it pins, and an example of what their
    # numbers must come to for this business. Not empty, and nothing to ask
    # it to declare.
    name = "@demo/counted"
    step(store, name, "start", title="Counted", kind="application", business=BUSINESS,
         description="The rental business's own numbers, from the rental module.")
    assert reading.state(store, name, conn)["empty"] is True
    step(store, name, "pin", module=f"{rental[0]}@v1")
    step(store, name, "add_example", example="ours",
         says="Sari rents out two tents.")
    step(store, name, "record", example="ours", record="sari", **{"class": "Party"},
         facts="party_name=Sari")
    step(store, name, "record", example="ours", record="tent", **{"class": "Item"},
         facts="item_name=Tent")
    step(store, name, "record", example="ours", record="r1", **{"class": "Rental"},
         when="2026-10-06",
         facts="rental_number=R1, rental_customer=sari, rental_date=2026-10-06")
    step(store, name, "record", example="ours", record="l1", **{"class": "RentalLine"},
         when="2026-10-06",
         facts="line_rental=r1, line_item=tent, line_quantity=2, line_date=2026-10-06")
    step(store, name, "expect", example="ours", table="ItemOut", row="tent",
         values="out_quantity=2")
    step(store, name, "agree_example", example="ours")

    report = reading.state(store, name, conn)
    assert report["empty"] is False
    assert "nothing_declared" not in [h["kind"] for h in report["holes"]]
    [ours] = report["examples"]
    assert ours["passed"] is True, ours
    assert report["sealable"] is True
    # A module pinning only core and declaring nothing is still empty.
    step(store, "@demo/bare", "start", title="Bare",
         description="A module that declares nothing yet.")
    assert reading.state(store, "@demo/bare", conn)["empty"] is True
    studio.apply(store, name, "discard", {})
    studio.apply(store, "@demo/bare", "discard", {})


def test_a_module_on_the_library_points_at_one_party_and_one_item(store, rental):
    name, report, out = rental
    assert [h for h in report["holes"] if h["blocking"]] == []
    [example] = report["examples"]
    assert example["passed"] is True
    assert [(c["column"], c["got"]) for c in example["checks"]] == [
        ("out_quantity", "2"), ("out_quantity", "1"), ("held_amount", "150000"),
        ("customer_out", "3")]
    assert out["version"] == "v1"
    # The map is told where the key is read: off the line, the rental it names,
    # and that rental's customer.
    working = next(t for t in report["workings"] if t["class"] == "CustomerOut")
    columns = {c["name"]: c for c in working["columns"]}
    assert columns["customer_out"]["reads"] == [{
        "class": "RentalLine", "fields": ["line_quantity"],
        "by": {"customer_party": "line_rental"},
        "via": {"customer_party": ["rental_customer"]}}]
    sealed = store.document(name, "v1")
    # Nothing of the library is declared again: the module points at it.
    assert not {"Party", "Item"} & set(sealed["classes"])
    assert sealed["slots"]["rental_customer"]["range"] == "Party"
    assert sealed["slots"]["deposit_customer"]["range"] == "Party"
    # The deposit names the rental, not one of its lines.
    assert sealed["slots"]["deposit_rental"]["range"] == "Rental"
    assert sealed["classes"]["RentalLine"]["mixins"] == ["TransactionLine", "Flow"]


def _a_kind_of_item(store, name):
    step(store, name, "start", title="Kinds",
         description="A module that would make its own kind of an item.")
    step(store, name, "pin", module="@uniti/item@v1")
    step(store, name, "add_class", **{"class": "RentalItem",
                                      "description": "An item that is rented out."})
    return name


def test_a_kind_of_another_modules_class_is_refused_at_the_step(store):
    name = _a_kind_of_item(store, "@probe/kinds")
    with pytest.raises(StudioError) as refused:
        step(store, name, "set_class", **{"class": "RentalItem", "field": "is_a",
                                          "value": "Item"})
    assert refused.value.code == "kind_of_foreign_class"
    assert "@uniti/item@v1" in str(refused.value)
    assert refused.value.as_dict()["repairs"][0]["options"] == ["add_slot"]

    # A kind of a role, and a kind of the module's own class, are not refused.
    step(store, name, "add_class", **{"class": "Tent", "description": "A tent."})
    step(store, name, "set_class", **{"class": "Tent", "field": "is_a",
                                      "value": "RentalItem"})
    step(store, name, "set_class", **{"class": "RentalItem", "field": "is_a",
                                      "value": "Resource"})


def test_a_kind_of_another_modules_class_is_refused_by_the_seal(store, conn):
    """Written past the studio, straight into the file: the seal is the judge,
    and the studio's reading of the draft says the same thing it does."""
    name = _a_kind_of_item(store, "@probe/kinds-written")
    where = studio.path(store, name)
    document = yaml.safe_load(where.read_text(encoding="utf-8"))
    document["classes"]["RentalItem"]["is_a"] = "Item"
    where.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    with pytest.raises(DraftError) as refused:
        seal(conn, where, actor_id="probe", into=store.directory(name), store=store)
    assert refused.value.code == "kind_of_foreign_class"
    assert refused.value.where.endswith("class RentalItem")

    report = reading.state(store, name, conn)
    assert "kind_of_foreign_class" in {r["code"] for r in report["refusals"]}
    assert report["sealable"] is False


def _stated(conn, store, name, class_name, subject, day, **values):
    application.state(conn, store, name, "v1", class_name, subject=subject,
                      values=values, actor_id="test", valid_from=f"{day}T08:00:00Z")


def test_a_line_is_grouped_by_the_customer_of_its_rental(store, conn, rental, shop):
    """In the log, not only in the example: two customers, and each one's
    lines found through the rental they belong to, at both clocks.

    Recorded through the business's application; read through the module
    itself, which anyone may do."""
    name, _, _ = rental
    with pytest.raises(BusinessError) as refused:
        _stated(conn, store, name, "Party", "party:nobody", "2026-10-01", party_name="X")
    assert refused.value.code == "not_installed"
    assert f"{shop}@v1" in refused.value.as_dict()["repairs"][0]["options"]

    for subject, party in (("party:budi", "Budi"), ("party:citra", "Citra")):
        _stated(conn, store, shop, "Party", subject, "2026-10-01", party_name=party)
    for subject, item in (("item:tent", "Tent"), ("item:stove", "Stove")):
        _stated(conn, store, shop, "Item", subject, "2026-10-01", item_name=item)
    for rented, who, number, day in (("rent:r1", "party:budi", "R1", "2026-10-06"),
                                     ("rent:r2", "party:citra", "R2", "2026-10-08")):
        _stated(conn, store, shop, "Rental", rented, day, rental_number=number,
                rental_customer=who, rental_date=day)
    for line, rented, item, quantity, day in (
            ("line:1", "rent:r1", "item:tent", "2", "2026-10-06"),
            ("line:2", "rent:r1", "item:stove", "1", "2026-10-06"),
            ("line:3", "rent:r2", "item:tent", "1", "2026-10-08")):
        _stated(conn, store, shop, "RentalLine", line, day, line_rental=rented,
                line_item=item, line_quantity=quantity, line_date=day)

    def table(valid_at):
        out = application.projection(conn, store, name, "v1", "CustomerOut",
                                     valid_at=valid_at, as_of="2026-12-31")
        return {row[0]: row[1] for row in out["rows"]}

    assert table("2026-10-31") == {"party:budi": 3, "party:citra": 1}
    # Before Citra rented, her rental and its line are not yet true.
    assert table("2026-10-07") == {"party:budi": 3}

    taken = application.cell(conn, store, name, "v1", "CustomerOut", "customer_out",
                             {"customer_party": "party:budi"},
                             valid_at="2026-10-31", as_of="2026-12-31")
    assert sorted(int(s["value"]) for s in taken["statements"]) == [1, 2]
    assert {s["subject_uri"] for s in taken["statements"]} == {"line:1", "line:2"}


def test_a_key_two_records_away_is_refused_as_not_possible_yet(store):
    name = "@probe/too-far"
    step(store, name, "start", title="Too far", description="Reaches too far.")
    step(store, name, "add_class", **{"class": "Total", "description": "A total."})
    step(store, name, "add_slot", slot="total_x", range="decimal", description="X.",
         unit="piece", direction="level")
    step(store, name, "attach", **{"class": "Total", "slot": "total_x"})
    with pytest.raises(StudioError) as refused:
        step(store, name, "aggregate", **{
            "class": "Total", "column": "total_x", "over": "Total", "sum": "total_x",
            "by": "total_key=a.b.c"})
    assert refused.value.code == "not_possible_yet"


def test_a_key_reached_through_a_value_that_names_nothing_is_refused(store, rental):
    name, _, _ = rental
    map_ = read_map(store.path(name, "v1"), store=store)
    with pytest.raises(CompileError) as refused:
        _read_aggregate(map_, "CustomerOut.customer_out", {
            "over": "RentalLine", "sum": "line_quantity",
            "by": {"customer_party": "line_quantity.party_name"}})
    assert refused.value.code == "not_a_reference"
    assert refused.value.as_dict()["repairs"][0]["options"] == ["line_item", "line_rental"]

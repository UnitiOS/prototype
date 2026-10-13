"""Pointing at roles, as the normal way to connect (ECOSYSTEM_PLAN.md, step 4).

Dewi's guarantee secures "a transaction", not Rudi's `Rental`: her slot ranges
over the library's role, so it fits Rudi's rentals, SewaPro's bookings and any
transaction module written later. What has to hold, and is asserted here:

    stand-in        a module pointing at a role has no record of that role of
                    its own for its examples; it records a stand-in, the role
                    itself as class, stating nothing but that it is one — in
                    the example's scratch log only
    one rule, both  an application pinning both transaction modules and
                    Dewi's totals guarantees per rental and per booking
    labels          the form's choices for a role say what each one is and
                    which: "Rental — Budi, 2026-10-06", not an address
    stands alone    a class of a module pinning the library that points at
                    nothing shared, or names itself the way `Party` and `Item`
                    do, is an opening asking whether it is the library's
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

from components.business import declare  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from generate import form, read_map, submit  # noqa: E402
from perform import connect  # noqa: E402
from seal import register, seal  # noqa: E402

BUSINESS = "demo"
REGISTERED = [("@uniti/core", "v1"), ("@uniti/core", "v2"), ("@uniti/party", "v1"),
              ("@uniti/item", "v1"), ("@uniti/transaction", "v1")]
RENTAL, BOOKING, GUARANTEE, APP = "@rudi/sewa", "@sewapro/kasir", "@dewi/jaminan", "@demo/toko"
DAY = {"time_meaning": "happened"}


@pytest.fixture(scope="module")
def conn():
    """One connection, never committed: the seals here are rolled back."""
    with connect(os.environ["UNITI_DSN"]) as conn:
        yield conn
        conn.rollback()


@pytest.fixture(scope="module")
def store(conn, tmp_path_factory):
    held = Store([tmp_path_factory.mktemp("packages"), ROOT / "packages"])
    for name, version in REGISTERED:
        register(conn, held.path(name, version), actor_id="dev", store=held)
    declare(conn, BUSINESS, actor_id="dev")
    return held


def step(store, name, op, **args):
    return studio.apply(store, name, op, args)


def holes_of(store, name, conn=None):
    return reading.state(store, name, conn)["holes"]


def blocking(store, name, conn=None):
    return [(h["kind"], h["where"]) for h in holes_of(store, name, conn) if h["blocking"]]


def declared(store, name, class_name, slots):
    """A class and its slots, each slot attached and bound as it says."""
    for slot, range_, said, meant, binds in slots:
        step(store, name, "add_slot", slot=slot, range=range_, description=said, **meant)
        step(store, name, "attach", **{"class": class_name, "slot": slot})
        if binds:
            step(store, name, "bind", slot=slot, binding=binds)


def transactions(store, conn, name, class_name, word, title):
    """A module recording one kind of transaction, as Rudi and SewaPro do."""
    step(store, name, "start", title=title, description=f"One {word} of camping gear.")
    step(store, name, "pin", module="@uniti/transaction@v1")
    step(store, name, "add_class", **{"class": class_name,
                                      "description": f"One {word} by one customer."})
    step(store, name, "fill_role", **{"class": class_name, "role": "Transaction"})
    declared(store, name, class_name, [
        (f"{word}_customer", "Party", "Who it was with.", {}, "transaction_counterparty"),
        (f"{word}_date", "date", "The day it happened.", DAY, "moment"),
    ])
    seal(conn, studio.path(store, name), actor_id="dev",
         into=store.directory(name), store=store)


def guarantees(store, name=GUARANTEE):
    """Dewi's guarantees: money left against any transaction, totalled per
    transaction and per customer. It points at the role, never at a module."""
    step(store, name, "start", title="Guarantees",
         description="Money a customer leaves against a transaction, and what is held.")
    step(store, name, "pin", module="@uniti/transaction@v1")
    step(store, name, "add_class", **{"class": "Guarantee",
                                      "description": "Money left against one transaction."})
    step(store, name, "fill_role", **{"class": "Guarantee", "role": "Thing"})
    declared(store, name, "Guarantee", [
        ("guarantee_number", "string", "The receipt number.", {}, None),
        ("guarantee_customer", "Party", "Who left it.", {}, None),
        ("guarantee_date", "date", "The day it was left.", DAY, None),
        ("guarantee_for", "Transaction", "The transaction it secures, from any module.", {}, None),
        ("guarantee_amount", "decimal", "Money left.",
         {"unit": "IDR", "direction": "increase"}, None),
    ])
    step(store, name, "set_slot", slot="guarantee_number", field="identifier", value="true")
    step(store, name, "add_class", **{"class": "GuaranteeHeld",
                                      "description": "Guarantee money held per transaction."})
    declared(store, name, "GuaranteeHeld", [
        ("held_for", "Transaction", "The transaction.", {}, None),
        ("held_amount", "decimal", "Money held.", {"unit": "IDR", "direction": "level"}, None),
    ])
    step(store, name, "add_class", **{"class": "CustomerGuarantee",
                                      "description": "Guarantee money held per customer."})
    declared(store, name, "CustomerGuarantee", [
        ("customer_party", "Party", "The customer.", {}, None),
        ("customer_amount", "decimal", "Money held.", {"unit": "IDR", "direction": "level"}, None),
    ])
    step(store, name, "aggregate", **{"class": "GuaranteeHeld", "column": "held_amount",
                                      "over": "Guarantee", "sum": "guarantee_amount",
                                      "by": "held_for=guarantee_for"})
    step(store, name, "aggregate", **{"class": "CustomerGuarantee",
                                      "column": "customer_amount", "over": "Guarantee",
                                      "sum": "guarantee_amount",
                                      "by": "customer_party=guarantee_customer"})
    step(store, name, "add_example", example="own",
         says="Budi leaves 100000 against a transaction.")
    step(store, name, "record", example="own", record="budi", **{"class": "Party"},
         facts="party_name=Budi")
    return name


@pytest.fixture(scope="module")
def sealed(store, conn):
    """Rudi's rentals, SewaPro's bookings and Dewi's guarantees, sealed."""
    transactions(store, conn, RENTAL, "Rental", "rental", "Rentals")
    transactions(store, conn, BOOKING, "Booking", "booking", "Bookings")
    guarantees(store)
    step(store, GUARANTEE, "record", example="own", record="t1",
         **{"class": "Transaction"})
    step(store, GUARANTEE, "record", example="own", record="g1", **{"class": "Guarantee"},
         when="2026-10-06", facts="guarantee_number=G1, guarantee_customer=budi, "
         "guarantee_date=2026-10-06, guarantee_for=t1, guarantee_amount=100000")
    step(store, GUARANTEE, "expect", example="own", table="GuaranteeHeld", row="t1",
         values="held_amount=100000")
    step(store, GUARANTEE, "expect", example="own", table="CustomerGuarantee", row="budi",
         values="customer_amount=100000")
    step(store, GUARANTEE, "agree_example", example="own")
    return GUARANTEE


@pytest.fixture(scope="module")
def application(store, conn, sealed):
    """Sari's shop: Rudi's rentals and SewaPro's bookings, both secured by
    Dewi's guarantees, with nothing of its own but its example."""
    if not store.versions(GUARANTEE):
        seal(conn, studio.path(store, GUARANTEE), actor_id="dewi",
             into=store.directory(GUARANTEE), store=store)
    step(store, APP, "start", title="Guarantees held", kind="application", business=BUSINESS,
         description="Rentals and bookings, both secured by guarantees.")
    for pinned in (RENTAL, BOOKING, GUARANTEE):
        step(store, APP, "pin", module=f"{pinned}@v1")
    step(store, APP, "add_example", example="mixed",
         says="One rental and one booking, each with a guarantee.")
    for record, class_name, facts in (
        ("budi", "Party", "party_name=Budi"),
        ("ani", "Party", "party_name=Ani"),
        ("r1", "Rental", "rental_date=2026-10-06, rental_customer=budi"),
        ("b1", "Booking", "booking_date=2026-10-07, booking_customer=ani"),
        ("g1", "Guarantee", "guarantee_number=G1, guarantee_customer=budi, "
                            "guarantee_date=2026-10-06, guarantee_for=r1, guarantee_amount=150000"),
        ("g2", "Guarantee", "guarantee_number=G2, guarantee_customer=ani, "
                            "guarantee_date=2026-10-07, guarantee_for=b1, guarantee_amount=200000"),
    ):
        step(store, APP, "record", example="mixed", record=record,
             **{"class": class_name}, when="2026-10-07", facts=facts)
    for table, row, values in (("GuaranteeHeld", "r1", "held_amount=150000"),
                               ("GuaranteeHeld", "b1", "held_amount=200000"),
                               ("CustomerGuarantee", "budi", "customer_amount=150000"),
                               ("CustomerGuarantee", "ani", "customer_amount=200000")):
        step(store, APP, "expect", example="mixed", table=table, row=row, values=values)
    step(store, APP, "agree_example", example="mixed")
    return APP


# ---- a stand-in for the role --------------------------------------------------

def test_a_module_pointing_at_a_role_holds_its_own_example_with_a_stand_in(
        store, conn, sealed):
    report = reading.state(store, GUARANTEE, conn)
    assert [(h["kind"], h["where"]) for h in report["holes"] if h["blocking"]] == []
    [example] = report["examples"]
    assert example["passed"] is True, example
    out = seal(conn, studio.path(store, GUARANTEE), actor_id="dewi",
               into=store.directory(GUARANTEE), store=store)
    assert out["version"] == "v1"
    # The stand-in is the role: no class of Dewi's own pretends to be one.
    sealed_classes = studio.open_draft if False else None  # noqa: F841
    held = Path(store.path(GUARANTEE, "v1")).read_text(encoding="utf-8")
    assert "mixins:\n    - Transaction" not in held


def test_a_stand_in_states_nothing_but_that_it_is_one(store, conn):
    name = guarantees(store, "@dewi/salah")
    step(store, name, "record", example="own", record="t1", **{"class": "Transaction"},
         facts="guarantee_amount=5")
    [example] = reading.state(store, name, conn)["examples"]
    [refusal] = example["refusals"]
    assert refusal["code"] == "stand_in_states_facts"
    assert "Transaction" in refusal["got"]
    step(store, name, "discard")


def test_a_role_nothing_points_at_has_no_stand_in(store, conn):
    name = guarantees(store, "@dewi/baris")
    step(store, name, "record", example="own", record="l1",
         **{"class": "TransactionLine"})
    [example] = reading.state(store, name, conn)["examples"]
    [refusal] = example["refusals"]
    assert refusal["code"] == "no_type_slot"
    # What a record can be: the classes, and the stand-ins this draft needs.
    options = {o for r in refusal["repairs"] for o in (r["options"] or ())}
    assert "Transaction" in options and "TransactionLine" not in options
    step(store, name, "discard")


# ---- one rule over both modules, and choices that say what they are ---------

def test_one_guarantee_module_serves_rentals_and_bookings(store, conn, application):
    report = reading.state(store, APP, conn)
    assert [(h["kind"], h["where"]) for h in report["holes"] if h["blocking"]] == []
    [example] = report["examples"]
    assert example["passed"] is True, example
    out = seal(conn, studio.path(store, APP), actor_id="dev",
               into=store.directory(APP), store=store)
    assert out["version"] == "v1"


def test_the_choices_for_a_role_say_what_each_one_is(store, conn, application):
    if not store.versions(APP):
        seal(conn, studio.path(store, APP), actor_id="dev",
             into=store.directory(APP), store=store)
    map_ = read_map(store.path(APP, "v1"), store)
    rec = "https://uniti.example/demo/rec/"
    written = dict(actor_id="staff", valid_from="2026-10-07T09:00:00Z")
    for subject, who in (("budi", "Budi"), ("ani", "Ani")):
        submit(conn, map_, "Party", subject=rec + subject,
               values={"entity_class": "Party", "party_name": who}, **written)
    submit(conn, map_, "sewa__Rental", subject=rec + "r1",
           values={"entity_class": "sewa__Rental", "sewa__rental_date": "2026-10-06",
                   "sewa__rental_customer": rec + "budi"}, **written)
    submit(conn, map_, "kasir__Booking", subject=rec + "b1",
           values={"entity_class": "kasir__Booking", "kasir__booking_date": "2026-10-07",
                   "kasir__booking_customer": rec + "ani"}, **written)

    fields = {f["name"]: f for f in form(conn, map_, "jaminan__Guarantee",
                                         valid_at="2026-10-08T00:00:00Z")["fields"]}
    secured = dict(fields["jaminan__guarantee_for"]["options"])
    assert secured[rec + "r1"] == "Rental — Budi, 2026-10-06"
    assert secured[rec + "b1"] == "Booking — Ani, 2026-10-07"
    # A choice of the very class the field names needs no kind before it.
    customers = dict(fields["jaminan__guarantee_customer"]["options"])
    assert customers[rec + "budi"] == "Budi"


# ---- a class that stands alone ----------------------------------------------

def standing(store, name, conn=None):
    return {h["where"]: h for h in holes_of(store, name, conn)
            if h["kind"] == "stands_alone"}


def test_a_class_that_stands_alone_is_asked_whether_it_is_the_librarys(store):
    """Built like the first empty-store test's guarantee module: a customer of
    its own, and receipts pointing only at it."""
    name = "@kemah/titipan"
    step(store, name, "start", title="Deposits", description="Money customers leave.")
    step(store, name, "pin", module="@uniti/party@v1")
    step(store, name, "pin", module="@uniti/item@v1")
    step(store, name, "add_class", **{"class": "Customer", "description": "A customer."})
    step(store, name, "fill_role", **{"class": "Customer", "role": "Thing"})
    declared(store, name, "Customer", [
        ("customer_name", "string", "The customer's name.", {}, None)])
    step(store, name, "add_class", **{"class": "DepositReceipt",
                                      "description": "Money received from a customer."})
    step(store, name, "fill_role", **{"class": "DepositReceipt", "role": "Thing"})
    declared(store, name, "DepositReceipt", [
        ("receipt_customer", "Customer", "Who left it.", {}, None),
        ("receipt_amount", "decimal", "Money received.",
         {"unit": "IDR", "direction": "increase"}, None)])

    found = standing(store, name)
    assert set(found) == {"Customer", "DepositReceipt"}
    for hole in found.values():
        assert hole["blocking"] is False
        assert hole["step"]["op"] == "add_slot"
        assert {"Party", "Item"} <= set(hole["step"]["options"])
    assert "Party" in found["Customer"]["question"]

    # Pointing at the library's party connects the receipt; the customer that
    # still names itself is still asked about, even once it points at an item.
    declared(store, name, "DepositReceipt", [
        ("receipt_party", "Party", "Who left it, as the library knows them.", {}, None)])
    declared(store, name, "Customer", [
        ("customer_item", "Item", "What they usually rent.", {}, None)])
    assert set(standing(store, name)) == {"Customer"}
    step(store, name, "discard")


def test_a_module_that_pins_no_library_is_not_asked(store):
    name = "@kemah/sendiri"
    step(store, name, "start", title="Alone", description="Nothing shared.")
    step(store, name, "add_class", **{"class": "Customer", "description": "A customer."})
    step(store, name, "fill_role", **{"class": "Customer", "role": "Thing"})
    declared(store, name, "Customer", [
        ("customer_name", "string", "The customer's name.", {}, None)])
    assert standing(store, name) == {}
    step(store, name, "discard")

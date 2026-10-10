"""Modules read together under their own names (ECOSYSTEM_PLAN.md, step 1).

The scenario the plan measured (§4.3): two authors who never met both call a
class `Rental`, and both slots `rental_deposit`. Before, an application pinning
both had one `Rental` — whichever LinkML read last — and the other author's
own rules broke inside it. What has to hold now, and is asserted here:

    side by side    the application sees `penyewaan__Rental` and
                    `kasir__Rental`; each module's own table is still computed
                    by its own rule, inside the application
    one rule        a name a person writes plain means the one module that
                    declares it; where two do, "which one?" with both offered
    same URIs       a qualified name records under exactly the predicate the
                    plain one did, so nothing in the log moves
    what stays      core's and the library's names are plain for everybody
    refused         and are nobody else's to declare; a name with `__`; two
                    modules with the same tag in one closure; a draft
                    declaring what a module it pins declares
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from components.business import declare  # noqa: E402
from components.modules import compose  # noqa: E402
from components.modules import read as modules_read  # noqa: E402
from components.modules.store import ModuleError, Store  # noqa: E402
from components.refusal import Refusal  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from compile import plan_for, tables  # noqa: E402
from generate import table_name  # noqa: E402
from perform import connect  # noqa: E402
from seal import class_uri, predicate, register, seal  # noqa: E402

BUSINESS = "demo"
REGISTERED = [("@uniti/core", "v1"), ("@uniti/core", "v2"),
              ("@uniti/party", "v1"), ("@uniti/transaction", "v1")]
RUDI, TILL, APP = "@komunitas/penyewaan", "@lain/kasir", "@demo/both"


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


def refused(store, name, op, **args):
    with pytest.raises(Refusal) as caught:
        step(store, name, op, **args)
    return caught.value


def _rental(store, conn, name, deposit):
    """A rental and what it holds per customer, as each author would build it:
    the same class names and the same slot names, by steps alone."""
    step(store, name, "start", title="Rental",
         description="Equipment rented out and the deposits left against it.")
    for pin in ("@uniti/party@v1", "@uniti/transaction@v1"):
        step(store, name, "pin", module=pin)
    for class_name, said in (("Rental", "One customer renting on one day."),
                             ("CustomerDeposit", "Deposit money held per customer.")):
        step(store, name, "add_class", **{"class": class_name, "description": said})
    step(store, name, "fill_role", **{"class": "Rental", "role": "Transaction"})
    day = {"time_meaning": "happened"}
    for class_name, slot, kind, said, meant, binds in (
        ("Rental", "rental_number", "string", "The number on the note.", {}, None),
        ("Rental", "rental_customer", "Party", "Who rented.", {}, "transaction_counterparty"),
        ("Rental", "rental_date", "date", "The day of the rental.", day, "moment"),
        ("Rental", "rental_deposit", "decimal", "Money left against it.",
         {"unit": "IDR", "direction": "increase"}, None),
        ("CustomerDeposit", "customer_deposit_party", "Party", "The customer.", {}, None),
        ("CustomerDeposit", "customer_deposit_total", "decimal", "Deposit money held.",
         {"unit": "IDR", "direction": "level"}, None),
    ):
        step(store, name, "add_slot", slot=slot, range=kind, description=said, **meant)
        step(store, name, "attach", **{"class": class_name, "slot": slot})
        if binds:
            step(store, name, "bind", slot=slot, binding=binds)
    step(store, name, "set_slot", slot="rental_number", field="identifier", value="true")
    step(store, name, "aggregate", **{
        "class": "CustomerDeposit", "column": "customer_deposit_total",
        "over": "Rental", "sum": "rental_deposit",
        "by": "customer_deposit_party=rental_customer"})
    step(store, name, "add_example", example="budi",
         says=f"Budi rents once and leaves {deposit} against it.")
    step(store, name, "record", example="budi", record="budi", **{"class": "Party"},
         facts="party_name=Budi")
    step(store, name, "record", example="budi", record="r1", **{"class": "Rental"},
         when="2026-10-06", facts=f"rental_number=R1, rental_customer=budi, "
                                  f"rental_date=2026-10-06, rental_deposit={deposit}")
    step(store, name, "expect", example="budi", table="CustomerDeposit", row="budi",
         values=f"customer_deposit_total={deposit}")
    step(store, name, "agree_example", example="budi")
    seal(conn, studio.path(store, name), actor_id="dev",
         into=store.directory(name), store=store)
    return name


@pytest.fixture(scope="module")
def both(store, conn):
    """Rudi's rental and another author's, sealed apart, each its own `Rental`."""
    return _rental(store, conn, RUDI, 100000), _rental(store, conn, TILL, 50000)


@pytest.fixture(scope="module")
def application(store, conn, both):
    """One business totalling the deposits taken under either module."""
    step(store, APP, "start", title="Both tills", kind="application", business=BUSINESS,
         description="Deposits taken on Rudi's rentals and at the other till.")
    step(store, APP, "pin", module=f"{RUDI}@v1")
    step(store, APP, "pin", module=f"{TILL}@v1")
    step(store, APP, "add_class", **{"class": "DepositTaken",
                                     "description": "Deposits per customer, both tills."})
    for slot, kind, said, meant in (
        ("deposit_taken_party", "Party", "The customer.", {}),
        ("deposit_taken_rudi", "decimal", "Deposits on Rudi's rentals.",
         {"unit": "IDR", "direction": "level"}),
        ("deposit_taken_till", "decimal", "Deposits at the other till.",
         {"unit": "IDR", "direction": "level"}),
    ):
        step(store, APP, "add_slot", slot=slot, range=kind, description=said, **meant)
        step(store, APP, "attach", **{"class": "DepositTaken", "slot": slot})
    return APP


def _finish(store, conn):
    """The rules and the example, with every name said in full where two
    modules declare it."""
    for column, tag in (("deposit_taken_rudi", "penyewaan"), ("deposit_taken_till", "kasir")):
        step(store, APP, "aggregate", **{
            "class": "DepositTaken", "column": column, "over": f"{tag}__Rental",
            "sum": f"{tag}__rental_deposit",
            "by": f"deposit_taken_party={tag}__rental_customer"})
    step(store, APP, "add_example", example="budi",
         says="Budi leaves 100000 with Rudi and 50000 at the other till.")
    step(store, APP, "record", example="budi", record="budi", **{"class": "Party"},
         facts="party_name=Budi")
    for record, tag, deposit in (("r1", "penyewaan", 100000), ("t1", "kasir", 50000)):
        step(store, APP, "record", example="budi", record=record,
             **{"class": f"{tag}__Rental"}, when="2026-10-06",
             facts=f"rental_number={record.upper()}, rental_customer=budi, "
                   f"rental_date=2026-10-06, rental_deposit={deposit}")
    step(store, APP, "expect", example="budi", table="DepositTaken", row="budi",
         values="deposit_taken_rudi=100000, deposit_taken_till=50000")
    # Rudi's own rule, read inside the application, still answers for his
    # rentals alone: the till's `Rental` is not his.
    step(store, APP, "expect", example="budi", table="penyewaan__CustomerDeposit",
         row="budi", values="customer_deposit_total=100000")
    step(store, APP, "expect", example="budi", table="kasir__CustomerDeposit",
         row="budi", values="customer_deposit_total=50000")
    step(store, APP, "agree_example", example="budi")


# ---- the scenario ---------------------------------------------------------

def test_two_modules_declaring_rental_are_read_side_by_side(store, application):
    view = store.view(studio.path(store, APP))
    classes = set(view.all_classes())
    assert {"penyewaan__Rental", "kasir__Rental"} <= classes
    assert "Rental" not in classes
    assert {"penyewaan__rental_deposit", "kasir__rental_deposit"} <= set(view.all_slots())
    # What everybody shares stays plain.
    assert {"Party", "Transaction", "Thing"} <= classes
    assert {"party_name", "transaction_counterparty", "entity_class"} <= set(view.all_slots())


def test_a_plain_name_two_modules_declare_is_asked_about(store, conn, application):
    step(store, APP, "add_example", example="probe", says="Which rental?")
    caught = refused(store, APP, "record", example="probe", record="r",
                     **{"class": "Rental"})
    assert caught.code == "name_ambiguous"
    assert list(caught.repairs[0].options) == ["kasir__Rental", "penyewaan__Rental"]
    step(store, APP, "remove_example", example="probe")

    # A rule written with the plain name is a hole naming both.
    step(store, APP, "aggregate", **{
        "class": "DepositTaken", "column": "deposit_taken_rudi", "over": "Rental",
        "sum": "rental_deposit", "by": "deposit_taken_party=rental_customer"})
    holes = reading.state(store, APP, conn)["holes"]
    asked = {h["where"]: h for h in holes if h["kind"] == "name_ambiguous"}
    assert set(asked) == {"draft.yaml: Rental", "draft.yaml: rental_customer",
                          "draft.yaml: rental_deposit"}
    assert all(h["blocking"] for h in asked.values())
    rental = asked["draft.yaml: Rental"]
    assert rental["refusal"]["repairs"][0]["options"] == ["kasir__Rental",
                                                          "penyewaan__Rental"]
    assert "which Rental is meant" in rental["question"]


def test_a_plain_name_one_module_declares_is_kept_in_full(store, application):
    step(store, APP, "add_slot", slot="deposit_taken_note", range="string",
         description="A note.")
    document = studio.open_draft(store, APP)
    step(store, APP, "remove_slot", slot="deposit_taken_note")
    assert document["slots"]["deposit_taken_party"]["range"] == "Party"
    held = Store(store.roots)
    probe = "@demo/one"
    step(held, probe, "start", title="One", description="Pins one rental module.")
    step(held, probe, "pin", module=f"{RUDI}@v1")
    step(held, probe, "add_class", **{"class": "RentalNote", "description": "A note."})
    step(held, probe, "add_slot", slot="rental_note_rental", range="Rental",
         description="The rental it is about.")
    document = studio.open_draft(held, probe)
    assert document["slots"]["rental_note_rental"]["range"] == "penyewaan__Rental"


def test_each_modules_own_rules_hold_inside_the_application_and_it_seals(
        store, conn, application):
    _finish(store, conn)
    report = reading.state(store, APP, conn)
    blocking = [(h["kind"], h["where"]) for h in report["holes"] if h["blocking"]]
    assert blocking == []
    [example] = report["examples"]
    assert example["passed"] is True, example

    map_ = reading._map(store, APP, studio.open_draft(store, APP))
    assert {"DepositTaken", "penyewaan__CustomerDeposit",
            "kasir__CustomerDeposit"} <= set(tables(map_))
    assert plan_for(map_, "penyewaan__CustomerDeposit")["aggregates"][
        "penyewaan__customer_deposit_total"]["over"] == "penyewaan__Rental"
    assert table_name("penyewaan__CustomerDeposit") == "p_penyewaan__customer_deposit"

    out = seal(conn, studio.path(store, APP), actor_id="dev",
               into=store.directory(APP), store=store)
    assert out["version"] == "v1"
    sealed = store.document(APP, "v1")
    spec = sealed["slots"]["deposit_taken_till"]["annotations"]["aggregate"]["value"]
    assert spec["over"] == "kasir__Rental"


def test_a_qualified_name_records_under_the_predicate_the_plain_one_did(
        store, conn, both):
    app = store.view(store.path(APP, "v1")) if store.versions(APP) else \
        store.view(studio.path(store, APP))
    for module, tag in ((RUDI, "penyewaan"), (TILL, "kasir")):
        own = store.view(store.path(module, "v1"))
        assert class_uri(own, "Rental") == class_uri(app, f"{tag}__Rental")
        for slot in ("rental_deposit", "rental_customer", "rental_number"):
            assert predicate(own, own.induced_slot(slot)) == \
                predicate(app, app.induced_slot(f"{tag}__{slot}"))
    # Two authors, two predicates: the names were the same, the words never.
    assert predicate(app, app.induced_slot("penyewaan__rental_deposit")) != \
        predicate(app, app.induced_slot("kasir__rental_deposit"))
    assert class_uri(app, "penyewaan__Rental") != class_uri(app, "kasir__Rental")


def test_the_store_page_shows_each_name_with_where_it_came_from(store, both):
    detail = modules_read.version(store, RUDI, "v1")
    by_name = {c["name"]: c for c in detail["classes"]}
    # A version's own names are plain on its own page; what it pins is
    # shown as the library names it.
    assert by_name["Rental"]["from"] == {"name": RUDI, "version": "v1"}
    assert by_name["Party"]["from"]["name"] == "@uniti/party"

    graph = modules_read.class_graph(store, APP, "v1")
    nodes = {n["name"]: n for n in graph["nodes"]}
    assert nodes["kasir__Rental"]["module"] == {"name": TILL, "version": "v1"}
    assert nodes["penyewaan__Rental"]["fills"] == ["Transaction"]
    assert {"from": "DepositTaken", "to": "kasir__Rental", "kind": "aggregate",
            "label": "deposit_taken_till"} in graph["edges"]


# ---- what is still refused ------------------------------------------------

def test_two_modules_with_one_tag_cannot_be_pinned_together(store, conn, both):
    other = "@rudi/penyewaan"
    _rental(store, conn, other, 70000)
    probe = "@demo/twotags"
    step(store, probe, "start", title="Two tags", description="Pins both rentals.")
    step(store, probe, "pin", module=f"{RUDI}@v1")
    caught = refused(store, probe, "pin", module=f"{other}@v1")
    assert caught.code == "tag_taken"
    assert list(caught.repairs[0].options) == [RUDI, other]
    assert studio.open_draft(store, probe)["imports"][-1] == f"{RUDI}@v1"


def test_core_and_library_names_are_nobody_elses(store, both):
    probe = "@demo/names"
    step(store, probe, "start", title="Names", description="Tries names.")
    step(store, probe, "pin", module=f"{RUDI}@v1")
    for op, args in (("add_class", {"class": "Party"}),
                     ("add_class", {"class": "Transaction"}),
                     ("add_slot", {"slot": "party_name"}),
                     ("add_class", {"class": "Two__Parts"})):
        assert refused(store, probe, op, **args).code == "name_reserved", args
    # A name a pinned module declares is still taken by its plain part.
    caught = refused(store, probe, "add_class", **{"class": "Rental"})
    assert caught.code == "name_taken"
    assert RUDI in caught.got


def test_tags_and_plain_names():
    assert compose.tag_of("@komunitas/penyewaan") == "penyewaan"
    assert compose.tag_of("@rival/stock-moves") == "stock_moves"
    assert compose.plain("penyewaan__Rental") == "Rental"
    assert compose.plain("Rental") == "Rental"
    known = {"penyewaan__Rental", "kasir__Rental", "Party", "kasir__Till"}
    assert compose.matches("Party", known) == ["Party"]
    assert compose.matches("Till", known) == ["kasir__Till"]
    assert compose.matches("Rental", known) == ["kasir__Rental", "penyewaan__Rental"]
    assert compose.matches("Nothing", known) == []

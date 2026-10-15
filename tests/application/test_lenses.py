"""Two lenses, and what a revision means for each user (ECOSYSTEM_PLAN.md,
step 7; stories 4 and 5).

The business owner reads her application as her business: things, events
and numbers, each with the title of the module it came from as a small
mark, never a composed name. A module's author reads his module as its
connections: what it points at, what it adds to whose things, which roles
it fills, and which shared modules build on it.

When an author seals a new version of a module an application pins, the
business owner is told before she moves: what changes, said as fields and
things, and her own examples run against the new version. Moving is three
ordinary Studio steps on a draft of her application; she seals it herself.
What was recorded before stays as it was.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "seal"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))

from components.api import application as app_api  # noqa: E402
from components.business import declare, install  # noqa: E402
from components.modules import read as modules_read  # noqa: E402
from components.modules.store import Store  # noqa: E402
from components.studio import draft as studio  # noqa: E402
from components.studio import read as reading  # noqa: E402
from perform import connect  # noqa: E402
from seal import register, seal  # noqa: E402

BUSINESS = "demo"
REGISTERED = [("@uniti/core", "v1"), ("@uniti/core", "v2"), ("@uniti/party", "v1"),
              ("@uniti/transaction", "v1"), ("@uniti/item", "v1"), ("@uniti/item", "v2")]
RUDI, DEWI, LAPORAN, APP = "@rudi/sewa", "@dewi/jaminan", "@komunitas/laporan", "@demo/kemah"
DAY = datetime(2026, 10, 8, tzinfo=timezone.utc)
NOW = datetime.now(timezone.utc)


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


def _sealed(store, conn, name, actor):
    blocking = [(h["kind"], h["where"]) for h in reading.state(store, name, conn)["holes"]
                if h["blocking"]]
    assert blocking == [], blocking
    out = seal(conn, studio.path(store, name), actor_id=actor,
               into=store.directory(name), store=store)
    # As the Studio's seal does: the draft is closed once it is a version.
    studio.closed(store, name, out["version"])
    return out


def _slots(store, name, rows):
    for class_name, slot, kind, said, meant, binds in rows:
        step(store, name, "add_slot", slot=slot, range=kind, description=said, **meant)
        step(store, name, "attach", **{"class": class_name, "slot": slot})
        if binds:
            step(store, name, "bind", slot=slot, binding=binds)


@pytest.fixture(scope="module")
def rudi(store, conn):
    """Rudi's rentals: a rental fills `Transaction`, the rate is a facet on
    the library's `Item`, and a total per customer."""
    step(store, RUDI, "start", title="Penyewaan alat kemah",
         description="Camping gear rented out, and the deposits left against it.")
    for pin in ("@uniti/party@v1", "@uniti/transaction@v1", "@uniti/item@v2"):
        step(store, RUDI, "pin", module=pin)
    for class_name, said in (("Rental", "One customer renting on one day."),
                             ("CustomerDeposit", "Deposit money held per customer.")):
        step(store, RUDI, "add_class", **{"class": class_name, "description": said})
    step(store, RUDI, "fill_role", **{"class": "Rental", "role": "Transaction"})
    _slots(store, RUDI, (
        ("Rental", "rental_number", "string", "The number on the note.", {}, None),
        ("Rental", "rental_customer", "Party", "Who rented.", {}, "transaction_counterparty"),
        ("Rental", "rental_date", "date", "The day of the rental.",
         {"time_meaning": "happened"}, "moment"),
        ("Rental", "rental_deposit", "decimal", "Money left against it.",
         {"unit": "IDR", "direction": "increase"}, None),
        ("Item", "rental_rate", "decimal", "What one day of renting this item costs.",
         {"unit": "IDR", "direction": "level"}, None),
        ("CustomerDeposit", "customer_deposit_party", "Party", "The customer.", {}, None),
        ("CustomerDeposit", "customer_deposit_total", "decimal", "Deposit money held.",
         {"unit": "IDR", "direction": "level"}, None),
    ))
    step(store, RUDI, "set_slot", slot="rental_number", field="identifier", value="true")
    step(store, RUDI, "aggregate", **{
        "class": "CustomerDeposit", "column": "customer_deposit_total",
        "over": "Rental", "sum": "rental_deposit",
        "by": "customer_deposit_party=rental_customer"})
    step(store, RUDI, "add_example", example="budi",
         says="Budi rents once and leaves 100000 against it.")
    step(store, RUDI, "record", example="budi", record="budi", **{"class": "Party"},
         facts="party_name=Budi")
    step(store, RUDI, "record", example="budi", record="r1", **{"class": "Rental"},
         when="2026-10-06", facts="rental_number=R1, rental_customer=budi, "
                                  "rental_date=2026-10-06, rental_deposit=100000")
    step(store, RUDI, "expect", example="budi", table="CustomerDeposit", row="budi",
         values="customer_deposit_total=100000")
    step(store, RUDI, "agree_example", example="budi")
    _sealed(store, conn, RUDI, "rudi")
    return RUDI


@pytest.fixture(scope="module")
def dewi(store, conn):
    """Dewi's guarantees, against any transaction: she never heard of Rudi."""
    step(store, DEWI, "start", title="Jaminan sewa",
         description="A guarantee left against any transaction.")
    for pin in ("@uniti/party@v1", "@uniti/transaction@v1"):
        step(store, DEWI, "pin", module=pin)
    step(store, DEWI, "add_class", **{"class": "Guarantee",
                                      "description": "Money left against a transaction."})
    step(store, DEWI, "fill_role", **{"class": "Guarantee", "role": "Thing"})
    _slots(store, DEWI, (
        ("Guarantee", "guarantee_for", "Transaction", "The transaction it is left against.",
         {}, None),
        ("Guarantee", "guarantee_amount", "decimal", "Money left.",
         {"unit": "IDR", "direction": "increase"}, None),
    ))
    _sealed(store, conn, DEWI, "dewi")
    return DEWI


@pytest.fixture(scope="module")
def laporan(store, conn, rudi):
    """A shared module built on Rudi's: it adds one field to his rentals."""
    step(store, LAPORAN, "start", title="Laporan sewa",
         description="Whether a rental has been checked on its return.")
    step(store, LAPORAN, "pin", module=f"{RUDI}@v1")
    step(store, LAPORAN, "add_slot", slot="rental_checked", range="boolean",
         description="Checked on its return.")
    step(store, LAPORAN, "attach", **{"class": "Rental", "slot": "rental_checked"})
    _sealed(store, conn, LAPORAN, "komunitas")
    return LAPORAN


@pytest.fixture(scope="module")
def kemah(store, conn, rudi, dewi, laporan):
    """Sari's application: Rudi's rentals and Dewi's guarantees, and the
    deposits per customer, installed and with records stated through it."""
    step(store, APP, "start", title="Kemah Ceria", kind="application", business=BUSINESS,
         description="The camping shop's rentals and guarantees.")
    step(store, APP, "pin", module=f"{RUDI}@v1")
    step(store, APP, "pin", module=f"{DEWI}@v1")
    step(store, APP, "add_class", **{"class": "DepositTaken",
                                     "description": "Deposits per customer."})
    _slots(store, APP, (
        ("DepositTaken", "deposit_taken_party", "Party", "The customer.", {}, None),
        ("DepositTaken", "deposit_taken_total", "decimal", "Deposits taken.",
         {"unit": "IDR", "direction": "level"}, None),
    ))
    step(store, APP, "aggregate", **{
        "class": "DepositTaken", "column": "deposit_taken_total", "over": "Rental",
        "sum": "rental_deposit", "by": "deposit_taken_party=rental_customer"})
    step(store, APP, "add_example", example="budi",
         says="Budi rents twice, leaving 100000 and 50000.")
    step(store, APP, "record", example="budi", record="budi", **{"class": "Party"},
         facts="party_name=Budi")
    for record, deposit in (("r1", 100000), ("r2", 50000)):
        step(store, APP, "record", example="budi", record=record, **{"class": "Rental"},
             when="2026-10-06", facts=f"rental_number={record.upper()}, "
                                      f"rental_customer=budi, rental_date=2026-10-06, "
                                      f"rental_deposit={deposit}")
    step(store, APP, "expect", example="budi", table="DepositTaken", row="budi",
         values="deposit_taken_total=150000")
    step(store, APP, "agree_example", example="budi")
    _sealed(store, conn, APP, "dev")
    install(conn, store, APP, "v1", actor_id="sari",
            valid_from=datetime(2026, 10, 1, tzinfo=timezone.utc))
    for class_name, subject, values, day in (
        ("Party", "kc:budi", {"party_name": "Budi"}, 5),
        ("Rental", "kc:r1", {"rental_number": "R1", "rental_customer": "kc:budi",
                             "rental_date": "2026-10-06", "rental_deposit": "100000"}, 6),
    ):
        app_api.state(conn, store, APP, "v1", class_name, subject=subject, values=values,
                      actor_id="sari",
                      valid_from=datetime(2026, 10, day, tzinfo=timezone.utc))
    return APP


@pytest.fixture(scope="module")
def rudi_v2(store, conn, kemah):
    """Rudi's second version: a rental gains a note."""
    step(store, RUDI, "revise")
    _slots(store, RUDI, (
        ("Rental", "rental_note", "string", "Anything worth knowing about the rental.",
         {}, None),
    ))
    out = _sealed(store, conn, RUDI, "rudi")
    assert out["version"] == "v2"
    return RUDI


# ---- the business lens -------------------------------------------------------

def test_an_application_reads_as_things_events_and_numbers(store, kemah):
    read = app_api.application(store, APP, "v1")
    lens = {t["class"]: t["lens"] for t in read["tables"]}
    assert lens["rudi_sewa__Rental"] == "event"
    assert lens["Party"] == "thing"
    assert lens["Item"] == "thing"
    assert lens["dewi_jaminan__Guarantee"] == "thing"
    assert lens["rudi_sewa__CustomerDeposit"] == "number"
    assert lens["DepositTaken"] == "number"


def test_each_table_and_module_carries_the_title_it_is_marked_with(store, kemah):
    read = app_api.application(store, APP, "v1")
    assert read["title"] == "Kemah Ceria"
    marks = {t["class"]: t["module_title"] for t in read["tables"]}
    assert marks["rudi_sewa__Rental"] == "Penyewaan alat kemah"
    assert marks["dewi_jaminan__Guarantee"] == "Jaminan sewa"
    assert marks["DepositTaken"] == "Kemah Ceria"
    titles = {m["name"]: (m["title"], m["kind"]) for m in read["modules"]}
    assert titles[RUDI] == ("Penyewaan alat kemah", "module")
    # The library is the common ground, not somebody's module: no mark.
    assert titles["@uniti/item"][1] == "library"


def test_the_item_carries_the_rate_another_module_adds_to_it(store, conn, kemah):
    item = app_api.projection(conn, store, APP, "v1", "Item", valid_at=DAY, as_of=NOW)
    [rate] = [c for c in item["columns"] if c["name"].endswith("rental_rate")]
    assert rate["module_title"] == "Penyewaan alat kemah"
    # The column saying which class a row is, is the form's bookkeeping.
    assert [c["carries_class"] for c in item["columns"]].count(True) == 1


def test_a_choice_says_which_module_its_kind_comes_from(store, conn, kemah):
    form = app_api.form_of(conn, store, APP, "v1", "Guarantee", valid_at=DAY,
                               as_of=datetime.now(timezone.utc))
    [field] = [f for f in form["fields"] if f["name"].endswith("guarantee_for")]
    [option] = field["options"]
    assert option["label"].startswith("Rental")
    assert option["from"] == "Penyewaan alat kemah"
    assert field["module_title"] == "Jaminan sewa"


# ---- a new version, told before the move -----------------------------------

def test_nothing_is_offered_while_every_pin_is_the_latest(store, conn, kemah):
    assert app_api.updates(conn, store, APP, "v1") == []


def test_a_new_version_is_offered_with_what_changes_and_her_examples_on_it(
        store, conn, rudi_v2):
    before = _held(conn)
    [update] = app_api.updates(conn, store, APP, "v1")
    assert (update["module"], update["title"]) == (RUDI, "Penyewaan alat kemah")
    assert (update["pinned"], update["latest"]) == ("v1", "v2")
    assert update["refusal"] is None
    assert {"change": "added", "what": "field", "name": "rental_note", "on": "Rental",
            "description": "Anything worth knowing about the rental."} in update["changes"]
    [example] = update["examples"]
    assert example["name"] == "budi"
    assert example["passed"] is True
    assert example["says"] == "Budi rents twice, leaving 100000 and 50000."
    # The examples ran in a scratch log: nothing reached the real one.
    assert _held(conn) == before


def test_moving_is_three_studio_steps_and_what_was_recorded_stays(store, conn, rudi_v2):
    step(store, APP, "revise")
    step(store, APP, "unpin", module=f"{RUDI}@v1")
    step(store, APP, "pin", module=f"{RUDI}@v2")
    report = reading.state(store, APP, conn)
    # The Studio is told whom it helps: an application's composer.
    assert report["kind"] == "application"
    [example] = report["examples"]
    assert example["passed"] is True
    out = _sealed(store, conn, APP, "dev")
    assert out["version"] == "v2"

    def rows(version):
        return app_api.projection(conn, store, APP, version, "DepositTaken",
                                  valid_at=DAY, as_of=datetime.now(timezone.utc))["rows"]
    assert rows("v2") == rows("v1")
    assert rows("v1") != []


# ---- the connection lens ---------------------------------------------------------

def test_a_module_reads_as_its_connections(store, conn, kemah):
    out = modules_read.connections(store, RUDI, "v1")
    assert {"class": "Rental", "role": "Transaction",
            "module": {"name": "@uniti/transaction", "version": "v1"}} in out["fills"]
    assert {"slot": "rental_rate", "class": "Item",
            "module": {"name": "@uniti/item", "version": "v2"}} in out["adds_to"]
    assert {"slot": "rental_customer", "class": "Party",
            "module": {"name": "@uniti/party", "version": "v1"}} in out["points_at"]


def test_who_builds_on_a_module_is_only_shared_modules(store, conn, kemah):
    # Laporan pins Rudi's module; so does Sari's application, which is
    # private to her business and is not listed.
    out = modules_read.connections(store, RUDI, "v1")
    assert out["built_on_by"] == [{"name": LAPORAN, "version": "v1",
                                   "title": "Laporan sewa", "pins": "v1"}]
    laporan = modules_read.connections(store, LAPORAN, "v1")
    assert {"slot": "rental_checked", "class": "Rental",
            "module": {"name": RUDI, "version": "v1"}} in laporan["adds_to"]


def _held(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM assertion")
        return cur.fetchone()[0]

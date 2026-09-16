import tempfile
from pathlib import Path
import pytest
import yaml

from components.studio.catalog import SemanticCatalog
from components.studio.patcher import SchemaPatcher

def test_semantic_catalog_search():
    catalog = SemanticCatalog()
    res = catalog.search("quantity")
    assert len(res) > 0
    assert res[0]["curie"] == "inv:quantity"

    po_res = catalog.search("purchase order")
    assert any(r["curie"] == "proc:po_number" for r in po_res)

def test_schema_patcher_crud():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        p = Path(f.name)
    try:
        patcher = SchemaPatcher(p)
        patcher.add_class(
            name="StockMovement",
            is_a="Event",
            description="Perpindahan stok fisik",
            slots=["movement_qty"],
        )
        patcher.add_slot(
            name="movement_qty",
            slot_uri="inv:quantity",
            range="decimal",
            description="Jumlah perpindahan",
        )
        patcher.add_invariant(
            class_name="StockMovement",
            inv_id="positive_qty",
            expression="self.movement_qty > 0",
            message="Kuantitas perpindahan harus lebih besar dari 0",
        )
        patcher.set_lifecycle(
            class_name="StockMovement",
            initial="RECORDED",
            states={"RECORDED": {}, "VERIFIED": {}},
            transitions=[{"from": "RECORDED", "to": "VERIFIED"}],
        )
        patcher.save()

        # Reload and check
        reloaded = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert "StockMovement" in reloaded["classes"]
        assert reloaded["classes"]["StockMovement"]["is_a"] == "Event"
        assert "movement_qty" in reloaded["slots"]
        assert reloaded["slots"]["movement_qty"]["slot_uri"] == "inv:quantity"
        invs = reloaded["classes"]["StockMovement"]["annotations"]["invariants"]["value"]
        assert invs[0]["id"] == "positive_qty"
    finally:
        p.unlink(missing_ok=True)


def test_semantic_catalog_domain_filter():
    catalog = SemanticCatalog()
    fin_res = catalog.search("amount", domain="finance")
    assert all(r["domain"] == "finance" for r in fin_res)

    inv_res = catalog.search("amount", domain="inventory")
    assert len(inv_res) == 0

def test_patcher_error_handling_and_update():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        p = Path(f.name)
    try:
        patcher = SchemaPatcher(p)
        # Calling add_invariant on non-existent class raises KeyError
        with pytest.raises(KeyError):
            patcher.add_invariant("GhostClass", "inv1", "self.x > 0", "msg")

        # Add class and slot
        patcher.add_class("Invoice", is_a="Event", description="Billing event")
        patcher.add_invariant("Invoice", "inv1", "self.amount > 0", "initial msg")
        # Updating same invariant id updates in-place
        patcher.add_invariant("Invoice", "inv1", "self.amount >= 0", "updated msg")
        assert len(patcher.data["classes"]["Invoice"]["annotations"]["invariants"]["value"]) == 1
        assert patcher.data["classes"]["Invoice"]["annotations"]["invariants"]["value"][0]["expression"] == "self.amount >= 0"
    finally:
        p.unlink(missing_ok=True)

def test_patched_draft_passes_linter():
    from components.linter.engine import LinterEngine
    from components.linter.package_loader import PackageLoader
    ROOT = Path(__file__).resolve().parent.parent.parent

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, dir=str(ROOT / "packages")) as f:
        p = Path(f.name)
    try:
        patcher = SchemaPatcher(p)
        patcher.add_class(
            name="RawFabric",
            is_a="Resource",
            description="Bahan mentah kain",
            slots=["fabric_weight"],
        )
        patcher.add_slot(
            name="fabric_weight",
            slot_uri="inv:quantity",
            range="decimal",
            description="Berat kain dalam kilogram",
        )
        patcher.save()

        loader = PackageLoader(packages_dir=ROOT / "packages")
        linter = LinterEngine(loader=loader)
        diagnostics = linter.lint_schema(p)
        errors = [d for d in diagnostics if d.severity == "ERROR"]
        assert len(errors) == 0
    finally:
        p.unlink(missing_ok=True)

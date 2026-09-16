from pathlib import Path
import pytest
from components.linter.package_loader import PackageLoader
from components.linter.engine import LinterEngine

ROOT = Path(__file__).resolve().parent.parent.parent

@pytest.fixture
def loader():
    return PackageLoader(packages_dir=ROOT / "packages")

@pytest.fixture
def linter(loader):
    return LinterEngine(loader=loader)

INV_SCHEMA = ROOT / "packages" / "@community" / "inventory" / "schema" / "domain.yaml"
TEXTILE_SCHEMA = ROOT / "packages" / "@tenants" / "textile_corp" / "schema" / "domain.yaml"
GELATO_SCHEMA = ROOT / "packages" / "@tenants" / "sorella_gelato" / "schema" / "domain.yaml"

@pytest.mark.skipif(not INV_SCHEMA.exists(), reason="Community inventory not present in clean-slate mode")
def test_community_inventory_compilation(loader, linter):
    inv_schema = ROOT / "packages" / "@community" / "inventory" / "schema" / "domain.yaml"
    diagnostics = linter.lint_schema(inv_schema)
    errors = [d for d in diagnostics if d.severity == "ERROR"]
    assert len(errors) == 0

    sv = loader.load_schemaview(inv_schema)
    classes = sv.all_classes()
    assert "InventoryItem" in classes
    assert "StockMovement" in classes
    assert "StockOnHand" in classes
    assert "Resource" in sv.class_ancestors("InventoryItem")
    assert "Event" in sv.class_ancestors("StockMovement")
    assert "Projection" in sv.class_ancestors("StockOnHand")

@pytest.mark.skipif(not TEXTILE_SCHEMA.exists(), reason="Textile tenant not present in clean-slate mode")
def test_textile_corp_modular_inheritance(loader, linter):
    textile_schema = ROOT / "packages" / "@tenants" / "textile_corp" / "schema" / "domain.yaml"
    diagnostics = linter.lint_schema(textile_schema)
    errors = [d for d in diagnostics if d.severity == "ERROR"]
    assert len(errors) == 0

    sv = loader.load_schemaview(textile_schema)
    classes = sv.all_classes()
    assert "FabricRoll" in classes
    assert "LoomRun" in classes

    # Lineage check: FabricRoll -> InventoryItem -> Resource -> CoreClass
    ancestors = sv.class_ancestors("FabricRoll")
    assert "InventoryItem" in ancestors
    assert "Resource" in ancestors
    assert "CoreClass" in ancestors

    # Universal URI check on domain slot
    roll_slot = sv.all_slots()["roll_length_meters"]
    assert roll_slot.slot_uri == "inv:quantity"

@pytest.mark.skipif(not GELATO_SCHEMA.exists(), reason="Gelato tenant not present in clean-slate mode")
def test_sorella_gelato_modular_inheritance(loader, linter):
    gelato_schema = ROOT / "packages" / "@tenants" / "sorella_gelato" / "schema" / "domain.yaml"
    diagnostics = linter.lint_schema(gelato_schema)
    errors = [d for d in diagnostics if d.severity == "ERROR"]
    assert len(errors) == 0

    sv = loader.load_schemaview(gelato_schema)
    classes = sv.all_classes()
    assert "GelatoTub" in classes
    assert "ChurnBatch" in classes

    # Lineage check: GelatoTub -> InventoryItem -> Resource -> CoreClass
    ancestors = sv.class_ancestors("GelatoTub")
    assert "InventoryItem" in ancestors
    assert "Resource" in ancestors
    assert "CoreClass" in ancestors

    # Universal URI check on domain slot
    tub_slot = sv.all_slots()["tub_net_weight_kg"]
    assert tub_slot.slot_uri == "inv:quantity"

@pytest.mark.skipif(not (TEXTILE_SCHEMA.exists() and GELATO_SCHEMA.exists()), reason="Tenants not present in clean-slate mode")
def test_universal_semantic_bridge_across_tenants(loader):
    """Demonstrates that two completely different businesses (Textile vs Ice Cream)
    share the identical universal semantic anchor (inv:quantity) through LinkML slot_uri.
    """
    textile_sv = loader.load_schemaview(ROOT / "packages" / "@tenants" / "textile_corp" / "schema" / "domain.yaml")
    gelato_sv = loader.load_schemaview(ROOT / "packages" / "@tenants" / "sorella_gelato" / "schema" / "domain.yaml")

    # Collect slots anchored to inv:quantity
    textile_qty_slots = [
        s_name for s_name, s_def in textile_sv.all_slots().items()
        if s_def.slot_uri == "inv:quantity"
    ]
    gelato_qty_slots = [
        s_name for s_name, s_def in gelato_sv.all_slots().items()
        if s_def.slot_uri == "inv:quantity"
    ]

    assert "roll_length_meters" in textile_qty_slots
    assert "tub_net_weight_kg" in gelato_qty_slots
    # Both inherit nominal_quantity from @community/inventory
    assert "nominal_quantity" in textile_qty_slots
    assert "nominal_quantity" in gelato_qty_slots

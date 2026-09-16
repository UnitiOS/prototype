"""Test Studio Package Sealing and P2 Kernel Registration."""

import os
from pathlib import Path
import pytest
import yaml

from components.agent.studio_server import StudioTools

ROOT = Path(__file__).resolve().parent.parent.parent
INVENTORY_PKG = "packages/@community/inventory"
MANIFEST_PATH = ROOT / "packages" / "@community" / "inventory" / "uniti.package.yaml"
SCHEMA_PATH = ROOT / "packages" / "@community" / "inventory" / "schema" / "domain.yaml"

pytestmark = pytest.mark.skipif(not MANIFEST_PATH.exists(), reason="Community inventory not present in clean-slate mode")


def test_studio_linter_validation():
    """Verify that @community/inventory passes all linter checks."""
    tools = StudioTools()
    res = tools.validate_linter(INVENTORY_PKG)
    assert res["status"] == "PASS", f"Linter failed: {res.get('diagnostics')}"
    assert res["can_seal"] is True
    assert res["error_count"] == 0


def test_studio_seal_package():
    """Verify that sealing packages stamps annotations and updates uniti.package.yaml."""
    tools = StudioTools()
    res = tools.seal_package(INVENTORY_PKG, version="1.0.0", author="test_ontologist")
    
    assert res["sealed"] is True
    assert res["version"] == "1.0.0"
    assert "sha256" in res
    assert res["manifest"] == str(MANIFEST_PATH)
    
    # Verify manifest was updated
    manifest_doc = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest_doc["status"] == "SEALED"
    assert manifest_doc["version"] == "1.0.0"
    
    # Verify schema annotations were stamped
    schema_doc = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    ann = schema_doc.get("annotations") or {}
    assert "valid_from" in ann
    assert "sealed_at" in ann

    # Check kernel registration result (either succeeded or gave graceful warning if DB offline)
    if res["registered_in_kernel"]:
        assert len(res["minted_uris"]) >= 1
    else:
        assert res["kernel_warning"] is not None

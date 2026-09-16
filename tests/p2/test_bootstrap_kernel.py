"""Test Prototype 2 Kernel Bootstrap and Ontology Registration."""

import os
from pathlib import Path
import psycopg
import pytest

from components.seal.seal import _slot_ranges, _validate, _valid_from, register
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
ARCHETYPES_PATH = ROOT / "packages" / "@uniti" / "core" / "schema" / "archetypes.yaml"
BASE_TYPES_PATH = ROOT / "packages" / "@uniti" / "core" / "schema" / "base_types.yaml"


def test_core_archetypes_sealable():
    """Verify that archetypes.yaml is a valid, sealable LinkML schema with valid_from."""
    assert ARCHETYPES_PATH.is_file(), f"Missing {ARCHETYPES_PATH}"
    view = _validate(ARCHETYPES_PATH, ARCHETYPES_PATH.name)
    assert view.schema.version == "1.0.0"
    
    doc = yaml.safe_load(ARCHETYPES_PATH.read_text(encoding="utf-8"))
    valid_from = _valid_from(doc.get("annotations") or {}, ARCHETYPES_PATH.name)
    assert valid_from is not None
    
    ranges = _slot_ranges(view, ARCHETYPES_PATH.name)
    assert len(ranges) >= 19
    # Key metamodel slots must be present
    assert "uniti:entity_class" in ranges
    assert "uniti:agent_id" in ranges
    assert "uniti:resource_id" in ranges
    assert "uniti:commitment_id" in ranges
    assert "uniti:event_id" in ranges
    assert "uniti:projection_id" in ranges


def test_core_base_types_sealable():
    """Verify that base_types.yaml is a valid, sealable LinkML schema with valid_from."""
    assert BASE_TYPES_PATH.is_file(), f"Missing {BASE_TYPES_PATH}"
    view = _validate(BASE_TYPES_PATH, BASE_TYPES_PATH.name)
    assert view.schema.version == "1.0.0"
    
    doc = yaml.safe_load(BASE_TYPES_PATH.read_text(encoding="utf-8"))
    valid_from = _valid_from(doc.get("annotations") or {}, BASE_TYPES_PATH.name)
    assert valid_from is not None
    
    ranges = _slot_ranges(view, BASE_TYPES_PATH.name)
    assert len(ranges) >= 9
    assert "uniti:person_first_name" in ranges
    assert "uniti:org_legal_name" in ranges
    assert "uniti:location_code" in ranges


def test_bootstrap_kernel_function():
    """Verify bootstrap_kernel logic with a live database if reachable."""
    dsn = os.environ.get("UNITI_P2_KERNEL_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_p2")
    try:
        conn = psycopg.connect(dsn, connect_timeout=2)
        conn.close()
    except Exception:
        pytest.skip(f"Database at {dsn} is not reachable. Skipping live bootstrap test.")

    from scripts.bootstrap_p2_kernel import bootstrap_kernel
    result = bootstrap_kernel(dsn, actor_id="test_runner")
    assert result["status"] == "success"
    assert result["operational_facts"] == 0
    assert result["assertion_count"] >= 28

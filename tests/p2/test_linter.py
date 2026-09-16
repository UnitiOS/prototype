import tempfile
from pathlib import Path
import pytest

from components.linter.engine import LinterEngine
from components.linter.package_loader import PackageLoader

ROOT = Path(__file__).resolve().parent.parent.parent

@pytest.fixture
def linter():
    loader = PackageLoader(packages_dir=ROOT / "packages")
    return LinterEngine(loader=loader)

def test_linter_passes_on_uniti_core(linter):
    core_schema = ROOT / "packages" / "@uniti" / "core" / "schema" / "archetypes.yaml"
    diagnostics = linter.lint_schema(core_schema)
    errors = [d for d in diagnostics if d.severity == "ERROR"]
    assert len(errors) == 0

def test_linter_detects_missing_archetype(linter):
    schema_yaml = """id: https://w3id.org/test/bad_archetype
name: bad_archetype
prefixes:
  linkml: https://w3id.org/linkml/
  test: https://w3id.org/test/
imports:
  - linkml:types
classes:
  OrphanClass:
    description: A class that inherits from nothing and has no archetype.
    slots:
      - name
slots:
  name:
    range: string
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(schema_yaml)
        p = Path(f.name)
    try:
        diagnostics = linter.lint_schema(p)
        errs = [d for d in diagnostics if d.rule_id == "LINT-001"]
        assert len(errs) == 1
        assert "OrphanClass" in errs[0].message
    finally:
        p.unlink()

def test_linter_warns_unanchored_numeric_slot(linter):
    schema_yaml = """id: https://w3id.org/test/unanchored
name: unanchored
prefixes:
  linkml: https://w3id.org/linkml/
  test: https://w3id.org/test/
imports:
  - linkml:types
  - "@uniti/core"
classes:
  CustomWidget:
    is_a: Resource
    slots:
      - widget_weight
slots:
  widget_weight:
    range: decimal
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(schema_yaml)
        p = Path(f.name)
    try:
        diagnostics = linter.lint_schema(p)
        warns = [d for d in diagnostics if d.rule_id == "LINT-002"]
        assert len(warns) == 1
        assert "widget_weight" in warns[0].message
    finally:
        p.unlink()

def test_linter_detects_broken_lifecycle(linter):
    schema_yaml = """id: https://w3id.org/test/bad_lifecycle
name: bad_lifecycle
prefixes:
  linkml: https://w3id.org/linkml/
  test: https://w3id.org/test/
imports:
  - linkml:types
  - "@uniti/core"
classes:
  PurchaseOrder:
    is_a: Commitment
    annotations:
      lifecycle:
        value:
          states:
            DRAFT: {}
            APPROVED: {}
          initial: NON_EXISTENT_STATE
          transitions:
            - from: DRAFT
              to: GHOST_STATE
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(schema_yaml)
        p = Path(f.name)
    try:
        diagnostics = linter.lint_schema(p)
        errs = [d for d in diagnostics if d.rule_id == "LINT-003"]
        assert len(errs) >= 1
    finally:
        p.unlink()

def test_linter_detects_projection_slot_mismatch(linter):
    schema_yaml = """id: https://w3id.org/test/bad_projection
name: bad_projection
prefixes:
  linkml: https://w3id.org/linkml/
  test: https://w3id.org/test/
imports:
  - linkml:types
  - "@uniti/core"
classes:
  MonthlySummary:
    is_a: Projection
    slots:
      - total_gain
slots:
  total_gain:
    range: decimal
    equals_expression: "{revenue} - {cost}"
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(schema_yaml)
        p = Path(f.name)
    try:
        diagnostics = linter.lint_schema(p)
        errs = [d for d in diagnostics if d.rule_id == "LINT-005"]
        assert len(errs) >= 1
    finally:
        p.unlink()

def test_linter_cli_execution():
    import subprocess
    import json
    import sys

    # Test clean run on @uniti/core
    cmd = [sys.executable, str(ROOT / "components" / "linter" / "cli.py"), str(ROOT / "packages" / "@uniti" / "core"), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "PASS"
    assert data["error_count"] == 0

def test_linter_detects_unsafe_invariant_call(linter):
    schema_yaml = """id: https://w3id.org/test/unsafe_invariant
name: unsafe_invariant
prefixes:
  linkml: https://w3id.org/linkml/
  test: https://w3id.org/test/
imports:
  - linkml:types
  - "@uniti/core"
classes:
  MaliciousEvent:
    is_a: Event
    annotations:
      invariants:
        value:
          - id: rce_attempt
            expression: "__import__('os').system('echo hacked')"
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(schema_yaml)
        p = Path(f.name)
    try:
        diagnostics = linter.lint_schema(p)
        errs = [d for d in diagnostics if d.rule_id == "LINT-004"]
        assert len(errs) >= 1
        assert "failed safety validation" in errs[0].message
    finally:
        p.unlink()


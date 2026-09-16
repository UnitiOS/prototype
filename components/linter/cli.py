import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from components.linter.engine import LinterEngine
from components.linter.package_loader import PackageLoader

def main():
    parser = argparse.ArgumentParser(description="UnitiOS Deterministic Semantic Linter")
    parser.add_argument("target", help="Path to schema YAML file or package directory")
    parser.add_argument("--json", action="store_true", help="Output diagnostics in JSON format")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    loader = PackageLoader()

    # Determine schema file
    if target_path.is_dir():
        candidates = [
            target_path / "schema" / "archetypes.yaml",
            target_path / "schema" / "domain.yaml",
            target_path / "schema" / "base_types.yaml",
            target_path / "schema.yaml",
        ]
        schema_file = None
        for c in candidates:
            if c.exists():
                schema_file = c
                break
        if not schema_file:
            print(f"Error: No schema YAML file found in package {target_path}", file=sys.stderr)
            sys.exit(1)
    else:
        schema_file = target_path

    engine = LinterEngine(loader=loader)
    diagnostics = engine.lint_schema(schema_file)

    errors = [d for d in diagnostics if d.severity == "ERROR"]
    warnings = [d for d in diagnostics if d.severity == "WARNING"]

    if args.json:
        result = {
            "target": str(schema_file),
            "status": "FAIL" if errors else "PASS",
            "error_count": len(errors),
            "warning_count": len(warnings),
            "diagnostics": [d.to_dict() for d in diagnostics],
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"\n========================================================")
        print(f" UNITIOS SEMANTIC LINTER AUDIT: {schema_file.name}")
        print(f"========================================================")
        if not diagnostics:
            print(" [PASS] 100% Compliant! All 5 archetypes and invariants sound.\n")
            sys.exit(0)

        for d in diagnostics:
            icon = "[ERROR]" if d.severity == "ERROR" else "[WARN] "
            print(f" {icon} {d.rule_id} on {d.target}: {d.message}")

        print(f"\nSummary: {len(errors)} error(s), {len(warnings)} warning(s).")
        if errors:
            print("Status: FAILED (Cannot seal package until errors are resolved).\n")
            sys.exit(1)
        else:
            print("Status: PASSED WITH WARNINGS (Package eligible to seal).\n")
            sys.exit(0)

if __name__ == "__main__":
    main()

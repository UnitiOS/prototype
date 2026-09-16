import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from linkml_runtime.utils.schemaview import SchemaView, load_schema_wrap
from linkml_runtime.linkml_model.meta import SchemaDefinition

ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGES_DIR = ROOT / "packages"

class UnitiSchemaView(SchemaView):
    """SchemaView subclass with native multi-package resolution for UnitiOS."""
    def __init__(self, schema, package_dirs=None, importmap=None, **kwargs):
        self.package_dirs: Dict[str, Path] = package_dirs or {}
        super().__init__(schema, importmap=importmap, **kwargs)

    def load_import(self, imp: str, from_schema: SchemaDefinition | None = None) -> SchemaDefinition:
        for pkg_name, default_path in self.package_dirs.items():
            if imp.endswith(pkg_name):
                return load_schema_wrap(str(default_path))
            if pkg_name in imp:
                sub = imp[imp.index(pkg_name) + len(pkg_name):].lstrip("/\\")
                if not sub:
                    return load_schema_wrap(str(default_path))
                sub_clean = sub if not sub.endswith(".yaml") else sub[:-5]
                sub_path = default_path.parent / f"{sub_clean}.yaml"
                if sub_path.exists():
                    return load_schema_wrap(str(sub_path))

        return super().load_import(imp, from_schema)

class PackageLoader:
    """Discovers packages in packages/ and provides UnitiSchemaView loader."""
    def __init__(self, packages_dir: Optional[Path] = None):
        self.packages_dir = packages_dir or PACKAGES_DIR
        self._package_paths: Dict[str, Path] = {}
        self._index_packages()

    def _index_packages(self):
        """Scans packages directory and registers package root schemas."""
        if not self.packages_dir.exists():
            return
        for manifest in self.packages_dir.glob("**/uniti.package.yaml"):
            try:
                data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
                pkg_name = data.get("name")
                if not pkg_name:
                    continue
                pkg_dir = manifest.parent
                schema_dir = pkg_dir / "schema"

                default_schema = None
                if (schema_dir / "archetypes.yaml").exists():
                    default_schema = schema_dir / "archetypes.yaml"
                elif (schema_dir / "domain.yaml").exists():
                    default_schema = schema_dir / "domain.yaml"
                elif (pkg_dir / "schema.yaml").exists():
                    default_schema = pkg_dir / "schema.yaml"

                if default_schema:
                    self._package_paths[pkg_name] = default_schema.resolve()

            except Exception:
                continue

    def get_package_paths(self) -> Dict[str, Path]:
        return dict(self._package_paths)

    def load_schemaview(self, schema_source) -> SchemaView:
        source_str = str(schema_source) if isinstance(schema_source, Path) else schema_source
        return UnitiSchemaView(source_str, package_dirs=self._package_paths)

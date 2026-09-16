"""components.agent.studio_server ? Model Context Protocol (MCP) server for Uniti Studio.

Provides a standard JSON-RPC 2.0 stdio server conforming to the MCP specification (2024-11-05).
Specialized for Design-Time Ontology Engineering, Socratic Modeling, and Semantic Linter Gates.

Run:
    .venv/Scripts/python.exe components/agent/studio_server.py
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from components.studio.catalog import SemanticCatalog
from components.studio.patcher import SchemaPatcher
from components.linter.engine import LinterEngine
from components.linter.package_loader import PackageLoader

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(asctime)s] [studio-mcp] %(levelname)s: %(message)s",
)
logger = logging.getLogger("studio-mcp")

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "uniti-studio-mcp",
    "version": "2.0.0",
}

TOOL_DEFINITIONS = [
    {
        "name": "studio_init_package",
        "description": "Initialize a new draft package with an official uniti.package.yaml manifest and schema skeleton.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_path": {"type": "string", "description": "Package directory relative to root, e.g. 'packages/@community/inventory'."},
                "title": {"type": "string", "description": "Human-readable package title."},
                "domain": {"type": "string", "description": "Domain vocabulary prefix, e.g. 'inventory' or 'procurement'."},
                "author": {"type": "string", "description": "Author identity, defaults to 'ontologist'."},
            },
            "required": ["package_path", "title"],
        },
    },
    {
        "name": "studio_search_catalog",
        "description": "Search for universal standardized URIs (e.g. inv:quantity, fin:amount, proc:po_number).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword to search for in catalog."},
                "domain": {"type": "string", "description": "Optional domain filter (inventory, finance, procurement)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "studio_inspect_package",
        "description": "Inspect classes, archetypes, and slots defined in a package draft.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_path": {"type": "string", "description": "Path to the package directory (e.g. packages/@community/inventory)."},
            },
            "required": ["package_path"],
        },
    },
    {
        "name": "studio_propose_patch",
        "description": "Apply a structured class, slot, invariant, or lifecycle patch to a draft schema.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_path": {"type": "string", "description": "Path to the package directory."},
                "class_name": {"type": "string", "description": "Name of class to add/update."},
                "archetype": {"type": "string", "description": "Base archetype: Agent, Resource, Commitment, Event, or Projection."},
                "description": {"type": "string", "description": "Human explanation of the business concept."},
                "slots": {"type": "array", "items": {"type": "string"}, "description": "List of slot names on this class."},
                "slot_definitions": {"type": "object", "description": "Mapping from slot_name to {range, slot_uri, description}."},
                "invariant": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "expression": {"type": "string"},
                        "message": {"type": "string"},
                    },
                },
                "lifecycle": {
                    "type": "object",
                    "properties": {
                        "initial": {"type": "string"},
                        "states": {"type": "object"},
                        "transitions": {"type": "array"},
                    },
                },
            },
            "required": ["package_path", "class_name", "archetype"],
        },
    },
    {
        "name": "studio_validate_linter",
        "description": "Run the deterministic semantic linter on a draft schema and get error diagnostics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_path": {"type": "string", "description": "Path to the package directory."},
            },
            "required": ["package_path"],
        },
    },
    {
        "name": "studio_render_graph",
        "description": "Generate graph nodes and edges with archetype color codes for visual canvas display.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_path": {"type": "string", "description": "Path to the package directory."},
            },
            "required": ["package_path"],
        },
    },
    {
        "name": "studio_seal_package",
        "description": "Seal an eligible draft package into an immutable release version if linter passes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_path": {"type": "string", "description": "Path to package directory."},
                "version": {"type": "string", "description": "Release version string, e.g. '1.0.0'."},
                "author": {"type": "string", "description": "Identity of signer/ontologist."},
            },
            "required": ["package_path", "version"],
        },
    },
]

ARCHETYPE_COLORS = {
    "Agent": "#8B5CF6",       # Purple
    "Resource": "#3B82F6",    # Blue
    "Commitment": "#F59E0B",  # Amber/Yellow
    "Event": "#10B981",       # Emerald Green
    "Projection": "#06B6D4",  # Cyan
    "CoreClass": "#64748B",   # Slate Gray
}

class PackagePathError(ValueError):
    """The package path leads somewhere this gate does not write."""


class StudioTools:
    """The authoring write gate.

    Every path it writes to is resolved under one root and checked to still be
    under it afterwards. The paths come from an agent's tool call, so they are
    model output shaped by whatever was typed into a chat box: a gate that
    followed them wherever they pointed would not be a gate.
    """

    def __init__(self, packages_root=None):
        self.catalog = SemanticCatalog()
        self.loader = PackageLoader()
        self.linter = LinterEngine(loader=self.loader)
        self._packages_root = packages_root

    @property
    def packages_root(self) -> Path:
        """Where packages are written. Configuration, read when it is used.

        Read on use rather than captured at construction, so that setting
        UNITI_PACKAGES_ROOT takes effect for a gate that already exists.
        """
        return Path(
            self._packages_root
            or os.environ.get("UNITI_PACKAGES_ROOT")
            or (ROOT / "packages")
        ).resolve()

    def _normalize_pkg_dir(self, pkg_path_str: str) -> Path:
        """Where a package path lands, refusing anything outside the root.

        A bare name is a package, not a directory at the top of the repository:
        'inventory' means packages/inventory. A leading 'packages/' is accepted
        and dropped, so both spellings of the same place agree.
        """
        raw = str(pkg_path_str or "").replace("\\", "/").strip()
        if not raw:
            raise PackagePathError("no package path given")

        norm = raw.strip("/")
        candidate = Path(raw)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            if norm.startswith("packages/"):
                norm = norm[len("packages/"):]
            resolved = (self.packages_root / norm).resolve()

        root = self.packages_root
        if resolved != root and root not in resolved.parents:
            raise PackagePathError(
                f"package path {pkg_path_str!r} resolves to {resolved}, which is "
                f"outside {root}. Packages are written under that directory and "
                f"nowhere else."
            )
        return resolved

    def _resolve_schema_file(self, pkg_path_str: str) -> Path:
        p = self._normalize_pkg_dir(pkg_path_str)
        if p.is_dir():
            candidates = [
                p / "schema" / "domain.yaml",
                p / "schema" / "archetypes.yaml",
                p / "draft.yaml",
                p / "schema.yaml",
            ]
            for c in candidates:
                if c.exists():
                    return c
            return p / "schema" / "domain.yaml"
        return p

    def search_catalog(self, query: str, domain: Optional[str] = None) -> List[Dict]:
        return self.catalog.search(query, domain=domain, limit=10)

    def inspect_package(self, package_path: str) -> Dict[str, Any]:
        schema_file = self._resolve_schema_file(package_path)
        if not schema_file.exists():
            return {"exists": False, "schema_file": str(schema_file)}
        try:
            sv = self.loader.load_schemaview(schema_file)
            classes_info = {}
            for name, c_def in sv.all_classes().items():
                try:
                    ancestors = sv.class_ancestors(name)
                except Exception:
                    ancestors = []
                archetype = next((a for a in ancestors if a in ARCHETYPE_COLORS), "Unknown")
                classes_info[name] = {
                    "is_a": c_def.is_a,
                    "archetype": archetype,
                    "description": c_def.description or "",
                    "slots": list(c_def.slots),
                }
            return {
                "exists": True,
                "schema_file": str(schema_file),
                "classes": classes_info,
                "slot_count": len(sv.all_slots()),
            }
        except Exception as e:
            return {"error": str(e), "schema_file": str(schema_file)}

    def init_package(self, package_path: str, title: str, domain: Optional[str] = None, author: str = "ontologist") -> Dict[str, Any]:
        p = self._normalize_pkg_dir(package_path)
        try:
            rel_pkg = str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            rel_pkg = str(p).replace("\\", "/")
        manifest_path = p / "uniti.package.yaml"
        if manifest_path.exists():
            try:
                existing = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                if existing.get("status") == "SEALED":
                    return {
                        "status": "REJECTED",
                        "error": f"Write Gate Rejection: Package at '{package_path}' is SEALED (immutable). Create a new package or draft version.",
                    }
            except Exception:
                pass

        p.mkdir(parents=True, exist_ok=True)
        schema_dir = p / "schema"
        schema_dir.mkdir(parents=True, exist_ok=True)
        schema_file = schema_dir / "domain.yaml"

        pkg_name = p.name
        if p.parent.name.startswith("@"):
            pkg_name = f"{p.parent.name}/{p.name}"

        clean_dom = (domain or p.name).lower().replace("@", "").replace("/", "_")

        manifest_data = {
            "name": pkg_name,
            "title": title,
            "version": "0.1.0-draft",
            "status": "DRAFT",
            "domain": clean_dom,
            "author": author,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dependencies": ["@uniti/core"],
        }
        manifest_path.write_text(yaml.safe_dump(manifest_data, sort_keys=False), encoding="utf-8")

        if not schema_file.exists():
            skeleton = {
                "id": f"https://w3id.org/uniti/{clean_dom}",
                "name": f"uniti_{clean_dom}",
                "title": title,
                "prefixes": {
                    "linkml": "https://w3id.org/linkml/",
                    "uniti": "https://w3id.org/uniti/core#",
                    clean_dom: f"https://w3id.org/uniti/vocab/{clean_dom}#",
                },
                "imports": [
                    "linkml:types",
                    "@uniti/core",
                ],
                "default_prefix": "uniti",
                "default_range": "string",
                "classes": {},
                "slots": {},
            }
            schema_file.write_text(yaml.safe_dump(skeleton, sort_keys=False, allow_unicode=True), encoding="utf-8")

        return {
            "status": "INITIALIZED",
            "package_path": rel_pkg,
            "manifest": str(manifest_path),
            "schema_file": str(schema_file),
            "manifest_data": manifest_data,
        }

    def propose_patch(self, package_path: str, class_name: str, archetype: str,
                      description: str, slots: Optional[List[str]] = None,
                      slot_definitions: Optional[Dict[str, Any]] = None,
                      invariant: Optional[Dict[str, Any]] = None,
                      lifecycle: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        schema_file = self._resolve_schema_file(package_path)

        # Write Gate Check 1: Immutability enforcement
        pkg_dir = schema_file.parent.parent if schema_file.parent.name == "schema" else schema_file.parent
        manifest_path = pkg_dir / "uniti.package.yaml"
        if manifest_path.exists():
            try:
                manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                if manifest_data.get("status") == "SEALED":
                    return {
                        "status": "REJECTED",
                        "can_patch": False,
                        "error": f"Write Gate Rejection: Package '{manifest_data.get('name', package_path)}' is SEALED (immutable). Create a new draft package or bump version.",
                        "schema_file": str(schema_file),
                        "linter_status": "BLOCKED",
                        "diagnostics": [],
                    }
            except Exception:
                pass

        patcher = SchemaPatcher(schema_file)

        patcher.add_class(
            name=class_name,
            is_a=archetype,
            description=description,
            slots=slots,
        )

        # Write Gate Check 2: Auto-anchor semantic catalog URIs for slots if missing
        if slots:
            if slot_definitions is None:
                slot_definitions = {}
            for s_name in slots:
                if s_name not in slot_definitions:
                    cat_matches = self.catalog.search(s_name, limit=1)
                    if cat_matches:
                        slot_definitions[s_name] = {
                            "slot_uri": cat_matches[0]["curie"],
                            "range": cat_matches[0].get("range", "string"),
                            "description": cat_matches[0].get("description", ""),
                        }
                elif not slot_definitions[s_name].get("slot_uri"):
                    cat_matches = self.catalog.search(s_name, limit=1)
                    if cat_matches:
                        slot_definitions[s_name]["slot_uri"] = cat_matches[0]["curie"]

        if slot_definitions:
            for s_name, s_meta in slot_definitions.items():
                patcher.add_slot(
                    name=s_name,
                    slot_uri=s_meta.get("slot_uri"),
                    range=s_meta.get("range", "string"),
                    description=s_meta.get("description", ""),
                    identifier=s_meta.get("identifier", False),
                )

        if invariant:
            patcher.add_invariant(
                class_name=class_name,
                inv_id=invariant.get("id", "inv_rule"),
                expression=invariant.get("expression", ""),
                message=invariant.get("message", ""),
            )

        if lifecycle:
            patcher.set_lifecycle(
                class_name=class_name,
                initial=lifecycle.get("initial", "DRAFT"),
                states=lifecycle.get("states", {}),
                transitions=lifecycle.get("transitions", []),
            )

        patcher.save()
        # Run linter immediately on patch
        diagnostics = self.linter.lint_schema(schema_file)
        return {
            "status": "PATCHED",
            "schema_file": str(schema_file),
            "linter_status": "PASS" if not [d for d in diagnostics if d.severity == "ERROR"] else "FAIL",
            "diagnostics": [d.to_dict() for d in diagnostics],
        }

    def validate_linter(self, package_path: str) -> Dict[str, Any]:
        schema_file = self._resolve_schema_file(package_path)
        diagnostics = self.linter.lint_schema(schema_file)
        errors = [d for d in diagnostics if d.severity == "ERROR"]
        warnings = [d for d in diagnostics if d.severity == "WARNING"]
        return {
            "schema_file": str(schema_file),
            "status": "PASS" if not errors else "FAIL",
            "can_seal": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "diagnostics": [d.to_dict() for d in diagnostics],
        }

    def render_graph(self, package_path: str) -> Dict[str, Any]:
        schema_file = self._resolve_schema_file(package_path)
        if not schema_file.exists():
            return {"nodes": [], "edges": []}
        try:
            sv = self.loader.load_schemaview(schema_file)
            nodes = []
            edges = []
            for c_name, c_def in sv.all_classes().items():
                try:
                    ancestors = sv.class_ancestors(c_name)
                except Exception:
                    ancestors = []
                archetype = next((a for a in ancestors if a in ARCHETYPE_COLORS), "CoreClass")
                color = ARCHETYPE_COLORS.get(archetype, "#94A3B8")
                nodes.append({
                    "id": c_name,
                    "label": c_name,
                    "archetype": archetype,
                    "color": color,
                    "description": c_def.description or "",
                    "slots": list(c_def.slots),
                })
                if c_def.is_a:
                    edges.append({
                        "source": c_name,
                        "target": c_def.is_a,
                        "label": "is_a",
                        "type": "inheritance",
                    })
                # Check slot ranges for relationships
                for s_name in c_def.slots:
                    s_def = sv.all_slots().get(s_name)
                    if s_def and s_def.range in sv.all_classes():
                        edges.append({
                            "source": c_name,
                            "target": s_def.range,
                            "label": s_name,
                            "type": "association",
                        })
            return {"nodes": nodes, "edges": edges}
        except Exception as e:
            return {"error": str(e), "nodes": [], "edges": []}

    def seal_package(self, package_path: str, version: str, author: str = "ontologist", dsn: Optional[str] = None) -> Dict[str, Any]:
        import os
        schema_file = self._resolve_schema_file(package_path)
        l_res = self.validate_linter(package_path)
        if not l_res["can_seal"]:
            return {
                "sealed": False,
                "error": "Cannot seal package: linter errors must be resolved first.",
                "diagnostics": l_res["diagnostics"],
            }

        # 1. Ensure LinkML annotations.valid_from and sealed_at are stamped
        try:
            schema_text = schema_file.read_text(encoding="utf-8")
            schema_doc = yaml.safe_load(schema_text) or {}
            ann = schema_doc.get("annotations") or {}
            now_iso = datetime.now(timezone.utc).isoformat()
            if not ann.get("valid_from"):
                ann["valid_from"] = now_iso
            ann["sealed_at"] = now_iso
            schema_doc["annotations"] = ann
            schema_doc["version"] = version
            schema_file.write_text(
                yaml.safe_dump(schema_doc, sort_keys=False, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Could not stamp annotations in {schema_file}: {e}")

        content = schema_file.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        pkg_dir = schema_file.parent.parent if schema_file.parent.name == "schema" else schema_file.parent
        manifest_path = pkg_dir / "uniti.package.yaml"

        existing = {}
        if manifest_path.exists():
            try:
                existing = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            except Exception:
                pass

        default_name = existing.get("name")
        if not default_name:
            if pkg_dir.parent.name.startswith("@"):
                default_name = f"{pkg_dir.parent.name}/{pkg_dir.name}"
            else:
                default_name = pkg_dir.name

        manifest_data = dict(existing)
        manifest_data.update({
            "name": default_name,
            "version": version,
            "sealed_at": datetime.now(timezone.utc).isoformat(),
            "author": author,
            "sha256": digest,
            "status": "SEALED",
        })

        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.dump(manifest_data, f, sort_keys=False)

        # 2. Register sealed vocabulary into Prototype 2 Kernel (uniti_p2)
        p2_dsn = dsn or os.environ.get(
            "UNITI_P2_KERNEL_DSN",
            os.environ.get("UNITI_KERNEL_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_p2"),
        )
        registered_in_kernel = False
        minted_uris = []
        kernel_warning = None
        # A refusal is the kernel judging the schema; an unreachable database is
        # not. Only the first one means the package is not sealed.
        kernel_refused = False

        try:
            import psycopg
            from components.seal.seal import register
            with psycopg.connect(p2_dsn, connect_timeout=3) as conn:
                reg_res = register(conn, schema_file, actor_id=author)
                registered_in_kernel = True
                minted_raw = reg_res.get("minted", {})
                minted_uris = list(minted_raw.keys()) if isinstance(minted_raw, dict) else [str(x) for x in minted_raw]
                logger.info(f"Registered {len(minted_uris)} URIs from {schema_file.name} into P2 kernel ({p2_dsn})")
        except psycopg.OperationalError as exc:
            kernel_warning = f"PostgreSQL at {p2_dsn} unreachable ({exc}). Package sealed locally."
            logger.warning(kernel_warning)
        except Exception as exc:
            kernel_warning = f"Kernel registration error: {exc}"
            kernel_refused = True
            logger.error(kernel_warning)

        # A package is sealed when the kernel holds its vocabulary, not when a
        # file on disk says so. Reporting success on a refused registration
        # leaves the manifest claiming SEALED while the kernel knows nothing —
        # two answers to one question, which is the state this system exists to
        # make impossible. The refusal is reported, and the manifest is put
        # back the way it was.
        if not registered_in_kernel and kernel_refused:
            manifest_data["status"] = existing.get("status", "DRAFT")
            manifest_data.pop("sha256", None)
            manifest_data.pop("sealed_at", None)
            with open(manifest_path, "w", encoding="utf-8") as f:
                yaml.dump(manifest_data, f, sort_keys=False)
            return {
                "sealed": False,
                "error": f"Kernel refused the vocabulary: {kernel_warning}",
                "registered_in_kernel": False,
                "kernel_dsn": p2_dsn,
            }

        return {
            "sealed": True,
            "version": version,
            "sha256": digest,
            "manifest": str(manifest_path),
            "registered_in_kernel": registered_in_kernel,
            "minted_uris": minted_uris,
            "kernel_warning": kernel_warning,
            "kernel_dsn": p2_dsn,
        }

class StudioMCPServer:
    def __init__(self):
        self.tools = StudioTools()

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        method = req.get("method")
        msg_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO,
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOL_DEFINITIONS},
            }

        if method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            args = params.get("arguments", {})

            try:
                if tool_name == "studio_init_package":
                    out = self.tools.init_package(
                        package_path=args["package_path"],
                        title=args["title"],
                        domain=args.get("domain"),
                        author=args.get("author", "ontologist"),
                    )
                elif tool_name == "studio_search_catalog":
                    out = self.tools.search_catalog(args["query"], args.get("domain"))
                elif tool_name == "studio_inspect_package":
                    out = self.tools.inspect_package(args["package_path"])
                elif tool_name == "studio_propose_patch":
                    out = self.tools.propose_patch(
                        package_path=args["package_path"],
                        class_name=args["class_name"],
                        archetype=args["archetype"],
                        description=args["description"],
                        slots=args.get("slots"),
                        slot_definitions=args.get("slot_definitions"),
                        invariant=args.get("invariant"),
                        lifecycle=args.get("lifecycle"),
                    )
                elif tool_name == "studio_validate_linter":
                    out = self.tools.validate_linter(args["package_path"])
                elif tool_name == "studio_render_graph":
                    out = self.tools.render_graph(args["package_path"])
                elif tool_name == "studio_seal_package":
                    out = self.tools.seal_package(
                        package_path=args["package_path"],
                        version=args["version"],
                        author=args.get("author", "ontologist"),
                    )
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {"code": -32601, "message": f"Method not found: {tool_name}"},
                    }

                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]},
                }
            except Exception as e:
                logger.exception("Error executing tool %s", tool_name)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "isError": True,
                    "error": {"code": -32000, "message": str(e)},
                }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }

    def run(self):
        logger.info("Uniti Studio MCP Server started on stdio.")
        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                req = json.loads(line_str)
                res = self.handle_request(req)
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
            except Exception as e:
                logger.error("JSON parse error: %s", str(e))

if __name__ == "__main__":
    server = StudioMCPServer()
    server.run()

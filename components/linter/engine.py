import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from linkml_runtime.utils.schemaview import SchemaView
from jsonasobj2 import as_dict
from .package_loader import PackageLoader

CORE_ARCHETYPES = {"Agent", "Resource", "Commitment", "Event", "Projection"}

def normalize_meta(obj: Any) -> Any:
    """Unwraps LinkML Annotation and JsonObj into standard Python primitives."""
    if obj is None:
        return None
    if hasattr(obj, "value"):
        obj = obj.value
    try:
        d = as_dict(obj)
        if isinstance(d, dict):
            return {k: normalize_meta(v) for k, v in d.items()}
        if isinstance(d, list):
            return [normalize_meta(item) for item in d]
        return d
    except Exception:
        return obj

@dataclass
class Diagnostic:
    rule_id: str
    severity: str  # "ERROR" | "WARNING"
    target: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "target": self.target,
            "message": self.message,
        }

class SafeASTValidator(ast.NodeVisitor):
    ALLOWED_NODES = (
        ast.Expression, ast.Compare, ast.BoolOp, ast.BinOp, ast.UnaryOp,
        ast.Constant, ast.Name, ast.Attribute, ast.Load,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.Is, ast.IsNot, ast.In, ast.NotIn,
        ast.And, ast.Or, ast.Not,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    )
    ALLOWED_ROOT_NAMES = {"self", "actor"}

    def __init__(self):
        self.errors = []

    def generic_visit(self, node):
        if not isinstance(node, self.ALLOWED_NODES):
            self.errors.append(f"Disallowed expression element: {type(node).__name__}")
        super().generic_visit(node)

    def visit_Attribute(self, node):
        curr = node
        while isinstance(curr, ast.Attribute):
            curr = curr.value
        if isinstance(curr, ast.Name):
            if curr.id not in self.ALLOWED_ROOT_NAMES:
                self.errors.append(f"Attribute access only permitted on 'self' or 'actor', found: '{curr.id}'")
        super().generic_visit(node)

class LinterEngine:
    """Deterministic Semantic Linter enforcing UnitiOS specifications."""

    def __init__(self, loader: Optional[PackageLoader] = None):
        self.loader = loader or PackageLoader()

    def _safe_class_ancestors(self, sv: SchemaView, class_name: str) -> Set[str]:
        try:
            return set(sv.class_ancestors(class_name))
        except Exception:
            return set()

    def lint_schema(self, schema_path: Path) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        # SchemaView resolves imports lazily, on first traversal rather than at
        # construction. Reading the classes and the slots inside this guard is
        # what lets LINT-000 report an unresolvable import as a diagnostic;
        # outside it, the commonest failure of all escapes as a traceback.
        try:
            sv = self.loader.load_schemaview(schema_path)
            all_classes = sv.all_classes()
            all_slots = sv.all_slots()
        except Exception as e:
            return [Diagnostic(
                rule_id="LINT-000",
                severity="ERROR",
                target=str(schema_path),
                message=f"Schema parsing error: {type(e).__name__}: {str(e)}"
            )]

        # -------------------------------------------------------------
        # Rule LINT-001: Archetype Check
        # -------------------------------------------------------------
        for class_name, class_def in all_classes.items():
            if class_name in CORE_ARCHETYPES or class_name == "CoreClass":
                continue
            try:
                ancestors = set(sv.class_ancestors(class_name))
            except Exception as e:
                diagnostics.append(Diagnostic(
                    rule_id="LINT-001",
                    severity="ERROR",
                    target=class_name,
                    message=f"Class '{class_name}' specifies invalid parent: {str(e)}"
                ))
                continue
            has_archetype = bool(ancestors.intersection(CORE_ARCHETYPES))
            if not has_archetype:
                diagnostics.append(Diagnostic(
                    rule_id="LINT-001",
                    severity="ERROR",
                    target=class_name,
                    message=f"Class '{class_name}' must inherit from one of the 5 foundational archetypes (Agent, Resource, Commitment, Event, Projection)."
                ))

        # -------------------------------------------------------------
        # Rule LINT-002: Standardized URI Anchoring
        # -------------------------------------------------------------
        # A slot's URI is its identity in the kernel: facts are recorded against
        # the URI, never the slot's name. `seal` refuses a slot without one, so
        # anything softer than an error here lets a package pass the linter and
        # then fail at the kernel — with the manifest already stamped SEALED.
        # The linter and the kernel have to want the same thing.
        local_slots = getattr(sv.schema, "slots", {}) or {}
        for slot_name in local_slots:
            slot_def = all_slots.get(slot_name)
            if slot_def is not None and not slot_def.slot_uri:
                diagnostics.append(Diagnostic(
                    rule_id="LINT-002",
                    severity="ERROR",
                    target=slot_name,
                    message=(f"Slot '{slot_name}' has no slot_uri, so it has no identity "
                             f"in the kernel. Anchor it to a standard URI from the "
                             f"catalog, or mint one under this schema's own prefix.")
                ))

        # -------------------------------------------------------------
        # Rule LINT-003: State Machine Soundness (Commitments)
        # -------------------------------------------------------------
        for class_name, class_def in all_classes.items():
            ancestors = self._safe_class_ancestors(sv, class_name)
            if "Commitment" in ancestors and class_name not in CORE_ARCHETYPES:
                annotations = class_def.annotations or {}
                lifecycle = annotations.get("lifecycle")
                if lifecycle:
                    val = normalize_meta(lifecycle)
                    if isinstance(val, dict):
                        states = val.get("states", {})
                        initial = val.get("initial")
                        if not initial:
                            diagnostics.append(Diagnostic(
                                rule_id="LINT-003",
                                severity="ERROR",
                                target=class_name,
                                message=f"Commitment '{class_name}' lifecycle is missing an 'initial' state declaration."
                            ))
                        elif initial not in states:
                            diagnostics.append(Diagnostic(
                                rule_id="LINT-003",
                                severity="ERROR",
                                target=class_name,
                                message=f"Initial state '{initial}' on '{class_name}' is not declared in 'states'."
                            ))

                        transitions = val.get("transitions", [])
                        from_states = set()
                        for t in transitions:
                            if isinstance(t, dict):
                                f_state = t.get("from")
                                t_state = t.get("to")
                                from_states.add(f_state)
                                if f_state and f_state not in states:
                                    diagnostics.append(Diagnostic(
                                        rule_id="LINT-003",
                                        severity="ERROR",
                                        target=class_name,
                                        message=f"Transition 'from: {f_state}' on '{class_name}' is not declared in 'states'."
                                    ))
                                if t_state and t_state not in states:
                                    diagnostics.append(Diagnostic(
                                        rule_id="LINT-003",
                                        severity="ERROR",
                                        target=class_name,
                                        message=f"Transition 'to: {t_state}' on '{class_name}' is not declared in 'states'."
                                    ))

                        known_terminal = {"CLOSED", "CANCELLED", "FULFILLED", "REJECTED", "COMPLETED"}
                        for s_name, s_meta in states.items():
                            is_marked_term = False
                            if isinstance(s_meta, dict):
                                is_marked_term = s_meta.get("terminal", False)
                            if s_name not in known_terminal and not is_marked_term and s_name not in from_states:
                                diagnostics.append(Diagnostic(
                                    rule_id="LINT-003",
                                    severity="WARNING",
                                    target=class_name,
                                    message=f"State '{s_name}' on '{class_name}' has no outbound transitions (possible deadlock)."
                                ))

        # -------------------------------------------------------------
        # Rule LINT-004: Safe AST Invariant Evaluator
        # -------------------------------------------------------------
        for class_name, class_def in all_classes.items():
            annotations = class_def.annotations or {}
            invariants = annotations.get("invariants")
            if invariants:
                inv_list = normalize_meta(invariants)
                if isinstance(inv_list, list):
                    for inv in inv_list:
                        if isinstance(inv, dict):
                            inv_id = inv.get("id", "unnamed")
                            expr = inv.get("expression", "")
                            if not expr:
                                diagnostics.append(Diagnostic(
                                    rule_id="LINT-004",
                                    severity="ERROR",
                                    target=class_name,
                                    message=f"Invariant '{inv_id}' on '{class_name}' is missing an 'expression'."
                                ))
                                continue
                            try:
                                tree = ast.parse(expr, mode="eval")
                                validator = SafeASTValidator()
                                validator.visit(tree)
                                for err in validator.errors:
                                    diagnostics.append(Diagnostic(
                                        rule_id="LINT-004",
                                        severity="ERROR",
                                        target=class_name,
                                        message=f"Invariant '{inv_id}' on '{class_name}' failed safety validation: {err}"
                                    ))
                            except SyntaxError as se:
                                diagnostics.append(Diagnostic(
                                    rule_id="LINT-004",
                                    severity="ERROR",
                                    target=class_name,
                                    message=f"Invariant '{inv_id}' on '{class_name}' syntax error: {str(se)}"
                                ))

        # -------------------------------------------------------------
        # Rule LINT-005: Projection Integrity
        # -------------------------------------------------------------
        for class_name, class_def in all_classes.items():
            ancestors = self._safe_class_ancestors(sv, class_name)
            if "Projection" in ancestors and class_name not in CORE_ARCHETYPES:
                for slot_name in class_def.slots:
                    s_def = all_slots.get(slot_name)
                    if s_def and hasattr(s_def, "equals_expression") and s_def.equals_expression:
                        refs = re.findall(r"\{([a-zA-Z0-9_]+)\}", s_def.equals_expression)
                        for ref in refs:
                            if ref not in class_def.slots:
                                diagnostics.append(Diagnostic(
                                    rule_id="LINT-005",
                                    severity="ERROR",
                                    target=f"{class_name}.{slot_name}",
                                    message=f"equals_expression references '{ref}' which is not a slot of '{class_name}'."
                                ))

        return diagnostics

"""components.agent.tools — Domain-agnostic generic primitives for Uniti.

Provides high-level, declarative functions over:
1. Graph & Ontology (SchemaView, draft modification, validation, sealing)
2. Operational Store & Digital Twin (compilation, projections query, explain)
3. Kernel & Provenance (activity ledger, assertion history, bitemporal tracing)
4. Write Gate & Task Execution (append-only intent/assertion submissions, corrections)
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import psycopg
import yaml
from linkml_runtime import SchemaView

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components" / "kernel"))
sys.path.insert(0, str(ROOT / "components" / "compiler"))
sys.path.insert(0, str(ROOT / "components" / "generator"))
sys.path.insert(0, str(ROOT / "components" / "ontology"))
sys.path.insert(0, str(ROOT / "components" / "provenance"))
sys.path.insert(0, str(ROOT / "components" / "seal"))

from compile import (  # noqa: E402
    OPS_DSN,
    _aggregate_classes,
    _annotation,
    _entity_classes,
    compile_class,
    plan_for,
    read_map,
    sql_text,
)
from generate import MapError, _registry, columns, submit  # noqa: E402
from ontology.resolve import load_versions, resolve_version  # noqa: E402
from perform import DSN as KERNEL_DSN  # noqa: E402
from perform import connect as connect_kernel  # noqa: E402
import provenance  # noqa: E402
from seal import DraftError, seal, _validate  # noqa: E402


# -----------------------------------------------------------------------------
# Serialization Helpers
# -----------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """Recursively convert types into JSON-serializable primitives."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        # Return as float if it has decimal places, else int
        return float(obj) if obj % 1 else int(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize(item) for item in obj]
    return obj


def _clean_clock(clock: Optional[str]) -> Optional[str]:
    """Normalize date/time input to ISO 8601 UTC string."""
    if not clock:
        return None
    written = str(clock).strip()
    if len(written) == 10:  # e.g. YYYY-MM-DD
        try:
            day = datetime.fromisoformat(written)
            return day.replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
            ).isoformat()
        except ValueError:
            return written
    return written


# -----------------------------------------------------------------------------
# UnitiTools Class
# -----------------------------------------------------------------------------

class UnitiTools:
    """Generic tool dispatcher for Uniti operating system capabilities."""

    def __init__(
        self,
        default_business: str = "sorella_demo",
        kernel_dsn: Optional[str] = None,
        ops_dsn: Optional[str] = None,
    ):
        self.default_business = default_business
        self.kernel_dsn = kernel_dsn or os.environ.get(
            "UNITI_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_demo"
        )
        self.ops_dsn = ops_dsn or os.environ.get(
            "UNITI_OPS_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_demo_ops"
        )

    def _get_business_dir(self, business: Optional[str]) -> Path:
        biz = business or self.default_business
        bdir = ROOT / "business" / biz
        if not bdir.is_dir():
            raise FileNotFoundError(f"Business directory '{biz}' not found at {bdir}")
        return bdir

    def _resolve_map(
        self,
        business: Optional[str] = None,
        valid_at: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolves the active sealed map or latest version for the business."""
        bdir = self._get_business_dir(business)
        versions = load_versions(bdir)
        if not versions:
            raise FileNotFoundError(f"No sealed versions found in {bdir}")

        if valid_at or as_of:
            v_at = _clean_clock(valid_at) or datetime.now(timezone.utc).isoformat()
            a_of = _clean_clock(as_of) or datetime.now(timezone.utc).isoformat()
            winning = resolve_version(bdir, valid_at=v_at, as_of=a_of)
            chosen_path = winning["path"] if winning else versions[-1]["path"]
        else:
            chosen_path = versions[-1]["path"]

        map_ = read_map(chosen_path)
        map_["business"] = bdir.name
        return map_

    def _connect_kernel(self):
        return psycopg.connect(self.kernel_dsn)

    def _connect_ops(self):
        return psycopg.connect(self.ops_dsn)

    # =========================================================================
    # Pilar 1: Knowledge Graph & Ontology (Read & Write)
    # =========================================================================

    def graph_get_schema(
        self,
        business: Optional[str] = None,
        class_name: Optional[str] = None,
        slot_name: Optional[str] = None,
        valid_at: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspect LinkML ontology schema: classes, slots, derivation formulas, and relationships.

        Args:
            business: Business namespace (default: "sorella_demo").
            class_name: Optional specific class to inspect (e.g. "StockReconciliation").
            slot_name: Optional specific slot to inspect.
            valid_at: Bitemporal business clock.
            as_of: Bitemporal system audit clock.
        """
        map_ = self._resolve_map(business, valid_at, as_of)
        view: SchemaView = map_["view"]

        if slot_name and class_name:
            slot_def = view.induced_slot(slot_name, class_name)
            return _serialize({
                "slot_name": slot_name,
                "class_name": class_name,
                "range": slot_def.range,
                "required": bool(slot_def.required),
                "multivalued": bool(slot_def.multivalued),
                "description": slot_def.description or "",
                "slot_uri": slot_def.slot_uri,
                "equals_expression": slot_def.equals_expression,
                "aggregate": _annotation(slot_def, "aggregate"),
                "parameter": _annotation(slot_def, "parameter"),
            })

        if class_name:
            cdef = view.get_class(class_name)
            if not cdef:
                raise ValueError(f"Class '{class_name}' does not exist in schema {map_['version']}")

            slots_info = {}
            for sname in view.class_slots(class_name):
                sdef = view.induced_slot(sname, class_name)
                slots_info[sname] = {
                    "range": sdef.range,
                    "required": bool(sdef.required),
                    "multivalued": bool(sdef.multivalued),
                    "description": sdef.description or "",
                    "slot_uri": sdef.slot_uri,
                    "equals_expression": sdef.equals_expression,
                    "aggregate": _annotation(sdef, "aggregate"),
                    "parameter": _annotation(sdef, "parameter"),
                }

            return _serialize({
                "business": map_["business"],
                "version": map_["version"],
                "class_name": class_name,
                "is_a": cdef.is_a,
                "description": cdef.description or "",
                "slots": slots_info,
            })

        # List all classes overview
        classes_overview = {}
        agg_classes = set(_aggregate_classes(map_))
        for cname in sorted(view.all_classes()):
            cdef = view.get_class(cname)
            slots = list(view.class_slots(cname))
            is_projection = cname in agg_classes
            classes_overview[cname] = {
                "description": cdef.description or "",
                "is_a": cdef.is_a,
                "slots_count": len(slots),
                "slots": slots,
                "is_projection": is_projection,
            }

        return _serialize({
            "business": map_["business"],
            "version": map_["version"],
            "classes_count": len(classes_overview),
            "classes": classes_overview,
        })

    def graph_update_draft(
        self,
        business: Optional[str] = None,
        yaml_content: Optional[str] = None,
        transcript_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write or patch draft ontology (draft.yaml) and draft interview transcript (draft.txt).

        Args:
            business: Target business namespace (default: "sorella_demo").
            yaml_content: Complete LinkML schema YAML content to save as draft.yaml.
            transcript_notes: Supporting domain interview notes to append or write to draft.txt.
        """
        bdir = self._get_business_dir(business)
        draft_yaml_path = bdir / "draft.yaml"
        draft_txt_path = bdir / "draft.txt"

        written = {}
        if yaml_content is not None:
            draft_yaml_path.write_text(yaml_content, encoding="utf-8", newline="\n")
            written["draft_yaml"] = {
                "path": str(draft_yaml_path),
                "bytes": len(yaml_content.encode("utf-8")),
            }

        if transcript_notes is not None:
            # If draft.txt already exists and has content, append notes
            if draft_txt_path.exists() and transcript_notes.startswith("+++"):
                existing = draft_txt_path.read_text(encoding="utf-8")
                new_text = existing + "\n\n" + transcript_notes[3:].strip()
            else:
                new_text = transcript_notes
            draft_txt_path.write_text(new_text, encoding="utf-8", newline="\n")
            written["draft_txt"] = {
                "path": str(draft_txt_path),
                "bytes": len(new_text.encode("utf-8")),
            }

        return _serialize({
            "status": "ok",
            "business": bdir.name,
            "written": written,
        })

    def graph_validate_draft(self, business: Optional[str] = None) -> Dict[str, Any]:
        """Validate draft.yaml against LinkML schema rules and requirements before sealing."""
        bdir = self._get_business_dir(business)
        draft_yaml_path = bdir / "draft.yaml"
        if not draft_yaml_path.is_file():
            return {"valid": False, "error": f"No draft.yaml found at {draft_yaml_path}"}

        try:
            text = draft_yaml_path.read_text(encoding="utf-8")
            view = _validate(text, "draft.yaml")
            draft = yaml.safe_load(text) or {}
            annotations = draft.get("annotations") or {}
            if "valid_from" not in annotations:
                return {
                    "valid": False,
                    "error": "draft.yaml is missing required 'annotations.valid_from' timestamp",
                }

            return _serialize({
                "valid": True,
                "classes_count": len(view.all_classes()),
                "slots_count": len(view.all_slots()),
                "classes": list(view.all_classes().keys()),
            })
        except Exception as exc:
            return {"valid": False, "error": f"{type(exc).__name__}: {str(exc)}"}

    def graph_seal_version(
        self,
        business: Optional[str] = None,
        actor: str = "agent",
        valid_from: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Seal draft.yaml into the next immutable version v(N+1).yaml and register entity URIs.

        Args:
            business: Target business namespace.
            actor: Actor identity performing the seal.
            valid_from: Optional timestamp when this version becomes valid.
        """
        bdir = self._get_business_dir(business)
        draft_path = bdir / "draft.yaml"
        if not draft_path.is_file():
            raise FileNotFoundError(f"No draft.yaml found to seal at {draft_path}")

        with self._connect_kernel() as conn:
            result = seal(draft_path, into=bdir, actor_id=actor, conn=conn)

        return _serialize({
            "status": "sealed",
            "version": result["version"],
            "path": result["path"],
            "assertions_count": len(result.get("assertions", [])),
            "entities_minted": len(result.get("minted", {})),
        })

    # =========================================================================
    # Pilar 2: Digital Twin & Analytical Projections (Read)
    # =========================================================================

    def ops_list_projections(
        self,
        business: Optional[str] = None,
        valid_at: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all analytical projections and tables compiled from the ontology.

        Args:
            business: Target business namespace.
            valid_at: Bitemporal business clock.
            as_of: Bitemporal system audit clock.
        """
        map_ = self._resolve_map(business, valid_at, as_of)
        agg_classes = _aggregate_classes(map_)
        ent_classes = _entity_classes(map_)

        projections = {}
        for cname in agg_classes:
            plan = plan_for(map_, cname)
            cols = [
                {
                    "name": col["name"],
                    "kind": col["kind"],
                    "formula": col.get("formula") or col.get("expression") or "",
                }
                for col in plan["columns"]
            ]
            projections[cname] = {
                "type": "aggregate_projection",
                "table_name": plan["table"],
                "columns_count": len(cols),
                "columns": cols,
            }

        return _serialize({
            "business": map_["business"],
            "version": map_["version"],
            "aggregate_projections": projections,
            "entity_tables_count": len(ent_classes),
            "entity_classes": ent_classes,
        })

    def ops_query_projection(
        self,
        class_name: str = "StockReconciliation",
        business: Optional[str] = None,
        valid_at: Optional[str] = None,
        as_of: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute dynamic SQL compiler for an analytical projection and return structured rows.

        Args:
            class_name: Target projection class (e.g. "StockReconciliation", "IngredientOnHand").
            business: Business namespace.
            valid_at: Business moment (ISO timestamp or YYYY-MM-DD).
            as_of: System audit moment (ISO timestamp or YYYY-MM-DD).
            filters: Optional dict of key-value column filters to apply to results.
        """
        map_ = self._resolve_map(business, valid_at, as_of)
        v_at = _clean_clock(valid_at) or datetime.now(timezone.utc).isoformat()
        a_of = _clean_clock(as_of) or datetime.now(timezone.utc).isoformat()

        with self._connect_kernel() as kernel, self._connect_ops() as ops:
            built = compile_class(kernel, ops, map_, class_name, valid_at=v_at, as_of=a_of)

        columns_meta = built["plan"]["columns"]
        col_names = [c["name"] for c in columns_meta]

        raw_rows = built["rows"]
        formatted_rows = []
        for r in raw_rows:
            row_dict = dict(zip(col_names, r))
            # Apply filters if provided
            if filters:
                match = True
                for f_col, f_val in filters.items():
                    val = str(row_dict.get(f_col, ""))
                    if str(f_val).lower() not in val.lower():
                        match = False
                        break
                if not match:
                    continue
            formatted_rows.append(row_dict)

        return _serialize({
            "class": class_name,
            "table": built["plan"]["table"],
            "valid_at": v_at,
            "as_of": a_of,
            "columns": col_names,
            "row_count": len(formatted_rows),
            "rows": formatted_rows,
        })

    def ops_explain_projection(
        self,
        class_name: str = "StockReconciliation",
        business: Optional[str] = None,
        valid_at: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve compiled SQL statements, CTE structures, and execution plans for a projection.

        Args:
            class_name: Target projection class.
            business: Business namespace.
            valid_at: Business moment.
            as_of: System audit moment.
        """
        map_ = self._resolve_map(business, valid_at, as_of)
        v_at = _clean_clock(valid_at) or datetime.now(timezone.utc).isoformat()
        a_of = _clean_clock(as_of) or datetime.now(timezone.utc).isoformat()

        with self._connect_kernel() as kernel, self._connect_ops() as ops:
            built = compile_class(kernel, ops, map_, class_name, valid_at=v_at, as_of=a_of)

        sql = sql_text(built)
        return _serialize({
            "class": class_name,
            "table": built["plan"]["table"],
            "columns": [c["name"] for c in built["plan"]["columns"]],
            "emitted_sql": sql,
            "ddl": built["ddl"],
        })

    # =========================================================================
    # Pilar 3: Kernel Provenance & Forensic Audit (Read)
    # =========================================================================

    def kernel_get_activity(
        self,
        business: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        filter_type: str = "all",
        actor: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch immutable assertion activity ledger with actor, intent, and bitemporal details.

        Args:
            business: Business namespace.
            limit: Maximum rows to return (default: 20).
            offset: Pagination offset.
            filter_type: Filter category ('all', 'revocations', 'master', 'stocktake', 'movement').
            actor: Filter by specific actor identity (e.g. 'marina', 'agent').
            search: Free-text search on subject, predicate, or values.
        """
        with self._connect_kernel() as kernel:
            summary = provenance.window(kernel)
            rows = provenance.recent_assertions(
                kernel,
                limit=limit,
                filter_type=filter_type,
                actor=actor,
                search=search,
            )

        return _serialize({
            "kernel_summary": summary,
            "count_returned": len(rows),
            "filter_applied": {
                "filter_type": filter_type,
                "actor": actor,
                "search": search,
                "limit": limit,
            },
            "activity_rows": rows,
        })

    def kernel_trace_provenance(
        self,
        subject: str,
        predicate: Optional[str] = None,
        business: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform deep forensic bitemporal audit: trace every assertion ever made about an entity.

        Args:
            subject: URI or identifier of the entity (e.g. 'sorella:item_vanilla_extract').
            predicate: Optional predicate URI or slot name to focus on.
            business: Business namespace.
        """
        if not subject:
            raise ValueError("Parameter 'subject' is required for provenance tracing.")

        with self._connect_kernel() as kernel:
            by_uri, by_id = provenance._registry(kernel)
            if subject not in by_uri:
                return _serialize({
                    "subject": subject,
                    "error": f"the log has never registered {subject!r}",
                    "assertions_count": 0,
                    "history_chain": [],
                })

            if predicate:
                target_pred = predicate
                if target_pred not in by_uri:
                    map_ = self._resolve_map(business)
                    view = map_["view"]
                    for slot in view.all_slots().values():
                        if slot.name == predicate and slot.slot_uri in by_uri:
                            target_pred = slot.slot_uri
                            break
                if target_pred in by_uri:
                    hist = provenance.history(kernel, subject, target_pred)
                    history_chain = hist["rows"]
                else:
                    return _serialize({
                        "subject": subject,
                        "predicate": predicate,
                        "error": f"Predicate '{predicate}' is not registered in the log.",
                        "assertions_count": 0,
                        "history_chain": [],
                    })
            else:
                from psycopg.rows import dict_row
                sub_id = by_uri[subject]
                with kernel.cursor(row_factory=dict_row) as cur:
                    cur.execute("""
                        SELECT a.*, i.occurred_at, i.actor_id, i.agent_id, i.action_name, i.note, i.reason_code
                        FROM assertion a
                        JOIN intent i ON a.intent_id = i.id
                        WHERE a.subject_id = %s
                        ORDER BY a.valid_from DESC, a.recorded_at DESC, a.seq DESC
                    """, (sub_id,))
                    raw = cur.fetchall()
                revoked_by = {row["revokes"]: row["id"] for row in raw if row["revokes"]}
                history_chain = []
                for row in raw:
                    history_chain.append({
                        **row,
                        "subject": subject,
                        "predicate": by_id.get(row["predicate_id"], str(row["predicate_id"])),
                        "value": (by_id.get(row["value_ref"], str(row["value_ref"]))
                                  if row["value_ref"] else row["value_literal"]),
                        "ref": row["value_ref"] is not None,
                        "revoked_by": revoked_by.get(row["id"]),
                    })

        return _serialize({
            "subject": subject,
            "predicate": predicate or "all",
            "assertions_count": len(history_chain),
            "history_chain": history_chain,
        })

    # =========================================================================
    # Pilar 4: Write Gate & Task Execution (Write)
    # =========================================================================

    def kernel_submit_transaction(
        self,
        class_name: str,
        fields: Dict[str, Any],
        actor: str = "agent",
        action_name: Optional[str] = None,
        subject: Optional[str] = None,
        valid_from: Optional[str] = None,
        reason: Optional[str] = None,
        business: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a new operational transaction or fact into the kernel via the official write gate.

        Creates exactly 1 intent and N assertions atomically in the append-only ledger.

        Args:
            class_name: Class of transaction/document (e.g. "StockMovement", "StockCount").
            fields: Dict of slot key-values.
            actor: Actor identity (e.g. "ai_agent", "marina").
            action_name: Action identifier on intent.
            subject: Optional entity URI. If omitted, will be generated.
            valid_from: Business effective timestamp (ISO format).
            reason: Audit note / explanation for why this action was performed.
            business: Business namespace.
        """
        map_ = self._resolve_map(business)
        v_from = _clean_clock(valid_from) or datetime.now(timezone.utc).isoformat()
        act_name = action_name or f"agent_submit_{class_name}"

        # If subject not given, generate a readable URI
        subj_uri = subject
        if not subj_uri:
            ts_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            subj_uri = f"{map_['business']}:{class_name.lower()}_{ts_slug}"

        with self._connect_kernel() as kernel:
            result = submit(
                kernel,
                map_,
                class_name,
                subject=subj_uri,
                values=fields,
                actor_id=actor,
                valid_from=v_from,
                reason_code="AGENT_ACTION",
                note=reason or f"Autonomous transaction by {actor}",
            )

        return _serialize({
            "status": "committed",
            "class_name": class_name,
            "subject": subj_uri,
            "intent_id": result["intent_id"],
            "assertions_count": len(result["assertions"]),
            "stated_assertions": result["stated"],
        })

    def kernel_correct_assertion(
        self,
        revokes_assertion_id: Union[str, int, UUID],
        subject: str,
        predicate: str,
        new_value: Optional[str] = None,
        actor: str = "agent",
        valid_from: Optional[str] = None,
        reason: Optional[str] = None,
        business: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform an append-only bitemporal correction or retraction on a previous assertion.

        Never deletes or updates rows. Writes a new assertion that revokes the old one via `revokes`.

        Args:
            revokes_assertion_id: The ID (UUID or string) of the previous assertion being withdrawn/replaced.
            subject: Entity URI of the assertion.
            predicate: Predicate URI or slot name.
            new_value: New value if correcting. If None, performs a pure retraction.
            actor: Actor identity performing correction.
            valid_from: Business effective date of the correction.
            reason: Audit rationale for correction.
            business: Business namespace.
        """
        map_ = self._resolve_map(business)
        v_from = _clean_clock(valid_from) or datetime.now(timezone.utc).isoformat()

        # Find corresponding slot_name and class_name
        view: SchemaView = map_["view"]
        target_class, target_slot = None, None
        for cname in view.all_classes():
            for sname in view.class_slots(cname):
                sdef = view.induced_slot(sname, cname)
                if sdef.slot_uri == predicate or sname == predicate or str(sdef.name) == predicate:
                    target_class = str(cname)
                    target_slot = str(sname)
                    break
            if target_class:
                break

        if not target_class or not target_slot:
            # Fallback to generic Entity class
            target_class = "Entity"
            target_slot = predicate

        values = {target_slot: new_value} if new_value is not None else {}
        revokes = {target_slot: str(revokes_assertion_id)}

        with self._connect_kernel() as kernel:
            result = submit(
                kernel,
                map_,
                target_class,
                subject=subject,
                values=values,
                actor_id=actor,
                revokes=revokes,
                valid_from=v_from,
                reason_code="CORRECTION",
                note=reason or f"Correction revoking assertion #{revokes_assertion_id}",
            )

        return _serialize({
            "status": "corrected",
            "revoked_assertion_id": revokes_assertion_id,
            "intent_id": result["intent_id"],
            "new_assertions": result["assertions"],
        })

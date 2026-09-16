from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

class SchemaPatcher:
    """Reads and safely modifies a draft LinkML schema."""
    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        default_skeleton = {
            "id": f"https://w3id.org/uniti/draft/{self.schema_path.stem}",
            "name": self.schema_path.stem,
            "prefixes": {
                "linkml": "https://w3id.org/linkml/",
                "uniti": "https://w3id.org/uniti/core#",
                "inv": "https://w3id.org/uniti/vocab/inv#",
                "proc": "https://w3id.org/uniti/vocab/proc#",
                "fin": "https://w3id.org/uniti/vocab/fin#",
            },
            "imports": ["linkml:types", "@uniti/core"],
            "default_prefix": "uniti",
            "default_range": "string",
            "classes": {},
            "slots": {},
        }
        if not self.schema_path.exists():
            return default_skeleton
        text = self.schema_path.read_text(encoding="utf-8")
        if not text.strip():
            return default_skeleton
        data = yaml.safe_load(text) or {}
        if not data.get("name"):
            data.setdefault("name", self.schema_path.stem)
        if not data.get("id"):
            data.setdefault("id", f"https://w3id.org/uniti/draft/{self.schema_path.stem}")
        if not data.get("prefixes"):
            data.setdefault("prefixes", default_skeleton["prefixes"])
        if not data.get("imports"):
            data.setdefault("imports", default_skeleton["imports"])
        return data

    def save(self):
        self.schema_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.schema_path, "w", encoding="utf-8") as f:
            yaml.dump(self.data, f, sort_keys=False, allow_unicode=True)

    def add_class(self, name: str, is_a: str, description: str, slots: Optional[List[str]] = None, annotations: Optional[Dict[str, Any]] = None):
        classes = self.data.setdefault("classes", {})
        cls_def = classes.setdefault(name, {})
        cls_def["is_a"] = is_a
        cls_def["description"] = description
        if slots:
            cls_def["slots"] = list(dict.fromkeys(cls_def.get("slots", []) + slots))
        if annotations:
            existing_ann = cls_def.setdefault("annotations", {})
            existing_ann.update(annotations)

    # The three ways a column can be derived rather than stated. The compiler
    # refuses a column that declares more than one, so this refuses it first,
    # while the author is still here to be told.
    DERIVATION_ANNOTATIONS = ("aggregate", "parameter")

    def add_slot(self, name: str, slot_uri: Optional[str] = None, range: str = "string",
                 description: str = "", identifier: bool = False,
                 equals_expression: Optional[str] = None,
                 annotations: Optional[Dict[str, Any]] = None):
        """Add a slot, always carrying an explicit `slot_uri`.

        A slot's URI is its identity in the kernel, so `seal` refuses a slot
        without one. Where the caller supplies no URI — no catalog entry
        matched — one is minted from the schema's own prefix and *written into
        the file*.

        Minting here is safe in the way minting at seal time is not: the URI
        becomes a stated line in the draft, so it is reviewable, and a later
        rename of the slot leaves it untouched. A URI derived on the fly at
        seal time would instead be recomputed from the new name and orphan
        every fact recorded under the old one.

        `equals_expression` and `annotations` are how a column is *derived*
        rather than stated: arithmetic over the columns beside it, an
        `aggregate` over a source class, or a `parameter` read off the entity a
        key column names. Without them a class can be called a Projection and
        still compute nothing — a table somebody has to fill in by hand.

        Annotations are written in LinkML's own shape, `{name: {value: spec}}`,
        which is what the compiler reads and what a sealed map already holds.
        """
        rules = [key for key in self.DERIVATION_ANNOTATIONS if (annotations or {}).get(key)]
        if equals_expression:
            rules.append("equals_expression")
        if len(rules) > 1:
            raise ValueError(
                f"slot '{name}' declares {sorted(rules)}, and a derived column "
                f"has exactly one rule"
            )

        slots = self.data.setdefault("slots", {})
        s_def = slots.setdefault(name, {})
        if slot_uri:
            s_def["slot_uri"] = slot_uri
        elif not s_def.get("slot_uri"):
            prefix = self.data.get("default_prefix") or "uniti"
            s_def["slot_uri"] = f"{prefix}:{name}"
        s_def["range"] = range
        if description:
            s_def["description"] = description
        if identifier:
            s_def["identifier"] = True
        if equals_expression:
            s_def["equals_expression"] = equals_expression
        if annotations:
            existing = s_def.setdefault("annotations", {})
            for key, spec in annotations.items():
                # A caller may hand over either the bare spec or one already
                # wrapped the way LinkML writes it; both mean the same thing.
                if isinstance(spec, dict) and set(spec) == {"value"}:
                    existing[key] = dict(spec)
                else:
                    existing[key] = {"value": spec}

    def add_invariant(self, class_name: str, inv_id: str, expression: str, message: str):
        classes = self.data.get("classes", {})
        if class_name not in classes:
            raise KeyError(f"Class {class_name} not found in draft.")
        cls_def = classes[class_name]
        ann = cls_def.setdefault("annotations", {})
        invariants = ann.setdefault("invariants", {"value": []})
        inv_list = invariants["value"] if isinstance(invariants, dict) and "value" in invariants else []
        existing = [i for i in inv_list if i.get("id") == inv_id]
        if existing:
            existing[0]["expression"] = expression
            existing[0]["message"] = message
        else:
            inv_list.append({"id": inv_id, "expression": expression, "message": message})
        ann["invariants"] = {"value": inv_list}

    def set_lifecycle(self, class_name: str, initial: str, states: Dict[str, Any], transitions: List[Dict[str, Any]]):
        classes = self.data.get("classes", {})
        if class_name not in classes:
            raise KeyError(f"Class {class_name} not found in draft.")
        cls_def = classes[class_name]
        ann = cls_def.setdefault("annotations", {})
        ann["lifecycle"] = {
            "value": {
                "initial": initial,
                "states": states,
                "transitions": transitions,
            }
        }

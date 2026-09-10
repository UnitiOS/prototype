"""components.agent.server — Model Context Protocol (MCP) server for Uniti.

Provides a standard JSON-RPC 2.0 stdio server conforming to the Model Context
Protocol (MCP) specification (2024-11-05). Allows any AI agent (Claude Desktop,
Cursor, Antigravity, or custom LLM client) to interact with Uniti's Graph,
Operational Projections, and Kernel via generic, domain-agnostic tools.

Run:
    .venv/Scripts/python.exe components/agent/server.py
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "components" / "agent"))

try:
    from .tools import UnitiTools, _serialize
except (ImportError, ValueError):
    from tools import UnitiTools, _serialize

# Configure logging to stderr to prevent any interference with stdout JSON-RPC
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(asctime)s] [uniti-mcp] %(levelname)s: %(message)s",
)
logger = logging.getLogger("uniti-mcp")

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "uniti-mcp-server",
    "version": "1.0.0",
}

# -----------------------------------------------------------------------------
# Tool Definitions (MCP Schema)
# -----------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "graph_get_schema",
        "description": (
            "Inspect the LinkML ontology knowledge graph: classes, slots, data types, "
            "relationships, and derivation rules (equals_expression and aggregate formulas)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "business": {
                    "type": "string",
                    "description": "Business namespace (default: 'sorella_demo').",
                },
                "class_name": {
                    "type": "string",
                    "description": "Optional specific class to inspect in detail (e.g. 'StockReconciliation').",
                },
                "slot_name": {
                    "type": "string",
                    "description": "Optional specific slot name to inspect.",
                },
                "valid_at": {
                    "type": "string",
                    "description": "Business validity moment (ISO timestamp or YYYY-MM-DD).",
                },
                "as_of": {
                    "type": "string",
                    "description": "System audit moment (ISO timestamp or YYYY-MM-DD).",
                },
            },
        },
    },
    {
        "name": "graph_update_draft",
        "description": (
            "Write or patch draft ontology (draft.yaml) and domain interview transcript (draft.txt). "
            "Allows an agent to define new classes, slots, or derivation rules in the draft stage."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "business": {
                    "type": "string",
                    "description": "Target business namespace (default: 'sorella_demo').",
                },
                "yaml_content": {
                    "type": "string",
                    "description": "Complete LinkML schema YAML to write as draft.yaml.",
                },
                "transcript_notes": {
                    "type": "string",
                    "description": "Interview transcript notes to write or append (use '+++' prefix to append).",
                },
            },
        },
    },
    {
        "name": "graph_validate_draft",
        "description": (
            "Validate draft.yaml against LinkML schema rules and requirements before sealing. "
            "Ensures types, ranges, slots, and annotations are sound."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "business": {
                    "type": "string",
                    "description": "Target business namespace (default: 'sorella_demo').",
                },
            },
        },
    },
    {
        "name": "graph_seal_version",
        "description": (
            "Seal draft.yaml into the next immutable version v(N+1).yaml, recording sealed_at timestamp "
            "and publishing entity URIs into the kernel. Sealed versions cannot be modified."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "business": {
                    "type": "string",
                    "description": "Target business namespace.",
                },
                "actor": {
                    "type": "string",
                    "description": "Actor identity performing the seal.",
                    "default": "agent",
                },
                "valid_from": {
                    "type": "string",
                    "description": "Optional timestamp when this schema version becomes active.",
                },
            },
        },
    },
    {
        "name": "ops_list_projections",
        "description": (
            "Discover all analytical projections and tables compiled from the ontology rules "
            "(e.g. StockReconciliation, IngredientOnHand) with their measure and grouping columns."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "business": {
                    "type": "string",
                    "description": "Target business namespace.",
                },
                "valid_at": {
                    "type": "string",
                    "description": "Business validity moment.",
                },
                "as_of": {
                    "type": "string",
                    "description": "System audit moment.",
                },
            },
        },
    },
    {
        "name": "ops_query_projection",
        "description": (
            "Query an operational analytical projection (digital twin) at specific bitemporal clocks. "
            "Executes dynamic SQL compiler multi-CTE aggregations and returns structured rows."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "class_name": {
                    "type": "string",
                    "description": "Target projection class (e.g. 'StockReconciliation', 'IngredientOnHand').",
                    "default": "StockReconciliation",
                },
                "business": {
                    "type": "string",
                    "description": "Business namespace.",
                },
                "valid_at": {
                    "type": "string",
                    "description": "Business validity clock (ISO timestamp or YYYY-MM-DD).",
                },
                "as_of": {
                    "type": "string",
                    "description": "System audit clock (ISO timestamp or YYYY-MM-DD).",
                },
                "filters": {
                    "type": "object",
                    "description": "Optional column-value filter mapping to filter returned rows.",
                },
            },
            "required": ["class_name"],
        },
    },
    {
        "name": "ops_explain_projection",
        "description": (
            "Retrieve emitted SQL multi-CTE statements and plan metadata for a compiled projection "
            "for complete execution transparency and formula verification."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "class_name": {
                    "type": "string",
                    "description": "Target projection class.",
                    "default": "StockReconciliation",
                },
                "business": {
                    "type": "string",
                    "description": "Business namespace.",
                },
                "valid_at": {
                    "type": "string",
                    "description": "Business validity moment.",
                },
                "as_of": {
                    "type": "string",
                    "description": "System audit moment.",
                },
            },
            "required": ["class_name"],
        },
    },
    {
        "name": "kernel_get_activity",
        "description": (
            "Fetch recent assertions from the immutable append-only kernel ledger with actor signatures, "
            "intent notes, and status categories (revocations, master data, movements, stocktakes)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "business": {
                    "type": "string",
                    "description": "Business namespace.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows to return (default: 20).",
                    "default": 20,
                },
                "filter_type": {
                    "type": "string",
                    "enum": ["all", "revocations", "master", "stocktake", "movement"],
                    "description": "Category filter.",
                    "default": "all",
                },
                "actor": {
                    "type": "string",
                    "description": "Filter by actor identity (e.g. 'marina', 'agent').",
                },
                "search": {
                    "type": "string",
                    "description": "Free text search on subject or value.",
                },
            },
        },
    },
    {
        "name": "kernel_trace_provenance",
        "description": (
            "Perform deep forensic bitemporal audit: trace every assertion ever made about an entity, "
            "revealing chronological value changes, author identities, timestamps, and revocation chains."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Entity URI or identifier (e.g. 'sorella:item_vanilla_extract').",
                },
                "predicate": {
                    "type": "string",
                    "description": "Optional slot name or predicate URI to filter.",
                },
                "business": {
                    "type": "string",
                    "description": "Business namespace.",
                },
            },
            "required": ["subject"],
        },
    },
    {
        "name": "kernel_submit_transaction",
        "description": (
            "Submit a new operational transaction or fact into the kernel via the official write gate. "
            "Atomically records 1 intent and N assertions in the append-only ledger."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "class_name": {
                    "type": "string",
                    "description": "Class of transaction (e.g. 'StockMovement', 'StockCount', 'Ingredient').",
                },
                "fields": {
                    "type": "object",
                    "description": "Dictionary of field name -> value.",
                },
                "actor": {
                    "type": "string",
                    "description": "Actor identity submitting the transaction.",
                    "default": "agent",
                },
                "action_name": {
                    "type": "string",
                    "description": "Intent action name (e.g. 'stock_adjustment', 'goods_receipt').",
                },
                "subject": {
                    "type": "string",
                    "description": "Optional entity URI. If omitted, will be generated.",
                },
                "valid_from": {
                    "type": "string",
                    "description": "Business effective moment (ISO timestamp).",
                },
                "reason": {
                    "type": "string",
                    "description": "Audit rationale explaining why this action was taken.",
                },
                "business": {
                    "type": "string",
                    "description": "Business namespace.",
                },
            },
            "required": ["class_name", "fields"],
        },
    },
    {
        "name": "kernel_correct_assertion",
        "description": (
            "Perform an append-only bitemporal correction or retraction on a previous assertion. "
            "Never deletes or updates records; writes a new assertion pointing to revokes_assertion_id."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "revokes_assertion_id": {
                    "type": "string",
                    "description": "ID (UUID string) of the previous assertion being withdrawn or corrected.",
                },
                "subject": {
                    "type": "string",
                    "description": "Entity URI of the assertion.",
                },
                "predicate": {
                    "type": "string",
                    "description": "Predicate URI or slot name.",
                },
                "new_value": {
                    "type": "string",
                    "description": "New value to assert. If omitted/null, performs a pure retraction.",
                },
                "actor": {
                    "type": "string",
                    "description": "Actor identity performing correction.",
                    "default": "agent",
                },
                "valid_from": {
                    "type": "string",
                    "description": "Business effective moment of the correction.",
                },
                "reason": {
                    "type": "string",
                    "description": "Audit rationale for why the assertion is corrected.",
                },
                "business": {
                    "type": "string",
                    "description": "Business namespace.",
                },
            },
            "required": ["revokes_assertion_id", "subject", "predicate"],
        },
    },
]


# -----------------------------------------------------------------------------
# MCP Server Handler
# -----------------------------------------------------------------------------

class MCPServer:
    """Standard JSON-RPC 2.0 stdio server implementing Model Context Protocol."""

    def __init__(self, tools: Optional[UnitiTools] = None):
        self.tools = tools or UnitiTools()
        self._handlers = {
            "initialize": self._handle_initialize,
            "notifications/initialized": self._handle_initialized_notif,
            "ping": self._handle_ping,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
        }

    def _handle_initialize(self, req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Client connected: %s", params.get("clientInfo", {}))
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    },
                },
                "serverInfo": SERVER_INFO,
            },
        }

    def _handle_initialized_notif(self, req_id: Any, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        logger.info("Client initialized successfully.")
        return None

    def _handle_ping(self, req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    def _handle_tools_list(self, req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOL_DEFINITIONS,
            },
        }

    def _handle_tools_call(self, req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = params.get("name")
        args = params.get("arguments", {})
        logger.info("Calling tool: %s with args: %s", tool_name, list(args.keys()))

        func = getattr(self.tools, tool_name, None)
        if not func or not callable(func):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Tool '{tool_name}' is not recognized.",
                        }
                    ],
                },
            }

        try:
            res = func(**args)
            output_json = json.dumps(_serialize(res), indent=2)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": output_json,
                        }
                    ],
                },
            }
        except Exception as exc:
            logger.error("Error executing %s: %s", tool_name, exc, exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing tool '{tool_name}': {type(exc).__name__}: {str(exc)}",
                        }
                    ],
                },
            }

    def handle_message(self, message: str) -> Optional[str]:
        """Process one incoming JSON-RPC message line and return response string if applicable."""
        message = message.strip()
        if not message:
            return None

        try:
            req = json.loads(message)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON received: %s", exc)
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error: Invalid JSON"},
            })

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        handler = self._handlers.get(method)
        if not handler:
            if req_id is not None:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method '{method}' not found"},
                })
            return None

        resp = handler(req_id, params)
        if resp is not None:
            return json.dumps(resp)
        return None

    def run_stdio(self):
        """Main stdio loop reading line-by-line JSON-RPC messages."""
        logger.info("Uniti MCP server started on stdio. Awaiting commands...")
        for line in sys.stdin:
            response = self.handle_message(line)
            if response:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()


def main():
    server = MCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()

"""tests.agent.test_agent_mcp — Tests for Uniti MCP Server and generic agent tools."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "components"))
sys.path.insert(0, str(ROOT / "components" / "agent"))

from components.agent.server import MCPServer, PROTOCOL_VERSION, TOOL_DEFINITIONS
from components.agent.tools import UnitiTools


def test_mcp_initialize():
    server = MCPServer()
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "clientInfo": {"name": "test-suite", "version": "1.0.0"},
        },
    })
    raw_resp = server.handle_message(req)
    assert raw_resp is not None
    resp = json.loads(raw_resp)
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert resp["result"]["serverInfo"]["name"] == "uniti-mcp-server"


def test_mcp_tools_list():
    server = MCPServer()
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    })
    raw_resp = server.handle_message(req)
    assert raw_resp is not None
    resp = json.loads(raw_resp)
    tools = resp["result"]["tools"]
    assert len(tools) == 11
    names = {t["name"] for t in tools}
    expected = {
        "graph_get_schema",
        "graph_update_draft",
        "graph_validate_draft",
        "graph_seal_version",
        "ops_list_projections",
        "ops_query_projection",
        "ops_explain_projection",
        "kernel_get_activity",
        "kernel_trace_provenance",
        "kernel_submit_transaction",
        "kernel_correct_assertion",
    }
    assert expected == names


def test_graph_get_schema_all():
    tools = UnitiTools()
    res = tools.graph_get_schema(business="sorella_demo")
    assert res["business"] == "sorella_demo"
    assert "classes_count" in res
    assert "StockReconciliation" in res["classes"]
    assert "Ingredient" in res["classes"]


def test_graph_get_schema_specific_class():
    tools = UnitiTools()
    res = tools.graph_get_schema(business="sorella_demo", class_name="Ingredient")
    assert res["class_name"] == "Ingredient"
    assert "slots" in res
    assert "item_name" in res["slots"]
    assert "item_price_per_kg" in res["slots"]


def test_graph_validate_draft():
    tools = UnitiTools()
    res = tools.graph_validate_draft(business="sorella_demo")
    assert res["valid"] is True
    assert "classes_count" in res
    assert res["classes_count"] > 0


def test_ops_list_projections():
    tools = UnitiTools()
    res = tools.ops_list_projections(business="sorella_demo")
    assert "StockReconciliation" in res["aggregate_projections"]
    recon = res["aggregate_projections"]["StockReconciliation"]
    col_names = [c["name"] for c in recon["columns"]]
    assert "reconciliation_ingredient" in col_names
    assert "reconciliation_variance" in col_names


def test_ops_explain_projection():
    tools = UnitiTools()
    res = tools.ops_explain_projection(class_name="StockReconciliation", business="sorella_demo")
    assert res["class"] == "StockReconciliation"
    assert "WITH" in res["emitted_sql"]
    assert any("CREATE TABLE" in stmt for stmt in res["ddl"])


def test_mcp_tool_call_via_server():
    server = MCPServer()
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 99,
        "method": "tools/call",
        "params": {
            "name": "graph_get_schema",
            "arguments": {
                "business": "sorella_demo",
                "class_name": "Ingredient",
            },
        },
    })
    raw_resp = server.handle_message(req)
    assert raw_resp is not None
    resp = json.loads(raw_resp)
    assert resp["id"] == 99
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["class_name"] == "Ingredient"
    assert "item_price_per_kg" in content["slots"]

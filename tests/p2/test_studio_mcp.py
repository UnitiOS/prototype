import json
import tempfile
from pathlib import Path
import pytest

from components.agent.studio_server import StudioMCPServer

@pytest.fixture
def mcp():
    return StudioMCPServer()

def test_mcp_initialize(mcp):
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }
    res = mcp.handle_request(req)
    assert res["id"] == 1
    assert res["result"]["serverInfo"]["name"] == "uniti-studio-mcp"

def test_mcp_tools_list(mcp):
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    res = mcp.handle_request(req)
    tools = res["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "studio_search_catalog" in tool_names
    assert "studio_propose_patch" in tool_names
    assert "studio_validate_linter" in tool_names
    assert "studio_render_graph" in tool_names
    assert "studio_seal_package" in tool_names

def test_mcp_workflow_propose_and_validate(mcp):
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_path = Path(tmp_dir) / "test_pkg"
        pkg_path.mkdir(parents=True, exist_ok=True)

        # Propose patch
        patch_req = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "studio_propose_patch",
                "arguments": {
                    "package_path": str(pkg_path),
                    "class_name": "FabricRoll",
                    "archetype": "Resource",
                    "description": "Roll of textile fabric",
                    "slots": ["fabric_length"],
                    "slot_definitions": {
                        "fabric_length": {
                            "slot_uri": "inv:quantity",
                            "range": "decimal",
                            "description": "Total length in meters",
                        }
                    },
                },
            },
        }
        p_res = mcp.handle_request(patch_req)
        assert p_res["id"] == 10
        out = json.loads(p_res["result"]["content"][0]["text"])
        assert out["status"] == "PATCHED"

        # Render graph
        graph_req = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "studio_render_graph",
                "arguments": {"package_path": str(pkg_path)},
            },
        }
        g_res = mcp.handle_request(graph_req)
        g_out = json.loads(g_res["result"]["content"][0]["text"])
        assert any(n["id"] == "FabricRoll" for n in g_out["nodes"])

        # Validate linter
        lint_req = {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "studio_validate_linter",
                "arguments": {"package_path": str(pkg_path)},
            },
        }
        l_res = mcp.handle_request(lint_req)
        l_out = json.loads(l_res["result"]["content"][0]["text"])
        assert l_out["status"] == "PASS"
        assert l_out["can_seal"] is True

        # Seal package
        seal_req = {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "studio_seal_package",
                "arguments": {
                    "package_path": str(pkg_path),
                    "version": "1.0.0",
                    "author": "analyst@textile.id",
                },
            },
        }
        s_res = mcp.handle_request(seal_req)
        s_out = json.loads(s_res["result"]["content"][0]["text"])
        assert s_out["sealed"] is True
        assert s_out["version"] == "1.0.0"
        assert "sha256" in s_out

def test_mcp_search_catalog_tool(mcp):
    req = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "tools/call",
        "params": {
            "name": "studio_search_catalog",
            "arguments": {"query": "quantity", "domain": "inventory"},
        },
    }
    res = mcp.handle_request(req)
    assert res["id"] == 20
    out = json.loads(res["result"]["content"][0]["text"])
    assert len(out) > 0
    assert out[0]["curie"] == "inv:quantity"

def test_mcp_seal_rejection_on_linter_failure(mcp):
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_path = Path(tmp_dir) / "broken_pkg"
        pkg_path.mkdir(parents=True, exist_ok=True)

        # Propose patch with orphan class (LINT-001 violation)
        patch_req = {
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {
                "name": "studio_propose_patch",
                "arguments": {
                    "package_path": str(pkg_path),
                    "class_name": "OrphanEntity",
                    "archetype": "NonExistentArchetype",
                    "description": "Invalid class",
                },
            },
        }
        p_res = mcp.handle_request(patch_req)
        p_out = json.loads(p_res["result"]["content"][0]["text"])
        assert p_out["linter_status"] == "FAIL"

        # Attempt to seal
        seal_req = {
            "jsonrpc": "2.0",
            "id": 31,
            "method": "tools/call",
            "params": {
                "name": "studio_seal_package",
                "arguments": {"package_path": str(pkg_path), "version": "1.0.0"},
            },
        }
        s_res = mcp.handle_request(seal_req)
        s_out = json.loads(s_res["result"]["content"][0]["text"])
        assert s_out["sealed"] is False
        assert "linter errors must be resolved" in s_out["error"]

def test_mcp_unknown_method_and_tool_errors(mcp):
    # Unknown RPC method
    req_bad_method = {"jsonrpc": "2.0", "id": 40, "method": "foobar"}
    res = mcp.handle_request(req_bad_method)
    assert res["error"]["code"] == -32601

    # Unknown tool name
    req_bad_tool = {
        "jsonrpc": "2.0",
        "id": 41,
        "method": "tools/call",
        "params": {"name": "ghost_tool", "arguments": {}},
    }
    res2 = mcp.handle_request(req_bad_tool)
    assert res2["error"]["code"] == -32601


def test_mcp_init_package_and_write_gate_immutability(mcp):
    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_path = Path(tmp_dir) / "community_test"

        # 1. Init package via MCP
        init_req = {
            "jsonrpc": "2.0",
            "id": 50,
            "method": "tools/call",
            "params": {
                "name": "studio_init_package",
                "arguments": {
                    "package_path": str(pkg_path),
                    "title": "Community Test Package",
                    "domain": "inventory",
                    "author": "analyst@initi.org",
                },
            },
        }
        res_init = mcp.handle_request(init_req)
        out_init = json.loads(res_init["result"]["content"][0]["text"])
        assert out_init["status"] == "INITIALIZED"
        assert Path(out_init["manifest"]).exists()
        assert Path(out_init["schema_file"]).exists()

        # 2. Propose patch with automatic semantic catalog anchoring
        patch_req = {
            "jsonrpc": "2.0",
            "id": 51,
            "method": "tools/call",
            "params": {
                "name": "studio_propose_patch",
                "arguments": {
                    "package_path": str(pkg_path),
                    "class_name": "TestStockMovement",
                    "archetype": "Event",
                    "description": "Historical transfer event",
                    "slots": ["quantity", "source_location"],
                },
            },
        }
        res_patch = mcp.handle_request(patch_req)
        out_patch = json.loads(res_patch["result"]["content"][0]["text"])
        assert out_patch["status"] == "PATCHED"
        assert out_patch["linter_status"] == "PASS"

        # Verify auto-anchored slot_uris from catalog
        schema_text = Path(out_init["schema_file"]).read_text(encoding="utf-8")
        assert "slot_uri: inv:quantity" in schema_text
        assert "slot_uri: inv:source_location" in schema_text

        # 3. Seal the package
        seal_req = {
            "jsonrpc": "2.0",
            "id": 52,
            "method": "tools/call",
            "params": {
                "name": "studio_seal_package",
                "arguments": {
                    "package_path": str(pkg_path),
                    "version": "1.0.0",
                    "author": "analyst@initi.org",
                },
            },
        }
        res_seal = mcp.handle_request(seal_req)
        out_seal = json.loads(res_seal["result"]["content"][0]["text"])
        assert out_seal["sealed"] is True

        # 4. Write Gate Immutability Check: Attempt to patch sealed package must be REJECTED
        res_patch2 = mcp.handle_request(patch_req)
        out_patch2 = json.loads(res_patch2["result"]["content"][0]["text"])
        assert out_patch2["status"] == "REJECTED"
        assert out_patch2["can_patch"] is False
        assert "immutable" in out_patch2["error"].lower()


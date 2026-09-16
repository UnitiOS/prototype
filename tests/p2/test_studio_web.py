import io
import json
from unittest.mock import MagicMock
import pytest

from components.web.studio_handler import (
    list_available_packages,
    get_studio_html,
    handle_studio_api_get,
    handle_studio_api_post,
)

def test_list_available_packages():
    pkgs = list_available_packages()
    pkg_names = [p["name"] for p in pkgs]
    assert "@uniti/core" in pkg_names

def test_get_studio_html_rendering():
    html = get_studio_html(valid_at="2026-09-14", as_of="2026-09-14")
    assert "Uniti Studio" in html
    assert "Socratic Ontologist Workbench" in html
    assert "LINT-001 Archetype Lineage" in html
    assert "cytoscape" in html.lower()
    assert "yamlModal" in html

def test_handle_studio_api_get():
    handler = MagicMock()
    handler.wfile = io.BytesIO()

    # Packages endpoint
    handled = handle_studio_api_get(handler, ["api", "studio", "packages"], "")
    assert handled is True
    handler.send_response.assert_called_with(200)

    # Graph endpoint
    handler.wfile = io.BytesIO()
    handled_graph = handle_studio_api_get(handler, ["api", "studio", "graph"], "pkg=packages/@uniti/core")
    assert handled_graph is True

    # Lint endpoint
    handler.wfile = io.BytesIO()
    handled_lint = handle_studio_api_get(handler, ["api", "studio", "lint"], "pkg=packages/@uniti/core")
    assert handled_lint is True

    # Raw YAML endpoint
    handler.wfile = io.BytesIO()
    handled_yaml = handle_studio_api_get(handler, ["api", "studio", "raw_yaml"], "pkg=packages/@uniti/core")
    assert handled_yaml is True
    yaml_res = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert "content" in yaml_res

    # Catalog endpoint
    handler.wfile = io.BytesIO()
    handled_cat = handle_studio_api_get(handler, ["api", "studio", "catalog"], "q=quantity&domain=inventory")
    assert handled_cat is True
    cat_res = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert len(cat_res) > 0

def test_handle_studio_api_post_invariant_sandbox():
    handler = MagicMock()

    # 1. Denied invariant
    handler.wfile = io.BytesIO()
    body_denied = json.dumps({"subject": "test", "value": -5.0}).encode("utf-8")
    handled = handle_studio_api_post(handler, ["api", "studio", "test_invariant"], body_denied)
    assert handled is True
    out_denied = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert out_denied["status"] == "DENIED"

    # 2. Approved invariant
    handler.wfile = io.BytesIO()
    body_ok = json.dumps({"subject": "test", "value": 15.0}).encode("utf-8")
    handled = handle_studio_api_post(handler, ["api", "studio", "test_invariant"], body_ok)
    assert handled is True
    out_ok = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert out_ok["status"] == "APPROVED"

def test_handle_studio_api_post_chat_stream():
    handler = MagicMock()
    handler.wfile = io.BytesIO()
    body = json.dumps({"message": "Halo AI", "package_path": "packages/@uniti/core"}).encode("utf-8")
    handled = handle_studio_api_post(handler, ["api", "studio", "chat"], body)
    assert handled is True
    handler.send_response.assert_called_with(200)
    stream_output = handler.wfile.getvalue().decode("utf-8")
    assert len(stream_output) > 0

def test_handle_studio_api_post_seal_endpoint():
    import tempfile
    from pathlib import Path
    from components.agent.studio_server import StudioTools

    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_path = Path(tmp_dir) / "test_web_pkg"
        pkg_path.mkdir(parents=True, exist_ok=True)
        # Create minimal valid schema
        tools = StudioTools()
        tools.propose_patch(
            package_path=str(pkg_path),
            class_name="Box",
            archetype="Resource",
            description="A box",
        )

        handler = MagicMock()
        handler.wfile = io.BytesIO()
        body = json.dumps({"package_path": str(pkg_path), "version": "1.0.0"}).encode("utf-8")
        handled = handle_studio_api_post(handler, ["api", "studio", "seal"], body)
        assert handled is True
        out = json.loads(handler.wfile.getvalue().decode("utf-8"))
        assert out["sealed"] is True
        assert out["version"] == "1.0.0"

def test_handle_studio_api_post_patch():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp_dir:
        pkg_path = Path(tmp_dir) / "test_patch_pkg"
        pkg_path.mkdir(parents=True, exist_ok=True)

        handler = MagicMock()
        handler.wfile = io.BytesIO()
        body = json.dumps({
            "package_path": str(pkg_path),
            "class_name": "WarehouseBin",
            "archetype": "Resource",
            "description": "Storage bin in warehouse",
            "slots": ["bin_code"],
            "slot_definitions": {"bin_code": {"range": "string"}},
        }).encode("utf-8")
        handled = handle_studio_api_post(handler, ["api", "studio", "patch"], body)
        assert handled is True
        out = json.loads(handler.wfile.getvalue().decode("utf-8"))
        assert out["status"] == "PATCHED"
        assert "linter_status" in out

def test_handle_studio_model_status_and_config():
    handler = MagicMock()
    handler.wfile = io.BytesIO()

    # GET model_status
    handled = handle_studio_api_get(handler, ["api", "studio", "model_status"], "")
    assert handled is True
    out = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert "framework" in out
    assert "PydanticAI" in out["framework"]

    # POST config_model
    handler.wfile = io.BytesIO()
    body = json.dumps({"model": "gemini-2.0-flash", "api_key": "test_gemini_key"}).encode("utf-8")
    handled_post = handle_studio_api_post(handler, ["api", "studio", "config_model"], body)
    assert handled_post is True
    out_post = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert out_post["status"] == "OK"
    assert "gemini-2.0-flash" in out_post["model"]


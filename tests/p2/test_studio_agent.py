"""tests/p2/test_studio_agent.py — Tests for PydanticAI Socratic Ontologist Agent.

Validates model-agnostic resolution, Gemini integration, MCP tool registration,
and streaming endpoint functionality.
"""

import os
import pytest
import asyncio
from unittest.mock import patch
from pathlib import Path
from tests.p2.conftest import package_sandbox

from components.studio.agent import (
    resolve_model_string,
    create_socratic_agent,
    stream_socratic_agent,
    convert_history_to_model_messages,
    StudioAgentContext,
)
from components.agent.studio_server import StudioTools
from pydantic_ai.models.test import TestModel
from pydantic_ai.exceptions import UserError


def test_model_resolution_empty():
    with patch.dict(os.environ, {}, clear=True):
        assert resolve_model_string() is None


def test_model_resolution_gemini():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy-gemini-key"}, clear=True):
        m = resolve_model_string()
        assert m == "google:gemini-2.5-flash"
        assert os.environ.get("GOOGLE_API_KEY") == "dummy-gemini-key"


def test_model_resolution_google_api_key():
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "dummy-google-key"}, clear=True):
        m = resolve_model_string()
        assert m == "google:gemini-2.5-flash"


def test_model_resolution_vertex():
    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "my-vertex-proj"}, clear=True):
        m = resolve_model_string()
        assert m == "google-cloud:gemini-2.5-pro"


def test_model_resolution_vertex_express_aq_key():
    """An Express key resolves once the project it belongs to is stated."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AQ.Ab8TestKey",
                                 "GOOGLE_CLOUD_PROJECT": "test-project"},
                    clear=True):
        m = resolve_model_string()
        assert m == "google-cloud:gemini-3.8-flash"
        assert os.environ.get("GOOGLE_CLOUD_LOCATION") == "global"


def test_model_resolution_express_key_without_a_project_is_refused():
    """No installation's project id is a default for another one.

    The previous behaviour fell back to a project number belonging to one
    developer's account, so a misconfigured environment resolved to somebody
    else's project instead of saying what was missing.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AQ.Ab8TestKey"}, clear=True):
        with pytest.raises(UserError, match="GOOGLE_CLOUD_PROJECT"):
            resolve_model_string()


def test_model_resolution_openai():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-dummy"}, clear=True):
        m = resolve_model_string()
        assert m == "openai:gpt-4o"


def test_model_resolution_anthropic():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-dummy"}, clear=True):
        m = resolve_model_string()
        assert m == "anthropic:claude-3-5-sonnet-20241022"


def test_convert_history_to_model_messages():
    history = [
        {"role": "user", "content": "Hello, I want to create an archetype."},
        {"role": "assistant", "content": "Certainly, which archetype would you like to define?"},
    ]
    msgs = convert_history_to_model_messages(history)
    assert len(msgs) == 2
    assert msgs[0].parts[0].content == "Hello, I want to create an archetype."
    assert msgs[1].parts[0].content == "Certainly, which archetype would you like to define?"


def test_create_agent_with_test_model():
    agent = create_socratic_agent(model_override=TestModel())
    assert agent is not None
    # Verify system prompt presence
    assert "Socratic AI Ontologist" in agent._system_prompts[0]


def test_stream_unconfigured():
    with patch.dict(os.environ, {}, clear=True):
        async def _run():
            chunks = []
            async for chunk in stream_socratic_agent("Hello", "packages/@community/inventory"):
                chunks.append(chunk)
            return "".join(chunks)

        full_text = asyncio.run(_run())
        assert "Uniti Socratic Ontologist" in full_text
        assert "GEMINI_API_KEY" in full_text


def test_stream_with_test_model():
    """TestModel calls the registered tools with synthetic arguments.

    Those arguments include package paths, and the write gate acts on them, so
    this runs inside a sandbox. Without one the gate faithfully writes a package
    named after whatever string the test model happened to invent.
    """
    with package_sandbox() as sandbox:
        pkg_dir = Path(sandbox) / "test_pkg"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        schema_file = pkg_dir / "schema.yaml"
        schema_file.write_text("id: test\nname: test\nclasses: {}\nslots: {}\n", encoding="utf-8")

        async def _run():
            chunks = []
            async for chunk in stream_socratic_agent(
                "I want to add a Resource SilkFabric",
                str(pkg_dir),
                model_override=TestModel(),
            ):
                chunks.append(chunk)
            return "".join(chunks)

        full_text = asyncio.run(_run())

    assert len(full_text) > 0

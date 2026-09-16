"""components/studio/agent.py — PydanticAI-powered Socratic Ontologist Agent.

Model-agnostic agent with native Google Gemini (Cloud / Vertex / AI Studio)
and MCP tools from components/agent/studio_server.py.
"""

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure ROOT in sys.path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
)
from pydantic_ai.models import infer_model
from pydantic_ai.exceptions import UserError

from components.agent.studio_server import StudioTools
from components.studio.prompts import SOCRATIC_ONTOLOGIST_SYSTEM_PROMPT

logger = logging.getLogger("studio-agent")


@dataclass
class StudioAgentContext:
    package_path: str
    tools: StudioTools
    events: List[Dict[str, Any]] = field(default_factory=list)


def resolve_model_string() -> Optional[str]:
    """Resolve configured model string in model-agnostic fashion.
    Prioritizes Gemini/Vertex (as requested by user), with seamless fallback to Claude, OpenAI, Groq, Ollama.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    vertex_project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("VERTEX_PROJECT")
    explicit_model = os.environ.get("STUDIO_MODEL")

    if explicit_model:
        if any(explicit_model.startswith(p) for p in ("google:", "google-cloud:", "openai:", "anthropic:", "groq:", "ollama:")):
            return explicit_model

    # 1. Google Cloud Vertex AI Express key (starts with AQ.)
    if gemini_key and gemini_key.startswith("AQ."):
        os.environ["GOOGLE_API_KEY"] = gemini_key
        if not vertex_project:
            # One installation's project id is not a default for every other
            # installation. It is stated in the environment or not at all.
            raise UserError(
                "an Express key was given but no project: set "
                "GOOGLE_CLOUD_PROJECT (or VERTEX_PROJECT) in your environment"
            )
        model_name = explicit_model or "gemini-3.8-flash"
        if not os.environ.get("GOOGLE_CLOUD_LOCATION"):
            os.environ["GOOGLE_CLOUD_LOCATION"] = "global" if "3." in model_name else "us-central1"
        if not model_name.startswith("google-cloud:"):
            return f"google-cloud:{model_name}"
        return model_name

    # 2. Google Cloud / Vertex AI via GOOGLE_CLOUD_PROJECT or VERTEX_PROJECT
    if vertex_project:
        model_name = explicit_model or "gemini-2.5-pro"
        if not model_name.startswith("google-cloud:"):
            return f"google-cloud:{model_name}"
        return model_name

    # 2. Google Gemini via AI Studio (AIzaSy...)
    if gemini_key:
        os.environ["GOOGLE_API_KEY"] = gemini_key
        model_name = explicit_model or "gemini-2.5-flash"
        if not model_name.startswith("google:"):
            return f"google:{model_name}"
        return model_name

    # 3. Anthropic Claude
    if os.environ.get("ANTHROPIC_API_KEY"):
        model_name = explicit_model or "claude-3-5-sonnet-20241022"
        if not model_name.startswith("anthropic:"):
            return f"anthropic:{model_name}"
        return model_name

    # 4. OpenAI / Compatible
    if os.environ.get("OPENAI_API_KEY"):
        model_name = explicit_model or "gpt-4o"
        if not model_name.startswith("openai:"):
            return f"openai:{model_name}"
        return model_name

    # 5. Groq
    if os.environ.get("GROQ_API_KEY"):
        model_name = explicit_model or "llama-3.3-70b-versatile"
        if not model_name.startswith("groq:"):
            return f"groq:{model_name}"
        return model_name

    # 6. Local Ollama
    if os.environ.get("OLLAMA_MODEL"):
        return f"ollama:{os.environ['OLLAMA_MODEL']}"

    return None


def create_socratic_agent(model_override: Optional[str] = None) -> Agent[StudioAgentContext]:
    """Instantiate a PydanticAI Agent equipped with Studio MCP tools and Socratic Ontologist prompt."""
    model_spec = model_override or resolve_model_string()
    if not model_spec:
        raise ValueError("No LLM model configured. Please set GEMINI_API_KEY, GOOGLE_API_KEY, or other provider credentials.")

    model_arg: Any = model_spec
    if isinstance(model_spec, str) and model_spec.startswith("google-cloud:"):
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if gemini_key and gemini_key.startswith("AQ."):
            try:
                from google import genai
                from pydantic_ai.models.google import GoogleModel
                from pydantic_ai.providers.google_cloud import GoogleCloudProvider

                raw_model = model_spec.removeprefix("google-cloud:")
                project = os.environ.get("GOOGLE_CLOUD_PROJECT")
                if not project:
                    raise UserError(
                        "GOOGLE_CLOUD_PROJECT is not set: an Express key names "
                        "no project of its own"
                    )
                location = os.environ.get("GOOGLE_CLOUD_LOCATION") or ("global" if "3." in raw_model else "us-central1")
                http_options = genai.types.HttpOptions(
                    api_version="v1",
                    retry_options=genai.types.HttpRetryOptions(attempts=4, http_status_codes=[429, 500, 503, 504])
                )
                client = genai.Client(vertexai=True, project=project, location=location, api_key=gemini_key, http_options=http_options)
                provider = GoogleCloudProvider(client=client)
                model_arg = GoogleModel(raw_model, provider=provider)
            except Exception as e:
                logger.warning(f"Could not build preconfigured GoogleCloudProvider: {e}")

    agent = Agent(
        model_arg,
        deps_type=StudioAgentContext,
        system_prompt=SOCRATIC_ONTOLOGIST_SYSTEM_PROMPT,
    )

    @agent.tool
    def studio_init_package(
        ctx: RunContext[StudioAgentContext],
        package_path: str,
        title: str,
        domain: Optional[str] = None,
        author: str = "ontologist",
    ) -> Dict[str, Any]:
        """Initialize a new draft package with an official uniti.package.yaml manifest and schema skeleton.
        Use this when creating a new domain or community module from scratch before proposing classes.
        """
        res = ctx.deps.tools.init_package(package_path=package_path, title=title, domain=domain, author=author)
        ctx.deps.events.append({
            "type": "tool_call",
            "tool": "studio_init_package",
            "args": {"package_path": package_path, "title": title, "domain": domain},
            "result": res,
        })
        return res

    @agent.tool
    def studio_search_catalog(ctx: RunContext[StudioAgentContext], query: str, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search universal standardized semantic URIs and CURIEs (such as inv:quantity, proc:vendor, fin:amount)
        in the centralized semantic catalog. Use this to anchor domain concepts to universal vocabularies.
        """
        res = ctx.deps.tools.search_catalog(query=query, domain=domain)
        ctx.deps.events.append({
            "type": "tool_call",
            "tool": "studio_search_catalog",
            "args": {"query": query, "domain": domain},
            "result": f"Found {len(res)} matches" + (f": {', '.join(r['curie'] for r in res[:4])}" if res else ""),
        })
        return res

    @agent.tool
    def studio_inspect_package(ctx: RunContext[StudioAgentContext], package_path: Optional[str] = None) -> Dict[str, Any]:
        """Inspect the active LinkML schema structure in a specific package (classes, slots, archetypes, and invariants).
        Use this to check what is already modeled before proposing new classes or slots.
        """
        pkg = package_path or ctx.deps.package_path
        res = ctx.deps.tools.inspect_package(package_path=pkg)
        classes = list(res.get("classes", {}).keys()) if isinstance(res, dict) and "classes" in res else []
        ctx.deps.events.append({
            "type": "tool_call",
            "tool": "studio_inspect_package",
            "args": {"package_path": pkg},
            "result": f"{len(classes)} classes found" + (f" ({', '.join(classes)})" if classes else ""),
        })
        return res

    @agent.tool
    def studio_propose_patch(
        ctx: RunContext[StudioAgentContext],
        class_name: str,
        archetype: str,
        description: str,
        slots: Optional[List[str]] = None,
        slot_definitions: Optional[Dict[str, Any]] = None,
        package_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply a proposed new class or class modification into the draft LinkML schema.
        Must inherit from one of the 5 REA-H Archetypes: Agent, Resource, Commitment, Event, or Projection.
        Added slots should preferably have standardized slot_uris from the semantic catalog.
        """
        pkg = package_path or ctx.deps.package_path
        res = ctx.deps.tools.propose_patch(
            package_path=pkg,
            class_name=class_name,
            archetype=archetype,
            description=description,
            slots=slots,
            slot_definitions=slot_definitions,
        )
        ctx.deps.events.append({
            "type": "tool_call",
            "tool": "studio_propose_patch",
            "args": {"class_name": class_name, "archetype": archetype, "slots": slots or []},
            "result": res,
        })
        return res

    @agent.tool
    def studio_validate_linter(ctx: RunContext[StudioAgentContext], package_path: Optional[str] = None) -> Dict[str, Any]:
        """Run deterministic linter audits (LINT-001 through LINT-005) on the package schema to verify
        there are no archetype violations, unanchored numeric slots, state deadlocks, or unsafe invariants.
        """
        pkg = package_path or ctx.deps.package_path
        res = ctx.deps.tools.validate_linter(package_path=pkg)
        ctx.deps.events.append({
            "type": "tool_call",
            "tool": "studio_validate_linter",
            "args": {"package_path": pkg},
            "result": f"Linter {res.get('status')} ({res.get('error_count', 0)} errors, {res.get('warning_count', 0)} warnings)",
        })
        return res

    return agent


def convert_history_to_model_messages(history: List[Dict[str, str]]) -> List[ModelMessage]:
    """Convert JSON conversation history into PydanticAI ModelMessage objects."""
    messages: List[ModelMessage] = []
    for h in history:
        role = h.get("role")
        content = h.get("content", "")
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


async def stream_socratic_agent(
    prompt: str,
    package_path: str,
    history: Optional[List[Dict[str, str]]] = None,
    model_override: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Asynchronous generator streaming real-time tokens and tool events from PydanticAI agent.
    If no model is configured, yields a clear onboarding guide rather than a misleading fake simulation.
    """
    model_spec = model_override or resolve_model_string()

    if not model_spec:
        onboarding_msg = (
            "### 🤖 Uniti Socratic Ontologist (PydanticAI Framework)\n\n"
            "The intelligent agent framework is active and ready to operate in a **model-agnostic** mode "
            "using your preferred LLM provider (such as **Google Gemini** via Cloud/Vertex API).\n\n"
            "**Current Credential Status:**\n"
            "- No active API key was detected in the server environment.\n\n"
            "**Simple Setup Instructions:**\n"
            "1. Obtain a Gemini API Key from [Google AI Studio](https://aistudio.google.com/) or prepare Vertex AI credentials.\n"
            "2. Set the environment variable on the server or configure it via the Studio UI:\n"
            "   ```powershell\n"
            "   $env:GEMINI_API_KEY = \"AIzaSy...\"\n"
            "   ```\n"
            "   *(Or `GOOGLE_API_KEY` / `GOOGLE_CLOUD_PROJECT` for Vertex AI)*\n"
            "3. Refresh this page to begin interactive ontology modeling with the Socratic AI Ontologist.\n\n"
            "> [!NOTE]\n"
            "> Once configured, the Socratic AI can inspect active graphs, search the universal semantic catalog "
            "via MCP tools, and propose LinkML schema patches automatically."
        )
        for line in onboarding_msg.splitlines(keepends=True):
            yield line
            await asyncio.sleep(0.01)
        return

    tools = StudioTools()
    agent_ctx = StudioAgentContext(package_path=package_path, tools=tools)
    agent = create_socratic_agent(model_override=model_spec)

    model_messages = convert_history_to_model_messages(history or [])

    try:
        result = await agent.run(prompt, deps=agent_ctx, message_history=model_messages)
        full_text = str(result.output)

        # 1. Emit live MCP tool execution badges if any tools were executed
        tool_prefix = ""
        has_patch = False
        for ev in agent_ctx.events:
            t_name = ev.get("tool")
            args = ev.get("args", {})
            res = ev.get("result")
            if t_name == "studio_init_package":
                tool_prefix += f"\n> 📦 **[MCP Tool]** `studio_init_package(package_path='{args.get('package_path')}', title='{args.get('title')}')`  \n> ↳ Status: **INITIALIZED** (Manifest DRAFT created)\n\n"
                has_patch = True
            elif t_name == "studio_search_catalog":
                tool_prefix += f"\n> 🔍 **[MCP Tool]** `studio_search_catalog(query='{args.get('query')}')`  \n> ↳ {res}\n\n"
            elif t_name == "studio_inspect_package":
                tool_prefix += f"\n> 📋 **[MCP Tool]** `studio_inspect_package({args.get('package_path')})`  \n> ↳ {res}\n\n"
            elif t_name == "studio_propose_patch":
                p_status = res.get("status") if isinstance(res, dict) else "DONE"
                l_status = res.get("linter_status") if isinstance(res, dict) else "CHECKED"
                icon = "✅" if p_status == "PATCHED" and l_status == "PASS" else "⚠️"
                tool_prefix += f"\n> 🛠️ **[MCP Write Gate]** `studio_propose_patch({args.get('class_name')} : {args.get('archetype')})`  \n> ↳ {icon} **Status: {p_status}** | **Linter Gate: {l_status}**\n\n"
                if p_status == "PATCHED":
                    has_patch = True
            elif t_name == "studio_validate_linter":
                tool_prefix += f"\n> 🛡️ **[MCP Linter Gate]** `studio_validate_linter`  \n> ↳ {res}\n\n"

        if tool_prefix:
            tool_prefix += "---\n\n"
            for line in tool_prefix.splitlines(keepends=True):
                yield line
                await asyncio.sleep(0.005)

        # 2. Stream AI ontological response
        chunk_size = 40
        for i in range(0, len(full_text), chunk_size):
            yield full_text[i : i + chunk_size]
            await asyncio.sleep(0.01)

        # 3. If patch was applied, emit auto-refresh marker for frontend
        if has_patch:
            yield "\n\n<!-- REFRESH_STUDIO -->"

    except Exception as e:
        logger.exception("Error during agent execution")
        yield f"\n\n> [!WARNING]\n> An issue occurred while communicating with model (`{model_spec}`): {str(e)}\n"

import json
import os
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import asyncio
from components.agent.studio_server import StudioTools, ARCHETYPE_COLORS
from components.studio.agent import (
    resolve_model_string,
    stream_socratic_agent,
)
from components.linter.package_loader import PackageLoader

studio_tools = StudioTools()


def get_p2_kernel_stats() -> Dict[str, Any]:
    """Query live assertions and intents from PostgreSQL uniti_p2."""
    p2_dsn = os.environ.get(
        "UNITI_P2_KERNEL_DSN",
        os.environ.get("UNITI_KERNEL_DSN", "postgresql://uniti:uniti@localhost:5433/uniti_p2"),
    )
    try:
        import psycopg
        with psycopg.connect(p2_dsn, connect_timeout=1) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM assertion;")
                assertions = cur.fetchone()[0]
                cur.execute("SELECT count(*) FROM intent;")
                intents = cur.fetchone()[0]
                return {"online": True, "assertions": assertions, "intents": intents, "db": "uniti_p2"}
    except Exception as exc:
        return {"online": False, "error": str(exc), "assertions": 0, "intents": 0, "db": "uniti_p2"}


def list_available_packages() -> List[Dict[str, Any]]:
    pkgs = []
    packages_dir = ROOT / "packages"
    if packages_dir.exists():
        for manifest in sorted(packages_dir.glob("**/uniti.package.yaml")):
            try:
                import yaml
                data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
                rel_path = str(manifest.parent.relative_to(ROOT)).replace("\\", "/")
                is_community = "@community" in rel_path
                is_tenant = "@tenants" in rel_path
                is_core = "@uniti/core" in rel_path
                pkg_type = "Core Metamodel" if is_core else ("Community Module" if is_community else ("Tenant Application" if is_tenant else "Package"))
                pkgs.append({
                    "name": data.get("name", manifest.parent.name),
                    "title": data.get("title", ""),
                    "path": rel_path,
                    "version": data.get("version", "1.0.0"),
                    "sealed": data.get("status") == "SEALED",
                    "pkg_type": pkg_type,
                })
            except Exception:
                continue
    return pkgs


def get_default_package_path() -> str:
    packages = list_available_packages()
    if not packages:
        return "packages/@uniti/core"
    community_or_tenant = [p["path"] for p in packages if p["path"] != "packages/@uniti/core"]
    return community_or_tenant[0] if community_or_tenant else packages[0]["path"]


def get_studio_html(valid_at: str, as_of: str, active_pkg: Optional[str] = None) -> str:
    packages = list_available_packages()
    available_paths = [p["path"] for p in packages]
    if not active_pkg or active_pkg not in available_paths:
        active_pkg = get_default_package_path()

    pkg_options = "".join(
        f'<option value="{p["path"]}" {"selected" if p["path"] == active_pkg else ""}>{escape(p["name"])} [{p["pkg_type"]}]</option>'
        for p in packages
    )

    k_stats = get_p2_kernel_stats()
    if k_stats["online"]:
        kernel_badge = (
            f'<span class="badge badge-success" title="PostgreSQL port 5433 / uniti_p2">'
            f'🏛️ uniti_p2 ({k_stats["assertions"]} Assertions)</span>'
        )
    else:
        kernel_badge = (
            f'<span class="badge badge-warning" title="{escape(k_stats.get("error", "Offline"))}">'
            f'⚠️ uniti_p2 Offline</span>'
        )

    active_model = resolve_model_string() or "google-cloud:gemini-3.8-flash"
    if "gemini-2.5" in active_model:
        model_display = "Gemini 2.5 Flash"
    elif "gemini-3.8" in active_model:
        model_display = "Gemini 3.8 Flash"
    elif "claude" in active_model:
        model_display = "Claude 3.5 Sonnet"
    elif "gpt" in active_model:
        model_display = "GPT-4o"
    else:
        model_display = active_model.split(":")[-1]
    ai_badge = f'<span class="badge badge-purple" title="Active Socratic Engine: {escape(active_model)}">🤖 {escape(model_display)} (PydanticAI · Vertex)</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Uniti Studio &mdash; Socratic Ontologist Workbench (P2)</title>
  <script src="/static/cytoscape.min.js"></script>
  <style>
    :root {{
      --bg: #090d16;
      --panel-bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --primary: #3b82f6;
      --agent: #8b5cf6;
      --resource: #3b82f6;
      --commitment: #f59e0b;
      --event: #10b981;
      --projection: #06b6d4;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    header {{
      background: #060911;
      border-bottom: 1px solid var(--border);
      padding: 0.55rem 1.2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 52px;
      flex-shrink: 0;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      font-size: 0.95rem;
      letter-spacing: -0.01em;
    }}
    .brand-tag {{
      background: #1e293b;
      color: #38bdf8;
      font-size: 0.72rem;
      padding: 2px 7px;
      border-radius: 4px;
      border: 1px solid #38bdf844;
      font-weight: 600;
    }}
    .nav-links {{
      display: flex;
      align-items: center;
      gap: 1.1rem;
      font-size: 0.85rem;
    }}
    .nav-links a {{
      color: var(--muted);
      text-decoration: none;
      transition: color 0.15s;
    }}
    .nav-links a:hover, .nav-links a.active {{
      color: #fff;
      font-weight: 600;
    }}
    .pkg-selector {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}
    select, button, input, textarea {{
      background: var(--card-bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.4rem 0.7rem;
      font-size: 0.85rem;
    }}
    button {{
      background: #2563eb;
      color: #fff;
      border: none;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }}
    button:hover {{ background: #1d4ed8; }}
    button.btn-secondary {{ background: #334155; }}
    button.btn-secondary:hover {{ background: #475569; }}
    button.btn-success {{ background: #059669; }}
    button.btn-success:hover {{ background: #047857; }}
    button:disabled {{ background: #475569; cursor: not-allowed; opacity: 0.6; }}

    /* 3-Column Workbench Layout */
    .workbench-grid {{
      flex: 1;
      display: grid;
      grid-template-columns: 350px 1fr 380px;
      height: calc(100vh - 52px);
      overflow: hidden;
    }}
    .panel {{
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--panel-bg);
      overflow: hidden;
    }}
    .panel:last-child {{ border-right: none; }}
    .panel-header {{
      padding: 0.65rem 1rem;
      background: #090e1a;
      border-bottom: 1px solid var(--border);
      font-weight: 600;
      font-size: 0.85rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }}

    /* Column 1: Socratic AI Chat Panel */
    .chat-container {{
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: #090e1a;
    }}
    .chat-messages {{
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
    }}
    .chat-msg {{
      display: flex;
      flex-direction: column;
      max-width: 96%;
      font-size: 0.82rem;
      line-height: 1.45;
    }}
    .chat-msg.user {{
      align-self: flex-end;
      background: #1e3a8a;
      border: 1px solid #3b82f644;
      border-radius: 8px 8px 0 8px;
      padding: 8px 12px;
      color: #f0fdf4;
    }}
    .chat-msg.assistant {{
      align-self: flex-start;
      background: #1e293b;
      border: 1px solid var(--border);
      border-radius: 8px 8px 8px 0;
      padding: 10px 12px;
      color: #f8fafc;
    }}
    .msg-sender {{
      font-size: 0.7rem;
      font-weight: 700;
      color: #94a3b8;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .chat-suggestions {{
      padding: 0.5rem 0.8rem;
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      background: #060911;
      border-top: 1px solid var(--border);
    }}
    .sug-chip {{
      background: #1e293b;
      color: #38bdf8;
      border: 1px solid #334155;
      font-size: 0.72rem;
      padding: 3px 7px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .sug-chip:hover {{
      background: #334155;
      color: #fff;
    }}
    .chat-input-box {{
      padding: 0.8rem;
      background: #090e1a;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 6px;
    }}
    .chat-input-box textarea {{
      flex: 1;
      resize: none;
      height: 48px;
      font-family: inherit;
    }}

    /* Column 2: Graph Canvas */
    .canvas-container {{
      flex: 1 1 0;
      position: relative;
      background: #060911;
      min-height: 400px;
      height: 100%;
      overflow: hidden;
    }}
    #cy {{
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      width: 100%; height: 100%;
      display: block;
    }}
    .archetype-legend {{
      position: absolute;
      bottom: 12px; left: 12px;
      background: rgba(15, 23, 42, 0.92);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 0.72rem;
      display: flex;
      gap: 10px;
      z-index: 10;
      backdrop-filter: blur(4px);
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .dot {{
      width: 9px; height: 9px;
      border-radius: 50%;
    }}
    .canvas-controls {{
      position: absolute;
      top: 12px; right: 12px;
      display: flex;
      gap: 6px;
      z-index: 10;
    }}
    .canvas-btn {{
      background: rgba(30, 41, 59, 0.9);
      color: #fff;
      border: 1px solid var(--border);
      padding: 4px 8px;
      font-size: 0.75rem;
      border-radius: 4px;
      cursor: pointer;
    }}
    .canvas-btn:hover {{ background: #334155; }}

    /* Node Inspector */
    .node-inspector {{
      position: absolute;
      top: 12px; left: 12px;
      width: 300px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      font-size: 0.78rem;
      display: none;
      z-index: 15;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      backdrop-filter: blur(6px);
      max-height: 80%;
      overflow-y: auto;
    }}

    /* Column 3: Cards & Diagnostics */
    .right-content {{
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .studio-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.9rem;
    }}
    .card-title {{
      font-size: 0.85rem;
      font-weight: 700;
      margin-bottom: 0.6rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #38bdf8;
    }}
    .meta-row {{
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      padding: 3px 0;
      border-bottom: 1px solid #33415544;
    }}
    .meta-row:last-child {{ border-bottom: none; }}
    .meta-label {{ color: var(--muted); }}
    .meta-val {{ font-family: monospace; font-weight: 600; color: #f1f5f9; }}

    .badge {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 600;
    }}
    .badge-success {{ background: #059669; color: #fff; }}
    .badge-warning {{ background: #d97706; color: #fff; }}
    .badge-info {{ background: #0284c7; color: #fff; }}
    .badge-danger {{ background: #dc2626; color: #fff; }}
    .badge-purple {{ background: #7c3aed; color: #fff; }}

    /* Diagnostics list */
    .rule-item {{
      padding: 6px 8px;
      background: #090e1a;
      border-radius: 4px;
      margin-bottom: 6px;
      font-size: 0.78rem;
      border-left: 3px solid #334155;
    }}
    .rule-item.pass {{ border-left-color: #10b981; }}
    .rule-item.fail {{ border-left-color: #ef4444; }}
    .rule-header {{
      display: flex;
      justify-content: space-between;
      font-weight: 600;
      margin-bottom: 2px;
    }}
    .rule-desc {{ color: var(--muted); font-size: 0.74rem; }}

    /* Modal */
    .modal-overlay {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      z-index: 1000;
      display: none;
      align-items: center;
      justify-content: center;
    }}
    .modal-content {{
      background: var(--panel-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      width: 760px;
      max-width: 90vw;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 40px rgba(0,0,0,0.8);
    }}
    .modal-header {{
      padding: 0.75rem 1.2rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-weight: 700;
    }}
    .modal-body {{
      padding: 1.2rem;
      overflow-y: auto;
      flex: 1;
    }}
    .modal-footer {{
      padding: 0.75rem 1.2rem;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: flex-end;
      gap: 0.5rem;
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <header>
    <div class="brand">
      <span>Uniti Studio</span>
      <span class="brand-tag">Modular Metamodel Workbench (P2)</span>
    </div>

    <div class="pkg-selector">
      <span style="font-size:0.8rem;color:var(--muted)">Active Module:</span>
      <select id="pkgSelect" onchange="switchPackage(this.value)">
        {pkg_options}
      </select>
      <button class="btn-secondary" onclick="viewYamlSchema()" title="View raw LinkML YAML">📄 View LinkML</button>
      <button class="btn-success" onclick="sealPackage()" title="Seal package and register into PostgreSQL uniti_p2">🛡️ Seal to Kernel</button>
      <button onclick="refreshStudio()" title="Refresh graph and linter">🔄 Refresh</button>
    </div>

    <div class="nav-links">
      {ai_badge}
      {kernel_badge}
      <a href="/why" target="_blank" title="View bitemporal assertion ledger">🏛️ Kernel Ledger</a>
      <a href="/classes" target="_blank" title="View compiled dynamic forms">📋 Forms</a>
      <a href="/graph" target="_blank" title="Mermaid domain diagram">🗺️ Map</a>
      <a href="/" target="_blank" title="Prototype 2 dashboard">🏠 Home</a>
    </div>
  </header>

  <!-- MAIN WORKBENCH: 3 COLUMNS -->
  <div class="workbench-grid">

    <!-- COLUMN 1: Socratic AI Ontologist (PydanticAI · Gemini 3.8 Flash) -->
    <div class="panel">
      <div class="panel-header">
        <span>🤖 Socratic AI Ontologist</span>
        <span class="badge badge-purple" id="chatModelBadge">{escape(model_display)}</span>
      </div>
      <div class="chat-container">
        <div class="chat-messages" id="chatMessages">
          <div class="chat-msg assistant">
            <div class="msg-sender">🏛️ Socratic Ontologist · {escape(model_display)}</div>
            <div class="msg-body">
              Greetings! I am your <strong>UnitiOS Socratic Ontologist</strong>, powered by <em>PydanticAI</em> and <em>{escape(model_display)}</em>.
              <br><br>
              I can help you explore domain boundaries, align classes with universal <strong>REA-H Archetypes</strong> (<em>Agent</em>, <em>Resource</em>, <em>Commitment</em>, <em>Event</em>, <em>Projection</em>), search universal vocabularies, and propose LinkML schema patches.
              <br><br>
              What business domain or concept would you like to model?
            </div>
          </div>
        </div>

        <div class="chat-suggestions">
          <span class="sug-chip" onclick="quickPrompt('Propose a QualityInspection event archetype for inventory batches')">+ QualityInspection Event</span>
          <span class="sug-chip" onclick="quickPrompt('Explain when a concept belongs to the Event archetype rather than the Commitment archetype')">Event vs Commitment</span>
          <span class="sug-chip" onclick="quickPrompt('Audit our active package against UnitiOS bitemporal rules')">Audit Package Rules</span>
        </div>

        <div class="chat-input-box">
          <textarea id="chatInput" placeholder="Ask Socratic Ontologist (e.g. 'Add a Warehouse Location resource')..." onkeydown="handleChatKeyDown(event)"></textarea>
          <button id="sendChatBtn" onclick="sendChatMessage()" style="padding:0 1rem;">➤</button>
        </div>
      </div>
    </div>

    <!-- COLUMN 2: Interactive Knowledge Graph Canvas -->
    <div class="panel">
      <div class="panel-header">
        <span>🕸️ Ontological Knowledge Graph</span>
        <span style="font-size:0.75rem;color:var(--muted)" id="graphStats">Loading topology...</span>
      </div>
      <div class="canvas-container">
        <div class="archetype-legend">
          <div class="legend-item"><div class="dot" style="background:var(--agent)"></div>Agent</div>
          <div class="legend-item"><div class="dot" style="background:var(--resource)"></div>Resource</div>
          <div class="legend-item"><div class="dot" style="background:var(--commitment)"></div>Commitment</div>
          <div class="legend-item"><div class="dot" style="background:var(--event)"></div>Event</div>
          <div class="legend-item"><div class="dot" style="background:var(--projection)"></div>Projection</div>
          <div class="legend-item"><div class="dot" style="background:#64748B"></div>CoreClass</div>
        </div>
        <div class="canvas-controls">
          <button class="canvas-btn" onclick="zoomIn()" title="Zoom In">+</button>
          <button class="canvas-btn" onclick="zoomOut()" title="Zoom Out">&minus;</button>
          <button class="canvas-btn" onclick="fitGraph()" title="Fit to Screen">⛶ Fit</button>
          <button class="canvas-btn" onclick="toggleLayout()" id="layoutToggleBtn" title="Switch Layout">Hierarchy / Cose</button>
        </div>
        <div id="cy"></div>
        <div class="node-inspector" id="nodeInspector">
          <div style="font-weight:700;font-size:0.9rem;margin-bottom:4px;" id="inspTitle">Class Name</div>
          <div style="color:var(--muted);margin-bottom:6px;" id="inspDesc">Class Description</div>
          <div id="inspSlots"></div>
        </div>
      </div>
    </div>

    <!-- COLUMN 3: Real Engine Diagnostics & Verification -->
    <div class="panel">
      <div class="panel-header">
        <span>⚙️ Engine Verification &amp; Invariants</span>
        <span class="badge badge-info" id="statusBadge">Checking...</span>
      </div>
      <div class="right-content">

        <!-- Card 1: Package Specification -->
        <div class="studio-card">
          <div class="card-title">
            <span>📦 Module Specification</span>
            <span class="badge badge-success" id="pkgStatusBadge">ACTIVE</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Package Path</span>
            <span class="meta-val" id="pkgPathDisplay">{active_pkg}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Version</span>
            <span class="meta-val" id="pkgVersionDisplay">1.0.0</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Target Kernel</span>
            <span class="meta-val" style="color:#38bdf8">postgresql://localhost:5433/uniti_p2</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Last Synchronized</span>
            <span class="meta-val" id="pkgSyncDisplay">&mdash;</span>
          </div>
        </div>

        <!-- Card 2: Deterministic Linter (Real Engine) -->
        <div class="studio-card">
          <div class="card-title">
            <span>🛡️ Deterministic LinkML Linter</span>
            <span class="badge" id="lintBadge">Validating...</span>
          </div>
          <p style="font-size:0.75rem;color:var(--muted);margin-bottom:8px;">
            Deterministic structural verification against UnitiOS ontology rules (LINT-001 Archetype Lineage, unique identity, bitemporal slots).
          </p>
          <div id="linterRulesContainer">
            <div style="color:var(--muted);font-size:0.78rem;">Evaluating ontology rules (LINT-001 Archetype Lineage)...</div>
          </div>
        </div>

        <!-- Card 3: Deterministic Invariant Sandbox (Real Engine) -->
        <div class="studio-card">
          <div class="card-title">
            <span>🧪 CEL Invariant Sandbox</span>
            <span class="badge badge-info">Deterministic</span>
          </div>
          <p style="font-size:0.75rem;color:var(--muted);margin-bottom:8px;">
            Test invariant expression enforcement deterministically against synthetic claim values.
          </p>
          <div style="display:flex;flex-direction:column;gap:6px;">
            <div>
              <label style="font-size:0.74rem;color:var(--muted)">Rule / Expression:</label>
              <input type="text" id="invRuleExpr" value="self.quantity_moved &gt; 0" style="width:100%;font-family:monospace;font-size:0.78rem;">
            </div>
            <div style="display:flex;gap:6px;">
              <div style="flex:1;">
                <label style="font-size:0.74rem;color:var(--muted)">Test Value (quantity):</label>
                <input type="number" id="invTestValue" value="15.5" step="any" style="width:100%;font-size:0.8rem;">
              </div>
              <div style="align-self:flex-end;">
                <button onclick="testInvariant()" style="padding:0.4rem 0.9rem;font-size:0.8rem;">Test Rule</button>
              </div>
            </div>
            <div id="invResult" style="margin-top:6px;font-size:0.78rem;padding:6px;border-radius:4px;display:none;"></div>
          </div>
        </div>

      </div>
    </div>

  </div>

  <!-- MODAL: YAML Schema Viewer -->
  <div class="modal-overlay" id="yamlModal">
    <div class="modal-content">
      <div class="modal-header">
        <span id="yamlModalTitle">LinkML Schema Definition</span>
        <button class="btn-secondary" onclick="closeYamlModal()" style="padding:2px 8px;">&times;</button>
      </div>
      <div class="modal-body">
        <pre id="yamlContentPre" style="background:#090d16;padding:12px;border-radius:6px;overflow-x:auto;font-size:0.78rem;border:1px solid #334155;color:#f8fafc;font-family:monospace;line-height:1.4;"></pre>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="copyYamlText()">📋 Copy YAML</button>
        <button onclick="closeYamlModal()">Close</button>
      </div>
    </div>
  </div>

  <!-- CORE SCRIPT: 100% Valid JavaScript (Tested with node --check) -->
  <script>
    let currentPkg = "{active_pkg}";
    let cyInstance = null;
    let currentLayout = 'breadthfirst';
    let rawYamlCache = '';
    let chatHistory = [];
    let currentGraphData = {{ nodes: [], edges: [] }};

    function switchPackage(pkg) {{
      currentPkg = pkg;
      document.getElementById('pkgPathDisplay').innerText = pkg;
      refreshStudio();
    }}

    function toggleLayout() {{
      currentLayout = (currentLayout === 'breadthfirst') ? 'cose' : 'breadthfirst';
      document.getElementById('layoutToggleBtn').innerText = (currentLayout === 'breadthfirst') ? 'Switch to Force (Cose)' : 'Switch to Hierarchy';
      loadGraph();
    }}

    function showNodeInspectorById(id) {{
      const n = (currentGraphData.nodes || []).find(x => x.id === id);
      if (!n) return;
      const insp = document.getElementById('nodeInspector');
      if (!insp) return;
      insp.style.display = 'block';
      document.getElementById('inspTitle').innerHTML = n.label + ' <span class="badge" style="background:' + (n.color || '#64748B') + '">' + (n.archetype || 'Entity') + '</span>';
      document.getElementById('inspDesc').innerText = n.description || n.desc || 'No description provided in LinkML schema.';
      const slots = n.slots || [];
      const slotsHtml = slots.map(s => '<code style="background:#090e1a;padding:2px 5px;margin:2px;display:inline-block;border-radius:3px;border:1px solid #334155;">' + s + '</code>').join(' ');
      document.getElementById('inspSlots').innerHTML = '<strong>Declared Slots (' + slots.length + '):</strong><br>' + (slotsHtml || '<span style="color:var(--muted)">None</span>');
    }}

    function renderSvgFallback(nodes, edges) {{
      const container = document.getElementById('cy');
      if (!container) return;
      const w = container.clientWidth || 800;
      const h = container.clientHeight || 550;
      const cx = w / 2;
      const cy = h / 2;
      const radius = Math.min(w, h) * 0.38;

      const nodeMap = {{}};
      nodes.forEach((n, idx) => {{
        const angle = (idx / nodes.length) * 2 * Math.PI - Math.PI / 2;
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);
        nodeMap[n.id] = Object.assign({{}}, n, {{ x: x, y: y }});
      }});

      let svg = '<svg width="100%" height="100%" viewBox="0 0 ' + w + ' ' + h + '" style="background:#060911;">';
      svg += '<defs><marker id="arr" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748B"/></marker></defs>';

      edges.forEach(e => {{
        const s = nodeMap[e.source];
        const t = nodeMap[e.target];
        if (s && t) {{
          svg += '<line x1="' + s.x + '" y1="' + s.y + '" x2="' + t.x + '" y2="' + t.y + '" stroke="#475569" stroke-width="2" marker-end="url(#arr)" />';
        }}
      }});

      nodes.forEach(n => {{
        const pt = nodeMap[n.id];
        svg += '<g onclick="showNodeInspectorById(\\'' + n.id + '\\')" style="cursor:pointer;">';
        svg += '<circle cx="' + pt.x + '" cy="' + pt.y + '" r="28" fill="' + (pt.color || '#64748B') + '" stroke="#ffffff" stroke-width="2"/>';
        svg += '<text x="' + pt.x + '" y="' + (pt.y + 4) + '" fill="#ffffff" font-size="10px" font-weight="600" text-anchor="middle">' + n.label + '</text>';
        svg += '</g>';
      }});

      svg += '</svg>';
      container.innerHTML = svg;
    }}

    async function loadGraph(retries = 15) {{
      const stats = document.getElementById('graphStats');
      if (stats) stats.innerText = 'Loading ontology topology...';

      try {{
        const resp = await fetch('/api/studio/graph?pkg=' + encodeURIComponent(currentPkg));
        if (!resp.ok) {{
          if (stats) stats.innerHTML = '<span style="color:#ef4444">⚠️ Graph API Error: ' + resp.status + '</span>';
          return;
        }}
        const data = await resp.json();
        currentGraphData = data;
        const nodes = data.nodes || [];
        const edges = data.edges || [];

        if (stats) stats.innerText = nodes.length + ' classes, ' + edges.length + ' relations';

        if (typeof cytoscape === 'undefined') {{
          if (retries > 0) {{
            if (stats) stats.innerText = 'Initializing Cytoscape engine (' + retries + ')...';
            setTimeout(() => loadGraph(retries - 1), 150);
            return;
          }}
          if (stats) stats.innerHTML = nodes.length + ' classes (SVG Interactive Fallback)';
          renderSvgFallback(nodes, edges);
          return;
        }}

        const elements = [];

        nodes.forEach(n => {{
          elements.push({{
            data: {{
              id: n.id,
              label: n.label,
              color: n.color || '#64748B',
              archetype: n.archetype || 'Entity',
              desc: n.description || 'No description provided in LinkML schema.',
              slots: n.slots || []
            }}
          }});
        }});

        edges.forEach(e => {{
          elements.push({{
            data: {{
              source: e.source,
              target: e.target,
              label: e.label || '',
              type: e.type || ''
            }}
          }});
        }});

        if (cyInstance) {{
          try {{ cyInstance.destroy(); }} catch(e) {{}}
        }}

        const cyContainer = document.getElementById('cy');
        if (!cyContainer) return;

        const layoutConfig = (currentLayout === 'breadthfirst') ? {{
          name: 'breadthfirst',
          directed: true,
          roots: ['CoreClass'],
          padding: 30,
          spacingFactor: 1.25,
          animate: false
        }} : {{
          name: 'cose',
          padding: 35,
          animate: false,
          randomize: true,
          nodeRepulsion: function(node) {{ return 450000; }},
          idealEdgeLength: function(edge) {{ return 80; }}
        }};

        cyInstance = cytoscape({{
          container: cyContainer,
          elements: elements,
          style: [
            {{
              selector: 'node',
              style: {{
                'background-color': 'data(color)',
                'label': 'data(label)',
                'color': '#ffffff',
                'font-size': '11px',
                'font-weight': '600',
                'text-valign': 'center',
                'text-halign': 'center',
                'width': '68px',
                'height': '68px',
                'border-width': 2,
                'border-color': '#ffffff',
                'text-outline-width': 2,
                'text-outline-color': '#0f172a'
              }}
            }},
            {{
              selector: 'edge',
              style: {{
                'width': 2,
                'line-color': '#475569',
                'target-arrow-color': '#475569',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'label': 'data(label)',
                'font-size': '9px',
                'color': '#94a3b8',
                'text-rotation': 'autorotate'
              }}
            }},
            {{
              selector: 'edge[type = "inheritance"]',
              style: {{
                'line-style': 'solid',
                'line-color': '#60a5fa',
                'target-arrow-color': '#60a5fa',
                'width': 2.5
              }}
            }},
            {{
              selector: 'node:selected',
              style: {{
                'border-width': 4,
                'border-color': '#38bdf8'
              }}
            }}
          ],
          layout: layoutConfig
        }});

        cyInstance.ready(function() {{
          cyInstance.resize();
          cyInstance.fit(undefined, 35);
        }});

        setTimeout(() => {{
          if (cyInstance) {{
            cyInstance.resize();
            cyInstance.fit(undefined, 35);
          }}
        }}, 150);

        setTimeout(() => {{
          if (cyInstance) {{
            cyInstance.resize();
            cyInstance.fit(undefined, 35);
          }}
        }}, 500);

        cyInstance.on('tap', 'node', function(evt) {{
          const node = evt.target;
          const d = node.data();
          const insp = document.getElementById('nodeInspector');
          if (!insp) return;
          insp.style.display = 'block';
          document.getElementById('inspTitle').innerHTML = d.label + ' <span class="badge" style="background:' + d.color + '">' + d.archetype + '</span>';
          document.getElementById('inspDesc').innerText = d.desc || 'No description';
          const slotsHtml = (d.slots || []).map(s => '<code style="background:#090e1a;padding:2px 5px;margin:2px;display:inline-block;border-radius:3px;border:1px solid #334155;">' + s + '</code>').join(' ');
          document.getElementById('inspSlots').innerHTML = '<strong>Declared Slots (' + (d.slots || []).length + '):</strong><br>' + (slotsHtml || '<span style="color:var(--muted)">None</span>');
        }});

        cyInstance.on('tap', function(evt) {{
          if (evt.target === cyInstance) {{
            const insp = document.getElementById('nodeInspector');
            if (insp) insp.style.display = 'none';
          }}
        }});
      }} catch (err) {{
        console.error('loadGraph error:', err);
        if (stats) stats.innerHTML = '<span style="color:#ef4444">⚠️ ' + err.message + '</span>';
      }}
    }}

    function zoomIn() {{ if (cyInstance) cyInstance.zoom(cyInstance.zoom() * 1.2); }}
    function zoomOut() {{ if (cyInstance) cyInstance.zoom(cyInstance.zoom() * 0.8); }}
    function fitGraph() {{ if (cyInstance) {{ cyInstance.resize(); cyInstance.fit(undefined, 35); }} }}

    async function loadLinter() {{
      const container = document.getElementById('linterRulesContainer');
      const badge = document.getElementById('lintBadge');
      const statusBadge = document.getElementById('statusBadge');
      try {{
        const resp = await fetch('/api/studio/lint?pkg=' + encodeURIComponent(currentPkg));
        const data = await resp.json();
        const diags = data.diagnostics || [];
        const canSeal = data.can_seal;

        if (canSeal) {{
          badge.className = 'badge badge-success';
          badge.innerText = 'PASS (Valid LinkML)';
          statusBadge.className = 'badge badge-success';
          statusBadge.innerText = 'READY TO SEAL';
        }} else {{
          badge.className = 'badge badge-danger';
          badge.innerText = 'ERRORS DETECTED';
          statusBadge.className = 'badge badge-danger';
          statusBadge.innerText = 'LINTER BLOCKED';
        }}

        if (diags.length === 0) {{
          container.innerHTML = '<div class="rule-item pass"><div class="rule-header"><span style="color:#10b981">✓ All LinkML Invariants Met</span></div><div class="rule-desc">Archetype inheritance, unique identity, bitemporal slots, and closed ranges validated successfully.</div></div>';
        }} else {{
          let html = '';
          diags.forEach(d => {{
            const isErr = d.severity === 'ERROR';
            const cls = isErr ? 'fail' : 'pass';
            const icon = isErr ? '❌' : '⚠️';
            const color = isErr ? '#ef4444' : '#f59e0b';
            html += '<div class="rule-item ' + cls + '">';
            html += '  <div class="rule-header">';
            html += '    <span style="color:' + color + '">' + icon + ' ' + (d.rule || 'RULE') + '</span>';
            html += '    <span class="badge" style="background:#1e293b;border:1px solid #334155;color:' + color + '">' + d.severity + '</span>';
            html += '  </div>';
            html += '  <div class="rule-desc">' + (d.message || '') + '</div>';
            if (d.location) {{
              html += '  <div style="font-family:monospace;font-size:0.7rem;color:#64748b;margin-top:2px;">Target: ' + d.location + '</div>';
            }}
            html += '</div>';
          }});
          container.innerHTML = html;
        }}
      }} catch (err) {{
        container.innerHTML = '<div style="color:#ef4444;font-size:0.78rem;">Linter Error: ' + err.message + '</div>';
      }}
    }}

    async function testInvariant() {{
      const expr = document.getElementById('invRuleExpr').value.trim();
      const val = parseFloat(document.getElementById('invTestValue').value) || 0;
      const resDiv = document.getElementById('invResult');
      resDiv.style.display = 'block';
      resDiv.style.background = '#1e293b';
      resDiv.style.color = '#94a3b8';
      resDiv.innerText = 'Evaluating rule via Python AST...';

      try {{
        const resp = await fetch('/api/studio/test_invariant', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ expression: expr, value: val, rule_name: 'sandbox_check' }})
        }});
        const data = await resp.json();
        if (data.status === 'ALLOWED') {{
          resDiv.style.background = '#05966922';
          resDiv.style.color = '#34d399';
          resDiv.style.border = '1px solid #05966966';
          resDiv.innerHTML = '<strong>✓ ALLOWED</strong>: Invariant satisfied deterministically.';
        }} else {{
          resDiv.style.background = '#dc262622';
          resDiv.style.color = '#f87171';
          resDiv.style.border = '1px solid #dc262666';
          resDiv.innerHTML = '<strong>✗ DENIED</strong>: ' + (data.reason || 'Condition evaluated to False');
        }}
      }} catch (err) {{
        resDiv.style.background = '#dc262622';
        resDiv.style.color = '#f87171';
        resDiv.innerText = 'Execution error: ' + err.message;
      }}
    }}

    async function sealPackage() {{
      if (!confirm('Seal module "' + currentPkg + '" and register immutable ontology into PostgreSQL kernel (uniti_p2)?')) return;
      try {{
        const resp = await fetch('/api/studio/seal', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ package_path: currentPkg, version: '1.0.0', author: 'ontologist' }})
        }});
        const data = await resp.json();
        if (data.sealed) {{
          const urisCount = (data.minted_uris ? data.minted_uris.length : 0);
          const alertMsg = '✅ Package Successfully Sealed!\\nSHA-256: ' + data.sha256 + '\\n\\n🏛️ Registered in Kernel (uniti_p2): ' + urisCount + ' URIs minted.';
          alert(alertMsg);
          refreshStudio();
        }} else {{
          alert('❌ Cannot seal package: ' + (data.error || 'Linter verification failed'));
        }}
      }} catch (err) {{
        alert('Seal Error: ' + err.message);
      }}
    }}

    async function viewYamlSchema() {{
      const modal = document.getElementById('yamlModal');
      const title = document.getElementById('yamlModalTitle');
      const pre = document.getElementById('yamlContentPre');
      title.innerText = 'LinkML Schema &mdash; ' + currentPkg;
      pre.innerText = 'Fetching LinkML YAML...';
      modal.style.display = 'flex';

      try {{
        const resp = await fetch('/api/studio/raw_yaml?pkg=' + encodeURIComponent(currentPkg));
        const data = await resp.json();
        rawYamlCache = data.content || '';
        pre.innerText = rawYamlCache;
      }} catch (err) {{
        pre.innerText = '# Error loading schema YAML: ' + err.message;
      }}
    }}

    function closeYamlModal() {{
      document.getElementById('yamlModal').style.display = 'none';
    }}

    function copyYamlText() {{
      if (rawYamlCache) {{
        navigator.clipboard.writeText(rawYamlCache);
        alert('LinkML Schema YAML copied to clipboard!');
      }}
    }}

    /* ------------------------------------------------------------- */
    /* CHAT LOGIC (PydanticAI · Gemini 3.8 Streaming)               */
    /* ------------------------------------------------------------- */

    function quickPrompt(txt) {{
      const input = document.getElementById('chatInput');
      input.value = txt;
      sendChatMessage();
    }}

    function handleChatKeyDown(e) {{
      if (e.key === 'Enter' && !e.shiftKey) {{
        e.preventDefault();
        sendChatMessage();
      }}
    }}

    function appendMessage(role, initialText) {{
      const container = document.getElementById('chatMessages');
      const msgDiv = document.createElement('div');
      msgDiv.className = 'chat-msg ' + role;

      const senderDiv = document.createElement('div');
      senderDiv.className = 'msg-sender';
      senderDiv.innerHTML = (role === 'user') ? '👤 You' : ('🏛️ Socratic Ontologist · ' + (document.getElementById('chatModelBadge')?.innerText || 'AI'));

      const bodyDiv = document.createElement('div');
      bodyDiv.className = 'msg-body';
      bodyDiv.innerText = initialText;

      msgDiv.appendChild(senderDiv);
      msgDiv.appendChild(bodyDiv);
      container.appendChild(msgDiv);
      container.scrollTop = container.scrollHeight;
      return bodyDiv;
    }}

    function renderMarkdownToHtml(text) {{
      let cleanText = text.replace(/<!-- REFRESH_STUDIO -->/g, '');
      let html = cleanText
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      // Code blocks
      html = html.replace(/```([\\s\\S]*?)```/g, function(match, p1) {{
        return '<pre style="background:#090d16;padding:8px;border-radius:4px;overflow-x:auto;margin:6px 0;border:1px solid #334155;"><code>' + p1.trim() + '</code></pre>';
      }});

      // Bold & Italic & inline code
      html = html.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
      html = html.replace(/\\*(.*?)\\*/g, '<em>$1</em>');
      html = html.replace(/`([^`]+)`/g, '<code style="background:#090d16;color:#38bdf8;padding:1px 5px;border-radius:3px;border:1px solid #334155;font-size:0.82rem;">$1</code>');

      // Horizontal rules
      html = html.replace(/---/g, '<hr style="border:none;border-top:1px solid #334155;margin:8px 0;">');

      // MCP Callout Badges
      html = html.replace(/&gt; (.*?)(?=\\n|$)/g, '<div style="background:#0f172a;border-left:3px solid #38bdf8;padding:5px 9px;margin:3px 0;font-size:0.78rem;border-radius:0 4px 4px 0;color:#cbd5e1;">$1</div>');

      // Line breaks
      html = html.replace(/\\n/g, '<br>');
      return html;
    }}

    async function sendChatMessage() {{
      const input = document.getElementById('chatInput');
      const btn = document.getElementById('sendChatBtn');
      const text = input.value.trim();
      if (!text) return;

      appendMessage('user', text);
      input.value = '';
      input.disabled = true;
      btn.disabled = true;

      const assistantBody = appendMessage('assistant', 'Thinking with Gemini 3.8 Flash...');

      try {{
        const resp = await fetch('/api/studio/chat', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            message: text,
            package_path: currentPkg,
            history: chatHistory
          }})
        }});

        if (!resp.ok) {{
          assistantBody.innerHTML = '<span style="color:#ef4444">⚠️ Error communicating with Gemini 3.8: ' + resp.status + '</span>';
          return;
        }}

        const reader = resp.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullResponse = '';

        while (true) {{
          const {{ done, value }} = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, {{ stream: true }});
          fullResponse += chunk;
          assistantBody.innerHTML = renderMarkdownToHtml(fullResponse);
          const container = document.getElementById('chatMessages');
          container.scrollTop = container.scrollHeight;
        }}

        chatHistory.push({{ role: 'user', content: text }});
        chatHistory.push({{ role: 'assistant', content: fullResponse }});

        if (fullResponse.includes('<!-- REFRESH_STUDIO -->') || 
            fullResponse.toLowerCase().includes('patch applied') || 
            fullResponse.toLowerCase().includes('initialized') ||
            fullResponse.toLowerCase().includes('successfully added')) {{
          setTimeout(refreshStudio, 300);
        }}
      }} catch (err) {{
        assistantBody.innerHTML = '<span style="color:#ef4444">Connection Error: ' + err.message + '</span>';
      }} finally {{
        input.disabled = false;
        btn.disabled = false;
        input.focus();
      }}
    }}

    async function loadPackages(targetPkg = null) {{
      try {{
        const resp = await fetch('/api/studio/packages');
        if (!resp.ok) return;
        const pkgs = await resp.json();
        const sel = document.getElementById('pkgSelect');
        if (!sel || !pkgs || pkgs.length === 0) return;
        
        let selected = targetPkg || currentPkg;
        const found = pkgs.find(p => p.path === selected);
        if (!found) {{
          const nonCore = pkgs.find(p => p.path !== 'packages/@uniti/core');
          selected = nonCore ? nonCore.path : pkgs[0].path;
        }} else if (currentPkg === 'packages/@uniti/core') {{
          // If a new community or tenant module was created, auto-switch to it
          const nonCore = pkgs.find(p => p.path !== 'packages/@uniti/core');
          if (nonCore) selected = nonCore.path;
        }}

        sel.innerHTML = pkgs.map(p => 
          '<option value="' + p.path + '" ' + (p.path === selected ? 'selected' : '') + '>' + p.name + ' [' + p.pkg_type + ']</option>'
        ).join('');

        if (selected !== currentPkg) {{
          currentPkg = selected;
          const displayEl = document.getElementById('pkgPathDisplay');
          if (displayEl) displayEl.innerText = selected;
        }}
      }} catch (e) {{
        console.error('Failed to load packages:', e);
      }}
    }}

    async function refreshStudio() {{
      await loadPackages();
      loadGraph();
      loadLinter();
      const syncEl = document.getElementById('pkgSyncDisplay');
      if (syncEl) syncEl.innerText = new Date().toLocaleTimeString();
    }}

    function initStudio() {{
      refreshStudio();
    }}

    if (document.readyState === 'loading') {{
      document.addEventListener('DOMContentLoaded', initStudio);
    }} else {{
      initStudio();
    }}

    window.addEventListener('load', () => {{
      if (cyInstance) {{
        cyInstance.resize();
        cyInstance.fit(undefined, 35);
      }}
    }});

    window.addEventListener('resize', () => {{
      if (cyInstance) {{
        cyInstance.resize();
        cyInstance.fit(undefined, 35);
      }}
    }});
  </script>
</body>
</html>
"""


def _send_json(handler, obj: Any, status: int = 200) -> None:
    try:
        body = json.dumps(obj, default=str).encode("utf-8")
    except Exception as exc:
        body = json.dumps({"error": f"Serialization error: {exc}"}).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def handle_studio_api_get(handler, parts: List[str], query: str) -> bool:
    q = parse_qs(query)
    avail_paths = [p["path"] for p in list_available_packages()]
    pkg = q.get("pkg", [None])[0]
    if not pkg or pkg not in avail_paths:
        pkg = get_default_package_path()

    if parts == ["api", "studio", "packages"]:
        pkgs = list_available_packages()
        _send_json(handler, pkgs)
        return True

    if parts == ["api", "studio", "graph"]:
        graph = studio_tools.render_graph(pkg)
        _send_json(handler, graph)
        return True

    if parts == ["api", "studio", "lint"]:
        lint = studio_tools.validate_linter(pkg)
        _send_json(handler, lint)
        return True

    if parts == ["api", "studio", "raw_yaml"]:
        schema_file = studio_tools._resolve_schema_file(pkg)
        if schema_file.exists():
            _send_json(handler, {"content": schema_file.read_text(encoding="utf-8"), "path": str(schema_file)})
        else:
            _send_json(handler, {"content": "# File not found: " + str(schema_file), "path": str(schema_file)})
        return True

    if parts == ["api", "studio", "catalog"]:
        term = q.get("q", [""])[0]
        domain = q.get("domain", [None])[0]
        results = studio_tools.search_catalog(term, domain=domain)
        _send_json(handler, results)
        return True

    if parts == ["api", "studio", "model_status"]:
        active_model = resolve_model_string()
        _send_json(handler, {
            "configured": bool(active_model),
            "model": active_model or "google-cloud:gemini-3.8-flash",
            "framework": "PydanticAI",
        })
        return True

    return False


def handle_studio_api_post(handler, parts: List[str], body: bytes) -> bool:
    try:
        data = json.loads(body.decode("utf-8")) if body else {}
    except Exception:
        data = {}

    if parts == ["api", "studio", "config_model"]:
        model_choice = data.get("model", "gemini-3.8-flash")
        api_key = data.get("api_key", "")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["GOOGLE_API_KEY"] = api_key
        if model_choice:
            os.environ["STUDIO_MODEL"] = model_choice
        active_model = resolve_model_string()
        _send_json(handler, {"status": "OK", "model": active_model or model_choice})
        return True

    if parts == ["api", "studio", "chat"]:
        user_msg = data.get("message", "")
        avail_paths = [p["path"] for p in list_available_packages()]
        pkg = data.get("package_path")
        if not pkg or pkg not in avail_paths:
            pkg = get_default_package_path()
        history = data.get("history", [])

        handler.send_response(200)
        handler.send_header("Content-Type", "text/plain; charset=utf-8")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.close_connection = True

        async def _stream_reply():
            async for chunk in stream_socratic_agent(user_msg, pkg, history=history):
                handler.wfile.write(chunk.encode("utf-8"))
                handler.wfile.flush()

        try:
            asyncio.run(_stream_reply())
        except Exception as e:
            try:
                handler.wfile.write(f"\n\n[Chat Streaming Error: {e}]".encode("utf-8"))
                handler.wfile.flush()
            except Exception:
                pass
        return True

    if parts == ["api", "studio", "init_package"]:
        pkg = data.get("package_path", "")
        title = data.get("title", "")
        domain = data.get("domain")
        author = data.get("author", "ontologist")
        res = studio_tools.init_package(package_path=pkg, title=title, domain=domain, author=author)
        _send_json(handler, res)
        return True

    if parts == ["api", "studio", "patch"]:
        pkg = data.get("package_path", "")
        class_name = data.get("class_name", "")
        archetype = data.get("archetype", "Resource")
        desc = data.get("description", "")
        slots = data.get("slots", [])
        slot_defs = data.get("slot_definitions")
        res = studio_tools.propose_patch(
            package_path=pkg,
            class_name=class_name,
            archetype=archetype,
            description=desc,
            slots=slots,
            slot_definitions=slot_defs,
        )
        _send_json(handler, res)
        return True

    if parts == ["api", "studio", "seal"]:
        pkg = data.get("package_path", "")
        version = data.get("version", "1.0.0")
        author = data.get("author", "ontologist")
        res = studio_tools.seal_package(pkg, version, author=author)
        _send_json(handler, res)
        return True

    if parts == ["api", "studio", "test_invariant"]:
        expr_str = data.get("expression", "self.quantity_moved > 0")
        val = data.get("value", 0.0)
        rule_name = data.get("rule_name", "sandbox_check")
        denied = False
        reason = ""

        if expr_str:
            try:
                import ast
                from components.linter.engine import SafeASTValidator
                tree = ast.parse(expr_str, mode="eval")
                validator = SafeASTValidator()
                validator.visit(tree)
                if validator.errors:
                    denied = True
                    reason = f"Unsafe AST: {'; '.join(validator.errors)}"
                else:
                    class SafeSelf:
                        def __init__(self, **kw):
                            self.__dict__.update(kw)
                    self_obj = SafeSelf(value=val, quantity=val, quantity_moved=val, produced_weight_kg=val, output_length_meters=val)
                    compiled = compile(tree, "<invariant>", "eval")
                    passed = bool(eval(compiled, {"__builtins__": {}}, {"self": self_obj}))
                    if not passed:
                        denied = True
                        reason = f"Condition evaluated to False for value {val}"
            except Exception as e:
                denied = True
                reason = f"Evaluation error: {e}"
        else:
            if val <= 0:
                denied = True
                reason = f"Value {val} is not > 0"

        if denied:
            _send_json(handler, {"status": "DENIED", "rule_name": rule_name, "reason": reason})
        else:
            _send_json(handler, {"status": "APPROVED", "rule_name": rule_name, "message": "Invariant passed"})
        return True

    return False

// The map. A module is a graph, so the page that makes one is a graph.
//
// It is looked at two ways, one button apart. "What's in it": a box is a kind
// of thing and a line is a field that points from one kind at another. What
// this module declares is drawn solid; what it builds on is drawn dashed,
// because a pinned version is sealed and cannot be changed from here — you
// change it by sealing a new version of that module. "How the numbers are
// worked out": a box is a field, inside the kind it belongs to, and a line
// runs from what is recorded through each rule to what it comes to — with one
// business example's numbers written on it, beside what the example expects.
//
// While the agent builds, the map is where its work shows: what it added or
// changed is marked on the boxes and the fields as it happens, and the same
// marks can be put back afterwards for any one of its answers, or for
// everything a seal would change.
//
// Every gesture is one of the closed steps and nothing else. Dragging from the
// dot on top of a box onto another box is `add_slot` with that kind as its
// range, then `attach`. Moving a box is not a step at all: where a box sits
// is a fact about this screen, never about the module, so it is never written
// to the file — only remembered by this browser, for this module.
//
// The drawing is React Flow; what is a box, what is a line, what each is
// called and where it sits are worked out in `studioMap.ts`.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background, BackgroundVariant, Controls, Handle, MarkerType, MiniMap, Panel,
  Position, ReactFlow, ReactFlowProvider, useNodesState, useReactFlow, useStore,
} from "@xyflow/react";
import type { Connection, Edge, Node, NodeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { DraftState } from "./api";
import {
  BOX, CELL, CHANGE_SAID, arrange, arrangeWorkings, cellHeight, daySaid, firstSentence, heightOf,
  lineage, momentsOf, neighbours, roomFor, spoken, walkThrough, workingsOf,
} from "./studioMap";
import type {
  Cell, ChangeHow, Check, Group, MapEdge, MapNode, Marks, Place, Rect, Shown,
} from "./studioMap";

type KindData = {
  node: MapNode;
  chosen: boolean;
  dim: boolean;
  open: boolean;
  linkable: boolean;
  onOpen: (name: string) => void;
  marks: Marks | null;
};
type KindNode = Node<KindData, "kind">;

export type Layer = "things" | "numbers";

// ---- what this browser remembers ------------------------------------------------

const PLACES = "uniti.studio.places.";
const LAYER = "uniti.studio.layer";

function recalled(module: string): Record<string, Place> {
  try {
    const raw = window.localStorage.getItem(PLACES + module);
    return raw ? JSON.parse(raw) as Record<string, Place> : {};
  } catch {
    return {};
  }
}

function remember(module: string, places: Record<string, Place>) {
  try {
    if (Object.keys(places).length === 0) window.localStorage.removeItem(PLACES + module);
    else window.localStorage.setItem(PLACES + module, JSON.stringify(places));
  } catch {
    // A browser that keeps nothing still draws the map; it just forgets.
  }
}

function recalledLayer(): Layer {
  try {
    return window.localStorage.getItem(LAYER) === "numbers" ? "numbers" : "things";
  } catch {
    return "things";
  }
}

function rememberLayer(layer: Layer) {
  try {
    window.localStorage.setItem(LAYER, layer);
  } catch {
    // As above: forgetting which way the map was looked at costs one click.
  }
}

// ---- marks shared by both ways of looking -----------------------------------------

const CHECK_MARK: Record<Check["state"], string> = {
  checked: "✓", failing: "✗", unchecked: "?", unrun: "…",
};

const CHECK_WORD: Record<Check["state"], string> = {
  checked: "checked", failing: "wrong", unchecked: "not checked", unrun: "not run",
};

export function CheckMark({ check, words = false }: { check: Check; words?: boolean }) {
  return (
    <span className={`check-mark check-${check.state}${words ? " check-words" : ""}`}
      title={check.text} aria-label={check.text}>
      {CHECK_MARK[check.state]}{words && <> {CHECK_WORD[check.state]}</>}
    </span>
  );
}

/** "new" or "changed", beside what is. */
export function ChangeTag({ how }: { how: ChangeHow }) {
  return <span className={`change-tag change-${how}`}>{CHANGE_SAID[how]}</span>;
}

/** What the map is marking, and how to stop: changes as the agent makes them,
 *  those of one of its answers, or everything a seal would change. */
export interface Showing {
  marks: Marks;
  title: string;
  said: string;
  live: boolean;
  onStop: (() => void) | null;
}

function ShowingLine({ showing }: { showing: Showing }) {
  return (
    <div className={`map-changes${showing.live ? " map-changes-live" : ""}`} role="status">
      {showing.live && <span className="spinner" aria-hidden="true" />}
      <p>
        <strong>{showing.title}</strong>
        <span className="map-changes-said">{showing.said}</span>
      </p>
      {showing.onStop && (
        <button className="button button-small" onClick={showing.onStop}>Stop showing</button>
      )}
    </div>
  );
}

/** How far down the drawing has to start: below the panel over its top left,
 *  whose height depends on what it holds and how its words wrap here. */
function roomAbove(lead: HTMLElement | null, otherwise: number) {
  const frame = lead?.closest(".react-flow");
  return lead && frame
    ? lead.getBoundingClientRect().bottom - frame.getBoundingClientRect().top + 20
    : otherwise;
}

function LayerSwitch({ layer, onLayer }: { layer: Layer; onLayer: (next: Layer) => void }) {
  const ways: [Layer, string][] = [["things", "What's in it"], ["numbers", "How the numbers are worked out"]];
  return (
    <div className="layer-switch" role="group" aria-label="What the map shows">
      {ways.map(([key, label]) => (
        <button key={key} className={`layer${layer === key ? " layer-on" : ""}`}
          aria-pressed={layer === key} onClick={() => onLayer(key)}>{label}</button>
      ))}
    </div>
  );
}

/** How the whole map is fitted: room left at the top for the panels drawn
 *  over it, and at the bottom for the zoom controls. */
const FIT = {
  maxZoom: 1.1,
  padding: { top: "112px", bottom: "40px", left: "32px", right: "32px" },
} as const;

/** Where the numbers are seen from: all of them, as large as fits up to the
 *  usual limit, starting just below the panel drawn over their top left —
 *  whose height depends on how its words wrap on this screen. Worked out
 *  here from the layout, which is already known, rather than measured. */
function viewOf(rects: Rect[], width: number, height: number, top: number) {
  const left = Math.min(...rects.map((r) => r.x));
  const upper = Math.min(...rects.map((r) => r.y));
  const wide = Math.max(...rects.map((r) => r.x + r.width)) - left;
  const tall = Math.max(...rects.map((r) => r.y + r.height)) - upper;
  const side = 32;
  const bottom = 40;
  const zoom = Math.max(0.2, Math.min(FIT.maxZoom,
    (width - 2 * side) / wide, (height - top - bottom) / tall));
  return {
    x: side + Math.max(0, (width - 2 * side - wide * zoom) / 2) - left * zoom,
    y: top - upper * zoom,
    zoom,
  };
}

// ---- the canvas ---------------------------------------------------------------

interface CanvasProps {
  module: string;
  draft: DraftState;
  nodes: MapNode[];
  edges: MapEdge[];
  chosen: string | null;
  onChoose: (name: string | null) => void;
  onConnect: (from: string, to: string) => void;
  busy: boolean;
  /** What changed, when the map is showing it. */
  showing: Showing | null;
  /** A kind somebody asked to be shown, from elsewhere on the page; `n` grows
   *  with every ask, so asking twice brings it into view twice. */
  focus: { name: string; n: number } | null;
}

export function MapCanvas(props: CanvasProps) {
  const [layer, setLayer] = useState<Layer>(recalledLayer);
  const pick = (next: Layer) => { setLayer(next); rememberLayer(next); };
  return (
    <div className="map">
      {/* One drawing per way of looking, each fitted when it is shown. */}
      <ReactFlowProvider key={layer}>
        {layer === "numbers"
          ? <Numbers {...props} layer={layer} onLayer={pick} />
          : <Things {...props} layer={layer} onLayer={pick} />}
      </ReactFlowProvider>
    </div>
  );
}

type WithLayer = CanvasProps & { layer: Layer; onLayer: (next: Layer) => void };

// ==== what's in it ===================================================================

function KindBox({ data }: NodeProps<KindNode>) {
  const { node, chosen, dim, open, linkable, onOpen, marks } = data;
  const shown = open ? node.fields : node.fields.slice(0, BOX.shown);
  const rest = node.fields.length - shown.length;
  const change = marks?.kinds.get(node.name) ?? null;
  const fieldChange = (field: string) => marks?.fields.get(`${node.name}.${field}`) ?? null;
  const hiddenChanged = node.fields.slice(shown.length).filter((f) => fieldChange(f.name)).length;
  return (
    <div className={[
      "kind",
      node.own ? "kind-own" : "kind-theirs",
      chosen ? "kind-on" : "",
      dim ? "kind-dim" : "",
      node.questions ? "kind-asks" : "",
      change ? `kind-${change}` : "",
      marks?.fresh.has(node.name) ? "kind-fresh" : "",
    ].filter(Boolean).join(" ")} style={{ width: BOX.width }}>
      {/* Lines land on the bottom edge and leave from the top: what a kind
          points at sits above it. */}
      <Handle type="target" position={Position.Bottom} className="kind-in"
        isConnectableStart={false} />
      <Handle type="source" position={Position.Top}
        className={`kind-out${linkable ? "" : " kind-out-off"}`}
        isConnectable={linkable}
        title={linkable ? "Drag onto another box to say this points at it" : undefined} />

      <header className="kind-head">
        <span className="kind-name" title={node.name}>{node.label}</span>
        {change && <ChangeTag how={change} />}
        {node.questions > 0 && (
          <span className="kind-questions"
            title={`${node.questions} open ${node.questions === 1 ? "question" : "questions"}`}>
            {node.questions}
          </span>
        )}
      </header>
      {(node.fills.length > 0 || node.module) && (
        <p className="kind-sub">
          {node.fills.map((role) => <span key={role} className="kind-role">{role}</span>)}
          {node.module && (
            <span className="kind-from" title={node.module}>from {node.module}</span>
          )}
        </p>
      )}
      <ul className="kind-fields">
        {shown.map((field) => {
          const how = fieldChange(field.name);
          return (
          <li key={field.name} className={[
            field.asks ? "kind-field-asks" : "",
            how ? `field-${how}` : "",
            marks?.fresh.has(`${node.name}.${field.name}`) ? "field-fresh" : "",
          ].filter(Boolean).join(" ")}
            title={[field.name, field.check?.text, how && CHANGE_SAID[how]]
              .filter(Boolean).join(": ")}>
            <span className="kind-field">{field.label}</span>
            {field.mark ? (
              <span className="kind-marks">
                <span className={`kind-mark kind-mark-${field.mark.kind}`}>{field.mark.text}</span>
                {field.check && <CheckMark check={field.check} />}
              </span>
            ) : (
              <span className={field.points ? "kind-points" : "kind-holds"}>
                {field.points ? `→ ${field.holds}` : field.holds}
              </span>
            )}
          </li>
          );
        })}
        {node.fields.length === 0 && <li className="kind-empty">nothing said about it yet</li>}
        {(rest > 0 || (open && node.fields.length > BOX.shown)) && (
          <li>
            <button className="kind-more nodrag" onClick={(e) => {
              e.stopPropagation();
              onOpen(node.name);
            }}>
              {open ? "show fewer"
                : `and ${rest} more${hiddenChanged ? ` (${hiddenChanged} changed)` : ""}`}
            </button>
          </li>
        )}
      </ul>
    </div>
  );
}

const KIND_TYPES = { kind: KindBox };

function Finder({ nodes, onChoose }: { nodes: MapNode[]; onChoose: (name: string) => void }) {
  const flow = useReactFlow();
  const [text, setText] = useState("");
  const go = (value: string) => {
    const wanted = value.trim().toLowerCase();
    if (!wanted) return;
    const hit = nodes.find((n) => n.label.toLowerCase() === wanted || n.name.toLowerCase() === wanted)
      ?? nodes.find((n) => n.label.toLowerCase().includes(wanted)
        || n.name.toLowerCase().includes(wanted)
        || n.fields.some((f) => f.label.toLowerCase().includes(wanted)));
    if (!hit) return;
    onChoose(hit.name);
    void flow.fitView({ nodes: [{ id: hit.name }], duration: 400, maxZoom: 1.2, padding: 0.6 });
  };
  return (
    <form className="map-find" role="search" onSubmit={(e) => { e.preventDefault(); go(text); }}>
      <input value={text} list="map-kinds" placeholder="Find a kind of thing or a field…"
        aria-label="Find on the map" onChange={(e) => setText(e.target.value)} />
      <datalist id="map-kinds">
        {nodes.map((n) => <option key={n.name} value={n.label} />)}
      </datalist>
    </form>
  );
}

function Things(
  {
    module, nodes, edges, chosen, onChoose, onConnect, busy, layer, onLayer, showing, focus,
  }: WithLayer,
) {
  const flow = useReactFlow();
  const lead = useRef<HTMLDivElement>(null);
  const marks = showing?.marks ?? null;
  const width = useStore((state) => state.width);
  const height = useStore((state) => state.height);
  const [open, setOpen] = useState<Set<string>>(new Set());
  const [moved, setMoved] = useState<Record<string, Place>>(() => recalled(module));
  const [legend, setLegend] = useState(false);
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<KindNode>([]);

  useEffect(() => { setMoved(recalled(module)); setOpen(new Set()); }, [module]);

  const shape = `${nodes.map((n) => n.name).join("|")}#${edges.map((e) => e.id).join("|")}`;
  const openKey = [...open].sort().join("|");

  // Where every box goes: worked out again only when the set of boxes, their
  // lines or which ones are opened changes — never because a field was
  // reworded — so reading the map is never interrupted by it rearranging.
  const places = useMemo(
    () => arrange(nodes, edges, open, moved),
    [shape, openKey, moved],
  );

  // Everything, below whatever the panel at the top left holds just now.
  // Worked out from where the boxes go and how tall each is drawn, as the
  // numbers are: React Flow's own fit keeps only roughly to a top margin.
  const fitAll = (duration: number) => {
    const rects = nodes.map((n) => ({
      ...(places[n.name] ?? { x: 0, y: 0 }),
      width: BOX.width, height: heightOf(n, open.has(n.name)),
    }));
    if (rects.length === 0 || width === 0 || height === 0) return;
    void flow.setViewport(viewOf(rects, width, height, roomAbove(lead.current, 112)), { duration });
  };

  const near = useMemo(() => (chosen ? neighbours(edges, chosen) : null), [edges, chosen]);

  const toggle = useCallback((name: string) => {
    setOpen((held) => {
      const next = new Set(held);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  }, []);

  useEffect(() => {
    // What React Flow measured about a box is kept: a box handed over again
    // without its size would be one it has to measure all over again.
    setFlowNodes((held) => {
      const was = new Map(held.map((n) => [n.id, n]));
      return nodes.map((node) => ({
        ...was.get(node.name),
        id: node.name,
        type: "kind",
        position: places[node.name] ?? { x: 0, y: 0 },
        selected: node.name === chosen,
        data: {
          node,
          chosen: node.name === chosen,
          dim: near !== null && !near.has(node.name),
          open: open.has(node.name),
          linkable: node.own && !busy,
          onOpen: toggle,
          marks,
        },
      }));
    });
  }, [nodes, places, chosen, near, open, busy, marks]);

  // Seen whole again when the panel over the top left grows or shrinks, so
  // what it says never covers a box.
  const marking = useRef(showing !== null);
  useEffect(() => {
    if (marking.current === (showing !== null)) return;
    marking.current = showing !== null;
    const id = window.setTimeout(() => fitAll(250), 60);
    return () => window.clearTimeout(id);
  }, [showing !== null]);

  // Brought into view when somebody elsewhere on the page points at it.
  useEffect(() => {
    if (!focus || !nodes.some((n) => n.name === focus.name)) return;
    const id = window.setTimeout(() => {
      void flow.fitView({ nodes: [{ id: focus.name }], duration: 400, maxZoom: 1.1, padding: 0.5 });
    }, 60);
    return () => window.clearTimeout(id);
  }, [focus?.n]);

  // Fit when the set of boxes changes, not on every reload: somebody who
  // panned somewhere is reading something there. The first fit is React
  // Flow's own (`fitView` below), which waits until every box is measured;
  // a box added later is fitted a moment after it is drawn.
  const seen = useRef<string | null>(null);
  useEffect(() => {
    const names = nodes.map((n) => n.name).join(" ");
    if (seen.current === null || seen.current === names) { seen.current = names; return; }
    seen.current = names;
    const id = window.setTimeout(() => fitAll(250), 250);
    return () => window.clearTimeout(id);
  }, [shape]);

  const flowEdges: Edge[] = useMemo(() => edges.map((edge) => {
    const lit = chosen !== null && (edge.from === chosen || edge.to === chosen);
    const dim = chosen !== null && !lit;
    return {
      id: edge.id,
      source: edge.from,
      target: edge.to,
      type: "smoothstep",
      label: edge.label ?? undefined,
      className: [
        "line", edge.kind === "reads" ? "line-reads" : edge.own ? "line-own" : "line-theirs",
        lit ? "line-lit" : "", dim ? "line-dim" : "",
      ].filter(Boolean).join(" "),
      markerEnd: {
        type: MarkerType.ArrowClosed, width: 18, height: 18,
        color: lit || edge.kind === "reads" ? "var(--focus)"
          : edge.own ? "var(--ink-soft)" : "var(--later)",
      },
      labelBgPadding: [6, 3] as [number, number],
      labelBgBorderRadius: 4,
      animated: lit,
      selectable: false,
      focusable: false,
    };
  }), [edges, chosen]);

  const tidy = () => {
    remember(module, {});
    setMoved({});
    window.setTimeout(() => fitAll(300), 30);
  };

  return (
    <ReactFlow<KindNode, Edge>
      nodes={flowNodes}
      edges={flowEdges}
      nodeTypes={KIND_TYPES}
      onNodesChange={onNodesChange}
      onNodeClick={(_, node) => onChoose(node.id)}
      onPaneClick={() => onChoose(null)}
      onNodeDragStop={(_, node) => {
        const next = { ...moved, [node.id]: { x: Math.round(node.position.x), y: Math.round(node.position.y) } };
        remember(module, next);
        setMoved(next);
      }}
      onConnect={(c: Connection) => {
        if (c.source && c.target && c.source !== c.target) onConnect(c.source, c.target);
      }}
      isValidConnection={(c) => c.source !== c.target}
      connectionRadius={48}
      nodesConnectable={!busy}
      fitView
      fitViewOptions={FIT}
      minZoom={0.2}
      maxZoom={2}
      colorMode="system"
      proOptions={{ hideAttribution: true }}
      deleteKeyCode={null}
      selectionKeyCode={null}
      multiSelectionKeyCode={null}
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} />
      <Controls showInteractive={false} position="bottom-left" />
      <MiniMap pannable zoomable position="bottom-right" className="map-mini"
        nodeClassName={(n) => ((n as KindNode).data.node.own ? "mini-own" : "mini-theirs")} />
      <Panel position="top-left" className="map-panel">
        <div className="map-lead" ref={lead}>
          <LayerSwitch layer={layer} onLayer={onLayer} />
          <Finder nodes={nodes} onChoose={onChoose} />
          {showing && <ShowingLine showing={showing} />}
        </div>
      </Panel>
      <Panel position="top-right" className="map-panel map-corner">
        <div className="map-actions">
          <button className="button button-small" onClick={tidy}
            title="Put every box back where the map would put it">Tidy up</button>
          <button className="button button-small" onClick={() => fitAll(300)}>
            Show all
          </button>
          <button className={`button button-small${legend ? " button-on" : ""}`}
            aria-expanded={legend} onClick={() => setLegend(!legend)}>How to read this</button>
        </div>
        {legend && <ThingsLegend changes={showing !== null} />}
      </Panel>
    </ReactFlow>
  );
}

const SAMPLE_CHECKS: Check[] = [
  { state: "checked", text: "checked by an example" },
  { state: "failing", text: "an example says it should come out differently" },
  { state: "unchecked", text: "no example checks it yet" },
];

function ChecksRow() {
  return (
    <p className="legend-row">
      <span className="legend-checks">
        {SAMPLE_CHECKS.map((c) => <CheckMark key={c.state} check={c} />)}
      </span>
      <span>
        A worked-out number an example checks and gets right; one an example
        says should come out differently; one no example checks yet
      </span>
    </p>
  );
}

function ChangesRow() {
  return (
    <p className="legend-row">
      <span className="legend-checks"><ChangeTag how="added" /><ChangeTag how="changed" /></span>
      <span>What the agent added or changed, while the map is showing it</span>
    </p>
  );
}

function ThingsLegend({ changes }: { changes: boolean }) {
  return (
    <div className="map-legend">
      <p className="legend-row"><span className="legend-box legend-own" /><span>A kind of thing this module defines</span></p>
      <p className="legend-row"><span className="legend-box legend-theirs" /><span>A kind of thing it builds on, from another module; it cannot be changed here</span></p>
      <p className="legend-row"><span className="legend-arrow">↑</span><span>Points at: each one refers to one of those</span></p>
      <p className="legend-row"><span className="legend-arrow legend-reads">↑</span><span>Adds up: numbers here are worked out from records of that kind</span></p>
      <p className="legend-row"><span><span className="kind-mark kind-mark-key">key</span></span><span>What tells one apart from another</span></p>
      <p className="legend-row"><span><span className="kind-mark kind-mark-sum">sum</span></span><span>Worked out by a rule, never typed in: a sum, a formula, or a value looked up elsewhere</span></p>
      <ChecksRow />
      {changes && <ChangesRow />}
      <p className="legend-row"><span><span className="kind-questions">2</span></span><span>Questions still open about it</span></p>
      <p className="legend-hint">
        Click a box to see everything about it. Drag a box to move it. Drag the
        dot on top of a box onto another box to say it points at that one.
        Scroll or pinch to zoom. "How the numbers are worked out" shows where
        each number comes from.
      </p>
    </div>
  );
}

// ==== how the numbers are worked out ======================================================

type CellData = {
  cell: Cell; shown: Shown | null; lines: number; lit: boolean; dim: boolean;
  change: ChangeHow | null; fresh: boolean;
};
type GroupData = { group: Group; chosen: boolean; dim: boolean; change: ChangeHow | null };
type CellNode = Node<CellData, "cell">;
type GroupNode = Node<GroupData, "kindGroup">;
type NumberNode = CellNode | GroupNode;

const ROLE_SAID: Record<Cell["role"], string> = {
  key: "one row each", recorded: "recorded", sum: "adds up", lookup: "looked up", formula: "formula",
};

function CellBox({ data }: NodeProps<CellNode>) {
  const { cell, shown, lines, lit, dim, change, fresh } = data;
  const items = shown?.items ?? [];
  // A number that should be empty and is, is a number shown: "none ✓".
  const sure = shown !== null
    && (shown.value !== null || shown.expected !== null || shown.holds !== null);
  return (
    <div className={[
      "cell", `cell-${cell.role}`, lit ? "cell-lit" : "", dim ? "cell-dim" : "",
      shown?.holds === false ? "cell-wrong" : "",
      change ? `cell-${change}` : "", fresh ? "cell-fresh" : "",
    ].filter(Boolean).join(" ")} style={{ width: CELL.width, height: cellHeight(lines) }}>
      <Handle type="target" position={Position.Left} className="cell-port" isConnectable={false} />
      <Handle type="source" position={Position.Right} className="cell-port" isConnectable={false} />
      <header className="cell-head">
        <span className="cell-name" title={cell.field}>{cell.label}</span>
        {change && <ChangeTag how={change} />}
        {cell.check
          ? <CheckMark check={cell.check} words />
          : <span className={`cell-role cell-role-${cell.role}`}>{ROLE_SAID[cell.role]}</span>}
      </header>
      <p className="cell-how" title={cell.how}>{cell.how}</p>
      {shown && (
        <div className="cell-body">
          {items.slice(0, 5).map((item) => (
            <p key={item.record} className="cell-line cell-item" title={item.record}>
              <span className="cell-number">{item.value}</span>
              <span className="cell-when">{item.when ? daySaid(item.when) : "from the start"}</span>
            </p>
          ))}
          {items.length > 5 && <p className="cell-line cell-quiet">and {items.length - 5} more</p>}
          {shown.sum && <p className="cell-line cell-equation">= {shown.sum}</p>}
          {sure && (
            <p className="cell-line">
              <span className="cell-number cell-value">{shown.value ?? "none"}</span>
              {shown.holds !== null && (
                <span className={shown.holds ? "cell-holds" : "cell-fails"}>
                  {shown.holds ? "✓ as the example says" : `✗ the example says ${shown.expected ?? "none"}`}
                </span>
              )}
            </p>
          )}
          {shown.note && <p className="cell-line cell-quiet">{shown.note}</p>}
        </div>
      )}
    </div>
  );
}

function GroupBox({ data }: NodeProps<GroupNode>) {
  const { group, chosen, dim, change } = data;
  return (
    <div className={[
      "group", group.own ? "group-own" : "group-theirs",
      chosen ? "group-on" : "", dim ? "group-dim" : "",
    ].filter(Boolean).join(" ")}>
      <header className="group-head">
        <span className="group-name" title={group.name}>{group.label}</span>
        {change && <ChangeTag how={change} />}
        {group.module && <span className="group-from" title={group.module}>from {group.module}</span>}
      </header>
    </div>
  );
}

const NUMBER_TYPES = { cell: CellBox, kindGroup: GroupBox };

function Numbers({ draft, chosen, onChoose, layer, onLayer, showing, focus }: WithLayer) {
  const flow = useReactFlow();
  const marks = showing?.marks ?? null;
  const [legend, setLegend] = useState(false);
  const [lit, setLit] = useState<string | null>(null);
  const lead = useRef<HTMLDivElement>(null);
  const w = useMemo(() => workingsOf(draft), [draft]);
  const moments = useMemo(() => momentsOf(draft), [draft]);
  const [momentKey, setMomentKey] = useState<string>(() => moments[0]?.key ?? "");
  const moment = moments.find((m) => m.key === momentKey) ?? null;

  // A moment that went away (an example removed or changed) falls back to the first.
  useEffect(() => {
    if (momentKey && !moments.some((m) => m.key === momentKey)) setMomentKey(moments[0]?.key ?? "");
  }, [moments, momentKey]);

  const room = useMemo(() => roomFor(draft, w), [draft, w]);
  const laid = useMemo(() => arrangeWorkings(w, room), [w, room]);
  const shown = useMemo(() => (moment ? walkThrough(draft, w, moment) : new Map<string, Shown>()),
    [draft, w, moment]);
  const path = useMemo(() => (lit ? lineage(w.flows, lit) : null), [w, lit]);

  const drawn: NumberNode[] = useMemo(() => [
    // A group is listed before the fields inside it, as React Flow nests them.
    ...w.groups.filter((g) => laid.groups[g.name]).map((group): GroupNode => {
      const box = laid.groups[group.name];
      return {
        id: `group:${group.name}`, type: "kindGroup", position: { x: box.x, y: box.y },
        width: box.width, height: box.height, style: { width: box.width, height: box.height },
        draggable: false, selectable: false,
        data: {
          group, chosen: group.name === chosen,
          dim: path !== null && !w.cells.some((c) => c.kind === group.name && path.has(c.id)),
          change: marks?.kinds.get(group.name) ?? null,
        },
      };
    }),
    ...w.cells.map((cell): CellNode => ({
      id: cell.id, type: "cell", parentId: `group:${cell.kind}`, extent: "parent",
      position: laid.cells[cell.id], draggable: false, selectable: false,
      width: CELL.width, height: cellHeight(room[cell.id] ?? 0),
      data: {
        cell, shown: moment ? shown.get(cell.id) ?? null : null, lines: room[cell.id] ?? 0,
        lit: path !== null && path.has(cell.id),
        dim: path !== null && !path.has(cell.id),
        change: marks?.fields.get(cell.id) ?? null,
        fresh: marks?.fresh.has(cell.id) ?? false,
      },
    })),
  ], [w, laid, room, shown, moment, path, chosen, marks]);

  // Held as React Flow's own state, so what it measures comes back to it —
  // a fit is only carried out once it has.
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<NumberNode>(drawn);
  useEffect(() => { setFlowNodes(drawn); }, [drawn]);

  const flowEdges: Edge[] = useMemo(() => w.flows.map((f) => {
    const on = path !== null && path.has(f.from) && path.has(f.to);
    return {
      id: f.id, source: f.from, target: f.to, type: "default",
      label: f.label ?? undefined,
      className: ["flow", `flow-${f.kind}`, on ? "flow-lit" : "", path && !on ? "line-dim" : ""]
        .filter(Boolean).join(" "),
      markerEnd: {
        type: MarkerType.ArrowClosed, width: 16, height: 16,
        color: on ? "var(--focus)" : f.kind === "row" ? "var(--later)" : "var(--known)",
      },
      labelBgPadding: [6, 3] as [number, number],
      labelBgBorderRadius: 4,
      animated: on,
      selectable: false,
      focusable: false,
    };
  }), [w, path]);

  const width = useStore((state) => state.width);
  const height = useStore((state) => state.height);
  const showAll = useCallback((duration = 0) => {
    const rects = Object.values(laid.groups);
    if (rects.length === 0 || width === 0 || height === 0) return;
    const top = roomAbove(lead.current, 180);
    void flow.setViewport(viewOf(rects, width, height, top), { duration });
  }, [laid, width, height]);
  // Seen whole when it is first drawn, when its shape changes, and when the
  // panel over it grows or shrinks; never because an example was changed, so
  // the reader stays where they were.
  const sized = width > 0 && height > 0;
  useEffect(() => { showAll(); }, [sized, laid, showing !== null]);

  useEffect(() => {
    if (!focus || !w.groups.some((g) => g.name === focus.name)) return;
    const id = window.setTimeout(() => {
      void flow.fitView({
        nodes: [{ id: `group:${focus.name}` }], duration: 400, maxZoom: 1.1, padding: 0.3,
      });
    }, 60);
    return () => window.clearTimeout(id);
  }, [focus?.n]);

  if (w.cells.length === 0) {
    return (
      <div className="map-empty map-empty-numbers">
        <LayerSwitch layer={layer} onLayer={onLayer} />
        <div className="map-empty-card">
          <h3>Nothing here is worked out yet</h3>
          <p className="quiet">
            Every field of this module is typed in or recorded as it happens. When
            a field is added up, looked up or worked out by a formula, this shows
            where its numbers come from, and an example's numbers along the way.
          </p>
        </div>
      </div>
    );
  }

  const example = moment ? draft.examples.find((e) => e.name === moment.example) ?? null : null;
  const byExample = draft.examples
    .map((e) => ({ example: e, moments: moments.filter((m) => m.example === e.name) }))
    .filter((g) => g.moments.length > 0);

  return (
    <ReactFlow<NumberNode, Edge>
      nodes={flowNodes}
      edges={flowEdges}
      nodeTypes={NUMBER_TYPES}
      onNodesChange={onNodesChange}
      onNodeClick={(_, node) => {
        if (node.type === "cell") {
          setLit(lit === node.id ? null : node.id);
          onChoose((node as CellNode).data.cell.kind);
        } else {
          setLit(null);
          onChoose((node as GroupNode).data.group.name);
        }
      }}
      onPaneClick={() => { setLit(null); onChoose(null); }}
      nodesDraggable={false}
      nodesConnectable={false}
      minZoom={0.2}
      maxZoom={2}
      colorMode="system"
      proOptions={{ hideAttribution: true }}
      deleteKeyCode={null}
      selectionKeyCode={null}
      multiSelectionKeyCode={null}
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} />
      <Controls showInteractive={false} position="bottom-left" />
      <Panel position="top-left" className="map-panel">
        <div className="map-lead" ref={lead}>
        <LayerSwitch layer={layer} onLayer={onLayer} />
        <div className="example-pick">
          {byExample.length > 0 ? (
            <>
              <label className="example-choose">
                <span>Follow an example</span>
                <select value={moment?.key ?? ""} onChange={(e) => setMomentKey(e.target.value)}>
                  <option value="">No example</option>
                  {byExample.map((g) => (
                    <optgroup key={g.example.name} label={spoken(g.example.name)}>
                      {g.moments.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
                    </optgroup>
                  ))}
                </select>
              </label>
              {example && (
                <p className="example-says" title={example.says}>
                  {firstSentence(example.says)}
                </p>
              )}
            </>
          ) : (
            <p className="example-says">
              {draft.examples.length > 0 && !draft.examples_run
                ? "The examples have not been run, so there are no numbers to follow yet."
                : "No example has numbers yet. An example says what some numbers must come to; they then show here, beside what the module makes of them."}
            </p>
          )}
        </div>
        {showing && <ShowingLine showing={showing} />}
        </div>
      </Panel>
      <Panel position="top-right" className="map-panel map-corner">
        <div className="map-actions">
          <button className="button button-small"
            onClick={() => showAll(300)}>
            Show all
          </button>
          <button className={`button button-small${legend ? " button-on" : ""}`}
            aria-expanded={legend} onClick={() => setLegend(!legend)}>How to read this</button>
        </div>
        {legend && <NumbersLegend changes={showing !== null} />}
      </Panel>
    </ReactFlow>
  );
}

function NumbersLegend({ changes }: { changes: boolean }) {
  return (
    <div className="map-legend">
      <p className="legend-row"><span className="legend-box legend-theirs" /><span>A kind of thing, holding the fields its numbers come from or go to</span></p>
      <p className="legend-row"><span><span className="cell-role cell-role-recorded">recorded</span></span><span>Typed in, or recorded as things happen</span></p>
      <p className="legend-row"><span><span className="cell-role cell-role-sum">adds up</span></span><span>Worked out by a rule, never typed in: added up, looked up, or a formula</span></p>
      <p className="legend-row"><span className="legend-arrow legend-reads">→</span><span>Goes into: the number on the right is worked out from the one on the left</span></p>
      <ChecksRow />
      {changes && <ChangesRow />}
      <p className="legend-hint">
        Pick an example at the top left to follow its numbers: what was
        recorded, what each rule made of it, and what the example says it
        should come to. Click a field to light up everything it comes from and
        goes into.
      </p>
    </div>
  );
}

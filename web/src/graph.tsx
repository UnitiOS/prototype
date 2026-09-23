// The map. A module is a graph, so the page that makes one is a graph.
//
// A node is a kind of thing. An edge is a field that points from one kind at
// another. What this module declares is drawn solid; what it builds on is
// drawn faintly above it, because a pinned version is sealed and cannot be
// changed from here — you change it by sealing a new version of that module.
//
// Every gesture is one of the closed steps and nothing else. Dragging a line
// from one kind to another is `add_slot` with a class range, then `attach`.
// Moving a node is not a step at all: where a box sits is a fact about this
// screen, never about the module, so it is never written to the file.
//
// Nothing is laid out by hand. The seating below is a small deterministic
// simulation — the same module always opens the same shape — and a node the
// person has moved stays where they put it while new ones settle around it.

import { useEffect, useMemo, useRef, useState } from "react";

export interface MapField {
  name: string;
  holds: string;
  /** What this field is to a role that claimed it, or "key". */
  mark: string | null;
  asks: boolean;
}

export interface MapNode {
  name: string;
  own: boolean;
  description: string;
  fills: string[];
  fields: MapField[];
  questions: number;
  /** Where it came from, for what is not yours. */
  module: string | null;
  /** Whether anything could ever be stated to be one of these. */
  rows: boolean;
}

export interface MapEdge {
  id: string;
  from: string;
  to: string;
  label: string;
  own: boolean;
}

interface Place { x: number; y: number }
type Places = Record<string, Place>;

const W = 256;         // a node is a fixed width so names line up down the map
const HEAD = 32;
const ROW = 16;
const SHOW = 6;        // fields drawn inside a node before it says "and more"

/** A box has a width, and text does not wrap in it. */
const cut = (text: string, most: number) =>
  text.length > most ? `${text.slice(0, most - 1)}…` : text;

function heightOf(node: MapNode) {
  const rows = Math.min(node.fields.length, SHOW)
    + (node.fields.length > SHOW ? 1 : 0);
  return HEAD + rows * ROW + (rows ? 12 : 4);
}

// ---- seating --------------------------------------------------------------

/** Where the boxes go: repulsion, springs along the edges, and a preference
 *  for what you build on to float above what you are building. */
function seat(nodes: MapNode[], edges: MapEdge[], held: Places): Places {
  const place: Places = {};
  const fresh: string[] = [];
  nodes.forEach((node, i) => {
    if (held[node.name]) { place[node.name] = held[node.name]; return; }
    const turn = (i / Math.max(nodes.length, 1)) * Math.PI * 2;
    place[node.name] = {
      x: Math.cos(turn) * 300,
      y: Math.sin(turn) * 170 + (node.own ? 150 : -150),
    };
    fresh.push(node.name);
  });
  if (fresh.length === 0) return place;

  // Everything moves on a first opening; afterwards only what is new does, so
  // adding one kind of thing never rearranges the map somebody was reading.
  const settled = nodes.some((n) => held[n.name]);
  const moves = new Set(settled ? fresh : nodes.map((n) => n.name));
  const high: Record<string, number> = {};
  for (const node of nodes) high[node.name] = heightOf(node);

  for (let pass = 0; pass < 340; pass++) {
    const push: Places = {};
    for (const node of nodes) push[node.name] = { x: 0, y: 0 };

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = place[nodes[i].name];
        const b = place[nodes[j].name];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const far = Math.hypot(dx, dy) || 1;
        const force = 50000 / (far * far);
        push[nodes[i].name].x += (dx / far) * force;
        push[nodes[i].name].y += (dy / far) * force;
        push[nodes[j].name].x -= (dx / far) * force;
        push[nodes[j].name].y -= (dy / far) * force;
      }
    }

    for (const edge of edges) {
      const a = place[edge.from];
      const b = place[edge.to];
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const far = Math.hypot(dx, dy) || 1;
      const force = (far - 205) * 0.06;
      push[edge.from].x += (dx / far) * force;
      push[edge.from].y += (dy / far) * force;
      push[edge.to].x -= (dx / far) * force;
      push[edge.to].y -= (dy / far) * force;
    }

    for (const node of nodes) {
      push[node.name].y += node.own ? 1.0 : -1.0;
      push[node.name].x -= place[node.name].x * 0.014;
    }

    for (const node of nodes) {
      if (!moves.has(node.name)) continue;
      const at = place[node.name];
      const by = push[node.name];
      const cap = 26;
      place[node.name] = {
        x: at.x + Math.max(-cap, Math.min(cap, by.x)),
        y: at.y + Math.max(-cap, Math.min(cap, by.y)),
      };
    }

    // Boxes, not points. A force between centres leaves a tall node sitting
    // through a short one, so whatever still overlaps is pushed apart along
    // whichever axis is nearer to clear — which is also the axis a reader
    // would have moved it along.
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const one = nodes[i].name;
        const two = nodes[j].name;
        const a = place[one];
        const b = place[two];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const intoX = W + 46 - Math.abs(dx);
        const intoY = (high[one] + high[two]) / 2 + 40 - Math.abs(dy);
        if (intoX <= 0 || intoY <= 0) continue;
        const along = intoX < intoY ? "x" : "y";
        const off = along === "x" ? intoX : intoY;
        const way = ((along === "x" ? dx : dy) >= 0 ? 1 : -1) * off / 2;
        if (moves.has(one)) {
          place[one] = along === "x" ? { ...a, x: a.x - way } : { ...a, y: a.y - way };
        }
        if (moves.has(two)) {
          const now = place[two];
          place[two] = along === "x"
            ? { ...now, x: now.x + way } : { ...now, y: now.y + way };
        }
      }
    }
  }
  return place;
}

/** The box a line stops at, so an arrow lands on an edge and not in the middle. */
function clip(dx: number, dy: number, halfWide: number, halfHigh: number) {
  if (!dx && !dy) return { x: 0, y: 0 };
  const by = Math.min(
    dx ? halfWide / Math.abs(dx) : Infinity,
    dy ? halfHigh / Math.abs(dy) : Infinity,
  );
  return { x: dx * by, y: dy * by };
}

interface Box { x: number; y: number; w: number; h: number }

const lineOf = (edge: MapEdge, lit: boolean) =>
  `map-edge${edge.own ? "" : " map-edge-theirs"}${lit ? " map-edge-lit" : ""}`;

function around(nodes: MapNode[], place: Places): Box {
  const xs: number[] = [];
  const ys: number[] = [];
  for (const node of nodes) {
    const at = place[node.name];
    if (!at) continue;
    const high = heightOf(node);
    xs.push(at.x - W / 2, at.x + W / 2);
    ys.push(at.y - high / 2, at.y + high / 2);
  }
  if (!xs.length) return { x: -300, y: -200, w: 600, h: 400 };
  const pad = 44;
  const x = Math.min(...xs) - pad;
  const y = Math.min(...ys) - pad;
  return { x, y, w: Math.max(...xs) + pad - x, h: Math.max(...ys) + pad - y };
}

// ---- the canvas -----------------------------------------------------------

type Doing =
  | { what: "none" }
  | { what: "pan"; from: Place; box: Box }
  | { what: "move"; node: string; grab: Place }
  | { what: "link"; from: string; at: Place };

export function MapCanvas(
  { nodes, edges, chosen, onChoose, onConnect, busy }: {
    nodes: MapNode[];
    edges: MapEdge[];
    chosen: string | null;
    onChoose: (name: string | null) => void;
    onConnect: (from: string, to: string) => void;
    busy: boolean;
  },
) {
  const [place, setPlace] = useState<Places>({});
  const [box, setBox] = useState<Box | null>(null);
  const [doing, setDoing] = useState<Doing>({ what: "none" });
  const frame = useRef<SVGSVGElement | null>(null);

  const shape = nodes.map((n) => n.name).join("\u0000");
  const wires = edges.map((e) => e.id).join("\u0000");

  useEffect(() => {
    setPlace((held) => seat(nodes, edges, held));
  }, [shape, wires]);

  // Fit when the set of kinds changes, not on every reload: a person who
  // panned somewhere is reading something there.
  useEffect(() => {
    if (!Object.keys(place).length) return;
    setBox((held) => (held ? held : around(nodes, place)));
  }, [place]);
  useEffect(() => { setBox(null); }, [shape]);

  const view = box ?? around(nodes, place);
  const high = useMemo(() => {
    const out: Record<string, number> = {};
    for (const node of nodes) out[node.name] = heightOf(node);
    return out;
  }, [nodes]);

  // Where each line starts and stops, worked out once: the lines are drawn
  // under the boxes and their names over them, so a name is never buried by
  // a box that happens to lie across the middle of its line.
  const drawn = useMemo(() => edges.flatMap((edge) => {
    const a = place[edge.from];
    const b = place[edge.to];
    if (!a || !b) return [];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const out = clip(dx, dy, W / 2, (high[edge.from] ?? 40) / 2);
    const into = clip(-dx, -dy, W / 2, (high[edge.to] ?? 40) / 2);
    return [{
      edge,
      x1: a.x + out.x, y1: a.y + out.y,
      x2: b.x + into.x, y2: b.y + into.y,
      lit: chosen === edge.from || chosen === edge.to,
    }];
  }), [edges, place, high, chosen]);

  /** Client coordinates in the map's own numbers. */
  const at = (event: { clientX: number; clientY: number }): Place => {
    const svg = frame.current;
    if (!svg) return { x: 0, y: 0 };
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const matrix = svg.getScreenCTM();
    if (!matrix) return { x: 0, y: 0 };
    const held = point.matrixTransform(matrix.inverse());
    return { x: held.x, y: held.y };
  };

  const onWheel = (event: React.WheelEvent<SVGSVGElement>) => {
    event.preventDefault();
    const on = at(event);
    const by = event.deltaY > 0 ? 1.12 : 1 / 1.12;
    const w = Math.max(320, Math.min(4200, view.w * by));
    const h = view.h * (w / view.w);
    setBox({
      x: on.x - (on.x - view.x) * (w / view.w),
      y: on.y - (on.y - view.y) * (h / view.h),
      w, h,
    });
  };

  const onMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (doing.what === "none") return;
    const on = at(event);
    if (doing.what === "pan") {
      setBox({
        ...doing.box,
        x: doing.box.x - (on.x - doing.from.x),
        y: doing.box.y - (on.y - doing.from.y),
      });
    } else if (doing.what === "move") {
      setPlace({
        ...place,
        [doing.node]: { x: on.x - doing.grab.x, y: on.y - doing.grab.y },
      });
    } else {
      setDoing({ ...doing, at: on });
    }
  };

  // Which box a point is in, topmost first. A line being drawn lands where it
  // is let go, worked out from the coordinates rather than from which box the
  // pointer was last said to be over: hovering does not exist on a touch
  // screen, and a fast drag can pass over a box without ever entering it.
  const nodeAt = (spot: Place): string | null => {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const node = nodes[i];
      const put = place[node.name];
      if (!put) continue;
      if (Math.abs(spot.x - put.x) <= W / 2
        && Math.abs(spot.y - put.y) <= (high[node.name] ?? 40) / 2) {
        return node.name;
      }
    }
    return null;
  };

  const onUp = (event?: React.PointerEvent<SVGSVGElement>) => {
    if (doing.what === "link") {
      const onto = nodeAt(event ? at(event) : doing.at);
      if (onto && onto !== doing.from) onConnect(doing.from, onto);
    }
    setDoing({ what: "none" });
  };

  const landing = doing.what === "link" ? nodeAt(doing.at) : null;

  return (
    <div className="map">
      <svg ref={frame} className="map-frame"
        viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
        role="application" aria-label="The kinds of thing in this module"
        onWheel={onWheel}
        onPointerDown={(e) => {
          if (e.target !== e.currentTarget) return;
          onChoose(null);
          setDoing({ what: "pan", from: at(e), box: view });
        }}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerLeave={onUp}>
        <defs>
          <marker id="points" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 1 L 9 5 L 0 9 z" className="map-head" />
          </marker>
        </defs>

        <rect x={view.x} y={view.y} width={view.w} height={view.h} fill="transparent" />

        {drawn.map(({ edge, x1, y1, x2, y2, lit }) => (
          <g key={edge.id} className={lineOf(edge, lit)}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} markerEnd="url(#points)" />
          </g>
        ))}

        {doing.what === "link" && place[doing.from] && (
          <line className="map-drawing"
            x1={place[doing.from].x} y1={place[doing.from].y}
            x2={doing.at.x} y2={doing.at.y} />
        )}

        {nodes.map((node) => {
          const spot = place[node.name];
          if (!spot) return null;
          const h = high[node.name];
          const top = spot.y - h / 2;
          const left = spot.x - W / 2;
          const shown = node.fields.slice(0, SHOW);
          const rest = node.fields.length - shown.length;
          const target = landing === node.name
            && doing.what === "link" && node.name !== doing.from;
          return (
            <g key={node.name}
              className={[
                "map-node",
                node.own ? "map-node-own" : "map-node-theirs",
                chosen === node.name ? "map-node-on" : "",
                node.questions ? "map-node-asks" : "",
                target ? "map-node-target" : "",
              ].filter(Boolean).join(" ")}
              onPointerDown={(e) => {
                e.stopPropagation();
                onChoose(node.name);
                setDoing({
                  what: "move", node: node.name,
                  grab: { x: at(e).x - spot.x, y: at(e).y - spot.y },
                });
              }}>
              <rect className="map-box" x={left} y={top} width={W} height={h} rx="10" />
              <text className="map-name" x={left + 12} y={top + 21}>
                {node.name}
              </text>
              {node.questions > 0 && (
                <>
                  <circle className="map-asks" cx={left + W - 15} cy={top + 15} r="8" />
                  <text className="map-asks-count" x={left + W - 15} y={top + 19}
                    textAnchor="middle">{node.questions}</text>
                </>
              )}
              {shown.map((field, i) => (
                <g key={field.name}>
                  <text className={`map-field${field.asks ? " map-field-asks" : ""}`}
                    x={left + 12} y={top + HEAD + i * ROW + 6}>
                    <tspan className="map-field-name">{cut(field.name, 18)}</tspan>
                    <tspan className="map-field-holds" dx="6">
                      {cut(field.holds, field.mark ? 10 : 18)}
                    </tspan>
                  </text>
                  {/* The mark is what a role calls this field, and it is put
                      against the right edge so a long name never pushes it
                      out of the box. */}
                  {field.mark && (
                    <text className="map-field map-field-mark" textAnchor="end"
                      x={left + W - 12} y={top + HEAD + i * ROW + 6}>
                      {field.mark}
                    </text>
                  )}
                </g>
              ))}
              {rest > 0 && (
                <text className="map-field map-field-rest" x={left + 12}
                  y={top + HEAD + shown.length * ROW + 6}>
                  and {rest} more
                </text>
              )}
              {node.fills.map((role, i) => (
                <text key={role} className="map-fills"
                  x={left + W - 12} y={top + h - 8 - i * 13} textAnchor="end">
                  {role}
                </text>
              ))}
              {node.own && !busy && (
                <circle className="map-handle" cx={spot.x} cy={top + h} r="7"
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    setDoing({ what: "link", from: node.name, at: at(e) });
                  }} />
              )}
            </g>
          );
        })}

        {drawn.map(({ edge, x1, y1, x2, y2, lit }) => (
          // A third of the way along and not halfway: in a chain of boxes the
          // middle of one line is where the next box tends to sit.
          <text key={`${edge.id}-said`} className={`map-said ${lineOf(edge, lit)}`}
            x={x1 + (x2 - x1) * 0.34} y={y1 + (y2 - y1) * 0.34} textAnchor="middle">
            {edge.label}
          </text>
        ))}
      </svg>

      <div className="map-tools">
        <button className="button button-small"
          onClick={() => setBox(around(nodes, place))}>Fit</button>
        <p className="quiet">
          Drag a box to move it · drag the dot under a box onto another to make
          a relation · scroll to zoom
        </p>
      </div>
    </div>
  );
}

// Every sealed version of every module, on one timeline. Each module is a lane;
// its versions sit on it in the order they were sealed, left to right. An arrow
// runs from a version to each version it pins. Modules that others build on sit
// lower, so imports point down.
//
// Selecting a version lights it and everything it can see; the rest fades.

import { useEffect, useMemo, useRef, useState } from "react";
import type { ModuleGraph, Pin } from "./api";

const LANE = 64;
const GUTTER = 190;
const RIGHT = 32;
const TOP = 12;

const key = (p: Pin) => `${p.name}@${p.version}`;

interface Props {
  graph: ModuleGraph;
  selected: Pin | null;
  onSelect: (pin: Pin) => void;
}

export function ModuleTimeline({ graph, selected, onSelect }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(900);

  useEffect(() => {
    if (!box.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(box.current);
    return () => observer.disconnect();
  }, []);

  const layout = useMemo(() => {
    const imports = graph.edges.filter((e) => e.kind === "imports");
    const names = [...new Set(graph.nodes.map((n) => n.name))];

    // A module's depth is the longest chain of modules beneath it.
    const depends = new Map<string, Set<string>>(names.map((n) => [n, new Set<string>()]));
    for (const e of imports) if (e.from.name !== e.to.name) depends.get(e.from.name)!.add(e.to.name);
    const depth = new Map<string, number>();
    const measure = (name: string, trail: string[] = []): number => {
      if (depth.has(name)) return depth.get(name)!;
      if (trail.includes(name)) return 0;
      const below = [...depends.get(name)!].map((d) => measure(d, [...trail, name]));
      const d = below.length ? Math.max(...below) + 1 : 0;
      depth.set(name, d);
      return d;
    };
    names.forEach((n) => measure(n));
    const lanes = [...names].sort((a, b) => depth.get(b)! - depth.get(a)! || a.localeCompare(b));

    const order = [...graph.nodes].sort((a, b) => Date.parse(a.sealed_at) - Date.parse(b.sealed_at));
    const rank = new Map(order.map((n, i) => [key(n), i]));

    // What the selected version can see: itself and everything it pins, transitively.
    const seen = new Set<string>();
    if (selected) {
      const walk = (pin: Pin) => {
        if (seen.has(key(pin))) return;
        seen.add(key(pin));
        imports.filter((e) => key(e.from) === key(pin)).forEach((e) => walk(e.to));
      };
      walk(selected);
    }
    return { lanes, rank, count: order.length, imports, seen };
  }, [graph, selected]);

  const height = TOP * 2 + layout.lanes.length * LANE + 24;
  const step = Math.max((width - GUTTER - RIGHT) / Math.max(layout.count, 1), 40);
  const x = (p: Pin) => GUTTER + (layout.rank.get(key(p))! + 0.5) * step;
  const y = (name: string) => TOP + layout.lanes.indexOf(name) * LANE + LANE / 2;
  const lit = (p: Pin) => !selected || layout.seen.has(key(p));

  if (graph.nodes.length === 0) {
    return <p className="empty">The store holds no sealed module yet.</p>;
  }

  return (
    <figure className="timeline" ref={box}>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img"
        aria-label="Sealed module versions over time, with the versions each one pins">
        <defs>
          <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0L8 4L0 8Z" className="tl-arrowhead" />
          </marker>
          <marker id="arrow-lit" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0L8 4L0 8Z" className="tl-arrowhead-lit" />
          </marker>
        </defs>

        {layout.lanes.map((name) => {
          const versions = graph.nodes.filter((n) => n.name === name);
          const xs = versions.map(x);
          return (
            <g key={name}>
              <text className="tl-lane-name" x={16} y={y(name) + 4}>{name}</text>
              <line className="tl-lane" x1={Math.min(...xs)} x2={Math.max(...xs)} y1={y(name)} y2={y(name)} />
            </g>
          );
        })}

        {layout.imports.map((e) => {
          const x1 = x(e.from), y1 = y(e.from.name);
          const x2 = x(e.to), y2 = y(e.to.name);
          const on = selected && layout.seen.has(key(e.from)) && layout.seen.has(key(e.to));
          const bend = Math.max(Math.abs(y2 - y1) * 0.5, 24);
          const d = `M${x1} ${y1 + 9}C${x1} ${y1 + 9 + bend} ${x2} ${y2 - 9 - bend} ${x2} ${y2 - 11}`;
          return (
            <path key={`${key(e.from)}>${key(e.to)}`} d={d}
              className={on ? "tl-edge tl-edge-lit" : selected ? "tl-edge tl-edge-faded" : "tl-edge"}
              markerEnd={on ? "url(#arrow-lit)" : "url(#arrow)"} />
          );
        })}

        {graph.nodes.map((n) => {
          const isSelected = selected && key(selected) === key(n);
          return (
            <g key={key(n)} className={`tl-node${lit(n) ? "" : " tl-faded"}${isSelected ? " tl-selected" : ""}`}
              transform={`translate(${x(n)} ${y(n.name)})`}
              role="button" tabIndex={0}
              aria-label={`${key(n)}${n.latest ? ", latest" : ""}`}
              onClick={() => onSelect({ name: n.name, version: n.version })}
              onKeyDown={(ev) => {
                if (ev.key === "Enter" || ev.key === " ") {
                  ev.preventDefault();
                  onSelect({ name: n.name, version: n.version });
                }
              }}>
              <circle r={isSelected ? 11 : 9} />
              <text x={isSelected ? 16 : 14} y={4}>{n.version}</text>
            </g>
          );
        })}

        <text className="tl-axis" x={width - RIGHT} y={height - 6} textAnchor="end">Order sealed</text>
      </svg>
    </figure>
  );
}

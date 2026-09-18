// Every class an application can see, in one picture, coloured by the module
// that declares it. The timeline next door answers *when* a version was sealed
// and what it pins; this answers what a pin was for — which class points at
// which, and where a derived column gets its rows from.
//
// A module is a band. Bands are ordered so that a module sits below the ones
// that pin it, which makes every arrow run downward: a class reaches down into
// the module its own module pinned.

import { useEffect, useMemo, useRef, useState } from "react";
import type { ClassGraph as Graph, ClassEdge } from "./api";

const BAND = 108;
const BOX_W = 150;
const BOX_H = 42;
const GAP = 22;
const GUTTER = 168;
const TOP = 16;

const KIND_LABEL: Record<ClassEdge["kind"], string> = {
  is_a: "is a",
  reference: "points at",
  aggregate: "totals",
  parameter: "reads one fact off",
};

interface Props {
  graph: Graph;
  selected: string | null;
  onSelect: (className: string | null) => void;
}

export function ClassGraph({ graph, selected, onSelect }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(900);

  useEffect(() => {
    if (!box.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(box.current);
    return () => observer.disconnect();
  }, []);

  const layout = useMemo(() => {
    const colour = new Map(graph.modules.map((m, i) => [m.name, i % 6]));
    // Bands, dependents first: the closure comes back dependencies first, and
    // this reads better the other way up, so an arrow always points down.
    const bands = [...graph.modules]
      .reverse()
      .map((m) => m.name)
      .filter((name) => graph.nodes.some((n) => n.module.name === name));

    const place = new Map<string, { x: number; y: number; band: number }>();
    bands.forEach((name, band) => {
      const mine = graph.nodes.filter((n) => n.module.name === name);
      mine.forEach((node, i) => {
        place.set(node.name, {
          x: GUTTER + i * (BOX_W + GAP),
          y: TOP + band * BAND,
          band,
        });
      });
    });

    const widest = Math.max(
      ...bands.map((name) => graph.nodes.filter((n) => n.module.name === name).length), 1);
    return { colour, bands, place, needed: GUTTER + widest * (BOX_W + GAP) };
  }, [graph]);

  const height = TOP * 2 + layout.bands.length * BAND;
  const board = Math.max(width, layout.needed);
  const lit = (name: string) =>
    !selected || name === selected ||
    graph.edges.some((e) =>
      (e.from === selected && e.to === name) || (e.to === selected && e.from === name));

  if (graph.nodes.length === 0) {
    return <p className="empty">This version can see no class at all.</p>;
  }

  return (
    <figure className="classgraph" ref={box}>
      <svg viewBox={`0 0 ${board} ${height}`} width="100%" height={height} role="img"
        aria-label="The classes this application can see, and what joins them">
        <defs>
          <marker id="cg-arrow" viewBox="0 0 8 8" refX="7" refY="4"
            markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0L8 4L0 8Z" className="cg-head" />
          </marker>
          <marker id="cg-arrow-lit" viewBox="0 0 8 8" refX="7" refY="4"
            markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 0L8 4L0 8Z" className="cg-head-lit" />
          </marker>
        </defs>

        {layout.bands.map((name, i) => (
          <g key={name} className={`cg-band cg-mod-${layout.colour.get(name)}`}>
            <rect x={0} y={TOP + i * BAND - 12} width={board} height={BAND - 8} rx={8} />
            <text x={14} y={TOP + i * BAND + BOX_H / 2 + 4}>{name}</text>
          </g>
        ))}

        {graph.edges.map((e, i) => {
          const a = layout.place.get(e.from);
          const b = layout.place.get(e.to);
          if (!a || !b) return null;
          const on = selected && (e.from === selected || e.to === selected);
          const x1 = a.x + BOX_W / 2;
          const x2 = b.x + BOX_W / 2;
          const sameBand = a.band === b.band;
          // Within a band the two boxes sit side by side, so the line leaves
          // and arrives underneath them and dips between; across bands it
          // simply runs down. Either way the label sits on the slack, clear of
          // every box.
          const y1 = a.y + BOX_H;
          const y2 = sameBand ? b.y + BOX_H + 2 : b.y - 6;
          // Neighbouring edges in one band dip by different amounts, so two
          // labels never land on the same line.
          const dip = sameBand ? 26 + (i % 2) * 16 : 0;
          const d = sameBand
            ? `M${x1} ${y1}C${x1} ${y1 + dip} ${x2} ${y2 + dip} ${x2} ${y2}`
            : `M${x1} ${y1}C${x1} ${y1 + 30} ${x2} ${y2 - 30} ${x2} ${y2}`;
          const labelY = sameBand ? y1 + dip - 3 : y1 + (y2 - y1) * 0.34;
          return (
            <g key={i} className={`cg-edge cg-edge-${e.kind}${on ? " cg-lit" : selected ? " cg-dim" : ""}`}>
              <title>{`${e.from} ${KIND_LABEL[e.kind]} ${e.to} — ${e.label}`}</title>
              <path d={d} markerEnd={on ? "url(#cg-arrow-lit)" : "url(#cg-arrow)"} />
              <text x={(x1 + x2) / 2} y={labelY} textAnchor="middle">{e.label}</text>
            </g>
          );
        })}

        {graph.nodes.map((node) => {
          const at = layout.place.get(node.name)!;
          const on = selected === node.name;
          return (
            <g key={node.name}
              className={`cg-node cg-mod-${layout.colour.get(node.module.name)} cg-shape-${node.shape}`
                + `${on ? " cg-selected" : ""}${lit(node.name) ? "" : " cg-faded"}`}
              transform={`translate(${at.x} ${at.y})`}
              role="button" tabIndex={0}
              aria-label={`${node.name}, declared by ${node.module.name} ${node.module.version}`}
              onClick={() => onSelect(on ? null : node.name)}
              onKeyDown={(ev) => {
                if (ev.key === "Enter" || ev.key === " ") {
                  ev.preventDefault();
                  onSelect(on ? null : node.name);
                }
              }}>
              <title>{node.description ?? node.name}</title>
              <rect width={BOX_W} height={BOX_H} rx={6} />
              <text x={10} y={18}>{node.name}</text>
              <text x={10} y={33} className="cg-sub">
                {node.shape === "derived" ? "derived table"
                  : node.shape === "stated" ? `${node.slots.length} slots`
                    : "nothing can be one"}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption className="cg-key">
        <span className="cg-key-item cg-key-reference">points at</span>
        <span className="cg-key-item cg-key-aggregate">totals</span>
        <span className="cg-key-item cg-key-parameter">reads one fact off</span>
        <span className="cg-key-item cg-key-is_a">is a</span>
        <span className="quiet">Click a class to keep only what touches it.</span>
      </figcaption>
    </figure>
  );
}

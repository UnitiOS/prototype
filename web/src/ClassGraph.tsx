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
import { plainName, tagOf } from "./studioMap";

const BAND = 108;
const BOX_W = 150;
const BOX_H = 42;
const GAP = 22;
const GUTTER = 168;
const TOP = 16;

const KIND_LABEL: Record<ClassEdge["kind"], string> = {
  is_a: "is a",
  fills: "fills",
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

    // Each edge's position among the ones that leave its own band, so that two
    // labels on one band never land at the same height. Counted separately for
    // edges that stay inside a band and edges that cross one, because the two
    // are drawn on different pieces of slack.
    const seen = new Map<string, number>();
    const rank = new Map<number, number>();
    graph.edges.forEach((e, i) => {
      const from = place.get(e.from);
      const to = place.get(e.to);
      if (!from || !to) return;
      const lane = `${from.band}:${from.band === to.band}`;
      const next = seen.get(lane) ?? 0;
      rank.set(i, next);
      seen.set(lane, next + 1);
    });

    const widest = Math.max(
      ...bands.map((name) => graph.nodes.filter((n) => n.module.name === name).length), 1);
    return { colour, bands, place, rank, needed: GUTTER + widest * (BOX_W + GAP) };
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
          // Edges are staggered against the others leaving the *same band*,
          // not against the whole list. Two labels collide when they share a
          // band and a height, and nothing else about the order matters.
          const rank = layout.rank.get(i) ?? 0;
          const dip = sameBand ? 24 + (rank % 3) * 15 : 0;
          const d = sameBand
            ? `M${x1} ${y1}C${x1} ${y1 + dip} ${x2} ${y2 + dip} ${x2} ${y2}`
            : `M${x1} ${y1}C${x1} ${y1 + 30} ${x2} ${y2 - 30} ${x2} ${y2}`;
          // A crossing edge's label sits in the strip below its own band, not
          // partway down the run: an edge that skips a band would otherwise
          // drop its label on top of that band's boxes.
          const labelY = sameBand ? y1 + dip - 3 : y1 + 13 + (rank % 4) * 12;
          return (
            <g key={i} className={`cg-edge cg-edge-${e.kind}${e.awaiting ? " cg-awaiting" : ""}${on ? " cg-lit" : selected ? " cg-dim" : ""}`}>
              <title>{`${plainName(e.from)} ${KIND_LABEL[e.kind]} ${plainName(e.to)} — ${plainName(e.label)}`
                + (e.awaiting ? " (not computed yet)" : "")}</title>
              <path d={d} markerEnd={on ? "url(#cg-arrow-lit)" : "url(#cg-arrow)"} />
              <text x={(x1 + x2) / 2} y={labelY} textAnchor="middle">{plainName(e.label)}</text>
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
              aria-label={`${plainName(node.name)}, declared by ${node.module.name} ${node.module.version}`}
              onClick={() => onSelect(on ? null : node.name)}
              onKeyDown={(ev) => {
                if (ev.key === "Enter" || ev.key === " ") {
                  ev.preventDefault();
                  onSelect(on ? null : node.name);
                }
              }}>
              <title>{node.description ?? plainName(node.name)}</title>
              <rect width={BOX_W} height={BOX_H} rx={6} />
              <text x={10} y={18}>
                {plainName(node.name)}
                {tagOf(node.name) && <tspan className="cg-tag"> · {tagOf(node.name)}</tspan>}
              </text>
              <text x={10} y={33} className="cg-sub">
                {node.shape === "role" ? "a role"
                  : node.shape === "derived" ? "derived table"
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
        <span className="cg-key-item cg-key-fills">fills a role</span>
        <span className="cg-key-item cg-key-is_a">is a</span>
        <span className="quiet">Click a class to keep only what touches it.</span>
      </figcaption>
    </figure>
  );
}

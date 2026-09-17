// The two clocks as one plane. Across: when a statement says the world was so
// (valid from). Up: when the log learned it (recorded at). Every assertion is a
// point. The crosshair is (valid at, as of), and the shaded corner below and
// left of it holds every statement that can count at those clocks.
//
// Pressing on the plane moves both clocks to that spot; dragging follows the
// pointer, and the clocks are committed when the pointer is released. Arrow
// keys move one day (Shift: thirty); left and right move the valid clock, up
// and down the record clock.

import { useEffect, useMemo, useRef, useState } from "react";
import type { Clocks, Point, Status } from "./api";
import { STATUS, day } from "./format";

const DAY = 86_400_000;
const PAD = { left: 72, right: 20, top: 16, bottom: 40 };
const HEIGHT = 300;

const ORDER: Status[] = ["candidate", "not_yet_valid", "revoked", "retraction", "not_recorded"];

interface Props {
  points: Point[];
  clocks: Clocks;
  highlight: string | null;
  onChange: (clocks: Clocks) => void;
}

function monthTicks(from: number, to: number): Date[] {
  const start = new Date(from);
  const ticks: Date[] = [];
  const cursor = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1));
  const span = (to - from) / DAY;
  const step = span > 900 ? 6 : span > 400 ? 3 : 1;
  while (cursor.getTime() <= to) {
    if (cursor.getUTCMonth() % step === 0) ticks.push(new Date(cursor));
    cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
  return ticks;
}

function tickLabel(t: Date): string {
  const month = t.toLocaleString("en-GB", { month: "short", timeZone: "UTC" });
  return t.getUTCMonth() === 0 ? `${month} ${t.getUTCFullYear()}` : month;
}

export function ClockPlane({ points, clocks, highlight, onChange }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(900);
  const [draft, setDraft] = useState<Clocks | null>(null);
  const shown = draft ?? clocks;

  useEffect(() => {
    if (!box.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(box.current);
    return () => observer.disconnect();
  }, []);

  // The span covers the whole log and the clocks, so neither falls off the plane.
  const [from, to] = useMemo(() => {
    const times = points.flatMap((p) => [Date.parse(p.valid_from), Date.parse(p.recorded_at)]);
    times.push(clocks.validAt.getTime(), clocks.asOf.getTime());
    const lo = Math.min(...times);
    const hi = Math.max(...times);
    const margin = Math.max((hi - lo) * 0.04, 7 * DAY);
    return [lo - margin, hi + margin];
  }, [points, clocks]);

  const plotW = Math.max(width - PAD.left - PAD.right, 100);
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const x = (t: number) => PAD.left + ((t - from) / (to - from)) * plotW;
  const y = (t: number) => PAD.top + plotH - ((t - from) / (to - from)) * plotH;
  const tx = (px: number) => from + ((px - PAD.left) / plotW) * (to - from);
  const ty = (py: number) => from + ((PAD.top + plotH - py) / plotH) * (to - from);
  const clamp = (t: number) => Math.min(Math.max(t, from), to);

  const cx = x(shown.validAt.getTime());
  const cy = y(shown.asOf.getTime());

  const fromEvent = (event: React.PointerEvent<SVGSVGElement>): Clocks => {
    const rect = event.currentTarget.getBoundingClientRect();
    const scaleX = width / rect.width;
    const scaleY = HEIGHT / rect.height;
    return {
      validAt: new Date(clamp(tx((event.clientX - rect.left) * scaleX))),
      asOf: new Date(clamp(ty((event.clientY - rect.top) * scaleY))),
    };
  };

  const onKey = (event: React.KeyboardEvent) => {
    const step = (event.shiftKey ? 30 : 1) * DAY;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, step], ArrowDown: [0, -step],
    };
    const move = moves[event.key];
    if (!move) return;
    event.preventDefault();
    onChange({
      validAt: new Date(clocks.validAt.getTime() + move[0]),
      asOf: new Date(clocks.asOf.getTime() + move[1]),
    });
  };

  const ticks = monthTicks(from, to);
  const drawn = [...points].sort((a, b) => ORDER.indexOf(b.status) - ORDER.indexOf(a.status));
  const counts = points.reduce<Partial<Record<Status, number>>>((acc, p) => {
    acc[p.status] = (acc[p.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <figure className="plane" ref={box}>
      <svg
        viewBox={`0 0 ${width} ${HEIGHT}`}
        width="100%"
        height={HEIGHT}
        role="slider"
        tabIndex={0}
        aria-label="Clocks. Left and right move valid at, up and down move as of."
        aria-valuetext={`valid at ${day(shown.validAt)}, as of ${day(shown.asOf)}`}
        onKeyDown={onKey}
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          setDraft(fromEvent(e));
        }}
        onPointerMove={(e) => {
          if (draft) setDraft(fromEvent(e));
        }}
        onPointerUp={(e) => {
          if (!draft) return;
          const next = fromEvent(e);
          setDraft(null);
          onChange(next);
        }}
      >
        <rect className="plane-field" x={PAD.left} y={PAD.top} width={plotW} height={plotH} />
        <rect
          className="plane-counts"
          x={PAD.left}
          y={cy}
          width={Math.max(cx - PAD.left, 0)}
          height={Math.max(PAD.top + plotH - cy, 0)}
        />
        <line className="plane-diagonal" x1={x(from)} y1={y(from)} x2={x(to)} y2={y(to)} />

        {ticks.map((t) => (
          <g key={t.getTime()}>
            <line className="plane-grid" x1={x(t.getTime())} x2={x(t.getTime())} y1={PAD.top} y2={PAD.top + plotH} />
            <line className="plane-grid" y1={y(t.getTime())} y2={y(t.getTime())} x1={PAD.left} x2={PAD.left + plotW} />
            <text className="plane-tick" x={x(t.getTime())} y={HEIGHT - PAD.bottom + 16} textAnchor="middle">
              {tickLabel(t)}
            </text>
            <text className="plane-tick" x={PAD.left - 8} y={y(t.getTime()) + 4} textAnchor="end">
              {tickLabel(t)}
            </text>
          </g>
        ))}

        {drawn.map((p) => {
          const px = x(Date.parse(p.valid_from));
          const py = y(Date.parse(p.recorded_at));
          const mark = p.subject_id === highlight;
          const cls = `pt pt-${p.status}${mark ? " pt-mark" : ""}`;
          const s = mark ? 5 : 3.5;
          if (p.status === "revoked") {
            return (
              <path key={p.id} className={cls}
                d={`M${px - s} ${py - s}L${px + s} ${py + s}M${px + s} ${py - s}L${px - s} ${py + s}`} />
            );
          }
          if (p.status === "retraction") {
            const d = s + 1;
            return (
              <path key={p.id} className={cls}
                d={`M${px} ${py - d}L${px + d} ${py}L${px} ${py + d}L${px - d} ${py}Z`} />
            );
          }
          return <circle key={p.id} className={cls} cx={px} cy={py} r={mark ? 5 : 3.5} />;
        })}

        <line className="plane-clock" x1={cx} x2={cx} y1={PAD.top} y2={PAD.top + plotH} />
        <line className="plane-clock" y1={cy} y2={cy} x1={PAD.left} x2={PAD.left + plotW} />
        <circle className="plane-handle" cx={cx} cy={cy} r={6} />

        <text className="plane-axis" x={PAD.left + plotW} y={HEIGHT - 4} textAnchor="end">
          Valid from
        </text>
        <text className="plane-axis" transform={`translate(14 ${PAD.top + plotH / 2}) rotate(-90)`} textAnchor="middle">
          Recorded at
        </text>
      </svg>
      <figcaption className="legend">
        {ORDER.map((s) => (
          <span key={s} className="legend-item" title={STATUS[s].meaning}>
            <svg width="12" height="12" aria-hidden="true">
              {s === "revoked" && <path className={`pt pt-${s}`} d="M2.5 2.5L9.5 9.5M9.5 2.5L2.5 9.5" />}
              {s === "retraction" && <path className={`pt pt-${s}`} d="M6 1.5L10.5 6L6 10.5L1.5 6Z" />}
              {s !== "revoked" && s !== "retraction" && <circle className={`pt pt-${s}`} cx="6" cy="6" r="4" />}
            </svg>
            {s === "candidate" ? "Can count" : STATUS[s].label}
            <b>{counts[s] ?? 0}</b>
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

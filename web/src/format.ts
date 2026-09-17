import type { Named, Status } from "./api";

export const STATUS: Record<Status, { label: string; meaning: string }> = {
  winner: { label: "Stands", meaning: "What the log holds to be true at these two clocks." },
  outranked: { label: "Outranked", meaning: "Known and in effect, but a later statement about the same thing wins." },
  candidate: { label: "Known", meaning: "Known to the log and in effect at these clocks." },
  not_yet_valid: { label: "Not in effect yet", meaning: "It describes the world from a later moment than the valid clock." },
  not_recorded: { label: "Not recorded yet", meaning: "The log learned it after the record clock." },
  revoked: { label: "Withdrawn", meaning: "A later statement the log already held says this one was wrong." },
  retraction: { label: "Withdrawal", meaning: "Says an earlier statement was wrong, and states nothing in its place." },
};

export function name(n: Named | null): string {
  if (!n) return "";
  return n.uri ?? shortId(n.id);
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

const dateFmt = new Intl.DateTimeFormat("en-GB", {
  day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
});
const timeFmt = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit", minute: "2-digit", timeZone: "UTC",
});

export function day(iso: string | Date): string {
  return dateFmt.format(typeof iso === "string" ? new Date(iso) : iso);
}

export function instant(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return `${dateFmt.format(d)}, ${timeFmt.format(d)} UTC`;
}

// A <input type="datetime-local"> holds no zone; the app reads and writes it as UTC.
export function toInput(d: Date): string {
  return d.toISOString().slice(0, 16);
}

export function fromInput(value: string): Date | null {
  const d = new Date(`${value}:00Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

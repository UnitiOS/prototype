// What the studio's map draws, worked out from a draft and nothing else.
//
// Everything here is plain data in and plain data out, so it can be tested
// without a browser: which kinds of thing are boxes, which fields are lines,
// what each is called in words a person reads, and where each box sits.
//
// The words are the person's own where the module keeps them: a module is
// recorded in English, and the words its people used are labels beside it, one
// per language, so a box reads "Stok bahan" to somebody whose browser reads
// Indonesian. Otherwise they are made mechanically, never from a dictionary of
// anybody's subject: a name somebody wrote as `quantity_on_hand` or
// `IngredientStock` is said "Quantity on hand" and "Ingredient stock", a
// field's own title wins where its author wrote one, and a field that repeats
// its kind's name (`ingredient_code` on Ingredient) drops the repetition. The
// name the machinery uses is always one click away, in the panel.

import dagre from "@dagrejs/dagre";
import type {
  Binding, DraftBorrowed, DraftChange as Change, DraftSlot, DraftState, ExampleResult, Pin,
} from "./api";

// The types a field can hold are a closed set — the compiler's own — so they
// can be said in words without guessing about anybody's subject.
export const HOLDS: Record<string, string> = {
  string: "text", uri: "text", uriorcurie: "text", curie: "text",
  ncname: "text", date: "date", datetime: "date & time", time: "time",
  integer: "whole number", decimal: "number", double: "number",
  float: "number", boolean: "yes / no",
};
export const holds = (range: string | null) => (range ? HOLDS[range] ?? range : "text");

export const pinText = (p: Pin) => `${p.name}@${p.version}`;

/** A name as its module wrote it. Read beside other modules, a pinned
 *  module's names carry its tag, `komunitas_penyewaan__Rental`; a person is shown
 *  `Rental`, and the module it came from as a mark of its own. */
export const plainName = (name: string) =>
  name.includes("__") ? name.slice(name.lastIndexOf("__") + 2) : name;

/** The tag a composed name carries, or null for a name of one's own. */
export const tagOf = (name: string): string | null =>
  name.includes("__") ? name.slice(0, name.lastIndexOf("__")) : null;

/** Text that may carry composed names — a rule, a table's name — with each
 *  name's tag taken off: `{rudi_sewa__rental_rate} * 2` reads `{rental_rate} * 2`. */
export const untagged = (text: string): string => text.replace(/[A-Za-z0-9_]*__(?=[A-Za-z0-9])/g, "");

/** A name offered in a list: the plain name, and the module's tag as a mark
 *  after it where it carries one — two `Rental`s are told apart, and the
 *  value chosen is still the full name. */
export const nameShown = (name: string): string =>
  tagOf(name) ? `${plainName(name)} · ${tagOf(name)}` : name;

/** A name as words: `quantity_on_hand` and `QuantityOnHand` are both
 *  "Quantity on hand". Runs of capitals stay as they are ("SKU code"). A
 *  pinned module's tag is not part of what it is called. */
export function spoken(name: string): string {
  const words = plainName(name)
    .replace(/[_\-.]+/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (words.length === 0) return name;
  const said = words.map((w, i) => (i > 0 && !/^[A-Z0-9]{2,}$/.test(w) ? w.toLowerCase() : w));
  said[0] = said[0][0].toUpperCase() + said[0].slice(1);
  return said.join(" ");
}

// Where the language somebody chose to read the studio in is kept: on this
// browser only, a convenience, never anything the module depends on.
const CHOSEN = "uniti.studio.language";

/** The language the person reads the studio in: the one they chose, otherwise
 *  their browser's, as a primary tag (`id` for `id-ID`). */
export function personLanguage(): string {
  try {
    const kept = globalThis.localStorage?.getItem(CHOSEN);
    if (kept) return kept;
  } catch {
    // Storage refused, as in a private window: the browser's language it is.
  }
  const said = (globalThis as { navigator?: { language?: string } }).navigator?.language;
  return (said || "en").split("-")[0].toLowerCase();
}

/** Keep the language the person chose, for the next time on this browser. */
export function chooseLanguage(language: string): void {
  try {
    globalThis.localStorage?.setItem(CHOSEN, language);
  } catch {
    // Not kept; it still holds for this visit.
  }
}

/** Every language this draft keeps somebody's words in, English first. */
export function languagesOf(draft: DraftState): string[] {
  const found = new Set<string>();
  const add = (labels?: Record<string, string>) => {
    for (const language of Object.keys(labels ?? {})) found.add(language);
  };
  add(draft.labels);
  for (const kind of [...draft.classes, ...draft.borrowed, ...(draft.read_from ?? [])]) {
    add(kind.labels);
  }
  for (const slot of draft.slots) add(slot.labels);
  for (const example of draft.examples) add(example.labels);
  found.delete("en");
  return found.size === 0 ? [] : ["en", ...[...found].sort()];
}

/** A language tag said in words, in English: `id` is "Indonesian". */
export function languageSaid(language: string): string {
  try {
    return new Intl.DisplayNames(["en"], { type: "language" }).of(language) ?? language;
  } catch {
    return language;
  }
}

/** What the person calls each thing in this draft, in their language, where the
 *  module keeps their word for it: kinds, fields, and those of what it pins. */
export function wordsOf(draft: DraftState, language: string = personLanguage()): Map<string, string> {
  const out = new Map<string, string>();
  const keep = (name: string, labels?: Record<string, string>) => {
    const word = labels?.[language];
    if (word && !out.has(name)) out.set(name, word);
  };
  for (const kind of draft.classes) keep(kind.name, kind.labels);
  for (const slot of draft.slots) keep(slot.name, slot.labels);
  for (const kind of [...draft.borrowed, ...(draft.read_from ?? [])]) {
    keep(kind.name, kind.labels);
    for (const slot of kind.slots) keep(slot.name, slot.labels);
  }
  return out;
}

/** What a number or a date holds, with what it means where the module says. */
export function holdsSaid(slot: { range: string | null; unit?: string | null }): string {
  const said = holds(slot.range);
  return slot.unit ? `${said}, in ${slot.unit}` : said;
}

/** A name as a machine name: `IngredientStock` is `ingredient_stock`. */
export const snake = (name: string) =>
  name.replace(/([a-z0-9])([A-Z])/g, "$1_$2").replace(/[\s-]+/g, "_").toLowerCase();

/** What a field is called on a box: its author's title where there is one,
 *  otherwise its name in words, less the kind's own name in front of it. */
export function fieldLabel(slot: string, kind: string, title?: string | null): string {
  const written = title?.trim();
  if (written && written !== slot) return written;
  const own = plainName(slot);
  const lead = `${snake(plainName(kind))}_`;
  const rest = own.toLowerCase().startsWith(lead) ? own.slice(lead.length) : own;
  return spoken(rest || own);
}

/** The first sentence of what somebody wrote, for a line that has room for one. */
export function firstSentence(text: string | null | undefined): string {
  const said = (text ?? "").replace(/\s+/g, " ").trim();
  const stop = said.search(/\.(\s|$)/);
  return stop === -1 ? said : said.slice(0, stop + 1);
}

// ---- the map --------------------------------------------------------------

/** How a field's value comes to be, in a word or two. */
export type MarkKind = "key" | "role" | "sum" | "formula" | "lookup" | "worked" | "adds";
export interface Mark { kind: MarkKind; text: string }

export interface MapField {
  name: string;
  label: string;
  /** What it holds, in words, or the kind of thing it points at. */
  holds: string;
  /** The kind of thing it points at, when it is a relation. */
  points: string | null;
  mark: Mark | null;
  asks: boolean;
  /** Whether the examples say a worked-out field comes out right. */
  check: Check | null;
}

export interface MapNode {
  name: string;
  label: string;
  own: boolean;
  description: string;
  fills: string[];
  fields: MapField[];
  questions: number;
  /** Where it came from, for what is not yours. */
  module: string | null;
  rows: boolean;
  /** Drawn only because a rule of this module reads it. */
  read: boolean;
}

export interface MapEdge {
  id: string;
  from: string;
  to: string;
  field: string;
  /** Said on the line only when the field's name adds something to the name
   *  of what it points at: "Ingredient → Category" needs no word on it,
   *  "Movement → Store" twice, as "from" and "to", does. */
  label: string | null;
  own: boolean;
  /** A field pointing at a kind, or a rule reading one. */
  kind: "points" | "reads";
}

export interface Drawn { nodes: MapNode[]; edges: MapEdge[] }

function bindingIn(draft: DraftState, binding: string): Binding | null {
  for (const role of draft.roles) {
    const found = role.bindings.find((b) => b.name === binding);
    if (found) return found;
  }
  return null;
}

const RULE_MARK: Record<string, Mark> = {
  aggregate: { kind: "sum", text: "sum" },
  expression: { kind: "formula", text: "formula" },
  parameter: { kind: "lookup", text: "looked up" },
};

function markOf(draft: DraftState, slot: DraftSlot): Mark | null {
  if (slot.identifier) return { kind: "key", text: "key" };
  if (slot.rule) return RULE_MARK[slot.rule.kind] ?? { kind: "worked", text: "worked out" };
  if (slot.binds) {
    return { kind: "role", text: bindingIn(draft, slot.binds)?.title ?? spoken(slot.binds) };
  }
  return null;
}

// ---- whether the numbers are checked ----------------------------------------

/** What the examples say about one worked-out field. A seal needs every one
 *  of them `checked`: a number some example expects, and gets. */
export type CheckState = "checked" | "failing" | "unchecked" | "unrun";
export interface Check { state: CheckState; text: string }

/** Every field this draft works out, as `Kind.field`. */
export function workedOut(draft: DraftState): string[] {
  const slotOf = new Map(draft.slots.map((s) => [s.name, s]));
  return draft.classes.flatMap((kind) => kind.slots
    .filter((name) => slotOf.get(name)?.rule)
    .map((name) => `${kind.name}.${name}`));
}

export function checksOf(draft: DraftState): Map<string, Check> {
  const out = new Map<string, Check>();
  const unchecked = new Set(draft.refusals
    .filter((r) => r.code === "column_unchecked").map((r) => r.where));
  for (const where of workedOut(draft)) {
    const [table, column] = where.split(".");
    const by = draft.examples.filter((e) => e.checks
      .some((c) => c.table === table && c.column === column));
    const wrong = by.filter((e) => e.checks
      .some((c) => c.table === table && c.column === column && !c.holds));
    if (wrong.length > 0) {
      out.set(where, { state: "failing", text: wrong.length === 1
        ? "an example says it should come out differently"
        : `${wrong.length} examples say it should come out differently` });
    } else if (by.length > 0) {
      out.set(where, { state: "checked", text: by.length === 1
        ? "checked by an example" : `checked by ${by.length} examples` });
    } else if (unchecked.has(where) || draft.examples.length === 0 || draft.examples_run) {
      out.set(where, { state: "unchecked", text: "no example checks it yet" });
    } else {
      out.set(where, { state: "unrun", text: "the examples have not been run" });
    }
  }
  return out;
}

const asksAbout = (draft: DraftState, where: string) =>
  draft.holes.filter((h) => h.where === where || h.where.startsWith(`${where}.`)).length;

/** Kinds of thing and the fields that point from one at another.
 *
 *  Everything drawn is already in the draft the server sent. Nothing is
 *  judged here — that is the gates' — this only decides what is a box, what
 *  is a line, and what each is called. */
export function mapOf(draft: DraftState, language: string = personLanguage()): Drawn {
  const slotOf = new Map(draft.slots.map((s) => [s.name, s]));
  const readOnly = draft.read_from ?? [];
  const words = wordsOf(draft, language);
  const label = new Map<string, string>();
  for (const kind of [...draft.classes, ...draft.borrowed, ...readOnly]) {
    label.set(kind.name, words.get(kind.name) ?? spoken(kind.name));
  }
  const checks = checksOf(draft);
  const nodes: MapNode[] = [];
  const edges: MapEdge[] = [];

  const line = (from: string, field: string, fieldSaid: string, to: string, own: boolean) => {
    const target = label.get(to) ?? to;
    edges.push({
      id: `${from}/${field}`, from, to, field, own, kind: "points",
      label: fieldSaid.toLowerCase() === target.toLowerCase() ? null : fieldSaid,
    });
  };

  for (const kind of draft.classes) {
    const fields: MapField[] = kind.slots.map((name) => {
      const slot = slotOf.get(name);
      if (!slot) {
        return {
          name, label: fieldLabel(name, kind.name), holds: "built on", points: null,
          mark: null, asks: false, check: null,
        };
      }
      const said = words.get(name) ?? fieldLabel(name, kind.name, slot.title);
      const points = slot.range && label.has(slot.range) ? slot.range : null;
      if (points) line(kind.name, name, said, points, true);
      return {
        name, label: said,
        holds: points ? label.get(points)! : holdsSaid(slot),
        points, mark: markOf(draft, slot), asks: asksAbout(draft, name) > 0,
        check: checks.get(`${kind.name}.${name}`) ?? null,
      };
    });
    nodes.push({
      name: kind.name, label: label.get(kind.name)!, own: true,
      description: kind.description, fills: kind.fills, fields,
      questions: asksAbout(draft, kind.name), module: null, rows: kind.has_rows,
      read: false,
    });
  }

  const reading = new Set(readOnly.map((k) => k.name));
  for (const kind of [...draft.borrowed, ...readOnly]) {
    const fields: MapField[] = kind.slots.map((slot) => {
      // A field this module adds to somebody else's kind (a facet): drawn on
      // their box, marked as this module's, and asked about like its own.
      const added = slotOf.get(slot.name)?.adds_to === kind.name ? slotOf.get(slot.name)! : null;
      const said = words.get(slot.name) ?? fieldLabel(slot.name, kind.name, added?.title);
      const points = slot.range && label.has(slot.range) ? slot.range : null;
      if (points) line(kind.name, slot.name, said, points, added !== null);
      return {
        name: slot.name, label: said,
        holds: points ? label.get(points)! : added ? holdsSaid(added) : holds(slot.range),
        points,
        mark: added ? { kind: "adds", text: "added here" }
          : slot.identifier ? { kind: "key", text: "key" } : null,
        asks: added ? asksAbout(draft, slot.name) > 0 : false,
        check: null,
      };
    });
    nodes.push({
      name: kind.name, label: label.get(kind.name)!, own: false,
      description: kind.description, fills: kind.fills, fields, questions: 0,
      module: pinText(kind.module), rows: true, read: reading.has(kind.name),
    });
  }

  // A rule that reads a kind nothing points at still joins the two: the
  // numbers in one come from the other. Drawn once per pair, and not at all
  // where a field already joins them.
  const joined = new Set(edges.map((e) => `${e.from}>${e.to}`));
  for (const table of draft.workings ?? []) {
    for (const column of table.columns) {
      for (const read of column.reads) {
        const pair = `${table.class}>${read.class}`;
        if (joined.has(pair) || !label.has(read.class)) continue;
        joined.add(pair);
        edges.push({
          id: `${table.class}/${column.name}/reads/${read.class}`,
          from: table.class, to: read.class, field: column.name, own: true, kind: "reads",
          label: column.kind === "aggregate" ? operatorSaid(column.operator) : "looks up",
        });
      }
    }
  }
  return { nodes, edges };
}

/** What an aggregate does, in a word: the compiler's operators are a closed set. */
export function operatorSaid(operator: string | undefined): string {
  return operator === "sum" || !operator ? "adds up" : spoken(operator).toLowerCase();
}

// ---- where the boxes go ---------------------------------------------------

export const BOX = { width: 248, head: 46, row: 24, foot: 14, shown: 7 };

/** How tall a box is drawn: the map needs it before the box exists. */
export function heightOf(node: MapNode, open: boolean): number {
  const rows = open || node.fields.length <= BOX.shown
    ? node.fields.length
    : BOX.shown + 1;
  const fills = node.fills.length > 0 || node.module ? 20 : 0;
  return BOX.head + fills + Math.max(rows, 1) * BOX.row + BOX.foot;
}

export interface Place { x: number; y: number }

/** A layered drawing: what a kind of thing points at sits above it, so what
 *  you build on is at the top and what you are building grows beneath it.
 *  Deterministic — the same module always opens in the same shape — and a
 *  box somebody moved by hand stays where they put it. */
export function arrange(
  nodes: MapNode[], edges: MapEdge[], open: ReadonlySet<string>,
  held: Readonly<Record<string, Place>> = {},
): Record<string, Place> {
  const g = new dagre.graphlib.Graph({ multigraph: true });
  g.setGraph({ rankdir: "BT", nodesep: 56, ranksep: 88, marginx: 24, marginy: 24 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const node of nodes) {
    g.setNode(node.name, { width: BOX.width, height: heightOf(node, open.has(node.name)) });
  }
  for (const edge of edges) {
    if (edge.from !== edge.to) g.setEdge(edge.from, edge.to, {}, edge.id);
  }
  dagre.layout(g);
  const out: Record<string, Place> = {};
  for (const node of nodes) {
    if (held[node.name]) { out[node.name] = held[node.name]; continue; }
    const at = g.node(node.name);
    // dagre gives centres; the map places boxes by their top-left corner.
    out[node.name] = {
      x: Math.round(at.x - BOX.width / 2),
      y: Math.round(at.y - heightOf(node, open.has(node.name)) / 2),
    };
  }
  return out;
}

/** The kinds of thing a box is joined to, either way. */
export function neighbours(edges: MapEdge[], name: string): Set<string> {
  const near = new Set([name]);
  for (const edge of edges) {
    if (edge.from === name) near.add(edge.to);
    if (edge.to === name) near.add(edge.from);
  }
  return near;
}

// ---- how the numbers are worked out -----------------------------------------
//
// The second way of looking at the same module. Not kinds of thing and what
// points at what, but fields and where each worked-out number comes from:
// what is recorded on the left, the rules in the middle, what they come to on
// the right, and around each field the kind of thing it belongs to. Nothing
// here is worked out again — which classes a sum reads is the compiler's
// reading, sent by the server as `workings`.

/** What a field is in the working-out of the numbers. */
export type CellRole = "key" | "recorded" | "sum" | "lookup" | "formula";

export interface Cell {
  id: string;
  kind: string;
  field: string;
  label: string;
  role: CellRole;
  /** How it comes to be, in a sentence that fits under it. */
  how: string;
  check: Check | null;
  /** The formula with the names of the fields it uses, for a formula. */
  formula: string | null;
}

export interface Group { name: string; label: string; own: boolean; module: string | null }

export type FlowKind = "sum" | "lookup" | "formula" | "row";
export interface Flow { id: string; from: string; to: string; kind: FlowKind; label: string | null }

export interface Workings { groups: Group[]; cells: Cell[]; flows: Flow[] }

const cellId = (kind: string, field: string) => `${kind}.${field}`;

/** What a worked-out field says when its rule is sealed and not computed yet. */
export const NOT_YET = "Not computed yet: the rule is sealed, the compiler does not follow it yet";

/** Every number this draft works out, the fields it is worked out from, and
 *  a line from each one that feeds it. Empty for a draft that works nothing
 *  out — nothing is drawn rather than something empty. */
export function workingsOf(draft: DraftState): Workings {
  const slotOf = new Map(draft.slots.map((s) => [s.name, s]));
  const theirs = new Map<string, DraftBorrowed>(
    [...draft.borrowed, ...(draft.read_from ?? [])].map((k) => [k.name, k]));
  const checks = checksOf(draft);
  const groups = new Map<string, Group>();
  const cells = new Map<string, Cell>();
  const flows = new Map<string, Flow>();

  const group = (kind: string) => {
    if (groups.has(kind)) return;
    const from = theirs.get(kind);
    groups.set(kind, {
      name: kind, label: spoken(kind), own: !from && draft.classes.some((c) => c.name === kind),
      module: from ? pinText(from.module) : null,
    });
  };
  const called = (kind: string, field: string) =>
    fieldLabel(field, kind, theirs.has(kind) ? null : slotOf.get(field)?.title);
  const cell = (kind: string, field: string, role: CellRole, how: string, formula: string | null = null) => {
    const id = cellId(kind, field);
    group(kind);
    const was = cells.get(id);
    // A field something else reads is "recorded" only until we learn it is
    // itself worked out; the worked-out reading wins.
    if (was && (was.role !== "recorded" || role === "recorded")) return id;
    cells.set(id, {
      id, kind, field, label: called(kind, field), role, how, formula,
      check: checks.get(id) ?? null,
    });
    return id;
  };
  const flow = (from: string, to: string, kind: FlowKind, label: string | null) => {
    const id = `${from}>${to}`;
    if (!flows.has(id)) flows.set(id, { id, from, to, kind, label });
  };

  for (const table of draft.workings ?? []) {
    const kind = table.class;
    const kindSaid = spoken(kind).toLowerCase();
    for (const key of table.keys) {
      const range = slotOf.get(key)?.range;
      const thing = range && (theirs.has(range) || draft.classes.some((c) => c.name === range))
        ? spoken(range).toLowerCase() : called(kind, key).toLowerCase();
      cell(kind, key, "key", `One row for each ${thing}`);
    }
    for (const column of table.columns) {
      const at = cellId(kind, column.name);
      if (column.awaiting) {
        // Drawn as it reads, and said first: the compiler does not follow it yet.
        cell(kind, column.name, column.kind === "aggregate" ? "sum"
          : column.kind === "parameter" ? "lookup" : "formula", NOT_YET);
      }
      if (column.kind === "aggregate") {
        const what = column.reads.map((r) =>
          `${r.fields.map((f) => called(r.class, f).toLowerCase()).join(" and ")} of every ${spoken(r.class).toLowerCase()}`);
        cell(kind, column.name, "sum",
          `${spoken(operatorSaid(column.operator))} the ${what.join(", and the ") || "records"}`);
        for (const read of column.reads) {
          for (const field of read.fields) {
            flow(cell(read.class, field, "recorded", recordedOn(read.class)), at, "sum",
              operatorSaid(column.operator));
          }
          for (const [key, by] of Object.entries(read.by)) {
            if (!by) continue;
            flow(cell(read.class, by, "recorded",
              `Says which row each ${spoken(read.class).toLowerCase()} counts towards`),
              cellId(kind, key), "row", "which row");
          }
        }
      } else if (column.kind === "parameter") {
        const of = column.of ? called(kind, column.of).toLowerCase() : kindSaid;
        cell(kind, column.name, "lookup", `Looked up on the ${of} of the row`);
        for (const read of column.reads) {
          for (const field of read.fields) {
            flow(cell(read.class, field, "recorded", recordedOn(read.class)), at, "lookup", "looked up");
          }
        }
      } else {
        const text = String(slotOf.get(column.name)?.rule?.spec ?? "");
        const uses = [...new Set([...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]))];
        const formula = arithmetic(text.replace(/\{(\w+)\}/g, (_, n: string) => called(kind, n)));
        cell(kind, column.name, "formula", `Worked out as ${formula}`, formula);
        for (const name of uses) {
          // A field a formula uses that no rule fills is one somebody types.
          const used = cell(kind, name, "recorded", recordedOn(kind));
          flow(used, at, "formula", null);
        }
      }
    }
  }

  // Groups in the order the map reads: what is recorded, then what is built.
  const ordered = [...groups.values()].sort((a, b) => Number(a.own) - Number(b.own)
    || a.name.localeCompare(b.name));
  return { groups: ordered, cells: [...cells.values()], flows: [...flows.values()] };
}

const recordedOn = (kind: string) => `Recorded on each ${spoken(kind).toLowerCase()}`;

/** A formula as it is read aloud: the minus and times signs of arithmetic. */
export function arithmetic(text: string): string {
  return text.replace(/\s*\*\s*/g, " × ").replace(/\s+-\s+/g, " − ").replace(/\s*\/\s*/g, " ÷ ");
}

// ---- one example, worked through ------------------------------------------------

/** One row of one table at one moment that an example says what it comes to. */
export interface Moment {
  key: string;
  example: string;
  table: string;
  row: string;
  at: string | null;
  label: string;
}

/** A day as people write it, for a moment an example names. */
export function daySaid(value: string | null): string {
  if (!value) return "";
  const day = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00Z` : value;
  const when = new Date(day);
  if (Number.isNaN(when.getTime())) return value;
  return when.toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}

export function momentsOf(draft: DraftState): Moment[] {
  const out: Moment[] = [];
  const tables = new Set((draft.workings ?? []).map((w) => w.class));
  for (const example of draft.examples) {
    const seen = new Set<string>();
    for (const check of example.checks) {
      const key = `${example.name}|${check.table}|${check.row}|${check.at ?? ""}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const table = tables.size > 1 ? `${spoken(check.table)}, ` : "";
      out.push({
        key, example: example.name, table: check.table, row: check.row, at: check.at,
        label: `${table}${check.row}${check.at ? `, on ${daySaid(check.at)}` : ""}`,
      });
    }
  }
  return out;
}

/** What one field shows for one moment of one example. */
export interface Shown {
  /** The number it came to, or the one value recorded. */
  value: string | null;
  /** What the example says it should come to, for a worked-out field. */
  expected: string | null;
  holds: boolean | null;
  /** Each recorded value that went into a sum, and when it was recorded. */
  items: { value: string; when: string | null; record: string }[];
  /** A formula with the numbers it used in place of the names. */
  sum: string | null;
  /** Said under the value: since when it has held, or why there is none. */
  note: string | null;
}

const NOTHING: Shown = { value: null, expected: null, holds: null, items: [], sum: null, note: null };

/** Up to the end of the day a moment names, as an example reads its tables. */
function byMoment(at: string | null): (when: string | null) => boolean {
  if (!at) return () => true;
  const end = /^\d{4}-\d{2}-\d{2}$/.test(at) ? `${at}T23:59:59.999Z` : at;
  const limit = Date.parse(end);
  return (when) => {
    if (!when) return true;
    const start = /^\d{4}-\d{2}-\d{2}$/.test(when) ? `${when}T00:00:00Z` : when;
    const t = Date.parse(start);
    return Number.isNaN(t) || Number.isNaN(limit) || t <= limit;
  };
}

/** Every thing an example records, as it stands at a moment: its kind, each
 *  field's latest value and when that value was recorded. */
function standing(example: ExampleResult, at: string | null) {
  const inTime = byMoment(at);
  const out = new Map<string, { kind: string | null; first: string | null;
    facts: Map<string, { value: unknown; when: string | null }> }>();
  for (const record of example.recorded ?? []) {
    if (!inTime(record.when)) continue;
    const held = out.get(record.record) ?? { kind: record.class, first: record.when, facts: new Map() };
    held.kind = held.kind ?? record.class;
    for (const [field, value] of Object.entries(record.facts)) {
      held.facts.set(field, { value, when: record.when });
    }
    out.set(record.record, held);
  }
  return out;
}

const valueSaid = (value: unknown): string | null =>
  value === null || value === undefined || value === "empty" ? null : String(value);

const signed = (value: string) => (/^\d/.test(value) && Number(value) !== 0 ? `+${value}` : value);

/** One moment of one example, worked through every field on the drawing:
 *  the records that went in, and against each worked-out field the number
 *  the example expects beside the number the draft made of it. */
export function walkThrough(draft: DraftState, w: Workings, moment: Moment): Map<string, Shown> {
  const out = new Map<string, Shown>();
  const example = draft.examples.find((e) => e.name === moment.example);
  if (!example) return out;
  const things = standing(example, moment.at);
  const table = (draft.workings ?? []).find((t) => t.class === moment.table);
  const checkOf = (column: string) => example.checks.find((c) => c.table === moment.table
    && c.row === moment.row && (c.at ?? null) === (moment.at ?? null) && c.column === column);
  const got = new Map<string, string | null>();

  for (const cell of w.cells) {
    if (cell.kind !== moment.table) continue;
    if (cell.role === "key") {
      out.set(cell.id, { ...NOTHING, value: moment.row });
      continue;
    }
    const check = checkOf(cell.field);
    if (check) {
      got.set(cell.field, valueSaid(check.got));
      out.set(cell.id, {
        ...NOTHING, value: valueSaid(check.got), expected: valueSaid(check.expected),
        holds: check.holds,
      });
    } else if (cell.role === "recorded") {
      const held = things.get(moment.row)?.facts.get(cell.field);
      out.set(cell.id, { ...NOTHING, value: valueSaid(held?.value) });
    }
  }

  // Formulas with their numbers, once every number is known.
  for (const cell of w.cells) {
    if (cell.kind !== moment.table || cell.role !== "formula") continue;
    const text = String(draft.slots.find((s) => s.name === cell.field)?.rule?.spec ?? "");
    const used = [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]);
    const shown = out.get(cell.id);
    if (!shown || used.some((n) => !got.get(n))) continue;
    out.set(cell.id, {
      ...shown, sum: arithmetic(text.replace(/\{(\w+)\}/g, (_, n: string) => got.get(n)!)),
    });
  }

  // What was recorded, as far as it went into this row: the records a sum
  // counted towards it, and the value a lookup found on the thing it is about.
  const single = table && table.keys.length === 1 ? table.keys[0] : null;
  for (const column of table?.columns ?? []) {
    for (const read of column.reads) {
      const mine = [...things.entries()].filter(([, t]) => t.kind === read.class);
      if (column.kind === "aggregate") {
        const by = single ? read.by[single] : null;
        // A key one record away: the record `by` names, and its own field.
        const via = single ? read.via?.[single] : undefined;
        const keyOf = (t: { facts: Map<string, { value: unknown }> }) => {
          const named = valueSaid(t.facts.get(by!)?.value);
          if (!via) return named;
          const far = named === null ? undefined : things.get(named);
          return valueSaid(via.map((f) => far?.facts.get(f)?.value).find((v) => valueSaid(v) !== null));
        };
        const counted = mine.filter(([, t]) => !by || keyOf(t) === moment.row);
        for (const field of read.fields) {
          const items = counted.flatMap(([record, t]) => {
            const v = valueSaid(t.facts.get(field)?.value);
            return v === null ? [] : [{ value: signed(v), when: t.first, record }];
          });
          out.set(cellId(read.class, field), { ...NOTHING, items,
            note: items.length === 0 ? "nothing recorded for this row" : null });
        }
        if (by) {
          out.set(cellId(read.class, by), { ...NOTHING,
            value: counted.length > 0 ? (via ? valueSaid(counted[0][1].facts.get(by)?.value) : moment.row) : null,
            note: counted.length === 1 ? "1 record says so"
              : counted.length > 1 ? `${counted.length} records say so` : null });
        }
      } else if (column.kind === "parameter") {
        const thing = mine.find(([record]) => record === moment.row)?.[1];
        for (const field of read.fields) {
          const held = thing?.facts.get(field);
          const v = valueSaid(held?.value);
          out.set(cellId(read.class, field), { ...NOTHING, value: v,
            note: v === null ? "not recorded"
              : held?.when ? `since ${daySaid(held.when)}` : "from the start" });
        }
      }
    }
  }
  return out;
}

/** Everything a number comes from and everything that comes from it: what
 *  lights up when somebody points at one field. */
export function lineage(flows: Flow[], id: string): Set<string> {
  const out = new Set([id]);
  const walk = (from: string, up: boolean) => {
    for (const flow of flows) {
      const [here, there] = up ? [flow.to, flow.from] : [flow.from, flow.to];
      if (here === from && !out.has(there)) { out.add(there); walk(there, up); }
    }
  };
  walk(id, true);
  walk(id, false);
  return out;
}

// ---- where the fields go ------------------------------------------------------

export const CELL = { width: 236, head: 66, line: 20, pad: 12 };
export const GROUP = { head: 40, side: 14, foot: 14 };

/** How many lines of example a field needs room for, at the busiest moment
 *  of any example — so changing the example never moves the drawing. */
export function roomFor(draft: DraftState, w: Workings): Record<string, number> {
  const out: Record<string, number> = {};
  for (const cell of w.cells) out[cell.id] = 0;
  for (const moment of momentsOf(draft)) {
    for (const [id, shown] of walkThrough(draft, w, moment)) {
      const lines = Math.min(shown.items.length, 5) + (shown.items.length > 5 ? 1 : 0)
        + (shown.value !== null || shown.expected !== null || shown.holds !== null ? 1 : 0)
        + (shown.sum ? 1 : 0) + (shown.note ? 1 : 0);
      out[id] = Math.max(out[id] ?? 0, lines);
    }
  }
  return out;
}

export const cellHeight = (lines: number) => CELL.head + lines * CELL.line + CELL.pad;

export interface Rect { x: number; y: number; width: number; height: number }
export interface Laid { groups: Record<string, Rect>; cells: Record<string, Place> }

/** Left to right, the way it is worked out: recorded, then rules, then what
 *  they come to. Each field sits inside the box of its kind; a cell's place
 *  is given inside its group, the way the drawing nests them. */
export function arrangeWorkings(w: Workings, room: Record<string, number>): Laid {
  const g = new dagre.graphlib.Graph({ compound: true, multigraph: true });
  g.setGraph({ rankdir: "LR", nodesep: 72, ranksep: 120, marginx: 24, marginy: 24 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const group of w.groups) g.setNode(`group:${group.name}`, {});
  for (const cell of w.cells) {
    g.setNode(cell.id, { width: CELL.width, height: cellHeight(room[cell.id] ?? 0) });
    g.setParent(cell.id, `group:${cell.kind}`);
  }
  for (const flow of w.flows) g.setEdge(flow.from, flow.to, {}, flow.id);
  dagre.layout(g);

  const groups: Record<string, Rect> = {};
  const absolute: Record<string, Place> = {};
  for (const cell of w.cells) {
    const at = g.node(cell.id);
    absolute[cell.id] = {
      x: Math.round(at.x - CELL.width / 2),
      y: Math.round(at.y - cellHeight(room[cell.id] ?? 0) / 2),
    };
  }
  for (const group of w.groups) {
    const mine = w.cells.filter((c) => c.kind === group.name);
    if (mine.length === 0) continue;
    const left = Math.min(...mine.map((c) => absolute[c.id].x)) - GROUP.side;
    const top = Math.min(...mine.map((c) => absolute[c.id].y)) - GROUP.head;
    const right = Math.max(...mine.map((c) => absolute[c.id].x + CELL.width)) + GROUP.side;
    const bottom = Math.max(...mine.map((c) => absolute[c.id].y + cellHeight(room[c.id] ?? 0))) + GROUP.foot;
    groups[group.name] = { x: left, y: top, width: right - left, height: bottom - top };
  }
  const cells: Record<string, Place> = {};
  for (const cell of w.cells) {
    const box = groups[cell.kind];
    cells[cell.id] = { x: absolute[cell.id].x - box.x, y: absolute[cell.id].y - box.y };
  }
  return { groups, cells };
}

// ---- what changed -------------------------------------------------------------

export type ChangeHow = Change["how"];

/** A change in a word, as a mark beside what changed. */
export const CHANGE_SAID: Record<ChangeHow, string> = {
  added: "new", changed: "changed", removed: "removed",
};

/** What the map marks: kinds, and fields as `Kind.field`, that are new or
 *  different — and which of them changed just now, while somebody watches. */
export interface Marks {
  kinds: Map<string, ChangeHow>;
  fields: Map<string, ChangeHow>;
  fresh: Set<string>;
}

export function marksOf(changes: Change[], now: Change[] = []): Marks {
  const kinds = new Map<string, ChangeHow>();
  const fields = new Map<string, ChangeHow>();
  for (const change of changes) {
    if (change.what === "kind") kinds.set(change.name, change.how);
    if (change.what === "field") fields.set(change.name, change.how);
  }
  const fresh = new Set(now.filter((c) => c.what === "kind" || c.what === "field")
    .map((c) => c.name));
  return { kinds, fields, fresh };
}

export interface ChangedField { name: string; label: string; how: ChangeHow; check: Check | null }
export interface ChangedKind { name: string; label: string; how: ChangeHow; fields: ChangedField[] }

/** Changes as a person reads them: by kind of thing, each with its fields. */
export interface Changed {
  kinds: ChangedKind[];
  examples: { name: string; label: string; how: ChangeHow }[];
  pins: { name: string; how: ChangeHow }[];
  module: boolean;
  /** The whole of it in a few words: "1 new kind, 4 new fields". */
  said: string;
}

const counted = (n: number, one: string, many: string, how: string) =>
  n === 0 ? null : `${n} ${how ? `${how} ` : ""}${n === 1 ? one : many}`;

export function changedOf(
  draft: DraftState | null, changes: Change[], words: Map<string, string> = new Map(),
): Changed {
  const called = (name: string) => words.get(name) ?? spoken(name);
  const titleOf = new Map((draft?.slots ?? []).map((s) => [s.name, s.title]));
  const checks = draft ? checksOf(draft) : new Map<string, Check>();
  const kinds = new Map<string, ChangedKind>();
  const examples: Changed["examples"] = [];
  const pins: Changed["pins"] = [];
  let module = false;
  for (const change of changes) {
    if (change.what === "kind") {
      kinds.set(change.name, {
        name: change.name, label: called(change.name), how: change.how, fields: [],
      });
    } else if (change.what === "field") {
      const [kind, slot] = change.name.split(".");
      const held = kinds.get(kind) ?? { name: kind, label: called(kind), how: "changed" as ChangeHow, fields: [] };
      kinds.set(kind, held);
      held.fields.push({
        name: change.name, how: change.how,
        label: words.get(slot)
          ?? fieldLabel(slot, kind, change.how === "removed" ? null : titleOf.get(slot)),
        check: change.how === "removed" ? null : checks.get(change.name) ?? null,
      });
    } else if (change.what === "example") {
      examples.push({ name: change.name, label: spoken(change.name), how: change.how });
    } else if (change.what === "pin") {
      pins.push({ name: change.name, how: change.how });
    } else {
      module = true;
    }
  }
  const list = [...kinds.values()];
  const fields = list.flatMap((k) => k.fields);
  const of = <T extends { how: ChangeHow }>(items: T[], how: ChangeHow) =>
    items.filter((i) => i.how === how).length;
  const said = [
    counted(of(list, "added"), "kind", "kinds", "new"),
    counted(list.filter((k) => k.how === "changed" && k.fields.length === 0).length,
      "kind changed", "kinds changed", ""),
    counted(of(list, "removed"), "kind removed", "kinds removed", ""),
    counted(of(fields, "added"), "field", "fields", "new"),
    counted(of(fields, "changed"), "field changed", "fields changed", ""),
    counted(of(fields, "removed"), "field removed", "fields removed", ""),
    counted(of(examples, "added"), "example", "examples", "new"),
    counted(of(examples, "changed"), "example changed", "examples changed", ""),
    counted(of(examples, "removed"), "example removed", "examples removed", ""),
    counted(of(pins, "added"), "module built on", "modules built on", "new"),
    counted(of(pins, "removed"), "module no longer built on", "modules no longer built on", ""),
    module ? "its description" : null,
  ].filter((s): s is string => s !== null).join(", ");
  return { kinds: list, examples, pins, module, said: said || "nothing" };
}

/** The requests in a conversation that changed one kind of thing, latest
 *  last: where a map sends somebody who asks "how did this come about?". */
export function turnsAbout(
  turns: { touched?: Change[] }[], kind: string,
): { turn: number; how: ChangeHow }[] {
  return turns.flatMap((turn, i) => {
    const line = (turn.touched ?? []).find((c) => c.what === "kind" && c.name === kind);
    return line ? [{ turn: i, how: line.how }] : [];
  });
}

// ---- what the agent says, as a page reads it ---------------------------------
//
// The agent writes the way a chat is written: paragraphs, lists, a word in
// **bold** or in `code`. A page shows that as it is meant, not as asterisks —
// read here into plain pieces, never handed to the browser as markup.

export interface Piece { text: string; bold?: boolean; code?: boolean; italic?: boolean }
export interface ListItem { depth: number; marker: string; pieces: Piece[] }
export type Block =
  | { kind: "paragraph"; lines: Piece[][] }
  | { kind: "list"; items: ListItem[] };

const INLINE = /(\*\*[^*\n]+?\*\*|__[^_\n]+?__|`[^`\n]+`|\*[^*\s][^*\n]*?\*)/g;

/** One line's bold, italic and code, the rest as it is. */
export function piecesOf(line: string): Piece[] {
  const out: Piece[] = [];
  let at = 0;
  for (const found of line.matchAll(INLINE)) {
    const index = found.index ?? 0;
    if (index > at) out.push({ text: line.slice(at, index) });
    const token = found[0];
    if (token.startsWith("**") || token.startsWith("__")) out.push({ text: token.slice(2, -2), bold: true });
    else if (token.startsWith("`")) out.push({ text: token.slice(1, -1), code: true });
    else out.push({ text: token.slice(1, -1), italic: true });
    at = index + token.length;
  }
  if (at < line.length) out.push({ text: line.slice(at) });
  return out;
}

const ITEM = /^(\s*)([-*•]|\d+[.)])\s+(.*)$/;

/** A message as paragraphs and lists. A list item keeps its own marker — "2."
 *  stays "2." — and how far it is indented; a heading is a line in bold. */
export function blocksOf(text: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: Piece[][] = [];
  let list: ListItem[] = [];
  const close = () => {
    if (paragraph.length) blocks.push({ kind: "paragraph", lines: paragraph });
    if (list.length) blocks.push({ kind: "list", items: list });
    paragraph = [];
    list = [];
  };
  for (const raw of text.replace(/\r\n/g, "\n").split("\n")) {
    if (!raw.trim()) { close(); continue; }
    const item = raw.match(ITEM);
    if (item) {
      if (paragraph.length) { blocks.push({ kind: "paragraph", lines: paragraph }); paragraph = []; }
      const marker = /^\d/.test(item[2]) ? item[2].replace(")", ".") : "•";
      list.push({ depth: item[1].replace(/\t/g, "  ").length >= 2 ? 1 : 0, marker,
                  pieces: piecesOf(item[3]) });
      continue;
    }
    if (list.length) { blocks.push({ kind: "list", items: list }); list = []; }
    const heading = raw.match(/^\s*#{1,6}\s+(.*)$/);
    paragraph.push(heading ? [{ text: heading[1].replace(/\*\*/g, "").trim(), bold: true }]
      : piecesOf(raw.trim()));
  }
  close();
  return blocks;
}

// ---- the questions a draft stands in, as a person is asked them -------------

/** The example a question is about, from where it stands ("example flour: …"). */
export function exampleOf(where: string): string | null {
  const found = where.match(/^example ([^:\s]+)/);
  return found ? found[1] : null;
}

/** The questions to put to a person, each asked once. An example waiting for
 *  the rules that work its numbers out stands in one question for every number
 *  it expects; that is one thing to say, not one per number. */
export function askedOnce<H extends { kind: string; where: string }>(
  holes: H[], waiting: Set<string>,
): H[] {
  const seen = new Set<string>();
  return holes.filter((hole) => {
    const example = exampleOf(hole.where);
    if (hole.kind !== "example_failed" || !example || !waiting.has(example)) return true;
    if (seen.has(example)) return false;
    seen.add(example);
    return true;
  });
}

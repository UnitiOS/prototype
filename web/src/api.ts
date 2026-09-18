// Types and fetchers for the kernel read API. Every read that depends on time
// carries both clocks, so a view is always reproducible from its URL.

export type Status =
  | "winner" | "outranked" | "candidate"
  | "not_yet_valid" | "not_recorded" | "revoked" | "retraction";

export interface Named { id: string; uri: string | null }

export interface Assertion {
  id: string; seq: number;
  subject: Named; predicate: Named;
  value: string | null; ref: Named | null;
  valid_from: string; recorded_at: string;
  revokes: string | null; revoked_by: string[];
  intent_id: string; source: string;
  confidence: string | null; authority: string | null;
  ontology_version: string; status: Status;
}

export interface Summary {
  assertions: number; intents: number; entities: number; registered: number;
  revocations: number;
  first_valid_from: string | null; last_valid_from: string | null;
  first_recorded_at: string | null; last_recorded_at: string | null;
}

export interface EntityRow {
  id: string; uri: string | null; minted_at: string;
  assertions: number; predicates: number;
}

export interface Fact { predicate: Named; standing: string | null; rows: Assertion[] }

export interface Entity {
  id: string; uri: string | null; minted_at: string; intent_id: string;
  facts: Fact[]; referenced_by: Assertion[];
}

export interface IntentRow {
  id: string; occurred_at: string; actor_id: string; agent_id: string | null;
  action_name: string; reason_code: string | null; note: string | null;
  assertions: number; minted: number; recorded_at: string | null;
  ontology_version: string | null;
}

export interface IntentDetail {
  id: string; occurred_at: string; actor_id: string; agent_id: string | null;
  action_name: string; reason_code: string | null; note: string | null;
  minted: Named[]; assertions: Assertion[];
}

export interface Point {
  id: string; seq: number; subject_id: string;
  valid_from: string; recorded_at: string; status: Status;
}

export interface Clocks { validAt: Date; asOf: Date }

// ---- refusals -------------------------------------------------------------
// A refusal is data before it is a sentence, so the page can draw the way out
// rather than print a paragraph and leave the reader to work it out. `options`
// is the finite set of valid answers, computed from the graph: in Studio it
// becomes a list to pick from, and here it is at least visible.

export interface Repair { do: string; where: string | null; options: string[] }

export interface Refusal {
  code: string; means: string; gate: string;
  where: string; expected: string; got: string; sentence: string;
  repairs: Repair[];
}

export class ApiError extends Error {
  readonly refusal: Refusal | null;

  constructor(message: string, refusal: Refusal | null = null) {
    super(message);
    this.refusal = refusal;
  }
}

function clockParams(c: Clocks): Record<string, string> {
  return { valid_at: c.validAt.toISOString(), as_of: c.asOf.toISOString() };
}

async function get<T>(path: string, params: Record<string, string | number> = {}): Promise<T> {
  const query = new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)]),
  ).toString();
  let response: Response;
  try {
    response = await fetch(query ? `${path}?${query}` : path);
  } catch {
    throw new ApiError("The API is not reachable. Start it with uvicorn on port 8200.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(body?.error ?? `The API answered ${response.status}.`,
                       body?.refusal ?? null);
  }
  return body as T;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError("The API is not reachable. Start it with uvicorn on port 8200.");
  }
  const answer = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(answer?.error ?? `The API answered ${response.status}.`,
                       answer?.refusal ?? null);
  }
  return answer as T;
}

export const api = {
  summary: () => get<Summary>("/api/kernel/summary"),
  entities: (search: string) =>
    get<EntityRow[]>("/api/kernel/entities", search ? { search } : {}),
  entity: (id: string, c: Clocks) => get<Entity>(`/api/kernel/entities/${id}`, clockParams(c)),
  intents: (offset: number, limit: number) =>
    get<{ total: number; intents: IntentRow[] }>("/api/kernel/intents", { offset, limit }),
  intent: (id: string, c: Clocks) => get<IntentDetail>(`/api/kernel/intents/${id}`, clockParams(c)),
  log: (c: Clocks, offset: number, limit: number) =>
    get<{ total: number; assertions: Assertion[] }>("/api/kernel/log", { ...clockParams(c), offset, limit }),
  plane: (c: Clocks) => get<{ total: number; points: Point[] }>("/api/kernel/plane", clockParams(c)),
};

// ---------------------------------------------------------------- modules

export interface Pin { name: string; version: string }

export interface ModuleVersionRow {
  version: string; valid_from: string; sealed_at: string; supersedes: string | null;
  imports: Pin[]; classes: number; slots: number;
}

export interface ModuleRow {
  name: string; title: string | null; purpose: string | null; description: string | null;
  versions: ModuleVersionRow[]; latest: string | null; draft: boolean;
}

export interface ModuleGraph {
  nodes: (Pin & { latest: boolean; purpose: string | null; sealed_at: string })[];
  edges: { from: Pin; to: Pin; kind: "imports" | "supersedes" }[];
}

export interface ClassItem {
  name: string; is_a: string | null; description: string | null; slots: string[]; from: Pin;
}

export interface SlotItem {
  name: string; slot_uri: string | null; range: string | null;
  identifier: boolean; required: boolean; designates_type: boolean;
  rule: "aggregate" | "parameter" | "expression" | null;
  rule_spec: RuleSpec | null;
  title: string; description: string | null; from: Pin; registered: boolean | null;
}

export interface RuleSpec {
  kind: "aggregate" | "parameter" | "expression";
  expression?: string;
  spec?: Record<string, unknown>;
}

export interface ModuleVersion {
  name: string; version: string; title: string | null;
  purpose: string | null; description: string | null;
  valid_from: string; sealed_at: string; supersedes: string | null; latest: string | null;
  imports: (Pin & { latest: string | null })[]; imported_by: Pin[]; closure: Pin[];
  classes: ClassItem[]; slots: SlotItem[]; transcript: string | null;
}

interface Change { from: unknown; to: unknown }

export interface ModuleDiff {
  name: string; from: string; to: string;
  diff: {
    imports: { added: string[]; removed: string[] };
    classes: {
      added: string[]; removed: string[];
      changed: { name: string; changes: Record<string, Change>; slots_added: string[]; slots_removed: string[] }[];
    };
    slots: {
      added: string[]; removed: string[];
      renamed: { from: string; to: string; slot_uri: string; changes: Record<string, Change> }[];
      changed: { name: string; changes: Record<string, Change> }[];
    };
  };
}

export interface ClassNode {
  name: string; module: Pin; is_a: string | null;
  fills: string[]; abstract: boolean;
  description: string | null;
  shape: "derived" | "stated" | "unstatable" | "role"; slots: string[];
}

export interface ClassEdge {
  from: string; to: string;
  kind: "is_a" | "fills" | "reference" | "aggregate" | "parameter"; label: string;
}

export interface ClassGraph {
  name: string; version: string;
  modules: (Pin & { purpose: string | null; title: string | null })[];
  nodes: ClassNode[]; edges: ClassEdge[];
}

export const modulesApi = {
  list: () => get<ModuleRow[]>("/api/modules"),
  graph: () => get<ModuleGraph>("/api/modules/graph"),
  version: (name: string, version: string) => get<ModuleVersion>("/api/modules/version", { name, version }),
  diff: (name: string, from: string, to: string) => get<ModuleDiff>("/api/modules/diff", { name, from, to }),
  classes: (name: string, version: string) => get<ClassGraph>("/api/modules/classes", { name, version }),
};

// ------------------------------------------------------------ applications

export interface TableRow {
  class: string; table: string; shape: "grouped" | "entities";
  module: Pin | null; columns: number;
}

export interface Application {
  name: string; version: string; title: string | null;
  purpose: string | null; description: string | null;
  modules: (Pin & { purpose: string | null })[];
  tables: TableRow[];
}

export interface ColumnRule {
  kind: "aggregate" | "parameter" | "expression";
  operator?: string; over?: string; measure?: string; by?: Record<string, string>;
  // What the rule was written against, and what it resolved to. They differ
  // whenever the rule names a role, and that difference is the swappable seam.
  covers?: string[]; measure_uris?: string[]; by_uris?: Record<string, string[]>;
  of?: string; slot?: string; slot_uris?: string[]; expression?: string;
}

export interface Column {
  name: string; title: string; type: string;
  kind: "identity" | "key" | "stated" | "aggregate" | "parameter" | "expression" | "unfilled";
  description: string; module: Pin | null; rule: ColumnRule | null;
}

export interface Projection {
  name: string; version: string; class: string; table: string;
  shape: "grouped" | "entities"; keys: string[];
  columns: Column[]; rows: (string | null)[][]; sql: string;
  valid_at: string; as_of: string;
}

export interface Statement {
  assertion_id: string; intent_id: string;
  subject_id: string; subject_uri: string | null;
  predicate: string; value: string | null; names_entity: boolean;
  valid_from: string; recorded_at: string;
  source: string; ontology_version: string;
}

export interface CellSource {
  name: string; version: string; class: string; column: string;
  kind: Column["kind"]; keys: Record<string, string>;
  statements: Statement[]; reads: string[]; cut_off: boolean;
  entity: { uri: string; id: string } | null;
  over?: string; covers?: string[]; operator?: string; of?: string; expression?: string;
  valid_at: string; as_of: string;
}

export interface FormField {
  name: string; title: string; range: string | null;
  required: boolean; ref: boolean; description: string;
  module: Pin | null;
  options: { uri: string; label: string }[];
  options_from: string | null;
}

export interface FormSpec {
  name: string; version: string; class: string; label: string;
  type_slot: string | null; fields: FormField[];
}

export interface Written {
  intent_id: string; subject_id: string; assertions: number; minted: number;
  class: string; subject: string; ontology_version: string;
}

// ---- roles, and what a swap would cost ------------------------------------

export interface Binding {
  name: string; required: boolean; range: string | null; description: string;
}

export interface Role {
  name: string; module: Pin; description: string;
  bindings: Binding[];
  filled_by: { class: string; module: Pin; bindings: Record<string, string | null> }[];
}

export interface Roles {
  name: string; version: string; modules: Pin[]; roles: Role[];
}

export interface FitReport {
  name: string; from: string; to: string;
  pins: { removed: Pin[]; added: Pin[]; kept: Pin[] };
  roles: { name: string; before: string[]; after: string[];
           status: "unchanged" | "gained" | "lost" | "replaced" }[];
  rules: { class: string; column: string; kind: string; over: string;
           covered_before: string[]; covered_after: string[];
           reads_before: string[]; reads_after: string[];
           status: "unchanged" | "rebound" }[];
  // A rule that does not survive the move, with the refusal that stopped it —
  // repairs and all, so "what must I add" is answered on the page. Null where
  // there is no gate to ask: the new closure simply has nothing to say here.
  dark: { class: string; column: string | null; why: string; refusal: Refusal | null }[];
  orphaned: { uri: string; module: Pin; held: number }[];
  orphaned_statements: number;
  clean: boolean;
}

export interface CheckReport {
  name: string; version: string; clean: boolean;
  tables: { class: string; holds: boolean; shape: string | null;
            columns: number; unfilled: string[] }[];
  refusals: (Refusal & { class: string })[];
}

export const appApi = {
  read: (name: string, version: string) => get<Application>("/api/app", { name, version }),
  roles: (name: string, version: string) => get<Roles>("/api/app/roles", { name, version }),
  check: (name: string, version: string) => get<CheckReport>("/api/app/check", { name, version }),
  fit: (name: string, version: string, against: string) =>
    get<FitReport>("/api/app/fit", { name, version, against }),
  projection: (name: string, version: string, klass: string, c: Clocks) =>
    get<Projection>("/api/app/projection", { name, version, class: klass, ...clockParams(c) }),
  cell: (name: string, version: string, klass: string, column: string,
         keys: Record<string, string>, c: Clocks) =>
    get<CellSource>("/api/app/cell", {
      name, version, class: klass, column, ...clockParams(c),
      ...Object.fromEntries(Object.entries(keys).map(([k, v]) => [`key.${k}`, v])),
    }),
  form: (name: string, version: string, klass: string, c: Clocks) =>
    get<FormSpec>("/api/app/form", { name, version, class: klass, ...clockParams(c) }),
  state: (body: {
    name: string; version: string; class: string; subject: string;
    actor: string; valid_from: string; values: Record<string, string>; note?: string;
  }) => post<Written>("/api/app/state", body),
};

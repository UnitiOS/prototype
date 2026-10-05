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

/** Which of the four kinds a module is (DESIGN_NOTES.md §15.2). */
export type ModuleKind = "core" | "library" | "module" | "application";

export interface ModuleGraph {
  nodes: (Pin & { latest: boolean; purpose: string | null; sealed_at: string;
                  kind: ModuleKind; business: string | null })[];
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
  kind: ModuleKind; business: string | null;
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
  name: string; title: string; required: boolean;
  range: string | null; description: string;
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

/** An application the business uses, and the day this version came into use. */
export interface InUse { name: string; version: string; since: string; assertion: string }

/** Whose kernel this is, and what it uses on the day asked about. */
export interface Business { business: string | null; installed: InUse[] }

export const appApi = {
  business: (c: Clocks) => get<Business>("/api/business", clockParams(c)),
  install: (body: { name: string; version: string; actor: string; valid_from: string }) =>
    post<InUse & { intent_id: string; registered: string[] }>("/api/app/install", body),
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

// ---- the catalogue, and the graph's health --------------------------------
// Both are computed from sealed content on every read. Nothing here is a
// document somebody maintains, so nothing here can be out of date.

export type CatalogueKind = "module" | "role" | "class" | "slot";

export interface RuleRef { module: Pin; rule: string; kind: string }

export interface CatalogueEntry {
  kind: CatalogueKind; name: string; module: Pin; title: string | null;
  description: string; fills: string[];
  // module
  purpose?: string | null; versions?: string[]; pins?: Pin[];
  declares?: { classes: string[]; slots: string[] };
  // role
  bindings?: Binding[]; filled_by?: { class: string; module: Pin }[];
  // class
  statable?: boolean; slots?: string[];
  // slot
  uri?: string | null; range?: string | null; abstract?: boolean; on?: string[];
  // role, class, slot
  read_by?: RuleRef[];
}

export interface CatalogueFound {
  entries: CatalogueEntry[];
  counts: Record<CatalogueKind, number>;
  held: Record<CatalogueKind, number>;
  roles: string[]; bindings: string[]; modules: string[];
}

export interface CatalogueQuery {
  q?: string | null; kind?: string | null; fills?: string | null;
  module?: string | null; pins?: string | null;
}

export type DiagnosisCode =
  | "dead_term" | "empty_column" | "empty_class"
  | "unfilled_role" | "lagging_pin" | "orphaned_fact";

// One finding. Which fields it carries depends on the diagnosis; the sentence
// is assembled from them on the server and is never stored apart from them.
export interface Finding {
  sentence: string;
  uri?: string; slot?: string; module?: Pin | string; on?: string[];
  fills?: string | null; held?: number;
  class?: string; column?: string; read_by?: string[];
  role?: string; bindings?: string[]; candidates?: string[];
  pinned?: string; latest?: string; newer?: string[]; pinned_by?: Pin[];
  declared_by?: { name: string; versions: string[] }[];
}

export interface Diagnosis { code: DiagnosisCode; means: string; findings: Finding[] | null }

export interface Term {
  uri: string; slot: string; module: Pin; on: string[]; fills: string | null;
  held: number | null; read_by: { rule: string; kind: string; reader: string }[];
}

export interface HealthReport {
  name: string; version: string; counted: boolean; modules: Pin[];
  terms: Term[]; diagnoses: Diagnosis[]; refusals: (Refusal & { class: string })[];
}

export const catalogueApi = {
  find: (query: CatalogueQuery) =>
    get<CatalogueFound>("/api/catalogue", Object.fromEntries(
      Object.entries(query).filter(([, v]) => v) as [string, string][])),
  health: (name: string, version: string) =>
    get<HealthReport>("/api/app/health", { name, version }),
};

// ---- the studio -----------------------------------------------------------
//
// A draft is the one thing in the store that can be edited, and it is edited
// only by steps from a closed list. So the client never builds a document: it
// names a step and the answers it chose, and the server writes the file and
// sends the whole draft back — the holes recomputed, the gates re-run.

export interface DraftRow {
  name: string; title: string | null; purpose: string | null;
  versions: string[]; revises: string | null; steps: number;
}

/** One argument of one step, and the finite set of answers where there is one. */
export interface StepArgument {
  name: string; kind: string; required: boolean; options: string[];
  // Named where the answers cannot be listed until another argument is: a
  // column is a slot of whichever class was chosen.
  depends?: string;
}

export interface StepSpec { op: string; does: string; takes: StepArgument[] }

/** What to do next, where the answers to it are. */
export interface Step {
  op: string; args: Record<string, string>; choose: string; options: string[];
}

export interface Hole {
  kind: string; where: string; blocking: boolean;
  question: string; because: string;
  step: Step | null; refusal: Refusal | null;
}

/** What the person calls a thing, by language: the words they used for it,
 *  kept beside the English the module is recorded in. */
export type Labels = Record<string, string>;

export interface DraftClass {
  name: string; description: string; fills: string[]; is_a: string | null;
  slots: string[]; has_rows: boolean; labels?: Labels;
}

export interface DraftSlot {
  name: string; title: string; description: string; slot_uri: string | null;
  range: string | null; identifier: boolean; designates_type: boolean;
  binds: string | null; rule: { kind: string; spec: unknown } | null;
  on: string[]; labels?: Labels;
  /** What its value means, as the recording standard asks: a number's unit
   *  and which way it runs, a date's moment. */
  unit?: string | null; direction?: string | null; time_meaning?: string | null;
}

export interface DraftRole {
  name: string; module: Pin | null; description: string; bindings: Binding[];
  filled_by: { class: string; bindings: Record<string, string | null> }[];
}

/** A class from a module this draft pins, reachable from something it declares.
 *  What the map draws around what you are building, and cannot change. */
export interface DraftBorrowed {
  name: string; description: string; module: Pin; fills: string[]; labels?: Labels;
  slots: { name: string; range: string | null; identifier: boolean; labels?: Labels }[];
}

/** What one worked-out column reads, as the compiler reads it: the classes,
 *  the fields of each, and for a sum the field saying which row it lands on. */
export interface WorkingRead {
  class: string; fields: string[]; by: Record<string, string | null>;
  /** A key read one record away: the fields of the record `by` names that hold it. */
  via?: Record<string, string[]>;
}

export interface WorkingColumn {
  name: string; kind: "aggregate" | "parameter" | "expression";
  operator?: string; of?: string; reads: WorkingRead[];
}

/** One table the draft computes: what a row stands for, and where each
 *  worked-out column's numbers come from. */
export interface Working { class: string; keys: string[]; columns: WorkingColumn[] }

/** One record an example states: a thing, what it is, when, and the facts. */
export interface Recorded {
  record: string; class: string | null; when: string | null;
  facts: Record<string, string | number | boolean | null>;
}

/** One thing a draft changed, as the map draws it: a kind of thing, a field
 *  (`Kind.field`), an example, a module built on, or the module's own words. */
export interface DraftChange {
  what: "kind" | "field" | "example" | "pin" | "module";
  name: string;
  how: "added" | "changed" | "removed";
}

export interface DraftState {
  name: string; title: string | null; description: string | null;
  labels?: Labels;
  purpose: string | null; valid_from: string | null;
  versions: string[]; revises: string | null; becomes: string;
  pins: Pin[]; sees: { classes: number; slots: number };
  classes: DraftClass[]; slots: DraftSlot[]; roles: DraftRole[];
  borrowed: DraftBorrowed[];
  /** Where the numbers come from, and the classes only a rule reads. */
  workings: Working[]; read_from: DraftBorrowed[];
  tables: CheckReport["tables"];
  refusals: Refusal[]; holes: Hole[]; blocking: number;
  steps: StepSpec[]; taken: string; diff: ModuleDiff["diff"];
  /** What sealing it would change against the version it revises. */
  changes: DraftChange[];
  /** Nothing to freeze yet: it declares nothing, or changes nothing. */
  empty?: boolean;
  sealable: boolean; document: string;
  examples: ExampleResult[]; examples_run: boolean;
}

/** One number an example expects, and what the draft made of it. */
/** One number an example expects. `waiting` when no rule computes it yet:
 *  not wrong, not there yet. */
export interface ExampleCheck {
  table: string; row: string; at: string | null; column: string | null;
  expected: string; got: string; holds: boolean; waiting?: boolean;
}

/** A business example, run in a scratch log of its own. `passed` is null when
 *  nothing could run it; `waits` when the only numbers it lacks are ones no
 *  rule computes yet, so it can be agreed to before the rules are written. */
export interface ExampleResult {
  name: string; says: string; agreed: boolean; records: number; expected: number;
  /** What it says in the words of its people, by language. */
  labels?: Labels;
  checks: ExampleCheck[];
  tables: { table: string; columns: string[]; rows: string[][] }[];
  refusals: Refusal[]; passed: boolean | null; waits?: boolean;
  /** The records it states, in order; only on a draft's examples. */
  recorded?: Recorded[];
}

// ---- the agent --------------------------------------------------------------

/** What one request to the agent used, every part together. */
export interface Spent {
  requests: number; input: number; output: number; dollars: number | null; seconds: number;
}

/** How a request ended. `said` is the ending's own fields: `message` for a
 *  Reply or a Stopped, `question` and `choices` for a Question, for a Plan
 *  `message` and what it `builds`, from which `records`, which `numbers` come
 *  out and what it `cannot` do yet, and for a Proposal `message`, the
 *  examples to `agree` to and whether it may `seal`. */
export interface ChatTurn {
  at?: string; person: string;
  ended: "Reply" | "Question" | "Plan" | "Proposal" | "Stopped";
  said: {
    message?: string; question?: string; choices?: string[];
    builds?: string; records?: string[]; numbers?: string[]; cannot?: string[];
    module?: string; agree?: string[]; seal?: boolean; cause?: string;
  };
  // A Stopped turn carries `agree` and `seal` too: what the system found
  // waiting for the person when the request stopped.
  spent: Spent;
  shown?: string | null;
  /** What the request changed in the draft. */
  touched?: DraftChange[];
}

export interface Reckoning {
  happened: string[]; wanted: string[];
  figures: { figure: string; value: string; working: string }[];
  question: string; by: string;
}

/** The plan beside a draft, as the person was shown it, and whether they
 *  agreed to it. */
export interface PlanHeld {
  builds: string; records: string[]; numbers: string[]; cannot: string[];
  proposed_at: string; agreed: boolean; agreed_at?: string;
}

export interface Chat {
  name: string; running: boolean; turns: ChatTurn[];
  reckonings: Record<string, Reckoning>;
  plan: PlanHeld | null;
}

/** One thing the agent did in one call: a tool it called, words it said, or
 *  a thought the model let be seen. */
export interface Did { tool?: string; args?: Record<string, unknown>; text?: string; thought?: string }

export type AgentEvent =
  | { event: "started"; watch: string }
  | { event: "call"; part: string; step: number; seconds: number; did: Did[];
      answered: { tool: string; first: string }[]; changed: boolean;
      /** When it changed the draft: in this call, and since the request began. */
      now?: DraftChange[]; touched?: DraftChange[];
      tokens: { input: number; output: number; thinking: number; cached: number } }
  | { event: "note"; text: string }
  | { event: "error"; part: string; error: string }
  | ({ event: "turn" } & Omit<ChatTurn, "person" | "at">)
  | { event: "failed"; error: string };

/** One request to the agent. Each event is handed to `on` as it arrives; the
 *  promise settles when the request has ended. */
async function ask(name: string, text: string, on: (e: AgentEvent) => void): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/api/studio/ask", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, text }),
    });
  } catch {
    throw new ApiError("The API is not reachable. Start it with uvicorn on port 8200.");
  }
  if (!response.ok || !response.body) {
    const answer = await response.json().catch(() => null);
    throw new ApiError(answer?.error ?? `The API answered ${response.status}.`,
                       answer?.refusal ?? null);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let held = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (value) held += decoder.decode(value, { stream: true });
    let cut: number;
    while ((cut = held.indexOf("\n")) !== -1) {
      const line = held.slice(0, cut).trim();
      held = held.slice(cut + 1);
      if (line) on(JSON.parse(line) as AgentEvent);
    }
    if (done) break;
  }
  if (held.trim()) on(JSON.parse(held) as AgentEvent);
}

export const studioApi = {
  drafts: () => get<DraftRow[]>("/api/studio/drafts"),
  draft: (name: string) => get<DraftState>("/api/studio/draft", { name }),
  step: (name: string, step: string, args: Record<string, string>) =>
    post<DraftState & { discarded?: boolean; plan?: PlanHeld }>(
      "/api/studio/step", { name, step, args }),
  chat: (name: string) => get<Chat>("/api/studio/chat", { name }),
  ask,
  seal: (name: string, actor: string) =>
    post<{ name: string; version: string; minted: number }>(
      "/api/studio/seal", { name, actor }),
};

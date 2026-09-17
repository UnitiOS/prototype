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

export class ApiError extends Error {}

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
    throw new ApiError(body?.error ?? `The API answered ${response.status}.`);
  }
  return body as T;
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

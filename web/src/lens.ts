// The business lens: an application read as its owner's business.
//
// What the application keeps, what happened, and what it works out — things,
// events and numbers — each called in words, with the title of the module it
// came from as a small mark where it is somebody's module. No composed name
// (`tag__Name`) and none of the machinery's words reach this lens: they are
// one click away, under "How it works".
//
// Plain data in, sentences out, so all of it is tested without a browser.

import type { Application, Business, Column, Pin, Update, VersionChange } from "./api";
import { fieldLabel, plainName, spoken } from "./studioMap";

/** Words the business owner is not shown on this lens (ECOSYSTEM_PLAN §7.3). */
export const MACHINERY =
  /__|\b(modules?|seal(s|ed)?|uri|sql|predicates?|intents?|pin(s|ned)?|closure|slots?|class(es)?|aggregates?|schema|projection|kernel|refusal)\b/i;

export type Lens = "thing" | "event" | "number";

export const LENSES: { lens: Lens; heading: string; says: string }[] = [
  { lens: "thing", heading: "Things", says: "what the business keeps" },
  { lens: "event", heading: "Events", says: "what happened" },
  { lens: "number", heading: "Numbers", says: "what it works out" },
];

/** What a table, a thing or a field's kind is called: words, never a tag. */
export const called = (name: string) => spoken(plainName(name));

/**
 * The mark beside a thing or a field: the title of the module it came from,
 * where that is somebody's module. The application's own carry none, and
 * neither does the library's or core's: they are the common ground.
 */
export function markOf(app: Pick<Application, "name" | "modules">, module: Pin | null,
                       title: string | null | undefined): string | null {
  if (!module || module.name === app.name || !title) return null;
  const kind = app.modules.find((m) => m.name === module.name)?.kind;
  return kind === "module" ? title : null;
}

export interface LensItem { class: string; name: string; mark: string | null }

/** The tables in the owner's three words, in that order, empty ones left out. */
export function lensGroups(app: Application):
    { lens: Lens; heading: string; says: string; items: LensItem[] }[] {
  return LENSES.map((l) => ({
    ...l,
    items: app.tables.filter((t) => t.lens === l.lens).map((t) => ({
      class: t.class, name: called(t.class), mark: markOf(app, t.module, t.module_title),
    })),
  })).filter((g) => g.items.length > 0);
}

/** A column's heading: the record's own code, or the field in words. */
export function columnName(klass: string, column: Pick<Column, "name" | "title" | "kind">): string {
  return column.kind === "identity" ? "Code" : fieldLabel(column.name, klass, column.title);
}

/** The mark on a column another module adds to this table's thing (a facet). */
export function columnMark(app: Pick<Application, "name" | "modules">, table: Pin | null,
                           column: Pick<Column, "module" | "module_title">): string | null {
  if (!column.module || (table && column.module.name === table.name)) return null;
  return markOf(app, column.module, column.module_title);
}

/** A choice in a form: two kinds can both be called "Rental", so a choice
 *  of another module's kind says whose it is. */
export const choiceLabel = (o: { label: string; from?: string | null }) =>
  o.from ? `${o.label} (${o.from})` : o.label;

// ---- in use ------------------------------------------------------------------

/** Whether the business uses this version on the day, in its owner's words,
 *  and whether starting to use it is the owner's step to take here. */
export function inUseSaid(
  app: Pick<Application, "name" | "version" | "kind" | "business">,
  business: Business, on: string, day: (iso: string) => string,
): { line: string; installable: boolean } {
  const inUse = business.installed.find((i) => i.name === app.name) ?? null;
  if (app.kind !== "application") {
    return { line: "Shared with other businesses, shown here to look at. A business uses it "
      + "through an application of its own.", installable: false };
  }
  if (app.business !== business.business) {
    return { line: `This belongs to ${app.business}. It can be looked at here, not used.`,
             installable: false };
  }
  if (inUse && inUse.version === app.version) {
    return { line: `In use since ${day(inUse.since)}.`, installable: false };
  }
  if (inUse) {
    return { line: `Not in use yet. On ${on} the business uses ${inUse.version}, since `
      + `${day(inUse.since)}; this one reads the same records.`, installable: true };
  }
  return { line: `Not in use on ${on}. Nothing is recorded through it until the owner `
    + "starts using it.", installable: true };
}

// ---- a new version --------------------------------------------------------------

/** One change, as a sentence about her things and their fields. */
export function changeSaid(c: VersionChange): string {
  const name = called(c.name);
  if (c.what === "thing") {
    if (c.change === "added") return `Something new is kept: ${name}`;
    if (c.change === "removed") return `${name} is no longer kept`;
    return `${name} is described differently`;
  }
  const on = c.on ? called(c.on) : "It";
  const field = fieldLabel(c.name, c.on ?? "");
  if (c.change === "added") return `${on} gains a field: ${field}`;
  if (c.change === "removed") return `${on} loses a field: ${field}`;
  if (c.change === "renamed") {
    return `${on}: ${fieldLabel(c.was ?? "", c.on ?? "")} is now called ${field}; `
      + "what was recorded under it stays";
  }
  const fields = c.fields ?? [];
  const wording = fields.every((f) => ["description", "title", "annotations"].includes(f));
  if (wording) return `${on}: ${field} is described differently`;
  if (fields.includes("required")) return `${on}: ${field} changes whether it must be filled in`;
  if (fields.includes("range")) return `${on}: ${field} now holds something different`;
  return `${on}: ${field} changes`;
}

export type ExampleState = "holds" | "differs" | "not computed yet";

export const exampleState = (e: Update["examples"][number]): ExampleState =>
  e.passed ? "holds" : e.pending ? "not computed yet" : "differs";

/** What her own examples say about the new version, in one sentence. */
export function examplesSaid(u: Update): string {
  const n = u.examples.length;
  if (u.refusal) return "The examples were not run: the move is not possible as it stands.";
  if (n === 0) return "This application has no examples of its own to check the new version against.";
  const differ = u.examples.filter((e) => exampleState(e) === "differs").length;
  const waiting = u.examples.filter((e) => exampleState(e) === "not computed yet").length;
  if (differ > 0) {
    return `${differ} of ${n} ${n === 1 ? "example comes" : "examples come"} out differently `
      + `on ${u.latest}. Read ${differ === 1 ? "it" : "them"} before moving.`;
  }
  const held = n === 1 ? "The example holds" : `All ${n} examples hold`;
  return waiting > 0
    ? `${held} on ${u.latest}, ${waiting} of them not computed yet.`
    : `${held} on ${u.latest}.`;
}

/** Why a move cannot be prepared, without the machinery's words. */
export function blockedSaid(u: Update): string | null {
  if (!u.refusal) return null;
  return u.refusal.code === "two_versions_of_a_module"
    ? "Not possible on its own yet: something else this application uses still needs "
      + `${u.pinned}. Its author has to move first.`
    : "Not possible as it stands.";
}

export const STAYS = "What has been recorded stays as it was. Moving changes how things are "
  + "read from then on, not what was said.";

/** The ordinary Studio steps that move one of an application's versions,
 *  on a draft of it; the person seals that draft themselves. `held` is what
 *  a draft already open pins, if one is: a step already taken is not taken
 *  twice, so preparing the move again opens the same draft. */
export function moveSteps(u: Pick<Update, "module" | "pinned" | "latest">, held?: Pin[]):
    { step: string; args: Record<string, string> }[] {
  const pins = (held ?? [{ name: u.module, version: u.pinned }])
    .map((p) => `${p.name}@${p.version}`);
  const old = `${u.module}@${u.pinned}`, next = `${u.module}@${u.latest}`;
  return [
    ...(held ? [] : [{ step: "revise", args: {} }]),
    ...(pins.includes(old) ? [{ step: "unpin", args: { module: old } }] : []),
    ...(pins.includes(next) ? [] : [{ step: "pin", args: { module: next } }]),
  ];
}

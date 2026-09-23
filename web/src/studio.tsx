// The studio: where a version is made, before it is a version.
//
// A module is a graph, so the studio is a graph. The map is the page; a
// panel beside it says everything about whatever is selected and offers the
// one or two things to do about it next.
//
// The words on this page are the words of somebody who knows the subject,
// not the words of the compiler. `class` is a kind of thing, `slot` is a
// field, `range` is what it holds, a role is a shape, and a hole is a
// question. Where a plain word would be a guess about somebody's subject the
// page uses what the module itself wrote — a binding's own description is
// what turns `moment` into a question a person can answer — so nothing here
// is a translation table for any one business.
//
// Nothing on this page composes YAML. Every control names a step from the
// closed list the server sent and an answer it offered, so a click cannot
// produce a document that does not parse, and an answer that turns out to be
// wrong comes back as a refusal carrying the set it should have come from.
// The same list is what an agent is given. This page is one reader of it.
//
// The compiler's own vocabulary is not hidden, only moved: everything the
// previous version of this page showed is under "Behind the scenes".

import { useEffect, useMemo, useState } from "react";
import { studioApi } from "./api";
import type {
  Binding, DraftBorrowed, DraftClass, DraftRow, DraftSlot, DraftState, Hole,
  Pin, Refusal as RefusalSpec, Step, StepSpec,
} from "./api";
import { ApiError } from "./api";
import { Failure, RefusalCard } from "./Refusal";
import { MapCanvas } from "./graph";
import type { MapEdge, MapField, MapNode } from "./graph";
import type { StudioPick } from "./route";

const pinText = (p: Pin) => `${p.name}@${p.version}`;

// The types a field can hold are a closed set — the compiler's own — so they
// can be said in words without guessing about anybody's subject.
const HOLDS: Record<string, string> = {
  string: "text", uri: "text", uriorcurie: "text", curie: "text",
  ncname: "text", date: "date", datetime: "date & time", time: "time",
  integer: "whole number", decimal: "number", double: "number",
  float: "number", boolean: "yes / no",
};
const holds = (range: string | null) => (range ? HOLDS[range] ?? range : "text");

/** The first sentence of what somebody wrote, for a label that has one line. */
function first(text: string) {
  const said = text.replace(/\s+/g, " ").trim();
  const stop = said.search(/\.(\s|$)/);
  return stop === -1 ? said : said.slice(0, stop);
}

const lower = (text: string) =>
  /^[A-Z][a-z]/.test(text) ? text[0].toLowerCase() + text.slice(1) : text;

type Run = (step: string, args: Record<string, string>) => Promise<boolean>;

interface Held {
  draft: DraftState | null;
  failure: { error: string; refusal: RefusalSpec | null } | null;
  busy: boolean;
  run: Run;
}

/** One draft, and the one way of changing it: name a step, send the answers. */
function useDraft(name: string | null, onGone: () => void): Held {
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [failure, setFailure] = useState<Held["failure"]>(null);
  const [busy, setBusy] = useState(false);

  const take = (promise: Promise<DraftState & { discarded?: boolean }>) => {
    setBusy(true);
    return promise.then((next) => {
      setFailure(null);
      if (next.discarded) { setDraft(null); onGone(); return true; }
      setDraft(next);
      return true;
    }).catch((e) => {
      setFailure({
        error: e instanceof ApiError ? e.message : "Something failed while reading the API.",
        refusal: e instanceof ApiError ? e.refusal : null,
      });
      return false;
    }).finally(() => setBusy(false));
  };

  useEffect(() => {
    if (!name) { setDraft(null); setFailure(null); return; }
    void take(studioApi.draft(name));
  }, [name]);

  const run: Run = (step, args) =>
    name ? take(studioApi.step(name, step, args)) : Promise.resolve(false);
  return { draft, failure, busy, run };
}

// ---- what the map draws ---------------------------------------------------

/** The binding a class's field is filling, wherever in sight it was declared. */
function bindingIn(draft: DraftState, binding: string): Binding | null {
  for (const role of draft.roles) {
    const found = role.bindings.find((b) => b.name === binding);
    if (found) return found;
  }
  return null;
}

/** The role a question is owed to: the one this kind of thing actually claimed,
 *  where more than one carries the binding — a role inherits its ancestors'
 *  bindings, so `moment` belongs to Event and to every Flow as well, and the
 *  shape drawn on the box is the one the sentence should name. */
function roleFor(draft: DraftState, binding: string, kind: string): string | null {
  const carries = draft.roles.filter((r) => r.bindings.some((b) => b.name === binding));
  const claimed = carries.find((r) => r.filled_by.some((f) => f.class === kind));
  return (claimed ?? carries[0])?.name ?? null;
}

/** "a" or "an", because a sentence somebody reads should read. */
const an = (word: string) => (/^[AEIOUaeiou]/.test(word) ? `an ${word}` : `a ${word}`);

const about = (draft: DraftState, where: string) =>
  draft.holes.filter((h) => h.where === where || h.where.startsWith(`${where}.`));

/** Kinds of thing and the fields that point from one at another.
 *
 *  Everything drawn is already in the draft the server sent. Nothing is
 *  computed here that the gates would disagree with, because nothing is
 *  computed here at all — this only decides what is a box and what is a line.
 */
function mapOf(draft: DraftState): { nodes: MapNode[]; edges: MapEdge[] } {
  const slotOf = new Map(draft.slots.map((s) => [s.name, s]));
  const kinds = new Set([
    ...draft.classes.map((c) => c.name),
    ...draft.borrowed.map((b) => b.name),
  ]);
  const nodes: MapNode[] = [];
  const edges: MapEdge[] = [];

  const markOf = (slot: DraftSlot) => {
    if (slot.identifier) return "key";
    if (slot.binds) return bindingIn(draft, slot.binds)?.title ?? slot.binds;
    if (slot.rule) return slot.rule.kind;
    return null;
  };

  for (const kind of draft.classes) {
    const fields: MapField[] = kind.slots.map((name) => {
      const slot = slotOf.get(name);
      if (!slot) return { name, holds: "built on", mark: null, asks: false };
      if (slot.range && kinds.has(slot.range)) {
        edges.push({
          id: `${kind.name}/${name}`, from: kind.name, to: slot.range,
          label: name, own: true,
        });
      }
      return {
        name,
        holds: slot.range && kinds.has(slot.range) ? slot.range : holds(slot.range),
        mark: markOf(slot),
        asks: about(draft, name).length > 0,
      };
    });
    nodes.push({
      name: kind.name, own: true, description: kind.description,
      fills: kind.fills, fields, questions: about(draft, kind.name).length,
      module: null, rows: kind.has_rows,
    });
  }

  for (const kind of draft.borrowed) {
    const fields: MapField[] = kind.slots.map((slot) => {
      if (slot.range && kinds.has(slot.range)) {
        edges.push({
          id: `${kind.name}/${slot.name}`, from: kind.name, to: slot.range,
          label: slot.name, own: false,
        });
      }
      return {
        name: slot.name,
        holds: slot.range && kinds.has(slot.range) ? slot.range : holds(slot.range),
        mark: slot.identifier ? "key" : null,
        asks: false,
      };
    });
    nodes.push({
      name: kind.name, own: false, description: kind.description,
      fills: kind.fills, fields, questions: 0,
      module: pinText(kind.module), rows: true,
    });
  }
  return { nodes, edges };
}

// ---- a question in the words of somebody who knows the subject ------------

/** One hole, asked and explained.
 *
 *  Where the question is about a role, the words come from the module that
 *  declared the role: its binding wrote a sentence saying what it is for, and
 *  that sentence is the question. The studio never has to know that `moment`
 *  means a date, and a role invented tomorrow reads as well as core's do.
 */
function wording(draft: DraftState, hole: Hole): { ask: string; why: string } {
  const [head, tail] = hole.where.split(".");
  if (hole.kind === "binding_unfilled" || hole.kind === "binding_ambiguous") {
    const binding = bindingIn(draft, tail);
    const role = roleFor(draft, tail, head);
    const says = binding?.description
      ? lower(first(binding.description))
      : `its ${tail}`;
    const why = role
      ? `${head} is ${an(role)}. Taking a shape is a promise to name one `
        + `field for each thing it needs — name it, and every rule written `
        + `for ${an(role)} anywhere reaches ${head} too.`
      : hole.because;
    if (hole.kind === "binding_ambiguous") {
      return { ask: `Two fields of ${head} both say ${says} — which one does not?`, why };
    }
    return { ask: `Which field of ${head} says ${says}?`, why };
  }
  if (hole.kind === "class_is_empty") {
    return {
      ask: `What can you say about ${an(head)}?`,
      why: "A kind of thing with no fields has nothing to record about it.",
    };
  }
  if (hole.kind === "class_has_no_rows") {
    return {
      ask: `Nothing could ever be recorded as ${an(head)}. What shape does it take?`,
      why: "The log says an entity is something by stating it, and the "
        + "statement is carried by a shape. Claim one and a table appears.",
    };
  }
  if (hole.kind === "slot_is_loose") {
    return {
      ask: `Which kind of thing is ${head} said about?`,
      why: "A field on no kind of thing is never recorded, so nothing reads it.",
    };
  }
  if (hole.kind === "nothing_said_about_it") {
    return {
      ask: `What is ${head}?`,
      why: "One sentence. This is what somebody choosing between two modules "
        + "reads, and the only part of this they read before installing it.",
    };
  }
  if (hole.kind === "nothing_declared") {
    return {
      ask: "What kinds of thing does this module know about?",
      why: "A module is a vocabulary. Nothing is in this one yet.",
    };
  }
  if (hole.kind === "no_valid_from") {
    return {
      ask: "From when are these definitions true of the world?",
      why: hole.because,
    };
  }
  return { ask: hole.question, why: hole.because };
}

// ---- the page -------------------------------------------------------------

export function StudioPage(
  { pick, onPick }: { pick: StudioPick; onPick: (next: StudioPick) => void },
) {
  const [drafts, setDrafts] = useState<DraftRow[]>([]);
  const [listFailure, setListFailure] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  const [joining, setJoining] = useState<{ from: string; to: string } | null>(null);
  const held = useDraft(pick.name, () => onPick({ name: null }));

  const listDrafts = () => {
    studioApi.drafts().then((rows) => { setDrafts(rows); setListFailure(null); })
      .catch((e) => setListFailure(e instanceof ApiError ? e.message : String(e)));
  };
  useEffect(listDrafts, [held.draft?.name, held.draft?.holes.length, pick.name]);
  useEffect(() => { setChosen(null); setJoining(null); }, [pick.name]);

  const draft = held.draft;
  const world = useMemo(() => (draft ? mapOf(draft) : { nodes: [], edges: [] }), [draft]);

  return (
    <div className="studio">
      <StudioHead drafts={drafts} open={pick.name} draft={draft}
        onOpen={(name) => onPick({ name })}
        onStarted={(name) => { onPick({ name }); listDrafts(); }}
        run={held.run} busy={held.busy} />
      {listFailure && <p className="failure" role="alert">{listFailure}</p>}

      {!pick.name && (
        <p className="empty">
          Open a module, or start one. A module is a vocabulary somebody agreed
          on: the kinds of thing that exist, what can be said about each, and
          how the numbers are worked out.
        </p>
      )}

      {pick.name && held.failure && !draft && (
        <Failure error={held.failure.error} refusal={held.failure.refusal} />
      )}

      {draft && (
        <>
          <div className="studio-floor">
            <MapCanvas nodes={world.nodes} edges={world.edges} chosen={chosen}
              busy={held.busy}
              onChoose={(name) => { setChosen(name); setJoining(null); }}
              onConnect={(from, to) => { setChosen(from); setJoining({ from, to }); }} />
            <aside className="studio-panel" aria-label="What is selected">
              {held.failure && (
                <Failure error={held.failure.error} refusal={held.failure.refusal} />
              )}
              {joining ? (
                <Joining draft={draft} joining={joining} run={held.run}
                  onDone={() => setJoining(null)} />
              ) : chosen === null ? (
                <Whole draft={draft} run={held.run} onChoose={setChosen} />
              ) : (
                <Selected draft={draft} chosen={chosen} run={held.run}
                  onChoose={setChosen} />
              )}
            </aside>
          </div>
          <Behind draft={draft} run={held.run} />
        </>
      )}
    </div>
  );
}

// ---- the bar across the top -----------------------------------------------

function StudioHead(
  { drafts, open, draft, onOpen, onStarted, run, busy }: {
    drafts: DraftRow[]; open: string | null; draft: DraftState | null;
    onOpen: (name: string) => void; onStarted: (name: string) => void;
    run: Run; busy: boolean;
  },
) {
  const [starting, setStarting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  return (
    <header className="studio-head">
      <div className="studio-bar">
        <div className="studio-open">
          {drafts.map((row) => (
            <button key={row.name}
              className={`draft-row${row.name === open ? " draft-row-on" : ""}`}
              aria-current={row.name === open} onClick={() => onOpen(row.name)}>
              <span className="draft-name">{row.name}</span>
              <span className="quiet">
                {row.revises ? `changing ${row.revises}` : "not yet a version"}
              </span>
            </button>
          ))}
          {drafts.length === 0 && <p className="quiet">Nothing is being worked on.</p>}
          <button className="button" onClick={() => setStarting(!starting)}>
            {starting ? "Never mind" : "Start a module"}
          </button>
        </div>
        {draft && (
          <div className="studio-standing">
            <span className={draft.sealable ? "chip chip-good" : "chip chip-asks"}>
              {draft.sealable
                ? "nothing left to answer"
                : `${draft.blocking} to answer before it can be frozen`}
            </span>
            {confirming ? (
              <>
                <button className="button button-warn" disabled={busy}
                  onClick={() => run("discard", {})}>Yes, throw it away</button>
                <button className="button" onClick={() => setConfirming(false)}>
                  Keep it
                </button>
              </>
            ) : (
              <button className="button button-small"
                onClick={() => setConfirming(true)}>Throw away</button>
            )}
          </div>
        )}
      </div>
      {starting && (
        <StartForm onStarted={(name) => { setStarting(false); onStarted(name); }} />
      )}
      {draft && (
        <p className="studio-what">
          <strong>{draft.title || draft.name}</strong>
          {draft.purpose === "demonstration" && (
            <span className="badge badge-demo">demonstration</span>
          )}
          {draft.description && <span className="quiet"> — {draft.description}</span>}
          <br />
          <span className="quiet">
            Built on {draft.pins.length === 0 ? "nothing" : draft.pins.map(pinText).join(", ")}.
            {" "}Freezing it makes {draft.becomes}
            {draft.revises ? `, replacing ${draft.revises}` : ", its first version"}.
          </span>
        </p>
      )}
    </header>
  );
}

function StartForm({ onStarted }: { onStarted: (name: string) => void }) {
  const [name, setName] = useState("@");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [failure, setFailure] = useState<Held["failure"]>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    studioApi.step(name, "start", { title, description })
      .then(() => onStarted(name))
      .catch((err) => setFailure({
        error: err instanceof ApiError ? err.message : String(err),
        refusal: err instanceof ApiError ? err.refusal : null,
      }));
  };

  return (
    <form className="start-form" onSubmit={submit}>
      <label>
        <span>Where it lives</span>
        <input value={name} onChange={(e) => setName(e.target.value)}
          placeholder="@scope/name" required />
      </label>
      <label>
        <span>What it is called</span>
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
      </label>
      <label className="wide">
        <span>What it is for</span>
        <textarea value={description} rows={2} required
          onChange={(e) => setDescription(e.target.value)}
          placeholder="One sentence. This is what somebody choosing between two modules reads." />
      </label>
      <button className="button button-go" type="submit">Start it</button>
      {failure && <Failure error={failure.error} refusal={failure.refusal} />}
    </form>
  );
}

// ---- the panel, when nothing on the map is selected -----------------------

function Whole(
  { draft, run, onChoose }: {
    draft: DraftState; run: Run; onChoose: (name: string) => void;
  },
) {
  const [adding, setAdding] = useState(false);
  const blocking = draft.holes.filter((h) => h.blocking);
  const open = draft.holes.filter((h) => !h.blocking);
  return (
    <>
      <h3>This module</h3>
      {draft.sealable ? (
        <p className="settled">
          Everything it promised is named and everything it declares is
          described. It can be frozen as {draft.becomes}.
        </p>
      ) : (
        <p className="quiet">
          {blocking.length === 1 ? "One question stops" : `${blocking.length} questions stop`}
          {" "}it being frozen. The rest nobody refuses, and somebody still has
          to answer them before anyone else can use this.
        </p>
      )}

      <Questions draft={draft} holes={blocking} run={run} onChoose={onChoose} />
      <Questions draft={draft} holes={open} run={run} onChoose={onChoose} />

      <h4>What it would build</h4>
      {draft.tables.length === 0 ? (
        <p className="quiet">Nothing yet.</p>
      ) : (
        <ul className="plain">
          {draft.tables.map((table) => (
            <li key={table.class}>
              <button className="as-link" onClick={() => onChoose(table.class)}>
                {table.class}
              </button>
              <span className="quiet">
                {" "}— {table.columns} columns of {table.shape}
                {table.unfilled.length > 0
                  && `, ${table.unfilled.length} that no rule fills`}
              </span>
            </li>
          ))}
        </ul>
      )}

      {adding ? (
        <AddKind run={run} onDone={(name) => { setAdding(false); onChoose(name); }} />
      ) : (
        <button className="button button-go" onClick={() => setAdding(true)}>
          Add a kind of thing
        </button>
      )}
    </>
  );
}

// ---- the panel, when something on the map is selected ---------------------

function Selected(
  { draft, chosen, run, onChoose }: {
    draft: DraftState; chosen: string; run: Run; onChoose: (name: string | null) => void;
  },
) {
  const mine = draft.classes.find((c) => c.name === chosen);
  const theirs = draft.borrowed.find((b) => b.name === chosen);
  if (mine) return <Kind draft={draft} kind={mine} run={run} onChoose={onChoose} />;
  if (theirs) return <Theirs draft={draft} kind={theirs} onChoose={onChoose} />;
  return <p className="quiet">That is no longer on the map.</p>;
}

function Kind(
  { draft, kind, run, onChoose }: {
    draft: DraftState; kind: DraftClass; run: Run;
    onChoose: (name: string | null) => void;
  },
) {
  const [adding, setAdding] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const slotOf = new Map(draft.slots.map((s) => [s.name, s]));
  const roles = draft.steps.find((s) => s.op === "fill_role")
    ?.takes.find((t) => t.name === "role")?.options ?? [];
  const spare = roles.filter((r) => !kind.fills.includes(r));

  return (
    <>
      <h3>
        {kind.name}
        <button className="as-link close" onClick={() => onChoose(null)}>
          back to the whole module
        </button>
      </h3>

      <Saying what={kind.description} run={run}
        onSave={(value) => run("set_class",
          { class: kind.name, field: "description", value })} />

      {/* What is being asked comes first. Everything below it is here so the
          question can be answered, not the other way round. */}
      <Questions draft={draft} holes={about(draft, kind.name)} run={run}
        onChoose={onChoose} />

      <h4>Shapes it takes</h4>
      {kind.fills.length === 0 && (
        <p className="quiet">
          None. A shape is what lets a rule somebody else wrote reach this
          without knowing its name.
        </p>
      )}
      {kind.fills.map((role) => {
        const held = draft.roles.find((r) => r.name === role);
        return (
          <div key={role} className="shape">
            <p>
              <strong>{role}</strong>
              <button className="as-link" onClick={() => run("unfill_role",
                { class: kind.name, role })}>drop</button>
            </p>
            {held?.description && <p className="quiet">{first(held.description)}.</p>}
            <ul className="bindings">
              {(held?.bindings ?? []).map((binding) => {
                const filler = held?.filled_by.find((f) => f.class === kind.name)
                  ?.bindings[binding.name];
                return (
                  <li key={binding.name} className={filler ? "met" : "unmet"}>
                    <span className="mark">{filler ? "✓" : "?"}</span>
                    <span>{lower(first(binding.description || binding.title))}</span>
                    <span className="quiet">
                      {filler ? ` — ${filler}` : " — no field named yet"}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
      {spare.length > 0 && (
        <Pick label="Take another shape" options={spare}
          go={(role) => run("fill_role", { class: kind.name, role })} />
      )}

      <h4>What can be said about it</h4>
      <ul className="fields">
        {kind.slots.map((name) => {
          const slot = slotOf.get(name);
          return (
            <li key={name}>
              <code>{name}</code>
              {slot ? (
                <>
                  <span className="quiet"> {holds(slot.range)}</span>
                  {slot.identifier && <span className="tag">key</span>}
                  {slot.binds && (
                    <span className="tag tag-role">
                      {bindingIn(draft, slot.binds)?.title ?? slot.binds}
                    </span>
                  )}
                  {slot.rule && <span className="tag tag-rule">worked out</span>}
                  {slot.description
                    ? <p className="quiet said">{slot.description}</p>
                    : <p className="quiet">nothing said about it yet</p>}
                  <button className="as-link" onClick={() => run("detach",
                    { class: kind.name, slot: name })}>take off</button>
                </>
              ) : (
                <span className="quiet"> from a module this is built on</span>
              )}
            </li>
          );
        })}
        {kind.slots.length === 0 && <li className="quiet">Nothing yet.</li>}
      </ul>

      {adding ? (
        <AddField draft={draft} kind={kind.name} run={run}
          onDone={() => setAdding(false)} />
      ) : (
        <button className="button button-go" onClick={() => setAdding(true)}>
          Add a field
        </button>
      )}

      <div className="studio-danger">
        {confirming ? (
          <>
            <button className="button button-warn" onClick={() => {
              void run("remove_class", { class: kind.name }).then(() => onChoose(null));
            }}>Yes, remove {kind.name}</button>
            <button className="button" onClick={() => setConfirming(false)}>Keep it</button>
          </>
        ) : (
          <button className="button button-small" onClick={() => setConfirming(true)}>
            Remove this kind of thing
          </button>
        )}
      </div>
    </>
  );
}

function Theirs(
  { draft, kind, onChoose }: {
    draft: DraftState; kind: DraftBorrowed; onChoose: (name: string | null) => void;
  },
) {
  const kinds = new Set([
    ...draft.classes.map((c) => c.name),
    ...draft.borrowed.map((b) => b.name),
  ]);
  return (
    <>
      <h3>
        {kind.name}
        <button className="as-link close" onClick={() => onChoose(null)}>
          back to the whole module
        </button>
      </h3>
      <p className="quiet">
        This is not yours. It comes from <code>{pinText(kind.module)}</code>,
        which is frozen — you can point at it, and you change it by making a
        new version of that module, not here.
      </p>
      {kind.description && <p className="said">{kind.description}</p>}
      {kind.fills.length > 0 && (
        <p className="quiet">Takes the shape of {kind.fills.join(", ")}.</p>
      )}
      <h4>What can be said about it</h4>
      <ul className="fields">
        {kind.slots.map((slot) => (
          <li key={slot.name}>
            <code>{slot.name}</code>
            <span className="quiet"> {holds(slot.range)}</span>
            {slot.identifier && <span className="tag">key</span>}
            {slot.range && kinds.has(slot.range) && (
              <button className="as-link" onClick={() => onChoose(slot.range)}>
                go to {slot.range}
              </button>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}

// ---- questions ------------------------------------------------------------

function Questions(
  { draft, holes, run, onChoose }: {
    draft: DraftState; holes: Hole[]; run: Run;
    onChoose: (name: string) => void;
  },
) {
  if (holes.length === 0) return null;
  return (
    <div className="asks">
      {holes.map((hole, i) => {
        const said = wording(draft, hole);
        const head = hole.where.split(".")[0];
        const known = draft.classes.some((c) => c.name === head);
        return (
          <article key={`${hole.kind}${hole.where}${i}`}
            className={`hole${hole.blocking ? " hole-blocking" : ""}`}>
            <p className="hole-question">{said.ask}</p>
            <p className="quiet">{said.why}</p>
            {hole.step && <Answer step={hole.step} run={run} />}
            {known && (
              <button className="as-link" onClick={() => onChoose(head)}>
                show me {head}
              </button>
            )}
          </article>
        );
      })}
    </div>
  );
}

/** One question, one answer: a list where the answers are finite, a box where
 *  not. The list is the server's, never this page's. */
function Answer({ step, run }: { step: Step; run: Run }) {
  const [value, setValue] = useState("");
  const long = step.choose === "value" && step.options.length === 0;
  const send = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    void run(step.op, { ...step.args, [step.choose]: value });
    setValue("");
  };
  return (
    <form className="answer" onSubmit={send}>
      {step.options.length > 0 ? (
        <select value={value} onChange={(e) => setValue(e.target.value)}>
          <option value="">choose…</option>
          {step.options.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      ) : long ? (
        <textarea value={value} rows={2}
          onChange={(e) => setValue(e.target.value)} />
      ) : (
        <input value={value} onChange={(e) => setValue(e.target.value)} />
      )}
      <button className="button button-go" type="submit" disabled={!value.trim()}>
        Answer
      </button>
    </form>
  );
}

function Pick(
  { label, options, go }: {
    label: string; options: string[]; go: (value: string) => void;
  },
) {
  const [value, setValue] = useState("");
  return (
    <form className="answer" onSubmit={(e) => {
      e.preventDefault();
      if (value) { go(value); setValue(""); }
    }}>
      <label className="visually-hidden">{label}</label>
      <select value={value} onChange={(e) => setValue(e.target.value)}>
        <option value="">{label}…</option>
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
      <button className="button" type="submit" disabled={!value}>Do it</button>
    </form>
  );
}

/** A description, which is the part of a module somebody else actually reads. */
function Saying(
  { what, onSave }: {
    what: string; run: Run; onSave: (value: string) => Promise<boolean>;
  },
) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(what);
  useEffect(() => { setValue(what); }, [what]);
  if (!editing) {
    return (
      <p className={what ? "said" : "quiet"}>
        {what || "Nobody has said what this is."}
        <button className="as-link" onClick={() => setEditing(true)}>
          {what ? "reword" : "say what it is"}
        </button>
      </p>
    );
  }
  return (
    <form className="answer" onSubmit={(e) => {
      e.preventDefault();
      void onSave(value).then(() => setEditing(false));
    }}>
      <textarea value={value} rows={3} onChange={(e) => setValue(e.target.value)} />
      <button className="button button-go" type="submit">Save</button>
      <button className="button" type="button" onClick={() => setEditing(false)}>
        Never mind
      </button>
    </form>
  );
}

// ---- making things --------------------------------------------------------

function AddKind({ run, onDone }: { run: Run; onDone: (name: string) => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  return (
    <form className="make" onSubmit={(e) => {
      e.preventDefault();
      void run("add_class", { class: name, description }).then((ok) => {
        if (ok) onDone(name);
      });
    }}>
      <label>
        <span>What is it called</span>
        <input value={name} required onChange={(e) => setName(e.target.value)}
          placeholder="one word, e.g. Delivery" />
      </label>
      <label>
        <span>What is it</span>
        <textarea value={description} rows={2}
          onChange={(e) => setDescription(e.target.value)} />
      </label>
      <button className="button button-go" type="submit">Add it</button>
    </form>
  );
}

function AddField(
  { draft, kind, run, onDone }: {
    draft: DraftState; kind: string; run: Run; onDone: () => void;
  },
) {
  const [name, setName] = useState("");
  const [range, setRange] = useState("string");
  const [description, setDescription] = useState("");
  const offered = draft.steps.find((s) => s.op === "add_slot")
    ?.takes.find((t) => t.name === "range")?.options ?? [];

  // Two steps, because declaring a field and putting it on a kind of thing
  // are two different facts — a field can sit on more than one.
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    void run("add_slot", { slot: name, range, description }).then((ok) => {
      if (!ok) return;
      void run("attach", { class: kind, slot: name }).then(() => onDone());
    });
  };

  return (
    <form className="make" onSubmit={submit}>
      <label>
        <span>What is it called</span>
        <input value={name} required onChange={(e) => setName(e.target.value)}
          placeholder="one word" />
      </label>
      <label>
        <span>What does it hold</span>
        <select value={range} onChange={(e) => setRange(e.target.value)}>
          {offered.map((option) => (
            <option key={option} value={option}>
              {HOLDS[option] ? `${HOLDS[option]}` : `a ${option}`}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>What is it</span>
        <textarea value={description} rows={2}
          onChange={(e) => setDescription(e.target.value)} />
      </label>
      <button className="button button-go" type="submit">Add it</button>
      <button className="button" type="button" onClick={onDone}>Never mind</button>
    </form>
  );
}

/** A line was drawn from one kind of thing to another. That is a field, and
 *  it needs a name before it is one. */
function Joining(
  { joining, run, onDone }: {
    draft: DraftState; joining: { from: string; to: string }; run: Run;
    onDone: () => void;
  },
) {
  const [name, setName] = useState(
    `${joining.from.toLowerCase()}_${joining.to.toLowerCase()}`);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    void run("add_slot", { slot: name, range: joining.to }).then((ok) => {
      if (!ok) return;
      void run("attach", { class: joining.from, slot: name }).then(() => onDone());
    });
  };
  return (
    <form className="make" onSubmit={submit}>
      <h3>{an(joining.from)} points at {an(joining.to)}</h3>
      <p className="quiet">
        What is that called? It becomes a field of {joining.from} holding which{" "}
        {joining.to} it is about.
      </p>
      <label>
        <span>Name it</span>
        <input value={name} required onChange={(e) => setName(e.target.value)} />
      </label>
      <button className="button button-go" type="submit">Make the relation</button>
      <button className="button" type="button" onClick={onDone}>Never mind</button>
    </form>
  );
}

// ---- everything the compiler says, where it belongs -----------------------

function Behind({ draft, run }: { draft: DraftState; run: Run }) {
  return (
    <details className="behind">
      <summary>Behind the scenes</summary>
      <p className="quiet">
        The same draft in the words of the machinery that reads it. Nothing
        here is another judge: these are the gates' own sentences, and the
        questions above are made out of them.
      </p>
      <div className="behind-grid">
        <section>
          <h4>What the gates say</h4>
          {draft.refusals.length === 0
            ? <p className="quiet">Nothing is refused.</p>
            : draft.refusals.map((refusal, i) => (
              <RefusalCard key={i} refusal={refusal} />
            ))}
        </section>

        <section>
          <h4>{draft.revises ? `Against ${draft.revises}` : "New in this version"}</h4>
          <DiffView diff={draft.diff} />
          <h4>Sees</h4>
          <p className="quiet">
            {draft.sees.classes} classes and {draft.sees.slots} slots, counting
            everything it is built on.
          </p>
        </section>

        <section>
          <h4>Every step it performs</h4>
          <p className="quiet">
            The closed list, with the answers that fit right now. This is what
            an agent is given, and what every control above chooses from.
          </p>
          <StepList draft={draft} run={run} />
        </section>
      </div>

      <details className="taken">
        <summary>Every step that got it here</summary>
        <pre>{draft.taken}</pre>
      </details>
      <details className="taken">
        <summary>The file this writes</summary>
        <pre>{draft.document}</pre>
      </details>
    </details>
  );
}

function StepList({ draft, run }: { draft: DraftState; run: Run }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <ul className="steps">
      {draft.steps.map((spec) => (
        <li key={spec.op}>
          <button className={`step-name${open === spec.op ? " step-name-on" : ""}`}
            onClick={() => setOpen(open === spec.op ? null : spec.op)}>
            <code>{spec.op}</code> <span className="quiet">{spec.does}</span>
          </button>
          {open === spec.op && <StepForm spec={spec} draft={draft} run={run} />}
        </li>
      ))}
    </ul>
  );
}

function StepForm(
  { spec, draft, run }: { spec: StepSpec; draft: DraftState; run: Run },
) {
  const [args, setArgs] = useState<Record<string, string>>({});
  const set = (key: string, value: string) => setArgs({ ...args, [key]: value });

  // An argument whose answers depend on another one: a column is a slot of
  // whichever class was named, and until it is named there is nothing to list.
  const optionsFor = (kind: string, given: string[]) => {
    if (kind !== "column") return given;
    const chosen = draft.classes.find((c) => c.name === args["class"]);
    return chosen ? chosen.slots : [];
  };

  return (
    <form className="step-form" onSubmit={(e) => {
      e.preventDefault();
      void run(spec.op, args);
      setArgs({});
    }}>
      {spec.takes.map((takes) => {
        const options = optionsFor(takes.kind, takes.options);
        return (
          <label key={takes.name}>
            <span>
              {takes.name}
              {!takes.required && <em className="quiet"> optional</em>}
            </span>
            {options.length > 0 ? (
              <select value={args[takes.name] ?? ""}
                onChange={(e) => set(takes.name, e.target.value)}>
                <option value="">choose…</option>
                {options.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            ) : (
              <input value={args[takes.name] ?? ""}
                placeholder={takes.kind === "mapping" ? "column=slot" : takes.kind}
                onChange={(e) => set(takes.name, e.target.value)} />
            )}
          </label>
        );
      })}
      <button className="button button-go" type="submit">Do it</button>
    </form>
  );
}

function DiffView({ diff }: { diff: DraftState["diff"] }) {
  const rows: { label: string; items: string[] }[] = [
    { label: "classes added", items: diff.classes.added },
    { label: "classes removed", items: diff.classes.removed },
    { label: "classes changed", items: diff.classes.changed.map((c) => c.name) },
    { label: "slots added", items: diff.slots.added },
    { label: "slots removed", items: diff.slots.removed },
    { label: "slots renamed", items: diff.slots.renamed.map((r) => `${r.from} → ${r.to}`) },
    { label: "slots changed", items: diff.slots.changed.map((s) => s.name) },
    { label: "imports added", items: diff.imports.added },
    { label: "imports removed", items: diff.imports.removed },
  ].filter((row) => row.items.length > 0);

  if (rows.length === 0) return <p className="quiet">Nothing differs yet.</p>;
  return (
    <dl className="diff-rows">
      {rows.map((row) => (
        <div key={row.label}>
          <dt>{row.label}</dt>
          <dd>{row.items.map((item) => <code key={item}>{item}</code>)}</dd>
        </div>
      ))}
      {diff.slots.renamed.length > 0 && (
        <p className="quiet">
          A rename keeps the predicate, so every fact already stated under it
          still belongs to the slot under its new name.
        </p>
      )}
    </dl>
  );
}

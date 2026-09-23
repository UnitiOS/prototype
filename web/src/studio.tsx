// The studio: where a version is made, before it is a version.
//
// Three columns, and the middle one is the point.
//
//   left    what is being built — the classes, the slots, the rules, with the
//           obligations that are not met yet marked
//   middle  the hole you are standing in: one question, and the answers that
//           fit, enumerated. Never a blank page and never the whole graph
//   right   what it would do: the tables it would build, what the gates say,
//           what changes against the version it would supersede, and every
//           step that got it here
//
// Nothing on this page composes YAML. Every control names a step from the
// closed list the server sent and the answers it offered, so a click cannot
// produce a document that does not parse, and an answer that turns out to be
// wrong comes back as a refusal carrying the set it should have come from.
//
// The same list is what an agent will be given in the next slice. This page is
// one reader of it, not the definition of it.

import { useEffect, useState } from "react";
import { studioApi } from "./api";
import type {
  DraftRow, DraftState, Hole, Pin, Refusal as RefusalSpec, Step, StepSpec,
} from "./api";
import { ApiError } from "./api";
import { Failure, RefusalCard } from "./Refusal";
import type { StudioPick } from "./route";

const pinText = (p: Pin) => `${p.name}@${p.version}`;

// What a hole is asking for, in the words of the thing being asked about.
// Written here and not on the server because it is a label on a control, and
// the server's own sentence is already on the card above it.
const CHOOSE: Record<string, string> = {
  slot: "Slot", class: "Class", role: "Role", binding: "Binding",
  value: "Answer", column: "Column", module: "Module",
};

type Run = (step: string, args: Record<string, string>) => Promise<void>;

interface Held {
  draft: DraftState | null;
  failure: { error: string; refusal: RefusalSpec | null } | null;
  run: Run;
}

/** One draft, and the one way of changing it: name a step, send the answers. */
function useDraft(name: string | null, onGone: () => void): Held {
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [failure, setFailure] = useState<Held["failure"]>(null);

  const take = (promise: Promise<DraftState & { discarded?: boolean }>) =>
    promise.then((next) => {
      setFailure(null);
      if (next.discarded) { setDraft(null); onGone(); return; }
      setDraft(next);
    }).catch((e) => setFailure({
      error: e instanceof ApiError ? e.message : "Something failed while reading the API.",
      refusal: e instanceof ApiError ? e.refusal : null,
    }));

  const reload = () => {
    if (!name) { setDraft(null); setFailure(null); return; }
    void take(studioApi.draft(name));
  };
  useEffect(reload, [name]);

  const run: Run = (step, args) => {
    if (!name) return Promise.resolve();
    return take(studioApi.step(name, step, args));
  };
  return { draft, failure, run };
}

export function StudioPage(
  { pick, onPick }: { pick: StudioPick; onPick: (next: StudioPick) => void },
) {
  const [drafts, setDrafts] = useState<DraftRow[]>([]);
  const [listFailure, setListFailure] = useState<string | null>(null);
  const held = useDraft(pick.name, () => onPick({ name: null }));

  const listDrafts = () => {
    studioApi.drafts().then((rows) => { setDrafts(rows); setListFailure(null); })
      .catch((e) => setListFailure(e instanceof ApiError ? e.message : String(e)));
  };
  useEffect(listDrafts, [held.draft?.name, held.draft?.holes.length, pick.name]);

  return (
    <div className="studio">
      <header className="studio-head">
        <h2>Studio</h2>
        <p className="quiet">
          A version is made here by answering questions. Nothing on this page
          writes to the log — a draft is a file until somebody seals it.
        </p>
        <DraftPicker drafts={drafts} open={pick.name}
          onOpen={(name) => onPick({ name })}
          onStarted={(name) => { onPick({ name }); listDrafts(); }} />
        {listFailure && <p className="failure" role="alert">{listFailure}</p>}
      </header>

      {!pick.name && (
        <p className="empty">
          Pick a draft, or start a module. A module starts with a name of the
          form <code>@scope/name</code>, a title, and a sentence saying what it
          is for — which is what somebody choosing between two modules reads.
        </p>
      )}

      {pick.name && held.failure && !held.draft && (
        <Failure error={held.failure.error} refusal={held.failure.refusal} />
      )}

      {held.draft && (
        <div className="studio-columns">
          <Building draft={held.draft} run={held.run} />
          <Standing draft={held.draft} run={held.run} failure={held.failure} />
          <Doing draft={held.draft} />
        </div>
      )}
    </div>
  );
}

// ---- picking and starting -------------------------------------------------

function DraftPicker(
  { drafts, open, onOpen, onStarted }:
  { drafts: DraftRow[]; open: string | null;
    onOpen: (name: string) => void; onStarted: (name: string) => void },
) {
  const [starting, setStarting] = useState(false);
  return (
    <div className="studio-picker">
      <div className="draft-rows">
        {drafts.map((row) => (
          <button key={row.name}
            className={`draft-row${row.name === open ? " draft-row-on" : ""}`}
            aria-current={row.name === open} onClick={() => onOpen(row.name)}>
            <span className="draft-name">{row.name}</span>
            <span className="quiet">
              {row.revises ? `revising ${row.revises}` : "new module"}
              {" · "}{row.steps} step{row.steps === 1 ? "" : "s"}
            </span>
          </button>
        ))}
        {drafts.length === 0 && <p className="quiet">No draft is open.</p>}
      </div>
      <button className="button" onClick={() => setStarting(!starting)}>
        {starting ? "Never mind" : "Start a module"}
      </button>
      {starting && (
        <StartForm onStarted={(name) => { setStarting(false); onStarted(name); }} />
      )}
    </div>
  );
}

function StartForm({ onStarted }: { onStarted: (name: string) => void }) {
  const [name, setName] = useState("@");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [failure, setFailure] = useState<{ error: string; refusal: RefusalSpec | null } | null>(null);

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
        <span>Name</span>
        <input value={name} onChange={(e) => setName(e.target.value)}
          placeholder="@scope/name" required />
      </label>
      <label>
        <span>Title</span>
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

// ---- left: what is being built --------------------------------------------

function Building({ draft, run }: { draft: DraftState; run: Run }) {
  const [confirming, setConfirming] = useState(false);
  const loose = draft.slots.filter((s) => s.on.length === 0);
  const holesAt = (where: string) =>
    draft.holes.filter((h) => h.where === where || h.where.startsWith(`${where}.`));

  return (
    <section className="studio-column" aria-label="What is being built">
      <h3>What is being built</h3>
      <p className="becomes">
        <strong>{draft.name}</strong> — {draft.title || "untitled"}
        {draft.purpose === "demonstration" && (
          <span className="badge badge-demo">demonstration</span>
        )}
        <br />
        <span className="quiet">
          becomes {draft.becomes}
          {draft.revises ? `, superseding ${draft.revises}` : ", the first version"}
          {draft.valid_from && `, true of the world from ${draft.valid_from.slice(0, 10)}`}
        </span>
      </p>
      {draft.description && <p className="said">{draft.description}</p>}

      <p className="quiet pins">
        pins {draft.pins.length === 0 ? "nothing" : draft.pins.map(pinText).join(", ")}
        {" · sees "}{draft.sees.classes} classes and {draft.sees.slots} slots
      </p>

      {draft.classes.map((item) => (
        <article key={item.name} className="built">
          <h4>
            {item.name}
            {item.fills.map((role) => (
              <span key={role} className="tag">fills {role}</span>
            ))}
            {!item.has_rows && <span className="tag tag-open">no rows</span>}
          </h4>
          {item.description
            ? <p className="said">{item.description}</p>
            : <p className="quiet">nothing said about it yet</p>}
          <ul className="built-slots">
            {item.slots.map((slotName) => {
              const slot = draft.slots.find((s) => s.name === slotName);
              return (
                <li key={slotName}>
                  <code>{slotName}</code>
                  {slot ? (
                    <span className="quiet">
                      {" "}{slot.range || "string"}
                      {slot.identifier && " · identifier"}
                      {slot.binds && ` · is a ${slot.binds}`}
                      {slot.rule && ` · ${slot.rule.kind}`}
                    </span>
                  ) : <span className="quiet"> · from a module you pin</span>}
                </li>
              );
            })}
            {item.slots.length === 0 && <li className="quiet">no slot on it yet</li>}
          </ul>
          {holesAt(item.name).length > 0 && (
            <p className="quiet">
              {holesAt(item.name).length} question{holesAt(item.name).length === 1 ? "" : "s"} about it
            </p>
          )}
        </article>
      ))}

      {loose.length > 0 && (
        <article className="built">
          <h4>On no class yet</h4>
          <ul className="built-slots">
            {loose.map((slot) => (
              <li key={slot.name}>
                <code>{slot.name}</code>
                <span className="quiet"> {slot.range || "string"}</span>
              </li>
            ))}
          </ul>
        </article>
      )}

      {draft.classes.length === 0 && (
        <p className="quiet">Nothing declared yet.</p>
      )}

      <div className="studio-danger">
        {confirming ? (
          <>
            <button className="button button-warn"
              onClick={() => run("discard", {})}>Yes, throw it away</button>
            <button className="button" onClick={() => setConfirming(false)}>Keep it</button>
          </>
        ) : (
          <button className="button" onClick={() => setConfirming(true)}>
            Discard this draft
          </button>
        )}
      </div>
    </section>
  );
}

// ---- middle: the hole you are standing in ---------------------------------

function Standing(
  { draft, run, failure }:
  { draft: DraftState; run: Run; failure: Held["failure"] },
) {
  const blocking = draft.holes.filter((h) => h.blocking);
  const open = draft.holes.filter((h) => !h.blocking);
  return (
    <section className="studio-column studio-middle" aria-label="Where you are standing">
      <h3>Where you are standing</h3>
      {failure && (
        <Failure error={failure.error} refusal={failure.refusal} />
      )}

      {draft.holes.length === 0 && (
        <p className="settled">
          Nothing is missing. Every obligation this draft claimed is met, every
          term it declares is described, and the gates have nothing to say.
        </p>
      )}

      {blocking.length > 0 && (
        <p className="quiet">
          {blocking.length === 1 ? "One of these stops" : `${blocking.length} of these stop`} a
          seal. The rest are things nobody refuses and somebody still has to answer.
        </p>
      )}

      {blocking.map((hole, i) => <HoleCard key={`b${i}`} hole={hole} run={run} />)}
      {open.map((hole, i) => <HoleCard key={`o${i}`} hole={hole} run={run} />)}

      <details className="something-else">
        <summary>Do something else</summary>
        <p className="quiet">
          Every step the studio performs, with the answers that fit this draft
          right now. This is the same list an agent is given.
        </p>
        <StepList draft={draft} run={run} />
      </details>
    </section>
  );
}

function HoleCard({ hole, run }: { hole: Hole; run: Run }) {
  return (
    <article className={`hole${hole.blocking ? " hole-blocking" : ""}`}>
      <p className="hole-question">{hole.question}</p>
      <p className="quiet hole-where">
        <code>{hole.where}</code> — {hole.because}
      </p>
      {hole.step && <Answer step={hole.step} run={run} />}
      {hole.refusal && (
        <details className="hole-refusal">
          <summary>What refused it</summary>
          <RefusalCard refusal={hole.refusal} />
        </details>
      )}
      <p className="quiet hole-kind"><code>{hole.kind}</code></p>
    </article>
  );
}

/** One question, one answer: a list where the answers are finite, a box where not. */
function Answer({ step, run }: { step: Step; run: Run }) {
  const [value, setValue] = useState("");
  const label = CHOOSE[step.choose] ?? step.choose;
  const send = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value) return;
    void run(step.op, { ...step.args, [step.choose]: value });
    setValue("");
  };
  return (
    <form className="answer" onSubmit={send}>
      <label>
        <span>{label}</span>
        {step.options.length > 0 ? (
          <select value={value} onChange={(e) => setValue(e.target.value)}>
            <option value="">choose…</option>
            {step.options.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        ) : (
          <input value={value} onChange={(e) => setValue(e.target.value)} />
        )}
      </label>
      <button className="button button-go" type="submit" disabled={!value}>
        {step.op}
      </button>
    </form>
  );
}

// ---- the whole step list --------------------------------------------------

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

function StepForm({ spec, draft, run }: { spec: StepSpec; draft: DraftState; run: Run }) {
  const [args, setArgs] = useState<Record<string, string>>({});
  const set = (key: string, value: string) => setArgs({ ...args, [key]: value });

  // An argument whose answers depend on another one: a column is a slot of
  // whichever class was named, and until it is named there is nothing to list.
  const optionsFor = (kind: string, given: string[]) => {
    if (kind !== "column") return given;
    const chosen = draft.classes.find((c) => c.name === args["class"]);
    return chosen ? chosen.slots : [];
  };

  const send = (e: React.FormEvent) => {
    e.preventDefault();
    void run(spec.op, args);
    setArgs({});
  };

  return (
    <form className="step-form" onSubmit={send}>
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

// ---- right: what it would do ----------------------------------------------

function Doing({ draft }: { draft: DraftState }) {
  return (
    <section className="studio-column" aria-label="What it would do">
      <h3>What it would do</h3>

      <p className={draft.sealable ? "settled" : "quiet"}>
        {draft.sealable
          ? "Every gate reads this as it stands. It can be sealed."
          : `${draft.blocking} thing${draft.blocking === 1 ? "" : "s"} in the way of a seal.`}
      </p>

      <h4>Tables</h4>
      {draft.tables.length === 0 && <p className="quiet">None yet.</p>}
      <ul className="built-slots">
        {draft.tables.map((table) => (
          <li key={table.class}>
            <code>{table.class}</code>
            <span className="quiet">
              {" "}{table.shape}, {table.columns} columns
              {table.unfilled.length > 0
                && ` · ${table.unfilled.length} no rule reaches`}
            </span>
          </li>
        ))}
      </ul>

      {draft.refusals.length > 0 && (
        <>
          <h4>What the gates say</h4>
          {draft.refusals.map((refusal, i) => (
            <RefusalCard key={i} refusal={refusal} />
          ))}
        </>
      )}

      <h4>Roles</h4>
      <p className="quiet">
        What each role obliges, and what this draft has named for it. A tick is
        a slot of your own; a role nothing here claims is simply available.
      </p>
      {draft.roles.filter((r) => r.filled_by.length > 0 && r.bindings.length > 0).map((role) => (
        <article key={role.name} className="role-fit">
          <h5>{role.name} <span className="quiet">{role.module ? pinText(role.module) : "yours"}</span></h5>
          {role.filled_by.map((filler) => (
            <div key={filler.class} className="role-filler">
              <p><code>{filler.class}</code></p>
              <ul className="bindings">
                {role.bindings.map((binding) => {
                  const named = filler.bindings[binding.name];
                  return (
                    <li key={binding.name} className={named ? "met" : "unmet"}>
                      <span className="mark">{named ? "✓" : "✗"}</span>
                      <code>{binding.name}</code>
                      <span className="quiet">
                        {named ? ` → ${named}` : ` — nothing named, ${binding.range || "any"}`}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </article>
      ))}

      <h4>{draft.revises ? `Against ${draft.revises}` : "New in this version"}</h4>
      <DiffView diff={draft.diff} />

      <details className="taken">
        <summary>Every step that got it here</summary>
        <pre>{draft.taken}</pre>
      </details>

      <details className="taken">
        <summary>The file this writes</summary>
        <pre>{draft.document}</pre>
      </details>
    </section>
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

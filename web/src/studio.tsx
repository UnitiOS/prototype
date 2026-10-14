// The studio: where a version is made, before it is a version.
//
// A module is a graph, so the studio is a graph. The map is the middle of the
// page and the largest thing on it. Beside it, on one side, the conversation
// with the agent that builds most drafts; on the other, a panel that says
// everything about whatever is selected, the examples and their numbers, and
// what the machinery says. On a narrow screen the three take turns.
//
// The conversation and the map point at each other: what the agent changes is
// marked on the map as it changes it, a name in the conversation brings its
// box into view, and a box says which requests made it.
//
// The words on this page are the words of somebody who knows the subject,
// not the words of the compiler. `class` is a kind of thing, `slot` is a
// field, `range` is what it holds, a role is a shape, and a hole is a
// question. Names are said as words (`quantity_on_hand` is "Quantity on
// hand"), and where a plain word would be a guess about somebody's subject
// the page uses what the module itself wrote — a binding's own description
// is what turns `moment` into a question a person can answer — so nothing
// here is a translation table for any one business.
//
// Nothing on this page composes YAML. Every control names a step from the
// closed list the server sent and an answer it offered, so a click cannot
// produce a document that does not parse, and an answer that turns out to be
// wrong comes back as a refusal carrying the set it should have come from.
// The same list is what an agent is given. This page is one reader of it.

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { modulesApi, studioApi } from "./api";
import type {
  Binding, Chat, ChatTurn, DraftBorrowed, DraftClass, DraftRow, DraftState, ExampleResult, Hole,
  ModuleRow, Refusal as RefusalSpec, Step, StepSpec,
} from "./api";
import { AgentPanel, ExamplesPanel, SealButton, ownersSaid } from "./agent";
import type { Marking, ToMap } from "./agent";
import { ApiError } from "./api";
import { Failure, RefusalCard } from "./Refusal";
import { CheckMark, MapCanvas } from "./graph";
import type { Showing } from "./graph";
import {
  CHANGE_SAID, HOLDS, askedOnce, changedOf, checksOf, chooseLanguage, exampleOf, fieldLabel,
  firstSentence, holds, holdsSaid, languageSaid, languagesOf, mapOf, marksOf, personLanguage,
  nameShown, pinText, snake, spoken, turnsAbout, wordsOf,
} from "./studioMap";
import { Language, useSay } from "./words";
import type { StudioPick } from "./route";

/** The first sentence of what somebody wrote, without its full stop. */
const first = (text: string) => firstSentence(text).replace(/\.$/, "");

const lower = (text: string) =>
  /^[A-Z][a-z]/.test(text) ? text[0].toLowerCase() + text.slice(1) : text;

type Run = (step: string, args: Record<string, string>) => Promise<boolean>;

interface Held {
  draft: DraftState | null;
  failure: { error: string; refusal: RefusalSpec | null } | null;
  busy: boolean;
  run: Run;
  reload: () => void;
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
    setDraft(null);
    setFailure(null);
    if (!name) return;
    void take(studioApi.draft(name));
  }, [name]);

  const run: Run = (step, args) =>
    name ? take(studioApi.step(name, step, args)) : Promise.resolve(false);
  // Read again after somebody else changed it: the agent, or a seal.
  const reload = () => {
    if (!name) return;
    studioApi.draft(name).then((next) => { setDraft(next); setFailure(null); })
      .catch((e) => {
        setDraft(null);
        setFailure({
          error: e instanceof ApiError ? e.message : "Something failed while reading the API.",
          refusal: e instanceof ApiError ? e.refusal : null,
        });
      });
  };
  return { draft, failure, busy, run, reload };
}

/** How much room there is: all three side by side, the map with the
 *  conversation and a panel that slides over it, or one at a time. */
type Size = "wide" | "mid" | "narrow";

function sizeNow(): Size {
  if (typeof window === "undefined" || !window.matchMedia) return "wide";
  if (window.matchMedia("(min-width: 1440px)").matches) return "wide";
  if (window.matchMedia("(min-width: 1024px)").matches) return "mid";
  return "narrow";
}

function useSize(): Size {
  const [size, setSize] = useState<Size>(sizeNow);
  useEffect(() => {
    const again = () => setSize(sizeNow());
    window.addEventListener("resize", again);
    return () => window.removeEventListener("resize", again);
  }, []);
  return size;
}

// ---- words about a draft ----------------------------------------------------

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

/** One hole, asked and explained.
 *
 *  Where the question is about a role, the words come from the module that
 *  declared the role: its binding wrote a sentence saying what it is for, and
 *  that sentence is the question. The studio never has to know that `moment`
 *  means a date, and a role invented tomorrow reads as well as core's do.
 */
function wording(
  draft: DraftState, hole: Hole, name: (term: string) => string,
  says: (example: ExampleResult) => string,
): { ask: string; why: string } {
  const [head, tail] = hole.where.split(".");
  const kind = name(head);
  // The examples' own questions: what a person agrees to, and what waits on
  // the agent, said as such rather than in the gate's words.
  const example = exampleOf(hole.where);
  const held = example ? draft.examples.find((e) => e.name === example) : undefined;
  const called = held ? `“${spoken(held.name)}”${says(held) ? ` (${first(says(held))})` : ""}` : "";
  if (hole.kind === "example_not_agreed" && held) {
    return {
      ask: `Are the numbers in the example ${called} right?`,
      why: "The agent wrote them with the accountant, from what you said. Only you can "
        + "agree to them: in the conversation, or under Examples.",
    };
  }
  if (hole.kind === "example_failed" && held?.waits) {
    return {
      ask: `The example ${called} waits for the rules that work its numbers out.`,
      why: "The rules come once the example is agreed to; nothing for you to do but agree.",
    };
  }
  if (hole.kind === "example_failed" && held) {
    return {
      ask: `The example ${called} does not come out as it says.`,
      why: hole.because,
    };
  }
  if (hole.kind === "column_unchecked") {
    return {
      ask: `Which example says what ${name(tail).toLowerCase()} of ${kind.toLowerCase()} must come to?`,
      why: "Every number the module works out needs an example with the right answer, "
        + "so a wrong rule is caught before anybody relies on it.",
    };
  }
  if (hole.kind === "binding_unfilled" || hole.kind === "binding_ambiguous") {
    const binding = bindingIn(draft, tail);
    const role = roleFor(draft, tail, head);
    const says = binding?.description
      ? lower(first(binding.description))
      : `its ${tail}`;
    const why = role
      ? `${kind} is ${an(role)}. Taking a shape is a promise to name one `
        + `field for each thing it needs — name it, and every rule written `
        + `for ${an(role)} anywhere reaches ${kind} too.`
      : hole.because;
    if (hole.kind === "binding_ambiguous") {
      return { ask: `Two fields of ${kind} both say ${says} — which one does not?`, why };
    }
    return { ask: `Which field of ${kind} says ${says}?`, why };
  }
  if (hole.kind === "class_is_empty") {
    return {
      ask: `What can you say about ${an(kind.toLowerCase())}?`,
      why: "A kind of thing with no fields has nothing to record about it.",
    };
  }
  if (hole.kind === "class_has_no_rows") {
    return {
      ask: `Nothing could ever be recorded as ${an(kind.toLowerCase())}. What shape does it take?`,
      why: "The log says an entity is something by stating it, and the "
        + "statement is carried by a shape. Claim one and a table appears.",
    };
  }
  if (hole.kind === "slot_is_loose") {
    return {
      ask: `Which kind of thing is "${kind}" said about?`,
      why: "A field on no kind of thing is never recorded, so nothing reads it.",
    };
  }
  if (hole.kind === "stands_alone") {
    return {
      ask: `Is ${an(kind.toLowerCase())} something the library already knows — a party, an item — or does it point at one?`,
      why: "Nothing it points at is shared with another module, so no other "
        + "module can find it, and it cannot find theirs.",
    };
  }
  if (hole.kind === "nothing_said_about_it") {
    return {
      ask: `What is ${kind}?`,
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

// ---- the page ---------------------------------------------------------------

type Side = "details" | "examples" | "behind";
type View = "chat" | "map" | "side";

export function StudioPage(
  { pick, onPick }: { pick: StudioPick; onPick: (next: StudioPick) => void },
) {
  const size = useSize();
  const [chosen, setChosen] = useState<string | null>(null);
  const [joining, setJoining] = useState<{ from: string; to: string } | null>(null);
  const [opening, setOpening] = useState<{ name: string; text: string } | null>(null);
  const [chat, setChat] = useState<Chat | null>(null);
  const [side, setSide] = useState<Side>("details");
  const [frozen, setFrozen] = useState<string | null>(null);
  const [talking, setTalking] = useState(true);
  const [inspecting, setInspecting] = useState(() => sizeNow() === "wide");
  const [view, setView] = useState<View>("map");
  const [marking, setMarking] = useState<Marking | null>(null);
  const [focus, setFocus] = useState<{ name: string; n: number } | null>(null);
  const [spot, setSpot] = useState<{ turn: number; n: number } | null>(null);
  const held = useDraft(pick.name, () => onPick({ name: null }));
  // The language the map and the panels say things in, where the module keeps
  // somebody's words for them.
  const [language, setLanguage] = useState(personLanguage);

  useEffect(() => {
    setChosen(null); setJoining(null); setChat(null); setSide("details");
    setInspecting(sizeNow() === "wide");
    setMarking(null); setFocus(null); setSpot(null);
  }, [pick.name]);

  const draft = held.draft;
  const world = useMemo(() => (draft ? mapOf(draft, language) : { nodes: [], edges: [] }),
    [draft, language]);

  const showing: Showing | null = useMemo(() => {
    if (!marking) return null;
    const said = changedOf(draft, marking.changes).said;
    return {
      marks: marksOf(marking.changes, marking.now),
      title: marking.title,
      said: marking.changes.length === 0 ? "Nothing has changed yet."
        : `${said[0].toUpperCase()}${said.slice(1)}${marking.live ? " so far" : ""}.`,
      live: marking.live,
      onStop: marking.live ? null : () => setMarking(null),
    };
  }, [marking, draft]);
  // No draft yet is not a failure when the agent is about to start one.
  const missing = held.failure?.refusal?.code === "no_draft"
    || held.failure?.refusal?.code === "no_such_module";

  /** Somebody wants to read about one thing: the panel comes forward. */
  const show = (next: Side) => {
    setSide(next);
    setInspecting(true);
    if (size === "narrow") setView("side");
  };
  const choose = (name: string | null) => {
    setChosen(name);
    setJoining(null);
    if (name) show("details");
  };
  /** The conversation points at the map: one kind, or what changed. */
  const toMap: ToMap = {
    onFocus: (name) => {
      setChosen(name);
      setJoining(null);
      setSide("details");
      setFocus((was) => ({ name, n: (was?.n ?? 0) + 1 }));
      if (size === "narrow") setView("map");
    },
    onMarking: (next, reveal) => {
      setMarking(next);
      if (reveal && size === "narrow") setView("map");
    },
  };
  /** The map points at the conversation: one request in it. */
  const toTurn = (turn: number) => {
    setTalking(true);
    setSpot((was) => ({ turn, n: (was?.n ?? 0) + 1 }));
    if (size === "narrow") setView("chat");
  };

  if (!pick.name) {
    return (
      <div className="studio">
        {frozen && <p className="settled banner" role="status">{frozen}</p>}
        <StudioHome
          onOpen={(name) => { setFrozen(null); onPick({ name }); }}
          onAsk={(name, text) => {
            setFrozen(null); setOpening({ name, text }); setView("chat"); onPick({ name });
          }} />
      </div>
    );
  }

  const sealed = (version: string) => {
    setFrozen(`${spoken(pick.name!.split("/").pop() ?? pick.name!)} (${pick.name}) is frozen as `
      + `${version}. The conversation that built it is kept beside the version.`);
    setOpening(null);
    onPick({ name: null });
  };

  const sides: [Side, string][] = [
    ["details", chosen ? (draft && wordsOf(draft, language).get(chosen)) || spoken(chosen)
      : "This module"],
    ["examples", `Examples${draft ? ` (${draft.examples.length})` : ""}`],
    ["behind", "Behind the scenes"],
  ];
  const views: [View, string][] = [
    ["chat", "Conversation"], ["map", "Map"], ["side", "Details"],
  ];

  return (
    <Language.Provider value={language}>
    <div className="studio">
      <StudioBar name={pick.name} draft={draft} size={size}
        talking={talking} inspecting={inspecting}
        onTalking={() => setTalking(!talking)}
        onInspecting={() => setInspecting(!inspecting)}
        onStanding={() => { setChosen(null); show("details"); }}
        onLeave={() => onPick({ name: null })}
        onSealed={sealed}
        run={held.run} busy={held.busy}
        language={language}
        onLanguage={(chosenLanguage) => { chooseLanguage(chosenLanguage); setLanguage(chosenLanguage); }} />

      {size === "narrow" && (
        <nav className="studio-switch" aria-label="What to show">
          {views.map(([key, label]) => (
            <button key={key} className={`switch${view === key ? " switch-on" : ""}`}
              aria-current={view === key} onClick={() => setView(key)}>{label}</button>
          ))}
        </nav>
      )}

      <div className={[
        "studio-work", `size-${size}`, `view-${view}`,
        talking ? "" : "no-chat", inspecting ? "" : "no-side",
      ].filter(Boolean).join(" ")}>
        <section className="pane pane-chat" aria-label="Conversation with the agent">
          <AgentPanel name={pick.name} draft={draft}
            first={opening?.name === pick.name ? opening.text : null}
            onChat={setChat}
            onChanged={() => held.reload()}
            onSealed={sealed}
            map={toMap} spot={spot} />
        </section>

        <section className="pane pane-map" aria-label="Map of the module">
          {draft ? (
            <MapCanvas key={pick.name} module={pick.name} draft={draft}
              nodes={world.nodes} edges={world.edges}
              chosen={chosen} busy={held.busy} onChoose={choose}
              showing={showing} focus={focus}
              onConnect={(from, to) => {
                setChosen(from); setJoining({ from, to }); show("details");
              }} />
          ) : missing ? (
            <Nothing name={pick.name} starting={marking?.live ?? false}
              onStarted={() => held.reload()} />
          ) : held.failure ? (
            <div className="map-empty">
              <Failure error={held.failure.error} refusal={held.failure.refusal} />
            </div>
          ) : (
            <div className="map-empty" role="status">
              <p><span className="spinner" aria-hidden="true" /> Opening {pick.name}…</p>
            </div>
          )}
        </section>

        <aside className="pane pane-side" aria-label="About what is selected">
          <nav className="side-tabs" aria-label="What to read">
            {sides.map(([key, label]) => (
              <button key={key} className={`side-tab${side === key ? " side-tab-on" : ""}`}
                aria-current={side === key} onClick={() => setSide(key)}>{label}</button>
            ))}
            {size !== "narrow" && (
              <button className="side-close" aria-label="Close this panel"
                onClick={() => setInspecting(false)}>×</button>
            )}
          </nav>
          <div className="side-body">
            {held.failure && draft && (
              <Failure error={held.failure.error} refusal={held.failure.refusal} />
            )}
            {!draft && <p className="quiet">Nothing to show until there is a draft.</p>}
            {draft && side === "details" && (
              joining ? (
                <Joining draft={draft} joining={joining} run={held.run}
                  onDone={() => setJoining(null)} />
              ) : chosen === null ? (
                <Whole draft={draft} run={held.run} onChoose={choose}
                  onExamples={() => show("examples")} />
              ) : (
                <Selected draft={draft} chosen={chosen} run={held.run} onChoose={choose}
                  turns={chat?.turns ?? []} onTurn={toTurn} />
              )
            )}
            {draft && side === "examples" && (
              <ExamplesPanel draft={draft} reckonings={chat?.reckonings ?? {}} />
            )}
            {draft && side === "behind" && <Behind draft={draft} run={held.run} />}
          </div>
        </aside>
      </div>
    </div>
    </Language.Provider>
  );
}

// ---- the bar across the top ---------------------------------------------------

function StudioBar(
  {
    name, draft, size, talking, inspecting, onTalking, onInspecting, onStanding,
    onLeave, onSealed, run, busy, language, onLanguage,
  }: {
    name: string; draft: DraftState | null; size: Size;
    talking: boolean; inspecting: boolean;
    onTalking: () => void; onInspecting: () => void; onStanding: () => void;
    onLeave: () => void; onSealed: (version: string) => void;
    run: Run; busy: boolean;
    language: string; onLanguage: (language: string) => void;
  },
) {
  const [more, setMore] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const title = draft?.labels?.[language] || draft?.title || spoken(name.split("/").pop() ?? name);
  const languages = draft ? languagesOf(draft) : [];
  const line = firstSentence(draft?.description);
  return (
    <header className="studio-bar">
      <button className="button button-small studio-back" onClick={onLeave}>
        ← All modules
      </button>
      <div className="studio-title">
        <h2>
          {title}
          <code className="studio-module">{name}</code>
          {draft?.purpose === "demonstration" && (
            <span className="badge badge-demo">demonstration</span>
          )}
        </h2>
        {draft && (
          <p className="studio-line">
            {more ? draft.description : line}
            {" "}
            <button className="as-link" aria-expanded={more} onClick={() => setMore(!more)}>
              {more ? "less" : "more"}
            </button>
            {more && (
              <span className="quiet studio-pins">
                Built on {draft.pins.length === 0 ? "nothing" : draft.pins.map(pinText).join(", ")}.
                {" "}Freezing it makes {draft.becomes}
                {draft.revises ? `, replacing ${draft.revises}` : ", its first version"}.
              </span>
            )}
            {ownersSaid(draft.owners) && (
              <span className="quiet studio-pins">{ownersSaid(draft.owners)}</span>
            )}
          </p>
        )}
      </div>

      {draft && (
        <div className="studio-standing">
          {languages.length > 0 && (
            <label className="studio-language" title="The module is recorded in English; these are the words its people use">
              <span className="quiet">Words in</span>{" "}
              <select value={languages.includes(language) ? language : "en"}
                onChange={(e) => onLanguage(e.target.value)}>
                {languages.map((l) => <option key={l} value={l}>{languageSaid(l)}</option>)}
              </select>
            </label>
          )}
          <button className={`chip chip-button ${draft.sealable ? "chip-good" : "chip-asks"}`}
            onClick={onStanding} title="What is still open">
            {draft.empty
              ? "Nothing built yet"
              : draft.sealable
                ? `Ready to freeze as ${draft.becomes}`
                : `${draft.blocking} ${draft.blocking === 1 ? "question" : "questions"} before it can be frozen`}
          </button>
          {draft.sealable && <SealButton name={name} draft={draft} onSealed={onSealed} />}
          {size !== "narrow" && (
            <>
              <button className={`button button-small${talking ? " button-on" : ""}`}
                aria-pressed={talking} onClick={onTalking}>Conversation</button>
              <button className={`button button-small${inspecting ? " button-on" : ""}`}
                aria-pressed={inspecting} onClick={onInspecting}>Details</button>
            </>
          )}
          {confirming ? (
            <>
              <button className="button button-small button-warn" disabled={busy}
                onClick={() => run("discard", {})}>Yes, throw the draft away</button>
              <button className="button button-small" onClick={() => setConfirming(false)}>
                Keep it
              </button>
            </>
          ) : (
            <button className="button button-small" onClick={() => setConfirming(true)}>
              Throw away
            </button>
          )}
        </div>
      )}
    </header>
  );
}

// ---- where the studio starts: build, or open -----------------------------------

function StudioHome(
  { onOpen, onAsk }: {
    onOpen: (name: string) => void; onAsk: (name: string, text: string) => void;
  },
) {
  const [drafts, setDrafts] = useState<DraftRow[]>([]);
  const [modules, setModules] = useState<ModuleRow[]>([]);
  const [failure, setFailure] = useState<Held["failure"]>(null);
  const [changing, setChanging] = useState<string | null>(null);

  const said = (e: unknown) => setFailure({
    error: e instanceof ApiError ? e.message : String(e),
    refusal: e instanceof ApiError ? e.refusal : null,
  });

  useEffect(() => {
    studioApi.drafts().then(setDrafts).catch(said);
    modulesApi.list().then(setModules).catch(said);
  }, []);

  const drafted = new Set(drafts.map((d) => d.name));
  const frozen = modules.filter((m) => m.latest && !drafted.has(m.name));

  // Changing a frozen module is a draft that revises its latest version.
  const change = (name: string) => {
    setChanging(name);
    studioApi.step(name, "revise", {})
      .then(() => onOpen(name))
      .catch(said)
      .finally(() => setChanging(null));
  };

  return (
    <div className="studio-home">
      <section className="home-card home-agent">
        <h2>Build with the agent</h2>
        <p className="quiet">
          Say in your own words what the business keeps track of and what it
          wants to know. The agent asks what it cannot be sure of, works the
          numbers out with an accountant, builds the module step by step, and
          puts it before you. Agreeing to the numbers and freezing the module
          are always yours.
        </p>
        <AskForm modules={[...drafts.map((d) => d.name), ...frozen.map((m) => m.name)]}
          onAsk={onAsk} />
      </section>

      <section className="home-card">
        <h2>Open a module</h2>
        {failure && <Failure error={failure.error} refusal={failure.refusal} />}
        {drafts.length > 0 && (
          <>
            <h3>Being worked on</h3>
            <ul className="home-list">
              {drafts.map((row) => (
                <li key={row.name}>
                  <div>
                    <strong>{row.title || spoken(row.name.split("/").pop() ?? row.name)}</strong>
                    <code className="quiet"> {row.name}</code>
                    <p className="quiet">
                      {row.revises ? `A change to ${row.revises}` : "Not yet a version"}
                      {` · ${row.steps} ${row.steps === 1 ? "step" : "steps"} so far`}
                    </p>
                  </div>
                  <button className="button button-go" onClick={() => onOpen(row.name)}>
                    Continue
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
        <h3>Frozen</h3>
        {frozen.length === 0 && <p className="quiet">None yet.</p>}
        <ul className="home-list">
          {frozen.map((row) => (
            <li key={row.name}>
              <div>
                <strong>{row.title || spoken(row.name.split("/").pop() ?? row.name)}</strong>
                <code className="quiet"> {row.name}</code>
                {row.purpose === "demonstration" && (
                  <span className="badge badge-demo">demonstration</span>
                )}
                <p className="quiet">
                  {row.latest}
                  {row.description ? ` · ${firstSentence(row.description)}` : ""}
                </p>
              </div>
              <button className="button" disabled={changing !== null}
                onClick={() => change(row.name)}>
                {changing === row.name ? "Opening…" : "Change it"}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <details className="home-card home-hand">
        <summary>Or start a new module by hand</summary>
        <StartForm onStarted={onOpen} />
      </details>
    </div>
  );
}

/** Which module, and what the business needs: the agent takes it from there,
 *  starting the module when there is none, or opening a draft of one that is
 *  already frozen. */
function AskForm(
  { modules, onAsk }: { modules: string[]; onAsk: (name: string, text: string) => void },
) {
  const [name, setName] = useState("@");
  const [text, setText] = useState("");
  const known = modules.includes(name.trim());
  return (
    <form className="start-form" onSubmit={(e) => {
      e.preventDefault();
      if (name.trim().length > 1 && text.trim()) onAsk(name.trim(), text.trim());
    }}>
      <label>
        <span>Which module</span>
        <input value={name} onChange={(e) => setName(e.target.value)} list="studio-modules"
          placeholder="@your-team/name" required />
        <datalist id="studio-modules">
          {modules.map((m) => <option key={m} value={m} />)}
        </datalist>
        <small className="quiet">
          {known ? "An existing module: the agent opens a change to it."
            : "A new name starts a new module. Pick an existing one to change it."}
        </small>
      </label>
      <label className="wide">
        <span>What the business needs</span>
        <textarea value={text} rows={4} required onChange={(e) => setText(e.target.value)}
          placeholder="For example: we buy flour and sugar in sacks and use them in baking; we want to know how much is on hand and when to reorder." />
      </label>
      <button className="button button-go" type="submit">Ask the agent</button>
    </form>
  );
}

function StartForm(
  { onStarted, name: given }: { onStarted: (name: string) => void; name?: string },
) {
  const [name, setName] = useState(given ?? "@");
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
      {given === undefined && (
        <label>
          <span>Where it lives</span>
          <input value={name} onChange={(e) => setName(e.target.value)}
            placeholder="@your-team/name" required />
        </label>
      )}
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

/** A module with no draft yet: the agent starts one, or a person does. */
function Nothing(
  { name, starting, onStarted }: { name: string; starting: boolean; onStarted: () => void },
) {
  if (starting) {
    return (
      <div className="map-empty" role="status">
        <p><span className="spinner" aria-hidden="true" /> The agent is starting {name}.
          The map appears here as soon as there is something to draw.</p>
      </div>
    );
  }
  return (
    <div className="map-empty">
      <div className="map-empty-card">
        <h3>Nothing is drafted in {name} yet</h3>
        <p className="quiet">
          Tell the agent what the business needs, in the conversation, and it
          starts the draft. Or start it yourself:
        </p>
        <StartForm name={name} onStarted={onStarted} />
      </div>
    </div>
  );
}

// ---- the panel, when nothing on the map is selected -------------------------------

function Whole(
  { draft, run, onChoose, onExamples }: {
    draft: DraftState; run: Run; onChoose: (name: string) => void; onExamples: () => void;
  },
) {
  const [adding, setAdding] = useState(false);
  const say = useSay(draft);
  const waits = new Set(draft.examples.filter((e) => e.waits).map((e) => e.name));
  const blocking = askedOnce(draft.holes.filter((h) => h.blocking), waits);
  const open = draft.holes.filter((h) => !h.blocking);
  const agreed = draft.examples.filter((e) => e.agreed).length;
  const failing = draft.examples.filter((e) => e.passed === false && !e.waits).length;
  const waiting = draft.examples.filter((e) => e.waits).length;
  return (
    <>
      <h3>This module</h3>
      {draft.empty ? (
        <p className="quiet">
          Nothing is built in it yet. Say in the conversation what the business needs.
        </p>
      ) : draft.sealable ? (
        <p className="settled">
          Everything it promised is named, everything it declares is described,
          and its examples hold. It can be frozen as {draft.becomes}.
        </p>
      ) : (
        <p className="quiet">
          {blocking.length === 1 ? "One question stops" : `${blocking.length} questions stop`}
          {" "}it being frozen.
          {open.length > 0 && " The others nobody refuses, and somebody still has to answer them before anyone else can use this."}
        </p>
      )}

      <Questions draft={draft} holes={blocking} run={run} onChoose={onChoose} />
      <Questions draft={draft} holes={open} run={run} onChoose={onChoose} />

      <h4>Examples</h4>
      <p className="said">
        {draft.examples.length === 0
          ? "None yet. An example is a few records and the numbers they must come to."
          : `${draft.examples.length} ${draft.examples.length === 1 ? "example" : "examples"}, `
            + `${agreed} agreed`
            + (failing ? `, ${failing} failing` : "")
            + (waiting ? `, ${waiting} waiting for the rules that work their numbers out` : "")
            + (failing || waiting ? "" : ", all holding")
            + "."}
        {draft.examples.length > 0 && (
          <button className="as-link" onClick={onExamples}>see them</button>
        )}
      </p>

      <h4>What it would build</h4>
      {draft.tables.length === 0 ? (
        <p className="quiet">Nothing yet.</p>
      ) : (
        <ul className="plain">
          {draft.tables.map((table) => (
            <li key={table.class}>
              <button className="as-link as-link-bare" onClick={() => onChoose(table.class)}>
                {say.name(table.class)}
              </button>
              <span className="quiet">
                {" "}— a table of {table.columns} columns
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

// ---- the panel, when something on the map is selected ---------------------------

function Selected(
  { draft, chosen, run, onChoose, turns, onTurn }: {
    draft: DraftState; chosen: string; run: Run; onChoose: (name: string | null) => void;
    turns: ChatTurn[]; onTurn: (turn: number) => void;
  },
) {
  const mine = draft.classes.find((c) => c.name === chosen);
  const theirs = [...draft.borrowed, ...(draft.read_from ?? [])].find((b) => b.name === chosen);
  if (mine) {
    return (
      <Kind draft={draft} kind={mine} run={run} onChoose={onChoose}
        story={<Story turns={turns} kind={mine.name} onTurn={onTurn} />} />
    );
  }
  if (theirs) return <Theirs draft={draft} kind={theirs} onChoose={onChoose} />;
  return <p className="quiet">That is no longer on the map.</p>;
}

/** Which requests to the agent made this kind of thing what it is, each a
 *  click away from where it was said. */
function Story(
  { turns, kind, onTurn }: { turns: ChatTurn[]; kind: string; onTurn: (turn: number) => void },
) {
  const about = turnsAbout(turns, kind);
  if (about.length === 0) return null;
  return (
    <section className="story">
      <h4>How it came about</h4>
      <ul>
        {about.map(({ turn, how }) => (
          <li key={turn}>
            <button className="as-link" onClick={() => onTurn(turn)}>
              {how === "added" ? "Made" : CHANGE_SAID[how][0].toUpperCase() + CHANGE_SAID[how].slice(1)}
              {" "}when you said “{firstSentence(turns[turn].person)}”
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** How a worked-out field is worked out, in a sentence, using the names the
 *  fields are shown under on the map. */
function ruleSaid(
  draft: DraftState, owner: string, kind: string, spec: unknown, column?: string,
): string {
  const slotOf = new Map(draft.slots.map((s) => [s.name, s]));
  const called = (name: string, on = owner) => fieldLabel(name, on, slotOf.get(name)?.title);
  if (kind === "expression" && typeof spec === "string") {
    return `Worked out by the formula: ${spec.replace(/\{(\w+)\}/g, (_, n: string) => called(n))}.`;
  }
  const held = (spec ?? {}) as Record<string, unknown>;
  // What the compiler reads, where it has read it: the kinds that actually
  // fill a role, not the role's own words.
  const reads = (draft.workings ?? []).find((t) => t.class === owner)
    ?.columns.find((c) => c.name === column)?.reads ?? [];
  if (kind === "aggregate" && reads.length > 0) {
    const what = reads.map((r) => {
      const by = Object.entries(r.by).find(([, field]) => field);
      return `the ${r.fields.map((f) => fieldLabel(f, r.class).toLowerCase()).join(" and ")} of every `
        + `${spoken(r.class).toLowerCase()}`
        + (by ? ` whose ${fieldLabel(by[1]!, r.class).toLowerCase()}`
          + (r.via?.[by[0]] ? `'s ${called(by[0]).toLowerCase()} is this row's` : " is this row's")
          + ` ${called(by[0]).toLowerCase()}` : "");
    });
    return `Added up: ${what.join(", and ")}.`;
  }
  if (kind === "aggregate") {
    // A column totalling several sources lists them; a lone one is the rule.
    const sources = Array.isArray(held.sources) ? held.sources as Record<string, unknown>[] : [held];
    const what = sources.map((source) => {
      const over = source.over ? spoken(String(source.over)).toLowerCase() : "record";
      const sum = source.sum ? spoken(String(source.sum)).toLowerCase() : "value";
      return `the ${sum} of every ${over}`;
    });
    return `Added up: ${what.join(", and ")} that concerns this row.`;
  }
  if (kind === "parameter") {
    const of = held.of ? String(held.of) : "";
    const pointed = slotOf.get(of)?.range ?? "";
    const thing = of ? called(of).toLowerCase() : "thing";
    const value = held.slot ? fieldLabel(String(held.slot), pointed).toLowerCase() : "value";
    return `Looked up: the ${value} of the ${thing} this row is about.`;
  }
  return "Worked out by a rule, never typed in.";
}

function Kind(
  { draft, kind, run, onChoose, story }: {
    draft: DraftState; kind: DraftClass; run: Run;
    onChoose: (name: string | null) => void;
    /** How it came about, in the conversation, where there is one. */
    story: ReactNode;
  },
) {
  const [adding, setAdding] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const slotOf = new Map(draft.slots.map((s) => [s.name, s]));
  const kinds = new Set([...draft.classes, ...draft.borrowed, ...(draft.read_from ?? [])]
    .map((k) => k.name));
  const checks = checksOf(draft);
  const roles = draft.steps.find((s) => s.op === "fill_role")
    ?.takes.find((t) => t.name === "role")?.options ?? [];
  const spare = roles.filter((r) => !kind.fills.includes(r));
  const { words } = useSay(draft);

  return (
    <>
      <h3>
        {words.get(kind.name) ?? spoken(kind.name)}
        <button className="as-link close" onClick={() => onChoose(null)}>
          back to the whole module
        </button>
      </h3>
      <p className="machine-name">named <code>{kind.name}</code></p>

      <Saying what={kind.description} run={run}
        onSave={(value) => run("set_class",
          { class: kind.name, field: "description", value })} />
      {story}

      {/* What is being asked comes first. Everything below it is here so the
          question can be answered, not the other way round. */}
      <Questions draft={draft} holes={about(draft, kind.name)} run={run}
        onChoose={onChoose} />

      <h4>What can be said about it</h4>
      <ul className="fields">
        {kind.slots.map((name) => {
          const slot = slotOf.get(name);
          return (
            <li key={name}>
              <strong>{words.get(name) ?? fieldLabel(name, kind.name, slot?.title)}</strong>
              {slot ? (
                <>
                  <span className="quiet">
                    {" "}{slot.range && kinds.has(slot.range)
                      ? `points at ${an(words.get(slot.range) ?? spoken(slot.range))}`
                      : holdsSaid(slot)}
                  </span>
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
                  {slot.rule && (
                    <p className="said rule-said">
                      {ruleSaid(draft, kind.name, slot.rule.kind, slot.rule.spec, name)}
                    </p>
                  )}
                  {checks.get(`${kind.name}.${name}`) && (
                    <p className="rule-check">
                      <CheckMark check={checks.get(`${kind.name}.${name}`)!} words />{" "}
                      {checks.get(`${kind.name}.${name}`)!.text}
                    </p>
                  )}
                  <p className="machine-name">
                    named <code>{name}</code>
                    {slot.range && kinds.has(slot.range) && (
                      <button className="as-link" onClick={() => onChoose(slot.range)}>
                        go to {spoken(slot.range)}
                      </button>
                    )}
                    <button className="as-link" onClick={() => run("detach",
                      { class: kind.name, slot: name })}>take off</button>
                  </p>
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

      <h4>Shapes it takes</h4>
      {kind.fills.length === 0 && (
        <p className="quiet">
          None. A shape is what lets a rule somebody else wrote reach this
          without knowing its name.
        </p>
      )}
      {kind.fills.map((role) => {
        const shape = draft.roles.find((r) => r.name === role);
        return (
          <div key={role} className="shape">
            <p>
              <strong>{role}</strong>
              <button className="as-link" onClick={() => run("unfill_role",
                { class: kind.name, role })}>drop</button>
            </p>
            {shape?.description && <p className="quiet">{first(shape.description)}.</p>}
            <ul className="bindings">
              {(shape?.bindings ?? []).map((binding) => {
                const filler = shape?.filled_by.find((f) => f.class === kind.name)
                  ?.bindings[binding.name];
                return (
                  <li key={binding.name} className={filler ? "met" : "unmet"}>
                    <span className="mark">{filler ? "✓" : "?"}</span>
                    <span>{lower(first(binding.description || binding.title))}</span>
                    <span className="quiet">
                      {filler ? ` — ${fieldLabel(filler, kind.name, slotOf.get(filler)?.title)}`
                        : " — no field named yet"}
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

      <div className="studio-danger">
        {confirming ? (
          <>
            <button className="button button-warn" onClick={() => {
              void run("remove_class", { class: kind.name }).then(() => onChoose(null));
            }}>Yes, remove {spoken(kind.name)}</button>
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
    ...(draft.read_from ?? []).map((b) => b.name),
  ]);
  const slotOf = new Map(draft.slots.map((s) => [s.name, s]));
  // The numbers of this module that come from this kind, as the compiler reads them.
  const feeds = (draft.workings ?? []).flatMap((table) => table.columns.flatMap((column) =>
    column.reads.filter((r) => r.class === kind.name).map((read) => ({ table, column, read }))));
  const { words } = useSay(draft);
  return (
    <>
      <h3>
        {words.get(kind.name) ?? spoken(kind.name)}
        <button className="as-link close" onClick={() => onChoose(null)}>
          back to the whole module
        </button>
      </h3>
      <p className="machine-name">named <code>{kind.name}</code></p>
      <p className="quiet">
        This is not part of this module. It comes from <code>{pinText(kind.module)}</code>,
        which is frozen: this module can point at it, and it is changed by
        making a new version of that module, not here.
      </p>
      {kind.description && <p className="said">{kind.description}</p>}
      {kind.fills.length > 0 && (
        <p className="quiet">Takes the shape of {kind.fills.join(", ")}.</p>
      )}
      {feeds.length > 0 && (
        <>
          <h4>Numbers this module works out from it</h4>
          <ul className="fields">
            {feeds.map(({ table, column, read }) => (
              <li key={`${table.class}.${column.name}`}>
                <strong>{fieldLabel(column.name, table.class, slotOf.get(column.name)?.title)}</strong>
                <span className="quiet"> in {spoken(table.class)}</span>
                <p className="said">
                  {column.kind === "aggregate" ? "Adds up" : "Looks up"} its{" "}
                  {read.fields.map((f) => fieldLabel(f, kind.name).toLowerCase()).join(" and ")}.
                </p>
                <p className="machine-name">
                  <button className="as-link" onClick={() => onChoose(table.class)}>
                    go to {spoken(table.class)}
                  </button>
                </p>
              </li>
            ))}
          </ul>
        </>
      )}
      <h4>What can be said about it</h4>
      <ul className="fields">
        {kind.slots.map((slot) => (
          <li key={slot.name}>
            <strong>{fieldLabel(slot.name, kind.name)}</strong>
            <span className="quiet">
              {" "}{slot.range && kinds.has(slot.range)
                ? `points at ${an(spoken(slot.range))}` : holds(slot.range)}
            </span>
            {slot.identifier && <span className="tag">key</span>}
            <p className="machine-name">
              named <code>{slot.name}</code>
              {slot.range && kinds.has(slot.range) && (
                <button className="as-link" onClick={() => onChoose(slot.range)}>
                  go to {spoken(slot.range)}
                </button>
              )}
            </p>
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
  const say = useSay(draft);
  if (holes.length === 0) return null;
  return (
    <div className="asks">
      {holes.map((hole, i) => {
        const said = wording(draft, hole, say.name, say.says);
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
                show me {say.name(head)}
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
            <option key={option} value={option}>{nameShown(option)}</option>
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
          <option key={option} value={option}>{nameShown(option)}</option>
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
              {HOLDS[option] ? `${HOLDS[option]}` : `a ${nameShown(option)}`}
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
  const [name, setName] = useState(`${snake(joining.from)}_${snake(joining.to)}`);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    void run("add_slot", { slot: name, range: joining.to }).then((ok) => {
      if (!ok) return;
      void run("attach", { class: joining.from, slot: name }).then(() => onDone());
    });
  };
  return (
    <form className="make" onSubmit={submit}>
      <h3>{an(spoken(joining.from))} points at {an(spoken(joining.to).toLowerCase())}</h3>
      <p className="quiet">
        What is that called? It becomes a field of {spoken(joining.from)} saying
        which {spoken(joining.to).toLowerCase()} it is about.
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
    <div className="behind">
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
    </div>
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
                  <option key={option} value={option}>{nameShown(option)}</option>
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

// The agent, beside the draft it is building.
//
// A person says what the business needs; the agent works through the studio's
// own steps and answers in one of five ways: it replies, it asks (with choices
// where it can offer them), it plans (what it will build, from which records,
// which numbers come out), it proposes (examples to agree to, and whether the
// draft is ready to freeze), or it stops (its budget spent, or the model
// failing). While it works, every call it makes is shown as it happens — what
// it read, what it changed, what it asked the accountant — because a person
// trusting a draft should be able to watch it being made.
//
// The work goes in that order, a request each: the plan, then the examples,
// then the rules that make the examples come out. The system holds the agent
// to it, so an example is agreed to while its numbers still wait for the
// rules that will work them out.
//
// Three things only a person does, and this page is where they do them: agree
// to the plan, agree to an example's numbers, and freeze the draft. The agent
// has no button for any of them. What the person is shown when the agent
// proposes is not the agent's summary: the system reads it off the draft.
//
// The conversation and the map are one piece of work. While the agent works,
// what it changes is marked on the map as it happens; afterwards every answer
// says what it changed, a click away from the map; a proposal carries a map
// of everything freezing the draft would change; and a box on the map says
// which requests made it (`turnsAbout`), a click away from the conversation.

import { useEffect, useRef, useState } from "react";
import { ApiError, studioApi } from "./api";
import type {
  AgentEvent, Chat, ChatTurn, Did, DraftChange, DraftState, ExampleResult, PlanHeld, Reckoning,
  Spent,
} from "./api";
import { ChangeTag, CheckMark } from "./graph";
import { changedOf, firstSentence, spoken } from "./studioMap";
import type { ChangeHow } from "./studioMap";
import { Said, useSay } from "./words";

/** What the map is asked to mark: a request's changes while it runs, the
 *  changes of one answer, or everything a seal would change. */
export interface Marking {
  changes: DraftChange[];
  now: DraftChange[];
  title: string;
  live: boolean;
}

/** How the panel reaches the map beside it. `reveal` brings the map forward
 *  where the two take turns on a narrow screen. */
export interface ToMap {
  onMarking: (marking: Marking | null, reveal: boolean) => void;
  onFocus: (kind: string) => void;
}

const clip = (text: string, most: number) =>
  text.length <= most ? text : `${text.slice(0, most - 1).trimEnd()}…`;

const SIGN: Record<ChangeHow, string> = { added: "+", changed: "~", removed: "−" };

// What each tool is, in the words of somebody watching.
const DOING: Record<string, string> = {
  look: "read the draft",
  options: "checked which steps fit",
  do: "changed the draft",
  catalogue: "searched the catalogue",
  guide: "read the guide",
  reckon: "asked the accountant",
};

function money(spent: Spent) {
  const dollars = spent.dollars === null ? "cost unknown" : `$${spent.dollars.toFixed(3)}`;
  return `${spent.requests} model calls · ${dollars} · ${Math.round(spent.seconds)} s`;
}

/** One thing done, as a line: a tool with the gist of its arguments, or words. */
function doneLine(d: Did): string | null {
  if (d.tool) {
    if (d.tool.endsWith("Reply") || d.tool.endsWith("Question") || d.tool.endsWith("Plan")
        || d.tool.endsWith("Proposal") || d.tool === "final_result") {
      return "answered";
    }
    const args = d.args ?? {};
    if (d.tool === "do") {
      const steps = (args.steps as { op: string }[] | undefined) ?? [];
      return `${DOING.do}: ${steps.map((s) => s.op).join(", ") || "nothing"}`;
    }
    if (d.tool === "reckon") {
      return `${DOING.reckon} about ${String(args.example ?? "an example")}`;
    }
    const what = ["module", "text", "kind", "op", "part", "topic"]
      .map((k) => args[k]).filter((v) => v).join(" ");
    return `${DOING[d.tool] ?? d.tool}${what ? ` (${what})` : ""}`;
  }
  if (d.text) return `said: ${d.text}`;
  return null;
}

export function AgentPanel(
  { name, draft, first, onChat, onChanged, onSealed, map, spot }: {
    name: string; draft: DraftState | null; first: string | null;
    onChat: (chat: Chat) => void;
    onChanged: () => void; onSealed: (version: string) => void;
    map: ToMap;
    /** A request somebody asked to see from the map; `n` grows with every ask. */
    spot: { turn: number; n: number } | null;
  },
) {
  const [chat, setChat] = useState<Chat | null>(null);
  const [live, setLive] = useState<AgentEvent[] | null>(null);
  const [asked, setAsked] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [lit, setLit] = useState<number | null>(null);
  // Asked to change the plan: the box below waits for what should change.
  const [changing, setChanging] = useState(false);
  const box = useRef<HTMLTextAreaElement | null>(null);
  const sentFirst = useRef<string | null>(null);
  const feed = useRef<HTMLDivElement | null>(null);
  // How much of the conversation there was when the feed last followed it.
  const followed = useRef({ turns: -1, events: -1 });

  const readChat = () => studioApi.chat(name).then((read) => { setChat(read); onChat(read); })
    .catch((e) => setFailure(e instanceof ApiError ? e.message : String(e)));

  useEffect(() => {
    setChat(null); setLive(null); setFailure(null);
    followed.current = { turns: -1, events: -1 };
    void readChat();
  }, [name]);
  // The feed follows the conversation when something new is said in it — a
  // request starting, its next call, a turn ending — and not when the same
  // conversation is read again, as it is after somebody agrees to something.
  // Only the feed moves, never the page around it.
  useEffect(() => {
    const turns = chat?.turns.length ?? 0;
    const events = live === null ? -1 : live.length;
    const grew = turns > followed.current.turns || events > followed.current.events;
    followed.current = { turns, events };
    const box = feed.current;
    if (grew && box) box.scrollTop = box.scrollHeight;
  }, [chat, live]);

  // Asked for from the map: brought into view, and lit for a moment.
  useEffect(() => {
    if (!spot) return;
    feed.current?.querySelector(`[data-turn="${spot.turn}"]`)
      ?.scrollIntoView({ block: "center", behavior: "smooth" });
    setLit(spot.turn);
    const id = window.setTimeout(() => setLit(null), 2400);
    return () => window.clearTimeout(id);
  }, [spot?.n]);

  const running = live !== null;

  const send = (said: string) => {
    const words = said.trim();
    if (!words || running) return;
    setText("");
    setChanging(false);
    setFailure(null);
    setAsked(words);
    setLive([]);
    // The map follows the work: what changed so far, and what just did.
    const working = "The agent is working";
    let touched: DraftChange[] = [];
    let ended = false;
    map.onMarking({ changes: [], now: [], title: working, live: true }, false);
    studioApi.ask(name, words, (event) => {
      setLive((held) => [...(held ?? []), event]);
      if (event.event === "call" && event.changed) {
        onChanged();
        touched = event.touched ?? touched;
        map.onMarking({ changes: touched, now: event.now ?? [], title: working, live: true }, false);
      }
      if (event.event === "turn") {
        ended = true;
        touched = event.touched ?? touched;
        map.onMarking(touched.length
          ? { changes: touched, now: [], title: "What the agent just changed", live: false }
          : null, false);
      }
      if (event.event === "failed") setFailure(event.error);
    }).catch((e) => setFailure(e instanceof ApiError ? e.message : String(e)))
      .finally(() => {
        if (!ended) {
          map.onMarking(touched.length
            ? { changes: touched, now: [], title: "What the agent changed before it stopped",
                live: false }
            : null, false);
        }
        setLive(null);
        setAsked(null);
        onChanged();
        void readChat();
      });
  };

  // A request the page was opened with: sent once, when the panel first shows.
  useEffect(() => {
    if (first && sentFirst.current !== `${name}\n${first}`) {
      sentFirst.current = `${name}\n${first}`;
      send(first);
    }
  }, [name, first]);

  const turns = chat?.turns ?? [];
  const latest = turns.length - 1;
  // The plan the person is asked about is the last one put forward.
  const lastPlan = turns.map((t) => t.ended).lastIndexOf("Plan");

  return (
    <div className="agent">
      <header className="agent-head">
        <h2>Conversation with the agent</h2>
        <p className="quiet">
          {running ? "Working on it — you can watch every step below."
            : "Say what you need; the agent builds it and shows you."}
        </p>
      </header>
      <div className="agent-feed" ref={feed}>
        {turns.length === 0 && !running && (
          <p className="quiet">
            Say what the business needs, in its own words. The agent asks what
            it cannot be sure of, works out the numbers with the accountant,
            builds the draft step by step, and puts it before you. Agreeing to
            the numbers and freezing the draft are yours.
          </p>
        )}
        {turns.map((turn, i) => (
          <Exchange key={i} index={i} turn={turn} name={name} draft={draft}
            reckonings={chat?.reckonings ?? {}} latest={i === latest && !running}
            lit={lit === i} map={map}
            plan={i === lastPlan ? chat?.plan ?? null : null}
            onAnswer={send} onChanged={onChanged} onSealed={onSealed}
            onChangePlan={() => { setChanging(true); box.current?.focus(); }} />
        ))}
        {running && (
          <>
            <p className="bubble bubble-person">{asked}</p>
            <Working events={live ?? []} map={map} />
          </>
        )}
        {failure && <p className="failure" role="alert">{failure}</p>}
      </div>
      <form className="agent-say" onSubmit={(e) => { e.preventDefault(); send(text); }}>
        <textarea value={text} rows={3} disabled={running} ref={box}
          placeholder={running ? "The agent is working…"
            : changing ? "What should be different in the plan?" : "Say what you need…"}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); }
          }} />
        <button className="button button-go" type="submit"
          disabled={running || !text.trim()}>Send</button>
      </form>
    </div>
  );
}

/** What changed, as a row of names that each lead to the map. */
function Touched(
  { changes, map, draft, title, onShow }: {
    changes: DraftChange[]; map: ToMap; draft: DraftState | null;
    title?: string; onShow?: () => void;
  },
) {
  const kinds = changes.filter((c) => c.what === "kind");
  const fields = changes.filter((c) => c.what === "field"
    && !kinds.some((k) => c.name.startsWith(`${k.name}.`)));
  const others = changes.filter((c) => c.what === "example" || c.what === "pin");
  const say = useSay(draft);
  if (changes.length === 0) return null;
  return (
    <div className="touched">
      {title && <span className="touched-title">{title}</span>}
      {kinds.map((c) => (
        <button key={c.name} className={`touched-item touched-${c.how}`}
          disabled={c.how === "removed"} title="Show it on the map"
          onClick={() => map.onFocus(c.name)}>
          <span className="change-sign">{SIGN[c.how]}</span>{say.name(c.name)}
        </button>
      ))}
      {fields.map((c) => (
        <button key={c.name} className={`touched-item touched-${c.how}`}
          disabled={c.how === "removed"} title="Show it on the map"
          onClick={() => map.onFocus(c.name.split(".")[0])}>
          <span className="change-sign">{SIGN[c.how]}</span>{say.name(c.name.split(".")[1])}
        </button>
      ))}
      {others.map((c) => (
        <span key={`${c.what}:${c.name}`} className={`touched-item touched-${c.how}`}>
          <span className="change-sign">{SIGN[c.how]}</span>
          {c.what === "example" ? `example ${spoken(c.name).toLowerCase()}` : c.name}
        </span>
      ))}
      {onShow && draft && (
        <button className="as-link touched-show" onClick={onShow}>show on the map</button>
      )}
    </div>
  );
}

/** What a call changed. The draft is only seen to have changed when the next
 *  call of the same part comes back carrying the step's answer, so what one
 *  call did is said by the call after it. */
function madeBy(events: AgentEvent[], i: number): DraftChange[] {
  const call = events[i];
  if (call.event !== "call" || !call.did.some((d) => d.tool === "do")) return [];
  const next = events.slice(i + 1)
    .find((e) => e.event === "call" && e.part === call.part);
  return next?.event === "call" && next.changed ? next.now ?? [] : [];
}

/** A request while it runs: each call as it comes back. */
function Working({ events, map }: { events: AgentEvent[]; map: ToMap }) {
  const calls = events.filter((e) => e.event === "call").length;
  return (
    <div className="working" aria-live="polite">
      <p className="working-head">
        <span className="spinner" aria-hidden="true" /> Working — {calls} model
        {calls === 1 ? " call" : " calls"} so far
      </p>
      <ol className="working-calls">
        {events.map((event, i) => {
          if (event.event === "call") {
            const lines = event.did.map(doneLine).filter((l): l is string => l !== null);
            const thoughts = event.did.filter((d) => d.thought).map((d) => d.thought);
            return (
              <li key={i} className={event.part === "accountant" ? "by-accountant" : ""}>
                <span className="who">{event.part === "accountant" ? "accountant" : "agent"}</span>
                {" "}{lines.length ? lines.join("; ") : "thought"}
                <span className="quiet">
                  {" "}· {event.seconds.toFixed(1)} s · {event.tokens.input} in
                  {event.tokens.cached ? ` (${event.tokens.cached} cached)` : ""}
                  {" "}/ {event.tokens.output} out
                  {event.tokens.thinking ? ` (${event.tokens.thinking} thinking)` : ""}
                </span>
                <Touched changes={madeBy(events, i)} map={map} draft={null} />
                {thoughts.length > 0 && (
                  <details className="thought">
                    <summary>what it was thinking</summary>
                    {thoughts.map((t, j) => <p key={j}>{t}</p>)}
                  </details>
                )}
              </li>
            );
          }
          if (event.event === "note") return <li key={i} className="note">{event.text}</li>;
          if (event.event === "error") {
            return <li key={i} className="note note-bad">a call failed: {event.error}</li>;
          }
          return null;
        })}
      </ol>
    </div>
  );
}

/** Whether a stopped request left something for the person to do. */
const waitsForThem = (turn: ChatTurn) =>
  (turn.said.agree ?? []).length > 0 || Boolean(turn.said.seal);

/** One request and how it ended. */
function Exchange(
  {
    index, turn, name, draft, reckonings, latest, lit, map, plan,
    onAnswer, onChanged, onSealed, onChangePlan,
  }: {
    index: number; turn: ChatTurn; name: string; draft: DraftState | null;
    reckonings: Record<string, Reckoning>; latest: boolean; lit: boolean; map: ToMap;
    /** The plan beside the draft, when this turn is the one that put it forward. */
    plan: PlanHeld | null;
    onAnswer: (text: string) => void; onChanged: () => void;
    onSealed: (version: string) => void; onChangePlan: () => void;
  },
) {
  const said = turn.said;
  const touched = turn.touched ?? [];
  return (
    <div className={`exchange${lit ? " exchange-lit" : ""}`} data-turn={index}>
      <p className="bubble bubble-person">{turn.person}</p>
      <div className={`bubble bubble-agent bubble-${turn.ended.toLowerCase()}`}>
        {turn.ended === "Question" && (
          <>
            <Said text={said.question ?? ""} />
            {latest && (said.choices ?? []).length > 0 && (
              <div className="choices">
                {(said.choices ?? []).map((choice) => (
                  <button key={choice} className="button choice"
                    onClick={() => onAnswer(choice)}>{choice}</button>
                ))}
              </div>
            )}
          </>
        )}
        {turn.ended === "Plan" && (
          <PlanCard turn={turn} name={name} plan={plan} latest={latest}
            onAgreed={() => onAnswer(AGREED)} onChange={onChangePlan} />
        )}
        {(turn.ended === "Proposal" || (turn.ended === "Stopped" && waitsForThem(turn))) && (
          // A stop that left examples or a seal waiting puts them before the
          // person as a proposal would: the system read them off the draft.
          <Proposal turn={turn} name={name} draft={draft} reckonings={reckonings}
            latest={latest} map={map} onChanged={onChanged} onSealed={onSealed} />
        )}
        {(turn.ended === "Reply" || (turn.ended === "Stopped" && !waitsForThem(turn))) && (
          <Said text={said.message ?? ""} />
        )}
        <Touched changes={touched} map={map} draft={draft} title="Changed:"
          onShow={() => map.onMarking({
            changes: touched, now: [], live: false,
            title: `What the agent changed when you said “${clip(firstSentence(turn.person), 60)}”`,
          }, true)} />
        <p className="spent quiet">{money(turn.spent)}</p>
      </div>
    </div>
  );
}

// What the page says for the person when they agree to a plan with its button.
const AGREED = "Agreed, go on.";

/** What the agent is going to build, put before the person before any rule
 *  is written. Agreeing is the person's step, then the agent goes on; asking
 *  for a change is said in their own words, below. */
function PlanCard(
  { turn, name, plan, latest, onAgreed, onChange }: {
    turn: ChatTurn; name: string; plan: PlanHeld | null; latest: boolean;
    onAgreed: () => void; onChange: () => void;
  },
) {
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const said = turn.said;
  const agree = () => {
    setBusy(true);
    studioApi.step(name, "agree_plan", {})
      .then(() => { setFailure(null); onAgreed(); })
      .catch((e) => setFailure(e instanceof ApiError ? e.message : String(e)))
      .finally(() => setBusy(false));
  };
  const listed = (title: string, items: string[] | undefined) => (items ?? []).length > 0 && (
    <>
      <h4>{title}</h4>
      <ul>{(items ?? []).map((item, i) => <li key={i}><Said text={item} className="" /></li>)}</ul>
    </>
  );
  return (
    <div className="plan">
      <Said text={said.message ?? ""} />
      <section className="plan-card" aria-label="The plan">
        <header className="plan-head">
          <strong>The plan</strong>
          {plan?.agreed && <span className="chip chip-good">agreed</span>}
          {!plan && !latest && <span className="chip">replaced</span>}
        </header>
        <Said text={said.builds ?? ""} className="" />
        {listed("Worked out from", said.records)}
        {listed("Numbers it gives", said.numbers)}
        {listed("Not possible yet", said.cannot)}
      </section>
      {latest && plan && !plan.agreed && (
        <div className="plan-acts">
          <button className="button button-go" disabled={busy} onClick={agree}>
            Agree, go on
          </button>
          <button className="button" disabled={busy} onClick={onChange}>Change it</button>
        </div>
      )}
      {failure && <p className="failure" role="alert">{failure}</p>}
    </div>
  );
}

/** What the agent put before the person, and the two things only they do. */
function Proposal(
  { turn, name, draft, reckonings, latest, map, onChanged, onSealed }: {
    turn: ChatTurn; name: string; draft: DraftState | null;
    reckonings: Record<string, Reckoning>; latest: boolean; map: ToMap;
    onChanged: () => void; onSealed: (version: string) => void;
  },
) {
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const said = turn.said;
  const example = (n: string) => draft?.examples.find((e) => e.name === n);

  const agree = (n: string) => {
    setBusy(true);
    studioApi.step(name, "agree_example", { example: n })
      .then(() => { setFailure(null); onChanged(); })
      .catch((e) => setFailure(e instanceof ApiError ? e.message : String(e)))
      .finally(() => setBusy(false));
  };
  const waiting = (said.agree ?? []).filter((n) => example(n) && !example(n)?.agreed);
  return (
    <div className="proposal">
      <Said text={said.message ?? ""} />
      {turn.ended === "Stopped" && latest && (
        <p className="quiet">Waiting for you, as the system reads the draft:</p>
      )}
      {turn.shown && (
        <details className="shown" open={latest}>
          <summary>What the system reads off the draft</summary>
          <pre>{turn.shown}</pre>
        </details>
      )}
      {latest && draft && <ChangeMap draft={draft} map={map} />}
      {latest && draft && (
        <div className="proposal-acts">
          {(said.agree ?? []).map((n) => {
            const held = example(n);
            if (!held) return <p key={n} className="quiet">{n} is no longer in the draft.</p>;
            return (
              <div key={n} className="agree-row">
                <ExampleLine example={held} reckoning={reckonings[n]} draft={draft} />
                {held.agreed ? (
                  <span className="chip chip-good">agreed</span>
                ) : (
                  // An example waiting for its rules is agreed to as it is: the
                  // numbers are the person's word, the rules come after.
                  <button className="button button-go"
                    disabled={busy || !(held.passed === true || held.waits)}
                    onClick={() => agree(n)}>
                    These numbers are right — agree
                  </button>
                )}
              </div>
            );
          })}
          {said.seal && (
            draft.sealable ? (
              <SealButton name={name} draft={draft} onSealed={onSealed} />
            ) : (
              <p className="quiet">
                {waiting.length > 0
                  ? "Agree to the numbers above, and it can be frozen."
                  : `${draft.blocking} still to answer before it can be frozen.`}
              </p>
            )
          )}
          {failure && <p className="failure" role="alert">{failure}</p>}
        </div>
      )}
    </div>
  );
}

/** Everything freezing the draft would change, drawn small: a box for each
 *  kind of thing, with the fields that are new, different or gone, and each
 *  worked-out field's check. Read off the draft as it is now, by the system. */
function ChangeMap({ draft, map }: { draft: DraftState; map: ToMap }) {
  const { words } = useSay(draft);
  const changed = changedOf(draft, draft.changes ?? [], words);
  const title = draft.revises
    ? `What freezing it as ${draft.becomes} changes from ${draft.revises}`
    : `What freezing it as ${draft.becomes} brings in`;
  if ((draft.changes ?? []).length === 0) {
    return <p className="quiet">{title}: nothing yet.</p>;
  }
  return (
    <section className="change-map" aria-label={title}>
      <header className="change-map-head">
        <strong>{title}</strong>
        <span className="quiet">{changed.said}</span>
      </header>
      <div className="change-boxes">
        {changed.kinds.map((kind) => (
          <div key={kind.name} className={`change-box change-box-${kind.how}`}>
            <button className="change-box-head" disabled={kind.how === "removed"}
              title="Show it on the map" onClick={() => map.onFocus(kind.name)}>
              <span className="change-box-name">{kind.label}</span>
              <ChangeTag how={kind.how} />
            </button>
            {kind.fields.length > 0 && (
              <ul className="change-fields">
                {kind.fields.map((field) => (
                  <li key={field.name} className={`field-${field.how}`}>
                    <span className="change-sign">{SIGN[field.how]}</span>
                    <span className="change-field">{field.label}</span>
                    {field.check && <CheckMark check={field.check} />}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      {(changed.examples.length > 0 || changed.pins.length > 0 || changed.module) && (
        <ul className="change-others">
          {changed.examples.map((e) => (
            <li key={e.name} className={`field-${e.how}`}>
              <span className="change-sign">{SIGN[e.how]}</span>example {e.label.toLowerCase()}
            </li>
          ))}
          {changed.pins.map((pin) => (
            <li key={pin.name} className={`field-${pin.how}`}>
              <span className="change-sign">{SIGN[pin.how]}</span>
              {pin.how === "removed" ? "no longer built on" : "built on"} {pin.name}
            </li>
          ))}
          {changed.module && (
            <li className="field-changed">
              <span className="change-sign">~</span>what the module says about itself
            </li>
          )}
        </ul>
      )}
      <button className="button button-small" onClick={() => map.onMarking({
        changes: draft.changes, now: [], live: false, title,
      }, true)}>See it on the map</button>
    </section>
  );
}

/** Freezing a draft: only a person does it, and says who they are. The seal's
 *  own gates judge, so a refusal comes back here rather than being guessed. */
export function SealButton(
  { name, draft, onSealed }: {
    name: string; draft: DraftState; onSealed: (version: string) => void;
  },
) {
  const [sealing, setSealing] = useState(false);
  const [actor, setActor] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const seal = () => {
    setBusy(true);
    studioApi.seal(name, actor.trim())
      .then((out) => { setFailure(null); setSealing(false); onSealed(out.version); })
      .catch((e) => setFailure(e instanceof ApiError ? e.message : String(e)))
      .finally(() => setBusy(false));
  };
  if (!sealing) {
    return (
      <button className="button button-go button-small" onClick={() => setSealing(true)}>
        Freeze as {draft.becomes}…
      </button>
    );
  }
  return (
    <form className="seal-form" onSubmit={(e) => { e.preventDefault(); seal(); }}>
      <label>
        <span>Freezing {name} as {draft.becomes} cannot be undone. Your name:</span>
        <input value={actor} onChange={(e) => setActor(e.target.value)} autoFocus
          placeholder="who is freezing it" required />
      </label>
      <div className="seal-acts">
        <button className="button button-warn" type="submit"
          disabled={busy || !actor.trim()}>Freeze it</button>
        <button className="button" type="button" onClick={() => setSealing(false)}>
          Not yet
        </button>
      </div>
      {failure && <p className="failure" role="alert">{failure}</p>}
    </form>
  );
}

/** An example in one line: what it says, and whether its numbers hold. */
function ExampleLine(
  { example, reckoning, draft }: {
    example: ExampleResult; reckoning?: Reckoning; draft: DraftState;
  },
) {
  const say = useSay(draft);
  return (
    <div className="example-line">
      <strong>{spoken(example.name)}</strong>
      {say.says(example) && <span className="quiet"> — {say.says(example)}</span>}
      <Checks example={example} name={say.name} />
      {reckoning && <Reckoned reckoning={reckoning} />}
    </div>
  );
}

function Checks(
  { example, name }: { example: ExampleResult; name: (term: string) => string },
) {
  if (example.passed === null) {
    return <p className="quiet">Not run: there is no log to run it in.</p>;
  }
  return (
    <ul className="checks">
      {example.checks.map((c, i) => (
        <li key={i} className={c.holds ? "holds" : c.waiting ? "waits" : "fails"}>
          <span className="mark">{c.holds ? "✓" : c.waiting ? "…" : "✗"}</span>
          {" "}{name(c.table)} <em>{c.row}</em>{c.column ? ` · ${name(c.column)}` : ""}
          {c.at ? ` on ${c.at}` : ""}: expected <strong>{c.expected}</strong>
          {c.holds ? "" : c.waiting
            ? <span className="quiet">, worked out once its rule is written</span>
            : <>, the draft makes <strong>{c.got}</strong></>}
        </li>
      ))}
      {example.refusals.length > 0 && example.checks.length === 0 && (
        <li className="fails">{example.refusals[0].sentence ?? "refused"}</li>
      )}
    </ul>
  );
}

function Reckoned({ reckoning }: { reckoning: Reckoning }) {
  return (
    <details className="reckoning">
      <summary>How the accountant worked it out</summary>
      <ul>
        {reckoning.happened.map((h, i) => <li key={`h${i}`} className="quiet">{h}</li>)}
      </ul>
      <ul>
        {reckoning.figures.map((f, i) => (
          <li key={`f${i}`}><strong>{f.figure} = {f.value}</strong> — {f.working}</li>
        ))}
      </ul>
      {reckoning.question && <p>It asked: {reckoning.question}</p>}
    </details>
  );
}

/** Every example of the draft, with its numbers. */
export function ExamplesPanel(
  { draft, reckonings }: { draft: DraftState; reckonings: Record<string, Reckoning> },
) {
  const say = useSay(draft);
  if (draft.examples.length === 0) {
    return (
      <p className="quiet">
        No examples yet. An example is a few records and the numbers they must
        come to; the agent writes them with the accountant, and you agree.
      </p>
    );
  }
  return (
    <div className="examples">
      {draft.examples.map((example) => (
        <article key={example.name} className="example">
          <header>
            <strong>{spoken(example.name)}</strong>
            <span className={`chip ${example.agreed ? "chip-good" : "chip-asks"}`}>
              {example.agreed ? "agreed" : "proposed"}
            </span>
            {example.passed !== null && (
              <span className={`chip ${example.passed ? "chip-good"
                : example.waits ? "chip-asks" : "chip-bad"}`}>
                {example.passed ? "holds" : example.waits ? "waits for its rules" : "fails"}
              </span>
            )}
          </header>
          {say.says(example) && <p className="said">{say.says(example)}</p>}
          <p className="quiet">
            {example.records} records, {example.expected} expected
            {example.expected === 1 ? " number" : " numbers"}
          </p>
          <Checks example={example} name={say.name} />
          {reckonings[example.name] && <Reckoned reckoning={reckonings[example.name]} />}
          {example.tables.map((table) => (
            <details key={table.table} className="example-table">
              <summary>{say.name(table.table)}, as this example makes it</summary>
              <div className="table-scroll"><table>
                <thead><tr>{table.columns.map((c) => <th key={c}>{say.name(c)}</th>)}</tr></thead>
                <tbody>
                  {table.rows.map((row, i) => (
                    <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
                  ))}
                </tbody>
              </table></div>
            </details>
          ))}
        </article>
      ))}
    </div>
  );
}

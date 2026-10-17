// The module store: the timeline of every sealed version, and one version read
// in full — what it pins, its connections, what it declares and what it can see
// through its imports, and how it differs from another version of itself.
//
// The connections are the module read by the person who wrote it: what it
// points at, what it adds to whose things, which roles it fills, and which
// shared modules build on it. Applications never appear there: each is private
// to its business.

import { useEffect, useState } from "react";
import { ApiError, modulesApi } from "./api";
import type { Connections, ModuleDiff, ModuleGraph, ModuleRow, ModuleVersion, Pin } from "./api";
import { Kept } from "./agent";
import { ModuleTimeline } from "./ModuleTimeline";
import { day, instant } from "./format";
import type { ModulePick } from "./route";

function useLoad<T>(load: (() => Promise<T>) | null, deps: unknown[]) {
  const [state, setState] = useState<{ data?: T; error?: string }>({});
  useEffect(() => {
    if (!load) { setState({}); return; }
    let live = true;
    load()
      .then((data) => live && setState({ data }))
      .catch((e) => live && setState({ error: e instanceof ApiError ? e.message : "Something failed while reading the API." }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

const pinText = (p: Pin) => `${p.name}@${p.version}`;

export function ModulesPage({ pick, onPick }: { pick: ModulePick; onPick: (next: ModulePick) => void }) {
  const graph = useLoad<ModuleGraph>(() => modulesApi.graph(), []);
  const list = useLoad<ModuleRow[]>(() => modulesApi.list(), []);

  const selected = pick.name && pick.version ? { name: pick.name, version: pick.version } : null;
  const select = (pin: Pin) => onPick({ name: pin.name, version: pin.version, compare: null });

  return (
    <>
      <section className="panel" aria-label="Timeline">
        {graph.error && <p className="failure" role="alert">{graph.error}</p>}
        {graph.data && <ModuleTimeline graph={graph.data} selected={selected} onSelect={select} />}
      </section>

      <main className="body">
        <div className="list">
          {list.data?.length === 0 && <p className="empty">No module in the store yet.</p>}
          <ul>
            {list.data?.map((m) => (
              <li key={m.name} className="module-row">
                <span className="id">
                  {m.name}
                  {m.purpose && <span className="badge badge-demo">{m.purpose}</span>}
                </span>
                <span className="versions">
                  {m.versions.map((v) => {
                    const on = selected && selected.name === m.name && selected.version === v.version;
                    return (
                      <button key={v.version} className={`version-chip${on ? " version-chip-on" : ""}`}
                        aria-current={!!on} onClick={() => select({ name: m.name, version: v.version })}>
                        {v.version}
                      </button>
                    );
                  })}
                  {m.draft && <span className="quiet">draft</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
        {selected
          ? <VersionView pin={selected} compare={pick.compare} onPick={onPick} />
          : <p className="empty">Pick a version on the timeline or in the list to read it.</p>}
      </main>
    </>
  );
}

function VersionView({ pin, compare, onPick }: { pin: Pin; compare: string | null; onPick: (next: ModulePick) => void }) {
  const { data, error } = useLoad(() => modulesApi.version(pin.name, pin.version), [pin.name, pin.version]);
  if (error) return <p className="failure" role="alert">{error}</p>;
  if (!data) return <p className="quiet">Reading…</p>;
  const v: ModuleVersion = data;
  const goTo = (p: Pin) => onPick({ name: p.name, version: p.version, compare: null });
  const own = (from: Pin) => from.name === v.name && from.version === v.version;

  const byOrigin = new Map<string, typeof v.classes>();
  for (const c of v.classes) {
    const k = pinText(c.from);
    byOrigin.set(k, [...(byOrigin.get(k) ?? []), c]);
  }
  const versionsOfThis = Array.from({ length: Number(v.latest?.slice(1) ?? 0) }, (_, i) => `v${i + 1}`)
    .filter((x) => x !== v.version);

  return (
    <article className="detail">
      <header className="detail-head">
        <h2>
          <span className="id">{v.name}</span> {v.version}
          {v.purpose && <span className="badge badge-demo">{v.purpose}</span>}
        </h2>
        <p className="quiet">
          Sealed {instant(v.sealed_at)}. In effect from {day(v.valid_from)}.
          {v.supersedes ? ` Supersedes ${v.supersedes}.` : " The first version."}
          {v.latest && v.latest !== v.version ? ` A newer version, ${v.latest}, exists.` : ""}
        </p>
        {v.description && <p>{v.description}</p>}
      </header>

      <section className="fact">
        <div className="fact-head"><h3>Pins</h3></div>
        {v.imports.length === 0
          ? <p className="chips quiet">Nothing. This version stands on LinkML alone.</p>
          : (
            <ul className="pins">
              {v.imports.map((p) => (
                <li key={pinText(p)}>
                  <button className="link id" onClick={() => goTo(p)}>{pinText(p)}</button>
                  {p.latest && p.latest !== p.version && (
                    <span className="drift">
                      {p.name} has moved on to {p.latest}; this version still means what {p.version} means
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
      </section>

      <ConnectionsView pin={pin} goTo={goTo} />

      <section className="fact">
        <div className="fact-head">
          <h3>Compared with</h3>
          <span className="chips chips-inline">
            {versionsOfThis.length === 0 && <span className="quiet">no other version</span>}
            {versionsOfThis.map((other) => (
              <button key={other} className={`version-chip${compare === other ? " version-chip-on" : ""}`}
                onClick={() => onPick({ name: v.name, version: v.version, compare: compare === other ? null : other })}>
                {other}
              </button>
            ))}
          </span>
        </div>
        {compare && <DiffView name={v.name} version={v.version} other={compare} />}
      </section>

      {[...byOrigin.entries()].map(([origin, classes]) => {
        const mine = own(classes[0].from);
        const slotNames = new Set(classes.flatMap((c) => c.slots));
        const slots = v.slots.filter((s) => slotNames.has(s.name));
        return (
          <details key={`${v.name}@${v.version}:${origin}`} open={mine} className={`fact${mine ? "" : " fact-imported"}`}>
            <summary className="fact-head">
              <h3>{mine ? "Declared here" : <>Seen through <span className="id">{origin}</span></>}</h3>
              <span className="quiet">
                {classes.length} {classes.length === 1 ? "class" : "classes"}
                {!mine && <>, <button className="link" onClick={(e) => { e.preventDefault(); goTo(classes[0].from); }}>open it</button></>}
              </span>
            </summary>
            <div className="scroll-plain">
              <table>
                <thead><tr><th>Class</th><th>Is a</th><th>Slots</th></tr></thead>
                <tbody>
                  {classes.map((c) => (
                    <tr key={c.name}>
                      <td><strong>{c.name}</strong>{c.description && <div className="quiet">{c.description}</div>}</td>
                      <td>{c.is_a ?? <span className="quiet">none</span>}</td>
                      <td className="id">{c.slots.join(", ") || <span className="quiet">none</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {slots.length > 0 && (
                <table>
                  <thead><tr><th>Slot</th><th>Predicate</th><th>Range</th><th>Role</th><th>In the kernel</th></tr></thead>
                  <tbody>
                    {slots.map((s) => (
                      <tr key={s.name}>
                        <td className="id">{s.name}</td>
                        <td className="id">{s.slot_uri}</td>
                        <td>{s.range ?? <span className="quiet">string</span>}</td>
                        <td>{[s.identifier && "identifier", s.designates_type && "names the class", s.required && "required", s.rule]
                          .filter(Boolean).join(", ") || <span className="quiet">stated</span>}</td>
                        <td>{s.registered === null ? <span className="quiet">kernel unreachable</span>
                          : s.registered ? "registered" : <span className="drift">not registered</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </details>
        );
      })}

      {v.conversation && (
        <section className="fact">
          <div className="fact-head"><h3>Conversation</h3>
            <span className="quiet">what was asked and answered while it was built</span></div>
          <div className="agent-feed agent-feed-page">
            <Kept name={v.name} open
              built={{ version: v.version, sealed_at: v.sealed_at, ...v.conversation }} />
          </div>
        </section>
      )}

      {v.transcript && (
        <section className="fact">
          <div className="fact-head"><h3>Transcript</h3></div>
          <pre className="transcript">{v.transcript}</pre>
        </section>
      )}
    </article>
  );
}

function ConnectionsView({ pin, goTo }: { pin: Pin; goTo: (p: Pin) => void }) {
  const { data, error } = useLoad<Connections>(() => modulesApi.connections(pin.name, pin.version),
    [pin.name, pin.version]);
  if (error) return <p className="failure" role="alert">{error}</p>;
  if (!data) return null;
  const from = (p: Pin) => (
    <button className="link id" onClick={() => goTo(p)}>{pinText(p)}</button>
  );
  const none = (said: string) => <p className="quiet">{said}</p>;

  return (
    <section className="fact connections">
      <div className="fact-head">
        <h3>Connections</h3>
        <span className="quiet">what it points at, adds to, fills, and who builds on it</span>
      </div>
      <dl className="fit-block">
        <dt>Points at</dt>
        <dd>
          {data.points_at.length === 0 ? none("Nothing outside itself.")
            : data.points_at.map((c) => (
              <p key={c.slot}><span className="id">{c.slot}</span> → <strong>{c.class}</strong> · {from(c.module)}</p>))}
        </dd>
        <dt>Adds to</dt>
        <dd>
          {data.adds_to.length === 0 ? none("No other module's things.")
            : data.adds_to.map((c) => (
              <p key={c.slot}><span className="id">{c.slot}</span> on <strong>{c.class}</strong> · {from(c.module)}</p>))}
        </dd>
        <dt>Fills</dt>
        <dd>
          {data.fills.length === 0 ? none("No role.")
            : data.fills.map((c) => (
              <p key={`${c.class}-${c.role}`}><strong>{c.class}</strong> fills {c.role} · {from(c.module)}</p>))}
        </dd>
        <dt>Built on by</dt>
        <dd>
          {data.built_on_by.length === 0
            ? none("No shared module builds on it yet.")
            : data.built_on_by.map((b) => (
              <p key={b.name}>
                <strong>{b.title}</strong> · {from({ name: b.name, version: b.version })}
                <span className="quiet"> pins {b.pins}{b.pins !== pin.version ? "" : ", this version"}</span>
              </p>))}
          <p className="quiet">Applications are private to their business and are not listed.</p>
        </dd>
      </dl>
    </section>
  );
}

function DiffView({ name, version, other }: { name: string; version: string; other: string }) {
  const [older, newer] = Number(other.slice(1)) < Number(version.slice(1)) ? [other, version] : [version, other];
  const { data, error } = useLoad<ModuleDiff>(() => modulesApi.diff(name, older, newer), [name, older, newer]);
  if (error) return <p className="failure" role="alert">{error}</p>;
  if (!data) return <p className="chips quiet">Reading…</p>;
  const d = data.diff;
  const lines: { kind: "added" | "removed" | "changed"; text: string }[] = [];
  d.imports.removed.forEach((i) => lines.push({ kind: "removed", text: `pin ${i}` }));
  d.imports.added.forEach((i) => lines.push({ kind: "added", text: `pin ${i}` }));
  d.classes.added.forEach((c) => lines.push({ kind: "added", text: `class ${c}` }));
  d.classes.removed.forEach((c) => lines.push({ kind: "removed", text: `class ${c}` }));
  d.classes.changed.forEach((c) => {
    const parts = [
      ...c.slots_added.map((s) => `gains ${s}`),
      ...c.slots_removed.map((s) => `loses ${s}`),
      ...Object.keys(c.changes).map((f) => `${f} changed`),
    ];
    lines.push({ kind: "changed", text: `class ${c.name}: ${parts.join(", ")}` });
  });
  d.slots.renamed.forEach((r) =>
    lines.push({ kind: "changed", text: `slot ${r.from} renamed to ${r.to}; same predicate ${r.slot_uri}, so its facts carry over` }));
  d.slots.added.forEach((s) => lines.push({ kind: "added", text: `slot ${s}` }));
  d.slots.removed.forEach((s) => lines.push({ kind: "removed", text: `slot ${s}` }));
  d.slots.changed.forEach((s) =>
    lines.push({ kind: "changed", text: `slot ${s.name}: ${Object.entries(s.changes).map(([f, c]) => `${f} ${String(c.from ?? "none")} to ${String(c.to ?? "none")}`).join(", ")}` }));

  return (
    <div className="diff">
      <p className="quiet">From {older} to {newer}</p>
      {lines.length === 0 ? <p className="quiet">No difference in what either version declares.</p> : (
        <ul>
          {lines.map((l, i) => (
            <li key={i} className={`diff-${l.kind}`}>
              <span className="diff-mark" aria-label={l.kind}>{l.kind === "added" ? "+" : l.kind === "removed" ? "−" : "~"}</span>
              {l.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

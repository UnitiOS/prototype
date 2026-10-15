// The business lens of an application: what the page opens on.
//
// The owner reads their business here, not modules: things, events and numbers
// in words, a small mark of whose module a thing came from, the fields other
// modules add to a thing shown inside it, and a card when something the
// application uses has a new version — what changes, and whether its own
// examples still hold on it, before anything moves. Everything technical is one
// click away, under "How it works"; none of it is repeated here.

import { useState } from "react";
import { ApiError, appApi, studioApi } from "./api";
import type {
  Application, Business, CellSource, Clocks, FormField, FormSpec, Pin, Projection,
  Update,
} from "./api";
import { emptyCell, formSections, InstallForm, useLoad } from "./application";
import { day, fromInput, toInput } from "./format";
import {
  blockedSaid, called, changeSaid, choiceLabel, columnMark, columnName, examplesSaid,
  exampleState, inUseSaid, lensGroups, moveSteps, STAYS,
} from "./lens";
import type { AppPick } from "./route";
import { fieldLabel, holds } from "./studioMap";

function Trouble({ error }: { error: string }) {
  return <p className="failure" role="alert">Something went wrong: {error}</p>;
}

export function BusinessView(
  { app, pin, pick, clocks, onPick, business, onInstalled }: {
    app: Application; pin: Pin; pick: AppPick; clocks: Clocks;
    onPick: (next: AppPick) => void; business: Business | null; onInstalled: () => void;
  },
) {
  const groups = lensGroups(app);
  const chosen = pick.klass ?? groups[0]?.items[0]?.class ?? null;
  const table = app.tables.find((t) => t.class === chosen) ?? null;

  return (
    <>
      <section className="panel">
        <header className="detail-head">
          <h2>{app.title ?? called(app.name)}</h2>
          {app.description && <p>{app.description}</p>}
          {business && <InUseLine app={app} business={business} clocks={clocks}
            onInstalled={onInstalled} />}
          <p className="chips">
            <button className="link" onClick={() => onPick({ ...pick, how: true })}>
              How it works
            </button>
          </p>
        </header>
      </section>

      {app.kind === "application" && <Updates app={app} pin={pin} />}

      <main className="body">
        <nav className="list lens-list" aria-label="The business">
          {groups.map((g) => (
            <div key={g.lens} className="lens-group">
              <p className="list-head">
                {g.heading} <span className="quiet">— {g.says}</span>
              </p>
              <ul>
                {g.items.map((item) => {
                  const on = item.class === chosen;
                  return (
                    <li key={item.class}>
                      <button className={`row row-stacked${on ? " row-selected" : ""}`}
                        aria-current={on}
                        onClick={() => onPick({ ...pick, klass: item.class, column: null,
                          keys: null, stating: false })}>
                        <span>{item.name}</span>
                        {item.mark && <span className="quiet mark">from {item.mark}</span>}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
        {chosen && table
          ? <BusinessTable app={app} pin={pin} klass={chosen} module={table.module}
              entities={table.shape === "entities"} pick={pick} onPick={onPick} clocks={clocks} />
          : <p className="empty">Nothing is kept here yet.</p>}
      </main>
    </>
  );
}

function InUseLine(
  { app, business, clocks, onInstalled }:
  { app: Application; business: Business; clocks: Clocks; onInstalled: () => void },
) {
  const { line, installable } = inUseSaid(app, business, day(clocks.validAt), day);
  return (
    <div className={`check${installable ? "" : " check-clean"}`}>
      <p className="check-verdict">{line}</p>
      {installable && <InstallForm app={app} clocks={clocks} onInstalled={onInstalled} />}
    </div>
  );
}

// ---- a new version of something it uses ----------------------------------------

function Updates({ app, pin }: { app: Application; pin: Pin }) {
  const updates = useLoad<Update[]>(() => appApi.updates(pin.name, pin.version),
    [pin.name, pin.version]);
  if (updates.error) return <section className="panel"><Trouble error={updates.error} /></section>;
  if (!updates.data || updates.data.length === 0) return null;
  return (
    <>
      {updates.data.map((u) => <UpdateCard key={u.module} app={app} update={u} />)}
    </>
  );
}

function UpdateCard({ app, update: u }: { app: Application; update: Update }) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const blocked = blockedSaid(u);

  // The move is the Studio's ordinary steps, sent as the page sends any: a
  // draft of this application with the one version moved. A draft already
  // open is moved in place, and a step it has already taken is not taken
  // again; the person seals it in the Studio.
  const prepare = async () => {
    setBusy(true);
    setFailed(null);
    try {
      const open = (await studioApi.drafts()).some((d) => d.name === app.name);
      const held = open ? (await studioApi.draft(app.name)).pins : undefined;
      for (const { step, args } of moveSteps(u, held)) {
        await studioApi.step(app.name, step, args);
      }
      window.location.hash = `#/studio?name=${encodeURIComponent(app.name)}`;
    } catch (e) {
      setFailed(e instanceof ApiError ? e.message : "The draft could not be prepared.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel update" aria-label={`A new version of ${u.title}`}>
      <header className="detail-head">
        <h3>{u.title} has a new version</h3>
        <p className="quiet">This application uses {u.pinned}; {u.latest} is available.</p>
      </header>
      {u.changes.length > 0 ? (
        <ul className="changes">
          {u.changes.map((c, i) => (
            <li key={i}>
              {changeSaid(c)}
              {c.description && <span className="quiet block">{c.description}</span>}
            </li>
          ))}
        </ul>
      ) : <p className="quiet">Nothing it keeps changes; only how it is worked out.</p>}
      <p className={u.examples.some((e) => exampleState(e) === "differs") ? "drift" : ""}>
        {examplesSaid(u)}
      </p>
      {u.examples.length > 1 || u.examples.some((e) => exampleState(e) !== "holds") ? (
        <ul className="changes">
          {u.examples.map((e) => (
            <li key={e.name}>
              <span className={`badge badge-${exampleState(e) === "holds" ? "in-use" : "awaiting"}`}>
                {exampleState(e)}</span> {e.says}
            </li>
          ))}
        </ul>
      ) : null}
      <p className="quiet">{STAYS}</p>
      {blocked
        ? <p className="drift">{blocked}</p>
        : (
          <p className="chips">
            <button className="button" disabled={busy} onClick={prepare}>
              {busy ? "Preparing…" : `Prepare the move to ${u.latest}`}
            </button>
            <span className="quiet">
              Opens a draft in the Studio. Nothing changes until it is finished there and put to use.
            </span>
          </p>
        )}
      {failed && <Trouble error={failed} />}
    </section>
  );
}

// ---- one table -------------------------------------------------------------------

function keysOf(table: Projection, row: (string | null)[]): Record<string, string> {
  const keys: Record<string, string> = {};
  table.columns.forEach((c, i) => {
    if (c.kind === "key" || c.kind === "identity") keys[c.name] = String(row[i] ?? "");
  });
  return keys;
}

function BusinessTable(
  { app, pin, klass, module, entities, pick, onPick, clocks }: {
    app: Application; pin: Pin; klass: string; module: Pin | null; entities: boolean;
    pick: AppPick; onPick: (next: AppPick) => void; clocks: Clocks;
  },
) {
  const [written, setWritten] = useState(0);
  const { data, error } = useLoad<Projection>(
    () => appApi.projection(pin.name, pin.version, klass, clocks),
    [pin.name, pin.version, klass, clocks.validAt.getTime(), clocks.asOf.getTime(), written]);
  if (error) return <Trouble error={error} />;
  if (!data) return <p className="quiet">Working it out…</p>;

  const name = called(klass);
  // The column saying which class a row is stays under "How it works".
  const shownColumns = data.columns.map((c, j) => [c, j] as const).filter(([c]) => !c.carries_class);
  const keyColumns = data.columns.filter((c) => c.kind === "key" || c.kind === "identity");
  const values = pick.keys === null ? [] : pick.keys.split(",");
  const picked = pick.column && values.length === keyColumns.length
    ? { column: pick.column,
        keys: Object.fromEntries(keyColumns.map((c, i) => [c.name, values[i]])) }
    : null;
  const open = (column: string | null, keys: Record<string, string> | null) =>
    onPick({ ...pick, column, keys: keys ? keyColumns.map((c) => keys[c.name]).join(",") : null });
  const shown = picked ? data.columns.find((c) => c.name === picked.column) ?? null : null;

  return (
    <article className="detail">
      <header className="detail-head">
        <h2>{name}</h2>
        <p className="quiet">As things stood on {day(data.valid_at)}.</p>
        {entities && (
          <p className="chips">
            <button className="button"
              onClick={() => onPick({ ...pick, stating: !pick.stating, column: null, keys: null })}>
              {pick.stating ? "Never mind" : `Record a new ${name.toLowerCase()}`}
            </button>
          </p>
        )}
      </header>

      {pick.stating && (
        <BusinessForm pin={pin} klass={klass} clocks={clocks}
          onWritten={() => setWritten(written + 1)} />
      )}

      <div className="scroll">
        <table className="projection">
          <thead>
            <tr>
              {shownColumns.map(([c]) => {
                const mark = columnMark(app, module, c);
                return (
                  <th key={c.name}>
                    <span className="column-head">{columnName(klass, c)}</span>
                    {c.awaiting && <span className="badge badge-awaiting">not computed yet</span>}
                    {mark && <span className="quiet block">from {mark}</span>}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => {
              const keys = keysOf(data, row);
              return (
                <tr key={i}>
                  {shownColumns.map(([c, j]) => {
                    const value = row[j];
                    const on = picked?.column === c.name
                      && JSON.stringify(picked.keys) === JSON.stringify(keys);
                    return (
                      <td key={j} className={c.type === "text" ? "" : "num"}>
                        <button className={`cell${on ? " cell-on" : ""}`} aria-current={on}
                          title="Where does this come from?"
                          onClick={() => (on ? open(null, null) : open(c.name, keys))}>
                          {value === null ? <span className="quiet">{emptyCell(c)}</span> : String(value)}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {data.rows.length === 0 && <p className="empty">Nothing recorded answers this on that day.</p>}

      {shown && picked && (
        <section className="fact">
          <div className="fact-head"><h3>{columnName(klass, shown)}</h3></div>
          {shown.description && <p className="rule">{shown.description}</p>}
          <BusinessCell pin={pin} klass={klass} column={shown.name} keys={picked.keys}
            clocks={clocks} />
        </section>
      )}
    </article>
  );
}

function BusinessCell(
  { pin, klass, column, keys, clocks }:
  { pin: Pin; klass: string; column: string; keys: Record<string, string>; clocks: Clocks },
) {
  const { data, error } = useLoad<CellSource>(
    () => appApi.cell(pin.name, pin.version, klass, column, keys, clocks),
    [pin.name, pin.version, klass, column, JSON.stringify(keys),
      clocks.validAt.getTime(), clocks.asOf.getTime()]);
  if (error) return <Trouble error={error} />;
  if (!data) return <p className="quiet">Reading…</p>;
  if (data.awaiting) {
    return <p className="quiet rule">Not computed yet: how to work it out is written and agreed, and the system does not compute it yet, so it stays empty.</p>;
  }
  if (data.kind === "expression") {
    return (
      <p className="quiet rule">
        Worked out from {data.reads.map((r) => fieldLabel(r, klass)).join(" and ")} in the same row.
      </p>
    );
  }
  if (data.statements.length === 0) {
    return <p className="quiet rule">Nothing has been recorded here, which is why it is empty rather than nought.</p>;
  }
  if (data.kind !== "aggregate") {
    const s = data.statements[0];
    return <p className="quiet rule">Recorded as true from {day(s.valid_from)}.</p>;
  }
  return (
    <div className="rule">
      <p className="quiet">Worked out from {data.statements.length} {data.statements.length === 1 ? "record" : "records"}:</p>
      <ul className="changes">
        {data.statements.map((s) => (
          <li key={s.assertion_id}>
            {s.subject_uri ?? "a record"}: {s.value} <span className="quiet">({day(s.valid_from)})</span>
          </li>
        ))}
      </ul>
      {data.cut_off && <p className="quiet">Only the first of them are shown.</p>}
    </div>
  );
}

// ---- recording something new ---------------------------------------------------

function BusinessForm(
  { pin, klass, clocks, onWritten }:
  { pin: Pin; klass: string; clocks: Clocks; onWritten: () => void },
) {
  const { data, error } = useLoad<FormSpec>(
    () => appApi.form(pin.name, pin.version, klass, clocks), [pin.name, pin.version, klass]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [code, setCode] = useState("");
  const [actor, setActor] = useState("");
  const [from, setFrom] = useState(toInput(clocks.validAt));
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (error) return <Trouble error={error} />;
  if (!data) return <p className="quiet">Reading…</p>;

  const send = async () => {
    setBusy(true);
    setFailed(null);
    try {
      await appApi.state({
        name: pin.name, version: pin.version, class: klass, subject: code.trim(),
        actor: actor.trim(), valid_from: (fromInput(from) ?? clocks.validAt).toISOString(), values,
      });
      setDone(true);
      setValues({});
      setCode("");
      onWritten();
    } catch (e) {
      setFailed(e instanceof ApiError ? e.message : "It could not be recorded.");
    } finally {
      setBusy(false);
    }
  };

  const field = (f: FormField) => (
    <label key={f.name} className="field">
      <span>{fieldLabel(f.name, klass, f.title)}</span>
      {f.options.length > 0 || f.ref ? (
        <select value={values[f.name] ?? ""}
          onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}>
          <option value="">—</option>
          {f.options.map((o) => <option key={o.uri} value={o.uri}>{choiceLabel(o) || o.uri}</option>)}
        </select>
      ) : (
        <input value={values[f.name] ?? ""}
          onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} />
      )}
      <small>
        {f.description || (f.ref ? `One of the ${called(f.range ?? "").toLowerCase()} records.`
          : holds(f.range))}
      </small>
    </label>
  );
  const ready = code.trim() !== "" && actor.trim() !== "" && Object.values(values).some((v) => v !== "");

  return (
    <section className="fact">
      <div className="fact-head"><h3>New {called(klass).toLowerCase()}</h3></div>
      <div className="form">
        <label className="field">
          <span>Code</span>
          <input value={code} placeholder="a short code, like kc:r3" onChange={(e) => setCode(e.target.value)} />
          <small>What it will be known by. A code already used means the same one.</small>
        </label>
        <label className="field">
          <span>Who records it</span>
          <input value={actor} placeholder="your name" onChange={(e) => setActor(e.target.value)} />
          <small>Kept beside what is recorded.</small>
        </label>
        <label className="field">
          <span>True from</span>
          <input type="datetime-local" value={from} onChange={(e) => setFrom(e.target.value)} />
          <small>From when this is true, not when it is written down.</small>
        </label>
        {data.fields.filter((f) => !f.section && f.name !== data.type_slot).map(field)}
        {formSections(data.fields).map(([title, fields]) => (
          <fieldset key={title} className="form-section">
            <legend>{title}</legend>
            {fields.map(field)}
          </fieldset>
        ))}
      </div>
      {failed && <Trouble error={failed} />}
      {done && <p className="rule">Recorded.</p>}
      <p className="chips">
        <button className="button" disabled={!ready || busy} onClick={send}>
          {busy ? "Recording…" : "Record it"}
        </button>
        {!ready && <span className="quiet">A code, who records it, and at least one field.</span>}
      </p>
    </section>
  );
}

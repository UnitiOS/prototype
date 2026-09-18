// An application: a set of pinned modules, read as one map.
//
// Nothing here is a new kind of thing in the store — an application is one
// sealed version that pins others and declares the tables somebody wants. So
// this page picks a version, draws every class its pins let it see, fills one
// of its tables from the log at the two clocks in the URL, and lets a person
// state something new into the same log.
//
// Every number on this page can be taken apart. A cell nobody can explain is a
// cell nobody should act on.

import { useEffect, useState } from "react";
import { ApiError, appApi, modulesApi } from "./api";
import type {
  Application, CellSource, ClassGraph as Graph, Clocks, Column, FormSpec,
  ModuleGraph, Pin, Projection, Written,
} from "./api";
import { ClassGraph } from "./ClassGraph";
import { day, fromInput, instant, toInput } from "./format";
import type { AppPick } from "./route";

function useLoad<T>(load: (() => Promise<T>) | null, deps: unknown[]) {
  const [state, setState] = useState<{ data?: T; error?: string }>({});
  useEffect(() => {
    if (!load) { setState({}); return; }
    let live = true;
    load()
      .then((data) => live && setState({ data }))
      .catch((e) => live && setState({
        error: e instanceof ApiError ? e.message : "Something failed while reading the API.",
      }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

const pinText = (p: Pin) => `${p.name}@${p.version}`;

/** A version nothing else pins, which pins something itself: a root of the graph. */
function roots(graph: ModuleGraph): Pin[] {
  const imports = graph.edges.filter((e) => e.kind === "imports");
  const pinned = new Set(imports.map((e) => `${e.to.name}@${e.to.version}`));
  return graph.nodes
    .filter((n) => n.latest)
    .filter((n) => !pinned.has(`${n.name}@${n.version}`))
    .filter((n) => imports.some((e) => e.from.name === n.name && e.from.version === n.version))
    .map((n) => ({ name: n.name, version: n.version }));
}

export function ApplicationPage(
  { pick, clocks, onPick }: { pick: AppPick; clocks: Clocks; onPick: (next: AppPick) => void },
) {
  const graph = useLoad<ModuleGraph>(() => modulesApi.graph(), []);
  const candidates = graph.data ? roots(graph.data) : [];

  // Nothing here names an application: the one offered first is whichever
  // sealed version nothing else pins, which is what being an application is.
  useEffect(() => {
    if (!pick.name && candidates.length > 0) {
      onPick({ ...pick, name: candidates[0].name, version: candidates[0].version });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph.data]);

  const chosen = pick.name && pick.version ? { name: pick.name, version: pick.version } : null;

  return (
    <>
      {graph.error && <p className="failure" role="alert">{graph.error}</p>}
      {graph.data && candidates.length === 0 && (
        <p className="empty">
          No sealed version pins another one, so there is nothing here yet that composes.
        </p>
      )}
      {candidates.length > 1 && (
        <nav className="chips chips-inline" aria-label="Applications">
          <span className="quiet">Application</span>
          {candidates.map((c) => {
            const on = chosen?.name === c.name && chosen?.version === c.version;
            return (
              <button key={pinText(c)} className={`version-chip${on ? " version-chip-on" : ""}`}
                aria-current={on}
                onClick={() => onPick({ name: c.name, version: c.version, klass: null,
                  column: null, keys: null, stating: false })}>
                {pinText(c)}
              </button>
            );
          })}
        </nav>
      )}
      {chosen && <ApplicationView pin={chosen} pick={pick} clocks={clocks} onPick={onPick} />}
    </>
  );
}

function ApplicationView(
  { pin, pick, clocks, onPick }:
  { pin: Pin; pick: AppPick; clocks: Clocks; onPick: (next: AppPick) => void },
) {
  const klass = pick.klass;
  const app = useLoad<Application>(() => appApi.read(pin.name, pin.version), [pin.name, pin.version]);
  const classes = useLoad<Graph>(() => modulesApi.classes(pin.name, pin.version), [pin.name, pin.version]);
  const [focus, setFocus] = useState<string | null>(null);

  if (app.error) return <p className="failure" role="alert">{app.error}</p>;
  if (!app.data) return <p className="quiet">Reading…</p>;
  const a = app.data;
  const chosen = klass ?? (a.tables[0]?.class ?? null);
  const table = a.tables.find((t) => t.class === chosen) ?? null;

  return (
    <>
      <section className="panel">
        <header className="detail-head">
          <h2>
            <span className="id">{a.name}</span> {a.version}
            {a.purpose && <span className="badge badge-demo">{a.purpose}</span>}
          </h2>
          <p className="quiet">
            One map, made of {a.modules.length} pinned {a.modules.length === 1 ? "version" : "versions"}:{" "}
            {a.modules.map((m) => pinText(m)).join(", ")}. It fills {a.tables.length}{" "}
            {a.tables.length === 1 ? "table" : "tables"}, and declares {a.tables.filter((t) => t.module?.name === a.name).length} of the classes behind them.
          </p>
          {a.description && <p>{a.description}</p>}
        </header>
        {classes.error && <p className="failure" role="alert">{classes.error}</p>}
        {classes.data && <ClassGraph graph={classes.data} selected={focus} onSelect={setFocus} />}
      </section>

      <main className="body">
        <div className="list">
          <p className="list-head quiet">Tables this application can fill</p>
          <ul>
            {a.tables.map((t) => {
              const on = t.class === chosen;
              return (
                <li key={t.class}>
                  <button className={`row row-stacked${on ? " row-selected" : ""}`}
                    aria-current={on}
                    onClick={() => {
                      onPick({ ...pick, klass: t.class, column: null, keys: null,
                        stating: false });
                      setFocus(t.class);
                    }}>
                    <span>
                      {t.class}
                      <span className={`badge badge-${t.shape}`}>{t.shape === "grouped" ? "derived" : "entities"}</span>
                    </span>
                    <span className="quiet">
                      {t.table}, {t.columns} columns
                      {t.module && t.module.name !== a.name && <>, from <span className="id">{t.module.name}</span></>}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
        {chosen && table
          ? <ProjectionView pin={pin} klass={chosen} shape={table.shape} pick={pick}
              onPick={onPick} clocks={clocks} appName={a.name} />
          : <p className="empty">This application fills no table yet.</p>}
      </main>
    </>
  );
}

function ruleText(col: Column): string {
  const rule = col.rule;
  if (!rule) {
    if (col.kind === "key") return "The grouping. One row per distinct value of this column.";
    if (col.kind === "identity") return "The URI the log registered this entity under.";
    if (col.kind === "stated") return "Whatever stands under this slot at the two clocks.";
    return "No rule reaches this column, so it is a column of nulls.";
  }
  if (rule.kind === "aggregate") {
    const by = Object.entries(rule.by ?? {}).map(([k, v]) => `${k} = ${v}`).join(", ");
    return `Every ${rule.over} the log holds, ${rule.operator} of ${rule.measure}, grouped by ${by}.`;
  }
  if (rule.kind === "parameter") {
    return `Not computed from the rows: one fact the log holds under ${rule.slot_uri} about whatever ${rule.of} names. Where nobody stated one, the cell is empty.`;
  }
  return `Arithmetic over the columns beside it: ${rule.expression}`;
}

// A link into the kernel explorer, at the same two clocks. A number here and
// the statement it came from are one thing seen from two sides, so the page
// never makes a reader copy an id across.
function kernelHref(tab: "entities" | "actions", id: string, clocks: Clocks): string {
  const query = new URLSearchParams({
    valid_at: clocks.validAt.toISOString(),
    as_of: clocks.asOf.toISOString(),
  });
  return `#/${tab}/${id}?${query}`;
}

/** The grouping values of one row: what identifies the cell a reader clicked. */
function keysOf(table: Projection, row: (string | null)[]): Record<string, string> {
  const keys: Record<string, string> = {};
  table.columns.forEach((c, i) => {
    if (c.kind === "key" || c.kind === "identity") keys[c.name] = String(row[i] ?? "");
  });
  return keys;
}

function ProjectionView(
  { pin, klass, shape, pick, onPick, clocks, appName }: {
    pin: Pin; klass: string; shape: "grouped" | "entities";
    pick: AppPick; onPick: (next: AppPick) => void; clocks: Clocks; appName: string;
  },
) {
  // Bumped after a submission, so the table is worked out again from a log
  // that now holds one more statement. Nothing is invalidated; it is derived.
  const [written, setWritten] = useState(0);
  const { data, error } = useLoad<Projection>(
    () => appApi.projection(pin.name, pin.version, klass, clocks),
    [pin.name, pin.version, klass, clocks.validAt.getTime(), clocks.asOf.getTime(), written]);
  if (error) return <p className="failure" role="alert">{error}</p>;
  if (!data) return <p className="quiet">Deriving…</p>;

  // Which cell is open lives in the URL, in key-column order, so a link to a
  // number is a link to the statements underneath it.
  const keyColumns = data.columns.filter((c) => c.kind === "key" || c.kind === "identity");
  const values = pick.keys === null ? [] : pick.keys.split(",");
  const picked = pick.column && values.length === keyColumns.length
    ? { column: pick.column,
        keys: Object.fromEntries(keyColumns.map((c, i) => [c.name, values[i]])) }
    : null;
  const open = (column: string | null, keys: Record<string, string> | null) =>
    onPick({ ...pick, column, keys: keys ? keyColumns.map((c) => keys[c.name]).join(",") : null });
  const stating = pick.stating;
  const shown = picked ? data.columns.find((c) => c.name === picked.column) ?? null : null;

  return (
    <article className="detail">
      <header className="detail-head">
        <h2>{data.class}</h2>
        <p className="quiet">
          <span className="id">{data.table}</span>, derived from the log at{" "}
          {instant(data.valid_at)} as the log knew it on {instant(data.as_of)}.
          Nothing is stored: move either clock and it is worked out again.
        </p>
        {shape === "entities" && (
          <p className="chips">
            <button className="button"
              onClick={() => onPick({ ...pick, stating: !stating, column: null, keys: null })}>
              {stating ? "Never mind" : `State a ${data.class}`}
            </button>
          </p>
        )}
      </header>

      {stating && (
        <FormPanel pin={pin} klass={klass} clocks={clocks}
          onWritten={() => setWritten(written + 1)} />
      )}

      <div className="scroll">
        <table className="projection">
          <thead>
            <tr>
              {data.columns.map((c) => (
                <th key={c.name}>
                  <span className="column-head">{c.name}</span>
                  <span className={`badge badge-${c.kind}`}>{c.kind}</span>
                  {c.module && c.module.name !== appName && (
                    <span className="quiet block">{c.module.name}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i}>
                {row.map((value, j) => {
                  const c = data.columns[j];
                  const keys = keysOf(data, row);
                  const on = picked?.column === c.name
                    && JSON.stringify(picked.keys) === JSON.stringify(keys);
                  return (
                    <td key={j} className={c.type === "text" ? "id" : "num"}>
                      <button className={`cell${on ? " cell-on" : ""}`} aria-current={on}
                        title="Where does this come from?"
                        onClick={() => (on ? open(null, null) : open(c.name, keys))}>
                        {value === null ? <span className="quiet">not stated</span> : String(value)}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.rows.length === 0 && <p className="empty">Nothing in the log answers this at these clocks.</p>}

      <section className="fact">
        <div className="fact-head">
          <h3>{shown ? `How ${shown.name} is worked out` : "Where a number comes from"}</h3>
          {picked && (
            <span className="quiet">
              {Object.entries(picked.keys).map(([k, v]) => `${k} = ${v}`).join(", ")}
            </span>
          )}
        </div>
        {shown ? (
          <div className="rule">
            <p>{ruleText(shown)}</p>
            {shown.description && <p className="quiet">{shown.description}</p>}
            <p className="quiet">
              The slot belongs to <span className="id">{shown.module ? pinText(shown.module) : "no module"}</span>,
              and holds {shown.type} in the operational store.
            </p>
          </div>
        ) : (
          <p className="quiet">Click any cell to see the statements it stands on.</p>
        )}
        {picked && (
          <CellPanel pin={pin} klass={klass} column={picked.column}
            keys={picked.keys} clocks={clocks} />
        )}
      </section>

      <details className="fact">
        <summary className="fact-head">
          <h3>The SQL this came from</h3>
          <span className="quiet">emitted, not written by hand</span>
        </summary>
        <pre className="transcript">{data.sql}</pre>
      </details>
    </article>
  );
}

function CellPanel(
  { pin, klass, column, keys, clocks }:
  { pin: Pin; klass: string; column: string; keys: Record<string, string>; clocks: Clocks },
) {
  const { data, error } = useLoad<CellSource>(
    () => appApi.cell(pin.name, pin.version, klass, column, keys, clocks),
    [pin.name, pin.version, klass, column, JSON.stringify(keys),
      clocks.validAt.getTime(), clocks.asOf.getTime()]);
  if (error) return <p className="failure" role="alert">{error}</p>;
  if (!data) return <p className="chips quiet">Reading the log…</p>;

  if (data.kind === "expression") {
    return (
      <div className="rule">
        <p className="quiet">
          Nothing in the log says this directly. It is{" "}
          <span className="id">{data.expression}</span>, so click{" "}
          {data.reads.map((r) => <span key={r} className="id">{r} </span>)}
          in this same row to see what those stand on.
        </p>
      </div>
    );
  }

  const total = data.kind === "aggregate"
    ? data.statements.reduce((sum, s) => sum + Number(s.value ?? 0), 0)
    : null;

  return (
    <div className="sources">
      <p className="quiet">
        {data.statements.length === 0
          ? "Nothing stands here. Nobody has stated it at these two clocks, which is why the cell is empty rather than nought."
          : data.kind === "aggregate"
            ? `${data.statements.length} statements, ${data.operator} ${total}. Each one is a ${data.over} the log holds.`
            : "One statement stands here."}
        {data.cut_off && " Only the first of them are shown."}
      </p>
      {data.statements.length > 0 && (
        <div className="scroll-plain">
          <table>
            <thead>
              <tr>
                <th>Subject</th><th>Predicate</th><th>Value</th>
                <th>Valid from</th><th>Recorded at</th><th>Said by</th>
              </tr>
            </thead>
            <tbody>
              {data.statements.map((s) => (
                <tr key={s.assertion_id}>
                  <td>
                    <a className="link id" href={kernelHref("entities", s.subject_id, clocks)}>
                      {s.subject_uri ?? s.subject_id.slice(0, 8)}
                    </a>
                  </td>
                  <td className="id">{s.predicate}</td>
                  <td className={s.names_entity ? "id" : "num"}>{s.value}</td>
                  <td className="num" title={instant(s.valid_from)}>{day(s.valid_from)}</td>
                  <td className="num" title={instant(s.recorded_at)}>{day(s.recorded_at)}</td>
                  <td>
                    <a className="link" href={kernelHref("actions", s.intent_id, clocks)}>
                      {s.source.replace(/_/g, " ")}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// The form. Every field, its range and its choices are read out of the map;
// nothing here is written per class. Submitting is one intent.
function FormPanel(
  { pin, klass, clocks, onWritten }:
  { pin: Pin; klass: string; clocks: Clocks; onWritten: () => void },
) {
  const { data, error } = useLoad<FormSpec>(
    () => appApi.form(pin.name, pin.version, klass, clocks),
    [pin.name, pin.version, klass]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [subject, setSubject] = useState("");
  const [actor, setActor] = useState("");
  const [validFrom, setValidFrom] = useState(toInput(clocks.validAt));
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [done, setDone] = useState<Written | null>(null);

  if (error) return <p className="failure" role="alert">{error}</p>;
  if (!data) return <p className="quiet">Reading the map…</p>;

  const send = async () => {
    setBusy(true);
    setFailed(null);
    try {
      const at = fromInput(validFrom) ?? clocks.validAt;
      const answer = await appApi.state({
        name: pin.name, version: pin.version, class: klass,
        subject: subject.trim(), actor: actor.trim(),
        valid_from: at.toISOString(), values,
      });
      setDone(answer);
      setValues({});
      setSubject("");
      onWritten();
    } catch (e) {
      setFailed(e instanceof ApiError ? e.message : "The submission failed.");
    } finally {
      setBusy(false);
    }
  };

  const ready = subject.trim() !== "" && actor.trim() !== ""
    && Object.values(values).some((v) => v !== "");

  return (
    <section className="fact">
      <div className="fact-head">
        <h3>State a {data.class}</h3>
        <span className="quiet">
          one action, one intent, written under <span className="id">{data.label}</span>
        </span>
      </div>
      <div className="form">
        <label className="field">
          <span>URI</span>
          <input value={subject} placeholder="prefix:name"
            onChange={(e) => setSubject(e.target.value)} />
          <small>What the log will call it. A URI it already holds is reused, never minted twice.</small>
        </label>
        <label className="field">
          <span>Who says so</span>
          <input value={actor} placeholder="your name"
            onChange={(e) => setActor(e.target.value)} />
          <small>Lands on the intent. Nothing reaches the log without somebody behind it.</small>
        </label>
        <label className="field">
          <span>Valid from</span>
          <input type="datetime-local" value={validFrom}
            onChange={(e) => setValidFrom(e.target.value)} />
          <small>From when this is true of the world, not when it is written down.</small>
        </label>

        {data.fields.map((f) => (
          <label key={f.name} className="field">
            <span>
              {f.title}
              {f.ref && <span className="badge badge-stated">names an entity</span>}
            </span>
            {f.ref ? (
              <select value={values[f.name] ?? ""}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}>
                <option value="">—</option>
                {f.options.map((o) => (
                  <option key={o.uri} value={o.uri}>{o.label ? `${o.label} — ${o.uri}` : o.uri}</option>
                ))}
              </select>
            ) : (
              <input value={values[f.name] ?? ""}
                onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} />
            )}
            <small>
              {f.description
                || (f.ref ? `One ${f.range}, chosen from ${f.options_from ?? "the log"}.` : f.range ?? "text")}
              {f.module && <> · <span className="id">{f.module.name}</span></>}
            </small>
          </label>
        ))}
      </div>
      {data.type_slot && (
        <p className="quiet rule">
          <span className="id">{data.type_slot}</span> is not a field: the map says which slot
          carries the class, and submitting states it. Nobody types the class in.
        </p>
      )}
      {failed && <p className="failure" role="alert">{failed}</p>}
      {done && (
        <p className="rule">
          Written: {done.assertions} statements
          {done.minted > 0 && `, ${done.minted} entity minted`} under one action.{" "}
          <a className="link" href={kernelHref("actions", done.intent_id, clocks)}>
            Open it in the kernel
          </a>
        </p>
      )}
      <p className="chips">
        <button className="button" disabled={!ready || busy} onClick={send}>
          {busy ? "Writing…" : "State it"}
        </button>
        {!ready && <span className="quiet">A URI, who says so, and at least one field.</span>}
      </p>
    </section>
  );
}

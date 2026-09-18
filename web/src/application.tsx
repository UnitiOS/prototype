// An application: a set of pinned modules, read as one map.
//
// Nothing here is a new kind of thing in the store — an application is one
// sealed version that pins others and declares the tables somebody wants. So
// this page picks a version, draws every class its pins let it see, and then
// fills one of its tables from the log at the two clocks in the URL.
//
// Every number on this page carries its rule beside it. A cell nobody can
// explain is a cell nobody should trust.

import { useEffect, useState } from "react";
import { ApiError, appApi, modulesApi } from "./api";
import type { Application, ClassGraph as Graph, Column, ModuleGraph, Pin, Projection } from "./api";
import { ClassGraph } from "./ClassGraph";
import { instant } from "./format";
import type { AppPick } from "./route";
import type { Clocks } from "./api";

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
                onClick={() => onPick({ name: c.name, version: c.version, klass: null })}>
                {pinText(c)}
              </button>
            );
          })}
        </nav>
      )}
      {chosen && <ApplicationView pin={chosen} klass={pick.klass} clocks={clocks}
        onPick={(klass) => onPick({ ...pick, klass })} />}
    </>
  );
}

function ApplicationView(
  { pin, klass, clocks, onPick }:
  { pin: Pin; klass: string | null; clocks: Clocks; onPick: (klass: string | null) => void },
) {
  const app = useLoad<Application>(() => appApi.read(pin.name, pin.version), [pin.name, pin.version]);
  const classes = useLoad<Graph>(() => modulesApi.classes(pin.name, pin.version), [pin.name, pin.version]);
  const [focus, setFocus] = useState<string | null>(null);

  if (app.error) return <p className="failure" role="alert">{app.error}</p>;
  if (!app.data) return <p className="quiet">Reading…</p>;
  const a = app.data;
  const chosen = klass ?? (a.tables[0]?.class ?? null);

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
                    aria-current={on} onClick={() => { onPick(t.class); setFocus(t.class); }}>
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
        {chosen
          ? <ProjectionView pin={pin} klass={chosen} clocks={clocks} appName={a.name} />
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

function ProjectionView(
  { pin, klass, clocks, appName }:
  { pin: Pin; klass: string; clocks: Clocks; appName: string },
) {
  const { data, error } = useLoad<Projection>(
    () => appApi.projection(pin.name, pin.version, klass, clocks),
    [pin.name, pin.version, klass, clocks.validAt.getTime(), clocks.asOf.getTime()]);
  const [column, setColumn] = useState<string | null>(null);

  if (error) return <p className="failure" role="alert">{error}</p>;
  if (!data) return <p className="quiet">Deriving…</p>;
  const shown = data.columns.find((c) => c.name === column) ?? null;

  return (
    <article className="detail">
      <header className="detail-head">
        <h2>{data.class}</h2>
        <p className="quiet">
          <span className="id">{data.table}</span>, derived from the log at{" "}
          {instant(data.valid_at)} as the log knew it on {instant(data.as_of)}.
          Nothing is stored: move either clock and it is worked out again.
        </p>
      </header>

      <div className="scroll">
        <table className="projection">
          <thead>
            <tr>
              {data.columns.map((c) => (
                <th key={c.name}>
                  <button className="link column-head" onClick={() => setColumn(column === c.name ? null : c.name)}
                    aria-current={column === c.name}>
                    {c.name}
                  </button>
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
                {row.map((cell, j) => (
                  <td key={j} className={data.columns[j].type === "text" ? "id" : "num"}>
                    {cell === null ? <span className="quiet">not stated</span> : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.rows.length === 0 && <p className="empty">Nothing in the log answers this at these clocks.</p>}

      <section className="fact">
        <div className="fact-head">
          <h3>{shown ? `How ${shown.name} is worked out` : "How a column is worked out"}</h3>
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
          <p className="quiet">Click a column heading to see the rule that fills it.</p>
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

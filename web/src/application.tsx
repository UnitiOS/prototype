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
  Application, CellSource, CheckReport, ClassGraph as Graph, Clocks, Column, FitReport,
  FormSpec, ModuleGraph, Pin, Projection, Refusal as RefusalSpec, Roles, Written,
} from "./api";
import { ClassGraph } from "./ClassGraph";
import { Failure, RefusalCard } from "./Refusal";
import { day, fromInput, instant, toInput } from "./format";
import type { AppPick } from "./route";

function useLoad<T>(load: (() => Promise<T>) | null, deps: unknown[]) {
  // The refusal travels beside the sentence, because a page that keeps only
  // the sentence has thrown away the repair.
  const [state, setState] =
    useState<{ data?: T; error?: string; refusal?: RefusalSpec | null }>({});
  useEffect(() => {
    if (!load) { setState({}); return; }
    let live = true;
    load()
      .then((data) => live && setState({ data }))
      .catch((e) => live && setState({
        error: e instanceof ApiError ? e.message : "Something failed while reading the API.",
        refusal: e instanceof ApiError ? e.refusal : null,
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
  // Every sealed version of the chosen application, oldest first. Not only the
  // newest: what a move would cost is asked from the version somebody is on,
  // and that is usually an older one.
  const siblings = (graph.data?.nodes ?? [])
    .filter((n) => n.name === chosen?.name)
    .map((n) => n.version)
    .sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));

  return (
    <>
      {graph.error && <Failure error={graph.error} refusal={graph.refusal} />}
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
                  column: null, keys: null, stating: false, against: null })}>
                {pinText(c)}
              </button>
            );
          })}
        </nav>
      )}
      {chosen && siblings.length > 1 && (
        <nav className="chips chips-inline" aria-label="Versions of this application">
          <span className="quiet">Version</span>
          {siblings.map((v) => {
            const on = chosen.version === v;
            return (
              <button key={v} className={`version-chip${on ? " version-chip-on" : ""}`}
                aria-current={on}
                onClick={() => onPick({ name: chosen.name, version: v, klass: null,
                  column: null, keys: null, stating: false, against: null })}>
                {v}
              </button>
            );
          })}
        </nav>
      )}
      {chosen && (
        <ApplicationView pin={chosen} pick={pick} clocks={clocks} onPick={onPick}
          siblings={siblings} />
      )}
    </>
  );
}

function ApplicationView(
  { pin, pick, clocks, onPick, siblings }:
  { pin: Pin; pick: AppPick; clocks: Clocks; onPick: (next: AppPick) => void;
    siblings: string[] },
) {
  const klass = pick.klass;
  const app = useLoad<Application>(() => appApi.read(pin.name, pin.version), [pin.name, pin.version]);
  const classes = useLoad<Graph>(() => modulesApi.classes(pin.name, pin.version), [pin.name, pin.version]);
  const [focus, setFocus] = useState<string | null>(null);

  if (app.error) return <Failure error={app.error} refusal={app.refusal} />;
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
          <CheckStrip pin={pin} />
        </header>
        {classes.error && <Failure error={classes.error} refusal={classes.refusal} />}
        {classes.data && <ClassGraph graph={classes.data} selected={focus} onSelect={setFocus} />}
      </section>

      <RolesPanel pin={pin} pick={pick} onPick={onPick} siblings={siblings} />

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

// Does this application hold? The same readers the compiler runs, with the
// refusals collected instead of thrown — a gate stops at the first problem,
// and somebody deciding what to fix wants all of them at once.
function CheckStrip({ pin }: { pin: Pin }) {
  const check = useLoad<CheckReport>(() => appApi.check(pin.name, pin.version),
    [pin.name, pin.version]);

  if (check.error) return <Failure error={check.error} refusal={check.refusal} />;
  if (!check.data) return null;
  const c = check.data;
  const hollow = c.tables.flatMap((t) => t.unfilled.map((u) => `${t.class}.${u}`));

  return (
    <div className={`check${c.clean ? " check-clean" : " check-dark"}`}>
      <p className="check-verdict">
        {c.clean
          ? `Every rule resolves. All ${c.tables.length} tables compile as they stand.`
          : `${c.refusals.length} of ${c.tables.length} tables do not compile as they stand.`}
      </p>
      {hollow.length > 0 && (
        <p className="quiet">
          No rule reaches {hollow.join(", ")}, so {hollow.length === 1 ? "it is a column" : "they are columns"} of nulls.
        </p>
      )}
      {c.refusals.map((r, i) => <RefusalCard key={i} refusal={r} at={r.class} />)}
    </div>
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
    const written = `Every ${rule.over} the log holds, ${rule.operator} of ${rule.measure}, grouped by ${by}.`;
    const covers = rule.covers ?? [];
    // A rule written against a role names nothing anybody owns, so the page
    // has to say what it actually reached — otherwise the number has no
    // visible source at all.
    if (covers.length === 0 || covers.join() === rule.over) return written;
    return `${written} ${rule.over} is a role: here it reaches ${covers.join(", ")}, through ${(rule.measure_uris ?? []).join(", ")}.`;
  }
  if (rule.kind === "parameter") {
    return `Not computed from the rows: one fact the log holds under ${(rule.slot_uris ?? []).join(" or ")} about whatever ${rule.of} names. Where nobody stated one, the cell is empty.`;
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
  const { data, error, refusal } = useLoad<Projection>(
    () => appApi.projection(pin.name, pin.version, klass, clocks),
    [pin.name, pin.version, klass, clocks.validAt.getTime(), clocks.asOf.getTime(), written]);
  if (error) return <Failure error={error} refusal={refusal} at={klass} />;
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
  const { data, error, refusal } = useLoad<CellSource>(
    () => appApi.cell(pin.name, pin.version, klass, column, keys, clocks),
    [pin.name, pin.version, klass, column, JSON.stringify(keys),
      clocks.validAt.getTime(), clocks.asOf.getTime()]);
  if (error) return <Failure error={error} refusal={refusal} />;
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
  const { data, error, refusal } = useLoad<FormSpec>(
    () => appApi.form(pin.name, pin.version, klass, clocks),
    [pin.name, pin.version, klass]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [subject, setSubject] = useState("");
  const [actor, setActor] = useState("");
  const [validFrom, setValidFrom] = useState(toInput(clocks.validAt));
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<{ error: string; refusal: RefusalSpec | null } | null>(null);
  const [done, setDone] = useState<Written | null>(null);

  if (error) return <Failure error={error} refusal={refusal} at={klass} />;
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
      setFailed({
        error: e instanceof ApiError ? e.message : "The submission failed.",
        refusal: e instanceof ApiError ? e.refusal : null,
      });
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
      {failed && <Failure error={failed.error} refusal={failed.refusal} at={klass} />}
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

// ---------------------------------------------------------------- roles

// What this application stands on, and what it would cost to stand on
// something else. Both are read straight out of sealed content: nobody
// maintains this page's contents, and it cannot drift from what the compiler
// does, because it is the same walk.
function RolesPanel(
  { pin, pick, onPick, siblings }: {
    pin: Pin; pick: AppPick; onPick: (next: AppPick) => void; siblings: string[];
  },
) {
  const roles = useLoad<Roles>(() => appApi.roles(pin.name, pin.version),
    [pin.name, pin.version]);
  const others = siblings.filter((v) => v !== pin.version);
  const against = pick.against && others.includes(pick.against) ? pick.against : null;

  if (roles.error) return <Failure error={roles.error} refusal={roles.refusal} />;
  if (!roles.data) return null;
  const carried = roles.data.roles.filter((r) => r.bindings.length > 0 || r.filled_by.length > 0);

  return (
    <section className="panel roles">
      <header className="detail-head">
        <h3>What it stands on</h3>
        <p className="quiet">
          A role is an obligation, not a description of the world: a class mixes one in
          and thereby promises to name a slot of its own for each binding. A rule written
          against the role reaches whoever kept the promise — which is the only seam a
          module can be replaced at.
        </p>
      </header>

      {carried.length === 0 && (
        <p className="empty">
          Nothing this version pins declares a role, so there is nothing here yet for a
          rule to be written against. Its rules name classes in the modules under it, and
          replacing one of those modules breaks them — which is what the comparison
          below says in numbers.
        </p>
      )}

      {carried.length > 0 && (
      <table className="grid roles-grid">
        <thead>
          <tr><th>Role</th><th>Binding</th><th>Filled by</th><th>Under the name</th></tr>
        </thead>
        <tbody>
          {carried.map((role) =>
            (role.bindings.length ? role.bindings : [null]).map((binding, i) => (
              <tr key={`${role.name}-${binding?.name ?? i}`}>
                {i === 0 && (
                  <th scope="row" rowSpan={Math.max(role.bindings.length, 1)}>
                    {role.name}
                    <span className="quiet block">{role.module.name}</span>
                  </th>
                )}
                <td>
                  {binding ? (
                    <>
                      {binding.name}
                      {binding.required && <span className="badge badge-must">must</span>}
                      {binding.range && <span className="quiet"> → {binding.range}</span>}
                    </>
                  ) : <span className="quiet">obliges nothing of its own</span>}
                </td>
                <td>
                  {role.filled_by.length === 0
                    ? <span className="quiet">nobody yet</span>
                    : role.filled_by.map((f) => (
                        <span key={f.class} className="filler">
                          {f.class}<span className="quiet"> · {f.module.name}</span>
                        </span>
                      ))}
                </td>
                <td>
                  {binding && role.filled_by.map((f) => (
                    <span key={f.class} className="filler">
                      {f.bindings[binding.name] ?? <span className="quiet">—</span>}
                    </span>
                  ))}
                </td>
              </tr>
            )))}
        </tbody>
      </table>
      )}

      {others.length > 0 && (
        <div className="swap">
          <p className="quiet">
            Weigh this version against another one of the same application: same rules,
            different pins.
          </p>
          <nav className="chips chips-inline" aria-label="Compare against">
            {others.map((v) => {
              const on = against === v;
              return (
                <button key={v} className={`version-chip${on ? " version-chip-on" : ""}`}
                  aria-current={on}
                  onClick={() => onPick({ ...pick, against: on ? null : v })}>
                  {pin.version} → {v}
                </button>
              );
            })}
          </nav>
          {against && <FitPanel pin={pin} against={against} />}
        </div>
      )}
    </section>
  );
}

function FitPanel({ pin, against }: { pin: Pin; against: string }) {
  const fit = useLoad<FitReport>(() => appApi.fit(pin.name, pin.version, against),
    [pin.name, pin.version, against]);

  if (fit.error) return <Failure error={fit.error} refusal={fit.refusal} />;
  if (!fit.data) return <p className="quiet">Working it out…</p>;
  const f = fit.data;

  return (
    <div className={`fit${f.clean ? " fit-clean" : " fit-dark"}`}>
      <p className="fit-verdict">
        {f.clean
          ? `Every rule still resolves. ${pin.version} can become ${against} without one of them being touched.`
          : `${f.dark.length} ${f.dark.length === 1 ? "rule does" : "rules do"} not survive this move.`}
      </p>

      {(f.pins.removed.length > 0 || f.pins.added.length > 0) && (
        <dl className="fit-block">
          <dt>Pins</dt>
          <dd>
            {f.pins.removed.map((p) => (
              <span key={pinText(p)} className="pill pill-out">− {pinText(p)}</span>))}
            {f.pins.added.map((p) => (
              <span key={pinText(p)} className="pill pill-in">+ {pinText(p)}</span>))}
          </dd>
        </dl>
      )}

      {f.roles.filter((r) => r.status !== "unchanged").length > 0 && (
        <dl className="fit-block">
          <dt>Roles</dt>
          <dd>
            {f.roles.filter((r) => r.status !== "unchanged").map((r) => (
              <p key={r.name}>
                <strong>{r.name}</strong> {r.status}: {r.before.join(", ") || "nobody"}
                {" → "}{r.after.join(", ") || "nobody"}
              </p>
            ))}
          </dd>
        </dl>
      )}

      {f.dark.length > 0 && (
        <dl className="fit-block">
          <dt>Would go dark</dt>
          <dd>
            {f.dark.map((d, i) => (
              d.refusal
                ? <RefusalCard key={i} refusal={d.refusal}
                    at={`${d.class}${d.column ? `.${d.column}` : ""}`} />
                : <p key={i}>
                    <strong>{d.class}{d.column ? `.${d.column}` : ""}</strong>
                    <span className="quiet block">{d.why}</span>
                  </p>
            ))}
          </dd>
        </dl>
      )}

      {f.rules.length > 0 && (
        <dl className="fit-block">
          <dt>Rules</dt>
          <dd>
            {f.rules.map((r) => (
              <p key={`${r.class}.${r.column}`}>
                <strong>{r.column}</strong>{" "}
                <span className={`badge badge-${r.status}`}>{r.status}</span>
                {r.status === "rebound" && (
                  <span className="quiet block">
                    {r.reads_before.join(", ")} → {r.reads_after.join(", ")}
                  </span>
                )}
              </p>
            ))}
          </dd>
        </dl>
      )}

      <dl className="fit-block">
        <dt>The log keeps</dt>
        <dd>
          {f.orphaned.length === 0
            ? <p className="quiet">Every predicate either side declares is still declared.</p>
            : <>
                <p>
                  {f.orphaned_statements} statements under {f.orphaned.length}{" "}
                  {f.orphaned.length === 1 ? "predicate" : "predicates"} that no module in the
                  new closure declares. Nothing is deleted and nothing is migrated — they stop
                  being read, and that is the whole of it.
                </p>
                <ul className="orphans">
                  {f.orphaned.map((o) => (
                    <li key={o.uri}>
                      <span className="id">{o.uri}</span>
                      <span className="quiet"> {o.held} · was {o.module.name}</span>
                    </li>
                  ))}
                </ul>
              </>}
        </dd>
      </dl>
    </div>
  );
}

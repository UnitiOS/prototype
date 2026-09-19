// The catalogue, and the health of one application's graph.
//
// Two questions, one page. The catalogue answers "what is there": every
// module, role, class and slot the store offers now, who fills which role, and
// which rules anywhere read what. The health report answers "what in this
// application is doing nothing": six findings that are not refusals — nothing
// stops, something is idle.
//
// Neither is written by anybody. Both are computed from sealed content, and
// the health report also counts the log, so both change the moment something
// is sealed or stated.

import { useEffect, useState } from "react";
import { catalogueApi, modulesApi } from "./api";
import type {
  CatalogueEntry, CatalogueFound, Diagnosis, DiagnosisCode, Finding, HealthReport,
  ModuleGraph, Pin, RuleRef,
} from "./api";
import { roots, useLoad } from "./application";
import { Failure, RefusalCard } from "./Refusal";
import type { CataloguePick } from "./route";

const pinText = (p: Pin) => `${p.name}@${p.version}`;

const KINDS: { kind: string | null; label: string }[] = [
  { kind: null, label: "Everything" },
  { kind: "module", label: "Modules" },
  { kind: "role", label: "Roles" },
  { kind: "class", label: "Classes" },
  { kind: "slot", label: "Slots" },
];

export function CataloguePage(
  { pick, onPick }: { pick: CataloguePick; onPick: (next: CataloguePick, replace?: boolean) => void },
) {
  return (
    <>
      <CatalogueView pick={pick} onPick={onPick} />
      <HealthView pick={pick} onPick={onPick} />
    </>
  );
}

// ---- the catalogue --------------------------------------------------------

function CatalogueView(
  { pick, onPick }: { pick: CataloguePick; onPick: (next: CataloguePick, replace?: boolean) => void },
) {
  // The text box is typed into; the URL follows it a moment later, so a
  // search can be sent as a link without every keystroke becoming history.
  const [text, setText] = useState(pick.q ?? "");
  useEffect(() => { setText(pick.q ?? ""); }, [pick.q]);
  useEffect(() => {
    const t = window.setTimeout(() => {
      if ((pick.q ?? "") !== text) onPick({ ...pick, q: text || null }, true);
    }, 250);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  const found = useLoad<CatalogueFound>(
    () => catalogueApi.find({ q: pick.q, kind: pick.kind, fills: pick.fills }),
    [pick.q, pick.kind, pick.fills]);
  // The filter choices come from the whole store, not from what the current
  // search happens to have left, or a filter could not be undone from here.
  const all = useLoad<CatalogueFound>(() => catalogueApi.find({}), []);

  const setFills = (fills: string | null) => onPick({ ...pick, fills });

  return (
    <section className="panel catalogue">
      <header className="detail-head">
        <h2>Catalogue</h2>
        <p className="quiet">
          Everything the store offers now: the newest sealed version of every module, and
          what it declares. Computed from what was sealed — nobody writes this page, so it
          cannot be out of date. <em>Read by</em> looks wider, at every sealed version of
          everything, because an application still pinned to an old version still reads.
        </p>
      </header>

      <div className="catalogue-controls">
        <label className="search catalogue-search">
          <span className="visually-hidden">Search the catalogue</span>
          <input type="search" value={text} placeholder="Search names, descriptions, predicates…"
            onChange={(e) => setText(e.target.value)} />
        </label>
        <nav className="chips-inline" aria-label="Kind">
          {KINDS.map(({ kind, label }) => {
            const on = (pick.kind ?? null) === kind;
            const held = all.data
              ? kind ? all.data.held[kind as keyof CatalogueFound["held"]]
                : Object.values(all.data.held).reduce((a, b) => a + b, 0)
              : null;
            return (
              <button key={label} className={`version-chip${on ? " version-chip-on" : ""}`}
                aria-current={on} onClick={() => onPick({ ...pick, kind })}>
                {label}{held !== null && <span className="chip-count"> {held}</span>}
              </button>
            );
          })}
        </nav>
        {all.data && (
          <label className="catalogue-fills">
            <span className="quiet">Fills</span>
            <select value={pick.fills ?? ""} onChange={(e) => setFills(e.target.value || null)}>
              <option value="">any role or binding</option>
              <optgroup label="Roles — the classes that fill it">
                {all.data.roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </optgroup>
              <optgroup label="Bindings — the slots that fill it">
                {all.data.bindings.map((b) => <option key={b} value={b}>{b}</option>)}
              </optgroup>
            </select>
          </label>
        )}
      </div>

      {found.error && <Failure error={found.error} refusal={found.refusal} />}
      {found.data && (
        <>
          <p className="quiet catalogue-count">
            {found.data.entries.length === 0
              ? "Nothing in the store matches."
              : `${found.data.entries.length} of ${Object.values(found.data.held).reduce((a, b) => a + b, 0)} entries.`}
          </p>
          <ul className="entries">
            {found.data.entries.map((e) => (
              <li key={`${e.kind}:${e.module.name}:${e.name}`}>
                <Entry entry={e} onFills={setFills} />
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function Readers({ rules }: { rules: RuleRef[] | undefined }) {
  if (!rules || rules.length === 0) {
    return <span className="quiet">no rule in any sealed version</span>;
  }
  return (
    <>
      {rules.map((r) => (
        <span key={`${pinText(r.module)} ${r.rule}`} className="pill">
          {r.rule} <span className="quiet">in {pinText(r.module)}</span>
        </span>
      ))}
    </>
  );
}

function Entry({ entry: e, onFills }: { entry: CatalogueEntry; onFills: (fills: string) => void }) {
  const fillsButton = (name: string) => (
    <button key={name} className="link" onClick={() => onFills(name)}
      title={`Show everything that fills ${name}`}>{name}</button>
  );
  return (
    <article className="entry">
      <header className="entry-head">
        <span className={`badge badge-kind-${e.kind}`}>{e.kind}</span>
        <strong className="id">{e.name}</strong>
        {e.kind === "slot" && e.uri && <span className="id quiet">{e.uri}</span>}
        <span className="quiet">{pinText(e.module)}</span>
        {e.purpose && <span className="badge badge-demo">{e.purpose}</span>}
      </header>
      {e.description && <p className="entry-text">{e.description}</p>}
      <dl className="entry-facts">
        {e.kind === "module" && <>
          <dt>Versions</dt><dd>{(e.versions ?? []).join(", ")}</dd>
          <dt>Pins</dt>
          <dd>{(e.pins ?? []).length ? (e.pins ?? []).map(pinText).join(", ") : <span className="quiet">nothing</span>}</dd>
          <dt>Declares</dt>
          <dd>
            {(e.declares?.classes ?? []).length} classes, {(e.declares?.slots ?? []).length} slots
          </dd>
        </>}
        {e.kind === "role" && <>
          <dt>Obliges</dt>
          <dd>
            {(e.bindings ?? []).length === 0
              ? <span className="quiet">no binding of its own — being one is the promise</span>
              : (e.bindings ?? []).map((b) => (
                <span key={b.name} className="pill">{b.name}{b.range ? `: ${b.range}` : ""}</span>
              ))}
          </dd>
          <dt>Filled by</dt>
          <dd>
            {(e.filled_by ?? []).length === 0
              ? <span className="quiet">nothing in the store</span>
              : (e.filled_by ?? []).map((f) => (
                <span key={`${f.class}${pinText(f.module)}`} className="pill">
                  {f.class} <span className="quiet">in {pinText(f.module)}</span>
                </span>
              ))}
          </dd>
          <dt>Rules over it</dt><dd><Readers rules={e.read_by} /></dd>
        </>}
        {e.kind === "class" && <>
          <dt>Fills</dt>
          <dd>{e.fills.length ? e.fills.map(fillsButton) : <span className="quiet">no role</span>}</dd>
          <dt>In the log</dt>
          <dd>{e.statable
            ? "the log can say an entity is one"
            : <span className="quiet">nothing can be stated to be one — it has no class slot</span>}</dd>
          <dt>Slots</dt><dd className="id">{(e.slots ?? []).join(", ") || "—"}</dd>
          <dt>Read by</dt><dd><Readers rules={e.read_by} /></dd>
        </>}
        {e.kind === "slot" && <>
          {e.abstract
            ? <><dt>Binding</dt><dd>a hole a role carries: each class filling the role names a slot of its own for it</dd></>
            : <><dt>On</dt><dd className="id">{(e.on ?? []).join(", ") || "—"}</dd></>}
          {e.range && <><dt>Range</dt><dd className="id">{e.range}</dd></>}
          {e.fills.length > 0 && <><dt>Fills</dt><dd>{e.fills.map(fillsButton)}</dd></>}
          {!e.abstract && <><dt>Read by</dt><dd><Readers rules={e.read_by} /></dd></>}
        </>}
      </dl>
    </article>
  );
}

// ---- health ---------------------------------------------------------------

const TITLES: Record<DiagnosisCode, { title: string; why: string }> = {
  dead_term: {
    title: "Stated, read by nothing",
    why: "Recorded in the log and computed on by no rule. Often that is fine — a label is " +
      "there for a person to read. It matters where a term was meant to be computed: one " +
      "that fills a role's binding was put there for a rule, and no rule here has " +
      "collected on that promise yet. Those come first.",
  },
  empty_column: {
    title: "Columns no rule fills",
    why: "A derived table's column with no rule behind it compiles, as nothing. The table " +
      "holds; this part of it says nothing.",
  },
  empty_class: {
    title: "Classes nothing has been",
    why: "The log could say an entity is one of these, and never has. A table of it has " +
      "no rows, and a rule reading it adds up nothing.",
  },
  unfilled_role: {
    title: "Roles nobody fills",
    why: "A rule written against one of these has no rows, because no class here keeps " +
      "its promise. Pinning a module whose class fills it is how it gets some.",
  },
  lagging_pin: {
    title: "Pins the store has moved past",
    why: "A pinned version never changes meaning, which is why a newer one does not reach " +
      "this application by itself. Moving is a decision: the application's Fit report " +
      "says what it would cost.",
  },
  orphaned_fact: {
    title: "Facts this application cannot see",
    why: "The log holds statements under predicates no module here declares. Nothing was " +
      "deleted — they are simply not read. Where another module declares them, pinning " +
      "it makes them readable again.",
  },
};

function HealthView(
  { pick, onPick }: { pick: CataloguePick; onPick: (next: CataloguePick, replace?: boolean) => void },
) {
  const graph = useLoad<ModuleGraph>(() => modulesApi.graph(), []);

  // Nothing here names an application. The one read first is a sealed version
  // nothing else pins — the same rule the Application area uses.
  useEffect(() => {
    if (!pick.name && graph.data) {
      const first = roots(graph.data)[0];
      if (first) onPick({ ...pick, name: first.name, version: first.version }, true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph.data]);

  const names = [...new Set((graph.data?.nodes ?? []).map((n) => n.name))].sort();
  const versions = (graph.data?.nodes ?? [])
    .filter((n) => n.name === pick.name)
    .map((n) => n.version)
    .sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));
  const chosen = pick.name && pick.version ? { name: pick.name, version: pick.version } : null;

  return (
    <section className="panel health">
      <header className="detail-head">
        <h2>Health of one application</h2>
        <p className="quiet">
          Six things about one sealed version and everything it pins, none of them a refusal:
          nothing here stops the application, each one is something doing nothing. Read
          against one application because "read by nothing" only means something against a
          particular set of rules. The log is counted whole — every statement ever recorded.
        </p>
        {graph.error && <Failure error={graph.error} refusal={graph.refusal} />}
        <nav className="chips-inline health-pick" aria-label="Module">
          <span className="quiet">Module</span>
          {names.map((n) => {
            const on = pick.name === n;
            const latest = (graph.data?.nodes ?? []).find((x) => x.name === n && x.latest);
            return (
              <button key={n} className={`version-chip${on ? " version-chip-on" : ""}`}
                aria-current={on}
                onClick={() => onPick({ ...pick, name: n, version: latest?.version ?? null })}>
                {n}
              </button>
            );
          })}
        </nav>
        {versions.length > 0 && (
          <nav className="chips-inline health-pick" aria-label="Version">
            <span className="quiet">Version</span>
            {versions.map((v) => {
              const on = pick.version === v;
              return (
                <button key={v} className={`version-chip${on ? " version-chip-on" : ""}`}
                  aria-current={on} onClick={() => onPick({ ...pick, version: v })}>
                  {v}
                </button>
              );
            })}
          </nav>
        )}
      </header>
      {chosen && <HealthReportView pin={chosen} />}
    </section>
  );
}

function HealthReportView({ pin }: { pin: Pin }) {
  const report = useLoad<HealthReport>(
    () => catalogueApi.health(pin.name, pin.version), [pin.name, pin.version]);
  if (report.error) return <Failure error={report.error} refusal={report.refusal} />;
  if (!report.data) return <p className="quiet">Reading…</p>;
  const h = report.data;

  return (
    <>
      <p className="quiet health-closure">
        {pinText(pin)} and what it pins: {h.modules.map(pinText).join(", ")}.
        {!h.counted && " The log could not be reached, so the three findings that need a count are not given."}
      </p>
      {h.refusals.map((r, i) => <RefusalCard key={i} refusal={r} at={r.class} />)}
      <div className="diagnoses">
        {h.diagnoses.map((d) => <DiagnosisBlock key={d.code} diagnosis={d} />)}
      </div>
      <details className="terms">
        <summary>
          Every predicate this application declares ({h.terms.length}), how often the log
          states it, and what reads it
        </summary>
        <div className="scroll">
          <table>
            <thead>
              <tr><th>Predicate</th><th>Declared by</th><th className="num">Stated</th><th>Read by</th></tr>
            </thead>
            <tbody>
              {h.terms.map((t) => (
                <tr key={t.uri}>
                  <td className="id">
                    {t.uri}
                    {t.fills && <span className="badge">fills {t.fills}</span>}
                  </td>
                  <td className="quiet">{pinText(t.module)}</td>
                  <td className="num">{t.held ?? "—"}</td>
                  <td>
                    {t.read_by.length === 0
                      ? <span className="quiet">nothing</span>
                      : t.read_by.map((r) => (
                        <span key={`${r.rule}${r.kind}`} className="pill">
                          {r.rule} <span className="quiet">{r.kind}, {r.reader}</span>
                        </span>
                      ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}

function DiagnosisBlock({ diagnosis: d }: { diagnosis: Diagnosis }) {
  const { title, why } = TITLES[d.code];
  const count = d.findings === null ? "not counted" : String(d.findings.length);
  const none = d.findings !== null && d.findings.length === 0;
  return (
    <section className={`diagnosis${none ? " diagnosis-none" : ""}`}>
      <h3>
        {title} <span className="diagnosis-count">{count}</span>
        <code className="quiet diagnosis-code">{d.code}</code>
      </h3>
      <p className="quiet diagnosis-why">{why}</p>
      {d.findings && d.findings.length > 0 && (
        <ul className="findings">
          {d.findings.map((f, i) => <li key={i}><FindingLine code={d.code} f={f} /></li>)}
        </ul>
      )}
    </section>
  );
}

function FindingLine({ code, f }: { code: DiagnosisCode; f: Finding }) {
  const module = typeof f.module === "object" && f.module ? pinText(f.module) : f.module;
  return (
    <>
      <span>{f.sentence}.</span>
      {code === "dead_term" && (
        <span className="quiet finding-detail">
          {" "}On {(f.on ?? []).join(", ") || "—"}, declared by {module}.
        </span>
      )}
      {code === "empty_class" && (f.read_by ?? []).length > 0 && (
        <span className="quiet finding-detail"> Read by {(f.read_by ?? []).join(", ")}.</span>
      )}
      {code === "unfilled_role" && (
        <span className="quiet finding-detail">
          {" "}{(f.bindings ?? []).length > 0 && <>Obliges {(f.bindings ?? []).join(", ")}. </>}
          {(f.candidates ?? []).length > 0 && <>Classes here that could fill it: {(f.candidates ?? []).join(", ")}.</>}
        </span>
      )}
      {code === "lagging_pin" && (
        <span className="quiet finding-detail">
          {" "}Newer: {(f.newer ?? []).join(", ")}. Pinned by {(f.pinned_by ?? []).map(pinText).join(", ")}.
        </span>
      )}
      {code === "orphaned_fact" && (f.declared_by ?? []).length > 0 && (
        <span className="quiet finding-detail">
          {" "}Declared in {(f.declared_by ?? []).map((d) => `${d.name} ${d.versions.join(", ")}`).join("; ")}.
        </span>
      )}
    </>
  );
}

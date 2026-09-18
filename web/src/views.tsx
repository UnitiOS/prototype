// The lists on the left and the detail on the right. Every view reads at the
// clocks in the URL; nothing here decides which statement stands — the API
// says so, and these views only show it.

import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { Assertion, Clocks, Entity, EntityRow, IntentDetail, IntentRow } from "./api";
import { STATUS, day, instant, name, shortId } from "./format";

export type Open = (tab: "entities" | "actions", id: string) => void;

function useLoad<T>(load: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({ loading: true });
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true }));
    load()
      .then((data) => live && setState({ data, loading: false }))
      .catch((e) => live && setState({
        error: e instanceof ApiError ? e.message : "Something failed while reading the API.",
        loading: false,
      }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

function Failure({ message }: { message: string }) {
  return <p className="failure" role="alert">{message}</p>;
}

function StatusMark({ status }: { status: Assertion["status"] }) {
  return (
    <span className={`status status-${status}`} title={STATUS[status].meaning}>
      {STATUS[status].label}
    </span>
  );
}

function Value({ row, open }: { row: Assertion; open: Open }) {
  if (row.ref) {
    return (
      <button className="link id" onClick={() => open("entities", row.ref!.id)}>
        {name(row.ref)}
      </button>
    );
  }
  if (row.value === null) return <span className="quiet">no value</span>;
  return <span className="value">{row.value}</span>;
}

function Clockstamp({ row }: { row: Assertion }) {
  return (
    <>
      <td className="num" title={instant(row.valid_from)}>{day(row.valid_from)}</td>
      <td className="num" title={instant(row.recorded_at)}>{day(row.recorded_at)}</td>
    </>
  );
}

// ---------------------------------------------------------------- entities

export function EntityList({ selected, open }: { selected: string | null; open: Open }) {
  const [search, setSearch] = useState("");
  const { data, error } = useLoad(() => api.entities(search), [search]);
  return (
    <div className="list">
      <label className="search">
        <span className="visually-hidden">Find an entity</span>
        <input
          type="search"
          placeholder="Find by URI or id"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      {error && <Failure message={error} />}
      {data && data.length === 0 && (
        <p className="empty">
          {search ? "No entity matches that." : "The log holds no entities yet. Seal a map or seed the log to see some."}
        </p>
      )}
      <ul>
        {data?.map((e: EntityRow) => (
          <li key={e.id}>
            <button
              className={`row${selected === e.id ? " row-selected" : ""}`}
              aria-current={selected === e.id}
              onClick={() => open("entities", e.id)}
            >
              <span className="id">{e.uri ?? shortId(e.id)}</span>
              <span className="count">{e.assertions}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function EntityView({ id, clocks, open }: { id: string; clocks: Clocks; open: Open }) {
  const { data, error } = useLoad(() => api.entity(id, clocks), [id, clocks.validAt.getTime(), clocks.asOf.getTime()]);
  if (error) return <Failure message={error} />;
  if (!data) return <p className="quiet">Reading…</p>;
  const entity: Entity = data;
  return (
    <article className="detail">
      <header className="detail-head">
        <h2 className="id">{entity.uri ?? shortId(entity.id)}</h2>
        <p className="quiet">
          Minted {instant(entity.minted_at)} by{" "}
          <button className="link" onClick={() => open("actions", entity.intent_id)}>
            one action
          </button>
          . Id <span className="id">{entity.id}</span>
        </p>
      </header>

      {entity.facts.length === 0 && <p className="empty">Nothing has been said about this entity.</p>}

      {entity.facts.map((fact) => {
        const standing = fact.rows.find((r) => r.id === fact.standing);
        return (
          <section key={fact.predicate.id} className="fact">
            <div className="fact-head">
              <h3 className="id">{name(fact.predicate)}</h3>
              <div className="fact-now">
                {standing ? <Value row={standing} open={open} /> : <span className="quiet">nothing stands</span>}
              </div>
            </div>
            <Rows rows={fact.rows} open={open} />
          </section>
        );
      })}

      {entity.referenced_by.length > 0 && (
        <section className="fact">
          <div className="fact-head">
            <h3>Pointed at by</h3>
          </div>
          <table>
            <thead>
              <tr><th>Subject</th><th>Predicate</th><th>Valid from</th><th>Recorded at</th><th>At these clocks</th></tr>
            </thead>
            <tbody>
              {entity.referenced_by.map((r) => (
                <tr key={r.id} className={`tr-${r.status}`}>
                  <td>
                    <button className="link id" onClick={() => open("entities", r.subject.id)}>{name(r.subject)}</button>
                  </td>
                  <td className="id">{name(r.predicate)}</td>
                  <Clockstamp row={r} />
                  <td><StatusMark status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </article>
  );
}

function Rows({ rows, open }: { rows: Assertion[]; open: Open }) {
  return (
    <table>
      <thead>
        <tr><th>Value</th><th>Valid from</th><th>Recorded at</th><th>At these clocks</th><th>Said by</th></tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className={`tr-${r.status}`}>
            <td><Value row={r} open={open} /></td>
            <Clockstamp row={r} />
            <td><StatusMark status={r.status} /></td>
            <td>
              <button className="link" onClick={() => open("actions", r.intent_id)}>{r.source.replace(/_/g, " ")}</button>
              {r.confidence && <span className="quiet">, {r.confidence} confidence</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------- actions

const PAGE = 50;

export function ActionList({ selected, open }: { selected: string | null; open: Open }) {
  const [offset, setOffset] = useState(0);
  const { data, error } = useLoad(() => api.intents(offset, PAGE), [offset]);
  return (
    <div className="list">
      {error && <Failure message={error} />}
      {data && data.total === 0 && <p className="empty">No action has been recorded yet.</p>}
      <ul>
        {data?.intents.map((i: IntentRow) => (
          <li key={i.id}>
            <button
              className={`row row-stacked${selected === i.id ? " row-selected" : ""}`}
              aria-current={selected === i.id}
              onClick={() => open("actions", i.id)}
            >
              <span>
                {i.action_name.replace(/_/g, " ")}
                {i.ontology_version && <span className="id under"> {i.ontology_version}</span>}
                {i.reason_code && <span className="badge badge-demo">{i.reason_code}</span>}
              </span>
              <span className="quiet">
                {day(i.occurred_at)}, {i.actor_id}, {i.assertions} {i.assertions === 1 ? "statement" : "statements"}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {data && <Pager offset={offset} total={data.total} onMove={setOffset} />}
    </div>
  );
}

export function ActionView({ id, clocks, open }: { id: string; clocks: Clocks; open: Open }) {
  const { data, error } = useLoad(() => api.intent(id, clocks), [id, clocks.validAt.getTime(), clocks.asOf.getTime()]);
  if (error) return <Failure message={error} />;
  if (!data) return <p className="quiet">Reading…</p>;
  const action: IntentDetail = data;
  return (
    <article className="detail">
      <header className="detail-head">
        <h2>{action.action_name.replace(/_/g, " ")}</h2>
        <p className="quiet">
          By {action.actor_id}
          {action.agent_id ? ` through ${action.agent_id}` : ""}, {instant(action.occurred_at)}.
          {action.reason_code ? ` Reason: ${action.reason_code}.` : ""}
        </p>
        {action.note && <p>{action.note}</p>}
      </header>
      {action.minted.length > 0 && (
        <section className="fact">
          <div className="fact-head"><h3>Entities it created</h3></div>
          <p className="chips">
            {action.minted.map((m) => (
              <button key={m.id} className="link id" onClick={() => open("entities", m.id)}>{name(m)}</button>
            ))}
          </p>
        </section>
      )}
      {action.assertions.length > 0 && (
        <section className="fact">
          <div className="fact-head"><h3>What it stated</h3></div>
          <LogTable rows={action.assertions} open={open} />
        </section>
      )}
    </article>
  );
}

// ---------------------------------------------------------------- log

export function LogView({ clocks, open }: { clocks: Clocks; open: Open }) {
  const [offset, setOffset] = useState(0);
  const { data, error } = useLoad(() => api.log(clocks, offset, 100), [offset, clocks.validAt.getTime(), clocks.asOf.getTime()]);
  if (error) return <Failure message={error} />;
  if (!data) return <p className="quiet">Reading…</p>;
  if (data.total === 0) return <p className="empty">The log is empty.</p>;
  return (
    <article className="detail">
      <LogTable rows={data.assertions} open={open} />
      <Pager offset={offset} total={data.total} size={100} onMove={setOffset} />
    </article>
  );
}

function LogTable({ rows, open }: { rows: Assertion[]; open: Open }) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th className="num">Seq</th><th>Subject</th><th>Predicate</th><th>Value</th>
            <th>Valid from</th><th>Recorded at</th><th>At these clocks</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className={`tr-${r.status}`}>
              <td className="num">{r.seq}</td>
              <td><button className="link id" onClick={() => open("entities", r.subject.id)}>{name(r.subject)}</button></td>
              <td className="id">{name(r.predicate)}</td>
              <td><Value row={r} open={open} /></td>
              <Clockstamp row={r} />
              <td><StatusMark status={r.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Pager({ offset, total, size = PAGE, onMove }: { offset: number; total: number; size?: number; onMove: (n: number) => void }) {
  if (total <= size) return null;
  return (
    <nav className="pager" aria-label="Pages">
      <button disabled={offset === 0} onClick={() => onMove(Math.max(offset - size, 0))}>Newer</button>
      <span className="quiet">{offset + 1}–{Math.min(offset + size, total)} of {total}</span>
      <button disabled={offset + size >= total} onClick={() => onMove(offset + size)}>Older</button>
    </nav>
  );
}

import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { Clocks, Point, Summary } from "./api";
import { ClockPlane } from "./ClockPlane";
import { day, fromInput, toInput } from "./format";
import { useRoute } from "./route";
import { ModulesPage } from "./modules";
import { ApplicationPage } from "./application";
import type { Tab } from "./route";
import { ActionList, ActionView, EntityList, EntityView, LogView } from "./views";

const TABS: { tab: Tab; label: string }[] = [
  { tab: "entities", label: "Entities" },
  { tab: "actions", label: "Actions" },
  { tab: "log", label: "Log" },
];

const AREAS: { tab: Tab; label: string }[] = [
  { tab: "entities", label: "Kernel" },
  { tab: "modules", label: "Modules" },
  { tab: "app", label: "Application" },
];

export function App() {
  const [route, go] = useRoute();
  const { clocks } = route;
  const [summary, setSummary] = useState<Summary | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.summary().then(setSummary).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, []);

  useEffect(() => {
    api.plane(clocks).then((p) => setPoints(p.points)).catch(() => undefined);
  }, [clocks.validAt.getTime(), clocks.asOf.getTime()]);

  const setClocks = (next: Clocks) => go({ ...route, clocks: next }, true);
  const open = (tab: "entities" | "actions", id: string) => go({ ...route, tab, id });
  const inModules = route.tab === "modules";
  const inApp = route.tab === "app";
  // The clocks are what a projection is read at, so they belong to both the
  // kernel explorer and the application. Only the module store is timeless.
  const inKernel = !inModules && !inApp;

  const now = () => {
    const t = new Date();
    setClocks({ validAt: t, asOf: t });
  };

  return (
    <div className="app">
      <header className="top">
        <h1 className="brand">Uniti</h1>
        <nav className="areas" aria-label="Areas">
          {AREAS.map(({ tab, label }) => {
            const on = tab === "modules" ? inModules : tab === "app" ? inApp : inKernel;
            return (
              <button key={tab} className={`area${on ? " area-on" : ""}`} aria-current={on}
                onClick={() => go({ ...route, tab, id: null })}>
                {label}
              </button>
            );
          })}
        </nav>
        {summary && inKernel && (
          <p className="held">
            {summary.assertions} statements from {summary.intents} actions about {summary.entities} entities
            {summary.first_recorded_at && summary.last_recorded_at && (
              <>, recorded {day(summary.first_recorded_at)} to {day(summary.last_recorded_at)}</>
            )}
          </p>
        )}
      </header>

      {error && <p className="failure" role="alert">{error}</p>}

      {inModules && (
        <ModulesPage pick={route.module} onPick={(module) => go({ ...route, module })} />
      )}

      {!inModules && <>
      <section className="clocks" aria-label="Clocks">
        <div className="clock-fields">
          <label className="clock">
            <span>Valid at</span>
            <input
              type="datetime-local"
              value={toInput(clocks.validAt)}
              onChange={(e) => {
                const d = fromInput(e.target.value);
                if (d) setClocks({ ...clocks, validAt: d });
              }}
            />
            <small>how the world stood at this moment</small>
          </label>
          <label className="clock">
            <span>As of</span>
            <input
              type="datetime-local"
              value={toInput(clocks.asOf)}
              onChange={(e) => {
                const d = fromInput(e.target.value);
                if (d) setClocks({ ...clocks, asOf: d });
              }}
            />
            <small>according to what the log knew by then</small>
          </label>
          <button className="button" onClick={now}>Set both to now</button>
          <p className="hint">Times are UTC. Press or drag on the plane to move both clocks.</p>
        </div>
        <ClockPlane
          points={points}
          clocks={clocks}
          highlight={route.tab === "entities" ? route.id : null}
          onChange={setClocks}
        />
      </section>

      {inApp && (
        <ApplicationPage pick={route.app} clocks={clocks}
          onPick={(app) => go({ ...route, app })} />
      )}

      {inKernel && <>
      <nav className="tabs" aria-label="Views">
        {TABS.map(({ tab, label }) => (
          <button
            key={tab}
            className={`tab${route.tab === tab ? " tab-on" : ""}`}
            aria-current={route.tab === tab}
            onClick={() => go({ ...route, tab, id: null })}
          >
            {label}
          </button>
        ))}
      </nav>

      <main className={route.tab === "log" ? "body body-wide" : "body"}>
        {route.tab === "entities" && (
          <>
            <EntityList selected={route.id} open={open} />
            {route.id
              ? <EntityView id={route.id} clocks={clocks} open={open} />
              : <p className="empty">Pick an entity to see everything the log says about it, read at these clocks.</p>}
          </>
        )}
        {route.tab === "actions" && (
          <>
            <ActionList selected={route.id} open={open} />
            {route.id
              ? <ActionView id={route.id} clocks={clocks} open={open} />
              : <p className="empty">Pick an action to see who took it and what it wrote.</p>}
          </>
        )}
        {route.tab === "log" && <LogView clocks={clocks} open={open} />}
      </main>
      </>}
      </>}
    </div>
  );
}

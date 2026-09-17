// The whole view lives in the URL hash: which list, which item, which clocks.
// A link to a view is therefore a link to exactly what was on screen.

import { useEffect, useState } from "react";
import type { Clocks } from "./api";

export type Tab = "entities" | "actions" | "log";

export interface Route { tab: Tab; id: string | null; clocks: Clocks }

function parse(hash: string): Route {
  const [path, query = ""] = hash.replace(/^#\/?/, "").split("?");
  const [first, id] = path.split("/");
  const tab: Tab = first === "actions" || first === "log" ? first : "entities";
  const params = new URLSearchParams(query);
  const read = (name: string) => {
    const raw = params.get(name);
    const moment = raw ? new Date(raw) : new Date();
    return Number.isNaN(moment.getTime()) ? new Date() : moment;
  };
  return { tab, id: id || null, clocks: { validAt: read("valid_at"), asOf: read("as_of") } };
}

export function href(route: Route): string {
  const path = route.id ? `${route.tab}/${route.id}` : route.tab;
  const query = new URLSearchParams({
    valid_at: route.clocks.validAt.toISOString(),
    as_of: route.clocks.asOf.toISOString(),
  });
  return `#/${path}?${query}`;
}

export function useRoute(): [Route, (next: Route, replace?: boolean) => void] {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const onHash = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const go = (next: Route, replace = false) => {
    const target = href(next);
    if (replace) window.history.replaceState(null, "", target);
    else window.history.pushState(null, "", target);
    setRoute(next);
  };
  return [route, go];
}

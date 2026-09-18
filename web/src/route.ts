// The whole view lives in the URL hash: which area, which item, which clocks.
// A link to a view is therefore a link to exactly what was on screen.
//
//   #/entities/<id>?valid_at=..&as_of=..         the kernel
//   #/modules?name=@x/y&version=v2&compare=v1     the module store
//   #/app?name=@x/y&version=v1&class=Thing&column=c&keys=a,b   one cell of it

import { useEffect, useState } from "react";
import type { Clocks } from "./api";

export type Tab = "entities" | "actions" | "log" | "modules" | "app";

export interface ModulePick { name: string | null; version: string | null; compare: string | null }

export interface AppPick {
  name: string | null; version: string | null; klass: string | null;
  // Which cell is open, if any: a column, and the grouping values of its row
  // in key-column order. A link to a number is a link to its explanation.
  column: string | null; keys: string | null;
  // Whether the form for stating a new one is open. In the URL because every
  // other part of the view is, so a link can hand somebody the form itself.
  stating: boolean;
}

export interface Route {
  tab: Tab; id: string | null; clocks: Clocks; module: ModulePick; app: AppPick;
}

function parse(hash: string): Route {
  const [path, query = ""] = hash.replace(/^#\/?/, "").split("?");
  const [first, id] = path.split("/");
  const tab: Tab = first === "actions" || first === "log" || first === "modules" || first === "app"
    ? first : "entities";
  const params = new URLSearchParams(query);
  const read = (name: string) => {
    const raw = params.get(name);
    const moment = raw ? new Date(raw) : new Date();
    return Number.isNaN(moment.getTime()) ? new Date() : moment;
  };
  return {
    tab,
    id: tab === "modules" || tab === "app" ? null : id || null,
    clocks: { validAt: read("valid_at"), asOf: read("as_of") },
    module: { name: params.get("name"), version: params.get("version"), compare: params.get("compare") },
    app: {
      name: params.get("name"), version: params.get("version"),
      klass: params.get("class"), column: params.get("column"),
      keys: params.get("keys"), stating: params.get("new") === "1",
    },
  };
}

export function href(route: Route): string {
  const path = route.id ? `${route.tab}/${route.id}` : route.tab;
  const query = new URLSearchParams();
  if (route.tab === "modules") {
    const { name, version, compare } = route.module;
    if (name) query.set("name", name);
    if (version) query.set("version", version);
    if (compare) query.set("compare", compare);
  }
  if (route.tab === "app") {
    const { name, version, klass, column, keys, stating } = route.app;
    if (name) query.set("name", name);
    if (version) query.set("version", version);
    if (klass) query.set("class", klass);
    if (column) query.set("column", column);
    if (keys) query.set("keys", keys);
    if (stating) query.set("new", "1");
  }
  query.set("valid_at", route.clocks.validAt.toISOString());
  query.set("as_of", route.clocks.asOf.toISOString());
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

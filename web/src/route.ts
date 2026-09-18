// The whole view lives in the URL hash: which area, which item, which clocks.
// A link to a view is therefore a link to exactly what was on screen.
//
//   #/entities/<id>?valid_at=..&as_of=..         the kernel
//   #/modules?name=@x/y&version=v2&compare=v1     the module store
//   #/app?name=@x/y&version=v1&class=Thing        one application's tables

import { useEffect, useState } from "react";
import type { Clocks } from "./api";

export type Tab = "entities" | "actions" | "log" | "modules" | "app";

export interface ModulePick { name: string | null; version: string | null; compare: string | null }

export interface AppPick { name: string | null; version: string | null; klass: string | null }

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
    app: { name: params.get("name"), version: params.get("version"), klass: params.get("class") },
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
    const { name, version, klass } = route.app;
    if (name) query.set("name", name);
    if (version) query.set("version", version);
    if (klass) query.set("class", klass);
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

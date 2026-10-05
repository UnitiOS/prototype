import { describe, expect, it } from "vitest";
import type { ModuleGraph } from "./api";
import { applications } from "./application";

const node = (name: string, version: string, kind: "module" | "application",
              business: string | null, latest = true) =>
  ({ name, version, latest, purpose: null, sealed_at: "2026-10-01", kind, business });

const graph: ModuleGraph = {
  nodes: [
    node("@shared/rental", "v1", "module", null),
    node("@kemahceria/rental", "v1", "application", "kemahceria", false),
    node("@kemahceria/rental", "v2", "application", "kemahceria"),
    node("@kemahceria/books", "v1", "application", "kemahceria"),
    node("@another/shop", "v1", "application", "another"),
  ],
  edges: [
    { from: { name: "@kemahceria/rental", version: "v2" },
      to: { name: "@shared/rental", version: "v1" }, kind: "imports" },
    { from: { name: "@another/shop", version: "v1" },
      to: { name: "@shared/rental", version: "v1" }, kind: "imports" },
  ],
};

describe("the applications a business is offered", () => {
  it("puts the version in use first, then its own others, and never another business's", () => {
    const offered = applications(graph, {
      business: "kemahceria",
      installed: [{ name: "@kemahceria/rental", version: "v1", since: "2026-10-08",
                    assertion: "a" }],
    });
    expect(offered).toEqual([
      { name: "@kemahceria/rental", version: "v1" },
      { name: "@kemahceria/books", version: "v1" },
    ]);
  });

  it("falls back on the roots of the graph when it has no application of its own", () => {
    const offered = applications(graph, { business: null, installed: [] });
    expect(offered.map((p) => p.name)).toEqual(["@kemahceria/rental", "@another/shop"]);
  });
});

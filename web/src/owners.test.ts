import { describe, expect, it } from "vitest";
import { ownersSaid } from "./agent";

const owner = (name: string) => ({ owner: name, since: "2026-10-06", assertion: name });

describe("who may freeze under a draft's name", () => {
  it("says nothing without a log to ask", () => {
    expect(ownersSaid(undefined)).toBeNull();
  });

  it("names the owners, or says the first to freeze takes the name", () => {
    expect(ownersSaid({ name: "@budi", owned: false, owners: [] }))
      .toBe("Nobody owns @budi yet: whoever freezes it first becomes its owner.");
    expect(ownersSaid({ name: "@budi", owned: true, owners: [owner("budi")] }))
      .toBe("Only an owner of @budi freezes under it: budi.");
    expect(ownersSaid({ name: "@budi", owned: true,
                        owners: [owner("ani"), owner("budi"), owner("sari")] }))
      .toBe("Only an owner of @budi freezes under it: ani, budi and sari.");
  });
});

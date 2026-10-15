import { describe, expect, it } from "vitest";
import type { Application, Business, Update } from "./api";
import {
  MACHINERY, blockedSaid, changeSaid, choiceLabel, columnMark, columnName, examplesSaid,
  inUseSaid, lensGroups, moveSteps, STAYS,
} from "./lens";

const pin = (name: string, version = "v1") => ({ name, version });
const mod = (name: string, title: string, kind: "core" | "library" | "module" | "application") =>
  ({ ...pin(name), purpose: null, title, kind });

const app: Application = {
  name: "@kemahceria/toko", version: "v1", title: "Kemah Ceria", kind: "application",
  business: "kemahceria", purpose: null, description: null,
  modules: [
    mod("@uniti/item", "Item", "library"),
    mod("@rudi/penyewaan", "Penyewaan alat kemah", "module"),
    mod("@sewapro/kasir", "Kasir SewaPro", "module"),
    mod("@kemahceria/toko", "Kemah Ceria", "application"),
  ],
  tables: [
    { class: "Item", table: "p_item", shape: "entities", lens: "thing",
      module: pin("@uniti/item", "v2"), module_title: "Item", columns: 3 },
    { class: "rudi_penyewaan__Rental", table: "p_rudi_penyewaan__rental", shape: "entities",
      lens: "event", module: pin("@rudi/penyewaan"), module_title: "Penyewaan alat kemah",
      columns: 5 },
    { class: "sewapro_kasir__Rental", table: "p_sewapro_kasir__rental", shape: "entities",
      lens: "event", module: pin("@sewapro/kasir"), module_title: "Kasir SewaPro", columns: 5 },
    { class: "DepositTaken", table: "p_deposit_taken", shape: "grouped", lens: "number",
      module: pin("@kemahceria/toko"), module_title: "Kemah Ceria", columns: 2 },
  ],
};

const update: Update = {
  module: "@rudi/penyewaan", title: "Penyewaan alat kemah", pinned: "v1", latest: "v2",
  changes: [
    { change: "added", what: "field", name: "rental_note", on: "Rental",
      description: "Anything worth knowing about the rental." },
    { change: "renamed", what: "field", name: "rental_units", was: "rental_qty", on: "Rental",
      description: "" },
    { change: "changed", what: "field", name: "rental_deposit", on: "Rental",
      fields: ["description"], description: "" },
    { change: "added", what: "thing", name: "ReturnNote", on: null, description: "" },
  ],
  examples: [{ name: "budi", says: "Budi rents twice.", passed: true, pending: false,
               refusals: [] }],
  refusal: null,
};

describe("the business lens", () => {
  it("reads the tables as things, events and numbers, in the owner's words", () => {
    const groups = lensGroups(app);
    expect(groups.map((g) => g.heading)).toEqual(["Things", "Events", "Numbers"]);
    const events = groups[1].items;
    // Two kinds called "Rental", told apart by whose module they came from.
    expect(events.map((i) => [i.name, i.mark])).toEqual([
      ["Rental", "Penyewaan alat kemah"], ["Rental", "Kasir SewaPro"]]);
    // The library and the application's own carry no mark.
    expect(groups[0].items[0]).toMatchObject({ name: "Item", mark: null });
    expect(groups[2].items[0]).toMatchObject({ name: "Deposit taken", mark: null });
  });

  it("calls a column by its field's words, and marks a field another module adds", () => {
    expect(columnName("Item", { name: "rudi_penyewaan__rental_rate",
      title: "rudi_penyewaan__rental_rate", kind: "stated" })).toBe("Rental rate");
    expect(columnName("Item", { name: "entity_uri", title: "entity_uri", kind: "identity" }))
      .toBe("Code");
    expect(columnMark(app, pin("@uniti/item", "v2"),
      { module: pin("@rudi/penyewaan"), module_title: "Penyewaan alat kemah" }))
      .toBe("Penyewaan alat kemah");
    expect(columnMark(app, pin("@uniti/item", "v2"),
      { module: pin("@uniti/item", "v2"), module_title: "Item" })).toBeNull();
  });

  it("says whose kind a choice is when it is not the field's own", () => {
    expect(choiceLabel({ label: "Rental — Budi, 2026-10-06", from: "Kasir SewaPro" }))
      .toBe("Rental — Budi, 2026-10-06 (Kasir SewaPro)");
    expect(choiceLabel({ label: "Budi" })).toBe("Budi");
  });

  it("says what changes in a new version as fields and things", () => {
    expect(update.changes.map(changeSaid)).toEqual([
      "Rental gains a field: Note",
      "Rental: Qty is now called Units; what was recorded under it stays",
      "Rental: Deposit is described differently",
      "Something new is kept: Return note",
    ]);
    expect(examplesSaid(update)).toBe("The example holds on v2.");
    const differs = { ...update, examples: [
      ...update.examples, { name: "ani", says: "", passed: false, pending: false, refusals: [] }] };
    expect(examplesSaid(differs)).toBe("1 of 2 examples come out differently on v2. "
      + "Read it before moving.");
  });

  it("moves one version by three ordinary Studio steps", () => {
    expect(moveSteps(update)).toEqual([
      { step: "revise", args: {} },
      { step: "unpin", args: { module: "@rudi/penyewaan@v1" } },
      { step: "pin", args: { module: "@rudi/penyewaan@v2" } },
    ]);
    // A draft already open: only what is left, and nothing when it is done.
    expect(moveSteps(update, [pin("@rudi/penyewaan", "v1"), pin("@dewi/jaminan")])).toEqual([
      { step: "unpin", args: { module: "@rudi/penyewaan@v1" } },
      { step: "pin", args: { module: "@rudi/penyewaan@v2" } },
    ]);
    expect(moveSteps(update, [pin("@rudi/penyewaan", "v2")])).toEqual([]);
  });

  it("never uses a word of the machinery", () => {
    const business: Business = { business: "kemahceria", installed: [] };
    const blocked = { ...update, refusal: { code: "two_versions_of_a_module" } as never };
    const said = [
      ...lensGroups(app).flatMap((g) => [g.heading, g.says, ...g.items.map((i) => i.name)]),
      ...update.changes.map(changeSaid),
      examplesSaid(update), examplesSaid({ ...update, examples: [] }), examplesSaid(blocked),
      blockedSaid(blocked) ?? "", STAYS,
      inUseSaid(app, business, "8 Oct", (d) => d).line,
      inUseSaid({ ...app, kind: "module" }, business, "8 Oct", (d) => d).line,
      inUseSaid(app, { business: "kemahceria", installed: [
        { name: app.name, version: "v1", since: "2026-10-05", assertion: "a" }] },
        "8 Oct", (d) => d).line,
    ];
    for (const line of said) expect(line, line).not.toMatch(MACHINERY);
  });
});

describe("the machinery's words", () => {
  it("catches a composed name and the words a business owner is not shown", () => {
    for (const line of ["rudi_sewa__Rental", "a sealed version", "the module", "SQL",
                        "under one intent", "pin it"]) {
      expect(line).toMatch(MACHINERY);
    }
    expect("Penyewaan alat kemah, in use since 5 Oct").not.toMatch(MACHINERY);
  });
});


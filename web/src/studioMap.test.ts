import { describe, expect, it } from "vitest";
import type { DraftState, ExampleResult } from "./api";
import {
  BOX, CELL, GROUP, arrange, arrangeWorkings, cellHeight, changedOf, checksOf, fieldLabel, heightOf,
  askedOnce, blocksOf, exampleOf, lineage, mapOf, marksOf, momentsOf, neighbours, piecesOf, roomFor,
  nameShown, plainName, spoken, tagOf, turnsAbout, untagged, walkThrough,
  workingsOf, NOT_YET,
} from "./studioMap";

/** A draft shaped like the demo stock module: one kind of its own that points
 *  at three it builds on, with each kind of worked-out field. */
function draft(): DraftState {
  const slot = (name: string, over: Partial<DraftState["slots"][number]> = {}) => ({
    name, title: "", description: "", slot_uri: null, range: "string",
    identifier: false, designates_type: false, binds: null, rule: null, on: [], ...over,
  });
  return {
    name: "@demo/stock", title: "Stock", description: null, purpose: null, valid_from: null,
    versions: ["v1"], revises: "v1", becomes: "v2",
    pins: [{ name: "@demo/catalog", version: "v3" }],
    sees: { classes: 4, slots: 10 },
    classes: [{
      name: "IngredientStock", description: "One row per ingredient.", fills: [], is_a: null,
      slots: ["stock_ingredient", "quantity_on_hand", "reorder_level", "headroom"], has_rows: true,
    }],
    slots: [
      slot("stock_ingredient", { title: "Ingredient", range: "Ingredient" }),
      slot("quantity_on_hand", {
        title: "On hand", range: "decimal",
        rule: { kind: "aggregate", spec: { over: "Flow", sum: "amount" } },
      }),
      slot("reorder_level", {
        title: "Reorder level", range: "decimal",
        rule: { kind: "parameter", spec: { of: "stock_ingredient", slot: "ingredient_reorder_level" } },
      }),
      slot("headroom", {
        title: "headroom", range: "decimal",
        rule: { kind: "expression", spec: "{quantity_on_hand} - {reorder_level}" },
      }),
    ],
    roles: [],
    borrowed: [
      {
        name: "Ingredient", description: "", fills: ["Resource"],
        module: { name: "@demo/catalog", version: "v3" },
        slots: [
          { name: "ingredient_code", range: "string", identifier: true },
          { name: "ingredient_category", range: "Category", identifier: false },
          { name: "ingredient_supplier", range: "Supplier", identifier: false },
        ],
      },
      {
        name: "Category", description: "", fills: [], module: { name: "@demo/catalog", version: "v3" },
        slots: [{ name: "category_code", range: "string", identifier: true }],
      },
      {
        name: "Supplier", description: "", fills: [], module: { name: "@demo/catalog", version: "v3" },
        slots: [{ name: "supplier_code", range: "string", identifier: true }],
      },
    ],
    read_from: [{
      name: "Movement", description: "", fills: ["Flow"],
      module: { name: "@rival/stock-moves", version: "v1" },
      slots: [
        { name: "move_ref", range: "string", identifier: true },
        { name: "qty_delta", range: "decimal", identifier: false },
        { name: "item", range: "Ingredient", identifier: false },
      ],
    }],
    workings: [{
      class: "IngredientStock", keys: ["stock_ingredient"],
      columns: [
        { name: "quantity_on_hand", kind: "aggregate", operator: "sum",
          reads: [{ class: "Movement", fields: ["qty_delta"], by: { stock_ingredient: "item" } }] },
        { name: "reorder_level", kind: "parameter", of: "stock_ingredient",
          reads: [{ class: "Ingredient", fields: ["ingredient_reorder_level"], by: {} }] },
        { name: "headroom", kind: "expression", reads: [] },
      ],
    }],
    tables: [], refusals: [], blocking: 0,
    holes: [{ kind: "nothing_said_about_it", where: "headroom", question: "", because: "", blocking: false, step: null }],
    steps: [], taken: "", diff: {} as DraftState["diff"], sealable: true, document: "",
    examples: [flour()], examples_run: true,
  } as unknown as DraftState;
}

/** Flour in twice and out once; its reorder level raised on 1 July. The last
 *  headroom is expected wrong on purpose, to see a failing check. */
function flour(): ExampleResult {
  const check = (at: string, column: string, expected: string, got = expected) => ({
    table: "IngredientStock", row: "flour", at, column, expected, got, holds: expected === got,
  });
  const move = (record: string, when: string, qty: number) => ({
    record, class: "Movement", when, facts: { move_ref: record, item: "flour", qty_delta: qty },
  });
  return {
    name: "flour_in_and_out", says: "Flour in and out.", agreed: true, records: 6, expected: 2,
    checks: [
      check("2026-06-30", "quantity_on_hand", "36"), check("2026-06-30", "reorder_level", "20"),
      check("2026-06-30", "headroom", "16"),
      check("2026-07-05", "quantity_on_hand", "36"), check("2026-07-05", "reorder_level", "30"),
      check("2026-07-05", "headroom", "6", "16"),
    ],
    tables: [], refusals: [], passed: false,
    recorded: [
      { record: "flour", class: "Ingredient", when: null,
        facts: { ingredient_code: "FLR", ingredient_reorder_level: 20 } },
      move("flour_in_1", "2026-06-02", 25), move("flour_in_2", "2026-06-16", 25),
      move("flour_used", "2026-06-20", -14),
      { record: "salt_in", class: "Movement", when: "2026-06-03", facts: { item: "salt", qty_delta: 5 } },
      { record: "flour", class: null, when: "2026-07-01", facts: { ingredient_reorder_level: 30 } },
    ],
  };
}

describe("names said as words", () => {
  it("reads snake case and camel case alike", () => {
    expect(spoken("quantity_on_hand")).toBe("Quantity on hand");
    expect(spoken("IngredientStock")).toBe("Ingredient stock");
    expect(spoken("SKU_code")).toBe("SKU code");
    expect(spoken("HTTPServer")).toBe("HTTP server");
    expect(spoken("flow")).toBe("Flow");
  });

  it("drops a kind's own name from the front of its fields", () => {
    expect(fieldLabel("ingredient_code", "Ingredient")).toBe("Code");
    expect(fieldLabel("ingredient_reorder_level", "Ingredient")).toBe("Reorder level");
    expect(fieldLabel("stock_ingredient", "IngredientStock")).toBe("Stock ingredient");
    expect(fieldLabel("ingredient", "Ingredient")).toBe("Ingredient");
  });

  it("says a pinned module's name as its module wrote it, and keeps the tag apart", () => {
    expect(plainName("penyewaan__Rental")).toBe("Rental");
    expect(plainName("Rental")).toBe("Rental");
    expect(tagOf("penyewaan__Rental")).toBe("penyewaan");
    expect(tagOf("Rental")).toBeNull();
    expect(nameShown("kasir__Rental")).toBe("Rental · kasir");
    expect(nameShown("Party")).toBe("Party");
    expect(untagged("{rudi_sewa__rental_rate} * {days}")).toBe("{rental_rate} * {days}");
    expect(untagged("rudi_sewa__Rental.rudi_sewa__rental_deposit")).toBe("Rental.rental_deposit");
    expect(spoken("penyewaan__RentalLine")).toBe("Rental line");
    expect(fieldLabel("penyewaan__rental_deposit", "penyewaan__Rental")).toBe("Deposit");
  });

  it("prefers the title its author wrote", () => {
    expect(fieldLabel("quantity_on_hand", "IngredientStock", "On hand")).toBe("On hand");
    expect(fieldLabel("headroom", "IngredientStock", "headroom")).toBe("Headroom");
    expect(fieldLabel("headroom", "IngredientStock", "  ")).toBe("Headroom");
  });
});

describe("the map of a draft", () => {
  const drawn = mapOf(draft());
  const node = (name: string) => drawn.nodes.find((n) => n.name === name)!;

  it("draws what the module declares and what it builds on", () => {
    expect(drawn.nodes.map((n) => [n.name, n.own, n.read])).toEqual([
      ["IngredientStock", true, false], ["Ingredient", false, false], ["Category", false, false],
      ["Supplier", false, false], ["Movement", false, true],
    ]);
    expect(node("Ingredient").module).toBe("@demo/catalog@v3");
    expect(node("IngredientStock").label).toBe("Ingredient stock");
  });

  it("says how each worked-out field comes to be", () => {
    const marks = Object.fromEntries(node("IngredientStock").fields.map((f) => [f.label, f.mark?.kind ?? null]));
    expect(marks).toEqual({
      Ingredient: null, "On hand": "sum", "Reorder level": "lookup", Headroom: "formula",
    });
    expect(node("Ingredient").fields[0]).toMatchObject({ label: "Code", mark: { kind: "key" } });
    expect(node("IngredientStock").fields[3].asks).toBe(true);
  });

  it("draws a line for every field pointing at a kind in sight, named only when the name adds something", () => {
    expect(drawn.edges.map((e) => [e.from, e.to, e.label, e.own, e.kind])).toEqual([
      ["IngredientStock", "Ingredient", null, true, "points"],
      ["Ingredient", "Category", null, false, "points"],
      ["Ingredient", "Supplier", null, false, "points"],
      ["Movement", "Ingredient", "Item", false, "points"],
      // The sum reads Movement, which nothing points at; the lookup reads
      // Ingredient, which a field already joins, so it gets no second line.
      ["IngredientStock", "Movement", "adds up", true, "reads"],
    ]);
    expect(node("IngredientStock").fields[0]).toMatchObject({ points: "Ingredient", holds: "Ingredient" });
  });

  it("draws a field this module adds to another module's kind on that kind, as its own", () => {
    const d = draft();
    d.slots.push({ ...d.slots[0], name: "ingredient_shelf_life", title: "Shelf life",
                   range: "integer", unit: "day", on: [], adds_to: "Ingredient" });
    d.borrowed[0].slots.push({ name: "ingredient_shelf_life", range: "integer", identifier: false });
    const shelf = mapOf(d).nodes.find((n) => n.name === "Ingredient")!.fields.slice(-1)[0];
    expect(shelf).toMatchObject({
      label: "Shelf life", holds: "whole number, in day", mark: { kind: "adds", text: "added here" },
    });
  });

  it("knows what a box is joined to", () => {
    expect([...neighbours(drawn.edges, "Ingredient")].sort())
      .toEqual(["Category", "Ingredient", "IngredientStock", "Movement", "Supplier"]);
  });
});

describe("the person's own words", () => {
  /** The same draft, with the words its people used kept beside the English. */
  function labelled(): DraftState {
    const d = draft();
    d.classes[0].labels = { id: "Stok bahan" };
    d.slots[1] = { ...d.slots[1], labels: { id: "Stok tersedia" }, unit: "kg", direction: "level" };
    d.borrowed[0].labels = { id: "Bahan" };
    return d;
  }

  it("draws a kind and a field in the person's language where the module keeps it", () => {
    const { nodes } = mapOf(labelled(), "id");
    const own = nodes.find((n) => n.name === "IngredientStock")!;
    expect(own.label).toBe("Stok bahan");
    expect(own.fields.find((f) => f.name === "quantity_on_hand")!.label).toBe("Stok tersedia");
    // A field pointing at a kind says the kind in the same words.
    expect(own.fields.find((f) => f.name === "stock_ingredient")!.holds).toBe("Bahan");
    // Where nobody kept a word, the name is said as words, as before.
    expect(own.fields.find((f) => f.name === "headroom")!.label).toBe("Headroom");
  });

  it("says the English where the person reads another language", () => {
    const own = mapOf(labelled(), "en").nodes.find((n) => n.name === "IngredientStock")!;
    expect(own.label).toBe("Ingredient stock");
  });

  it("says a number's unit beside what it holds", () => {
    const own = mapOf(labelled(), "en").nodes.find((n) => n.name === "IngredientStock")!;
    expect(own.fields.find((f) => f.name === "quantity_on_hand")!.holds).toBe("number, in kg");
  });
});

describe("where the boxes go", () => {
  const { nodes, edges } = mapOf(draft());
  const none = new Set<string>();

  it("puts what a kind points at above it, the same way every time", () => {
    const at = arrange(nodes, edges, none);
    expect(arrange(nodes, edges, none)).toEqual(at);
    expect(at.Ingredient.y).toBeLessThan(at.IngredientStock.y);
    expect(at.Category.y).toBeLessThan(at.Ingredient.y);
  });

  it("never lays one box over another", () => {
    const at = arrange(nodes, edges, none);
    for (const a of nodes) {
      for (const b of nodes) {
        if (a.name >= b.name) continue;
        const apart = at[a.name].x + BOX.width <= at[b.name].x
          || at[b.name].x + BOX.width <= at[a.name].x
          || at[a.name].y + heightOf(a, false) <= at[b.name].y
          || at[b.name].y + heightOf(b, false) <= at[a.name].y;
        expect(apart, `${a.name} and ${b.name}`).toBe(true);
      }
    }
  });

  it("leaves a box somebody moved where they put it", () => {
    const at = arrange(nodes, edges, none, { Supplier: { x: 900, y: -40 } });
    expect(at.Supplier).toEqual({ x: 900, y: -40 });
  });

  it("makes room for a box opened to show every field", () => {
    const many = { ...nodes[0], fields: Array.from({ length: 12 }, (_, i) => ({ ...nodes[0].fields[0], name: `f${i}` })) };
    expect(heightOf(many, true)).toBeGreaterThan(heightOf(many, false));
  });
});

describe("whether the numbers are checked", () => {
  it("says of every worked-out field what the examples make of it", () => {
    const said = Object.fromEntries([...checksOf(draft())].map(([k, c]) => [k, c.state]));
    expect(said).toEqual({
      "IngredientStock.quantity_on_hand": "checked",
      "IngredientStock.reorder_level": "checked",
      "IngredientStock.headroom": "failing",
    });
  });

  it("knows a field no example checks, and examples nobody ran", () => {
    const none = { ...draft(), examples: [] };
    expect(checksOf(none).get("IngredientStock.headroom")?.state).toBe("unchecked");
    const unrun = { ...draft(), examples_run: false,
      examples: [{ ...flour(), checks: [], passed: null }] };
    expect(checksOf(unrun).get("IngredientStock.headroom")?.state).toBe("unrun");
    const refused = { ...unrun, refusals: [{ code: "column_unchecked", where: "IngredientStock.headroom" }] };
    expect(checksOf(refused as unknown as DraftState).get("IngredientStock.headroom")?.state)
      .toBe("unchecked");
  });

  it("puts the check on the field on the map", () => {
    const field = mapOf(draft()).nodes[0].fields.find((f) => f.name === "headroom")!;
    expect(field.check?.state).toBe("failing");
  });
});

describe("how the numbers are worked out", () => {
  const w = workingsOf(draft());
  const cell = (id: string) => w.cells.find((c) => c.id === id)!;

  it("draws each worked-out field and what it is worked out from", () => {
    expect(w.groups.map((g) => [g.name, g.own])).toEqual([
      ["Ingredient", false], ["Movement", false], ["IngredientStock", true],
    ]);
    expect(Object.fromEntries(w.cells.map((c) => [c.id, c.role]))).toEqual({
      "IngredientStock.stock_ingredient": "key",
      "IngredientStock.quantity_on_hand": "sum",
      "Movement.qty_delta": "recorded",
      "Movement.item": "recorded",
      "IngredientStock.reorder_level": "lookup",
      "Ingredient.ingredient_reorder_level": "recorded",
      "IngredientStock.headroom": "formula",
    });
    expect(w.flows.map((f) => [f.from, f.to, f.kind])).toEqual([
      ["Movement.qty_delta", "IngredientStock.quantity_on_hand", "sum"],
      ["Movement.item", "IngredientStock.stock_ingredient", "row"],
      ["Ingredient.ingredient_reorder_level", "IngredientStock.reorder_level", "lookup"],
      ["IngredientStock.quantity_on_hand", "IngredientStock.headroom", "formula"],
      ["IngredientStock.reorder_level", "IngredientStock.headroom", "formula"],
    ]);
  });

  it("says each rule in words, with the names on the drawing", () => {
    expect(cell("IngredientStock.quantity_on_hand").how).toBe("Adds up the qty delta of every movement");
    expect(cell("IngredientStock.reorder_level").how).toBe("Looked up on the ingredient of the row");
    expect(cell("IngredientStock.headroom").formula).toBe("On hand − Reorder level");
    expect(cell("IngredientStock.stock_ingredient").how).toBe("One row for each ingredient");
    expect(cell("Ingredient.ingredient_reorder_level").label).toBe("Reorder level");
  });

  it("lights everything a number comes from and goes into, and nothing else", () => {
    expect([...lineage(w.flows, "IngredientStock.reorder_level")].sort()).toEqual([
      "Ingredient.ingredient_reorder_level", "IngredientStock.headroom", "IngredientStock.reorder_level",
    ]);
    expect([...lineage(w.flows, "IngredientStock.headroom")].sort()).toEqual([
      "Ingredient.ingredient_reorder_level", "IngredientStock.headroom",
      "IngredientStock.quantity_on_hand", "IngredientStock.reorder_level", "Movement.qty_delta",
    ]);
  });

  it("draws nothing for a draft that works nothing out", () => {
    expect(workingsOf({ ...draft(), workings: [] })).toEqual({ groups: [], cells: [], flows: [] });
  });

  it("says first of a field the compiler does not compute yet that it is not, and still draws what it reads", () => {
    const d = draft();
    const columns = d.workings![0].columns.map((c) =>
      c.name === "quantity_on_hand" ? { ...c, awaiting: true } : c);
    const waiting = workingsOf({ ...d, workings: [{ ...d.workings![0], columns }] });
    const held = waiting.cells.find((c) => c.id === "IngredientStock.quantity_on_hand")!;
    expect(held.how).toBe(NOT_YET);
    expect(held.role).toBe("sum");
    expect(waiting.flows.map((f) => f.from)).toContain("Movement.qty_delta");
  });
});

describe("one example, worked through", () => {
  const d = draft();
  const w = workingsOf(d);
  const moments = momentsOf(d);

  it("offers each row and moment an example says what it comes to", () => {
    expect(moments.map((m) => m.label)).toEqual(["flour, on 30 Jun 2026", "flour, on 5 Jul 2026"]);
  });

  it("shows the records that went into a sum, and only those of the row", () => {
    const shown = walkThrough(d, w, moments[0]);
    expect(shown.get("Movement.qty_delta")!.items.map((i) => i.value)).toEqual(["+25", "+25", "-14"]);
    expect(shown.get("Movement.item")!.value).toBe("flour");
    expect(shown.get("IngredientStock.quantity_on_hand"))
      .toMatchObject({ value: "36", expected: "36", holds: true });
    expect(shown.get("IngredientStock.stock_ingredient")!.value).toBe("flour");
  });

  it("follows a row's key one record further when the rule reads it there", () => {
    // Each movement names a batch, and the batch says which ingredient it is.
    const viaBatch = {
      ...d,
      workings: [{
        ...d.workings![0],
        columns: [{ name: "quantity_on_hand", kind: "aggregate", operator: "sum",
          reads: [{ class: "Movement", fields: ["qty_delta"], by: { stock_ingredient: "batch" },
            via: { stock_ingredient: ["batch_ingredient"] } }] }],
      }],
      examples: [{
        ...flour(),
        recorded: [
          { record: "b1", class: "Batch", when: null, facts: { batch_ingredient: "flour" } },
          { record: "b2", class: "Batch", when: null, facts: { batch_ingredient: "salt" } },
          { record: "m1", class: "Movement", when: "2026-06-02", facts: { batch: "b1", qty_delta: 25 } },
          { record: "m2", class: "Movement", when: "2026-06-03", facts: { batch: "b2", qty_delta: 5 } },
          { record: "m3", class: "Movement", when: "2026-06-20", facts: { batch: "b1", qty_delta: -14 } },
        ],
      }],
    } as DraftState;
    const shown = walkThrough(viaBatch, workingsOf(viaBatch), momentsOf(viaBatch)[0]);
    expect(shown.get("Movement.qty_delta")!.items.map((i) => i.value)).toEqual(["+25", "-14"]);
    expect(shown.get("Movement.batch")!.value).toBe("b1");
  });

  it("reads what was recorded as it stood at the moment", () => {
    expect(walkThrough(d, w, moments[0]).get("Ingredient.ingredient_reorder_level"))
      .toMatchObject({ value: "20", note: "from the start" });
    expect(walkThrough(d, w, moments[1]).get("Ingredient.ingredient_reorder_level"))
      .toMatchObject({ value: "30", note: "since 1 Jul 2026" });
  });

  it("shows a number that should be empty, and is, as checked", () => {
    const salt: ExampleResult = {
      ...flour(), name: "no_level",
      checks: [{ table: "IngredientStock", row: "salt", at: null, column: "headroom",
        expected: "empty", got: "empty", holds: true }],
      recorded: [{ record: "salt", class: "Ingredient", when: null, facts: { ingredient_code: "SLT" } }],
    };
    const d2 = { ...d, examples: [salt] };
    const [only] = momentsOf(d2);
    expect(only.label).toBe("salt");
    const shown = walkThrough(d2, w, only);
    expect(shown.get("IngredientStock.headroom")).toMatchObject({ value: null, expected: null, holds: true });
    expect(shown.get("Ingredient.ingredient_reorder_level")).toMatchObject({ value: null, note: "not recorded" });
    expect(roomFor(d2, w)["IngredientStock.headroom"]).toBe(1);
  });

  it("puts the numbers into a formula and says when one comes out wrong", () => {
    expect(walkThrough(d, w, moments[0]).get("IngredientStock.headroom"))
      .toMatchObject({ sum: "36 − 20", value: "16", holds: true });
    expect(walkThrough(d, w, moments[1]).get("IngredientStock.headroom"))
      .toMatchObject({ expected: "6", value: "16", holds: false });
  });
});

describe("where the fields go", () => {
  const d = draft();
  const w = workingsOf(d);
  const room = roomFor(d, w);
  const laid = arrangeWorkings(w, room);
  const at = (id: string) => {
    const c = w.cells.find((x) => x.id === id)!;
    return { x: laid.groups[c.kind].x + laid.cells[id].x, y: laid.groups[c.kind].y + laid.cells[id].y };
  };

  it("reads left to right: recorded, then worked out from it", () => {
    expect(at("Movement.qty_delta").x).toBeLessThan(at("IngredientStock.quantity_on_hand").x);
    expect(at("IngredientStock.quantity_on_hand").x).toBeLessThan(at("IngredientStock.headroom").x);
  });

  it("keeps every field inside its kind, under its name", () => {
    for (const c of w.cells) {
      const p = laid.cells[c.id];
      const g = laid.groups[c.kind];
      expect(p.x).toBeGreaterThanOrEqual(GROUP.side);
      expect(p.y).toBeGreaterThanOrEqual(GROUP.head);
      expect(p.x + CELL.width).toBeLessThanOrEqual(g.width);
      expect(p.y + cellHeight(room[c.id])).toBeLessThanOrEqual(g.height);
    }
  });

  it("never lays one kind over another", () => {
    const names = Object.keys(laid.groups);
    for (const a of names) {
      for (const b of names) {
        if (a >= b) continue;
        const r = laid.groups[a];
        const s = laid.groups[b];
        const apart = r.x + r.width <= s.x || s.x + s.width <= r.x
          || r.y + r.height <= s.y || s.y + s.height <= r.y;
        expect(apart, `${a} and ${b}`).toBe(true);
      }
    }
  });

  it("makes room for the busiest example, so changing it moves nothing", () => {
    expect(room["Movement.qty_delta"]).toBe(3);
    expect(room["IngredientStock.headroom"]).toBe(2);
  });
});

describe("what changed", () => {
  const changes = [
    { what: "pin" as const, name: "@rival/stock-moves@v1", how: "added" as const },
    { what: "kind" as const, name: "IngredientStock", how: "changed" as const },
    { what: "field" as const, name: "IngredientStock.headroom", how: "added" as const },
    { what: "field" as const, name: "IngredientStock.stock_note", how: "removed" as const },
    { what: "kind" as const, name: "Shelf", how: "added" as const },
    { what: "field" as const, name: "Shelf.shelf_code", how: "added" as const },
    { what: "example" as const, name: "flour_in_and_out", how: "changed" as const },
  ];

  it("marks the boxes and the fields, and what changed just now", () => {
    const marks = marksOf(changes, [changes[2]]);
    expect(marks.kinds.get("IngredientStock")).toBe("changed");
    expect(marks.kinds.get("Shelf")).toBe("added");
    expect(marks.fields.get("IngredientStock.headroom")).toBe("added");
    expect(marks.fields.has("IngredientStock.quantity_on_hand")).toBe(false);
    expect([...marks.fresh]).toEqual(["IngredientStock.headroom"]);
  });

  it("says it by kind, with the map's own names and checks", () => {
    const changed = changedOf(draft(), changes);
    expect(changed.kinds.map((k) => [k.label, k.how])).toEqual([
      ["Ingredient stock", "changed"], ["Shelf", "added"],
    ]);
    const stock = changed.kinds[0].fields;
    expect(stock.map((f) => [f.label, f.how])).toEqual([
      ["Headroom", "added"], ["Stock note", "removed"],
    ]);
    // The flour example expects a different headroom on 5 July.
    expect(stock[0].check?.state).toBe("failing");
    expect(stock[1].check).toBeNull();
    expect(changed.examples).toEqual([
      { name: "flour_in_and_out", label: "Flour in and out", how: "changed" }]);
    expect(changed.said).toBe(
      "1 new kind, 2 new fields, 1 field removed, 1 example changed, 1 new module built on");
  });

  it("says nothing changed when nothing did", () => {
    expect(changedOf(draft(), []).said).toBe("nothing");
  });

  it("finds the requests that made a kind of thing", () => {
    const turns = [
      { touched: [changes[4]] },
      {},
      { touched: [changes[1], changes[2]] },
      { touched: [{ what: "kind" as const, name: "Shelf", how: "changed" as const }] },
    ];
    expect(turnsAbout(turns, "Shelf")).toEqual([{ turn: 0, how: "added" }, { turn: 3, how: "changed" }]);
    expect(turnsAbout(turns, "IngredientStock")).toEqual([{ turn: 2, how: "changed" }]);
    expect(turnsAbout(turns, "Movement")).toEqual([]);
  });
});

describe("what the agent says", () => {
  it("reads bold, code and italic, and leaves the rest as it is", () => {
    expect(piecesOf("Sisa **tepung** ada `20` kg, *kira-kira*.")).toEqual([
      { text: "Sisa " }, { text: "tepung", bold: true }, { text: " ada " },
      { text: "20", code: true }, { text: " kg, " }, { text: "kira-kira", italic: true },
      { text: "." },
    ]);
    // A lone asterisk is a character, not the start of anything.
    expect(piecesOf("2 * 3 = 6")).toEqual([{ text: "2 * 3 = 6" }]);
  });

  it("reads paragraphs and lists, each item with its own marker and depth", () => {
    const blocks = blocksOf(
      "Berikut ringkasannya:\n\n1. **Selesai:**\n   - tabel stok\n   - contoh\n2. Sisa\n\nTerima kasih.\n### Catatan");
    expect(blocks.map((b) => b.kind)).toEqual(["paragraph", "list", "paragraph"]);
    const list = blocks[1];
    if (list.kind !== "list") throw new Error("not a list");
    expect(list.items.map((i) => [i.marker, i.depth])).toEqual([
      ["1.", 0], ["•", 1], ["•", 1], ["2.", 0]]);
    expect(list.items[0].pieces).toEqual([{ text: "Selesai:", bold: true }]);
    const last = blocks[2];
    if (last.kind !== "paragraph") throw new Error("not a paragraph");
    expect(last.lines).toEqual([[{ text: "Terima kasih." }], [{ text: "Catatan", bold: true }]]);
  });
});

describe("the questions a person is asked", () => {
  it("asks once about an example waiting for its rules, not once per number", () => {
    const holes = [
      { kind: "example_not_agreed", where: "example flour" },
      { kind: "example_failed", where: "example flour: Level flour, on_hand" },
      { kind: "example_failed", where: "example flour: Level flour, headroom" },
      { kind: "example_failed", where: "example sugar: Level sugar, on_hand" },
      { kind: "example_failed", where: "example sugar: Level sugar, headroom" },
      { kind: "column_unchecked", where: "Level.on_hand" },
    ];
    expect(exampleOf("example flour: Level flour, on_hand")).toBe("flour");
    expect(exampleOf("Level.on_hand")).toBeNull();
    expect(askedOnce(holes, new Set(["flour"])).map((h) => h.where)).toEqual([
      "example flour", "example flour: Level flour, on_hand",
      "example sugar: Level sugar, on_hand", "example sugar: Level sugar, headroom",
      "Level.on_hand",
    ]);
  });
});

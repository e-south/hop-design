import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const load = async () => import("data:text/javascript;base64," + Buffer.from(await readFile(
  new URL("../../src/hop_design/assets/variant_explorer/grouped_navigation.js", import.meta.url)
)).toString("base64"));

class Target {
  constructor() { this.attributes = {}; this.events = {}; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(key, callback) { this.events[key] = callback; }
  focus() { this.events.focus(); }
  key(key) { const event = {key, defaultPrevented:false, preventDefault(){this.defaultPrevented=true;}}; this.events.keydown(event); return event; }
}

test("one tab entry per group retains every value and updates only the focused group", async () => {
  const { groupedNavigation } = await load();
  const a = Array.from({length:256}, () => new Target()), b = [new Target(),new Target()];
  groupedNavigation([a,b]);
  const entries = nodes => nodes.filter(n=>n.attributes.tabindex === "0");
  assert.equal(entries([...a,...b]).length, 2);
  for(let i=0;i<a.length-1;i++) assert.equal(a[i].key("ArrowDown").defaultPrevented,true);
  assert.deepEqual(entries(a), [a.at(-1)]);
  assert.deepEqual(entries(b), [b[0]]);
  assert.equal(a.at(-1).key("Home").defaultPrevented,false);
  a.at(-1).key("ArrowUp");
  assert.deepEqual(entries(a), [a.at(-2)]);
  b[1].focus();
  assert.deepEqual(entries(b), [b[1]]);
});

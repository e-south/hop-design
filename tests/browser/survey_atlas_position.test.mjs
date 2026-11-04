import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const load = async () => import("data:text/javascript;base64," + Buffer.from(await readFile(
  new URL("../../src/hop_design/assets/survey_explorer/atlas_position.js", import.meta.url)
)).toString("base64"));
const oldAddress = {state_id: "old", strand_id: "source", index: 10};
const newAddress = {state_id: "new", strand_id: "changed-source", index: 12};
const key = value => JSON.stringify([value.state_id, value.strand_id, value.index]);
const before = {atlas: {materialized_realization_id: "a", states: [{state: {state_id: "old", phase: "hairpin"}}]}};
const after = {atlas: {materialized_realization_id: "b", states: [{state: {state_id: "new", phase: "hairpin"}}]}, comparison: {
  reference: "a", transitions: [{links: [{reference: oldAddress, target: newAddress, relation: "comparison"}]}],
}};
const geometry = () => ({
  frame: [100, 1000, 400, 300], whole: [0, 0, 1000, 3000], nextWhole: [0, 0, 1200, 6000],
  beforePoints: new Map([[key(oldAddress), [250, 1100]]]),
  afterPoints: new Map([[key(newAddress), [270, 1400]]]),
  beforeRows: new Map([["old", [0, 1000]]]), afterRows: new Map([["new", [0, 1240]]]),
  focus: oldAddress,
});

test("verified base correspondence preserves zoom and screen position despite changed route height", async () => {
  const { transferAtlasView } = await load();
  const result = transferAtlasView(before, after, geometry());
  assert.deepEqual(result.frame, [120, 1300, 400, 300]);
  assert.deepEqual(result.focus, newAddress);
  assert.equal(result.focusStatus, "mapped");
});

test("ambiguous base correspondence keeps the processing stage without inventing a position", async () => {
  const { transferAtlasView } = await load();
  const target = structuredClone(after);
  target.comparison.transitions[0].links = [];
  const result = transferAtlasView(before, target, geometry());
  assert.deepEqual(result.frame, [100, 1240, 400, 300]);
  assert.equal(result.focus, null);
  assert.equal(result.focusStatus, "unresolved");
});

test("a comparison against another preparation cannot move the inspected base", async () => {
  const { transferAtlasView } = await load();
  const target = structuredClone(after);
  target.comparison.reference = "different-preparation";
  const result = transferAtlasView(before, target, geometry());
  assert.equal(result.focus, null);
  assert.equal(result.focusStatus, "unresolved");
  assert.deepEqual(result.frame, [100, 1240, 400, 300]);
});

test("the fitted atlas stays fitted and an unchanged preparation preserves exact addresses", async () => {
  const { transferAtlasView } = await load();
  const g = geometry();
  g.frame = [...g.whole];
  assert.deepEqual(transferAtlasView(before, after, g).frame, g.nextWhole);
  g.frame = [100, 1000, 400, 300];
  g.afterPoints = new Map([[key(oldAddress), [250, 1500]]]);
  const result = transferAtlasView(before, before, g);
  assert.deepEqual(result.focus, oldAddress);
  assert.deepEqual(result.frame, [100, 1400, 400, 300]);
});

test("repeated phases do not masquerade as unique processing-stage correspondence", async () => {
  const { transferAtlasView } = await load();
  const target = structuredClone(after);
  target.comparison.transitions[0].links = [];
  target.atlas.states.push({state: {state_id: "another", phase: "hairpin"}});
  const g = geometry();
  const result = transferAtlasView(before, target, g);
  assert.deepEqual(result.frame, g.frame);
  assert.equal(result.focus, null);
});

async function loadViewport() {
  const root = new URL("../../src/hop_design/assets/", import.meta.url);
  const uri = async name => "data:text/javascript;base64," + Buffer.from(await readFile(new URL(name, root))).toString("base64");
  let source = await readFile(new URL("survey_explorer/atlas.js", root), "utf8");
  for (const [name, file] of [["grouped_navigation", "variant_explorer/grouped_navigation.js"], ["camera_geometry", "variant_explorer/camera_geometry.js"], ["parameters", "survey_explorer/parameters.js"], ["atlas_position", "survey_explorer/atlas_position.js"]])
    source = source.replace(`"./${name}.js"`, JSON.stringify(await uri(file)));
  return import("data:text/javascript;base64," + Buffer.from(source).toString("base64"));
}

const events = () => ({
  listeners: {}, addEventListener(name, fn) {
    const previous = this.listeners[name];
    this.listeners[name] = event => { previous?.(event); fn(event); };
  },
});
function drawing(box, location, rowY) {
  const attrs = {viewBox: box.join(" ")};
  const base = {
    ...events(),
    dataset: {stateId: location.state_id, strandId: location.strand_id, baseIndex: String(location.index)},
    getBBox: () => ({x: 240, y: 90, width: 20, height: 20}),
    closest: selector => selector === "[data-base-index]" ? base : selector === "[data-atlas-state]" ? {dataset: {atlasX: "0", atlasY: String(rowY)}} : null,
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; },
  };
  const svg = {
    dataset: {}, getAttribute: name => attrs[name], setAttribute: (name, value) => attrs[name] = value,
    querySelectorAll: selector => selector === "[data-base-index]" ? [base] : selector === "[data-site-id]" ? [] : [{dataset: {atlasState: location.state_id, atlasX: "0", atlasY: String(rowY)}}],
  };
  return {svg, base};
}

test("viewport keeps the focused base in place and ignores an obsolete drawing response", async t => {
  const {molecularViewport} = await loadViewport();
  const host = {...events(), parentElement: events(), replaceChildren(svg) { this.current = svg; }};
  const fit = events();
  const a = drawing([0, 0, 1000, 3000], oldAddress, 1000);
  const b = drawing([0, 0, 1200, 6000], newAddress, 1300);
  const c = drawing([0, 0, 1500, 6000], newAddress, 1600);
  const documents = {a, b, c};
  const originalFetch = globalThis.fetch, originalParser = globalThis.DOMParser;
  t.after(() => { globalThis.fetch = originalFetch; globalThis.DOMParser = originalParser; });
  globalThis.DOMParser = class { parseFromString(value) { return {documentElement: documents[value].svg, querySelector: () => null}; } };
  let release, rejectFetch, rejectText;
  globalThis.fetch = async url => {
    if (url === "slow") await new Promise(resolve => { release = resolve; });
    if (url === "rejected-fetch") await new Promise((_resolve, reject) => { rejectFetch = reject; });
    if (url === "rejected-text") return {ok: true, text: () => new Promise((_resolve, reject) => { rejectText = reject; })};
    return {ok: true, text: async () => url === "slow" ? "c" : url};
  };
  const viewport = molecularViewport(host, fit, () => {});
  await viewport.show({drawing: "a", summary: before});
  host.parentElement.listeners.keydown({key: "+", target: {closest: () => null}, preventDefault() {}});
  host.listeners.focusin({target: a.base});
  assert.equal(a.base.attributes["data-inspected"], "true", "focus visibly marks the inspected base immediately");
  const frame = a.svg.getAttribute("viewBox").split(" ").map(Number);
  const slow = viewport.show({drawing: "slow", summary: after});
  await viewport.show({drawing: "b", summary: after});
  const expected = [frame[0], frame[1] + 300, frame[2], frame[3]];
  b.svg.getAttribute("viewBox").split(" ").map(Number).forEach((value, i) => assert.ok(Math.abs(value - expected[i]) < 1e-9));
  assert.equal(b.base.attributes["data-inspected"], "true");
  assert.equal(b.svg.dataset.focusStatus, "mapped");
  release(); await slow;
  assert.equal(host.current, b.svg);
  const failedFetch = viewport.show({drawing: "rejected-fetch", summary: after});
  await viewport.show({drawing: "b", summary: after});
  rejectFetch(Error("obsolete fetch"));
  await assert.doesNotReject(failedFetch);
  const failedText = viewport.show({drawing: "rejected-text", summary: after});
  await Promise.resolve();
  await viewport.show({drawing: "b", summary: after});
  rejectText(Error("obsolete response body"));
  await assert.doesNotReject(failedText);
  assert.equal(host.current, b.svg);
});

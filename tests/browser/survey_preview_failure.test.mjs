import {test} from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";

test("a failed drawing cannot leave an old molecule beside retrieval of a new preparation", async t => {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      textContent: "", disabled: false, hidden: false, addEventListener() {}, replaceChildren() {},
      classList: {add() {}, remove() {}},
    });
    return elements.get(id);
  };
  const old = {document: globalThis.document, fetch: globalThis.fetch, seam: globalThis.hopTest, window:globalThis.window};
  t.after(() => {
    globalThis.document = old.document;
    globalThis.fetch = old.fetch;
    globalThis.hopTest = old.seam;
    globalThis.window = old.window;
  });
  globalThis.document = {getElementById: element, querySelector: () => ({content: "test-token"}), body: element("body")};
  globalThis.window = {addEventListener() {}};
  const preparation = id => ({
    token: "test-state", choices: {axes: [], coverage: {}, matching_preparations: 2,
      matching_products: {endpoint: 2}, query: {parameters: []}},
    selection: {materialized_realization_id: id}, parameter_key: null,
    preview: {drawing: id, summary: {atlas: {construction_cost: {summary_lines: [`Cost for ${id}`]}}, projection: {values: {
      loop_word: id, basal_release_recognition_material: "source_duplex",
    }}}},
  });
  globalThis.fetch = async url => ({ok: true, json: async () => preparation(url === "/api/state" ? "A" : "B")});
  let displayed = null, rejectDrawing = true;
  const seam = globalThis.hopTest = {
    drawPlot(_host, _choices, _drawing, actions) { seam.actions = actions; },
    molecularViewport: () => ({
      async prepare(preview) {
        if (preview.drawing === "B" && rejectDrawing) throw Error("drawing unavailable");
        return () => { displayed = preview.drawing; };
      },
      clear() { displayed = null; }, highlight() {},
    }),
  };
  const uri = source => "data:text/javascript;base64," + Buffer.from(source).toString("base64");
  let source = await readFile(new URL("../../src/hop_design/assets/survey_explorer/editor.js", import.meta.url), "utf8");
  const modules = {
    selected_views: await readFile(new URL("../../src/hop_design/assets/survey_explorer/selected_views.js", import.meta.url), "utf8"),
    grouped_navigation: "export const teachingNavigation=()=>{};",
    teaching_links: "export const connectTeaching=()=>{};",
    plot: "export const drawPlot=(...args)=>globalThis.hopTest.drawPlot(...args);",
    atlas: "export const molecularViewport=(...args)=>globalThis.hopTest.molecularViewport(...args);",
    model: "export const toggleValue=()=>{}, rangeQuery=()=>{}, queryCommands=()=>'', preparationDescription=()=>'', coverageDescription=()=>'';",
    parameters: await readFile(new URL("../../src/hop_design/assets/survey_explorer/parameters.js", import.meta.url), "utf8"),
  };
  for (const [name, body] of Object.entries(modules))
    source = source.replace(`"./${name}.js"`, JSON.stringify(uri(body)));
  await import(uri(source));
  assert.equal(displayed, "A");
  assert.equal(element("retrieve").disabled, false);
  assert.equal(element("construction-cost").textContent, "Cost for A");
  await seam.actions.value("loop_word", "B");
  assert.equal(displayed, null, "old molecular image must not impersonate the new selection");
  assert.equal(element("construction-cost").textContent, "");
  assert.equal(element("retrieve").disabled, true);
  assert.equal(element("save-selection").disabled, true);
  assert.equal(element("download").hidden, true);
  assert.match(element("notice").textContent, /drawing unavailable/);
  rejectDrawing = false;
  await element("reload").onclick();
  assert.equal(displayed, "B");
  assert.equal(element("construction-cost").textContent, "Cost for B");
  assert.equal(element("retrieve").disabled, false);
  assert.match(element("molecule").textContent, /loop B/);
});

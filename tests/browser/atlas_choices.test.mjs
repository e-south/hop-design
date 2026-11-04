import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const load = async () => import("data:text/javascript;base64," + Buffer.from(await readFile(
  new URL("../../src/hop_design/assets/variant_explorer/local_choice_model.js", import.meta.url)
)).toString("base64"));
test("local choices retain complete-route ambiguity and exclude unsupported combinations", async () => {
  const { supportedVariants } = await load();
  const choices = { compatible_options: ["a", "c"], variants: [
    {variant_id: "one", option_labels: ["a", "b", "c"], sequences: [{sequence: "AAAA"}]},
    {variant_id: "two", option_labels: ["b"], sequences: [{sequence: "AACA"}]},
  ]};
  const result = supportedVariants(choices);
  assert.equal(result.length, 1);
  assert.deepEqual(result[0].option_labels, ["a", "c"]);
  assert.deepEqual(choices.variants[0].option_labels, ["a", "b", "c"]);
});

test("exclusions explain regional changes without turning unassessed cases into differences", async () => {
  const { exclusionSummaries } = await load();
  const choices = { query: {stage: "hairpin"}, excluded_options: [
    {label: "a", reasons: [{kind: "preserved_surroundings", neighborhood: "assembly", stage: "hairpin", status: "different"}]},
    {label: "b", reasons: [{kind: "preserved_surroundings", neighborhood: "assembly", stage: "hairpin", status: "different"}]},
    {label: "c", reasons: [{kind: "preserved_property", property: "terminal_chemistry", stage: "endpoint", status: "unassessed"}]},
    {label: "d", reasons: [{kind: "neighborhood_pin", neighborhood: "loop", status: "different"}]},
  ]};
  const labels = {neighborhoods: {assembly: "Open side", loop: "Loop"}, properties: {terminal_chemistry: "Terminal chemistry"}};
  assert.deepEqual(exclusionSummaries(choices, labels), [
    {count: 2, text: "Open side differs from the fixed reference at the hairpin stage."},
    {count: 1, text: "Terminal chemistry is unassessed against the fixed reference at the requested endpoint."},
    {count: 1, text: "Loop does not match the allowed variants at the hairpin stage."},
  ]);
});

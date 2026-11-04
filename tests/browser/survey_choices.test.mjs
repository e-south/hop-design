import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const source = await readFile(
  new URL(
    "../../src/hop_design/assets/survey_explorer/model.js",
    import.meta.url,
  ),
  "utf8",
);
const { toggleValue, rangeQuery } = await import(
  "data:text/javascript;base64," + Buffer.from(source).toString("base64")
);
const a = {
  address: { target: 1, step: 0 },
  materialized_realization_id: "a",
  values: { loop_nt: 4, left_end_word: "AGTC" },
  matches: true,
};
test("axis toggling keeps other predicates and chooses complete queries", () => {
  const query = {
    schema: "hop.interface-survey-query/v1",
    parameters: [
      { key: "loop_nt", minimum: 3, maximum: 8 },
      { key: "left_end_word", values: ["AGTC"] },
    ],
  };
  const next = toggleValue(query, "left_end_word", "TGCA");
  assert.deepEqual(next.parameters[0], query.parameters[0]);
  assert.deepEqual(next.parameters[1], {
    key: "left_end_word",
    values: ["TGCA"],
  });
  assert.deepEqual(toggleValue(next, "left_end_word", "TGCA").parameters, [
    query.parameters[0],
  ]);
  assert.deepEqual(rangeQuery(query, "loop_nt", 8, 4).parameters[1], {
    key: "loop_nt",
    minimum: 4,
    maximum: 8,
  });
  assert.equal(query.parameters[0].minimum, 3);
});
test("CLI handoff preserves exact selection and exposes reproducible sampling separately", async () => {
  const { queryCommands } = await import(
    "data:text/javascript;base64," + Buffer.from(source).toString("base64")
  );
  const exact = queryCommands(a, null);
  assert.match(
    exact,
    /survey select .*--target 1 --step 0 --identity 'a' > selection.json/,
  );
  assert.match(exact, /survey atlas .*--selection selection.json/);
  assert.match(exact, /survey retrieve .*--selection selection.json/);
  const sampled = queryCommands(a, 73);
  assert.match(sampled, /survey sample .*--seed 73 > sampled-selection.json/);
  assert.match(sampled, /survey select .* > selection.json/);
  assert.doesNotMatch(
    queryCommands(null, null),
    /survey (select|atlas|retrieve|sample)/,
  );
});

test('overlapping choices name methods and changed materials before provenance IDs', async () => {
  const { preparationDescription, coverageDescription } = await import(
    'data:text/javascript;base64,' + Buffer.from(source).toString('base64')
  );
  const reference = { ...a, values: {loop_word: 'AAAA', left_end_word: 'AGTC', right_end_word: 'AACC'},
    methods: [{name:'Nb.BsrDI'}], material_roles: {adapter_oligo:{material_id:'old',length_nt:31}}};
  const next = {...reference, material_roles:{adapter_oligo:{material_id:'new',length_nt:31}}};
  const text = preparationDescription(next, reference);
  assert.match(text, /AGTC \/ AACC/);
  assert.match(text, /loop AAAA/);
  assert.match(text, /Nb.BsrDI/);
  assert.match(text, /adapter oligo changes/);
  assert.doesNotMatch(text, /record|target|step/);
  assert.match(coverageDescription({supported_pairs:1, excluded_pairs:2, unresolved_pairs:3}), /2 excluded/);
});

test('discovery view exports the short lifecycle and separates further search', async () => {
  const {queryCommands} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
  const canonical = "hop-design design query 'my designs' --query '/view/applied.json'";
  const commands = queryCommands(null, null, {commands: canonical});
  assert.equal(commands, canonical);
  assert.doesNotMatch(commands, /continue|sample/);
  assert.throws(() => queryCommands(a, 1, {}), /command/);
});

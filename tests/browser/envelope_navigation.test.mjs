import {test} from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const load = async () => import("data:text/javascript;base64," + Buffer.from(await readFile(
  new URL("../../src/hop_design/assets/variant_explorer/envelope_model.js", import.meta.url)
)).toString("base64"));

test("choosing an unobserved coordinate preserves other parameters and controls", async () => {
  const {selectCoordinate} = await load();
  const query = {reference:"fixed", controls:[{stage:"hairpin",property:"non_loop_sequences"}],
    parameters:[{key:"foldback_arm_bp",minimum:8,maximum:10}], pins:[{neighborhood:"stem"}]};
  const next = selectCoordinate(query, "loop_word", "AAAA");
  assert.deepEqual(next.parameters, [...query.parameters,{key:"loop_word",values:["AAAA"]}]);
  assert.deepEqual(next.controls, query.controls);
  assert.deepEqual(next.pins, query.pins);
  assert.equal(next.reference, "fixed");
  assert.equal(query.parameters.length, 1);
});

test("an explicit pivot changes only named exploratory filters using one complete path", async () => {
  const {pivotQuery} = await load();
  const query = {reference:"fixed", controls:[{property:"non_loop_sequences"}],
    parameters:[{key:"self_paired_arm_bp",values:[900]},{key:"left_gap",values:[6]}]};
  const path = {values:{self_paired_arm_bp:7,left_gap:6,loop_word:"GAAA"}};
  const alternative = {different_selections:["self_paired_arm_bp"],preservation_conflicts:[]};
  const next = pivotQuery(query, "loop_word", "GAAA", alternative, path);
  assert.deepEqual(next.parameters, [{key:"self_paired_arm_bp",values:[7]},
    {key:"left_gap",values:[6]},{key:"loop_word",values:["GAAA"]}]);
  assert.deepEqual(next.controls, query.controls);
  assert.throws(() => pivotQuery(query,"loop_word","GAAA",{
    ...alternative,preservation_conflicts:[{kind:"preserved_property"}]
  },path), /preserved/);
});

test("open permission edits use source semantics and retain explicit zero", async () => {
  const {rangePermission} = await load();
  assert.deepEqual(rangePermission({unrestricted:"empty"}, 0, 0, true), []);
  assert.equal(rangePermission({unrestricted:"null"}, 0, 0, true), null);
  assert.deepEqual(rangePermission({kind:"integers"}, 0, 2, false), [0,1,2]);
  assert.equal(rangePermission({kind:"integer"}, 0, 0, false), 0);
  assert.throws(() => rangePermission({kind:"integers"}, 3, 2, false), /ordered/);
});

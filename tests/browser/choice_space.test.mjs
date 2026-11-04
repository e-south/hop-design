import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const load = async () => import("data:text/javascript;base64," + Buffer.from(await readFile(
  new URL("../../src/hop_design/assets/variant_explorer/choice_space_model.js", import.meta.url)
)).toString("base64"));
const space = {
  stage: "endpoint",
  axes: [
    {key: "loop", kind: "categorical", values: ["GAAA", "TTTC"].map(value => ({value}))},
    {key: "method", kind: "categorical", values: ["a", "b"].map(value => ({value}))},
  ],
  paths: [
    {option_label: "one", molecule_id: "p", values: {loop: "GAAA", method: "a"}},
    {option_label: "two", molecule_id: "q", values: {loop: "TTTC", method: "b"}},
    {option_label: "three", molecule_id: "p", values: {loop: "GAAA", method: "b"}},
  ],
};
test("filters use OR within axes and AND between axes over whole paths", async () => {
  const {filterChoices, toggleValue} = await load(), before = structuredClone(space);
  let filters = toggleValue({}, "loop", "GAAA");
  filters = toggleValue(filters, "loop", "TTTC");
  filters = toggleValue(filters, "method", "a");
  const result = filterChoices(space, filters);
  assert.deepEqual(result.paths.map(p => p.option_label), ["one"]);
  assert.equal(result.availability.loop.TTTC, 0);
  assert.equal(result.availability.method.b, 2);
  assert.deepEqual(space, before);
  assert.deepEqual(filters.loop, ["GAAA", "TTTC"]);
  assert.deepEqual(toggleValue(filters, "method", "a"), {loop: ["GAAA", "TTTC"]});
});
test("empty filters never synthesize a path or select a product; exact products retain preparations", async () => {
  const {filterChoices} = await load();
  const empty = filterChoices(space, {loop: ["TTTC"], method: ["a"]});
  assert.deepEqual(empty.paths, []);
  assert.deepEqual(empty.products, []);
  assert.deepEqual(filterChoices(space, {}).products, [
    {molecule_id: "p", option_labels: ["one", "three"]},
    {molecule_id: "q", option_labels: ["two"]},
  ]);
  assert.throws(() => filterChoices(space, {loop: ["unknown"]}), /Unknown/);
  assert.throws(() => filterChoices(space, {invented: [1]}), /Unknown/);
});
test("numeric coordinates preserve magnitude, zero and unknown values", async () => {
  const {axisPositions} = await load();
  const axis = {kind: "numeric", values: [0, 2, 8, null].map(value => ({value}))};
  const positions = axisPositions(axis, 0, 100);
  assert.equal(positions.get(0), 80);
  assert.equal(positions.get(2), 60);
  assert.equal(positions.get(8), 0);
  assert.equal(positions.get(null), 100);
  assert.equal(axisPositions({kind: "numeric", values: [{value: 0}]}, 0, 100).get(0), 50);
});

test("background display omits repeated literal words without inferring correspondence", async () => {
  const {backgroundLabel} = await load();
  const values = ["ACGA", "ACGG"].map(word => ({label: "full context", detail: {
    assembly: {sequences: [{sequence: "TATA"}, {sequence: word}]},
    stem: {sequences: [{sequence: "CCCC"}]},
  }}));
  assert.equal(backgroundLabel(values[0], values), "Open side: ACGA");
  assert.equal(backgroundLabel(values[1], values), "Open side: ACGG");
  assert.equal(backgroundLabel(values[0], [values[0]]), "Shared assessed surroundings");
  const same = {...values[0], detail: {...values[0].detail, contacts: []}};
  assert.match(backgroundLabel(values[0], [values[0], same]), /Shared sequence words; inspect pairing, order and termini/);
});

test("mouse picking retains all complete paths sharing a segment or crossing", async () => {
  const {pathsNearPoint} = await load();
  const paths = [
    {option_label: "one", points: [[0, 0], [10, 5], [20, 5]]},
    {option_label: "two", points: [[0, 10], [10, 5], [20, 5]]},
    {option_label: "three", points: [[0, 10], [10, 0], [20, 0]]},
  ];
  assert.deepEqual(pathsNearPoint(paths, [15, 5], .1).map(p => p.option_label), ["one", "two"]);
  assert.deepEqual(pathsNearPoint(paths, [2, 1], .1).map(p => p.option_label), ["one"]);
  assert.deepEqual(pathsNearPoint(paths, [20, 20], .1), []);
});

test("integer range brushing retains declared unsupported values and conditional alternatives", async () => {
  const {filterChoices, setRange, selectionList} = await load();
  const extended = structuredClone(space);
  extended.axes.push({key: "arm", kind: "numeric", declared: {minimum: 6, maximum: 10},
    values: [6, 7, 8, 9, 10].map(value => ({value}))});
  [7, 8, 9].forEach((value, i) => { extended.paths[i].values.arm = value; });
  const filters = setRange({method: ["b"]}, "arm", 8.2, 6.8);
  assert.deepEqual(filters.arm, {minimum: 7, maximum: 8});
  const result = filterChoices(extended, filters);
  assert.deepEqual(result.paths.map(p => p.option_label), ["two"]);
  assert.equal(result.availability.arm[9], 1);
  assert.equal(result.availability.arm[6], 0);
  assert.equal(result.availability.method.a, 1);
  assert.deepEqual(selectionList(filters), [
    {key: "arm", minimum: 7, maximum: 8}, {key: "method", values: ["b"]},
  ]);
  assert.deepEqual(filterChoices(extended, setRange({}, "arm", 6, 6)).paths, []);
  assert.throws(() => filterChoices(extended, {loop: {minimum: 0, maximum: 1}}), /numeric/);
});

test("coverage intersects declared joint branches without inventing failed coordinates", async () => {
  const {branchCoverage} = await load();
  const branches = [
    {branch_id: "a", status: "evaluated", domains: {left_gap: {values: [0]}, right_gap: {values: [0]}}, failures: [{code: "span"}], option_labels: []},
    {branch_id: "b", status: "unexamined", domains: {left_gap: {values: [6]}, right_gap: {values: [6]}}, failures: [], option_labels: []},
  ];
  assert.deepEqual(branchCoverage(branches, {left_gap: [0], right_gap: [6]}), []);
  assert.equal(branchCoverage(branches, {left_gap: {minimum: 0, maximum: 2}})[0].branch_id, "a");
  // Unknown achieved contact count cannot exclude a branch before it is evaluated.
  assert.equal(branchCoverage(branches, {noncanonical_pairs: [0]}).length, 2);
});

test("local support cannot acquire unknown downstream coordinates or imply complete products", async () => {
  const {filterLocalSupport} = await load();
  const paths = [{scope:"foldback_local_only", values:{loop_word:"GAAA", foldback_arm_bp:9}},
                 {scope:"foldback_local_only", values:{loop_word:"TTTC", foldback_arm_bp:8}}];
  assert.equal(filterLocalSupport(paths, {loop_word:["GAAA"], left_gap:[0]}).length, 1);
  assert.equal(filterLocalSupport(paths, {foldback_arm_bp:{minimum:10,maximum:11}}).length, 0);
  assert.equal(paths[0].values.left_gap, undefined);
});

test("partial paths stop before an unassessed intervening axis", async () => {
  const {localCoordinateRuns} = await load();
  const axes = ["A", "D", "end", "R", "C"].map(key => ({key}));
  const values = {A:9, D:2, R:7, C:4};
  assert.deepEqual(localCoordinateRuns(axes, values), [[0,1], [3,4]]);
  assert.deepEqual(localCoordinateRuns(axes, {A:9, R:7}), [[0], [3]]);
});

test("path colors describe a named low-cardinality coordinate and survive filtering", async () => {
  const {pathPalette} = await load();
  const axes = [{key:'basal_method', label:'Basal nickase', values:[
    {value:'a',label:'Method A'},{value:'b',label:'Method B'}
  ]}];
  const palette = pathPalette({axes});
  assert.equal(palette.key, 'basal_method');
  assert.equal(palette.entries.length, 2);
  assert.notEqual(palette.entries[0].color, palette.entries[1].color);
  assert.deepEqual(pathPalette({axes:[...axes].reverse()}), palette);
  assert.equal(pathPalette({axes:[]}).key, null);
});

test('coverage distinguishes exhausted local rejection from unresolved or downstream failure', async () => {
  const {localRejections} = await load();
  const exhausted = {status:'evaluated',local_coverage:{basal:{completion:'complete',feasibility:'infeasible',termination_reason:'exhausted_domain',rejection_counts:{'recognition-payload-conflict':1}},foldback:{completion:'complete',feasibility:'feasible',rejection_counts:{}}}};
  assert.deepEqual(localRejections(exhausted),[{region:'basal',reasons:['recognition-payload-conflict']}]);
  assert.deepEqual(localRejections({...exhausted,status:'unexamined'}),[]);
  assert.deepEqual(localRejections({status:'evaluated',local_coverage:{basal:{...exhausted.local_coverage.basal,completion:'truncated',termination_reason:'max_hits'}}}),[]);
  assert.deepEqual(localRejections({status:'evaluated',failures:[{code:'primer_span'}]}),[]);
});

test("parallel-coordinate layout stays short and fits the available width", async () => {
  const {compactPlotLayout} = await load();
  for (const width of [430, 900, 1244]) for (const count of [1, 6, 12]) {
    const box = compactPlotLayout(count, width);
    assert.equal(box.width, width);
    assert.ok(box.height <= 368);
    assert.ok(box.xs.every(x => x-box.labelWidth/2 >= 0 && x+box.labelWidth/2 <= width));
    assert.ok(Math.abs(box.xs[0]+box.xs.at(-1)-width)<.01);
    if (width >= 900) assert.ok(box.width / box.height >= 3.35);
    for (let i=1;i<box.xs.length;i++) assert.ok(box.xs[i-1]+box.labelWidth+6 < box.xs[i]);
  }
});
test("dense tick labels cannot overlap while all coordinate positions remain", async () => {
  const {tickLabelValues} = await load();
  const entries=Array.from({length:80},(_,value)=>({value}));
  const positions=new Map(entries.map(({value})=>[value,70+value*3]));
  const before=[...positions];
  const visible=tickLabelValues(entries,positions,{37:4,38:2},12);
  assert.ok(visible.has(37));
  const ys=[...visible].map(v=>positions.get(v)).sort((a,b)=>a-b);
  for(let i=1;i<ys.length;i++)assert.ok(ys[i]-ys[i-1]>=12);
  assert.deepEqual([...positions],before);
});

test('molecular detail exposes related contacts together without changing the query', async () => {
  const {molecularAxisOrder} = await load();
  const keys=['loop_word','foldback_arm_bp','join_offset_nt','self_paired_arm_bp','basal_method','basal_nick_offset_nt','left_gap','right_gap','source_reverse_primer_available_nt', ...['source_base','adapter_base','pair_class'].map(k=>'basal_'+k+'_3')];
  const axes=keys.map(key=>({key,dependencies:[],equivalent_measurements:[]}));
  const before=structuredClone(axes), order=molecularAxisOrder(axes,'basal_source_base_3');
  assert.ok(order.length<=9);
  assert.deepEqual(order.filter(k=>k.endsWith('_3')),['basal_source_base_3','basal_adapter_base_3','basal_pair_class_3']);
  for(const key of ['loop_word','left_gap','right_gap'])assert.ok(order.includes(key));
  assert.deepEqual(axes,before);
  assert.deepEqual(molecularAxisOrder(axes),keys.slice(0,9));
});
test('dense molecular words remain literal and completed words receive readable positions', async () => {
  const {molecularLabelLines,compactPlotLayout}=await load();
  const word='ACGTACGTACGTACGTACGT';
  assert.equal(molecularLabelLines(word,8).join(''),word);
  assert.ok(molecularLabelLines(word,8).every(x=>!x.includes('…')));
  const box=compactPlotLayout(9,1200,24);
  assert.ok((box.bottom-box.top)/23>=12);
  assert.ok(box.height<=368);
});

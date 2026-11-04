import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source = await readFile(new URL('../../src/hop_design/assets/design_explorer/linked_focus.js', import.meta.url), 'utf8');
const module = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));

const state = {
  choices: {paths: [
    {materialized_realization_id: 'a', matches: true},
    {materialized_realization_id: 'b', matches: false},
    {materialized_realization_id: 'c', matches: true},
  ]},
  families: {
    products: [
      {identity: 'x', preparations: ['a'], features: {loop_nt: [4]}},
      {identity: 'y', preparations: ['b'], features: {foldback_arm_bp: [6]}},
      {identity: 'z', preparations: ['c'], features: {loop_nt: [6]}},
    ],
    families: [{identity: 'f', preparations: ['a', 'b']}, {identity: 'g', preparations: ['c']}],
  },
};

test('coincident products highlight every represented feature without changing eligibility', () => {
  const before = JSON.stringify(state);
  const focus = module.preparationIndex(state).focus( ['a', 'b', 'a']);
  assert.deepEqual(focus.preparations, ['a', 'b']);
  assert.deepEqual(focus.keys.sort(), ['foldback_arm_bp', 'loop_nt']);
  assert.deepEqual(focus.families, ['f']);
  assert.equal(focus.eligible, 1);
  assert.equal(JSON.stringify(state), before);
  assert.throws(() => module.preparationIndex(state).focus( ['absent']), /absent/i);
});

function mark(dataset) {
  const attributes = new Map();
  return {dataset, attributes,
    setAttribute: (key, value) => attributes.set(key, String(value)),
    removeAttribute: key => attributes.delete(key)};
}

test('linked focus preserves partial multiplicity, hollow marks and exact membership', () => {
  const marks = [
    mark({members: '["a","b"]'}),
    mark({preparations: '["b"]', selected: 'true'}),
    mark({familyIds: '["f"]'}),
    mark({members: '["c"]'}),
  ];
  const root = {querySelectorAll: () => marks, classList: {toggle: () => {}}};
  const marksIndex=module.linkedMarks(root,state.families);
  marksIndex.focus(module.preparationIndex(state).focus(['b']));
  assert.deepEqual(marks.map(m => m.attributes.get('data-linked-count')), ['1', '1', '1', undefined]);
  assert.equal(marks[0].attributes.get('data-linked-total'), '2');
  assert.equal(marks[2].attributes.get('data-linked-total'), '2');
  assert.equal(marks[1].dataset.selected, 'true');
  assert.ok(marks.every(m => !m.attributes.has('fill')));
  marksIndex.focus(null);
  assert.ok(marks.every(m => !m.attributes.has('data-linked-count')));
  marksIndex.close();
  assert.ok(marks.every(m => m.attributes.size === 0));
});

test('preparation highlighting does not register nucleotide-address ribbons as choice marks',()=>{
  const trace=mark({members:'["a","b"]'});
  const strand=mark({members:'[["strand",0],["strand",1]]',regionFill:'stem'});
  const root={querySelectorAll:()=>[trace,strand],classList:{toggle(){}}};
  const index=module.linkedMarks(root,state.families);
  index.focus(module.preparationIndex(state).focus(['a']));
  assert.equal(trace.attributes.get('data-choice-mark'),'true');
  assert.equal(trace.attributes.get('data-linked-count'),'1');
  assert.equal(strand.attributes.size,0,'molecular membership is base addresses, not preparation IDs');
  index.close();
  assert.equal(trace.attributes.size,0);
  assert.equal(strand.attributes.size,0);
});

test('an admitted index answers repeated focus without rescanning cohort arrays',()=>{
  const guarded={...state,choices:{paths:state.choices.paths}};
  const index=module.preparationIndex(guarded);
  Object.defineProperty(guarded.choices,'paths',{get(){throw Error('cohort rescanned');}});
  assert.deepEqual(index.focus(['b']).families,['f']);
  assert.equal(index.focus(['b']).eligible,0);
  assert.equal(index.rows(['a','a']).length,1);
  assert.throws(()=>index.focus(['absent']),/absent/);

});

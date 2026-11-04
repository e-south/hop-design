import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source = await readFile(new URL('../../src/hop_design/assets/survey_explorer/parameters.js', import.meta.url), 'utf8');
const { parameterKeys, highlightParameters, resolveParameterFocus } = await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
function element(dataset) {
  return {dataset, active: false, classList: {toggle(name, active) {this.owner.active=active;} }};
}
test('teaching groups retain every coupled parameter while axes retain a single key', () => {
  assert.deepEqual(parameterKeys({dataset:{teachingKeys:'["foldback_arm_bp","self_paired_arm_bp","join_offset_nt"]'}}), ['foldback_arm_bp','self_paired_arm_bp','join_offset_nt']);
  assert.deepEqual(parameterKeys({dataset:{parameter:'left_end_word'}}), ['left_end_word']);
  assert.deepEqual(parameterKeys({dataset:{parameterKeys:'["basal_method","basal_strand"]'}}), ['basal_method','basal_strand']);
  assert.deepEqual(parameterKeys({dataset:{}}), []);
});
test('one semantic focus links grouped glyph, molecular occurrence and axis without choosing or zooming', () => {
  const marks=[element({teachingKeys:'["loop_word","loop_nt"]'}),element({parameterKeys:'["loop_word"]'}),element({parameter:'loop_nt'}),element({parameter:'left_gap'})];
  for(const mark of marks) mark.classList.owner=mark;
  const root={querySelectorAll:()=>marks};
  highlightParameters(root,['loop_word','loop_nt']);
  assert.deepEqual(marks.map(x=>x.active),[true,true,true,false]);
  highlightParameters(root,['left_gap']);
  assert.deepEqual(marks.map(x=>x.active),[false,false,false,true]);
  highlightParameters(root,[]);
  assert.deepEqual(marks.map(x=>x.active),[false,false,false,false]);
});

test('an equivalent molecular measurement focuses its one canonical axis without rewriting a query', () => {
  const axes = [
    {key:'foldback_arm_bp', canonical_key:'foldback_arm_bp', equivalent_measurements:['loop_side_paired_bp']},
    {key:'loop_side_paired_bp', canonical_key:'foldback_arm_bp', equivalent_measurements:['foldback_arm_bp']},
    {key:'left_gap', canonical_key:'left_gap', equivalent_measurements:[]},
  ];
  const before = JSON.stringify(axes);
  const focused = resolveParameterFocus(axes, ['loop_side_paired_bp']);
  assert.deepEqual(focused.axes.map(a=>a.key), ['foldback_arm_bp']);
  assert.deepEqual(new Set(focused.keys), new Set(['foldback_arm_bp','loop_side_paired_bp']));
  assert.equal(JSON.stringify(axes), before);
  assert.deepEqual(resolveParameterFocus(axes,['unavailable']).axes, []);
});

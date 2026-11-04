import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const {preparationName} = await import('data:text/javascript;base64,' + Buffer.from(await readFile(
  new URL('../../src/hop_design/assets/variant_explorer/common.js', import.meta.url)
)).toString('base64'));

test('preparations with matching loops and methods expose their different measured geometry', () => {
  const state = {
    pool: {options: ['first', 'second'].map(label => ({label, loop_sequence:'GAAA'}))},
    choices: {
      preparations: ['first', 'second'].map(label => ({label, methods:[{name:'Nb.BtsI'}]})),
      choice_space: {
        axes: [{key:'foldback_arm_bp',symbol:'A',unit:'bp'}, {key:'join_offset_nt',symbol:'D',unit:'nt'}],
        paths: [{option_label:'first',values:{foldback_arm_bp:8,join_offset_nt:2}},
          {option_label:'second',values:{foldback_arm_bp:9,join_offset_nt:3}}],
      },
    },
  };
  assert.match(preparationName(state,'first'), /loop GAAA.*A 8 bp.*D 2 nt/);
  assert.match(preparationName(state,'second'), /loop GAAA.*A 9 bp.*D 3 nt/);
  assert.match(preparationName(state,'first'), /Nb\.BtsI.*first/);
  state.choices.choice_space.paths[0].values = {foldback_arm_bp:null,join_offset_nt:0};
  assert.match(preparationName(state,'first'), /D 0 nt/);
  assert.doesNotMatch(preparationName(state,'first'), /A (null|0|undefined)/);
});

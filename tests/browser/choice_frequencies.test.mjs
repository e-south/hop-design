// HOP Design
// hop-design/tests/browser/choice_frequencies.test.mjs
// Check exact preparation memberships and bounded frequency summaries.
// Module Author(s): Eric J. South
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../../src/hop_design/assets/design_explorer/choice_frequencies_model.js',import.meta.url),'utf8');
const {frequencyIndex}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const paths=[
 {materialized_realization_id:'a',matches:true,values:{loop_word:'AGCA',left_end_word:'GCAA',right_end_word:'AATG'},material_roles:{source_ssdna:{material_id:'source-a',length_nt:64}}},
 {materialized_realization_id:'b',matches:false,values:{loop_word:'AGCA',left_end_word:'GCAA',right_end_word:'AATG'},material_roles:{source_ssdna:{material_id:'source-b',length_nt:64}}},
 {materialized_realization_id:'c',matches:true,values:{loop_word:'GAAA',left_end_word:'AATG',right_end_word:'GCAA'},material_roles:{}},
];
const choices={axes:[{key:'loop_word',label:'Loop sequence'},{key:'left_end_word',label:'Left end'},{key:'right_end_word',label:'Right end'}],paths};
test('choice frequencies retain distinct preparation identities and left/right order',()=>{
 const before=JSON.stringify(choices),index=frequencyIndex(choices);
 const loops=index.profile('parameter:loop_word');assert.equal(loops.total,3);assert.equal(loops.choices,2);
 assert.deepEqual(loops.rows[0].members,['a','b']);assert.equal(loops.rows[0].eligible,1);
 const pairs=index.profile('assembly:end_pairs');assert.equal(pairs.choices,2);assert.equal(pairs.rows[0].count,2);
 const materials=index.profile('material:source_ssdna');assert.equal(materials.choices,3);assert.ok(materials.rows.some(r=>r.label==='Not applicable'));
 assert.equal(JSON.stringify(choices),before);assert.throws(()=>index.profile('unknown'),/Unknown/);
 assert.throws(()=>frequencyIndex({...choices,paths:[paths[0],paths[0]]}),/identity/);
});
test('bounded frequency profiles preserve every preparation in Other without double counting',()=>{
 const rows=Array.from({length:40},(_,i)=>({materialized_realization_id:`p${i}`,matches:i%2===0,values:{loop_word:`value-${i}`}}));
 const p=frequencyIndex({axes:choices.axes.slice(0,1),paths:rows}).profile('parameter:loop_word',8);
 assert.equal(p.rows.length,9);assert.equal(p.rows.at(-1).other,true);assert.equal(p.rows.at(-1).count,32);
 const ids=p.rows.flatMap(r=>r.members);assert.equal(ids.length,40);assert.equal(new Set(ids).size,40);
 assert.equal(p.rows.reduce((n,r)=>n+r.count,0),40);assert.equal(p.rows.reduce((n,r)=>n+r.eligible,0),20);
 assert.throws(()=>frequencyIndex({axes:[],paths:[]}).profile('parameter:loop_word'),/Unknown/);
});

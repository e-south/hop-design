import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/inspection_facts.js',import.meta.url))).toString('base64'));
const cost={materialized_realization_id:'B',endpoint:'clone_ready_duplex',added_nt_by_strand:{top:32,bottom:30},distinct_orders:5};
const explanation={materialized_realization_id:'B',reference_identity:'A',basis:'recorded_parameters',description:'Left gap: 0 → 2 bp',coordinate_changes:[]};
function host(){const fields=new Map(['reference','description','cost'].map(k=>[k,{textContent:'',title:''}]));return {dataset:{},fields,querySelector:s=>fields.get(s.match(/data-(\w+)/)[1])};}
test('cost names the measured product, and preview facts commit together with an explicit reference',async()=>{
 const {inspectionFacts}=await load(),node=host(),facts=inspectionFacts(node);
 const commit=facts.prepare('B',explanation,cost,{preview:true});
 assert.equal(node.fields.get('cost').textContent,'');commit();
 assert.equal(node.dataset.preparationId,'B');assert.equal(node.dataset.referenceId,'A');
 assert.equal(node.fields.get('reference').textContent,'From pinned: ');
 assert.equal(node.fields.get('description').textContent,explanation.description);
 assert.equal(node.fields.get('cost').textContent,'Released insert: added DNA — top 32 nt; bottom 30 nt. 5 distinct oligo orders.');
 facts.prepare('B',{...explanation,reference_identity:null,description:''},cost)();
 assert.equal(node.fields.get('reference').textContent,'');assert.equal(node.dataset.referenceId,'');
 assert.equal(node.fields.get('description').textContent,'');
 facts.clear();assert.equal(node.dataset.preparationId,undefined);
});

test('an opening inspection does not repeat unexplained parameter summaries',async()=>{
 const {inspectionFacts}=await load(),node=host();
 inspectionFacts(node).prepare('B',{...explanation,reference_identity:null,description:'Loop AAAG · 5 bp loop-side extension'},cost)();
 assert.equal(node.fields.get('description').textContent,'');
});
test('excluded but retained inspection remains an explicitly named reference',async()=>{
 const {inspectionFacts}=await load(),node=host();
 inspectionFacts(node).prepare('B',explanation,cost,{preview:true,referencePinned:false})();
 assert.equal(node.fields.get('reference').textContent,'From retained inspection: ');
 assert.equal(node.fields.get('reference').title,'A');
});
test('mismatched cost or comparison is rejected before replacing current molecular facts',async()=>{
 const {inspectionFacts}=await load(),node=host(),facts=inspectionFacts(node);
 facts.prepare('B',explanation,cost)();
 assert.throws(()=>facts.prepare('C',explanation,cost),/identity/);
 assert.throws(()=>facts.prepare('B',explanation,{...cost,materialized_realization_id:'C'}),/identity/);
 assert.equal(node.dataset.preparationId,'B');
 facts.prepare('B',explanation,null)();assert.equal(node.fields.get('cost').textContent,'');
});

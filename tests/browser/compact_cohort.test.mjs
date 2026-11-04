import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/cohort_state.js',import.meta.url))).toString('base64'));
const column=(dictionary,indices)=>({dictionary,indices});
function packet() {return {
  schema:'hop.inspection-cohort/v1',choices:{query:{parameters:[]}},members:['one','two'],matches:[true,false],
  values:{loop_word:column(['AAAA','AACA'],[0,1])},methods:column([[{name:'Nickase'}]],[0,0]),
  roles:{source:column([{material_id:'a',length_nt:70},{material_id:'b',length_nt:70}],[0,1])},
};}
test('compact rows retain exact words, eligibility and distinct material facts',async()=>{
  const {hydrateCohort}=await load();
  const decoded=hydrateCohort({cohort:'a',compact:packet(),families:null,map_index:{digest:'map'}},null);
  assert.deepEqual(decoded.choices.paths.map(p=>[p.materialized_realization_id,p.matches,p.values.loop_word,p.material_roles.source.material_id]),[['one',true,'AAAA','a'],['two',false,'AACA','b']]);
  assert.equal(decoded.choices.paths[1].methods[0].name,'Nickase');
  assert.equal(decoded.compact,undefined);
  const delta=hydrateCohort({cohort:'a',cohort_unchanged:true,token:'new'},decoded);
  assert.equal(delta.choices,decoded.choices);assert.equal(delta.map_index,decoded.map_index);
});
test('invalid compact references fail before an inspector can use them',async()=>{
  const {hydrateCohort}=await load();
  for(const change of [p=>p.members[1]='one',p=>p.matches.pop(),p=>p.values.loop_word.indices[1]=7,p=>p.methods.indices[0]=-1,p=>p.schema='unknown']) {
    const p=packet();change(p);assert.throws(()=>hydrateCohort({cohort:'a',compact:p},null),/cohort|column|member/i);
  }
});

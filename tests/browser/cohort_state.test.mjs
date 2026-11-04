import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/cohort_state.js',import.meta.url))).toString('base64'));
test('selection transport reuses only the matching admitted cohort',async()=>{
 const {hydrateCohort}=await load(),choices={paths:['one']},families={products:['product']};
 const feature_parameters=[{key:'loop_nt',operations:{filter:{available:true}}}];
 const previous={cohort:'a',choices,families,feature_parameters,token:'old'};
 const next=hydrateCohort({cohort:'a',cohort_unchanged:true,token:'new'},previous);
 assert.equal(next.choices,choices);assert.equal(next.families,families);assert.equal(next.token,'new');
 assert.equal(next.feature_parameters,feature_parameters);
 assert.equal(previous.token,'old');
 assert.throws(()=>hydrateCohort({cohort:'b',cohort_unchanged:true},previous),/cohort/i);
 assert.throws(()=>hydrateCohort({cohort:'a',cohort_unchanged:true},null),/cohort/i);
 const changed={cohort:'b',cohort_unchanged:false,choices:{paths:[]},families:{products:[]}};
 assert.equal(hydrateCohort(changed,previous),changed);
 const preview={materialized_realization_id:'one'};assert.equal(hydrateCohort(preview,previous),preview);
});

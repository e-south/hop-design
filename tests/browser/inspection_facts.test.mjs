import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/inspection_facts.js',import.meta.url))).toString('base64'));
const explanation={materialized_realization_id:'B',reference_identity:'A',description:'Left gap: 0 → 2 bp'};
const cost={materialized_realization_id:'B',added_nt_by_strand:{top:32,bottom:30}};

test('removing diagnostic UI preserves identity validation for hover and pin projections',async()=>{
  const {validateInspectionFacts:validate}=await load();
  assert.doesNotThrow(()=>validate('B',explanation,cost));
  assert.doesNotThrow(()=>validate('B',explanation,null));
  assert.doesNotThrow(()=>validate(null,null,null));
  assert.throws(()=>validate('C',explanation,cost),/identity/);
  assert.throws(()=>validate('B',explanation,{...cost,materialized_realization_id:'C'}),/identity/);
  assert.throws(()=>validate('B',null,cost),/identity/);
});

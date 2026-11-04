import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/molecular_colors.js',import.meta.url))).toString('base64'));
const axes=[{key:'left_gap',label:'Left end-to-stem gap',unit:'bp',kind:'numeric',stage:'released_insert'},{key:'right_gap',label:'Right end-to-stem gap',unit:'bp',kind:'numeric',stage:'released_insert'},{key:'loop_nt',label:'Loop size',unit:'nt',kind:'numeric',stage:'hairpin'},{key:'left_end_word',label:'Left sticky end',unit:'',kind:'categorical',stage:'released_insert'},{key:'right_end_word',label:'Right sticky end',unit:'',kind:'categorical',stage:'released_insert'}];
const paths=[
 {materialized_realization_id:'A',matches:true,values:{left_gap:0,right_gap:6,loop_nt:4,left_end_word:'AGTC',right_end_word:'AACC'}},
 {materialized_realization_id:'B',matches:true,values:{left_gap:6,right_gap:0,loop_nt:4,left_end_word:'AACC',right_end_word:'AGTC'}},
 {materialized_realization_id:'C',matches:false,values:{left_gap:12,right_gap:3,loop_nt:4,left_end_word:'AGTC',right_end_word:'AGTC'}},
 {materialized_realization_id:'D',matches:true,values:{loop_nt:4}},
];

test('numeric color is edition-bound, preserves zero and distinguishes absent measurements',async()=>{
 const {molecularColors}=await load(),before=structuredClone(paths);
 const lens=molecularColors(paths,axes,{key:'left_gap'});
 assert.equal(lens.label,axes[0].label);assert.equal(lens.unit,'bp');assert.equal(lens.stage,'released_insert');
 assert.deepEqual(lens.extent,[0,12]);assert.equal(lens.missing,1);
 assert.notEqual(lens.color(paths[0]),lens.color(paths[2]));assert.equal(lens.color(paths[3]),null);
 const filtered=molecularColors(paths.map(p=>({...p,matches:p.materialized_realization_id==='A'})),axes,{key:'left_gap'});
 assert.deepEqual(filtered.extent,[0,12]);for(const p of paths)assert.equal(filtered.color(p),lens.color(p));
 assert.deepEqual(paths,before,'Color cannot mutate constraints, eligibility or identities');
});

test('constant loop size is stated without suggesting molecular diversity',async()=>{
 const {molecularColors}=await load(),lens=molecularColors(paths,axes,{key:'loop_nt'});
 assert.equal(lens.constant,true);assert.deepEqual(lens.extent,[4,4]);assert.equal(lens.missing,0);
 assert.equal(new Set(paths.map(p=>lens.color(p))).size,1);
});

test('sticky-end highlights use exact words on the chosen side and retain all counts',async()=>{
 const {molecularColors}=await load(),left=molecularColors(paths,axes,{key:'left_end_word',word:'AGTC'}),right=molecularColors(paths,axes,{key:'right_end_word',word:'AGTC'});
 assert.equal(left.word,'AGTC');assert.deepEqual(left.values.map(x=>[x.value,x.total,x.eligible]),[['AACC',1,1],['AGTC',2,1]]);
 assert.notEqual(left.color(paths[0]),left.color(paths[1]));assert.equal(left.color(paths[0]),left.color(paths[2]));
 assert.notEqual(left.color(paths[0]),right.color(paths[0]));assert.equal(right.color(paths[1]),left.color(paths[0]));
 assert.equal(left.color(paths[3]),null);assert.throws(()=>molecularColors(paths,axes,{key:'left_end_word',word:'TTTT'}),/word|recorded/i);
});

test('unavailable and unknown lenses fail honestly',async()=>{
 const {molecularColors}=await load();
 const missing=molecularColors([paths[3]],axes,{key:'left_gap'});
 assert.equal(missing.missing,1);assert.deepEqual(missing.extent,null);assert.equal(missing.color(paths[3]),null);
 assert.throws(()=>molecularColors(paths,axes,{key:'arbitrary'}),/color|parameter/i);
 assert.throws(()=>molecularColors([{...paths[0],values:{left_gap:'6'}}],axes,{key:'left_gap'}),/numeric/i);
});

test('loop sequence and added pairing expose distinct molecular choices without changing membership',async()=>{
 const {molecularColors}=await load();
 const definitions=[...axes,{key:'loop_word',label:'Loop sequence',kind:'categorical',unit:'',stage:'hairpin'},
   {key:'foldback_arm_bp',label:'Loop-side extension',kind:'numeric',unit:'bp',stage:'hairpin'}];
 const rows=[
  {materialized_realization_id:'A',matches:true,values:{loop_word:'AAAC',foldback_arm_bp:3}},
  {materialized_realization_id:'B',matches:false,values:{loop_word:'AACA',foldback_arm_bp:5}},
 ];
 const before=structuredClone(rows);
 const word=molecularColors(rows,definitions,{key:'loop_word',word:'AACA'});
 assert.equal(word.label,'Loop sequence');assert.equal(word.word,'AACA');
 assert.deepEqual(word.values,[{value:'AAAC',total:1,eligible:1},{value:'AACA',total:1,eligible:0}]);
 assert.notEqual(word.color(rows[0]),word.color(rows[1]));
 const extent=molecularColors(rows,definitions,{key:'foldback_arm_bp'});
 assert.deepEqual(extent.extent,[3,5]);assert.equal(extent.unit,'bp');assert.equal(extent.stage,'hairpin');
 assert.deepEqual(rows,before);
});

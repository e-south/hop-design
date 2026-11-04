import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
const file=name=>readFile(new URL(`../../src/hop_design/assets/design_explorer/${name}.js`,import.meta.url),'utf8');
const load=async()=>import(uri((await file('route_scene_work')).replace("'./hover_preview.js'",JSON.stringify(uri(await file('hover_preview'))))));
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const context=id=>({identity:id,token:'view-1',snapshot:'pool-1'});
const response=job=>({materialized_realization_id:job.identity,token:job.token,snapshot_digest:job.snapshot,scenes:job.phases.map(phase=>({phase,state_id:`${job.identity}-${phase}`})),unavailable:[]});

test('visible scene work is bounded, lazy and rejects mismatched authority',async()=>{
 const {routeSceneWork}=await load(),calls=[],seen=[],failures=[];
 const work=routeSceneWork(async job=>{calls.push(job);return {...response(job),materialized_realization_id:'wrong'};},async value=>()=>seen.push(value),{failed:e=>failures.push(e.message)});
 await work.show(context('A'),[]);assert.equal(calls.length,0);
 assert.throws(()=>work.show(context('A'),['a','a']),/distinct/);
 await work.show(context('A'),['duplex']);
 assert.equal(seen.length,0);assert.match(failures[0],/preparation/);
 work.close();await work.show(context('B'),['duplex']);assert.equal(calls.length,1);
});

test('one visible viewport requests its scenes together without loading hidden phases',async()=>{
 const {routeSceneWork}=await load(),calls=[],seen=[];
 const phases=['source_ssdna','duplex','cleaved_duplex','annealed_complex','foldback_closed_hairpin','adapter_annealed','hairpin_pcr_duplex'];
 const work=routeSceneWork(async job=>{calls.push(job);return response(job);},async(value,job)=>()=>seen.push(job.phases));
 await work.show(context('A'),phases);
 assert.equal(calls.length,1);assert.deepEqual(calls[0].phases,phases);assert.deepEqual(seen,[phases]);
 work.close();
});

test('visible scenes coalesce and cannot commit after their context changes',async()=>{
 const {routeSceneWork}=await load(),slow=deferred(),calls=[],seen=[];
 const work=routeSceneWork(async job=>{calls.push(job.identity);if(job.identity==='A')await slow.promise;return response(job);},async value=>()=>seen.push(value.materialized_realization_id));
 const a=work.show(context('A'),['duplex']),b=work.show(context('B'),['duplex']),c=work.show(context('C'),['cleaved_duplex']);
 await b;assert.deepEqual(calls,['A']);slow.resolve();await Promise.all([a,c]);
 assert.deepEqual(calls,['A','C']);assert.deepEqual(seen,['C']);
 work.clear();work.close();
});

for(const field of ['token','snapshot_digest']) test(`scene ${field} must match the requesting context`,async()=>{
 const {routeSceneWork}=await load(),seen=[],errors=[];
 const work=routeSceneWork(async job=>({...response(job),[field]:'old'}),async value=>()=>seen.push(value),{failed:e=>errors.push(e.message)});
 await work.show(context('A'),['duplex']);assert.equal(seen.length,0);assert.match(errors[0],/context/);work.close();
});

test('every requested phase is explicitly present or unavailable',async()=>{
 const {routeSceneWork}=await load(),errors=[];
 const work=routeSceneWork(async job=>({...response(job),scenes:[]}),async()=>()=>assert.fail('Incomplete route response cannot commit'),{failed:e=>errors.push(e.message)});
 await work.show(context('A'),['duplex']);assert.match(errors[0],/phase/);work.close();
});

test('a shared preview prepares scenes without another request and validates context before commit',async()=>{
 const {routeSceneWork}=await load(),seen=[];
 const work=routeSceneWork(async()=>assert.fail('Already rendered in the preview request'),async(value,job)=>()=>seen.push(job.identity));
 const job={...context('A'),phases:['duplex']};
 const commit=await work.prepareResponse(response(job),job);
 assert.deepEqual(seen,[]);commit();assert.deepEqual(seen,['A']);
 for(const changed of [{materialized_realization_id:'B'},{token:'old'},{snapshot_digest:'old'},{scenes:[]}])
  await assert.rejects(work.prepareResponse({...response(job),...changed},job),/preparation|context|phase/);
 work.close();
});

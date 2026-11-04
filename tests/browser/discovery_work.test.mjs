import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/discovery.js',import.meta.url))).toString('base64'));
class Element {
  hidden=false;disabled=false;value='';textContent='';listeners={};
  addEventListener(name,fn){this.listeners[name]=fn;}
  removeEventListener(name){delete this.listeners[name];}
}
function fixture(){
  const ids=['discovery-request','discovery-evaluations','discovery-start','discovery-continue','discovery-stop','discovery-status','discovery-progress','discovery-result','discovery-command','discovery-inspect'];
  const elements=new Map(ids.map(id=>[id,new Element()]));elements.get('discovery-evaluations').value='4';
  return {get:id=>{assert.ok(elements.has(id),`Discovery touched unrelated inspector node ${id}`);return elements.get(id);},elements};
}
const initial={discovery_request:{stem_arm:'ACGT',product:'hairpin'},discovery_work:null};
const active={id:'one',status:'running',progress:null,can_continue:false,command:null};

test('search is explicit and polling changes only its own controls',async()=>{
  const {discoveryControls}=await load(),{get}=fixture(),calls=[],timers=[];
  const panel=discoveryControls(get,async(action,payload)=>{
    calls.push({action,payload});
    if(action==='start-discovery')return active;
    return {...active,status:'cancelled',can_continue:true,progress:{new_evaluations:1,evaluation_budget:4},command:'hop-design design continue saved'};
  },{schedule:fn=>{timers.push(fn);return timers.length;},cancel:()=>{}});
  panel.update(initial);assert.equal(calls.length,0);
  await get('discovery-start').listeners.click();
  assert.deepEqual(calls[0],{action:'start-discovery',payload:{request:initial.discovery_request,evaluations:4}});
  assert.equal(get('discovery-start').disabled,true);
  await timers.shift()();
  assert.match(get('discovery-status').textContent,/Stopped/);
  assert.equal(get('discovery-continue').hidden,false);
  assert.match(get('discovery-command').textContent,/design continue/);
  panel.close();
});

test('stop is explicit and a late poll cannot overwrite the stopping state',async()=>{
  const {discoveryControls}=await load(),{get}=fixture(),timers=[],calls=[];let finish;
  const panel=discoveryControls(get,(action,payload)=>{
    calls.push({action,payload});
    if(action==='status-discovery')return new Promise(done=>{finish=done;});
    return Promise.resolve({...active,status:'stopping'});
  },{schedule:fn=>{timers.push(fn);return timers.length;},cancel:()=>{}});
  panel.update({...initial,discovery_work:active});
  const polling=timers.shift()();await get('discovery-stop').listeners.click();
  finish(active);await polling;
  assert.match(get('discovery-status').textContent,/Stopping/);
  assert.equal(calls[1].payload.job_id,'one');
  panel.close();
});

test('closing stops owned work without applying a late response',async()=>{
  const {discoveryControls}=await load(),{get}=fixture(),timers=[],calls=[];let finish;
  const panel=discoveryControls(get,(action,payload)=>{
    calls.push({action,payload});
    return action==='status-discovery'?new Promise(done=>{finish=done;}):Promise.resolve({...active,status:'stopping'});
  },{schedule:fn=>{timers.push(fn);return timers.length;},cancel:()=>{}});
  panel.update({...initial,discovery_work:active});const polling=timers.shift()();
  panel.close();const text=get('discovery-status').textContent;
  finish({...active,status:'completed',matching_preparations:100});await polling;
  assert.equal(get('discovery-status').textContent,text);
  assert.equal(calls.at(-1).action,'stop-discovery');
});


test('finished nonempty results open only through an explicit inspection action',async()=>{
  const {discoveryControls}=await load(),{get}=fixture(),calls=[];let finish;
  const result={...active,status:'completed',matching_preparations:2,can_continue:true};
  const panel=discoveryControls(get,async()=>{throw Error('Inspection must use the coherent action owner');},{
    inspect:id=>{calls.push(id);return new Promise(done=>{finish=done;});},
  });
  panel.update({...initial,discovery_work:result});
  assert.deepEqual(calls,[]);assert.equal(get('discovery-inspect').hidden,false);
  const opening=get('discovery-inspect').listeners.click();
  assert.deepEqual(calls,['one']);assert.equal(get('discovery-start').disabled,true);
  assert.equal(get('discovery-continue').disabled,true);assert.equal(get('discovery-inspect').disabled,true);
  finish(true);await opening;assert.equal(get('discovery-inspect').disabled,false);
  panel.close();
});

test('running, empty and zero-snapshot results cannot replace the inspector',async()=>{
  const {discoveryControls}=await load();
  for(const result of [active,{...active,status:'completed',matching_preparations:0},{...active,status:'cancelled',matching_preparations:null},{...active,status:'failed',matching_preparations:2}]){
    const {get}=fixture(),calls=[];
    const panel=discoveryControls(get,async()=>active,{inspect:id=>calls.push(id),schedule:()=>0,cancel:()=>{}});
    panel.update({...initial,discovery_work:result});assert.equal(get('discovery-inspect').hidden,true);
    await get('discovery-inspect').listeners.click();assert.deepEqual(calls,[]);panel.close();
  }
});

test('failed result admission leaves retry and continuation available',async()=>{
  const {discoveryControls}=await load(),{get}=fixture();
  const panel=discoveryControls(get,async()=>{}, {inspect:async()=>{throw Error('Admission failed');}});
  panel.update({...initial,discovery_work:{...active,status:'completed',matching_preparations:2,can_continue:true}});
  await get('discovery-inspect').listeners.click();
  assert.match(get('discovery-status').textContent,/Admission failed/);
  assert.equal(get('discovery-inspect').disabled,false);assert.equal(get('discovery-continue').disabled,false);
  panel.close();
});

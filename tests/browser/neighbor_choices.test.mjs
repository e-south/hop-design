import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/neighbors.js',import.meta.url))).toString('base64'));
class Element {
  open=false;children=[];listeners={};textContent='';
  addEventListener(name,fn){this.listeners[name]=fn;}
  removeEventListener(name){delete this.listeners[name];}
  replaceChildren(...children){this.children=children;}
  append(...children){this.children.push(...children);}
}
const answer={neighbors:[{materialized_realization_id:'candidate',description:'Loop AAAA → AAAC',coordinate_changes:[{key:'loop_word'}]}]};

test('nearby ranking is separate from deliberate verification and exact selection',async()=>{
  const previous=globalThis.document;globalThis.document={createElement:()=>new Element()};
  try {
    const {neighboringChoices}=await load(),details=new Element(),host=new Element(),calls=[],selected=[];
    const state={token:'current',has_landscape:true,plots:{}};
    const nearby=neighboringChoices(details,host,async(action,payload)=>{calls.push({action,payload});return answer;},()=>state,id=>selected.push(id));
    details.open=true;await details.listeners.toggle();
    assert.equal(calls[0].payload.verify_controls,false);
    assert.equal(host.children[1].textContent,'Check shared surroundings');
    await host.children[1].listeners.click();
    assert.equal(calls[1].payload.verify_controls,true);
    assert.equal(host.children.length,1);
    host.children[0].listeners.click();assert.deepEqual(selected,['candidate']);
    nearby.close();assert.equal(details.open,false);
  } finally {globalThis.document=previous;}
});

test('closing cancels the exact pending request and discards its late result',async()=>{
  const {neighboringChoices}=await load(),details=new Element(),host=new Element(),calls=[];
  let resolve;
  const waiting=new Promise(done=>{resolve=done;});
  const nearby=neighboringChoices(details,host,(action,payload)=>{
    calls.push({action,payload});return action==='neighbors'?waiting:Promise.resolve({status:'cancelled'});
  },()=>({token:'current',has_landscape:true,plots:{}}),()=>{});
  details.open=true;const pending=details.listeners.toggle();nearby.clear();
  assert.equal(calls[1].action,'cancel-neighbors');
  assert.equal(calls[1].payload.request_id,calls[0].payload.request_id);
  resolve(answer);await pending;
  assert.deepEqual(host.children,[]);
  nearby.close();
});

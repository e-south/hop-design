// HOP Design
// hop-design/tests/browser/saved_view_file.test.mjs
// Exercise saved-view file handlers with native same-file change suppression.
// Module Author(s): Eric J. South
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';

const editor=await readFile(new URL('../../src/hop_design/assets/design_explorer/editor.js',import.meta.url),'utf8');
// Execute the actual adjacent registrations without booting unrelated map/render UI.
const handlers=editor.slice(editor.indexOf("$('open-view').addEventListener"),editor.indexOf('async function restoreHash'));
function picker(act) {
 const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,{handlers:new Map(),addEventListener(name,fn){this.handlers.set(name,fn);},textContent:''});return nodes.get(id);};
 const file=node('view-file');let value='';file.files=[];file.click=()=>{};
 Object.defineProperty(file,'value',{get:()=>value,set(next){value=next;if(!next)file.files=[];}});
 runInNewContext(handlers,{$:node,act});
 return {status:node('status'),async choose(selected) {
  node('open-view').handlers.get('click')();
  if(!selected)return; // Cancelling the native picker emits no change event.
  const next=`C:\\fakepath\\${selected.name}`;
  if(file.value===next)return; // Native inputs suppress change for the same selection.
  file.value=next;file.files=[selected];await file.handlers.get('change')();
 }};
}
const saved=(text='{"schema":"saved-view"}')=>({name:'hop-view.json',text:async()=>text});

test('opening the identical saved view twice restores twice; cancelling preserves the current view',async()=>{
 const calls=[],ui=picker(async(...args)=>calls.push(args)),file=saved();
 await ui.choose(file);assert.equal(calls.length,1);
 await ui.choose(null);assert.equal(calls.length,1,'cancel must not restore or clear the current view');
 await ui.choose(file);assert.equal(calls.length,2,'choosing the same file again must restore again');
 for(const [action,payload,history]of calls){assert.equal(action,'restore');assert.equal(payload.receipt.schema,'saved-view');assert.equal(history,false);}
});

test('a malformed saved view can be corrected and reopened using the same filename',async()=>{
 const calls=[],ui=picker(async(...args)=>calls.push(args));
 await ui.choose(saved('{'));assert.equal(calls.length,0);assert.ok(ui.status.textContent);
 await ui.choose(saved());assert.equal(calls.length,1,'parse failure must not suppress same-file retry');
});

test('a failed restore can retry the identical file after cancel',async()=>{
 let attempts=0;const ui=picker(async()=>{if(++attempts===1)throw Error('Restore unavailable');}),file=saved();
 await ui.choose(file);assert.equal(ui.status.textContent,'Restore unavailable');
 await ui.choose(null);assert.equal(attempts,1);
 await ui.choose(file);assert.equal(attempts,2,'restore failure must not suppress same-file retry');
});

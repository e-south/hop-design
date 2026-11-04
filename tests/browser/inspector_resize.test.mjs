import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../../src/hop_design/assets/design_explorer/inspector_resize.js',import.meta.url),'utf8');
const {resizableInspector}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));

class Element {
 constructor(){this.events=new Map();this.attributes=new Map();this.dataset={};this.hidden=false;this.properties=new Map();this.style={setProperty:(k,v)=>this.properties.set(k,v),removeProperty:k=>this.properties.delete(k)};}
 addEventListener(k,v){this.events.set(k,v);} removeEventListener(k){this.events.delete(k);}
 setAttribute(k,v){this.attributes.set(k,String(v));} removeAttribute(k){this.attributes.delete(k);}
 setPointerCapture(id){this.pointer=id;} releasePointerCapture(){this.pointer=null;} hasPointerCapture(id){return this.pointer===id;}
 emit(k,v={}){this.events.get(k)?.({preventDefault(){},stopPropagation(){},...v});}
}
function setup(t) {
 const original={ResizeObserver,MutationObserver,requestAnimationFrame,cancelAnimationFrame};
 t.after(()=>Object.assign(globalThis,original));
 const watchers=[],frames=new Map();let serial=0;
 globalThis.ResizeObserver=globalThis.MutationObserver=class {constructor(fn){this.fn=fn;this.active=true;watchers.push(this);}observe(){}disconnect(){this.active=false;}};
 globalThis.requestAnimationFrame=fn=>{frames.set(++serial,fn);return serial;};globalThis.cancelAnimationFrame=id=>frames.delete(id);
 const surface=new Element(),inspector=new Element(),scroll=new Element(),handle=new Element();
 surface.clientWidth=1100;inspector.dataset.hasPin='true';scroll.scrollTop=500;
 inspector.getBoundingClientRect=()=>({width:parseFloat(surface.properties.get('--inspector-width')||440)});
 scroll.getBoundingClientRect=()=>({top:0,bottom:700});
 // A route scene below a width-dependent teaching plate; keep this scene in place.
 const scene={getBoundingClientRect:()=>({top:inspector.getBoundingClientRect().width-scroll.scrollTop,bottom:inspector.getBoundingClientRect().width-scroll.scrollTop+300})};
 scroll.querySelectorAll=()=>[scene];
 let changes=0,begins=0;
 const control=resizableInspector(surface,inspector,scroll,handle,()=>changes++,()=>begins++);
 const flush=()=>{const jobs=[...frames.values()];frames.clear();jobs.forEach(fn=>fn());};
 return {surface,inspector,scroll,handle,control,flush,watchers,frames,changes:()=>changes,begins:()=>begins};
}
// The controller uses native observers in the browser, not a persistent render loop.
for(const key of ['ResizeObserver','MutationObserver','requestAnimationFrame','cancelAnimationFrame'])if(!(key in globalThis))globalThis[key]=undefined;

test('dragging bounds inspector width, batches layout and preserves the visible scene',t=>{
 const x=setup(t),before=x.scroll.scrollTop;
 x.handle.emit('pointerdown',{button:0,pointerId:1,clientX:660});
 x.handle.emit('pointermove',{pointerId:1,clientX:500});x.handle.emit('pointermove',{pointerId:1,clientX:450});
 assert.equal(x.surface.properties.size,0,'No per-event layout before the animation frame');
 x.flush();assert.equal(x.surface.properties.get('--inspector-width'),'650px');assert.equal(x.scroll.scrollTop,before+210);
 assert.equal(x.changes(),1);assert.equal(x.begins(),1);
 x.handle.emit('pointermove',{pointerId:1,clientX:0});x.flush();assert.equal(x.surface.properties.get('--inspector-width'),'760px');
 x.handle.emit('pointerup',{pointerId:1});assert.equal(x.handle.pointer,null);
 x.control.close();assert.ok(x.watchers.every(w=>!w.active));assert.equal(x.handle.events.size,0);
});

test('keyboard, focus disclosure and viewport constraints are local and accessible',t=>{
 const x=setup(t);assert.equal(x.handle.hidden,false);assert.equal(x.handle.attributes.get('aria-valuenow'),'440');
 x.handle.emit('keydown',{key:'ArrowLeft'});x.flush();assert.equal(x.surface.properties.get('--inspector-width'),'464px');
 x.handle.emit('keydown',{key:'Home'});x.flush();assert.equal(x.surface.properties.get('--inspector-width'),'440px');
 x.handle.emit('keydown',{key:'End'});x.flush();assert.equal(x.surface.properties.get('--inspector-width'),'760px');
 x.inspector.dataset.focus='figure-one';x.watchers.forEach(w=>w.fn());assert.equal(x.handle.hidden,true);
 delete x.inspector.dataset.focus;x.surface.clientWidth=800;x.watchers.forEach(w=>w.fn());x.flush();assert.equal(x.surface.properties.get('--inspector-width'),'480px');
 x.surface.clientWidth=600;x.watchers.forEach(w=>w.fn());assert.equal(x.handle.hidden,true);assert.equal(x.surface.properties.has('--inspector-width'),false);
 x.surface.clientWidth=1100;x.watchers.forEach(w=>w.fn());x.flush();assert.equal(x.surface.properties.get('--inspector-width'),'760px','Restore the chosen width when space returns');
 x.control.close();assert.equal(x.frames.size,0);
});

test('unexpected pointer-capture loss releases the old drag anchor',t=>{
 const x=setup(t);
 x.handle.emit('pointerdown',{button:0,pointerId:3,clientX:660});
 x.handle.emit('pointermove',{pointerId:3,clientX:600});
 x.handle.emit('lostpointercapture',{pointerId:3});x.flush();
 const width=x.surface.properties.get('--inspector-width');
 x.handle.emit('pointermove',{pointerId:3,clientX:100});x.flush();
 assert.equal(x.surface.properties.get('--inspector-width'),width);assert.equal(x.handle.dataset.resizing,undefined);x.control.close();
});

test('a closed inspector can preview without exposing a docked resize handle',t=>{
 const x=setup(t);
 x.inspector.dataset.dismissed='true';x.inspector.dataset.transient='true';
 x.watchers.forEach(w=>w.fn());assert.equal(x.handle.hidden,true);
 delete x.inspector.dataset.dismissed;delete x.inspector.dataset.transient;
 x.watchers.forEach(w=>w.fn());assert.equal(x.handle.hidden,false);
 x.inspector.dataset.transient='true';x.watchers.forEach(w=>w.fn());
 assert.equal(x.handle.hidden,false,'Preview over an already docked inspector keeps its layout');
 x.control.close();
});

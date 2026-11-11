import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
const source=name=>readFile(new URL(`../../src/hop_design/assets/design_explorer/${name}.js`,import.meta.url),'utf8');
test('failed bundled preview gives its visible route a terminal error; obsolete failures cannot replace a newer loading state',async t=>{
 let scenes;const names=['document','IntersectionObserver','requestAnimationFrame','cancelAnimationFrame'],saved=Object.fromEntries(names.map(n=>[n,globalThis[n]]));t.after(()=>{scenes?.close();Object.assign(globalThis,saved);});
 const frames=new Map();let serial=0,requests=0;
 globalThis.requestAnimationFrame=fn=>{frames.set(++serial,fn);return serial;};globalThis.cancelAnimationFrame=id=>frames.delete(id);
 globalThis.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
 function element(){const attrs=new Map();return{children:[],dataset:{},style:{},inert:false,
  get firstElementChild(){return this.children[0]??null;},getClientRects:()=>[{}],closest:()=>null,getBoundingClientRect:()=>({top:0,bottom:300}),
  setAttribute:(k,v)=>attrs.set(k,String(v)),getAttribute:k=>attrs.get(k),removeAttribute:k=>attrs.delete(k),
  append(...children){for(const child of children){if(child.parent)child.parent.children=child.parent.children.filter(c=>c!==child);child.parent=this;this.children.push(child);}},
  replaceChildren(...children){this.children=[];this.append(...children);},remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);},before(){},addEventListener(){},removeEventListener(){}};}
 globalThis.document={createElement:element};
 let work=await source('route_scene_work');work=work.replace("'./hover_preview.js'",JSON.stringify(uri(await source('hover_preview'))));
 let text=await source('route_scenes');text=text.replace("'./route_scene_work.js'",JSON.stringify(uri(work))).replace("'./panel_status.js'",JSON.stringify(uri(await source('panel_status'))));
 const {routeScenes}=await import(uri(text)),host=element(),scroll=element(),progress=element();
 scenes=routeScenes(host,scroll,async()=>{requests++;throw Error('No independent request is needed for this failed bundle');},{},progress);
 const state={token:'token',choices:{snapshot_digest:'snapshot'},render_policy:'current',presentation:{route:'assembly'},stage_options:[{value:'released-state',label:'Released insert'}],preview:{summary:{atlas:{materialized_realization_id:'A',states:[{state:{state_id:'released-state',phase:'clone_ready_duplex'}}]}}}};
 scenes.pin(state);
 const slot=host.children[0],body=slot.children[0],previous=element();previous.dataset.preparationId='A';body.append(previous);
 assert.equal(slot.getAttribute('aria-label'),'Released insert');
 assert.throws(()=>scenes.pin({...state,stage_options:[]}),/label/i,'Missing labels must fail before replacing the route');
 assert.equal(host.children[0],slot);
 scenes.pending('B');assert.equal(slot.dataset.panelState,'waiting');assert.equal(slot.dataset.panelRetained,'previous');
 assert.equal(slot.dataset.panelFeedback,'quiet');assert.equal(progress.textContent,'Updating…');
 assert.equal(progress.dataset.busy,'true');
 host.getClientRects=()=>[];scenes.refresh();
 for(const [id,fn] of frames){frames.delete(id);fn();}
 assert.equal(progress.textContent,'','Offscreen waiting steps must not imply ongoing work');
 host.getClientRects=()=>[{}];scenes.refresh();
 for(const [id,fn] of frames){frames.delete(id);fn();}
 assert.equal(progress.textContent,'Updating…');
 scenes.previewFailed?.('B');assert.equal(slot.dataset.panelState,'error','The route must not remain Preparing after the shared preview fails');
 assert.equal(slot.getAttribute('aria-busy'),'false');assert.equal(body.firstElementChild,previous);assert.equal(requests,0);
 assert.equal(progress.textContent,'');assert.equal(progress.dataset.busy,undefined);
 scenes.pending('C');scenes.previewFailed('B');assert.equal(slot.dataset.panelState,'waiting');assert.equal(slot.dataset.pendingIdentity,'C');
 scenes.previewFailed('C');assert.equal(slot.dataset.panelState,'error');assert.equal(requests,0);
 scenes.close();assert.equal(frames.size,0);assert.equal(host.children.length,0);
 assert.equal(progress.textContent,'');
});

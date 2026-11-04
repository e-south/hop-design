import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
const file=name=>readFile(new URL(`../../src/hop_design/assets/design_explorer/${name}.js`,import.meta.url),'utf8');
function element(){return {children:[],dataset:{},attributes:new Map(),querySelector(){return null;},append(...items){this.children.push(...items);},before(item){this.announcement=item;},setAttribute(k,v){this.attributes.set(k,v);},removeAttribute(k){this.attributes.delete(k);},remove(){}};}

test('leaving a point cannot uncover panels while a pin is still loading',async t=>{
  const old=globalThis.document;t.after(()=>{globalThis.document=old;});globalThis.document={createElement:element};
  const module=(await file('inspection_loading')).replace("'./panel_status.js'",JSON.stringify(uri(await file('panel_status'))));
  const {inspectionLoading}=await import(uri(module)),hosts=new Map();
  const get=id=>{if(!hosts.has(id))hosts.set(id,element());return hosts.get(id);};
  const loading=inspectionLoading(get);
  loading.pending('A');loading.ready('A');
  assert.equal(get('route-focus').dataset.panelState,'waiting','No spinner implies a route request that has not started');
  loading.clear();loading.beginAction('select',{materialized_realization_id:'B'});loading.clear();
  assert.equal(get('figure-one-canvas').dataset.panelState,'loading');
  assert.equal(get('preparation-info').dataset.pendingIdentity,'B');
  loading.failedAction();assert.equal(get('figure-one-canvas').dataset.panelState,'error');
  loading.beginAction('retry');loading.readyAction();assert.equal(get('figure-one-canvas').dataset.panelState,undefined);
  const opening=loading.opening();opening.fail('Could not open');
  loading.beginAction('retry');loading.readyAction();
  assert.equal(get('landscape-panels').dataset.panelState,undefined,'Successful initial drawing retry uncovers the map');
  loading.beginAction('retrieve');assert.equal(get('figure-one-canvas').dataset.panelState,undefined);
  assert.equal(get('preparation-info').dataset.panelState,'loading');loading.readyAction();loading.close();
});

test('opening discovery results keeps the old atlas visibly pending until commit',async t=>{
  const old=globalThis.document;t.after(()=>{globalThis.document=old;});globalThis.document={createElement:element};
  const module=(await file('inspection_loading')).replace("'./panel_status.js'",JSON.stringify(uri(await file('panel_status'))));
  const {inspectionLoading}=await import(uri(module)),hosts=new Map();
  const get=id=>{if(!hosts.has(id))hosts.set(id,element());return hosts.get(id);};
  const drawing=element();get('landscape-panels').append(drawing);get('plot').querySelector=()=>drawing;
  const loading=inspectionLoading(get);loading.beginAction('inspect-discovery');
  assert.equal(get('landscape-panels').dataset.panelState,'loading');
  assert.equal(get('landscape-panels').dataset.panelRetained,'previous');
  assert.equal(drawing.inert,true);
  loading.readyAction();assert.equal(get('landscape-panels').dataset.panelState,undefined);
  assert.equal(drawing.inert,undefined);loading.close();
});

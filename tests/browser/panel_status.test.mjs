import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/panel_status.js',import.meta.url))).toString('base64'));
function element(){return {dataset:{},children:[],attributes:new Map(),append(...items){this.children.push(...items);},before(item){this.announcement=item;},setAttribute(k,v){this.attributes.set(k,v);},removeAttribute(k){this.attributes.delete(k);},getAttribute(k){return this.attributes.get(k)??null;},remove(){this.removed=true;}};}

test('local loading preserves contents, blocks stale interaction and rejects obsolete completion',async t=>{
  const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
  globalThis.document={createElement:element};
  const {panelStatus}=await load(),host=element(),content=element();content.inert=false;host.append(content);
  const panel=panelStatus(host),first=panel.begin('Preparing hairpin…','A');
  assert.equal(host.getAttribute('aria-busy'),'true');assert.equal(content.inert,true);
  assert.equal(host.announcement?.getAttribute('role'),'status','Announcement lives outside the busy subtree');
  assert.equal(host.announcement?.textContent,'Preparing hairpin…');
  assert.equal(host.dataset.pendingIdentity,'A');assert.equal(host.children[0],content);
  const next=panel.begin('Preparing hairpin…','B');first.ready();
  assert.equal(host.dataset.pendingIdentity,'B');assert.equal(host.getAttribute('aria-busy'),'true');
  next.fail('Could not load this hairpin.');
  assert.equal(host.dataset.panelState,'error');assert.equal(host.getAttribute('aria-busy'),'false');
  assert.equal(content.inert,true,'Failed preparation must not expose old data as current');
  panel.clear();assert.equal(content.inert,false);assert.equal(host.dataset.panelState,undefined);
  assert.equal(host.getAttribute('aria-busy'),null);next.fail('late');assert.equal(host.dataset.panelState,undefined);
});

test('panel status releases detached content and preserves an existing inert boundary',async t=>{
  const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});globalThis.document={createElement:element};
  const {panelStatus}=await load(),host=element(),content=element();content.inert=true;host.append(content);
  const panel=panelStatus(host);panel.begin('Loading');panel.clear();assert.equal(content.inert,true);
  panel.close();assert.equal(host.children.at(-1).removed,true);assert.equal(host.dataset.panelState,undefined);
});

test('a previous drawing remains identified and inert until the matching replacement is ready',async t=>{
  const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});globalThis.document={createElement:element};
  const {panelStatus}=await load(),host=element(),drawing=element();drawing.inert=false;host.append(drawing);
  let hasDrawing=false;
  const panel=panelStatus(host,{retainPrevious:()=>hasDrawing});
  panel.begin('Loading next preparation…','A');assert.equal(host.dataset.panelRetained,undefined,'An empty first load has no prior drawing');
  panel.clear();hasDrawing=true;
  const first=panel.begin('Loading next preparation…','B');
  assert.equal(host.dataset.panelRetained,'previous');assert.equal(drawing.inert,true);
  assert.equal(host.announcement.textContent,'Previous preparation · Loading next preparation…');
  assert.equal(host.children[0],drawing,'Reuse the existing drawing without a clone');
  const next=panel.begin('Loading next preparation…','C');first.ready();
  assert.equal(host.dataset.pendingIdentity,'C');assert.equal(host.dataset.panelRetained,'previous');
  next.idle('Waiting for matching scene…');assert.equal(host.dataset.panelRetained,'previous');
  next.fail('Preview unavailable.');assert.equal(host.dataset.panelRetained,undefined,'An error must not look like a completed replacement');
  assert.equal(drawing.inert,true);assert.equal(host.announcement.textContent,'Preview unavailable.');
  panel.begin('Loading next preparation…','D').ready();
  assert.equal(host.dataset.panelRetained,undefined);assert.equal(drawing.inert,false);
  panel.close();assert.equal(host.children.at(-1).removed,true);
});

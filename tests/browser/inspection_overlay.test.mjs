import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/inspection_overlay.js',import.meta.url))).toString('base64'));
const trace={projection:'geometry-one',frame:'0 0 1200 330',materialized_realization_id:'a',eligible:false,path:'M0 1 L20 3',values:[{key:'left_end_word',label:'Left sticky end',value:'AGTC',display:'AGTC',unit:'',x:0,y:1}]};

test('only an exact projection match can decorate a mounted parameter scene',async()=>{
  const {validateOverlay}=await load();
  assert.equal(validateOverlay(trace,{projection:'geometry-one',frame:'0 0 1200 330'}),trace);
  assert.throws(()=>validateOverlay(trace,{projection:'geometry-two',frame:trace.frame}),/projection/i);
  assert.throws(()=>validateOverlay({...trace,frame:'0 0 100 330'},{projection:'geometry-one',frame:trace.frame}),/projection/i);
  assert.equal(trace.eligible,false);assert.equal(trace.values[0].display,'AGTC');
});

test('transient inspection preserves scroll while dependent panels are masked',async()=>{
  const {transientInspector}=await load();
  const inspector={dataset:{focus:'figure-two'}},scroll={scrollTop:410};
  const preview=transientInspector(inspector,scroll);
  preview.show();assert.equal(inspector.dataset.transient,'true');assert.equal(scroll.scrollTop,410);
  scroll.scrollTop=25;preview.show();assert.equal(scroll.scrollTop,25);
  preview.clear();assert.equal(inspector.dataset.transient,undefined);assert.equal(scroll.scrollTop,25);
  assert.equal(inspector.dataset.focus,'figure-two','Pinned focus mode is untouched');
  scroll.scrollTop=320;preview.clear();assert.equal(scroll.scrollTop,320,'Repeated blur/clear cannot overwrite restored scroll');
});

test('Escape restores a transient preview before closing the inspector or leaving figure focus',async()=>{
  const {escapeInspection}=await load(),events=[];
  const inspector={dataset:{transient:'true',focus:'figure-two'}};
  const actions={restorePreview:()=>events.push('restore'),returnToMap:()=>events.push('map'),close:()=>events.push('close')};
  escapeInspection(inspector,actions);assert.deepEqual(events,['restore']);
  delete inspector.dataset.transient;escapeInspection(inspector,actions);assert.deepEqual(events,['restore','map']);
  delete inspector.dataset.focus;escapeInspection(inspector,actions);assert.deepEqual(events,['restore','map','close']);
});

function element(name, attrs={}) {
  const node={localName:name,attributes:{...attrs},children:[],dataset:{},parent:null,
    getAttribute(k){return this.attributes[k]??null;},
    setAttribute(k,v){this.attributes[k]=String(v);},removeAttribute(k){delete this.attributes[k];},
    append(...children){for(const child of children){child.parent=this;this.children.push(child);}},
    insertBefore(child,before){child.parent=this;this.children.splice(this.children.indexOf(before),0,child);},
    remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);},
    querySelectorAll(selector){
      const key=selector.slice(1,-1),found=[];
      const visit=n=>{for(const c of n.children){if(c.getAttribute(key)!==null)found.push(c);visit(c);}};
      visit(this);return found;
    }};
  return node;
}

function labelFixture(t) {
  const original=globalThis.document;t.after(()=>{globalThis.document=original;});
  globalThis.document={createElementNS:(_,name)=>element(name)};
  const svg=element('svg',{'font-size':'22'}),nodes=[];
  for(const [word,y] of [['AAAA',140],['AACA',180],['GGGG',240]]){
    const node=element('g',{'data-node-value':word,tabindex:'0',role:'button'});
    const mark=element('line',{'data-node-mark':'true'});
    const box=element('rect',{'data-node-label':'true',x:'70',y:String(y-13),width:'60',height:'26'});
    const text=element('text',{'data-node-label':'true'});text.textContent=word;
    node.append(mark,box,text);svg.append(node);nodes.push({node,mark,box,text});
  }
  let mounted=svg;
  return {svg,nodes,host:{querySelector:()=>mounted},replace:()=>{mounted=element('svg');},
    trace:{...trace,path:'M100 160',values:[{...trace.values[0],x:100,y:160,display:'AATT',node_label:{lines:['AATT'],width:60,height:26}}]}};
}

test('hover commits shared label contours without hiding node targets or leaving suppressed labels',async t=>{
  const {inspectionOverlay}=await load(),f=labelFixture(t),overlay=inspectionOverlay(f.host);
  const projection={projection:f.trace.projection,frame:f.trace.frame};
  const commit=overlay.prepare(f.trace,projection);
  assert.ok(f.nodes.every(n=>n.box.getAttribute('visibility')===null),'Preparing cannot change mounted labels');
  commit();
  assert.deepEqual(f.nodes.map(n=>n.text.getAttribute('visibility')),['hidden','hidden',null]);
  assert.ok(f.nodes.every(n=>n.mark.getAttribute('visibility')===null&&n.node.getAttribute('tabindex')==='0'));
  f.nodes[2].box.setAttribute('visibility','visible');
  const second={...f.trace,values:[{...f.trace.values[0],y:240,node_label:{lines:['Nb.Mva','1269I'],width:80,height:48}}]};
  const next=overlay.prepare(second,projection);
  assert.equal(f.nodes[0].text.getAttribute('visibility'),'hidden','Next preparation leaves current view alone');
  next();
  assert.deepEqual(f.nodes.map(n=>n.text.getAttribute('visibility')),[null,null,'hidden']);
  const group=f.svg.children.at(-1).children.at(-1);
  assert.deepEqual(group.children.filter(c=>c.localName==='text').map(c=>c.textContent),['Nb.Mva','1269I']);
  assert.equal(group.children[0].getAttribute('height'),'48');
  overlay.clear();overlay.clear();
  assert.ok(f.nodes.every(n=>n.text.getAttribute('visibility')===null));
  assert.equal(f.nodes[2].box.getAttribute('visibility'),'visible','Restore the original visibility exactly');
  assert.equal(f.svg.children.length,3);
});

test('a replaced parameter scene cannot receive a previously prepared overlay',async t=>{
  const {inspectionOverlay}=await load(),f=labelFixture(t),overlay=inspectionOverlay(f.host);
  const commit=overlay.prepare(f.trace,{projection:f.trace.projection,frame:f.trace.frame});
  f.replace();commit();
  assert.equal(f.svg.children.length,3);
  assert.ok(f.nodes.every(n=>n.box.getAttribute('visibility')===null));
});

test('the selected path paints below value cells while its exact labels remain on top',async t=>{
  const {inspectionOverlay}=await load(),f=labelFixture(t),overlay=inspectionOverlay(f.host);
  overlay.show(f.trace,{projection:f.trace.projection,frame:f.trace.frame});
  const layer=f.svg.children.find(e=>e.dataset.inspectionPath);
  assert.ok(layer,'The selected path has a separate paint layer');
  assert.ok(f.svg.children.indexOf(layer)<f.svg.children.indexOf(f.nodes[0].node));
  assert.ok(!f.svg.children.at(-1).children.some(e=>e.localName==='path'));
  overlay.clear();assert.equal(f.svg.children.length,3);
});

test('compact sequence labels retain the exact word in their accessible name and title',async t=>{
  const {inspectionOverlay}=await load(),f=labelFixture(t),overlay=inspectionOverlay(f.host);
  const word='ACGTACGTACGTACGTACGT';
  f.trace.values[0]={...f.trace.values[0],display:word,node_label:{lines:['20 nt'],width:65,height:26}};
  overlay.show(f.trace,{projection:f.trace.projection,frame:f.trace.frame});
  const label=f.svg.children.at(-1).children.at(-1);
  assert.ok(label.getAttribute('aria-label')?.includes(word));
  assert.equal(label.children.find(e=>e.localName==='title')?.textContent,word);
});

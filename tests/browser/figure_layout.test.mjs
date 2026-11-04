import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');

test('Figure 1 uses supplied publication geometry without replacing its mounted molecules or axes',async t=>{
  const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
  const element=()=>({style:{setProperty(k,v){this[k]=String(v);}},dataset:{},attributes:{},children:[],classList:{add(){}},setAttribute(k,v){this.attributes[k]=String(v);},append(...values){this.children.push(...values);},remove(){this.removed=true;}});
  globalThis.document={createElementNS:()=>element()};
  const parent=element(),area=element(),trace=element(),hairpin=element(),axes=element();
  const backdrop=element();hairpin.querySelectorAll=()=>[backdrop];axes.querySelectorAll=()=>[];
  const oldLayer=element();parent.querySelectorAll=()=>[oldLayer];
  const {figureLayout}=await import(uri(await readFile(new URL('../../src/hop_design/assets/design_explorer/figure_layout.js',import.meta.url),'utf8')));
  const layout=figureLayout(parent,area,trace);
  const spec={frame:'0 0 1200 1032',hairpin:{frame:'-4 10 600 180',x:0,y:0,width:1200,height:360},trace:{frame:'0 0 1200 660',x:0,y:372,width:1200,height:660},links:[{parameter:'loop_size',points:'1,2 3,4 5,6'}],origins:[{parameter:'loop_size',x:1,y:2,width:3,height:4,rx:3}]};
  layout.show(spec,hairpin,axes);
  assert.equal(parent.style.aspectRatio,'1200 / 1032');
  assert.equal(area.style.width,'100%');assert.equal(area.style.height,`${360/1032*100}%`);
  assert.equal(trace.style.top,`${372/1032*100}%`);
  assert.equal(hairpin.attributes.viewBox,spec.hairpin.frame);assert.equal(axes.attributes.viewBox,spec.trace.frame);
  assert.equal(oldLayer.removed,true);assert.equal(backdrop.attributes.fill,'none');
  const [links,origins]=parent.children;
  assert.equal(links.attributes.viewBox,spec.frame);
  assert.equal(links.children[0].attributes.points,spec.links[0].points);
  assert.equal(origins.children[0].attributes.x,'1');
  assert.equal(origins.children[0].dataset.parameterOrigin,'loop_size');
  assert.deepEqual(hairpin.children,[]);assert.deepEqual(axes.children,[]);
  assert.throws(()=>layout.show({...spec,frame:'0 0 0 12'},hairpin,axes),/frame/i);
});

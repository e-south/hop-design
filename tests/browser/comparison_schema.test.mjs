import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const base=new URL('../../src/hop_design/assets/design_explorer/',import.meta.url);
const url=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');
async function load() {
 const helper=url(await readFile(new URL('comparison_schema.js',base),'utf8'));
 const source=(await readFile(new URL('comparison_features.js',base),'utf8')).replace("'./comparison_schema.js'",JSON.stringify(helper));
 return {...await import(helper),...await import(url(source))};
}
function node(tag) {
 return {tag,hidden:false,children:[],dataset:{},attributes:{},handlers:new Map(),animations:[],
  style:{values:{},setProperty(k,v){this.values[k]=v;}},classList:{add(){}},
  setAttribute(k,v){this.attributes[k]=String(v);},append(...children){this.children.push(...children);},
  replaceChildren(...children){this.children=children;},addEventListener(k,v){this.handlers.set(k,v);},removeEventListener(k){this.handlers.delete(k);},
  querySelector(selector){return this.children.find(n=>selector.startsWith('.')?n.className===selector.slice(1):n.tag===selector);},
  animate(frames,options){const animation={frames,options,cancel(){this.cancelled=true;}};this.animations.push(animation);return animation;},focus(){}};
}
const order=['shape.open_side_paired_positions','shape.loop_side_paired_bp','shape.loop_nt','shape.left_gap','shape.right_gap','sequences.basal_pairs','sequences.foldback_pairs','sequences.loop','interfaces.left_word','interfaces.right_word','processing.basal_method','processing.foldback_method','processing.release_method'];
function packet() {
 const shape={left_gap:2,loop_nt:3,loop_side_paired_bp:3,open_side_paired_positions:14,right_gap:0};
 const keys=[...Object.keys(shape).map(k=>'shape.'+k),...order.slice(5)];
 const columns=keys.map(key=>({key,active:true,parameters:[key.split('.')[1]],
  dictionary:key.startsWith('shape.')?[shape[key.split('.')[1]]]:key.endsWith('_pairs')?[[['A','T','watson_crick']]]:key==='processing.release_method'?['enzyme-a','enzyme-b']:['ACGT'],indices:key==='processing.release_method'?[0,1]:[0,0]}));
 return {algorithm:'umap',basis:{shape_scales:shape,sequence_keys:['basal_pairs','foldback_pairs','loop'],interface_keys:['left_word','right_word'],processing_keys:['basal_method','foldback_method','release_method'],weights:[1,1,1,1]},columns,
  presentation:{display:'schematic-glyphs',display_order:[...order],field_pitch:13.2,font_size:7.2,label_angle:-45,
   glyphs:Object.fromEntries(keys.map(key=>[key,{view_box:[-6,-4,12,8],nodes:[{tag:'line',attrs:{x1:'-4',x2:'4',y1:'0',y2:'0',stroke:'#233c43','data-measured-flank':'true'}}]}]))}};
}
function dom(t) {
 const old=globalThis.document;t.after(()=>{globalThis.document=old;});globalThis.document={createElement:node,createElementNS:(_,tag)=>node(tag)};
}
const state=p=>({presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}});
test('schematic display uses reviewed order and three visual groups without altering the saved vector',async t=>{
 dom(t);const {comparisonReader,comparisonStrip}=await load(),p=packet(),before=JSON.stringify(p),host=node('div');
 const raw=comparisonReader(p,['A','B'])('A').vector.map(f=>f.key);
 comparisonStrip(host,()=>{}).prepare('A',state(p))();
 assert.equal(host.dataset.comparisonDisplay,'schematic-glyphs');
 const fields=host.children[0].children.filter(n=>n.dataset.feature);
 assert.deepEqual(fields.map(n=>n.dataset.feature),order);
 assert.deepEqual(host.children[0].children.filter(n=>n.dataset.featureGroup).map(n=>n.textContent),['Geometry','Sequences','Enzymes']);
 assert.equal(fields.length,13);assert.ok(fields.every(n=>n.children.some(c=>c.tag==='svg')));
 assert.ok(fields.every(n=>n.children.find(c=>c.className==='comparison-value').hidden));
 assert.deepEqual(comparisonReader(p,['A','B'])('A').vector.map(f=>f.key),raw);
 assert.notDeepEqual(raw,order);assert.equal(JSON.stringify(p),before);
});
test('untrusted glyph markup and incomplete or repeated display order fail before mounting',async()=>{
 const {comparisonReader}=await load();
 const mutations=[p=>p.presentation.display_order.pop(),p=>p.presentation.display_order[1]=order[0],p=>p.presentation.field_pitch=Infinity,p=>p.presentation.label_angle=30,
  p=>p.presentation.glyphs[order[0]].nodes[0].tag='script',p=>p.presentation.glyphs[order[0]].nodes[0].attrs.onload='alert(1)',
  p=>p.presentation.glyphs[order[0]].nodes[0].attrs.href='https://example.com',p=>p.presentation.glyphs[order[0]].nodes[0].attrs.style='fill:red',
  p=>p.presentation.glyphs[order[0]].nodes[0].attrs.stroke='url(https://example.com)',p=>p.presentation.glyphs[order[0]].nodes[0].attrs.x1='NaN',
  p=>p.presentation.glyphs[order[0]].nodes=[{tag:'path',attrs:{d:'M0 0<script>'}}]];
 for(const mutate of mutations){const p=packet();mutate(p);assert.throws(()=>comparisonReader(p,['A','B']),/comparison|glyph|schematic/i);}
});
test('only changed fields receive a stationary opacity cue after committed selection',async t=>{
 dom(t);const {comparisonStrip}=await load(),p=packet(),host=node('div'),strip=comparisonStrip(host,()=>{}),s=state(p);
 s.selection={materialized_realization_id:'A'};strip.prepare('A',s)();
 const pending=strip.prepare('B',{...s,selection:{materialized_realization_id:'B'}});
 assert.equal(host.dataset.preparationId,'A');pending();
 const fields=host.children[0].children.filter(n=>n.dataset.feature),animated=fields.filter(n=>n.children.find(c=>c.className==='comparison-change-cue')?.animations.length);
 assert.deepEqual(animated.map(n=>n.dataset.feature),['processing.release_method']);
 const animation=animated[0].children.find(c=>c.className==='comparison-change-cue').animations[0];
 assert.ok(animation.frames.every(frame=>Object.keys(frame).every(k=>k==='opacity'||k==='offset')));
 strip.clear();assert.equal(animation.cancelled,true);
});
test('reduced-motion changes keep identical static glyphs without animation',async t=>{
 dom(t);const {comparisonStrip}=await load(),p=packet(),host=node('div'),strip=comparisonStrip(host,()=>{}),s=state(p);
 s.selection={materialized_realization_id:'A'};strip.prepare('A',s)();
 const fields=()=>host.children[0].children.filter(n=>n.dataset.feature);
 const glyphs=()=>fields().map(n=>JSON.stringify(n.children.find(c=>c.tag==='svg')));
 const before=glyphs();assert.ok(fields().every(n=>!n.children.find(c=>c.className==='comparison-change-cue').animations.length));
 const old=globalThis.matchMedia;globalThis.matchMedia=()=>({matches:true});t.after(()=>{globalThis.matchMedia=old;});
 strip.prepare('B',{...s,selection:{materialized_realization_id:'B'}})();
 assert.deepEqual(glyphs(),before);assert.ok(fields().every(n=>!n.children.find(c=>c.className==='comparison-change-cue').animations.length));
});
test('the visible help follows reviewed display positions and preserves four distance weights',async t=>{
 dom(t);const {comparisonStrip}=await load(),p=packet(),host=node('div'),help={button:node(),close:node(),panel:node(),content:node()};
 help.panel.id='help';help.panel.hidden=true;
 comparisonStrip(host,()=>{},help).prepare('A',state(p))();help.button.handlers.get('click')();
 assert.match(help.content.children.find(n=>n.tag==='h3').textContent,/Basal contacts · X1/);
 assert.equal(help.content.querySelector('select').children[0].value,order[0]);
 assert.match(help.content.children.find(n=>n.className==='comparison-policy').textContent,/geometry : sequence : ends : enzymes.*1 : 1 : 1 : 1/);
});
test('shared typography metadata changes browser font scale, pitch and angle together',async t=>{
 dom(t);const {comparisonStrip}=await load(),p=packet(),host=node('div');
 Object.assign(p.presentation,{font_size:8,field_pitch:15,label_angle:-30});
 comparisonStrip(host,()=>{}).prepare('A',state(p))();
 assert.equal(host.children[0].style.values['--schema-font-scale'],String(8/7.2));
 assert.equal(host.children[0].style.values['--schema-field-ratio'],String(15/8));
 assert.equal(host.children[0].style.values['--schema-label-angle'],'-30deg');
});
test('a committed hover preview cues its changed field even when another preparation stays pinned',async t=>{
 dom(t);const {comparisonStrip}=await load(),p=packet(),host=node('div'),strip=comparisonStrip(host,()=>{}),s=state(p);
 s.selection={materialized_realization_id:'A'};strip.prepare('A',s)();
 const commit=strip.prepare('B',s);
 assert.equal(host.dataset.preparationId,'A');commit();
 const changed=host.children[0].children.filter(n=>n.dataset.feature).filter(n=>n.children.find(c=>c.className==='comparison-change-cue').animations.length);
 assert.deepEqual(changed.map(n=>n.dataset.feature),['processing.release_method']);
});

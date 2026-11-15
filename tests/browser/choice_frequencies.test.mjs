// HOP Design
// hop-design/tests/browser/choice_frequencies.test.mjs
// Check exact preparation memberships and bounded frequency summaries.
// Module Author(s): Eric J. South
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../../src/hop_design/assets/design_explorer/choice_frequencies_model.js',import.meta.url),'utf8');
const {frequencyIndex}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const paths=[
 {materialized_realization_id:'a',matches:true,values:{loop_word:'AGCA',left_end_word:'GCAA',right_end_word:'AATG'},material_roles:{source_ssdna:{material_id:'source-a',length_nt:64}}},
 {materialized_realization_id:'b',matches:false,values:{loop_word:'AGCA',left_end_word:'GCAA',right_end_word:'AATG'},material_roles:{source_ssdna:{material_id:'source-b',length_nt:64}}},
 {materialized_realization_id:'c',matches:true,values:{loop_word:'GAAA',left_end_word:'AATG',right_end_word:'GCAA'},material_roles:{}},
];
const choices={axes:[{key:'loop_word',label:'Loop sequence'},{key:'left_end_word',label:'Left end'},{key:'right_end_word',label:'Right end'}],paths};
test('choice frequencies retain distinct preparation identities and left/right order',()=>{
 const before=JSON.stringify(choices),index=frequencyIndex(choices);
 const loops=index.profile('parameter:loop_word');assert.equal(loops.total,3);assert.equal(loops.choices,2);
 assert.deepEqual(loops.rows[0].members,['a','b']);assert.equal(loops.rows[0].eligible,1);
 const pairs=index.profile('assembly:end_pairs');assert.equal(pairs.choices,2);assert.equal(pairs.rows[0].count,2);
 const materials=index.profile('material:source_ssdna');assert.equal(materials.choices,3);assert.ok(materials.rows.some(r=>r.label==='Not applicable'));
 assert.equal(JSON.stringify(choices),before);assert.throws(()=>index.profile('unknown'),/Unknown/);
 assert.throws(()=>frequencyIndex({...choices,paths:[paths[0],paths[0]]}),/identity/);
});
test('bounded frequency profiles preserve every preparation in Other without double counting',()=>{
 const rows=Array.from({length:40},(_,i)=>({materialized_realization_id:`p${i}`,matches:i%2===0,values:{loop_word:`value-${i}`}}));
 const p=frequencyIndex({axes:choices.axes.slice(0,1),paths:rows}).profile('parameter:loop_word',8);
 assert.equal(p.rows.length,9);assert.equal(p.rows.at(-1).other,true);assert.equal(p.rows.at(-1).count,32);
 const ids=p.rows.flatMap(r=>r.members);assert.equal(ids.length,40);assert.equal(new Set(ids).size,40);
 assert.equal(p.rows.reduce((n,r)=>n+r.count,0),40);assert.equal(p.rows.reduce((n,r)=>n+r.eligible,0),20);
 assert.throws(()=>frequencyIndex({axes:[],paths:[]}).profile('parameter:loop_word'),/Unknown/);
});

// A small bubbling DOM keeps the widget contract independent of a browser library.
function element(tag='div') {
 const node={tag,children:[],handlers:new Map(),attrs:{},dataset:{},hidden:false,value:'',textContent:'',
  append(...items){for(const item of items){item.parent=this;this.children.push(item);}},
  replaceChildren(...items){for(const child of this.children){child.parent=null;if(child.contains(document.activeElement))document.activeElement=null;}this.children=[];this.append(...items);},
  setAttribute(key,value){this.attrs[key]=String(value);if(key==='data-frequency-row')this.dataset.frequencyRow=String(value);},
  addEventListener(key,handler){this.handlers.set(key,handler);},removeEventListener(key){this.handlers.delete(key);},
  contains(item){return item===this||this.children.some(child=>child.contains(item));},
  querySelectorAll(selector){return this.children.flatMap(child=>[...(selector==='[data-frequency-row]'&&child.dataset.frequencyRow?[child]:[]),...child.querySelectorAll(selector)]);},
  focus(){document.activeElement=this;this.handlers.get('focus')?.();},
  dispatch(type,event={}){event.target??=this;event.preventDefault??=()=>{event.defaultPrevented=true;};event.stopPropagation??=()=>{event.stopped=true;};this.handlers.get(type)?.(event);if(!event.stopped)this.parent?.dispatch(type,event);return event;},
 };
 Object.defineProperty(node,'selectedOptions',{get(){return this.children.flatMap(group=>group.children).filter(option=>option.value===this.value);}});
 return node;
}
for(const location of ['focused row','kept row','clear button'])test(`Escape from the ${location} clears frequency feedback and retains usable focus`,async t=>{
 const before=globalThis.document;t.after(()=>{globalThis.document=before;});
 globalThis.document={createElement:element,createElementNS:(_,tag)=>element(tag),activeElement:null};
 const uri=text=>'data:text/javascript;base64,'+Buffer.from(text).toString('base64');
 const widget=await readFile(new URL('../../src/hop_design/assets/design_explorer/choice_frequencies.js',import.meta.url),'utf8');
 const {choiceFrequencies}=await import(uri(widget.replace("'./choice_frequencies_model.js'",JSON.stringify(uri(source)))));
 const inspector=element(),host=element(),select=element('select'),chart=element(),summary=element(),clear=element('button'),outside=element('button'),focus=[];
 inspector.append(host,outside);host.append(select,chart,summary,clear);
 host.querySelector=selector=>({'select':select,'[data-frequency-chart]':chart,'button':clear}[selector]);
 inspector.addEventListener('keydown',e=>{if(e.key==='Escape')inspector.hidden=true;});
 const frequencies=choiceFrequencies(host,(...args)=>focus.push(args));frequencies.update({choices,preview:true});
 const row=chart.querySelectorAll('[data-frequency-row]')[0];row.focus();if(location!=='focused row')row.dispatch('click');if(location==='clear button')clear.focus();
 assert.equal(focus.at(-1)[0].length,2);
 const event=document.activeElement.dispatch('keydown',{key:'Escape'});
 assert.equal(inspector.hidden,false,'local Escape must not reach the inspector close handler');
 assert.equal(event.defaultPrevented,true);
 assert.equal(document.activeElement,location==='clear button'?select:row,'clearing feedback must retain visible usable focus');
 assert.equal(chart.contains(row),true);assert.equal(row.attrs['aria-pressed'],'false');
 assert.deepEqual(focus.at(-1),[null,{pin:false}]);assert.equal(clear.hidden,true);
 assert.equal(summary.textContent,'','linked highlighting does not create changing status prose');
 outside.dispatch('keydown',{key:'Escape'});assert.equal(inspector.hidden,true,'Escape outside the widget keeps its global behavior');
 frequencies.close();
});

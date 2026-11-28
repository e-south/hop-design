// HOP Design
// hop-design/tests/browser/landscape_accessibility.test.mjs
// Check interactive structural-map admission and keyboard actions.
// Module Author(s): Eric J. South
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');
const file=name=>readFile(new URL(`../../src/hop_design/assets/design_explorer/${name}.js`,import.meta.url),'utf8');
function element(attrs={}) {
 return {attrs:{...attrs},dataset:{},children:[],handlers:new Map(),classList:{toggle(){}},
  setAttribute(key,value){this.attrs[key]=String(value);},getAttribute(key){return this.attrs[key]??null;},removeAttribute(key){delete this.attrs[key];},
  addEventListener(key,handler){this.handlers.set(key,handler);},removeEventListener(key){this.handlers.delete(key);},
  replaceChildren(...items){this.children=items;},querySelectorAll(){return [];},querySelector(){return null;},
 };
}
for(const labelled of [false,true])test(`${labelled?'Already labelled':'Static structural'} SVG admits a named interactive group and retains keyboard actions`,async t=>{
 const before={document:globalThis.document,DOMParser:globalThis.DOMParser};t.after(()=>Object.assign(globalThis,before));
 const nodes=new Map(),get=key=>{if(!nodes.has(key))nodes.set(key,element());return nodes.get(key);};
 globalThis.document={querySelector:get};
 const host=get('plot');host.closest=()=>get('landscape');
 const family=element({role:'button',tabindex:'0','aria-label':'Explore family: Loop 4'}),preparation=element({role:'button',tabindex:'0','aria-label':'AAAG preparation'});
 family.dataset.familyIds='["family"]';preparation.dataset.preparations='["A"]';
 const name=labelled?'Molecular similarity of complete preparations':'Exact molecular products and their complete preparations';
 const svg=element(labelled?{role:'group','aria-label':name}:{role:'img'});svg.querySelectorAll=selector=>selector==='[data-family-ids]'?[family]:selector==='[data-preparations]'?[preparation]:[];
 svg.querySelector=selector=>selector==='title'&&!labelled?{textContent:name}:null;
 const staticDrawing='<svg role="img"><title>Exact molecular products and their complete preparations</title></svg>';
 globalThis.DOMParser=class{parseFromString(value){assert.equal(value,staticDrawing);return {documentElement:svg,querySelector:()=>null};}};
 let source=await file('landscape');
 const replacements={
  plot:'export const drawPlot=()=>{};',model:'export const toggleValue=()=>{},rangeQuery=()=>{};',
  parameters:'export const highlightParameters=()=>{},resolveParameterFocus=()=>({keys:[]});',
  linked_focus:await file('linked_focus'),persistent_scene:await file('persistent_scene'),
  grouped_navigation:'export const groupedNavigation=()=>{};',
  indexed_map:'export const indexedMap=()=>({focus(){},clear(){},close(){}});',
  member_choices:'export const memberChoices=()=>({dismiss(){},close(){}});',
 };
 for(const [name,body]of Object.entries(replacements))source=source.replace(`'./${name}.js'`,JSON.stringify(uri(body)));
 const {landscape}=await import(uri(source)),queries=[],selections=[];
 const view=landscape(host,get('members'),query=>queries.push(query),id=>selections.push(id),()=>{});
 const query={parameters:[{key:'loop_nt',values:[4]}]};
 const state={plots:{inspection:'trace',families:'families'},family_svg:staticDrawing,choices:{axes:[],paths:[{materialized_realization_id:'A',matches:true}]},families:{families:[{identity:'family',query,preparations:['A']}],products:[]}};
 view.draw(state,'families');
 assert.equal(host.children[0],svg);
 assert.equal(svg.getAttribute('role'),'group','an image root suppresses its descendant controls from accessibility trees');
 assert.equal(svg.getAttribute('aria-label'),name);
 assert.equal(family.getAttribute('role'),'button');assert.equal(preparation.getAttribute('tabindex'),'0');
 for(const [control,key]of [[family,'Enter'],[preparation,' ']]) {
  let prevented=false;control.handlers.get('keydown')({key,preventDefault(){prevented=true;}});assert.equal(prevented,true);
 }
 assert.deepEqual(queries,[query]);assert.deepEqual(selections,['A']);
 assert.equal(state.family_svg,staticDrawing,'interactive admission must not mutate the source export');
 view.close();
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=text=>'data:text/javascript;base64,'+Buffer.from(text).toString('base64');
const root=new URL('../../src/hop_design/assets/',import.meta.url);
async function load(){
 const parameters=uri(await readFile(new URL('survey_explorer/parameters.js',root),'utf8'));
 return import(uri((await readFile(new URL('design_explorer/local_choices.js',root),'utf8')).replace("'./parameters.js'",JSON.stringify(parameters))));
}
const axes=[
 {key:'loop_nt',canonical_key:'loop_nt',label:'Loop size',kind:'numeric',unit:'nt',design_role:'product',stage:'hairpin',neighborhood:'loop',measurement:'Unpaired nucleotides between the two loop boundaries.',relationship:'C = length(loop word)'},
 {key:'loop_word',canonical_key:'loop_word',label:'Loop sequence',kind:'categorical',design_role:'product',stage:'hairpin',neighborhood:'loop'},
 {key:'foldback_arm_bp',canonical_key:'foldback_arm_bp',label:'Loop-side extension',kind:'numeric',design_role:'product',equivalent_measurements:['loop_side_paired_bp']},
 {key:'loop_side_paired_bp',canonical_key:'foldback_arm_bp',kind:'numeric',design_role:'product',equivalent_measurements:['foldback_arm_bp']},
 {key:'left_gap',canonical_key:'left_gap',label:'Left gap',kind:'numeric',design_role:'product',applicable:false},
];
for(const a of axes)a.operations={inspect:{available:true},filter:{available:a.applicable!==false},
 preserve:{available:a.neighborhood==='loop',arguments:{stage:'hairpin',except_neighborhood:'loop'}},
 revise:{available:false,reason:'This frozen edition cannot revise permissions; open its discovery.'}};

test('feature disclosure follows shared operations, including derived measurements',async()=>{
 const {featureOptions,featureQuery}=await load();
 const derived={key:'self_paired_arm_bp',canonical_key:'self_paired_arm_bp',label:'Self-paired arm',kind:'numeric',
   design_role:'construction',operations:{inspect:{available:true},filter:{available:true},revise:{available:false}}};
 const captured={...derived,key:'legacy',canonical_key:'legacy',operations:{inspect:{available:true},filter:{available:false,reason:'Use its producer.'}}};
 assert.equal(featureOptions([derived],['self_paired_arm_bp'],{self_paired_arm_bp:3}).length,1);
 assert.throws(()=>featureQuery({parameters:[]},[captured],'legacy',3),/producer/);
});

test('feature teaching uses recorded names and distinct canonical measurements',async()=>{
 const {featureOptions}=await load(),values={loop_nt:4,loop_word:'AAAC',foldback_arm_bp:0};
 const loop=featureOptions(axes,['loop_nt','loop_word'],values);
 assert.deepEqual(loop.map(f=>[f.definition.key,f.value]),[['loop_nt',4],['loop_word','AAAC']]);
 assert.equal(loop[0].definition.measurement,axes[0].measurement);
 assert.equal(loop[0].definition.relationship,'C = length(loop word)');
 assert.deepEqual(featureOptions(axes,['loop_side_paired_bp','foldback_arm_bp'],values).map(f=>[f.definition.key,f.value]),[['foldback_arm_bp',0]]);
 assert.deepEqual(featureOptions(axes,['left_gap'],{left_gap:0}),[]);
});

test('filtering a feature replaces only its equivalent constraint and keeps all surrounding intent',async()=>{
 const {featureQuery}=await load();
 const query={parameters:[{key:'loop_side_paired_bp',minimum:0,maximum:6},{key:'loop_word',values:['AAAC']}],
   membership:['A','B'],preserved:{reference:'exact-reference',stage:'hairpin'}};
 const before=structuredClone(query);
 assert.deepEqual(featureQuery(query,axes,'foldback_arm_bp',3),{
   ...query,parameters:[{key:'loop_word',values:['AAAC']},{key:'foldback_arm_bp',values:[3]}],
 });
 assert.deepEqual(query,before);
 assert.throws(()=>featureQuery(query,axes,'left_gap',0),/applicable/);
 assert.throws(()=>featureQuery(query,axes,'loop_nt','4'),/value/);
 assert.throws(()=>featureQuery(query,axes,'loop_word',4),/value/);
});

function element(tag='div') {
 const node={tag,children:[],handlers:new Map(),dataset:{},style:{},attributes:{},hidden:false,textContent:'',offsetWidth:280,offsetHeight:230,
  append(...items){for(const item of items){item.parent=this;this.children.push(item);}},
  insertBefore(item,before){item.parent=this;this.children.splice(this.children.indexOf(before),0,item);},
  replaceChildren(...items){this.children=[];this.append(...items);},
  setAttribute(k,v){this.attributes[k]=v;},removeAttribute(k){delete this.attributes[k];},
  addEventListener(k,v){this.handlers.set(k,v);},removeEventListener(k){this.handlers.delete(k);},
  contains(item){return item===this||this.children.some(c=>c.contains(item));},
  getBoundingClientRect(){return {left:0,top:0,right:400,bottom:400,width:400,height:400};},
  focus(){this.focused=true;},remove(){this.removed=true;},
  querySelectorAll(){return [];},querySelector(){return null;},closest(){return null;},
 };
 return node;
}
function descendants(node){return node.children.flatMap(c=>[c,...descendants(c)]);}

test('local actions describe the pinned feature and cannot act on a pending or hovered molecule',async t=>{
 const old=globalThis.document;t.after(()=>{globalThis.document=old;});
 const doc=element();doc.createElement=element;globalThis.document=doc;
 const {localChoices}=await load(),host=element(),surface=element(),anchor=element('text'),empty=element('g'),calls=[];
 anchor.dataset.teachingNote='loop';anchor.closest=()=>anchor;
 empty.dataset.parameterAnchor='loop_nt';empty.closest=()=>empty;
 host.querySelectorAll=()=>[anchor,empty];host.append(anchor,empty);
 const first={feature_parameters:axes,selection:{materialized_realization_id:'A'},choices:{axes,query:{parameters:[]},paths:[
   {materialized_realization_id:'A',values:{loop_nt:4,loop_word:'AAAC'}},
   {materialized_realization_id:'B',values:{loop_nt:6,loop_word:'AAAAGC'}},
 ]}};
 const before=structuredClone(first);
 const local=localChoices(host,{
   surface,
   onQuery:q=>calls.push(['query',q]),onColor:(k,v)=>calls.push(['color',k,v]),
   canColor:()=>true,onLoop:()=>calls.push(['loop']),onFocus:()=>{},
 });
 local.update(first);
 assert.equal(anchor.attributes.role,'button');
 assert.equal(empty.attributes.role,undefined,'empty connector anchors must not create invisible controls');
 host.handlers.get('click')({target:anchor});
 assert.equal(descendants(host).filter(n=>n.tag==='button').length,0,'feature actions must not cover the molecular drawing');
 const buttons=()=>descendants(surface).filter(n=>n.tag==='button');
 assert.ok(buttons().find(n=>n.textContent==='Meaning'),'full definitions need deliberate disclosure in the compact action area');
 const color=buttons().find(n=>n.textContent==='Color map');
 assert.ok(color,'the molecular feature must reveal the shared color action');
 assert.ok(!descendants(surface).some(n=>n.textContent.includes('Unpaired nucleotides')));
 buttons().find(n=>n.textContent==='Meaning').handlers.get('click')();
 assert.ok(descendants(surface).some(n=>n.textContent.includes('Unpaired nucleotides')));
 assert.ok(descendants(surface).some(n=>n.textContent.includes('frozen edition')),'operation limits should be available in the same local disclosure');
 assert.equal(calls.length,0,'reading a definition must not filter or recolor');
 buttons().find(n=>n.textContent==='Actions').handlers.get('click')();
 assert.ok(buttons().find(n=>n.textContent==='Loop sequence · AAAC'),'the second feature is available without duplicating its actions');
 assert.equal(buttons().filter(n=>n.textContent==='Color map').length,1);
 buttons().find(n=>n.textContent==='Color map').handlers.get('click')();assert.deepEqual(calls,[['color','loop_nt',4]]);
 host.handlers.get('click')({target:anchor});
 buttons().find(n=>n.textContent==='Loop sequence · AAAC').handlers.get('click')();
 buttons().find(n=>n.textContent==='Color map').handlers.get('click')();
 assert.deepEqual(calls.at(-1),['color','loop_word','AAAC']);
 host.handlers.get('click')({target:anchor});
 buttons().find(n=>n.textContent==='Filter to 4 nt').handlers.get('click')();
 assert.deepEqual(calls.at(-1),['query',{parameters:[{key:'loop_nt',values:[4]}]}]);
 assert.deepEqual(first,before);
 host.handlers.get('click')({target:anchor});
 buttons().find(n=>n.attributes['aria-label']==='Close feature').handlers.get('click')();
 assert.equal(anchor.focused,true,'closing returns focus to the feature');anchor.focused=false;
 local.suspend();host.handlers.get('click')({target:anchor});
 assert.equal(buttons().length,0,'pending/hovered content has no pinned-feature actions');
 local.update(first);host.handlers.get('keydown')({key:'Enter',target:anchor,preventDefault(){}});
 assert.ok(buttons().some(n=>n.focused),'keyboard access opens and focuses the same actions');
 const event={key:'Escape',target:anchor,preventDefault(){},stopPropagation(){this.stopped=true;}};
 host.handlers.get('keydown')(event);assert.equal(event.stopped,true);assert.equal(anchor.focused,true);
 local.close();assert.equal(host.handlers.size,0);assert.equal(doc.handlers.size,0);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');
const file=name=>readFile(new URL(`../../src/hop_design/assets/design_explorer/${name}.js`,import.meta.url),'utf8');

test('a failed render retries the returned state without another selection or token graft',async()=>{
  const {pendingRender}=await import(uri(await file('pending_render')));
  const old={token:'old',selection:'A'},next={token:'new',selection:'B'};
  let displayed=old,fail=true,attempts=[];
  const controller=pendingRender(async(value,restore)=>{attempts.push([value,restore]);if(fail)throw Error('drawing unavailable');displayed=value;});
  await assert.rejects(controller.show(next,true),/unavailable/);
  assert.equal(displayed,old);assert.equal(controller.blocked,true);
  await assert.rejects(controller.show({token:'third'}),/pending/i);
  assert.equal(attempts.length,1);
  fail=false;await controller.retry();
  assert.equal(displayed,next);assert.equal(controller.blocked,false);
  assert.deepEqual(attempts,[[next,true],[next,true]]);
  assert.equal(old.token,'old');
});

test('coincident candidates use the pinned reference without shadowing the cohort index',async t=>{
  const before={document:globalThis.document,actions:globalThis.testActions};t.after(()=>{globalThis.document=before.document;globalThis.testActions=before.actions;});
  const elements=new Map();
  const element=id=>{if(!elements.has(id))elements.set(id,{dataset:{},classList:{toggle(){}},addEventListener(){},removeEventListener(){},querySelectorAll(){return[];},querySelector(){return null;},replaceChildren(...children){this.children=children;}});return elements.get(id);};
  globalThis.document={querySelector:selector=>element(selector),createElement:()=>({addEventListener(){},setAttribute(){},focus(){}})};
  const host=element('host');host.closest=()=>element('#landscape');
  let source=await file('landscape');
  const model=await readFile(new URL('../../src/hop_design/assets/survey_explorer/model.js',import.meta.url),'utf8');
  const replacements={
    plot:'export function drawPlot(host,choices,drawing,actions){globalThis.testActions=actions;}',
    model,
    member_choices:(await file('member_choices')).replace("'./model.js'",JSON.stringify(uri(model))),
    parameters:'export const highlightParameters=()=>{},resolveParameterFocus=()=>({keys:[]});',
    grouped_navigation:'export const groupedNavigation=()=>{};',
    indexed_map:'export const indexedMap=()=>({focus(){},clear(){},update(){},close(){}});',
    linked_focus:await file('linked_focus'),persistent_scene:await file('persistent_scene'),
  };
  for(const[name,body]of Object.entries(replacements))source=source.replace(`'./${name}.js'`,JSON.stringify(uri(body)));
  const {landscape}=await import(uri(source));
  const a={materialized_realization_id:'A',matches:true,values:{loop_word:'AAAA'},material_roles:{source_ssdna:{material_id:'MA',length_nt:70}}},b={...a,materialized_realization_id:'B',material_roles:{source_ssdna:{material_id:'MB',length_nt:70}}};
  const focuses=[],previews=[];let drawing=true;
  const view=landscape(host,element('members'),()=>{},()=>{},keys=>focuses.push(keys),identity=>{
    assert.equal(drawing,false,'Drawing must not restore preview against unmounted or obsolete axes');previews.push(identity);
  });
  const state={plots:{parameters:'plot'},plot_svg:'svg',choices:{paths:[a,b],axes:[],query:{parameters:[]}},families:{products:[{preparations:['A','B'],features:{loop_nt:[4],foldback_arm_bp:[6]}}],families:[]},selection:a};
  view.draw(state,'parameters');drawing=false;
  assert.deepEqual(previews,[],'Pinned reload does not restore before initial axes mount');
  globalThis.testActions.path([a,b]);
  assert.deepEqual(element('#member-options').children.map(b=>b.textContent),['loop AAAA','loop AAAA']);
  assert.match(element('#member-options').children[0].title,/source ssdna 70 nt/);
  assert.match(element('#member-options').children[1].title,/source ssdna changes/);
  globalThis.testActions.hover([a]);
  assert.deepEqual(focuses.at(-1),[],'Point hover must not highlight every molecular parameter');
  globalThis.testActions.focus({key:'loop_nt',label:'Loop size',measurement:'nt'});
  assert.deepEqual(focuses.at(-1),['loop_nt'],'Explicit axis focus retains its molecular highlight');
  const retainedPreviews=[...previews];
  view.focusParameters([]);
  assert.deepEqual(focuses.at(-1),[],'Leaving a feature clears its highlight');
  assert.deepEqual(previews,retainedPreviews,'Feature focus must not reset the preparation or its chooser');
  drawing=true;view.draw({...state,plots:{parameters:'changed-query-projection'}},'parameters');drawing=false;
  assert.deepEqual(previews,['A'],'Changed projection does not restore the new selection into old axes');
  view.clear();assert.equal(previews.at(-1),null,'User clearing still restores the committed preview');
  view.close();
});

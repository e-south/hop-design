import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=text=>'data:text/javascript;base64,'+Buffer.from(text).toString('base64');
const source=name=>readFile(new URL(`../../src/hop_design/assets/design_explorer/${name}.js`,import.meta.url),'utf8');
function element(){return {children:[],handlers:new Map(),dataset:{},style:{},hidden:false,value:'',textContent:'',append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;this.textContent='';},setAttribute(){},addEventListener(k,v){this.handlers.set(k,v);},removeEventListener(k){this.handlers.delete(k);}};}
async function setup(t){
 const previous={document:globalThis.document,Option:globalThis.Option};t.after(()=>Object.assign(globalThis,previous));
 globalThis.document={createElement:element};globalThis.Option=class {constructor(text,value){this.text=text;this.value=value;}};
 const {colorControls}=await import(uri((await source('color_controls')).replace("'./molecular_colors.js'",JSON.stringify(uri(await source('molecular_colors'))))));
 const host=element(),select=element(),words=element(),legend=element(),lenses=[];
 host.querySelector=s=>s==='select[data-lens]'?select:s==='select[data-word]'?words:legend;
 return {host,select,words,legend,lenses,controls:colorControls(host,lens=>lenses.push(lens))};
}
const state=()=>({presentation:{landscape:'similarity'},map_index:{digest:'edition'},selection:null,choices:{axes:[{key:'left_gap',label:'Left gap',unit:'bp',kind:'numeric'}],paths:[{materialized_realization_id:'A',matches:true,values:{left_gap:0}},{materialized_realization_id:'B',matches:true,values:{}}]}});
test('no grouping survives filters and view changes without changing the chosen molecular context',async t=>{
 const {host,select,controls,lenses}=await setup(t),first=state();controls.update(first);
 select.value='none';select.handlers.get('change')();
 const filtered=structuredClone(first);filtered.choices.paths[0].matches=false;controls.update(filtered);
 assert.equal(select.value,'none');assert.equal(lenses.at(-1).kind,'none');
 controls.update({...filtered,presentation:{landscape:'families'}});assert.equal(host.hidden,true);
 controls.update(filtered);assert.equal(host.hidden,false);assert.equal(select.value,'none');
 controls.close();assert.equal(select.handlers.size,0);
});
test('constant legend does not claim a coordinate exists on every preparation',async t=>{
 const {controls,legend}=await setup(t);controls.update(state());controls.choose('left_gap');
 assert.match(legend.children.map(n=>n.textContent).join(' '),/0 bp where applicable/);
 assert.doesNotMatch(legend.children.map(n=>n.textContent).join(' '),/throughout this edition/);
 controls.close();
});

test('opening color explains varying displayed features and remains stable across filters',async t=>{
 const {controls,select,lenses}=await setup(t),next=state();
 next.presentation.display_axes=['loop_nt','foldback_arm_bp','left_gap'];
 next.choices.axes.push(
  {key:'loop_nt',label:'Loop size',unit:'nt',kind:'numeric'},
  {key:'foldback_arm_bp',label:'Loop-side extension',unit:'bp',kind:'numeric'});
 Object.assign(next.choices.paths[0].values,{left_gap:6,loop_nt:4,foldback_arm_bp:5});
 Object.assign(next.choices.paths[1].values,{left_gap:6,loop_nt:6,foldback_arm_bp:4});
 const before=structuredClone(next);controls.update(next);
 assert.equal(select.value,'loop_nt','the first constant color key must not obscure molecular variation');
 assert.deepEqual(lenses.at(-1).extent,[4,6]);assert.deepEqual(next,before);
 controls.choose('left_gap');
 const filtered=structuredClone(next);filtered.choices.paths[1].matches=false;controls.update(filtered);
 assert.equal(select.value,'left_gap','a deliberate lens remains selected even when it is constant');
 controls.close();
});

test('constant cohorts open neutrally rather than implying a varying scale',async t=>{
 const {controls,select,lenses,legend}=await setup(t);controls.update(state());
 assert.equal(select.value,'none');assert.equal(lenses.at(-1).kind,'none');
 assert.match(legend.textContent,/constant/);
 controls.close();
});
test('color controls stay hidden for a legacy SVG map without the indexed color surface',async t=>{
 const {host,controls}=await setup(t),legacy=state();delete legacy.map_index;controls.update(legacy);
 assert.equal(host.hidden,true);controls.close();
});

test('a molecular feature selects the same color lens without rewriting the query or pin',async t=>{
 const {controls,select,words,lenses}=await setup(t),next=state();
 next.choices.axes.push({key:'loop_word',label:'Loop sequence',kind:'categorical',stage:'hairpin'});
 next.choices.paths[0].values.loop_word='AAAC';next.choices.paths[1].values.loop_word='AACA';
 next.selection={materialized_realization_id:'A'};next.choices.query={parameters:[]};
 const before=structuredClone(next);controls.update(next);
 assert.equal(controls.available('loop_word'),true);
 controls.choose('loop_word','AACA');
 assert.equal(select.value,'loop_word');assert.equal(words.value,'AACA');
 assert.equal(lenses.at(-1).word,'AACA');assert.deepEqual(next,before);
 assert.throws(()=>controls.choose('loop_word','GGGG'),/word|recorded/);
 assert.equal(select.value,'loop_word');assert.equal(words.value,'AACA');
 controls.update({...next,presentation:{landscape:'families'}});
 assert.equal(controls.available('loop_word'),false);
 controls.close();
});

test('reopening restores an explicit lens even when cohort arrays are already mounted',async t=>{
 const {controls,select,words,lenses}=await setup(t),next=state();
 next.choices.axes.push({key:'loop_word',label:'Loop sequence',kind:'categorical'});
 next.choices.paths[0].values.loop_word='AAAC';next.choices.paths[1].values.loop_word='AACA';
 controls.update(next);controls.choose('left_gap');
 controls.update({...next,presentation:{...next.presentation,color:{key:'loop_word',word:'AACA'}}},{restore:true});
 assert.equal(select.value,'loop_word');assert.equal(words.value,'AACA');
 assert.deepEqual(controls.snapshot(),{key:'loop_word',word:'AACA'});
 assert.equal(lenses.at(-1).word,'AACA');
 controls.update({...next,presentation:{...next.presentation,color:{key:'none',word:null}}},{restore:true});
 assert.equal(select.value,'none');assert.equal(lenses.at(-1).kind,'none');controls.close();
});

test('ordinary responses cannot overwrite a locally chosen color; invalid restore fails before paint',async t=>{
 const {controls,select,lenses}=await setup(t),next=state();
 next.presentation.color={key:'left_gap',word:null};controls.update(next);
 controls.choose('none');controls.update({...next,choices:structuredClone(next.choices)});
 assert.equal(select.value,'none');const count=lenses.length;
 assert.throws(()=>controls.update({...next,presentation:{...next.presentation,color:{key:'missing',word:null}}},{restore:true}),/color|available|parameter/i);
 assert.equal(select.value,'none');assert.equal(lenses.length,count);controls.close();
});

test('word counts appear once and retain eligible versus recorded counts after filtering',async t=>{
 const {controls,words,legend,lenses}=await setup(t),next=state();
 next.choices.axes.push({key:'loop_word',label:'Loop sequence',kind:'categorical'});
 for(const row of next.choices.paths)row.values.loop_word='AAAC';
 controls.update(next);controls.choose('loop_word','AAAC');
 assert.equal(words.children[0].text,'AAAC · 2');
 assert.equal(legend.children.length,0,'the selected word and count already appear in the selector');
 const filtered=structuredClone(next);filtered.choices.paths[1].matches=false;controls.update(filtered);
 assert.equal(words.children[0].text,'AAAC · 1 / 2');
 assert.equal(words.value,'AAAC');assert.equal(lenses.at(-1).word,'AAAC');
 assert.deepEqual(legend.children.map(n=>n.textContent),['Hollow: outside filters']);
 controls.close();
});

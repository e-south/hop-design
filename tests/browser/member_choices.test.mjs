import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
async function load(){
 const model=uri(await readFile(new URL('../../src/hop_design/assets/survey_explorer/model.js',import.meta.url),'utf8'));
 return import(uri((await readFile(new URL('../../src/hop_design/assets/design_explorer/member_choices.js',import.meta.url),'utf8')).replace("'./model.js'",JSON.stringify(model))));
}
function element(){return {children:[],handlers:new Map(),attrs:{},hidden:false,textContent:'',
 append(...children){this.children.push(...children);},replaceChildren(...children){this.children=children;},
 setAttribute(k,v){this.attrs[k]=String(v);},addEventListener(k,f){this.handlers.set(k,f);},removeEventListener(k){this.handlers.delete(k);},
 focus(){this.handlers.get('focus')?.();},
};}
const all=n=>n.children.flatMap(c=>[c,...all(c)]);
test('member inspection bounds DOM work and retains outside-filter preview and exact selection',async t=>{
 const prior=globalThis.document;globalThis.document={createElement:()=>element()};t.after(()=>{globalThis.document=prior;});
 const {memberChoices}=await load(),panel=element(),title=element(),options=element(),close=element(),events=[];
 const rows=Array.from({length:25},(_,i)=>({materialized_realization_id:`P${i}`,matches:i!==0,values:{loop_word:'AAAA'},methods:[{name:'Nb.BtsI'}],material_roles:{source_ssdna:{material_id:`M${i}`,length_nt:70}}}));
 const picker=memberChoices({panel,title,options,close},id=>events.push(['select',id]),id=>events.push(['preview',id]));
 picker.open(rows,rows[1]);
 assert.ok(all(options).length<40,'a large coincident group must not create one DOM subtree per preparation');
 assert.match(title.textContent,/25.*24/);
 assert.match(options.children[0].textContent,/AAAA.*Nb.BtsI/);
 assert.doesNotMatch(options.children[0].textContent,/source ssdna|changes/,'the picker should lead with molecular and method choices, not a materials diff');
 assert.match(options.children[0].title,/source ssdna changes/,'complete context remains inspectable');
 const first=options.children[0];first.focus();assert.deepEqual(events.at(-1),['preview','P0']);
 first.handlers.get('click')();assert.ok(!events.some(([kind])=>kind==='select'),'excluded points remain inspectable but cannot be selected');
 const next=()=>all(options).find(n=>n.textContent==='Next');
 next().handlers.get('click')();next().handlers.get('click')();next().handlers.get('click')();
 const last=options.children[0];last.focus();assert.deepEqual(events.at(-1),['preview','P24']);
 last.handlers.get('click')();assert.deepEqual(events.find(([kind])=>kind==='select'),['select','P24']);
 assert.equal(panel.hidden,true);assert.equal(options.children.length,0);
 const beforeClose=events.length;picker.close();assert.equal(panel.handlers.size,0);assert.equal(close.handlers.size,0);
 assert.equal(events.length,beforeClose,'teardown must not schedule a restored molecular render');
});

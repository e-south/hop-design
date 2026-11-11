import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/comparison_features.js',import.meta.url))).toString('base64'));
function element(tag){return {tag,hidden:false,attributes:{},handlers:new Map(),style:{values:{},setProperty(k,v){this.values[k]=v;}},dataset:{},children:[],classList:{add(){}},setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,v){this.handlers.set(k,v);},removeEventListener(k){this.handlers.delete(k);},append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;},querySelector(tag){return this.children.find(e=>e.tag===tag);},focus(){this.focused=true;}};}
const packet=()=>({algorithm:'umap',basis:{shape_scales:{five_prime_unpaired_nt:2},sequence_keys:['basal_pairs'],interface_keys:['left_word'],weights:[1,1,1]},columns:[
 {key:'shape.five_prime_unpaired_nt',parameters:['five_prime_unpaired_nt'],active:true,dictionary:[4,6],indices:[0,1]},
 {key:'shape.loop_nt',parameters:['loop_nt'],active:false,dictionary:[4],indices:[0,0]},
 {key:'sequences.basal_pairs',parameters:['open_side_paired_positions'],active:true,dictionary:[[['A','T','watson_crick']],[['G','T','gt_wobble']]],indices:[0,1]},
 {key:'interfaces.left_word',parameters:['left_end_word'],active:true,dictionary:['AGTC','GGAA'],indices:[0,1]},
]});
test('distance explanations follow the saved policy without adding controls',async()=>{
 const {distanceDescription}=await load(),basis=packet().basis;
 assert.match(distanceDescription('shape','five_prime_unpaired_nt',basis),/observed range.*2/);
 assert.match(distanceDescription('sequences','basal_pairs',basis),/length difference subtracted/);
 basis.distance_policy={regional_metric:'normalized_edit',end_word_metric:'hamming',numeric_scaling:'declared'};
 assert.match(distanceDescription('shape','five_prime_unpaired_nt',basis),/declared scale.*2/);
 assert.match(distanceDescription('sequences','basal_pairs',basis),/longer region/);
 assert.match(distanceDescription('interfaces','left_word',basis),/positionwise/);
 assert.match(distanceDescription('interfaces','left_polarity',basis),/nominal/);
});

test('feature explanations distinguish physical values from exact dictionary lookups',async()=>{
 const {comparisonReader,comparisonExplanation}=await load(),p=packet(),reading=comparisonReader(p,['A','B'])('B');
 const geometry=comparisonExplanation(reading.vector[0],reading.basis);
 assert.equal(geometry.kind,'Measurement');assert.equal(geometry.display,'6');
 assert.match(geometry.formula,/abs\(a − b\) \/ 2/);
 const contact=comparisonExplanation(reading.vector[1],reading.basis);
 assert.equal(contact.kind,'Dictionary code');assert.match(contact.decoded,/G:T/);
 assert.match(contact.meaning,/1 ordered contact/);assert.match(contact.meaning,/not a count/);
 assert.match(contact.formula,/edit\(a, b\)/);assert.match(contact.formula,/abs\(m − n\)/);
 const end=comparisonExplanation(reading.vector[2],reading.basis);
 assert.equal(end.decoded,'GGAA');assert.match(end.meaning,/4 nt/);
 p.basis.distance_policy={regional_metric:'normalized_edit',end_word_metric:'hamming'};
 assert.equal(comparisonExplanation(reading.vector[2],p.basis).formula,'mismatches(a, b) / length(a)');
 assert.equal(JSON.stringify(p.columns[2].dictionary[1]),'[["G","T","gt_wobble"]]');
});

test('optional X explanation follows committed hover values, retains its field and closes before clearing',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});globalThis.document={createElement:element};
 const {comparisonStrip}=await load(),host=element(),help={button:element(),close:element(),panel:element(),content:element()};
 help.panel.id='help';help.panel.hidden=true;
 const p=packet();p.basis.weights=[2,1,3];const state={presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}};
 const strip=comparisonStrip(host,()=>{},help);strip.prepare('A',state)();
 help.button.handlers.get('click')();assert.equal(help.panel.hidden,false);assert.equal(help.panel.dataset.preparationId,'A');
 const select=help.content.querySelector('select');select.value='sequences.basal_pairs';select.handlers.get('change')();
 const pending=strip.prepare('B',state);assert.equal(help.panel.dataset.preparationId,'A');
 pending();assert.equal(help.panel.dataset.preparationId,'B');assert.equal(help.content.querySelector('select').value,'sequences.basal_pairs');
 assert.match(help.content.children.find(e=>e.tag==='h3').textContent,/= 1.*Dictionary code/);
 assert.match(help.content.children.find(e=>e.className==='comparison-policy').textContent,/2 : 1 : 3/);
 assert.match(help.content.children.at(-1).textContent,/sum\(active w\)/);
 assert.ok(strip.dismiss(true));assert.equal(help.button.focused,true);assert.equal(help.panel.hidden,true);
 help.button.handlers.get('click')();strip.clear();assert.equal(help.panel.hidden,true);assert.equal(help.button.hidden,true);
 strip.close();assert.equal(help.button.handlers.size,0);assert.equal(help.close.handlers.size,0);
});

test('the numeric strip reserves readable space for the longest exact value without rounding',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});globalThis.document={createElement:element};
 const {comparisonStrip}=await load(),p=packet(),host=element();p.columns[0].dictionary[1]=123456;
 const state={presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}};
 comparisonStrip(host,()=>{}).prepare('B',state)();
 assert.equal(host.children[0].style.values['--feature-min'],'60px');
 assert.equal(host.children[0].children.find(e=>e.dataset.feature).children.find(e=>e.className==='comparison-value').textContent,'123456');
});
test('comparison reading uses exact fitted tokens and preserves fixed versus active features',async()=>{
 const {comparisonReader}=await load(),p=packet(),original=JSON.stringify(p),read=comparisonReader(p,['A','B']);
 assert.equal(read('B').identity,'B');assert.equal(read('B').features[0].value,6);
 assert.equal(read('A').features[1].active,false);
 assert.deepEqual(read('B').features[2].value,[['G','T','gt_wobble']]);
 assert.deepEqual(read('B').features[2].parameters,['open_side_paired_positions']);
 assert.equal(read('B').features[3].value,'GGAA');
 assert.equal(JSON.stringify(p),original);
 assert.throws(()=>read('foreign'),/identity/i);
});
test('invalid or mismatched comparison columns cannot masquerade as the current molecule',async()=>{
 const {comparisonReader}=await load();
 for(const change of [p=>p.columns[0].indices.pop(),p=>p.columns[0].indices[1]=9,p=>p.columns[0].active=false]){
  const p=packet();change(p);assert.throws(()=>comparisonReader(p,['A','B']),/comparison/i);
 }
});

test('contact token coding is lossless and rejects missing contacts',async()=>{
 const {comparisonReader}=await load(),p=packet(),column=p.columns[2];
 p.contacts=column.dictionary.flat();column.dictionary=[[0],[1]];column.encoding='contacts';
 assert.deepEqual(comparisonReader(p,['A','B'])('B').features[2].value,[['G','T','gt_wobble']]);
 column.dictionary[1]=[2];assert.throws(()=>comparisonReader(p,['A','B']),/contact/);
});

test('the compact vector follows the saved active feature order with exact contact codes',async()=>{
 const {comparisonReader}=await load(),p=packet(),column=p.columns[2];
 p.contacts=column.dictionary.flat();column.dictionary=[[0],[1]];column.encoding='contacts';
 const reading=comparisonReader(p,['A','B'])('B');
 assert.deepEqual(reading.vector.map(f=>f.key),['shape.five_prime_unpaired_nt','sequences.basal_pairs','interfaces.left_word']);
 assert.deepEqual(reading.vector.map(f=>f.encoded),[6,[1],'GGAA']);
 assert.deepEqual(reading.vector[1].value,[['G','T','gt_wobble']]);
 assert.equal(reading.vector[1].encoding,'contacts');
 assert.equal(reading.features.find(f=>f.key==='shape.loop_nt').active,false);
});

test('retained terminal fields remain exact and do not masquerade as complete hairpin tails',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
 globalThis.document={createElement:element,createElementNS:element};
 const {comparisonReader,comparisonStrip}=await load(),p=packet();
 p.basis.schema_id='hop.molecular-comparison/v2';
 p.basis.shape_scales={five_prime_retained_tail_nt:2};
 p.basis.sequence_keys=['five_prime_retained_tail'];
 p.basis.interface_keys=[];
 p.columns=[
  {key:'shape.five_prime_retained_tail_nt',parameters:['five_prime_unpaired_nt'],active:true,dictionary:[0,2],indices:[0,1]},
  {key:'sequences.five_prime_retained_tail',parameters:['five_prime_unpaired_nt'],active:true,dictionary:[[],['A','C']],indices:[0,1]},
 ];
 const read=comparisonReader(p,['A','B']);
 assert.deepEqual(read('A').features[1].value,[]);
 assert.deepEqual(read('B').features[1].value,['A','C']);
 assert.equal(read('B').features[0].value,2);
 const host=element(),strip=comparisonStrip(host,()=>{});
 strip.prepare('A',{presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}})();
 assert.match(host.children[0].children[0].title,/discarded handle changes do not move/);
 assert.doesNotMatch(host.children[0].children[0].title,/includes complete hairpin tail/);
});

test('strip prepares without changing visible identity, commits atomically and restores the pin',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
 globalThis.document={createElement:element,createElementNS:element};
 const {comparisonStrip}=await load(),host=element(),strip=comparisonStrip(host,()=>{});
 const state={presentation:{landscape:'similarity'},map_index:{comparison:packet()},choices:{paths:['A','B'].map(id=>({materialized_realization_id:id}))}};
 const pin=strip.prepare('A',state);assert.equal(host.dataset.preparationId,undefined);pin();
 const next=strip.prepare('B',state);assert.equal(host.dataset.preparationId,'A');next();assert.equal(host.dataset.preparationId,'B');
 pin();assert.equal(host.dataset.preparationId,'A');
 assert.throws(()=>strip.prepare('foreign',state),/identity/);assert.equal(host.dataset.preparationId,'A');
 strip.prepare('A',{...state,presentation:{landscape:'families'}})();assert.equal(host.hidden,true);
});

test('descriptor names and units have separate lines without fragmenting either label',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
 globalThis.document={createElement:element,createElementNS:element};
 const {comparisonStrip}=await load(),host=element(),p=packet();
 p.columns[0].label='Retained from 5′ tail';p.columns[0].unit='nt';
 const state={presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}};
 comparisonStrip(host,()=>{}).prepare('A',state)();
 const fields=host.children[0].children.filter(e=>e.dataset.feature);
 assert.deepEqual(fields[0].children[0].children.map(n=>n.textContent),['Retained from 5′ tail','nt']);
 assert.deepEqual(fields[1].children[0].children.map(n=>n.textContent),['Basal contacts']);
 assert.equal(fields[0].children[3].dataset.encoded,'4');
 assert.match(fields[0].title,/Retained from 5′ tail: 4 nt/);
});

test('decoded strip shows scientific scalar values while retaining exact stored encodings',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
 globalThis.document={createElement:element,createElementNS:element};
 const {comparisonStrip}=await load(),host=element(),strip=comparisonStrip(host,()=>{});
 const p=packet(),state={presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}};
 strip.prepare('B',state)();
 assert.equal(host.dataset.comparisonDisplay,'numeric-row');
 const fields=host.children[0].children.filter(e=>e.dataset.feature);
 assert.deepEqual(fields.map(e=>e.dataset.feature),['shape.five_prime_unpaired_nt','sequences.basal_pairs','interfaces.left_word']);
 const scalar=fields[0];
 assert.equal(scalar.children.find(e=>e.className==='comparison-value').textContent,'6');
 const code=scalar.children.find(e=>e.className==='comparison-code');
 assert.equal(code.dataset.encoded,'6');assert.equal(code.hidden,true);
 const contacts=fields[1].children.find(e=>e.className==='comparison-value');
 assert.equal(contacts.textContent,'1');
 assert.match(fields[1].title,/G:T gt wobble/);
 assert.match(fields[1].title,/code magnitude is not a distance/);
});

test('literal scientific features retain the exact recorded values',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
 globalThis.document={createElement:element,createElementNS:element};
 const {comparisonStrip}=await load(),host=element(),p=packet(),before=JSON.stringify(p);
 comparisonStrip(host,()=>{}).prepare('B',{presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}})();
 const panel=host.children[0];
 assert.equal(host.dataset.comparisonDisplay,'numeric-row');
 assert.equal(panel.children[0].textContent,'X = [');
 assert.deepEqual(panel.children.filter(e=>e.dataset.feature).map(e=>e.dataset.feature),['shape.five_prime_unpaired_nt','sequences.basal_pairs','interfaces.left_word']);
 assert.equal(JSON.stringify(p),before);
});

test('literal X keeps every active feature in one bracketed reading row',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
 globalThis.document={createElement:element,createElementNS:element};
 const {comparisonStrip}=await load(),host=element(),p=packet();
 comparisonStrip(host,()=>{}).prepare('B',{presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}})();
 const nodes=host.children[0].children;
 assert.equal(host.dataset.comparisonDisplay,'numeric-row');
 assert.equal(nodes[0].textContent,'X = [');assert.equal(nodes.at(-1).textContent,']');
 assert.deepEqual(nodes.filter(e=>e.dataset.feature).map(e=>e.dataset.feature),['shape.five_prime_unpaired_nt','sequences.basal_pairs','interfaces.left_word']);
});


test('numeric field codes keep exact meanings and shared group spans during hover',async t=>{
 const previous=globalThis.document;t.after(()=>{globalThis.document=previous;});
 globalThis.document={createElement:element,createElementNS:element};
 const {comparisonStrip}=await load(),host=element(),p=packet();
 p.presentation={groups:{shape:{label:'Geometry',fill:'#E3EBE9'},sequences:{label:'Sequence',fill:'#D1E6FA'},interfaces:{label:'Ends',fill:'#FDEDD7'}}};
 const state={presentation:{landscape:'similarity'},map_index:{comparison:p},choices:{paths:['A','B'].map(materialized_realization_id=>({materialized_realization_id}))}};
 const before=JSON.stringify(p),strip=comparisonStrip(host,()=>{});
 strip.prepare('A',state)();
 assert.deepEqual(host.children[0].children.filter(e=>e.dataset.featureGroup).map(e=>e.textContent),['Geometry','Sequence','Ends']);
 assert.equal(host.children[0].children.find(e=>e.dataset.featureGroup==='shape').style.values['grid-column'],'2 / 3');
 assert.equal(host.children[0].children.find(e=>e.dataset.feature).style.values['grid-row'],'2 / 4');
 const read=()=>host.children[0].children.filter(e=>e.dataset.feature).map(e=>e.children.find(n=>n.className==='comparison-value').textContent);
 assert.deepEqual(read(),['4','0','0']);
 const next=strip.prepare('B',state);assert.deepEqual(read(),['4','0','0']);next();
 assert.deepEqual(read(),['6','1','1']);assert.equal(host.dataset.preparationId,'B');
 assert.equal(JSON.stringify(p),before);
});

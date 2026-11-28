import {comparisonSchema,comparisonGlyph,changedComparisonFields,cueComparisonChanges} from './comparison_schema.js';
// A reading of the saved comparison basis, not a second embedding or distance model.
const names={
 basal_method:['Basal nickase',''],foldback_method:['Foldback nickase',''],release_method:['Release enzyme',''],
 loop_nt:['Loop length','nt'],loop_side_paired_bp:['Loop-side pairing','bp'],open_side_paired_positions:['Basal contacts','positions'],
 five_prime_unpaired_nt:['5′ tail','nt'],three_prime_unpaired_nt:['3′ tail','nt'],left_gap:['Left insert spacer','bp'],right_gap:['Right insert spacer','bp'],
 five_prime_retained_tail_nt:['Retained from 5′ tail','nt'],three_prime_retained_tail_nt:['Retained from 3′ tail','nt'],
 five_prime_retained_tail:['5′ tail contribution',''],three_prime_retained_tail:['3′ tail contribution',''],
 loop:['Loop sequence',''],basal_pairs:['Basal pattern',''],foldback_pairs:['Loop-side pattern',''],
 left_word:['Left sticky end',''],right_word:['Right sticky end',''],left_polarity:['Left polarity',''],right_polarity:['Right polarity',''],
};

export function comparisonReader(packet,members) {
 const index=new Map(members.map((identity,i)=>[identity,i]));
 if(index.size!==members.length||!packet?.basis||!Array.isArray(packet.columns))throw Error('Invalid map comparison.');
 for(const style of Object.values(packet.presentation?.groups||{})) {
  if(typeof style.label!=='string'||!/^#[0-9a-f]{6}$/i.test(style.fill))throw Error('Invalid comparison presentation group.');
 }
 const active={shape:Object.keys(packet.basis.shape_scales),sequences:packet.basis.sequence_keys,interfaces:packet.basis.interface_keys,processing:packet.basis.processing_keys||[]};
 for(const column of packet.columns){
  const [block,key]=column.key.split('.');
  if(!names[key]||!active[block]||column.active!==active[block].includes(key)||
     !Array.isArray(column.parameters)||!Array.isArray(column.dictionary)||!Array.isArray(column.indices)||column.indices.length!==members.length||
     column.indices.some(i=>!Number.isInteger(i)||i<0||i>=column.dictionary.length))throw Error('Invalid map comparison column.');
  if(column.encoding==='contacts'&&(!Array.isArray(packet.contacts)||column.dictionary.some(v=>!Array.isArray(v)||v.some(i=>!Number.isInteger(i)||i<0||i>=packet.contacts.length))))throw Error('Invalid map comparison contact token.');
 }
 comparisonSchema(packet.presentation,Object.entries(active).flatMap(([block,keys])=>keys.map(key=>`${block}.${key}`)));
 return identity=>{
  if(!index.has(identity))throw Error('Comparison identity is outside this atlas.');
  const i=index.get(identity);
  const features=packet.columns.map(c=>{
   const value=c.dictionary[c.indices[i]];
   return {key:c.key,label:c.label,unit:c.unit,definition:c.definition,parameters:c.parameters,active:c.active,displayValue:c.key.startsWith('shape.')?value:c.indices[i],encoded:value,encoding:c.encoding,displayLabel:c.display_dictionary?.[c.indices[i]],value:c.encoding==='contacts'?value.map(t=>packet.contacts[t]):value};
  });
  const vector=Object.entries(active).flatMap(([block,keys])=>keys.map(key=>features.find(f=>f.key===`${block}.${key}`)));
  if(vector.some(f=>!f))throw Error('Map comparison lacks an active feature.');
  return {identity,algorithm:packet.algorithm,basis:packet.basis,presentation:packet.presentation,features,vector};
 };
}

function element(tag,text,className) {
 const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;
}
export function distanceDescription(block,key,basis) {
 const policy=basis.distance_policy||{};
 if(block==='processing')return 'Matching enzyme identities contribute 0; different identities contribute 1.';
 if(block==='shape')return `Absolute difference divided by the ${policy.numeric_scaling==='declared'?'declared scale':'observed range'} of ${basis.shape_scales[key]}.`;
 if(block==='sequences')return policy.regional_metric==='normalized_edit'?
  'Edit distance divided by the longer region length.':
  'Edit distance with the length difference subtracted, divided by the shorter region length and bounded to [0, 1].';
 if(key.endsWith('_word'))return policy.end_word_metric==='hamming'?
  'Compare the two 5′→3′ end sequences base by base, then divide the mismatch count by their length.':
  'Edit distance divided by the longer end-word length, in recorded strand orientation.';
 return 'Matching strand polarities contribute 0; differing polarities contribute 1.';
}
export function comparisonExplanation(feature,basis) {
 const [block,key]=feature.key.split('.'),measurement=block==='shape',contacts=['basal_pairs','foldback_pairs'].includes(key);
 const label=feature.label||names[key][0],unit=feature.unit??names[key][1],policy=basis.distance_policy||{};
 const decoded=block==='processing'?(feature.displayLabel||String(feature.value)):contacts?feature.value.map(([a,b,kind])=>`${a}:${b} ${kind.replaceAll('_',' ')}`).join(', ')||'0 contacts':Array.isArray(feature.value)?feature.value.join('')||'0 bases':String(feature.value);
 const count=block==='processing'?'enzyme':contacts?`${feature.value.length} ordered contact${feature.value.length===1?'':'s'}`:key.endsWith('_polarity')?'strand polarity':`${feature.value.length}-nt sequence`;
 const valueMeaning=measurement?`${label}: ${feature.value}${unit?' '+unit:''}.`:
  `Code ${feature.displayValue} identifies the ${contacts?'contact list':count} shown below${contacts?' ('+count+')':''}.`;
 const meaning=feature.definition?`${feature.definition} ${valueMeaning}`:valueMeaning;
 const formula=measurement?`abs(a − b) / ${basis.shape_scales[key]}`:block==='sequences'?
  (policy.regional_metric==='normalized_edit'?'edit(a, b) / max(1, m, n)':'min(1, max(0, edit(a, b) − abs(m − n)) / max(1, min(m, n)))'):
  key.endsWith('_word')?(policy.end_word_metric==='hamming'?'mismatches(a, b) / length(a)':'edit(a, b) / max(1, m, n)'):'0 if a = b, otherwise 1';
 const variables=block==='processing'?'a and b are enzyme identities from two preparations.':measurement?'a and b are measurements from two preparations.':key.endsWith('_polarity')?'a and b are the two recorded strand polarities.':key.endsWith('_word')&&policy.end_word_metric==='hamming'?'a and b are the two end sequences, each read 5′→3′.':'a and b are the two oriented regions; m and n are their lengths. An edit adds, removes or replaces one base or ordered contact.';
 return {label,display:String(feature.displayValue),kind:measurement?'Measurement':'Dictionary code',decoded,meaning,formula,variables,rule:distanceDescription(block,key,basis)};
}
function field(feature,basis,glyph=null) {
 const [block,key]=feature.key.split('.'),label=feature.label||names[key][0],unit=feature.unit??names[key][1];
 const node=element('span',undefined,'comparison-feature');node.tabIndex=0;
 node.dataset.feature=feature.key;node.dataset.parameterKeys=JSON.stringify(feature.parameters);node.dataset.active=String(feature.active);
 const title=element('span',undefined,'comparison-name'),value=element('span',undefined,'comparison-value');
 title.append(element('span',label));if(unit&&!glyph)title.append(element('span',({positions:'pos',contacts:'ct'})[unit]||unit));
 node.append(title,value);
 const measurement=block==='shape';
 node.dataset.displayKind=measurement?'measurement':'nominal-code';
 value.textContent=String(feature.displayValue);value.hidden=Boolean(glyph);
 const description=comparisonExplanation(feature,basis).decoded;
 const encoded=JSON.stringify(feature.encoded),code=element('code',encoded,'comparison-code');
 code.dataset.encoded=encoded;code.hidden=true;code.setAttribute('aria-hidden','true');
 const connector=element('span',undefined,'comparison-encoding-link');connector.setAttribute('aria-hidden','true');
 connector.hidden=true;
 node.append(connector,code);
 const contacts=['basal_pairs','foldback_pairs'].includes(key);
 const retention=key.includes('retained_tail')?' These tail bases contribute to the released insert through copying or primer binding.':'';
 const valueDescription=measurement?`${label}: ${description}${unit?' '+unit:''}.`:contacts?`${label} · code ${feature.displayValue} · ${feature.value.length} ordered contact${feature.value.length===1?'':'s'}.`:`${label} · code ${feature.displayValue} = ${description}${key.endsWith('_word')?' (5′→3′)':''}.`;
 node.title=(feature.definition?feature.definition+' ':'')+valueDescription+(feature.active?(measurement?' '+distanceDescription(block,key,basis):''):' All preparations share this value.')+retention;
 node.setAttribute('aria-label',node.title);
 if(glyph){const cue=element('span',undefined,'comparison-change-cue');cue.setAttribute('aria-hidden','true');node.append(cue,comparisonGlyph(glyph));}
 return node;
}

export function comparisonStrip(host,onFocus,help=null) {
 let packet=null,reader=null,displayed=null,displayedFields=null,explained=null,lastCommitted=null,committedPacket=null,stopCue=()=>{};
 const panel=element('div');panel.dataset.comparisonValues='true';host.append(panel);
 function explain() {
  if(!help||help.panel.hidden||!displayed)return;
  const vector=displayedFields||displayed.vector;
  if(!vector.some(f=>f.key===explained))explained=vector[0]?.key;
  help.content.replaceChildren();help.panel.dataset.preparationId=displayed.identity;
  const intro=element('p',`X lists the ${vector.length} fields used to compare these preparations. Geometry entries are measurements; sequence, end${displayed.basis.processing_keys?.length?' and enzyme':''} entries are integer codes for exact molecular values. Select a field to see its value and comparison rule.`);
  const select=element('select');select.setAttribute('aria-label','Feature explained');
  vector.forEach((f,i)=>{const option=element('option',`${i+1}. ${f.label||names[f.key.split('.')[1]][0]} = ${f.displayValue}`);option.value=f.key;select.append(option);});
  select.value=explained;select.addEventListener('change',()=>{explained=select.value;explain();help.content.querySelector('select').focus();});
  help.content.append(intro,select);
  if(!explained)return;
  const f=vector.find(f=>f.key===explained),reading=comparisonExplanation(f,displayed.basis);
  help.content.append(element('h3',`${reading.label} · X${vector.indexOf(f)+1} = ${reading.display}`),element('p',reading.meaning),element('p',reading.decoded,'comparison-decoded'),element('code',reading.formula,'comparison-formula'),element('p',reading.rule));
  help.content.append(element('p',reading.variables));
  help.content.append(element('p',`Distance averages geometry, regional sequences${displayed.basis.processing_keys?.length?', assembly ends and enzymes':' and assembly ends'} separately, then combines their means with the saved weights (geometry : sequence : ends${displayed.basis.processing_keys?.length?' : enzymes':''}) ${displayed.basis.weights.join(' : ')}. D is this weighted mean.`, 'comparison-policy'),element('code','D(a, b) = sum(w × group mean) / sum(active w)','comparison-formula'));
 }
 function dismiss(restore=false) {if(!help)return false;const open=!help.panel.hidden;help.panel.hidden=true;help.button.setAttribute('aria-expanded','false');if(open&&restore)help.button.focus();return open;}
 function reveal(key=null) {if(!help||!displayed)return;explained=key||explained;help.panel.hidden=false;help.button.setAttribute('aria-expanded','true');explain();}
 const toggle=()=>help.panel.hidden?reveal():dismiss();
 const close=()=>dismiss(true);
 if(help){help.button.addEventListener('click',toggle);help.close.addEventListener('click',close);}
 const activate=e=>{const item=e.target.closest('[data-feature]');if(item&&help){reveal(item.dataset.feature);if(e.type==='keydown')help.content.querySelector('select').focus();}};
 panel.addEventListener('click',activate);
 const keydown=e=>{if(['Enter',' '].includes(e.key)&&e.target.closest('[data-feature]')){e.preventDefault();activate(e);}};
 panel.addEventListener('keydown',keydown);
 for(const event of ['pointerover','focusin']) panel.addEventListener(event,e=>{
  const item=e.target.closest('[data-feature]');if(item)onFocus(JSON.parse(item.dataset.parameterKeys));
 });
 for(const event of ['pointerleave','focusout']) panel.addEventListener(event,e=>{if(!panel.contains(e.relatedTarget))onFocus([]);});
 return {
  prepare(identity,state) {
   const next=state?.presentation?.landscape==='similarity'?state.map_index?.comparison:null;
   if(!identity||!next)return ()=>{stopCue();lastCommitted=null;committedPacket=null;host.hidden=true;panel.replaceChildren();delete host.dataset.preparationId;displayed=null;displayedFields=null;dismiss();if(help)help.button.hidden=true;};
   if(packet!==next){reader=comparisonReader(next,state.choices.paths.map(p=>p.materialized_realization_id));packet=next;}
   const reading=reader(identity),schema=comparisonSchema(reading.presentation,reading.vector.map(f=>f.key)),content=[];
   const fields=schema?schema.display_order.map(key=>reading.vector.find(f=>f.key===key)):reading.vector;
   const heading=element('span','X = [','comparison-vector-open');
   heading.title=reading.basis.processing_keys?.length?'Map proximity uses the saved geometry, sequence, assembly-end and enzyme comparison around the fixed stem.':'Map proximity uses geometry, retained sequences and assembly ends around the fixed stem. Enzyme choices appear in the preparation record. '+(reading.basis.schema_id==='hop.molecular-comparison/v2'?'Tail fields cover bases contributing to the released insert through recorded copying or primer binding.':'Tail fields cover the complete hairpin tails.');
   content.push(heading);
   const groups=schema?Object.fromEntries(schema.schema_groups.map(group=>[group.key,group])):reading.presentation?.groups||{};
   for(const [block,style] of Object.entries(groups)) {
    const indices=fields.flatMap((f,i)=>(schema?style.fields.includes(f.key):f.key.split('.')[0]===block)?[i]:[]);
    if(!indices.length)continue;
    const visible=!schema||style.label.length*.55*schema.font_size<=indices.length*schema.field_pitch;
    const band=element('span',visible?style.label:'','comparison-group');band.dataset.featureGroup=block;band.title=style.label;band.setAttribute('aria-label',style.label);
    band.style.setProperty('grid-column',`${indices[0]+2} / ${indices.at(-1)+3}`);
    band.style.setProperty('--group-fill',style.fill||'transparent');
    content.push(band);
   }
   content.push(...fields.map((f,i)=>{
    const node=field(f,reading.basis,schema?.glyphs[f.key]);node.style.setProperty('grid-column',String(i+2));node.style.setProperty('grid-row','2 / 4');if(help){node.setAttribute('role','button');node.setAttribute('aria-controls',help.panel.id);}return node;
   }),element('span',']','comparison-vector-close'));
   return ()=>{stopCue();panel.style?.setProperty('--feature-count',String(reading.vector.length));panel.style?.setProperty('--feature-min',`${Math.max(35,...reading.vector.map(f=>String(f.displayValue).length*10))}px`);panel.replaceChildren(...content);host.dataset.preparationId=identity;host.dataset.comparisonDisplay=schema?'schematic-glyphs':'numeric-row';
    if(schema){panel.style.setProperty('--schema-font-scale',String(schema.font_size/7.2));panel.style.setProperty('--schema-field-ratio',String(schema.field_pitch/schema.font_size));panel.style.setProperty('--schema-label-angle',`${schema.label_angle}deg`);}
    if(schema&&committedPacket===packet)stopCue=cueComparisonChanges(content.filter(n=>n.dataset.feature),changedComparisonFields(lastCommitted,reading));lastCommitted=reading;committedPacket=packet;
    host.hidden=false;displayed=reading;displayedFields=fields;if(help)help.button.hidden=false;explain();};
  },
  dismiss,
  clear(){stopCue();lastCommitted=null;committedPacket=null;host.hidden=true;panel.replaceChildren();delete host.dataset.preparationId;displayed=null;displayedFields=null;dismiss();if(help)help.button.hidden=true;},
  close(){this.clear();if(help){help.button.removeEventListener('click',toggle);help.close.removeEventListener('click',close);}panel.removeEventListener('click',activate);panel.removeEventListener('keydown',keydown);},
 };
}

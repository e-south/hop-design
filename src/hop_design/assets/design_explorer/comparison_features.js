// A reading of the saved comparison basis, not a second embedding or distance model.
const names={
 loop_nt:['Loop','nt'],loop_side_paired_bp:['Added pairing','bp'],open_side_paired_positions:['Basal','positions'],
 five_prime_unpaired_nt:['5′ tail','nt'],three_prime_unpaired_nt:['3′ tail','nt'],left_gap:['Left gap','bp'],right_gap:['Right gap','bp'],
 five_prime_retained_tail_nt:['Retained from 5′ tail','nt'],three_prime_retained_tail_nt:['Retained from 3′ tail','nt'],
 five_prime_retained_tail:['5′ tail contribution',''],three_prime_retained_tail:['3′ tail contribution',''],
 loop:['Loop',''],basal_pairs:['Basal contacts',''],foldback_pairs:['Foldback contacts',''],
 left_word:['Left end',''],right_word:['Right end',''],left_polarity:['Left polarity',''],right_polarity:['Right polarity',''],
};

export function comparisonReader(packet,members) {
 const index=new Map(members.map((identity,i)=>[identity,i]));
 if(index.size!==members.length||!packet?.basis||!Array.isArray(packet.columns))throw Error('Invalid map comparison.');
 const active={shape:Object.keys(packet.basis.shape_scales),sequences:packet.basis.sequence_keys,interfaces:packet.basis.interface_keys};
 for(const column of packet.columns){
  const [block,key]=column.key.split('.');
  if(!names[key]||!active[block]||column.active!==active[block].includes(key)||
     !Array.isArray(column.parameters)||!Array.isArray(column.dictionary)||!Array.isArray(column.indices)||column.indices.length!==members.length||
     column.indices.some(i=>!Number.isInteger(i)||i<0||i>=column.dictionary.length))throw Error('Invalid map comparison column.');
  if(column.encoding==='contacts'&&(!Array.isArray(packet.contacts)||column.dictionary.some(v=>!Array.isArray(v)||v.some(i=>!Number.isInteger(i)||i<0||i>=packet.contacts.length))))throw Error('Invalid map comparison contact token.');
 }
 return identity=>{
  if(!index.has(identity))throw Error('Comparison identity is outside this atlas.');
  const i=index.get(identity);
  const features=packet.columns.map(c=>{
   const value=c.dictionary[c.indices[i]];
   return {key:c.key,label:c.label,unit:c.unit,parameters:c.parameters,active:c.active,encoded:value,encoding:c.encoding,value:c.encoding==='contacts'?value.map(t=>packet.contacts[t]):value};
  });
  const vector=Object.entries(active).flatMap(([block,keys])=>keys.map(key=>features.find(f=>f.key===`${block}.${key}`)));
  if(vector.some(f=>!f))throw Error('Map comparison lacks an active feature.');
  return {identity,algorithm:packet.algorithm,basis:packet.basis,features,vector};
 };
}

function element(tag,text,className) {
 const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;
}
export function distanceDescription(block,key,basis) {
 const policy=basis.distance_policy||{};
 if(block==='shape')return `Absolute difference divided by the ${policy.numeric_scaling==='declared'?'declared scale':'observed range'} of ${basis.shape_scales[key]}.`;
 if(block==='sequences')return policy.regional_metric==='normalized_edit'?
  'Edit distance divided by the longer region length.':
  'Edit distance with the length difference subtracted, divided by the shorter region length and bounded to [0, 1].';
 if(key.endsWith('_word'))return policy.end_word_metric==='hamming'?
  'Equal-length end words compared by positionwise mismatch fraction, in recorded strand orientation.':
  'Edit distance divided by the longer end-word length, in recorded strand orientation.';
 return 'Polarity is nominal: equal or different.';
}
function field(feature,basis) {
 const [block,key]=feature.key.split('.'),label=feature.label||names[key][0],unit=feature.unit??names[key][1];
 const node=element('span',undefined,'comparison-feature');node.tabIndex=0;
 node.dataset.feature=feature.key;node.style?.setProperty('--comparison-weight',String(feature.encoding==='contacts'?Math.max(1,feature.value.length/6):1));node.dataset.parameterKeys=JSON.stringify(feature.parameters);node.dataset.active=String(feature.active);
 const title=element('span',undefined,'comparison-name'),value=element('span',undefined,'comparison-value');
 title.append(element('span',label));if(unit)title.append(element('span',unit));
 node.append(title,value);
 let description;
 if(block==='sequences'&&['basal_pairs','foldback_pairs'].includes(key)){
  // Both rows follow the descriptor's ordered contacts. These are not two
  // independently authored strands, and contact classes remain part of the data.
  const upper=element('span'),lower=element('span'),glyphs=element('span',undefined,'comparison-contact-glyphs');
  feature.value.forEach(([a,b,kind])=>{
   for(const [row,base] of [[upper,a],[lower,b]]){
    const letter=element('span',base);letter.dataset.contactClass=kind;row.append(letter);
   }
   const glyph=document.createElementNS('http://www.w3.org/2000/svg','svg');
   glyph.setAttribute('viewBox','0 0 8 12');glyph.setAttribute('aria-hidden','true');
   glyph.dataset.contactGlyph=kind==='watson_crick'?'line':'diamond';glyph.dataset.contactClass=kind;
   const path=document.createElementNS('http://www.w3.org/2000/svg','path');
   path.setAttribute('d',kind==='watson_crick'?'M4,0 V12':'M4,1 L7,6 L4,11 L1,6 Z');
   path.setAttribute('fill','none');path.setAttribute('stroke','currentColor');path.setAttribute('stroke-width','1');
   glyph.append(path);glyphs.append(glyph);
  });
  if(!feature.value.length)upper.textContent='∅';
  value.append(upper,glyphs,lower);value.classList.add('comparison-pairs');
  description=feature.value.map(([a,b,kind])=>`${a}:${b} ${kind.replaceAll('_',' ')}`).join('; ')||'No paired positions';
 } else {
  const text=block==='sequences'?(feature.value.join('')||'∅'):key.endsWith('polarity')?({'five_prime':'5′','three_prime':'3′'}[feature.value]):String(feature.value);
  value.textContent=text;description=`${text}${unit?' '+unit:''}`;
 }
 const encoded=JSON.stringify(feature.encoded),code=element('code',encoded,'comparison-code');
 code.dataset.encoded=encoded;code.hidden=true;code.setAttribute('aria-hidden','true');
 const connector=element('span',undefined,'comparison-encoding-link');connector.setAttribute('aria-hidden','true');
 connector.hidden=true;
 node.append(connector,code);
 const scale=feature.active?' '+distanceDescription(block,key,basis):'';
 const retention=key.includes('retained_tail')?' Hairpin-tail bases contributing through recorded copying or primer binding to either insert strand; each template base is counted once.':'';
 const encoding=feature.encoding==='contacts'?' Stored nominal IDs preserve these displayed ordered contacts and classes; they have no numerical ordering.':'';
 node.title=`${label}: ${description}. ${feature.active?'Used in molecular distance.':'Constant in this atlas; does not affect distance.'}${scale}${retention}${encoding}`;
 node.setAttribute('aria-label',node.title);return node;
}

export function comparisonStrip(host,onFocus) {
 let packet=null,reader=null;
 const panel=element('div');panel.dataset.comparisonValues='true';host.append(panel);
 for(const event of ['pointerover','focusin']) panel.addEventListener(event,e=>{
  const item=e.target.closest('[data-feature]');if(item)onFocus(JSON.parse(item.dataset.parameterKeys));
 });
 for(const event of ['pointerleave','focusout']) panel.addEventListener(event,e=>{if(!panel.contains(e.relatedTarget))onFocus([]);});
 return {
  prepare(identity,state) {
   const next=state?.presentation?.landscape==='similarity'?state.map_index?.comparison:null;
   if(!identity||!next)return ()=>{host.hidden=true;panel.replaceChildren();delete host.dataset.preparationId;};
   if(packet!==next){reader=comparisonReader(next,state.choices.paths.map(p=>p.materialized_realization_id));packet=next;}
   const reading=reader(identity),content=[];
   const heading=element('span','Mixed-type molecular features','comparison-reading-key');
   heading.title='Molecular descriptors define dissimilarity; the layout uses that dissimilarity, not Euclidean distance on these displayed values. The supplied stem is held fixed; methods are excluded. '+(reading.basis.schema_id==='hop.molecular-comparison/v2'?'Only tail bases contributing through recorded copying or primer binding to the released insert affect distance; discarded handle changes do not move the scaffold.':'This saved comparison includes complete hairpin tail lengths.');
   const groups=new Map(),labels={shape:'Geometry',sequences:'Contacts and loop',interfaces:'Assembly ends'};
   for(const feature of reading.vector){
    const label=labels[feature.key.split('.')[0]];
    if(!groups.has(label)){
     const group=element('section',undefined,'comparison-group');group.dataset.featureGroup=label;group.title=heading.title;
     group.append(element('h3',label));groups.set(label,group);
    }
    groups.get(label).append(field(feature,reading.basis));
   }
   content.push(...groups.values());
   return ()=>{panel.replaceChildren(...content);host.dataset.preparationId=identity;host.dataset.comparisonDisplay='typed-features';host.hidden=false;};
  },
  clear(){host.hidden=true;panel.replaceChildren();delete host.dataset.preparationId;},
 };
}

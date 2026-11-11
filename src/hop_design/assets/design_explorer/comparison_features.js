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
 for(const style of Object.values(packet.presentation?.groups||{})) {
  if(typeof style.label!=='string'||!/^#[0-9a-f]{6}$/i.test(style.fill))throw Error('Invalid comparison presentation group.');
 }
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
   return {key:c.key,label:c.label,unit:c.unit,parameters:c.parameters,active:c.active,displayValue:c.key.startsWith('shape.')?value:c.indices[i],encoded:value,encoding:c.encoding,value:c.encoding==='contacts'?value.map(t=>packet.contacts[t]):value};
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
 node.dataset.feature=feature.key;node.dataset.parameterKeys=JSON.stringify(feature.parameters);node.dataset.active=String(feature.active);
 const title=element('span',undefined,'comparison-name'),value=element('span',undefined,'comparison-value');
 title.append(element('span',label));if(unit)title.append(element('span',({positions:'pos',contacts:'ct'})[unit]||unit));
 node.append(title,value);
 const measurement=block==='shape';
 node.dataset.displayKind=measurement?'measurement':'nominal-code';
 value.textContent=String(feature.displayValue);
 const description=['basal_pairs','foldback_pairs'].includes(key)?
   feature.value.map(([a,b,kind])=>`${a}:${b} ${kind.replaceAll('_',' ')}`).join('; ')||'No paired positions':
   Array.isArray(feature.value)?feature.value.join('')||'∅':String(feature.value);
 const encoded=JSON.stringify(feature.encoded),code=element('code',encoded,'comparison-code');
 code.dataset.encoded=encoded;code.hidden=true;code.setAttribute('aria-hidden','true');
 const connector=element('span',undefined,'comparison-encoding-link');connector.setAttribute('aria-hidden','true');
 connector.hidden=true;
 node.append(connector,code);
 const scale=feature.active?' '+distanceDescription(block,key,basis):'';
 const retention=key.includes('retained_tail')?' Hairpin-tail bases contributing through recorded copying or primer binding to either insert strand; each template base is counted once.':'';
 const encoding=measurement?'':` Code ${feature.displayValue} identifies this exact field value in the atlas dictionary; code magnitudes are not distances.`;
 node.title=`${label}: ${description}${measurement&&unit?' '+unit:''}. ${feature.active?'Used in molecular distance.':'Constant in this atlas; does not affect distance.'}${scale}${retention}${encoding}`;
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
   const heading=element('span','X = [','comparison-vector-open');
   heading.title='Molecular descriptors define dissimilarity; the layout uses that dissimilarity, not Euclidean distance on these displayed values. The supplied stem is held fixed; methods are excluded. '+(reading.basis.schema_id==='hop.molecular-comparison/v2'?'Only tail bases contributing through recorded copying or primer binding to the released insert affect distance; discarded handle changes do not move the scaffold.':'This saved comparison includes complete hairpin tail lengths.');
   content.push(heading);
   const groups=reading.presentation?.groups||{};
   for(const [block,style] of Object.entries(groups)) {
    const indices=reading.vector.flatMap((f,i)=>f.key.split('.')[0]===block?[i]:[]);
    if(!indices.length)continue;
    const band=element('span',style.label,'comparison-group');band.dataset.featureGroup=block;
    band.style.setProperty('grid-column',`${indices[0]+2} / ${indices.at(-1)+3}`);
    band.style.setProperty('--group-fill',style.fill);
    content.push(band);
   }
   content.push(...reading.vector.map((f,i)=>{
    const node=field(f,reading.basis);node.style.setProperty('grid-column',String(i+2));node.style.setProperty('grid-row','2 / 4');return node;
   }),element('span',']','comparison-vector-close'));
   return ()=>{panel.style?.setProperty('--feature-count',String(reading.vector.length));panel.replaceChildren(...content);host.dataset.preparationId=identity;host.dataset.comparisonDisplay='numeric-row';host.hidden=false;};
  },
  clear(){host.hidden=true;panel.replaceChildren();delete host.dataset.preparationId;},
 };
}

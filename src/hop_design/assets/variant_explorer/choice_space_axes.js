"use strict";
import {$, node} from "./common.js";
export function renderMolecularControls(space, focus, filters, onFocus, onClear) {
  const axes=space.axes;
  const host=$("choice-axis-controls"); host.replaceChildren();
  const intent=node('div',''); intent.className='molecular-context';
  for(const key of ['foldback_method','release_method','left_end_word','left_end_polarity','right_end_word','right_end_polarity']) {
    const axis=axes.find(a=>a.key===key); if(!axis)continue;
    const values=axis.declared?.values;
    const basis=values?.length ? (values.length===1?'fixed by request':'permitted') : 'recorded';
    const names=(values||axis.values.map(v=>v.value)).map(v=>({five_prime:"5′",three_prime:"3′"}[v] || axis.values.find(e=>e.value===v)?.label || String(v)));
    const button=node('button',`${axis.label}: ${names.join(' / ')} · ${basis}`);
    button.className='quiet';button.onclick=()=>onFocus(key);intent.append(button);
  }
  host.append(intent);
  const pairs=space.joint_permissions?.receiving_end_pairs;
  if(pairs?.length){
    const roster=node('details','');roster.open=true;
    roster.append(node('summary',`${pairs.length} declared receiving-end pairs · no cross-combinations`));
    const same=(a,b)=>a&&['left','right'].every(side=>['cohesive_end_sequence','overhang_end','orientation','payload_end_offset_bp'].every(k=>a[side][k]===b[side][k]));
    for(const pair of pairs){
      const records=(space.branch_coverage||[]).filter(b=>same(b.receiving_end_pair,pair));
      const complete=new Set(records.flatMap(b=>b.option_labels)), examined=records.filter(b=>b.status==='evaluated').length;
      const excluded=records.filter(b=>Object.values(b.local_coverage||{}).some(c=>c.completion==='complete'&&c.feasibility==='infeasible'&&c.termination_reason==='exhausted_domain')).length;
      const ends=['left','right'].map(side=>{const e=pair[side];return `${side}: ${e.cohesive_end_sequence} · ${e.overhang_end==='five_prime'?'5′':'3′'} · ${e.orientation} site · ${e.payload_end_offset_bp} bp`;});
      roster.append(node('p',`${ends.join(' / ')} — ${complete.size} complete preparations; ${examined}/${records.length} branches examined${excluded?`; ${excluded} exhausted local exclusion(s)`:''}.`));
    }
    host.append(roster);
  }
  const navigation=node('div','');navigation.className='molecular-context';
  if(focus){const reset=node('button','Return to molecular overview');reset.className='quiet';reset.onclick=()=>onFocus(null);navigation.append(reset);}
  navigation.append(node('span',focus?`Detail: ${axes.find(a=>a.key===focus)?.label}`:'Select a molecular feature above for related quantities. R = A − D; loop length follows its word.'));
  for(const [key,values] of Object.entries(filters)) {
    const axis=axes.find(a=>a.key===key),text=Array.isArray(values)?values.map(v=>axis.values.find(e=>e.value===v)?.label||v).join(' or '):`${values.minimum}–${values.maximum}`;
    const button=node('button',`${axis.label}: ${text} ×`);button.className='quiet';button.onclick=()=>onClear(key);button.setAttribute('aria-label',`Clear ${axis.label} selection`);navigation.append(button);
  }
  host.append(navigation);
  const meanings=node('details',''); meanings.append(node('summary','All parameter meanings'));
  const list=node('div','');list.className='parameter-features';
  for(const axis of axes){const button=node('button',axis.symbol?`${axis.symbol} · ${axis.label}`:axis.label);button.className='quiet';button.onclick=()=>onFocus(axis.key);button.title=`${axis.measurement} ${axis.relationship||''}`;list.append(button);}
  meanings.append(list);host.append(meanings);
}

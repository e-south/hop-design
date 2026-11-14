// HOP Design
// hop-design/src/hop_design/assets/design_explorer/choice_frequencies_model.js
// Group recorded choices by exact preparation membership without changing eligibility.
// Module Author(s): Eric J. South

const roleNames={source_ssdna:'Source oligo',ligation_adapter:'Y adapter',source_materialization_forward_primer:'Source PCR forward',source_materialization_reverse_primer:'Source PCR reverse',endpoint_forward_primer:'Hairpin PCR forward',endpoint_reverse_primer:'Hairpin PCR reverse'};
export function frequencyIndex(choices) {
  const paths=choices.paths,seen=new Set(),names=new Map(),cache=new Map();
  for(const p of paths) {
    if(!p.materialized_realization_id||seen.has(p.materialized_realization_id))throw Error('Invalid frequency preparation identity.');
    seen.add(p.materialized_realization_id);
    for(const method of p.methods||[])names.set(method.enzyme_id,method.name);
  }
  const canonical=new Set();
  const fields=choices.axes.filter(a=>{const key=a.canonical_key||a.key;if(canonical.has(key))return false;canonical.add(key);return true;}).map(a=>({key:`parameter:${a.key}`,label:a.label,group:'Parameter choices',read:p=>p.values[a.key]??null}));
  if(choices.axes.some(a=>a.key==='left_end_word')&&choices.axes.some(a=>a.key==='right_end_word'))
    fields.push({key:'assembly:end_pairs',label:'Sticky-end pairs',group:'Assembly interfaces',read:p=>p.values.left_end_word&&p.values.right_end_word?[p.values.left_end_word,p.values.right_end_word]:null});
  const roles=[...new Set(paths.flatMap(p=>Object.keys(p.material_roles||{})))].sort();
  for(const role of roles)fields.push({key:`material:${role}`,label:roleNames[role]||role.replaceAll('_',' '),group:'Oligonucleotides',read:p=>p.material_roles?.[role]?.material_id??null,role});
  function buckets(field) {
    if(cache.has(field.key))return cache.get(field.key);
    const groups=new Map();
    for(const p of paths) {
      const value=field.read(p),key=JSON.stringify(value);
      if(!groups.has(key)) {
        const labelValue=v=>names.get(v)??(typeof v==='object'?JSON.stringify(v):String(v));
        let label=value===null?'Not applicable':Array.isArray(value)?value.map(labelValue).join(' / '):labelValue(value);
        if(field.role&&value!==null) {
          const material=p.material_roles[field.role],short=value.split('/').at(-1).split('@')[0].replace('sha256:','').slice(0,10);
          label=`${short} · ${material.length_nt} nt`;
        }
        groups.set(key,{key,label,value,members:[],eligible:0});
      }
      const row=groups.get(key);row.members.push(p.materialized_realization_id);if(p.matches)row.eligible++;
    }
    const rows=[...groups.values()].map(row=>({...row,count:row.members.length})).sort((a,b)=>b.count-a.count||a.key.localeCompare(b.key));
    cache.set(field.key,rows);return rows;
  }
  return {
    fields:fields.map(({read,...field})=>field),
    profile(key,limit=12) {
      if(!Number.isInteger(limit)||limit<1)throw Error('Frequency row limit must be positive.');
      const field=fields.find(f=>f.key===key);if(!field)throw Error('Unknown frequency component.');
      const all=buckets(field),rows=all.slice(0,limit),rest=all.slice(limit);
      if(rest.length)rows.push({key:'other',label:`Other ${rest.length.toLocaleString()} choices`,other:true,value:null,members:rest.flatMap(r=>r.members),count:rest.reduce((n,r)=>n+r.count,0),eligible:rest.reduce((n,r)=>n+r.eligible,0)});
      return {total:paths.length,choices:all.length,rows};
    },
  };
}

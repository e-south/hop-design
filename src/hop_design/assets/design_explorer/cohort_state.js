// A transport omission is valid only for the exact cohort already held by this client.
function decodeCompact(packet) {
  if(packet.schema!=='hop.inspection-cohort/v1' || !Array.isArray(packet.members) ||
     packet.members.some(id=>typeof id!=='string'||!id) || new Set(packet.members).size!==packet.members.length)
    throw Error('Invalid compact cohort members.');
  const n=packet.members.length;
  if(!Array.isArray(packet.matches)||packet.matches.length!==n||packet.matches.some(v=>typeof v!=='boolean'))
    throw Error('Invalid compact cohort eligibility.');
  function column(value) {
    if(!value || !Array.isArray(value.dictionary)||!Array.isArray(value.indices)||value.indices.length!==n||
       value.indices.some(i=>!Number.isInteger(i)||i<0||i>=value.dictionary.length))
      throw Error('Invalid compact cohort column reference.');
    return i=>value.dictionary[value.indices[i]];
  }
  const values=Object.entries(packet.values).map(([key,c])=>[key,column(c)]);
  const roles=Object.entries(packet.roles).map(([key,c])=>[key,column(c)]),methods=column(packet.methods);
  const row=(columns,i)=>Object.fromEntries(columns.map(([key,get])=>[key,get(i)]).filter(([,v])=>v!==null));
  return {...packet.choices,paths:packet.members.map((id,i)=>({materialized_realization_id:id,matches:packet.matches[i],
    values:row(values,i),methods:methods(i),material_roles:row(roles,i)}))};
}
export function hydrateCohort(value, previous) {
  if(value.compact) {const {compact,...rest}=value;return {...rest,choices:decodeCompact(compact)};}
  if(!('cohort_unchanged' in value)||value.cohort_unchanged===false) return value;
  if(value.cohort_unchanged!==true || !previous || value.cohort!==previous.cohort || !previous.choices || (!previous.families&&!previous.map_index))
    throw Error('Inspection response does not match the retained cohort. Reopen this atlas.');
  return {...value,choices:previous.choices,families:previous.families,feature_parameters:previous.feature_parameters,...(previous.map_index?{map_index:previous.map_index}:{}),...(previous.cohort_summary?{cohort_summary:previous.cohort_summary}:{})};
}

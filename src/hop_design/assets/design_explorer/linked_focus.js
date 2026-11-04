// Session-owned indexes preserve exact membership without rescanning the cohort on hover.
export function preparationIndex(state) {
  const paths=new Map(state.choices.paths.map(p=>[p.materialized_realization_id,p]));
  const familyRows=new Map((state.families?.families||[]).map(f=>[f.identity,f]));
  const memberships=new Map([...paths.keys()].map(id=>[id,{keys:new Set(),families:new Set()}]));
  for(const product of state.families?.products||[])
    for(const id of product.preparations)
      for(const key of Object.keys(product.features)) memberships.get(id)?.keys.add(key);
  for(const family of state.families?.families||[])
    for(const id of family.preparations) memberships.get(id)?.families.add(family.identity);
  function rows(identities) {
    return [...new Set(identities)].map(id=>{
      if(!paths.has(id)) throw Error('Focused preparation is absent from the recorded pool.');
      return paths.get(id);
    });
  }
  return {
    rows,
    family: id=>familyRows.get(id),
    focus(identities) {
      const found=rows(identities);
      return {
        preparations:found.map(p=>p.materialized_realization_id),
        eligible:found.filter(p=>p.matches).length,
        families:[...new Set(found.flatMap(p=>[...memberships.get(p.materialized_realization_id).families]))],
        keys:[...new Set(found.flatMap(p=>[...memberships.get(p.materialized_realization_id).keys]))],
      };
    },
  };
}

export function linkedMarks(root, atlas) {
  const families=new Map((atlas?.families||[]).map(f=>[f.identity,f.preparations]));
  const byIdentity=new Map(), sizes=new Map();
  let focused=new Set(), pinned=new Set();
  for(const element of root.querySelectorAll('[data-members],[data-preparations],[data-family-ids]')) {
    const d=element.dataset;
    const values=d.familyIds?JSON.parse(d.familyIds).flatMap(id=>families.get(id)||[]):JSON.parse(d.members||d.preparations);
    // Molecular ribbons carry [strand, index] addresses under data-members.
    // Only preparation-ID memberships participate in landscape highlighting.
    if(!Array.isArray(values)||!values.every(id=>typeof id==='string'))continue;
    const members=new Set(values);
    element.setAttribute('data-choice-mark','true');
    sizes.set(element,members.size);
    for(const id of members) {
      if(!byIdentity.has(id)) byIdentity.set(id,new Set());
      byIdentity.get(id).add(element);
    }
  }
  function counts(identities) {
    const result=new Map();
    for(const id of new Set(identities)) for(const element of byIdentity.get(id)||[])
      result.set(element,(result.get(element)||0)+1);
    return result;
  }
  return {
    focus(value) {
      for(const element of focused) {element.removeAttribute('data-linked-count');element.removeAttribute('data-linked-total');}
      const current=counts(value?.preparations||[]);focused=new Set(current.keys());
      for(const [element,count] of current) {
        element.setAttribute('data-linked-count',count);
        element.setAttribute('data-linked-total',sizes.get(element));
      }
      root.classList.toggle('linked-focus',Boolean(value));
    },
    pin(identity) {
      for(const element of pinned) element.setAttribute('data-selected','false');
      pinned=new Set(counts(identity?[identity]:[]).keys());
      for(const element of pinned) element.setAttribute('data-selected','true');
    },
    close() {this.focus(null);this.pin(null);for(const element of sizes.keys())element.removeAttribute('data-choice-mark');byIdentity.clear();sizes.clear();},
  };
}

// These are projections of the same admitted preparation, never molecular inference.
export function inspectionFacts(host) {
  const reference=host.querySelector('[data-reference]'),description=host.querySelector('[data-description]'),costLabel=host.querySelector('[data-cost]');
  function clear(){delete host.dataset.preparationId;delete host.dataset.referenceId;reference.textContent=description.textContent=costLabel.textContent='';reference.title='';}
  return {
    prepare(identity,explanation,cost,{preview=false,referencePinned=true,productLabel=null}={}) {
      if(!identity)return clear;
      if(explanation?.materialized_realization_id!==identity || cost&&cost.materialized_realization_id!==identity)
        throw Error('Inspection facts disagree with the molecular identity.');
      if(cost&&(typeof productLabel!=='string'||!productLabel.trim()))throw Error('Inspection cost requires its projected product label.');
      const strands=Object.entries(cost?.added_nt_by_strand??{});
      const added=strands.map(([name,n])=>`${strands.length===1?'hairpin':name} ${n} nt`).join('; ');
      const roles=cost?.material_roles?` for ${cost.material_roles} material roles`:'';
      const ordered=Number.isInteger(cost?.ordered_nt)?` Total ordered DNA: ${cost.ordered_nt} nt.`:'';
      const costText=cost?`${productLabel}: added DNA — ${added}. ${cost.distinct_orders} distinct oligo orders${roles}.${ordered}`:'';
      return ()=>{
        host.dataset.preparationId=identity;host.dataset.referenceId=explanation.reference_identity??'';
        reference.textContent=explanation.reference_identity?(preview?(referencePinned?'Compared with pinned: ':'Compared with retained inspection: '):'Compared with reference: '):'';
        reference.title=explanation.reference_identity??'';
        description.textContent=explanation.reference_identity?explanation.description:'';
        costLabel.textContent=costText;
      };
    },
    clear,
  };
}

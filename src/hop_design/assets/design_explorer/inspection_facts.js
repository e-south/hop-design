// These are projections of the same admitted preparation, never molecular inference.
const endpoints={clone_ready_duplex:'Released insert',ssdna_hairpin:'Hairpin',adapter_ligated_hairpin:'Adapter-ligated hairpin'};
export function inspectionFacts(host) {
  const reference=host.querySelector('[data-reference]'),description=host.querySelector('[data-description]'),costLabel=host.querySelector('[data-cost]');
  function clear(){delete host.dataset.preparationId;delete host.dataset.referenceId;reference.textContent=description.textContent=costLabel.textContent='';reference.title='';}
  return {
    prepare(identity,explanation,cost,{preview=false,referencePinned=true}={}) {
      if(!identity)return clear;
      if(explanation?.materialized_realization_id!==identity || cost&&cost.materialized_realization_id!==identity)
        throw Error('Inspection facts disagree with the molecular identity.');
      const strands=Object.entries(cost?.added_nt_by_strand??{});
      const added=strands.map(([name,n])=>`${strands.length===1?'hairpin':name} ${n} nt`).join('; ');
      const roles=cost?.material_roles?` covering ${cost.material_roles} roles`:'';
      const costText=cost?`${endpoints[cost.endpoint]??'Selected product'}: added DNA — ${added}. ${cost.distinct_orders} distinct oligo orders${roles}.`:'';
      return ()=>{
        host.dataset.preparationId=identity;host.dataset.referenceId=explanation.reference_identity??'';
        reference.textContent=explanation.reference_identity?(preview?(referencePinned?'From pinned: ':'From retained inspection: '):'From reference: '):'';
        reference.title=explanation.reference_identity??'';
        description.textContent=explanation.reference_identity?explanation.description:'';
        costLabel.textContent=costText;
      };
    },
    clear,
  };
}

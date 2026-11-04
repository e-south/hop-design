// Deliberate comparison inspection; molecular verification stays in the shared API.
export function neighboringChoices(details, host, post, current, select) {
  let serial=0, pending=null;
  const cancel=()=>{
    serial++;
    if(pending) {const request_id=pending;pending=null;void post('cancel-neighbors',{request_id}).catch(()=>{});}
  };
  const clear=()=>{cancel();details.open=false;host.replaceChildren();};
  const open=async(verify=false)=>{
    if(!details.open) {cancel();return;}
    const ticket=++serial,state=current(),token=state.token;
    if(!state.has_landscape){host.textContent='Capture molecular coordinates to inspect nearby alternatives.';return;}
    const request_id=crypto.randomUUID();pending=request_id;
    host.textContent=verify?'Checking shared surroundings…':'Finding nearby constructions…';
    try {
      const result=await post('neighbors',{verify_controls:verify,request_id});
      if(ticket!==serial || current().token!==token || !details.open) return;
      const rows=result.neighbors.slice(0,3);
      if(!rows.length){host.textContent='No other eligible preparation in this recorded pool.';return;}
      host.replaceChildren(...rows.map(row=>{
        const button=document.createElement('button');button.textContent=row.description;
        button.addEventListener('click',()=>select(row.materialized_realization_id));return button;
      }));
      if(!verify && rows.some(row=>row.coordinate_changes.some(change=>change.key==='loop_word'))) {
        const check=document.createElement('button');check.textContent='Check shared surroundings';
        check.addEventListener('click',()=>open(true));host.append(check);
      }
      if(result.preservation_notice){const note=document.createElement('p');note.textContent=result.preservation_notice;host.append(note);}
    }catch(error){if(ticket===serial && current().token===token)host.textContent=error.message;}
    finally {if(ticket===serial)pending=null;}
  };
  const toggle=()=>open(false);
  details.addEventListener('toggle',toggle);
  return {clear,close(){clear();details.removeEventListener('toggle',toggle);}};
}

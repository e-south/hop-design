// Discovery owns a separate branch. Its progress never replaces the inspected pool.
export function discoveryControls(get, post, {schedule=setTimeout,cancel=clearTimeout,inspect=null}={}) {
  let job=null, serial=0, timer=null, closed=false, initialized=false, available=false, submitting=false;
  const active=()=>job&&['running','stopping'].includes(job.status);
  const inspectable=()=>inspect&&['completed','cancelled'].includes(job?.status)&&job?.matching_preparations>0;
  const clearTimer=()=>{if(timer!==null)cancel(timer);timer=null;};
  function paint() {
    const running=active(), progress=job?.progress;
    get('discovery-start').disabled=!available||Boolean(running)||submitting;
    get('discovery-continue').hidden=!job?.can_continue||Boolean(running);
    get('discovery-continue').disabled=submitting;
    get('discovery-inspect').hidden=!inspectable();get('discovery-inspect').disabled=submitting;
    get('discovery-stop').hidden=!running;
    get('discovery-stop').disabled=job?.status==='stopping';
    get('discovery-progress').hidden=!progress;
    if(progress){get('discovery-progress').max=progress.evaluation_budget;get('discovery-progress').value=progress.new_evaluations;}
    const committed=progress?`${progress.new_evaluations} / ${progress.evaluation_budget} evaluations committed`:'';
    const count=job?.matching_preparations;
    const outcomes={
      running:'Searching',stopping:'Stopping after the current evaluation',
      completed:`Finished${count===null||count===undefined?'':` · ${count} complete preparations saved`}`,
      cancelled:count===null||count===undefined?'Stopped before a first snapshot':'Stopped',
      failed:'Search failed',interrupted:'Search interrupted',
    };
    get('discovery-status').textContent=job?[outcomes[job.status],committed,job.message].filter(Boolean).join(' · '):
      (available?'Search a separate branch while keeping this atlas open.':'Discovery feedback currently requires one exact stem.');
    get('discovery-result').hidden=!job?.command;
    get('discovery-command').textContent=job?.command||'';
  }
  function queue() {
    clearTimer();if(closed||!active())return;
    timer=schedule(poll,500);
  }
  async function poll() {
    timer=null;if(closed||!active())return;
    const ticket=serial,id=job.id;
    try {
      const next=await post('status-discovery',{job_id:id},{independent:true});
      if(closed||ticket!==serial||job?.id!==id)return;
      job=next;paint();
    } catch(error) {if(!closed&&ticket===serial)get('discovery-status').textContent=error.message;}
    finally {if(!closed&&ticket===serial)queue();}
  }
  async function begin(continuing=false) {
    if(closed||submitting||active())return;
    const ticket=++serial;clearTimer();submitting=true;paint();
    get('discovery-result').hidden=true;get('discovery-progress').hidden=true;
    try {
      const evaluations=Number(get('discovery-evaluations').value);
      if(!Number.isInteger(evaluations)||evaluations<1)throw Error('Choose a positive evaluation budget.');
      const payload=continuing?{job_id:job.id,evaluations}:{request:JSON.parse(get('discovery-request').value),evaluations};
      get('discovery-status').textContent='Starting search…';
      const next=await post(continuing?'continue-discovery':'start-discovery',payload,{independent:true});
      if(closed||ticket!==serial){if(['running','stopping'].includes(next.status))void post('stop-discovery',{job_id:next.id},{independent:true,keepalive:true}).catch(()=>{});return;}
      job=next;paint();queue();
    } catch(error) {if(!closed&&ticket===serial)get('discovery-status').textContent=error.message;}
    finally {submitting=false;if(!closed&&ticket===serial){get('discovery-start').disabled=!available||Boolean(active());get('discovery-continue').disabled=false;}}
  }
  async function stop() {
    if(closed||!active())return;
    const ticket=++serial,id=job.id;clearTimer();job={...job,status:'stopping'};paint();
    try {
      const next=await post('stop-discovery',{job_id:id},{independent:true});
      if(closed||ticket!==serial||job?.id!==id)return;
      job=next;paint();
    } catch(error) {if(!closed&&ticket===serial)get('discovery-status').textContent=error.message;}
    finally {if(!closed&&ticket===serial)queue();}
  }
  async function openResults() {
    if(closed||submitting||!inspectable())return;
    const ticket=++serial,id=job.id;clearTimer();submitting=true;paint();
    get('discovery-status').textContent='Opening saved preparations…';
    let failure=null;
    try {await inspect(id);}
    catch(error){failure=error.message;}
    finally {
      submitting=false;
      if(!closed&&ticket===serial&&job?.id===id){paint();if(failure)get('discovery-status').textContent=failure;}
    }
  }
  const start=()=>begin(false),resume=()=>begin(true);
  get('discovery-start').addEventListener('click',start);
  get('discovery-continue').addEventListener('click',resume);
  get('discovery-stop').addEventListener('click',stop);
  get('discovery-inspect').addEventListener('click',openResults);
  return {
    update(state){
      if(closed||initialized)return;initialized=true;available=Boolean(state.discovery_request);
      if(available)get('discovery-request').value=JSON.stringify(state.discovery_request,null,2);
      job=state.discovery_work;paint();queue();
    },
    close(){
      if(closed)return;closed=true;serial++;clearTimer();
      if(active())void post('stop-discovery',{job_id:job.id},{independent:true,keepalive:true}).catch(()=>{});
      get('discovery-start').removeEventListener('click',start);
      get('discovery-continue').removeEventListener('click',resume);
      get('discovery-stop').removeEventListener('click',stop);
      get('discovery-inspect').removeEventListener('click',openResults);
    },
  };
}

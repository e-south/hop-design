import {panelStatus} from './panel_status.js';
import {routeSceneWork} from './route_scene_work.js';

export function retainedSceneAnchor(phases,current,retained) {
  const index=phases.indexOf(current),keep=new Set(retained);
  if(index<0)return null;
  for(let distance=0;distance<phases.length;distance++) {
    for(const candidate of [phases[index+distance],phases[index-distance]])
      if(candidate!==undefined && keep.has(candidate))return candidate;
  }
  return null;
}

export function sceneSlotGeometry(current,frame,pinned) {
  const values=typeof frame==='string'?frame.trim().split(/\s+/).map(Number):[];
  if(values.length!==4 || values.some(v=>!Number.isFinite(v)) || values[0]!==0 || values[1]!==0 || values[2]<=0 || values[3]<=0)
    throw Error('Invalid molecular scene frame.');
  // Hover uses the pin's measured slot; only a committed preparation can reflow it.
  return pinned?{width:values[2],height:values[3]}:current;
}

export function previewScenePhases(view,teaching,phases) {
  // Keep the fast hairpin-only request whenever its panel is visible. When the
  // route owns the viewport, one request can share its molecular projection.
  return teaching.bottom>view.top && teaching.top<view.bottom?[]:phases;
}

// One stable slot per processing phase. Only visible slots acquire drawings;
// the pin retains at most four scene nodes for immediate restoration.
export function routeScenes(host,scroll,request,artifacts) {
  const slots=new Map(),pinnedNodes=new Map();
  let pinned=null,context=null,ready=false,closed=false,frame=null,lastRequest=null,pinnedRoster=null;
  const contextKey=c=>c?JSON.stringify([c.identity,c.token,c.snapshot,c.policy,c.presentation]):'';
  const drawingKey=(c,phase)=>JSON.stringify([c.identity,c.snapshot,c.policy,c.presentation,phase]);
  const work=routeSceneWork(request,async(value,job)=>{
    const drawings=await Promise.all(value.scenes.map(async scene=>{
      const doc=new DOMParser().parseFromString(await artifacts.text(scene.drawing),'image/svg+xml');
      const svg=doc.documentElement;
      if(doc.querySelector('parsererror') || svg.dataset.preparationId!==job.identity || svg.dataset.routeScene!==scene.state_id || svg.querySelector('[data-atlas-phase]')?.dataset.atlasPhase!==scene.phase || svg.getAttribute('viewBox')!==scene.frame) throw Error('Route drawing disagrees with the requested preparation, phase or frame.');
      svg.setAttribute('preserveAspectRatio','xMidYMin meet');
      return [scene.phase,svg,scene.frame];
    }));
    return ()=>{
      if(!ready || contextKey(context)!==contextKey(job)) return;
      const pinnedResult=contextKey(pinned)===contextKey(job);
      const updates=drawings.map(([phase,svg,frame])=>[phase,svg,sceneSlotGeometry(slots.get(phase)?.geometry||null,frame,pinnedResult)]);
      if(pinnedResult && value.roster?.length) {pinnedRoster=value.roster;setRoster(pinnedRoster);}
      const saved=pinnedResult?anchor([...slots.keys()]):null;
      for(const [phase,svg,geometry] of updates) {
        const slot=slots.get(phase);if(!slot) continue;
        if(geometry) {slot.geometry=geometry;slot.element.style.aspectRatio=`${geometry.width} / ${geometry.height}`;}
        slot.body.replaceChildren(svg);slot.shown=drawingKey(job,phase);slot.failed=null;slot.unavailable=null;slot.status.clear();
        if(pinnedResult) {
          const key=drawingKey(job,phase);pinnedNodes.delete(key);pinnedNodes.set(key,svg);
          while(pinnedNodes.size>4)pinnedNodes.delete(pinnedNodes.keys().next().value);
        }
      }
      for(const phase of value.unavailable||[]) {
        const slot=slots.get(phase);if(!slot)continue;
        slot.shown=drawingKey(job,phase);slot.body.replaceChildren();
        slot.unavailable={key:slot.shown,message:value.notice || 'No unique corresponding state in this preparation.'};
        slot.status.begin('',job.identity).idle(slot.unavailable.message);
      }
      restoreAnchor(saved);
    };
  },{
    pending(job) {
      for(const phase of job.phases) slots.get(phase)?.status.begin('Preparing matching scene…',job.identity);
    },
    ready(job) {if(contextKey(context)===contextKey(job)){lastRequest=null;schedule();}},
    failed(error,job) {
      if(contextKey(context)!==contextKey(job))return;
      for(const phase of job.phases) {
        const slot=slots.get(phase);if(!slot)continue;
        slot.failed=drawingKey(job,phase);
        slot.status.begin('',job.identity).fail('Scene unavailable. Reinspect this point to retry.');
      }
      lastRequest=null;schedule();
    },
  });
  const observer=new IntersectionObserver(schedule,{root:scroll,threshold:0});
  function visibleSlots() {
    if(!host.getClientRects().length || host.closest('[hidden]')) return [];
    const view=scroll.getBoundingClientRect();
    return [...slots.values()].filter(slot=>{
      const box=slot.element.getBoundingClientRect();return box.bottom>view.top && box.top<view.bottom;
    });
  }
  function anchor(phases) {
    const current=visibleSlots()[0]?.phase;
    const slot=slots.get(retainedSceneAnchor([...slots.keys()],current,phases));
    return slot?{phase:slot.phase,top:slot.element.getBoundingClientRect().top}:null;
  }
  function restoreAnchor(saved) {
    if(saved && slots.has(saved.phase)) scroll.scrollTop+=slots.get(saved.phase).element.getBoundingClientRect().top-saved.top;
  }
  function setRoster(roster) {
    const phases=[...new Set(roster.map(s=>s.phase))];
    if(JSON.stringify([...slots.keys()])===JSON.stringify(phases)) return;
    const saved=anchor(phases),keep=new Set(phases);
    for(const [phase,slot] of slots) if(!keep.has(phase)) {
      observer.unobserve(slot.element);slot.status.close();slot.element.remove();slots.delete(phase);
    }
    const ordered=[];
    for(const phase of phases) {
      let slot=slots.get(phase);
      if(!slot) {
        const element=document.createElement('div'),body=document.createElement('div');
        element.className='route-scene';element.dataset.scenePhase=phase;element.setAttribute('aria-label',phase.replaceAll('_',' '));
        body.className='route-scene-drawing';element.append(body);host.append(element);
        slot={phase,element,body,status:panelStatus(element,{retainPrevious:()=>Boolean(body.firstElementChild)}),shown:null,failed:null,unavailable:null,geometry:null};
        slot.status.begin('').idle(phase.replaceAll('_',' '));observer.observe(element);
      }
      ordered.push([phase,slot]);host.append(slot.element);
    }
    slots.clear();for(const [phase,slot] of ordered)slots.set(phase,slot);
    restoreAnchor(saved);
  }
  function pump() {
    frame=null;if(closed || !ready || !context)return;
    const visible=visibleSlots();
    for(const slot of slots.values()) if(!visible.includes(slot)) slot.body.replaceChildren();
    const needed=[];
    for(const slot of visible) {
      const key=drawingKey(context,slot.phase),saved=contextKey(context)===contextKey(pinned)?pinnedNodes.get(key):null;
      if(saved) {slot.body.replaceChildren(saved);slot.shown=key;slot.status.clear();}
      else if(slot.shown===key && !slot.body.firstElementChild && slot.failed!==key && slot.unavailable?.key!==key) slot.shown=null;
      if(slot.shown!==key && slot.failed!==key && slot.unavailable?.key!==key)needed.push(slot.phase);
    }
    // One visible viewport shares one verified molecular context. The server
    // bounds phases to its finite recorded vocabulary; hidden slots stay lazy.
    const phases=needed;
    if(!phases.length) {if(lastRequest){work.clear();lastRequest=null;}return;}
    const key=JSON.stringify([contextKey(context),phases]);if(key===lastRequest)return;
    lastRequest=key;void work.show(context,phases);
  }
  function schedule() {if(!closed && frame===null)frame=requestAnimationFrame(pump);}
  function invalidate(identity) {
    work.clear();lastRequest=null;ready=false;
    for(const slot of slots.values()) {
      slot.failed=null;slot.status.begin('',identity||'').idle('Preparing matching route…');
    }
  }
  function show(next) {
    if(contextKey(context)!==contextKey(next))invalidate(next?.identity);
    context=next;ready=Boolean(context);
    if(context)for(const slot of slots.values()) {
      const key=drawingKey(context,slot.phase),saved=contextKey(context)===contextKey(pinned)?pinnedNodes.get(key):null;
      if(saved){slot.body.replaceChildren(saved);slot.shown=key;slot.status.clear();}
      else if(slot.shown===key && slot.body.firstElementChild)slot.status.clear();
      else if(slot.unavailable?.key===key)slot.status.begin('',context.identity).idle(slot.unavailable.message);
    }
    schedule();
  }
  scroll.addEventListener('scroll',schedule,{passive:true});
  return {
    pin(state) {
      const identity=state.preview?.summary.atlas.materialized_realization_id;
      const next=identity?{identity,token:state.token,snapshot:state.choices.snapshot_digest,policy:state.render_policy,presentation:state.presentation.route}:null;
      if(!pinned || !next || drawingKey(pinned,'')!==drawingKey(next,'')){pinnedNodes.clear();pinnedRoster=null;}
      pinned=next;
      setRoster(pinnedRoster||(state.preview?.summary.atlas.states||[]).map(s=>s.state));
      show(pinned);
    },
    pending:invalidate,
    previewFailed(identity) {
      for(const slot of slots.values()) if(slot.element.dataset.pendingIdentity===identity)
        slot.status.begin('',identity).fail('Preview unavailable. Reinspect this point to retry.');
    },
    previewPhases(teaching) {
      return previewScenePhases(scroll.getBoundingClientRect(),teaching.getBoundingClientRect(),visibleSlots().map(slot=>slot.phase));
    },
    async preparePreview(value,state,phases) {
      const next={identity:value.materialized_realization_id,token:value.token,snapshot:value.snapshot_digest,policy:state.render_policy,presentation:state.presentation.route};
      if(!phases.length) return ()=>show(next);
      const commit=await work.prepareResponse(value.route_scenes,{...next,phases});
      return ()=>{show(next);commit();};
    },
    restore(){show(pinned);},
    refresh:schedule,
    close(){closed=true;work.close();observer.disconnect();scroll.removeEventListener('scroll',schedule);if(frame!==null)cancelAnimationFrame(frame);for(const slot of slots.values())slot.status.close();slots.clear();pinnedNodes.clear();host.replaceChildren();pinned=context=null;},
  };
}

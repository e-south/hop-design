import {hoverPreview} from './hover_preview.js';

// The scene channel is read-only and follows the same latest-only lifecycle as
// hairpin preview. A transport response cannot establish selection authority.
export function routeSceneWork(request,prepare,status={}) {
  async function prepareResponse(value,job) {
    if(value.materialized_realization_id!==job.identity) throw Error('Route scene preparation disagrees with the preview.');
    if(value.token!==job.token || value.snapshot_digest!==job.snapshot) throw Error('Route scene context is obsolete.');
    const phases=[...(value.scenes||[]).map(s=>s.phase),...(value.unavailable||[])];
    if(phases.length!==job.phases.length || new Set(phases).size!==phases.length || phases.some(p=>!job.phases.includes(p))) throw Error('Route response must account for each requested phase.');
    return prepare(value,job);
  }
  const queue=hoverPreview(async key=>{
    const job=JSON.parse(key);return {job,value:await request(job)};
  },({job,value})=>prepareResponse(value,job),()=>{},()=>{}, {
    pending:key=>status.pending?.(JSON.parse(key)),
    ready:key=>status.ready?.(JSON.parse(key)),
    failed:(error,key)=>status.failed?.(error,JSON.parse(key)),
  });
  return {
    prepareResponse,
    show(context,phases) {
      if(!phases.length) {queue.clear();return Promise.resolve();}
      if(new Set(phases).size!==phases.length) throw Error('Request distinct scene phases.');
      return queue.show(JSON.stringify({...context,phases}));
    },
    clear:()=>queue.clear(),
    close:()=>queue.close(),
  };
}

// Preview owns no selection, query, camera or history. Both drawings commit atomically.
export function hoverPreview(request, prepare, restore, report, status={}) {
  let serial=0, closed=false, running=false, pending=null;
  function discard() {
    if(pending) {pending.resolve();pending=null;}
  }
  async function drain() {
    if(running) return;
    running=true;
    try {
      while(pending) {
        const {identity,current,resolve}=pending;pending=null;
        try {
          const value=await request(identity);
          if(closed || current!==serial) continue;
          const commit=await prepare(value);
          if(!closed && current===serial) {commit();status.ready?.(identity);}
        } catch(error) {
          if(!closed && current===serial) {
            if(status.failed) status.failed(error,identity);
            else {restore();report(error);}
          }
        } finally {resolve();}
      }
    } finally {running=false;}
  }
  return {
    async show(identity) {
      if(closed) return;
      if(identity && identity===status.current?.()) {this.clear();return;}
      const current=++serial;
      discard();
      status.pending?.(identity);
      return new Promise(resolve=>{pending={identity,current,resolve};void drain();});
    },
    invalidate(identity) {
      if(closed) return;
      if(identity && identity===status.current?.()) {this.clear();return;}
      serial++;discard();if(identity) status.pending?.(identity);
    },
    clear() {serial++;discard();restore();status.clear?.();},
    close() {closed=true;serial++;discard();restore();status.clear?.();},
  };
}

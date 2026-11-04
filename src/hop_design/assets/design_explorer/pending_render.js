// Hold a server-committed state privately until its drawings are ready.
// Retrying is presentation-only: it must never repeat the server mutation.
export function pendingRender(render) {
  let pending=null, running=false;
  async function attempt() {
    if(!pending || running) return;
    running=true;
    try {await render(pending.value,pending.restore);pending=null;}
    finally {running=false;}
  }
  return {
    get blocked(){return pending!==null;},
    async show(value,restore=false) {
      if(pending) throw Error('A drawing update is pending. Retry it before choosing another preparation.');
      pending={value,restore};await attempt();
    },
    retry:attempt,
    clear(){pending=null;},
  };
}

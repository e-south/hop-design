// Local status without timers, network work, or minimum duration. A molecular
// panel can retain its previous drawing as an explicitly old, inert reference.
export function panelStatus(host,{retainPrevious=()=>false,previousLabel='Previous preparation'}={}) {
  const overlay=document.createElement('div'),label=document.createElement('span');
  const announcement=document.createElement('span');
  announcement.className='sr-only';announcement.setAttribute('role','status');
  announcement.setAttribute('aria-atomic','true');host.before(announcement);
  overlay.className='panel-status';overlay.setAttribute('aria-hidden','true');
  overlay.append(label);host.append(overlay);
  let serial=0;
  const suspended=new Map();
  function describe(message) {
    const text=host.dataset.panelRetained?`${previousLabel} · ${message}`:message;
    label.textContent=text;announcement.textContent=text;
  }
  function clear() {
    serial++;delete host.dataset.panelState;delete host.dataset.pendingIdentity;delete host.dataset.panelRetained;
    host.removeAttribute('aria-busy');
    for(const [child,inert] of suspended) child.inert=inert;
    suspended.clear();label.textContent='';announcement.textContent='';
  }
  return {
    begin(message,identity='') {
      const ticket=++serial;
      for(const child of host.children) if(child!==overlay && !suspended.has(child)) {
        suspended.set(child,child.inert);child.inert=true;
      }
      host.dataset.panelState='loading';host.dataset.pendingIdentity=identity;
      if(retainPrevious()) host.dataset.panelRetained='previous';else delete host.dataset.panelRetained;
      host.setAttribute('aria-busy','true');describe(message);
      return {
        ready(){if(ticket===serial) clear();},
        fail(message){if(ticket===serial){host.dataset.panelState='error';delete host.dataset.panelRetained;host.setAttribute('aria-busy','false');describe(message);}},
        idle(message){if(ticket===serial){host.dataset.panelState='waiting';host.setAttribute('aria-busy','false');describe(message);}},
      };
    },
    clear,
    close(){clear();overlay.remove();announcement.remove();},
  };
}

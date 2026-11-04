// Display-only camera: coordinates and complete-preparation identities never change.
export function mapCamera(host, button) {
  let base=null, view=null, gesture=null, moved=false, attached=null;
  const svg=()=>host.querySelector('svg');
  const paint=()=>{if(view && svg()) svg().setAttribute('viewBox',view.join(' '));};
  const fit=()=>{if(base) {view=[...base];paint();}};
  function zoom(factor,x=.5,y=.5) {
    if(!view || !base) return;
    const w=Math.max(base[2]/12,Math.min(base[2]*1.5,view[2]*factor)),h=w*base[3]/base[2];
    view=[view[0]+(view[2]-w)*x,view[1]+(view[3]-h)*y,w,h];paint();
  }
  const down=e=>{
    if(e.button!==0 || e.target.closest('[role=button],[data-node-value]') || !view) return;
    gesture={id:e.pointerId,x:e.clientX,y:e.clientY,view:[...view]};moved=false;host.setPointerCapture(e.pointerId);
  };
  const move=e=>{
    if(!gesture || e.pointerId!==gesture.id) return;
    const r=svg().getBoundingClientRect(),scale=Math.min(r.width/gesture.view[2],r.height/gesture.view[3]);
    const dx=(e.clientX-gesture.x)/scale,dy=(e.clientY-gesture.y)/scale;
    moved ||= Math.abs(dx)+Math.abs(dy)>2;
    view=[gesture.view[0]-dx,gesture.view[1]-dy,...gesture.view.slice(2)];paint();
  };
  const up=()=>{gesture=null;};
  const wheel=e=>{
    if(!e.ctrlKey || !view) return;
    e.preventDefault();const r=host.getBoundingClientRect();
    zoom(Math.exp(Math.max(-.25,Math.min(.25,e.deltaY*.005))),(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height);
  };
  const key=e=>{if(e.target!==host) return;if(e.key==='0') fit();else if(e.key==='+'||e.key==='=') zoom(.8);else if(e.key==='-') zoom(1.25);else return;e.preventDefault();};
  const click=e=>{if(moved){e.stopPropagation();moved=false;}};
  for(const [name,fn] of [['pointerdown',down],['pointermove',move],['pointerup',up],['pointercancel',up],['keydown',key]]) host.addEventListener(name,fn);
  host.addEventListener('wheel',wheel,{passive:false});host.addEventListener('click',click,true);button.addEventListener('click',fit);
  return {
    attach(){const node=svg();if(!node)return;if(node!==attached){const current=(node.getAttribute('data-map-frame')||node.getAttribute('viewBox')).split(/\s+/).map(Number);if(!base||current.join(' ')!==base.join(' ')){base=current;view=[...base];}attached=node;}paint();},
    close(){for(const [name,fn] of [['pointerdown',down],['pointermove',move],['pointerup',up],['pointercancel',up],['keydown',key],['wheel',wheel]]) host.removeEventListener(name,fn);host.removeEventListener('click',click,true);button.removeEventListener('click',fit);gesture=null;attached=null;base=null;view=null;},
  };
}

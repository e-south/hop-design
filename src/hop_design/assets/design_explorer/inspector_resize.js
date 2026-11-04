// Local composition only: never persist a new query, molecular camera or selection.
export function resizableInspector(surface,inspector,scroll,handle,changed,before=()=>{}) {
  let chosen=null,pending=null,frame=null,gesture=null,closed=false;
  const bounds=()=>[440,Math.min(760,surface.clientWidth-320)];
  const width=()=>inspector.getBoundingClientRect().width;
  function anchor() {
    const view=scroll.getBoundingClientRect();
    const element=[...scroll.querySelectorAll('#molecular-area,#trace-context,.route-scene,#preparation-info')].find(e=>{const b=e.getBoundingClientRect();return b.bottom>view.top&&b.top<view.bottom;});
    return element?{element,top:element.getBoundingClientRect().top}:null;
  }
  function describe() {
    const [min,max]=bounds();
    handle.setAttribute('aria-valuemin',min);handle.setAttribute('aria-valuemax',Math.max(min,max));
    handle.setAttribute('aria-valuenow',Math.round(width()));
    handle.setAttribute('aria-valuetext',`${Math.round(width())} pixels`);
  }
  function apply(value) {
    const saved=gesture?.anchor||anchor();
    if(value===null)surface.style.removeProperty('--inspector-width');
    else surface.style.setProperty('--inspector-width',`${value}px`);
    changed();
    if(saved)scroll.scrollTop+=saved.element.getBoundingClientRect().top-saved.top;
    describe();
  }
  function flush() {
    frame=null;if(closed||pending===null)return;
    const value=pending;pending=null;if(value!==width())apply(value);else describe();
  }
  function schedule(value) {
    pending=value;if(frame===null)frame=requestAnimationFrame(flush);
  }
  function request(value) {
    chosen=Math.max(440,Math.min(760,value));
    const [min,max]=bounds();schedule(Math.max(min,Math.min(max,chosen)));
  }
  function end() {
    if(gesture&&handle.hasPointerCapture(gesture.id))handle.releasePointerCapture(gesture.id);
    gesture=null;delete handle.dataset.resizing;
  }
  function refresh() {
    if(closed)return;
    const compact=surface.clientWidth<760;
    handle.hidden=compact||inspector.hidden||inspector.dataset.dismissed==='true'||Boolean(inspector.dataset.focus)||inspector.dataset.hasPin!=='true';
    if(handle.hidden)end();
    if(compact) {
      if(frame!==null)cancelAnimationFrame(frame);frame=null;pending=null;
      if(chosen!==null)apply(null);
    } else if(chosen!==null) {
      const [min,max]=bounds();schedule(Math.max(min,Math.min(max,chosen)));
    }
    describe();
  }
  const down=e=>{
    if(e.button!==0||handle.hidden)return;
    e.preventDefault();e.stopPropagation();before();
    gesture={id:e.pointerId,x:e.clientX,width:width(),anchor:anchor()};handle.setPointerCapture(e.pointerId);handle.dataset.resizing='true';
  };
  const move=e=>{if(gesture&&gesture.id===e.pointerId)request(gesture.width+gesture.x-e.clientX);};
  const up=()=>{if(frame!==null)cancelAnimationFrame(frame);flush();end();};
  const key=e=>{
    if(handle.hidden)return;
    const [min,max]=bounds(),values={ArrowLeft:width()+24,ArrowRight:width()-24,Home:min,End:max};
    if(!(e.key in values))return;e.preventDefault();before();request(values[e.key]);
  };
  const events=[['pointerdown',down],['pointermove',move],['pointerup',up],['pointercancel',up],['lostpointercapture',up],['keydown',key]];
  for(const [name,listener] of events)handle.addEventListener(name,listener);
  const resizing=new ResizeObserver(refresh),disclosure=new MutationObserver(refresh);
  resizing.observe(surface);disclosure.observe(inspector,{attributes:true,attributeFilter:['hidden','data-focus','data-has-pin','data-dismissed']});refresh();
  return {close(){closed=true;end();if(frame!==null)cancelAnimationFrame(frame);frame=null;pending=null;resizing.disconnect();disclosure.disconnect();for(const [name,listener] of events)handle.removeEventListener(name,listener);}};
}

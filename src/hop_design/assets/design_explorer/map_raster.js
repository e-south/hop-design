// Rasterize only presentation. The original SVG retains exact picking and keyboard semantics.
export function mapTransform(view,width,height,pixelRatio=1) {
  const ratio=Math.max(1,Math.min(2,pixelRatio||1)),scale=Math.min(width/view[2],height/view[3])*ratio;
  return {ratio,scale,x:(width*ratio-view[2]*scale)/2-view[0]*scale,y:(height*ratio-view[3]*scale)/2-view[1]*scale,width:Math.round(width*ratio),height:Math.round(height*ratio)};
}
// Visible radius is independent of the larger interaction target.
export function cloudPointRadius(radius,pixel) {
  return Math.max(.65*pixel,Math.min(radius,1.35*pixel));
}
export function mapRaster(host) {
  const cloud=document.createElement('canvas'),selection=document.createElement('canvas');
  for(const canvas of [cloud,selection]) {canvas.dataset.mapRaster='true';canvas.setAttribute('aria-hidden','true');}
  const background=cloud.getContext('2d'),foreground=selection.getContext('2d');
  let svg=null,mode=null,points=[],spokes=[],byMark=new Map(),marked=new Set(),ticket=null,cloudDirty=false,closed=false,oldOpacity='';
  const number=(element,key,fallback=0)=>Number(element.getAttribute(key)??fallback);
  function schedule(full=false) {
    if(!svg||closed)return;cloudDirty ||= full;
    if(ticket===null)ticket=requestAnimationFrame(paint);
  }
  const restored=()=>schedule(true);
  for(const canvas of [cloud,selection])canvas.addEventListener('contextrestored',restored);
  function reset(ctx,canvas,transform) {
    if(canvas.width!==transform.width)canvas.width=transform.width;
    if(canvas.height!==transform.height)canvas.height=transform.height;
    ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.setTransform(transform.scale,0,0,transform.scale,transform.x,transform.y);
  }
  function point(ctx,p,transform,highlight=null) {
    const pixel=transform.ratio/transform.scale;
    const radius=highlight?2*pixel:cloudPointRadius(p.radius,pixel);
    const hollow=['none','white','#fff','#ffffff'].includes(p.fill.toLowerCase());
    ctx.globalAlpha=highlight?1:.28;
    ctx.beginPath();ctx.arc(p.x,p.y,radius,0,2*Math.PI);ctx.fillStyle=p.fill;
    if(!hollow)ctx.fill();
    ctx.strokeStyle=highlight?'#a55236':p.stroke;ctx.lineWidth=(highlight?1.5:.8)*pixel;
    ctx.setLineDash(p.dash);if((hollow&&p.stroke!=='none')||highlight)ctx.stroke();
    ctx.globalAlpha=1;
  }
  function paint() {
    ticket=null;if(!svg||closed)return;
    const bounds=host.getBoundingClientRect(),view=svg.getAttribute('viewBox').trim().split(/\s+/).map(Number);
    if(!bounds.width||!bounds.height||view.length!==4||view.some(v=>!Number.isFinite(v))||view[2]<=0||view[3]<=0)return;
    const transform=mapTransform(view,bounds.width,bounds.height,globalThis.devicePixelRatio);
    if(cloudDirty) {
      reset(background,cloud,transform);
      for(const path of spokes) {background.strokeStyle=path.stroke;background.lineWidth=path.width;background.setLineDash([]);background.stroke(path.shape);}
      for(const p of points)point(background,p,transform);
      cloudDirty=false;
    }
    reset(foreground,selection,transform);
    // Paint pinned first, hovered second, so preview emphasis is never occluded.
    for(const kind of ['pinned','hover'])for(const mark of marked) {
      const hover=Number(mark.dataset.linkedCount)>0,pinned=mark.dataset.selected==='true';
      if(kind==='hover'?!hover:!pinned||hover)continue;
      for(const p of byMark.get(mark)||[])point(foreground,p,transform,kind);
    }
    cloud.style.display=selection.style.display='block';svg.style.opacity='0';
  }
  const changes=new MutationObserver(records=>{
    let full=false;
    for(const record of records) {
      if(record.target===svg&&record.attributeName==='viewBox')full=true;
      else if(byMark.has(record.target)) {
        const mark=record.target;
        if(mark.dataset.selected==='true'||Number(mark.dataset.linkedCount)>0)marked.add(mark);else marked.delete(mark);
      }
    }
    schedule(full);
  });
  const resize=new ResizeObserver(()=>schedule(true));resize.observe(host);
  function detach() {
    changes.disconnect();if(ticket!==null)cancelAnimationFrame(ticket);ticket=null;
    if(svg)svg.style.opacity=oldOpacity;
    svg=null;points=[];spokes=[];byMark.clear();marked.clear();cloudDirty=false;
    for(const canvas of [cloud,selection]) {canvas.remove();canvas.width=canvas.height=0;canvas.style.display='none';}
  }
  function attach(nextMode=mode) {
    mode=nextMode;const next=host.querySelector('svg');
    if(next===svg&&mode==='similarity')return;
    detach();
    if(closed||!background||!foreground||mode!=='similarity'||!next||next.querySelectorAll('[data-preparations]').length<1024)return;
    svg=next;oldOpacity=svg.style.opacity||'';
    for(const circle of svg.querySelectorAll('circle')) {
      const dash=circle.getAttribute('stroke-dasharray'),mark=circle.closest('[data-preparations]');
      const p={x:number(circle,'cx'),y:number(circle,'cy'),radius:number(circle,'r'),fill:circle.getAttribute('fill')||'black',stroke:circle.getAttribute('stroke')||'none',width:number(circle,'stroke-width',1),dash:!dash||dash==='none'?[]:dash.split(/[\s,]+/).map(Number)};
      points.push(p);
      if(mark){if(!byMark.has(mark))byMark.set(mark,[]);byMark.get(mark).push(p);if(mark.dataset.selected==='true'||Number(mark.dataset.linkedCount)>0)marked.add(mark);}
    }
    spokes=[...svg.querySelectorAll('path')].map(path=>({shape:new Path2D(path.getAttribute('d')),stroke:path.getAttribute('stroke')||'none',width:number(path,'stroke-width',1)}));
    host.append(cloud,selection);
    changes.observe(svg,{subtree:true,attributes:true,attributeFilter:['viewBox','data-selected','data-linked-count']});schedule(true);
  }
  const replacement=new MutationObserver(records=>{if(records.some(r=>r.type==='childList'))attach();});replacement.observe(host,{childList:true});
  return {attach,close(){closed=true;detach();for(const canvas of [cloud,selection])canvas.removeEventListener('contextrestored',restored);replacement.disconnect();resize.disconnect();}};
}

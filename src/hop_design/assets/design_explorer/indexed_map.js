import {pointIndex} from './map_index.js';
import {cloudPointRadius,mapTransform} from './map_raster.js';

// Two canvases and one camera frame replace one DOM node per preparation.
export function indexedMap(host,onInspect,onSelect) {
  let svg=null,data=null,rows=null,index=null,byIdentity=new Map(),pin=null,hover=null,active=-1;
  let ticket=null,dirty=false,transform=null,cloud=null,overlay=null,option=null,lens=null;
  const originalRole=host.getAttribute('role');
  function schedule(full=false){dirty ||= full;if(svg&&ticket===null)ticket=requestAnimationFrame(paint);}
  const restored=()=>schedule(true);
  function setup(canvas) {
    if(canvas.width!==transform.width)canvas.width=transform.width;
    if(canvas.height!==transform.height)canvas.height=transform.height;
    const ctx=canvas.getContext('2d');ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.setTransform(transform.scale,0,0,transform.scale,transform.x,transform.y);return ctx;
  }
  function markRadius(){return cloudPointRadius(data.radius,transform.ratio/transform.scale);}
  function cloudAlpha(row) {
    if(!row.matches)return .35;
    if(lens?.kind==='word')return row.values[lens.key]===lens.word ? .5 : .18;
    return .28;
  }
  function point(ctx,p,highlight=null) {
    const tone=lens?lens.color(p.row):'#216e72',pixel=transform.ratio/transform.scale;
    const radius=highlight?Math.max(markRadius(),2*pixel):markRadius();
    ctx.globalAlpha=highlight?1:cloudAlpha(p.row);
    ctx.beginPath();ctx.arc(p.x,p.y,radius,0,2*Math.PI);
    ctx.fillStyle=tone??'#71858a';if(p.row.matches)ctx.fill();
    ctx.strokeStyle=highlight==='pin'?'#a55236':highlight?'#20383f':tone??'#71858a';
    ctx.lineWidth=(highlight?2:.8)*pixel;
    ctx.setLineDash(p.row.matches?[]:[2*pixel,2*pixel]);if(highlight||!p.row.matches)ctx.stroke();
    if(tone===null) {
      const r=radius*.6;ctx.beginPath();ctx.setLineDash([]);ctx.lineWidth=1/transform.scale;
      ctx.moveTo(p.x-r,p.y-r);ctx.lineTo(p.x+r,p.y+r);ctx.moveTo(p.x-r,p.y+r);ctx.lineTo(p.x+r,p.y-r);ctx.stroke();
    }
    if(highlight) {
      ctx.beginPath();ctx.setLineDash([]);ctx.lineWidth=1.5*pixel;
      ctx.arc(p.x,p.y,radius+(highlight==='pin'?3:5)*pixel,0,2*Math.PI);ctx.stroke();
      if(p.group.points.length>1){ctx.font=`${12*pixel}px system-ui`;ctx.textAlign='center';ctx.textBaseline='bottom';ctx.fillStyle='#20383f';
        ctx.fillText(`${p.group.points.length} preparations`,p.x,p.y-radius-8*pixel);}
    }
    ctx.globalAlpha=1;
  }
  function representative(p) {
    return p.group.points.find(m=>m.row.materialized_realization_id===pin)||p.group.points.find(m=>m.row.matches)||p;
  }
  function paint() {
    ticket=null;if(!svg)return;
    const bounds=host.getBoundingClientRect(),view=svg.getAttribute('viewBox').split(/\s+/).map(Number);
    if(!bounds.width||!bounds.height)return;
    transform=mapTransform(view,bounds.width,bounds.height,globalThis.devicePixelRatio);
    if(dirty){
      const ctx=setup(cloud);
      // Every preparation contributes alpha, including exact coincident positions.
      // Paint the requested word last so its emphasis survives background overlap.
      const word=lens?.kind==='word';
      for(const emphasized of word?[false,true]:[false])for(const p of index.points) {
        if(word&&(p.row.values[lens.key]===lens.word)!==emphasized)continue;
        point(ctx,p);
      }
      dirty=false;
    }
    const ctx=setup(overlay);for(const [id,kind] of [[pin,'pin'],[hover,'hover']])if(byIdentity.has(id))point(ctx,byIdentity.get(id),kind);
  }
  function coordinates(event) {
    if(!transform)return null;
    const r=host.getBoundingClientRect();
    return [(event.clientX-r.left)*transform.ratio-transform.x,(event.clientY-r.top)*transform.ratio-transform.y].map(v=>v/transform.scale);
  }
  function hit(event){const xy=coordinates(event);return xy?index.nearest(...xy,Math.max(markRadius(),7*transform.ratio/transform.scale)):null;}
  function describe(p) {
    const value=lens&&lens.key!=='none'?`${lens.label}: ${p.row.values[lens.key]??'not applicable'} ${lens.unit??''}; `:'';
    option.textContent=`${value}Loop ${p.row.values.loop_word??'unspecified'}; ${p.row.matches?'eligible':'outside current filters'}; preparation ${p.order+1} of ${index.points.length}`;
    if(p.group.points.length>1)option.textContent+=`; ${p.group.points.length} preparations at this plotted position; click to inspect members`;
    option.setAttribute('aria-posinset',p.order+1);option.setAttribute('aria-setsize',index.points.length);
    option.setAttribute('aria-selected',String(p.row.materialized_realization_id===pin));
    option.dataset.preparation=p.row.materialized_realization_id;
  }
  const move=e=>{if(!svg||e.buttons)return;const found=hit(e),p=found?representative(found):null;const id=p?.row.materialized_realization_id??null;
    if(id!==hover){hover=id;active=p?.order??active;if(p)describe(p);onInspect(p?[id]:null);schedule();}};
  const click=e=>{if(!svg)return;const p=hit(e);if(p){active=p.order;describe(p);onSelect(p.group.points.map(m=>m.row.materialized_realization_id));}};
  const key=e=>{
    if(!svg||e.target!==host||!index.points.length)return;
    if(['ArrowRight','ArrowDown','ArrowLeft','ArrowUp','Home','End'].includes(e.key)) {
      e.preventDefault();active=e.key==='Home'?0:e.key==='End'?index.points.length-1:
        (active+(['ArrowLeft','ArrowUp'].includes(e.key)?-1:1)+index.points.length)%index.points.length;
      const p=index.points[active];describe(p);hover=p.row.materialized_realization_id;onInspect([hover]);schedule();
    } else if((e.key==='Enter'||e.key===' ')&&active>=0){e.preventDefault();onSelect([index.points[active].row.materialized_realization_id]);}
  };
  const changes=new MutationObserver(()=>schedule(true)),resize=new ResizeObserver(()=>schedule(true));resize.observe(host);
  host.addEventListener('pointermove',move);host.addEventListener('click',click);host.addEventListener('keydown',key);
  function clear() {
    changes.disconnect();if(ticket!==null)cancelAnimationFrame(ticket);ticket=null;
    for(const canvas of [cloud,overlay])if(canvas){canvas.removeEventListener('contextrestored',restored);canvas.remove();canvas.width=canvas.height=0;}
    svg?.remove();option?.remove();svg=data=rows=index=cloud=overlay=option=transform=null;byIdentity.clear();hover=pin=null;active=-1;
    host.removeAttribute('aria-activedescendant');if(originalRole)host.setAttribute('role',originalRole);else host.removeAttribute('role');
  }
  return {
    update(next,paths,selected) {
      if(next!==data||paths!==rows) {
        const prepared=pointIndex(next,paths);
        data=next;rows=paths;index=prepared;byIdentity=new Map(index.points.map(p=>[p.row.materialized_realization_id,p]));
        if(!svg){
          svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox',data.frame.join(' '));svg.setAttribute('data-map-frame',data.frame.join(' '));svg.style.opacity='0';
          cloud=document.createElement('canvas');overlay=document.createElement('canvas');
          for(const canvas of [cloud,overlay]){canvas.dataset.mapRaster='true';canvas.style.display='block';canvas.setAttribute('aria-hidden','true');canvas.addEventListener('contextrestored',restored);}
          option=document.createElement('span');option.id='active-map-preparation';option.className='sr-only';option.setAttribute('role','option');
          host.replaceChildren(svg,cloud,overlay,option);host.setAttribute('role','listbox');host.setAttribute('aria-activedescendant',option.id);
          changes.observe(svg,{attributes:true,attributeFilter:['viewBox']});
        }
        schedule(true);
      }
      pin=selected;if(active>=0)describe(index.points[active]);schedule();
    },
    color(value){lens=value;if(active>=0)describe(index.points[active]);schedule(true);},
    focus(ids){hover=ids?.length===1?ids[0]:null;schedule();},
    clear,
    close(){clear();lens=null;resize.disconnect();host.removeEventListener('pointermove',move);host.removeEventListener('click',click);host.removeEventListener('keydown',key);},
  };
}

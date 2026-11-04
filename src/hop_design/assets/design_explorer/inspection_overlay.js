// Exact selected geometry comes from the same projection as the publication path.
export function validateOverlay(trace, projection) {
  if(!trace || trace.projection!==projection?.projection || trace.frame!==projection.frame)
    throw Error('Molecular preview belongs to a different parameter projection.');
  return trace;
}
export function inspectionOverlay(host) {
  let layer=null, pathLayer=null, suppressed=[];
  const backgrounds=new WeakMap();
  function labels(svg) {
    if(!backgrounds.has(svg)) {
      const items=[];
      for(const node of svg.querySelectorAll('[data-node-value]')) {
        const paint=[...node.querySelectorAll('[data-node-label]')];
        const rect=paint.find(e=>e.localName==='rect');
        if(rect) items.push({paint,box:Object.fromEntries(['x','y','width','height'].map(k=>[k,Number(rect.getAttribute(k))]))});
      }
      backgrounds.set(svg,items);
    }
    return backgrounds.get(svg);
  }
  function clear() {
    layer?.remove();layer=null;
    pathLayer?.remove();pathLayer=null;
    for(const [item,visibility] of suppressed) {
      if(visibility===null)item.removeAttribute('visibility');
      else item.setAttribute('visibility',visibility);
    }
    suppressed=[];
  }
  const overlaps=(a,b)=>a.x<b.x+b.width && b.x<a.x+a.width && a.y<b.y+b.height && b.y<a.y+a.height;
  return {
    prepare(trace, projection) {
      validateOverlay(trace,projection);
      const svg=host.querySelector('svg');
      if(!svg) throw Error('The parameter projection is not mounted.');
      const ns='http://www.w3.org/2000/svg';
      const group=document.createElementNS(ns,'g');
      group.dataset.inspectionOverlay=trace.materialized_realization_id;
      group.setAttribute('pointer-events','none');
      group.setAttribute('aria-label',`Exact trace of ${trace.materialized_realization_id}`);
      const path=document.createElementNS(ns,'path');
      path.dataset.inspectionPath=trace.materialized_realization_id;
      path.setAttribute('pointer-events','none');
      for(const [key,value] of Object.entries({d:trace.path,fill:'none',stroke:'#a55236','stroke-width':3,opacity:1})) path.setAttribute(key,value);
      const font=Number(svg.getAttribute('font-size'))||22;
      const boxes=[];
      for(const value of trace.values) {
        const geometry=value.node_label;
        if(!geometry || !Array.isArray(geometry.lines) || !geometry.lines.length ||
          !geometry.lines.every(line=>typeof line==='string') ||
          ![geometry.width,geometry.height,value.x,value.y].every(Number.isFinite) ||
          geometry.width<=0 || geometry.height<=0) throw Error('Molecular trace lacks shared label geometry.');
        const label=document.createElementNS(ns,'g');label.dataset.inspectionParameter=value.key;
        label.setAttribute('aria-label',`${value.label}: ${value.display}${value.unit?' '+value.unit:''}`);
        const rect=document.createElementNS(ns,'rect');
        const box={x:value.x-geometry.width/2,y:value.y-geometry.height/2,width:geometry.width,height:geometry.height};
        boxes.push(box);
        for(const [key,v] of Object.entries({...box,rx:3,fill:'#fff',stroke:'#a55236','stroke-width':1.4})) rect.setAttribute(key,v);
        label.append(rect);
        geometry.lines.forEach((line,index)=>{
          const text=document.createElementNS(ns,'text');
          for(const [key,v] of Object.entries({x:value.x,y:value.y+(index-(geometry.lines.length-1)/2)*font+font*.35,'text-anchor':'middle',fill:'#74351f','font-size':font})) text.setAttribute(key,v);
          text.textContent=line;label.append(text);
        });
        const title=document.createElementNS(ns,'title');title.textContent=value.display;label.append(title);
        group.append(label);
      }
      const obscured=labels(svg).filter(item=>boxes.some(box=>overlaps(box,item.box)));
      return ()=>{
        if(host.querySelector('svg')!==svg)return;
        clear();
        for(const {paint} of obscured)for(const item of paint){
          suppressed.push([item,item.getAttribute('visibility')]);item.setAttribute('visibility','hidden');
        }
        const before=svg.querySelectorAll('[data-axis]')[0]??svg.querySelectorAll('[data-node-value]')[0];
        if(before)svg.insertBefore(path,before);else svg.append(path);
        pathLayer=path;svg.append(group);layer=group;
      };
    },
    show(trace,projection) {if(!trace){clear();return;}this.prepare(trace,projection)();},
    clear,
  };
}

// Transient content never changes the user's place in the inspector.
export function transientInspector(inspector,scroll) {
  return {
    show() {
      inspector.dataset.transient='true';
    },
    clear() {
      delete inspector.dataset.transient;
    },
  };
}

export function escapeInspection(inspector,{restorePreview,returnToMap,close}) {
  if(inspector.dataset.transient) restorePreview();
  else if(inspector.dataset.focus) returnToMap();
  else close();
}

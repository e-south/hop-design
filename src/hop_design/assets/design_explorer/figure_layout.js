// Consume the same coordinate plate used by the static publication export.
const namespace='http://www.w3.org/2000/svg';
function frame(value) {
  const numbers=String(value).trim().split(/\s+/).map(Number);
  if(numbers.length!==4 || numbers.some(n=>!Number.isFinite(n)) || numbers[2]<=0 || numbers[3]<=0) throw Error('Invalid Figure 1 coordinate frame.');
  return numbers;
}
export function validateFigureLayout(spec) {
  frame(spec.frame);
  for(const part of [spec.hairpin,spec.trace]) {
    frame(part.frame);
    if(['x','y','width','height'].some(key=>!Number.isFinite(part[key])) || part.width<=0 || part.height<=0) throw Error('Invalid Figure 1 placement.');
  }
  return spec;
}
function node(tag,attributes={}) {
  const result=document.createElementNS(namespace,tag);
  for(const [key,value] of Object.entries(attributes)) result.setAttribute(key,value);
  return result;
}
export function figureLayout(parent,molecule,trace) {
  function clear() {for(const layer of parent.querySelectorAll('.figure-layout-layer')) layer.remove();}
  return {
    clear,
    show(spec,hairpin,axes) {
      if(!spec || !hairpin || !axes) {clear();return;}
      validateFigureLayout(spec);
      const [x,y,width,height]=frame(spec.frame);
      parent.style.aspectRatio=`${width} / ${height}`;
      parent.style.setProperty('--figure-ratio',width/height);
      for(const [host,svg,part] of [[molecule,hairpin,spec.hairpin],[trace,axes,spec.trace]]) {
        Object.assign(host.style,{left:`${(part.x-x)/width*100}%`,top:`${(part.y-y)/height*100}%`,width:`${part.width/width*100}%`,height:`${part.height/height*100}%`});
        for(const rect of svg.querySelectorAll?.(':scope > rect[fill="white"]')||[]) rect.setAttribute('fill','none');
        svg.setAttribute('viewBox',part.frame);
        svg.setAttribute('width','100%');svg.setAttribute('height','100%');
      }
      const links=node('svg',{viewBox:spec.frame,'aria-hidden':'true'}),origins=node('svg',{viewBox:spec.frame,'aria-hidden':'true'});
      links.classList.add('figure-layout-layer','teaching-links');origins.classList.add('figure-layout-layer','teaching-origins');
      for(const link of spec.links) {
        const polygon=node('polygon',{points:link.points});
        polygon.dataset.parameter=link.parameter;polygon.dataset.parameterLink=link.parameter;links.append(polygon);
      }
      for(const origin of spec.origins) {
        const {parameter,...bounds}=origin,mark=node('rect',{...bounds,fill:'none',stroke:'#182B34','stroke-width':2.2});
        mark.dataset.parameterOrigin=parameter;mark.dataset.parameter=parameter;origins.append(mark);
      }
      clear();parent.append(links,origins);
    },
  };
}

// HOP Design
// hop-design/src/hop_design/assets/design_explorer/choice_frequencies.js
// Inspect exact choice frequencies with linked hover and persistent highlighting.
// Module Author(s): Eric J. South
import {frequencyIndex} from './choice_frequencies_model.js';

export function choiceFrequencies(host,onFocus) {
  const select=host.querySelector('select'),chart=host.querySelector('[data-frequency-chart]'),clear=host.querySelector('button');
  let choices=null,index=null,pinned=null;
  const ns='http://www.w3.org/2000/svg';
  function svg(tag,attrs={},text=null) {
    const node=document.createElementNS(ns,tag);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);
    if(text!==null)node.textContent=text;return node;
  }
  function restore(){onFocus(pinned?.members??null,{pin:Boolean(pinned)});}
  function highlight(row,pin=false) {
    if(pin)pinned=pinned?.key===row.key?null:row;
    const value=pin?pinned:row;onFocus(value?.members??null,{pin});clear.hidden=!pinned;
    for(const node of chart.querySelectorAll('[data-frequency-row]'))node.setAttribute('aria-pressed',String(node.dataset.frequencyRow===pinned?.key));
  }
  function reset(){pinned=null;onFocus(null,{pin:true});clear.hidden=true;}
  function draw() {
    const profile=index.profile(select.value),rows=profile.rows,left=164,top=18,size=300,bottom=top+size;
    const drawing=svg('svg',{viewBox:'0 0 510 395',role:'group','aria-label':`${select.selectedOptions[0].textContent} frequencies`});
    for(const tick of [0,25,50,75,100]) {
      const x=left+size*tick/100;
      if(tick)drawing.append(svg('line',{x1:x,x2:x,y1:top,y2:bottom,stroke:'#e1e6e5','stroke-width':.7}));
      drawing.append(svg('line',{x1:x,x2:x,y1:bottom,y2:bottom+5,stroke:'#627477'}),svg('text',{x,y:bottom+22,'text-anchor':'middle',fill:'#203b43','font-size':13},String(tick)));
    }
    drawing.append(svg('path',{d:`M${left},${top}V${bottom}H${left+size}`,stroke:'#627477',fill:'none','stroke-width':.8}),svg('text',{x:left+size/2,y:bottom+51,'text-anchor':'middle',fill:'#203b43','font-size':14},'Preparations using this choice (%)'));
    const step=size/Math.max(rows.length,1);
    for(const [i,row] of rows.entries()) {
      const y=top+(i+.5)*step,width=size*row.count/Math.max(profile.total,1);
      const group=svg('g',{'data-frequency-row':row.key,role:'button',tabindex:0,'aria-pressed':String(pinned?.key===row.key),'aria-label':`${row.label}: ${row.count} preparations; ${row.eligible} matching filters. Click to keep highlight.`});
      group.append(svg('title',{},`${row.label}\n${row.count.toLocaleString()} preparations; ${row.eligible.toLocaleString()} matching filters`),svg('rect',{x:0,y:y-step/2,width:510,height:step,fill:'transparent'}),svg('text',{x:left-9,y:y+4.5,'text-anchor':'end','font-size':13,fill:'#203b43'},row.label.length>23?row.label.slice(0,22)+'…':row.label),svg('line',{x1:left-4,x2:left,y1:y,y2:y,stroke:'#627477'}),svg('rect',{x:left,y:y-step*.3,width:Math.max(width,.8),height:step*.6,fill:row.other?'#cad5d3':'#0072B2'}),svg('text',{x:left+width+6,y:y+4.5,'font-size':13,fill:'#203b43'},row.count.toLocaleString()));
      for(const event of ['pointerenter','focus'])group.addEventListener(event,()=>highlight(row));
      group.addEventListener('click',()=>highlight(row,true));
      group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();highlight(row,true);}});
      drawing.append(group);
    }
    chart.replaceChildren(drawing);
  }
  const change=()=>{reset();draw();},leave=restore,focusout=e=>{if(!chart.contains(e.relatedTarget))restore();},escape=e=>{if(e.key==='Escape'){
    e.preventDefault();e.stopPropagation();reset();
    for(const row of chart.querySelectorAll('[data-frequency-row]'))row.setAttribute('aria-pressed','false');
    restore();if(e.target===clear)select.focus();
  }};
  select.addEventListener('change',change);clear.addEventListener('click',change);chart.addEventListener('pointerleave',leave);chart.addEventListener('focusout',focusout);host.addEventListener('keydown',escape);
  return {
    update(state) {
      if(choices!==state.choices) {
        const key=select.value;choices=state.choices;index=frequencyIndex(choices);reset();select.replaceChildren();
        for(const name of [...new Set(index.fields.map(f=>f.group))]) {
          const group=document.createElement('optgroup');group.label=name;
          for(const field of index.fields.filter(f=>f.group===name)){const option=document.createElement('option');option.value=field.key;option.textContent=field.label;group.append(option);}
          select.append(group);
        }
        select.value=index.fields.some(f=>f.key===key)?key:index.fields.find(f=>f.key==='parameter:loop_word')?.key??index.fields[0]?.key??'';
      }
      host.hidden=!state.preview||!index.fields.length;if(!host.hidden){draw();restore();}
    },
    close(){pinned=null;select.removeEventListener('change',change);clear.removeEventListener('click',change);chart.removeEventListener('pointerleave',leave);chart.removeEventListener('focusout',focusout);host.removeEventListener('keydown',escape);chart.replaceChildren();choices=index=pinned=null;},
  };
}

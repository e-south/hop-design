import {preparationDescription,preparationSummary} from './model.js';

// Deliberate inspection of coincident marks; at most eight material rows in the DOM.
export function memberChoices({panel,title,options,close},onSelect,onPreview) {
  const pageSize=8;
  let rows=[],reference=null,page=0,origin=null;
  function dismiss(restore=false,notify=true) {
    panel.hidden=true;options.replaceChildren();rows=[];reference=null;page=0;
    if(notify)onPreview(null);if(restore)origin?.focus();origin=null;
  }
  function paint() {
    const start=page*pageSize,visible=rows.slice(start,start+pageSize);
    options.replaceChildren(...visible.map(row=>{
      const b=document.createElement('button');
      b.textContent=preparationSummary(row)+(row.matches?'':' · outside filters');
      b.title=[reference?preparationDescription(row,reference):preparationSummary(row),row.materialized_realization_id].join('\n');
      b.setAttribute('aria-disabled',String(!row.matches));
      for(const event of ['pointerenter','focus'])b.addEventListener(event,()=>onPreview(row.materialized_realization_id));
      b.addEventListener('click',()=>{if(row.matches){const id=row.materialized_realization_id;dismiss();onSelect(id);}});
      return b;
    }));
    if(rows.length>pageSize){
      const navigation=document.createElement('div');navigation.className='member-pages';
      const previous=document.createElement('button'),next=document.createElement('button'),count=document.createElement('span');
      previous.textContent='Previous';previous.disabled=page===0;
      next.textContent='Next';next.disabled=start+pageSize>=rows.length;
      count.textContent=`${start+1}–${start+visible.length} of ${rows.length}`;
      previous.addEventListener('click',()=>{if(page>0){page--;paint();options.children[0]?.focus();}});
      next.addEventListener('click',()=>{if(start+pageSize<rows.length){page++;paint();options.children[0]?.focus();}});
      navigation.append(previous,count,next);options.append(navigation);
    }
  }
  const escape=e=>{if(e.key==='Escape'&&!panel.hidden){e.preventDefault();e.stopPropagation();dismiss(true);}};
  const cancel=()=>dismiss(true);panel.addEventListener('keydown',escape);close.addEventListener('click',cancel);
  return {
    open(next,pinned,label){
      rows=next;reference=pinned;page=0;origin=document.activeElement;
      title.textContent=label||`${rows.length} preparations · ${rows.filter(p=>p.matches).length} eligible`;
      paint();panel.hidden=false;options.children[0]?.focus();
    },
    dismiss,
    close(){dismiss(false,false);panel.removeEventListener('keydown',escape);close.removeEventListener('click',cancel);},
  };
}

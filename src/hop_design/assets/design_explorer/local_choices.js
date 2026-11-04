import {parameterKeys,parameterSelector,resolveParameterFocus} from './parameters.js';

// Definitions and coordinates come from the admitted edition, never UI-owned biology.
export function featureOptions(axes,keys,values) {
  return resolveParameterFocus(axes,keys).axes.filter(a=>
    a.operations?.inspect.available&&a.applicable!==false&&values[a.key]!==null&&values[a.key]!==undefined
  ).map(definition=>({definition,value:values[definition.key]}));
}

export function featureQuery(query,axes,key,value) {
  const definition=axes.find(a=>a.key===key&&a.canonical_key===key);
  if(!definition||definition.applicable===false)throw Error('This molecular feature is not applicable.');
  if(!definition.operations?.filter.available)throw Error(definition.operations?.filter.reason??'Filtering is unavailable for this feature.');
  if(definition.kind==='numeric'?!Number.isInteger(value):typeof value!=='string')
    throw Error('The feature value does not match its recorded type.');
  const {keys}=resolveParameterFocus(axes,[key]);
  return {...query,parameters:[...query.parameters.filter(p=>!keys.includes(p.key)),{key,values:[value]}]};
}

// One temporary feature disclosure; it neither zooms nor creates new constraints.
export function localChoices(host,{surface=host,onQuery,onColor,canColor,onLoop,onFocus}) {
  const panel=document.createElement('div');panel.className='local-feature';panel.hidden=true;
  panel.id='molecular-feature-details';panel.setAttribute('role','region');panel.setAttribute('aria-label','Molecular feature');surface.append(panel);
  let state=null,axes=[],paths=null,rows=new Map(),row=null,enabled=false,opener=null;
  const selector=parameterSelector+',[data-teaching-note]';
  function options(target) {
    if(!enabled||panel.contains(target))return [];
    const feature=target?.closest?.(selector);if(!feature)return [];
    const keys=parameterKeys(feature);
    if(feature.dataset.teachingNote)keys.push(...axes.filter(a=>a.design_role==='product'&&a.neighborhood===feature.dataset.teachingNote).map(a=>a.key));
    return featureOptions(axes,keys,row.values);
  }
  function dismiss(restore=false) {
    panel.hidden=true;panel.replaceChildren();delete surface.dataset.featureOpen;
    opener?.setAttribute('aria-expanded','false');
    if(restore)opener?.focus();opener=null;
  }
  function button(parent,label,action) {
    const node=document.createElement('button');node.textContent=label;
    node.addEventListener('click',()=>{dismiss();action();});parent.append(node);return node;
  }
  function reveal(target,keyboard=false) {
    const features=options(target);if(!features.length)return;
    dismiss();opener=target.closest(selector);
    const origin=opener;
    function show(feature,focus=false,meaning=false) {
      panel.replaceChildren();const tabs=document.createElement('div');tabs.className='feature-heading';panel.append(tabs);
      for(const f of meaning?[feature]:features){
        const tab=document.createElement('button');tab.textContent=`${f.definition.label} · ${f.value}${f.definition.unit?' '+f.definition.unit:''}`;
        tab.setAttribute('aria-pressed',String(f===feature));tab.addEventListener('click',()=>show(f,true));tabs.append(tab);
      }
      const close=button(tabs,'×',()=>origin.focus());close.className='feature-close';close.setAttribute('aria-label','Close feature');
      const {definition:d,value}=feature;
      const switchView=document.createElement('button');switchView.textContent=meaning?'Actions':'Meaning';
      switchView.addEventListener('click',()=>show(feature,true,!meaning));
      if(meaning){
        tabs.insertBefore(switchView,close);
        const detail=document.createElement('p');detail.textContent=[d.stage?.replaceAll('_',' '),d.measurement,d.relationship,d.operations.revise.reason].filter(Boolean).join(' · ');panel.append(detail);
        if(focus)switchView.focus();return;
      }
      const actions=document.createElement('div');actions.className='actions';panel.append(actions);
      let first=null;
      if(canColor(d.key)){first=button(actions,'Color map',()=>onColor(d.key,value));first.setAttribute('aria-label',`Color by ${d.label.toLowerCase()}`);}
      const filter=d.operations.filter.available?button(actions,`Filter to ${value}${d.unit?' '+d.unit:''}`,()=>onQuery(featureQuery(state.choices.query,axes,d.key,value))):null;
      const preserve=d.operations.preserve;
      if(preserve?.available&&preserve.arguments?.stage==='hairpin'&&preserve.arguments?.except_neighborhood==='loop'){const another=button(actions,'Another loop',onLoop);another.title='Another loop, same surroundings';another.setAttribute('aria-label',another.title);}
      actions.append(switchView);
      onFocus([d.key]);if(focus)(first??filter??switchView).focus();
    }
    panel.hidden=false;surface.dataset.featureOpen='true';opener.setAttribute('aria-expanded','true');
    show(features[0],keyboard);
  }
  const click=event=>reveal(event.target);
  const keydown=event=>{
    if(event.key==='Escape'&&!panel.hidden){event.preventDefault();event.stopPropagation();dismiss(true);}
    else if((event.key==='Enter'||event.key===' ')&&options(event.target).length){event.preventDefault();reveal(event.target,true);}
  };
  const outside=event=>{if(!host.contains(event.target)&&!panel.contains(event.target))dismiss();};
  host.addEventListener('click',click);host.addEventListener('keydown',keydown);document.addEventListener('pointerdown',outside);
  if(surface!==host)panel.addEventListener('keydown',keydown);
  function suspend(){enabled=false;dismiss();}
  return {
    dismiss,suspend,
    update(next) {
      suspend();state=next;
      if(!state)return;
      axes=state.feature_parameters??[];
      if(paths!==state.choices.paths){paths=state.choices.paths;rows=new Map(paths.map(p=>[p.materialized_realization_id,p]));}
      row=rows.get(state.selection?.materialized_realization_id);enabled=Boolean(row);
      for(const feature of host.querySelectorAll('[data-parameter-anchor],[data-teaching-note],[data-teaching-bracket]')) {
        // Empty anchor groups connect the figures but are not visible controls.
        if(!feature.dataset.teachingNote&&!feature.querySelector('text,path,rect,polygon,circle'))continue;
        if(!options(feature).length)continue;
        feature.setAttribute('tabindex','0');feature.setAttribute('role','button');feature.setAttribute('aria-controls',panel.id);feature.setAttribute('aria-expanded','false');
        feature.setAttribute('aria-label',`Inspect ${options(feature).map(f=>f.definition.label.toLowerCase()).join(' and ')}`);
      }
    },
    close(){suspend();host.removeEventListener('click',click);host.removeEventListener('keydown',keydown);panel.removeEventListener('keydown',keydown);document.removeEventListener('pointerdown',outside);panel.remove();rows.clear();state=paths=row=opener=null;},
  };
}

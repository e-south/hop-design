"use strict";
import {$,node} from "./common.js";
import {selectCoordinate,pivotQuery} from "./envelope_model.js";
import {permissionEditor} from "./envelope_fields.js";

export function envelopeBrowser({getState,api,acceptState,action,update,afterEvaluation}) {
  const dialog=$("domain-dialog"), body=$("domain-body"), title=$("domain-title");
  let axisKey=null, offset=0, length=null, prefix="", pending=new Map(), editor=null;
  function button(text,fn,quiet=false) {
    const el=node("button",text);el.type="button";if(quiet)el.className="quiet";el.onclick=fn;return el;
  }
  function show() {if(!dialog.open)dialog.showModal();}
  function axis() {return getState().choices.choice_space.axes.find(a=>a.key===axisKey);}
  function errorSafe(fn) {return ()=>action(fn);}
  function select(value) {
    return action(async()=>{await update(selectCoordinate(getState().choices.query,axisKey,value));dialog.close();});
  }
  async function renderDomain() {
    const state=getState(), a=axis();if(!a)return;
    title.textContent=`${a.symbol ? a.symbol+" · " : ""}${a.label}`;body.replaceChildren();
    body.append(node("p",a.measurement));
    const domain=state.pool.parameter_domains[axisKey] || {};
    if(axisKey==="loop_word" && domain.alphabet) {
      const sizes=state.pool.parameter_domains.loop_nt, select=document.createElement("select"), label=node("label","Loop length (nt)");
      const values=sizes.values || Array.from({length:Math.min(1024,sizes.maximum-sizes.minimum+1)},(_,i)=>sizes.minimum+i);
      if(!values.includes(length))length=values[0];
      values.forEach(v=>select.add(new Option(String(v),String(v))));select.value=length;
      select.onchange=errorSafe(async()=>{length=Number(select.value);prefix="";offset=0;await renderDomain();});
      label.append(select);body.append(label);
      const row=node("div","");row.className="domain-prefix";
      row.append(node("span",`Sequence prefix: ${prefix || "any"}`));
      if(prefix)row.append(button("Back one base",errorSafe(async()=>{prefix=prefix.slice(0,-1);offset=0;await renderDomain();}),true));
      if(prefix.length<length)for(const base of "ACGT")row.append(button(base,errorSafe(async()=>{prefix+=base;offset=0;await renderDomain();}),true));
      body.append(row);
    } else {length=null;prefix="";}
    if(!Object.keys(domain).length) {
      body.append(node("p","This coordinate is measured from completed molecules; it has no independent generating domain."));
    } else {
      const page=await api("/api/parameter-domain",{query_digest:state.choices.query_digest,request:{key:axisKey,length,prefix,offset,limit:32}});
      body.append(node("p",`${page.total} permitted value(s) in this domain. Permission does not establish a complete preparation.`));
      const grid=node("div","");grid.className="domain-values";
      for(const value of page.values) {
        const item=button(value.label,()=>{
          if(value.status==="blocked_by_selections")renderAlternatives(value);
          else select(value.value);
        },true);
        item.dataset.status=value.status;
        item.title=`${value.matching_preparations} matching complete preparation(s); ${value.complete_preparations} in the recorded pool. Select to target this value.`;
        item.setAttribute("aria-label",`${value.label}: ${item.title}`);grid.append(item);
      }
      body.append(grid);
      const nav=node("div","");nav.className="domain-paging";
      if(offset)nav.append(button("Previous",errorSafe(async()=>{offset=Math.max(0,offset-32);await renderDomain();}),true));
      if(page.next_offset!==null)nav.append(button("Next",errorSafe(async()=>{offset=page.next_offset;await renderDomain();}),true));
      body.append(nav,node("p","Outlined values have no complete preparation recorded. They remain selectable for targeted evaluation; failures and unfinished coverage remain in the plot's coverage view."));
    }
    body.append(button("Change generating permissions…",()=>renderRevision(),true));
  }
  function renderAlternatives(value) {
    body.replaceChildren(node("p",`${value.label} exists in recorded complete preparations, but other selections exclude them.`));
    body.append(button("Select this value; keep all other selections",()=>select(value.value)));
    for(const alternative of value.recorded_alternatives) {
      const path=getState().choices.choice_space.paths.find(p=>p.option_label===alternative.option_label);
      const changes=alternative.different_selections.map(key=>`${getState().choices.choice_space.axes.find(a=>a.key===key)?.label || key} → ${path.values[key]}`).join("; ");
      const row=node("div","");row.className="recorded-alternative";
      row.append(node("p",changes || "Same numerical selections"));
      if(alternative.preservation_conflicts.length)row.append(node("p","Conflicts with preserved properties or neighborhood choices. Those controls remain fixed."));
      else row.append(button("Use this recorded combination",errorSafe(async()=>{
        await update(pivotQuery(getState().choices.query,axisKey,value.value,alternative,path));dialog.close();
      })));
      body.append(row);
    }
    body.append(button("Back to values",errorSafe(renderDomain),true));
  }
  function renderRevision(selectedPath=null) {
    title.textContent="Revise the construction envelope";body.replaceChildren();
    body.append(node("p","Changes are previewed before evaluation. The supplied stem, receiving ends, material policies and preserved properties remain fixed."));
    const state=getState(), fields=state.pool.envelope.fields, select=document.createElement("select"), label=node("label","Generating permission");
    select.setAttribute("aria-label","Generating permission");
    for(const field of fields)select.add(new Option(`${field.group} · ${field.label}`,field.path));
    select.value=selectedPath || fields.find(f=>f.axis===axisKey)?.path || fields[0].path;
    const region=node("div","");
    function field() {return fields.find(f=>f.path===select.value);}
    function redraw() {const f=field();editor=permissionEditor({...f,value:pending.has(f.path)?pending.get(f.path):f.value},state);region.replaceChildren(editor.host);}
    select.onchange=redraw;label.append(select);body.append(label,region);redraw();
    body.append(button("Add to revision",()=>{
      try {pending.set(field().path,editor.read());renderRevision(field().path);}
      catch(error){$("domain-error").textContent=error.message;}
    },true));
    const list=node("div","");list.className="pending-revisions";
    for(const [path,value]of pending) {
      const row=node("div","");row.append(node("span",`${fields.find(f=>f.path===path)?.label}: ${value===null ? "unfixed / inherited" : JSON.stringify(value)}`),button("Remove",()=>{pending.delete(path);renderRevision(select.value);},true));list.append(row);
    }
    body.append(list);
    const preview=button("Preview revised envelope",errorSafe(async()=>{
      const next=await api("/api/preview-envelope",{query_digest:getState().choices.query_digest,revision:{schema:"hop.scaffold-envelope-revision/v1",changes:[...pending].map(([path,value])=>({path,value}))}});
      acceptState(next);renderPreview(next.envelope_revision);
    }));preview.dataset.requiresChanges="true";preview.disabled=!pending.size;body.append(preview);
  }
  function renderPreview(preview) {
    title.textContent="Review changed permissions";body.replaceChildren();
    for(const change of preview.changes)body.append(node("p",`${change.label}: ${JSON.stringify(change.before)} → ${JSON.stringify(change.after)}`));
    body.append(node("p",`The current chart selections and preservation controls remain. ${preview.bounds.permitted_branches} targeted branch(es) are planned; none has been evaluated by this preview.`));
    for(const conflict of preview.conflicts)body.append(node("p",`${conflict.requested_field}: ${conflict.explicit_edit || conflict.code}`));
    body.append(button("Edit revision",()=>renderRevision(),true));
    const bounds=node("div","");bounds.className="permission-pair";
    const inputs={};
    for(const [key,text,source]of [["branches","Maximum new branches","evaluation-branches"],["continuations","Continuations per branch","evaluation-continuations"]]) {
      const label=node("label",text),input=document.createElement("input");input.type="number";input.min="1";input.max="64";input.step="1";input.value=$(source).value;
      label.append(input);bounds.append(label);inputs[key]=input;
    }
    body.append(bounds);
    if(preview.status==="ready")body.append(button("Evaluate this revised envelope",errorSafe(async()=>{
      const next=await api("/api/evaluate-envelope",{query_digest:getState().choices.query_digest,revision_digest:preview.revision_digest,max_branches:Number(inputs.branches.value),max_continuations_per_branch:Number(inputs.continuations.value)});
      acceptState(next);pending.clear();dialog.close();await afterEvaluation();
    })));
  }
  $("close-domain").onclick=()=>dialog.close();
  $("revise-envelope").onclick=()=>{axisKey=null;$("domain-error").textContent="";renderRevision();show();};
  document.addEventListener("hop:browse-parameter",event=>action(async()=>{
    axisKey=event.detail;offset=0;length=null;prefix="";$("domain-error").textContent="";show();await renderDomain();
  }));
  return {refresh:busy=>{
    dialog.setAttribute("aria-busy",String(busy));
    body.inert=busy;
    for(const el of dialog.querySelectorAll("[data-requires-changes]"))el.disabled=busy || !pending.size;
  }};
}

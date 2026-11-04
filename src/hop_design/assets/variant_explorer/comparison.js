"use strict";

// This adapter only authors the public comparison request; HOP assesses every group.
export function comparisonPanel({api, action, getState, acceptState, preview}) {
  const $=id=>document.getElementById(id), required=new Set();
  let assessedInput=null;
  function node(tag,text){const n=document.createElement(tag);n.textContent=text;return n;}
  function inputKey(){return JSON.stringify([getState().choices.query_digest,[...required].sort(),$("set-surroundings").checked]);}
  function invalidate(){assessedInput=null;$("comparison-handoff").replaceChildren();render();}
  function refresh(busy=false){
    $("assess-required").disabled=busy||!required.size;
    $("retrieve-required").disabled=busy||assessedInput!==inputKey()||!$("compatible-set").value||!$("set-baseline").value;
  }
  function render(){
    const state=getState(), words=[...new Set(state.pool.options.map(o=>o.loop_sequence))].sort();
    $("required-loops").replaceChildren(...words.map(word=>{
      const b=node("button",word);b.setAttribute("aria-pressed",String(required.has(word)));
      b.onclick=()=>{required.has(word)?required.delete(word):required.add(word);invalidate();};return b;
    }));
    const active=assessedInput===inputKey()?state.comparison:null;
    if(!active) $("comparison-handoff").replaceChildren();
    const old=$("compatible-set").value, baseline=$("set-baseline").value;
    $("compatible-set").replaceChildren(new Option("Choose a compatible set",""));
    $("set-baseline").replaceChildren(new Option("Choose a presentation baseline",""));
    $("comparison-preview").replaceChildren();
    if(active){
      active.sets.forEach(s=>{
        const methods=[...new Set(Object.values(s.members).flatMap(label=>state.choices.preparations.find(p=>p.label===label).methods.map(m=>m.name)))];
        $("compatible-set").append(new Option(`${s.label} · ${methods.join(" / ")}`,s.label));
      });
      $("compatible-set").value=old;
      const chosen=active.sets.find(s=>s.label===$("compatible-set").value);
      if(chosen){
        Object.entries(chosen.members).forEach(([name,label])=>{
          $("set-baseline").append(new Option(name,name));
          const b=node("button",`Inspect ${name}`);b.onclick=()=>action(()=>preview(label));$("comparison-preview").append(b);
        });
        $("set-baseline").value=baseline;
      }
      const missing=active.missing_members.map(m=>`${m.name}: ${m.reason.replaceAll("_"," ")}`).join("; ");
      $("comparison-status").textContent=`${active.sets.length} compatible sets; ${active.group_coverage.evaluated_assignments} assignments examined, ${active.group_coverage.unexamined_assignments} unexamined. ${missing}`;
    }else{
      $("comparison-status").textContent=required.size?`${required.size} required members. Assess against current choices; none will be silently dropped.`:"Choose each loop that must occur in the set. This does not alter allowed variants above.";
    }
    refresh();
  }
  $("set-surroundings").onchange=invalidate;
  $("compatible-set").onchange=()=>{ $("comparison-handoff").replaceChildren();render(); };
  $("set-baseline").onchange=()=>{ $("comparison-handoff").replaceChildren();refresh(); };
  $("assess-required").onclick=()=>action(async()=>{
    const state=getState();
    const value=await api("/api/compare",{
      result_digest:state.pool.result_digest,query_digest:state.choices.query_digest,
      required_members:[...required].sort().map(word=>({name:word.toLowerCase(),loop_sequence:word})),
      stage_controls:$("set-surroundings").checked?[{stage:state.choices.query.stage,property:"non_loop_sequences",scope:"set"}]:[],
      shared_properties:["release_interfaces"],max_group_evaluations:256,max_sets:16,
    });
    acceptState(value);assessedInput=inputKey();render();
  });
  $("retrieve-required").onclick=()=>action(async()=>{
    const state=getState();
    $("comparison-handoff").textContent="Rechecking required members, molecular controls and source records…";
    const value=await api("/api/select-comparison",{
      query_digest:state.choices.query_digest,request_digest:state.comparison.request_digest,
      set_label:$("compatible-set").value,baseline:$("set-baseline").value,
    });
    acceptState(value);const link=node("a","Download this verified set and oligos");link.href=value.selection.archive;
    $("comparison-handoff").replaceChildren(link);
  });
  return {render,refresh};
}

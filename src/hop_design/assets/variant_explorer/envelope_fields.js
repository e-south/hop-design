"use strict";
import {node} from "./common.js";
import {rangePermission} from "./envelope_model.js";

function number(label, value) {
  const host = node("label", label), input = document.createElement("input");
  input.type = "number"; input.step = "1"; input.value = value ?? 0; host.append(input);
  return {host,input};
}
function checklist(values, names, selected) {
  const host = node("div", ""), inputs = [];
  host.className = "permission-choices";
  for (const value of values) {
    const label = node("label", ""), input = document.createElement("input");
    input.type = "checkbox"; input.value = value; input.checked = selected.includes(value);
    label.append(input,document.createTextNode(names[value] || value)); host.append(label); inputs.push(input);
  }
  return {host, read:() => inputs.filter(i => i.checked).map(i => i.value)};
}
export function permissionEditor(field, state) {
  const host = node("div", ""); host.className = "permission-editor";
  if (["integer","integers"].includes(field.kind)) {
    const values = Array.isArray(field.value) ? field.value : [field.value];
    const low = number(field.kind === "integer" ? "Value" : "Minimum", values[0]);
    const high = number("Maximum", values.at(-1));
    const free = document.createElement("input"), label = node("label", ""); free.type = "checkbox";
    free.checked = (field.unrestricted === "empty" && !values.length) || (field.nullable && field.value === null);
    label.append(free,document.createTextNode(field.nullable ? "Use inherited requirement" : "Any value within the construction budget"));
    if (field.unrestricted === "empty" || field.nullable) host.append(label);
    host.append(low.host); if (field.kind === "integers") host.append(high.host);
    const disable = () => {low.input.disabled = high.input.disabled = free.checked;};
    free.onchange = disable; disable();
    return {host,read:() => field.nullable && free.checked ? null : rangePermission(field,low.input.value,field.kind === "integer" ? low.input.value : high.input.value,free.checked)};
  }
  if (field.kind === "choice") {
    const select = document.createElement("select");
    select.setAttribute("aria-label",field.label);
    field.choices.forEach(v => select.add(new Option(v,v))); select.value=field.value; host.append(select);
    return {host,read:() => select.value};
  }
  if (["methods","words"].includes(field.kind)) {
    const names = state.pool.parameter_names || {};
    const values = field.kind === "methods" ? Object.keys(names) : field.value || [];
    const list = checklist(values,names,field.value || []); host.append(list.host);
    const free = document.createElement("input"), label = node("label", ""); free.type="checkbox";
    free.checked=field.value === null;
    label.append(free,document.createTextNode(field.axis === "loop_word" ? "Leave sequence free within the declared length domain" : field.kind === "words" ? "Use inherited tail permissions" : "Use inherited method permissions"));
    if (field.nullable) host.prepend(label);
    return {host,read:() => field.nullable && free.checked ? null : list.read()};
  }
  if (field.path === "end_placements") {
    const rows = [], add = value => {
      const row = node("div", ""), left = number("Left (bp)",value.left_bp), right=number("Right (bp)",value.right_bp);
      const remove=node("button","Remove pair"); remove.type="button"; remove.className="quiet";
      row.className="permission-pair"; row.append(left.host,right.host,remove); host.append(row);
      const record={row,left,right}; rows.push(record); remove.onclick=() => {rows.splice(rows.indexOf(record),1);row.remove();};
    };
    (field.value || []).forEach(add);
    const button=node("button","Add a joint placement"); button.type="button"; button.onclick=() => add({left_bp:0,right_bp:0}); host.append(button);
    return {host,read:() => rows.length ? rows.map(r => ({left_bp:Number(r.left.input.value),right_bp:Number(r.right.input.value)})) : null};
  }
  if (field.path === "parameters") {
    const retained = new Set((field.value || []).map(p => p.key));
    for (const p of field.value || []) {
      const label=node("label",""), input=document.createElement("input"); input.type="checkbox"; input.checked=true;
      input.onchange=() => input.checked ? retained.add(p.key) : retained.delete(p.key);
      label.append(input,document.createTextNode(`${p.key}: ${p.values?.join(" / ") || `${p.minimum}–${p.maximum}`}`));host.append(label);
    }
    host.append(node("p","Unchecked inherited restrictions will be explicitly removed in the preview. Current chart selections and preservation controls remain."));
    return {host,read:() => (field.value || []).filter(p => retained.has(p.key))};
  }
  if (field.path.endsWith("role_restrictions")) {
    const names=state.pool.parameter_names, lists=[];
    for (const role of field.value || []) {
      const list=checklist(Object.keys(names),names,role.allowed_enzyme_ids);
      host.append(node("p",role.role),list.host); lists.push({role:role.role,read:list.read});
    }
    return {host,read:() => lists.map(v => ({role:v.role,allowed_enzyme_ids:v.read()}))};
  }
  if (field.path.endsWith("pairing_constraints")) {
    const values=structuredClone(field.value || []), select=document.createElement("select"), detail=node("div","");
    select.setAttribute("aria-label","Position outward from ligation");
    values.forEach((p,i)=>select.add(new Option(`Position ${p.position_from_ligation}`,String(i))));
    function render() {
      detail.replaceChildren(); const p=values[Number(select.value)]; if (!p) return;
      const kind=document.createElement("select"); kind.setAttribute("aria-label","Pairing class");
      ["match","wobble","mismatch","any"].forEach(v=>kind.add(new Option(v,v)));kind.value=p.allowed_class;
      kind.onchange=()=>{p.allowed_class=kind.value;};detail.append(kind);
      for (const role of ["source","adapter"]) {
        const list=checklist([..."ACGT"],{},p[`allowed_${role}_bases`] || [..."ACGT"]);
        list.host.onchange=()=>{p[`allowed_${role}_bases`]=list.read();};detail.append(node("p",`${role} bases`),list.host);
      }
    }
    select.onchange=render;host.append(select,detail);render();
    return {host,read:()=>values};
  }
  host.append(node("p","This permission uses the structured CLI/API revision contract."));
  return {host,read:()=>field.value};
}

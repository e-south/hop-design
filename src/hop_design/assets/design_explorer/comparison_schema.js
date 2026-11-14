/*
--------------------------------------------------------------------------------
HOP Design
hop-design/src/hop_design/assets/design_explorer/comparison_schema.js

Render safe field-type schematics without changing saved comparison values.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
*/
const ns='http://www.w3.org/2000/svg',tags=new Set(['line','path','circle','rect','g']);
const numeric=new Set(['x','y','x1','y1','x2','y2','cx','cy','r','width','height','rx','ry','stroke-width','opacity','stroke-opacity','fill-opacity']);
const inert=new Set(['data-fixed-stem','data-measured-flank','data-end-context']);
const number=/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
function invalid(){throw Error('Invalid comparison schematic glyph presentation.');}
function finite(value){return typeof value==='number'&&Number.isFinite(value)&&Math.abs(value)<=10000;}
function attribute(key,value) {
 if(typeof value!=='string'||value.length>4096)invalid();
 if(numeric.has(key)){if(!number.test(value)||!finite(Number(value)))invalid();return;}
 if(inert.has(key)){if(value.length>256)invalid();return;}
 if(['fill','stroke'].includes(key)){if(!/^(?:none|currentColor|#[0-9a-f]{3}(?:[0-9a-f]{3})?)$/i.test(value))invalid();return;}
 if(key==='d'){
  if(!value||!/[Mm]/.test(value)||!/^[MmLlHhVvCcSsQqTtAaZz0-9.,+eE\s-]+$/.test(value))invalid();
  for(const token of value.match(/[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/g)||[])if(!finite(Number(token)))invalid();return;
 }
 if(key==='stroke-linecap'&&['butt','round','square'].includes(value))return;
 if(key==='stroke-linejoin'&&['miter','round','bevel'].includes(value))return;
 invalid();
}
function validateGlyph(glyph) {
 if(!glyph||Object.keys(glyph).some(k=>!['view_box','nodes'].includes(k))||!Array.isArray(glyph.view_box)||glyph.view_box.length!==4||!glyph.view_box.every(finite)||glyph.view_box[2]<=0||glyph.view_box[3]<=0||!Array.isArray(glyph.nodes)||!glyph.nodes.length)invalid();
 let count=0;
 function visit(node,depth) {
  if(++count>256||depth>8||!node||!tags.has(node.tag)||Object.keys(node).some(k=>!['tag','attrs','children'].includes(k))||!node.attrs||typeof node.attrs!=='object'||Array.isArray(node.attrs))invalid();
  for(const [key,value] of Object.entries(node.attrs))attribute(key,value);
  if(node.children!==undefined){if(node.tag!=='g'||!Array.isArray(node.children))invalid();for(const child of node.children)visit(child,depth+1);}
 }
 for(const node of glyph.nodes)visit(node,0);
}
export function comparisonSchema(presentation,keys) {
 if(presentation?.display!=='schematic-glyphs')return null;
 const order=presentation.display_order;
 if(!Array.isArray(order)||!order.length||order.length>64||order.length!==keys.length||new Set(order).size!==keys.length||order.some(k=>!keys.includes(k))||!finite(presentation.field_pitch)||presentation.field_pitch<=0||!finite(presentation.font_size)||presentation.font_size<=0||!finite(presentation.label_angle)||presentation.label_angle < -90||presentation.label_angle>0||!presentation.glyphs||typeof presentation.glyphs!=='object'||Array.isArray(presentation.glyphs)||Object.keys(presentation.glyphs).length!==keys.length)invalid();
 for(const key of order)validateGlyph(presentation.glyphs[key]);
 const groups=presentation.schema_groups||[
  {key:'shape',label:'Geometry',fields:order.filter(k=>k.startsWith('shape.'))},
  {key:'sequence',label:'Sequences',fields:order.filter(k=>/^(sequences|interfaces)\./.test(k))},
  {key:'processing',label:'Enzymes',fields:order.filter(k=>k.startsWith('processing.'))},
 ].filter(g=>g.fields.length);
 if(!Array.isArray(groups))invalid();
 const covered=[];
 for(const group of groups){
  if(!group||typeof group.key!=='string'||typeof group.label!=='string'||group.label.length>80||group.fill!==undefined&&!/^#[0-9a-f]{6}$/i.test(group.fill)||!Array.isArray(group.fields)||!group.fields.length||group.fields.some(k=>!order.includes(k)))invalid();
  const start=order.indexOf(group.fields[0]);
  if(group.fields.some((key,i)=>order[start+i]!==key))invalid();covered.push(...group.fields);
 }
 if(covered.length!==order.length||new Set(covered).size!==order.length)invalid();
 return {...presentation,schema_groups:groups};
}
export function comparisonGlyph(glyph) {
 validateGlyph(glyph);
 const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox',glyph.view_box.join(' '));svg.setAttribute('class','comparison-glyph');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');svg.style.setProperty('--glyph-width-ratio',String(glyph.view_box[2]/7.2));svg.style.setProperty('--glyph-height-ratio',String(glyph.view_box[3]/7.2));
 function draw(spec){const node=document.createElementNS(ns,spec.tag);for(const [key,value] of Object.entries(spec.attrs))node.setAttribute(key,value);for(const child of spec.children||[])node.append(draw(child));return node;}
 for(const spec of glyph.nodes)svg.append(draw(spec));return svg;
}
export function changedComparisonFields(previous,current) {
 if(!previous||previous.identity===current.identity)return [];
 const before=new Map(previous.vector.map(f=>[f.key,JSON.stringify(f.value)]));
 return current.vector.filter(f=>before.has(f.key)&&before.get(f.key)!==JSON.stringify(f.value)).map(f=>f.key);
}
export function cueComparisonChanges(fields,changed) {
 const animations=[];
 if(!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
  for(const field of fields)if(changed.includes(field.dataset.feature)){
   const cue=field.querySelector('.comparison-change-cue');
   if(cue?.animate)animations.push(cue.animate([{opacity:0},{opacity:.22,offset:.22},{opacity:0}],{duration:420,easing:'ease-out'}));
  }
 return ()=>{for(const animation of animations)animation.cancel();};
}

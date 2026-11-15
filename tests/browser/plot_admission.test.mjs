// HOP Design
// hop-design/tests/browser/plot_admission.test.mjs
// Preserve validated plot trees and their selection actions through mounting.
// Module Author(s): Eric J. South
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const uri=source=>'data:text/javascript;base64,'+Buffer.from(source).toString('base64');
const source=await readFile(new URL('../../src/hop_design/assets/survey_explorer/plot.js',import.meta.url),'utf8');
const {drawPlot}=await import(uri(source.replace('"./grouped_navigation.js"',JSON.stringify(uri('export const groupedNavigation=()=>{};')))));

function plot(t) {
  const previous=globalThis.DOMParser;
  t.after(()=>{globalThis.DOMParser=previous;});
  let parses=0,broken=false;
  const handlers=new Map(),path={dataset:{members:'["A"]'},addEventListener:(name,fn)=>handlers.set(name,fn)};
  const svg={dataset:{},querySelector:()=>null,querySelectorAll:selector=>selector==='[data-members]'?[path]:[]};
  const document={documentElement:svg,querySelector:()=>broken?{}:null};
  svg.ownerDocument=document;
  globalThis.DOMParser=class{parseFromString(){parses++;return document;}};
  const container={children:['old'],replaceChildren(...children){this.children=children;}};
  const record={materialized_realization_id:'A',values:{loop_nt:4}};
  return {container,record,svg,handlers,parses:()=>parses,break:()=>{broken=true;}};
}

for(const prepared of [false,true])test(`${prepared?'Admitted SVG':'SVG text'} retains exact paths and keyboard selection without reparsing`,t=>{
  const p=plot(t),selected=[],hovered=[];
  const drawing=prepared?new DOMParser().parseFromString('<svg/>','image/svg+xml').documentElement:'<svg/>';
  drawPlot(p.container,{axes:[],paths:[p.record]},drawing,{path:rows=>selected.push(rows),hover:rows=>hovered.push(rows)});
  assert.equal(p.parses(),1,'The admitted SVG must be parsed only once before mounting');
  assert.equal(p.container.children[0],p.svg,'Mount the same tree without cloning or changing paths');
  p.handlers.get('pointerenter')();
  let prevented=false;
  p.handlers.get('keydown')({key:'Enter',preventDefault(){prevented=true;}});
  assert.equal(prevented,true);
  assert.deepEqual(selected,[[p.record]]);
  assert.deepEqual(hovered,[[p.record]]);
});

for(const prepared of [false,true])test(`${prepared?'Admitted SVG':'SVG text'} rejects a parse error before replacing the previous plot`,t=>{
  const p=plot(t);
  const drawing=prepared?new DOMParser().parseFromString('<svg','image/svg+xml').documentElement:'<svg';
  p.break();
  assert.throws(()=>drawPlot(p.container,{axes:[],paths:[p.record]},drawing,{}),/Invalid survey drawing/);
  assert.deepEqual(p.container.children,['old']);
});

for(const compactSequences of [false,true])test(`compact sequence domains ${compactSequences?'omit':'retain'} unlabeled coverage ticks without changing recorded paths`,t=>{
  const p=plot(t),groups=[];
  function node(parameter,label,pinned=false){
    const handlers=new Map();
    const group={dataset:{parameter,nodeValue:'"AAAA"'},removed:false,
      querySelector:selector=>selector==='title'?{textContent:'Recorded value'}:(label||pinned?{}:null),
      setAttribute(){},addEventListener:(key,fn)=>handlers.set(key,fn),remove(){this.removed=true;},handlers};
    groups.push(group);return group;
  }
  const dense=node('loop_word',false),visible=node('loop_word',true),pin=node('loop_word',false,true),numeric=node('loop_nt',false);
  const old=p.svg.querySelectorAll;
  p.svg.querySelectorAll=selector=>selector==='[data-node-value]'?groups.filter(g=>!g.removed):old(selector);
  const choices={axes:[{key:'loop_word',representation:'sequence'},{key:'loop_nt',representation:'span'}],paths:[p.record]},before=structuredClone(choices);
  drawPlot(p.container,choices,p.svg,{}, {compactSequences});
  assert.equal(dense.removed,compactSequences);
  assert.equal(dense.handlers.has('focus'),!compactSequences,'unpainted values must not become invisible keyboard stops');
  for(const group of [visible,pin,numeric])assert.equal(group.removed,false);
  assert.deepEqual(choices,before);assert.equal(p.handlers.has('click'),true);
});

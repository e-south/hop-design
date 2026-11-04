import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../../src/hop_design/assets/design_explorer/route_scenes.js',import.meta.url),'utf8');
// Anchor choice is independent of DOM, transport and scene rendering.
const {retainedSceneAnchor,sceneSlotGeometry,previewScenePhases}=await import('data:text/javascript;base64,'+Buffer.from(source.replace(/^import .*;\n/gm,'')).toString('base64'));

test('changing route disclosure retains the inspected phase or its nearest surviving neighbor',()=>{
 const phases=['source','copied','cleaved','separated','retained','annealed','closed'];
 assert.equal(retainedSceneAnchor(phases,'annealed',['source','annealed','closed']),'annealed');
 assert.equal(retainedSceneAnchor(phases,'separated',['source','cleaved','annealed','closed']),'cleaved');
 assert.equal(retainedSceneAnchor(phases,'retained',['source','cleaved','annealed','closed']),'annealed');
 assert.equal(retainedSceneAnchor(phases,'closed',['source','cleaved']),'cleaved');
 assert.equal(retainedSceneAnchor(phases,'source',[]),null);
 assert.equal(retainedSceneAnchor(phases,'unknown',['source']),null);
});

test('scene slots follow measured pin bounds and remain fixed during hover',()=>{
 const pinned=sceneSlotGeometry(null,'0 0 1200 400',true);
 assert.deepEqual(pinned,{width:1200,height:400});
 assert.equal(sceneSlotGeometry(pinned,'0 0 1600 200',false),pinned,'Hover must not reflow the route');
 assert.equal(sceneSlotGeometry(null,'0 0 1600 200',false),null,'Hover cannot establish a new slot budget');
 assert.deepEqual(sceneSlotGeometry(pinned,'0 0 1600 200',true),{width:1600,height:200},'An explicit pin can adopt its measured frame');
});

test('malformed scene bounds fail before changing the slot',()=>{
 for(const frame of ['',null,'0 0 0 10','0 0 10 -1','0 0 Infinity 10','0 0 10','1 0 10 10','0 0 10 10 10'])
  assert.throws(()=>sceneSlotGeometry(null,frame,true),/scene frame/i);
});

test('route bundling never delays a visible hairpin and never asks for hidden phases',()=>{
 const view={top:0,bottom:800},phases=['duplex','cleaved_duplex'];
 assert.deepEqual(previewScenePhases(view,{top:-600,bottom:20},phases),[]);
 assert.deepEqual(previewScenePhases(view,{top:790,bottom:900},phases),[]);
 assert.deepEqual(previewScenePhases(view,{top:-600,bottom:0},phases),phases);
 assert.deepEqual(previewScenePhases(view,{top:-600,bottom:0},[]),[]);
});

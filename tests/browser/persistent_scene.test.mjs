import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async name=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL(`../../src/hop_design/assets/design_explorer/${name}.js`,import.meta.url))).toString('base64'));

test('persistent scenes retain mounted geometry for selection changes and release it on close',async()=>{
  const {persistentScene}=await load('persistent_scene');
  let calls=0;const host={replaceChildren(...nodes){this.nodes=nodes;}};
  const scene=persistentScene(host), node={geometry:'first'};
  assert.equal(scene.update('edition/query',()=>{calls++;return node;}),true);
  assert.equal(scene.update('edition/query',()=>{calls++;return {};}),false);
  assert.equal(calls,1);assert.equal(host.nodes[0],node);
  assert.equal(scene.update('edition/new-query',()=>({geometry:'second'})),true);
  scene.clear();assert.deepEqual(host.nodes,[]);
});

test('reattaching the same map preserves zoom and its original fit frame',async()=>{
  const {mapCamera}=await load('map_camera');
  const handlers=new Map(),attributes=new Map([['viewBox','0 0 1000 800']]);
  const svg={getAttribute:k=>attributes.get(k),setAttribute:(k,v)=>attributes.set(k,v)};
  const host={querySelector:()=>svg,addEventListener:(k,v)=>handlers.set(k,v),removeEventListener:k=>handlers.delete(k)};
  const button={addEventListener:(k,v)=>handlers.set('fit',v),removeEventListener(){}};
  const camera=mapCamera(host,button);camera.attach();
  handlers.get('keydown')({target:host,key:'+',preventDefault(){}});
  const zoomed=attributes.get('viewBox');assert.notEqual(zoomed,'0 0 1000 800');
  camera.attach();assert.equal(attributes.get('viewBox'),zoomed);
  handlers.get('fit')();assert.equal(attributes.get('viewBox'),'0 0 1000 800');camera.close();
});

test('map fit uses molecular content bounds rather than the publication caption frame',async()=>{
  const {mapCamera}=await load('map_camera');
  const handlers=new Map(),attributes=new Map([['viewBox','0 0 1200 480'],['data-map-frame','400 100 300 200']]);
  const svg={getAttribute:k=>attributes.get(k),setAttribute:(k,v)=>attributes.set(k,v)};
  const host={querySelector:()=>svg,addEventListener:(k,v)=>handlers.set(k,v),removeEventListener:k=>handlers.delete(k)};
  const button={addEventListener:(k,v)=>handlers.set('fit',v),removeEventListener(){}};
  const camera=mapCamera(host,button);camera.attach();
  assert.equal(attributes.get('viewBox'),'400 100 300 200');
  handlers.get('keydown')({target:host,key:'+',preventDefault(){}});camera.attach();
  assert.notEqual(attributes.get('viewBox'),'400 100 300 200');
  handlers.get('fit')();assert.equal(attributes.get('viewBox'),'400 100 300 200');camera.close();
});

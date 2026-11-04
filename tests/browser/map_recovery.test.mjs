import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const uri=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
const source=name=>readFile(new URL(`../../src/hop_design/assets/design_explorer/${name}.js`,import.meta.url),'utf8');
function environment(t){
 const names=['document','MutationObserver','ResizeObserver','requestAnimationFrame','cancelAnimationFrame','Path2D'];
 const saved=Object.fromEntries(names.map(n=>[n,globalThis[n]]));t.after(()=>Object.assign(globalThis,saved));
 const frames=new Map(),observers=[];let serial=0;
 globalThis.requestAnimationFrame=fn=>{frames.set(++serial,fn);return serial;};globalThis.cancelAnimationFrame=id=>frames.delete(id);
 globalThis.MutationObserver=globalThis.ResizeObserver=class{constructor(fn){this.fn=fn;observers.push(this);}observe(target,options){this.options=options;}disconnect(){this.closed=true;}};
 globalThis.Path2D=class{};
 function element(tag){
  const attrs=new Map(),handlers=new Map(),context={painted:0,clears:0,setTransform(){},clearRect(){this.painted=0;this.clears++;},beginPath(){},closePath(){},arc(){},moveTo(){},lineTo(){},fillText(){},fill(){this.painted++;},stroke(){},setLineDash(){}};
  return {tag,dataset:{},style:{},children:[],handlers,context,
   setAttribute:(k,v)=>attrs.set(k,String(v)),getAttribute:k=>attrs.get(k)??null,removeAttribute:k=>attrs.delete(k),
   replaceChildren(...c){this.children=c;},append(...c){this.children.push(...c);},remove(){this.removed=true;},
   addEventListener(k,v){assert.ok(!handlers.has(k),'No duplicated lifecycle registration');handlers.set(k,v);},removeEventListener:k=>handlers.delete(k),
   getContext:()=>context,getBoundingClientRect:()=>({left:0,top:0,width:400,height:200})};
 }
 globalThis.document={createElement:element,createElementNS:(ns,tag)=>element(tag)};
 return {frames,observers,element,flush(){const f=[...frames.values()];frames.clear();f.forEach(fn=>fn());}};
}
test('indexed canvas recovery preserves camera, selection, foreground-only hover and clean remount',async t=>{
 const {frames,element,flush}=environment(t);let s=await source('indexed_map');
 for(const name of ['map_index','map_raster'])s=s.replace(`'./${name}.js'`,JSON.stringify(uri(await source(name))));
 const {indexedMap}=await import(uri(s)),host=element('div'),actions=[];
 const map=indexedMap(host,ids=>actions.push(ids),ids=>actions.push(ids));t.after(()=>map.close());
 const rows=['A','B'].map(id=>({materialized_realization_id:id,matches:true,values:{loop_word:'AAAA'}}));
 const data={schema:'hop.inspection-map/v1',digest:'edition',frame:[0,0,100,100],radius:2,points:[[0,0,0],[1,100,100]]};
 map.update(data,rows,'A');flush();const [svg,cloud,overlay]=host.children,view=svg.getAttribute('viewBox');
 assert.equal(cloud.context.painted,2);cloud.context.painted=0;
 for(const canvas of [cloud,overlay])canvas.handlers.get('contextrestored')?.({target:canvas});
 assert.equal(frames.size,1,'One repaint for restored buffers');flush();
 assert.equal(cloud.context.painted,2);assert.ok(overlay.context.painted>0);assert.deepEqual(actions,[]);
 assert.equal(host.children[0],svg);assert.equal(svg.getAttribute('viewBox'),view);
 const clearCount=cloud.context.clears;map.focus(['B']);flush();assert.equal(cloud.context.clears,clearCount,'Hover does not repaint the background');
 cloud.handlers.get('contextrestored')({target:cloud});map.clear();assert.equal(frames.size,0);
 for(const canvas of [cloud,overlay]){assert.equal(canvas.handlers.size,0);assert.equal(canvas.width*canvas.height,0);}
 map.update(data,rows,'A');flush();const remounted=host.children.slice(1,3);assert.notEqual(remounted[0],cloud);
 assert.ok(remounted.every(canvas=>canvas.handlers.has('contextrestored')));map.close();
 assert.ok(remounted.every(canvas=>canvas.handlers.size===0));assert.equal(frames.size,0);
});
test('SVG raster recovery preserves retained points, detached lifecycle and foreground-only focus',async t=>{
 const {element,frames,observers,flush}=environment(t);
 const group={dataset:{selected:'true'},getAttribute(){return null;}};
 const circle={closest:()=>group,getAttribute:key=>({cx:'10',cy:'20',r:'2',fill:'#216e72',stroke:'#216e72','stroke-width':'1','stroke-dasharray':'none'}[key]??null)};
 const svg={style:{},getAttribute:key=>key==='viewBox'?'0 0 100 100':null,querySelectorAll:q=>q==='[data-preparations]'?Array(1024).fill(group):q==='circle'?Array(1024).fill(circle):[]};
 const host=element('div');host.querySelector=()=>svg;
 const {mapRaster}=await import(uri(await source('map_raster'))),map=mapRaster(host);t.after(()=>map.close());map.attach('similarity');flush();
 const [cloud,overlay]=host.children;assert.equal(cloud.context.painted,1024);cloud.context.painted=0;
 for(const canvas of [cloud,overlay])canvas.handlers.get('contextrestored')?.({target:canvas});
 assert.equal(frames.size,1);flush();assert.equal(cloud.context.painted,1024);assert.ok(overlay.context.painted>0);assert.equal(svg.style.opacity,'0');
 const clears=cloud.context.clears;group.dataset.linkedCount='1';observers.find(o=>o.options?.attributeFilter).fn([{target:group,attributeName:'data-linked-count'}]);flush();assert.equal(cloud.context.clears,clears);
 map.attach('families');cloud.handlers.get('contextrestored')({target:cloud});assert.equal(frames.size,0);assert.equal(svg.style.opacity,'');
 map.attach('similarity');flush();assert.equal(cloud.context.painted,1024);
 cloud.handlers.get('contextrestored')({target:cloud});map.close();assert.equal(frames.size,0);
 for(const canvas of [cloud,overlay]){assert.equal(canvas.handlers.size,0);assert.equal(canvas.width*canvas.height,0);}
});

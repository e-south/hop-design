import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load=async()=>import('data:text/javascript;base64,'+Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/map_index.js',import.meta.url))).toString('base64'));
const rows=[{materialized_realization_id:'a',matches:true},{materialized_realization_id:'b',matches:false}];
const packet=()=>({schema:'hop.inspection-map/v1',digest:'geometry',frame:[0,0,100,100],radius:2,points:[[1,60,20],[0,10,20]]});
test('spatial picking resolves exact members including excluded points and empty space',async()=>{
  const {pointIndex}=await load(),index=pointIndex(packet(),rows);
  assert.equal(index.nearest(60,21,5).row.materialized_realization_id,'b');
  assert.equal(index.nearest(60,21,5).row.matches,false);
  assert.equal(index.nearest(11,20,5).row.materialized_realization_id,'a');
  assert.equal(index.nearest(35,20,4),null);
});
test('map membership must be a complete one-to-one reference to the cohort',async()=>{
  const {pointIndex}=await load();
  for(const change of [p=>p.points[1][0]=1,p=>p.points[0][0]=8,p=>p.points[0][1]=NaN,p=>p.frame[2]=0,p=>p.points.pop()]) {
    const p=packet();change(p);assert.throws(()=>pointIndex(p,rows),/map/i);
  }
});

test('coincident coordinates preserve every exact member and stable keyboard order',async()=>{
  const {pointIndex}=await load(),p=packet();p.points=[[0,30,40],[1,30,40]];
  const index=pointIndex(p,rows);
  assert.equal(index.groups.length,1);
  assert.equal(index.points.length,2);
  assert.deepEqual(index.groups[0].points.map(p=>p.row.materialized_realization_id),['a','b']);
  assert.equal(index.nearest(30,40,5).group,index.groups[0]);
  assert.deepEqual(index.points.map(p=>[p.x,p.y]),[[30,40],[30,40]]);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source=new URL('../../src/hop_design/assets/design_explorer/',import.meta.url);
test('the inspector presents molecular views and retrieval without diagnostic panels',async()=>{
  const page=await readFile(new URL('index.html',source),'utf8');
  const inspector=page.split('<aside id="inspector"')[1].split('</aside>')[0];
  for(const id of ['figure-one','trace-context','figure-two','route-scenes','retrieve','download','record'])
    assert.match(inspector,new RegExp(`id="${id}"`),'Retain molecular views and exact export: '+id);
  for(const id of ['selection-details','inspection-facts','distributions','comparison-changes','nearby',
    'render-policy','route-presentation','render-info','recipe','selection-receipt','coverage','definitions'])
    assert.doesNotMatch(inspector,new RegExp(`id="${id}"`),'Remove reading-flow noise: '+id);
  assert.match(page,/id="bookmark"/,'Exact view export remains available');
  assert.match(page,/id="view-file"/,'Saved view restoration remains available');
});

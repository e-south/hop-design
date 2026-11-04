import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load = async () => import('data:text/javascript;base64,' + Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/artifacts.js', import.meta.url))).toString('base64'));

test('unchanged drawings reuse a bounded cache and missing artifacts fail explicitly', async () => {
  const {artifactLoader} = await load();
  let calls=0;
  const loader=artifactLoader(async url => {calls++; return {ok:url!=='/missing',text:async()=>url};},2,100);
  assert.equal(await loader.text('/a'),'/a');
  assert.equal(await loader.text('/a'),'/a');
  assert.equal(calls,1);
  await loader.text('/b'); await loader.text('/c'); await loader.text('/a');
  assert.equal(calls,4);
  await assert.rejects(loader.text('/missing'), /expired|unavailable/i);
  loader.clear(); await loader.text('/a'); assert.equal(calls,6);
});

test('oversized artifacts remain readable without being retained', async () => {
  const {artifactLoader} = await load(); let calls=0;
  const loader=artifactLoader(async()=>{calls++;return {ok:true,text:async()=>'long drawing'};},2,4);
  assert.equal(await loader.text('/large'),'long drawing');
  await loader.text('/large'); assert.equal(calls,2);
});

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
}

for (const pending of ['response', 'body']) {
  test(`clearing during a pending ${pending} does not refill the cache`, async () => {
    const {artifactLoader} = await load();
    const wait = deferred(); let calls = 0;
    const loader = artifactLoader(async () => {
      calls++;
      if (calls > 1) return {ok:true, text:async () => 'fresh'};
      return pending === 'response' ? wait.promise : {ok:true, text:() => wait.promise};
    });
    const old = loader.text('/drawing');
    await Promise.resolve();
    loader.clear();
    wait.resolve(pending === 'response' ? {ok:true, text:async () => 'old'} : 'old');
    assert.equal(await old, 'old');
    assert.equal(await loader.text('/drawing'), 'fresh');
    assert.equal(calls, 2);
  });
}

for (const oldFirst of [true, false]) {
  test(`old requests cannot replace the new cache generation (old first: ${oldFirst})`, async () => {
    const {artifactLoader} = await load();
    const oldBody = deferred(), newBody = deferred(); let calls = 0;
    const loader = artifactLoader(async () => ({ok:true, text:() => ++calls === 1 ? oldBody.promise : newBody.promise}));
    const old = loader.text('/drawing');
    await Promise.resolve();
    loader.clear();
    const fresh = loader.text('/drawing');
    await Promise.resolve();
    if (oldFirst) { oldBody.resolve('old'); await old; newBody.resolve('fresh'); await fresh; }
    else { newBody.resolve('fresh'); await fresh; oldBody.resolve('old'); await old; }
    assert.equal(await loader.text('/drawing'), 'fresh');
    assert.equal(calls, 2);
  });
}

test('concurrent misses account for one retained artifact per URL', async () => {
  const {artifactLoader} = await load();
  const body = deferred(); let calls = 0;
  const loader = artifactLoader(async url => {
    calls++;
    return {ok:true, text:() => url === '/a' ? body.promise : Promise.resolve('bbb')};
  }, 2, 6);
  const first = loader.text('/a'), second = loader.text('/a');
  body.resolve('aaa');
  await Promise.all([first, second]);
  await loader.text('/b');
  await loader.text('/a');
  await loader.text('/b');
  assert.equal(calls, 3);
});

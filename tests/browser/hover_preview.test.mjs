import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load = async () => import('data:text/javascript;base64,' + Buffer.from(await readFile(new URL('../../src/hop_design/assets/design_explorer/hover_preview.js', import.meta.url))).toString('base64'));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};

test('hover commits molecule and trace together and ignores superseded responses',async()=>{
  const {hoverPreview}=await load(), a=deferred(), b=deferred(), seen=[];
  const hover=hoverPreview(id=>id==='A'?a.promise:b.promise,async value=>()=>seen.push(value),()=>seen.push('pinned'),e=>{throw e;});
  const first=hover.show('A'),second=hover.show('B');
  b.resolve('B');
  a.resolve('A');await Promise.all([first,second]);
  assert.deepEqual(seen,['B']);
  hover.clear();assert.deepEqual(seen,['B','pinned']);
});

test('rapid hover requests keep only the latest waiting preparation',async()=>{
  const {hoverPreview}=await load(), a=deferred(), c=deferred(), calls=[], seen=[];
  const hover=hoverPreview(id=>{calls.push(id);return id==='A'?a.promise:c.promise;},async value=>()=>seen.push(value),()=>{},e=>{throw e;});
  const first=hover.show('A'), superseded=Array.from({length:500},(_,i)=>hover.show(`B${i}`)), latest=hover.show('C');
  assert.deepEqual(calls,['A']);
  await Promise.all(superseded);
  a.resolve('A');await first;
  assert.deepEqual(calls,['A','C']);
  c.resolve('C');await latest;
  assert.deepEqual(seen,['C']);
});

for (const action of ['invalidate','clear','close']) {
  test(`${action} drops waiting hover work`,async()=>{
    const {hoverPreview}=await load(), a=deferred(), calls=[], seen=[];
    const hover=hoverPreview(id=>{calls.push(id);return a.promise;},async value=>()=>seen.push(value),()=>seen.push('pinned'),e=>{throw e;});
    const first=hover.show('A'), waiting=hover.show('B');
    hover[action]();a.resolve('A');await Promise.all([first,waiting]);
    assert.deepEqual(calls,['A']);
    assert.deepEqual(seen,action==='invalidate'?[]:['pinned']);
  });
}

test('a failed obsolete preview does not block a new request after clearing',async()=>{
  const {hoverPreview}=await load(), a=deferred(), calls=[], seen=[];
  const hover=hoverPreview(id=>{calls.push(id);return id==='A'?a.promise:Promise.resolve(id);},async value=>()=>seen.push(value),()=>seen.push('pinned'),e=>seen.push(e.message));
  const first=hover.show('A');hover.clear();const fresh=hover.show('C');
  a.reject(Error('obsolete'));await Promise.all([first,fresh]);
  assert.deepEqual(calls,['A','C']);assert.deepEqual(seen,['pinned','C']);
});

test('waiting work coalesces while the active molecular drawing is prepared',async()=>{
  const {hoverPreview}=await load(), prepared=deferred(), calls=[], seen=[];
  const hover=hoverPreview(async id=>{calls.push(id);return id;},async value=>{if(value==='A') await prepared.promise;return ()=>seen.push(value);},()=>{},e=>{throw e;});
  const first=hover.show('A');await Promise.resolve();
  const skipped=hover.show('B'),latest=hover.show('C');await skipped;
  assert.deepEqual(calls,['A']);prepared.resolve();await Promise.all([first,latest]);
  assert.deepEqual(calls,['A','C']);assert.deepEqual(seen,['C']);
});

test('leaving or teardown invalidates prepared views and failed previews restore the pin',async()=>{
  const {hoverPreview}=await load(), pending=deferred(), seen=[];
  const hover=hoverPreview(async id=>id,async()=>{await pending.promise;return ()=>seen.push('stale');},()=>seen.push('pinned'),e=>seen.push(e.message));
  const request=hover.show('A');await Promise.resolve();hover.clear();pending.resolve();await request;
  assert.deepEqual(seen,['pinned']);
  const failed=hoverPreview(async()=>{throw Error('gone');},async()=>()=>{},()=>seen.push('pinned'),e=>seen.push(e.message));
  await failed.show('A');assert.deepEqual(seen,['pinned','pinned','gone']);
  failed.close();await failed.show('B');assert.deepEqual(seen,['pinned','pinned','gone','pinned']);
});

test('hover announces a pending identity immediately and releases only its matching complete drawing',async()=>{
  const {hoverPreview}=await load(),a=deferred(),b=deferred(),events=[];
  const hover=hoverPreview(id=>id==='A'?a.promise:b.promise,async value=>()=>events.push(['draw',value]),()=>events.push(['restore']),()=>{}, {
    pending:id=>events.push(['pending',id]),ready:id=>events.push(['ready',id]),clear:()=>events.push(['clear']),
  });
  hover.invalidate('A');
  assert.deepEqual(events,[['pending','A']],'Feedback must precede the hover debounce or network work');
  const first=hover.show('A');hover.invalidate('B');const last=hover.show('B');
  a.resolve('A');await first;
  assert.equal(events.some(e=>e[0]==='ready'),false,'An obsolete completion cannot release the new loading panel');
  b.resolve('B');await last;
  assert.deepEqual(events.slice(-2),[['draw','B'],['ready','B']]);
  hover.clear();assert.deepEqual(events.slice(-2),[['restore'],['clear']]);
});

test('a current hover failure is attributed to its pending identity; obsolete failures stay silent',async()=>{
  const {hoverPreview}=await load(),slow=deferred(),events=[];
  const hover=hoverPreview(id=>id==='A'?slow.promise:Promise.reject(Error('unavailable')),async()=>()=>{},()=>{},()=>{}, {
    pending:id=>events.push(['pending',id]),failed:(error,id)=>events.push(['failed',id,error.message]),clear:()=>events.push(['clear']),
  });
  const a=hover.show('A'),b=hover.show('B');slow.reject(Error('old'));
  await Promise.all([a,b]);
  assert.deepEqual(events.filter(e=>e[0]==='failed'),[['failed','B','unavailable']]);
  hover.close();assert.equal(events.at(-1)[0],'clear');
});

test('returning to the pinned point restores it without a spinner or redundant request',async()=>{
  const {hoverPreview}=await load(),pending=deferred(),calls=[],events=[];
  const hover=hoverPreview(id=>{calls.push(id);return pending.promise;},async id=>()=>events.push(['draw',id]),()=>events.push(['restore']),()=>{}, {
    current:()=> 'A',pending:id=>events.push(['loading',id]),clear:()=>events.push(['clear']),
  });
  const other=hover.show('B');hover.invalidate('A');const same=hover.show('A');
  assert.deepEqual(events.filter(e=>e[0]==='loading'),[['loading','B']]);
  assert.equal(events.at(-1)[0],'clear');
  pending.resolve('B');await Promise.all([other,same]);
  assert.deepEqual(calls,['B']);assert.equal(events.some(e=>e[0]==='draw'),false);
});

test('selection invalidation holds the displayed preview and rejects in-flight replacements',async()=>{
  const {hoverPreview}=await load(),pending=deferred(),seen=[];
  const hover=hoverPreview(id=>id==='A'?Promise.resolve(id):pending.promise,async id=>()=>seen.push(id),()=>seen.push('committed'),()=>{});
  await hover.show('A');const next=hover.show('B');hover.invalidate();
  assert.deepEqual(seen,['A'],'A pin must not erase its displayed preview while awaiting authority');
  pending.resolve('B');await next;assert.deepEqual(seen,['A']);
  hover.clear();assert.deepEqual(seen,['A','committed']);
});

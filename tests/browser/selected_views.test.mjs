import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const load = async () => import('data:text/javascript;base64,' + Buffer.from(await readFile(new URL('../../src/hop_design/assets/survey_explorer/selected_views.js', import.meta.url))).toString('base64'));

test('selected teaching and route commit together; late responses cannot replace them', async () => {
  const {coherentViews} = await load();
  let route = 'old', teaching = 'old', release;
  const views = coherentViews(async value => {
    if (value === 'slow') await new Promise(resolve => {release = resolve;});
    return () => {route = value;};
  }, async value => () => {teaching = value;}, () => {route = teaching = null;});
  const slow = views.show('slow');
  assert.equal(route, 'old'); assert.equal(teaching, 'old');
  await views.show('new');
  release(); await slow;
  assert.equal(route, 'new'); assert.equal(teaching, 'new');
});

test('an unavailable teaching drawing prevents a new route from committing', async () => {
  const {coherentViews} = await load();
  let route = 'old', teaching = 'old';
  const views = coherentViews(async () => () => {route = 'new';}, async () => {throw Error('missing teaching');}, () => {route = teaching = null;});
  await assert.rejects(views.show('new'), /missing teaching/);
  assert.equal(route, 'old'); assert.equal(teaching, 'old');
});

test('inspection loads only the visible molecular view and commits it atomically', async () => {
  const {coherentViews} = await load();
  const calls=[], commits=[];
  const views=coherentViews(async value=>{calls.push(['route',value]);return ()=>commits.push(['route',value]);},
    async value=>{calls.push(['teaching',value]);return ()=>commits.push(['teaching',value]);},()=>{});
  await views.show('a','molecule');
  assert.deepEqual(calls,[['teaching','a']]);
  assert.deepEqual(commits,[['teaching','a']]);
  await views.show('a','route');
  assert.deepEqual(calls,[['teaching','a'],['route','a']]);
  assert.deepEqual(commits,[['teaching','a'],['route','a']]);
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const {attachNumericBrush} = await import('data:text/javascript;base64,' + Buffer.from(await readFile(
  new URL('../../src/hop_design/assets/variant_explorer/choice_space_brush.js', import.meta.url)
)).toString('base64'));

test('discrete numeric choices never display a continuous full-domain brush', () => {
  const original = globalThis.document;
  globalThis.document = {createElementNS: () => ({style:{}, attributes:{}, setAttribute(k,v){this.attributes[k]=String(v);}})};
  try {
    for (const selection of [[7], [5,9], {minimum:6,maximum:8}]) {
      let nodes;
      attachNumericBrush({chart:{append(...items){nodes=items;}}, axis:{key:'R',label:'Self-paired arm',unit:'bp',values:[5,6,7,8,9].map(value=>({value}))},
        x:100,top:0,bottom:100,positions:new Map([[5,100],[6,75],[7,50],[8,25],[9,0]]),selection,
        onRange(){},onClear(){},onDetail(){}});
      const [track,band]=nodes;
      track.onfocus();
      if (Array.isArray(selection)) {
        assert.equal(band.style.display,'none');
        assert.equal(track.attributes['aria-valuetext'],selection.join(' or ')+' bp; discrete selection');
      } else {
        assert.equal(band.style.display,'');
        assert.equal(band.attributes.height,'50');
      }
    }
  } finally {globalThis.document=original;}
});

// HOP Design
// hop-design/tests/browser/retained_preview_label.test.mjs
// Exercise retained preview labels through editor render and restoration handlers.
// Module Author(s): Eric J. South
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createContext,runInContext} from 'node:vm';
const source=await readFile(new URL('../../src/hop_design/assets/design_explorer/editor.js',import.meta.url),'utf8');
const label=source.slice(source.indexOf('function pinnedPreviewLabel('),source.indexOf('function clearHoverDrawing('));
const render=source.slice(source.indexOf('async function render('),source.indexOf('function download('));
const action=source.slice(source.indexOf('async function act('),source.indexOf('const suspendedControls='));
const restoreStart=source.indexOf('},()=>{\n  clearHoverDrawing();');
const restore=source.slice(restoreStart+2,source.indexOf('},error=>',restoreStart)+1);
const noop=()=>{};
function fixture(excluded=true,matching=0){
 const preview={summary:{atlas:{materialized_realization_id:'A',states:[]}},record:'record.json'};
 return {preview,preview_status:excluded?'excluded_by_query':'selected',selection:excluded?null:{materialized_realization_id:'A'},
  stage:'all',stage_options:[],presentation:{landscape:'families',molecule:'molecule'},plots:{families:'f',inspection:'t',distributions:'d',parameters:'p'},
  cohort_summary:{eligible_products:matching,product:'hairpin'},choices:{matching_preparations:matching,query:{parameters:[{key:'loop_word',values:['AAAA']}]},axes:[]},
  render_policy:'current',explanation:{guidance:'Inspect recorded preparations'},commands:'design inspect'};
}
function editor(){
 const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',dataset:{},hidden:false,setAttribute:noop,replaceChildren:noop});return nodes.get(id);};
 const drawn=[],cleared=[];
 const context=createContext({$:get,state:null,mode:'families',molecularMode:'molecule',definitionsKey:'p',inspectorDismissed:false,busy:false,
  artifacts:{text:async()=>{throw Error('No new drawing should be requested');}},
  plots:{needsMap:()=>false,needsTrace:()=>false,draw:noop},distributionScene:{matches:()=>true},
  views:{show:async preview=>drawn.push(preview),clear:()=>cleared.push(true)},
  validateInspectionFacts:noop,comparisonView:{prepare:()=>noop},scenes:{pin:noop,restore:noop,pending:noop},nearby:{clear:noop},
  discovery:{update:noop},frequencies:{update:noop},colors:{update:noop},mapView:{attach:noop},raster:{attach:noop},
  selectedTrace:{show:noop},local:{update:noop,suspend:noop},viewport:{stage:noop},
  clearHoverDrawing:noop,setMolecularMode:noop,connect:noop,Option:function(){},
  pendingControls:noop,loading:{beginAction:noop,readyAction:noop},hover:{invalidate:noop,clear:noop},
 });
 runInContext(label+render+action+`;globalThis.restorePreview=${restore};`,context);
 context.rendering={blocked:false,show:next=>context.render(next)};
 return {context,get,drawn,cleared};
}

test('zero-result render visibly labels the retained molecule and offers filter recovery',async()=>{
 const ui=editor(),state=fixture();await ui.context.render(state);
 assert.equal(ui.get('preview-label').textContent,'Preview · outside current filters');
 assert.match(ui.get('preview-recovery').textContent,/clear or revise.*filters/i);
 assert.doesNotMatch(ui.get('preview-recovery').textContent,/choose an eligible trace/i);
 assert.equal(ui.get('preview-recovery').hidden,false);
 assert.equal(ui.get('retrieve').disabled,true);assert.equal(ui.get('inspector').hidden,false);
 assert.equal(ui.drawn[0],state.preview);assert.equal(ui.cleared.length,0,'retain the molecular drawing');
});

test('query completion and hover restoration retain exclusion feedback until filters recover',async()=>{
 const ui=editor();await ui.context.render(fixture(false,1));
 const excluded=fixture();ui.context.post=async()=>excluded;
 await ui.context.act('query',{},false);
 assert.equal(ui.get('preview-label').textContent,'Preview · outside current filters','action finally must preserve the excluded label');
 ui.get('preview-label').textContent='Preparing preview…';ui.context.restorePreview();
 assert.equal(ui.get('preview-label').textContent,'Preview · outside current filters','leaving hover must restore the pinned status');
 assert.equal(ui.get('inspector').hidden,false);assert.equal(ui.cleared.length,0);
 ui.context.post=async()=>fixture(false,1);await ui.context.act('query',{},false);ui.context.restorePreview();
 assert.equal(ui.get('preview-label').textContent,'');assert.equal(ui.get('preview-recovery').hidden,true);assert.equal(ui.get('retrieve').disabled,false);
 await ui.context.act('select',{materialized_realization_id:'A'},false);
 assert.equal(ui.get('preview-label').textContent,'','pinning clears the exclusion label');
});

test('an excluded preview with eligible alternatives keeps its trace-selection guidance',async()=>{
 const ui=editor();await ui.context.render(fixture(true,2));
 assert.equal(ui.get('preview-label').textContent,'Preview · outside current filters');
 assert.match(ui.get('preview-recovery').textContent,/Choose an eligible trace/);
});

test('selection avoids a redundant heading while the next drawing loads',async()=>{
 const ui=editor();await ui.context.render(fixture(false,1));
 let finish;ui.context.post=()=>new Promise(resolve=>{finish=resolve;});
 const pending=ui.context.act('select',{materialized_realization_id:'B'},false);
 assert.equal(ui.get('preview-label').textContent,'');
 finish(fixture(false,1));await pending;
});

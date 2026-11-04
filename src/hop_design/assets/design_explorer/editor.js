import {artifactLoader} from './artifacts.js';
import {molecularViewport} from './atlas.js';
import {coherentViews} from './selected_views.js';
import {landscape} from './landscape.js';
import {parameterKeys, parameterSelector} from './parameters.js';
import {figureLayout,validateFigureLayout} from './figure_layout.js';
import {localChoices} from './local_choices.js';
import {hoverPreview} from './hover_preview.js';
import {mapCamera} from './map_camera.js';
import {mapRaster} from './map_raster.js';
import {inspectionOverlay,transientInspector,escapeInspection} from './inspection_overlay.js';
import {persistentScene} from './persistent_scene.js';
import {pendingRender} from './pending_render.js';
import {hydrateCohort} from './cohort_state.js';
import {neighboringChoices} from './neighbors.js';
import {inspectionLoading} from './inspection_loading.js';
import {colorControls} from './color_controls.js';
import {inspectionFacts} from './inspection_facts.js';
import {routeScenes} from './route_scenes.js';
import {resizableInspector} from './inspector_resize.js';
import {comparisonStrip} from './comparison_features.js';
import {discoveryControls} from './discovery.js';

const $ = id => document.getElementById(id), token = document.querySelector('meta[name=hop-token]').content;
let state=null, mode='families', molecularMode='molecule', busy=false, teachingURL=null;
let inspectorDismissed=false, figureScroll=0, figureReturn=null, definitionsKey=null, hoverLayout=null;
const rendering=pendingRender(render);
const figure=figureLayout($('figure-one-plate'),$('molecular-area'),$('trace-context'));
const facts=inspectionFacts($('inspection-facts'));
let pinnedFacts=()=>facts.clear();
let pinnedComparison=()=>comparisonView.clear();
const transient=transientInspector($('inspector'),$('inspector-scroll'));
const selectedTrace=inspectionOverlay($('trace-context'));
const distributionScene=persistentScene($('distributions'));
const artifacts=artifactLoader();
const loading=inspectionLoading($);
const scenes=routeScenes($('route-scenes'),$('inspector-scroll'),job=>post('scenes',{materialized_realization_id:job.identity,phases:job.phases}),artifacts);
const resizing=resizableInspector($('object'),$('inspector'),$('inspector-scroll'),$('inspector-resize'),()=>{connect();scenes.refresh();},()=>showHover(null));
const nearby=neighboringChoices($('nearby'),$('neighbor-options'),post,()=>state,id=>act('select',{materialized_realization_id:id}));
const discovery=discoveryControls($,post,{inspect:async job_id=>{
  if(!await act('inspect-discovery',{job_id}))throw Error($('status').textContent||'Finish the current drawing update before opening results.');
}});
const mapView=mapCamera($('plot'),$('fit-map'));
const raster=mapRaster($('plot'));
const local=localChoices($('molecular-area'),{
  surface:$('feature-details'),
  onQuery:query=>act('query',{query}),onColor:(key,value)=>colors.choose(key,value),canColor:key=>colors.available(key),
  onLoop:()=>act('sample',{strategy:'loop'}),onFocus:keys=>plots.focusParameters(keys),
});
const viewport=molecularViewport($('route'),$('fit'),keys=>plots.focusParameters(keys));
const plots=landscape($('plot'),$('members'),q=>act('query',{query:q}),id=>act('select',{materialized_realization_id:id}),keys=>viewport.highlight(keys),showHover);
const comparisonView=comparisonStrip($('map-comparison'),keys=>plots.focusParameters(keys));
const colors=colorControls($('map-color'),lens=>plots.color(lens));
for(const event of ['pointerover','focusin']) $('teaching').addEventListener(event,e=>{
  const feature=e.target.closest(parameterSelector);
  if(feature) plots.focusParameters(parameterKeys(feature));
});
// Leaving a feature clears its highlight, not the preparation or local chooser.
$('teaching').addEventListener('pointerleave',e=>{if(!$('molecular-area').contains(e.relatedTarget))plots.focusParameters([]);});
$('teaching').addEventListener('focusout',e=>{if(!$('molecular-area').contains(e.relatedTarget))plots.focusParameters([]);});
const views=coherentViews(p=>viewport.prepare(p),async p=>{
  if (!p) return ()=>{$('teaching').replaceChildren();};
  if(p.teaching===teachingURL) return ()=>{};
  const doc=new DOMParser().parseFromString(await artifacts.text(p.teaching),'image/svg+xml');
  if (doc.querySelector('parsererror')) throw Error('Invalid teaching SVG.');
  return ()=>{$('teaching').replaceChildren(doc.documentElement);teachingURL=p.teaching;};
},()=>{viewport.clear();$('teaching').replaceChildren();teachingURL=null;});

function svgDocument(text) {
  const doc=new DOMParser().parseFromString(text,'image/svg+xml');
  if(doc.querySelector('parsererror')) throw Error('Invalid molecular preview drawing.');
  return doc.documentElement;
}
function clearHoverDrawing() {
  hoverLayout=null;$('hover-molecule').hidden=true;$('hover-molecule').replaceChildren();
  $('molecular-area').classList.remove('previewing');transient.clear();
}
const hover=hoverPreview(async id=>{
  const phases=scenes.previewPhases($('figure-one-canvas'));
  return {value:await post('preview',{materialized_realization_id:id,...(phases.length?{phases}:{})}),phases};
},async({value,phases})=>{
  const [molecule,sceneCommit]=await Promise.all([artifacts.text(value.molecule),scenes.preparePreview(value,state,phases)]),a=svgDocument(molecule);
  if(a.dataset.preparationId!==value.materialized_realization_id) throw Error('Preview identity disagrees with its molecule.');
  if(value.trace.materialized_realization_id!==value.materialized_realization_id) throw Error('Preview identity disagrees with its trace.');
  const trace=selectedTrace.prepare(value.trace,state.trace_projection);
  const factCommit=facts.prepare(value.materialized_realization_id,value.inspection_explanation,value.construction_cost,{preview:true,referencePinned:Boolean(state.selection)});
  const comparisonCommit=comparisonView.prepare(value.materialized_realization_id,state);
  validateFigureLayout(value.figure_layout);
  return ()=>{
    hoverLayout=value.figure_layout;$('hover-molecule').replaceChildren(a);$('hover-molecule').hidden=false;trace();factCommit();
    $('preview-label').textContent=value.eligible?'Preparation':'Preview · outside current filters';
    $('molecular-area').classList.add('previewing');transient.show();$('inspector').hidden=false;
    sceneCommit();comparisonCommit();
    connect();
  };
},()=>{
  clearHoverDrawing();
  selectedTrace.show(state?.selected_trace,state?.trace_projection);
  pinnedFacts();pinnedComparison();scenes.restore();local.update(state);
  $('preview-label').textContent='Preparation';
  $('inspector').hidden=inspectorDismissed||!state?.preview;
  connect();
},error=>{$('status').textContent=error.message;},{
  current:()=>state?.preview?.summary.atlas.materialized_realization_id,
  pending(identity){
    local.suspend();scenes.pending(identity);loading.pending(identity);transient.show();$('inspector').hidden=false;
    $('preview-label').textContent='Preparing preview…';
  },
  ready:identity=>loading.ready(identity),
  failed(error,identity){scenes.previewFailed(identity);loading.failed(error,identity);$('preview-label').textContent='Preview unavailable';},
  clear:()=>loading.clear(),
});
function showHover(identity) {
  if(busy || rendering.blocked) return;
  // The preview controller already bounds work to one active and one latest target.
  if(identity) void hover.show(identity);else hover.clear();
}

async function post(action,payload,{independent=false,keepalive=false}={}) {
  if(rendering.blocked&&!independent) throw Error('Retry the pending drawing before changing this preparation.');
  const response=await fetch(`/api/${action}`,{method:'POST',keepalive,headers:{'Content-Type':'application/json','X-HOP-Editor-Token':token,'X-HOP-Inspection':'compact-v1',...(state?.cohort?{'X-HOP-Cohort':state.cohort}:{})},body:JSON.stringify({...payload,token:state?.token||''})});
  const value=await response.json(); if(!response.ok) throw Error(value.error || 'The inspection action failed.');
  return hydrateCohort(value,state);
}
function currentPresentation() {
  const color=colors.snapshot();return {...state.presentation,...(color?{color}:{})};
}
async function rememberCamera(includeColor=false) {
  if (!state.selection) return;
  const camera=molecularMode==='route'?viewport.camera():state.view_receipt.camera;
  const sameCamera=JSON.stringify(camera)===JSON.stringify(state.view_receipt.camera);
  const sameColor=JSON.stringify(colors.snapshot())===JSON.stringify(state.view_receipt.presentation.color);
  if(sameCamera&&(!includeColor||sameColor)) return;
  state=await post('view',{stage:state.stage,camera,presentation:currentPresentation()});
}
async function act(action,payload={},remember=true) {
  if(!state || busy || rendering.blocked) return false; hover.invalidate();busy=true;$('status').textContent='';
  local.suspend();scenes.pending(payload.materialized_realization_id);loading.beginAction(action,payload);
  if(['select','sample','restore','inspect-discovery'].includes(action)) {inspectorDismissed=false;delete $('inspector').dataset.dismissed;$('inspector').hidden=false;$('preview-label').textContent='Preparing selection…';}
  try {
    if(remember && action!=='view') await rememberCamera();
    const next=await post(action,payload);
    // A saved old-cohort view must not be replayed after this explicit switch.
    if(action==='inspect-discovery'&&location.hash.startsWith('#view='))history.replaceState(null,'',location.pathname+location.search);
    await rendering.show(next,action==='back'||action==='restore');
    if(next.inspection_notice)$('status').textContent=next.inspection_notice;
    return true;
  } catch(error) { $('status').textContent=error.message;return false; }
  finally {
    busy=false;
    if(rendering.blocked) loading.failedAction();
    else {hover.clear();loading.readyAction();scenes.restore();local.update(state);$('preview-label').textContent='Preparation';$('inspector').hidden=inspectorDismissed||!state.preview;}
    pendingControls();
  }
}
const suspendedControls=new Map();
function restoreControls() {
  for(const [control,disabled] of suspendedControls) control.disabled=disabled;
  suspendedControls.clear();
}
function pendingControls() {
  $('retry-render').hidden=!rendering.blocked;
  document.body.classList.toggle('render-pending',rendering.blocked);
  if(rendering.blocked) {
    for(const id of ['another','back','retrieve','bookmark','open-view','stage','route-view','render-policy','family-stage','clear','similarity','parameters','families']) {
      const control=$(id);if(!suspendedControls.has(control)) suspendedControls.set(control,control.disabled);control.disabled=true;
    }
    $('status').textContent='The new preparation is saved; its drawing could not load. Retry to display it.';
  }
}
$('retry-render').addEventListener('click',async()=>{
  if(busy) return;
  busy=true;$('retry-render').disabled=true;$('status').textContent='';loading.beginAction('retry');
  try {restoreControls();artifacts.clear();await rendering.retry();$('status').textContent='';}
  catch(error){$('status').textContent=error.message;pendingControls();}
  finally {busy=false;$('retry-render').disabled=false;if(rendering.blocked)loading.failedAction();else loading.readyAction();pendingControls();}
});
function setMolecularMode(mode) {
  molecularMode=mode;const route=mode==='route';
  const focused=$('inspector').dataset.focus==='figure-two';
  $('route-focus').hidden=!focused;$('route-scenes').hidden=focused;
  $('route-frame').hidden=!route;$('stage-label').hidden=!route;
  $('route-view').hidden=route||focused;$('focus-route').hidden=!route||focused;
  scenes.refresh();
  connect();
}
function connect() {
  const source=$('hover-molecule').hidden?$('teaching'):$('hover-molecule');
  figure.show(hoverLayout||state?.figure_layout,source.querySelector('svg'),$('trace-context').querySelector('svg'));
}
function focusFigure(id,trigger) {
  figureScroll=$('inspector-scroll').scrollTop;figureReturn=trigger;
  $('inspector').dataset.focus=id;$('return-map').hidden=false;$('inspector-scroll').scrollTop=0;
  $('return-map').focus();setMolecularMode(molecularMode);connect();
}
function returnToAtlas() {
  if(!$('inspector').dataset.focus)return;
  delete $('inspector').dataset.focus;$('return-map').hidden=true;
  $('inspector-scroll').scrollTop=figureScroll;figureReturn?.focus();figureReturn=null;setMolecularMode(molecularMode);connect();
}
function closeInspector() {
  showHover(null);returnToAtlas();inspectorDismissed=true;$('inspector').dataset.dismissed='true';$('inspector').hidden=true;scenes.pending();$('plot').focus();
}
function definitions(axes) {
  $('definitions').replaceChildren(...axes.flatMap(axis=>{
    const title=document.createElement('dt'),description=document.createElement('dd');
    title.textContent=axis.label; description.textContent=`${axis.measurement} ${axis.relationship || ''} Measured at ${axis.stage.replaceAll('_',' ')}.`;
    return [title,description];
  }));
}
async function render(next,restore=false) {
  const previousMode=molecularMode, previousStage=state?.stage;
  const mapNeeded=!next.map_index&&plots.needsMap(next.plots[next.presentation.landscape]);
  const traceNeeded=plots.needsTrace(next.plots.inspection);
  const distributionNeeded=!distributionScene.matches(next.plots.distributions);
  const [plot,trace,distribution]=await Promise.all([
    mapNeeded?artifacts.text(next.plots[next.presentation.landscape]):null,
    traceNeeded?artifacts.text(next.plots.inspection):null,
    distributionNeeded?artifacts.text(next.plots.distributions):null,
  ]);
  if(next.figure_layout) validateFigureLayout(next.figure_layout);
  const distributionDrawing=distributionNeeded?svgDocument(distribution):null;
  // Validate all incoming drawings and overlay authority before committing any view.
  if(mapNeeded) svgDocument(plot);
  if(traceNeeded) svgDocument(trace);
  if(next.selected_trace && (next.selected_trace.projection!==next.trace_projection.projection || next.selected_trace.frame!==next.trace_projection.frame)) throw Error('Selected trace does not match the parameter projection.');
  next={...next,landscape_svg:plot,plot_svg:trace};
  const factCommit=facts.prepare(next.preview?.summary.atlas.materialized_realization_id,next.inspection_explanation,next.preview?.summary.atlas.construction_cost);
  const comparisonCommit=comparisonView.prepare(next.preview?.summary.atlas.materialized_realization_id,next);
  if(next.preview) await views.show(next.preview,next.presentation.molecule==='route'?'both':'molecule',()=>setMolecularMode(next.presentation.molecule));
  else views.clear();
  clearHoverDrawing();
  state=next;scenes.pin(state);nearby.clear();pinnedFacts=factCommit;pinnedFacts();
  discovery.update(state);
  pinnedComparison=comparisonCommit;pinnedComparison();
  if(distributionDrawing) distributionScene.update(next.plots.distributions,()=>distributionDrawing);
  mode=state.presentation.landscape;
  for(const id of ['parameters','families','similarity']) $(id).setAttribute('aria-pressed',String(id===mode));
  $('similarity').disabled=!state.has_landscape;
  $('map-scope').textContent=state.has_landscape?'Nearby points compare declared molecular shape, retained sequence and receiving interfaces. Coordinates stay fixed while filtering.':'Structural groups are shown. Capture molecular coordinates with design freeze --include-landscape for similarity navigation.';
  $('family-stage-label').hidden=mode!=='families';
  $('selection-actions').hidden=!state.preview;$('selection-details').hidden=!state.preview;
  $('preview-label').textContent='Preparation';
  setMolecularMode(state.presentation.molecule);
  $('figure-two').hidden=!state.preview;$('inspector').dataset.hasPin=String(Boolean(state.preview));$('inspector').hidden=inspectorDismissed||!state.preview;
  const counts=state.cohort_summary||{products:state.families.products.length,eligible_products:state.families.products.filter(p=>p.eligible_preparations.length).length,product:state.families.product};
  $('counts').textContent=`${state.choices.matching_preparations.toLocaleString()} preparations · ${counts.eligible_products.toLocaleString()} ${counts.product.replaceAll('_',' ')} products`;
  plots.draw(state,mode);colors.update(state,{restore});delete state.landscape_svg;delete state.plot_svg;mapView.attach();raster.attach(mode);selectedTrace.show(state.selected_trace,state.trace_projection);connect(); $('another').disabled=!state.choices.matching_preparations;
  $('back').disabled=!state.can_back;$('retrieve').disabled=!state.selection;$('bookmark').disabled=!state.selection;
  $('clear').hidden=!state.choices.query.parameters.length && !state.choices.query.membership;
  const current=state.preview?.summary, comparison=current?.comparison;
  local.update(state);
  $('render-policy').value=state.render_policy==='current' && state.presentation.route==='assembly'?'assembly':state.render_policy;$('render-policy').disabled=!state.selection;
  $('render-info').textContent=current?.rendering?.notice || (current?.rendering?.effective==='current'?'Current shared glyphs over the same molecular record.':'Artwork retained from this recorded edition.');
  const notices=comparison?.notices || [];
  $('change').textContent=state.preview_status==='excluded_by_query' ? 'The inspected molecule is outside the current filters. Choose an eligible trace to retrieve it.' :
    (state.sample_receipt?.explanation || comparison?.description || (state.selection ? 'One exact preparation drives this molecule, its route and its materials.' : state.explanation.guidance));
  const changes=state.sample_receipt?.coordinate_changes || [];
  $('comparison-detail').textContent=[state.sample_receipt?.explanation,...changes.map(c=>`${c.label}: ${c.before} → ${c.after}${c.unit?' '+c.unit:''}`),...notices.map(n=>typeof n==='string'?n:JSON.stringify(n))].filter(Boolean).join(' ');
  if(state.sample_receipt?.status==='loop_alternative') {
    const loop=changes.find(c=>c.key==='loop_word');
    if(loop) $('change').textContent=`Loop ${loop.before} → ${loop.after}; other hairpin regions held.`;
  } else if(changes.length) {
    $('change').textContent+=' '+changes.slice(0,2).map(c=>`${c.label}: ${c.before} → ${c.after}${c.unit?' '+c.unit:''}`).join(' · ');
  }
  if(notices.length) $('change').textContent+=' Some base correspondence remains unresolved.';
  const cost=current?.atlas.construction_cost;
  $('cost').textContent=cost?`Added DNA ${Object.values(cost.added_nt_by_strand).join(' / ')} nt${Object.keys(cost.added_nt_by_strand).length>1?' per strand':''} · ${cost.distinct_orders} orders`:'';
  $('cost-detail').textContent=cost?`${cost.distinct_orders} distinct oligo orders cover ${cost.material_roles} material roles, totaling ${cost.ordered_nt} ordered nucleotides.`:'';
  const selectedStage=state.stage;
  $('stage').replaceChildren(new Option('All processing steps','all'),...(current?.atlas.states || []).map(s=>new Option(s.state.phase.replaceAll('_',' '),s.state.state_id)));
  $('stage').value=selectedStage;
  if(!restore && previousStage!==selectedStage) viewport.stage(selectedStage);
  else if(restore || previousMode!==state.presentation.molecule) {
    if(state.view_receipt?.camera) viewport.restoreCamera(state.view_receipt.camera);
    else viewport.stage(selectedStage);
  }
  $('download').hidden=!state.handoff;if(state.handoff) {$('download').href=state.handoff.archive;$('download').download='hop-preparation.zip';}
  $('record').hidden=!current;if(current) $('record').href=state.preview.record;
  $('family-stage').value=state.family_stage;
  if(definitionsKey!==state.plots.parameters){definitions(state.choices.axes);definitionsKey=state.plots.parameters;}
  $('recipe').textContent=state.commands+'\n\n'+JSON.stringify(state.sample_receipt || state.selection || state.choices.query,null,2);
  $('coverage').textContent=state.explanation.guidance;
}
function download(name,value) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function changePresentation(change) {
  return act('view',{stage:state.stage,camera:state.selection?(molecularMode==='route'?viewport.camera():state.view_receipt.camera):null,presentation:{...currentPresentation(),...change}});
}
for(const view of ['parameters','families','similarity']) $(view).addEventListener('click',()=>changePresentation({landscape:view}));
$('focus-route').addEventListener('click',()=>focusFigure('figure-two',$('focus-route')));
$('return-map').addEventListener('click',returnToAtlas);
$('close-inspector').addEventListener('click',closeInspector);
$('route-view').addEventListener('click',async()=>{await changePresentation({molecule:'route'});if(state.presentation.molecule==='route'&&!rendering.blocked)focusFigure('figure-two',$('focus-route'));});
$('another').addEventListener('click',()=>act('sample',{strategy:'families'}));
$('back').addEventListener('click',()=>act('back',{},false));
$('retrieve').addEventListener('click',()=>act('retrieve',{selection:state.selection}));
$('clear').addEventListener('click',()=>{const {membership,...query}=state.choices.query;act('query',{query:{...query,parameters:[]}});});
$('family-stage').addEventListener('change',()=>act('family-stage',{stage:$('family-stage').value}));
$('stage').addEventListener('change',()=>act('view',{stage:$('stage').value,camera:null}));
$('bookmark').addEventListener('click',async()=>{
  if(busy || rendering.blocked) return;
  try {await rememberCamera(true);download('hop-view.json',state.view_receipt);
    const fragment=btoa(unescape(encodeURIComponent(JSON.stringify(state.view_receipt))));
    $('view-link').href=`#view=${fragment}`;$('view-link').hidden=false;
  }catch(error){$('status').textContent=error.message;pendingControls();}
});
$('render-policy').addEventListener('change',()=>{const choice=$('render-policy').value;act('view',{stage:state.stage,camera:null,render_policy:choice==='captured'?'captured':'current',presentation:{...state.presentation,route:choice==='assembly'?'assembly':'complete'}});});
$('open-view').addEventListener('click',()=>$('view-file').click());
$('view-file').addEventListener('change',async()=>{try{const file=$('view-file').files[0];if(file) await act('restore',{receipt:JSON.parse(await file.text())},false);}catch(error){$('status').textContent=error.message;}});
async function restoreHash(){if(location.hash.startsWith('#view=')){const receipt=JSON.parse(decodeURIComponent(escape(atob(location.hash.slice(6)))));await act('restore',{receipt},false);}}
window.addEventListener('hashchange',()=>restoreHash().catch(e=>{$('status').textContent=e.message;}));
const observer=new ResizeObserver(()=>{connect();scenes.refresh();});observer.observe($('object'));
window.addEventListener('pagehide',()=>{discovery.close();hover.close();local.close();resizing.close();scenes.close();loading.close();colors.close();nearby.close();raster.close();mapView.close();views.clear();figure.clear();selectedTrace.clear();plots.close();distributionScene.clear();artifacts.clear();rendering.clear();state=null;observer.disconnect();});
window.addEventListener('blur',()=>showHover(null));
document.addEventListener('keydown',e=>{if(e.key==='Escape')escapeInspection($('inspector'),{restorePreview:()=>showHover(null),returnToMap:returnToAtlas,close:closeInspector});});
$('refine').addEventListener('click',()=>{$('refinement').open=!$('refinement').open;});
$('fit-map').addEventListener('click',()=>{showHover(null);plots.clear();});
const opening=loading.opening();
try {const response=await fetch('/api/state',{headers:{'X-HOP-Inspection':'compact-v1'}});if(!response.ok) throw Error('Could not open the recorded choices.');await rendering.show(hydrateCohort(await response.json(),null));opening.ready();await restoreHash();}
catch(error){opening.fail('Could not open the atlas. Reload to retry.');$('status').textContent=error.message;pendingControls();}

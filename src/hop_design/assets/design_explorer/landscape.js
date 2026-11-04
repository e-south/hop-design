import {drawPlot} from './plot.js';
import {toggleValue, rangeQuery} from './model.js';
import {highlightParameters, resolveParameterFocus} from './parameters.js';
import {preparationIndex, linkedMarks} from './linked_focus.js';
import {persistentScene} from './persistent_scene.js';
import {groupedNavigation} from './grouped_navigation.js';
import {indexedMap} from './indexed_map.js';
import {memberChoices} from './member_choices.js';

export function landscape(host, members, onQuery, onSelect, onFocus, onPreview=()=>{}) {
  let state, index, marks, cohortKey=null, mode = 'parameters';
  const note = document.querySelector('#focus');
  const root = host.closest('#landscape');
  const context = document.querySelector('#trace-context');
  const mapScene=persistentScene(host), traceScene=persistentScene(context);
  const indexed=indexedMap(host,ids=>ids?inspect(ids):clear(),ids=>candidates(ids));
  const picker=memberChoices({panel:members,title:document.querySelector('#member-title'),options:document.querySelector('#member-options'),close:document.querySelector('#close-members')},onSelect,id=>id?inspect([id]):clear());
  function highlight(keys, ids=null) {
    const focus = ids === null ? null : index.focus(ids);
    marks?.focus(focus);
    indexed.focus(ids);
    // Point inspection identifies a preparation; only explicit axis/region focus
    // should decorate molecular parameters throughout the route.
    const requested = keys || [];
    const resolved = [...new Set([...requested, ...resolveParameterFocus(state.choices.axes, requested).keys])];
    highlightParameters(document.querySelector('#object'), resolved);
    onFocus(resolved);
    return focus;
  }
  function clear() {
    if (!state) return;
    highlight([], null);
    onPreview(null);
  }
  function inspect(ids, description='') {
    const focused = highlight(null, ids);
    note.textContent = focused.preparations.length===1
      ? (focused.eligible ? 'Previewing one complete preparation. Click to pin.' : 'Recorded preparation outside the current filters. Preview available; selection unchanged.')
      : `${description} ${focused.preparations.length} recorded preparations · ${focused.eligible} eligible.`.trim();
    onPreview(focused.preparations.length===1?focused.preparations[0]:null);
  }
  root.addEventListener('pointerleave', clear);
  root.addEventListener('focusout', e => {if (!root.contains(e.relatedTarget)) clear();});
  function candidates(ids, label) {
    const rows=index.rows(ids);
    const eligible = rows.filter(p => p.matches);
    if(rows.length===1){
      if(eligible.length)return onSelect(eligible[0].materialized_realization_id);
      note.textContent='This preparation is outside the current filters. Clear or revise the filters to select it.';return;
    }
    picker.open(rows,state.selection?index.rows([state.selection.materialized_realization_id])[0]:null,label);
  }
  function focus(axis, description, value) {
    note.textContent = description || `${axis.label}: ${axis.measurement}${axis.relationship ? ' '+axis.relationship : ''}`;
    const ids = value === undefined ? null : state.choices.paths
      .filter(p => p.values[axis.key] === value).map(p => p.materialized_realization_id);
    highlight([axis.key], ids);
  }
  function families(ids) {
    picker.dismiss(false,false);
    const rows = state.families.families.filter(f => ids.includes(f.identity));
    if (rows.length === 1) return onQuery(rows[0].query);
    document.querySelector('#member-title').textContent = 'Choose a structural family';
    const options = document.querySelector('#member-options');
    options.replaceChildren(...rows.map(family => {
      const button = document.createElement('button');
      button.textContent = `Explore ${family.label} · ${family.preparations.length} complete preparations`;
      button.addEventListener('click', () => onQuery(family.query));
      return button;
    }));
    members.hidden = false; options.querySelector('button')?.focus();
  }
  function draw(next, view=mode) {
    picker.dismiss(false,false);state=next;mode=view;members.hidden=true;
    const key=next.plots.inspection;
    if((next.cohort??key)!==cohortKey) {index=preparationIndex(state);cohortKey=next.cohort??key;}
    // The caller commits the selected overlay after these axes are mounted.
    // Clearing transient marks here must not restore a preview into old axes.
    highlight([], null);
    const actions={
      path:rows=>candidates(rows.map(p=>p.materialized_realization_id)),
      hover:rows=>inspect(rows.map(p=>p.materialized_realization_id)),
      value:(key,value)=>onQuery(toggleValue(state.choices.query,key,value)),
      range:(key,a,b)=>onQuery(rangeQuery(state.choices.query,key,a,b)),
      focus,domain:axis=>focus(axis),
    };
    root.classList.toggle('family-context',mode==='families');
    root.classList.toggle('similarity-context',mode==='similarity');
    const traceChanged=traceScene.update(key,()=>{
      drawPlot(context,state.choices,state.plot_svg,actions);
      return null;
    });
    const compact=mode==='similarity'&&next.map_index;
    const mapChanged=mapScene.update(compact?`indexed:${next.map_index.digest}`:next.plots[mode],()=>{
      if(compact){indexed.update(next.map_index,state.choices.paths,state.selection?.materialized_realization_id);return null;}
      indexed.clear();
      if(mode==='parameters') {
        drawPlot(host,state.choices,state.landscape_svg,{...actions,context:text=>{document.querySelector('#coverage').textContent=text;}});
        return null;
      }
      const doc=new DOMParser().parseFromString(state.landscape_svg||state.family_svg,'image/svg+xml');
      if(doc.querySelector('parsererror')) throw Error('Invalid molecular-family drawing.');
      const svg=doc.documentElement;
      for(const target of svg.querySelectorAll('[data-family-ids]')) {
        const ids=JSON.parse(target.dataset.familyIds),filter=()=>families(ids);
        target.addEventListener('click',filter);
        target.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();filter();}});
        for(const event of ['pointerenter','focus']) target.addEventListener(event,()=>{
          const rows=ids.map(id=>index.family(id));
          inspect(rows.flatMap(f=>f.preparations),rows.map(f=>f.label).join('; '));
        });
      }
      for(const group of svg.querySelectorAll('[data-preparations]')) {
        const ids=JSON.parse(group.dataset.preparations),select=()=>candidates(ids);
        group.addEventListener('click',select);
        group.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});
        for(const event of ['pointerenter','focus']) group.addEventListener(event,()=>inspect(ids,group.querySelector('title')?.textContent||''));
      }
      groupedNavigation([svg.querySelectorAll('[data-family-ids]'),svg.querySelectorAll('[data-preparations]')]);
      return svg;
    });
    if(compact)indexed.update(next.map_index,state.choices.paths,state.selection?.materialized_realization_id);
    if(mapChanged||traceChanged) {
      marks?.close();marks=linkedMarks(document.querySelector('#object'),state.families);
    }
    marks.pin(state.selection?.materialized_realization_id);
    return mapChanged;
  }
  return {draw, color:lens=>indexed.color(lens), needsMap:key=>!mapScene.matches(key), needsTrace:key=>!traceScene.matches(key), focusParameters: keys => highlight(keys), clear, close(){picker.close();indexed.close();marks?.close();mapScene.clear();traceScene.clear();index=null;state=null;cohortKey=null;}};
}

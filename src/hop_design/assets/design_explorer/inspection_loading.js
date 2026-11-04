import {panelStatus} from './panel_status.js';

// Inspection feedback is presentation-only. Request ownership stays with the
// hover and committed-render controllers; neither can expose half an update.
export function inspectionLoading(get) {
  const hairpinHost=get('figure-one-canvas');
  const hairpin=panelStatus(hairpinHost,{retainPrevious:()=>Boolean(hairpinHost.querySelector('svg[data-preparation-id]'))});
  const route=panelStatus(get('route-focus'));
  const materials=panelStatus(get('preparation-info'));
  const map=panelStatus(get('landscape-panels'),{retainPrevious:()=>Boolean(get('plot').querySelector('svg,canvas')),previousLabel:'Previous atlas'});
  const comparisonHost=get('map-comparison');
  const comparison=panelStatus(comparisonHost,{retainPrevious:()=>Boolean(comparisonHost.dataset.preparationId)});
  let hover=null,action=[];
  function clearHover() {
    if(!hover) return;
    hover=null;hairpin.clear();comparison.clear();route.clear();materials.clear();
  }
  return {
    pending(identity) {
      if(hover?.identity===identity) return;
      hover={identity,ticket:hairpin.begin('Loading next preparation…',identity),comparison:comparison.begin('Loading…',identity)};
      route.begin('',identity).idle('Pin this preparation to open its route.');
      materials.begin('',identity).idle('Pin this preparation to inspect its materials.');
    },
    ready(identity) {if(hover?.identity===identity) {hover.ticket.ready();hover.comparison.ready();}},
    failed(error,identity) {if(hover?.identity===identity) {hover.ticket.fail('Preview unavailable. Move to another point or leave to restore the pinned preparation.');hover.comparison.fail('Preview unavailable');}},
    clear:clearHover,
    beginAction(kind,payload={}) {
      clearHover();
      const identity=payload.materialized_realization_id||'';
      if(kind==='retrieve') action=[materials.begin('Preparing oligos and route files…',identity)];
      else if(kind==='view' && payload.presentation?.molecule==='route') action=[route.begin('Preparing route…',identity)];
      else action=[hairpin.begin('Loading preparation…',identity),comparison.begin('Loading…',identity),route.begin('Preparing route…',identity),materials.begin('Preparing details…',identity)];
      if(kind==='inspect-discovery')action.push(map.begin('Opening saved preparations…'));
    },
    readyAction(){for(const ticket of action) ticket.ready();action=[];map.clear();},
    failedAction(){for(const ticket of action) ticket.fail('Drawing unavailable. Use Retry drawing to finish this selection.');},
    opening(){return map.begin('Opening atlas…');},
    close(){for(const panel of [hairpin,route,materials,map,comparison]) panel.close();},
  };
}

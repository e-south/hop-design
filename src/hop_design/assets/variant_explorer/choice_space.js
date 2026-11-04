"use strict";
import {$, preparationName} from "./common.js";
import {filterLocalSupport, filterChoices, pathPalette, selectionList, toggleValue, molecularAxisOrder} from "./choice_space_model.js";
import {renderMolecularControls} from "./choice_space_axes.js";
import {renderCoverage} from "./choice_space_coverage.js";
import {locateParameter, prepareParameterKey} from "./parameter_key.js";
import {drawChoiceSpace} from "./choice_space_plot.js";
import {renderPrimerBoundary} from "./primer_boundary.js";
import {connectTeaching} from "./teaching_links.js";

export function choiceSpacePanel({getState, previewLabel, preview, action, update, evaluate}) {
  let filters = {}, queryDigest = null, current = null, order = null, focus = null, renderedWidth = 0;
  document.addEventListener("hop:expose-parameter", event => {
    const key = event.detail;
    if (!getState()?.choices.choice_space.axes.some(a => a.key === key)) return;
    expose(key);
    $("choice-space").open = true;
    const target = $("choice-plot").querySelector(`[data-axis="${key}"]`);
    target?.scrollIntoView({block:"nearest", inline:"nearest"}); target?.focus({preventScroll:true});
  });
  function expose(key) {
    if (["background", "methods"].includes(key)) {
      document.dispatchEvent(new CustomEvent("hop:browse-parameter", {detail:key})); return;
    }
    focus = key; render();
  }
  function clear(key) {delete filters[key]; render(); commit();}
  function render() {
    const state = getState();
    if (!state) return;
    const space = state.choices.choice_space;
    $("choice-detail").textContent = "Hover or focus a value or path for its molecular meaning.";

    if (queryDigest !== state.choices.query_digest) filters = Object.fromEntries((state.choices.query.parameters || []).map(({key, values, minimum, maximum}) => [key, values || {minimum, maximum}]));
    order = molecularAxisOrder(space.axes, focus);
    queryDigest = state.choices.query_digest;
    current = filterChoices(space, filters);
    const product = space.stage === "hairpin" ? "hairpin" : "endpoint product";
    const count = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
    $("choice-count").textContent = `${count(current.products.length, `distinct ${product}`)} · ${count(current.paths.length, "preparation")} shown of ${count(space.paths.length, "evaluated preparation")}.`;
    $("choice-empty").textContent = !current.paths.length
      ? "No matching complete preparation in this evaluated pool. Clear parameter selections or explicitly evaluate this region; this is not global impossibility."
      : "";
    const previewed = previewLabel();
    $("choice-preview-context").textContent = previewed && !current.paths.some(p => p.option_label === previewed)
      ? "The atlas retains the previous preparation for context; it is outside these parameter selections. Choose a remaining path to change the preview."
      : "Paths describe compatible choices, not processing order. Previewing preserves the fixed reference, processing step and camera.";
    const fixed = space.axes.filter(a => !a.varying && a.values.length === 1 && a.values[0].value !== null);
    $("choice-fixed").textContent = "Shared across the evaluated pool: " + fixed.map(a => `${a.label}: ${a.values[0].label}${a.unit ? ` ${a.unit}` : ""} (${a.stage.replaceAll("_", " ")})`).join("; ");
    renderMolecularControls(space, focus, filters, expose, clear);
    renderCoverage(space, filters);
    renderPrimerBoundary(state.primer_boundary_views, space, current.paths.map(p => p.option_label), label => action(() => preview(label)));
    const palette = pathPalette(space), legend = $("choice-color-legend");
    legend.replaceChildren(document.createTextNode(palette.key ? `${palette.label}: ` : ""));
    for (const entry of palette.entries) {
      const item = document.createElement("span"), swatch = document.createElement("i");
      swatch.style.background = entry.color; item.append(swatch, document.createTextNode(entry.label)); legend.append(item);
    }
    renderedWidth = Math.round($("choice-plot").clientWidth);
    $("choice-plot").replaceChildren(drawChoiceSpace({viewportWidth:renderedWidth,space, result: current, filters, preview: previewed, order, onLocate: locateParameter,
      onClear: clear,
      onRange: (key, range, save) => {
        if (range) filters[key] = range; else delete filters[key];
        current = filterChoices(space, filters);
        $("choice-count").textContent = `${current.products.length} products · ${current.paths.length} complete preparations`;
        const allowed = new Set(current.paths.map(p => p.option_label));
        for (const path of $("choice-plot").querySelectorAll(".choice-path")) {
          const matching = path.dataset.options.split(", ").some(id => allowed.has(id));
          path.classList.toggle("excluded", !matching); path.classList.toggle("available", matching);
        }
        const activeLocal = new Set(filterLocalSupport(space.local_support || [], filters).map(p => p.local_realization_id));
        for (const path of $("choice-plot").querySelectorAll(".local-support-path")) {
          const matching = JSON.parse(path.dataset.localIds).some(id => activeLocal.has(id));
          path.classList.toggle("excluded", !matching); path.classList.toggle("available", matching);
        }
        for (const value of $("choice-plot").querySelectorAll(".choice-value")) {
          const count = current.availability[value.dataset.axis][value.dataset.value] || 0;
          value.classList.toggle("unavailable", !count);
          value.dataset.count = count;
        }
        if (save) {render(); commit(key);}
      },
      onFilter: (key, value) => {
        filters = toggleValue(filters, key, value); render(); commit();
        const target = [...$("choice-plot").querySelectorAll(".choice-value")].find(
          el => el.dataset.axis === key && el.dataset.value === String(value),
        );
        target?.focus({preventScroll: true});
      },
      onPath: paths => {
        if (paths.length === 1) action(() => preview(paths[0].option_label));
        else {
          $("choice-detail").textContent = `${paths.length} preparations share these coordinates. Choose an exact preparation below; no arbitrary route was previewed.`;
          listPaths(paths); $("choice-preparation").focus();
        }
      },
      onDetail: text => {$("choice-detail").textContent = text;},
    }));
    listPaths(current.paths);
    connectTeaching($("parameter-key"), $("choice-plot"));
    $("clear-choice-filters").hidden = !Object.keys(filters).length;
  }
  function listPaths(paths) {
    const state = getState(), select = $("choice-preparation");
    select.replaceChildren(new Option("Choose a complete preparation", ""));
    const products = new Map();
    for (const path of paths) {
      if (!products.has(path.molecule_id)) products.set(path.molecule_id, []);
      products.get(path.molecule_id).push(path);
    }
    for (const [identity, members] of products) {
      const group = document.createElement("optgroup");
      const first = members[0], option = state.pool.options.find(o => o.label === first.option_label);
      group.label = `Loop ${option.loop_sequence} · ${members.length} preparation(s) for this exact ${state.choices.query.stage} product`;
      group.dataset.productId = identity;
      for (const path of members) group.append(new Option(preparationName(state, path.option_label), path.option_label));
      select.append(group);
    }
    select.value = paths.some(p => p.option_label === previewLabel()) ? previewLabel() : "";
  }
  async function commit(brushKey = null) {
    const q = {...getState().choices.query, schema: "hop.scaffold-variant-query/v2", parameters: selectionList(filters)};
    await action(() => update(q));
    if (brushKey) $("choice-plot").querySelector(`[data-brush-key="${brushKey}"]`)?.focus({preventScroll: true});
  }
  $("clear-choice-filters").onclick = () => {filters = {}; render(); commit();};
  $("evaluate-parameters").onclick = () => action(() => evaluate({query_digest: getState().choices.query_digest, max_branches: Number($("evaluation-branches").value), max_continuations_per_branch: Number($("evaluation-continuations").value)}));
  $("choice-preparation").onchange = () => {
    const label = $("choice-preparation").value;
    if (label) action(() => preview(label));
  };
  $("choice-to-comparison").onclick = () => {
    $("required-comparison").open = true;
    $("required-comparison").scrollIntoView({block: "start", behavior: "auto"});
    $("required-loops").querySelector("button")?.focus();
  };
  function refresh(busy) {
    $("choice-space").inert = busy;
    $("choice-preparation").disabled = busy || !current?.paths.length;
    $("evaluate-parameters").disabled = busy || !Object.keys(filters).length;
  }
  let resizeFrame = null;
  new ResizeObserver(entries => {
    const width = Math.round(entries[0].contentRect.width);
    if (width>0 && Math.abs(width-renderedWidth)>1 && current) {
      cancelAnimationFrame(resizeFrame); resizeFrame=requestAnimationFrame(render);
    }
  }).observe($("choice-plot"));
  return {render, refresh, prepareTeaching: (preview, axes) => prepareParameterKey(axes, expose, preview)};
}

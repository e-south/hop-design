"use strict";
// Parameter selections intersect recorded paths and serialize to the same public query.
export function toggleValue(filters, key, value) {
  const next = {...filters}, values = Array.isArray(next[key]) ? [...next[key]] : [];
  const index = values.indexOf(value);
  if (index < 0) values.push(value); else values.splice(index, 1);
  if (values.length) next[key] = values; else delete next[key];
  return next;
}

export function setRange(filters, key, first, last) {
  const a = Math.round(first), b = Math.round(last);
  if (!Number.isFinite(a) || !Number.isFinite(b)) throw new Error("A brush needs integer boundaries.");
  return {...filters, [key]: {minimum: Math.min(a, b), maximum: Math.max(a, b)}};
}

export function selectionList(filters) {
  return Object.entries(filters).sort(([a], [b]) => a.localeCompare(b)).map(([key, value]) =>
    Array.isArray(value) ? {key, values: [...value]} : {key, ...value});
}

export function acceptsSelection(selection, value) {
  return Array.isArray(selection) ? selection.includes(value) :
    Number.isInteger(value) && value >= selection.minimum && value <= selection.maximum;
}

export function filterChoices(space, filters) {
  for (const [key, values] of Object.entries(filters)) {
    const axis = space.axes.find(a => a.key === key);
    if (!Array.isArray(values)) {
      if (!axis || axis.kind !== "numeric" || !Number.isInteger(values.minimum) ||
          !Number.isInteger(values.maximum) || values.minimum > values.maximum)
        throw new Error("A range selection needs a numeric axis and ordered integer boundaries.");
    } else if (!axis || !values.length || values.some(v => !axis.values.some(e => e.value === v)))
      throw new Error("Unknown choice coordinate; clear the view filters explicitly.");
  }
  const matches = (path, omit) => path.eligible_under_preserved_controls !== false && Object.entries(filters).every(
    ([key, values]) => key === omit || acceptsSelection(values, path.values[key]),
  );
  const paths = space.paths.filter(p => matches(p));
  const products = new Map();
  for (const path of paths) {
    if (!products.has(path.molecule_id)) products.set(path.molecule_id, []);
    products.get(path.molecule_id).push(path.option_label);
  }
  const availability = {};
  for (const axis of space.axes) {
    availability[axis.key] = Object.fromEntries(axis.values.map(v => [v.value, 0]));
    for (const path of space.paths)
      if (matches(path, axis.key)) availability[axis.key][path.values[axis.key]]++;
  }
  return {paths, products: [...products].map(([molecule_id, option_labels]) => ({molecule_id, option_labels})), availability};
}

export function axisPositions(axis, top, bottom) {
  const values = axis.values.map(v => v.value), known = values.filter(v => v !== null);
  const end = values.includes(null) && known.length ? bottom - (bottom - top) * .2 : bottom;
  const min = Math.min(...known), max = Math.max(...known);
  return new Map(values.map((value, index) => [value,
    value === null ? bottom : axis.kind === "numeric" && min !== max
      ? end - (value - min) / (max - min) * (end - top)
      : axis.kind === "numeric" || values.length === 1 ? (top + end) / 2
        : top + index / (values.length - 1) * (bottom - top),
  ]));
}

export function backgroundLabel(entry, entries) {
  if (!entry.detail) return entry.label;
  const known = entries.filter(e => e.detail);
  if (known.length === 1) return "Shared assessed surroundings";
  const names = {closing: "Loop side", assembly: "Open side", stem: "Supplied stem", interfaces: "Interfaces"};
  const parts = [];
  for (const [key, name] of Object.entries(names)) {
    const words = [...new Set((entry.detail[key]?.sequences || []).map(s => s.sequence))];
    const different = words.filter(word => !known.every(e => e.detail[key]?.sequences.some(s => s.sequence === word)));
    if (different.length) parts.push(`${name}: ${different.join(" / ")}`);
  }
  return parts.join("; ") || "Shared sequence words; inspect pairing, order and termini";
}

export function pathsNearPoint(paths, [x, y], tolerance) {
  return paths.filter(path => path.points.some(([ax, ay], index) => {
    if (!index) return false;
    const [bx, by] = path.points[index - 1], dx = bx - ax, dy = by - ay;
    const length = dx * dx + dy * dy;
    const t = length ? Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / length)) : 0;
    return Math.hypot(x - ax - t * dx, y - ay - t * dy) <= tolerance;
  }));
}

function intersects(domain, selection) {
  if (!domain || (!domain.values && domain.minimum === undefined && !domain.intervals)) return true;
  if (domain.values) return domain.values.some(v => acceptsSelection(selection, v));
  const intervals = domain.intervals || [domain];
  return intervals.some(({minimum, maximum}) => Array.isArray(selection)
    ? selection.some(v => Number.isInteger(v) && v >= minimum && v <= maximum)
    : selection.minimum <= maximum && selection.maximum >= minimum);
}
export function branchCoverage(branches, filters) {
  return branches.filter(branch => Object.entries(filters).every(([key, selection]) =>
    intersects(branch.domains[key], selection)));
}

export function localRejections(branch) {
  if (branch.status !== "evaluated") return [];
  return Object.entries(branch.local_coverage || {}).flatMap(([region, coverage]) =>
    coverage.completion === "complete" && coverage.feasibility === "infeasible" && coverage.termination_reason === "exhausted_domain"
      ? [{region, reasons: Object.keys(coverage.rejection_counts || {})}]
      : []);
}

export function filterLocalSupport(paths, filters) {
  // Missing coordinates remain unknown. A local witness cannot assess downstream controls.
  return paths.filter(path => Object.entries(filters).every(([key, selection]) =>
    !(key in path.values) || acceptsSelection(selection, path.values[key])));
}

export function localCoordinateRuns(axes, values) {
  const runs = []; let run = [];
  axes.forEach((axis, i) => {
    if (Object.hasOwn(values, axis.key)) run.push(i);
    else if (run.length) {runs.push(run); run = [];}
  });
  if (run.length) runs.push(run);
  return runs;
}

export function pathPalette(space) {
  // Color a named categorical coordinate, never score or inferred feasibility.
  const colors = ["#26758B", "#C17036", "#7466A1", "#498765", "#AD6075", "#8D8240"];
  for (const key of ["basal_method", "release_method", "foldback_method", "loop_word"]) {
    const axis = space.axes.find(a => a.key === key);
    const values = (axis?.values || []).filter(v => v.value !== null);
    if (values.length > 1 && values.length <= colors.length)
      return {key, label:axis.label, entries: values.map((v,i) => ({...v, color:colors[i]}))};
  }
  return {key:null, label:"Complete preparations", entries:[]};
}

// Presentation only: coordinates and path membership are never thinned.
export function compactPlotLayout(axisCount, availableWidth, categoricalCount = 0) {
  const width = Math.max(320, Math.round(availableWidth || 1200));
  const needed = width >= 1100 ? 82 + (categoricalCount-1)*12 : 0;
  const height = Math.round(Math.min(368, Math.max(240, width / 3.4, needed)));
  const margin = Math.min(84, Math.max(40, width / (axisCount+1) * .7));
  const step = axisCount>1 ? (width-2*margin)/(axisCount-1) : width/2;
  const xs = Array.from({length:axisCount}, (_,i) => axisCount===1 ? width/2 : margin+i*step);
  return {width,height,top:50,bottom:height-32,xs,
    labelWidth:Math.max(8,Math.min(step-18,2*margin-12))};
}

// Stable molecular context; a selected feature replaces detail, never permissions.
export function molecularAxisOrder(axes, focus = null) {
  const known = new Map(axes.map(a => [a.key,a]));
  const overview = ['loop_word','foldback_arm_bp','join_offset_nt','self_paired_arm_bp',
    'basal_method','basal_nick_offset_nt','left_gap','right_gap','source_reverse_primer_available_nt'];
  if (!focus || !known.has(focus)) return overview.filter(k=>known.has(k));
  const axis=known.get(focus), contact=focus.match(/^basal_(?:source_base|adapter_base|pair_class)_(\d+)$/);
  const details=contact ? ['source_base','adapter_base','pair_class'].map(k=>`basal_${k}_${contact[1]}`)
    : [focus,...(axis.dependencies||[]),...(axis.equivalent_measurements||[])];
  const required=[...new Set(details)].filter(k=>known.has(k));
  const context=['loop_word','basal_method','left_gap','right_gap'];
  const ordered=[...new Set([...context.slice(0,2),...required,...context.slice(2)])].filter(k=>known.has(k));
  // Registry relationships are bounded; do not silently omit a new dependency.
  if (ordered.length>9) return required;
  return ordered;
}

export function molecularLabelLines(text, width) {
  // Literal words wrap without ellipses or invented sequence identifiers.
  const result=[];
  for (let word of String(text).split(/\s+/)) {
    if (result.length && result.at(-1).length+word.length+1<=width) result[result.length-1]+=' '+word;
    else {
      while(word.length>width){result.push(word.slice(0,width));word=word.slice(width);}
      if(word)result.push(word);
    }
  }
  return result;
}
export function tickLabelValues(entries, positions, priority = {}, minimumGap = 12) {
  const ranked = entries.map((entry, index) => ({value:entry.value, index,
    weight:(priority[entry.value] || 0) + (index===0 || index===entries.length-1 ? .5 : 0)}))
    .sort((a,b) => b.weight-a.weight || a.index-b.index);
  const accepted = [];
  for (const entry of ranked) if (accepted.every(value =>
    Math.abs(positions.get(value)-positions.get(entry.value)) >= minimumGap)) accepted.push(entry.value);
  return new Set(accepted);
}

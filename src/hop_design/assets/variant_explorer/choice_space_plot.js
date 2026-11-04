"use strict";
import {acceptsSelection, axisPositions, backgroundLabel, pathPalette, pathsNearPoint, compactPlotLayout, tickLabelValues, molecularLabelLines} from "./choice_space_model.js";
import {groupedNavigation} from "./grouped_navigation.js";
import {drawLocalSupport} from "./choice_space_local.js";
import {attachNumericBrush} from "./choice_space_brush.js";
const ns = "http://www.w3.org/2000/svg";
function svgNode(tag, attributes = {}, text = null) {
  const el = document.createElementNS(ns, tag);
  for (const [key, value] of Object.entries(attributes)) el.setAttribute(key, value);
  if (text !== null) el.textContent = text;
  return el;
}
const stageName = stage => ({hairpin: "hairpin", endpoint: "requested endpoint", released_insert: "released insert", preparation: "preparation"})[stage] || stage.replaceAll("_", " ");
function activate(el, action) {
  el.onclick = action;
  el.onkeydown = event => {
    if (["Enter", " "].includes(event.key)) { event.preventDefault(); action(); }
  };
}
export function drawChoiceSpace({space, result, filters, preview, order, viewportWidth, onFilter, onRange, onClear, onLocate, onPath, onDetail}) {
  const axes = order.map(key => space.axes.find(a => a.key === key)).filter(Boolean);
  const {width, height, top, bottom, xs, labelWidth} = compactPlotLayout(axes.length, viewportWidth, Math.max(0,...axes.filter(a=>a.kind!=="numeric").map(a=>a.values.length)));
  const chart = svgNode("svg", {viewBox: `0 0 ${width} ${height}`, role: "group", "aria-label": "Complete preparation paths", class: "choice-plot"});
  chart.append(svgNode("title", {}, "Select coordinate values to filter complete preparations. Select a whole path to preview it. All coordinates remain; crowded labels are available on focus or in Browse domain."));
  const positions = axes.map(a => axisPositions(a, top, bottom));
  drawLocalSupport(chart, space, filters, axes, xs, positions, onDetail);
  const projected = result.paths.map(p => ({...p,
    points: axes.map((a, i) => [xs[i], positions[i].get(p.values[a.key])]),
  }));
  const palette = pathPalette(space);
  const color = path => palette.entries.find(e => e.value === path.values[palette.key])?.color || "#536C78";
  const groups = new Map();
  for (const path of space.paths) {
    const points = axes.map((a, i) => `${xs[i]},${positions[i].get(path.values[a.key])}`).join(" ");
    const key = points + "|" + color(path);
    if (!groups.has(key)) groups.set(key, {points, members:[]});
    groups.get(key).members.push(path);
  }
  const eligible = new Set(result.paths.map(p => p.option_label));
  for (const {points, members} of groups.values()) {
    const available = members.filter(p => eligible.has(p.option_label));
    const selected = available.some(p => p.option_label === preview);
    const label = members.map(p => p.option_label).join(", ");
    const group = svgNode("g", {class: `choice-path ${available.length ? "available" : "excluded"} ${selected ? "previewed" : ""}`, "data-options": label});
    group.style.setProperty("--path-color", color(members[0]));
    group.style.setProperty("--path-opacity", Math.max(.12, Math.min(.48, 2.2 / Math.sqrt(space.paths.length))));
    group.append(svgNode("polyline", {points, class: "choice-line"}));
    if (available.length) {
      const description = axes.map(a => a.values.find(v => v.value === available[0].values[a.key])?.label || "Unassessed").join("; ");
      const hit = svgNode("polyline", {points, class: "choice-hit", tabindex: "0", role: "button", "aria-label": `Preview ${description}. ${available.length} preparation(s).`});
      hit.append(svgNode("title", {}, description));
      activate(hit, event => {
        if (event?.type === "click" && event.detail) {
          const matrix = chart.getScreenCTM();
          const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
          const picked = pathsNearPoint(projected, [point.x, point.y], 7 / matrix.a);
          if (picked.length) onPath(picked);
        } else onPath(available);
      });
      hit.onfocus = hit.onpointerenter = () => onDetail(`${description} · ${available.length} complete preparation(s). Select this path to preview.`);
      group.append(hit);
    }
    chart.append(group);
  }
  const keyboardGroups = [];
  axes.forEach((axis, index) => {
    const preceding = new Set(chart.children);
    const x = xs[index];
    chart.append(svgNode("line", {x1: x, x2: x, y1: top - 15, y2: bottom + 15, class: "choice-axis"}));
    const headingWidth = Math.min(index ? xs[index]-xs[index-1]-12 : 2*x-6, index<axes.length-1 ? xs[index+1]-x-12 : 2*(width-x)-6);
    const headingChars = Math.max(5, Math.floor(headingWidth/6.4));
    const heading = svgNode("text", {x, y: 16, "text-anchor": "middle", class: "choice-heading", tabindex: 0, "data-axis-title": axis.key});
    const headingText = `${axis.symbol ? axis.symbol + " · " : ""}${axis.label}`;
    const headingLines = molecularLabelLines(headingText, headingChars);
    headingLines.forEach((line,n)=>heading.append(svgNode("tspan",{x,dy:n?Math.min(12,25/Math.max(1,headingLines.length-1)):0},line)));
    if (headingLines.length>2) heading.setAttribute("y",8);
    heading.append(svgNode("title",{},headingText));
    heading.onpointerenter = heading.onfocus = () => {onLocate(axis); onDetail(`${axis.measurement} ${axis.relationship || ""}`);};
    heading.onpointerleave = heading.onblur = () => onLocate(null);
    chart.append(heading);
    const stage = `${stageName(axis.stage)}${axis.unit ? ` · ${axis.unit}` : ""}`;
    const stageLabel = svgNode("text", {x, y: 39, "text-anchor": "middle", class: "choice-stage"}, ({released_insert:"insert",source_duplex:"source",source_adapter_association:"association",preparation:"methods"}[axis.stage] || stageName(axis.stage)) + (axis.unit ? ` · ${axis.unit}` : ""));
    stageLabel.append(svgNode("title",{},stage)); chart.append(stageLabel);
    if (filters[axis.key]) {
      const clear = svgNode("text", {x:x+44, y:bottom+27, "text-anchor": "middle", tabindex: 0, role: "button", class: "choice-clear", "aria-label":`Clear ${axis.label} selection`}, "×");
      activate(clear, () => onClear(axis.key)); chart.append(clear);
    }
    const priority = Object.fromEntries(axis.values.map(entry => [entry.value,
      filters[axis.key] && acceptsSelection(filters[axis.key],entry.value) ? 4 : result.availability[axis.key][entry.value] ? 2 : 0]));
    const limit = Math.max(4,Math.floor((labelWidth-12)/6.4));
    const labelRows = Math.max(1,...axis.values.map(e=>molecularLabelLines(e.label,limit).length));
    const labels = tickLabelValues(axis.values,positions[index],priority,labelRows*12);
    axis.values.forEach(entry => {
      const y = positions[index].get(entry.value), active = filters[axis.key] ? acceptsSelection(filters[axis.key], entry.value) : false;
      const count = result.availability[axis.key][entry.value] || 0;
      const text = axis.key === "background" ? backgroundLabel(entry, axis.values) : entry.label;
      const label = molecularLabelLines(text,limit);
      const labeled = labels.has(entry.value);
      const g = svgNode("g", {class: `choice-value ${count ? "" : "unavailable"}`, tabindex: "0", role: "button", "aria-pressed": String(active), "aria-label": `${axis.label}: ${text}; ${count} preparations with other filters held`, "data-axis": axis.key, "data-value": entry.value, "data-count": count});
      g.append(svgNode("title", {}, `${entry.label}\n${count} complete preparations with other axes held. Full regional pairing and chemistry remain in the exact record.`));
      const nodeWidth = labeled ? Math.min(labelWidth,Math.max(...label.map(t=>t.length))*6.4+12) : 4;
      g.append(svgNode("rect", {x:x-nodeWidth/2,y:y-(labeled?label.length*6:2),width:nodeWidth,height:labeled?label.length*12:4,rx:labeled?3:2}));
      const letters=svgNode("text",{x,y:y+3.5-(label.length-1)*6,"text-anchor":"middle",class:labeled?"":"focus-label"});
      label.forEach((line,n)=>letters.append(svgNode("tspan",{x,dy:n?12:0},line)));
      g.append(letters);
      if(!labeled)g.classList.add("tick-only");
      if (entry.value !== null) activate(g, () => onFilter(axis.key, entry.value));
      else {g.removeAttribute("role"); g.removeAttribute("aria-pressed");}
      g.onfocus = g.onpointerenter = () => {onLocate(axis); onDetail(`${axis.label} (${stageName(axis.stage)}): ${text}. ${g.dataset.count} preparation(s) with the other filters held. ${axis.measurement}`);};
      g.onblur = g.onpointerleave = () => onLocate(null);
      chart.append(g);
    });
    if (axis.kind === "numeric") attachNumericBrush({chart, axis, x, top, bottom, positions: positions[index], selection: filters[axis.key], onRange: (range, commit) => onRange(axis.key, range, commit), onClear: () => onClear(axis.key), onDetail});
    const description = axis.declared?.values ? `${axis.declared.values.length} values` : axis.declared?.minimum !== undefined || axis.declared?.intervals ? "Integer range" : axis.declared?.alphabet ? "Word domain" : "Observed";
    chart.append(svgNode("text", {x, y: bottom + 14, "text-anchor": "middle", class: "choice-stage"}, description));
    const browse = svgNode("text", {x,y:bottom+27,"text-anchor":"middle",tabindex:0,role:"button",class:"choice-domain","aria-label":`Browse the ${axis.label} domain`},"Browse…");
    activate(browse, () => document.dispatchEvent(new CustomEvent("hop:browse-parameter",{detail:axis.key})));
    chart.append(browse);
    keyboardGroups.push([...chart.children].filter(el => !preceding.has(el) && el.hasAttribute("tabindex"))
      .sort((a, b) => Number(a.getAttribute("role") === "slider") - Number(b.getAttribute("role") === "slider")));

  });
  groupedNavigation(keyboardGroups);
  groupedNavigation([chart.querySelectorAll(".choice-hit"), chart.querySelectorAll(".local-support-path")]);
  return chart;
}

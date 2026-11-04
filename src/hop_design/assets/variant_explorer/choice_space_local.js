"use strict";
import {filterLocalSupport, localCoordinateRuns} from "./choice_space_model.js";
const ns = "http://www.w3.org/2000/svg";
export function drawLocalSupport(chart, space, filters, axes, xs, positions, onDetail) {
  const active = new Set(filterLocalSupport(space.local_support || [], filters).map(p => p.local_realization_id));
  const groups = new Map();
  for (const local of space.local_support || []) {
    for (const run of localCoordinateRuns(axes, local.values)) {
      if (run.length < 2) continue;
      const points = run.map(i => [xs[i], positions[i].get(local.values[axes[i].key])]);
      const key = points.map(p => p.join(",")).join(" ");
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(local);
    }
  }
  for (const [points, members] of groups) {
    const line = document.createElementNS(ns,"polyline");
    line.dataset.localIds = JSON.stringify(members.map(p => p.local_realization_id));
    line.setAttribute("points", points); line.setAttribute("tabindex", "0");
    const count = members.filter(p => active.has(p.local_realization_id)).length;
    line.setAttribute("class", `local-support-path ${count ? "available" : "excluded"}`);
    const detail = `${count}/${members.length} locally supported ${members[0].scope.replace("_local_only", "")} realization(s). Only shown coordinates are established; gaps, other neighborhoods, preservation controls and completion remain unassessed by this record.`;
    line.setAttribute("aria-label", detail);
    const title = document.createElementNS(ns,"title");title.textContent = detail;line.append(title);
    line.onpointerenter = line.onfocus = () => onDetail(detail);
    chart.append(line);
  }
}

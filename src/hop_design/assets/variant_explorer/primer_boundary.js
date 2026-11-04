"use strict";
import {$, node} from "./common.js";

let selected = null;
export function renderPrimerBoundary(views, space, compatible, preview) {
  const host = $("primer-boundary"); host.replaceChildren();
  if (!views?.length) return;
  const key = v => `${v.primer}/${v.required_nt}/${v.available_nt}`;
  const view = views.find(v => key(v) === selected) || views[0]; selected = key(view);
  host.append(node("p", `Examined primer boundary · ${view.available_nt} nt available; ${view.required_nt} nt required. ${view.examined_continuations} recorded continuation(s) at this bound.`));
  const controls = node("div", ""); controls.className = "boundary-choices";
  for (const v of views) {
    const button = node("button", `${v.primer} ${v.available_nt}/${v.required_nt} nt`);
    button.className = "quiet"; button.setAttribute("aria-pressed", String(key(v) === selected));
    button.onclick = () => {selected = key(v); renderPrimerBoundary(views, space, compatible, preview);};
    controls.append(button);
  }
  if (views.length > 1) host.append(controls);
  const drawing = new DOMParser().parseFromString(view.svg, "image/svg+xml").documentElement;
  host.append(document.importNode(drawing, true));
  const labels = view.representative.complete_alternative_labels.filter(label => compatible.includes(label));
  const alternatives = node("div", ""); alternatives.className = "boundary-choices";
  const byLabel = new Map(space.paths.map(p => [p.option_label, p]));
  for (const label of labels) {
    const p = byLabel.get(label), word = p?.values.loop_word;
    const available = p?.values[`source_${view.primer}_primer_available_nt`];
    const button = node("button", `Inspect ${word || "complete option"} · ${available} nt available`);
    button.className = "quiet"; button.onclick = () => preview(label); alternatives.append(button);
  }
  host.append(node("p", labels.length
    ? "Complete alternatives in the same declared branch are available below. Each has its own sequence and preparation."
    : "No complete alternative in this branch satisfies the current selections. This is an examined continuation, not a global impossibility."), alternatives);
}

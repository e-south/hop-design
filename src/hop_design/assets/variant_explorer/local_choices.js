"use strict";
import { $, node, neighborhoods, variantName } from "./common.js";
import { supportedVariants } from "./local_choice_model.js";
import { realizationName } from "./inspection_labels.js";

export function showLocalChoices(choices, anchor, choose, inspect = null, backgrounds = null, previewLabel = null, parameterKeys = []) {
  const viewport = $("viewport");
  viewport.querySelector(".local-choices")?.remove();
  const panel = node("div", "");
  panel.className = "local-choices";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", `${neighborhoods[choices.query.focus]} supported choices`);
  const title = node("strong", neighborhoods[choices.query.focus]);
  const close = node("button", "×");
  close.setAttribute("aria-label", "Close local choices");
  close.onclick = () => panel.remove();
  const heading = node("div", "");
  heading.append(title, close);
  panel.append(heading, node("p", `Supported complete preparations · assessed at ${choices.query.stage}`));
  for (const v of supportedVariants(choices)) {
    const button = node("button", variantName(v));
    button.title = `${v.option_labels.length} complete preparation${v.option_labels.length === 1 ? "" : "s"}`;
    button.setAttribute("aria-pressed", String(v.option_labels.includes(previewLabel)));
    button.onclick = () => choose(v.variant_id);
    panel.append(button);
  }
  if (backgrounds?.candidates.length > 1) {
    panel.append(node("p", "Choose the complete molecular background for this variant:"));
    for (const candidate of backgrounds.candidates) {
      const button = node("button", realizationName(candidate, backgrounds.candidates, choices.query.focus));
      button.title = candidate.label;
      button.onclick = () => backgrounds.choose(candidate.label);
      panel.append(button);
    }
  }
  for (const key of parameterKeys.filter(k => k.startsWith("basal_"))) {
    const axis = choices.choice_space.axes.find(a => a.key === key);
    if (!axis) continue;
    const button = node("button", `Explore ${axis.label}`);
    button.onclick = () => {panel.remove(); document.dispatchEvent(new CustomEvent("hop:expose-parameter", {detail: key}));};
    panel.append(button);
  }
  if (inspect) {
    const button = node("button", "Follow this base through processing");
    button.onclick = () => { panel.remove(); inspect(); };
    panel.append(button);
  }
  panel.addEventListener("keydown", e => { if (e.key === "Escape") { e.stopPropagation(); panel.remove(); } });
  viewport.append(panel);
  const rect = viewport.getBoundingClientRect();
  panel.style.left = Math.max(8, Math.min(rect.width - panel.offsetWidth - 8, anchor.x - rect.left + 8)) + "px";
  panel.style.top = Math.max(8, Math.min(rect.height - panel.offsetHeight - 8, anchor.y - rect.top + 8)) + "px";
  close.focus({preventScroll:true});
}

export function attachLocalExploration(drawing, onNeighborhood, onPick) {
  const bases = [...drawing.querySelectorAll("[data-base-index]")];
  const regionFor = new Map(bases.map(b => [JSON.stringify([
    b.dataset.stateId, b.dataset.strandId, +b.dataset.baseIndex,
  ]), b.dataset.neighborhood]));
  const sites = [...drawing.querySelectorAll("[data-site-id]")];
  for (const site of sites) {
    site.dataset.neighborhoods = JSON.stringify([...new Set(
      [...site.querySelectorAll("[data-members]")].flatMap(r => JSON.parse(r.dataset.members))
        .map(a => regionFor.get(JSON.stringify(a))).filter(Boolean)
    )]);
    site.setAttribute("tabindex", "0");
    site.setAttribute("aria-label", site.textContent.trim());
  }
  function highlight(region, siteId = null) {
    for (const b of drawing.querySelectorAll("[data-base-index],[data-region-fill]"))
      b.classList.toggle("region-highlight", !!region && (b.dataset.neighborhood || b.dataset.regionFill) === region);
    for (const site of sites) site.classList.toggle("site-highlight", siteId === site.dataset.siteId ||
      (!!region && JSON.parse(site.dataset.neighborhoods).includes(region)));
    const active = new Set(sites.filter(s => s.classList.contains("site-highlight")).map(s => s.dataset.siteId));
    for (const label of drawing.querySelectorAll("[data-site-labels]"))
      label.classList.toggle("site-highlight", JSON.parse(label.dataset.siteLabels).some(id => active.has(id)));
    for (const cut of drawing.querySelectorAll("[data-operation-id]"))
      cut.classList.toggle("site-highlight", active.has(cut.dataset.operationId));
  }
  for (const element of drawing.querySelectorAll("[data-base-index],[data-region-fill],[data-site-id]")) {
    const region = element.dataset.neighborhood || element.dataset.regionFill;
    element.addEventListener("pointerenter", () => highlight(region, element.dataset.siteId));
    element.addEventListener("focus", () => highlight(region, element.dataset.siteId));
    element.addEventListener("pointerleave", () => highlight(null));
    element.addEventListener("blur", () => highlight(null));
    if (!region) continue;
    const choose = event => {
      if (drawing.getAttribute("aria-disabled") === "true") return;
      const box = element.getBoundingClientRect();
      const picked = element.dataset.baseIndex === undefined ? null : {
        address: {state_id: element.dataset.stateId, strand_id: element.dataset.strandId,
                  index: +element.dataset.baseIndex}, neighborhood: region,
        parameterKeys: JSON.parse(element.dataset.parameterKeys || "[]"),
      };
      onNeighborhood(region, {x: event.clientX || box.x + box.width / 2,
                              y: event.clientY || box.y + box.height / 2}, picked);
    };
    element.addEventListener("click", choose);
    element.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(e); }
      if (e.key === "i" && element.dataset.baseIndex !== undefined) onPick({address: {
        state_id: element.dataset.stateId, strand_id: element.dataset.strandId, index: +element.dataset.baseIndex,
      }});
    });
  }
}

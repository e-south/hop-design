"use strict";
// Molecular facts and glyph geometry arrive from the shared static export.
import {$, node} from "./common.js";
import { teachingNavigation } from "./grouped_navigation.js";
import { connectTeaching } from "./teaching_links.js";
const drawings = new Map();

export function locateParameter(axis) {
  const selected = Array.isArray(axis) ? axis : axis ? [axis] : [];
  const keys = new Set(selected.flatMap(a => [a.key, ...(a.dependencies || []), ...(a.equivalent_measurements || [])]));
  for (const el of $("viewport").querySelectorAll("[data-parameter-keys]")) {
    el.classList.toggle("parameter-highlight", JSON.parse(el.dataset.parameterKeys).some(k => keys.has(k)));
  }
  for (const el of $("parameter-key").querySelectorAll("[data-teaching-keys]")) {
    el.classList.toggle("parameter-highlight", JSON.parse(el.dataset.teachingKeys).some(k => keys.has(k)));
  }
  const detail = $("parameter-definition");
  if (detail) detail.textContent = selected.length
    ? selected.map(a => `${a.symbol ? a.symbol + " · " : ""}${a.label} (${a.stage.replaceAll("_", " ")}${a.unit ? ", " + a.unit : ""}): ${a.measurement} ${a.relationship || ""}`).join(" ")
    : "Hover or focus a bracket for its meaning; select it to expose its coordinates.";
}

export async function prepareParameterKey(axes, expose, preview) {
  const host = $("parameter-key");
  if (!preview?.teaching_drawing || !preview.teaching) {
    return () => host.replaceChildren(node("p", "Preview a complete preparation to see its molecular parameter key."));
  }
    if (!drawings.has(preview.teaching_drawing)) {
      const response = await fetch(preview.teaching_drawing);
      if (!response.ok) throw new Error(`Teaching drawing unavailable (${response.status}).`);
      drawings.set(preview.teaching_drawing, await response.text());
      while (drawings.size > 2) drawings.delete(drawings.keys().next().value);
    }
    const parsed = new DOMParser().parseFromString(drawings.get(preview.teaching_drawing), "image/svg+xml");
    if (parsed.querySelector("parsererror")) throw new Error("Teaching drawing is not valid SVG.");
    if (parsed.documentElement.dataset.preparationId !== preview.teaching.materialized_realization_id)
      throw new Error("Teaching drawing does not match the selected preparation.");
    const drawing = document.importNode(parsed.documentElement, true);
    return () => {
    drawing.classList.add("parameter-key");
    const detail = node("p", ""); detail.id = "parameter-definition"; detail.className = "hint";
    const choices = node("div", ""); choices.className = "parameter-features";
    const parameters = new Map(preview.teaching.parameters.map(p => [p.key, p]));
    const configuration = document.querySelector("#choice-space .choice-configuration");
    function inspect(keys) {
      choices.replaceChildren();
      for (const key of keys) {
        const p = parameters.get(key), axis = axes.find(a => a.key === key);
        if (!p || !axis) continue;
        const scope = p.effective_requirement_differs ? ` · effective here; request permits ${p.domain.values.join(", ")}` : "";
        const button = node("button", `${axis.symbol || axis.label}: ${p.value_label}${axis.unit ? " " + axis.unit : ""}${scope}`);
        button.className = "quiet";
        button.title = p.coverage === "not_applicable" ? "Not applicable to this preparation" : "Expose this quantity in the choice plot";
        button.onclick = () => expose(key);
        button.onpointerenter = button.onfocus = () => locateParameter(axis);
        button.onpointerleave = button.onblur = () => locateParameter(null);
        choices.append(button);
      }
      locateParameter(keys.map(k => axes.find(a => a.key === k)).filter(Boolean));
      if (configuration && choices.childElementCount) configuration.open = true;
    }
    for (const feature of drawing.querySelectorAll("[data-teaching-keys]")) {
      const keys = JSON.parse(feature.dataset.teachingKeys);
      feature.onclick = () => inspect(keys);
      feature.onkeydown = event => {
        if (["Enter", " "].includes(event.key)) {event.preventDefault(); inspect(keys);}
      };
      feature.onpointerenter = feature.onfocus = () => locateParameter(keys.map(k => axes.find(a => a.key === k)).filter(Boolean));
      feature.onpointerleave = feature.onblur = () => locateParameter(null);
    }
    const context = node("details", "");
    context.append(node("summary", "Preparation permissions, preservation and evaluation coverage"));
    const facts = preview.teaching.context, modes = [];
    function materialModes(value, path = []) {
      if (!value || typeof value !== 'object') return;
      if (value.mode) modes.push(`${path.join(' / ').replaceAll('_',' ')}: ${value.mode}`);
      else for (const [key, child] of Object.entries(value)) materialModes(child,[...path,key]);
    }
    materialModes(facts.material_policies);
    context.append(node('p',modes.join(' · ')));
    context.append(node('p',`Evaluation limits: ${facts.budgets.max_branches} branches, ${facts.budgets.max_continuations_per_branch} continuations per branch. Local search bounds remain in force.`));
    const exact=node('details','');exact.append(node('summary','Exact policies, controls and coverage'));
    exact.append(node("pre", JSON.stringify(facts, null, 2)));context.append(exact);
    const frame = node("div", ""); frame.className = "teaching-window"; frame.tabIndex = 0;
    frame.setAttribute("role", "region");
    frame.setAttribute("aria-label", "Selected molecular structure and parameters");
    frame.append(drawing);
    // Keep the molecule next to its axes. Detailed permissions and inspection
    // controls belong in the existing disclosure, never between the two plots.
    host.replaceChildren(frame);
    let information = document.getElementById("teaching-information");
    if (!information) {
      information = node("div", ""); information.id = "teaching-information";
      (configuration || host).append(information);
    }
    information.replaceChildren(choices, detail, context);
    teachingNavigation(drawing);
    // A molecular feature includes the space between its letters and brackets.
    // Do not require a pixel-perfect click on a stroke or character.
    for (const feature of drawing.querySelectorAll("[data-teaching-keys]")) {
      const box = feature.getBBox();
      if (!box.width && !box.height) continue;
      const hit = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      for (const [key, value] of Object.entries({x:box.x-3, y:box.y-3, width:Math.max(14,box.width+6), height:Math.max(14,box.height+6), fill:"transparent", "data-teaching-hit":"true"})) hit.setAttribute(key, value);
      feature.insertBefore(hit, feature.firstChild);
    }
    locateParameter(null);
    connectTeaching(host, $("choice-plot"));
    };
}

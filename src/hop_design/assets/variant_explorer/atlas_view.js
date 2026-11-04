"use strict";
// Layout arrives from the shared export. This module owns interaction only.
import { molecularNavigation } from "./grouped_navigation.js";
import { attachCamera } from "./camera.js";
import { scenePoints, stopMotion, tweenScene } from "./motion.js";
import { attachLocalExploration } from "./local_choices.js";

export function renderAtlas(preview, text, onPick, onNeighborhood, transition) {
  const viewport = document.getElementById("viewport");
  stopMotion();
  const before = scenePoints(viewport.querySelector("svg"));
  const root = new DOMParser().parseFromString(text, "image/svg+xml").documentElement;
  const drawing = document.importNode(root, true);
  drawing.dataset.wholeFrame = drawing.getAttribute("viewBox");
  const assembly = drawing.dataset.atlasPresentation === "assembly";
  drawing.setAttribute("aria-label", assembly
    ? `Complete preparation in ${drawing.querySelectorAll("[data-atlas-state]").length} assembly scenes; detailed record retained`
    : "Complete molecular preparation; all recorded processing steps");
  // Replace once only after the complete target SVG has been fetched and parsed.
  viewport.replaceChildren(drawing);
  attachCamera(drawing);
  attachLocalExploration(drawing, onNeighborhood, onPick);
  molecularNavigation(drawing);
  tweenScene(before, drawing, transition);
  document.getElementById("molecule-stage").textContent = assembly
    ? "Assembly overview · one complete preparation"
    : "All recorded processing steps · one complete preparation";
  document.getElementById("construction-cost").textContent = (preview.atlas.construction_cost?.summary_lines || []).join(" ");
  const shown = new Set([...drawing.querySelectorAll("[data-atlas-state]")].map(e => e.dataset.atlasState));
  const focus = preview.atlas.states.filter(s => shown.has(s.state.state_id)).flatMap(s => s.bases.filter(b => b.focus_relation));
  document.getElementById("inspection-detail").textContent = focus.length
    ? `${focus.length} recorded occurrences follow the inspected position across this route.`
    : "Every base in each displayed scene is retained. Zoom to inspect exact sequence and recorded contacts.";
}

"use strict";
import { panFrame, zoomFrame, wheelMode, cameraKey } from "./camera_geometry.js";
// Camera state never enters a query, selection, or retrieval receipt.
let current = null, frameId = null;
const frames = new Map(), numbers = value => value.split(/\s+/).map(Number);
const scope = drawing => drawing.dataset.atlas ? "all" : "single";
const whole = drawing => numbers(drawing.dataset.wholeFrame);

function setFrame(target, animate = false) {
  if (!current) return;
  if (frameId !== null) cancelAnimationFrame(frameId);
  const drawing = current, before = numbers(drawing.getAttribute("viewBox"));
  frames.set(scope(drawing), target);
  const duration = animate && !matchMedia("(prefers-reduced-motion: reduce)").matches ? 240 : 0;
  const start = performance.now();
  function tick(now) {
    const t = duration ? Math.min(1, (now - start) / duration) : 1, e = t * t * (3 - 2 * t);
    drawing.setAttribute("viewBox", target.map((v, i) => before[i] + (v - before[i]) * e).join(" "));
    frameId = t < 1 ? requestAnimationFrame(tick) : null;
  }
  tick(start);
}
export function wholeMolecule() { if (current) setFrame(whole(current), true); }
export function zoomNeighborhood(name) {
  if (!current) return;
  const base = current.querySelector(`[data-base-index][data-neighborhood="${name}"]`);
  if (!base) return;
  const box = base.getBBox(), y = +(base.closest("[data-atlas-y]")?.dataset.atlasY || 0) + +(base.closest("[data-scene-y]")?.dataset.sceneY || 0);
  const x = +(base.closest("[data-atlas-x]")?.dataset.atlasX || 0);
  setFrame([box.x + x - 180, box.y + y - 120, 420, 280], true);
}
function position(event, drawing) {
  const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(drawing.getScreenCTM().inverse());
  const frame = numbers(drawing.getAttribute("viewBox"));
  return {frame, point, anchor: [(point.x - frame[0]) / frame[2], (point.y - frame[1]) / frame[3]]};
}
export function attachCamera(drawing) {
  current = drawing;
  drawing.style.minWidth = "0";
  drawing.style.aspectRatio = "auto";
  drawing.style.height = "100%";
  drawing.dataset.camera = "continuous";
  setFrame(frames.get(scope(drawing)) || whole(drawing));
  const viewport = drawing.parentElement;
  viewport.classList.add("molecular-camera");
  const fit = document.createElement("button");
  fit.id = "fit-route";
  fit.className = "camera-fit";
  fit.textContent = drawing.dataset.atlas ? "Fit route" : "Fit molecule";
  fit.title = "Restore full view (Home or 0). Pinch or Ctrl+scroll to zoom; pan after zooming.";
  fit.onclick = wholeMolecule;
  viewport.querySelector("#fit-route")?.remove();
  viewport.append(fit);
  drawing.addEventListener("wheel", event => {
    const { frame, anchor } = position(event, drawing);
    const mode = wheelMode(frame, whole(drawing), event);
    if (mode === "page") return;
    event.preventDefault();
    if (mode === "zoom") setFrame(zoomFrame(frame, Math.exp(event.deltaY * 0.003), anchor, whole(drawing)));
    else {
      const matrix = drawing.getScreenCTM();
      setFrame(panFrame(frame, event.deltaX / matrix.a, event.deltaY / matrix.d));
    }
  }, { passive: false });
  let drag = null, moved = false;
  drawing.addEventListener("pointerdown", event => {
    if (event.button !== 0 || event.target.closest("[data-base-index],[data-site-id],[data-region-anchor]")) return;
    if (wheelMode(numbers(drawing.getAttribute("viewBox")), whole(drawing), {}) === "page") return;
    drag = [event.clientX, event.clientY];
    moved = false;
    drawing.setPointerCapture(event.pointerId);
  });
  drawing.addEventListener("pointermove", event => {
    if (!drag) return;
    moved ||= Math.hypot(drag[0] - event.clientX, drag[1] - event.clientY) > 2;
    const frame = numbers(drawing.getAttribute("viewBox")), matrix = drawing.getScreenCTM();
    setFrame(panFrame(frame, (drag[0] - event.clientX) / matrix.a, (drag[1] - event.clientY) / matrix.d));
    drag = [event.clientX, event.clientY];
  });
  drawing.addEventListener("pointerup", () => { drag = null; });
  drawing.addEventListener("pointercancel", () => { drag = null; });
  drawing.addEventListener("click", event => {
    if (moved) { event.stopImmediatePropagation(); moved = false; }
  }, true);
  viewport.onkeydown = event => {
    if (event.defaultPrevented || event.target.closest("select,input,textarea")) return;
    const frame = numbers(drawing.getAttribute("viewBox"));
    const action = cameraKey(event.key);
    if (action === "fit") { event.preventDefault(); wholeMolecule(); }
    else if (action !== null) {
      event.preventDefault(); setFrame(zoomFrame(frame, action, [0.5, 0.5], whole(drawing)));
    }
  };
}

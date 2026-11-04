"use strict";
import { motionPlan } from "./continuity.js";
import { bandPath, ribbonPoints, ribbonPath } from "./strand_curve.js";

export { ribbonPoints };

let animation = null;
export function stopMotion() {
  if (animation !== null) cancelAnimationFrame(animation);
  animation = null;
}
function sceneY(element) {
  return +(element.closest("[data-scene-y]")?.dataset.sceneY || 0);
}
export function scenePoints(drawing) {
  const points = new Map();
  for (const element of drawing?.querySelectorAll("[data-base-index]") || []) {
    const rect = element.querySelector("rect"),
      text = element.querySelector("text");
    const transform = element.transform.baseVal.consolidate()?.matrix;
    const x = +rect.getAttribute("x") + +rect.getAttribute("width") / 2;
    const y = +text.getAttribute("y") - 5;
    points.set(
      JSON.stringify([element.dataset.stateId, element.dataset.strandId, +element.dataset.baseIndex]),
      {
        x: x + (transform?.e || 0) + +(element.closest("[data-atlas-x]")?.dataset.atlasX || 0),
        y: y + sceneY(element) + (transform?.f || 0) + +(element.closest("[data-atlas-y]")?.dataset.atlasY || 0),
        element,
      },
    );
  }
  return points;
}

function updateEdges(drawing, positions) {
  for (const edge of drawing.querySelectorAll("[data-edge-kind]")) {
    const a = positions.get(edge.dataset.from),
      b = positions.get(edge.dataset.to);
    if (!a || !b) continue;
    const length = Math.max(1, Math.hypot(b.x - a.x, b.y - a.y));
    const pad = Math.min(edge.dataset.edgeKind === "pair" ? 10 : 7, length / 2);
    const dx = ((b.x - a.x) * pad) / length,
      dy = ((b.y - a.y) * pad) / length;
    const offset = sceneY(edge) + +(edge.closest("[data-atlas-y]")?.dataset.atlasY || 0);
    const left = +(edge.closest("[data-atlas-x]")?.dataset.atlasX || 0);
    let path = `M${a.x + dx - left},${a.y + dy - offset} L${b.x - dx - left},${b.y - dy - offset}`;
    if (edge.dataset.contactGlyph === "diamond") {
      const mx = (a.x+b.x)/2-left, my = (a.y+b.y)/2-offset, ux = (b.x-a.x)/length, uy = (b.y-a.y)/length;
      const c = [mx-ux*6,my-uy*6], d = [mx+ux*6,my+uy*6];
      path = `M${a.x+dx-left},${a.y+dy-offset} L${c} M${c} L${mx-uy*5},${my+ux*5} L${d} L${mx+uy*5},${my-ux*5} Z M${d} L${b.x-dx-left},${b.y-dy-offset}`;
    }
    edge.setAttribute("d", path);
  }
  for (const span of drawing.querySelectorAll("rect[data-members]")) {
    const pts = JSON.parse(span.dataset.members)
      .map((k) => positions.get(JSON.stringify(k)))
      .filter(Boolean);
    if (!pts.length) continue;
    const x = Math.min(...pts.map((p) => p.x)) - 9,
      y = Math.min(...pts.map((p) => p.y)) - 13;
    span.setAttribute("x", x - +(span.closest("[data-atlas-x]")?.dataset.atlasX || 0));
    span.setAttribute("y", y - sceneY(span) - +(span.closest("[data-atlas-y]")?.dataset.atlasY || 0));
    span.setAttribute("width", Math.max(...pts.map((p) => p.x)) + 9 - x);
    span.setAttribute("height", Math.max(...pts.map((p) => p.y)) + 13 - y);
  }
  for (const span of drawing.querySelectorAll("polygon[data-recognition-footprint],polygon[data-region-width]")) {
    const x = +(span.closest("[data-atlas-x]")?.dataset.atlasX || 0),
      y = sceneY(span) + +(span.closest("[data-atlas-y]")?.dataset.atlasY || 0);
    const pts = JSON.parse(span.dataset.pathMembers || span.dataset.members).map(k => positions.get(JSON.stringify(k)));
    if (pts.every(Boolean)) span.setAttribute("points", ribbonPoints(pts.map(p => [p.x - x, p.y - y]),
      +(span.dataset.recognitionFootprint || span.dataset.regionWidth), +(span.dataset.pathStart || 0),
      span.dataset.pathEnd === undefined ? pts.length - 1 : +span.dataset.pathEnd)
      .map(p => p.join(",")).join(" "));
  }
  for (const span of drawing.querySelectorAll("path[data-region-width],path[data-recognition-footprint]")) {
    const x = +(span.closest("[data-atlas-x]")?.dataset.atlasX || 0),
      y = sceneY(span) + +(span.closest("[data-atlas-y]")?.dataset.atlasY || 0);
    const pts = JSON.parse(span.dataset.pathMembers).map(k => positions.get(JSON.stringify(k)));
    if (!pts.every(Boolean)) continue;
    const local = pts.map(p => [p.x-x,p.y-y]), start = +span.dataset.pathStart, end = +span.dataset.pathEnd;
    span.setAttribute("d", span.dataset.ribbonContour || span.dataset.recognitionFootprint
      ? ribbonPath(local, +(span.dataset.recognitionFootprint || span.dataset.regionWidth), start, end,
          +(span.dataset.terminalExtension || 8))
      : bandPath(local, start, end));
  }
}
export function tweenScene(before, drawing, transition) {
  stopMotion();
  if (
    !before?.size ||
    !transition ||
    matchMedia("(prefers-reduced-motion: reduce)").matches
  )
    return;
  const after = scenePoints(drawing),
    plan = motionPlan(before, after, transition);
  const ghosts = [];
  for (const [key, source] of before) {
    const targets = [...plan.mapped.entries()].filter(
      ([, p]) => p.sourceKey === key,
    );
    if (
      targets.length &&
      targets.every(
        ([to]) =>
          after.get(to).element.textContent === source.element.textContent,
      )
    )
      continue;
    const ghost = source.element.cloneNode(true);
    ghost.removeAttribute("data-base-index");
    ghost.removeAttribute("tabindex");
    ghost.setAttribute("aria-hidden", "true");
    const offset = sceneY(source.element) + +(source.element.closest("[data-atlas-y]")?.dataset.atlasY || 0);
    const left = +(source.element.closest("[data-atlas-x]")?.dataset.atlasX || 0);
    ghost.setAttribute("transform", `translate(${left} ${offset})`);
    ghost.style.pointerEvents = "none";
    drawing.append(ghost);
    ghosts.push(ghost);
  }
  const contextual = [
    ...drawing.querySelectorAll(
      "[data-operation-id], [data-formed-bond], [data-primer-binding], [data-staged-material], [data-foldback-cue], [data-site-id] text, [data-site-labels], [data-region-anchor], [data-interface], [data-correspondence-notice], [data-change-legend]",
    ),
  ];
  const start = performance.now(),
    duration = 340;
  drawing.dataset.transitionMode = transition.mode;
  drawing.setAttribute("aria-busy", "true");
  drawing.setAttribute("aria-disabled", "true");
  drawing.style.pointerEvents = "none";
  function frame(now) {
    const raw = Math.min(1, (now - start) / duration),
      t = raw * raw * (3 - 2 * raw),
      positions = new Map();
    for (const [key, end] of after) {
      const from = plan.mapped.get(key);
      const x = from ? from.x + (end.x - from.x) * t : end.x,
        y = from ? from.y + (end.y - from.y) * t : end.y;
      end.element.setAttribute(
        "transform",
        `translate(${x - end.x} ${y - end.y})`,
      );
      end.element.style.opacity = from ? 1 : t;
      positions.set(key, { x, y });
    }
    updateEdges(drawing, positions);
    ghosts.forEach((g) => (g.style.opacity = 1 - t));
    contextual.forEach((e) => (e.style.opacity = t));
    if (raw < 1) animation = requestAnimationFrame(frame);
    else {
      ghosts.forEach((g) => g.remove());
      after.forEach((p) => {
        p.element.removeAttribute("transform");
        p.element.style.opacity = "";
      });
      contextual.forEach((e) => (e.style.opacity = ""));
      drawing.removeAttribute("data-transition-mode");
      drawing.removeAttribute("aria-busy");
      drawing.removeAttribute("aria-disabled");
      drawing.style.pointerEvents = "";
      animation = null;
    }
  }
  frame(start);
}

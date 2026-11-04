// Interaction only: coordinates, labels and trace membership come from the shared SVG.
import { groupedNavigation } from "./grouped_navigation.js";
function activate(element, callback) {
  element.addEventListener("click", callback);
  element.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      callback();
    }
  });
}
export function plotDrawing(drawing, contextText=()=>{}) {
  const document = new DOMParser().parseFromString(drawing, "image/svg+xml");
  if (document.querySelector("parsererror")) throw Error("Invalid survey drawing.");
  const svg = document.documentElement;
  // The exported caption stays exact; the browser discloses it outside the plot.
  const context = svg.querySelector("[data-plot-context]");
  if (context && svg.dataset.landscapeFrame) {
    contextText([...context.querySelectorAll("text")].map(e => e.textContent).join(" "));
    context.remove();
    svg.setAttribute("viewBox", svg.dataset.landscapeFrame);
    svg.removeAttribute("height");
  }
  return svg;
}
export function drawPlot(container, choices, drawing, actions) {
  const svg=plotDrawing(drawing,actions.context);
  const axes = new Map(choices.axes.map((axis) => [axis.key, axis]));
  const records = new Map();
  for (const record of choices.paths) {
    if (!records.has(record.materialized_realization_id))
      records.set(record.materialized_realization_id, record);
  }
  for (const path of svg.querySelectorAll("[data-members]")) {
    const members = JSON.parse(path.dataset.members).map((id) => {
      if (!records.has(id)) throw Error("Plotted preparation is absent from the admitted pool.");
      return records.get(id);
    });
    activate(path, () => actions.path(members));
    for (const event of ["pointerenter", "focus"])
      path.addEventListener(event, () => actions.hover?.(members));
  }
  for (const title of svg.querySelectorAll("[data-axis-title]")) {
    const axis = axes.get(title.dataset.axisTitle);
    title.addEventListener("pointerenter", () => actions.focus(axis));
    title.addEventListener("focus", () => actions.focus(axis));
    activate(title, () => actions.domain(axis));
  }
  for (const group of svg.querySelectorAll("[data-node-value]")) {
    const axis = axes.get(group.dataset.parameter);
    const value = JSON.parse(group.dataset.nodeValue);
    const description = group.querySelector("title").textContent;
    group.setAttribute("aria-label", description);
    activate(group, () => actions.value(axis.key, value));
    group.addEventListener("pointerenter", () => actions.focus(axis, description, value));
    group.addEventListener("focus", () => actions.focus(axis, description, value));
  }
  for (const hit of svg.querySelectorAll("[data-brush-axis]")) {
    const positions = JSON.parse(hit.dataset.positions);
    let start = null;
    const nearest = (event) => {
      const point = svg.createSVGPoint();
      point.x = event.clientX;
      point.y = event.clientY;
      const y = point.matrixTransform(svg.getScreenCTM().inverse()).y;
      return positions.reduce((a, b) => Math.abs(a[1] - y) < Math.abs(b[1] - y) ? a : b)[0];
    };
    hit.addEventListener("pointerdown", (event) => {
      start = nearest(event);
      hit.setPointerCapture(event.pointerId);
    });
    hit.addEventListener("pointerup", (event) => {
      if (start !== null) {
        actions.range(hit.dataset.brushAxis, start, nearest(event));
        start = null;
      }
    });
    hit.addEventListener("pointercancel", () => { start = null; });
  }
  groupedNavigation([...axes.keys()].map(key => [
    ...svg.querySelectorAll(`[data-axis-title="${key}"],[data-node-value][data-parameter="${key}"]`),
  ]));
  groupedNavigation([svg.querySelectorAll("[data-members]")]);
  container.replaceChildren(svg);
}

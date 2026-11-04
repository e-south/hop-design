"use strict";
const ns = "http://www.w3.org/2000/svg";
function element(tag, attrs, text) {
  const el = document.createElementNS(ns, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  if (text) el.textContent = text;
  return el;
}
// A numeric brush edits one inclusive integer interval. It does not enumerate or interpolate products.
export function attachNumericBrush({chart, axis, x, top, bottom, positions, selection, onRange, onClear, onDetail}) {
  const known = axis.values.map(v => v.value).filter(v => Number.isInteger(v));
  if (!known.length) return;
  const minimum = Math.min(...known), maximum = Math.max(...known);
  const yMin = positions.get(minimum), yMax = positions.get(maximum);
  const toY = value => maximum === minimum ? yMin : yMin + (value - minimum) / (maximum - minimum) * (yMax - yMin);
  const toValue = y => maximum === minimum ? minimum : Math.max(minimum, Math.min(maximum, Math.round(minimum + (y - yMin) / (yMax - yMin) * (maximum - minimum))));
  const track = element("rect", {x: x - 30, y: top - 8, width: 20, height: bottom - top + 16, class: "axis-brush-track", "data-brush-key": axis.key, tabindex: 0, role: "slider", "aria-label": `Brush ${axis.label}; arrows move the range, Shift plus arrows changes its upper boundary, Escape clears`, "aria-valuemin": minimum, "aria-valuemax": maximum});
  const band = element("rect", {x: x - 29, width: 18, rx: 3, class: "axis-brush-band", "pointer-events": "none"});
  const discrete = Array.isArray(selection);
  let current = discrete ? {minimum: Math.min(...selection), maximum: Math.min(...selection)} : selection ? {...selection} : {minimum, maximum}, anchor = null;
  function paint(active = true, announce = true) {
    const a = toY(current.minimum), b = toY(current.maximum);
    band.setAttribute("y", Math.min(a, b) - 3); band.setAttribute("height", Math.max(6, Math.abs(a - b)));
    band.style.display = active ? "" : "none";
    track.setAttribute("aria-valuenow", current.minimum);
    const description = discrete && !active ? `${selection.join(" or ")} ${axis.unit}; discrete selection` : `${current.minimum} to ${current.maximum} ${axis.unit}`;
    track.setAttribute("aria-valuetext", description);
    if (announce) onDetail(`${axis.label}: ${description}. Other constraints remain held.`);
  }
  const y = event => new DOMPoint(event.clientX, event.clientY).matrixTransform(chart.getScreenCTM().inverse()).y;
  track.onpointerdown = event => {event.preventDefault(); anchor = toValue(y(event)); track.setPointerCapture(event.pointerId); current = {minimum: anchor, maximum: anchor}; paint(); onRange(current, false);};
  track.onpointermove = event => {
    if (anchor === null) return;
    const end = toValue(y(event)); current = {minimum: Math.min(anchor, end), maximum: Math.max(anchor, end)}; paint(); onRange(current, false);
  };
  track.onpointerup = event => {if (anchor === null) return; anchor = null; track.releasePointerCapture(event.pointerId); onRange(current, true);};
  track.onpointercancel = () => {anchor = null; onRange(selection || null, true);};
  track.onkeydown = event => {
    if (event.key === "Escape") {event.preventDefault(); onClear(); return;}
    const delta = ["ArrowUp", "ArrowRight"].includes(event.key) ? 1 : ["ArrowDown", "ArrowLeft"].includes(event.key) ? -1 : 0;
    if (!delta) return; event.preventDefault();
    if (event.shiftKey) current.maximum = Math.min(maximum, Math.max(current.minimum, current.maximum + delta));
    else if (current.minimum + delta >= minimum && current.maximum + delta <= maximum) {current.minimum += delta; current.maximum += delta;}
    paint(); onRange(current, true);
  };
  track.onfocus = () => paint(Boolean(selection) && !discrete);
  chart.append(track, band); paint(Boolean(selection) && !discrete, false);
}

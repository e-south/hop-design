// Presentation coordinates only; parameter identities and spans come from HOP.
export function connectTeaching(teaching, plot, parent = teaching.parentElement) {
  parent.querySelector(".teaching-links")?.remove();
  const source = teaching.querySelector("svg"), destination = plot.querySelector("svg");
  if (!source || !destination) return;
  const bounds = parent.getBoundingClientRect(), box = source.getBoundingClientRect();
  const extent = Math.max(box.bottom, destination.getBoundingClientRect().bottom) - bounds.top;
  const [,,width,height] = source.getAttribute("viewBox").split(/\s+/).map(Number);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("teaching-links");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("viewBox", `0 0 ${bounds.width} ${extent}`);
  // Expanding controls below the plot must not stretch its measured coordinates.
  svg.style.width = `${bounds.width}px`;
  svg.style.height = `${extent}px`;
  source.querySelectorAll('[data-parameter-origin]').forEach(e => e.remove());
  source.querySelectorAll(':scope > rect[fill="white"]').forEach(e => e.setAttribute('fill', 'none'));
  for (const anchor of source.querySelectorAll("[data-parameter-anchor]")) {
    const key = anchor.dataset.parameterAnchor;
    const label = [...destination.querySelectorAll("[data-axis-title]")].find(e =>
      e.dataset.axisTitle === key && (e.closest("[data-band]")?.dataset.band || "0") === "0");
    if (!label) continue;
    const regions = JSON.parse(anchor.dataset.anchorRegions || "null") || [JSON.parse(anchor.dataset.anchorBox)];
    const target = label.getBoundingClientRect(), tx = target.left - bounds.left + target.width/2;
    const ty = target.top - bounds.top - 7;
    for (const [x,y,w,h] of regions) {
      const a = box.left - bounds.left + x * box.width / width, b = a + w * box.width / width;
      const sy = box.top - bounds.top + (y+h) * box.height / height;
      const polygon = document.createElementNS(svg.namespaceURI, "polygon");
      polygon.dataset.parameter = key;
      polygon.dataset.parameterLink = key;
      polygon.setAttribute("points", `${a},${sy} ${b},${sy} ${tx+15},${ty} ${tx-15},${ty}`);
      svg.append(polygon);
      if (regions.length === 1 && w <= 18 && h <= 24) {
        const mark = document.createElementNS(svg.namespaceURI, "rect");
        mark.dataset.parameterOrigin = key;
        for (const [k,v] of Object.entries({x:x-2,y:y-3,width:w+4,height:h+6,rx:3,fill:"none",stroke:"#182B34","stroke-width":2.2,"pointer-events":"none"})) mark.setAttribute(k,v);
        source.append(mark);
      }
    }
  }
  parent.append(svg);
}

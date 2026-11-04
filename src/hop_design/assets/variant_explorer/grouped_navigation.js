// One Tab entry per semantic group. Arrow keys inspect without selecting anything.
export function groupedNavigation(groups) {
  for (const group of groups) {
    const nodes = [...group];
    nodes.forEach((node, index) => {
      node.setAttribute("tabindex", index === 0 ? "0" : "-1");
      node.addEventListener("focus", () => {
        for (const peer of nodes) peer.setAttribute("tabindex", peer === node ? "0" : "-1");
      });
      node.addEventListener("keydown", event => {
        if (event.defaultPrevented) return;
        const delta = ["ArrowRight", "ArrowDown"].includes(event.key) ? 1
          : ["ArrowLeft", "ArrowUp"].includes(event.key) ? -1 : 0;
        if (!delta) return;
        event.preventDefault();
        nodes[Math.max(0, Math.min(nodes.length - 1, index + delta))].focus();
      });
    });
  }
}

export function groupBy(nodes, key) {
  const groups = new Map();
  for (const node of nodes) {
    const value = key(node);
    if (!groups.has(value)) groups.set(value, []);
    groups.get(value).push(node);
  }
  return [...groups.values()];
}

export function molecularNavigation(drawing) {
  groupedNavigation(groupBy(drawing.querySelectorAll("[data-base-index]"), base =>
    `${base.dataset.stateId}|${base.dataset.neighborhood || base.dataset.strandId}`));
  groupedNavigation(groupBy(drawing.querySelectorAll("[data-site-id]"), site =>
    site.closest("[data-atlas-state]")?.dataset.atlasState || "sites"));
}

export function teachingNavigation(drawing) {
  groupedNavigation(groupBy(drawing.querySelectorAll("[data-teaching-keys]"), feature =>
    feature.closest("[data-teaching-frame]")?.dataset.teachingFrame || "teaching"));
}

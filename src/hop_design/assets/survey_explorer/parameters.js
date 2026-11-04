// Shared parameter identities on axes, teaching groups and exact molecular marks.
export const parameterSelector =
  "[data-parameter],[data-parameter-keys],[data-teaching-keys]";

export function parameterKeys(element) {
  const data = element.dataset;
  return [...new Set([
    ...(data.parameter ? [data.parameter] : []),
    ...JSON.parse(data.parameterKeys || "[]"),
    ...JSON.parse(data.teachingKeys || "[]"),
  ])];
}

export function resolveParameterFocus(axes, keys) {
  const concepts = new Map(), expanded = new Set();
  for (const axis of axes) {
    const family = [axis.key, axis.canonical_key || axis.key, ...(axis.equivalent_measurements || [])];
    if (!family.some(key => keys.includes(key))) continue;
    const canonical = axis.canonical_key || axis.key;
    if (!concepts.has(canonical) || axis.key === canonical) concepts.set(canonical, axis);
    family.forEach(key => expanded.add(key));
  }
  return {axes: [...concepts.values()], keys: [...expanded]};
}

export function highlightParameters(root, keys) {
  for (const element of root.querySelectorAll(parameterSelector))
    element.classList.toggle(
      "parameter-highlight",
      parameterKeys(element).some((key) => keys.includes(key)),
    );
}

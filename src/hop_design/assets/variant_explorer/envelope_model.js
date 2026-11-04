"use strict";
export function selectCoordinate(query, key, value) {
  const parameters = (query.parameters || []).filter(p => p.key !== key);
  return {...query, schema:"hop.scaffold-variant-query/v2", parameters:[...parameters,{key,values:[value]}]};
}
export function pivotQuery(query, key, value, alternative, path) {
  if (alternative.preservation_conflicts.length) throw new Error("This preparation conflicts with preserved properties or neighborhood choices.");
  let next = {...query, parameters:[...(query.parameters || [])]};
  for (const name of alternative.different_selections) {
    const actual = path.values[name];
    if (actual === null || actual === undefined) throw new Error("This coordinate is unassessed.");
    next.parameters = next.parameters.map(p => p.key === name ? {key:name,values:[actual]} : p);
  }
  return selectCoordinate(next, key, value);
}
export function rangePermission(field, minimum, maximum, unrestricted) {
  if (unrestricted && field.unrestricted === "empty") return [];
  if (unrestricted && field.unrestricted === "null") return null;
  const lo = Number(minimum), hi = Number(maximum);
  if (!Number.isSafeInteger(lo) || !Number.isSafeInteger(hi) || lo > hi)
    throw new Error("Use ordered integer boundaries.");
  if (field.kind === "integer") return lo;
  if (hi - lo > 10000) throw new Error("This editor limits a discrete roster to 10,001 entries; use a bounded free domain or the CLI/API for a different envelope.");
  return Array.from({length:hi-lo+1},(_,i) => lo+i);
}

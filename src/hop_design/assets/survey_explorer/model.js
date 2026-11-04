// Pure projections: never synthesize combinations from independent axis values.
export function toggleValue(query, key, value) {
  const previous = query.parameters.find((p) => p.key === key);
  const rest = query.parameters.filter((p) => p.key !== key);
  return {
    ...query,
    parameters:
      previous?.values?.length === 1 && previous.values[0] === value
        ? rest
        : [...rest, { key, values: [value] }],
  };
}
export function rangeQuery(query, key, first, last) {
  return {
    ...query,
    parameters: [
      ...query.parameters.filter((p) => p.key !== key),
      { key, minimum: Math.min(first, last), maximum: Math.max(first, last) },
    ],
  };
}
export function queryCommands(selection, seed, discovery = null) {
  if (discovery !== null) {
    if (typeof discovery.commands !== 'string') throw Error('Missing authoritative design commands.');
    return discovery.commands;
  }
  const prefix = "hop-design construction survey";
  const source = "request.json --index survey.sqlite";
  const lines = [`${prefix} query ${source} --query query.json`];
  if (!selection) return lines.join("\n");
  const { target, step } = selection.address;
  const identity =
    "'" +
    selection.materialized_realization_id.replaceAll("'", "'\"'\"'") +
    "'";
  lines.push(
    `${prefix} select ${source} --query query.json --target ${target} --step ${step} --identity ${identity} > selection.json`,
    `${prefix} atlas ${source} --selection selection.json --out atlas`,
    `${prefix} retrieve ${source} --selection selection.json --out preparation`,
  );
  if (seed !== null)
    lines.push(
      "# Repeat the draw against the same admitted pool and query:",
      `${prefix} sample ${source} --query query.json --seed ${seed} > sampled-selection.json`,
    );
  return lines.join("\n");
}

export function preparationSummary(path) {
  const ends = [path.values.left_end_word, path.values.right_end_word];
  const words = ends.some(value => value !== undefined && value !== null)
    ? ends.map(value => value ?? 'unspecified').join(' / ') : '';
  const methods = [...new Set((path.methods || []).map(m => m.name))].join(', ');
  const loop = path.values.loop_word ? `loop ${path.values.loop_word}` : '';
  return [words, loop, methods].filter(Boolean).join(' · ');
}

export function preparationDescription(path, reference) {
  const roles = path.material_roles || {}, previous = reference?.material_roles || {};
  const changed = Object.keys({...roles, ...previous}).filter(role =>
    roles[role]?.material_id !== previous[role]?.material_id);
  const materials = path === reference
    ? Object.entries(roles).map(([role, material]) => `${role.replaceAll('_', ' ')} ${material.length_nt} nt`).join(', ')
    : changed.length
      ? changed.map(role => `${role.replaceAll('_', ' ')} changes`).join(', ')
      : 'same materials';
  return [preparationSummary(path), materials].filter(Boolean).join(' · ');
}
export function coverageDescription(coverage) {
  return `${coverage.supported_pairs ?? 0} supported pairs · ${coverage.excluded_pairs ?? 0} excluded within scope · ${coverage.unresolved_pairs ?? 0} unresolved`;
}

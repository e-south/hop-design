"use strict";
export function supportedVariants(choices) {
  return choices.variants.map(v => ({...v,
    option_labels: v.option_labels.filter(label => choices.compatible_options.includes(label)),
  })).filter(v => v.option_labels.length && v.sequences.length);
}

export function exclusionSummaries(choices, labels) {
  const groups = new Map();
  for (const excluded of choices.excluded_options) {
    const messages = new Set(excluded.reasons.map(reason => {
      const stage = (reason.stage || choices.query.stage) === "hairpin"
        ? "at the hairpin stage" : "at the requested endpoint";
      const subject = labels.neighborhoods[reason.neighborhood] || labels.properties[reason.property];
      if (!subject) return "A recorded exclusion requires the exact diagnostic below.";
      if (reason.kind === "neighborhood_pin") return reason.status === "different"
        ? `${subject} does not match the allowed variants ${stage}.`
        : `${subject} is unassessed against the allowed variants ${stage}.`;
      if (["preserved_surroundings", "preserved_property"].includes(reason.kind))
        return reason.status === "different"
          ? `${subject} differs from the fixed reference ${stage}.`
          : `${subject} is unassessed against the fixed reference ${stage}.`;
      return "A recorded exclusion requires the exact diagnostic below.";
    }));
    for (const text of messages) groups.set(text, (groups.get(text) || 0) + 1);
  }
  return [...groups].map(([text, count]) => ({text, count}));
}

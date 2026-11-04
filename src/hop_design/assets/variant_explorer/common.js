"use strict";
export const $ = (id) => document.getElementById(id);
export const neighborhoods = {
  loop: "Loop",
  closing: "Loop-side stem",
  assembly: "Open side",
  stem: "Supplied stem",
  interfaces: "Released interfaces",
};
export const properties = {
  non_loop_sequences: "Sequence outside the loop",
  non_loop_pairing: "Pairing outside the loop",
  terminal_chemistry: "Terminal chemistry",
  product_identity: "Exact whole product",
};
export function node(tag, text) {
  const n = document.createElement(tag);
  n.textContent = text;
  return n;
}
export function variantName(v) {
  return v.sequences.length
    ? v.sequences
        .map((s) =>
          s.product_end
            ? `${s.product_end}: ${s.sequence} (${s.overhang_end.replaceAll("_", " ")})`
            : `${s.sequence} · ${s.sequence.length} nt`,
        )
        .join(" / ")
    : "No sequence at the assessment stage";
}
export function preparationName(state, label) {
  const p = state.choices.preparations.find((p) => p.label === label),
    o = state.pool.options.find((o) => o.label === label);
  const space = state.choices.choice_space, values = space.paths.find(path => path.option_label === label)?.values || {};
  const dimensions = ["foldback_arm_bp", "join_offset_nt"].flatMap(key => {
    const axis = space.axes.find(axis => axis.key === key), value = values[key];
    return axis && value !== null && value !== undefined ? [`${axis.symbol || axis.label} ${value} ${axis.unit}`] : [];
  });
  return [`loop ${o.loop_sequence}`, ...dimensions, p.methods.map((m) => m.name).join(" / "), label].join(" · ");
}

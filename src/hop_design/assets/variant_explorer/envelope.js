"use strict";
import { $, node } from "./common.js";

const domain = values => values?.length ? values.join(", ") : "bounded by the recorded request";
const span = range => range ? (range.minimum === range.maximum ? String(range.minimum) : `${range.minimum}–${range.maximum}`) : "not separately required";

export function renderEnvelope(preview) {
  const box = $("design-envelope"), envelope = preview.envelope;
  box.replaceChildren();
  if (!envelope) return;
  const g = envelope.generating_domains, observed = envelope.observed;
  $("achieved").textContent = `Hairpin ${envelope.observed_stage_role}: ${observed.stem_bp} supplied bp · ${observed.loop_side_paired_bp} added loop-side bp · ${observed.loop_nt}-nt loop · ${observed.open_side_paired_positions} open-side paired positions.`;
  const regions = node("div", ""); regions.className = "envelope-regions";
  const closing = node("p", `Foldback permissions: arm ${domain(g.foldback.annealing_arm_lengths_bp)} bp; join displacement ${domain(g.foldback.junction_offsets_nt)} nt; loop ${domain(g.foldback.loop_lengths_nt)} nt.`);
  closing.dataset.envelopeRegion = "closing";
  const basal = node("p", g.basal ? `Basal permissions: nick offset ${domain(g.basal.nick_offsets_nt)} nt; adapter annealing ≥${g.basal.minimum_adapter_annealing_nt} nt.` : "Basal construction is defined by the captured request.");
  basal.dataset.envelopeRegion = "assembly";
  regions.append(basal, closing); box.append(regions);
  if (Object.keys(envelope.effective_scaffold).length)
    box.append(node("p", "Required hairpin dimensions: " + Object.entries(envelope.effective_scaffold).map(([key, range]) => `${key.replaceAll("_", " ")}: ${span(range)}`).join("; ") + "."));
  if (envelope.end_placements.length)
    box.append(node("p", "Permitted insert end-to-stem gaps (left/right): " + envelope.end_placements.map(p => `${p.left_bp}/${p.right_bp} bp`).join(" · ") + "."));
  box.append(node("p", "Permitted methods: " + Object.entries(envelope.method_permissions).map(([role, items]) => `${role.replaceAll("_", " ")}: ${items.map(i => i.name).join(", ") || "none"}`).join("; ") + "."));
  for (const conflict of envelope.conflicts) {
    const warning = node("p", `${conflict.requested_field}: conflicts with ${conflict.inherited_field}. ${conflict.explicit_edit}`);
    warning.className = "envelope-conflict"; box.append(warning);
  }
  const detail = node("details", "");
  detail.append(node("summary", "Revise the generating request · separate from browsing"));
  detail.append(node("p", "These are recorded permissions, not independent sliders. Export the request, author an explicit revision, and preview its inherited conflicts before any further evaluation."));
  if (preview.request_file) {
    const link = node("a", "Export captured request"); link.href = preview.request_file;
    link.download = "request.json"; detail.append(link);
  }
  detail.append(node("pre", "hop-design construction prepare-edit request.json --loop GAAA --out revision\n# Review revision/report.md before a separate evaluate-edit operation."));
  box.append(detail);
  $("readiness").textContent = envelope.readiness;
}

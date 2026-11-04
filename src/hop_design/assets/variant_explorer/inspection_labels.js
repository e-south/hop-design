"use strict";
import { neighborhoods, variantName } from "./common.js";

export function realizationName(candidate, peers, focus) {
  const other = peers.filter((p) => p.label !== candidate.label);
  const methods = candidate.methods
    .filter((m) =>
      other.some((p) => !p.methods.some((x) => x.enzyme_id === m.enzyme_id)),
    )
    .map((m) => m.name);
  const regions = Object.entries(candidate.neighborhoods)
    .filter(
      ([k, v]) =>
        k !== focus &&
        v?.sequences?.length &&
        other.some((p) => p.neighborhoods[k]?.variant_id !== v.variant_id),
    )
    .map(([k, v]) => {
      // Omit sequence components identical in every background. Literal differing words
      // are displayed whole; this is not a new positional alignment or molecular claim.
      const changed = v.sequences.filter((part, index) =>
        other.some(
          (p) =>
            p.neighborhoods[k]?.sequences?.[index]?.sequence !== part.sequence,
        ),
      );
      return `${neighborhoods[k]}: ${variantName({ ...v, sequences: changed })}`;
    });
  const distances = candidate.interface?.achieved_distances_bp;
  if (
    distances &&
    other.some(
      (p) =>
        JSON.stringify(p.interface?.achieved_distances_bp) !==
        JSON.stringify(distances),
    )
  )
    regions.push(`End gaps ${distances.left}/${distances.right} bp`);
  const description =
    [...methods, ...regions].join(" · ") ||
    "Same molecular regions; distinct preparation";
  // IDs remain available in the exact record and option title, beneath molecular labels.
  return description;
}
export function inspectionNotices(preview, transition) {
  const states = preview.molecular_state || { recognition_sites: [] },
    differences = preview.view?.regions || [];
  const unresolved = differences.filter((r) =>
    ["ambiguous_minimum_edit", "unresolved_budget"].includes(r.correspondence),
  );
  const notes = [...(transition?.notices || []), ...(preview.comparison?.notices || [])].filter(
    (n) =>
      !unresolved.some((r) =>
        n.startsWith(`Position correspondence unresolved: ${r.region} (`),
      ),
  );
  for (const site of states.recognition_sites || []) {
    if (site.presence === "present") continue;
    notes.push(
      `${site.enzyme_name} (${site.role.replaceAll("_", " ")}): ${site.presence.replaceAll("_", " ")}${site.presence === "partial" ? ` (${site.mapped_reference_bases}/${site.reference_base_count} footprint bases)` : ""}.`,
    );
  }
  for (const r of differences)
    if (
      ["ambiguous_minimum_edit", "unresolved_budget"].includes(r.correspondence)
    )
      notes.push(
        `${r.region}: ${r.reference_sequence} → ${r.observed_sequence}; position correspondence unresolved. Uncolored bases here do not imply no change.`,
      );
  return [...new Set(notes)].join(" ");
}

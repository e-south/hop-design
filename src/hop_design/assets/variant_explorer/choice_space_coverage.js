"use strict";
import {$, node} from "./common.js";
import {branchCoverage, localRejections} from "./choice_space_model.js";
export function renderCoverage(space, filters) {
  const branches = branchCoverage(space.branch_coverage || [], filters);
  const examined = branches.filter(b => b.status === "evaluated"), unexamined = branches.length - examined.length;
  const failed = examined.filter(b => b.failures.length || b.parameter_exclusions?.length);
  const locallyRejected = examined.filter(b => localRejections(b).length);
  $("choice-coverage-summary").textContent = `${branches.length} declared branch records overlap these permissions: ${examined.length} examined, ${unexamined} unexamined; ${locallyRejected.length} have an exhausted local exclusion; ${failed.length} include failed or excluded continuations. This is branch coverage, not exhaustive feasibility.`;
  const list = $("choice-coverage"); list.replaceChildren();
  const permissions = space.joint_permissions?.end_placements || [];
  if (permissions.length) list.append(node("p", "Joint left/right end gaps: " + permissions.map(p => `${p.left_bp}/${p.right_bp} bp`).join(" · ") + ". Marginal brushing does not authorize other combinations."));
  list.append(node("p", space.joint_permissions?.foldback || "All original construction permissions remain in force."));
  for (const branch of branches) {
    const detail = node("details", "");
    const label = ["foldback_arm_bp", "join_offset_nt", "loop_word", "left_gap", "right_gap", "basal_method", "release_method"].flatMap(key => {
      const domain = branch.domains[key], axis = space.axes.find(a => a.key === key);
      return domain?.values ? [`${axis?.symbol || axis?.label || key}: ${domain.values.map(v => axis?.values.find(e => e.value === v)?.label || v).join("/")}`] : [];
    }).join(" · ");
    const exclusions = localRejections(branch).map(({region, reasons}) => `${region} domain exhausted: ${reasons.join(", ") || "no local realization"}`).join("; ");
    detail.append(node("summary", `${branch.status}${exclusions ? " · " + exclusions : ""} · ${branch.option_labels.length} complete option(s) · ${label}`));
    detail.append(node("pre", JSON.stringify({local_coverage: branch.local_coverage, continuation_coverage: branch.continuation_coverage, failures: branch.failures, parameter_exclusions: branch.parameter_exclusions, scope: branch.scope}, null, 2)));
    list.append(detail);
  }
}

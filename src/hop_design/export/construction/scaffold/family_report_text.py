"""Readable links and explanatory prose; typed facts remain the comparison authority."""

import json

from hop_design.export.construction.labels import endpoint_label, material_role_label
from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.projections.family_report import (
    ConstructionFamilyReportProjection,
    FamilyReportMember,
)

from .retrieval_text import retrieval_text


def describe_member(member: FamilyReportMember) -> str:
    names = {"loop_nt": "nt loop", "loop_side_paired_bp": "bp loop-side extension"}
    return ", ".join(
        f"{value} {names.get(key, key)}"
        for key, value in member.requested_variation.items()
        if value is not None
    )


def render_report_text(report: ConstructionFamilyReportProjection, page_count: int) -> str:
    md = [
        "# Your scaffold comparison",
        "",
        "[Complete illustrated report](report.pdf) · [First overview](report.svg)",
        "",
        "Selected members: " + (", ".join(report.selected_members) or "none; choose explicitly"),
        "",
        *retrieval_text(report),
        "## Technical evidence and individual outcomes",
        "",
        report.interpretation,
        "",
        "Report verification replays saved bounded authorities; rendering performs "
        "no new request execution, relaxation or selection.",
        "",
        "Shared requirements: " + ", ".join(report.shared_properties) + ".",
        "",
        "Search bounds: `" + json.dumps(report.upper_bounds, sort_keys=True) + "`.",
        "",
        "Editable pages: " + " · ".join(f"[{i}](pages/{i}.svg)" for i in range(1, page_count + 1)),
        "",
    ]
    if report.revision:
        md += [
            "## Explicit revision",
            "",
            f"{report.revision['source_member']} → {report.revision['target_member']}: "
            f"{report.revision['kind']}; prior outcome {report.revision['prior_status']}.",
            "[Original family and outcomes](family/history/parent/report.md)",
            "",
        ]
    for member in report.members:
        md += [
            f"## {member.name}",
            "",
            "Requested: " + describe_member(member) + ".",
            "",
            "Effective geometry domains: `"
            + json.dumps(member.effective_geometry, sort_keys=True)
            + "`.",
            "",
            f"Outcome: {member.status}; stage: {member.stage}; scope: {member.scope}.",
            "",
            "Local coverage: `" + json.dumps(member.local_coverage, sort_keys=True) + "`.",
            "",
        ]
        for diagnostic in member.preparation_constraints:
            if isinstance(diagnostic, dict):
                md += [
                    f"This selected preparation needs {diagnostic.get('requested')} "
                    f"nt but supplies {diagnostic.get('available')} nt. "
                    + str(diagnostic.get("message", "")),
                    "",
                ]
        if member.rejection_reasons:
            md += ["Recorded rejection reasons: " + ", ".join(member.rejection_reasons) + ".", ""]
        for c in member.choices:
            md += [
                f"Obtained: {c.geometry['loop_nt']}-nt loop; "
                f"{c.geometry['loop_side_paired_bp']}-bp loop-side extension; "
                f"{c.geometry['open_side_paired_positions']} open-side paired "
                f"positions; {c.geometry['stem_bp']}-bp stem.",
                "",
                f"Pictured state: hairpin {c.stage_role}. Requested endpoint: "
                f"{endpoint_label(ConstructionEndpoint(c.endpoint))}. Membership: "
                + ("selected" if c.selected else "not selected")
                + ".",
                "",
                f"[Whole molecule]({c.portrait}) · [Countable closing "
                f"region]({c.closing_drawing}) · "
                f"[Matched product stages]({c.stage_drawing}) · [Exact "
                f"preparation]({c.preparation})",
                "",
                f"Exact identity: `{c.source_result_id}` / `{c.materialized_realization_id}`.",
                "",
            ]
            if c.shared_property_differences:
                md += [
                    "Shared-property disagreement: `"
                    + json.dumps(c.shared_property_differences)
                    + "`.",
                    "",
                ]
    if report.comparisons:
        md += [
            "## Intended and accompanying differences",
            "",
            "The named baseline is a comparison reference, not a winning design. "
            "Whole comparisons are retained in summary.json.",
            "",
        ]
    for ordinal, comparison in enumerate(report.comparisons, start=1):
        assessment = comparison.molecular.assessment
        conserved = assessment.non_loop_sequences_conserved
        md += [
            f"### {comparison.baseline_member} → {comparison.member}",
            "",
            f"[Detailed correspondence drawing](details/comparison-{ordinal}.svg)",
            "",
            "What changes in my molecule: " + ", ".join(assessment.changed_scaffold_fields) + ".",
            "",
            "Non-loop sequences: "
            + ({True: "unchanged", False: "changed", None: "not assessed"}[conserved])
            + ".",
            "",
            "Coordinate movement is reported separately from sequence changes.",
            "",
            "What changes in making it — changed material roles: "
            + ", ".join(material_role_label(r) for r in comparison.molecular.changed_material_roles)
            + ".",
            "",
        ]
        for region in comparison.regions:
            if region.reference_sequence != region.observed_sequence or region.coordinates_changed:
                md += [
                    f"{region.region}: `{region.reference_sequence}` → "
                    f"`{region.observed_sequence}` (each 5\u2032→3\u2032); "
                    f"net length change {region.length_delta:+d} nt. Correspondence: "
                    f"{region.correspondence.replace('_', ' ')}. "
                    f"Coordinates: {region.reference_span} → {region.observed_span} (half-open).",
                    "",
                ]
        md += [
            "Repeated sequence can make the exact added/removed position ambiguous. "
            "Display alignment does not establish mutation history, causation or a minimal repair.",
            "",
        ]
    for edit in report.authored_edits:
        md += [
            f"## Authored alternative: {edit.source_member} → {edit.target_member}",
            "",
            "Requested changes: `" + json.dumps(edit.requested_changes) + "`.",
            "",
            "Effective-domain changes: `" + json.dumps(edit.effective_changes) + "`.",
            "",
            "An explicitly authored alternative, not a uniquely necessary repair. "
            "A failed continuation has no completed molecule to compare; its missing "
            "molecular differences are not zero. "
            "The target retains its own complete preparation and unresolved conditions.",
            "",
        ]
    md += [
        "Each preparation report lists its exact materials and terminal chemistry.",
        "",
        "Captured source inputs are preserved under family/ for provenance; "
        "regenerated report facts, drawings and exact preparation links above are "
        "the reading surface.",
        "",
    ]
    return "\n".join(md)

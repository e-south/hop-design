"""Render a typed comparison without deriving a second set of molecular differences."""

from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.projections.comparison import ConstructionComparisonProjection

from .report import _text

_MATERIAL_LABELS = {
    MaterialUseRole.SOURCE_SSDNA: "Source oligo",
    MaterialUseRole.SOURCE_MATERIALIZATION_FORWARD_PRIMER: "Source forward primer",
    MaterialUseRole.SOURCE_MATERIALIZATION_REVERSE_PRIMER: "Source reverse primer",
    MaterialUseRole.LIGATION_ADAPTER: "Adapter",
    MaterialUseRole.ENDPOINT_FORWARD_PRIMER: "Endpoint forward primer",
    MaterialUseRole.ENDPOINT_REVERSE_PRIMER: "Endpoint reverse primer",
}


def _material_changes(projection: ConstructionComparisonProjection) -> list[str]:
    changed = [_MATERIAL_LABELS[role] for role in projection.changed_material_roles]
    same = [_MATERIAL_LABELS[role] for role in projection.unchanged_material_roles]
    return [
        "Changed external oligo roles: " + (", ".join(changed) or "none") + ".",
        "Same sequence and terminal chemistry: " + (", ".join(same) or "none") + ".",
        "Roles present in only one preparation count as changed; shared oligos "
        "retain all roles in each CSV.",
    ]


def render_construction_comparison(projection: ConstructionComparisonProjection) -> str:
    """Render a property comparison, not a new route or molecular equivalence claim."""
    lines = [
        "# Compare selected constructions",
        "",
        "## What changes in my molecule",
        "",
        "Changed scaffold properties: "
        + (", ".join(projection.assessment.changed_scaffold_fields) or "none recorded")
        + ".",
        "Non-loop sequences: "
        + {True: "unchanged", False: "changed", None: "not assessed"}[
            projection.assessment.non_loop_sequences_conserved
        ]
        + ".",
        "Coordinate shifts are distinct from sequence changes.",
        "",
        "## What changes in making it",
        "",
        *_material_changes(projection),
        "",
        "Sequences are written 5-prime to 3-prime; intervals are zero-based and half-open. "
        "Same/changed compares each displayed property.",
        f"Composition coverage: left {projection.left.composition_status}; "
        f"right {projection.right.composition_status}.",
        "Local search coverage is recorded with each source result.",
        "",
        "| Property | Comparison | Left | Right |",
        "| --- | --- | --- | --- |",
    ]
    for prop in projection.properties:
        if not prop.field.startswith("preparation."):
            continue
        comparison = "changed" if prop.changed else "same"
        lines.append(
            f"| {prop.label} | {comparison} | {_text(str(prop.left))} | {_text(str(prop.right))} |"
        )
    lines.extend(
        [
            "",
            "Inspect each route for exact coordinates, pairing, bonds and lineage.",
            "",
            f"Left result: `{projection.left.source_result_id}`.",
            f"Left realization: `{projection.left.materialized_realization_id}`.",
            f"Right result: `{projection.right.source_result_id}`.",
            f"Right realization: `{projection.right.materialized_realization_id}`.",
        ]
    )
    return "\n".join(lines) + "\n"

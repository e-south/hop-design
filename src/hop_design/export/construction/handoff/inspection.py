"""Render the concise inspection of a typed, selected construction trajectory."""

from __future__ import annotations

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.projections import CompleteConstructionTrajectoryProjection

from .materials import external_material_uses, external_oligos
from .outcome import product_outcome_lines


def render_construction_inspection(projection: CompleteConstructionTrajectoryProjection) -> str:
    """Describe recorded facts through the same material reader as the oligo exports."""
    route = projection.realization
    reference = route.final_product.reference
    materials = external_material_uses(route)
    program = route.construction_program
    lines = [
        *product_outcome_lines(projection),
        "",
        f"Result: {projection.source_result_id}",
        f"Realization: {route.materialized_realization_id}",
        f"Source ssDNA: {route.source_preparation.source_ssdna.sequence_5prime}",
        f"Distinct external oligos: {len(external_oligos(route))}",
        f"External material roles: {len(materials)}",
    ]
    lines.extend(
        f"  {use.role.value}: {material.sequence_5prime} · "
        f"5-prime {material.five_prime_end.value} · 3-prime {material.three_prime_end.value}"
        for material, use in materials
    )
    lines.append(
        f"Molecular states: {len(program.states)} · transitions: {len(program.transitions)}"
    )
    if projection.source_partition_certificate is None:
        lines.append("Source-fragment removal: unresolved (no bound removal program)")
    else:
        lines.append("Source-fragment removal: verified")
    lines.extend(
        [
            f"Endpoint: {reference.endpoint.value} · {reference.topology}",
            f"Endpoint sequence: {reference.sequence}",
        ]
    )
    if reference.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        lines.extend(
            f"{end.product_end.capitalize()} cohesive end: {end.sequence} "
            f"(5-prime to 3-prime) · {end.overhang_end.value.replace('_', '-')} overhang"
            for end in route.final_product.cohesive_ends
        )
    else:
        lines.append("Cohesive ends: not generated for this endpoint")
    return "\n".join(lines)

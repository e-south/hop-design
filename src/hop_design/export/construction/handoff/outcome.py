"""Lead every selected handoff with the same verified product and flank facts."""

from hop_design.export.construction.labels import endpoint_label
from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete.clone.geometry import clone_payload_end_offsets
from hop_design.models.construction.projections import CompleteConstructionTrajectoryProjection
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget


def product_outcome_lines(projection: CompleteConstructionTrajectoryProjection) -> list[str]:
    """Read achieved geometry without substituting a preference for a required end."""
    route = projection.realization
    product = route.final_product
    lines = [
        f"Achieved product: {endpoint_label(product.reference.endpoint)}; "
        f"strand lengths {', '.join(str(len(s.sequence)) for s in product.strands)} nt.",
        "This selected route satisfies its bound molecular request in the model.",
    ]
    if product.reference.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        left, right = product.cohesive_ends
        offsets = clone_payload_end_offsets(
            ends=(left, right),
            encoding_start=product.design_projection.source_span.start.offset,
            payload_boundaries=route.design.payload_boundaries,
        )
        lines.extend(
            f"{end.product_end.capitalize()} cohesive end: {end.sequence} "
            f"(5-prime to 3-prime on its own protruding strand); "
            f"{end.overhang_end.value.replace('_', ' ')} overhang."
            for end in (left, right)
        )
        lines.append(
            f"Paired flank distances: left {offsets[0]} bp; right {offsets[1]} bp "
            "between the paired edge of each end and its payload boundary; overhang excluded."
        )
    else:
        lines.append("Cohesive ends and paired release-flank distances: not generated here.")
    closing = route.foldback_authority.local_realization.achieved_geometry
    assert isinstance(closing, FoldbackTarget)
    lines.append(
        f"Closing flank: paired arm {closing.annealing_arm_length_bp} bp; "
        f"unpaired cap {closing.loop_length_nt} nt; join displacement "
        f"{closing.junction_offset_nt} nt."
    )
    if route.basal_authority is not None:
        basal = route.basal_authority.local_realization.achieved_geometry
        assert isinstance(basal, BasalTarget)
        lines.append(f"Attachment flank: nick displacement {basal.nick_offset_nt} nt.")
    lines.extend(
        [
            "Laboratory stock: not supplied. Enzyme reaction prerequisites: not evaluated.",
            "Association, ligation, primer performance and physical recovery require "
            "experimental qualification; destination compatibility is not evaluated.",
        ]
    )
    return lines

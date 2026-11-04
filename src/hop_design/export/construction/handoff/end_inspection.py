"""Read one oriented cohesive end's recorded coordinates and material origins."""

from __future__ import annotations

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.projections import CompleteConstructionTrajectoryProjection
from hop_design.models.molecular_state import (
    CohesiveEnd,
    MaterialBaseLineage,
    MolecularStrand,
    StrandEnd,
)


def end_lineage(end: CohesiveEnd, strand: MolecularStrand) -> tuple[MaterialBaseLineage, ...]:
    """Read the terminal lineage slice on the verified protruding strand."""
    length = len(end.sequence)
    return (
        strand.lineage[:length]
        if end.overhang_end is StrandEnd.FIVE_PRIME
        else strand.lineage[-length:]
    )


def render_end_inspection(
    projection: CompleteConstructionTrajectoryProjection,
    product_end: str,
    *,
    base_index: int | None,
) -> str:
    """Select terminal lineage by strand identity and polarity, never a sequence match."""
    if product_end not in ("left", "right"):
        raise ValueError("Product end must be 'left' or 'right'.")
    route = projection.realization
    product = route.final_product
    if product.reference.endpoint is not ConstructionEndpoint.CLONE_READY_DUPLEX:
        raise ValueError("End inspection requires a released duplex product.")
    end = next(item for item in product.cohesive_ends if item.product_end == product_end)
    if base_index is not None and (
        type(base_index) is not int or not 0 <= base_index < len(end.sequence)
    ):
        raise ValueError(f"Base index must be an integer from 0 to {len(end.sequence) - 1}.")
    strand = next(s for s in product.strands if s.strand_id == end.protruding_strand_id)
    origins = end_lineage(end, strand)
    indexes = range(len(end.sequence)) if base_index is None else (base_index,)
    materials = {
        use.use_id: (material, use)
        for material, use in zip(route.materials, route.material_uses, strict=True)
    }
    lines = [
        f"Result: {projection.source_result_id}",
        f"Realization: {route.materialized_realization_id}",
        f"{product_end.capitalize()} cohesive end: {end.sequence} (5-prime to 3-prime)",
        f"Protruding strand: {strand.strand_id} · "
        f"{end.overhang_end.value.replace('_', '-')} overhang",
        "Indexes: zero-based; end and material indexes follow "
        "their own 5-prime to 3-prime sequences",
        f"Release cuts: primary={end.primary_cut.offset}; "
        f"complementary={end.complementary_cut.offset} "
        "(boundaries on the pre-release primary-strand coordinate axis)",
    ]
    selected_uses: list[str] = []
    for index in indexes:
        origin = origins[index]
        material, use = materials[origin.origin_id]
        lines.append(
            f"  end[{index}] {end.sequence[index]} <- "
            f"{use.role.value}[{origin.origin_index}] "
            f"{material.sequence_5prime[origin.origin_index]}"
            f" · product[{origin.product_index}]"
        )
        if origin.origin_id not in selected_uses:
            selected_uses.append(origin.origin_id)
    for use_id in selected_uses:
        material, use = materials[use_id]
        lines.extend(
            [
                f"Material: {use.role.value} · {use.route_entry.value}",
                f"  Use: {use.use_id}",
                f"  Identity: {material.material_id}",
                f"  Chemistry: 5-prime {material.five_prime_end.value}; "
                f"3-prime {material.three_prime_end.value}",
            ]
        )
    lines.append(
        "Origins describe this selected route; they do not establish independent end choices."
    )
    return "\n".join(lines)

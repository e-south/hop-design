"""Match a hairpin to its actual endpoint using recorded base lineage and contacts."""

from typing import Literal

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection
from hop_design.models.construction.projections.product_stages import (
    ProductDiagramBase,
    ProductStageProjection,
)
from hop_design.models.construction.projections.trajectory import (
    CompleteConstructionTrajectoryProjection,
)

_Region = Literal["open", "stem", "closing", "unmapped"]


def project_product_stages(
    portrait: HairpinPortraitProjection,
    trajectory: CompleteConstructionTrajectoryProjection,
) -> ProductStageProjection:
    product = trajectory.realization.final_product
    if portrait.stage_role == "endpoint":
        return ProductStageProjection(
            hairpin_state_id=portrait.state.state_id,
            hairpin_role=portrait.stage_role,
            endpoint=portrait.endpoint,
            product=product,
            bases=(),
            pairing_columns=(),
        )

    def unavailable(reason: str) -> ProductStageProjection:
        return ProductStageProjection(
            hairpin_state_id=portrait.state.state_id,
            hairpin_role=portrait.stage_role,
            endpoint=portrait.endpoint,
            product=product,
            bases=(),
            pairing_columns=(),
            unavailable_reason=reason,
        )

    if len(product.strands) != 2 or not product.pairings:
        return unavailable("Compact view requires a paired duplex; exact product is retained.")
    regions: dict[tuple[str, int], set[_Region]] = {}
    for base in portrait.state.molecules[0].lineage:
        i = base.product_index
        region: _Region = "open"
        if portrait.stem_primary_span.contains_index(i) or portrait.stem_return_span.contains_index(
            i
        ):
            region = "stem"
        elif portrait.stem_primary_span.end.offset <= i < portrait.stem_return_span.start.offset:
            region = "closing"
        regions.setdefault((base.origin_id, base.origin_index), set()).add(region)
    top, bottom = product.strands
    pairs = []
    for pair in product.pairings:
        if pair.left_strand_id == top.strand_id and pair.right_strand_id == bottom.strand_id:
            pairs.append((pair.left_index, pair.right_index))
        elif pair.right_strand_id == top.strand_id and pair.left_strand_id == bottom.strand_id:
            pairs.append((pair.right_index, pair.left_index))
        else:
            raise ValueError("Product pairing must connect its two recorded strands.")
    sums = {a + b for a, b in pairs}
    if len(sums) != 1:
        return unavailable(
            "Compact view needs a single antiparallel frame; exact product is retained."
        )
    reverse_origin = sums.pop()
    bases = []
    for strand_index, strand in enumerate(product.strands):
        for base in strand.lineage:
            matches = regions.get((base.origin_id, base.origin_index), set())
            bases.append(
                ProductDiagramBase(
                    strand_index=0 if strand_index == 0 else 1,
                    product_index=base.product_index,
                    column=base.product_index
                    if strand_index == 0
                    else reverse_origin - base.product_index,
                    base=strand.sequence[base.product_index],
                    region=next(iter(matches)) if len(matches) == 1 else "unmapped",
                )
            )
    return ProductStageProjection(
        hairpin_state_id=portrait.state.state_id,
        hairpin_role=portrait.stage_role,
        endpoint=portrait.endpoint,
        product=product,
        bases=tuple(bases),
        pairing_columns=tuple(a for a, _ in pairs),
    )

"""Project literal folded sequences from existing verified portraits, without new chemistry."""

from typing import Any

from hop_design.models.construction.complete.product import MaterializedFinalProduct
from hop_design.models.construction.projections.folded_sequence import FoldedSequenceView
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..comparison_regions import region_spans
from .sequence_difference import compare_sequence_region


def folded_sequence_view(
    portrait: HairpinPortraitProjection,
    reference: HairpinPortraitProjection,
    *,
    label: str,
    reference_label: str,
    materials: dict[str, Any],
    reference_materials: dict[str, Any],
    endpoint: MaterializedFinalProduct,
    reference_endpoint: MaterializedFinalProduct,
) -> FoldedSequenceView:
    spans, reference_spans = region_spans(portrait), region_spans(reference)
    sequence, original = portrait.state.molecules[0].sequence, reference.state.molecules[0].sequence
    roles = sorted(set(materials) | set(reference_materials))

    def paired_regions(p: HairpinPortraitProjection) -> list[tuple[str, int, str, int]]:
        regions = region_spans(p)

        def position(index: int) -> tuple[str, int]:
            return next((r, index - a) for r, (a, b) in regions.items() if a <= index < b)

        return [
            (*position(pair.left_index), *position(pair.right_index)) for pair in p.ordered_contacts
        ]

    return FoldedSequenceView(
        label=label,
        reference_label=reference_label,
        portrait=portrait,
        regions=tuple(
            compare_sequence_region(region, original[c:d], sequence[a:b], (c, d), (a, b))
            for region, (a, b) in spans.items()
            for c, d in (reference_spans[region],)
        ),
        changed_material_roles=tuple(
            r for r in roles if materials.get(r) != reference_materials.get(r)
        ),
        unchanged_material_roles=tuple(
            r for r in roles if materials.get(r) == reference_materials.get(r)
        ),
        pairing_relationships_unchanged=paired_regions(portrait) == paired_regions(reference),
        endpoint_product=endpoint,
        endpoint_sequence_differences=tuple(
            compare_sequence_region(
                f"strand_{i + 1}",
                a.sequence,
                b.sequence,
                (0, len(a.sequence)),
                (0, len(b.sequence)),
            )
            for i, (a, b) in enumerate(
                zip(reference_endpoint.strands, endpoint.strands, strict=True)
            )
        ),
    )

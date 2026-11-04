"""Project decision facts from a verified route, never by adding local overheads."""

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.materials import external_oligos
from hop_design.models.construction.projections.overhead.complete import (
    AddedRegion,
    ConstructionCost,
    OligoOrder,
)
from hop_design.models.molecular_state import EndChemistry

from ...comparisons.controls import stage_contexts


def construction_cost(route: MaterializedConstructionRealization) -> ConstructionCost:
    hairpin = describe_hairpin(route)
    strand = hairpin.state.molecules[0]
    stem = strand.sequence[
        hairpin.stem_primary_span.start.offset : hairpin.stem_primary_span.end.offset
    ]
    product = route.final_product
    regions = []
    if product.endpoint_sequence_fate_spans:
        strands, _, region_labels = stage_contexts(route)["endpoint"]
        locations = dict(
            zip(("top", "bottom"), zip(strands, region_labels, strict=True), strict=True)
        )
        for span in product.endpoint_sequence_fate_spans:
            if span.fate.value != "payload":
                molecule, names = locations[span.endpoint_strand.value]
                start, end = span.endpoint_span.start.offset, span.endpoint_span.end.offset
                while start < end:
                    stop = start + 1
                    while stop < end and names[stop] == names[start]:
                        stop += 1
                    regions.append(
                        AddedRegion(
                            strand=span.endpoint_strand.value,
                            strand_id=molecule.strand_id,
                            start=start,
                            end=stop,
                            region=names[start] or "unmapped_region",
                            fate=span.fate.value,
                        )
                    )
                    start = stop
        counts = {"top": 0, "bottom": 0}
    else:
        # The exact joined hairpin has two supplied stem spans. Everything else
        # is added sequence, including unpaired handles; paired positions are not nt.
        a, b = hairpin.stem_primary_span, hairpin.stem_return_span
        for start, end, name in (
            (0, a.start.offset, "open_side_primary"),
            (a.end.offset, hairpin.loop_span.start.offset, "loop_side_primary"),
            (hairpin.loop_span.start.offset, hairpin.loop_span.end.offset, "loop"),
            (hairpin.loop_span.end.offset, b.start.offset, "loop_side_return"),
            (b.end.offset, len(strand.sequence), "open_side_return"),
        ):
            if end > start:
                regions.append(
                    AddedRegion(
                        strand=strand.strand_id,
                        strand_id=strand.strand_id,
                        start=start,
                        end=end,
                        region=name,
                        fate="retained_construction",
                    )
                )
        counts = {strand.strand_id: 0}
    for region in regions:
        counts[region.strand] += region.end - region.start
    orders = tuple(
        OligoOrder(
            material_id=material.material_id,
            length_nt=len(material.sequence_5prime),
            roles=tuple(use.role.value for use in uses),
            five_prime_end=material.five_prime_end,
            three_prime_end=material.three_prime_end,
            modifications=tuple(
                f"{end} phosphate"
                for end, chemistry in (
                    ("5-prime", material.five_prime_end),
                    ("3-prime", material.three_prime_end),
                )
                if chemistry is EndChemistry.PHOSPHATE
            ),
        )
        for material, uses in external_oligos(route)
    )
    roles = sum(len(order.roles) for order in orders)
    added = ", ".join(
        f"{name if len(counts) > 1 else 'hairpin'}: {n} nt" for name, n in counts.items()
    )
    lines = [
        f"Preserved stem arm: {len(stem)} nt. Added DNA in the selected product — {added}.",
        f"{len(orders)} distinct oligo orders covering {roles} roles; "
        f"{sum(o.length_nt for o in orders)} nt to order.",
    ]
    for order in orders:
        labels = ", ".join(
            role.replace("_", " ").replace("materialization ", "") for role in order.roles
        )
        if len(order.roles) > 1:
            lines.append(f"Shared oligo: {labels}.")
        if order.modifications:
            lines.append(f"{labels.capitalize()}: {', '.join(order.modifications)}.")
    return ConstructionCost(
        materialized_realization_id=route.materialized_realization_id,
        endpoint=product.reference.endpoint.value,
        state_id=route.construction_program.states[-1].state_id,
        stem_arm=stem,
        added_nt_by_strand=counts,
        added_regions=tuple(regions),
        distinct_orders=len(orders),
        material_roles=roles,
        ordered_nt=sum(o.length_nt for o in orders),
        orders=orders,
        achieved_ends={
            end.product_end: {
                "word": end.sequence,
                "polarity": end.overhang_end.value,
                "strand_id": end.protruding_strand_id,
            }
            for end in product.cohesive_ends
        },
        summary_lines=tuple(lines),
    )

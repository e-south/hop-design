"""Small plotting facts derived once from exact complete construction authority."""

from typing import Any

from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.materials import external_oligos

from ..discovery.molecules import molecular_identities, preparation_materials
from ..navigation.molecular_descriptor import molecular_descriptor
from ..projections.interfaces import preparation_interface
from ..public import ConstructionCompilation, VerifiedConstructionBundle
from ..variants.parameters.facts import parameter_facts


def witness_projection(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
    request: dict[str, Any],
    identity: str,
) -> dict[str, Any]:
    route = next(
        r
        for r in receipt._verified_source().result.realizations
        if r.materialized_realization_id == identity
    )
    hairpin = describe_hairpin(route)
    interface = preparation_interface(route, request)
    endpoint_non_payload: dict[str, int] = {}
    for span in route.final_product.endpoint_sequence_fate_spans:
        strand = span.endpoint_strand.value
        endpoint_non_payload.setdefault(strand, 0)
        if span.fate.value != "payload":
            endpoint_non_payload[strand] += span.endpoint_span.length.value
    descriptor = molecular_descriptor(route)
    return {
        "materialized_realization_id": identity,
        "molecular_identity": molecular_identities(receipt, identity),
        "molecular_descriptor_schema": "hop.molecular-descriptor/v2"
        if descriptor.retained_terminal_bases is not None
        else "hop.molecular-descriptor/v1",
        "molecular_descriptor": descriptor.model_dump(mode="json"),
        "values": {
            **parameter_facts(route, request),
            **hairpin.scaffold_dimensions,
            "loop_word": hairpin.state.molecules[0].sequence[
                hairpin.loop_span.start.offset : hairpin.loop_span.end.offset
            ],
            **{
                f"{side}_gap": gap
                for side, gap in interface["interface"]["achieved_distances_bp"].items()
            },
        },
        "methods": interface["methods"],
        "material_roles": preparation_materials(receipt, identity),
        "overhead": {
            "foldback_local_retained_nt": (
                route.foldback_authority.retained_overhead.retained_overhead_nt
            ),
            "basal_local_retained_nt": route.basal_authority.retained_overhead.retained_overhead_nt
            if route.basal_authority is not None
            else None,
            "hairpin_non_stem_nt": len(hairpin.state.molecules[0].sequence) - 2 * hairpin.stem_bp,
            "endpoint_non_payload_nt_by_strand": endpoint_non_payload,
            "ordered_unique_oligo_nt": sum(
                len(m.sequence_5prime) for m, _ in external_oligos(route)
            ),
        },
    }

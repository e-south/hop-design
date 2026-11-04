"""Project comparison features from recorded anatomy, never a predicted folding state."""

from hop_design.models.construction.complete.clone.geometry import clone_payload_end_offsets
from hop_design.models.construction.complete.pcr.authority import PrimerExtensionAuthority
from hop_design.models.construction.hairpin_geometry import HairpinArchitecture, describe_hairpin
from hop_design.models.construction.projections.route_view import MolecularRouteView
from hop_design.models.construction.variants.similarity import SHAPE_KEYS, MolecularDescriptor
from hop_design.models.molecular_state import MaterialBaseLineage
from hop_design.serialization import canonical_json_bytes

from ..projections.inspection_lineage import ancestry_resolver


def _retained_terminals(
    route: MolecularRouteView, anatomy: HairpinArchitecture
) -> dict[str, tuple[str, ...]] | None:
    """Trace each hairpin tail base into either strand of the released insert.

    Copies share an ancestral base but may have opposite strand orientation.
    Primer annealing segments preserve template dependence even where the
    physical material comes from a primer. Independent primer extensions do not.
    Sequence similarity alone never establishes this relationship.
    """
    if route.final_product.reference.endpoint.value != "clone_ready_duplex":
        return None
    final = [s for s in route.construction_program.states if s.phase.value == "clone_ready_duplex"]
    if len(final) != 1:
        raise ValueError("Terminal retention requires exactly one released insert state.")
    resolve = ancestry_resolver(route)
    molecule = anatomy.state.molecules[0]
    copies = [
        t.pcr_authority
        for t in route.construction_program.transitions
        if isinstance(t.pcr_authority, PrimerExtensionAuthority)
    ]
    if len(copies) != 1 or copies[0].pre_state_id != anatomy.state.state_id:
        raise ValueError("Terminal retention requires the recorded hairpin copying authority.")
    copying = copies[0]
    primer_templates = {}
    for primer, use, reverse in (
        (copying.forward_primer, copying.forward_primer_use, False),
        (copying.reverse_primer, copying.reverse_primer_use, True),
    ):
        handle = len(primer.oligo.sequence_5prime) - primer.annealing_length_nt
        for i in range(primer.annealing_length_nt):
            template_index = len(molecule.sequence) - 1 - i if reverse else i
            primer_templates[use.use_id, handle + i] = molecule.lineage[template_index]

    def origin_key(base: MaterialBaseLineage) -> tuple[str, int]:
        base = primer_templates.get((base.origin_id, base.origin_index), base)
        origin, _, index = resolve(base)
        return origin, index

    origins = {origin_key(b) for m in final[0].molecules for b in m.lineage}
    return {
        side: tuple(molecule.sequence[b.product_index] for b in lineage if origin_key(b) in origins)
        for side, lineage in (
            ("five_prime", molecule.lineage[: anatomy.paired_primary_span.start.offset]),
            ("three_prime", molecule.lineage[anatomy.paired_return_span.end.offset :]),
        )
    }


def molecular_descriptor(route: MolecularRouteView) -> MolecularDescriptor:
    anatomy = describe_hairpin(route)
    lo, hi = anatomy.stem_primary_span.start.offset, anatomy.stem_primary_span.end.offset
    sequence = anatomy.state.molecules[0].sequence
    shape = {key: getattr(anatomy, key) for key in SHAPE_KEYS}
    ends = tuple(sorted(route.final_product.cohesive_ends, key=lambda end: end.product_end))
    interfaces = None
    if ends:
        if len(ends) != 2:
            raise ValueError("Molecular similarity requires both receiving interfaces.")
        gaps = clone_payload_end_offsets(
            ends=(ends[0], ends[1]),
            encoding_start=route.final_product.design_projection.source_span.start.offset,
            payload_boundaries=route.design.payload_boundaries,
        )
        interfaces = {}
        for end, gap in zip(ends, gaps, strict=True):
            shape[f"{end.product_end}_gap"] = gap
            interfaces[f"{end.product_end}_word"] = end.sequence
            interfaces[f"{end.product_end}_polarity"] = end.overhang_end.value
    contacts = anatomy.ordered_contacts
    return MolecularDescriptor.model_validate_json(
        canonical_json_bytes(
            {
                "identity": route.materialized_realization_id,
                "stem": route.design.payload_sequence,
                "endpoint": route.final_product.reference.endpoint.value,
                "shape": shape,
                "sequences": {
                    "loop": list(
                        sequence[anatomy.loop_span.start.offset : anatomy.loop_span.end.offset]
                    ),
                    "basal_pairs": [
                        (p.left_base, p.right_base, p.kind.value)
                        for p in contacts
                        if p.left_index < lo
                    ],
                    "foldback_pairs": [
                        (p.left_base, p.right_base, p.kind.value)
                        for p in contacts
                        if p.left_index >= hi
                    ],
                },
                "interfaces": interfaces,
                **(
                    {"retained_terminal_bases": retained}
                    if (retained := _retained_terminals(route, anatomy)) is not None
                    else {}
                ),
            }
        )
    )

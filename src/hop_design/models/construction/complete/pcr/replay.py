"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/replay.py

Replays exact adapter and primer-extension molecular transformations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    MolecularStrand,
    StrandPairObservation,
)
from hop_design.models.physical import classify_literal_pair
from hop_design.models.sequence import reverse_complement_iupac

from ..state import ConstructionState
from .authority import (
    AdapterAnnealingAuthority,
    AdapterLigationAuthority,
    EndpointSequenceFate,
    MaterialFunction,
    PrimerExtensionAuthority,
)
from .products import pcr_products, validate_material_function_spans


def _route_material_functions(
    template: MolecularStrand,
    authority: PrimerExtensionAuthority,
) -> dict[str, MaterialFunction]:
    runs: list[tuple[str, LineageStrand]] = []
    for item in template.lineage:
        identity = (item.origin_id, item.origin_strand)
        if not runs or runs[-1] != identity:
            runs.append(identity)
    expected_strands = (
        LineageStrand.PRIMARY,
        LineageStrand.COMPLEMENTARY,
        LineageStrand.PRIMARY,
    )
    if len(runs) != 3 or tuple(strand for _, strand in runs) != expected_strands:
        raise ValueError("PCR template lineage must preserve exact route material roles.")
    source_reference, source_complement, adapter = (material_id for material_id, _ in runs)
    material_ids = (
        source_reference,
        source_complement,
        adapter,
        authority.forward_primer.material_id,
        authority.reverse_primer.material_id,
    )
    if len(set(material_ids)) != len(MaterialFunction):
        raise ValueError("PCR route material roles must bind distinct exact materials.")
    return dict(zip(material_ids, MaterialFunction, strict=True))


def _validate_adapter_annealing(
    authority: AdapterAnnealingAuthority,
    pre_state: ConstructionState,
    post_state: ConstructionState,
) -> None:
    if len(pre_state.molecules) != 1 or len(post_state.molecules) != 2:
        raise ValueError("Adapter annealing requires one hairpin and one adapter strand.")
    hairpin, adapter = post_state.molecules
    if hairpin != pre_state.molecules[0]:
        raise ValueError("Adapter annealing must preserve the exact closed hairpin.")
    material = authority.adapter
    if (
        adapter.sequence != material.sequence_5prime
        or adapter.five_prime_end is not material.five_prime_end
        or adapter.three_prime_end is not material.three_prime_end
        or any(item.origin_id != material.material_id for item in adapter.lineage)
    ):
        raise ValueError("Adapter strand must replay its exact declared material.")
    target = set(range(authority.hairpin_span.start.offset, authority.hairpin_span.end.offset))
    retained = tuple(
        pair
        for pair in pre_state.pairings
        if not (pair.left_strand_id == hairpin.strand_id and pair.left_index in target)
        and not (pair.right_strand_id == hairpin.strand_id and pair.right_index in target)
    )
    if post_state.pairings != (*retained, *authority.pairings):
        raise ValueError("Adapter annealing must preserve and replace exact associations.")
    if post_state.formed_bonds != pre_state.formed_bonds:
        raise ValueError("Adapter annealing cannot change covalent bonds.")


def _validate_adapter_ligation(
    authority: AdapterLigationAuthority,
    pre_state: ConstructionState,
    post_state: ConstructionState,
) -> None:
    if len(pre_state.molecules) != 2 or post_state.molecules != (authority.product,):
        raise ValueError("Adapter ligation must produce its one exact declared strand.")
    hairpin, adapter = pre_state.molecules
    material = authority.adapter
    if (
        authority.bond.upstream_strand_id != hairpin.strand_id
        or authority.bond.downstream_strand_id != adapter.strand_id
        or hairpin.three_prime_end is not EndChemistry.HYDROXYL
        or adapter.five_prime_end is not EndChemistry.PHOSPHATE
    ):
        raise ValueError("Adapter ligation requires hairpin 3-prime OH and adapter 5-prime P.")
    if (
        adapter.sequence != material.sequence_5prime
        or adapter.five_prime_end is not material.five_prime_end
        or adapter.three_prime_end is not material.three_prime_end
        or any(item.origin_id != material.material_id for item in adapter.lineage)
    ):
        raise ValueError("Adapter ligation must bind the exact pre-state adapter material.")
    expected_lineage = tuple(
        item.model_copy(update={"product_index": index})
        for index, item in enumerate((*hairpin.lineage, *adapter.lineage))
    )
    product = authority.product
    if (
        product.sequence != hairpin.sequence + adapter.sequence
        or product.lineage != expected_lineage
        or product.five_prime_end is not hairpin.five_prime_end
        or product.three_prime_end is not adapter.three_prime_end
    ):
        raise ValueError("Adapter-ligated product must replay exact sequence and lineage.")
    expected_bonds = (
        *(
            item.model_copy(update={"product_strand_id": product.strand_id})
            for item in pre_state.formed_bonds
        ),
        post_state.formed_bonds[-1].model_copy(
            update={"bond": authority.bond, "product_strand_id": product.strand_id}
        ),
    )
    if post_state.formed_bonds != expected_bonds:
        raise ValueError(
            "Adapter ligation must preserve pre-existing bonds and add its declared bond."
        )
    offsets = {hairpin.strand_id: 0, adapter.strand_id: len(hairpin.sequence)}
    expected_pairings = tuple(
        pair.model_copy(
            update={
                "left_strand_id": product.strand_id,
                "right_strand_id": product.strand_id,
                "left_index": pair.left_index + offsets[pair.left_strand_id],
                "right_index": pair.right_index + offsets[pair.right_strand_id],
            }
        )
        for pair in pre_state.pairings
    )
    if post_state.pairings != expected_pairings:
        raise ValueError("Adapter ligation must preserve exact remapped pairings.")


def _validate_primer_extension(
    authority: PrimerExtensionAuthority,
    pre_state: ConstructionState,
    post_state: ConstructionState,
) -> None:
    if len(pre_state.molecules) != 1 or post_state.molecules != authority.products:
        raise ValueError("Primer extension must produce its exact ordered duplex strands.")
    template = pre_state.molecules[0]
    top, bottom = authority.products
    forward, reverse = authority.forward_primer, authority.reverse_primer
    if (
        forward.three_prime_end is not EndChemistry.HYDROXYL
        or reverse.three_prime_end is not EndChemistry.HYDROXYL
    ):
        raise ValueError("PCR primers require exact three-prime hydroxyl chemistry.")
    if top.sequence != template.sequence or bottom.sequence != reverse_complement_iupac(
        template.sequence
    ):
        raise ValueError("Primer extension products must be exact reverse complements.")
    if post_state.pairings != authority.pairings or len(post_state.pairings) != len(top.sequence):
        raise ValueError("PCR duplex authority must cover every exact base pair.")
    expected_pairings = tuple(
        StrandPairObservation(
            left_strand_id=top.strand_id,
            right_strand_id=bottom.strand_id,
            left_index=index,
            right_index=len(top.sequence) - 1 - index,
            left_base=base,
            right_base=bottom.sequence[len(top.sequence) - 1 - index],
            kind=classify_literal_pair(
                left_base=base,
                right_base=bottom.sequence[len(top.sequence) - 1 - index],
            ),
        )
        for index, base in enumerate(top.sequence)
    )
    if authority.pairings != expected_pairings:
        raise ValueError("PCR duplex must use canonical antiparallel pair order.")
    if post_state.formed_bonds:
        raise ValueError("PCR duplex products cannot inherit precursor ligation bonds.")
    function_by_role = {
        item.function: item.material_id for item in authority.material_function_spans
    }
    if function_by_role[MaterialFunction.FORWARD_PRIMER] != forward.material_id or (
        function_by_role[MaterialFunction.REVERSE_PRIMER] != reverse.material_id
    ):
        raise ValueError("PCR material-function spans must bind both exact primers.")
    validate_material_function_spans(
        records=authority.material_function_spans,
        function_by_material=_route_material_functions(template, authority),
        top=top,
        bottom=bottom,
    )
    fwd_length = len(forward.sequence_5prime)
    rev_length = len(reverse.sequence_5prime)
    if top.sequence[:fwd_length] != forward.sequence_5prime or (
        bottom.sequence[:rev_length] != reverse.sequence_5prime
    ):
        raise ValueError("PCR products must preserve both exact primer sequences.")
    expected_bindings = (
        (
            forward.material_id,
            f"{template.strand_id}-derived-complement",
            len(template.sequence) - fwd_length,
            len(template.sequence),
        ),
        (
            reverse.material_id,
            template.strand_id,
            len(template.sequence) - rev_length,
            len(template.sequence),
        ),
    )
    observed_bindings = tuple(
        (
            item.primer_id,
            item.template_strand_id,
            item.template_span.start.offset,
            item.template_span.end.offset,
        )
        for item in authority.bindings
    )
    if observed_bindings != expected_bindings or any(
        item.orientation is not BindingOrientation.REVERSE_COMPLEMENT_5TO3
        for item in authority.bindings
    ):
        raise ValueError("PCR primer bindings must replay exact template boundaries.")
    if (
        reverse.sequence_5prime != reverse_complement_iupac(template.sequence[-rev_length:])
        or forward.sequence_5prime != template.sequence[:fwd_length]
    ):
        raise ValueError("PCR primer sequences must match their exact template sites.")
    if authority.products != pcr_products(template, forward, reverse):
        raise ValueError("PCR product lineage must replay primer and template origins.")
    if EndpointSequenceFate.PAYLOAD not in {
        item.fate for item in authority.endpoint_sequence_fate_spans
    }:
        raise ValueError("PCR endpoint fate must identify the exact payload span.")


def validate_pcr_transition(
    *,
    kind: object,
    authority: object,
    pre_state: ConstructionState,
    post_state: ConstructionState,
) -> None:
    """Dispatch one PCR-only transition to its exact molecular replay."""
    kind_value = getattr(kind, "value", kind)
    if kind_value == "annealing" and isinstance(authority, AdapterAnnealingAuthority):
        _validate_adapter_annealing(authority, pre_state, post_state)
        return
    if kind_value == "ligation" and isinstance(authority, AdapterLigationAuthority):
        _validate_adapter_ligation(authority, pre_state, post_state)
        return
    if kind_value == "primer_extension" and isinstance(authority, PrimerExtensionAuthority):
        _validate_primer_extension(authority, pre_state, post_state)
        return
    raise ValueError("PCR transition kind must match its exact molecular authority.")


__all__ = ["validate_pcr_transition"]

"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/authority.py

Derives and replays exact source-ssDNA copying into one construction duplex.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import _content_id
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_replay import observe_pair, strand_from_sequence
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    PrimerBinding,
)
from hop_design.models.sequence import reverse_complement_iupac

from ..material import (
    ExactConstructionMaterial,
    MaterialOrigin,
    PcrPrimer,
    ProducedMaterialBinding,
)
from ..materials import derived_source_material_id
from ..pcr.products import pcr_products, validate_pcr_annealing_spans
from ..state import ConstructionState, ConstructionStatePhase


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _overlaps(left: Span, right: Span) -> bool:
    return left.start.offset < right.end.offset and right.start.offset < left.end.offset


def _validate_inputs(
    *,
    source_ssdna: ExactConstructionMaterial,
    forward_primer: PcrPrimer,
    reverse_primer: PcrPrimer,
    payload_source_span: Span,
) -> None:
    material_ids = (
        source_ssdna.material_id,
        forward_primer.oligo.material_id,
        reverse_primer.oligo.material_id,
    )
    if len(set(material_ids)) != len(material_ids):
        raise ValueError("Source preparation requires distinct material ids.")
    if (
        forward_primer.oligo.three_prime_end is not EndChemistry.HYDROXYL
        or reverse_primer.oligo.three_prime_end is not EndChemistry.HYDROXYL
    ):
        raise ValueError("Source PCR primers require exact three-prime hydroxyl chemistry.")
    if forward_primer.five_prime_handle or reverse_primer.five_prime_handle:
        raise ValueError(
            "Source PCR five-prime handles require an explicit template-to-product map."
        )
    source_length = len(source_ssdna.sequence_5prime)
    validate_pcr_annealing_spans(source_length, forward_primer, reverse_primer)
    if forward_primer.annealing_sequence != source_ssdna.sequence_5prime[
        : forward_primer.annealing_length_nt
    ]:
        raise ValueError("Source PCR forward primer must match the source prefix.")
    if reverse_primer.annealing_sequence != reverse_complement_iupac(
        source_ssdna.sequence_5prime[-reverse_primer.annealing_length_nt :]
    ):
        raise ValueError("Source PCR reverse primer must reverse-complement the source suffix.")
    if (
        payload_source_span.length.value == 0
        or payload_source_span.end.offset > source_length
    ):
        raise ValueError("Source payload span must be nonempty and lie inside the source ssDNA.")
    primer_source_spans = (
        _span(0, forward_primer.annealing_length_nt),
        _span(source_length - reverse_primer.annealing_length_nt, source_length),
    )
    if any(_overlaps(span, payload_source_span) for span in primer_source_spans):
        raise ValueError("Source PCR primer annealing must remain outside the payload.")


def _derived_content(
    *,
    source_ssdna: ExactConstructionMaterial,
    forward_primer: PcrPrimer,
    reverse_primer: PcrPrimer,
    payload_source_span: Span,
) -> dict[str, object]:
    _validate_inputs(
        source_ssdna=source_ssdna,
        forward_primer=forward_primer,
        reverse_primer=reverse_primer,
        payload_source_span=payload_source_span,
    )
    template = strand_from_sequence(
        strand_id="source-ssdna-template",
        sequence=source_ssdna.sequence_5prime,
        five_prime_end=source_ssdna.five_prime_end,
        three_prime_end=source_ssdna.three_prime_end,
        origin_id=source_ssdna.material_id,
        origin_strand=LineageStrand.PRIMARY,
        origin_indexes=range(len(source_ssdna.sequence_5prime)),
    )
    top, bottom = pcr_products(
        template,
        forward_primer,
        reverse_primer,
        top_strand_id="source-duplex-top",
        bottom_strand_id="source-duplex-bottom",
    )
    source_length = len(source_ssdna.sequence_5prime)
    bindings = (
        PrimerBinding(
            binding_id="source-preparation-forward-binding",
            primer_id=forward_primer.oligo.material_id,
            template_strand_id=bottom.strand_id,
            template_span=_span(
                source_length - forward_primer.annealing_length_nt,
                source_length,
            ),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
        PrimerBinding(
            binding_id="source-preparation-reverse-binding",
            primer_id=reverse_primer.oligo.material_id,
            template_strand_id=top.strand_id,
            template_span=_span(
                source_length - reverse_primer.annealing_length_nt,
                source_length,
            ),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
    )
    pairings = tuple(
        observe_pair(
            left_strand_id=top.strand_id,
            right_strand_id=bottom.strand_id,
            left_index=index,
            right_index=source_length - 1 - index,
            left_base=base,
            right_base=bottom.sequence[source_length - 1 - index],
        )
        for index, base in enumerate(top.sequence)
    )
    product_state = ConstructionState.create(
        molecules=(top, bottom),
        phase=ConstructionStatePhase.DUPLEX,
        pairings=pairings,
    )
    produced_material_bindings = tuple(
        ProducedMaterialBinding(
            material=ExactConstructionMaterial(
                material_id=derived_source_material_id(
                    strand.sequence,
                    complementary=index == 1,
                ),
                origin=MaterialOrigin.PCR_DERIVED,
                sequence_5prime=strand.sequence,
                five_prime_end=strand.five_prime_end,
                three_prime_end=strand.three_prime_end,
            ),
            product_state_id=product_state.state_id,
            product_strand_id=strand.strand_id,
        )
        for index, strand in enumerate(product_state.molecules)
    )
    return {
        "source_ssdna": source_ssdna,
        "forward_primer": forward_primer,
        "reverse_primer": reverse_primer,
        "payload_source_span": payload_source_span,
        "bindings": bindings,
        "product_state": product_state,
        "produced_material_bindings": produced_material_bindings,
    }


class SourceDuplexPreparationAuthority(HopModel):
    """Exact source-ssDNA, primer-binding, and copied-duplex relation."""

    authority_id: str = Field(
        pattern=r"^hop:source-duplex-preparation/[0-9a-f]{64}@1$"
    )
    source_ssdna: ExactConstructionMaterial
    forward_primer: PcrPrimer
    reverse_primer: PcrPrimer
    payload_source_span: Span
    bindings: tuple[PrimerBinding, PrimerBinding]
    product_state: ConstructionState
    produced_material_bindings: tuple[ProducedMaterialBinding, ProducedMaterialBinding]

    @classmethod
    def create(cls, **content: object) -> SourceDuplexPreparationAuthority:
        draft = cls.model_construct(authority_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"authority_id"})
        return cls.model_validate(
            {
                "authority_id": _content_id("source-duplex-preparation", 1, seed),
                **content,
            }
        )

    @model_validator(mode="after")
    def validate_authority(self) -> SourceDuplexPreparationAuthority:
        expected = _derived_content(
            source_ssdna=self.source_ssdna,
            forward_primer=self.forward_primer,
            reverse_primer=self.reverse_primer,
            payload_source_span=self.payload_source_span,
        )
        if self.bindings != expected["bindings"]:
            raise ValueError("Source-duplex preparation bindings must replay exactly.")
        if self.product_state != expected["product_state"]:
            raise ValueError("Source-duplex preparation product must replay exactly.")
        if self.produced_material_bindings != expected["produced_material_bindings"]:
            raise ValueError("Source-duplex produced-material bindings must replay exactly.")
        content = self.model_dump(mode="json", exclude={"authority_id"})
        if self.authority_id != _content_id("source-duplex-preparation", 1, content):
            raise ValueError("Source-duplex preparation identity must seal every exact fact.")
        return self


def derive_source_duplex_preparation(
    *,
    source_ssdna: ExactConstructionMaterial,
    forward_primer: PcrPrimer,
    reverse_primer: PcrPrimer,
    payload_source_span: Span,
) -> SourceDuplexPreparationAuthority:
    """Derive one replayable source duplex from exact ssDNA and terminal primers."""
    return SourceDuplexPreparationAuthority.create(
        **_derived_content(
            source_ssdna=source_ssdna,
            forward_primer=forward_primer,
            reverse_primer=reverse_primer,
            payload_source_span=payload_source_span,
        )
    )


__all__ = [
    "SourceDuplexPreparationAuthority",
    "derive_source_duplex_preparation",
]

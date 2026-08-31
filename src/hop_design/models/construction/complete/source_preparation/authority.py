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
from hop_design.models.coordinates import Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_replay import observe_pair, strand_from_sequence
from hop_design.models.molecular_state import (
    LineageStrand,
    MolecularStrand,
    PrimerBinding,
)

from ..material import (
    ExactConstructionMaterial,
    MaterialResolutionMode,
    MaterialRouteEntry,
    MaterialUse,
    MaterialUseRole,
    PcrPrimer,
    ProducedMaterialBinding,
)
from ..pcr.products import pcr_products
from ..state import ConstructionState, ConstructionStatePhase
from .input_validation import coordinate_span, validate_source_preparation_inputs


def _derived_content(
    *,
    source_ssdna: ExactConstructionMaterial,
    forward_primer: PcrPrimer,
    reverse_primer: PcrPrimer,
    payload_source_span: Span,
    source_resolution_mode: MaterialResolutionMode,
    forward_primer_resolution_mode: MaterialResolutionMode,
    reverse_primer_resolution_mode: MaterialResolutionMode,
) -> dict[str, object]:
    validate_source_preparation_inputs(
        source_ssdna=source_ssdna,
        forward_primer=forward_primer,
        reverse_primer=reverse_primer,
        payload_source_span=payload_source_span,
    )
    source_ssdna_use = MaterialUse.create(
        material_id=source_ssdna.material_id,
        role=MaterialUseRole.SOURCE_SSDNA,
        specification_resolution_mode=source_resolution_mode,
        route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
    )
    forward_primer_use = MaterialUse.create(
        material_id=forward_primer.oligo.material_id,
        role=MaterialUseRole.SOURCE_MATERIALIZATION_FORWARD_PRIMER,
        specification_resolution_mode=forward_primer_resolution_mode,
        route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
    )
    reverse_primer_use = MaterialUse.create(
        material_id=reverse_primer.oligo.material_id,
        role=MaterialUseRole.SOURCE_MATERIALIZATION_REVERSE_PRIMER,
        specification_resolution_mode=reverse_primer_resolution_mode,
        route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
    )
    template = strand_from_sequence(
        strand_id="source-ssdna-template",
        sequence=source_ssdna.sequence_5prime,
        five_prime_end=source_ssdna.five_prime_end,
        three_prime_end=source_ssdna.three_prime_end,
        origin_id=source_ssdna_use.use_id,
        origin_strand=LineageStrand.PRIMARY,
        origin_indexes=range(len(source_ssdna.sequence_5prime)),
    )
    input_state = ConstructionState.create(
        molecules=(template,),
        phase=ConstructionStatePhase.SOURCE_SSDNA,
    )
    top, bottom = pcr_products(
        template,
        forward_primer,
        reverse_primer,
        top_strand_id="source-duplex-top",
        bottom_strand_id="source-duplex-bottom",
        forward_use_id=forward_primer_use.use_id,
        reverse_use_id=reverse_primer_use.use_id,
    )
    source_length = len(source_ssdna.sequence_5prime)
    bindings = (
        PrimerBinding(
            binding_id="source-preparation-reverse-binding",
            primer_id=reverse_primer_use.use_id,
            template_strand_id=template.strand_id,
            template_span=coordinate_span(
                source_length - reverse_primer.annealing_length_nt,
                source_length,
            ),
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
        PrimerBinding(
            binding_id="source-preparation-forward-binding",
            primer_id=forward_primer_use.use_id,
            template_strand_id=bottom.strand_id,
            template_span=coordinate_span(
                source_length - forward_primer.annealing_length_nt,
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
    produced_materials = tuple(
        ExactConstructionMaterial(
            sequence_5prime=strand.sequence,
            five_prime_end=strand.five_prime_end,
            three_prime_end=strand.three_prime_end,
        )
        for strand in (top, bottom)
    )
    prepared_top_use = MaterialUse.create(
        material_id=produced_materials[0].material_id,
        role=MaterialUseRole.PREPARED_SOURCE_REFERENCE,
        specification_resolution_mode=MaterialResolutionMode.DERIVE,
        route_entry=MaterialRouteEntry.MODELED_PRODUCT,
    )
    prepared_bottom_use = MaterialUse.create(
        material_id=produced_materials[1].material_id,
        role=MaterialUseRole.PREPARED_SOURCE_COMPLEMENT,
        specification_resolution_mode=MaterialResolutionMode.DERIVE,
        route_entry=MaterialRouteEntry.MODELED_PRODUCT,
    )
    produced_uses = (prepared_top_use, prepared_bottom_use)
    upstream_lineages = (top.lineage, bottom.lineage)
    prepared_strands = tuple(
        strand.model_copy(
            update={
                "lineage": tuple(
                    item.model_copy(
                        update={
                            "origin_id": material_use.use_id,
                            "origin_strand": lineage_strand,
                            "origin_index": index,
                        }
                    )
                    for index, item in enumerate(strand.lineage)
                )
            }
        )
        for strand, material_use, lineage_strand in zip(
            (top, bottom),
            produced_uses,
            (LineageStrand.PRIMARY, LineageStrand.COMPLEMENTARY),
            strict=True,
        )
    )
    product_state = ConstructionState.create(
        molecules=prepared_strands,
        phase=ConstructionStatePhase.DUPLEX,
        pairings=pairings,
    )
    produced_material_bindings = tuple(
        ProducedMaterialBinding(
            material=material,
            material_use=material_use,
            product_state_id=product_state.state_id,
            product_strand_id=strand.strand_id,
            upstream_lineage=upstream_lineage,
        )
        for strand, material, material_use, upstream_lineage in zip(
            product_state.molecules,
            produced_materials,
            produced_uses,
            upstream_lineages,
            strict=True,
        )
    )
    return {
        "source_ssdna": source_ssdna,
        "forward_primer": forward_primer,
        "reverse_primer": reverse_primer,
        "source_ssdna_use": source_ssdna_use,
        "forward_primer_use": forward_primer_use,
        "reverse_primer_use": reverse_primer_use,
        "prepared_top_use": prepared_top_use,
        "prepared_bottom_use": prepared_bottom_use,
        "payload_source_span": payload_source_span,
        "source_template": template,
        "input_state": input_state,
        "pre_state_id": input_state.state_id,
        "bindings": bindings,
        "product_state": product_state,
        "post_state_id": product_state.state_id,
        "produced_material_bindings": produced_material_bindings,
    }


class SourceDuplexPreparationAuthority(HopModel):
    """Exact source-ssDNA, primer-binding, and copied-duplex relation."""

    authority_id: str = Field(pattern=r"^hop:source-duplex-preparation/[0-9a-f]{64}@1$")
    source_ssdna: ExactConstructionMaterial
    forward_primer: PcrPrimer
    reverse_primer: PcrPrimer
    source_ssdna_use: MaterialUse
    forward_primer_use: MaterialUse
    reverse_primer_use: MaterialUse
    prepared_top_use: MaterialUse
    prepared_bottom_use: MaterialUse
    payload_source_span: Span
    source_template: MolecularStrand
    input_state: ConstructionState
    pre_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    bindings: tuple[PrimerBinding, PrimerBinding]
    product_state: ConstructionState
    post_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
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
            source_resolution_mode=self.source_ssdna_use.specification_resolution_mode,
            forward_primer_resolution_mode=(
                self.forward_primer_use.specification_resolution_mode
            ),
            reverse_primer_resolution_mode=(
                self.reverse_primer_use.specification_resolution_mode
            ),
        )
        if self.source_template != expected["source_template"]:
            raise ValueError("Source-duplex preparation template must replay exactly.")
        if self.input_state != expected["input_state"] or self.pre_state_id != (
            self.input_state.state_id
        ):
            raise ValueError("Source-duplex preparation input state must replay exactly.")
        if self.bindings != expected["bindings"]:
            raise ValueError("Source-duplex preparation bindings must replay exactly.")
        if self.product_state != expected["product_state"]:
            raise ValueError("Source-duplex preparation product must replay exactly.")
        if self.post_state_id != self.product_state.state_id:
            raise ValueError("Source-duplex preparation output state must replay exactly.")
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
    source_resolution_mode: MaterialResolutionMode = MaterialResolutionMode.FIXED,
    forward_primer_resolution_mode: MaterialResolutionMode = MaterialResolutionMode.FIXED,
    reverse_primer_resolution_mode: MaterialResolutionMode = MaterialResolutionMode.FIXED,
) -> SourceDuplexPreparationAuthority:
    """Derive one replayable source duplex from exact ssDNA and terminal primers."""
    return SourceDuplexPreparationAuthority.create(
        **_derived_content(
            source_ssdna=source_ssdna,
            forward_primer=forward_primer,
            reverse_primer=reverse_primer,
            payload_source_span=payload_source_span,
            source_resolution_mode=source_resolution_mode,
            forward_primer_resolution_mode=forward_primer_resolution_mode,
            reverse_primer_resolution_mode=reverse_primer_resolution_mode,
        )
    )


__all__ = [
    "SourceDuplexPreparationAuthority",
    "derive_source_duplex_preparation",
]

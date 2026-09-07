"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/realization.py

Defines exact basal construction evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from typing import Any, cast

from pydantic import Field, model_validator
from pydantic_core import to_jsonable_python

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    BasalPairAllowance,
    BasalTarget,
    LocalRealization,
    OverheadPosition,
    PayloadSourceMap,
    RetainedOverheadLedger,
)
from hop_design.models.construction.enzyme_binding import ConstructionEnzymeBinding
from hop_design.models.enzymes import (
    EnzymeRole,
)
from hop_design.models.method_states import MultiSiteNickedDuplex
from hop_design.models.molecular_state import LineageStrand
from hop_design.models.reactions import ReactionProgram, ReactionStageAssessment
from hop_design.models.sequence import (
    reverse_complement_iupac,
)
from hop_design.serialization import canonical_json_bytes

from .identity import basal_realization_id
from .pairing import BasalBoundaryControl, BasalEnzymeDefinition
from .states import (
    BasalAdapterAnnealedComplex,
    BasalAdapterLigatedProduct,
    BasalEndpointProjection,
    BasalMaterialAccounting,
    BasalMaterialRecord,
    BasalMaterialRole,
    BasalPcrCopyState,
    assert_material_partition,
)


class BasalRealizationRecord(HopModel):
    """Complete exact basal route evidence for one discovered realization."""

    basal_realization_id: str = Field(pattern=r"^hop:basal-realization/[0-9a-f]{64}@1$")
    local_realization: LocalRealization
    payload_sequence: str
    source_precursor_sequence: str
    payload_source_map: PayloadSourceMap
    enzyme_definitions: tuple[BasalEnzymeDefinition, ...]
    enzyme_bindings: tuple[ConstructionEnzymeBinding, ...]
    basal_nick: BasalBoundaryControl
    pairing_constraints: tuple[BasalPairAllowance, ...]
    projection: BasalEndpointProjection
    reaction_programs: tuple[ReactionProgram, ...]
    stage_assessments: tuple[ReactionStageAssessment, ...]
    nicked_duplex: MultiSiteNickedDuplex
    adapter_annealed_complex: BasalAdapterAnnealedComplex
    adapter_ligated_product: BasalAdapterLigatedProduct
    hairpin_pcr_duplex: BasalPcrCopyState
    materials: tuple[BasalMaterialRecord, ...]
    material_accounting: BasalMaterialAccounting
    retained_overhead: RetainedOverheadLedger

    @classmethod
    def create(cls, **content: object) -> BasalRealizationRecord:
        draft = cls.model_construct(basal_realization_id="", **cast(Any, content))
        return cls.model_validate({"basal_realization_id": basal_realization_id(draft), **content})

    @model_validator(mode="after")
    def validate_realization(self) -> BasalRealizationRecord:
        if self.basal_realization_id != basal_realization_id(self):
            raise ValueError("basal_realization_id must seal the complete exact route evidence.")
        if self.local_realization.local_sequence != self.projection.pcr_reference_sequence:
            raise ValueError(
                "Local realization sequence must equal its exact endpoint-bearing state."
            )
        if self.local_realization.enzyme_binding_ids != tuple(
            binding.binding_id for binding in self.enzyme_bindings
        ):
            raise ValueError("Local realization must preserve every exact binding.")
        stage_ids = tuple(
            stage.stage_id for program in self.reaction_programs for stage in program.stages
        )
        if self.local_realization.stage_ids != stage_ids:
            raise ValueError("Local realization must preserve every exact reaction stage.")
        if tuple(item.stage_id for item in self.stage_assessments) != stage_ids:
            raise ValueError("Stage assessments must cover every reaction stage in order.")
        if any(item.report.has_errors for item in self.stage_assessments):
            raise ValueError("A basal realization cannot contain a rejected reaction stage.")
        if self.basal_nick.binding_id not in self.local_realization.enzyme_binding_ids:
            raise ValueError("Basal nick must reference one exact local binding.")
        achieved = cast(BasalTarget, self.local_realization.achieved_geometry)
        if (
            tuple(item.allowed_class for item in achieved.pairing_constraints)
            != self.pairing_constraints
        ):
            raise ValueError("Realization must retain the authored pairing constraints.")
        if self.projection.pairing_state is not None:
            realized = tuple(pair.pair_class.value for pair in self.projection.pairing_state.pairs)
            for allowed, observed in zip(self.pairing_constraints, realized, strict=True):
                if allowed is not BasalPairAllowance.ANY and allowed.value != observed:
                    raise ValueError("Literal basal pairs must satisfy authored class constraints.")
        self._validate_enzyme_replay()
        totals = {
            role: sum(len(item.sequence_5prime) for item in self.materials if item.role is role)
            for role in BasalMaterialRole
        }
        expected = BasalMaterialAccounting(
            retained_nt=totals[BasalMaterialRole.RETAINED],
            transient_nt=totals[BasalMaterialRole.TRANSIENT],
            auxiliary_nt=totals[BasalMaterialRole.AUXILIARY],
        )
        if self.material_accounting != expected:
            raise ValueError("Basal material accounting must derive from exact materials.")
        payload_span = self.payload_source_map.segments[0].source_span
        reference = self.projection.pcr_reference_sequence
        expected_positions = tuple(
            OverheadPosition(
                coordinate_space="basal-boundary",
                position=position,
                base=reference[position],
                material_role=("source" if position < payload_span.start.offset else "adapter"),
            )
            for position in range(len(reference))
            if not payload_span.start.offset <= position < payload_span.end.offset
        )
        if self.retained_overhead != RetainedOverheadLedger(
            neighborhood="basal",
            reference_state_id="basal-pcr-local-boundary",
            positions=expected_positions,
            retained_overhead_nt=len(expected_positions),
        ):
            raise ValueError("Retained overhead must replay the non-payload basal boundary.")
        self._validate_route_states()
        assert_material_partition(
            pcr_duplex=self.hairpin_pcr_duplex,
            materials=self.materials,
        )
        return self

    def _validate_enzyme_replay(self) -> None:
        definitions = {item.enzyme_id: item.enzyme for item in self.enzyme_definitions}
        if len(definitions) != len(self.enzyme_definitions) or set(definitions) != {
            item.enzyme_id for item in self.enzyme_bindings
        }:
            raise ValueError("Embedded enzyme definitions must cover every binding exactly.")
        for binding in self.enzyme_bindings:
            if binding.role is not EnzymeRole.BASAL_NICK:
                raise ValueError("Basal local authority may contain only basal-nick bindings.")
            binding.assert_definition_replay(
                enzyme=definitions[binding.enzyme_id],
                sequence=self.source_precursor_sequence,
            )
        stages = tuple(stage for program in self.reaction_programs for stage in program.stages)
        if len({item.binding_id for item in self.enzyme_bindings}) != len(self.enzyme_bindings):
            raise ValueError("Reaction operations must map bijectively to unique bindings.")

        def binding_key(
            *,
            enzyme_id: str,
            role: EnzymeRole,
            recognition_span: object,
            orientation: object,
            reference_cut: object,
            complement_cut: object,
        ) -> bytes:
            return canonical_json_bytes(
                to_jsonable_python(
                    {
                        "enzyme_id": enzyme_id,
                        "role": role,
                        "recognition_span": recognition_span,
                        "orientation": orientation,
                        "reference_cut": reference_cut,
                        "complement_cut": complement_cut,
                    }
                )
            )

        embedded = Counter(
            binding_key(
                enzyme_id=item.enzyme_id,
                role=item.role,
                recognition_span=item.recognition_span,
                orientation=item.orientation,
                reference_cut=item.reference_cut,
                complement_cut=item.complement_cut,
            )
            for item in self.enzyme_bindings
        )
        operations = tuple(operation for stage in stages for operation in stage.operations)
        declared_counts = Counter(
            binding_key(
                enzyme_id=item.enzyme_id,
                role=item.role,
                recognition_span=item.intended_binding.recognition_span,
                orientation=item.intended_binding.orientation,
                reference_cut=item.intended_binding.reference_cut,
                complement_cut=item.intended_binding.complement_cut,
            )
            for item in operations
        )
        if embedded != declared_counts or any(count != 1 for count in declared_counts.values()):
            raise ValueError(
                "Reaction operations must map bijectively to embedded enzyme bindings."
            )
        for stage, assessment in zip(stages, self.stage_assessments, strict=True):
            if assessment.resolved_against_state_id != stage.pre_state_id:
                raise ValueError("Stage assessment must replay its exact pre-state.")
            if assessment.undeclared_bindings:
                raise ValueError("Accepted basal stages cannot retain undeclared bindings.")
            intended = {item.operation_id: item for item in assessment.intended_bindings}
            if set(intended) != {item.operation_id for item in stage.operations}:
                raise ValueError("Stage assessment must replay every declared operation.")
            for operation in stage.operations:
                observed = intended[operation.operation_id]
                declared = operation.intended_binding
                if (
                    observed.enzyme_id != operation.enzyme_id
                    or observed.molecule_id != operation.molecule_id
                    or observed.recognition_span != declared.recognition_span
                    or observed.orientation is not declared.orientation
                    or observed.reference_cut != declared.reference_cut
                    or observed.complement_cut != declared.complement_cut
                ):
                    raise ValueError("Stage assessment must replay exact binding evidence.")

    def _validate_route_states(self) -> None:
        segment = self.payload_source_map.segments[0]
        observed_payload = self.source_precursor_sequence[
            segment.source_span.start.offset : segment.source_span.end.offset
        ]
        if observed_payload != self.payload_sequence:
            raise ValueError("Payload source map must preserve the exact payload sequence.")
        nick_program = self.reaction_programs[0]
        if len(nick_program.stages) != 1 or len(nick_program.states) != 2:
            raise ValueError("Basal nick route requires one exact cleavage stage.")
        pre_molecules = nick_program.states[0].molecules
        post_molecules = nick_program.states[1].molecules
        if len(pre_molecules) != 1 or pre_molecules != post_molecules:
            raise ValueError("Basal nick program post-state must preserve the exact duplex.")
        precursor = pre_molecules[0]
        if (
            precursor.reference_sequence_5prime != self.source_precursor_sequence
            or precursor.complement_sequence_5prime
            != reverse_complement_iupac(self.source_precursor_sequence)
        ):
            raise ValueError("Basal nick program must act on the exact source precursor.")
        nick_site = self.nicked_duplex.sites[0]
        if (
            self.nicked_duplex.top_strand.sequence != self.source_precursor_sequence
            or self.nicked_duplex.bottom_strand.sequence
            != reverse_complement_iupac(self.source_precursor_sequence)
            or nick_site.nick.boundary != self.basal_nick.boundary
            or nick_site.nick.strand is not self.basal_nick.strand
        ):
            raise ValueError("Nicked-duplex evidence must replay the exact basal binding.")
        adapter = next(
            item.sequence_5prime
            for item in self.materials
            if item.material_id == "ligation-adapter"
        )
        expected_ligated = self.source_precursor_sequence + adapter
        if self.adapter_ligated_product.strand.sequence != expected_ligated:
            raise ValueError(
                "Adapter-ligated product must concatenate the exact source and adapter."
            )
        if (
            self.hairpin_pcr_duplex.top_strand.sequence != expected_ligated
            or self.hairpin_pcr_duplex.bottom_strand.sequence
            != reverse_complement_iupac(expected_ligated)
        ):
            raise ValueError("PCR strands must copy the complete adapter-ligated duplex exactly.")
        top = self.hairpin_pcr_duplex.top_strand
        bottom = self.hairpin_pcr_duplex.bottom_strand
        ligated = self.adapter_ligated_product.strand
        if (
            top.lineage != ligated.lineage
            or top.five_prime_end is not ligated.five_prime_end
            or top.three_prime_end is not ligated.three_prime_end
            or tuple(item.origin_id for item in bottom.lineage)
            != (ligated.strand_id,) * len(bottom.sequence)
            or tuple(item.origin_strand for item in bottom.lineage)
            != (LineageStrand.COMPLEMENTARY,) * len(bottom.sequence)
            or tuple(item.origin_index for item in bottom.lineage)
            != tuple(reversed(range(len(bottom.sequence))))
        ):
            raise ValueError("PCR strands must replay exact adapter-ligated lineage and ends.")

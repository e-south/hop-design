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
    ConstructionEndpoint,
    LocalRealization,
    PayloadSourceMap,
)
from hop_design.models.enzymes import (
    EnzymeRole,
)
from hop_design.models.method_states import MultiSiteNickedDuplex
from hop_design.models.reactions import ReactionProgram, ReactionStageAssessment
from hop_design.models.sequence import (
    reverse_complement_iupac,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .pairing import BasalBoundaryControl, BasalEnzymeBinding, BasalEnzymeDefinition
from .states import (
    BasalAdapterAnnealedComplex,
    BasalEndpointProjection,
    BasalLigatedHairpin,
    BasalMaterialAccounting,
    BasalMaterialRecord,
    BasalMaterialRole,
    BasalPcrCopyState,
    BasalRestrictionProduct,
    assert_material_partition,
)


def _realization_id(content: dict[str, object]) -> str:
    digest = sha256_digest(canonical_json_bytes(to_jsonable_python(content))).removeprefix(
        "sha256:"
    )
    return f"hop:basal-realization/{digest}@1"


class BasalRealizationRecord(HopModel):
    """Complete exact basal route evidence for one discovered realization."""

    basal_realization_id: str = Field(pattern=r"^hop:basal-realization/[0-9a-f]{64}@1$")
    local_realization: LocalRealization
    payload_sequence: str
    source_precursor_sequence: str
    payload_source_map: PayloadSourceMap
    enzyme_definitions: tuple[BasalEnzymeDefinition, ...]
    enzyme_bindings: tuple[BasalEnzymeBinding, ...]
    basal_nick: BasalBoundaryControl
    pairing_constraints: tuple[BasalPairAllowance, ...]
    projection: BasalEndpointProjection
    reaction_programs: tuple[ReactionProgram, ...]
    stage_assessments: tuple[ReactionStageAssessment, ...]
    nicked_duplex: MultiSiteNickedDuplex
    adapter_annealed_complex: BasalAdapterAnnealedComplex | None
    ligated_hairpin: BasalLigatedHairpin | None
    hairpin_pcr_duplex: BasalPcrCopyState | None
    restriction_digest_product: BasalRestrictionProduct | None
    materials: tuple[BasalMaterialRecord, ...]
    material_accounting: BasalMaterialAccounting
    relaxation_radius: int = Field(ge=0)
    changed_coordinates: tuple[str, ...]

    @classmethod
    def create(cls, **content: object) -> BasalRealizationRecord:
        draft = cls.model_construct(basal_realization_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"basal_realization_id"})
        return cls.model_validate({"basal_realization_id": _realization_id(seed), **content})

    @model_validator(mode="after")
    def validate_realization(self) -> BasalRealizationRecord:
        content = self.model_dump(mode="json", exclude={"basal_realization_id"})
        if self.basal_realization_id != _realization_id(content):
            raise ValueError("basal_realization_id must seal the complete exact route evidence.")
        expected_local_sequence = (
            self.projection.pcr_reference_sequence or self.source_precursor_sequence
        )
        if self.local_realization.local_sequence != expected_local_sequence:
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
        if self.projection.pairing_profile is not None:
            realized = tuple(
                pair.pair_class.value for pair in self.projection.pairing_profile.pairs
            )
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
        self._validate_route_states()
        assert_material_partition(
            endpoint=self.projection.endpoint,
            source_precursor_sequence=self.source_precursor_sequence,
            pcr_duplex=self.hairpin_pcr_duplex,
            restriction_product=self.restriction_digest_product,
            materials=self.materials,
        )
        self._validate_endpoint_minimality()
        return self

    def _validate_enzyme_replay(self) -> None:
        definitions = {item.enzyme_id: item.enzyme for item in self.enzyme_definitions}
        if len(definitions) != len(self.enzyme_definitions) or set(definitions) != {
            item.enzyme_id for item in self.enzyme_bindings
        }:
            raise ValueError("Embedded enzyme definitions must cover every binding exactly.")
        for binding in self.enzyme_bindings:
            sequence = self.source_precursor_sequence
            if binding.role is EnzymeRole.END_GENERATION:
                if self.hairpin_pcr_duplex is None:
                    raise ValueError("End-generation bindings require an exact duplex state.")
                sequence = self.hairpin_pcr_duplex.top_strand.sequence
            binding.assert_definition_replay(
                enzyme=definitions[binding.enzyme_id],
                sequence=sequence,
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
        if self.projection.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            return
        if (
            self.adapter_annealed_complex is None
            or self.ligated_hairpin is None
            or self.hairpin_pcr_duplex is None
            or self.projection.pairing_profile is None
        ):
            raise ValueError(
                "PCR-bearing endpoints require exact annealing, ligation, and PCR states."
            )
        adapter = next(
            item.sequence_5prime
            for item in self.materials
            if item.material_id == "ligation-adapter"
        )
        expected_ligated = self.source_precursor_sequence + adapter
        if self.ligated_hairpin.strand.sequence != expected_ligated:
            raise ValueError("Ligated hairpin must concatenate the exact source and adapter.")
        if (
            self.hairpin_pcr_duplex.top_strand.sequence != expected_ligated
            or self.hairpin_pcr_duplex.bottom_strand.sequence
            != reverse_complement_iupac(expected_ligated)
        ):
            raise ValueError("PCR strands must copy the complete ligated heteroduplex exactly.")
        if self.projection.endpoint is not ConstructionEndpoint.CLONE_READY_DUPLEX:
            return
        if len(self.reaction_programs) != 2 or self.restriction_digest_product is None:
            raise ValueError("Clone-ready endpoint requires one exact Type IIS program.")
        end_program = self.reaction_programs[1]
        pre = end_program.states[0].molecules
        post = end_program.states[1].molecules
        if (
            len(pre) != 1
            or pre[0].reference_sequence_5prime != self.hairpin_pcr_duplex.top_strand.sequence
            or pre[0].complement_sequence_5prime != self.hairpin_pcr_duplex.bottom_strand.sequence
        ):
            raise ValueError("Type IIS program must act on the exact PCR duplex.")
        expected_post = {
            self.restriction_digest_product.primary_strand.sequence,
            self.restriction_digest_product.complementary_strand.sequence,
        }
        if {item.reference_sequence_5prime for item in post} != expected_post:
            raise ValueError(
                "Type IIS program post-state must equal the exact restriction product."
            )
        end_bindings = tuple(
            item.binding_id
            for item in self.enzyme_bindings
            if item.role is EnzymeRole.END_GENERATION
        )
        if self.restriction_digest_product.binding_ids != end_bindings:
            raise ValueError("Restriction product must preserve both Type IIS bindings.")
        if self.projection.cohesive_ends != self.restriction_digest_product.cohesive_ends:
            raise ValueError("Endpoint projection must preserve the exact restriction ends.")
        self.restriction_digest_product.assert_parent_replay(self.hairpin_pcr_duplex)

    def _validate_endpoint_minimality(self) -> None:
        endpoint = self.projection.endpoint
        if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            if any(
                item is not None
                for item in (
                    self.adapter_annealed_complex,
                    self.ligated_hairpin,
                    self.hairpin_pcr_duplex,
                    self.restriction_digest_product,
                )
            ):
                raise ValueError("A direct basal endpoint must remain adapter-free and PCR-free.")
        elif endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            if self.restriction_digest_product is not None:
                raise ValueError("A PCR endpoint must not contain clone-ready digestion.")
        elif self.restriction_digest_product is None:
            raise ValueError("A clone-ready endpoint requires an exact restriction product.")

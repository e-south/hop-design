"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/foldback/realization.py

Defines exact foldback construction evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    FinalPayloadReference,
    FoldbackTarget,
    LocalRealization,
    NeighborhoodDiscoveryResult,
    OverheadPosition,
    PayloadSourceMap,
    RetainedOverheadLedger,
    SourceOrientation,
    validate_linear_source_map,
)
from hop_design.models.coordinates import Boundary
from hop_design.models.molecular_state import (
    CovalentBond,
    EndChemistry,
    Fragment,
    MolecularStrand,
    StrandPairObservation,
)
from hop_design.models.payload import ExactPayload
from hop_design.models.physical import Strand
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.reactions import (
    ReactionProgram,
    ReactionStageAssessment,
)
from hop_design.models.sequence import iupac_bases, normalize_dna_sequence, reverse_complement_iupac
from hop_design.models.strand_state import ReleasedStrandState
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .binding import (
    _CONTENT_ADAPTER,
    FoldbackBoundaryControl,
    FoldbackCleavageProgramKind,
    FoldbackEnzymeBinding,
    FoldbackMaterialRequirement,
)


class FoldbackLocalRealization(HopModel):
    """Every exact sequence, site, fragment, stage, and closure fact for one route."""

    foldback_realization_id: str = Field(pattern=r"^hop:foldback-realization/[0-9a-f]{64}@1$")
    local_realization: LocalRealization
    payload_spec_id: str = Field(pattern=r"^hop:payload-spec/[0-9a-f]{64}@1$")
    program_kind: FoldbackCleavageProgramKind
    payload_sequence: str
    source_reference_sequence: str
    payload_source_map: PayloadSourceMap
    source_top_strand: MolecularStrand
    source_bottom_strand: MolecularStrand
    material_requirements: tuple[FoldbackMaterialRequirement, ...]
    enzyme_bindings: tuple[FoldbackEnzymeBinding, ...]
    foldback_nick: FoldbackBoundaryControl
    terminus: FoldbackBoundaryControl
    molecular_fragments: tuple[Fragment, ...]
    released_fragment_ids: tuple[str, ...]
    released_state: ReleasedStrandState
    loop_sequence: str
    foldback_arm_sequence: str
    retained_sequence: str
    annealing_pairs: tuple[StrandPairObservation, ...]
    ligation_bond: CovalentBond
    ligated_strand: MolecularStrand
    reaction_program: ReactionProgram
    stage_assessments: tuple[ReactionStageAssessment, ...]
    retained_overhead: RetainedOverheadLedger
    transient_construction_nt: int = Field(ge=0)

    @classmethod
    def create(cls, **content: object) -> FoldbackLocalRealization:
        """Create a content-addressed realization over every molecular authority."""
        canonical_content = _CONTENT_ADAPTER.dump_python(content, mode="json")
        digest = sha256_digest(canonical_json_bytes(canonical_content)).removeprefix("sha256:")
        return cls.model_validate(
            {
                "foldback_realization_id": f"hop:foldback-realization/{digest}@1",
                **content,
            }
        )

    @field_validator(
        "payload_sequence",
        "source_reference_sequence",
        "loop_sequence",
        "foldback_arm_sequence",
        "retained_sequence",
        mode="before",
    )
    @classmethod
    def normalize_sequences(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Foldback realization sequence must be a DNA string.")
        if value == "":
            return value
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_realization(self) -> FoldbackLocalRealization:
        content = self.model_dump(mode="json", exclude={"foldback_realization_id"})
        digest = sha256_digest(canonical_json_bytes(content)).removeprefix("sha256:")
        if self.foldback_realization_id != f"hop:foldback-realization/{digest}@1":
            raise ValueError("Foldback realization identity must seal every molecular fact.")
        validate_linear_source_map(
            self._payload_reference(),
            self.payload_source_map,
            allowed_orientations=(
                SourceOrientation.FORWARD,
                SourceOrientation.REVERSE_COMPLEMENT,
            ),
        )
        source_segment = self.payload_source_map.segments[0]
        mapped = self.source_reference_sequence[
            source_segment.source_span.start.offset : source_segment.source_span.end.offset
        ]
        expected_payload = (
            mapped
            if source_segment.orientation is SourceOrientation.FORWARD
            else reverse_complement_iupac(mapped)
        )
        if expected_payload != self.payload_sequence:
            raise ValueError("Payload source mapping must replay the exact payload bytes.")
        if self.local_realization.local_sequence != self.source_reference_sequence:
            raise ValueError("Local realization sequence must equal the exact source reference.")
        if self.local_realization.enzyme_binding_ids != tuple(
            binding.binding_id for binding in self.enzyme_bindings
        ):
            raise ValueError("Local realization binding ids must preserve every exact binding.")
        if self.local_realization.stage_ids != tuple(
            stage.stage_id for stage in self.reaction_program.stages
        ):
            raise ValueError("Local realization stage ids must preserve the exact program.")
        if tuple(item.stage_id for item in self.stage_assessments) != tuple(
            stage.stage_id for stage in self.reaction_program.stages
        ):
            raise ValueError("Stage assessments must cover the exact reaction program in order.")
        if any(item.report.has_errors for item in self.stage_assessments):
            raise ValueError("A foldback realization cannot contain a rejected reaction stage.")
        if self.foldback_nick.strand is self.terminus.strand:
            raise ValueError("Foldback nick and terminus must control different strands.")
        if self.terminus.strand is not (
            Strand.BOTTOM if self.foldback_nick.strand is Strand.TOP else Strand.TOP
        ):
            raise ValueError("Foldback nick and terminus strands must be physically opposite.")
        expected_stages = (
            1 if self.program_kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE else 2
        )
        if len(self.reaction_program.stages) != expected_stages:
            raise ValueError("Foldback cleavage-program kind must match its exact stage count.")
        expected_requirements = (
            (
                FoldbackMaterialRequirement.SOURCE_BOTTOM_5PRIME_PHOSPHATE
                if self.foldback_nick.strand is Strand.TOP
                else FoldbackMaterialRequirement.SOURCE_TOP_5PRIME_PHOSPHATE,
            )
            if self.program_kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE
            else ()
        )
        if self.material_requirements != expected_requirements:
            raise ValueError("Foldback material requirements must derive from the route program.")
        achieved = cast(FoldbackTarget, self.local_realization.achieved_geometry)
        from hop_design.models.construction.foldback_replay import replay_foldback_route

        replay = replay_foldback_route(
            payload_sequence=self.payload_sequence,
            target=achieved,
            program_kind=self.program_kind,
            source_reference_sequence=self.source_reference_sequence,
            enzyme_bindings=self.enzyme_bindings,
        )
        replay_fields = (
            (self.source_top_strand, replay.source_top_strand),
            (self.source_bottom_strand, replay.source_bottom_strand),
            (self.foldback_nick, replay.foldback_nick),
            (self.terminus, replay.terminus),
            (self.reaction_program, replay.reaction_program),
            (self.stage_assessments, replay.stage_assessments),
            (self.molecular_fragments, replay.molecular_fragments),
            (self.released_fragment_ids, replay.released_fragment_ids),
            (self.released_state, replay.released_state),
            (self.annealing_pairs, replay.annealing_pairs),
            (self.ligation_bond, replay.ligation_bond),
            (self.ligated_strand, replay.ligated_strand),
            (self.loop_sequence, replay.loop_sequence),
            (self.foldback_arm_sequence, replay.foldback_arm_sequence),
            (self.retained_sequence, replay.ligated_strand.sequence),
        )
        if any(observed != expected for observed, expected in replay_fields):
            raise ValueError("Foldback molecular authorities must equal route replay.")
        if self.foldback_nick.end_chemistry is not EndChemistry.HYDROXYL:
            raise ValueError("The nick-controlled three-prime end must be hydroxylated.")
        if self.terminus.end_chemistry is not EndChemistry.PHOSPHATE:
            raise ValueError("The foldback-side five-prime end must be phosphorylated.")
        overhead_start = len(self.payload_sequence)
        overhead_end = len(self.retained_sequence) - len(self.payload_sequence)
        expected_positions = tuple(
            OverheadPosition(
                coordinate_space="foldback-path",
                position=position,
                base=self.retained_sequence[position],
                material_role="source",
            )
            for position in range(overhead_start, overhead_end)
        )
        if self.retained_overhead != RetainedOverheadLedger(
            neighborhood="foldback",
            reference_state_id="foldback-local-product",
            positions=expected_positions,
            retained_overhead_nt=len(expected_positions),
        ):
            raise ValueError("Retained overhead must replay the non-payload foldback path.")
        expected_transient = sum(
            fragment.precursor_span.length.value
            for fragment in self.molecular_fragments
            if fragment.fragment_id in self.released_fragment_ids
        )
        if self.transient_construction_nt != expected_transient:
            raise ValueError("Transient construction count must derive from released fragments.")
        return self

    def _payload_reference(self) -> FinalPayloadReference:
        return FinalPayloadReference(
            payload=ExactPayload(sequence=self.payload_sequence),
            basal_boundary=Boundary(offset=0),
            foldback_boundary=Boundary(offset=len(self.payload_sequence)),
        )


class FoldbackNeighborhoodDiscoveryResult(HopModel):
    """Shared neighborhood authority plus lossless foldback-family evidence."""

    schema_id: Literal["hop.foldback-neighborhood-result/v4"] = Field(
        default="hop.foldback-neighborhood-result/v4", alias="schema"
    )
    result_id: str = Field(pattern=r"^hop:foldback-neighborhood-result/[0-9a-f]{64}@1$")
    neighborhood: NeighborhoodDiscoveryResult
    realizations: tuple[FoldbackLocalRealization, ...]

    @classmethod
    def create(cls, **content: object) -> FoldbackNeighborhoodDiscoveryResult:
        draft = cls.model_construct(result_id="", **cast(Any, content))
        return cls.model_validate({"result_id": draft._expected_result_id(), **content})

    def _expected_result_id(self) -> str:
        content = {
            "schema": self.schema_id,
            "neighborhood_result_id": self.neighborhood.result_id,
            "realizations": tuple(
                realization.model_dump(mode="json") for realization in self.realizations
            ),
        }
        digest = sha256_digest(canonical_json_bytes(content)).removeprefix("sha256:")
        return f"hop:foldback-neighborhood-result/{digest}@1"

    @model_validator(mode="after")
    def validate_membership(self) -> FoldbackNeighborhoodDiscoveryResult:
        NeighborhoodDiscoveryResult.model_validate(self.neighborhood.model_dump(mode="python"))
        generic_ids = tuple(
            realization.local_realization_id for realization in self.neighborhood.realizations
        )
        detailed_ids = tuple(
            realization.local_realization.local_realization_id for realization in self.realizations
        )
        if generic_ids != detailed_ids or len(detailed_ids) != len(set(detailed_ids)):
            raise ValueError("Foldback family details must preserve the exact ordered relation.")
        authored = self.neighborhood.request.payload.payload.sequence
        payload_spec_id = self.neighborhood.request.payload.payload_spec_id
        for realization in self.realizations:
            if realization.payload_spec_id != payload_spec_id:
                raise ValueError("Foldback realization must bind the request payload identity.")
            if any(
                base not in iupac_bases(symbol)
                for base, symbol in zip(
                    realization.payload_sequence,
                    authored,
                    strict=True,
                )
            ):
                raise ValueError("Foldback realization payload must belong to the request space.")
            assessment = assess_reaction_program(
                program=realization.reaction_program,
                policy=self.neighborhood.request.enzyme_provisioning,
            )
            if assessment.report.has_errors:
                raise ValueError(
                    "Foldback realization violates the local provisioning operation limit."
                )
        if self.result_id != self._expected_result_id():
            raise ValueError("result_id must seal the complete foldback neighborhood result.")
        return self

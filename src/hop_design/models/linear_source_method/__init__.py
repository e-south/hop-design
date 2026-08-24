"""Closed contracts for linear-source multi-nick hairpin-PCR resolution."""

from __future__ import annotations

from typing import Final, Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import (
    NickingAgent,
    ReleaseAgent,
)
from hop_design.models.linear_source_method.replay import validate_linear_source_method_plan
from hop_design.models.method import (
    BindingOrientation,
    LinearSourceHairpinPcrMaterialsPlan,
    LinearSourceHairpinPcrMaterialsSpec,
    MethodOutcome,
)
from hop_design.models.method_states import (
    AdapterAnnealedComplex,
    DenaturedFragmentSet,
    HairpinPcrDuplex,
    LengthSelectedFragmentSet,
    LigatedHairpin,
    MultiSiteNickedDuplex,
    RestrictionDigestProduct,
    SourcePcrDuplex,
)
from hop_design.models.molecular_state import (
    AdapterAnnealingRequest,
    FragmentLengthSelection,
)
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import (
    EXACT_DNA_ALPHABET,
    SequenceValidationError,
    normalize_dna_sequence,
)

LinearSourceMethodKind = Literal["linear-source-multinick-size-selection-hairpin-pcr@1"]
LINEAR_SOURCE_METHOD_KIND: Final[LinearSourceMethodKind] = (
    "linear-source-multinick-size-selection-hairpin-pcr@1"
)


class LinearSourceMultinickHairpinPcrRequest(HopModel):
    schema_id: Literal["hop.linear-source-multinick-hairpin-pcr-request/v1"] = Field(
        default="hop.linear-source-multinick-hairpin-pcr-request/v1", alias="schema"
    )
    request_id: ReferenceId
    method_kind: LinearSourceMethodKind = LINEAR_SOURCE_METHOD_KIND
    materials: LinearSourceHairpinPcrMaterialsSpec
    nicking_agents: tuple[NickingAgent, ...] = Field(min_length=1)
    fragment_selection: FragmentLengthSelection
    adapter_annealing: AdapterAnnealingRequest
    restriction_agent: ReleaseAgent
    hairpin_encoding_projection_orientation: BindingOrientation = (
        BindingOrientation.REVERSE_COMPLEMENT_5TO3
    )
    expected_hairpin_encoding: str | None = None

    @field_validator("expected_hairpin_encoding", mode="before")
    @classmethod
    def normalize_expected_encoding(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_request(self) -> LinearSourceMultinickHairpinPcrRequest:
        source = self.materials.source_oligo.sequence
        if not set(source) <= EXACT_DNA_ALPHABET:
            raise ValueError("The linear-source method requires one exact source oligo.")
        ids = tuple(agent.agent_id for agent in self.nicking_agents)
        if len(ids) != len(set(ids)):
            raise ValueError("Linear-source nicking-agent ids must be unique.")
        if self.adapter_annealing.adapter_span.end.offset > len(
            self.materials.ligation_adapter.sequence
        ):
            raise ValueError("Adapter annealing span must stay inside the adapter sequence.")
        return self


class LinearSourceMultinickHairpinPcrPlan(HopModel):
    schema_id: Literal["hop.linear-source-multinick-hairpin-pcr-plan/v2"] = Field(
        default="hop.linear-source-multinick-hairpin-pcr-plan/v2", alias="schema"
    )
    request_id: ReferenceId
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    method_kind: LinearSourceMethodKind = LINEAR_SOURCE_METHOD_KIND
    materials: LinearSourceHairpinPcrMaterialsPlan
    source_pcr_duplex: SourcePcrDuplex
    multi_site_nicked_duplex: MultiSiteNickedDuplex
    denatured_fragment_set: DenaturedFragmentSet
    length_selected_fragment_set: LengthSelectedFragmentSet
    adapter_annealing: AdapterAnnealingRequest
    adapter_annealed_complex: AdapterAnnealedComplex
    ligated_hairpin: LigatedHairpin
    hairpin_pcr_duplex: HairpinPcrDuplex
    restriction_agent: ReleaseAgent
    restriction_digest_product: RestrictionDigestProduct

    @model_validator(mode="after")
    def validate_transition_identity(self) -> LinearSourceMultinickHairpinPcrPlan:
        validate_linear_source_method_plan(self)
        return self


class LinearSourceMultinickHairpinPcrResult(HopModel):
    schema_id: Literal["hop.linear-source-multinick-hairpin-pcr-result/v2"] = Field(
        default="hop.linear-source-multinick-hairpin-pcr-result/v2", alias="schema"
    )
    request_id: ReferenceId
    method_kind: LinearSourceMethodKind = LINEAR_SOURCE_METHOD_KIND
    outcome: MethodOutcome
    plan: LinearSourceMultinickHairpinPcrPlan | None

    @model_validator(mode="after")
    def validate_result(self) -> LinearSourceMultinickHairpinPcrResult:
        is_complete = self.outcome.resolution_status == "complete"
        if is_complete != (self.plan is not None):
            raise ValueError("A method plan exists exactly when resolution is complete.")
        return self

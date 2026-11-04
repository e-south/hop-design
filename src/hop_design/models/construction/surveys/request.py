"""Finite interface-survey molecular permissions, independent of execution budgets."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import (
    CharacterizedEnzymeCatalog,
    EnzymePermissions,
    EnzymeProvisioningPolicy,
)
from hop_design.models.molecular_state import StrandEnd
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import normalize_dna_sequence

from ..complete.request import WholeRouteConstraints
from ..complete.source_preparation import LinearSourceMaterializationSpec
from ..complete.source_preparation.policy import ConstrainedSourceSsdnaPolicy
from ..discovery.placement import EndPlacement
from ..product_pairing import EndFootprintPairing
from ..product_request import ProductBasalGeometry, ProductBasalReleaseProjection
from ..search import FoldbackGeometryDomain
from ..source_partition.policy import SacrificialFragmentPolicy
from ..targets import ConstructionConstraints, ConstructionPreferences
from .preference import SurveyPreparationReference
from .targets import InterfaceTargetDomain


class SurveyInterfaceFrame(HopModel):
    """Words are read on their own protruding strand, in the declared orientation."""

    orientation: SiteOrientation
    overhang_end: StrandEnd


class SurveyInterfaces(HopModel):
    left: SurveyInterfaceFrame
    right: SurveyInterfaceFrame


class SurveyFoldback(HopModel):
    geometry: FoldbackGeometryDomain
    enzymes: EnzymePermissions
    max_retained_overhead_nt: int = Field(ge=0)


class SurveyBasalGeometry(ProductBasalGeometry):
    """Association requirements are authored once, in annealing_lengths_nt."""

    minimum_adapter_annealing_nt: None = Field(default=None, exclude=True)


class SurveyBasal(HopModel):
    geometry: SurveyBasalGeometry
    end_footprint_pairing: EndFootprintPairing | None = None
    annealing_lengths_nt: tuple[int, ...] = Field(min_length=1)
    enzymes: EnzymePermissions
    max_retained_overhead_nt: int = Field(ge=0)

    @field_validator("annealing_lengths_nt")
    @classmethod
    def canonical_lengths(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if any(value < 1 for value in values) or len(values) != len(set(values)):
            raise ValueError("Association lengths must be distinct positive nucleotide counts.")
        return tuple(sorted(values))


class SurveyRelease(HopModel):
    enzymes: EnzymePermissions
    basal_projections: tuple[ProductBasalReleaseProjection, ...] = Field(min_length=1)

    @field_validator("basal_projections")
    @classmethod
    def distinct_projections(
        cls, values: tuple[ProductBasalReleaseProjection, ...]
    ) -> tuple[ProductBasalReleaseProjection, ...]:
        if len(set(values)) != len(values):
            raise ValueError("Basal release projections must not repeat.")
        return tuple(
            sorted(values, key=lambda value: (value.product_end, value.recognition_material))
        )


class SourceContextPreference(HopModel):
    """Caller-supplied completion preferences; never additional molecular permissions."""

    source_handle_seed: str | None = Field(
        default=None, min_length=1, max_length=256, exclude_if=lambda value: value is None
    )

    @field_validator("source_handle_seed")
    @classmethod
    def exact_seed(cls, value: str | None) -> str | None:
        return None if value is None else normalize_dna_sequence(value, allow_degenerate=False)

    preferred_source_contexts: tuple[str, ...] = Field(
        default=(), max_length=16, exclude_if=lambda value: not value
    )

    @field_validator("preferred_source_contexts")
    @classmethod
    def known_contexts(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        words = tuple(normalize_dna_sequence(w, allow_degenerate=False) for w in values)
        if any(not 1 <= len(w) <= 256 for w in words):
            raise ValueError("Preferred source contexts require 1 to 256 exact bases.")
        if len(set(words)) != len(words):
            raise ValueError("Preferred source contexts must be distinct.")
        return tuple(sorted(words))


class InterfaceSurveyRequest(SourceContextPreference):
    """All targets and permitted compensations for one invariant supplied stem.

    The endpoint is the released duplex insert. This domain neither promises a
    complete construction nor asserts experimental assembly compatibility. Length
    limits and fixed materials are molecular permissions; batches and search-node
    quotas do not belong here. Placements are joint left/right permissions.
    """

    schema_id: Literal["hop.interface-survey/v2"] = Field(alias="schema")
    source_context_objective: Literal["all_words", "paired_scaffold_completions"] = Field(
        default="all_words", exclude_if=lambda value: value == "all_words"
    )
    name: str | None = None
    preferred_preparation: SurveyPreparationReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    stem_arm: str
    targets: InterfaceTargetDomain
    interfaces: SurveyInterfaces
    placements: tuple[EndPlacement, ...] = Field(min_length=1)
    foldback: SurveyFoldback
    basal: SurveyBasal
    release: SurveyRelease
    enzyme_catalog: CharacterizedEnzymeCatalog
    materialization: LinearSourceMaterializationSpec
    local_constraints: ConstructionConstraints
    preferences: ConstructionPreferences = ConstructionPreferences()
    whole_route_constraints: WholeRouteConstraints
    source_cleanup: SacrificialFragmentPolicy | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def bind_method_permissions(self) -> "InterfaceSurveyRequest":
        if self.preferred_preparation is not None and (
            self.source_context_objective != "paired_scaffold_completions"
        ):
            raise ValueError("A preferred preparation requires paired_scaffold_completions.")
        for job in (self.foldback, self.basal, self.release):
            EnzymeProvisioningPolicy(
                catalog=self.enzyme_catalog, **job.enzymes.model_dump(mode="python")
            )
        if (self.preferred_source_contexts or self.source_handle_seed is not None) and (
            self.source_context_objective != "paired_scaffold_completions"
            or not isinstance(
                self.materialization.source_preparation.source_ssdna, ConstrainedSourceSsdnaPolicy
            )
        ):
            raise ValueError(
                "Source-context preferences require paired_scaffold_completions "
                "and a constrained source-context domain."
            )
        return self

    @field_validator("stem_arm")
    @classmethod
    def exact_stem(cls, value: str) -> str:
        return normalize_dna_sequence(value, allow_degenerate=False)

    @field_validator("placements")
    @classmethod
    def joint_placements(cls, values: tuple[EndPlacement, ...]) -> tuple[EndPlacement, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Joint end placements must not repeat.")
        return tuple(sorted(values, key=lambda value: (value.left_bp, value.right_bp)))

"""Optional molecular intent, separately resolved against explicit construction permissions."""

from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import CharacterizedEnzymeCatalog
from hop_design.models.sequence import normalize_dna_sequence

from ..comparisons.materials import SelectedPreparationReference
from ..complete.request import WholeRouteConstraints
from ..complete.source_preparation import LinearSourceMaterializationSpec
from ..components import ExactBasalArms
from ..discovery.placement import EndPlacement
from ..scaffold import HairpinScaffoldRequirements
from ..source_partition.policy import SacrificialFragmentPolicy
from ..surveys.request import (
    SourceContextPreference,
    SurveyBasal,
    SurveyFoldback,
    SurveyInterfaces,
    SurveyRelease,
)
from ..targets import ConstructionConstraints, ConstructionPreferences


class ConstructionPermissions(HopModel):
    """Payload-independent molecular permissions, with no execution quotas."""

    schema_id: Literal["hop.construction-context/v1"] = Field(alias="schema")
    context_id: str
    description: str
    foldback: SurveyFoldback
    enzyme_catalog: CharacterizedEnzymeCatalog
    materialization: LinearSourceMaterializationSpec
    local_constraints: ConstructionConstraints
    preferences: ConstructionPreferences
    whole_route_constraints: WholeRouteConstraints
    source_cleanup: SacrificialFragmentPolicy | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class ConstructionContext(ConstructionPermissions, SourceContextPreference):
    """Released-insert permissions include the two downstream release interfaces."""

    product: Literal["released_insert"]
    basal: SurveyBasal
    release: SurveyRelease
    interfaces: SurveyInterfaces
    placements: tuple[EndPlacement, ...] = Field(min_length=1)
    source_context_objective: Literal["all_words", "paired_scaffold_completions"]


class HairpinConstructionContext(ConstructionPermissions):
    """Hairpin endpoint permissions never include a downstream release requirement."""

    product: Literal["hairpin", "adapter_ligated_hairpin"]
    basal: SurveyBasal | None = None
    hairpin_basal_component: ExactBasalArms | None = None


class OptionalEndWords(HopModel):
    """Exact words or independent alternatives; omitted sides are unconstrained."""

    left: str | tuple[str, ...] | None = Field(default=None)
    right: str | tuple[str, ...] | None = Field(default=None)

    @field_validator("left", "right")
    @classmethod
    def exact_word(cls, value: str | tuple[str, ...] | None) -> str | tuple[str, ...] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("An end word must contain DNA bases; omit it for no preference.")
        if isinstance(value, str):
            return normalize_dna_sequence(value, allow_degenerate=False)
        words = tuple(normalize_dna_sequence(w, allow_degenerate=False) for w in value)
        if not 1 <= len(words) <= 256 or len(set(words)) != len(words) or any(not w for w in words):
            raise ValueError("End alternatives must be distinct nonempty words.")
        return tuple(sorted(words))


class ConstructionMethodChoices(HopModel):
    """Method names or exact catalog IDs, restricted within context permissions."""

    foldback: tuple[str, ...] | None = Field(default=None, min_length=1)
    basal: tuple[str, ...] | None = Field(default=None, min_length=1)
    release: tuple[str, ...] | None = Field(default=None, min_length=1)


class ConstructionIntentRequirements(HopModel):
    """Shared product requirements for an exact stem or an explicit finite family."""

    product: Literal["released_insert", "hairpin", "adapter_ligated_hairpin"]
    context: str | ConstructionContext | HairpinConstructionContext | None = None
    ends: OptionalEndWords | None = None
    scaffold: HairpinScaffoldRequirements | None = None
    loop_words: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=256)
    methods: ConstructionMethodChoices = ConstructionMethodChoices()
    end_placements: tuple[EndPlacement, ...] | None = Field(default=None, min_length=1)

    @field_validator("loop_words")
    @classmethod
    def normalize_loops(cls, words: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if words is None:
            return None
        normalized = tuple(normalize_dna_sequence(w, allow_degenerate=False) for w in words)
        if len(set(normalized)) != len(normalized):
            raise ValueError("Loop words must not repeat.")
        return normalized

    @model_validator(mode="after")
    def distinct_placements(self) -> Self:
        if self.product != "released_insert" and (
            self.ends is not None
            or self.end_placements is not None
            or self.methods.release is not None
        ):
            raise ValueError(
                "End words, end placements and release methods apply to a released insert, "
                "not this hairpin endpoint."
            )
        if self.end_placements is not None and len(set(self.end_placements)) != len(
            self.end_placements
        ):
            raise ValueError("Joint end placements must not repeat.")
        return self


class ConstructionIntent(ConstructionIntentRequirements):
    """An exact stem and intended product; absent end words express no preference."""

    schema_id: Literal["hop.construction-intent/v1"] = Field(
        default="hop.construction-intent/v1", alias="schema"
    )
    stem_arm: str
    prefer_preparation: SelectedPreparationReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def preference_endpoint(self) -> Self:
        if self.prefer_preparation is not None and self.product != "released_insert":
            raise ValueError("A preparation preference currently requires a released insert.")
        return self

    @field_validator("stem_arm")
    @classmethod
    def normalize_stem(cls, value: str) -> str:
        normalized = normalize_dna_sequence(value, allow_degenerate=True)
        if any(base not in "ACGT" for base in normalized):
            raise ValueError(
                "An exact intent needs A/C/G/T. For required exact members from an IUPAC "
                "stem, use hop.construction-family-intent/v1 with max_members and "
                "max_total_evaluations; resolve it to preview membership before searching."
            )
        return normalized

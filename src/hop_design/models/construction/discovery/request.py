"""Desired scaffold properties remain separate from permitted preparation edits."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import normalize_dna_sequence

from ..product_request import ProductEnds, ProductRequest
from ..scaffold import HairpinScaffoldRequirements
from ..variants.objective import DesignSearchObjective
from ..variants.parameters import ParameterSelection, validate_selections
from .placement import EndPlacement
from .targets import ScaffoldSearchTarget


class PreparationChanges(HopModel):
    basal_nick_enzyme_ids: tuple[str, ...] | None = Field(
        default=None, min_length=1, max_length=16, exclude_if=lambda v: v is None
    )
    adapter_redesign: Literal["preserve", "allow"] = "preserve"
    release_enzyme_ids: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=16)
    three_prime_tail_sequences: tuple[str, ...] | None = Field(
        default=None, min_length=1, max_length=64, exclude_if=lambda value: value is None
    )

    @field_validator("three_prime_tail_sequences")
    @classmethod
    def exact_tails(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if value is None:
            return None
        words = tuple(
            normalize_dna_sequence(word, allow_degenerate=False) if word else "" for word in value
        )
        if len(set(words)) != len(words):
            raise ValueError("Permitted terminal sequences must not repeat.")
        return words

    @model_validator(mode="after")
    def distinct_methods(self) -> "PreparationChanges":
        if self.basal_nick_enzyme_ids is not None and len(set(self.basal_nick_enzyme_ids)) != len(
            self.basal_nick_enzyme_ids
        ):
            raise ValueError("Permitted basal nickase identities must not repeat.")
        if self.release_enzyme_ids is not None and len(set(self.release_enzyme_ids)) != len(
            self.release_enzyme_ids
        ):
            raise ValueError("Permitted release enzyme identities must not repeat.")
        return self


class ScaffoldDiscoveryRequest(HopModel):
    schema_id: Literal[
        "hop.scaffold-discovery/v1",
        "hop.scaffold-discovery/v2",
        "hop.scaffold-discovery/v3",
        "hop.scaffold-discovery/v4",
        "hop.scaffold-discovery/v5",
        "hop.scaffold-discovery/v6",
        "hop.scaffold-discovery/v7",
    ] = Field(alias="schema")
    product: ProductRequest
    receiving_end_pairs: tuple[ProductEnds, ...] | None = Field(
        default=None, min_length=1, max_length=64, exclude_if=lambda v: v is None
    )
    end_placements: tuple[EndPlacement, ...] | None = Field(
        default=None, min_length=1, max_length=64, exclude_if=lambda v: v is None
    )
    scaffold: HairpinScaffoldRequirements | None = None
    preparation_changes: PreparationChanges = PreparationChanges()
    comparison_stage: Literal["hairpin", "endpoint"]
    max_branches: int = Field(ge=1, le=64)
    max_continuations_per_branch: int = Field(ge=1, le=64)
    required_targets: tuple[ScaffoldSearchTarget, ...] = Field(
        default=(), max_length=64, exclude_if=lambda value: not value
    )
    parameters: tuple[ParameterSelection, ...] = Field(
        default=(), max_length=128, exclude_if=lambda values: not values
    )

    objective: DesignSearchObjective | None = Field(default=None, exclude_if=lambda v: v is None)

    @model_validator(mode="after")
    def terminal_translation_version(self) -> "ScaffoldDiscoveryRequest":
        if self.objective is not None and self.schema_id != "hop.scaffold-discovery/v7":
            raise ValueError("Diversity objectives require hop.scaffold-discovery/v7.")
        if self.parameters and self.schema_id not in (
            "hop.scaffold-discovery/v5",
            "hop.scaffold-discovery/v6",
            "hop.scaffold-discovery/v7",
        ):
            raise ValueError("Molecular parameter restrictions require hop.scaffold-discovery/v5.")
        validate_selections(self.parameters)
        if self.required_targets and self.schema_id not in (
            "hop.scaffold-discovery/v3",
            "hop.scaffold-discovery/v4",
            "hop.scaffold-discovery/v5",
            "hop.scaffold-discovery/v6",
            "hop.scaffold-discovery/v7",
        ):
            raise ValueError("Required-member scheduling requires hop.scaffold-discovery/v3.")
        if (
            self.end_placements is not None
            or self.preparation_changes.basal_nick_enzyme_ids is not None
        ) and self.schema_id not in (
            "hop.scaffold-discovery/v4",
            "hop.scaffold-discovery/v5",
            "hop.scaffold-discovery/v6",
            "hop.scaffold-discovery/v7",
        ):
            raise ValueError(
                "End placement and nickase alternatives require hop.scaffold-discovery/v4."
            )
        if self.end_placements is not None and len(set(self.end_placements)) != len(
            self.end_placements
        ):
            raise ValueError("End placements must be distinct.")
        if self.receiving_end_pairs is not None:
            if self.schema_id not in ("hop.scaffold-discovery/v6", "hop.scaffold-discovery/v7"):
                raise ValueError("Receiving-end alternatives require hop.scaffold-discovery/v6.")
            if self.product.ends is None or self.product.release is None:
                raise ValueError("Receiving-end alternatives require a released-insert product.")
            if self.end_placements is not None:
                raise ValueError("Declare placements within receiving_end_pairs, not separately.")
            if len(set(self.receiving_end_pairs)) != len(self.receiving_end_pairs):
                raise ValueError("Receiving-end pairs must be distinct joint tuples.")
        inherited = self.product.whole_route_constraints.hairpin_scaffold
        terminal = any(
            requirement is not None
            and (
                requirement.five_prime_unpaired_nt is not None
                or requirement.three_prime_unpaired_nt is not None
            )
            for requirement in (self.scaffold, inherited)
        )
        if self.schema_id.endswith("/v1") and (
            terminal or self.preparation_changes.three_prime_tail_sequences is not None
        ):
            raise ValueError("Terminal scaffold discovery requires hop.scaffold-discovery/v2.")
        if self.preparation_changes.three_prime_tail_sequences is not None and (
            not terminal or self.preparation_changes.adapter_redesign != "allow"
        ):
            raise ValueError(
                "Terminal sequences require terminal requirements "
                "and explicit adapter redesign permission."
            )
        return self

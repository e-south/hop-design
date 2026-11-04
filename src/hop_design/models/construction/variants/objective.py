"""Explicit search priorities, separate from molecular requirements and permissions."""

from typing import Literal

from pydantic import Field, field_validator

from hop_design.models.base import HopModel

from .parameters import parameter_definition

INTERFACE_DIVERSITY_PARAMETERS = frozenset(
    {"left_gap", "right_gap", "left_end_word", "right_end_word"}
)

DIVERSITY_PARAMETERS = frozenset(
    {
        "foldback_arm_bp",
        "join_offset_nt",
        "loop_nt",
        "loop_word",
        "foldback_strand",
        "basal_nick_offset_nt",
        "adapter_annealing_min_nt",
        "release_method",
        "foldback_method",
        "basal_method",
        "left_gap",
        "right_gap",
        "left_end_word",
        "right_end_word",
    }
)


class DesignSearchObjective(HopModel):
    """Seek contrasts in named dimensions; a finite run does not guarantee coverage."""

    kind: Literal["diversity"]
    parameters: tuple[str, ...] = Field(min_length=1, max_length=len(DIVERSITY_PARAMETERS))

    @property
    def explores_interfaces(self) -> bool:
        return bool(INTERFACE_DIVERSITY_PARAMETERS.intersection(self.parameters))

    @property
    def varies_foldback_members(self) -> bool:
        return "loop_word" in self.parameters

    @property
    def varies_local_methods(self) -> bool:
        return bool({"foldback_method", "basal_method"}.intersection(self.parameters))

    @property
    def target_policy(self) -> str:
        if self.explores_interfaces:
            return "joint_interface_relations/v9"
        if self.varies_local_methods:
            return "within_target/v6"
        if self.varies_foldback_members:
            return "within_target/v5"
        if {"foldback_arm_bp", "join_offset_nt", "loop_nt", "foldback_strand"}.intersection(
            self.parameters
        ):
            return "within_target/v3"
        return "within_target/v2"

    @field_validator("parameters")
    @classmethod
    def independent_dimensions(cls, parameters: tuple[str, ...]) -> tuple[str, ...]:
        canonical = tuple(parameter_definition(key).canonical_key for key in parameters)
        if len(set(canonical)) != len(canonical):
            raise ValueError("Repeated or equivalent diversity parameters must be declared once.")
        if {"loop_nt", "loop_word"} <= set(canonical):
            raise ValueError("Loop word already determines loop size; choose one diversity axis.")
        for key in canonical:
            parameter_definition(key)
            if key not in DIVERSITY_PARAMETERS:
                raise ValueError(
                    f"Diversity-directed search does not yet target parameter {key!r}."
                )
        return tuple(sorted(canonical))

"""Explicit per-evaluation safeguards, separate from the molecular survey scope."""

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.construction.sequence_sets import SequenceSpaceLimits
from hop_design.models.construction.variants.objective import DesignSearchObjective

DEFAULT_SEQUENCE_LIMITS = SequenceSpaceLimits(
    max_cases=100_000,
    max_programs=100_000,
    max_decisions=100_000,
    max_set_operations=1_000_000,
    max_site_checks=1_000_000,
    max_result_decisions=1_000_000,
)


class SurveyEvaluationLimits(HopModel):
    """A resource stop leaves the corresponding molecular search unresolved."""

    scheduling: Literal["coverage", "discovery"] = Field(
        default="coverage", exclude_if=lambda value: value == "coverage"
    )
    objective: DesignSearchObjective | None = Field(default=None, exclude_if=lambda v: v is None)
    navigation_nodes: int = Field(default=256, ge=1, le=100_000)
    navigation_frontier: int = Field(
        default=4096, ge=1, le=100_000, exclude_if=lambda value: value == 4096
    )
    continuation_batch_size: int = Field(default=1, ge=1, le=1024)

    local_nodes: int = Field(ge=1, le=100_000)
    local_realizations: int = Field(ge=1, le=100_000)
    release_site_pairs: int = Field(ge=1)
    sequence_decisions: int = Field(default=DEFAULT_SEQUENCE_LIMITS.max_decisions, ge=1, le=100_000)
    sequence_operations: int = Field(
        default=DEFAULT_SEQUENCE_LIMITS.max_set_operations, ge=1, le=1_000_000
    )
    sequence_site_checks: int = Field(
        default=DEFAULT_SEQUENCE_LIMITS.max_site_checks, ge=1, le=1_000_000
    )
    sequence_result_decisions: int = Field(
        default=DEFAULT_SEQUENCE_LIMITS.max_result_decisions, ge=1, le=1_000_000
    )

    @property
    def sequence_space_limits(self) -> SequenceSpaceLimits:
        return DEFAULT_SEQUENCE_LIMITS.model_copy(
            update={
                "max_decisions": self.sequence_decisions,
                "max_set_operations": self.sequence_operations,
                "max_site_checks": self.sequence_site_checks,
                "max_result_decisions": self.sequence_result_decisions,
            }
        )

"""Execution effort is separate from the molecular request and examined prefix."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from ..variants.query import Digest


class HairpinExecution(HopModel):
    schema_id: Literal["hop.hairpin-design-execution/v1", "hop.hairpin-design-execution/v2"] = (
        Field(default="hop.hairpin-design-execution/v1", alias="schema")
    )
    max_evaluations: int = Field(ge=1, le=64)
    first_choices: int | None = Field(default=None, ge=1)
    previous_evaluated_pairs: int = Field(ge=0)
    evaluated_pairs: int = Field(ge=0)
    previous_snapshot_digest: Digest | None = None
    snapshot_digest: Digest
    stopping_reason: Literal[
        "first_choices", "evaluation_limit", "recorded_pairs_examined", "cancelled"
    ]

    @model_validator(mode="after")
    def validate_progress(self) -> "HairpinExecution":
        if (
            self.schema_id.endswith("/v1")
            and max(self.previous_evaluated_pairs, self.evaluated_pairs) > 64
        ):
            raise ValueError("Legacy cumulative snapshots support at most 64 attempts.")
        if not 0 <= self.evaluated_pairs - self.previous_evaluated_pairs <= self.max_evaluations:
            raise ValueError("Execution exceeds its declared evaluation effort.")
        if self.stopping_reason == "first_choices" and self.first_choices is None:
            raise ValueError("A first-choice stop requires an explicit choice count.")
        if self.stopping_reason == "cancelled" and (
            self.evaluated_pairs == self.previous_evaluated_pairs
        ):
            raise ValueError("Cancellation before new work does not publish a molecular snapshot.")
        return self

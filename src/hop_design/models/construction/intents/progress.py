"""Transient discovery feedback describes committed work, never inferred coverage."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel


class DiscoveryProgress(HopModel):
    schema_id: Literal["hop.discovery-progress/v1"] = Field(
        default="hop.discovery-progress/v1", alias="schema"
    )
    product: Literal["released_insert", "hairpin", "adapter_ligated_hairpin"]
    phase: Literal["searching", "checkpointed", "stopped"]
    evaluations: int = Field(ge=0)
    new_evaluations: int = Field(ge=0)
    evaluation_budget: int = Field(ge=1)
    termination_reason: str | None = None

    @model_validator(mode="after")
    def committed_bounds(self) -> "DiscoveryProgress":
        if self.new_evaluations > min(self.evaluations, self.evaluation_budget):
            raise ValueError("Progress cannot exceed committed work or the execution budget.")
        if (self.phase == "stopped") != (self.termination_reason is not None):
            raise ValueError("Only stopped progress carries a termination reason.")
        return self

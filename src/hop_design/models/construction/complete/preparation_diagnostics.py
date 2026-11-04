"""Typed facts explaining one failed molecular preparation constraint."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

type PreparationConstraintCode = Literal[
    "primer-annealing-span-exceeded",
    "primer-length-bounds-incompatible",
    "fixed-source-sequence-mismatch",
    "fixed-source-route-mismatch",
    "fixed-primer-binding-mismatch",
    "fixed-primer-end-chemistry-mismatch",
    "source-primer-handle-unsupported",
    "prepared-duplex-sequence-mismatch",
    "fixed-adapter-sequence-mismatch",
]


class PreparationConstraintDiagnostic(HopModel):
    """An observed failed condition, not a uniquely necessary repair."""

    code: PreparationConstraintCode
    stage: Literal["source-duplex-preparation", "endpoint-auxiliary-preparation"] = (
        "source-duplex-preparation"
    )
    field: str = Field(
        pattern=(
            r"^materialization\.(?:source_preparation|endpoint_auxiliaries)\."
            r"[a-z_][a-z_0-9]*(?:\.[a-z_][a-z_0-9]*)*$"
        )
    )
    requirement: Literal["at-most", "equals", "starts-with", "matches-route"]
    requested: int | str
    available: int | str | None
    message: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_values(self) -> PreparationConstraintDiagnostic:
        adapter = self.code == "fixed-adapter-sequence-mismatch"
        expected_stage = (
            "endpoint-auxiliary-preparation" if adapter else "source-duplex-preparation"
        )
        expected_owner = "endpoint_auxiliaries" if adapter else "source_preparation"
        if self.stage != expected_stage or not self.field.startswith(
            f"materialization.{expected_owner}."
        ):
            raise ValueError(
                "Preparation diagnostics must identify their exact processing stage and field."
            )
        expected_requirement = (
            "at-most"
            if self.code in {"primer-annealing-span-exceeded", "primer-length-bounds-incompatible"}
            else "starts-with"
            if adapter
            else "matches-route"
            if self.code == "fixed-source-route-mismatch"
            else "equals"
        )
        if self.requirement != expected_requirement:
            raise ValueError("Preparation diagnostic comparison must match its exact constraint.")
        if self.code in {"primer-annealing-span-exceeded", "primer-length-bounds-incompatible"}:
            if (
                type(self.requested) is not int
                or type(self.available) is not int
                or self.available < 0
                or self.requested <= self.available
            ):
                raise ValueError("Primer span diagnostics require requested > available >= 0.")
        elif not isinstance(self.requested, str) or (
            self.available is not None and not isinstance(self.available, str)
        ):
            raise ValueError("Sequence and chemistry diagnostics require exact string values.")
        if (self.available is None) != (self.code == "fixed-source-route-mismatch"):
            raise ValueError("Only a fixed source route mismatch lacks a unique available value.")
        return self


def validate_preparation_constraint(
    reason: str | None, diagnostic: PreparationConstraintDiagnostic | None
) -> None:
    """Keep the optional explanation attached to its original rejection class."""
    if reason == "source-preparation-incompatible":
        if diagnostic is None or diagnostic.stage != "source-duplex-preparation":
            raise ValueError(
                "Source preparation rejections require an exact constraint diagnostic."
            )
    elif diagnostic is not None and not (
        reason == "pcr-adapter-mismatch" and diagnostic.stage == "endpoint-auxiliary-preparation"
    ):
        raise ValueError("Preparation constraint diagnostics must match their rejection class.")

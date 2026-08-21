"""Authored HOP design intent."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.basal import BasalDesignRequest
from hop_design.models.base import HopModel
from hop_design.models.foldback import FoldbackEvaluationRequest
from hop_design.models.payload import Payload
from hop_design.models.references import ExternalRef, ReferenceId
from hop_design.models.stem import PairedStemExtensionRequest
from hop_design.models.strand_state import ReleaseProjectionRequest


class FoldbackSelection(HopModel):
    """An explicit foldback-junction selection."""

    ref: ReferenceId


class BasalSelection(HopModel):
    """An explicit basal-junction selection."""

    ref: ReferenceId


class JunctionRequest(HopModel):
    """Authored selections for the two physical HOP junctions."""

    foldback: FoldbackSelection
    basal: BasalSelection


class DesignLimits(HopModel):
    """Explicit limits that prevent unbounded design enumeration."""

    max_candidates: int = Field(ge=1, le=100_000)


class HopSpec(HopModel):
    """The immutable, manually authored source of design intent."""

    schema_id: Literal["hop.design/v1"] = Field(default="hop.design/v1", alias="schema")
    design_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    payload: Payload
    junction: JunctionRequest
    processing_route_ref: ReferenceId
    constraint_profile_ref: ReferenceId
    defaults_ref: ReferenceId
    constraints: DesignLimits
    external_refs: tuple[ExternalRef, ...] = ()


class ResolvedHopSpec(HopModel):
    """Authored intent with explicit junction and already-resolved event inputs."""

    schema_id: Literal["hop.resolved-design/v1"] = Field(
        default="hop.resolved-design/v1", alias="schema"
    )
    design_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    payload: Payload
    foldback: FoldbackEvaluationRequest
    basal: BasalDesignRequest
    stem_extension: PairedStemExtensionRequest | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    release: ReleaseProjectionRequest | None
    defaults_ref: ReferenceId
    catalog_ref: ReferenceId
    constraint_profile_ref: ReferenceId
    processing_route_ref: ReferenceId
    constraints: DesignLimits
    external_refs: tuple[ExternalRef, ...] = ()

    @model_validator(mode="after")
    def validate_event_dependencies(self) -> ResolvedHopSpec:
        if self.release is not None and self.basal.terminal_nick is None:
            raise ValueError(
                "A release event requires a terminal nick in the resolved processing route."
            )
        return self


DesignSpec = HopSpec | ResolvedHopSpec

"""Authored HOP design intent."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.basal_policy import BasalDesignRequest
from hop_design.models.base import HopModel
from hop_design.models.foldback import FoldbackEvaluationRequest
from hop_design.models.junction import (
    BasalJunction,
    FoldbackJunction,
    derive_exact_basal_junction_id,
    derive_exact_foldback_junction_id,
)
from hop_design.models.payload import ExactPayload, Payload
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

    schema_id: Literal["hop.design/v2"] = Field(default="hop.design/v2", alias="schema")
    design_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    payload: Payload
    junction: JunctionRequest
    design_derivation_ref: ReferenceId
    constraint_profile_ref: ReferenceId
    defaults_ref: ReferenceId
    constraints: DesignLimits
    external_refs: tuple[ExternalRef, ...] = ()


class ResolvedHopSpec(HopModel):
    """Authored intent with explicit component and strand-projection inputs."""

    schema_id: Literal["hop.resolved-design/v2"] = Field(
        default="hop.resolved-design/v2", alias="schema"
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
    design_derivation_ref: ReferenceId
    constraints: DesignLimits
    external_refs: tuple[ExternalRef, ...] = ()

    @model_validator(mode="after")
    def validate_projection_dependencies(self) -> ResolvedHopSpec:
        if self.release is not None and self.basal.terminal_nick is None:
            raise ValueError(
                "A release projection requires terminal-nick geometry in the design derivation."
            )
        return self


class ExactJunctionDesignSpec(HopModel):
    """Exact route-neutral junction components used to derive one design authority."""

    schema_id: Literal["hop.exact-junction-design/v1"] = Field(
        default="hop.exact-junction-design/v1", alias="schema"
    )
    design_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    payload: ExactPayload
    foldback_junction: FoldbackJunction
    basal_junction: BasalJunction
    defaults_ref: Literal["hop:defaults/exact-junction-components@1"] = (
        "hop:defaults/exact-junction-components@1"
    )
    catalog_ref: Literal["hop:catalog/exact-junction-components@1"] = (
        "hop:catalog/exact-junction-components@1"
    )
    constraint_profile_ref: Literal["hop:constraints/exact-junction-components@1"] = (
        "hop:constraints/exact-junction-components@1"
    )
    design_derivation_ref: Literal["hop:derivation/exact-junction-components@1"] = (
        "hop:derivation/exact-junction-components@1"
    )
    external_refs: tuple[ExternalRef, ...] = ()

    @model_validator(mode="after")
    def validate_junction_identities(self) -> ExactJunctionDesignSpec:
        foldback = self.foldback_junction
        expected_foldback = derive_exact_foldback_junction_id(
            sequence=foldback.sequence,
            retained_nt=foldback.retained_tract_span.length.value,
            turn_nt=foldback.turn_span.length.value,
            pairs=foldback.pairs,
        )
        if foldback.junction_id != expected_foldback:
            raise ValueError("Exact foldback junction must use its content-derived identity.")
        basal = self.basal_junction
        expected_basal = derive_exact_basal_junction_id(
            left_arm=basal.left_arm,
            right_arm=basal.right_arm,
            pairs=basal.pairs,
        )
        if basal.junction_id != expected_basal:
            raise ValueError("Exact basal junction must use its content-derived identity.")
        return self


DesignSpec = HopSpec | ResolvedHopSpec
DesignAuthoritySpec = DesignSpec | ExactJunctionDesignSpec

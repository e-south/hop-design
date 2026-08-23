"""Resolved, non-temporal design-derivation contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from hop_design.models.basal_policy import BasalEvaluation
from hop_design.models.base import HopModel
from hop_design.models.foldback import FoldbackEvaluation
from hop_design.models.junction import BasalJunction, FoldbackJunction
from hop_design.models.references import ReferenceId
from hop_design.models.stem import PairedStemExtension
from hop_design.models.strand_state import NickEvent, ReleasedStrandState


class CatalogJunctionDerivation(HopModel):
    """Catalog-selected junctions used to derive one encoding."""

    derivation_id: ReferenceId
    kind: Literal["catalog_junctions"] = "catalog_junctions"
    description: str = Field(min_length=1)
    catalog_ref: ReferenceId
    foldback_junction: FoldbackJunction
    basal_junction: BasalJunction


class EvaluatedComponentDerivation(HopModel):
    """Evaluated caller-supplied components with no production-method claim."""

    derivation_id: ReferenceId
    kind: Literal["evaluated_components"] = "evaluated_components"
    description: str = Field(min_length=1)
    catalog_ref: ReferenceId
    foldback: FoldbackEvaluation
    basal: BasalEvaluation
    stem_extension: PairedStemExtension | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def validate_components(self) -> EvaluatedComponentDerivation:
        if self.foldback.report.has_errors:
            raise ValueError("Component derivation requires a feasible foldback evaluation.")
        if self.basal.decision.status == "reject":
            raise ValueError("Component derivation cannot contain a rejected basal evaluation.")
        return self


class ResolvedJunctionDerivation(HopModel):
    """Junction geometry derived from exact component and strand projections."""

    derivation_id: ReferenceId
    kind: Literal["resolved_junction_geometry"] = "resolved_junction_geometry"
    description: str = Field(min_length=1)
    catalog_ref: ReferenceId
    foldback: FoldbackEvaluation
    basal: BasalEvaluation
    stem_extension: PairedStemExtension | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    terminal_nick: NickEvent
    released_foldback_source: ReleasedStrandState | None

    @model_validator(mode="after")
    def validate_geometry(self) -> ResolvedJunctionDerivation:
        if self.foldback.report.has_errors:
            raise ValueError("Junction derivation requires a feasible foldback evaluation.")
        if self.basal.decision.status == "reject":
            raise ValueError("Junction derivation cannot contain a rejected basal evaluation.")
        if self.terminal_nick.boundary.offset != len(self.basal.junction.left_arm):
            raise ValueError("Resolved terminal nick boundary must equal the basal arm length.")
        if (
            self.released_foldback_source is not None
            and self.released_foldback_source.active_product_sequence
            != self.foldback.precursor_sequence
        ):
            raise ValueError("Released active product must equal the foldback precursor input.")
        if (
            self.released_foldback_source is not None
            and self.released_foldback_source.active_strand is self.terminal_nick.strand
        ):
            raise ValueError(
                "Released active strand and basal surviving strand must form one continuous strand."
            )
        return self


PlanDesignDerivation = Annotated[
    CatalogJunctionDerivation | EvaluatedComponentDerivation | ResolvedJunctionDerivation,
    Field(discriminator="kind"),
]


__all__ = [
    "CatalogJunctionDerivation",
    "EvaluatedComponentDerivation",
    "PlanDesignDerivation",
    "ResolvedJunctionDerivation",
]

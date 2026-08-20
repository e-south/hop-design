"""Strict precursor-event and released-strand-state contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport
from hop_design.models.junction import Strand
from hop_design.models.sequence import (
    SequenceValidationError,
    normalize_dna_sequence,
    reverse_complement_iupac,
)


class StrandExposureRoute(StrEnum):
    """The active strand after a nick and duplex release event."""

    BOTTOM_ACTIVE_AFTER_TOP_NICK = "bottom_active_after_top_nick"
    TOP_ACTIVE_AFTER_BOTTOM_NICK = "top_active_after_bottom_nick"


class NickEvent(HopModel):
    """One strand-specific nick at a zero-based precursor boundary."""

    boundary: Boundary
    strand: Strand


class DuplexCut(HopModel):
    """Top- and bottom-strand cut boundaries from one release event."""

    top: Boundary
    bottom: Boundary


class ReleaseProjectionConstraints(HopModel):
    """Explicit policy gates for physical release projection."""

    require_release_site_downstream_of_nick: bool
    require_complete_downstream_separation: bool


class ReleaseProjectionRequest(HopModel):
    """A precursor plus already-resolved nick and release events."""

    precursor_top_strand: str
    origin: Boundary
    nick: NickEvent
    release_cut: DuplexCut
    release_site_span: Span | None
    route: StrandExposureRoute
    constraints: ReleaseProjectionConstraints

    @field_validator("precursor_top_strand", mode="before")
    @classmethod
    def normalize_precursor(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_route(self) -> ReleaseProjectionRequest:
        if self.origin.offset > len(self.precursor_top_strand):
            raise ValueError("origin must stay inside the precursor sequence.")
        if (
            self.route is StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK
            and self.nick.strand is not Strand.TOP
        ):
            raise ValueError("bottom-active route requires a top-strand nick.")
        if (
            self.route is StrandExposureRoute.TOP_ACTIVE_AFTER_BOTTOM_NICK
            and self.nick.strand is not Strand.BOTTOM
        ):
            raise ValueError("top-active route requires a bottom-strand nick.")
        return self


class BaseLineage(HopModel):
    """One active-product base traced to a precursor strand and index."""

    active_index: int
    precursor_strand: Strand
    precursor_index: int


class ReleasedStrandState(HopModel):
    """The fully derived strand state after one resolved release event."""

    route: StrandExposureRoute
    precursor_top_strand: str
    active_strand: Strand
    retained_partner_strand: Strand
    nick: NickEvent
    release_cut: DuplexCut
    active_product_precursor_span: Span
    active_nick_boundary: Boundary
    active_product_sequence: str
    retained_partner_sequence: str
    active_product_lineage: tuple[BaseLineage, ...]

    @field_validator("precursor_top_strand", mode="before")
    @classmethod
    def normalize_precursor(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @field_validator("active_product_sequence", "retained_partner_sequence", mode="before")
    @classmethod
    def normalize_product(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        if not value or value.isspace():
            return ""
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_state(self) -> ReleasedStrandState:
        if self.active_strand is self.retained_partner_strand:
            raise ValueError("Active and retained-partner strands must differ.")
        if self.route is StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK:
            expected_active_strand = Strand.BOTTOM
            expected_partner_strand = Strand.TOP
            expected_nicked_strand = Strand.TOP
        else:
            expected_active_strand = Strand.TOP
            expected_partner_strand = Strand.BOTTOM
            expected_nicked_strand = Strand.BOTTOM
        if (
            self.active_strand is not expected_active_strand
            or self.retained_partner_strand is not expected_partner_strand
            or self.nick.strand is not expected_nicked_strand
        ):
            raise ValueError("Released-state strand roles must derive from the exposure route.")
        precursor_nt = len(self.precursor_top_strand)
        if (
            self.release_cut.top.offset > precursor_nt
            or self.release_cut.bottom.offset > precursor_nt
        ):
            raise ValueError("Released-state cuts must stay inside the precursor sequence.")
        active_cut = (
            self.release_cut.top.offset
            if self.active_strand is Strand.TOP
            else self.release_cut.bottom.offset
        )
        origin = self.active_product_precursor_span.start.offset
        if self.active_product_precursor_span.end.offset != active_cut:
            raise ValueError("Active-product span must end at the active-strand release cut.")
        if origin > self.nick.boundary.offset or self.nick.boundary.offset > active_cut:
            raise ValueError("Released-state origin, nick, and active cut must be ordered.")
        active_top_slice = self.precursor_top_strand[origin:active_cut]
        expected_active_sequence = (
            active_top_slice
            if self.active_strand is Strand.TOP
            else reverse_complement_iupac(active_top_slice)
        )
        if self.active_product_sequence != expected_active_sequence:
            raise ValueError("Active-product sequence must derive from the precursor and route.")
        retained_top_prefix = self.precursor_top_strand[: self.nick.boundary.offset]
        expected_partner_sequence = (
            retained_top_prefix
            if self.retained_partner_strand is Strand.TOP
            else reverse_complement_iupac(retained_top_prefix)
        )
        if self.retained_partner_sequence != expected_partner_sequence:
            raise ValueError("Retained-partner sequence must derive from the precursor and route.")
        expected_nick_boundary = (
            self.nick.boundary.offset - origin
            if self.active_strand is Strand.TOP
            else active_cut - self.nick.boundary.offset
        )
        if self.active_nick_boundary.offset != expected_nick_boundary:
            raise ValueError("Active nick boundary must use active-product orientation.")
        if self.active_product_precursor_span.length.value != len(self.active_product_sequence):
            raise ValueError("Active-product span length must match its sequence.")
        if len(self.active_product_lineage) != len(self.active_product_sequence):
            raise ValueError("Active-product lineage must cover every active-product base.")
        if self.active_nick_boundary.offset > len(self.active_product_sequence):
            raise ValueError("Active nick boundary must stay inside the active product.")
        for index, lineage in enumerate(self.active_product_lineage):
            if lineage.active_index != index:
                raise ValueError("Active-product lineage indexes must be contiguous.")
            if lineage.precursor_strand is not self.active_strand:
                raise ValueError("Active-product lineage must reference the active strand.")
            if self.active_strand is Strand.TOP:
                expected_precursor_index = self.active_product_precursor_span.start.offset + index
            else:
                expected_precursor_index = self.active_product_precursor_span.end.offset - 1 - index
            if lineage.precursor_index != expected_precursor_index:
                raise ValueError(
                    "Active-product lineage must preserve strand-oriented precursor coordinates."
                )
        return self


class ReleaseProjectionResult(HopModel):
    """Either one released strand state or actionable infeasibility diagnostics."""

    report: CheckReport
    projection: ReleasedStrandState | None

    @model_validator(mode="after")
    def validate_result(self) -> ReleaseProjectionResult:
        if self.report.has_errors == (self.projection is not None):
            raise ValueError("A release projection exists exactly when the report has no errors.")
        return self


__all__ = [
    "BaseLineage",
    "DuplexCut",
    "NickEvent",
    "ReleaseProjectionConstraints",
    "ReleaseProjectionRequest",
    "ReleaseProjectionResult",
    "ReleasedStrandState",
    "StrandExposureRoute",
]

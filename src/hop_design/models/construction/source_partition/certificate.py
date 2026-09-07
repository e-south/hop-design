"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/certificate.py

Defines full-span source-fragment partition certificates.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise
from typing import TYPE_CHECKING

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import ResolvedNickSite
from hop_design.models.coordinates import Span
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import Fragment, StrandEnd

from .policy import SacrificialFragmentPolicy, SourcePartitionThresholdAssessment

if TYPE_CHECKING:
    from .request import SourcePartitionDiscoveryRequest


class SourcePartitionBoundaryKind(StrEnum):
    """Whether one fragment edge is a physical end or a modeled cleavage bond."""

    PHYSICAL_END = "physical_end"
    CLEAVAGE = "cleavage"


class SourcePartitionFragmentDisposition(StrEnum):
    """Whether one exact fragment is required or sacrificial for this route."""

    REQUIRED = "required"
    SACRIFICIAL = "sacrificial"


class SourcePartitionFragmentBoundary(HopModel):
    """One exact fragment boundary with its physical or enzymatic cause."""

    source_offset: int = Field(ge=0)
    kind: SourcePartitionBoundaryKind
    physical_end: StrandEnd | None = None
    enzyme_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_cause(self) -> SourcePartitionFragmentBoundary:
        if self.enzyme_ids != tuple(sorted(set(self.enzyme_ids))):
            raise ValueError("Fragment-boundary enzyme ids must be unique and canonical.")
        if self.kind is SourcePartitionBoundaryKind.PHYSICAL_END:
            if self.physical_end is None or self.enzyme_ids:
                raise ValueError("A physical fragment boundary requires one end and no enzyme.")
        elif self.physical_end is not None or not self.enzyme_ids:
            raise ValueError("A cleavage fragment boundary requires enzyme evidence only.")
        return self


class SourcePartitionFragmentCertificate(HopModel):
    """One exact full-span source fragment and its route disposition."""

    fragment_id: str
    precursor_strand: Strand
    source_span: Span
    length_nt: int = Field(ge=1)
    disposition: SourcePartitionFragmentDisposition
    survivor_id: str | None = None
    left_boundary: SourcePartitionFragmentBoundary
    right_boundary: SourcePartitionFragmentBoundary

    @model_validator(mode="after")
    def validate_fragment(self) -> SourcePartitionFragmentCertificate:
        if self.length_nt != self.source_span.length.value:
            raise ValueError("Certified fragment length must equal its exact source span.")
        if (
            self.left_boundary.source_offset != self.source_span.start.offset
            or self.right_boundary.source_offset != self.source_span.end.offset
        ):
            raise ValueError("Certified fragment boundaries must equal its exact source span.")
        if self.disposition is SourcePartitionFragmentDisposition.REQUIRED:
            if self.survivor_id is None:
                raise ValueError("A required fragment certificate must identify its survivor.")
        elif self.survivor_id is not None:
            raise ValueError("A sacrificial fragment certificate cannot identify a survivor.")
        return self


class SourcePartitionCertificate(HopModel):
    """Full two-strand fragment partition and least-permissive successful threshold."""

    source_length_nt: int = Field(ge=1)
    fragment_policy: SacrificialFragmentPolicy
    selected_maximum_sacrificial_fragment_nt: int = Field(ge=1)
    thresholds: tuple[SourcePartitionThresholdAssessment, ...] = Field(min_length=1)
    fragments: tuple[SourcePartitionFragmentCertificate, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_certificate(self) -> SourcePartitionCertificate:
        expected_thresholds = self.fragment_policy.thresholds
        if (
            tuple(item.maximum_sacrificial_fragment_nt for item in self.thresholds)
            != expected_thresholds
        ):
            raise ValueError("Fragment-threshold assessments must cover the policy ladder.")
        expected_assessments = tuple(
            SourcePartitionThresholdAssessment(
                maximum_sacrificial_fragment_nt=threshold,
                feasible=not violations,
                violating_fragment_ids=violations,
            )
            for threshold in expected_thresholds
            for violations in (
                tuple(
                    sorted(
                        item.fragment_id
                        for item in self.fragments
                        if (
                            item.disposition is SourcePartitionFragmentDisposition.SACRIFICIAL
                            and item.length_nt > threshold
                        )
                        or (
                            item.disposition is SourcePartitionFragmentDisposition.REQUIRED
                            and item.length_nt <= threshold
                        )
                    )
                ),
            )
        )
        if self.thresholds != expected_assessments:
            raise ValueError("Fragment-threshold assessments must derive from exact fragments.")
        first_feasible = next(
            (item.maximum_sacrificial_fragment_nt for item in self.thresholds if item.feasible),
            None,
        )
        if self.selected_maximum_sacrificial_fragment_nt != first_feasible:
            raise ValueError("Selected fragment threshold must be the least permissive success.")
        strand_order = {Strand.TOP: 0, Strand.BOTTOM: 1}
        expected_order = tuple(
            sorted(
                self.fragments,
                key=lambda item: (
                    strand_order[item.precursor_strand],
                    item.source_span.start.offset,
                    item.source_span.end.offset,
                ),
            )
        )
        if self.fragments != expected_order:
            raise ValueError("Fragment certificates must use strand and source-coordinate order.")
        ids = tuple(item.fragment_id for item in self.fragments)
        if len(ids) != len(set(ids)):
            raise ValueError("Fragment certificates must use unique fragment ids.")
        for strand in Strand:
            fragments = tuple(item for item in self.fragments if item.precursor_strand is strand)
            if (
                not fragments
                or fragments[0].source_span.start.offset != 0
                or fragments[-1].source_span.end.offset != self.source_length_nt
                or any(
                    left.source_span.end.offset != right.source_span.start.offset
                    for left, right in pairwise(fragments)
                )
            ):
                raise ValueError("Fragment certificates must cover each source strand fully.")
            for item in fragments:
                self._validate_boundary(item.left_boundary, strand=strand)
                self._validate_boundary(item.right_boundary, strand=strand)
        return self

    def _validate_boundary(
        self,
        boundary: SourcePartitionFragmentBoundary,
        *,
        strand: Strand,
    ) -> None:
        if boundary.kind is SourcePartitionBoundaryKind.CLEAVAGE:
            if boundary.source_offset in {0, self.source_length_nt}:
                raise ValueError("A cleavage certificate must lie inside the source span.")
            return
        expected_end = {
            (Strand.TOP, 0): StrandEnd.FIVE_PRIME,
            (Strand.TOP, self.source_length_nt): StrandEnd.THREE_PRIME,
            (Strand.BOTTOM, 0): StrandEnd.THREE_PRIME,
            (Strand.BOTTOM, self.source_length_nt): StrandEnd.FIVE_PRIME,
        }.get((strand, boundary.source_offset))
        if boundary.physical_end is not expected_end:
            raise ValueError("Physical fragment boundary must identify the exact strand end.")


def _fragment_boundary(
    *,
    strand: Strand,
    offset: int,
    source_length: int,
    sites: tuple[ResolvedNickSite, ...],
) -> SourcePartitionFragmentBoundary:
    enzyme_ids = tuple(
        sorted(
            site.agent_id
            for site in sites
            if site.nick.strand is strand and site.nick.boundary.offset == offset
        )
    )
    if enzyme_ids:
        return SourcePartitionFragmentBoundary(
            source_offset=offset,
            kind=SourcePartitionBoundaryKind.CLEAVAGE,
            enzyme_ids=enzyme_ids,
        )
    physical_end = {
        (Strand.TOP, 0): StrandEnd.FIVE_PRIME,
        (Strand.TOP, source_length): StrandEnd.THREE_PRIME,
        (Strand.BOTTOM, 0): StrandEnd.THREE_PRIME,
        (Strand.BOTTOM, source_length): StrandEnd.FIVE_PRIME,
    }.get((strand, offset))
    if physical_end is None:
        raise ValueError("Every internal fragment boundary requires exact cleavage evidence.")
    return SourcePartitionFragmentBoundary(
        source_offset=offset,
        kind=SourcePartitionBoundaryKind.PHYSICAL_END,
        physical_end=physical_end,
    )


def build_source_partition_certificate(
    request: SourcePartitionDiscoveryRequest,
    *,
    fragments: tuple[Fragment, ...],
    sites: tuple[ResolvedNickSite, ...],
) -> SourcePartitionCertificate | None:
    """Certify every fragment and return the least-permissive successful threshold."""
    required = {
        (
            survivor.precursor_strand,
            survivor.source_span.start.offset,
            survivor.source_span.end.offset,
        ): survivor.survivor_id
        for survivor in request.constraints.required_survivors
    }
    source_length = len(request.source.top_sequence_5prime)
    strand_order = {Strand.TOP: 0, Strand.BOTTOM: 1}
    certified = tuple(
        sorted(
            (
                SourcePartitionFragmentCertificate(
                    fragment_id=fragment.fragment_id,
                    precursor_strand=fragment.precursor_strand,
                    source_span=fragment.precursor_span,
                    length_nt=len(fragment.sequence),
                    disposition=(
                        SourcePartitionFragmentDisposition.REQUIRED
                        if (
                            fragment.precursor_strand,
                            fragment.precursor_span.start.offset,
                            fragment.precursor_span.end.offset,
                        )
                        in required
                        else SourcePartitionFragmentDisposition.SACRIFICIAL
                    ),
                    survivor_id=required.get(
                        (
                            fragment.precursor_strand,
                            fragment.precursor_span.start.offset,
                            fragment.precursor_span.end.offset,
                        )
                    ),
                    left_boundary=_fragment_boundary(
                        strand=fragment.precursor_strand,
                        offset=fragment.precursor_span.start.offset,
                        source_length=source_length,
                        sites=sites,
                    ),
                    right_boundary=_fragment_boundary(
                        strand=fragment.precursor_strand,
                        offset=fragment.precursor_span.end.offset,
                        source_length=source_length,
                        sites=sites,
                    ),
                )
                for fragment in fragments
            ),
            key=lambda item: (
                strand_order[item.precursor_strand],
                item.source_span.start.offset,
                item.source_span.end.offset,
            ),
        )
    )
    thresholds = tuple(
        SourcePartitionThresholdAssessment(
            maximum_sacrificial_fragment_nt=threshold,
            feasible=not violations,
            violating_fragment_ids=violations,
        )
        for threshold in request.constraints.fragment_policy.thresholds
        for violations in (
            tuple(
                sorted(
                    item.fragment_id
                    for item in certified
                    if (
                        item.disposition is SourcePartitionFragmentDisposition.SACRIFICIAL
                        and item.length_nt > threshold
                    )
                    or (
                        item.disposition is SourcePartitionFragmentDisposition.REQUIRED
                        and item.length_nt <= threshold
                    )
                )
            ),
        )
    )
    selected = next(
        (item.maximum_sacrificial_fragment_nt for item in thresholds if item.feasible),
        None,
    )
    if selected is None:
        return None
    return SourcePartitionCertificate(
        source_length_nt=source_length,
        fragment_policy=request.constraints.fragment_policy,
        selected_maximum_sacrificial_fragment_nt=selected,
        thresholds=thresholds,
        fragments=certified,
    )


__all__ = [
    "SourcePartitionBoundaryKind",
    "SourcePartitionCertificate",
    "SourcePartitionFragmentBoundary",
    "SourcePartitionFragmentCertificate",
    "SourcePartitionFragmentDisposition",
    "build_source_partition_certificate",
]

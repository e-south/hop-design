"""Resolved precursor-event to released-strand-state projection."""

from __future__ import annotations

from pydantic import JsonValue

from hop_design.kernel.strand_state import route_semantics
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
from hop_design.models.junction import Strand
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.strand_state import (
    BaseLineage,
    ReleasedStrandState,
    ReleaseProjectionRequest,
    ReleaseProjectionResult,
)


def _error(
    code: str,
    *,
    path: str,
    message: str,
    evidence: dict[str, JsonValue],
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        path=path,
        message=message,
        evidence=evidence,
    )


def project_released_strand_state(request: ReleaseProjectionRequest) -> ReleaseProjectionResult:
    """Project a released strand from already-resolved events without catalog policy."""
    precursor_nt = len(request.precursor_top_strand)
    diagnostics: list[Diagnostic] = []
    cuts = (request.release_cut.top.offset, request.release_cut.bottom.offset)
    if any(boundary > precursor_nt for boundary in cuts):
        diagnostics.append(
            _error(
                "HOP-PROC-001",
                path="release_cut",
                message="Release cut boundaries must stay inside the precursor sequence.",
                evidence={
                    "top_cut": cuts[0],
                    "bottom_cut": cuts[1],
                    "precursor_nt": precursor_nt,
                },
            )
        )
    if request.constraints.require_complete_downstream_separation and any(
        boundary >= precursor_nt for boundary in cuts
    ):
        diagnostics.append(
            _error(
                "HOP-PROC-002",
                path="constraints.require_complete_downstream_separation",
                message="Both release cuts must leave a separate downstream fragment.",
                evidence={
                    "top_cut": cuts[0],
                    "bottom_cut": cuts[1],
                    "precursor_nt": precursor_nt,
                },
            )
        )
    if (
        request.constraints.require_release_site_downstream_of_nick
        and request.release_site_span is not None
        and request.release_site_span.start.offset < request.nick.boundary.offset
    ):
        diagnostics.append(
            _error(
                "HOP-PROC-003",
                path="release_site_span.start",
                message="The release site must start at or after the nick boundary.",
                evidence={
                    "release_site_start": request.release_site_span.start.offset,
                    "nick_boundary": request.nick.boundary.offset,
                },
            )
        )

    semantics = route_semantics(request.route)
    active_cut = (
        request.release_cut.top.offset
        if semantics.active_strand is Strand.TOP
        else request.release_cut.bottom.offset
    )
    if request.origin.offset > request.nick.boundary.offset or request.origin.offset > active_cut:
        diagnostics.append(
            _error(
                "HOP-PROC-004",
                path="origin",
                message="The active-product origin must not follow its nick or active-strand cut.",
                evidence={
                    "origin": request.origin.offset,
                    "nick_boundary": request.nick.boundary.offset,
                    "active_cut": active_cut,
                },
            )
        )
    if diagnostics:
        return ReleaseProjectionResult(
            report=CheckReport(diagnostics=tuple(diagnostics)),
            projection=None,
        )

    active_top_slice = request.precursor_top_strand[request.origin.offset : active_cut]
    active_product_sequence = (
        active_top_slice
        if semantics.active_strand is Strand.TOP
        else reverse_complement_iupac(active_top_slice)
    )
    retained_top_prefix = request.precursor_top_strand[: request.nick.boundary.offset]
    retained_partner_sequence = (
        retained_top_prefix
        if semantics.retained_partner_strand is Strand.TOP
        else reverse_complement_iupac(retained_top_prefix)
    )
    active_span = Span(start=request.origin, end=Boundary(offset=active_cut))
    precursor_indexes = (
        range(request.origin.offset, active_cut)
        if semantics.active_strand is Strand.TOP
        else range(active_cut - 1, request.origin.offset - 1, -1)
    )
    lineage = tuple(
        BaseLineage(
            active_index=index,
            precursor_strand=semantics.active_strand,
            precursor_index=precursor_index,
        )
        for index, precursor_index in enumerate(precursor_indexes)
    )
    projection = ReleasedStrandState(
        route=request.route,
        precursor_top_strand=request.precursor_top_strand,
        active_strand=semantics.active_strand,
        retained_partner_strand=semantics.retained_partner_strand,
        nick=request.nick,
        release_cut=request.release_cut,
        active_product_precursor_span=active_span,
        active_nick_boundary=Boundary(
            offset=(
                request.nick.boundary.offset - request.origin.offset
                if semantics.active_strand is Strand.TOP
                else active_cut - request.nick.boundary.offset
            )
        ),
        active_product_sequence=active_product_sequence,
        retained_partner_sequence=retained_partner_sequence,
        active_product_lineage=lineage,
    )
    return ReleaseProjectionResult(report=CheckReport(), projection=projection)


__all__ = ["project_released_strand_state"]

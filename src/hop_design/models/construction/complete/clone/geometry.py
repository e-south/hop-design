"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/clone/geometry.py

Derives exact Type IIS coordinate lifts and cut geometry for clone-ready products.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction.enzyme_binding import ConstructionEnzymeBinding
from hop_design.models.coordinates import Boundary, Span


class CloneEndGenerationError(ValueError):
    """An exact endpoint Type IIS route cannot produce the requested clone geometry."""


@dataclass(frozen=True, slots=True)
class CloneCutGeometry:
    """Exact strand and design spans implied by two inward-facing cuts."""

    primary_parent_span: Span
    complementary_parent_span: Span
    encoding_span: Span


def derive_clone_cut_geometry(
    *,
    bindings: tuple[ConstructionEnzymeBinding, ConstructionEnzymeBinding],
    parent_length: int,
    template_sequence: str,
    design_sequence: str,
) -> CloneCutGeometry:
    """Derive exact retained-strand and design-union spans from two bindings."""
    left, right = bindings
    cuts = (
        left.reference_cut,
        left.complement_cut,
        right.reference_cut,
        right.complement_cut,
    )
    if any(item is None for item in cuts):
        raise CloneEndGenerationError("Clone digestion requires four exact strand cuts.")
    left_reference = left.reference_cut
    left_complement = left.complement_cut
    right_reference = right.reference_cut
    right_complement = right.complement_cut
    assert left_reference is not None and left_complement is not None
    assert right_reference is not None and right_complement is not None
    if not (
        left_reference.offset < right_reference.offset
        and left_complement.offset < right_complement.offset
    ):
        raise CloneEndGenerationError("Clone end-generation sites must face inward.")
    primary_span = Span(start=left_reference, end=right_reference)
    complementary_span = Span(
        start=Boundary(offset=parent_length - right_complement.offset),
        end=Boundary(offset=parent_length - left_complement.offset),
    )
    if (
        primary_span.end.offset > parent_length
        or complementary_span.end.offset > parent_length
        or primary_span.start.offset >= primary_span.end.offset
        or complementary_span.start.offset >= complementary_span.end.offset
    ):
        raise CloneEndGenerationError("Clone digest cuts must retain nonempty exact strands.")
    encoding_span = Span(
        start=Boundary(offset=min(left_reference.offset, left_complement.offset)),
        end=Boundary(offset=max(right_reference.offset, right_complement.offset)),
    )
    if template_sequence[encoding_span.start.offset : encoding_span.end.offset] != design_sequence:
        raise CloneEndGenerationError(
            "Clone digest cut union must equal the exact verified design encoding."
        )
    return CloneCutGeometry(
        primary_parent_span=primary_span,
        complementary_parent_span=complementary_span,
        encoding_span=encoding_span,
    )


__all__ = [
    "CloneCutGeometry",
    "CloneEndGenerationError",
    "derive_clone_cut_geometry",
]

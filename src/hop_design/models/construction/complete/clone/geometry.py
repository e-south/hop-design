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

from hop_design.models.construction.basal import BasalEnzymeBinding, BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import EnzymeRole


class CloneEndGenerationError(ValueError):
    """An exact local Type IIS route cannot be lifted into the complete route."""


@dataclass(frozen=True, slots=True)
class CloneCutGeometry:
    """Exact strand and design spans implied by two inward-facing cuts."""

    primary_parent_span: Span
    complementary_parent_span: Span
    encoding_span: Span


def _shift_boundary(
    boundary: Boundary | None,
    *,
    payload_start: int,
    payload_end: int,
    delta: int,
) -> Boundary | None:
    if boundary is None:
        return None
    offset = boundary.offset
    if offset <= payload_start:
        return boundary
    if offset >= payload_end:
        return Boundary(offset=offset + delta)
    raise CloneEndGenerationError("End-generation cuts cannot occur inside the payload.")


def _shift_binding(
    binding: BasalEnzymeBinding,
    *,
    payload_start: int,
    payload_end: int,
    delta: int,
) -> BasalEnzymeBinding:
    span = binding.recognition_span
    if span.end.offset <= payload_start:
        shifted_span = span
    elif span.start.offset >= payload_end:
        shifted_span = Span(
            start=Boundary(offset=span.start.offset + delta),
            end=Boundary(offset=span.end.offset + delta),
        )
    else:
        raise CloneEndGenerationError(
            "End-generation recognition cannot overlap the replaced payload span."
        )
    return BasalEnzymeBinding.create(
        enzyme_id=binding.enzyme_id,
        role=binding.role,
        strand=binding.strand,
        recognition_span=shifted_span,
        orientation=binding.orientation,
        reference_cut=_shift_boundary(
            binding.reference_cut,
            payload_start=payload_start,
            payload_end=payload_end,
            delta=delta,
        ),
        complement_cut=_shift_boundary(
            binding.complement_cut,
            payload_start=payload_start,
            payload_end=payload_end,
            delta=delta,
        ),
    )


def lift_clone_end_bindings(
    *,
    basal: BasalRealizationRecord,
    foldback: FoldbackLocalRealization,
) -> tuple[BasalEnzymeBinding, BasalEnzymeBinding]:
    """Lift both local end-generation bindings across the complete foldback span."""
    if basal.restriction_digest_product is None or len(basal.payload_source_map.segments) != 1:
        raise CloneEndGenerationError(
            "Clone composition requires one exact local digest and payload occurrence."
        )
    segment = basal.payload_source_map.segments[0]
    payload_start = segment.source_span.start.offset
    payload_end = segment.source_span.end.offset
    delta = len(foldback.retained_sequence) - len(foldback.payload_sequence)
    local = tuple(
        sorted(
            (
                binding
                for binding in basal.enzyme_bindings
                if binding.role is EnzymeRole.END_GENERATION
            ),
            key=lambda item: item.recognition_span.start.offset,
        )
    )
    if len(local) != 2:
        raise CloneEndGenerationError(
            "Clone composition requires two exact end-generation bindings."
        )
    lifted = tuple(
        _shift_binding(
            binding,
            payload_start=payload_start,
            payload_end=payload_end,
            delta=delta,
        )
        for binding in local
    )
    return (lifted[0], lifted[1])


def validate_clone_binding_definitions(
    *,
    bindings: tuple[BasalEnzymeBinding, BasalEnzymeBinding],
    basal: BasalRealizationRecord | None,
    sequence: str,
) -> None:
    """Replay lifted bindings against the exact embedded enzyme definitions."""
    if basal is None:
        return
    definitions = {item.enzyme_id: item.enzyme for item in basal.enzyme_definitions}
    for binding in bindings:
        enzyme = definitions.get(binding.enzyme_id)
        if enzyme is None:
            raise CloneEndGenerationError(
                "Clone end-generation bindings require exact enzyme definitions."
            )
        try:
            binding.assert_definition_replay(enzyme=enzyme, sequence=sequence)
        except ValueError as error:
            raise CloneEndGenerationError(str(error)) from error


def derive_clone_cut_geometry(
    *,
    bindings: tuple[BasalEnzymeBinding, BasalEnzymeBinding],
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
    "lift_clone_end_bindings",
    "validate_clone_binding_definitions",
]

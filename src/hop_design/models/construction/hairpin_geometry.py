"""Locate whole-hairpin geometry in an explicitly selected, verified route."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.construction.complete.state import ConstructionState, ConstructionStatePhase
from hop_design.models.construction.payload import ConstructionEndpoint, SourceOrientation
from hop_design.models.construction.scaffold import (
    SCAFFOLD_DIMENSIONS,
    HairpinScaffoldRequirements,
    ScaffoldMismatch,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.molecular_state import CohesiveEnd, LineageStrand, StrandPairObservation

if TYPE_CHECKING:
    from .projections.route_view import MolecularRouteView


class LaterReleaseInterface(HopModel):
    """Ends present only after the recorded copying and release continuation."""

    stage: Literal["clone_ready_duplex"] = "clone_ready_duplex"
    state_id: str
    cohesive_ends: tuple[CohesiveEnd, ...] = Field(min_length=1)


class HairpinArchitecture(HopModel):
    """Recorded joined state and the dimensions shared by admission and portrayal."""

    endpoint: ConstructionEndpoint
    stage_role: Literal["endpoint", "intermediate"]
    state: ConstructionState
    stem_primary_span: Span
    stem_return_span: Span
    paired_primary_span: Span
    paired_return_span: Span
    loop_span: Span
    stem_bp: int = Field(gt=0)
    open_side_paired_positions: int = Field(ge=0)
    loop_side_paired_bp: int = Field(ge=0)
    loop_nt: int = Field(gt=0)
    noncanonical_open_side_contacts: int = Field(ge=0)
    join_boundaries: tuple[int, ...]
    later_release: LaterReleaseInterface | None = None

    @property
    def ordered_contacts(self) -> tuple[StrandPairObservation, ...]:
        """Sequence-ordered contacts for drawing, without changing recorded endpoint roles."""
        return ordered_hairpin_contacts(self.state)

    @property
    def five_prime_unpaired_nt(self) -> int:
        """Recorded prefix outside the single contiguous pairing architecture."""
        return self.paired_primary_span.start.offset

    @property
    def three_prime_unpaired_nt(self) -> int:
        """Recorded suffix outside the single contiguous pairing architecture."""
        return len(self.state.molecules[0].sequence) - self.paired_return_span.end.offset

    @property
    def scaffold_dimensions(self) -> dict[str, int]:
        return {dimension: getattr(self, dimension) for dimension in SCAFFOLD_DIMENSIONS}


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def ordered_hairpin_contacts(state: ConstructionState) -> tuple[StrandPairObservation, ...]:
    """Orient each complete contact endpoint by position on the joined strand."""
    if len(state.molecules) != 1 or not state.pairings:
        raise ValueError("Hairpin portrait requires antiparallel intramolecular contacts.")
    strand_id = state.molecules[0].strand_id
    contacts = []
    for pair in state.pairings:
        if (
            pair.left_strand_id != strand_id
            or pair.right_strand_id != strand_id
            or pair.left_index == pair.right_index
        ):
            raise ValueError("Hairpin portrait requires antiparallel intramolecular contacts.")
        if pair.left_index > pair.right_index:
            pair = pair.model_copy(
                update={
                    "left_index": pair.right_index,
                    "right_index": pair.left_index,
                    "left_base": pair.right_base,
                    "right_base": pair.left_base,
                    "left_strand_id": pair.right_strand_id,
                    "right_strand_id": pair.left_strand_id,
                }
            )
        contacts.append(pair)
    return tuple(sorted(contacts, key=lambda pair: pair.left_index))


def _payload_span(route: MolecularRouteView, state: ConstructionState) -> Span:
    segments = route.payload_source_map.segments
    if len(segments) != 1:
        raise ValueError("Hairpin portraits require a single payload source segment.")
    segment = segments[0]
    preparation = route.source_preparation
    reverse = segment.orientation is SourceOrientation.REVERSE_COMPLEMENT
    use = preparation.prepared_bottom_use if reverse else preparation.prepared_top_use
    origin_strand = LineageStrand.COMPLEMENTARY if reverse else LineageStrand.PRIMARY
    source_length = len(preparation.source_ssdna.sequence_5prime)
    source_span = (
        _span(
            source_length - segment.source_span.end.offset,
            source_length - segment.source_span.start.offset,
        )
        if reverse
        else segment.source_span
    )
    # The source map names the input ssDNA; state lineage names its copied strand.
    # Source-preparation validation excludes primer handles, preserving source coordinates,
    # while terminal chemistry can legitimately differ between template and copy.
    if segment.source_material_id != route.source_preparation.source_ssdna.material_id:
        raise ValueError("Hairpin portrait payload must originate in the recorded source ssDNA.")
    indices = [
        base.product_index
        for base in state.molecules[0].lineage
        if base.origin_id == use.use_id
        and base.origin_strand is origin_strand
        and source_span.contains_index(base.origin_index)
    ]
    if not indices or indices != list(range(indices[0], indices[-1] + 1)):
        raise ValueError("Hairpin portrait requires a contiguous recorded payload arm.")
    span = _span(indices[0], indices[-1] + 1)
    if (
        state.molecules[0].sequence[span.start.offset : span.end.offset]
        != route.design.payload_sequence
    ):
        raise ValueError("Hairpin portrait payload coordinates must replay the authored stem.")
    return span


def _joins(route: MolecularRouteView, state: ConstructionState) -> tuple[int, ...]:
    strands = {
        s.strand_id: s for stage in route.construction_program.states for s in stage.molecules
    }
    joined = state.molecules[0].sequence
    boundaries = []
    for formed in state.formed_bonds:
        upstream = strands[formed.bond.upstream_strand_id].sequence
        downstream = strands[formed.bond.downstream_strand_id].sequence
        boundary = len(upstream)
        if not joined.startswith(upstream + downstream):
            raise ValueError("Hairpin portrait requires a recorded head-to-tail joined strand.")
        boundaries.append(boundary)
    return tuple(sorted(boundaries))


def describe_hairpin(
    route: MolecularRouteView,
) -> HairpinArchitecture:
    """Project a contiguous, single-loop pairing architecture; never predict folding."""
    endpoint = route.final_product.reference.endpoint
    direct = endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
    phase = (
        ConstructionStatePhase.LIGATED_PRODUCT if direct else ConstructionStatePhase.ADAPTER_LIGATED
    )
    states = [s for s in route.construction_program.states if s.phase is phase]
    if len(states) != 1 or len(states[0].molecules) != 1:
        raise ValueError(
            "Hairpin portrait requires exactly one joined single-strand hairpin state."
        )
    state = states[0]
    pairs = ordered_hairpin_contacts(state)
    if any(
        b.left_index != a.left_index + 1 or b.right_index != a.right_index - 1
        for a, b in pairwise(pairs)
    ):
        raise ValueError(
            "Hairpin portrait supports one contiguous stem, not bulges or branched pairings."
        )
    outer, inner = pairs[0], pairs[-1]
    primary = _payload_span(route, state)
    by_index = {p.left_index: p for p in pairs}
    if not all(i in by_index for i in range(primary.start.offset, primary.end.offset)):
        raise ValueError("The complete authored stem must be paired in the portrayed state.")
    returned = _span(
        by_index[primary.end.offset - 1].right_index, by_index[primary.start.offset].right_index + 1
    )
    closing = [p for p in pairs if p.left_index >= primary.end.offset]
    if any(p.kind.value != "watson_crick" for p in closing):
        raise ValueError(
            "The current hairpin portrait requires a canonically paired closing extension."
        )
    later = None
    if route.final_product.cohesive_ends:
        released = [
            s
            for s in route.construction_program.states
            if s.phase is ConstructionStatePhase.CLONE_READY_DUPLEX
        ]
        if len(released) != 1:
            raise ValueError("Released interfaces require their exact later molecular state.")
        later = LaterReleaseInterface(
            state_id=released[0].state_id, cohesive_ends=route.final_product.cohesive_ends
        )
    return HairpinArchitecture(
        endpoint=endpoint,
        stage_role="endpoint"
        if direct or endpoint is ConstructionEndpoint.ADAPTER_LIGATED_HAIRPIN
        else "intermediate",
        state=state,
        stem_primary_span=primary,
        stem_return_span=returned,
        paired_primary_span=_span(outer.left_index, inner.left_index + 1),
        paired_return_span=_span(inner.right_index, outer.right_index + 1),
        loop_span=_span(inner.left_index + 1, inner.right_index),
        stem_bp=primary.length.value,
        open_side_paired_positions=primary.start.offset - outer.left_index,
        loop_side_paired_bp=len(closing),
        loop_nt=inner.right_index - inner.left_index - 1,
        noncanonical_open_side_contacts=sum(
            p.kind.value != "watson_crick" for p in pairs if p.left_index < primary.start.offset
        ),
        join_boundaries=_joins(route, state),
        later_release=later,
    )


def scaffold_mismatches(
    requirement: HairpinScaffoldRequirements | None,
    route: MolecularRouteView,
) -> tuple[ScaffoldMismatch, ...]:
    """Check the very same achieved-state dimensions used by the molecular portrait."""
    if requirement is None:
        return ()
    architecture = describe_hairpin(route)
    output = []
    for dimension in SCAFFOLD_DIMENSIONS:
        allowed = getattr(requirement, dimension)
        observed = getattr(architecture, dimension)
        if allowed is not None and not allowed.contains(observed):
            output.append(
                ScaffoldMismatch.model_validate(
                    {
                        "dimension": dimension,
                        "required": allowed,
                        "observed": observed,
                        "state_id": architecture.state.state_id,
                    }
                )
            )
    return tuple(output)


__all__ = [
    "HairpinArchitecture",
    "LaterReleaseInterface",
    "describe_hairpin",
    "scaffold_mismatches",
]

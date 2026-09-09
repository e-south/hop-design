"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal_views.py

Projects source recognition sites and nick boundaries from verified basal results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.views import (
    TrackDirection,
    ViewFeature,
    ViewPairing,
    ViewPanel,
    ViewTrack,
)

from .local_public import LocalNeighborhoodDiscovery


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def build_basal_source_panel(
    receipt: LocalNeighborhoodDiscovery, *, realization_id: str
) -> ViewPanel:
    """Show one source duplex and its nick, without asserting later processing.

    Select a local realization ID from the receipt. Track sequences and feature
    coordinates are 5-prime to 3-prime; the bottom track has reverse display direction.
    Recognition spans are annotated on the source-top coordinate reference.
    """
    source = receipt._verified_source()
    if not isinstance(source, BasalNeighborhoodDiscoveryResult):
        raise ValueError("A basal source panel requires a basal-neighborhood receipt.")
    realization = next(
        (
            item
            for item in source.realizations
            if item.local_realization.local_realization_id == realization_id
        ),
        None,
    )
    if realization is None:
        raise ValueError(f"Unknown basal local realization: {realization_id!r}.")
    duplex = realization.nicked_duplex
    length = len(duplex.top_strand.sequence)
    payload_span = realization.payload_source_map.segments[0].source_span
    names = {item.enzyme_id: item.enzyme.canonical_name for item in realization.enzyme_definitions}
    features = [
        ViewFeature(
            feature_id="payload",
            track_id="source_top",
            role="payload",
            label="Payload",
            span=payload_span,
        ),
        *(
            ViewFeature(
                feature_id=f"nickase_site_{index}",
                track_id="source_top",
                role="recognition_site",
                label=names[binding.enzyme_id],
                span=binding.recognition_span,
            )
            for index, binding in enumerate(realization.enzyme_bindings)
        ),
    ]
    nick = realization.basal_nick
    boundary = nick.boundary.offset if nick.strand is Strand.TOP else length - nick.boundary.offset
    features.append(
        ViewFeature(
            feature_id="basal_nick",
            track_id=f"source_{nick.strand.value}",
            role="nick",
            label="Nick",
            span=_span(boundary, boundary),
        )
    )
    action = realization.future_release_action
    if action is not None and action.requirement.recognition_material == "source_duplex":
        start, pattern = action.source_recognition_placement(
            payload_boundary=payload_span.start.offset
        )
        features.append(
            ViewFeature(
                feature_id="future_release_site",
                track_id="source_top",
                role="recognition_requirement",
                label=f"{names[action.enzyme_id]} (later processing)",
                span=_span(start, start + len(pattern)),
            )
        )
    return ViewPanel(
        panel_id="basal_source",
        title="Source duplex",
        tracks=(
            ViewTrack(
                track_id="source_top",
                label="Source strand",
                sequence=duplex.top_strand.sequence,
                strand=Strand.TOP,
                direction=TrackDirection.FORWARD,
            ),
            ViewTrack(
                track_id="source_bottom",
                label="Complementary strand",
                sequence=duplex.bottom_strand.sequence,
                strand=Strand.BOTTOM,
                direction=TrackDirection.REVERSE,
            ),
        ),
        features=tuple(features),
        pairings=tuple(
            ViewPairing(
                left_track_id="source_top",
                left_index=index,
                right_track_id="source_bottom",
                right_index=length - index - 1,
                kind="watson_crick",
            )
            for index in range(length)
        ),
    )

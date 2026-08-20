"""Build typed scientific view state from resolved mechanics."""

from __future__ import annotations

from hop_design.kernel.basal import surviving_strand
from hop_design.kernel.strand_state import complement_iupac
from hop_design.models.basal import BasalEvaluation
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.foldback import FoldbackEvaluation
from hop_design.models.junction import Strand
from hop_design.models.strand_state import ReleasedStrandState
from hop_design.models.views import (
    TrackDirection,
    ViewFeature,
    ViewPairing,
    ViewPanel,
    ViewTrack,
    WorkflowView,
)


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _foldback_panels(evaluation: FoldbackEvaluation) -> tuple[ViewPanel, ...]:
    precursor_bottom = complement_iupac(evaluation.precursor_sequence)
    retained_nt = evaluation.retained_tract_span.length.value
    turn_nt = len(evaluation.effective_turn_sequence)
    arm_start = retained_nt + turn_nt
    junction_features = (
        ViewFeature(
            feature_id="retained_tract",
            track_id="junction",
            role="retained_tract",
            label="retained tract",
            span=_span(0, retained_nt),
        ),
        ViewFeature(
            feature_id="turn",
            track_id="junction",
            role="turn",
            label="turn",
            span=_span(retained_nt, arm_start),
        ),
        ViewFeature(
            feature_id="foldback_arm",
            track_id="junction",
            role="foldback_arm",
            label="foldback arm",
            span=_span(arm_start, len(evaluation.junction_sequence)),
        ),
    )
    precursor_tracks = (
        ViewTrack(
            track_id="precursor_top",
            label="precursor top strand",
            sequence=evaluation.precursor_sequence,
            strand=Strand.TOP,
            direction=TrackDirection.FORWARD,
        ),
        ViewTrack(
            track_id="precursor_bottom",
            label="precursor bottom strand",
            sequence=precursor_bottom,
            strand=Strand.BOTTOM,
            direction=TrackDirection.REVERSE,
        ),
    )
    pre_feature = ViewFeature(
        feature_id="retained_tract_precursor",
        track_id="precursor_top",
        role="retained_tract",
        label="retained tract",
        span=evaluation.retained_tract_span,
    )
    junction_track = ViewTrack(
        track_id="junction",
        label="post-nick active strand",
        sequence=evaluation.junction_sequence,
        strand=Strand.TOP,
        direction=TrackDirection.FORWARD,
    )
    foldback_pairings = tuple(
        ViewPairing(
            left_track_id="junction",
            left_index=pair.left_index,
            right_track_id="junction",
            right_index=pair.right_index,
            kind=pair.kind.value,
        )
        for pair in evaluation.junction.pairs
    )
    return (
        ViewPanel(
            panel_id="pre_nick_duplex",
            title="Pre-nick duplex",
            tracks=precursor_tracks,
            features=(pre_feature,),
        ),
        ViewPanel(
            panel_id="post_nick_exposed",
            title="Post-nick exposed strand",
            tracks=(junction_track,),
            features=junction_features,
        ),
        ViewPanel(
            panel_id="post_nick_foldback",
            title="Post-nick foldback",
            tracks=(junction_track,),
            features=junction_features,
            pairings=foldback_pairings,
        ),
    )


def build_foldback_view(evaluation: FoldbackEvaluation) -> WorkflowView:
    """Build the three-panel foldback QA contract."""
    if evaluation.report.has_errors:
        raise ValueError("Foldback views require a feasible evaluation.")
    return WorkflowView(
        view_id="hop:view/foldback-qa@1",
        kind="foldback_qa",
        panels=_foldback_panels(evaluation),
    )


def build_released_workflow_view(
    state: ReleasedStrandState,
    foldback: FoldbackEvaluation,
) -> WorkflowView:
    """Build precursor, released-fragment, and origin-anchored foldback panels."""
    precursor_panel = ViewPanel(
        panel_id="precursor",
        title="Precursor and resolved cut state",
        tracks=(
            ViewTrack(
                track_id="precursor_top",
                label="precursor top strand",
                sequence=state.precursor_top_strand,
                strand=Strand.TOP,
                direction=TrackDirection.FORWARD,
            ),
            ViewTrack(
                track_id="precursor_bottom",
                label="precursor bottom strand",
                sequence=complement_iupac(state.precursor_top_strand),
                strand=Strand.BOTTOM,
                direction=TrackDirection.REVERSE,
            ),
        ),
    )
    released_tracks = [
        ViewTrack(
            track_id="active_product",
            label="active product",
            sequence=state.active_product_sequence,
            strand=state.active_strand,
            direction=TrackDirection.FORWARD,
        )
    ]
    if state.retained_partner_sequence:
        released_tracks.append(
            ViewTrack(
                track_id="retained_partner",
                label="retained partner",
                sequence=state.retained_partner_sequence,
                strand=state.retained_partner_strand,
                direction=TrackDirection.FORWARD,
            )
        )
    released_panel = ViewPanel(
        panel_id="released_fragments",
        title="Released strand state",
        tracks=tuple(released_tracks),
    )
    folded = _foldback_panels(foldback)[-1].model_copy(
        update={
            "panel_id": "origin_anchored_foldback",
            "title": "Origin-anchored foldback",
        }
    )
    return WorkflowView(
        view_id="hop:view/released-workflow@1",
        kind="released_workflow",
        panels=(precursor_panel, released_panel, folded),
    )


def build_basal_view(
    evaluation: BasalEvaluation,
    *,
    nicked_strand: Strand,
) -> WorkflowView:
    """Build pre- and post-terminal-nick basal-junction panels."""
    if evaluation.decision.status == "reject":
        raise ValueError("Basal views cannot represent a rejected pair profile.")
    left_track = ViewTrack(
        track_id="left_arm",
        label="left basal arm",
        sequence=evaluation.junction.left_arm,
        strand=Strand.TOP,
        direction=TrackDirection.FORWARD,
    )
    right_track = ViewTrack(
        track_id="right_arm",
        label="right basal arm",
        sequence=evaluation.junction.right_arm,
        strand=Strand.BOTTOM,
        direction=TrackDirection.REVERSE,
    )
    pairings = tuple(
        ViewPairing(
            left_track_id="left_arm",
            left_index=pair.left_index,
            right_track_id="right_arm",
            right_index=pair.right_index,
            kind=pair.kind.value,
        )
        for pair in evaluation.junction.pairs
    )
    pre = ViewPanel(
        panel_id="pre_terminal_nick",
        title="Pre-terminal-nick basal junction",
        tracks=(left_track, right_track),
        pairings=pairings,
    )
    survivor = surviving_strand(nicked_strand)
    survivor_track = left_track if survivor is Strand.TOP else right_track
    post = ViewPanel(
        panel_id="post_terminal_nick",
        title="Post-terminal-nick surviving strand",
        tracks=(survivor_track,),
    )
    return WorkflowView(
        view_id="hop:view/basal-terminal-nick@1",
        kind="basal_terminal_nick",
        panels=(pre, post),
    )


__all__ = ["build_basal_view", "build_foldback_view", "build_released_workflow_view"]

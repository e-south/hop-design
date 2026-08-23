from __future__ import annotations

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.design.views import (
    build_basal_pairing_view,
    build_basal_view,
    build_foldback_junction_view,
    build_foldback_view,
    build_released_workflow_view,
)
from hop_design.export.svg import render_workflow_svg
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.views import WorkflowView


def _foldback_evaluation():
    return hop.evaluate_foldback(
        hop.FoldbackEvaluationRequest(
            precursor_sequence="CCTCAGCA",
            retained_tract_span=Span(start=Boundary(offset=2), end=Boundary(offset=6)),
            source_turn_span=Span(start=Boundary(offset=6), end=Boundary(offset=8)),
            protected_region=Span(start=Boundary(offset=0), end=Boundary(offset=2)),
            turn_extension="T",
            foldback_arm="CTGA",
            constraints=hop.FoldbackConstraints(
                max_non_watson_crick_pairs=0,
                terminal_watson_crick_bp_min=4,
                terminal_watson_crick_bp_max=4,
                max_uninterrupted_watson_crick_bp=4,
                max_added_nt=5,
                required_turn_nt=3,
                allow_protected_region_non_watson_crick_pairs=False,
            ),
        )
    )


def _basal_evaluation():
    return hop.evaluate_basal_pairing(
        hop.BasalPairingRequest(left_arm="AAAA", right_arm="TTTT"),
        constraints=hop.BasalConstraintProfile(
            require_terminal_watson_crick=True,
            allow_active_gt_wobble=True,
            max_active_hard_mismatches=0,
            max_active_non_watson_crick_pairs=0,
            forbid_active_middle_double_hard=True,
            minimum_active_pair_support_index=4.0,
            maximum_active_pair_disruption_index=0.0,
            require_outer_hard_for_active_double=True,
            reject_compact_profiles=(),
            reserve_compact_profiles=(),
        ),
    )


def _released_state():
    result = hop.project_released_strand_state(
        hop.ReleaseProjectionRequest(
            precursor_top_strand="AACGTTGTTCCAA",
            origin=Boundary(offset=0),
            nick=hop.NickEvent(boundary=Boundary(offset=0), strand=Strand.TOP),
            release_cut=hop.DuplexCut(
                top=Boundary(offset=10),
                bottom=Boundary(offset=9),
            ),
            release_site_span=Span(start=Boundary(offset=9), end=Boundary(offset=13)),
            route=hop.StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
            constraints=hop.ReleaseProjectionConstraints(
                require_release_site_downstream_of_nick=True,
                require_complete_downstream_separation=True,
            ),
        )
    )
    assert result.projection is not None
    return result.projection


def test_foldback_view_is_a_typed_three_panel_scientific_contract() -> None:
    view = build_foldback_view(_foldback_evaluation())

    assert view.kind == "foldback_qa"
    assert [panel.panel_id for panel in view.panels] == [
        "pre_nick_duplex",
        "post_nick_exposed",
        "post_nick_foldback",
    ]
    assert len(view.panels[-1].pairings) == 4


def test_foldback_junction_view_does_not_invent_nicking_states() -> None:
    view = build_foldback_junction_view(_foldback_evaluation())

    assert view.kind == "foldback_junction"
    assert [panel.panel_id for panel in view.panels] == ["foldback_junction"]
    assert len(view.panels[0].pairings) == 4


def test_released_and_basal_views_keep_strand_and_pair_calls_explicit() -> None:
    released = build_released_workflow_view(_released_state(), _foldback_evaluation())
    basal = build_basal_view(_basal_evaluation(), nicked_strand=Strand.TOP)

    assert [panel.panel_id for panel in released.panels] == [
        "precursor",
        "released_fragments",
        "origin_anchored_foldback",
    ]
    assert released.panels[1].tracks[0].strand is Strand.BOTTOM
    assert {track.direction for track in released.panels[1].tracks} == {"5to3"}
    assert [panel.panel_id for panel in basal.panels] == [
        "pre_terminal_nick",
        "post_terminal_nick",
    ]
    assert basal.panels[1].tracks[0].strand is Strand.BOTTOM
    assert [pair.kind for pair in basal.panels[0].pairings] == ["watson_crick"] * 4


def test_basal_pairing_view_does_not_invent_terminal_processing() -> None:
    basal = build_basal_pairing_view(_basal_evaluation())

    assert basal.kind == "basal_pairing"
    assert [panel.panel_id for panel in basal.panels] == ["basal_junction"]
    assert len(basal.panels[0].tracks) == 2
    assert [pair.kind for pair in basal.panels[0].pairings] == ["watson_crick"] * 4


def test_coordinate_aligned_precursor_bottom_is_the_only_reverse_display() -> None:
    released = build_released_workflow_view(_released_state(), _foldback_evaluation())

    assert released.panels[0].tracks[1].strand is Strand.BOTTOM
    assert released.panels[0].tracks[1].direction == "3to5"


def test_svg_renderer_is_deterministic_and_consumes_view_state_only() -> None:
    view = build_foldback_view(_foldback_evaluation())

    first = render_workflow_svg(view)
    second = render_workflow_svg(WorkflowView.model_validate_json(view.model_dump_json()))

    assert first == second
    assert first.startswith(b"<svg")
    assert b'data-panel-id="post_nick_foldback"' in first
    assert first.count(b'data-pair-kind="watson_crick"') == 4


def test_view_contract_rejects_out_of_bounds_features() -> None:
    data = build_foldback_view(_foldback_evaluation()).model_dump(mode="json")
    data["panels"][0]["features"][0]["span"]["end"]["offset"] = 999

    with pytest.raises(ValidationError, match="feature span"):
        WorkflowView.model_validate_json(__import__("json").dumps(data))

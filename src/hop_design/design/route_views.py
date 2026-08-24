"""Route-owned workflow-view projections for exact discovery results."""

from __future__ import annotations

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.discovery.hairpin_routes import HairpinJunctionRouteCandidate
from hop_design.models.discovery.released_foldback import ReleasedFoldbackGeometryHit
from hop_design.models.discovery.released_foldback_candidate_evaluation import (
    released_foldback_precursor_domains,
)
from hop_design.models.discovery.released_foldback_candidates import (
    ReleasedFoldbackPrecursorCandidate,
    ReleasedFoldbackPrecursorSearchRequest,
)
from hop_design.models.foldback import FoldbackConstraints, FoldbackEvaluationRequest
from hop_design.models.strand_state import ReleasedStrandState
from hop_design.models.views import WorkflowView

from .foldback import evaluate_foldback
from .views import build_released_workflow_view


def build_released_foldback_precursor_view(
    *,
    geometry: ReleasedFoldbackGeometryHit,
    precursor: ReleasedFoldbackPrecursorCandidate,
    state: ReleasedStrandState,
) -> WorkflowView:
    """Project one exact released-foldback precursor into its workflow view."""
    if precursor.geometry_id != geometry.candidate_id:
        raise ValueError("The exact precursor must reference the selected foldback geometry.")
    request = ReleasedFoldbackPrecursorSearchRequest(
        geometry=geometry,
        precursor_template=precursor.precursor_sequence,
    )
    if released_foldback_precursor_domains(request) is None:
        raise ValueError("The exact precursor must satisfy the selected foldback geometry.")
    if state.precursor_top_strand != precursor.precursor_sequence:
        raise ValueError("The released state must project the selected exact precursor.")
    if state.nick != geometry.nick or state.release_cut != geometry.release_cut:
        raise ValueError("The released state must use the selected geometry events.")
    if state.active_product_precursor_span != geometry.active_product_span:
        raise ValueError("The released state must use the selected active-product span.")

    active_sequence = state.active_product_sequence
    paired_tract = len(geometry.pairing_domains)
    turn_length = len(active_sequence) - (2 * paired_tract)
    if paired_tract < 1 or turn_length < 0:
        raise ValueError("The selected geometry has an invalid foldback extent.")
    arm_start = paired_tract + turn_length
    foldback = evaluate_foldback(
        FoldbackEvaluationRequest(
            precursor_sequence=active_sequence[:arm_start],
            retained_tract_span=Span(
                start=Boundary(offset=0),
                end=Boundary(offset=paired_tract),
            ),
            source_turn_span=Span(
                start=Boundary(offset=paired_tract),
                end=Boundary(offset=arm_start),
            ),
            protected_region=Span(
                start=Boundary(offset=0),
                end=Boundary(offset=0),
            ),
            turn_extension="",
            foldback_arm=active_sequence[arm_start:],
            constraints=FoldbackConstraints(
                max_non_watson_crick_pairs=0,
                terminal_watson_crick_bp_min=paired_tract,
                terminal_watson_crick_bp_max=paired_tract,
                max_uninterrupted_watson_crick_bp=paired_tract,
                max_added_nt=paired_tract,
                required_turn_nt=turn_length,
                allow_protected_region_non_watson_crick_pairs=False,
            ),
        )
    )
    if foldback.report.has_errors or foldback.designed_sequence != active_sequence:
        raise ValueError("The selected precursor does not resolve one exact foldback view.")
    return build_released_workflow_view(state, foldback)


def build_hairpin_junction_route_view(
    route: HairpinJunctionRouteCandidate,
) -> WorkflowView:
    """Project one selected junction route into its released-workflow view."""
    return build_released_foldback_precursor_view(
        geometry=route.released_foldback_geometry,
        precursor=route.released_foldback_precursor,
        state=route.released_state,
    )


__all__ = [
    "build_hairpin_junction_route_view",
    "build_released_foldback_precursor_view",
]

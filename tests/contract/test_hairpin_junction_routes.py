from __future__ import annotations

import itertools
import json

import pytest
from pydantic import ValidationError

import hop_design as hop
import hop_design.discovery as discovery
import hop_design.views as views
from hop_design.models.catalog import SiteOrientation
from hop_design.models.discovery import (
    BasalProcessingGeometryRequest,
    BasalProcessingGeometrySearchLimits,
    BasalProcessingRouteSearchLimits,
    HairpinJunctionRouteSearchLimits,
    HairpinJunctionRouteSearchResult,
    ReleasedFoldbackGeometryRequest,
    ReleasedFoldbackGeometrySearchLimits,
    ReleasedFoldbackPrecursorSearchLimits,
    ReleasedFoldbackPrecursorSearchRequest,
)
from hop_design.models.discovery.hairpin_routes import (
    HairpinJunctionRouteCandidate,
    HairpinJunctionRouteFeasibility,
    hairpin_junction_route_feasibility,
    hairpin_junction_route_id,
)
from hop_design.models.discovery.released_foldback_candidates import (
    ReleasedFoldbackPrecursorCandidate,
    released_foldback_precursor_candidate_id,
)
from hop_design.serialization import sha256_digest


def _released_precursors(
    *,
    precursor_template: str = "AATC",
    max_search_nodes: int = 4,
) -> discovery.ReleasedFoldbackPrecursorSearchResult:
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/junction-route-foldback@1",
        nicking_agents=(
            hop.NickingAgent(
                agent_id="example:nicking-agent/foldback@1",
                motif_top_5to3="N",
                nicked_strand=hop.Strand.TOP,
                cut_offset=0,
                warning_codes=(),
            ),
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id="example:release-agent/foldback@1",
                motif_top_5to3="N",
                top_cut_offset=0,
                bottom_cut_offset=0,
                warning_codes=(),
            ),
        ),
    )
    geometry = discovery.search_released_foldback_geometries(
        catalog=catalog,
        request=ReleasedFoldbackGeometryRequest(
            target_nick_boundary=hop.Boundary(offset=0),
            paired_tract=hop.BasePairCount(value=1),
            turn_length=hop.NucleotideCount(value=1),
            route=hop.StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
            max_boundary_displacement=hop.NucleotideCount(value=0),
            require_release_site_downstream_of_nick=True,
            require_complete_downstream_separation=True,
        ),
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    ).hits[0]
    return discovery.search_released_foldback_precursors(
        ReleasedFoldbackPrecursorSearchRequest(
            geometry=geometry,
            precursor_template=precursor_template,
        ),
        limits=ReleasedFoldbackPrecursorSearchLimits(
            max_search_nodes=max_search_nodes,
            max_hits=4,
        ),
    )


def _constraints() -> hop.BasalConstraintProfile:
    return hop.BasalConstraintProfile(
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
    )


def _basal_routes(
    *,
    terminal_nicked_strand: hop.Strand = hop.Strand.TOP,
    agent_count: int = 1,
    max_route_nodes: int | None = None,
    release_id: str = "example:release-agent/basal@1",
) -> discovery.BasalProcessingRouteSearchResult:
    basal = discovery.search_basal_candidates(
        discovery.BasalCandidateSearchRequest(
            left_arm_template="AAAA",
            right_arm_template="TTTT",
            constraints=_constraints(),
            acceptance="active_only",
        ),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=1, max_hits=1),
    )
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/junction-route-basal@1",
        nicking_agents=tuple(
            hop.NickingAgent(
                agent_id=f"example:nicking-agent/basal-{index}@1",
                motif_top_5to3="NNNNN",
                nicked_strand=hop.Strand.TOP,
                cut_offset=4,
                warning_codes=(),
            )
            for index in range(1, agent_count + 1)
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id=release_id,
                motif_top_5to3="CCAA",
                top_cut_offset=4,
                bottom_cut_offset=8,
                warning_codes=(),
            ),
        ),
    )
    geometries = discovery.search_basal_processing_geometries(
        catalog=catalog,
        request=BasalProcessingGeometryRequest(
            release_agent_id=release_id,
            release_orientation=SiteOrientation.FORWARD,
            terminal_nicked_strand=terminal_nicked_strand,
            retained_scar_template="NNNN",
            post_nick_template="NNNN",
            post_nick_domain_mode="preserve",
            require_release_site_excised=True,
        ),
        limits=BasalProcessingGeometrySearchLimits(
            max_search_nodes=agent_count,
            max_hits=agent_count,
        ),
    )
    return discovery.search_basal_processing_routes(
        basal_candidates=basal,
        processing_geometries=geometries,
        limits=BasalProcessingRouteSearchLimits(
            max_search_nodes=(agent_count if max_route_nodes is None else max_route_nodes),
            max_hits=agent_count,
        ),
    )


def test_hairpin_junction_route_proves_one_continuous_active_strand() -> None:
    result = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "complete"
    assert result.schema_id == "hop.hairpin-junction-route-search-result/v2"
    assert result.available_pair_count == 1
    assert result.search_nodes_examined == 1
    assert result.observed_hit_count == 1
    assert result.truncated_by == ()
    assert result.feasibility[0].blockers == ()

    route = result.hits[0]
    assert route.released_state.active_strand is hop.Strand.BOTTOM

    retired = result.model_dump(mode="json", by_alias=True)
    retired["schema"] = "hop.hairpin-junction-route-search-result/v1"
    with pytest.raises(ValidationError):
        HairpinJunctionRouteSearchResult.model_validate(retired)
    assert route.released_state.active_strand is route.basal_route.surviving_strand
    assert route.released_state.active_product_sequence == "ATT"
    assert route.released_state.precursor_top_strand == "AATC"
    assert route.released_foldback_precursor.precursor_digest.startswith("sha256:")
    assert route.route_id.startswith("hop:hairpin-junction-route/")
    assert (
        route.released_foldback_geometry.release_agent_id
        != route.basal_route.release.release_agent_id
    )


def test_hairpin_route_content_identity_excludes_search_ordinals() -> None:
    route = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    ).hits[0]

    original = hairpin_junction_route_id(
        geometry=route.released_foldback_geometry,
        released_foldback_precursor=route.released_foldback_precursor,
        basal_route=route.basal_route,
    )
    reordered = hairpin_junction_route_id(
        geometry=route.released_foldback_geometry.model_copy(update={"canonical_ordinal": 31}),
        released_foldback_precursor=route.released_foldback_precursor.model_copy(
            update={"canonical_ordinal": 41}
        ),
        basal_route=route.basal_route.model_copy(update={"canonical_ordinal": 59}),
    )

    assert reordered == original


def test_hairpin_junction_route_builds_its_own_released_workflow_view() -> None:
    route = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    ).hits[0]

    view = views.build_hairpin_junction_route_view(route)
    precursor_view = views.build_released_foldback_precursor_view(
        geometry=route.released_foldback_geometry,
        precursor=route.released_foldback_precursor,
        state=route.released_state,
    )

    assert view == precursor_view
    assert view.kind == "released_workflow"
    assert tuple(panel.panel_id for panel in view.panels) == (
        "precursor",
        "released_fragments",
        "origin_anchored_foldback",
    )
    assert view.panels[1].tracks[0].sequence == route.released_state.active_product_sequence
    assert view.panels[1].tracks[0].strand is route.released_state.active_strand
    assert view.panels[2].tracks[0].strand is route.released_state.active_strand
    assert len(view.panels[2].pairings) == len(route.released_foldback_geometry.pairing_domains)


def test_hairpin_junction_route_rejects_a_discontinuous_strand_path() -> None:
    result = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(
            terminal_nicked_strand=hop.Strand.BOTTOM,
            release_id="example:release-agent/foldback@1",
        ),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "infeasible"
    assert result.hits == ()
    assert (
        result.released_precursors.request.geometry.release_agent_id
        == result.basal_routes.processing_geometries.release.release_agent_id
    )
    assert result.feasibility[0].blockers == ("continuous_strand_mismatch",)


def test_hairpin_junction_route_preserves_upstream_and_local_truncation() -> None:
    released_limited = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(
            precursor_template="NNNN",
            max_search_nodes=1,
        ),
        basal_routes=_basal_routes(),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=4, max_hits=4),
    )
    node_limited = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(
            precursor_template="RAYC",
            max_search_nodes=2,
        ),
        basal_routes=_basal_routes(),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=2),
    )
    hit_limited = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(agent_count=2),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=2, max_hits=1),
    )
    basal_limited = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(agent_count=2, max_route_nodes=1),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=2, max_hits=2),
    )

    assert released_limited.status == "truncated"
    assert released_limited.truncated_by == ("released_precursors",)
    assert node_limited.status == "truncated"
    assert node_limited.truncated_by == ("max_search_nodes",)
    assert hit_limited.status == "truncated"
    assert hit_limited.observed_hit_count == 2
    assert hit_limited.truncated_by == ("max_hits",)
    assert basal_limited.status == "truncated"
    assert basal_limited.truncated_by == ("basal_routes",)


def test_hairpin_junction_route_result_rejects_replay_and_identity_drift() -> None:
    result = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )
    mutations = []
    payload = result.model_dump(mode="json", by_alias=True)
    payload["feasibility"][0]["blockers"] = ["continuous_strand_mismatch"]
    payload["feasibility"][0]["compatible"] = False
    mutations.append(payload)
    payload = result.model_dump(mode="json", by_alias=True)
    payload["hits"][0]["route_id"] = "hop:hairpin-junction-route/" + "0" * 64 + "@1"
    mutations.append(payload)
    payload = result.model_dump(mode="json", by_alias=True)
    payload["hits"][0]["released_state"]["active_product_sequence"] = "AAA"
    mutations.append(payload)
    payload = result.model_dump(mode="json", by_alias=True)
    payload["available_pair_count"] += 1
    mutations.append(payload)

    for payload in mutations:
        with pytest.raises(ValidationError):
            HairpinJunctionRouteSearchResult.model_validate_json(json.dumps(payload))


def test_hairpin_junction_candidate_rejects_cross_object_drift() -> None:
    released = _released_precursors(precursor_template="RAYC", max_search_nodes=2)
    basal = _basal_routes()
    result = discovery.search_hairpin_junction_routes(
        released_precursors=released,
        basal_routes=basal,
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=2, max_hits=2),
    )
    first, second = result.hits
    candidate_mutations: list[dict[str, object]] = []

    data = first.model_dump(mode="python")
    data["released_foldback_precursor"] = first.released_foldback_precursor.model_copy(
        update={"geometry_id": "hop:released-foldback-geometry/" + "0" * 64 + "@1"}
    )
    candidate_mutations.append(data)

    mismatch = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(terminal_nicked_strand=hop.Strand.BOTTOM),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )
    data = first.model_dump(mode="python")
    data["feasibility"] = mismatch.feasibility[0]
    candidate_mutations.append(data)

    data = first.model_dump(mode="python")
    data["feasibility"] = HairpinJunctionRouteFeasibility(
        released_foldback_precursor_id="example:precursor/drift@1",
        basal_route_id=first.basal_route.route_id,
        released_active_strand=hop.Strand.BOTTOM,
        basal_surviving_strand=hop.Strand.BOTTOM,
        blockers=(),
        compatible=True,
    )
    candidate_mutations.append(data)

    data = first.model_dump(mode="python")
    data["released_state"] = second.released_state
    candidate_mutations.append(data)

    data = first.model_dump(mode="python")
    data["released_state"] = first.released_state.model_copy(
        update={"nick": hop.NickEvent(boundary=hop.Boundary(offset=1), strand=hop.Strand.TOP)}
    )
    candidate_mutations.append(data)

    data = first.model_dump(mode="python")
    data["released_state"] = first.released_state.model_copy(
        update={
            "active_product_precursor_span": hop.Span(
                start=hop.Boundary(offset=0),
                end=hop.Boundary(offset=2),
            )
        }
    )
    candidate_mutations.append(data)

    data = first.model_dump(mode="python")
    data["released_state"] = first.released_state.model_copy(
        update={"active_nick_boundary": hop.Boundary(offset=2)}
    )
    candidate_mutations.append(data)

    for data in candidate_mutations:
        with pytest.raises(ValidationError):
            HairpinJunctionRouteCandidate.model_validate(data)


def test_hairpin_junction_candidate_rejects_a_reidentified_out_of_domain_precursor() -> None:
    route = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    ).hits[0]
    invalid_sequence = "CCCC"
    precursor = ReleasedFoldbackPrecursorCandidate(
        candidate_id=released_foldback_precursor_candidate_id(
            geometry_id=route.released_foldback_geometry.candidate_id,
            sequence=invalid_sequence,
        ),
        canonical_ordinal=route.released_foldback_precursor.canonical_ordinal,
        geometry_id=route.released_foldback_geometry.candidate_id,
        precursor_sequence=invalid_sequence,
        precursor_digest=sha256_digest(invalid_sequence.encode("utf-8")),
    )
    projection = hop.project_released_strand_state(
        hop.ReleaseProjectionRequest(
            precursor_top_strand=invalid_sequence,
            origin=route.released_foldback_geometry.active_product_span.start,
            nick=route.released_foldback_geometry.nick,
            release_cut=route.released_foldback_geometry.release_cut,
            release_site_span=hop.Span(
                start=hop.Boundary(offset=route.released_foldback_geometry.release_site_start),
                end=hop.Boundary(offset=route.released_foldback_geometry.release_site_end),
            ),
            route=route.released_state.route,
            constraints=hop.ReleaseProjectionConstraints(
                require_release_site_downstream_of_nick=False,
                require_complete_downstream_separation=False,
            ),
        )
    ).projection
    assert projection is not None

    data = route.model_dump(mode="python")
    data["released_foldback_precursor"] = precursor
    data["released_state"] = projection
    data["feasibility"] = hairpin_junction_route_feasibility(
        geometry=route.released_foldback_geometry,
        released_foldback_precursor=precursor,
        basal_route=route.basal_route,
    )
    data["route_id"] = hairpin_junction_route_id(
        geometry=route.released_foldback_geometry,
        released_foldback_precursor=precursor,
        basal_route=route.basal_route,
    )

    with pytest.raises(ValidationError, match="precursor must satisfy"):
        HairpinJunctionRouteCandidate.model_validate(data)


def test_hairpin_junction_result_rejects_search_accounting_drift() -> None:
    released = _released_precursors(precursor_template="RAYC", max_search_nodes=2)
    basal = _basal_routes()
    full = discovery.search_hairpin_junction_routes(
        released_precursors=released,
        basal_routes=basal,
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=2, max_hits=2),
    )
    bounded = discovery.search_hairpin_junction_routes(
        released_precursors=released,
        basal_routes=basal,
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )
    mutations: list[dict[str, object]] = []

    data = full.model_dump(mode="python")
    data["search_nodes_examined"] = 1
    mutations.append(data)
    data = full.model_dump(mode="python")
    data["feasibility"] = data["feasibility"][:1]
    mutations.append(data)
    data = full.model_dump(mode="python")
    data["observed_hit_count"] = 1
    mutations.append(data)
    data = full.model_dump(mode="python")
    data["hits"] = data["hits"][:1]
    mutations.append(data)
    data = full.model_dump(mode="python")
    data["hits"] = (
        full.hits[1].model_copy(update={"canonical_ordinal": 1}),
        full.hits[0].model_copy(update={"canonical_ordinal": 2}),
    )
    mutations.append(data)
    data = bounded.model_dump(mode="python")
    data["hits"] = (full.hits[1].model_copy(update={"canonical_ordinal": 1}),)
    mutations.append(data)
    data = full.model_dump(mode="python")
    data["status"] = "truncated"
    mutations.append(data)
    data = full.model_dump(mode="python")
    data["status"] = "infeasible"
    mutations.append(data)

    mismatch = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(),
        basal_routes=_basal_routes(terminal_nicked_strand=hop.Strand.BOTTOM),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )
    data = mismatch.model_dump(mode="python")
    data["status"] = "complete"
    mutations.append(data)

    for data in mutations:
        with pytest.raises(ValidationError):
            HairpinJunctionRouteSearchResult.model_validate(data)


def test_hairpin_junction_route_does_not_consume_pairs_beyond_node_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hop_design.design import junction_routes as route_design
    from hop_design.models.discovery import hairpin_routes as route_models

    def guarded_product(*iterables: tuple[object, ...]):
        for index, item in enumerate(itertools.product(*iterables)):
            if index == 1:
                raise AssertionError("route search consumed a pair beyond max_search_nodes")
            yield item

    monkeypatch.setattr(route_design, "product", guarded_product)
    monkeypatch.setattr(route_models, "product", guarded_product)
    result = discovery.search_hairpin_junction_routes(
        released_precursors=_released_precursors(
            precursor_template="RAYC",
            max_search_nodes=2,
        ),
        basal_routes=_basal_routes(),
        limits=HairpinJunctionRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "truncated"
    assert result.available_pair_count == 2
    assert result.search_nodes_examined == 1
    assert result.truncated_by == ("max_search_nodes",)

from __future__ import annotations

import itertools
import json

import pytest
from pydantic import ValidationError

import hop_design as hop
import hop_design.discovery as discovery
from hop_design.design import junction_routes as route_design
from hop_design.models.catalog import SiteOrientation
from hop_design.models.discovery import (
    BasalProcessingGeometryRequest,
    BasalProcessingGeometrySearchLimits,
    BasalProcessingRouteSearchLimits,
    BasalProcessingRouteSearchResult,
)
from hop_design.models.discovery import basal_routes as route_models


def _constraints() -> hop.BasalConstraintProfile:
    return hop.BasalConstraintProfile(
        require_terminal_watson_crick=True,
        allow_active_gt_wobble=True,
        max_active_hard_mismatches=0,
        max_active_non_watson_crick_pairs=1,
        forbid_active_middle_double_hard=True,
        minimum_active_pair_support_index=3.5,
        maximum_active_pair_disruption_index=0.5,
        require_outer_hard_for_active_double=True,
        reject_compact_profiles=(),
        reserve_compact_profiles=(),
    )


def _basal_candidates(
    *,
    left_template: str = "RAAA",
    max_search_nodes: int = 2,
) -> discovery.BasalCandidateSearchResult:
    return discovery.search_basal_candidates(
        discovery.BasalCandidateSearchRequest(
            left_arm_template=left_template,
            right_arm_template="TTGG" if left_template == "CCAA" else "TTTT",
            constraints=_constraints(),
            acceptance="active_only",
        ),
        limits=discovery.BasalCandidateSearchLimits(
            max_search_nodes=max_search_nodes,
            max_hits=4,
        ),
    )


def _processing_geometries(
    *,
    scar_motif: str = "ANNNN",
    agent_count: int = 1,
    max_search_nodes: int | None = None,
    max_hits: int = 2,
) -> discovery.BasalProcessingGeometrySearchResult:
    release_id = "example:release-agent/four-base-scar@1"
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/basal-routes@1",
        nicking_agents=tuple(
            hop.NickingAgent(
                agent_id=f"example:nicking-agent/terminal-{index}@1",
                motif_top_5to3=scar_motif,
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
    return discovery.search_basal_processing_geometries(
        catalog=catalog,
        request=BasalProcessingGeometryRequest(
            release_agent_id=release_id,
            release_orientation=SiteOrientation.FORWARD,
            terminal_nicked_strand=hop.Strand.TOP,
            retained_scar_template="NNNN",
            post_nick_template="N",
            post_nick_domain_mode="preserve",
            require_release_site_excised=True,
        ),
        limits=BasalProcessingGeometrySearchLimits(
            max_search_nodes=agent_count if max_search_nodes is None else max_search_nodes,
            max_hits=max_hits,
        ),
    )


def test_basal_route_search_joins_retained_scar_to_the_left_arm() -> None:
    result = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(),
        processing_geometries=_processing_geometries(),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=2, max_hits=2),
    )

    assert result.status == "complete"
    assert result.available_pair_count == 2
    assert result.search_nodes_examined == 2
    assert result.observed_hit_count == 1
    assert result.truncated_by == ()
    assert result.schema_id == "hop.basal-processing-route-search-result/v2"
    assert [row.blockers for row in result.feasibility] == [(), ("retained_scar_domain_conflict",)]

    route = result.hits[0]
    assert route.canonical_ordinal == 1
    assert route.basal_candidate.pairing.left_arm == "AAAA"
    assert route.processing_geometry.nicking_agent_id == "example:nicking-agent/terminal-1@1"
    assert route.terminal_nick == hop.NickEvent(
        boundary=hop.Boundary(offset=4),
        strand=hop.Strand.TOP,
    )
    assert route.surviving_strand is hop.Strand.BOTTOM
    assert route.route_id.startswith("hop:basal-processing-route/")

    retired = result.model_dump(mode="json", by_alias=True)
    retired["schema"] = "hop.basal-processing-route-search-result/v1"
    with pytest.raises(ValidationError):
        BasalProcessingRouteSearchResult.model_validate(retired)


def test_basal_route_content_identity_excludes_search_ordinals() -> None:
    result = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(),
        processing_geometries=_processing_geometries(),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=2, max_hits=2),
    )
    route = result.hits[0]

    original = route_models.basal_processing_route_id(
        release=route.release,
        basal_candidate=route.basal_candidate,
        processing_geometry=route.processing_geometry,
    )
    reordered = route_models.basal_processing_route_id(
        release=route.release,
        basal_candidate=route.basal_candidate.model_copy(update={"canonical_ordinal": 99}),
        processing_geometry=route.processing_geometry.model_copy(update={"canonical_ordinal": 77}),
    )

    assert reordered == original


def test_basal_route_search_rejects_a_regenerated_release_site() -> None:
    result = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(left_template="CCAA", max_search_nodes=1),
        processing_geometries=_processing_geometries(scar_motif="NNNNN"),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "infeasible"
    assert result.hits == ()
    assert result.feasibility[0].blockers == ("retained_release_site_present",)


def test_basal_route_search_propagates_upstream_and_local_bounds() -> None:
    upstream = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(max_search_nodes=1),
        processing_geometries=_processing_geometries(),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=2, max_hits=2),
    )
    node_limited = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(),
        processing_geometries=_processing_geometries(scar_motif="NNNNN"),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=1, max_hits=2),
    )

    assert upstream.status == "truncated"
    assert upstream.truncated_by == ("basal_candidates",)
    assert node_limited.status == "truncated"
    assert node_limited.truncated_by == ("max_search_nodes",)


def test_basal_route_search_reports_processing_and_hit_truncation_separately() -> None:
    processing_limited = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(left_template="AAAA", max_search_nodes=1),
        processing_geometries=_processing_geometries(
            scar_motif="NNNNN",
            agent_count=2,
            max_search_nodes=1,
        ),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=2, max_hits=2),
    )
    hit_limited = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(left_template="AAAA", max_search_nodes=1),
        processing_geometries=_processing_geometries(
            scar_motif="NNNNN",
            agent_count=2,
        ),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=2, max_hits=1),
    )

    assert processing_limited.status == "truncated"
    assert processing_limited.truncated_by == ("processing_geometries",)
    assert hit_limited.status == "truncated"
    assert hit_limited.observed_hit_count == 2
    assert len(hit_limited.hits) == 1
    assert hit_limited.truncated_by == ("max_hits",)


def test_basal_route_search_does_not_consume_pairs_beyond_the_node_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def guarded_product(*iterables: tuple[object, ...]):
        for index, item in enumerate(itertools.product(*iterables)):
            if index == 1:
                raise AssertionError("route search consumed a pair beyond max_search_nodes")
            yield item

    monkeypatch.setattr(route_design, "product", guarded_product)
    monkeypatch.setattr(route_models, "product", guarded_product)

    result = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(),
        processing_geometries=_processing_geometries(),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "truncated"
    assert result.available_pair_count == 2
    assert result.search_nodes_examined == 1
    assert result.truncated_by == ("max_search_nodes",)


def test_basal_route_result_rejects_cross_object_and_identity_drift() -> None:
    result = discovery.search_basal_processing_routes(
        basal_candidates=_basal_candidates(),
        processing_geometries=_processing_geometries(),
        limits=BasalProcessingRouteSearchLimits(max_search_nodes=2, max_hits=2),
    )
    mutations = []
    payload = result.model_dump(mode="json", by_alias=True)
    payload["feasibility"][0]["blockers"] = ["retained_scar_domain_conflict"]
    payload["feasibility"][0]["compatible"] = False
    mutations.append(payload)
    payload = result.model_dump(mode="json", by_alias=True)
    payload["hits"][0]["route_id"] = "hop:basal-processing-route/" + "0" * 64 + "@1"
    mutations.append(payload)
    payload = result.model_dump(mode="json", by_alias=True)
    payload["hits"][0]["terminal_nick"]["strand"] = "bottom"
    mutations.append(payload)
    payload = result.model_dump(mode="json", by_alias=True)
    payload["available_pair_count"] += 1
    mutations.append(payload)
    payload = result.model_dump(mode="json", by_alias=True)
    payload["truncated_by"] = ["max_hits"]
    payload["status"] = "truncated"
    mutations.append(payload)

    for payload in mutations:
        with pytest.raises(ValidationError):
            BasalProcessingRouteSearchResult.model_validate_json(json.dumps(payload))

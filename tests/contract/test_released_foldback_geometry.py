from __future__ import annotations

import pytest

import hop_design as hop
import hop_design.discovery as discovery
from hop_design.models.discovery import (
    ReleasedFoldbackGeometryRequest,
    ReleasedFoldbackGeometrySearchLimits,
    ReleasedFoldbackGeometrySearchResult,
)
from hop_design.models.discovery.released_foldback import (
    ReleasedFoldbackGeometryFeasibility,
)


def _catalog(*, near_nick: bool = False) -> hop.ProcessingCatalog:
    return hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/released-foldback@1",
        nicking_agents=(
            hop.NickingAgent(
                agent_id="example:nicking-agent/near@1"
                if near_nick
                else "example:nicking-agent/exact@1",
                motif_top_5to3="TAACGTT" if near_nick else "AACGTTG",
                nicked_strand=hop.Strand.TOP,
                cut_offset=1 if near_nick else 0,
                warning_codes=(),
            ),
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id="example:release-agent/downstream@1",
                motif_top_5to3="CCAA",
                top_cut_offset=1,
                bottom_cut_offset=0,
                warning_codes=(),
            ),
        ),
    )


def _request(*, displacement: int = 0) -> ReleasedFoldbackGeometryRequest:
    return ReleasedFoldbackGeometryRequest(
        target_nick_boundary=hop.Boundary(offset=0),
        paired_tract=hop.BasePairCount(value=3),
        turn_length=hop.NucleotideCount(value=3),
        route=hop.StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        max_boundary_displacement=hop.NucleotideCount(value=displacement),
        require_release_site_downstream_of_nick=True,
        require_complete_downstream_separation=True,
    )


def test_released_foldback_geometry_resolves_one_exact_agent_pair() -> None:
    result = discovery.search_released_foldback_geometries(
        catalog=_catalog(),
        request=_request(),
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    )

    assert result.status == "complete"
    assert result.candidate_space_size == 2
    assert result.search_nodes_examined == 2
    assert result.observed_hit_count == 1
    assert result.truncated_by == ()

    hit = result.hits[0]
    assert hit.hit_kind == "exact"
    assert hit.evaluated_nick_boundary == hop.Boundary(offset=0)
    assert hit.nick == hop.NickEvent(boundary=hop.Boundary(offset=0), strand=hop.Strand.TOP)
    assert hit.release_orientation == "forward"
    assert hit.release_cut == hop.DuplexCut(
        top=hop.Boundary(offset=10),
        bottom=hop.Boundary(offset=9),
    )
    assert hit.active_product_span == hop.Span(
        start=hop.Boundary(offset=0),
        end=hop.Boundary(offset=9),
    )
    assert hit.active_nick_boundary == hop.Boundary(offset=9)
    assert hit.required_precursor == hop.NucleotideCount(value=13)
    assert hit.candidate_sequence_count == 1
    assert [(pair.left_coordinate, pair.right_coordinate) for pair in hit.pairing_domains] == [
        (0, 8),
        (1, 7),
        (2, 6),
    ]
    assert result.feasibility[1].blockers == ("processing_domain_conflict",)


def test_released_foldback_geometry_reports_a_near_boundary_without_hiding_search() -> None:
    result = discovery.search_released_foldback_geometries(
        catalog=_catalog(near_nick=True),
        request=_request(displacement=1),
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=4, max_hits=4),
    )

    assert result.status == "complete"
    assert result.candidate_space_size == 4
    assert result.search_nodes_examined == 4
    assert result.observed_hit_count == 1
    hit = result.hits[0]
    assert hit.hit_kind == "nearest"
    assert hit.boundary_displacement == hop.NucleotideCount(value=1)
    assert hit.evaluated_nick_boundary == hop.Boundary(offset=1)
    assert hit.nick_site_start == 0
    assert hit.active_product_span.end == hop.Boundary(offset=10)
    assert hit.required_precursor == hop.NucleotideCount(value=14)


def test_released_foldback_geometry_reports_pair_node_truncation() -> None:
    result = discovery.search_released_foldback_geometries(
        catalog=_catalog(),
        request=_request(),
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "truncated"
    assert result.candidate_space_size == 2
    assert result.search_nodes_examined == 1
    assert result.observed_hit_count == 1
    assert result.truncated_by == ("max_search_nodes",)


def test_released_foldback_geometry_supports_top_active_routes() -> None:
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/top-active@1",
        nicking_agents=(
            hop.NickingAgent(
                agent_id="example:nicking-agent/bottom@1",
                motif_top_5to3="AACGTTG",
                nicked_strand=hop.Strand.BOTTOM,
                cut_offset=0,
                warning_codes=(),
            ),
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id="example:release-agent/top@1",
                motif_top_5to3="CCAA",
                top_cut_offset=0,
                bottom_cut_offset=1,
                warning_codes=(),
            ),
        ),
    )
    request = _request().model_copy(
        update={"route": hop.StrandExposureRoute.TOP_ACTIVE_AFTER_BOTTOM_NICK}
    )

    result = discovery.search_released_foldback_geometries(
        catalog=catalog,
        request=request,
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    )

    assert result.status == "complete"
    hit = result.hits[0]
    assert hit.nick.strand is hop.Strand.BOTTOM
    assert hit.release_cut == hop.DuplexCut(
        top=hop.Boundary(offset=9),
        bottom=hop.Boundary(offset=10),
    )
    assert hit.active_nick_boundary == hop.Boundary(offset=0)


def test_released_foldback_geometry_distinguishes_hit_truncation() -> None:
    base = _catalog()
    catalog = base.model_copy(
        update={
            "release_agents": (
                *base.release_agents,
                base.release_agents[0].model_copy(
                    update={"agent_id": "example:release-agent/downstream-copy@1"}
                ),
            )
        }
    )

    result = discovery.search_released_foldback_geometries(
        catalog=catalog,
        request=_request(),
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=4, max_hits=1),
    )

    assert result.status == "truncated"
    assert result.candidate_space_size == 4
    assert result.observed_hit_count == 2
    assert len(result.hits) == 1
    assert result.truncated_by == ("max_hits",)


def test_released_foldback_geometry_reports_correlated_domain_cardinality() -> None:
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/symbolic-geometry@1",
        nicking_agents=(
            hop.NickingAgent(
                agent_id="example:nicking-agent/symbolic@1",
                motif_top_5to3="N",
                nicked_strand=hop.Strand.TOP,
                cut_offset=0,
                warning_codes=(),
            ),
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id="example:release-agent/symbolic@1",
                motif_top_5to3="N",
                top_cut_offset=0,
                bottom_cut_offset=0,
                warning_codes=(),
            ),
        ),
    )
    request = ReleasedFoldbackGeometryRequest(
        target_nick_boundary=hop.Boundary(offset=0),
        paired_tract=hop.BasePairCount(value=1),
        turn_length=hop.NucleotideCount(value=1),
        route=hop.StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        max_boundary_displacement=hop.NucleotideCount(value=0),
        require_release_site_downstream_of_nick=True,
        require_complete_downstream_separation=True,
    )

    result = discovery.search_released_foldback_geometries(
        catalog=catalog,
        request=request,
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    )

    assert result.observed_hit_count == 2
    assert result.hits[0].candidate_sequence_count == 64
    assert result.hits[0].pairing_domains[0].allowed_pairs == ("AT", "CG", "GC", "TA")


def test_released_foldback_geometry_distinguishes_pairing_from_process_conflict() -> None:
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/pair-conflict@1",
        nicking_agents=(
            hop.NickingAgent(
                agent_id="example:nicking-agent/left-a@1",
                motif_top_5to3="A",
                nicked_strand=hop.Strand.TOP,
                cut_offset=0,
                warning_codes=(),
            ),
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id="example:release-agent/right-a@1",
                motif_top_5to3="A",
                top_cut_offset=0,
                bottom_cut_offset=1,
                warning_codes=(),
            ),
        ),
    )
    request = ReleasedFoldbackGeometryRequest(
        target_nick_boundary=hop.Boundary(offset=0),
        paired_tract=hop.BasePairCount(value=1),
        turn_length=hop.NucleotideCount(value=0),
        route=hop.StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        max_boundary_displacement=hop.NucleotideCount(value=0),
        require_release_site_downstream_of_nick=True,
        require_complete_downstream_separation=False,
    )

    result = discovery.search_released_foldback_geometries(
        catalog=catalog,
        request=request,
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    )

    assert result.feasibility[0].blockers == ("foldback_pairing_domain_conflict",)
    assert result.feasibility[0].candidate_sequence_count == 0
    assert result.feasibility[1].compatible


def test_released_foldback_geometry_reports_exhaustive_infeasibility() -> None:
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/infeasible-foldback@1",
        nicking_agents=(
            hop.NickingAgent(
                agent_id="example:nicking-agent/left-a@1",
                motif_top_5to3="A",
                nicked_strand=hop.Strand.TOP,
                cut_offset=0,
                warning_codes=(),
            ),
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id="example:release-agent/right-s@1",
                motif_top_5to3="S",
                top_cut_offset=0,
                bottom_cut_offset=1,
                warning_codes=(),
            ),
        ),
    )
    request = ReleasedFoldbackGeometryRequest(
        target_nick_boundary=hop.Boundary(offset=0),
        paired_tract=hop.BasePairCount(value=1),
        turn_length=hop.NucleotideCount(value=0),
        route=hop.StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        max_boundary_displacement=hop.NucleotideCount(value=0),
        require_release_site_downstream_of_nick=True,
        require_complete_downstream_separation=False,
    )

    result = discovery.search_released_foldback_geometries(
        catalog=catalog,
        request=request,
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    )

    assert result.status == "infeasible"
    assert result.search_nodes_examined == result.candidate_space_size == 2
    assert result.observed_hit_count == 0
    assert result.hits == ()
    assert all(row.blockers == ("foldback_pairing_domain_conflict",) for row in result.feasibility)


def test_released_foldback_geometry_matches_sanitized_cross_agent_counts() -> None:
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/cross-agent-counts@1",
        nicking_agents=tuple(
            hop.NickingAgent(
                agent_id=f"example:nicking-agent/{agent_id}@1",
                motif_top_5to3=motif,
                nicked_strand=hop.Strand.TOP,
                cut_offset=cut_offset,
                warning_codes=(),
            )
            for agent_id, motif, cut_offset in (
                ("exact", "AACGTTG", 0),
                ("exact-alternate", "AAAGTTT", 0),
                ("near", "TAACGTT", 1),
            )
        ),
        release_agents=(
            hop.ReleaseAgent(
                agent_id="example:release-agent/exact@1",
                motif_top_5to3="CCAA",
                top_cut_offset=1,
                bottom_cut_offset=0,
                warning_codes=(),
            ),
            hop.ReleaseAgent(
                agent_id="example:release-agent/overlap@1",
                motif_top_5to3="GGGG",
                top_cut_offset=12,
                bottom_cut_offset=13,
                warning_codes=(),
            ),
        ),
    )
    request = ReleasedFoldbackGeometryRequest(
        target_nick_boundary=hop.Boundary(offset=0),
        paired_tract=hop.BasePairCount(value=3),
        turn_length=hop.NucleotideCount(value=3),
        route=hop.StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        max_boundary_displacement=hop.NucleotideCount(value=3),
        require_release_site_downstream_of_nick=True,
        require_complete_downstream_separation=True,
    )

    result = discovery.search_released_foldback_geometries(
        catalog=catalog,
        request=request,
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=48, max_hits=48),
    )

    assert result.status == "complete"
    assert result.candidate_space_size == 48
    assert sum(hit.hit_kind == "exact" for hit in result.hits) == 2
    assert sum(hit.hit_kind == "nearest" for hit in result.hits) == 9
    overlap_reverse = tuple(
        row
        for row in result.feasibility
        if row.release_agent_id == "example:release-agent/overlap@1"
        and row.release_orientation == "reverse"
    )
    assert overlap_reverse
    assert all("incomplete_downstream_separation" in row.blockers for row in overlap_reverse)


def test_released_foldback_result_rejects_replayed_geometry_drift() -> None:
    result = discovery.search_released_foldback_geometries(
        catalog=_catalog(),
        request=_request(),
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    )
    data = result.model_dump(mode="python")
    data["feasibility"][0]["nicking_agent_id"] = "example:nicking-agent/tampered@1"

    with pytest.raises(ValueError, match="replay canonical physical search nodes"):
        ReleasedFoldbackGeometrySearchResult.model_validate(data)


def test_released_foldback_feasibility_rejects_pair_outside_active_product() -> None:
    result = discovery.search_released_foldback_geometries(
        catalog=_catalog(),
        request=_request(),
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    )
    data = result.hits[0].model_dump(
        mode="python",
        exclude={"candidate_id", "canonical_ordinal"},
    )
    data["pairing_domains"][0]["right_coordinate"] = data["active_product_span"]["end"]["offset"]

    with pytest.raises(ValueError, match="active product span"):
        ReleasedFoldbackGeometryFeasibility.model_validate(data)


def test_released_foldback_search_does_not_materialize_nodes_beyond_the_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hop_design.models.discovery.released_foldback_evaluation as evaluator

    original_boundaries = evaluator.iter_released_foldback_boundaries

    def guarded_boundaries(request: ReleasedFoldbackGeometryRequest):
        for index, boundary in enumerate(original_boundaries(request)):
            if index > 0:
                raise AssertionError("search consumed a node beyond max_search_nodes")
            yield boundary

    monkeypatch.setattr(evaluator, "iter_released_foldback_boundaries", guarded_boundaries)
    result = discovery.search_released_foldback_geometries(
        catalog=_catalog(),
        request=_request(displacement=1_000_000),
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "truncated"
    assert result.search_nodes_examined == 1
    assert result.candidate_space_size == 2_000_002

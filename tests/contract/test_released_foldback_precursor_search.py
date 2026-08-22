from __future__ import annotations

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.models.discovery import (
    ReleasedFoldbackGeometryRequest,
    ReleasedFoldbackGeometrySearchLimits,
    ReleasedFoldbackPrecursorSearchLimits,
    ReleasedFoldbackPrecursorSearchRequest,
)
from hop_design.models.discovery.released_foldback import ReleasedFoldbackGeometryHit


def _selected_symbolic_geometry() -> ReleasedFoldbackGeometryHit:
    catalog = hop.ProcessingCatalog(
        catalog_id="example:processing-catalog/precursor-materialization@1",
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
    result = hop.search_released_foldback_geometries(
        catalog=catalog,
        request=request,
        limits=ReleasedFoldbackGeometrySearchLimits(max_search_nodes=2, max_hits=2),
    )
    assert result.status == "complete"
    return result.hits[0]


def test_released_foldback_precursor_search_materializes_only_caller_domains() -> None:
    result = hop.search_released_foldback_precursors(
        ReleasedFoldbackPrecursorSearchRequest(
            geometry=_selected_symbolic_geometry(),
            precursor_template="RAYC",
        ),
        limits=ReleasedFoldbackPrecursorSearchLimits(max_search_nodes=2, max_hits=2),
    )

    assert result.status == "complete"
    assert result.candidate_space_size == 2
    assert result.search_nodes_examined == 2
    assert result.observed_hit_count == 2
    assert result.truncated_by == ()
    assert [candidate.precursor_sequence for candidate in result.hits] == ["AATC", "GACC"]
    assert [candidate.rank for candidate in result.hits] == [1, 2]
    assert all(
        candidate.geometry_id == result.request.geometry.candidate_id for candidate in result.hits
    )


def test_released_foldback_precursor_search_reports_caller_domain_conflict() -> None:
    result = hop.search_released_foldback_precursors(
        ReleasedFoldbackPrecursorSearchRequest(
            geometry=_selected_symbolic_geometry(),
            precursor_template="AACC",
        ),
        limits=ReleasedFoldbackPrecursorSearchLimits(max_search_nodes=4, max_hits=4),
    )

    assert result.status == "infeasible"
    assert result.candidate_space_size == 0
    assert result.search_nodes_examined == 0
    assert result.observed_hit_count == 0
    assert result.hits == ()
    assert result.blockers == ("caller_domain_conflict",)


def test_released_foldback_precursor_search_separates_node_and_hit_truncation() -> None:
    request = ReleasedFoldbackPrecursorSearchRequest(
        geometry=_selected_symbolic_geometry(),
        precursor_template="NNNN",
    )

    by_nodes = hop.search_released_foldback_precursors(
        request,
        limits=ReleasedFoldbackPrecursorSearchLimits(max_search_nodes=1, max_hits=64),
    )
    by_hits = hop.search_released_foldback_precursors(
        request,
        limits=ReleasedFoldbackPrecursorSearchLimits(max_search_nodes=64, max_hits=1),
    )

    assert by_nodes.status == "truncated"
    assert by_nodes.candidate_space_size == 64
    assert by_nodes.search_nodes_examined == 1
    assert by_nodes.observed_hit_count == 1
    assert by_nodes.truncated_by == ("max_search_nodes",)
    assert by_hits.status == "truncated"
    assert by_hits.search_nodes_examined == 64
    assert by_hits.observed_hit_count == 64
    assert by_hits.truncated_by == ("max_hits",)
    assert by_hits.hits[0].precursor_sequence == "AATA"


def test_released_foldback_precursor_request_rejects_template_extent_drift() -> None:
    with pytest.raises(ValidationError, match="precursor_template length"):
        ReleasedFoldbackPrecursorSearchRequest(
            geometry=_selected_symbolic_geometry(),
            precursor_template="NNN",
        )


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"precursor_sequence": "GACC"}, "canonical physical order"),
        ({"candidate_space_size": 3}, "candidate_space_size"),
        ({"observed_hit_count": 1}, "observed hit"),
    ],
)
def test_released_foldback_precursor_result_rejects_replay_drift(
    update: dict[str, object],
    message: str,
) -> None:
    result = hop.search_released_foldback_precursors(
        ReleasedFoldbackPrecursorSearchRequest(
            geometry=_selected_symbolic_geometry(),
            precursor_template="RAYC",
        ),
        limits=ReleasedFoldbackPrecursorSearchLimits(max_search_nodes=2, max_hits=2),
    )
    data = result.model_dump(mode="python")
    if "precursor_sequence" in update:
        data["hits"] = ({**data["hits"][1], "rank": 1}, *data["hits"][1:])
    else:
        data.update(update)

    with pytest.raises(ValidationError, match=message):
        type(result).model_validate(data)


def test_released_foldback_precursor_search_does_not_consume_beyond_node_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hop_design.design.released_foldback as operation

    def guarded_enumerator(*args: object, **kwargs: object):
        yield "AATA"
        raise AssertionError("search consumed a sequence beyond max_search_nodes")

    monkeypatch.setattr(operation, "enumerate_released_foldback_precursors", guarded_enumerator)
    result = hop.search_released_foldback_precursors(
        ReleasedFoldbackPrecursorSearchRequest(
            geometry=_selected_symbolic_geometry(),
            precursor_template="NNNN",
        ),
        limits=ReleasedFoldbackPrecursorSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "truncated"
    assert result.search_nodes_examined == 1

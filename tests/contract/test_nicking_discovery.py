from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.design.discovery import search_nicking_placements
from hop_design.models.catalog import (
    NickingAgent,
    ProcessingCatalog,
    ReleaseAgent,
    SiteOrientation,
)
from hop_design.models.coordinates import BasePairCount, Boundary, NucleotideCount, Span
from hop_design.models.discovery import (
    NickingPlacementFeasibility,
    NickingPlacementHit,
    NickingPlacementSearchLimits,
    NickingPlacementTarget,
)
from hop_design.models.junction import Strand
from hop_design.models.strand_state import NickEvent


def _agent(
    agent_id: str,
    *,
    motif: str,
    nicked_strand: Strand,
    cut_offset: int,
) -> NickingAgent:
    return NickingAgent(
        agent_id=f"example:nicking-agent/{agent_id}@1",
        motif_top_5to3=motif,
        nicked_strand=nicked_strand,
        cut_offset=cut_offset,
        warning_codes=(),
    )


def _catalog(*agents: NickingAgent) -> ProcessingCatalog:
    return ProcessingCatalog(
        catalog_id="example:processing-catalog/discovery-parity@1",
        nicking_agents=agents,
        release_agents=(),
    )


def _target(*, boundary: int = 0, strand: Strand = Strand.TOP) -> NickingPlacementTarget:
    return NickingPlacementTarget(
        nick_boundary=Boundary(offset=boundary),
        nicked_strand=strand,
        paired_tract=BasePairCount(value=3),
        available_turn=NucleotideCount(value=3),
    )


def _parity_catalog() -> ProcessingCatalog:
    return _catalog(
        _agent("nt-bspqi", motif="GCTCTTC", nicked_strand=Strand.TOP, cut_offset=8),
        _agent("nt-cvipii", motif="CCD", nicked_strand=Strand.TOP, cut_offset=0),
        _agent("nb-bsrdi", motif="GCAATG", nicked_strand=Strand.BOTTOM, cut_offset=6),
        _agent("nb-btsi", motif="GCAGTG", nicked_strand=Strand.BOTTOM, cut_offset=6),
        _agent("nt-bpu10i", motif="CCTNAGC", nicked_strand=Strand.TOP, cut_offset=2),
    )


def test_nicking_discovery_finds_sanitized_exact_and_nearest_geometries() -> None:
    result = search_nicking_placements(
        catalog=_parity_catalog(),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=20, max_hits=20),
    )

    assert result.status == "complete"
    assert result.candidate_space_size == 5
    assert result.search_nodes_examined == 5
    assert result.observed_hit_count == 5
    assert [hit.agent_id for hit in result.hits[:3]] == [
        "example:nicking-agent/nt-cvipii@1",
        "example:nicking-agent/nb-bsrdi@1",
        "example:nicking-agent/nb-btsi@1",
    ]
    assert [hit.hit_kind for hit in result.hits] == [
        "exact",
        "exact",
        "exact",
        "nearest",
        "nearest",
    ]

    bsrdi = result.hits[1]
    assert bsrdi.orientation == "reverse"
    assert bsrdi.oriented_motif_5to3 == "CATTGC"
    assert bsrdi.site_span.start.offset == 0
    assert bsrdi.site_span.end.offset == 6
    assert bsrdi.nick.boundary.offset == 0
    assert bsrdi.nick.strand is Strand.TOP
    assert bsrdi.required_precursor.value == 6
    assert bsrdi.required_turn.value == 3

    bpu10i = result.hits[3]
    assert bpu10i.hit_kind == "nearest"
    assert bpu10i.nick.boundary.offset == 2
    assert bpu10i.boundary_displacement.value == 2
    assert bpu10i.required_precursor.value == 7
    assert bpu10i.required_turn.value == 2

    feasibility = {row.agent_id: row for row in result.feasibility}
    assert feasibility["example:nicking-agent/nt-bpu10i@1"].exact_blockers == ("HOP-DISC-001",)
    assert feasibility["example:nicking-agent/nt-bspqi@1"].earliest_feasible_boundary == Boundary(
        offset=8
    )


def test_nicking_discovery_is_catalog_order_invariant_and_physically_ordered() -> None:
    catalog = _parity_catalog()
    limits = NickingPlacementSearchLimits(max_search_nodes=20, max_hits=20)

    forward = search_nicking_placements(catalog=catalog, target=_target(), limits=limits)
    reverse = search_nicking_placements(
        catalog=catalog.model_copy(
            update={"nicking_agents": tuple(reversed(catalog.nicking_agents))}
        ),
        target=_target(),
        limits=limits,
    )

    assert forward == reverse


def test_nicking_discovery_reports_node_and_result_truncation_separately() -> None:
    by_nodes = search_nicking_placements(
        catalog=_parity_catalog(),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=2, max_hits=20),
    )
    by_hits = search_nicking_placements(
        catalog=_parity_catalog(),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=20, max_hits=2),
    )

    assert by_nodes.status == "truncated"
    assert by_nodes.truncated_by == ("max_search_nodes",)
    assert by_nodes.search_nodes_examined == 2
    assert len(by_nodes.feasibility) == 2
    assert by_hits.status == "truncated"
    assert by_hits.truncated_by == ("max_hits",)
    assert by_hits.search_nodes_examined == 5
    assert by_hits.observed_hit_count == 5
    assert len(by_hits.hits) == 2


def test_nicking_discovery_keeps_reverse_geometry_for_palindromic_motif() -> None:
    result = search_nicking_placements(
        catalog=_catalog(
            _agent("palindrome", motif="AATT", nicked_strand=Strand.BOTTOM, cut_offset=1)
        ),
        target=_target(boundary=3, strand=Strand.TOP),
        limits=NickingPlacementSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "complete"
    assert result.hits[0].orientation == "reverse"
    assert result.hits[0].oriented_motif_5to3 == "AATT"
    assert result.hits[0].nick.boundary.offset == 3
    assert result.hits[0].nick.strand is Strand.TOP


def test_nicking_discovery_can_truthfully_report_no_eligible_agents() -> None:
    result = search_nicking_placements(
        catalog=ProcessingCatalog(
            catalog_id="example:processing-catalog/release-only@1",
            nicking_agents=(),
            release_agents=(
                # The release entry is irrelevant to this bounded search.
                # It keeps the processing catalog valid without a nicking agent.
                ReleaseAgent(
                    agent_id="example:release-agent/synthetic@1",
                    motif_top_5to3="CCAA",
                    top_cut_offset=1,
                    bottom_cut_offset=0,
                    warning_codes=(),
                ),
            ),
        ),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "infeasible"
    assert result.candidate_space_size == 0
    assert result.search_nodes_examined == 0
    assert result.observed_hit_count == 0
    assert result.hits == ()
    assert result.feasibility == ()


def test_nicking_discovery_reports_a_fully_examined_infeasible_catalog() -> None:
    result = search_nicking_placements(
        catalog=_catalog(
            _agent("too-long", motif="AAAAAAA", nicked_strand=Strand.TOP, cut_offset=0)
        ),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "infeasible"
    assert result.feasibility[0].exact_blockers == ("HOP-DISC-002",)
    assert result.feasibility[0].earliest_feasible_boundary is None
    assert result.hits == ()


def test_nicking_discovery_rejects_an_empty_paired_tract() -> None:
    with pytest.raises(ValidationError, match="paired_tract"):
        NickingPlacementTarget(
            nick_boundary=Boundary(offset=0),
            nicked_strand=Strand.TOP,
            paired_tract=BasePairCount(value=0),
            available_turn=NucleotideCount(value=3),
        )


def test_nicking_discovery_result_rejects_untruthful_completion() -> None:
    result = search_nicking_placements(
        catalog=_parity_catalog(),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=2, max_hits=20),
    )
    serialized = result.model_dump(mode="json")
    serialized["status"] = "complete"

    with pytest.raises(ValidationError, match="truncated"):
        type(result).model_validate(serialized)


def test_discovery_evidence_models_reject_invalid_motifs_and_extents() -> None:
    with pytest.raises(ValidationError, match="DNA sequence"):
        NickingPlacementFeasibility(
            agent_id="example:nicking-agent/invalid@1",
            orientation=SiteOrientation.FORWARD,
            oriented_motif_5to3=7,
            site_start_at_target_boundary=0,
            site_end_at_target_boundary=1,
            exact_blockers=(),
            earliest_feasible_boundary=Boundary(offset=0),
        )
    with pytest.raises(ValidationError, match="Target-relative site extent"):
        NickingPlacementFeasibility(
            agent_id="example:nicking-agent/invalid@1",
            orientation=SiteOrientation.FORWARD,
            oriented_motif_5to3="AAAA",
            site_start_at_target_boundary=0,
            site_end_at_target_boundary=3,
            exact_blockers=(),
            earliest_feasible_boundary=Boundary(offset=0),
        )
    with pytest.raises(ValidationError, match="duplicates"):
        NickingPlacementFeasibility(
            agent_id="example:nicking-agent/invalid@1",
            orientation=SiteOrientation.FORWARD,
            oriented_motif_5to3="AAAA",
            site_start_at_target_boundary=0,
            site_end_at_target_boundary=4,
            exact_blockers=("HOP-DISC-001", "HOP-DISC-001"),
            earliest_feasible_boundary=Boundary(offset=4),
        )

    valid_hit = NickingPlacementHit(
        hit_kind="exact",
        agent_id="example:nicking-agent/invalid@1",
        orientation=SiteOrientation.FORWARD,
        oriented_motif_5to3="AAAA",
        site_span=Span(start=Boundary(offset=0), end=Boundary(offset=4)),
        nick=NickEvent(boundary=Boundary(offset=0), strand=Strand.TOP),
        boundary_displacement=NucleotideCount(value=0),
        required_precursor=NucleotideCount(value=4),
        required_turn=NucleotideCount(value=1),
    )
    with pytest.raises(ValidationError, match="Placed site extent"):
        type(valid_hit).model_validate(
            {
                **valid_hit.model_dump(),
                "oriented_motif_5to3": "AAA",
            }
        )
    with pytest.raises(ValidationError, match="complete motif"):
        type(valid_hit).model_validate(
            {
                **valid_hit.model_dump(),
                "required_precursor": NucleotideCount(value=3),
            }
        )


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"candidate_space_size": 1}, "cannot exceed"),
        ({"feasibility": ()}, "Feasibility rows"),
        ({"observed_hit_count": 3}, "observed_hit_count"),
        ({"observed_hit_count": 1}, "Returned hits"),
        ({"truncated_by": ()}, "truncated_by"),
    ],
)
def test_discovery_result_rejects_inconsistent_accounting(
    updates: dict[str, object], message: str
) -> None:
    result = search_nicking_placements(
        catalog=_parity_catalog(),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=2, max_hits=20),
    )

    with pytest.raises(ValidationError, match=message):
        type(result).model_validate({**result.model_dump(), **updates})


def test_discovery_result_rejects_duplicate_feasibility_agents() -> None:
    result = search_nicking_placements(
        catalog=_parity_catalog(),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=2, max_hits=20),
    )

    with pytest.raises(ValidationError, match="unique agent"):
        type(result).model_validate(
            {
                **result.model_dump(),
                "feasibility": (result.feasibility[0], result.feasibility[0]),
            }
        )


@pytest.mark.parametrize(
    ("hit_update", "message"),
    [
        ({"nick": NickEvent(boundary=Boundary(offset=0), strand=Strand.BOTTOM)}, "target strand"),
        ({"boundary_displacement": NucleotideCount(value=1)}, "displacement"),
        ({"hit_kind": "nearest"}, "Hit kind"),
        ({"required_precursor": NucleotideCount(value=99)}, "precursor length"),
        ({"required_turn": NucleotideCount(value=99)}, "turn length"),
    ],
)
def test_discovery_result_rejects_hit_projection_drift(
    hit_update: dict[str, object], message: str
) -> None:
    result = search_nicking_placements(
        catalog=_parity_catalog(),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=20, max_hits=20),
    )
    changed_hit = result.hits[0].model_copy(update=hit_update)

    with pytest.raises(ValidationError, match=message):
        type(result).model_validate(
            {
                **result.model_dump(),
                "hits": (changed_hit, *result.hits[1:]),
            }
        )

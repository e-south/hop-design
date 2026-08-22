from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.design.candidates import search_foldback_precursors
from hop_design.design.discovery import search_nicking_placements
from hop_design.models.catalog import NickingAgent, ProcessingCatalog
from hop_design.models.coordinates import BasePairCount, Boundary, NucleotideCount
from hop_design.models.discovery import (
    AdditionalNickConstraint,
    FoldbackPrecursorSearchLimits,
    FoldbackPrecursorSearchRequest,
    NickingPlacementSearchLimits,
    NickingPlacementTarget,
)
from hop_design.models.junction import Strand


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


def _target() -> NickingPlacementTarget:
    return NickingPlacementTarget(
        nick_boundary=Boundary(offset=0),
        nicked_strand=Strand.TOP,
        paired_tract=BasePairCount(value=3),
        available_turn=NucleotideCount(value=3),
    )


def _placement(agent: NickingAgent):
    result = search_nicking_placements(
        catalog=ProcessingCatalog(
            catalog_id="example:processing-catalog/candidate-parity@1",
            nicking_agents=(agent,),
            release_agents=(),
        ),
        target=_target(),
        limits=NickingPlacementSearchLimits(max_search_nodes=1, max_hits=1),
    )
    assert result.status == "complete"
    return result.hits[0]


def _request(
    agent: NickingAgent,
    *,
    precursor_template: str,
    turn_extension_template: str,
) -> FoldbackPrecursorSearchRequest:
    return FoldbackPrecursorSearchRequest(
        agent=agent,
        target=_target(),
        placement=_placement(agent),
        precursor_template=precursor_template,
        turn_extension_template=turn_extension_template,
        additional_nicks=AdditionalNickConstraint.ALLOW,
    )


def test_foldback_precursor_search_matches_sanitized_predecessor_candidate() -> None:
    agent = _agent(
        "nb-bsrdi",
        motif="GCAATG",
        nicked_strand=Strand.BOTTOM,
        cut_offset=6,
    )

    result = search_foldback_precursors(
        _request(agent, precursor_template="NNNNNN", turn_extension_template=""),
        limits=FoldbackPrecursorSearchLimits(max_search_nodes=4, max_hits=4),
    )

    assert result.status == "complete"
    assert result.candidate_space_size == 1
    assert result.search_nodes_examined == 1
    assert result.observed_hit_count == 1
    assert result.truncated_by == ()
    candidate = result.hits[0]
    assert candidate.precursor_sequence == "CATTGC"
    assert candidate.turn_extension == ""
    assert candidate.evaluation.foldback_arm == "ATG"
    assert candidate.evaluation.designed_sequence == "CATTGCATG"
    assert candidate.intended_site.matched_sequence == "CATTGC"
    assert candidate.extra_nick_sites == ()
    assert candidate.extra_target_strand_nick_count == 0


def test_foldback_precursor_search_requires_caller_authored_filler_domains() -> None:
    agent = _agent(
        "nb-bsrdi",
        motif="GCAATG",
        nicked_strand=Strand.BOTTOM,
        cut_offset=6,
    )

    result = search_foldback_precursors(
        _request(agent, precursor_template="AAAAAA", turn_extension_template=""),
        limits=FoldbackPrecursorSearchLimits(max_search_nodes=4, max_hits=4),
    )

    assert result.status == "infeasible"
    assert result.candidate_space_size == 0
    assert result.search_nodes_examined == 0
    assert result.hits == ()
    assert [(item.code, item.count) for item in result.rejections] == [("HOP-CAND-001", 1)]


def test_foldback_precursor_search_reports_node_and_hit_truncation() -> None:
    agent = _agent(
        "nt-cvipii",
        motif="CCD",
        nicked_strand=Strand.TOP,
        cut_offset=0,
    )
    request = _request(agent, precursor_template="NNN", turn_extension_template="NNN")

    by_nodes = search_foldback_precursors(
        request,
        limits=FoldbackPrecursorSearchLimits(max_search_nodes=1, max_hits=200),
    )
    by_hits = search_foldback_precursors(
        request,
        limits=FoldbackPrecursorSearchLimits(max_search_nodes=192, max_hits=1),
    )

    assert by_nodes.status == "truncated"
    assert by_nodes.candidate_space_size == 192
    assert by_nodes.search_nodes_examined == 1
    assert by_nodes.truncated_by == ("max_search_nodes",)
    assert by_hits.status == "truncated"
    assert by_hits.search_nodes_examined == 192
    assert by_hits.observed_hit_count == 192
    assert by_hits.truncated_by == ("max_hits",)
    assert by_hits.hits[0].precursor_sequence == "CCA"
    assert by_hits.hits[0].turn_extension == "AAT"
    assert by_hits.hits[0].evaluation.designed_sequence == "CCAAATTGG"


def test_foldback_precursor_search_applies_explicit_additional_nick_policy() -> None:
    agent = _agent(
        "nt-cvipii",
        motif="CCD",
        nicked_strand=Strand.TOP,
        cut_offset=0,
    )
    request = _request(agent, precursor_template="NNN", turn_extension_template="NNN")
    limits = FoldbackPrecursorSearchLimits(max_search_nodes=192, max_hits=192)

    target_strand_only = search_foldback_precursors(
        request.model_copy(
            update={"additional_nicks": AdditionalNickConstraint.FORBID_TARGET_STRAND}
        ),
        limits=limits,
    )
    forbid_any = search_foldback_precursors(
        request.model_copy(update={"additional_nicks": AdditionalNickConstraint.FORBID_ANY}),
        limits=limits,
    )

    assert target_strand_only.status == "complete"
    assert target_strand_only.observed_hit_count == 159
    assert [(item.code, item.count) for item in target_strand_only.rejections] == [
        ("HOP-CAND-002", 33)
    ]
    assert forbid_any.status == "infeasible"
    assert forbid_any.observed_hit_count == 0
    assert [(item.code, item.count) for item in forbid_any.rejections] == [("HOP-CAND-002", 192)]


def test_foldback_precursor_search_result_rejects_accounting_drift() -> None:
    agent = _agent(
        "nb-bsrdi",
        motif="GCAATG",
        nicked_strand=Strand.BOTTOM,
        cut_offset=6,
    )
    result = search_foldback_precursors(
        _request(agent, precursor_template="NNNNNN", turn_extension_template=""),
        limits=FoldbackPrecursorSearchLimits(max_search_nodes=4, max_hits=4),
    )

    with pytest.raises(ValidationError, match="observed_hit_count"):
        type(result).model_validate({**result.model_dump(), "observed_hit_count": 2})


@pytest.mark.parametrize(
    ("candidate_update", "message"),
    [
        ({"precursor_sequence": "AATTGC"}, "precursor"),
        ({"turn_extension": "A"}, "turn extension"),
        ({"extra_target_strand_nick_count": 1}, "target-strand"),
        ({"gc_fraction_added": 0.99}, "GC fraction"),
        ({"max_homopolymer_run_added": 99}, "homopolymer"),
    ],
)
def test_foldback_precursor_candidate_rejects_projection_drift(
    candidate_update: dict[str, object], message: str
) -> None:
    agent = _agent(
        "nb-bsrdi",
        motif="GCAATG",
        nicked_strand=Strand.BOTTOM,
        cut_offset=6,
    )
    result = search_foldback_precursors(
        _request(agent, precursor_template="NNNNNN", turn_extension_template=""),
        limits=FoldbackPrecursorSearchLimits(max_search_nodes=4, max_hits=4),
    )
    candidate = result.hits[0]

    with pytest.raises(ValidationError, match=message):
        type(candidate).model_validate({**candidate.model_dump(), **candidate_update})


@pytest.mark.parametrize(
    ("request_update", "message"),
    [
        ({"precursor_template": "NNNNN"}, "precursor_template length"),
        ({"turn_extension_template": "N"}, "turn_extension_template length"),
    ],
)
def test_foldback_precursor_request_rejects_template_extent_drift(
    request_update: dict[str, object], message: str
) -> None:
    agent = _agent(
        "nb-bsrdi",
        motif="GCAATG",
        nicked_strand=Strand.BOTTOM,
        cut_offset=6,
    )
    request = _request(agent, precursor_template="NNNNNN", turn_extension_template="")

    with pytest.raises(ValidationError, match=message):
        type(request).model_validate({**request.model_dump(), **request_update})


def test_foldback_precursor_request_rejects_selected_placement_drift() -> None:
    agent = _agent(
        "nb-bsrdi",
        motif="GCAATG",
        nicked_strand=Strand.BOTTOM,
        cut_offset=6,
    )
    request = _request(agent, precursor_template="NNNNNN", turn_extension_template="")

    with pytest.raises(ValidationError, match="placement"):
        FoldbackPrecursorSearchRequest.model_validate(
            {
                **request.model_dump(mode="json"),
                "placement": {
                    **request.placement.model_dump(mode="json"),
                    "oriented_motif_5to3": "CACTGC",
                },
            }
        )

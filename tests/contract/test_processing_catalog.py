from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.kernel.site_scanning import (
    classify_motif_presence,
    scan_nicking_agent,
    scan_release_agent,
)
from hop_design.models.catalog import (
    MotifPresence,
    NickingAgent,
    ProcessingCatalog,
    ReleaseAgent,
    SiteOrientation,
)
from hop_design.models.junction import Strand
from hop_design.models.physical import (
    opposite_strand,
    orient_nick_geometry,
    orient_release_geometry,
)


def _nicking_agent() -> NickingAgent:
    return NickingAgent(
        agent_id="example:nicking-agent/synthetic-a@1",
        motif_top_5to3="AAGC",
        nicked_strand=Strand.TOP,
        cut_offset=1,
        warning_codes=(),
    )


def _release_agent() -> ReleaseAgent:
    return ReleaseAgent(
        agent_id="example:release-agent/synthetic-b@1",
        motif_top_5to3="CCAA",
        top_cut_offset=1,
        bottom_cut_offset=0,
        warning_codes=(),
    )


def test_nicking_scan_resolves_forward_and_reverse_strand_geometry() -> None:
    matches = scan_nicking_agent("AAGCGCTT", agent=_nicking_agent())

    assert [(match.orientation, match.site_span.start.offset) for match in matches] == [
        ("forward", 0),
        ("reverse", 4),
    ]
    assert matches[0].nick.boundary.offset == 1
    assert matches[0].nick.strand is Strand.TOP
    assert matches[1].nick.boundary.offset == 7
    assert matches[1].nick.strand is Strand.BOTTOM


def test_release_scan_swaps_cut_offsets_for_reverse_orientation() -> None:
    matches = scan_release_agent("CCAATTGG", agent=_release_agent())

    assert [(match.orientation, match.site_span.start.offset) for match in matches] == [
        ("forward", 0),
        ("reverse", 4),
    ]
    assert (matches[0].cut.top.offset, matches[0].cut.bottom.offset) == (1, 0)
    assert (matches[1].cut.top.offset, matches[1].cut.bottom.offset) == (8, 7)


def test_palindromic_nick_scan_preserves_both_authoritative_orientations() -> None:
    agent = NickingAgent(
        agent_id="example:nicking-agent/palindromic@1",
        motif_top_5to3="AATT",
        nicked_strand=Strand.TOP,
        cut_offset=1,
        warning_codes=(),
    )

    matches = scan_nicking_agent("AATT", agent=agent)
    expected_geometries = (
        orient_nick_geometry(
            motif_top_5to3=agent.motif_top_5to3,
            native_nicked_strand=agent.nicked_strand,
            cut_offset=agent.cut_offset,
            target_strand=agent.nicked_strand,
        ),
        orient_nick_geometry(
            motif_top_5to3=agent.motif_top_5to3,
            native_nicked_strand=agent.nicked_strand,
            cut_offset=agent.cut_offset,
            target_strand=opposite_strand(agent.nicked_strand),
        ),
    )

    assert [match.orientation for match in matches] == [
        geometry.orientation for geometry in expected_geometries
    ]
    assert [match.matched_sequence for match in matches] == [
        geometry.motif_top_5to3 for geometry in expected_geometries
    ]
    assert [(match.nick.strand, match.nick.boundary.offset) for match in matches] == [
        (Strand.TOP, 1),
        (Strand.BOTTOM, 3),
    ]


def test_palindromic_release_scan_preserves_both_authoritative_orientations() -> None:
    agent = ReleaseAgent(
        agent_id="example:release-agent/palindromic@1",
        motif_top_5to3="AATT",
        top_cut_offset=1,
        bottom_cut_offset=2,
        warning_codes=(),
    )

    matches = scan_release_agent("AATT", agent=agent)
    expected_geometries = tuple(
        orient_release_geometry(
            motif_top_5to3=agent.motif_top_5to3,
            top_cut_offset=agent.top_cut_offset,
            bottom_cut_offset=agent.bottom_cut_offset,
            orientation=orientation,
        )
        for orientation in (SiteOrientation.FORWARD, SiteOrientation.REVERSE)
    )

    assert [match.orientation for match in matches] == [
        geometry.orientation for geometry in expected_geometries
    ]
    assert [match.matched_sequence for match in matches] == [
        geometry.motif_top_5to3 for geometry in expected_geometries
    ]
    assert [(match.cut.top.offset, match.cut.bottom.offset) for match in matches] == [
        (1, 2),
        (2, 3),
    ]


def test_palindromic_motif_presence_remains_one_textual_match() -> None:
    report = classify_motif_presence(sequence="AATT", motif="AATT")

    assert [(match.orientation, match.span.start.offset) for match in report.matches] == [
        (SiteOrientation.FORWARD, 0)
    ]


@pytest.mark.parametrize(
    ("top_offset", "bottom_offset"),
    [(100, 101), (-100, 0)],
)
def test_release_scan_filters_resolved_cuts_outside_the_sequence(
    top_offset: int,
    bottom_offset: int,
) -> None:
    agent = _release_agent().model_copy(
        update={"top_cut_offset": top_offset, "bottom_cut_offset": bottom_offset}
    )

    assert scan_release_agent("CCAATTGG", agent=agent) == ()


def test_symbolic_motif_presence_distinguishes_guaranteed_possible_and_absent() -> None:
    guaranteed = classify_motif_presence(sequence="AAN", motif="AAN")
    possible = classify_motif_presence(sequence="AAN", motif="AAC")
    absent = classify_motif_presence(sequence="AAN", motif="CCC")

    assert guaranteed.status is MotifPresence.GUARANTEED
    assert guaranteed.matches[0].certainty is MotifPresence.GUARANTEED
    assert possible.status is MotifPresence.POSSIBLE
    assert possible.matches[0].certainty is MotifPresence.POSSIBLE
    assert absent.status is MotifPresence.ABSENT
    assert absent.matches == ()


def test_processing_catalog_is_strict_versioned_and_has_unique_agent_ids() -> None:
    catalog = ProcessingCatalog(
        schema="hop.processing-catalog/v1",
        catalog_id="example:processing-catalog/synthetic@1",
        nicking_agents=(_nicking_agent(),),
        release_agents=(_release_agent(),),
    )

    assert catalog.by_id(_nicking_agent().agent_id) == _nicking_agent()
    assert catalog.by_id(_release_agent().agent_id) == _release_agent()

    with pytest.raises(ValidationError, match="unique"):
        ProcessingCatalog(
            schema="hop.processing-catalog/v1",
            catalog_id="example:processing-catalog/invalid@1",
            nicking_agents=(_nicking_agent(), _nicking_agent()),
            release_agents=(),
        )


def test_site_scanners_reject_symbolic_sequences_that_require_concrete_events() -> None:
    with pytest.raises(ValueError, match="exact DNA"):
        scan_nicking_agent("AANC", agent=_nicking_agent())

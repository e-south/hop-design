from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hop_design.design.processing import project_released_strand_state
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.strand_state import (
    DuplexCut,
    NickEvent,
    ReleasedStrandState,
    ReleaseProjectionConstraints,
    ReleaseProjectionRequest,
    StrandExposureRoute,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "processing" / "release-projection-v1.json"


def _request(case: dict[str, object]) -> ReleaseProjectionRequest:
    return ReleaseProjectionRequest(
        precursor_top_strand=case["precursor_top_strand"],
        origin=Boundary(offset=0),
        nick=NickEvent(boundary=Boundary(offset=case["nick_boundary"]), strand=Strand.TOP),
        release_cut=DuplexCut(
            top=Boundary(offset=case["top_cut_boundary"]),
            bottom=Boundary(offset=case["bottom_cut_boundary"]),
        ),
        release_site_span=Span(start=Boundary(offset=8), end=Boundary(offset=12)),
        route=StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        constraints=ReleaseProjectionConstraints(
            require_release_site_downstream_of_nick=True,
            require_complete_downstream_separation=True,
        ),
    )


def test_release_projection_matches_sanitized_origin_and_nonzero_fixtures() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for name in ("origin_nick", "nonzero_nick"):
        case = fixture[name]
        result = project_released_strand_state(_request(case))

        assert result.report.status == "valid"
        assert result.projection is not None
        assert result.projection.active_strand is Strand.BOTTOM
        assert result.projection.retained_partner_strand is Strand.TOP
        assert result.projection.active_product_sequence == case["expected_active_product"]
        assert result.projection.retained_partner_sequence == case["expected_retained_partner"]
        assert result.projection.active_nick_boundary.offset == (
            case["bottom_cut_boundary"] - case["nick_boundary"]
        )
        assert [item.precursor_index for item in result.projection.active_product_lineage] == list(
            range(case["bottom_cut_boundary"] - 1, -1, -1)
        )


def test_release_projection_supports_the_opposite_literal_strand_route() -> None:
    request = ReleaseProjectionRequest(
        precursor_top_strand="AACCGGTTAA",
        origin=Boundary(offset=0),
        nick=NickEvent(boundary=Boundary(offset=2), strand=Strand.BOTTOM),
        release_cut=DuplexCut(top=Boundary(offset=8), bottom=Boundary(offset=7)),
        release_site_span=None,
        route=StrandExposureRoute.TOP_ACTIVE_AFTER_BOTTOM_NICK,
        constraints=ReleaseProjectionConstraints(
            require_release_site_downstream_of_nick=False,
            require_complete_downstream_separation=True,
        ),
    )

    result = project_released_strand_state(request)

    assert result.report.status == "valid"
    assert result.projection is not None
    assert result.projection.active_strand is Strand.TOP
    assert result.projection.retained_partner_strand is Strand.BOTTOM
    assert result.projection.active_product_sequence == "AACCGGTT"
    assert result.projection.retained_partner_sequence == "TT"


def test_top_active_projection_allows_an_empty_retained_partner_at_origin() -> None:
    request = ReleaseProjectionRequest(
        precursor_top_strand="AACCGGTTAA",
        origin=Boundary(offset=0),
        nick=NickEvent(boundary=Boundary(offset=0), strand=Strand.BOTTOM),
        release_cut=DuplexCut(top=Boundary(offset=8), bottom=Boundary(offset=7)),
        release_site_span=None,
        route=StrandExposureRoute.TOP_ACTIVE_AFTER_BOTTOM_NICK,
        constraints=ReleaseProjectionConstraints(
            require_release_site_downstream_of_nick=False,
            require_complete_downstream_separation=True,
        ),
    )

    result = project_released_strand_state(request)

    assert result.report.status == "valid"
    assert result.projection is not None
    assert result.projection.active_product_sequence == "AACCGGTT"
    assert result.projection.retained_partner_sequence == ""
    assert result.projection.active_nick_boundary == Boundary(offset=0)


def test_bottom_active_product_is_stored_five_prime_to_three_prime() -> None:
    request = ReleaseProjectionRequest(
        precursor_top_strand="AACCGGTTAA",
        origin=Boundary(offset=1),
        nick=NickEvent(boundary=Boundary(offset=2), strand=Strand.TOP),
        release_cut=DuplexCut(top=Boundary(offset=8), bottom=Boundary(offset=7)),
        release_site_span=None,
        route=StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        constraints=ReleaseProjectionConstraints(
            require_release_site_downstream_of_nick=False,
            require_complete_downstream_separation=True,
        ),
    )

    result = project_released_strand_state(request)

    assert result.projection is not None
    assert result.projection.active_product_sequence == "ACCGGT"
    assert result.projection.active_nick_boundary == Boundary(offset=5)
    assert [item.precursor_index for item in result.projection.active_product_lineage] == [
        6,
        5,
        4,
        3,
        2,
        1,
    ]


def test_release_projection_aggregates_cut_and_site_failures() -> None:
    case = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["origin_nick"]
    request = _request(case).model_copy(
        update={
            "nick": NickEvent(boundary=Boundary(offset=9), strand=Strand.TOP),
            "release_cut": DuplexCut(top=Boundary(offset=14), bottom=Boundary(offset=13)),
            "release_site_span": Span(start=Boundary(offset=4), end=Boundary(offset=8)),
        }
    )

    result = project_released_strand_state(request)

    assert result.projection is None
    assert [item.code for item in result.report.diagnostics] == [
        "HOP-PROC-001",
        "HOP-PROC-002",
        "HOP-PROC-003",
    ]


def test_release_projection_contract_rejects_route_and_nick_strand_drift() -> None:
    case = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["origin_nick"]
    request = _request(case)

    try:
        ReleaseProjectionRequest(
            precursor_top_strand=request.precursor_top_strand,
            origin=request.origin,
            nick=NickEvent(boundary=request.nick.boundary, strand=Strand.BOTTOM),
            release_cut=request.release_cut,
            release_site_span=request.release_site_span,
            route=request.route,
            constraints=request.constraints,
        )
    except ValueError as error:
        assert "route requires a top-strand nick" in str(error)
    else:
        raise AssertionError("Expected route/nick contract validation to fail.")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"retained_partner_strand": "bottom"}, "must differ"),
        ({"active_product_sequence": "A"}, "derive from the precursor"),
        ({"active_nick_boundary": {"offset": 999}}, "nick boundary"),
    ],
)
def test_released_state_rejects_internally_inconsistent_serialization(
    change: dict[str, object],
    message: str,
) -> None:
    case = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["origin_nick"]
    projection = project_released_strand_state(_request(case)).projection
    assert projection is not None
    data = projection.model_dump(mode="json")
    data.update(change)

    with pytest.raises(ValidationError, match=message):
        ReleasedStrandState.model_validate_json(json.dumps(data))


def test_bottom_state_rejects_ascending_lineage_coordinates() -> None:
    case = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["origin_nick"]
    projection = project_released_strand_state(_request(case)).projection
    assert projection is not None
    data = projection.model_dump(mode="json")
    for index, lineage in enumerate(data["active_product_lineage"]):
        lineage["precursor_index"] = index

    with pytest.raises(ValidationError, match="strand-oriented"):
        ReleasedStrandState.model_validate_json(json.dumps(data))

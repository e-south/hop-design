"""A physical source-strand choice must not hide a valid whole hairpin."""

import pytest

from hop_design.design.construction.comparison_regions import architecture_facts
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.models.construction import FinalPayloadReference, SourceOrientation
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.coordinates import Boundary
from hop_design.models.payload import ExactPayload
from tests.contract.test_foldback_construction_discovery import _nickase, _request
from tests.integration.test_complete_construction_discovery import (
    _construction_request,
    _discover_raw,
    _verified_asymmetric_foldback_design,
)


@pytest.fixture(scope="module")
def routes(tmp_path_factory):
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(_request(_nickase(motif="ACATTT")))
    design = _verified_asymmetric_foldback_design(tmp_path_factory.mktemp("both-source-strands"))
    request = _construction_request(payload=payload, foldback=foldback, basal=None, design=design)
    result = _discover_raw(request, foldback=foldback, basal=None, design=design)
    return {r.payload_source_map.segments[0].orientation: r for r in result.realizations}


def test_both_source_strands_describe_same_hairpin_without_changing_records(routes):
    originals = {k: r.model_dump_json() for k, r in routes.items()}
    assert set(routes) == {SourceOrientation.FORWARD, SourceOrientation.REVERSE_COMPLEMENT}
    facts = []
    for route in routes.values():
        hairpin = describe_hairpin(route)
        assert hairpin.state.molecules[0].sequence == "AAAAGACAACAAAATGTTGTCTTTT"
        assert (hairpin.stem_primary_span.start.offset, hairpin.stem_primary_span.end.offset) == (
            4,
            8,
        )
        assert (hairpin.stem_return_span.start.offset, hairpin.stem_return_span.end.offset) == (
            17,
            21,
        )
        assert (hairpin.loop_span.start.offset, hairpin.loop_span.end.offset) == (11, 14)
        assert hairpin.open_side_paired_positions == 4
        assert hairpin.loop_side_paired_bp == 3
        facts.append(architecture_facts(hairpin))
    assert (
        facts[0]["hairpin.region.stem_primary.contacts"]
        == facts[1]["hairpin.region.stem_primary.contacts"]
    )
    assert len(facts[1]["hairpin.region.stem_primary.contacts"]) == 4
    assert {k: r.model_dump_json() for k, r in routes.items()} == originals


def test_payload_source_orientation_remains_evidence_not_a_sequence_search(routes):
    route = routes[SourceOrientation.REVERSE_COMPLEMENT]
    segment = route.payload_source_map.segments[0]
    bad_map = route.payload_source_map.model_copy(
        update={
            "segments": (segment.model_copy(update={"orientation": SourceOrientation.FORWARD}),)
        }
    )
    with pytest.raises(ValueError, match="payload"):
        describe_hairpin(route.model_copy(update={"payload_source_map": bad_map}))

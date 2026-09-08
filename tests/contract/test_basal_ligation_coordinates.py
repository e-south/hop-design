"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_ligation_coordinates.py

Checks adapter pairing and retained source positions at displaced basal nicks.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pytest
import yaml

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.models.construction import LocalNeighborhoodRequest, SearchScope
from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.coordinates import Boundary
from hop_design.models.sequence import reverse_complement_iupac


def _request(strand: str, offset: int, *, future_release: bool = False) -> LocalNeighborhoodRequest:
    path = Path(__file__).resolve().parents[2] / "examples/basal-junction/request.yaml"
    content = yaml.safe_load(path.read_text())
    if not future_release:
        content["endpoint"] = "hairpin_pcr_duplex"
        content["geometry_domain"].pop("future_release")
    content["geometry_domain"].update(nick_strand=strand, nick_offsets_nt=[offset])
    content["search"]["max_retained_overhead_nt"] = 12
    return LocalNeighborhoodRequest.model_validate_json(json.dumps(content))


@pytest.mark.parametrize(("strand", "offset"), (("top", 1), ("bottom", 6)))
def test_adapter_pairing_ends_at_nick_not_payload(strand: str, offset: int) -> None:
    request = _request(strand, offset)

    result = discover_basal_neighborhood(request)

    assert result.realizations
    for record in result.realizations:
        pairing = record.projection.pairing_state
        payload_start = record.payload_source_map.segments[0].source_span.start.offset
        assert pairing.source_span.end == record.basal_nick.boundary
        assert payload_start - pairing.source_span.end.offset == offset
        assert pairing.source_span.length.value == 4
        assert record.projection.annealing_obligation.proximal_annealing_nt == 4
        assert record.projection.annealing_obligation.annealing_completion_nt == 11
        assert record.retained_overhead.retained_overhead_nt == offset + 4
        assert (
            sum(p.material_role == "source" for p in record.retained_overhead.positions) == offset
        )


def test_future_end_includes_retained_source_before_adapter_bases() -> None:
    request = _request("bottom", 6, future_release=True)

    result = discover_basal_neighborhood(request)

    assert result.realizations
    for record in result.realizations:
        start = record.basal_nick.boundary.offset
        end = record.payload_source_map.segments[0].source_span.start.offset
        retained = reverse_complement_iupac(record.source_precursor_sequence[start:end])
        return_arm = retained + record.proximal_adapter_sequence
        action = record.future_release_action
        assert action is not None
        assert return_arm[:4] == reverse_complement_iupac(action.requirement.cohesive_end_sequence)
        projected = tuple(
            p.adapter_index
            for p in record.projection.pairing_state.pairs
            if p.participates_in_end_projection
        )
        assert projected == ()


def test_nick_evidence_must_agree_with_achieved_geometry() -> None:
    record = discover_basal_neighborhood(_request("top", 1)).realizations[0]
    changed_boundary = Boundary(offset=record.basal_nick.boundary.offset + 1)
    site = record.nicked_duplex.sites[0]
    changed_site = site.model_copy(
        update={"nick": site.nick.model_copy(update={"boundary": changed_boundary})}
    )
    content = {
        field: getattr(record, field)
        for field in type(record).model_fields
        if field != "basal_realization_id"
    }
    content["basal_nick"] = record.basal_nick.model_copy(update={"boundary": changed_boundary})
    content["nicked_duplex"] = record.nicked_duplex.model_copy(update={"sites": (changed_site,)})

    with pytest.raises(ValueError, match="nick must agree with the achieved geometry"):
        BasalRealizationRecord.create(**content)


def test_unconstrained_retained_base_is_enumerated_not_filled() -> None:
    request = _request("top", 1)
    request = request.model_copy(
        update={"search": request.search.model_copy(update={"scope": SearchScope.ALL_REALIZATIONS})}
    )

    result = discover_basal_neighborhood(request)

    assert result.discovery.disposition.completion.value == "complete"
    assert {
        record.source_precursor_sequence[record.basal_nick.boundary.offset]
        for record in result.realizations
    } == {"A", "C", "G", "T"}

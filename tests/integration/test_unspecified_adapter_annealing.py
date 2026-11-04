"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_unspecified_adapter_annealing.py

Checks local discovery with an unresolved full adapter association requirement.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.projections.basal import project_basal_feasibility
from hop_design.export.construction.basal_svg import render_basal_projection_svg
from hop_design.models.construction import ConstructionEndpoint, LocalNeighborhoodRequest
from hop_design.models.construction.complete.pcr.pairing import complete_adapter_pairing
from tests.contract.test_basal_construction_discovery import _request
from tests.integration.test_adapter_annealing_completion import _adapter_case
from tests.integration.test_complete_construction_discovery import _discover_raw


def _unresolved_request():
    data = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX).model_dump(
        mode="python", by_alias=True
    )
    data["geometry_domain"]["minimum_adapter_annealing_nt"] = None
    return LocalNeighborhoodRequest.model_validate(data)


def test_local_discovery_does_not_require_a_full_adapter_length() -> None:
    request = _unresolved_request()
    result = discover_basal_neighborhood(request)
    fixed = discover_basal_neighborhood(_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))
    assert result.realizations
    assert [
        (item.source_precursor_sequence, item.projection.pairing_state)
        for item in result.realizations
    ] == [
        (item.source_precursor_sequence, item.projection.pairing_state)
        for item in fixed.realizations
    ]
    for item in result.realizations:
        obligation = item.projection.annealing_obligation
        assert obligation.proximal_annealing_nt == 4
        assert obligation.minimum_annealing_nt is None
        assert obligation.required_annealing_nt is None
        assert obligation.annealing_completion_nt is None
        assert obligation.mismatch_fraction is None
        assert obligation.warnings == ()
        forged = obligation.model_dump()
        forged["annealing_completion_nt"] = 0
        with pytest.raises(ValidationError, match="exact counts"):
            type(obligation).model_validate(forged)
    assert type(result).model_validate_json(result.model_dump_json()) == result
    projection = project_basal_feasibility(result)
    assert all(row.required_annealing_nt is None for row in projection.realizations)
    assert b"full annealing unspecified" in render_basal_projection_svg(projection)


def test_complete_pairing_requires_the_full_association_requirement() -> None:
    result = discover_basal_neighborhood(_unresolved_request())
    with pytest.raises(ValueError, match="explicit adapter annealing requirement"):
        complete_adapter_pairing(result.realizations[0], source_prefix="A" * 20)


def test_unresolved_association_is_a_composition_input_error(tmp_path: Path) -> None:
    construction, foldback, basal, design = _adapter_case(tmp_path, "TGCAGTCTGACAAAA")
    local_data = basal.discovery.request.model_dump(mode="python", by_alias=True)
    local_data["geometry_domain"]["minimum_adapter_annealing_nt"] = None
    basal = discover_basal_neighborhood(LocalNeighborhoodRequest.model_validate(local_data))
    construction = type(construction).model_validate(
        {**construction.model_dump(mode="python"), "basal_result_id": basal.result_id}
    )
    with pytest.raises(ValueError, match="explicit adapter annealing requirement"):
        _discover_raw(construction, foldback=foldback, basal=basal, design=design)

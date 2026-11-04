"""Enumerate explicit recognition ownership without merging it into end geometry."""

import json

import pytest
from pydantic import ValidationError

from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.domains import survey_domains
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


def document():
    data = survey_document()
    data["schema"] = "hop.interface-survey/v2"
    data["release"].pop("basal_projection", None)
    data["release"]["basal_projections"] = [
        {"product_end": "right", "recognition_material": owner}
        for owner in ("source_duplex", "endpoint_material")
    ]
    return data


def test_both_ownership_permissions_remain_distinct_complete_branch_inputs():
    data = document()
    data["placements"] = [{"left_bp": 6, "right_bp": 0}]
    data["basal"]["annealing_lengths_nt"] = [17]
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    branches = SurveyBranches(request)
    assert branches.count == 2
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=16, release_site_pairs=100)
    products = [branches.product(0, branch=i, limits=limits) for i in range(2)]
    assert {p.release.basal_projection.recognition_material for p in products} == {
        "source_duplex",
        "endpoint_material",
    }
    assert all(
        p.ends.left.payload_end_offset_bp == 6 and p.ends.right.payload_end_offset_bp == 0
        for p in products
    )
    assert products[0].construction_source() != products[1].construction_source()
    assert survey_domains(request)["basal_release_recognition_material"]["values"] == [
        "endpoint_material",
        "source_duplex",
    ]
    data["release"]["basal_projections"].reverse()
    assert InterfaceSurveyRequest.model_validate_json(json.dumps(data)) == request


@pytest.mark.parametrize("case", ["empty", "duplicate", "singular", "legacy-schema"])
def test_projection_domain_is_explicit_and_old_authoring_fails_closed(case):
    data = document()
    if case == "empty":
        data["release"]["basal_projections"] = []
    elif case == "duplicate":
        data["release"]["basal_projections"].append(data["release"]["basal_projections"][0])
    elif case == "singular":
        data["release"]["basal_projection"] = data["release"].pop("basal_projections")[0]
    else:
        data["schema"] = "hop.interface-survey/v1"
    with pytest.raises(ValidationError):
        InterfaceSurveyRequest.model_validate_json(json.dumps(data))

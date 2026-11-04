"""Additional source cuts need explicit, portable fragment-cleanup permission."""

import json

import pytest

from hop_design import construction
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_construction_intent import STEM


def _intent(product="released_insert"):
    original = {"stem_arm": STEM, "product": product}
    context = json.loads(construction.resolve_design_request(original).json_bytes)["permissions"]
    context["source_cleanup"] = {"preferred_maximum_nt": 10, "absolute_maximum_nt": 15}
    return {**original, "context": context}


def test_source_cleanup_permission_survives_intent_survey_and_product_translation():
    intent = _intent()
    resolved = json.loads(construction.resolve_design_request(intent).json_bytes)
    cleanup = intent["context"]["source_cleanup"]
    effective = resolved["effective_request"]
    assert effective["source_cleanup"] == cleanup
    survey = InterfaceSurveyRequest.model_validate_json(json.dumps(effective))
    product = SurveyBranches(survey).product(
        0,
        branch=0,
        limits=SurveyEvaluationLimits(local_nodes=10, local_realizations=10, release_site_pairs=10),
    )
    assert product.source_cleanup.model_dump(mode="json") == cleanup
    source = product.construction_source()
    assert "source_cleanup" not in source.composition.model_dump(mode="json")


def test_missing_cleanup_permission_does_not_change_existing_request_bytes():
    resolved = json.loads(
        construction.resolve_design_request(
            {"stem_arm": STEM, "product": "released_insert"}
        ).json_bytes
    )
    assert "source_cleanup" not in resolved["permissions"]
    assert "source_cleanup" not in resolved["effective_request"]


def test_cleanup_permission_rejects_invalid_length_ladder():
    intent = _intent()
    intent["context"]["source_cleanup"]["absolute_maximum_nt"] = 9
    with pytest.raises(ValueError, match="Absolute fragment maximum"):
        construction.resolve_design_request(intent)

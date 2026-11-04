"""A survey declares molecular scope without inheriting teaching search quotas."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hop_design.models.construction.surveys.request import InterfaceSurveyRequest

ROOT = Path(__file__).resolve().parents[2]


def survey_document():
    seed = json.loads((ROOT / "examples/complete-construction/product-request.json").read_text())
    ends = seed.pop("ends")
    seed["schema"] = "hop.interface-survey/v2"
    seed.pop("endpoint")
    seed.pop("enumeration")
    seed["targets"] = {}
    seed["interfaces"] = {
        side: {key: ends[side][key] for key in ("orientation", "overhang_end")}
        for side in ("left", "right")
    }
    seed["placements"] = [{"left_bp": 0, "right_bp": 0}, {"left_bp": 6, "right_bp": 6}]
    for family in ("foldback", "basal"):
        search = seed[family].pop("search")
        seed[family]["max_retained_overhead_nt"] = search["max_retained_overhead_nt"]
    seed["basal"]["annealing_lengths_nt"] = [10, 17, 24]
    seed["basal"]["geometry"].pop("minimum_adapter_annealing_nt")
    seed["release"].pop("max_site_pairs")
    seed["release"]["basal_projections"] = [seed["release"].pop("basal_projection")]
    return seed


def test_full_domain_is_explicit_without_an_execution_quota():
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    assert request.targets.pair_count == 65536
    assert request.targets.pair_at(65535) == ("TTTT", "TTTT")
    assert request.stem_arm == survey_document()["stem_arm"]
    assert [(p.left_bp, p.right_bp) for p in request.placements] == [(0, 0), (6, 6)]
    assert request.basal.annealing_lengths_nt == (10, 17, 24)
    assert request.interfaces.left.orientation.value == "forward"
    assert request.interfaces.right.orientation.value == "reverse"
    serialized = request.model_dump(mode="json", by_alias=True)
    assert "search" not in serialized["foldback"]
    assert "enumeration" not in serialized
    assert "max_site_pairs" not in serialized["release"]


@pytest.mark.parametrize("family", ["foldback", "basal"])
def test_computing_limits_cannot_silently_narrow_molecular_scope(family):
    document = survey_document()
    document[family]["search"] = {"result_quota": 1}
    with pytest.raises(ValidationError, match="search"):
        InterfaceSurveyRequest.model_validate_json(json.dumps(document))


@pytest.mark.parametrize("edit", ["duplicate_placements", "duplicate_annealing", "zero_annealing"])
def test_permission_domains_reject_repetition_or_invalid_lengths(edit):
    document = survey_document()
    if edit == "duplicate_placements":
        document["placements"].append(document["placements"][0])
    else:
        document["basal"]["annealing_lengths_nt"] = (
            [10, 10] if edit == "duplicate_annealing" else [0]
        )
    with pytest.raises(ValidationError):
        InterfaceSurveyRequest.model_validate_json(json.dumps(document))


def test_association_length_has_one_authoring_location():
    document = survey_document()
    document["basal"]["geometry"]["minimum_adapter_annealing_nt"] = 17
    with pytest.raises(ValidationError, match="minimum_adapter_annealing_nt"):
        InterfaceSurveyRequest.model_validate_json(json.dumps(document))


def test_survey_rejects_unknown_method_before_creating_an_execution_index():
    document = survey_document()
    document["basal"]["enzymes"]["allowed_enzyme_ids"].append("example:enzyme/missing@1")
    with pytest.raises(ValidationError, match="unknown enzymes"):
        InterfaceSurveyRequest.model_validate_json(json.dumps(document))


def test_released_interface_survey_requires_pcr_material_policies():
    document = survey_document()
    document["materialization"]["endpoint_auxiliaries"] = None
    with pytest.raises(ValidationError, match="basal-bearing endpoint"):
        InterfaceSurveyRequest.model_validate_json(json.dumps(document))
